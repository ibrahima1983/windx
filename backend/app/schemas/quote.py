"""Quote Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for Quote data validation,
serialization, and API request/response handling.

Public Classes:
    QuoteBase: Base schema with common attributes
    QuoteCreate: Schema for creating quotes
    QuoteUpdate: Schema for updating quotes (partial)
    Quote: Schema for API responses

Features:
    - Composed schemas (not monolithic)
    - Semantic types (PositiveInt, Decimal validation)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
    - Date validation for quote validity
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator

__all__ = [
    "QuoteBase",
    "QuoteCreate",
    "QuoteCreateRequest",
    "QuoteUpdate",
    "Quote",
]


class QuoteBase(BaseModel):
    """Base quote schema with common attributes.

    Attributes:
        subtotal: Price before tax and discounts
        tax_rate: Applicable tax rate percentage
        tax_amount: Calculated tax amount
        discount_amount: Applied discounts
        total_amount: Final amount
        technical_requirements: Customer-specific needs
        valid_until: Quote expiration date
    """

    subtotal: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Price before tax and discounts",
            examples=[525.00, 1250.50],
        ),
    ]
    tax_rate: Annotated[
        Decimal,
        Field(
            ge=0,
            le=100,
            decimal_places=2,
            description="Applicable tax rate percentage",
            examples=[8.50, 10.00, 0.00],
        ),
    ]
    tax_amount: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Calculated tax amount",
            examples=[44.63, 125.05],
        ),
    ]
    discount_amount: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Applied discounts",
            examples=[0.00, 25.00, 50.00],
        ),
    ] = Decimal("0.00")
    total_amount: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Final amount (subtotal + tax - discount)",
            examples=[544.63, 1350.55],
        ),
    ]
    technical_requirements: Annotated[
        dict | None,
        Field(
            default=None,
            description="Customer-specific technical needs",
            examples=[{"installation": "professional", "delivery": "white_glove"}],
        ),
    ] = None
    valid_until: Annotated[
        date | None,
        Field(
            default=None,
            description="Quote expiration date",
            examples=["2025-02-24", "2025-03-15"],
        ),
    ] = None

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: date | None) -> date | None:
        """Validate that valid_until is not in the past."""
        if v is not None and v < date.today():
            raise ValueError("valid_until cannot be in the past")
        return v


class QuoteCreateRequest(BaseModel):
    """Schema for creating a new quote via API.

    This schema is used for API requests where calculated fields
    are not required from the user.

    Attributes:
        configuration_id: Configuration ID
        customer_id: Optional customer ID
        tax_rate: Tax rate percentage
        discount_amount: Discount amount to apply
        technical_requirements: Customer-specific needs
        valid_until: Quote expiration date
    """

    configuration_id: Annotated[
        PositiveInt,
        Field(
            description="Configuration ID",
            examples=[123, 456],
        ),
    ]
    customer_id: Annotated[
        PositiveInt | None,
        Field(
            default=None,
            description="Customer ID (optional, defaults to current user)",
            examples=[42, 123],
        ),
    ] = None
    tax_rate: Annotated[
        Decimal,
        Field(
            ge=0,
            le=100,
            decimal_places=2,
            description="Applicable tax rate percentage",
            examples=[8.50, 10.00, 0.00],
        ),
    ] = Decimal("0.00")
    discount_amount: Annotated[
        Decimal,
        Field(
            ge=0,
            decimal_places=2,
            description="Applied discounts",
            examples=[0.00, 25.00, 50.00],
        ),
    ] = Decimal("0.00")
    technical_requirements: Annotated[
        dict | None,
        Field(
            default=None,
            description="Customer-specific technical needs",
            examples=[{"installation": "professional", "delivery": "white_glove"}],
        ),
    ] = None
    valid_until: Annotated[
        date | None,
        Field(
            default=None,
            description="Quote expiration date (optional, defaults to 30 days from now)",
            examples=["2025-02-24", "2025-03-15"],
        ),
    ] = None

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: date | None) -> date | None:
        """Validate that valid_until is not in the past."""
        if v is not None and v < date.today():
            raise ValueError("valid_until cannot be in the past")
        return v


class QuoteCreate(QuoteBase):
    """Schema for creating a new quote (internal use).

    This schema is used internally by the service layer where
    all calculated fields are provided.

    Attributes:
        configuration_id: Configuration ID
        customer_id: Optional customer ID
        quote_number: Unique quote identifier
    """

    configuration_id: Annotated[
        PositiveInt,
        Field(
            description="Configuration ID",
            examples=[123, 456],
        ),
    ]
    customer_id: Annotated[
        PositiveInt | None,
        Field(
            default=None,
            description="Customer ID (optional)",
            examples=[42, 123],
        ),
    ] = None
    quote_number: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Unique quote identifier",
            examples=["Q-2025-001", "Q-20250125-001", "QUOTE-2025-JAN-001"],
        ),
    ]


class QuoteUpdate(BaseModel):
    """Schema for updating quote information.

    All fields are optional for partial updates.

    Attributes:
        subtotal: Optional new subtotal
        tax_rate: Optional new tax rate
        tax_amount: Optional new tax amount
        discount_amount: Optional new discount amount
        total_amount: Optional new total amount
        technical_requirements: Optional new technical requirements
        valid_until: Optional new expiration date
        status: Optional status update
    """

    subtotal: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Price before tax and discounts",
        ),
    ] = None
    tax_rate: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            le=100,
            decimal_places=2,
            description="Applicable tax rate percentage",
        ),
    ] = None
    tax_amount: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Calculated tax amount",
        ),
    ] = None
    discount_amount: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Applied discounts",
        ),
    ] = None
    total_amount: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Final amount",
        ),
    ] = None
    technical_requirements: Annotated[
        dict | None,
        Field(
            default=None,
            description="Customer-specific technical needs",
        ),
    ] = None
    valid_until: Annotated[
        date | None,
        Field(
            default=None,
            description="Quote expiration date",
        ),
    ] = None
    status: Annotated[
        str | None,
        Field(
            default=None,
            description="Current state: draft, sent, accepted, expired",
        ),
    ] = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, v: str | None) -> str | None:
        """Validate status is one of the allowed values."""
        if v is None:
            return v
        allowed = {"draft", "sent", "accepted", "expired"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}, got '{v}'")
        return v

    @field_validator("valid_until")
    @classmethod
    def validate_valid_until(cls, v: date | None) -> date | None:
        """Validate that valid_until is not in the past."""
        if v is not None and v < date.today():
            raise ValueError("valid_until cannot be in the past")
        return v


class Quote(QuoteBase):
    """Schema for quote API response.

    Attributes:
        id: Quote ID
        configuration_id: Configuration ID
        customer_id: Optional customer ID
        quote_number: Unique quote identifier
        status: Current state
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Quote ID"),
    ]
    configuration_id: Annotated[
        PositiveInt,
        Field(description="Configuration ID"),
    ]
    customer_id: Annotated[
        PositiveInt | None,
        Field(default=None, description="Customer ID (optional)"),
    ]
    quote_number: Annotated[
        str,
        Field(description="Unique quote identifier"),
    ]
    status: Annotated[
        str,
        Field(description="Current state: draft, sent, accepted, expired"),
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
