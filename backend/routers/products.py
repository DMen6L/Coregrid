from cProfile import label
from itertools import groupby
from typing import Annotated

from fastapi import APIRouter, Body, HTTPException, Path, Query, status
from sqlalchemy import String, func, or_, outerjoin, select, case
from sqlalchemy.dialects.postgresql import array
from sqlalchemy.orm import selectinload

from app import tags
from app.models import Company, Product, ProductSupplier, Supplier, Tag
from app.pricing import calculate_floor_price
from app.schemas import (
    PaginatedResponse,
    ProductCreate,
    ProductResponse,
    ProductSummaryResponse,
    ProductSupplierCreate,
    ProductSupplierResponse,
)
from app.tags import get_or_create_tags
from devs import DbSession
from errors import commit_or_raise
from utils import aggr_paginate, paginate

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
    supplier_summary = (
        select(
            ProductSupplier.product_id.label("product_id"),
            func.coalesce(func.sum(ProductSupplier.quantity), 0).label(
                "available_quantity"
            ),
            func.count(ProductSupplier.id).label("supplier_count"),
            func.count(ProductSupplier.id)
            .filter(ProductSupplier.quantity > 0)
            .label("available_supplier_count"),
            func.count(ProductSupplier.id)
            .filter(
                ProductSupplier.quantity > 0,
                ProductSupplier.quantity <= ProductSupplier.low_stock_threshold,
            )
            .label("low_supplier_count"),
        )
        .group_by(ProductSupplier.product_id)
        .subquery()
    )

    ranked_supplier = (
        select(
            ProductSupplier.product_id.label("product_id"),
            Supplier.name.label("most_profit_supplier"),
            ProductSupplier.purchase_price.label("available_min_cost"),
            ProductSupplier.margin_percent.label("available_margin"),
            ProductSupplier.sale_price.label("available_min_price"),
            ProductSupplier.low_stock_threshold.label("low_stock_threshold"),
            func.row_number()
            .over(
                partition_by=ProductSupplier.product_id,
                order_by=(ProductSupplier.sale_price.asc(), ProductSupplier.id.asc()),
            )
            .label("rank"),
        )
        .join(ProductSupplier.supplier)
        .where(ProductSupplier.quantity > 0)
        .subquery()
    )

    best_supplier = (
        select(ranked_supplier).where(ranked_supplier.c.rank == 1).subquery()
    )

    tag_summary = (
        select(
            Product.id.label("product_id"),
            func.coalesce(
                func.array_agg(Tag.name).filter(Tag.id.is_not(None)),
                array([], type_=String),
            ).label("tags"),
        )
        .select_from(Product)
        .outerjoin(Product.tags)
        .group_by(Product.id)
        .subquery()
    )

    summary_statement = (
        select(
            Product.id.label("id"),
            Product.name.label("name"),
            tag_summary.c.tags.label("tags"),
            Company.name.label("company_name"),
            best_supplier.c.most_profit_supplier,
            func.greatest(supplier_summary.c.supplier_count - 1, 0).label(
                "other_suppliers_count"
            ),
            func.coalesce(supplier_summary.c.available_quantity, 0).label(
                "available_quantity"
            ),
            best_supplier.c.available_min_cost,
            best_supplier.c.available_margin,
            best_supplier.c.available_min_price,
            best_supplier.c.low_stock_threshold,
            case(
                (supplier_summary.c.supplier_count.is_(None), "out"),
                (supplier_summary.c.available_quantity == 0, "out"),
                (supplier_summary.c.low_supplier_count > 0, "low"),
                else_="available",
            ).label("stock_status"),
        )
        .select_from(Product)
        .join(Product.company)
        .outerjoin(tag_summary, tag_summary.c.product_id == Product.id)
        .outerjoin(supplier_summary, supplier_summary.c.product_id == Product.id)
        .outerjoin(best_supplier, best_supplier.c.product_id == Product.id)
        .order_by(Product.id)
    )
    count_statement = select(func.count(Product.id)).select_from(Product)

    if search and (search := search.strip()):
        condition = or_(
            Product.name.ilike(f"%{search}%"),
        )

        summary_statement = summary_statement.where(condition)
        count_statement = count_statement.where(condition)

    return aggr_paginate(
        db=db,
        statement=summary_statement,
        count_statement=count_statement,
        page=page,
        page_size=page_size,
        response_schema=ProductSummaryResponse,
    )


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
                quantity_unit=supplier_link_data.quantity_unit,
                low_stock_threshold=supplier_link_data.low_stock_threshold,
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
