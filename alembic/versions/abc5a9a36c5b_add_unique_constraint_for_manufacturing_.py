"""Add unique constraint for manufacturing_type_id, page_type, name in attribute_nodes

Revision ID: abc5a9a36c5b
Revises: ba0a6a525f3f
Create Date: 2025-12-24 22:42:10.854103

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "abc5a9a36c5b"
down_revision: Union[str, None] = "ba0a6a525f3f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add unique constraint to prevent duplicate attribute names within same manufacturing type and page type
    op.create_unique_constraint(
        "uq_attribute_nodes_mfg_page_name",
        "attribute_nodes",
        ["manufacturing_type_id", "page_type", "name"],
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Remove the unique constraint
    op.drop_constraint("uq_attribute_nodes_mfg_page_name", "attribute_nodes", type_="unique")
