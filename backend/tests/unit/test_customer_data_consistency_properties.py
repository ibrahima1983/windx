"""Property-based tests for customer data consistency.

This module contains property-based tests that verify auto-created customers
accurately reflect the source user data.

Property 8: Customer data consistency
- For any auto-created customer, the contact information should accurately
  reflect the source user data

Requirements: 1.3, 4.2
"""

from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.core.rbac import Role
from app.models.customer import Customer
from app.models.user import User
from app.services.entry import EntryService


@composite
def user_data_for_customer_creation(draw):
    """Generate user data specifically for testing customer creation."""
    return User(
        id=draw(st.integers(min_value=1, max_value=1000)),
        email=draw(st.emails()),
        username=draw(
            st.text(
                min_size=3,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            )
        ),
        full_name=draw(st.text(min_size=1, max_size=100)),
        role=draw(st.sampled_from([Role.CUSTOMER.value, Role.SALESMAN.value, Role.PARTNER.value])),
        is_active=True,
        is_superuser=False,
    )


class TestCustomerDataConsistencyProperties:
    """Property-based tests for customer data consistency."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        db.add = AsyncMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        return db

    @given(user=user_data_for_customer_creation())
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_customer_data_consistency(self, mock_db, user: User):
        """
        **Feature: entry-page-customer-rbac-fix, Property 8: Customer data consistency**

        Property: For any auto-created customer, the contact information should
        accurately reflect the source user data.

        This ensures data integrity when customers are auto-created from user accounts.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock that no existing customer is found
        entry_service._find_customer_by_email = AsyncMock(return_value=None)

        # Mock customer repository
        entry_service.customer_repo.create = AsyncMock()

        # Act
        await entry_service._get_or_create_customer_for_user(user)

        # Assert - Verify customer data consistency
        entry_service.customer_repo.create.assert_called_once()
        customer_data = entry_service.customer_repo.create.call_args[0][0]

        # Email should match exactly
        assert customer_data.email == user.email

        # Contact person should be user's full name or username as fallback
        if user.full_name and user.full_name.strip():
            assert customer_data.contact_person == user.full_name
        else:
            assert customer_data.contact_person == user.username

        # Customer type should be set to residential by default
        assert customer_data.customer_type == "residential"

        # Should be active
        assert customer_data.is_active is True

        # Notes should indicate auto-creation
        assert "Auto-created" in customer_data.notes
        assert user.username in customer_data.notes

    @given(
        users=st.lists(user_data_for_customer_creation(), min_size=2, max_size=5),
        shared_email=st.emails(),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_duplicate_email_handling_consistency(
        self, mock_db, users: list[User], shared_email: str
    ):
        """
        Property: When multiple users have the same email, customer creation
        should handle duplicates consistently and maintain data integrity.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Set all users to have the same email
        for user in users:
            user.email = shared_email

        # Mock existing customer for the shared email
        existing_customer = Customer(
            id=999,
            email=shared_email,
            contact_person=users[0].full_name,
            customer_type="residential",
            is_active=True,
            notes=f"Auto-created from user: {users[0].username}",
        )

        # First user creates customer, subsequent users find existing
        call_count = 0

        def mock_find_customer(email):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return None  # First call - no existing customer
            else:
                return existing_customer  # Subsequent calls - existing customer found

        entry_service._find_customer_by_email = AsyncMock(side_effect=mock_find_customer)
        entry_service.customer_repo.create = AsyncMock(return_value=existing_customer)

        # Act - Process all users
        results = []
        for user in users:
            result = await entry_service._get_or_create_customer_for_user(user)
            results.append(result)

        # Assert - All users should get the same customer
        assert all(result.id == existing_customer.id for result in results)
        assert all(result.email == shared_email for result in results)

        # Only one customer should be created
        entry_service.customer_repo.create.assert_called_once()

    @given(
        user=user_data_for_customer_creation(),
        edge_case_data=st.sampled_from(
            ["empty_full_name", "whitespace_full_name", "special_characters_name", "very_long_name"]
        ),
    )
    @settings(max_examples=50, deadline=None)
    @pytest.mark.asyncio
    async def test_property_edge_case_data_consistency(
        self, mock_db, user: User, edge_case_data: str
    ):
        """
        Property: For any edge cases in user data (empty names, special characters, etc.),
        customer creation should handle them consistently and maintain data integrity.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Modify user data based on edge case
        if edge_case_data == "empty_full_name":
            user.full_name = ""
        elif edge_case_data == "whitespace_full_name":
            user.full_name = "   \t\n   "
        elif edge_case_data == "special_characters_name":
            user.full_name = "José María O'Connor-Smith"
        elif edge_case_data == "very_long_name":
            user.full_name = "A" * 200  # Very long name

        # Mock no existing customer
        entry_service._find_customer_by_email = AsyncMock(return_value=None)
        entry_service.customer_repo.create = AsyncMock()

        # Act
        await entry_service._get_or_create_customer_for_user(user)

        # Assert - Data should be handled consistently
        entry_service.customer_repo.create.assert_called_once()
        customer_data = entry_service.customer_repo.create.call_args[0][0]

        # Contact person should always be valid
        assert customer_data.contact_person is not None
        assert len(customer_data.contact_person.strip()) > 0

        # Should use username as fallback for empty/whitespace names
        if not user.full_name or not user.full_name.strip():
            assert customer_data.contact_person == user.username
        else:
            assert customer_data.contact_person == user.full_name

        # Email should always match
        assert customer_data.email == user.email

    @given(
        user=user_data_for_customer_creation(),
        customer_types=st.sampled_from(["residential", "commercial", "contractor"]),
    )
    @settings(max_examples=30, deadline=None)
    @pytest.mark.asyncio
    async def test_property_customer_type_consistency(
        self, mock_db, user: User, customer_types: str
    ):
        """
        Property: For any user role, the auto-created customer should have
        a consistent customer_type assignment based on business rules.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock no existing customer
        entry_service._find_customer_by_email = AsyncMock(return_value=None)
        entry_service.customer_repo.create = AsyncMock()

        # Act
        await entry_service._get_or_create_customer_for_user(user)

        # Assert - Customer type should be consistently assigned
        entry_service.customer_repo.create.assert_called_once()
        customer_data = entry_service.customer_repo.create.call_args[0][0]

        # Default should be residential for auto-created customers
        assert customer_data.customer_type == "residential"

        # Should be active
        assert customer_data.is_active is True

    @given(
        users_with_same_data=st.lists(
            user_data_for_customer_creation(), min_size=2, max_size=3
        ).map(
            lambda users: [
                User(
                    id=user.id,
                    email="same@example.com",  # Same email
                    username=f"user_{user.id}",  # Different usernames
                    full_name="Same Full Name",  # Same full name
                    role=user.role,
                    is_active=True,
                    is_superuser=False,
                )
                for user in users
            ]
        )
    )
    @settings(max_examples=20, deadline=None)
    @pytest.mark.asyncio
    async def test_property_idempotent_customer_creation(
        self, mock_db, users_with_same_data: list[User]
    ):
        """
        Property: For any users with the same email, customer creation should
        be idempotent - creating the same customer record regardless of which
        user triggers the creation first.
        """
        # Arrange
        entry_service = EntryService(mock_db)

        # Mock that customer doesn't exist initially
        created_customer = Customer(
            id=1000,
            email="same@example.com",
            contact_person="Same Full Name",
            customer_type="residential",
            is_active=True,
            notes="Auto-created from user: user_1",
        )

        entry_service._find_customer_by_email = AsyncMock(return_value=None)
        entry_service.customer_repo.create = AsyncMock(return_value=created_customer)

        # Act - Create customer with first user
        first_result = await entry_service._get_or_create_customer_for_user(users_with_same_data[0])

        # Now mock that customer exists for subsequent calls
        entry_service._find_customer_by_email = AsyncMock(return_value=created_customer)

        # Act - Get customer with other users
        subsequent_results = []
        for user in users_with_same_data[1:]:
            result = await entry_service._get_or_create_customer_for_user(user)
            subsequent_results.append(result)

        # Assert - All should get the same customer
        assert first_result.id == created_customer.id
        assert all(result.id == created_customer.id for result in subsequent_results)

        # Customer should only be created once
        entry_service.customer_repo.create.assert_called_once()

        # Data consistency should be maintained
        assert first_result.email == "same@example.com"
        assert first_result.contact_person == "Same Full Name"
        assert all(result.email == first_result.email for result in subsequent_results)
        assert all(
            result.contact_person == first_result.contact_person for result in subsequent_results
        )
