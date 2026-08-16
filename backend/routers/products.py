from typing import Annotated, cast

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import String, case, func, or_, select
from sqlalchemy.dialects.postgresql import aggregate_order_by, array
from sqlalchemy.orm import selectinload

from app.models import (
    Company,
    Product,
    ProductSupplier,
    Supplier,
    Tag,
    WorkspaceMembership,
)
from app.schemas import (
    AuditLogCreate,
    PaginatedResponse,
    ProductAtomicCreate,
    ProductCreate,
    ProductResponse,
    ProductSummaryResponse,
    ProductSupplierResponse,
    ProductSupplierUpdate,
    ProductUpdate,
)
from app.type_definitions import StockStatus
from helpers.dependencies import (
    DbSession,
    require_workspace_permission,
)
from helpers.pagination import aggr_paginate
from helpers.transactions import (
    commit_or_raise,
    create_or_resolve_company,
    create_or_resolve_supplier,
    flush_or_raise,
    get_or_create_tags,
    record_audit_log,
)
from helpers.update_helpers import (
    check_unique_constraints,
    validate_update,
)
from helpers.pricing import calculate_floor_price

router = APIRouter(prefix="/workspaces/{workspace_id}/products", tags=["products"])


@router.get(
    "",
    response_model=PaginatedResponse[ProductSummaryResponse],
    status_code=status.HTTP_200_OK,
)
def get_products_by_name(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
    search: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    company_name: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    supplier_name: Annotated[str | None, Query(min_length=2, max_length=100)] = None,
    tags: Annotated[list[str] | None, Query(min_length=1)] = None,
    stock_status: Annotated[StockStatus | None, Query()] = None,
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

    total_quantity = func.coalesce(supplier_summary.c.total_quantity, 0)

    stock_status_expr = case(
        (total_quantity == 0, "out"),
        (total_quantity <= Product.low_stock_threshold, "low"),
        else_="available",
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
            stock_status_expr.label("stock_status"),
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

    conditions = [Product.workspace_id == membership.workspace_id]

    if search and (search := search.strip()):
        conditions.append(
            or_(
                Product.name.ilike(f"%{search}%"),
                Product.tags.any(Tag.name.ilike(f"%{search}%")),
            )
        )

    if company_name and (company_name := company_name.strip()):
        conditions.append(Product.company.has(Company.name.ilike(f"%{company_name}%")))

    if supplier_name and (supplier_name := supplier_name.strip()):
        conditions.append(
            Product.supplier_links.any(
                ProductSupplier.supplier.has(Supplier.name.ilike(f"%{supplier_name}%"))
            )
        )

    if tags is not None:
        for tag_name in tags:
            conditions.append(Product.tags.any(Tag.name == tag_name))

    if stock_status is not None:
        conditions.append(stock_status_expr == stock_status)

    summary_statement = summary_statement.where(*conditions)
    count_statement = (
        select(func.count(Product.id))
        .select_from(Product)
        .outerjoin(supplier_summary, supplier_summary.c.product_id == Product.id)
        .where(*conditions)
    )

    return aggr_paginate(
        db=db,
        statement=summary_statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=ProductSummaryResponse,
    )


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def get_product_by_id(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("inventory.read")),
    ],
    product_id: Annotated[int, Path(gt=0)],
) -> Product:
    statement = (
        select(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.supplier_links).selectinload(ProductSupplier.supplier),
        )
        .where(
            Product.id == product_id,
            Product.workspace_id == membership.workspace_id,
        )
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
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    product_data: ProductCreate,
) -> Product:
    tags = get_or_create_tags(
        db=db,
        membership=membership,
        tag_names=product_data.tags,
    )

    company = db.scalar(
        select(Company).where(
            Company.id == product_data.company_id,
            Company.workspace_id == membership.workspace_id,
        )
    )

    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="COmpany with such id is not found for this workspace",
        )

    product_schema = {
        "name": product_data.name,
        "company_id": company.id,
        "low_stock_threshold": product_data.low_stock_threshold,
        "quantity_unit": product_data.quantity_unit,
        "workspace_id": membership.workspace_id,
    }

    check_unique_constraints(
        db=db,
        model=Product,
        constraint_name="uq_products_workspace_name_company_unit",
        values=product_schema,
    )

    product = Product(
        **product_schema,
        tags=tags,
    )

    db.add(product)
    flush_or_raise(db)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            action="product.created",
            entity_type="product",
            entity_id=str(product.id),
            entity_label=product.name,
        ),
    )

    commit_or_raise(db)
    db.refresh(product)

    return product


