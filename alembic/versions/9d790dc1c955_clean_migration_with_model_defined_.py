"""Clean migration with model-defined indexes

Revision ID: 9d790dc1c955
Revises: 057e539f7375
Create Date: 2025-12-19 18:20:57.771144

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9d790dc1c955"
down_revision: Union[str, None] = "057e539f7375"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade database schema."""

    # This migration ensures that all tables and indexes match the SQLAlchemy models
    # The models already define all necessary performance indexes in their __table_args__

    # Enable LTREE extension (required for hierarchical data)
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")

    # Add role column to users table if it doesn't exist
    op.execute("""
        DO $$ 
        BEGIN 
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                          WHERE table_name = 'users' AND column_name = 'role') THEN
                ALTER TABLE users ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'customer';
            END IF;
        END $$;
    """)

    # Create all tables and indexes as defined in SQLAlchemy models
    # This approach ensures that the database matches the model definitions exactly
    from app.database.base import Base

    # Get the current connection and create all tables/indexes
    connection = op.get_bind()
    Base.metadata.create_all(bind=connection, checkfirst=True)

    print("✅ All tables and model-defined indexes created")


def downgrade() -> None:
    """Downgrade database schema."""

    # Drop all tables (this will also drop their indexes)
    from app.database.base import Base

    connection = op.get_bind()
    Base.metadata.drop_all(bind=connection)

    # Remove role column from users if it exists
    op.execute("""
        DO $$ 
        BEGIN 
            IF EXISTS (SELECT 1 FROM information_schema.columns 
                      WHERE table_name = 'users' AND column_name = 'role') THEN
                ALTER TABLE users DROP COLUMN role;
            END IF;
        END $$;
    """)

    print("✅ All tables and indexes dropped")
