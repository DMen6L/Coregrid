"""add missing checks

Revision ID: c2d00b79afe9
Revises: 5d7c05bcf2f2
Create Date: 2026-07-02 19:06:55.689688

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2d00b79afe9"
down_revision: Union[str, Sequence[str], None] = "5d7c05bcf2f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_check_constraint(
        "ck_suppliers_phone_number",
        "suppliers",
        "char_length(phone_number) = 12",
    )

    op.create_check_constraint(
        "ck_products_price",
        "products",
        "price > 0",
    )

    op.create_check_constraint(
        "ck_products_quantity",
        "products",
        "quantity >= 0",
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_constraint("ck_products_quantity", "products", type_="check")
    op.drop_constraint("ck_products_price", "products", type_="check")
    op.drop_constraint("ck_suppliers_phone_number", "suppliers", type_="check")
