"""Order model for order management.

This module defines the Order ORM model for managing customer orders
using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    Order: Order management model

Features:
    - Unique order number generation
    - Order lifecycle tracking (confirmed, production, shipped, installed)
    - Timeline tracking (order_date, required_date)
    - JSONB for installation address
    - Special instructions support
    - Relationships with quotes and order items
    - Automatic timestamp management
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    Date,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.order_item import OrderItem
    from app.models.quote import Quote

__all__ = ["Order"]


class Order(Base):
    """Order model for order management.

    Represents confirmed purchases that enter production.
    Each order tracks delivery dates, special instructions,
    and installation details.

    Attributes:
        id: Primary key
        quote_id: Foreign key to Quote
        order_number: Unique order identifier
        order_date: When order was placed
        required_date: Requested delivery date
        status: Current state (confirmed, production, shipped, installed)
        special_instructions: Customer requests
        installation_address: Delivery location (JSONB)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        quote: Related quote
        items: Related order items
    """

    __tablename__ = "orders"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Foreign keys
    quote_id: Mapped[int] = mapped_column(
        ForeignKey("quotes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Quote ID",
    )

    # Order identification
    order_number: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        doc="Unique order identifier",
    )

    # Timeline tracking
    order_date: Mapped[date] = mapped_column(
        Date,
        default=date.today,
        server_default=func.current_date(),
        nullable=False,
        index=True,
        doc="When order was placed",
    )
    required_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        default=None,
        index=True,
        doc="Requested delivery date",
    )

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(20),
        default="confirmed",
        nullable=False,
        index=True,
        doc="Current state: confirmed, production, shipped, installed",
    )

    # Customer instructions
    special_instructions: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        default=None,
        doc="Customer requests and special instructions",
    )

    # Installation address (JSONB for flexibility)
    installation_address: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        default=None,
        doc="Delivery location (JSONB)",
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
    quote: Mapped[Quote] = relationship(
        "Quote",
        back_populates="orders",
        doc="Related quote",
    )
    items: Mapped[list[OrderItem]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
        doc="Related order items",
    )

    # Indexes
    __table_args__ = (
        # Composite index for filtering by status and order date
        Index(
            "idx_orders_status_date",
            "status",
            "order_date",
        ),
        # Composite index for filtering by status and required date
        Index(
            "idx_orders_status_required",
            "status",
            "required_date",
        ),
        # Composite index for filtering by quote and status
        Index(
            "idx_orders_quote_status",
            "quote_id",
            "status",
        ),
        # GIN index on installation_address for JSONB queries
        Index(
            "idx_orders_installation_address",
            "installation_address",
            postgresql_using="gin",
        ),
    )

    def __repr__(self) -> str:
        """String representation of Order.

        Returns:
            str: Order representation with ID, number, and status
        """
        return (
            f"<Order(id={self.id}, order_number='{self.order_number}', "
            f"status='{self.status}', order_date={self.order_date})>"
        )
