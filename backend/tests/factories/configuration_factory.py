"""Configuration factory for test data generation.

This module provides factory functions for creating configuration test data
with realistic values and proper validation.

Public Functions:
    create_configuration_data: Create configuration data dictionary

Public Classes:
    ConfigurationFactory: Class-based factory for creating configurations in database

Features:
    - Realistic test data
    - Unique values per call
    - Customizable fields
    - Automatic manufacturing type and customer creation
    - Proper validation
"""

from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.models.configuration import Configuration

__all__ = [
    "create_configuration_data",
    "ConfigurationFactory",
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


def create_configuration_data(
    manufacturing_type_id: int | None = None,
    customer_id: int | None = None,
    name: str | None = None,
    description: str | None = None,
    status: str = "draft",
    reference_code: str | None = None,
    base_price: Decimal | None = None,
    total_price: Decimal | None = None,
    calculated_weight: Decimal | None = None,
    calculated_technical_data: dict | None = None,
    **kwargs: Any,
) -> dict[str, Any]:
    """Create configuration data dictionary.

    Args:
        manufacturing_type_id (int | None): Manufacturing type ID (required for actual creation)
        customer_id (int | None): Customer ID (optional)
        name (str | None): Configuration name (auto-generated if None)
        description (str | None): Configuration description
        status (str): Configuration status (draft, saved, quoted, ordered)
        reference_code (str | None): Reference code (auto-generated if None)
        base_price (Decimal | None): Base price (default: 200.00)
        total_price (Decimal | None): Total price (default: 200.00)
        calculated_weight (Decimal | None): Calculated weight (default: 15.00)
        calculated_technical_data (dict | None): Technical data (JSONB)
        **kwargs: Additional fields

    Returns:
        dict[str, Any]: Configuration data dictionary

    Examples:
        >>> # Standard configuration
        >>> data = create_configuration_data(manufacturing_type_id=1)

        >>> # Configuration with custom pricing
        >>> data = create_configuration_data(
        ...     manufacturing_type_id=1,
        ...     total_price=Decimal("500.00")
        ... )
    """
    unique_id = _get_unique_id()

    # Generate default values
    if name is None:
        name = f"Test Configuration {unique_id}"

    if reference_code is None:
        reference_code = f"CFG-TEST-{unique_id}"

    if base_price is None:
        base_price = Decimal("200.00")

    if total_price is None:
        total_price = Decimal("200.00")

    if calculated_weight is None:
        calculated_weight = Decimal("15.00")

    if calculated_technical_data is None:
        calculated_technical_data = {}

    data = {
        "manufacturing_type_id": manufacturing_type_id,
        "customer_id": customer_id,
        "name": name,
        "description": description,
        "status": status,
        "reference_code": reference_code,
        "base_price": base_price,
        "total_price": total_price,
        "calculated_weight": calculated_weight,
        "calculated_technical_data": calculated_technical_data,
    }

    data.update(kwargs)
    return data


class ConfigurationFactory:
    """Class-based factory for creating configurations in database.

    This factory provides a convenient interface for creating configuration
    records in the database during tests, with automatic creation of
    required dependencies (manufacturing type, customer).

    Examples:
        >>> # Create single configuration (auto-creates dependencies)
        >>> config = await ConfigurationFactory.create(db_session)

        >>> # Create with custom fields
        >>> config = await ConfigurationFactory.create(
        ...     db_session,
        ...     name="Custom Window",
        ...     total_price=Decimal("500.00")
        ... )

        >>> # Create with existing manufacturing type
        >>> config = await ConfigurationFactory.create(
        ...     db_session,
        ...     manufacturing_type_id=mfg_type.id
        ... )

        >>> # Create multiple configurations
        >>> configs = await ConfigurationFactory.create_batch(db_session, 5)
    """

    @staticmethod
    async def create(
        db_session: AsyncSession,
        manufacturing_type_id: int | None = None,
        customer_id: int | None = None,
        **kwargs: Any,
    ) -> Configuration:
        """Create a configuration in the database.

        If manufacturing_type_id or customer_id are not provided,
        automatically creates them.

        Args:
            db_session: Database session
            manufacturing_type_id: Optional manufacturing type ID (auto-created if None)
            customer_id: Optional customer ID (auto-created if None)
            **kwargs: Configuration fields

        Returns:
            Configuration: Created configuration instance

        Examples:
            >>> # Auto-create dependencies
            >>> config = await ConfigurationFactory.create(db_session)

            >>> # Use existing manufacturing type
            >>> config = await ConfigurationFactory.create(
            ...     db_session,
            ...     manufacturing_type_id=mfg_type.id,
            ...     name="Custom Window"
            ... )
        """
        from app.models.configuration import Configuration
        from app.models.manufacturing_type import ManufacturingType

        # Create manufacturing type if not provided
        if manufacturing_type_id is None:
            unique_id = _get_unique_id()
            mfg_type = ManufacturingType(
                id=None,
                name=f"Test Type {unique_id}",
                description="Test manufacturing type",
                base_price=Decimal("200.00"),
                base_weight=Decimal("15.00"),
                is_active=True,
            )
            db_session.add(mfg_type)
            await db_session.flush()
            manufacturing_type_id = mfg_type.id

        # Create customer if not provided
        if customer_id is None:
            from tests.factories.customer_factory import CustomerFactory

            customer = await CustomerFactory.create(db_session)
            customer_id = customer.id

        # Create configuration data
        data = create_configuration_data(
            manufacturing_type_id=manufacturing_type_id,
            customer_id=customer_id,
            **kwargs,
        )

        # Create configuration instance
        config = Configuration(**data)

        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        return config

    @staticmethod
    async def create_batch(
        db_session: AsyncSession,
        count: int,
        **kwargs: Any,
    ) -> list[Configuration]:
        """Create multiple configurations in the database.

        Args:
            db_session: Database session
            count: Number of configurations to create
            **kwargs: Common fields for all configurations

        Returns:
            list[Configuration]: List of created configuration instances

        Examples:
            >>> # Create 5 configurations (each with own dependencies)
            >>> configs = await ConfigurationFactory.create_batch(db_session, 5)

            >>> # Create 3 configurations with same manufacturing type
            >>> configs = await ConfigurationFactory.create_batch(
            ...     db_session,
            ...     3,
            ...     manufacturing_type_id=mfg_type.id
            ... )
        """
        configs = []
        for _ in range(count):
            config = await ConfigurationFactory.create(db_session, **kwargs)
            configs.append(config)
        return configs
