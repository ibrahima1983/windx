"""Repository for Customer operations.

This module provides the repository implementation for Customer
model with custom query methods.

Public Classes:
    CustomerRepository: Repository for customer operations

Features:
    - Standard CRUD operations via BaseRepository
    - Get by email lookup
    - Get active customers
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.base import BaseRepository
from app.schemas.customer import CustomerCreate, CustomerUpdate

__all__ = ["CustomerRepository"]


# noinspection PyTypeChecker
class CustomerRepository(BaseRepository[Customer, CustomerCreate, CustomerUpdate]):
    """Repository for Customer operations.

    Provides data access methods for customers including
    lookups by email and active status filtering.

    Attributes:
        model: Customer model class
        db: Database session
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize repository with Customer model.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(Customer, db)

    async def get_by_email(self, email: str) -> Customer | None:
        """Get customer by email address.

        Args:
            email (str): Customer email address

        Returns:
            Customer | None: Customer or None if not found

        Example:
            ```python
            customer = await repo.get_by_email("john@example.com")
            ```
        """
        result = await self.db.execute(select(Customer).where(Customer.email == email))
        return result.scalar_one_or_none()

    async def get_active(self) -> list[Customer]:
        """Get all active customers.

        Returns only customers where is_active is True,
        ordered by company name or email.

        Returns:
            list[Customer]: List of active customers

        Example:
            ```python
            active_customers = await repo.get_active()
            ```
        """
        result = await self.db.execute(
            select(Customer)
            .where(Customer.is_active == True)
            .order_by(Customer.company_name, Customer.email)
        )
        return list(result.scalars().all())

    @staticmethod
    def get_filtered(
        is_active: bool | None = None,
        customer_type: str | None = None,
    ):
        """Build filtered query for customers.

        Args:
            is_active (bool | None): Filter by active status
            customer_type (str | None): Filter by customer type

        Returns:
            Select: SQLAlchemy select statement
        """
        from sqlalchemy import Select, select

        query: Select = select(Customer)

        if is_active is not None:
            query = query.where(Customer.is_active == is_active)

        if customer_type:
            query = query.where(Customer.customer_type == customer_type)

        query = query.order_by(Customer.company_name)

        return query

    async def get_with_configurations(self, customer_id: int) -> Customer | None:
        """Get customer with configurations eager-loaded.

        Loads the customer along with all their configurations
        in a single query to prevent N+1 query problems.

        Args:
            customer_id (int): Customer ID

        Returns:
            Customer | None: Customer with configurations or None if not found

        Example:
            ```python
            # Get customer with all configurations loaded
            customer = await repo.get_with_configurations(42)
            if customer:
                print(f"Configurations: {len(customer.configurations)}")
            ```
        """
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Customer)
            .where(Customer.id == customer_id)
            .options(selectinload(Customer.configurations))
        )
        return result.scalar_one_or_none()

    async def get_with_full_details(self, customer_id: int) -> Customer | None:
        """Get customer with all related data eager-loaded.

        Loads the customer along with:
        - All configurations
        - All quotes

        Args:
            customer_id (int): Customer ID

        Returns:
            Customer | None: Customer with full details or None if not found

        Example:
            ```python
            # Get customer with all related data
            customer = await repo.get_with_full_details(42)
            if customer:
                print(f"Configurations: {len(customer.configurations)}")
                print(f"Quotes: {len(customer.quotes)}")
            ```
        """
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(Customer)
            .where(Customer.id == customer_id)
            .options(
                selectinload(Customer.configurations),
                selectinload(Customer.quotes),
            )
        )
        return result.scalar_one_or_none()
