"""quantity_lowstock_migrate

Revision ID: 1b65fddf1fed
Revises: 78bdda7dc8d7
Create Date: 2026-07-26 13:44:31.440619

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b65fddf1fed'
down_revision: Union[str, Sequence[str], None] = '78bdda7dc8d7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "products",
        sa.Column(
            "quantity_unit",
            sa.String(length=20),
            server_default="шт",
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
    )
    op.drop_constraint("uq_products_name_company", "products", type_="unique")
    op.create_unique_constraint(
        "uq_products_name_company_unit",
        "products",
        ["name", "company_id", "quantity_unit"],
    )
    op.create_check_constraint(
        "ck_products_quantity_unit_not_empty",
        "products",
        "char_length(quantity_unit) > 0",
    )
    op.create_check_constraint(
        "ck_products_low_stock_threshold",
        "products",
        "low_stock_threshold >= 0",
    )
    op.drop_constraint(
        "ck_product_suppliers_quantity_unit_not_empty",
        "product_suppliers",
        type_="check",
    )
    op.drop_constraint(
        "ck_product_suppliers_low_stock_threshold",
        "product_suppliers",
        type_="check",
    )
    op.drop_column("product_suppliers", "quantity_unit")
    op.drop_column("product_suppliers", "low_stock_threshold")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "product_suppliers",
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
    )
    op.add_column(
        "product_suppliers",
        sa.Column(
            "quantity_unit",
            sa.String(length=20),
            server_default="шт",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "ck_product_suppliers_low_stock_threshold",
        "product_suppliers",
        "low_stock_threshold >= 0",
    )
    op.create_check_constraint(
        "ck_product_suppliers_quantity_unit_not_empty",
        "product_suppliers",
        "char_length(quantity_unit) > 0",
    )
    op.drop_constraint(
        "ck_products_low_stock_threshold",
        "products",
        type_="check",
    )
    op.drop_constraint(
        "ck_products_quantity_unit_not_empty",
        "products",
        type_="check",
    )
    op.drop_constraint("uq_products_name_company_unit", "products", type_="unique")
    op.create_unique_constraint(
        "uq_products_name_company",
        "products",
        ["name", "company_id"],
    )
    op.drop_column("products", "low_stock_threshold")
    op.drop_column("products", "quantity_unit")
