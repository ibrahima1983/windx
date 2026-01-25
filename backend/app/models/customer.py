"""Customer model for customer management.

This module defines the Customer ORM model for managing customer information
using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    Customer: Customer management model

Features:
    - JSONB address field for flexible international formats
    - Customer type classification (residential, commercial, contractor)
    - Tax ID and payment terms tracking
    - Active/inactive status
    - Automatic timestamp management
    - Relationships with configurations and quotes
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import TIMESTAMP, Index, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.configuration import Configuration
    from app.models.quote import Quote

__all__ = ["Customer"]


class Customer(Base):
    """Customer model for customer management.

    Represents customers who create configurations and place orders.
    Supports both individual and business customers with flexible
    address storage for international formats.

    Attributes:
        id: Primary key
        company_name: Business name (optional for individuals)
        contact_person: Primary contact name
        email: Unique contact email
        phone: Contact phone number
        address: Flexible address storage (JSONB)
        customer_type: Type classification (residential, commercial, contractor)
        tax_id: Tax identification number
        payment_terms: Payment agreement terms
        is_active: Active status
        notes: Internal notes
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        configurations: Related customer configurations
        quotes: Related customer quotes
    """

    __tablename__ = "customers"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Basic information
    company_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
        default=None,
        index=True,
        doc="Business name (optional for individuals)",
    )
    contact_person: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        doc="Primary contact name",
    )
    email: Mapped[str | None] = mapped_column(
        String(255),
        unique=True,
        nullable=True,
        index=True,
        doc="Unique contact email",
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        doc="Contact phone number",
    )

    # Address (JSONB for flexible international formats)
    address: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="Flexible address storage (JSONB)",
    )

    # Customer classification
    customer_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default=None,
        index=True,
        doc="Type: residential, commercial, contractor",
    )

    # Business information
    tax_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        doc="Tax identification number",
    )
    payment_terms: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        default=None,
        doc="Payment agreement terms",
    )

    # Status and notes
    is_active: Mapped[bool] = mapped_column(
        default=True,
        nullable=False,
        index=True,
        doc="Active status",
    )
    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Internal notes",
    )

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
        doc="Record creation timestamp (UTC)",
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        doc="Last update timestamp (UTC)",
    )

    # Relationships
    configurations: Mapped[list[Configuration]] = relationship(
        "Configuration",
        back_populates="customer",
        doc="Related customer configurations",
    )
    quotes: Mapped[list[Quote]] = relationship(
        "Quote",
        back_populates="customer",
        doc="Related customer quotes",
    )

    # Indexes
    __table_args__ = (
        # Composite index for filtering by customer type and active status
        Index(
            "idx_customers_type_active",
            "customer_type",
            "is_active",
        ),
        # GIN index on address for JSONB queries
        Index(
            "idx_customers_address",
            "address",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Customer.

        Returns:
            str: Customer representation with ID and name/email
        """
        identifier = self.company_name or self.email or f"ID:{self.id}"
        return f"<Customer(id={self.id}, identifier='{identifier}')>"
