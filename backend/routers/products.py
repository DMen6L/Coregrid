from typing import Annotated, cast

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from sqlalchemy import String, case, func, or_, select
from sqlalchemy.dialects.postgresql import aggregate_order_by, array
from sqlalchemy.orm import selectinload

from app.models import Company, Product, ProductSupplier, Supplier, Tag
from app.schemas import (
    PaginatedResponse,
    ProductAtomicCreate,
    ProductCreate,
    ProductResponse,
    ProductSummaryResponse,
    ProductSupplierCreate,
    ProductSupplierResponse,
    ProductSupplierUpdate,
    ProductUpdate,
)
from helpers.dependencies import DbSession
from helpers.pagination import aggr_paginate
from helpers.transactions import (
    commit_or_raise,
    create_or_resolve_company,
    create_or_resolve_supplier,
    flush_or_raise,
    get_or_create_tags,
)
from helpers.update_helpers import (
    check_unique_constraints,
    validate_update,
)
from helpers.pricing import calculate_floor_price

router = APIRouter(prefix="/products", tags=["products"])


@router.get(
    "",
    response_model=PaginatedResponse[ProductSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_products_by_name(
    db: DbSession,
    search: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> PaginatedResponse[ProductSummaryResponse]:
    tag_summary = (
        select(
            Product.id.label("product_id"),
            func.coalesce(
                func.array_agg(
                    aggregate_order_by(Tag.name, Tag.name),
                ).filter(Tag.id.is_not(None)),
                array([], type_=String),
            ).label("tags"),
        )
        .select_from(Product)
        .outerjoin(Product.tags)
        .group_by(Product.id)
        .subquery()
    )

    supplier_summary = (
        select(
            ProductSupplier.product_id.label("product_id"),
            func.count(ProductSupplier.id).label("suppliers_count"),
            func.coalesce(func.sum(ProductSupplier.quantity), 0).label(
                "total_quantity"
            ),
        )
        .group_by(ProductSupplier.product_id)
        .subquery()
    )

    ranked_available_supplier = (
        select(
            ProductSupplier.product_id.label("product_id"),
            ProductSupplier.purchase_price.label("min_purchase_price"),
            ProductSupplier.margin_percent.label("margin_percent"),
            ProductSupplier.sale_price.label("min_sale_price"),
            func.row_number()
            .over(
                partition_by=ProductSupplier.product_id,
                order_by=(
                    ProductSupplier.sale_price.asc(),
                    ProductSupplier.purchase_price.asc(),
                    ProductSupplier.id.asc(),
                ),
            )
            .label("rank"),
        )
        .where(ProductSupplier.quantity > 0)
        .subquery()
    )

    cheapest_available_supplier = (
        select(ranked_available_supplier)
        .where(ranked_available_supplier.c.rank == 1)
        .subquery()
    )

    summary_statement = (
        select(
            Product.id.label("id"),
            Product.name.label("name"),
            Product.created_at.label("created_at"),
            Product.quantity_unit.label("quantity_unit"),
            Product.low_stock_threshold.label("low_stock_threshold"),
            Company.name.label("company_name"),
            tag_summary.c.tags.label("tags"),
            func.coalesce(supplier_summary.c.suppliers_count, 0).label(
                "suppliers_count"
            ),
            func.coalesce(supplier_summary.c.total_quantity, 0).label("total_quantity"),
            cheapest_available_supplier.c.min_purchase_price,
            cheapest_available_supplier.c.margin_percent,
            cheapest_available_supplier.c.min_sale_price,
            case(
                (func.coalesce(supplier_summary.c.total_quantity, 0) == 0, "out"),
                (
                    supplier_summary.c.total_quantity <= Product.low_stock_threshold,
                    "low",
                ),
                else_="available",
            ).label("stock_status"),
        )
        .select_from(Product)
        .join(Product.company)
        .outerjoin(tag_summary, tag_summary.c.product_id == Product.id)
        .outerjoin(supplier_summary, supplier_summary.c.product_id == Product.id)
        .outerjoin(
            cheapest_available_supplier,
            cheapest_available_supplier.c.product_id == Product.id,
        )
        .order_by(Product.id)
    )

    count_statement = select(func.count(Product.id)).select_from(Product)

    if search and (search := search.strip()):
        search_condition = or_(
            Product.name.ilike(f"%{search}%"),
            Product.tags.any(Tag.name.ilike(f"%{search}%")),
        )
        summary_statement = summary_statement.where(search_condition)
        count_statement = count_statement.where(search_condition)

    return aggr_paginate(
        db=db,
        statement=summary_statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=ProductSummaryResponse,
    )


@router.get(
    "/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def get_product_by_id(
    db: DbSession,
    id: Annotated[int, Path(gt=0)],
):
    statement = (
        select(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.supplier_links).selectinload(ProductSupplier.supplier),
        )
        .where(Product.id == id)
    )

    product = db.scalars(statement).one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product with such id does not exist.",
        )

    return product


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def app_product(
    db: DbSession,
    product_data: ProductCreate,
):
    tags = get_or_create_tags(db, product_data.tags)

    product = Product(
        name=product_data.name,
        company_id=product_data.company_id,
        low_stock_threshold=product_data.low_stock_threshold,
        quantity_unit=product_data.quantity_unit,
        tags=tags,
    )

    db.add(product)
    commit_or_raise(db)
    db.refresh(product)

    return product


@router.post(
    "/{product_id}/links",
    response_model=list[ProductSupplierResponse],
    status_code=status.HTTP_201_CREATED,
)
def add_supplier_links(
    db: DbSession,
    supplier_links_data: Annotated[list[ProductSupplierCreate], Body(min_length=1)],
    product_id: Annotated[int, Path(gt=0)],
):
    statement = select(Product).where(Product.id == product_id)
    product = db.execute(statement).scalar_one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No product with such id in the database.",
        )

    supplier_ids = [supplier_link.supplier_id for supplier_link in supplier_links_data]
    if len(supplier_ids) != len(set(supplier_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Each supplier may be linked to a product only once per request.",
        )

    suppliers = db.scalars(select(Supplier).where(Supplier.id.in_(supplier_ids))).all()
    suppliers_by_id = {supplier.id: supplier for supplier in suppliers}

    missing_supplier_ids = sorted(set(supplier_ids) - suppliers_by_id.keys())
    if missing_supplier_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "message": "One or more suppliers were not found.",
                "supplier_ids": missing_supplier_ids,
            },
        )

    supplier_links = []
    for supplier_link_data in supplier_links_data:
        sale_price = supplier_link_data.sale_price
        if sale_price is None:
            sale_price = calculate_floor_price(
                purchase_price=supplier_link_data.purchase_price,
                margin_percent=supplier_link_data.margin_percent,
            )

        supplier_links.append(
            ProductSupplier(
                product=product,
                supplier=suppliers_by_id[supplier_link_data.supplier_id],
                purchase_price=supplier_link_data.purchase_price,
                margin_percent=supplier_link_data.margin_percent,
                sale_price=sale_price,
                quantity=supplier_link_data.quantity,
            )
        )

    db.add_all(supplier_links)
    commit_or_raise(db)

    supplier_link_ids = [supplier_link.id for supplier_link in supplier_links]
    created_supplier_links = db.scalars(
        select(ProductSupplier)
        .options(
            selectinload(ProductSupplier.product),
            selectinload(ProductSupplier.supplier),
        )
        .where(ProductSupplier.id.in_(supplier_link_ids))
        .order_by(ProductSupplier.id)
    ).all()

    return created_supplier_links


