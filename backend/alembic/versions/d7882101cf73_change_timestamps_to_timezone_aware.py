"""Change timestamps to timezone aware

Revision ID: d7882101cf73
Revises: 7895e0d26f10
Create Date: 2025-11-23 11:28:14.009304

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7882101cf73"
down_revision: str | None = "7895e0d26f10"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    # Change users table timestamps to timezone aware
    op.alter_column(
        "users",
        "created_at",
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(timezone=False),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "updated_at",
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(timezone=False),
        existing_nullable=False,
    )

    # Change sessions table timestamps to timezone aware
    op.alter_column(
        "sessions",
        "created_at",
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(timezone=False),
        existing_nullable=False,
    )
    op.alter_column(
        "sessions",
        "expires_at",
        type_=sa.TIMESTAMP(timezone=True),
        existing_type=sa.TIMESTAMP(timezone=False),
        existing_nullable=False,
    )


def downgrade() -> None:
    """Downgrade database schema."""
    # Revert sessions table timestamps
    op.alter_column(
        "sessions",
        "expires_at",
        type_=sa.TIMESTAMP(timezone=False),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "sessions",
        "created_at",
        type_=sa.TIMESTAMP(timezone=False),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )

    # Revert users table timestamps
    op.alter_column(
        "users",
        "updated_at",
        type_=sa.TIMESTAMP(timezone=False),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
    op.alter_column(
        "users",
        "created_at",
        type_=sa.TIMESTAMP(timezone=False),
        existing_type=sa.TIMESTAMP(timezone=True),
        existing_nullable=False,
    )
