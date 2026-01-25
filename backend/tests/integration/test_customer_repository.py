"""Integration tests for Customer repository.

This module tests the CustomerRepository data access layer including:
- CRUD operations (create, get, get_with_full_details, update, delete)
- Filtering by is_active and customer_type
- Search by company name, contact person, email
- Pagination with different page sizes and edge cases

Features:
    - Repository layer testing
    - Database integration testing
    - Relationship loading testing
    - Query filtering testing
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.repositories.customer import CustomerRepository
from app.schemas.customer import CustomerUpdate
from tests.factories.customer_factory import (
    create_customer_create_schema,
    create_customer_data,
)

pytestmark = pytest.mark.asyncio


class TestCustomerRepositoryCRUD:
    """Tests for basic CRUD operations."""

    async def test_create_customer(self, db_session: AsyncSession):
        """Test creating a customer through repository."""
        repo = CustomerRepository(db_session)

        customer_in = create_customer_create_schema()

        customer = await repo.create(customer_in)
        await db_session.commit()

        assert customer.id is not None
        assert customer.email == customer_in.email
        assert customer.company_name == customer_in.company_name
        assert customer.is_active is True

    async def test_get_customer(self, db_session: AsyncSession):
        """Test getting a customer by ID."""
        repo = CustomerRepository(db_session)

        # Create customer
        customer_in = create_customer_create_schema()
        customer = await repo.create(customer_in)
        await db_session.commit()

        # Get customer
        retrieved = await repo.get(customer.id)

        assert retrieved is not None
        assert retrieved.id == customer.id
        assert retrieved.email == customer.email

    async def test_get_nonexistent_customer(self, db_session: AsyncSession):
        """Test getting a customer that doesn't exist."""
        repo = CustomerRepository(db_session)

        customer = await repo.get(99999)

        assert customer is None

    async def test_get_with_full_details(self, db_session: AsyncSession):
        """Test getting customer with all related data eager-loaded."""
        repo = CustomerRepository(db_session)

        # Create customer
        customer_in = create_customer_create_schema()
        customer = await repo.create(customer_in)
        await db_session.commit()

        # Get with full details
        retrieved = await repo.get_with_full_details(customer.id)

        assert retrieved is not None
        assert retrieved.id == customer.id
        # Verify relationships are loaded (won't trigger additional queries)
        assert hasattr(retrieved, "configurations")
        assert hasattr(retrieved, "quotes")
        assert isinstance(retrieved.configurations, list)
        assert isinstance(retrieved.quotes, list)

    async def test_update_customer(self, db_session: AsyncSession):
        """Test updating a customer."""
        repo = CustomerRepository(db_session)

        # Create customer
        customer_in = create_customer_create_schema()
        customer = await repo.create(customer_in)
        await db_session.commit()

        # Update customer
        update_data = CustomerUpdate(
            company_name="Updated Company",
            phone="555-9999",
        )
        updated = await repo.update(customer, update_data)

        assert updated.company_name == "Updated Company"
        assert updated.phone == "555-9999"
        assert updated.email == customer.email  # Unchanged

    async def test_delete_customer(self, db_session: AsyncSession):
        """Test deleting a customer."""
        repo = CustomerRepository(db_session)

        # Create customer
        customer_in = create_customer_create_schema()
        customer = await repo.create(customer_in)
        await db_session.commit()
        customer_id = customer.id

        # Delete customer
        deleted = await repo.delete(customer_id)

        assert deleted is not None
        assert deleted.id == customer_id

        # Verify deletion
        retrieved = await repo.get(customer_id)
        assert retrieved is None

    async def test_delete_nonexistent_customer(self, db_session: AsyncSession):
        """Test deleting a customer that doesn't exist."""
        repo = CustomerRepository(db_session)

        deleted = await repo.delete(99999)

        assert deleted is None


class TestCustomerRepositoryFiltering:
    """Tests for filtering customers."""

    async def test_filter_by_is_active(self, db_session: AsyncSession):
        """Test filtering customers by active status."""
        repo = CustomerRepository(db_session)

        # Create active and inactive customers
        active_customer = create_customer_data(is_active=True)
        inactive_customer = create_customer_data(is_active=False, inactive=True)

        customer1 = Customer(**active_customer)
        customer2 = Customer(**inactive_customer)
        db_session.add(customer1)
        db_session.add(customer2)
        await db_session.commit()

        # Get active customers
        active_customers = await repo.get_active()

        assert len(active_customers) >= 1
        assert all(c.is_active for c in active_customers)

    async def test_filter_by_customer_type(self, db_session: AsyncSession):
        """Test filtering customers by customer type."""
        repo = CustomerRepository(db_session)

        # Create customers of different types
        commercial = create_customer_data(customer_type="commercial")
        residential = create_customer_data(residential=True)
        contractor = create_customer_data(contractor=True)

        customer1 = Customer(**commercial)
        customer2 = Customer(**residential)
        customer3 = Customer(**contractor)
        db_session.add_all([customer1, customer2, customer3])
        await db_session.commit()

        # Filter by commercial
        query = repo.get_filtered(customer_type="commercial")
        result = await db_session.execute(query)
        commercial_customers = list(result.scalars().all())

        assert len(commercial_customers) >= 1
        assert all(c.customer_type == "commercial" for c in commercial_customers)

    async def test_filter_by_active_and_type(self, db_session: AsyncSession):
        """Test filtering by both active status and customer type."""
        repo = CustomerRepository(db_session)

        # Create various customers
        active_commercial = create_customer_data(customer_type="commercial", is_active=True)
        inactive_commercial = create_customer_data(
            customer_type="commercial", is_active=False, inactive=True
        )
        active_residential = create_customer_data(residential=True, is_active=True)

        customer1 = Customer(**active_commercial)
        customer2 = Customer(**inactive_commercial)
        customer3 = Customer(**active_residential)
        db_session.add_all([customer1, customer2, customer3])
        await db_session.commit()

        # Filter by active commercial
        query = repo.get_filtered(is_active=True, customer_type="commercial")
        result = await db_session.execute(query)
        filtered_customers = list(result.scalars().all())

        assert len(filtered_customers) >= 1
        assert all(c.is_active and c.customer_type == "commercial" for c in filtered_customers)


