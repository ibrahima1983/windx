"""Base model class for all database models.

This module provides the declarative base class that all ORM models
should inherit from.

Public Classes:
    Base: Declarative base for all ORM models

Features:
    - SQLAlchemy 2.0 declarative base
    - Common model functionality
    - Type hints support
"""

from sqlalchemy.orm import DeclarativeBase

__all__ = ["Base"]


class Base(DeclarativeBase):
    """Base class for all database models.

    All SQLAlchemy ORM models should inherit from this class.
    Provides common functionality and configuration for all models.

    Example:
        ```python
        from app.database.base import Base
        from sqlalchemy.orm import Mapped, mapped_column

        class User(Base):
            __tablename__ = "users"

            id: Mapped[int] = mapped_column(primary_key=True)
            email: Mapped[str] = mapped_column(unique=True)
        ```
    """

    pass