@router.post(
    "/full",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_product_atomic(
    db: DbSession,
    data: ProductAtomicCreate,
) -> Product:
    company_id = create_or_resolve_company(data, db)

    product_schema = {
        "company_id": company_id,
        "name": data.product_name,
        "quantity_unit": data.quantity_unit,
        "low_stock_threshold": data.low_stock_threshold,
    }

    check_unique_constraints(
        db=db,
        model=Product,
        constraint_name="uq_products_name_company_unit",
        values=product_schema,
    )

    tags = get_or_create_tags(db, data.tags)

    product = Product(
        **product_schema,
        tags=tags,
    )

    db.add(product)
    flush_or_raise(db)

    for product_link in data.product_links:
        supplier_id = create_or_resolve_supplier(product_link, db)
        sale_price = (
            product_link.sale_price
            if product_link.sale_price
            else calculate_floor_price(
                product_link.purchase_price,
                product_link.margin_percent,
            )
        )

        product_supplier_schema = {
            "product_id": product.id,
            "supplier_id": supplier_id,
            "purchase_price": product_link.purchase_price,
            "margin_percent": product_link.margin_percent,
            "sale_price": sale_price,
            "quantity": product_link.quantity,
        }

        check_unique_constraints(
            db=db,
            model=ProductSupplier,
            constraint_name="uq_product_suppliers_product_supplier",
            values=product_supplier_schema,
        )
        product_supplier = ProductSupplier(**product_supplier_schema)

        db.add(product_supplier)

    commit_or_raise(db)

    statement = (
        select(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.tags),
            selectinload(Product.supplier_links).selectinload(ProductSupplier.supplier),
        )
        .where(Product.id == product.id)
    )

    response = db.scalars(statement).one()

    return response


