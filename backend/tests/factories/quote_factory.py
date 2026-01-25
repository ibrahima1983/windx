"""Quote factory for test data generation.

This module provides factory functions for creating quote test data
with realistic values and proper validation.

Public Functions:
    create_quote_data: Create quote data dictionary
    create_multiple_quotes_data: Create multiple quote data dictionaries

Features:
    - Realistic test data
    - Unique values per call
    - Customizable fields
    - Proper validation
    - Automatic quote number generation
"""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

__all__ = [
    "create_quote_data",
    "create_multiple_quotes_data",
    "QuoteFactory",
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


def create_quote_data(
    configuration_id: int | None = None,
    customer_id: int | None = None,
    quote_number: str | None = None,
    subtotal: Decimal | None = None,
    tax_rate: Decimal | None = None,
    tax_amount: Decimal | None = None,
    discount_amount: Decimal | None = None,
    total_amount: Decimal | None = None,
    technical_requirements: dict | None = None,
    valid_until: date | None = None,
    status: str = "draft",
    **kwargs: Any,
) -> dict[str, Any]:
    """Create quote data dictionary.

    Args:
        configuration_id (int | None): Configuration ID (required for actual creation)
        customer_id (int | None): Customer ID (optional)
        quote_number (str | None): Quote number (auto-generated if None)
        subtotal (Decimal | None): Subtotal (default: 500.00)
        tax_rate (Decimal | None): Tax rate percentage (default: 8.50)
        tax_amount (Decimal | None): Tax amount (auto-calculated if None)
        discount_amount (Decimal | None): Discount amount (default: 0.00)
        total_amount (Decimal | None): Total amount (auto-calculated if None)
        technical_requirements (dict | None): Technical requirements
        valid_until (date | None): Expiration date (default: 30 days from now)
        status (str): Quote status (draft, sent, accepted, expired)
        **kwargs: Additional fields

    Returns:
        dict[str, Any]: Quote data dictionary

    Examples:
        >>> # Standard quote
        >>> data = create_quote_data(configuration_id=1)

        >>> # Quote with custom pricing
        >>> data = create_quote_data(
        ...     configuration_id=1,
        ...     subtotal=Decimal("1000.00"),
        ...     tax_rate=Decimal("10.00")
        ... )
    """
    unique_id = _get_unique_id()

    # Generate default values
    if quote_number is None:
        today = date.today()
        quote_number = f"Q-{today.strftime('%Y%m%d')}-{unique_id}"

    if subtotal is None:
        subtotal = Decimal("500.00")

    if tax_rate is None:
        tax_rate = Decimal("8.50")

    if tax_amount is None:
        tax_amount = (subtotal * tax_rate / Decimal("100")).quantize(Decimal("0.01"))

    if discount_amount is None:
        discount_amount = Decimal("0.00")

    if total_amount is None:
        total_amount = (subtotal + tax_amount - discount_amount).quantize(Decimal("0.01"))

    if valid_until is None:
        valid_until = date.today() + timedelta(days=30)

    data = {
        "configuration_id": configuration_id,
        "customer_id": customer_id,
        "quote_number": quote_number,
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "tax_amount": tax_amount,
        "discount_amount": discount_amount,
        "total_amount": total_amount,
        "technical_requirements": technical_requirements,
        "valid_until": valid_until,
        "status": status,
    }

    data.update(kwargs)
    return data


def create_multiple_quotes_data(
    count: int = 3,
    **kwargs: Any,
) -> list[dict[str, Any]]:
    """Create multiple quote data dictionaries.

    Args:
        count (int): Number of quotes to create
        **kwargs: Common fields for all quotes

    Returns:
        list[dict[str, Any]]: List of quote data dictionaries

    Examples:
        >>> # Create 5 quotes
        >>> quotes = create_multiple_quotes_data(count=5, configuration_id=1)
    """
    return [create_quote_data(**kwargs) for _ in range(count)]


class QuoteFactory:
    """Class-based factory for creating quotes in database.

    This factory provides a convenient interface for creating quote
    records in the database during tests, with automatic creation of
    required dependencies (configuration, customer, manufacturing type).

    Examples:
        >>> # Create single quote (auto-creates dependencies)
        >>> quote = await QuoteFactory.create(db_session)

        >>> # Create with custom fields
        >>> quote = await QuoteFactory.create(
        ...     db_session,
        ...     quote_number="Q-2024-001",
        ...     status="sent"
        ... )

        >>> # Create with existing configuration
        >>> quote = await QuoteFactory.create(
        ...     db_session,
        ...     configuration_id=config.id
        ... )

        >>> # Create multiple quotes
        >>> quotes = await QuoteFactory.create_batch(db_session, 5)
    """

    @staticmethod
    async def create(
        db_session: Any,
        configuration_id: int | None = None,
        customer_id: int | None = None,
        **kwargs: Any,
    ) -> Any:
        """Create a quote in the database.

        If configuration_id is not provided, automatically creates a
        configuration with customer and manufacturing type.

        Args:
            db_session: Database session
            configuration_id: Optional configuration ID (auto-created if None)
            customer_id: Optional customer ID (auto-created if None)
            **kwargs: Quote fields

        Returns:
            Quote: Created quote instance

        Examples:
            >>> # Auto-create dependencies
            >>> quote = await QuoteFactory.create(db_session)

            >>> # Use existing configuration
            >>> quote = await QuoteFactory.create(
            ...     db_session,
            ...     configuration_id=config.id,
            ...     status="sent"
            ... )
        """
        from app.models.quote import Quote

        # Create configuration if not provided
        if configuration_id is None:
            from tests.factories.configuration_factory import ConfigurationFactory

            config = await ConfigurationFactory.create(db_session)
            configuration_id = config.id
            if customer_id is None:
                customer_id = config.customer_id

        # Create quote data
        data = create_quote_data(
            configuration_id=configuration_id,
            customer_id=customer_id,
            **kwargs,
        )

        # Create quote instance
        quote = Quote(**data)

        db_session.add(quote)
        await db_session.commit()
        await db_session.refresh(quote)

        return quote

    @staticmethod
    async def create_batch(
        db_session: Any,
        count: int,
        **kwargs: Any,
    ) -> list[Any]:
        """Create multiple quotes in the database.

        Args:
            db_session: Database session
            count: Number of quotes to create
            **kwargs: Common fields for all quotes

        Returns:
            list[Quote]: List of created quote instances

        Examples:
            >>> # Create 5 quotes (each with own config/customer)
            >>> quotes = await QuoteFactory.create_batch(db_session, 5)

            >>> # Create 3 quotes with same configuration
            >>> quotes = await QuoteFactory.create_batch(
            ...     db_session,
            ...     3,
            ...     configuration_id=config.id
            ... )
        """
        quotes = []
        for _ in range(count):
            quote = await QuoteFactory.create(db_session, **kwargs)
            quotes.append(quote)
        return quotes
