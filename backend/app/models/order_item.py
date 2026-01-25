"""OrderItem model for order line items.

This module defines the OrderItem ORM model for managing individual
items within orders using SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    OrderItem: Order line item model

Features:
    - Multiple configurations per order
    - Quantity tracking with CHECK constraint
    - Unit and total pricing
    - Production status tracking per item
    - Relationships with orders and configurations
    - Automatic timestamp management
"""

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.configuration import Configuration
    from app.models.order import Order

__all__ = ["OrderItem"]


class OrderItem(Base):
    """OrderItem model for order line items.

    Represents individual configurations within an order.
    Supports multiple quantities of the same configuration
    and tracks production status per item.

    Attributes:
        id: Primary key
        order_id: Foreign key to Order
        configuration_id: Foreign key to Configuration
        quantity: Item quantity (must be > 0)
        unit_price: Price per unit
        total_price: Total line item price (quantity * unit_price)
        production_status: Status (pending, in_production, completed)
        created_at: Record creation timestamp
        updated_at: Last update timestamp
        order: Related order
        configuration: Related configuration
    """

    __tablename__ = "order_items"

    # Primary key
    id: Mapped[int] = mapped_column(
        primary_key=True,
        index=True,
        autoincrement=True,
        sort_order=-100,
        doc="Primary key identifier",
    )

    # Foreign keys
    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Order ID",
    )
    configuration_id: Mapped[int] = mapped_column(
        ForeignKey("configurations.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Configuration ID",
    )

    # Quantity and pricing
    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        doc="Item quantity (must be > 0)",
    )
    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        doc="Price per unit",
    )
    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        index=True,
        doc="Total line item price (quantity * unit_price)",
    )

    # Production status tracking
    production_status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        nullable=False,
        index=True,
        doc="Production status: pending, in_production, completed",
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
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
        doc="Related order",
    )
    configuration: Mapped["Configuration"] = relationship(
        "Configuration",
        back_populates="order_items",
        doc="Related configuration",
    )

    # Constraints and Indexes
    __table_args__ = (
        # CHECK constraint: quantity must be positive
        CheckConstraint(
            "quantity > 0",
            name="ck_order_items_quantity_positive",
        ),
        # Composite index for filtering by order and production status
        Index(
            "idx_order_items_order_status",
            "order_id",
            "production_status",
        ),
        # Composite index for filtering by configuration and production status
        Index(
            "idx_order_items_config_status",
            "configuration_id",
            "production_status",
        ),
    )

    def __repr__(self) -> str:
        """String representation of OrderItem.

        Returns:
            str: OrderItem representation with ID, order, and quantity
        """
        return (
            f"<OrderItem(id={self.id}, order_id={self.order_id}, "
            f"configuration_id={self.configuration_id}, quantity={self.quantity}, "
            f"production_status='{self.production_status}')>"
        )
