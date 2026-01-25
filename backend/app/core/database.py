"""Database module - DEPRECATED.

This module is deprecated. Use app.database instead.

For backward compatibility, this module re-exports from app.database.
All new code should import directly from app.database.

Deprecated:
    Use `from app.database import Base, get_db, init_db, close_db` instead.
"""

import warnings

# Re-export from new location for backward compatibility
from app.database import Base, close_db, get_db, init_db  # noqa: F401

__all__ = ["Base", "get_db", "init_db", "close_db"]

# Warn about deprecation
warnings.warn(
    "app.core.database is deprecated. Use app.database instead.",
    DeprecationWarning,
    stacklevel=2,
)
