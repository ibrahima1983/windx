"""Quote model for quotation system.

This module defines the Quote ORM model for managing price quotes
using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    Quote: Quotation system model

Features:
    - Unique quote number generation
    - Pricing breakdown (subtotal, tax, discounts)
    - Quote validity period tracking
    - Status tracking (draft, sent, accepted, expired)
    - JSONB for technical requirements
    - Relationships with configurations and customers
    - Automatic timestamp management
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.configuration import Configuration
    from app.models.customer import Customer
    from app.models.order import Order

__all__ = ["Quote"]


class Quote(Base):
    """Quote model for quotation system.

    Represents formal price proposals for configurations.
    Each quote captures pricing at a specific point in time
    with validity period and detailed breakdown.

    Attributes:
        id: Primary key
        configuration_id: Foreign key to Configuration
        customer_id: Optional foreign key to Customer
        quote_number: Unique quote identifier
        subtotal: Price before tax and discounts
        tax_rate: Applicable tax rate percentage
        tax_amount: Calculated tax amount
        discount_amount: Applied discounts
        total_amount: Final amount (subtotal + tax - discount)
        technical_requirements: Customer-specific needs (JSONB)
        valid_until: Quote expiration date
        status: Current state (draft, sent, accepted, expired)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        configuration: Related configuration
        customer: Related customer
    """

    __tablename__ = "quotes"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Foreign keys
    configuration_id: Mapped[int] = mapped_column(
        ForeignKey("configurations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Configuration ID",
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        doc="Customer ID (optional)",
    )

    # Quote identification
    quote_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique quote identifier",
    )

    # Pricing breakdown
    subtotal: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Price before tax and discounts",
    )
    tax_rate: Mapped[Decimal] = mapped_column(
        Numeric(5, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Applicable tax rate percentage",
    )
    tax_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Calculated tax amount",
    )
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        doc="Applied discounts",
    )
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
        index=True,
        doc="Final amount (subtotal + tax - discount)",
    )

    # Technical requirements (JSONB for flexibility)
    technical_requirements: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="Customer-specific technical needs (JSONB)",
    )

    # Quote validity
    valid_until: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        default=None,
        index=True,
        doc="Quote expiration date",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default="draft",
        nullable=False,
        index=True,
        doc="Current state: draft, sent, accepted, expired",
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
    configuration: Mapped[Configuration] = relationship(
        "Configuration",
        back_populates="quotes",
        doc="Related configuration",
    )
    customer: Mapped[Customer | None] = relationship(
        "Customer",
        back_populates="quotes",
        doc="Related customer",
    )
    orders: Mapped[list[Order]] = relationship(
        "Order",
        back_populates="quote",
        doc="Related orders",
    )

    # Indexes
    __table_args__ = (
        # Composite index for filtering by configuration and status
        Index(
            "idx_quotes_config_status",
            "configuration_id",
            "status",
        ),
        # Composite index for filtering by customer and status
        Index(
            "idx_quotes_customer_status",
            "customer_id",
            "status",
        ),
        # Composite index for filtering by status and validity
        Index(
            "idx_quotes_status_valid",
            "status",
            "valid_until",
        ),
        # GIN index on technical_requirements for JSONB queries
        Index(
            "idx_quotes_technical_requirements",
            "technical_requirements",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Quote.

        Returns:
            str: Quote representation with ID, number, and total
        """
        return (
            f"<Quote(id={self.id}, quote_number='{self.quote_number}', "
            f"status='{self.status}', total_amount={self.total_amount})>"
        )
