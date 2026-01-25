"""Integration tests for user list filtering and sorting.

This module tests the user list endpoint with focus on:
- Filtering by is_active status
- Filtering by is_superuser status
- Text search functionality
- Sorting by different columns
- Combined filters
- Pagination with filters

Features:
    - Full stack testing (HTTP → Service → Repository → Database)
    - Filter combination testing
    - Search functionality validation
    - Sort order verification
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.factories.user_factory import create_user_create_schema

pytestmark = pytest.mark.asyncio


class TestUserListFiltering:
    """Tests for user list filtering functionality."""

    async def test_filter_by_is_active_true(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering users by is_active=true."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 3 active users
        for i in range(3):
            user_in = create_user_create_schema(
                email=f"active{i}@example.com",
                username=f"active{i}",
            )
            await user_service.create_user(user_in)

        # Create 2 inactive users
        for i in range(2):
            user_in = create_user_create_schema(
                email=f"inactive{i}@example.com",
                username=f"inactive{i}",
            )
            user = await user_service.create_user(user_in)
            user.is_active = False
            await db_session.commit()

        # Filter for active users only
        response = await client.get(
            "/api/v1/users/?is_active=true",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should be active
        for user in data["items"]:
            assert user["is_active"] is True

        # Should have at least 3 active users (plus test_superuser)
        assert data["total"] >= 4

    async def test_filter_by_is_active_false(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering users by is_active=false."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 2 inactive users
        for i in range(2):
            user_in = create_user_create_schema(
                email=f"inactive{i}@example.com",
                username=f"inactive{i}",
            )
            user = await user_service.create_user(user_in)
            user.is_active = False
            await db_session.commit()

        # Filter for inactive users only
        response = await client.get(
            "/api/v1/users/?is_active=false",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should be inactive
        for user in data["items"]:
            assert user["is_active"] is False

        # Should have at least 2 inactive users
        assert data["total"] >= 2

    async def test_filter_by_is_superuser_true(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering users by is_superuser=true."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 2 regular users
        for i in range(2):
            user_in = create_user_create_schema(
                email=f"regular{i}@example.com",
                username=f"regular{i}",
            )
            await user_service.create_user(user_in)

        # Filter for superusers only
        response = await client.get(
            "/api/v1/users/?is_superuser=true",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should be superusers
        for user in data["items"]:
            assert user["is_superuser"] is True

        # Should have at least 1 superuser (test_superuser)
        assert data["total"] >= 1

    async def test_filter_by_is_superuser_false(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering users by is_superuser=false."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 3 regular users
        for i in range(3):
            user_in = create_user_create_schema(
                email=f"regular{i}@example.com",
                username=f"regular{i}",
            )
            await user_service.create_user(user_in)

        # Filter for regular users only
        response = await client.get(
            "/api/v1/users/?is_superuser=false",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should not be superusers
        for user in data["items"]:
            assert user["is_superuser"] is False

        # Should have at least 3 regular users
        assert data["total"] >= 3


class TestUserListSearch:
    """Tests for user list search functionality."""

    async def test_search_by_username(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test searching users by username."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with specific usernames
        await user_service.create_user(
            create_user_create_schema(
                email="john@example.com",
                username="john_doe",
            )
        )
        await user_service.create_user(
            create_user_create_schema(
                email="jane@example.com",
                username="jane_smith",
            )
        )
        await user_service.create_user(
            create_user_create_schema(
                email="bob@example.com",
                username="bob_jones",
            )
        )

        # Search for "john"
        response = await client.get(
            "/api/v1/users/?search=john",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should find john_doe
        assert data["total"] >= 1
        usernames = [user["username"] for user in data["items"]]
        assert "john_doe" in usernames

    async def test_search_by_email(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test searching users by email."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with specific emails
        await user_service.create_user(
            create_user_create_schema(
                email="alice@company.com",
                username="alice",
            )
        )
        await user_service.create_user(
            create_user_create_schema(
                email="bob@company.com",
                username="bob",
            )
        )

        # Search for "company"
        response = await client.get(
            "/api/v1/users/?search=company",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should find both users
        assert data["total"] >= 2
        emails = [user["email"] for user in data["items"]]
        assert "alice@company.com" in emails
        assert "bob@company.com" in emails

    async def test_search_by_full_name(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test searching users by full name."""
        from app.schemas.user import UserCreate
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with specific full names
        await user_service.create_user(
            create_user_create_schema(
                email="charlie@example.com",
                username="charlie",
                full_name="Charlie Brown",
            )
        )
        await user_service.create_user(
            create_user_create_schema(
                email="david@example.com",
                username="david",
                full_name="David Green",
            )
        )

        # Search for "Brown"
        response = await client.get(
            "/api/v1/users/?search=Brown",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should find Charlie Brown
        assert data["total"] >= 1
        full_names = [user["full_name"] for user in data["items"]]
        assert "Charlie Brown" in full_names

    async def test_search_case_insensitive(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that search is case-insensitive."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create user with mixed case
        await user_service.create_user(
            create_user_create_schema(
                email="TestUser@Example.COM",
                username="TestUser",
            )
        )

        # Search with lowercase
        response = await client.get(
            "/api/v1/users/?search=testuser",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should find the user
        assert data["total"] >= 1
        usernames = [user["username"] for user in data["items"]]
        assert "TestUser" in usernames

    async def test_search_partial_match(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that search matches partial strings."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create user
        await user_service.create_user(
            create_user_create_schema(
                email="developer@example.com",
                username="developer",
            )
        )

        # Search with partial string
        response = await client.get(
            "/api/v1/users/?search=dev",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should find the user
        assert data["total"] >= 1
        usernames = [user["username"] for user in data["items"]]
        assert "developer" in usernames

    async def test_search_no_results(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
    ):
        """Test search with no matching results."""
        # Search for non-existent term
        response = await client.get(
            "/api/v1/users/?search=nonexistentuser12345",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should return empty results
        assert data["total"] == 0
        assert len(data["items"]) == 0


class TestUserListSorting:
    """Tests for user list sorting functionality."""

    async def test_sort_by_created_at_desc(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test sorting users by created_at in descending order."""
        import asyncio

        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with slight delays to ensure different timestamps
        users_created = []
        for i in range(3):
            user_in = create_user_create_schema(
                email=f"sort{i}@example.com",
                username=f"sort{i}",
            )
            user = await user_service.create_user(user_in)
            users_created.append(user)
            await asyncio.sleep(0.01)  # Small delay

        # Get users sorted by created_at desc (default)
        response = await client.get(
            "/api/v1/users/?sort_by=created_at&sort_order=desc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify descending order (newest first)
        items = data["items"]
        if len(items) >= 2:
            for i in range(len(items) - 1):
                created_at_1 = items[i]["created_at"]
                created_at_2 = items[i + 1]["created_at"]
                assert created_at_1 >= created_at_2

    async def test_sort_by_created_at_asc(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test sorting users by created_at in ascending order."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users
        for i in range(3):
            user_in = create_user_create_schema(
                email=f"asc{i}@example.com",
                username=f"asc{i}",
            )
            await user_service.create_user(user_in)

        # Get users sorted by created_at asc
        response = await client.get(
            "/api/v1/users/?sort_by=created_at&sort_order=asc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify ascending order (oldest first)
        items = data["items"]
        if len(items) >= 2:
            for i in range(len(items) - 1):
                created_at_1 = items[i]["created_at"]
                created_at_2 = items[i + 1]["created_at"]
                assert created_at_1 <= created_at_2

    async def test_sort_by_username_asc(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test sorting users by username in ascending order."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with specific usernames
        usernames = ["zebra", "alpha", "beta"]
        for username in usernames:
            user_in = create_user_create_schema(
                email=f"{username}@example.com",
                username=username,
            )
            await user_service.create_user(user_in)

        # Get users sorted by username asc
        response = await client.get(
            "/api/v1/users/?sort_by=username&sort_order=asc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify alphabetical order
        items = data["items"]
        usernames_returned = [user["username"] for user in items]

        # Check that our test users are in alphabetical order
        test_users = [u for u in usernames_returned if u in ["alpha", "beta", "zebra"]]
        assert test_users == sorted(test_users)

    async def test_sort_by_username_desc(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test sorting users by username in descending order."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with specific usernames
        usernames = ["aaa", "bbb", "ccc"]
        for username in usernames:
            user_in = create_user_create_schema(
                email=f"{username}@example.com",
                username=username,
            )
            await user_service.create_user(user_in)

        # Get users sorted by username desc
        response = await client.get(
            "/api/v1/users/?sort_by=username&sort_order=desc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify reverse alphabetical order
        items = data["items"]
        usernames_returned = [user["username"] for user in items]

        # Check that our test users are in reverse alphabetical order
        test_users = [u for u in usernames_returned if u in ["aaa", "bbb", "ccc"]]
        assert test_users == sorted(test_users, reverse=True)

    async def test_sort_by_email_asc(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test sorting users by email in ascending order."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create users with specific emails
        emails = ["zzz@example.com", "aaa@example.com", "mmm@example.com"]
        for i, email in enumerate(emails):
            user_in = create_user_create_schema(
                email=email,
                username=f"email_sort_{i}",
            )
            await user_service.create_user(user_in)

        # Get users sorted by email asc
        response = await client.get(
            "/api/v1/users/?sort_by=email&sort_order=asc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify alphabetical order by email
        items = data["items"]
        emails_returned = [user["email"] for user in items]

        # Check that our test emails are in alphabetical order
        test_emails = [e for e in emails_returned if e in emails]
        assert test_emails == sorted(test_emails)


class TestUserListCombinedFilters:
    """Tests for combining multiple filters."""

    async def test_filter_active_and_superuser(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test filtering by both is_active and is_superuser."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create active superuser
        user_in = create_user_create_schema(
            email="active_super@example.com",
            username="active_super",
        )
        user = await user_service.create_user(user_in)
        user.is_superuser = True
        await db_session.commit()

        # Create inactive superuser
        user_in = create_user_create_schema(
            email="inactive_super@example.com",
            username="inactive_super",
        )
        user = await user_service.create_user(user_in)
        user.is_superuser = True
        user.is_active = False
        await db_session.commit()

        # Filter for active superusers only
        response = await client.get(
            "/api/v1/users/?is_active=true&is_superuser=true",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should be active superusers
        for user in data["items"]:
            assert user["is_active"] is True
            assert user["is_superuser"] is True

    async def test_filter_and_search(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test combining filter with search."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create active user with "test" in username
        await user_service.create_user(
            create_user_create_schema(
                email="test_active@example.com",
                username="test_active",
            )
        )

        # Create inactive user with "test" in username
        user_in = create_user_create_schema(
            email="test_inactive@example.com",
            username="test_inactive",
        )
        user = await user_service.create_user(user_in)
        user.is_active = False
        await db_session.commit()

        # Filter for active users with "test" in name
        response = await client.get(
            "/api/v1/users/?is_active=true&search=test",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should be active and contain "test"
        for user in data["items"]:
            assert user["is_active"] is True
            user_text = f"{user['username']} {user['email']} {user.get('full_name', '')}".lower()
            assert "test" in user_text

    async def test_filter_search_and_sort(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test combining filter, search, and sort."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create multiple active users with "dev" in username
        usernames = ["dev_charlie", "dev_alice", "dev_bob"]
        for username in usernames:
            await user_service.create_user(
                create_user_create_schema(
                    email=f"{username}@example.com",
                    username=username,
                )
            )

        # Filter active, search "dev", sort by username asc
        response = await client.get(
            "/api/v1/users/?is_active=true&search=dev&sort_by=username&sort_order=asc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all users are active and contain "dev"
        for user in data["items"]:
            assert user["is_active"] is True
            assert "dev" in user["username"].lower()

        # Verify sorting
        dev_users = [u["username"] for u in data["items"] if "dev" in u["username"]]
        assert dev_users == sorted(dev_users)

    async def test_all_filters_combined(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test using all filter options together."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create specific user matching all criteria
        user_in = create_user_create_schema(
            email="admin_test@example.com",
            username="admin_test",
        )
        user = await user_service.create_user(user_in)
        user.is_superuser = True
        await db_session.commit()

        # Create user that doesn't match
        user_in = create_user_create_schema(
            email="regular@example.com",
            username="regular",
        )
        await user_service.create_user(user_in)

        # Apply all filters
        response = await client.get(
            "/api/v1/users/?is_active=true&is_superuser=true&search=admin&sort_by=username&sort_order=asc",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # All returned users should match all criteria
        for user in data["items"]:
            assert user["is_active"] is True
            assert user["is_superuser"] is True
            user_text = f"{user['username']} {user['email']}".lower()
            assert "admin" in user_text


class TestUserListPaginationWithFilters:
    """Tests for pagination combined with filters."""

    async def test_pagination_with_filter(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that pagination works with filters."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 10 active users
        for i in range(10):
            user_in = create_user_create_schema(
                email=f"page{i}@example.com",
                username=f"page{i}",
            )
            await user_service.create_user(user_in)

        # Get first page with filter
        response = await client.get(
            "/api/v1/users/?is_active=true&page=1&size=5",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should have pagination info
        assert "total" in data
        assert "page" in data
        assert "size" in data
        assert "pages" in data

        # Should return 5 items
        assert len(data["items"]) == 5
        assert data["page"] == 1
        assert data["size"] == 5

        # All should be active
        for user in data["items"]:
            assert user["is_active"] is True

    async def test_pagination_with_search(
        self,
        client: AsyncClient,
        superuser_auth_headers: dict,
        db_session: AsyncSession,
    ):
        """Test that pagination works with search."""
        from app.services.user import UserService

        user_service = UserService(db_session)

        # Create 8 users with "search" in username
        for i in range(8):
            user_in = create_user_create_schema(
                email=f"search{i}@example.com",
                username=f"search_user_{i}",
            )
            await user_service.create_user(user_in)

        # Get first page with search
        response = await client.get(
            "/api/v1/users/?search=search&page=1&size=5",
            headers=superuser_auth_headers,
        )

        assert response.status_code == 200
        data = response.json()

        # Should have at least 8 matching users
        assert data["total"] >= 8

        # Should return 5 items on first page
        assert len(data["items"]) == 5

        # All should contain "search"
        for user in data["items"]:
            user_text = f"{user['username']} {user['email']}".lower()
            assert "search" in user_text


class TestUserListAccessControl:
    """Tests for access control on user list endpoint."""

    async def test_list_users_requires_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that regular users cannot list users."""
        response = await client.get(
            "/api/v1/users/",
            headers=auth_headers,
        )

        assert response.status_code == 403

    async def test_list_users_requires_authentication(
        self,
        client: AsyncClient,
    ):
        """Test that unauthenticated users cannot list users."""
        response = await client.get("/api/v1/users/")

        assert response.status_code == 401

    async def test_filtered_list_requires_superuser(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """Test that filters still require superuser access."""
        response = await client.get(
            "/api/v1/users/?is_active=true&search=test",
            headers=auth_headers,
        )

        assert response.status_code == 403
