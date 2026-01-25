"""Database package for database configuration and utilities.

This package contains database configuration, connection management,
and database utilities.

Public Modules:
    connection: Database connection and session management
    base: Base model class
    utils: Database utilities
    types: Custom database types (LTREE, etc.)

Features:
    - Database connection management
    - Session lifecycle management
    - Base model configuration
    - Database utilities
    - PostgreSQL LTREE support for hierarchical data
"""

from app.database.base import Base
from app.database.connection import close_db, get_db, init_db
from app.database.types import LTREE, LtreeType
from app.database.utils import enable_ltree_extension

__all__ = [
    "Base",
    "get_db",
    "init_db",
    "close_db",
    "LTREE",
    "LtreeType",
    "enable_ltree_extension",
]
