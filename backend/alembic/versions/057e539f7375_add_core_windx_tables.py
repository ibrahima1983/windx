"""Add core windx tables

Revision ID: 057e539f7375
Revises: 95aa64961de9
Create Date: 2025-12-19 18:00:57.771144

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "057e539f7375"
down_revision: Union[str, None] = "95aa64961de9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # Enable LTREE extension
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")

    # Add role column to users table (if it doesn't exist)
    # Check if column exists first
    op.execute("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'users' AND column_name = 'role') THEN
                ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'customer';
            END IF;
        END $$;
    """)

    # Create all tables with their indexes as defined in models
    # This will create all tables and indexes defined in SQLAlchemy models
    from app.database.base import Base

    op.execute("-- Creating tables and indexes from SQLAlchemy models")

    # Note: The individual table creation below is for explicit control
    # In a fresh database, you could also use: Base.metadata.create_all(bind=op.get_bind())

    # Create manufacturing_types table
    op.create_table(
        "manufacturing_types",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("base_category", sa.String(length=50), nullable=True),
        sa.Column("image_url", sa.String(length=500), nullable=True),
        sa.Column("base_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("base_weight", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_manufacturing_types_id", "manufacturing_types", ["id"])
    op.create_index("ix_manufacturing_types_name", "manufacturing_types", ["name"], unique=True)
    op.create_index("ix_manufacturing_types_is_active", "manufacturing_types", ["is_active"])
    op.create_index("ix_manufacturing_types_created_at", "manufacturing_types", ["created_at"])

    # Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("company_name", sa.String(length=200), nullable=True),
        sa.Column("contact_person", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("address", JSONB(), nullable=True),
        sa.Column("customer_type", sa.String(length=50), nullable=True),
        sa.Column("tax_id", sa.String(length=100), nullable=True),
        sa.Column("payment_terms", sa.String(length=100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_customers_id", "customers", ["id"])
    op.create_index("ix_customers_email", "customers", ["email"], unique=True)
    op.create_index("ix_customers_company_name", "customers", ["company_name"])
    op.create_index("ix_customers_customer_type", "customers", ["customer_type"])
    op.create_index("ix_customers_is_active", "customers", ["is_active"])
    op.create_index("ix_customers_created_at", "customers", ["created_at"])
    op.create_index("idx_customers_type_active", "customers", ["customer_type", "is_active"])
    op.create_index("idx_customers_address", "customers", ["address"], postgresql_using="gin")

    # Create attribute_nodes table
    op.create_table(
        "attribute_nodes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("manufacturing_type_id", sa.Integer(), nullable=True),
        sa.Column("parent_node_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("node_type", sa.String(length=50), nullable=False),
        sa.Column("data_type", sa.String(length=50), nullable=True),
        sa.Column("ltree_path", sa.Text(), nullable=True),  # Will be LTREE type
        sa.Column("depth", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_required", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "price_impact_type", sa.String(length=50), nullable=False, server_default="'fixed'"
        ),
        sa.Column("price_impact_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("price_formula", sa.Text(), nullable=True),
        sa.Column("weight_impact_value", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("weight_formula", sa.Text(), nullable=True),
        sa.Column("technical_impact_formula", sa.Text(), nullable=True),
        sa.Column("display_condition", JSONB(), nullable=True),
        sa.Column("validation_rules", JSONB(), nullable=True),
        sa.Column("ui_component", sa.String(length=50), nullable=True),
        sa.Column("ui_props", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["manufacturing_type_id"], ["manufacturing_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["parent_node_id"], ["attribute_nodes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_attribute_nodes_id", "attribute_nodes", ["id"])
    op.create_index(
        "ix_attribute_nodes_manufacturing_type_id", "attribute_nodes", ["manufacturing_type_id"]
    )
    op.create_index("ix_attribute_nodes_parent_node_id", "attribute_nodes", ["parent_node_id"])
    op.create_index("ix_attribute_nodes_node_type", "attribute_nodes", ["node_type"])
    op.create_index("ix_attribute_nodes_is_active", "attribute_nodes", ["is_active"])
    op.create_index("ix_attribute_nodes_created_at", "attribute_nodes", ["created_at"])

    # Convert ltree_path column to LTREE type
    op.execute(
        "ALTER TABLE attribute_nodes ALTER COLUMN ltree_path TYPE ltree USING ltree_path::ltree"
    )
    op.create_index(
        "idx_attribute_nodes_ltree_path", "attribute_nodes", ["ltree_path"], postgresql_using="gist"
    )

    # Create configurations table
    op.create_table(
        "configurations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("manufacturing_type_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="'draft'"),
        sa.Column("reference_code", sa.String(length=50), nullable=True),
        sa.Column("base_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "calculated_weight",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("calculated_technical_data", JSONB(), nullable=False, server_default="{}"),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["manufacturing_type_id"], ["manufacturing_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_configurations_id", "configurations", ["id"])
    op.create_index(
        "ix_configurations_manufacturing_type_id", "configurations", ["manufacturing_type_id"]
    )
    op.create_index("ix_configurations_customer_id", "configurations", ["customer_id"])
    op.create_index("ix_configurations_status", "configurations", ["status"])
    op.create_index(
        "ix_configurations_reference_code", "configurations", ["reference_code"], unique=True
    )
    op.create_index("ix_configurations_created_at", "configurations", ["created_at"])
    # Note: idx_configurations_customer_status is defined in the model

    # Create configuration_selections table
    op.create_table(
        "configuration_selections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("configuration_id", sa.Integer(), nullable=False),
        sa.Column("attribute_node_id", sa.Integer(), nullable=False),
        sa.Column("string_value", sa.String(length=500), nullable=True),
        sa.Column("numeric_value", sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("json_value", JSONB(), nullable=True),
        sa.Column(
            "calculated_price_impact",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "calculated_weight_impact",
            sa.Numeric(precision=10, scale=2),
            nullable=False,
            server_default="0",
        ),
        sa.Column("selection_path", sa.Text(), nullable=True),  # Will be LTREE type
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["configuration_id"], ["configurations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["attribute_node_id"], ["attribute_nodes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_configuration_selections_id", "configuration_selections", ["id"])
    op.create_index(
        "ix_configuration_selections_configuration_id",
        "configuration_selections",
        ["configuration_id"],
    )
    op.create_index(
        "ix_configuration_selections_attribute_node_id",
        "configuration_selections",
        ["attribute_node_id"],
    )
    op.create_index(
        "ix_configuration_selections_created_at", "configuration_selections", ["created_at"]
    )
    # Note: Performance indexes for configuration_selections are defined in the model

    # Convert selection_path column to LTREE type
    op.execute(
        "ALTER TABLE configuration_selections ALTER COLUMN selection_path TYPE ltree USING selection_path::ltree"
    )

    # Create configuration_templates table
    op.create_table(
        "configuration_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("manufacturing_type_id", sa.Integer(), nullable=False),
        sa.Column(
            "template_type", sa.String(length=50), nullable=False, server_default="'standard'"
        ),
        sa.Column("is_public", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("success_rate", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("estimated_price", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("estimated_weight", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["manufacturing_type_id"], ["manufacturing_types.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_configuration_templates_id", "configuration_templates", ["id"])
    op.create_index(
        "ix_configuration_templates_manufacturing_type_id",
        "configuration_templates",
        ["manufacturing_type_id"],
    )
    op.create_index(
        "ix_configuration_templates_template_type", "configuration_templates", ["template_type"]
    )
    op.create_index(
        "ix_configuration_templates_is_public", "configuration_templates", ["is_public"]
    )
    op.create_index(
        "ix_configuration_templates_is_active", "configuration_templates", ["is_active"]
    )
    op.create_index(
        "ix_configuration_templates_created_at", "configuration_templates", ["created_at"]
    )

    # Create template_selections table
    op.create_table(
        "template_selections",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("attribute_node_id", sa.Integer(), nullable=False),
        sa.Column("string_value", sa.String(length=500), nullable=True),
        sa.Column("numeric_value", sa.Numeric(precision=15, scale=6), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("json_value", JSONB(), nullable=True),
        sa.Column("selection_path", sa.Text(), nullable=True),  # Will be LTREE type
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["template_id"], ["configuration_templates.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["attribute_node_id"], ["attribute_nodes.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_template_selections_id", "template_selections", ["id"])
    op.create_index("ix_template_selections_template_id", "template_selections", ["template_id"])
    op.create_index(
        "ix_template_selections_attribute_node_id", "template_selections", ["attribute_node_id"]
    )
    op.create_index("ix_template_selections_created_at", "template_selections", ["created_at"])

    # Convert selection_path column to LTREE type
    op.execute(
        "ALTER TABLE template_selections ALTER COLUMN selection_path TYPE ltree USING selection_path::ltree"
    )

    # Create quotes table
    op.create_table(
        "quotes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("configuration_id", sa.Integer(), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=True),
        sa.Column("quote_number", sa.String(length=50), nullable=False),
        sa.Column("subtotal", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(precision=5, scale=4), nullable=False, server_default="0"),
        sa.Column(
            "tax_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"
        ),
        sa.Column(
            "discount_amount", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0"
        ),
        sa.Column("total_amount", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="'draft'"),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["configuration_id"], ["configurations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_quotes_id", "quotes", ["id"])
    op.create_index("ix_quotes_configuration_id", "quotes", ["configuration_id"])
    op.create_index("ix_quotes_customer_id", "quotes", ["customer_id"])
    op.create_index("ix_quotes_quote_number", "quotes", ["quote_number"], unique=True)
    op.create_index("ix_quotes_status", "quotes", ["status"])
    op.create_index("ix_quotes_created_at", "quotes", ["created_at"])
    # Note: Performance indexes for quotes are defined in the model

    # Create orders table
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("quote_id", sa.Integer(), nullable=True),
        sa.Column("order_number", sa.String(length=50), nullable=False),
        sa.Column("order_date", sa.Date(), nullable=False),
        sa.Column("required_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="'confirmed'"),
        sa.Column("special_instructions", sa.Text(), nullable=True),
        sa.Column("installation_address", JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["quote_id"], ["quotes.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_orders_id", "orders", ["id"])
    op.create_index("ix_orders_quote_id", "orders", ["quote_id"])
    op.create_index("ix_orders_order_number", "orders", ["order_number"], unique=True)
    op.create_index("ix_orders_status", "orders", ["status"])
    op.create_index("ix_orders_order_date", "orders", ["order_date"])
    op.create_index("ix_orders_created_at", "orders", ["created_at"])
    # Note: Performance indexes for orders are defined in the model

    # Create order_items table
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("configuration_id", sa.Integer(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("unit_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("total_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "production_status", sa.String(length=50), nullable=False, server_default="'pending'"
        ),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["configuration_id"], ["configurations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_order_items_id", "order_items", ["id"])
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_index("ix_order_items_configuration_id", "order_items", ["configuration_id"])
    op.create_index("ix_order_items_production_status", "order_items", ["production_status"])
    op.create_index("ix_order_items_created_at", "order_items", ["created_at"])

    # Note: Additional performance indexes are defined in the SQLAlchemy models
    # and will be created automatically by SQLAlchemy when tables are created.
    # This migration focuses on creating the core table structure.


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop tables in reverse order (respecting foreign key constraints)
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("quotes")
    op.drop_table("template_selections")
    op.drop_table("configuration_templates")
    op.drop_table("configuration_selections")
    op.drop_table("configurations")
    op.drop_table("attribute_nodes")
    op.drop_table("customers")
    op.drop_table("manufacturing_types")

    # Remove role column from users
    op.drop_index("idx_users_role", "users")
    op.drop_column("users", "role")
