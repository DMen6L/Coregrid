from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.models import (
    Product,
    ProductSupplier,
    Sale,
    SaleLine,
    Supplier,
    User,
    Workspace,
    WorkspaceInvitation,
    WorkspaceMembership,
)
from app.schemas import (
    DailySalesResponse,
    SummariesResponse,
    TopProduct,
    TopSupplier,
)
from helpers.dependencies import DbSession
from app.type_definitions import BestSalesMode
from utils import get_best_sales_expr


def build_summaries(
    db: DbSession,
    membership: WorkspaceMembership,
    days: int,
    best_sales_mode: BestSalesMode,
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
        .where(
            Sale.created_at >= start_of_today,
            Sale.created_at < start_of_tomorrow,
            Sale.workspace_id == membership.workspace_id,
        )
        .scalar_subquery()
    )
    dashboard_sales_count_subquery = (
        select(func.count(func.distinct(Sale.id)))
        .where(
            Sale.created_at >= start_of_today,
            Sale.created_at < start_of_tomorrow,
            Sale.workspace_id == membership.workspace_id,
        )
        .scalar_subquery()
    )

    product_stock_summary = (
        select(
            ProductSupplier.product_id.label("product_id"),
            func.coalesce(func.sum(ProductSupplier.quantity), 0).label(
                "total_quantity"
            ),
        )
        .where(ProductSupplier.workspace_id == membership.workspace_id)
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
            Product.workspace_id == membership.workspace_id,
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
        .where(
            total_quantity == 0,
            Product.workspace_id == membership.workspace_id,
        )
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
            Sale.workspace_id == membership.workspace_id,
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
            Sale.workspace_id == membership.workspace_id,
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
        .where(Supplier.workspace_id == membership.workspace_id)
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


def get_user_info(
    db: DbSession,
    user: User,
):
    now = datetime.now()

    memberships = db.scalars(
        select(WorkspaceMembership)
        .options(selectinload(WorkspaceMembership.workspace))
        .where(WorkspaceMembership.user_id == user.id)
    ).all()

    workspaces = [
        {
            "id": membership.workspace_id,
            "name": membership.workspace.name,
            "role": membership.role,
        }
        for membership in memberships
    ]

    invitations_statement = (
        select(
            WorkspaceInvitation.id.label("id"),
            Workspace.id.label("workspace_id"),
            Workspace.name.label("workspace_name"),
            User.id.label("inviter_user_id"),
            User.name.label("inviter_user_name"),
            User.email.label("inviter_user_email"),
            WorkspaceInvitation.role.label("role"),
            WorkspaceInvitation.created_at.label("created_at"),
            WorkspaceInvitation.expires_at.label("expires_at"),
            WorkspaceInvitation.accepted_at.label("accepted_at"),
            WorkspaceInvitation.revoked_at.label("revoked_at"),
        )
        .select_from(WorkspaceInvitation)
        .join(Workspace, Workspace.id == WorkspaceInvitation.workspace_id)
        .outerjoin(User, User.id == WorkspaceInvitation.inviter_user_id)
        .where(
            WorkspaceInvitation.email == user.email,
            WorkspaceInvitation.accepted_at.is_(None),
            WorkspaceInvitation.revoked_at.is_(None),
            WorkspaceInvitation.expires_at > now,
        )
    )

    invitations = db.execute(invitations_statement).mappings().all()

    return {
        "user": user,
        "workspaces": workspaces,
        "invitations": invitations,
    }
