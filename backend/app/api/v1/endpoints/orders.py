"""Order management endpoints.

This module provides REST API endpoints for managing orders.

Public Variables:
    router: FastAPI router for order endpoints

Features:
    - List user's orders with pagination
    - Get order by ID with items
    - Create order from quote
    - Authorization checks (users see only their own)
    - OpenAPI documentation with examples
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from pydantic import PositiveInt

from app.api.types import CurrentUser, DBSession
from app.core.pagination import Page, PaginationParams, create_pagination_params
from app.models.order import Order
from app.schemas.order import Order as OrderSchema
from app.schemas.order import OrderCreateRequest, OrderWithItems
from app.schemas.responses import get_common_responses

__all__ = ["router"]

router = APIRouter(
    tags=["Orders"],
    responses=get_common_responses(401, 500),
)


@router.get(
    "/",
    response_model=Page[OrderSchema],
    summary="List Orders",
    description="List user's orders with pagination. Superusers can see all orders.",
    response_description="Paginated list of orders",
    operation_id="listOrders",
    responses={
        200: {
            "description": "Successfully retrieved orders",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "quote_id": 501,
                                "order_number": "O-2025-001",
                                "order_date": "2025-01-25",
                                "required_date": "2025-02-15",
                                "status": "production",
                                "special_instructions": "Call before delivery",
                                "installation_address": {
                                    "street": "123 Main St",
                                    "city": "Springfield",
                                    "state": "IL",
                                    "zip": "62701",
                                },
                                "created_at": "2025-01-25T00:00:00Z",
                                "updated_at": "2025-01-25T00:00:00Z",
                            }
                        ],
                        "total": 3,
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
async def list_orders(
    current_user: CurrentUser,
    params: Annotated[PaginationParams, Depends(create_pagination_params)],
    db: DBSession,
    status_filter: Annotated[
        str | None,
        Query(
            alias="status",
            description="Filter by status (confirmed, production, shipped, installed)",
        ),
    ] = None,
) -> Page[Order]:
    """List user's orders with filtering.

    Regular users see only their own orders (via quote ownership).
    Superusers can see all orders.

    Args:
        current_user (User): Current authenticated user
        params (PaginationParams): Pagination parameters
        db (AsyncSession): Database session
        status_filter (str | None): Filter by status

    Returns:
        Page[Order]: Paginated list of orders

    Example:
        GET /api/v1/orders?status=production
    """
    from app.core.pagination import paginate
    from app.services.order import OrderService

    order_service = OrderService(db)

    # Build filtered query with authorization
    query = order_service.get_user_orders_query(
        user=current_user,
        status=status_filter,
    )

    return await paginate(db, query, params)


@router.get(
    "/{order_id}",
    response_model=OrderWithItems,
    summary="Get Order",
    description="Get a single order by ID with all items",
    response_description="Order details with items",
    operation_id="getOrder",
    responses={
        200: {
            "description": "Successfully retrieved order",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "quote_id": 501,
                        "order_number": "O-2025-001",
                        "order_date": "2025-01-25",
                        "required_date": "2025-02-15",
                        "status": "production",
                        "special_instructions": "Call before delivery",
                        "installation_address": {
                            "street": "123 Main St",
                            "city": "Springfield",
                            "state": "IL",
                            "zip": "62701",
                        },
                        "created_at": "2025-01-25T00:00:00Z",
                        "updated_at": "2025-01-25T00:00:00Z",
                        "items": [
                            {
                                "id": 1,
                                "order_id": 1,
                                "configuration_id": 123,
                                "quantity": 3,
                                "unit_price": "525.00",
                                "total_price": "1575.00",
                                "production_status": "in_production",
                                "created_at": "2025-01-25T00:00:00Z",
                                "updated_at": "2025-01-25T00:00:00Z",
                            }
                        ],
                    }
                }
            },
        },
        403: {
            "description": "Not authorized to access this order",
        },
        404: {
            "description": "Order not found",
        },
        **get_common_responses(401, 500),
    },
)
async def get_order(
    order_id: PositiveInt,
    current_user: CurrentUser,
    db: DBSession,
) -> Order:
    """Get order by ID with items.

    Users can only access their own orders unless they are superusers.

    Args:
        order_id (PositiveInt): Order ID
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Order: Order details with items

    Raises:
        NotFoundException: If order not found
        AuthorizationException: If user lacks permission
    """
    from app.services.order import OrderService

    order_service = OrderService(db)
    return await order_service.get_order_with_items_auth(order_id, current_user)


@router.post(
    "/",
    response_model=OrderSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create Order",
    description="Create an order from an accepted quote",
    response_description="Created order",
    operation_id="createOrder",
    responses={
        201: {
            "description": "Order successfully created",
            "content": {
                "application/json": {
                    "example": {
                        "id": 1,
                        "quote_id": 501,
                        "order_number": "O-20250127-001",
                        "order_date": "2025-01-27",
                        "required_date": "2025-02-15",
                        "status": "confirmed",
                        "special_instructions": "Call before delivery",
                        "installation_address": {
                            "street": "123 Main St",
                            "city": "Springfield",
                            "state": "IL",
                            "zip": "62701",
                        },
                        "created_at": "2025-01-27T00:00:00Z",
                        "updated_at": "2025-01-27T00:00:00Z",
                    }
                }
            },
        },
        403: {
            "description": "Not authorized to create order for this quote",
        },
        404: {
            "description": "Quote not found",
        },
        422: {
            "description": "Quote not accepted or order already exists",
        },
        **get_common_responses(401, 422, 500),
    },
)
async def create_order(
    order_in: OrderCreateRequest,
    current_user: CurrentUser,
    db: DBSession,
) -> Order:
    """Create an order from an accepted quote.

    Creates an order from a quote that has been accepted. The quote must be
    in 'accepted' status and must not already have an order.

    Users can only create orders for their own quotes unless they are superusers.

    Args:
        order_in (OrderCreateRequest): Order creation data
        current_user (User): Current authenticated user
        db (AsyncSession): Database session

    Returns:
        Order: Created order

    Raises:
        NotFoundException: If quote not found
        AuthorizationException: If user lacks permission
        ValidationException: If quote is not accepted or order already exists

    Example:
        POST /api/v1/orders
        {
            "quote_id": 501,
            "required_date": "2025-02-15",
            "special_instructions": "Call before delivery"
        }
    """
    from app.services.order import OrderService

    order_service = OrderService(db)
    return await order_service.create_order_with_auth(order_in, current_user)
