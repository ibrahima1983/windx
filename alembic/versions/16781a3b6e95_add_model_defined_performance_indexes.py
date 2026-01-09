"""Add model-defined performance indexes

Revision ID: 16781a3b6e95
Revises: 9d790dc1c955
Create Date: 2025-12-19 18:24:46.018132

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "16781a3b6e95"
down_revision: Union[str, None] = "9d790dc1c955"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # First, ensure all columns exist that are referenced in indexes
    # This handles cases where the model has evolved but migrations haven't kept up

    # Add missing columns to attribute_nodes table if they don't exist
    op.execute("""
        DO $$ 
        BEGIN 
            -- Add technical_property_type column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'technical_property_type') THEN
                ALTER TABLE attribute_nodes ADD COLUMN technical_property_type VARCHAR(50);
                CREATE INDEX IF NOT EXISTS ix_attribute_nodes_technical_property_type ON attribute_nodes (technical_property_type);
            END IF;
            
            -- Add technical_impact_formula column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'technical_impact_formula') THEN
                ALTER TABLE attribute_nodes ADD COLUMN technical_impact_formula TEXT;
            END IF;
            
            -- Add required column if it doesn't exist (renamed from is_required)
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'required') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'is_required') THEN
                    -- Rename existing column
                    ALTER TABLE attribute_nodes RENAME COLUMN is_required TO required;
                ELSE
                    -- Add new column
                    ALTER TABLE attribute_nodes ADD COLUMN required BOOLEAN NOT NULL DEFAULT FALSE;
                END IF;
            END IF;
            
            -- Add weight_impact column if it doesn't exist (renamed from weight_impact_value)
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'weight_impact') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'weight_impact_value') THEN
                    -- Rename existing column
                    ALTER TABLE attribute_nodes RENAME COLUMN weight_impact_value TO weight_impact;
                ELSE
                    -- Add new column
                    ALTER TABLE attribute_nodes ADD COLUMN weight_impact NUMERIC(10,2) NOT NULL DEFAULT 0;
                END IF;
            END IF;
            
            -- Add sort_order column if it doesn't exist (renamed from display_order)
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'sort_order') THEN
                IF EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'display_order') THEN
                    -- Rename existing column
                    ALTER TABLE attribute_nodes RENAME COLUMN display_order TO sort_order;
                ELSE
                    -- Add new column
                    ALTER TABLE attribute_nodes ADD COLUMN sort_order INTEGER NOT NULL DEFAULT 0;
                END IF;
            END IF;
            
            -- Add description column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'description') THEN
                ALTER TABLE attribute_nodes ADD COLUMN description TEXT;
            END IF;
            
            -- Add help_text column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'help_text') THEN
                ALTER TABLE attribute_nodes ADD COLUMN help_text TEXT;
            END IF;
            
            -- Add weight_formula column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'attribute_nodes' AND column_name = 'weight_formula') THEN
                ALTER TABLE attribute_nodes ADD COLUMN weight_formula TEXT;
            END IF;
            
        END $$;
    """)

    # Add missing columns to quotes table if they don't exist
    op.execute("""
        DO $$ 
        BEGIN 
            -- Add technical_requirements column if it doesn't exist
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'quotes' AND column_name = 'technical_requirements') THEN
                ALTER TABLE quotes ADD COLUMN technical_requirements JSONB;
            END IF;
        END $$;
    """)

    # Create all model-defined performance indexes using IF NOT EXISTS
    # This handles cases where some indexes may already exist from previous migrations

    # Attribute nodes indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_attribute_nodes_mfg_type_node_type ON attribute_nodes (manufacturing_type_id, node_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_attribute_nodes_technical_property ON attribute_nodes (technical_property_type) WHERE technical_property_type IS NOT NULL"
    )

    # Configuration selections indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_config_selections_attr ON configuration_selections (attribute_node_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_config_selections_config ON configuration_selections (configuration_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_config_selections_json ON configuration_selections USING gin (json_value)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_config_selections_path ON configuration_selections USING gist (selection_path)"
    )

    # Configuration templates indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_templates_active_only ON configuration_templates (is_active) WHERE is_active = true"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_templates_mfg_type_template_type ON configuration_templates (manufacturing_type_id, template_type)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_templates_public_active ON configuration_templates (is_public, is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_templates_public_only ON configuration_templates (is_public) WHERE is_public = true"
    )

    # Configurations indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_configurations_mfg_type_status ON configurations (manufacturing_type_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_configurations_technical_data ON configurations USING gin (calculated_technical_data)"
    )

    # Order items indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_order_items_config_status ON order_items (configuration_id, production_status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_order_items_order_status ON order_items (order_id, production_status)"
    )

    # Orders indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_installation_address ON orders USING gin (installation_address)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_quote_status ON orders (quote_id, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_orders_status_date ON orders (status, order_date)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_orders_status_required ON orders (status, required_date)"
    )

    # Quotes indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_quotes_config_status ON quotes (configuration_id, status)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_quotes_customer_status ON quotes (customer_id, status)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_quotes_status_valid ON quotes (status, valid_until)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_quotes_technical_requirements ON quotes USING gin (technical_requirements)"
    )

    # Template selections indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_template_selections_attr_node ON template_selections (attribute_node_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_template_selections_path ON template_selections USING gist (selection_path)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_template_selections_template ON template_selections (template_id)"
    )

    # Fix users.role column default
    op.alter_column(
        "users",
        "role",
        existing_type=sa.VARCHAR(length=50),
        server_default=None,
        existing_nullable=False,
    )

    print("✅ All model-defined performance indexes created successfully")


def downgrade() -> None:
    """Downgrade database schema."""
    # ### commands auto generated by Alembic - please adjust! ###
    op.alter_column(
        "users",
        "role",
        existing_type=sa.VARCHAR(length=50),
        server_default=sa.text("'customer'::character varying"),
        existing_nullable=False,
    )

    # Drop indexes
    op.execute("DROP INDEX IF EXISTS idx_template_selections_template")
    op.execute("DROP INDEX IF EXISTS idx_template_selections_path")
    op.execute("DROP INDEX IF EXISTS idx_template_selections_attr_node")
    op.execute("DROP INDEX IF EXISTS idx_quotes_technical_requirements")
    op.execute("DROP INDEX IF EXISTS idx_quotes_status_valid")
    op.execute("DROP INDEX IF EXISTS idx_quotes_customer_status")
    op.execute("DROP INDEX IF EXISTS idx_quotes_config_status")
    op.execute("DROP INDEX IF EXISTS idx_orders_status_required")
    op.execute("DROP INDEX IF EXISTS idx_orders_status_date")
    op.execute("DROP INDEX IF EXISTS idx_orders_quote_status")
    op.execute("DROP INDEX IF EXISTS idx_orders_installation_address")
    op.execute("DROP INDEX IF EXISTS idx_order_items_order_status")
    op.execute("DROP INDEX IF EXISTS idx_order_items_config_status")
    op.execute("DROP INDEX IF EXISTS idx_configurations_technical_data")
    op.execute("DROP INDEX IF EXISTS idx_configurations_mfg_type_status")
    op.execute("DROP INDEX IF EXISTS idx_templates_public_only")
    op.execute("DROP INDEX IF EXISTS idx_templates_public_active")
    op.execute("DROP INDEX IF EXISTS idx_templates_mfg_type_template_type")
    op.execute("DROP INDEX IF EXISTS idx_templates_active_only")
    op.execute("DROP INDEX IF EXISTS idx_config_selections_path")
    op.execute("DROP INDEX IF EXISTS idx_config_selections_json")
    op.execute("DROP INDEX IF EXISTS idx_config_selections_config")
    op.execute("DROP INDEX IF EXISTS idx_config_selections_attr")
    op.execute("DROP INDEX IF EXISTS idx_attribute_nodes_technical_property")
    op.execute("DROP INDEX IF EXISTS idx_attribute_nodes_mfg_type_node_type")
    # ### end Alembic commands ###
