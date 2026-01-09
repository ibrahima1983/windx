"""Quote management endpoints.

This module provides REST API endpoints for managing quotes.

Public Variables:
    router: FastAPI router for quote endpoints

Features:
    - List user's quotes with pagination
    - Get quote by ID
    - Generate quote from configuration
    - Authorization checks (users see only their own)
    - OpenAPI documentation with examples
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentUser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.quote import Quote
from app.schemas.quote import Quote as QuoteSchema
from app.schemas.quote import QuoteCreateRequest
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Quotes"],
    responses=get_common_responses(401, 500),
)


@router.get(
    "/",
    response_model=Page[QuoteSchema],
    summary="List Quotes",
    description="List user's quotes with pagination. Superusers can see all quotes.",
    response_description="Paginated list of quotes",
    operation_id="listQuotes",
    responses={
        200: {
            "description": "Successfully retrieved quotes",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "configuration_id": 123,
                                "customer_id": 42,
                                "quote_number": "Q-2024-001",
                                "subtotal": "525.00",
                                "tax_rate": "8.50",
                                "tax_amount": "44.63",
                                "discount_amount": "0.00",
                                "total_amount": "569.63",
                                "valid_until": "2024-02-15",
                                "status": "sent",
                                "created_at": "2024-01-01T00:00:00Z",
                                "updated_at": "2024-01-01T00:00:00Z",
                            }
                        ],
                        "total": 5,
                        "page": 1,
                        "size": 50,
                        "pages": 1,
                    }
                }
            },
        },
        **get_common_responses(401, 500),
    },
)
async def list_quotes(
    current_user: CurrentUser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    status_filter: Annotated[
        str | None,
        Query(alias="status", description="Filter by status (draft, sent, accepted, expired)"),
    ] = None,
) -> Page[Quote]:
    """List user's quotes with filtering.

    Regular users see only their own quotes.
    Superusers can see all quotes.

    Args:
        current_user (User): Current authenticated user
        params (PaginationParams): Pagination parameters
        db (AsyncSession): Database session
        status_filter (str | None): Filter by status

    Returns:
        Page[Quote]: Paginated list of quotes

    Example:
        GET /api/v1/quotes?status=sent
    """
    from app.core.pagination import paginate
    from app.services.quote import QuoteService
    from app.services.rbac import RBACService
    from sqlalchemy import select

    quote_service = QuoteService(db)
    rbac_service = RBACService(db)

    # Build base query
    query = select(Quote)

    # Apply RBAC filtering
    if current_user.role != "superadmin":
        accessible_customers = await rbac_service.get_accessible_customers(current_user)

        if not accessible_customers:
            # User has no accessible customers - return empty result
            query = query.where(False)
        else:
            # Filter by accessible customers
            query = query.where(Quote.customer_id.in_(accessible_customers))

    # Apply status filter
    if status_filter:
        query = query.where(Quote.status == status_filter)

    # Order by most recent first
    query = query.order_by(Quote.created_at.desc())

    return await paginate(db, query, params)


@router.get(
    "/{quote_id}",
    response_model=QuoteSchema,
    summary="Get Quote",
    description="Get a single quote by ID",
    response_description="Quote details",
    operation_id="getQuote",
    responses={
        200: {
            "description": "Successfully retrieved quote",
        },
        403: {
            "description": "Not authorized to access this quote",
        },
        404: {
            "description": "Quote not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_quote(
    quote_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> Quote:
    """Get quote by ID.

    Users can only access their own quotes unless they are superusers.

    Args:
        quote_id (PositiveInt): Quote ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Quote: Quote details

    Raises:
        NotFoundException: If quote not found
        AuthorizationException: If user lacks permission
    """
    from app.services.quote import QuoteService

    quote_service = QuoteService(db)
    return await quote_service.get_quote_with_auth(quote_id, current_user)


@router.post(
    "/",
    response_model=QuoteSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Quote",
    description="Generate a quote from a configuration with automatic price calculation",
    response_description="Created quote with snapshot",
    operation_id="createQuote",
    responses={
        201: {
            "description": "Quote successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "configuration_id": 123,
                        "customer_id": 42,
                        "quote_number": "Q-20250127-001",
                        "subtotal": "525.00",
                        "tax_rate": "8.50",
                        "tax_amount": "44.63",
                        "discount_amount": "0.00",
                        "total_amount": "569.63",
                        "technical_requirements": None,
                        "valid_until": "2025-02-26",
                        "status": "draft",
                        "created_at": "2025-01-27T00:00:00Z",
                        "updated_at": "2025-01-27T00:00:00Z",
                    }
                }
            },
        },
        403: {
            "description": "Not authorized to create quote for this configuration",
        },
        404: {
            "description": "Configuration not found",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def create_quote(
    quote_in: QuoteCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> Quote:
    """Generate a quote from a configuration.

    Creates a quote with automatic price calculation and configuration snapshot
    to preserve pricing. The subtotal is taken from the configuration's total_price,
    and tax/discount are applied to calculate the final total.

    Users can only create quotes for their own configurations unless they are superusers.

    Args:
        quote_in (QuoteCreateRequest): Quote creation data
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Quote: Created quote with calculated pricing

    Raises:
        NotFoundException: If configuration not found
        AuthorizationException: If user lacks permission
        ValidationException: If tax rate or discount amount is invalid

    Example:
        POST /api/v1/quotes
        {
            "configuration_id": 123,
            "tax_rate": "8.50",
            "discount_amount": "0.00"
        }
    """
    from app.services.quote import QuoteService

    quote_service = QuoteService(db)
    return await quote_service.create_quote_with_auth(quote_in, current_user)
