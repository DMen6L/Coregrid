"""add sales

Revision ID: 7a9d21c8f604
Revises: 4f72b0ac9d31
Create Date: 2026-07-07 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "7a9d21c8f604"
down_revision: Union[str, Sequence[str], None] = "4f72b0ac9d31"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "sales",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("stock_movement_id", sa.Integer(), nullable=False),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["stock_movement_id"],
            ["stock_movements.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "stock_movement_id",
            name="uq_sales_stock_movement_id",
        ),
    )
    op.execute(
        "INSERT INTO sales (stock_movement_id, note, created_at) "
        "SELECT id, note, created_at "
        "FROM stock_movements "
        "WHERE movement_type = 'out' "
        "ORDER BY id"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("sales")
