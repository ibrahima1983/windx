"""Customer Pydantic schemas for validation and serialization.

This module defines composed Pydantic schemas for Customer data validation,
serialization, and API request/response handling.

Public Classes:
    CustomerBase: Base schema with common attributes
    CustomerCreate: Schema for creating customers
    CustomerUpdate: Schema for updating customers (partial)
    Customer: Schema for API responses

Features:
    - Composed schemas (not monolithic)
    - Semantic types (EmailStr, PositiveInt)
    - Field validation with constraints
    - Type-safe with Annotated types
    - Automatic ORM conversion support
    - Flexible address structure
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PositiveInt

__all__ = [
    "CustomerBase",
    "CustomerCreate",
    "CustomerUpdate",
    "Customer",
]


class CustomerBase(BaseModel):
    """Base customer schema with common attributes.

    Attributes:
        company_name: Business name (optional for individuals)
        contact_person: Primary contact name
        email: Unique contact email
        phone: Contact phone number
        address: Flexible address storage (dict)
        customer_type: Type classification
        tax_id: Tax identification number
        payment_terms: Payment agreement terms
        notes: Internal notes
    """

    company_name: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Business name (optional for individuals)",
            examples=["ABC Construction", "Smith Residence"],
        ),
    ] = None
    contact_person: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Primary contact name",
            examples=["John Smith", "Jane Doe"],
        ),
    ] = None
    email: Annotated[
        EmailStr | None,
        Field(
            default=None,
            description="Unique contact email",
            examples=["john.smith@example.com"],
        ),
    ] = None
    phone: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Contact phone number",
            examples=["+1-555-123-4567", "(555) 123-4567"],
        ),
    ] = None
    address: Annotated[
        dict | None,
        Field(
            default=None,
            description="Flexible address storage",
            examples=[
                {
                    "street": "123 Main St",
                    "city": "Springfield",
                    "state": "IL",
                    "postal_code": "62701",
                    "country": "USA",
                }
            ],
        ),
    ] = None
    customer_type: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Type: residential, commercial, contractor",
            examples=["residential", "commercial", "contractor"],
        ),
    ] = None
    tax_id: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Tax identification number",
            examples=["12-3456789", "EIN: 12-3456789"],
        ),
    ] = None
    payment_terms: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Payment agreement terms",
            examples=["Net 30", "Net 60", "COD", "Credit Card"],
        ),
    ] = None
    notes: Annotated[
        str | None,
        Field(
            default=None,
            description="Internal notes",
            examples=["Preferred customer", "Requires special handling"],
        ),
    ] = None


class CustomerCreate(CustomerBase):
    """Schema for creating a new customer.

    Inherits all fields from CustomerBase.
    All fields are optional to support various customer types.
    """

    pass


class CustomerUpdate(BaseModel):
    """Schema for updating customer information.

    All fields are optional for partial updates.

    Attributes:
        company_name: Optional new business name
        contact_person: Optional new contact name
        email: Optional new email
        phone: Optional new phone number
        address: Optional new address
        customer_type: Optional new customer type
        tax_id: Optional new tax ID
        payment_terms: Optional new payment terms
        is_active: Optional active status update
        notes: Optional new notes
    """

    company_name: Annotated[
        str | None,
        Field(
            default=None,
            max_length=200,
            description="Business name",
        ),
    ] = None
    contact_person: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Primary contact name",
        ),
    ] = None
    email: Annotated[
        EmailStr | None,
        Field(
            default=None,
            description="Contact email",
        ),
    ] = None
    phone: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Contact phone number",
        ),
    ] = None
    address: Annotated[
        dict | None,
        Field(
            default=None,
            description="Address information",
        ),
    ] = None
    customer_type: Annotated[
        str | None,
        Field(
            default=None,
            max_length=50,
            description="Customer type",
        ),
    ] = None
    tax_id: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Tax identification number",
        ),
    ] = None
    payment_terms: Annotated[
        str | None,
        Field(
            default=None,
            max_length=100,
            description="Payment terms",
        ),
    ] = None
    is_active: Annotated[
        bool | None,
        Field(
            default=None,
            description="Active status",
        ),
    ] = None
    notes: Annotated[
        str | None,
        Field(
            default=None,
            description="Internal notes",
        ),
    ] = None


class Customer(CustomerBase):
    """Schema for customer API response.

    Attributes:
        id: Customer ID (positive integer)
        is_active: Active status
        created_at: Record creation timestamp
        updated_at: Last update timestamp
    """

    id: Annotated[
        PositiveInt,
        Field(description="Customer ID"),
    ]
    is_active: Annotated[
        bool,
        Field(description="Active status"),
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
