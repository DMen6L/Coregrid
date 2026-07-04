"""update supplier phone validation

Revision ID: a1b2c3d4e5f6
Revises: f4a8c9d1e2b3
Create Date: 2026-07-04 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "f4a8c9d1e2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint("ck_suppliers_phone_number", "suppliers", type_="check")
    op.execute(
        "UPDATE suppliers "
        "SET phone_number = '+' || phone_number "
        "WHERE phone_number ~ '^7[0-9]{10}$'"
    )
    op.create_check_constraint(
        "ck_suppliers_phone_number",
        "suppliers",
        "phone_number ~ '^(8[0-9]{10}|\\+7[0-9]{10})$'",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint("ck_suppliers_phone_number", "suppliers", type_="check")
    op.execute(
        "UPDATE suppliers "
        "SET phone_number = phone_number || '0' "
        "WHERE phone_number ~ '^8[0-9]{10}$'"
    )
    op.create_check_constraint(
        "ck_suppliers_phone_number",
        "suppliers",
        "char_length(phone_number) = 12",
    )
