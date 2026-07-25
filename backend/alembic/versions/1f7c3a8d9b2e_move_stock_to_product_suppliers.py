"""move stock to product suppliers

Revision ID: 1f7c3a8d9b2e
Revises: ebffd8b37282
Create Date: 2026-07-24 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "1f7c3a8d9b2e"
down_revision: Union[str, Sequence[str], None] = "ebffd8b37282"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PLACEHOLDER_SUPPLIER_NAME = "__legacy_missing_supplier__"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "product_suppliers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("supplier_id", sa.Integer(), nullable=False),
        sa.Column("purchase_price", sa.Integer(), nullable=False),
        sa.Column("margin_percent", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sale_price", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "quantity_unit",
            sa.String(length=20),
            server_default="шт",
            nullable=False,
        ),
        sa.Column(
            "low_stock_threshold",
            sa.Integer(),
            server_default="5",
            nullable=False,
        ),
        sa.CheckConstraint(
            "purchase_price > 0",
            name="ck_product_suppliers_purchase_price",
        ),
        sa.CheckConstraint(
            "margin_percent >= 0",
            name="ck_product_suppliers_margin_percent",
        ),
        sa.CheckConstraint(
            "sale_price > 0",
            name="ck_product_suppliers_sale_price",
        ),
        sa.CheckConstraint(
            "sale_price * 100 >= purchase_price * (100 + margin_percent)",
            name="ck_product_suppliers_sale_price_floor",
        ),
        sa.CheckConstraint(
            "quantity >= 0",
            name="ck_product_suppliers_quantity",
        ),
        sa.CheckConstraint(
            "char_length(quantity_unit) > 0",
            name="ck_product_suppliers_quantity_unit_not_empty",
        ),
        sa.CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_product_suppliers_low_stock_threshold",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_product_suppliers_product_id_products",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["supplier_id"],
            ["suppliers.id"],
            name="fk_product_suppliers_supplier_id_suppliers",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "supplier_id",
            name="uq_product_suppliers_product_supplier",
        ),
    )

    op.execute(
        sa.text(
            f"""
            WITH missing_supplier_products AS (
                SELECT EXISTS (
                    SELECT 1 FROM products WHERE supplier_id IS NULL
                ) AS needed
            ),
            candidate_phone AS (
                SELECT '+7000000' || lpad(n::text, 4, '0') AS phone_number
                FROM generate_series(0, 9999) AS n
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM suppliers
                    WHERE phone_number = '+7000000' || lpad(n::text, 4, '0')
                )
                ORDER BY n
                LIMIT 1
            )
            INSERT INTO suppliers (name, phone_number)
            SELECT '{PLACEHOLDER_SUPPLIER_NAME}', candidate_phone.phone_number
            FROM missing_supplier_products, candidate_phone
            WHERE missing_supplier_products.needed
            ON CONFLICT (name) DO NOTHING
            """
        )
    )

    op.execute(
        sa.text(
            f"""
            INSERT INTO product_suppliers (
                product_id,
                supplier_id,
                purchase_price,
                margin_percent,
                sale_price,
                quantity,
                quantity_unit,
                low_stock_threshold
            )
            SELECT
                products.id,
                COALESCE(
                    products.supplier_id,
                    (
                        SELECT suppliers.id
                        FROM suppliers
                        WHERE suppliers.name = '{PLACEHOLDER_SUPPLIER_NAME}'
                    )
                ),
                products.purchase_price,
                products.margin_percent,
                products.sale_price,
                products.quantity,
                products.quantity_unit,
                products.low_stock_threshold
            FROM products
            """
        )
    )

    op.add_column(
        "restock_lines",
        sa.Column("product_supplier_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sale_lines",
        sa.Column("product_supplier_id", sa.Integer(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE restock_lines
            SET product_supplier_id = product_suppliers.id
            FROM product_suppliers
            WHERE product_suppliers.product_id = restock_lines.product_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE sale_lines
            SET product_supplier_id = product_suppliers.id
            FROM product_suppliers
            WHERE product_suppliers.product_id = sale_lines.product_id
            """
        )
    )

    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1 FROM restock_lines WHERE product_supplier_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'restock_lines backfill failed: product_supplier_id is null';
                END IF;

                IF EXISTS (
                    SELECT 1 FROM sale_lines WHERE product_supplier_id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'sale_lines backfill failed: product_supplier_id is null';
                END IF;
            END $$;
            """
        )
    )

    op.alter_column(
        "restock_lines",
        "product_supplier_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "sale_lines",
        "product_supplier_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint(
        "uq_restock_lines_restock_product",
        "restock_lines",
        type_="unique",
    )
    op.drop_constraint(
        "restock_lines_product_id_fkey",
        "restock_lines",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_restock_lines_product_supplier_id_product_suppliers",
        "restock_lines",
        "product_suppliers",
        ["product_supplier_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_restock_lines_restock_product_supplier",
        "restock_lines",
        ["restock_id", "product_supplier_id"],
    )
    op.drop_column("restock_lines", "product_id")

    op.drop_constraint(
        "uq_sale_lines_sale_product",
        "sale_lines",
        type_="unique",
    )
    op.drop_constraint(
        "sale_lines_product_id_fkey",
        "sale_lines",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "fk_sale_lines_product_supplier_id_product_suppliers",
        "sale_lines",
        "product_suppliers",
        ["product_supplier_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_sale_lines_sale_product_supplier",
        "sale_lines",
        ["sale_id", "product_supplier_id"],
    )
    op.drop_column("sale_lines", "product_id")

    op.drop_constraint("products_supplier_id_fkey", "products", type_="foreignkey")
    op.drop_constraint("ck_products_purchase_price", "products", type_="check")
    op.drop_constraint("ck_products_margin_percent", "products", type_="check")
    op.drop_constraint("ck_products_sale_price", "products", type_="check")
    op.drop_constraint("ck_products_sale_price_floor", "products", type_="check")
    op.drop_constraint("ck_products_quantity", "products", type_="check")
    op.drop_constraint(
        "ck_products_quantity_unit_not_empty",
        "products",
        type_="check",
    )
    op.drop_constraint("ck_products_low_stock_threshold", "products", type_="check")

    op.drop_column("products", "supplier_id")
    op.drop_column("products", "purchase_price")
    op.drop_column("products", "margin_percent")
    op.drop_column("products", "sale_price")
    op.drop_column("products", "quantity")
    op.drop_column("products", "quantity_unit")
    op.drop_column("products", "low_stock_threshold")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        sa.text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM product_suppliers
                    GROUP BY product_id
                    HAVING count(*) > 1
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade: products with multiple suppliers exist';
                END IF;

                IF EXISTS (
                    SELECT 1
                    FROM products
                    LEFT JOIN product_suppliers
                        ON product_suppliers.product_id = products.id
                    WHERE product_suppliers.id IS NULL
                ) THEN
                    RAISE EXCEPTION
                        'Cannot downgrade: catalog products without suppliers exist';
                END IF;
            END $$;
            """
        )
    )

    op.add_column(
        "products",
        sa.Column("supplier_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("purchase_price", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("margin_percent", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("sale_price", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("quantity", sa.Integer(), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("quantity_unit", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "products",
        sa.Column("low_stock_threshold", sa.Integer(), nullable=True),
    )

    op.execute(
        sa.text(
            f"""
            UPDATE products
            SET
                supplier_id = CASE
                    WHEN product_suppliers.supplier_id = (
                        SELECT suppliers.id
                        FROM suppliers
                        WHERE suppliers.name = '{PLACEHOLDER_SUPPLIER_NAME}'
                    )
                    THEN NULL
                    ELSE product_suppliers.supplier_id
                END,
                purchase_price = product_suppliers.purchase_price,
                margin_percent = product_suppliers.margin_percent,
                sale_price = product_suppliers.sale_price,
                quantity = product_suppliers.quantity,
                quantity_unit = product_suppliers.quantity_unit,
                low_stock_threshold = product_suppliers.low_stock_threshold
            FROM product_suppliers
            WHERE product_suppliers.product_id = products.id
            """
        )
    )

    op.alter_column(
        "products",
        "purchase_price",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "products",
        "margin_percent",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "products",
        "sale_price",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "products",
        "quantity",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="0",
    )
    op.alter_column(
        "products",
        "quantity_unit",
        existing_type=sa.String(length=20),
        nullable=False,
        server_default="шт",
    )
    op.alter_column(
        "products",
        "low_stock_threshold",
        existing_type=sa.Integer(),
        nullable=False,
        server_default="5",
    )

    op.create_foreign_key(
        "products_supplier_id_fkey",
        "products",
        "suppliers",
        ["supplier_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_check_constraint(
        "ck_products_purchase_price",
        "products",
        "purchase_price > 0",
    )
    op.create_check_constraint(
        "ck_products_margin_percent",
        "products",
        "margin_percent >= 0",
    )
    op.create_check_constraint(
        "ck_products_sale_price",
        "products",
        "sale_price > 0",
    )
    op.create_check_constraint(
        "ck_products_sale_price_floor",
        "products",
        "sale_price * 100 >= purchase_price * (100 + margin_percent)",
    )
    op.create_check_constraint(
        "ck_products_quantity",
        "products",
        "quantity >= 0",
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

    op.add_column(
        "restock_lines",
        sa.Column("product_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "sale_lines",
        sa.Column("product_id", sa.Integer(), nullable=True),
    )

    op.execute(
        sa.text(
            """
            UPDATE restock_lines
            SET product_id = product_suppliers.product_id
            FROM product_suppliers
            WHERE product_suppliers.id = restock_lines.product_supplier_id
            """
        )
    )
    op.execute(
        sa.text(
            """
            UPDATE sale_lines
            SET product_id = product_suppliers.product_id
            FROM product_suppliers
            WHERE product_suppliers.id = sale_lines.product_supplier_id
            """
        )
    )

    op.alter_column(
        "restock_lines",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "sale_lines",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    op.drop_constraint(
        "uq_restock_lines_restock_product_supplier",
        "restock_lines",
        type_="unique",
    )
    op.drop_constraint(
        "fk_restock_lines_product_supplier_id_product_suppliers",
        "restock_lines",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "restock_lines_product_id_fkey",
        "restock_lines",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_restock_lines_restock_product",
        "restock_lines",
        ["restock_id", "product_id"],
    )
    op.drop_column("restock_lines", "product_supplier_id")

    op.drop_constraint(
        "uq_sale_lines_sale_product_supplier",
        "sale_lines",
        type_="unique",
    )
    op.drop_constraint(
        "fk_sale_lines_product_supplier_id_product_suppliers",
        "sale_lines",
        type_="foreignkey",
    )
    op.create_foreign_key(
        "sale_lines_product_id_fkey",
        "sale_lines",
        "products",
        ["product_id"],
        ["id"],
    )
    op.create_unique_constraint(
        "uq_sale_lines_sale_product",
        "sale_lines",
        ["sale_id", "product_id"],
    )
    op.drop_column("sale_lines", "product_supplier_id")

    op.drop_table("product_suppliers")