@router.post(
    "/full",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_product_atomic(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    data: ProductAtomicCreate,
) -> Product:
    company_id = create_or_resolve_company(
        db=db,
        membership=membership,
        data=data,
    )

    product_schema = {
        "company_id": company_id,
        "name": data.product_name,
        "quantity_unit": data.quantity_unit,
        "low_stock_threshold": data.low_stock_threshold,
        "workspace_id": membership.workspace_id,
    }

    check_unique_constraints(
        db=db,
        model=Product,
        constraint_name="uq_products_workspace_name_company_unit",
        values=product_schema,
    )

    tags = get_or_create_tags(
        db=db,
        membership=membership,
        tag_names=data.tags,
    )

    product = Product(
        **product_schema,
        tags=tags,
    )

    db.add(product)
    flush_or_raise(db)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            action="product.created",
            entity_type="product",
            entity_id=str(product.id),
            entity_label=product.name,
            extra_data={
                "company_id": company_id,
                "quantity_unit": product.quantity_unit,
                "low_stock_threshold": product.low_stock_threshold,
                "tags": [tag.name for tag in tags],
                "supplier_links_count": len(data.product_links),
            },
        ),
    )

    for product_link in data.product_links:
        supplier_id = create_or_resolve_supplier(
            db=db,
            membership=membership,
            product_link=product_link,
        )
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
            "workspace_id": membership.workspace_id,
        }

        check_unique_constraints(
            db=db,
            model=ProductSupplier,
            constraint_name="uq_product_suppliers_product_supplier_workspace",
            values=product_supplier_schema,
        )
        product_supplier = ProductSupplier(**product_supplier_schema)

        db.add(product_supplier)
        flush_or_raise(db)

        record_audit_log(
            db=db,
            audit_log_data=AuditLogCreate(
                workspace_id=membership.workspace_id,
                actor_user_id=membership.user_id,
                action="product_supplier.created",
                entity_type="product_supplier",
                entity_id=str(product_supplier.id),
                entity_label=f"{product_supplier.product.name}_{product_supplier.supplier.name}",
            ),
        )

    commit_or_raise(db)

    statement = (
        select(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.tags),
            selectinload(Product.supplier_links).selectinload(ProductSupplier.supplier),
        )
        .where(
            Product.id == product.id,
            Product.workspace_id == membership.workspace_id,
        )
    )

    response = db.scalars(statement).one()

    return response


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
)
def patch_product(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    product_id: Annotated[int, Path(gt=0)],
    patch_data: ProductUpdate,
) -> Product:
    statement = (
        select(Product)
        .options(
            selectinload(Product.company),
            selectinload(Product.supplier_links).selectinload(ProductSupplier.supplier),
            selectinload(Product.tags),
        )
        .where(
            Product.id == product_id,
            Product.workspace_id == membership.workspace_id,
        )
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

    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Product update form cannot be empty",
        )

    validate_update(
        db=db,
        model=Product,
        constraint_name="uq_products_workspace_name_company_unit",
        update_data={
            **update_data,
            "workspace_id": membership.workspace_id,
        },
        update_obj=product,
    )

    changes: dict[str, object] = {}

    tag_names = cast(list[str] | None, update_data.pop("tags", None))

    if "company_id" in update_data:
        company = db.scalar(
            select(Company).where(
                Company.id == update_data["company_id"],
                Company.workspace_id == membership.workspace_id,
            )
        )
        if company is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Company with such id does not exist for this workspace",
            )

    for field, value in update_data.items():
        old_value = getattr(product, field)

        if old_value == value:
            continue

        changes[field] = {
            "old": old_value,
            "new": value,
        }
        setattr(product, field, value)

    if tag_names is not None:
        old_tags = sorted(tag.name for tag in product.tags)
        new_tags = sorted(tag_names)

        if old_tags != new_tags:
            changes["tags"] = {
                "old": old_tags,
                "new": new_tags,
            }

        product.tags = get_or_create_tags(
            db=db,
            membership=membership,
            tag_names=tag_names,
        )

    if changes:
        record_audit_log(
            db=db,
            audit_log_data=AuditLogCreate(
                workspace_id=membership.workspace_id,
                actor_user_id=membership.user_id,
                action="product.updated",
                entity_type="product",
                entity_id=str(product.id),
                entity_label=product.name,
                changes=changes,
            ),
        )

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
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    patch_data: ProductSupplierUpdate,
    product_id: Annotated[int, Path(gt=0)],
    link_id: Annotated[int, Path(gt=0)],
) -> ProductSupplier:
    if (
        db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.workspace_id == membership.workspace_id,
            )
        )
        is None
    ):
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
        .where(
            ProductSupplier.id == link_id,
            ProductSupplier.workspace_id == membership.workspace_id,
        )
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
    update_data["workspace_id"] = membership.workspace_id

    if "supplier_id" in update_data:
        supplier_id = cast(int, update_data["supplier_id"])
        supplier = db.scalar(
            select(Supplier).where(
                Supplier.id == supplier_id,
                Supplier.workspace_id == membership.workspace_id,
            )
        )
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
        constraint_name="uq_product_suppliers_product_supplier_workspace",
        update_data=update_data,
        update_obj=product_supplier,
    )

    changes: dict[str, object] = {}

    for field, value in update_data.items():
        old_value = getattr(product_supplier, field)

        if old_value == value:
            continue

        changes[field] = {
            "old": old_value,
            "new": value,
        }
        setattr(product_supplier, field, value)

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            action="product_supplier.updated",
            entity_type="product_supplier",
            entity_id=str(product_supplier.id),
            entity_label=f"{product_supplier.product.name}_{product_supplier.supplier.name}",
            changes=changes,
        ),
    )

    commit_or_raise(db)
    db.refresh(product_supplier)

    return product_supplier


@router.delete(
    "/{product_id}/links/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product_link(
    db: DbSession,
    membership: Annotated[
        WorkspaceMembership,
        Depends(require_workspace_permission("catalog.write")),
    ],
    product_id: Annotated[int, Path(gt=0)],
    link_id: Annotated[int, Path(gt=0)],
) -> None:
    if (
        db.scalar(
            select(Product).where(
                Product.id == product_id,
                Product.workspace_id == membership.workspace_id,
            )
        )
        is None
    ):
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
        .where(
            ProductSupplier.id == link_id,
            ProductSupplier.workspace_id == membership.workspace_id,
        )
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

    record_audit_log(
        db=db,
        audit_log_data=AuditLogCreate(
            workspace_id=membership.workspace_id,
            actor_user_id=membership.user_id,
            action="product_supplier.deleted",
            entity_type="product_supplier",
            entity_id=str(product_supplier.id),
            entity_label=f"{product_supplier.product.name}_{product_supplier.supplier.name}",
        ),
    )

    db.delete(product_supplier)
    commit_or_raise(db)