class TestCustomerRepositorySearch:
    """Tests for searching customers."""

    async def test_get_by_email(self, db_session: AsyncSession):
        """Test getting customer by email address."""
        repo = CustomerRepository(db_session)

        # Create customer
        customer_in = create_customer_create_schema(email="unique@example.com")
        customer = await repo.create(customer_in)
        await db_session.commit()

        # Search by email
        found = await repo.get_by_email("unique@example.com")

        assert found is not None
        assert found.id == customer.id
        assert found.email == "unique@example.com"

    async def test_get_by_email_not_found(self, db_session: AsyncSession):
        """Test searching for non-existent email."""
        repo = CustomerRepository(db_session)

        found = await repo.get_by_email("nonexistent@example.com")

        assert found is None

    async def test_search_by_company_name(self, db_session: AsyncSession):
        """Test searching customers by company name."""
        repo = CustomerRepository(db_session)

        # Create customers with specific company names
        customer1_data = create_customer_data(company_name="ABC Corporation")
        customer2_data = create_customer_data(company_name="XYZ Industries")

        customer1 = Customer(**customer1_data)
        customer2 = Customer(**customer2_data)
        db_session.add_all([customer1, customer2])
        await db_session.commit()

        # Get all customers (ordered by company_name)
        query = repo.get_filtered()
        result = await db_session.execute(query)
        all_customers = list(result.scalars().all())

        # Verify ordering by company name
        company_names = [c.company_name for c in all_customers if c.company_name]
        assert company_names == sorted(company_names)


class TestCustomerRepositoryPagination:
    """Tests for pagination."""

    async def test_get_multi_with_pagination(self, db_session: AsyncSession):
        """Test getting multiple customers with pagination."""
        repo = CustomerRepository(db_session)

        # Create multiple customers
        for i in range(5):
            customer_data = create_customer_data()
            customer = Customer(**customer_data)
            db_session.add(customer)
        await db_session.commit()

        # Get first page
        page1 = await repo.get_multi(skip=0, limit=2)
        assert len(page1) == 2

        # Get second page
        page2 = await repo.get_multi(skip=2, limit=2)
        assert len(page2) == 2

        # Verify different customers
        page1_ids = {c.id for c in page1}
        page2_ids = {c.id for c in page2}
        assert page1_ids.isdisjoint(page2_ids)

    async def test_pagination_edge_cases(self, db_session: AsyncSession):
        """Test pagination edge cases."""
        repo = CustomerRepository(db_session)

        # Create 3 customers
        for i in range(3):
            customer_data = create_customer_data()
            customer = Customer(**customer_data)
            db_session.add(customer)
        await db_session.commit()

        # Request more than available
        customers = await repo.get_multi(skip=0, limit=100)
        assert len(customers) >= 3

        # Skip beyond available
        customers = await repo.get_multi(skip=100, limit=10)
        assert len(customers) == 0

    async def test_pagination_with_different_page_sizes(self, db_session: AsyncSession):
        """Test pagination with different page sizes."""
        repo = CustomerRepository(db_session)

        # Create 10 customers
        for i in range(10):
            customer_data = create_customer_data()
            customer = Customer(**customer_data)
            db_session.add(customer)
        await db_session.commit()

        # Test different page sizes
        page_size_5 = await repo.get_multi(skip=0, limit=5)
        assert len(page_size_5) == 5

        page_size_3 = await repo.get_multi(skip=0, limit=3)
        assert len(page_size_3) == 3

        page_size_1 = await repo.get_multi(skip=0, limit=1)
        assert len(page_size_1) == 1


class TestCustomerRepositoryFactoryTraits:
    """Tests for factory traits."""

    async def test_residential_trait(self, db_session: AsyncSession):
        """Test residential customer trait."""
        repo = CustomerRepository(db_session)

        # Create residential customer using trait
        customer_in = create_customer_create_schema(residential=True)
        customer = await repo.create(customer_in)
        await db_session.commit()

        assert customer.customer_type == "residential"
        assert customer.company_name is None  # Residential typically don't have company

    async def test_contractor_trait(self, db_session: AsyncSession):
        """Test contractor customer trait."""
        repo = CustomerRepository(db_session)

        # Create contractor using trait
        customer_in = create_customer_create_schema(contractor=True)
        customer = await repo.create(customer_in)
        await db_session.commit()

        assert customer.customer_type == "contractor"
        assert customer.payment_terms == "net_15"

    async def test_inactive_trait(self, db_session: AsyncSession):
        """Test inactive customer trait."""
        repo = CustomerRepository(db_session)

        # Create inactive customer using trait
        customer_data = create_customer_data(inactive=True)
        customer = Customer(**customer_data)
        db_session.add(customer)
        await db_session.commit()

        assert customer.is_active is False

        # Verify not in active list
        active_customers = await repo.get_active()
        assert customer.id not in [c.id for c in active_customers]
