"""add_admin_performance_indexes

Add performance indexes for admin pages to improve query performance
on customers and orders tables.

Indexes added:
- Customers: email, company_name, composite (customer_type, is_active)
- Orders: order_number, status, order_date

Revision ID: 6a07301cffee
Revises: d7882101cf73
Create Date: 2025-12-02 00:07:26.561118

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6a07301cffee"
down_revision: str | None = "d7882101cf73"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema.

    Add performance indexes for admin pages. These indexes improve
    query performance for filtering, searching, and sorting operations
    on the customers and orders tables.

    Note: This migration is designed to be idempotent and will only
    create indexes if the tables exist. If customers or orders tables
    don't exist yet, this migration will skip index creation.

    The indexes are also defined in the ORM models, so they will be
    created automatically when tables are created via SQLAlchemy.
    """
    # Get connection to check if tables exist
    conn = op.get_bind()

    # Check if customers table exists
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()

    if "customers" in tables:
        # Customers table indexes
        op.create_index(
            "ix_customers_email",
            "customers",
            ["email"],
            unique=True,
            if_not_exists=True,
        )
        op.create_index(
            "ix_customers_company_name",
            "customers",
            ["company_name"],
            if_not_exists=True,
        )
        op.create_index(
            "idx_customers_type_active",
            "customers",
            ["customer_type", "is_active"],
            if_not_exists=True,
        )

    if "orders" in tables:
        # Orders table indexes
        op.create_index(
            "ix_orders_order_number",
            "orders",
            ["order_number"],
            unique=True,
            if_not_exists=True,
        )
        op.create_index(
            "ix_orders_status",
            "orders",
            ["status"],
            if_not_exists=True,
        )
        op.create_index(
            "ix_orders_order_date",
            "orders",
            ["order_date"],
            if_not_exists=True,
        )


def downgrade() -> None:
    """Downgrade database schema.

    Remove performance indexes added for admin pages.

    Note: We only drop indexes that are not critical for the application.
    Primary key and foreign key indexes are preserved.
    """
    # Drop orders table indexes
    op.drop_index("ix_orders_order_date", table_name="orders", if_exists=True)
    op.drop_index("ix_orders_status", table_name="orders", if_exists=True)
    op.drop_index("ix_orders_order_number", table_name="orders", if_exists=True)

    # Drop customers table indexes
    op.drop_index("idx_customers_type_active", table_name="customers", if_exists=True)
    op.drop_index("ix_customers_company_name", table_name="customers", if_exists=True)
    op.drop_index("ix_customers_email", table_name="customers", if_exists=True)