@router.patch(
    "/{id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def patch_product(
    db: DbSession,
    id: Annotated[int, Path(gt=0)],
    patch_data: ProductUpdate,
):
    statement = (
        select(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.supplier_links).selectinload(ProductSupplier.supplier),
        )
        .where(Product.id == id)
    )

    product = db.scalars(statement).one_or_none()

    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No product with such id exists.",
        )

    update_data = cast(
        dict[str, object],
        patch_data.model_dump(exclude_unset=True),
    )

    validate_update(
        db=db,
        model=Product,
        constraint_name="uq_products_name_company_unit",
        update_data=update_data,
        update_obj=product,
    )

    tag_names = cast(list[str], update_data.pop("tags", None))

    if "company_id" in update_data:
        company = db.get(
            Company,
            update_data["company_id"],
        )
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company with such id does not exist.",
            )

    for field, value in update_data.items():
        setattr(product, field, value)

    if tag_names is not None:
        product.tags = get_or_create_tags(db, tag_names)

    commit_or_raise(db)
    db.refresh(product)

    return product


@router.patch(
    "/{product_id}/links/{link_id}",
    response_model=ProductSupplierResponse,
    status_code=status.HTTP_200_OK,
)
def patch_product_links(
    db: DbSession,
    patch_data: ProductSupplierUpdate,
    product_id: Annotated[int, Path(gt=0)],
    link_id: Annotated[int, Path(gt=0)],
):
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="product with this id is not found.",
        )

    statement = (
        select(ProductSupplier)
        .options(
            selectinload(ProductSupplier.product),
            selectinload(ProductSupplier.supplier),
        )
        .where(ProductSupplier.id == link_id)
    )
    product_supplier = db.scalars(statement).one_or_none()
    if product_supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="link with this id is not found.",
        )
    if product_supplier.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product with supplier link providing is not found.",
        )

    update_data = cast(
        dict[str, object],
        patch_data.model_dump(exclude_unset=True),
    )

    if "supplier_id" in update_data:
        supplier_id = cast(int, update_data["supplier_id"])
        supplier = db.get(Supplier, supplier_id)

        if supplier is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Supplier with such id does not exist.",
            )

    # sale price check
    candidate_purchase_price = cast(
        int,
        update_data.get(
            "purchase_price",
            product_supplier.purchase_price,
        ),
    )
    candidate_margin_percent = cast(
        int,
        update_data.get(
            "margin_percent",
            product_supplier.margin_percent,
        ),
    )
    candidate_sale_price = cast(
        int,
        update_data.get(
            "sale_price",
            product_supplier.sale_price,
        ),
    )
    floor_price = calculate_floor_price(
        candidate_purchase_price,
        candidate_margin_percent,
    )

    if candidate_sale_price < floor_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="sale_price cannot be lower than calculated floor price.",
        )

    validate_update(
        db=db,
        model=ProductSupplier,
        constraint_name="uq_product_suppliers_product_supplier",
        update_data=update_data,
        update_obj=product_supplier,
    )

    for field, value in update_data.items():
        setattr(product_supplier, field, value)

    commit_or_raise(db)
    db.refresh(product_supplier)

    return product_supplier


@router.delete(
    "/{product_id}/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_link(
    db: DbSession,
    product_id: Annotated[int, Path(gt=0)],
    link_id: Annotated[int, Path(gt=0)],
) -> None:
    if db.get(Product, product_id) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product with such id for the link is not found",
        )

    statement = (
        select(ProductSupplier)
        .options(
            selectinload(ProductSupplier.product),
            selectinload(ProductSupplier.supplier),
        )
        .where(ProductSupplier.id == link_id)
    )
    product_supplier = db.scalars(statement).one_or_none()

    if product_supplier is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link for product and supplier with such id does not exist",
        )
    if product_supplier.product_id != product_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Link connects to the wrong product",
        )
    if product_supplier.quantity > 0:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete supplier link with stock",
        )
    if product_supplier.restock_lines or product_supplier.sale_lines:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete supplier link with stock movements tied",
        )

    db.delete(product_supplier)
    commit_or_raise(db)
