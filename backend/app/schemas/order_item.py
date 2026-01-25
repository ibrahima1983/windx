"""OrderItem Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for OrderItem data validation,
serialization, and API request/response handling.

Public Classes:
    OrderItemBase: Base schema with common attributes
    OrderItemCreate: Schema for creating order items
    OrderItemUpdate: Schema for updating order items (partial)
    OrderItem: Schema for API responses

Features:
    - Composed schemas (not monolithic)
    - Semantic types (PositiveInt, Decimal validation)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
    - Quantity validation (must be positive)
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

__all__ = [
    "OrderItemBase",
    "OrderItemCreate",
    "OrderItemUpdate",
    "OrderItem",
]


class OrderItemBase(BaseModel):
    """Base order item schema with common attributes.

    Attributes:
        quantity: Item quantity (must be > 0)
        unit_price: Price per unit
        total_price: Total line item price
    """

    quantity: Annotated[
        PositiveInt,
        Field(
            description="Item quantity (must be > 0)",
            examples=[1, 3, 5, 10],
        ),
    ]
    unit_price: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Price per unit",
            examples=[525.00, 1250.50, 988.50],
        ),
    ]
    total_price: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Total line item price (quantity * unit_price)",
            examples=[525.00, 3751.50, 9885.00],
        ),
    ]

    @field_validator("total_price")
    @classmethod
    def validate_total_price(cls, v: Decimal, info) -> Decimal:
        """Validate that total_price equals quantity * unit_price."""
        if "quantity" in info.data and "unit_price" in info.data:
            expected = Decimal(str(info.data["quantity"])) * info.data["unit_price"]
            # Allow small rounding differences (within 0.01)
            if abs(v - expected) > Decimal("0.01"):
                raise ValueError(f"total_price ({v}) must equal quantity * unit_price ({expected})")
        return v


class OrderItemCreate(OrderItemBase):
    """Schema for creating a new order item.

    Attributes:
        order_id: Order ID
        configuration_id: Configuration ID
    """

    order_id: Annotated[
        PositiveInt,
        Field(
            description="Order ID",
            examples=[301, 456],
        ),
    ]
    configuration_id: Annotated[
        PositiveInt,
        Field(
            description="Configuration ID",
            examples=[123, 456, 789],
        ),
    ]


class OrderItemUpdate(BaseModel):
    """Schema for updating order item information.

    All fields are optional for partial updates.

    Attributes:
        quantity: Optional new quantity
        unit_price: Optional new unit price
        total_price: Optional new total price
        production_status: Optional status update
    """

    quantity: Annotated[
        PositiveInt | None,
        Field(
            default=None,
            description="Item quantity (must be > 0)",
        ),
    ] = None
    unit_price: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Price per unit",
        ),
    ] = None
    total_price: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Total line item price",
        ),
    ] = None
    production_status: Annotated[
        str | None,
        Field(
            default=None,
            description="Production status: pending, in_production, completed",
        ),
    ] = None

    @field_validator("production_status")
    @classmethod
    def validate_production_status(cls, v: str | None) -> str | None:
        """Validate production_status is one of the allowed values."""
        if v is None:
            return v
        allowed = {"pending", "in_production", "completed"}
        if v not in allowed:
            raise ValueError(f"production_status must be one of {allowed}, got '{v}'")
        return v

    @field_validator("total_price")
    @classmethod
    def validate_total_price(cls, v: Decimal | None, info) -> Decimal | None:
        """Validate that total_price equals quantity * unit_price if all present."""
        if v is not None and "quantity" in info.data and "unit_price" in info.data:
            quantity = info.data["quantity"]
            unit_price = info.data["unit_price"]
            if quantity is not None and unit_price is not None:
                expected = Decimal(str(quantity)) * unit_price
                # Allow small rounding differences (within 0.01)
                if abs(v - expected) > Decimal("0.01"):
                    raise ValueError(
                        f"total_price ({v}) must equal quantity * unit_price ({expected})"
                    )
        return v


class OrderItem(OrderItemBase):
    """Schema for order item API response.

    Attributes:
        id: Order item ID
        order_id: Order ID
        configuration_id: Configuration ID
        production_status: Production status
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Order item ID"),
    ]
    order_id: Annotated[
        PositiveInt,
        Field(description="Order ID"),
    ]
    configuration_id: Annotated[
        PositiveInt,
        Field(description="Configuration ID"),
    ]
    production_status: Annotated[
        str,
        Field(description="Production status: pending, in_production, completed"),
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
