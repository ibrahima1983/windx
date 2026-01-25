"""Order factory for test data generation.

This module provides factory functions for creating order test data
with realistic values and proper validation.

Public Functions:
    create_order_data: Create order data dictionary
    create_multiple_orders_data: Create multiple order data dictionaries

Public Classes:
    OrderFactory: Class-based factory for creating orders in database

Features:
    - Realistic test data
    - Unique values per call
    - Customizable fields
    - Factory traits (in_production, shipped, completed)
    - Proper validation
    - Automatic order number generation
    - Automatic quote and customer creation
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.order import Order

__all__ = [
    "create_order_data",
    "create_multiple_orders_data",
    "OrderFactory",
]

import uuid


def reset_counter() -> None:
    """Reset the global counter for test isolation.

    Note: This function is kept for compatibility but is no longer needed
    since we use UUIDs for uniqueness.
    """
    pass  # No-op since we use UUIDs now


def _get_unique_id() -> str:
    """Get unique ID for test data.

    Returns:
        str: Unique UUID-based identifier
    """
    return str(uuid.uuid4())[:8]  # Use first 8 chars of UUID for readability
    _counter += 1
    return _counter


def create_order_data(
    quote_id: int | None = None,
    order_number: str | None = None,
    order_date: date | None = None,
    required_date: date | None = None,
    status: str = "confirmed",
    special_instructions: str | None = None,
    installation_address: dict | None = None,
    # Factory traits
    in_production: bool = False,
    shipped: bool = False,
    completed: bool = False,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create order data dictionary.

    Args:
        quote_id (int | None): Quote ID (required for actual creation)
        order_number (str | None): Order number (auto-generated if None)
        order_date (date | None): Order date (default: today)
        required_date (date | None): Required delivery date (default: 30 days from now)
        status (str): Order status (confirmed, production, shipped, installed)
        special_instructions (str | None): Customer instructions
        installation_address (dict | None): Installation address (auto-generated if None)
        in_production (bool): Apply in_production trait
        shipped (bool): Apply shipped trait
        completed (bool): Apply completed trait
        **kwargs: Additional fields

    Returns:
        dict[str, Any]: Order data dictionary

    Examples:
        >>> # Standard confirmed order
        >>> data = create_order_data(quote_id=1)

        >>> # Order in production (trait)
        >>> data = create_order_data(quote_id=1, in_production=True)

        >>> # Shipped order (trait)
        >>> data = create_order_data(quote_id=1, shipped=True)

        >>> # Completed order (trait)
        >>> data = create_order_data(quote_id=1, completed=True)
    """
    unique_id = _get_unique_id()

    # Apply traits (priority: completed > shipped > in_production)
    if completed:
        status = "installed"
    elif shipped:
        status = "shipped"
    elif in_production:
        status = "production"

    # Generate default values
    if order_number is None:
        today = date.today()
        order_number = f"ORD-{today.strftime('%Y%m%d')}-{unique_id}"

    if order_date is None:
        order_date = date.today()

    if required_date is None:
        required_date = date.today() + timedelta(days=30)

    if installation_address is None:
        installation_address = {
            "street": f"{unique_id} Installation Street",
            "city": "Install City",
            "state": "IC",
            "zip": f"{unique_id[:5]}",
            "country": "USA",
            "contact_name": f"Contact Person {unique_id}",
            "contact_phone": f"555-{unique_id}",
        }

    data = {
        "quote_id": quote_id,
        "order_number": order_number,
        "order_date": order_date,
        "required_date": required_date,
        "status": status,
        "special_instructions": special_instructions,
        "installation_address": installation_address,
    }

    data.update(kwargs)
    return data


def create_multiple_orders_data(
    count: int = 3,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Create multiple order data dictionaries.

    Args:
        count (int): Number of orders to create
        **kwargs: Common fields for all orders

    Returns:
        list[dict[str, Any]]: List of order data dictionaries

    Examples:
        >>> # Create 5 orders
        >>> orders = create_multiple_orders_data(count=5, quote_id=1)

        >>> # Create 3 orders in production
        >>> orders = create_multiple_orders_data(
        ...     count=3,
        ...     quote_id=1,
        ...     in_production=True
        ... )
    """
    return [create_order_data(**kwargs) for _ in range(count)]


class OrderFactory:
    """Class-based factory for creating orders in database.

    This factory provides a convenient interface for creating order
    records in the database during tests, with automatic creation of
    required dependencies (quote, customer, configuration).

    Examples:
        >>> # Create single order (auto-creates quote and customer)
        >>> order = await OrderFactory.create(db_session)

        >>> # Create with custom fields
        >>> order = await OrderFactory.create(
        ...     db_session,
        ...     order_number="ORD-2024-001",
        ...     status="production"
        ... )

        >>> # Create with trait
        >>> order = await OrderFactory.create(
        ...     db_session,
        ...     shipped=True
        ... )

        >>> # Create with existing quote
        >>> order = await OrderFactory.create(
        ...     db_session,
        ...     quote_id=existing_quote.id
        ... )

        >>> # Create multiple orders
        >>> orders = await OrderFactory.create_batch(db_session, 5)
    """

    @staticmethod
    async def create(
        db_session: AsyncSession,
        quote_id: int | None = None,
        **kwargs: Any,
    ) -> Order:
        """Create an order in the database.

        If quote_id is not provided, automatically creates a quote with
        customer and configuration.

        Args:
            db_session: Database session
            quote_id: Optional quote ID (auto-created if None)
            **kwargs: Order fields and traits

        Returns:
            Order: Created order instance

        Examples:
            >>> # Auto-create dependencies
            >>> order = await OrderFactory.create(db_session)

            >>> # Use existing quote
            >>> order = await OrderFactory.create(
            ...     db_session,
            ...     quote_id=quote.id,
            ...     status="production"
            ... )
        """
        from app.models.order import Order

        # Create quote if not provided
        if quote_id is None:
            from tests.factories.quote_factory import QuoteFactory

            quote = await QuoteFactory.create(db_session)
            quote_id = quote.id

        # Create order data
        data = create_order_data(quote_id=quote_id, **kwargs)

        # Create order instance
        order = Order(**data)

        db_session.add(order)
        await db_session.commit()
        await db_session.refresh(order)

        return order

    @staticmethod
    async def create_batch(
        db_session: AsyncSession,
        count: int,
        **kwargs: Any,
    ) -> list[Order]:
        """Create multiple orders in the database.

        Args:
            db_session: Database session
            count: Number of orders to create
            **kwargs: Common fields for all orders

        Returns:
            list[Order]: List of created order instances

        Examples:
            >>> # Create 5 orders (each with own quote/customer)
            >>> orders = await OrderFactory.create_batch(db_session, 5)

            >>> # Create 3 orders in production
            >>> orders = await OrderFactory.create_batch(
            ...     db_session,
            ...     3,
            ...     in_production=True
            ... )
        """
        orders = []
        for _ in range(count):
            order = await OrderFactory.create(db_session, **kwargs)
            orders.append(order)
        return orders
