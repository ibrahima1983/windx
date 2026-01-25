"""merge_rbac_indexes

Revision ID: 95aa64961de9
Revises: c281549c872f
Create Date: 2025-12-17 01:19:08.949089

"""

from collections.abc import Sequence

# revision identifiers, used by Alembic.
revision: str = "95aa64961de9"
down_revision: str | None = "c281549c872f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    pass


def downgrade() -> None:
    """Downgrade database schema."""
    pass
