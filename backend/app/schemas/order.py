"""Order Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for Order data validation,
serialization, and API request/response handling.

Public Classes:
    OrderBase: Base schema with common attributes
    OrderCreate: Schema for creating orders
    OrderUpdate: Schema for updating orders (partial)
    Order: Schema for API responses

Features:
    - Composed schemas (not monolithic)
    - Semantic types (PositiveInt, date validation)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
    - Date validation for required_date
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

__all__ = [
    "OrderBase",
    "OrderCreate",
    "OrderCreateRequest",
    "OrderUpdate",
    "Order",
    "OrderWithItems",
]


class OrderBase(BaseModel):
    """Base order schema with common attributes.

    Attributes:
        order_date: When order was placed
        required_date: Requested delivery date
        special_instructions: Customer requests
        installation_address: Delivery location
    """

    order_date: Annotated[
        date,
        Field(
            description="When order was placed",
            examples=["2025-01-25", "2025-02-15"],
        ),
    ]
    required_date: Annotated[
        date | None,
        Field(
            default=None,
            description="Requested delivery date",
            examples=["2025-02-15", "2025-03-01"],
        ),
    ] = None
    special_instructions: Annotated[
        str | None,
        Field(
            default=None,
            description="Customer requests and special instructions",
            examples=[
                "Call before delivery",
                "Deliver to back entrance",
                "Installation required on weekends only",
            ],
        ),
    ] = None
    installation_address: Annotated[
        dict | None,
        Field(
            default=None,
            description="Delivery location (flexible format)",
            examples=[
                {
                    "street": "123 Main St",
                    "city": "Springfield",
                    "state": "IL",
                    "zip": "62701",
                    "country": "USA",
                },
                {
                    "line1": "456 Oak Avenue",
                    "line2": "Apt 3B",
                    "city": "Portland",
                    "postal_code": "97201",
                },
            ],
        ),
    ] = None

    @field_validator("required_date")
    @classmethod
    def validate_required_date(cls, v: date | None, info) -> date | None:
        """Validate that required_date is not before order_date."""
        if v is not None and "order_date" in info.data:
            order_date = info.data["order_date"]
            if v < order_date:
                raise ValueError("required_date cannot be before order_date")
        return v


class OrderCreateRequest(BaseModel):
    """Schema for API request to create an order from a quote.

    Attributes:
        quote_id: Quote ID to create order from
        order_date: When order was placed (defaults to today)
        required_date: Requested delivery date
        special_instructions: Customer requests
        installation_address: Delivery location
    """

    quote_id: Annotated[
        PositiveInt,
        Field(
            description="Quote ID to create order from",
            examples=[501, 789],
        ),
    ]
    order_date: Annotated[
        date | None,
        Field(
            default=None,
            description="When order was placed (defaults to today)",
            examples=["2025-01-25", "2025-02-15"],
        ),
    ] = None
    required_date: Annotated[
        date | None,
        Field(
            default=None,
            description="Requested delivery date",
            examples=["2025-02-15", "2025-03-01"],
        ),
    ] = None
    special_instructions: Annotated[
        str | None,
        Field(
            default=None,
            description="Customer requests and special instructions",
            examples=[
                "Call before delivery",
                "Deliver to back entrance",
                "Installation required on weekends only",
            ],
        ),
    ] = None
    installation_address: Annotated[
        dict | None,
        Field(
            default=None,
            description="Delivery location (flexible format)",
            examples=[
                {
                    "street": "123 Main St",
                    "city": "Springfield",
                    "state": "IL",
                    "zip": "62701",
                    "country": "USA",
                },
                {
                    "line1": "456 Oak Avenue",
                    "line2": "Apt 3B",
                    "city": "Portland",
                    "postal_code": "97201",
                },
            ],
        ),
    ] = None

    @field_validator("required_date")
    @classmethod
    def validate_required_date(cls, v: date | None, info) -> date | None:
        """Validate that required_date is not before order_date."""
        if v is not None and "order_date" in info.data:
            order_date = info.data["order_date"]
            if order_date is not None and v < order_date:
                raise ValueError("required_date cannot be before order_date")
        return v


class OrderCreate(OrderBase):
    """Schema for creating a new order.

    Attributes:
        quote_id: Quote ID
        order_number: Unique order identifier
    """

    quote_id: Annotated[
        PositiveInt,
        Field(
            description="Quote ID",
            examples=[501, 789],
        ),
    ]
    order_number: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Unique order identifier",
            examples=["O-2025-001", "ORD-20250125-001", "ORDER-2025-JAN-001"],
        ),
    ]


class OrderUpdate(BaseModel):
    """Schema for updating order information.

    All fields are optional for partial updates.

    Attributes:
        order_date: Optional new order date
        required_date: Optional new required date
        status: Optional status update
        special_instructions: Optional new instructions
        installation_address: Optional new address
    """

    order_date: Annotated[
        date | None,
        Field(
            default=None,
            description="When order was placed",
        ),
    ] = None
    required_date: Annotated[
        date | None,
        Field(
            default=None,
            description="Requested delivery date",
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(
            default=None,
            description="Current state: confirmed, production, shipped, installed",
        ),
    ] = None
    special_instructions: Annotated[
        str | None,
        Field(
            default=None,
            description="Customer requests and special instructions",
        ),
    ] = None
    installation_address: Annotated[
        dict | None,
        Field(
            default=None,
            description="Delivery location",
        ),
    ] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of the allowed values."""
        if v is None:
            return v
        allowed = {"confirmed", "production", "shipped", "installed"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v

    @field_validator("required_date")
    @classmethod
    def validate_required_date(cls, v: date | None, info) -> date | None:
        """Validate that required_date is not before order_date."""
        if v is not None and "order_date" in info.data:
            order_date = info.data["order_date"]
            if order_date is not None and v < order_date:
                raise ValueError("required_date cannot be before order_date")
        return v


class Order(OrderBase):
    """Schema for order API response.

    Attributes:
        id: Order ID
        quote_id: Quote ID
        order_number: Unique order identifier
        status: Current state
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Order ID"),
    ]
    quote_id: Annotated[
        PositiveInt,
        Field(description="Quote ID"),
    ]
    order_number: Annotated[
        str,
        Field(description="Unique order identifier"),
    ]
    status: Annotated[
        str,
        Field(description="Current state: confirmed, production, shipped, installed"),
    ]
    created_at: Annotated[
        datetime,
        Field(description="Record creation timestamp"),
    ]
    updated_at: Annotated[
        datetime,
        Field(description="Last update timestamp"),
    ]

    model_config = ConfigDict(from_attributes=True)


class OrderWithItems(Order):
    """Schema for order API response with items.

    Includes all order fields plus the list of order items.

    Attributes:
        items: List of order items
    """

    items: Annotated[
        list[OrderItem],
        Field(
            default_factory=list,
            description="List of order items",
        ),
    ]

    model_config = ConfigDict(from_attributes=True)


# Import OrderItem for forward reference
from app.schemas.order_item import OrderItem  # noqa: E402

# Update forward references
OrderWithItems.model_rebuild()
