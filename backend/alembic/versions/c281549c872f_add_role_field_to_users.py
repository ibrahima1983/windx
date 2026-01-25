"""add_role_field_to_users

Revision ID: c281549c872f
Revises: 6a07301cffee
Create Date: 2025-12-16 23:50:13.439665

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c281549c872f"
down_revision: str | None = "6a07301cffee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Add role field to users table
    op.add_column(
        "users", sa.Column("role", sa.String(50), nullable=False, server_default="customer")
    )

    # Create index for role field
    op.create_index("ix_users_role", "users", ["role"])

    # Update existing superusers to have superadmin role
    op.execute("UPDATE users SET role = 'superadmin' WHERE is_superuser = true")

    # Update other users based on their current status
    # For now, all non-superusers get 'customer' role (already set by default)


def downgrade() -> None:
    """Downgrade database schema."""
    # Drop index
    op.drop_index("ix_users_role", "users")

    # Drop role column
    op.drop_column("users", "role")
