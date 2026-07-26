from datetime import date, datetime, time, timedelta
from typing import Literal, TypeVar

from pydantic import BaseModel
from sqlalchemy import Select, func, outerjoin, select
from sqlalchemy.orm import Session

from app.models import Product, ProductSupplier, Sale, SaleLine, Supplier
from app.schemas import (
    DailySalesResponse,
    PaginatedResponse,
    SummariesResponse,
    TopProduct,
    TopSupplier,
)
from devs import DbSession


OrmT = TypeVar("OrmT")
ResponseT = TypeVar("ResponseT", bound=BaseModel)

BestSalesMode = Literal[
    "quantity",
    "revenue",
    "gross_profit",
]


def get_best_sales_expr(mode: BestSalesMode):
    match mode:
        case "quantity":
            return func.sum(SaleLine.sale_quantity)

        case "revenue":
            return func.sum(SaleLine.unit_sale_price_snapshot * SaleLine.sale_quantity)

        case "gross_profit":
            return func.sum(
                (SaleLine.unit_sale_price_snapshot - SaleLine.unit_cost_snapshot)
                * SaleLine.sale_quantity
            )


def build_summaries(
    db: DbSession, days: int, best_sales_mode: BestSalesMode
) -> SummariesResponse:
    # Essential dates for queries
    today = date.today()
    start_of_today = datetime.combine(today, time.min)
    start_of_tomorrow = start_of_today + timedelta(days=1)
    start_of_period = start_of_today - timedelta(days=days - 1)

    # Dashboard first four summary subqueries(stock state and today sales)
    dashboard_sales_value_subquery = (
        select(
            func.coalesce(
                func.sum(SaleLine.unit_sale_price_snapshot * SaleLine.sale_quantity),
                0,
            )
        )
        .join(SaleLine.sale)
        .where(Sale.created_at >= start_of_today, Sale.created_at < start_of_tomorrow)
        .scalar_subquery()
    )
    dashboard_sales_count_subquery = (
        select(func.count(func.distinct(Sale.id)))
        .where(Sale.created_at >= start_of_today, Sale.created_at < start_of_tomorrow)
        .scalar_subquery()
    )

    product_stock_summary = (
        select(
            ProductSupplier.product_id.label("product_id"),
            func.coalesce(func.sum(ProductSupplier.quantity), 0).label(
                "total_quantity"
            ),
        )
        .group_by(ProductSupplier.product_id)
        .subquery()
    )
    total_quantity = func.coalesce(product_stock_summary.c.total_quantity, 0)
    low_stock_subquery = (
        select(func.count(Product.id))
        .select_from(Product)
        .outerjoin(
            product_stock_summary,
            product_stock_summary.c.product_id == Product.id,
        )
        .where(
            total_quantity > 0,
            total_quantity <= Product.low_stock_threshold,
        )
        .scalar_subquery()
    )
    out_of_stock_subquery = (
        select(func.count(Product.id))
        .select_from(Product)
        .outerjoin(
            product_stock_summary,
            product_stock_summary.c.product_id == Product.id,
        )
        .where(total_quantity == 0)
        .scalar_subquery()
    )

    # Helpers
    sale_date = func.date(Sale.created_at)
    sales_expr = get_best_sales_expr(best_sales_mode)
    sales_metric = func.coalesce(
        sales_expr,
        0,
    ).label("metric")

    # Statements
    initial_summaries_statement = select(
        dashboard_sales_value_subquery.label("dashboard_sales_value"),
        dashboard_sales_count_subquery.label("dashboard_sales_count"),
        low_stock_subquery.label("low_stock"),
        out_of_stock_subquery.label("out_of_stock"),
    )
    latest_sales_statement = (
        select(
            sale_date.label("date"),
            func.coalesce(
                func.sum(SaleLine.unit_sale_price_snapshot * SaleLine.sale_quantity),
                0,
            ).label("sales_value"),
        )
        .select_from(SaleLine)
        .join(SaleLine.sale)
        .where(
            Sale.created_at >= start_of_period,
            Sale.created_at < start_of_tomorrow,
        )
        .group_by(sale_date)
        .order_by(sale_date)
    )
    top_products_statement = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            sales_metric,
        )
        .select_from(SaleLine)
        .join(SaleLine.product_supplier)
        .join(ProductSupplier.product)
        .join(SaleLine.sale)
        .where(
            Sale.created_at >= start_of_period,
            Sale.created_at < start_of_tomorrow,
        )
        .group_by(
            Product.id,
            Product.name,
        )
        .order_by(sales_metric.desc())
        .limit(5)
    )
    top_suppliers_statement = (
        select(
            Supplier.id.label("supplier_id"),
            Supplier.name.label("supplier_name"),
            func.count(ProductSupplier.product_id).label("supplied_products"),
        )
        .select_from(Supplier)
        .join(Supplier.product_links)
        .group_by(Supplier.id, Supplier.name)
        .order_by(func.count(ProductSupplier.product_id).desc())
        .limit(5)
    )

    # Results
    initial_summaries = db.execute(initial_summaries_statement).one()
    latest_sales = [
        DailySalesResponse(
            **latest_sale,
        )
        for latest_sale in db.execute(latest_sales_statement).mappings().all()
    ]
    top_products = [
        TopProduct(
            **top_product,
        )
        for top_product in db.execute(top_products_statement).mappings().all()
    ]
    top_suppliers = [
        TopSupplier(
            **top_supplier,
        )
        for top_supplier in db.execute(top_suppliers_statement).mappings().all()
    ]

    return SummariesResponse(
        dashboard_sales_value=initial_summaries.dashboard_sales_value,
        dashboard_sales_count=initial_summaries.dashboard_sales_count,
        low_stock=initial_summaries.low_stock,
        out_of_stock=initial_summaries.out_of_stock,
        latest_sales=latest_sales,
        top_products=top_products,
        top_suppliers=top_suppliers,
    )


def paginate(
    db: Session,
    statement: Select[tuple[OrmT]],
    count_statement: Select[tuple[int]],
    page: int,
    page_size: int,
    response_schema: type[ResponseT],
) -> PaginatedResponse[ResponseT]:
    total = db.execute(count_statement).scalar_one()

    paginated_statement = statement.offset((page - 1) * page_size).limit(page_size)

    records = db.scalars(paginated_statement).all()

    items = [response_schema.model_validate(record) for record in records]

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse[ResponseT](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )


def aggr_paginate(
    db: Session,
    statement: Select[tuple[OrmT]],
    count_statement: Select[tuple[int]],
    page: int,
    page_size: int,
    response_schema: type[ResponseT],
) -> PaginatedResponse[ResponseT]:
    total = db.execute(count_statement).scalar_one()

    paginated_statement = statement.offset((page - 1) * page_size).limit(page_size)

    rows = db.execute(paginated_statement).mappings().all()

    items = [response_schema.model_validate(dict(row)) for row in rows]

    total_pages = (total + page_size - 1) // page_size

    return PaginatedResponse[ResponseT](
        items=items,
        page=page,
        page_size=page_size,
        total=total,
        total_pages=total_pages,
        has_next=page < total_pages,
        has_previous=page > 1,
    )
