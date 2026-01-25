"""ManufacturingType Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for ManufacturingType data validation,
serialization, and API request/response handling.

Public Classes:
    ManufacturingTypeBase: Base schema with common attributes
    ManufacturingTypeCreate: Schema for creating manufacturing types
    ManufacturingTypeUpdate: Schema for updating manufacturing types (partial)
    ManufacturingType: Schema for API responses

Features:
    - Composed schemas (not monolithic)
    - Semantic types (PositiveInt, Decimal validation)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

__all__ = [
    "ManufacturingTypeBase",
    "ManufacturingTypeCreate",
    "ManufacturingTypeUpdate",
    "ManufacturingType",
]


class ManufacturingTypeBase(BaseModel):
    """Base manufacturing type schema with common attributes.

    Attributes:
        name: Unique product category name
        description: Detailed description of the product type
        base_category: High-level grouping (window, door, furniture)
        image_url: URL to product category image
        base_price: Starting price for this product type
        base_weight: Base weight in kg
    """

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Unique product category name",
            examples=["Casement Window", "Entry Door", "Dining Table"],
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Detailed description of the product type",
            examples=["Energy-efficient casement windows with multiple configuration options"],
        ),
    ] = None
    base_category: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="High-level grouping",
            examples=["window", "door", "furniture"],
        ),
    ] = None
    image_url: Annotated[
        str | None,
        Field(
            default=None,
            max_length=255,
            description="URL to product category image",
            examples=["/images/casement-window.jpg"],
        ),
    ] = None
    base_price: Annotated[
        Decimal,
        Field(
            default=Decimal("0.00"),
            ge=0,
            decimal_places=2,
            description="Starting price for this product type",
            examples=[200.00, 500.00, 1000.00],
        ),
    ] = Decimal("0.00")
    base_weight: Annotated[
        Decimal,
        Field(
            default=Decimal("0.00"),
            ge=0,
            decimal_places=2,
            description="Base weight in kg",
            examples=[15.00, 25.50, 50.00],
        ),
    ] = Decimal("0.00")


class ManufacturingTypeCreate(ManufacturingTypeBase):
    """Schema for creating a new manufacturing type.

    Inherits all fields from ManufacturingTypeBase.
    """

    pass


class ManufacturingTypeUpdate(BaseModel):
    """Schema for updating manufacturing type information.

    All fields are optional for partial updates.

    Attributes:
        name: Optional new product category name
        description: Optional new description
        base_category: Optional new base category
        image_url: Optional new image URL
        base_price: Optional new base price
        base_weight: Optional new base weight
        is_active: Optional active status update
    """

    name: Annotated[
        str | None,
        Field(
            default=None,
            min_length=1,
            max_length=100,
            description="Unique product category name",
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Detailed description of the product type",
        ),
    ] = None
    base_category: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="High-level grouping",
        ),
    ] = None
    image_url: Annotated[
        str | None,
        Field(
            default=None,
            max_length=255,
            description="URL to product category image",
        ),
    ] = None
    base_price: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Starting price for this product type",
        ),
    ] = None
    base_weight: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Base weight in kg",
        ),
    ] = None
    is_active: Annotated[
        bool | None,
        Field(
            default=None,
            description="Whether this product type is available",
        ),
    ] = None


class ManufacturingType(ManufacturingTypeBase):
    """Schema for manufacturing type API response.

    Attributes:
        id: Manufacturing type ID (positive integer)
        is_active: Whether this product type is available
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Manufacturing type ID"),
    ]
    is_active: Annotated[
        bool,
        Field(description="Whether this product type is available"),
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
