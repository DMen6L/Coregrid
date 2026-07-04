"""add stock movements

Revision ID: e6a3f4d5c2b1
Revises: c2d00b79afe9
Create Date: 2026-07-03 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e6a3f4d5c2b1"
down_revision: Union[str, Sequence[str], None] = "c2d00b79afe9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "stock_movements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movement_type", sa.String(length=20), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "movement_type in ('in', 'out', 'adjustment')",
            name="ck_stock_movements_type",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "stock_movement_lines",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("movement_id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("quantity_delta", sa.Integer(), nullable=False),
        sa.Column("quantity_before", sa.Integer(), nullable=False),
        sa.Column("quantity_after", sa.Integer(), nullable=False),
        sa.Column("unit_price_snapshot", sa.Integer(), nullable=True),
        sa.CheckConstraint(
            "quantity_delta != 0",
            name="ck_stock_movement_lines_quantity_delta",
        ),
        sa.CheckConstraint(
            "quantity_before >= 0",
            name="ck_stock_movement_lines_quantity_before",
        ),
        sa.CheckConstraint(
            "quantity_after >= 0",
            name="ck_stock_movement_lines_quantity_after",
        ),
        sa.CheckConstraint(
            "unit_price_snapshot is null or unit_price_snapshot > 0",
            name="ck_stock_movement_lines_unit_price_snapshot",
        ),
        sa.ForeignKeyConstraint(
            ["movement_id"],
            ["stock_movements.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"]),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("stock_movement_lines")
    op.drop_table("stock_movements")
