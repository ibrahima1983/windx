"""Pagination configuration and utilities.

This module provides pagination functionality using fastapi-pagination.
Supports multiple pagination styles and automatic response formatting.

Public Classes:
    PaginationParams: Pagination parameters
    Page: Page-based pagination response
    LimitOffsetPage: Limit-offset pagination response

Public Functions:
    paginate: Paginate query results

Features:
    - Multiple pagination styles (page-based, limit-offset, cursor)
    - Automatic response formatting
    - SQLAlchemy integration
    - Customizable page sizes
    - Type-safe pagination
"""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi import Query
from fastapi_pagination import Page as FastAPIPaginationPage
from fastapi_pagination import Params
from fastapi_pagination.ext.sqlalchemy import apaginate as sqlalchemy_paginate
from pydantic import Field
from sqlalchemy import Select

__all__ = [
    "PaginationParams",
    "Page",
    "paginate",
    "create_pagination_params",
]

T = TypeVar("T")

# Type alias for Page response
Page = FastAPIPaginationPage


class PaginationParams(Params):
    """Pagination parameters.

    Attributes:
        page: Page number (1-indexed)
        size: Page size (number of items per page)
    """

    page: int = Field(1, ge=1, description="Page number")
    size: int = Field(50, ge=1, le=100, description="Page size")


def create_pagination_params(
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=100, description="Page size"),
) -> PaginationParams:
    """Create pagination parameters from query params.

    Args:
        page (int): Page number (1-indexed)
        size (int): Page size (max 100)

    Returns:
        PaginationParams: Pagination parameters

    Example:
        @router.get("/users")
        async def list_users(
            params: Annotated[PaginationParams, Depends(create_pagination_params)],
        ):
            pass
    """
    return PaginationParams(page=page, size=size)


async def paginate(db: Any, query: Select, params: PaginationParams | None = None) -> Page[T]:
    """Paginate SQLAlchemy query.

    Args:
        db: Database session
        query (Select): SQLAlchemy select query
        params (PaginationParams | None): Pagination parameters

    Returns:
        Page[T]: Paginated response with items and metadata

    Example:
        query = select(User).where(User.is_active == True)
        result = await paginate(db, query, params)

        # Response:
        # {
        #   "items": [...],
        #   "total": 100,
        #   "page": 1,
        #   "size": 50,
        #   "pages": 2
        # }
    """
    if params is None:
        params = PaginationParams()

    return await sqlalchemy_paginate(db, query, params=params)
