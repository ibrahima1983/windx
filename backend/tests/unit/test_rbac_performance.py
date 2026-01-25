"""Performance tests for Casbin and customer operations.

This module tests performance characteristics of the RBAC system including:
- Casbin policy evaluation performance with large policy sets
- Customer lookup performance with large datasets
- RBACQueryFilter performance impact
- Configuration filtering performance by customer
- Impact of customer auto-creation on response times
- Privilege object evaluation performance

Requirements: 11.1, 11.2, 11.4, 11.5
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.rbac import Permission, Privilege, RBACQueryFilter, Role
from app.models.customer import Customer
from app.models.user import User
from app.services.rbac import RBACService


class TestCasbinPerformance:
    """Test Casbin policy evaluation performance."""

    @pytest.fixture
    def rbac_service(self, mock_db):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(mock_db)
            service.enforcer = MagicMock()
            return service

    @pytest.fixture
    def users(self) -> list[User]:
        """Create multiple test users for performance testing."""
        users = []
        for i in range(100):
            user = User()
            user.id = i + 1
            user.email = f"user{i}@example.com"
            user.username = f"user{i}"
            user.role = Role.CUSTOMER.value if i % 4 != 0 else Role.SALESMAN.value
            users.append(user)
        return users

    @pytest.mark.asyncio
    async def test_casbin_policy_evaluation_performance_small_set(self, rbac_service, users):
        """Test Casbin policy evaluation performance with small policy set."""
        # Mock enforcer to return True quickly
        rbac_service.enforcer.enforce.return_value = True

        start_time = time.time()

        # Test 100 permission checks
        for user in users[:10]:  # Small set
            for resource in ["configuration", "quote", "order"]:
                for action in ["read", "create", "update"]:
                    await rbac_service.check_permission(user, resource, action)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 90 checks (10 users * 3 resources * 3 actions) quickly
        assert duration < 1.0, f"Small policy set took {duration:.3f}s, expected < 1.0s"

        # Verify all checks were made
        assert rbac_service.enforcer.enforce.call_count == 90

    @pytest.mark.asyncio
    async def test_casbin_policy_evaluation_performance_large_set(self, rbac_service, users):
        """Test Casbin policy evaluation performance with large policy set."""

        # Mock enforcer to simulate realistic policy evaluation time
        def mock_enforce(*args):
            time.sleep(0.001)  # Simulate 1ms policy evaluation
            return True

        rbac_service.enforcer.enforce.side_effect = mock_enforce

        start_time = time.time()

        # Test 900 permission checks (100 users * 3 resources * 3 actions)
        for user in users:
            for resource in ["configuration", "quote", "order"]:
                for action in ["read", "create", "update"]:
                    await rbac_service.check_permission(user, resource, action)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 900 checks in reasonable time (allowing for 1ms per check + overhead)
        assert duration < 5.0, f"Large policy set took {duration:.3f}s, expected < 5.0s"

        # Verify all checks were made
        assert rbac_service.enforcer.enforce.call_count == 900

    @pytest.mark.asyncio
    async def test_casbin_caching_performance_improvement(self, rbac_service, users):
        """Test that caching improves performance for repeated checks."""
        rbac_service.enforcer.enforce.return_value = True

        user = users[0]

        # First check - should hit enforcer
        start_time = time.time()
        result1 = await rbac_service.check_permission(user, "configuration", "read")
        first_check_time = time.time() - start_time

        # Second check - should hit cache
        start_time = time.time()
        result2 = await rbac_service.check_permission(user, "configuration", "read")
        second_check_time = time.time() - start_time

        assert result1 is True
        assert result2 is True

        # Cache hit should be significantly faster
        assert second_check_time < first_check_time / 2, (
            f"Cache hit ({second_check_time:.6f}s) not faster than first check ({first_check_time:.6f}s)"
        )

        # Only one enforcer call should have been made
        assert rbac_service.enforcer.enforce.call_count == 1

    @pytest.mark.asyncio
    async def test_privilege_evaluation_performance(self, rbac_service, users):
        """Test privilege object evaluation performance."""
        # Create privilege object
        privilege = Privilege(
            roles=[Role.CUSTOMER, Role.SALESMAN], permission=Permission("configuration", "read")
        )

        # Mock permission check to return quickly
        rbac_service.check_permission = AsyncMock(return_value=True)

        start_time = time.time()

        # Test privilege evaluation for multiple users
        for user in users[:50]:  # Test with 50 users
            await rbac_service.check_privilege(user, privilege)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 50 privilege evaluations quickly
        assert duration < 1.0, f"Privilege evaluation took {duration:.3f}s, expected < 1.0s"

        # Verify permission checks were made
        assert rbac_service.check_permission.call_count == 50


class TestCustomerLookupPerformance:
    """Test customer lookup performance with large datasets."""

    @pytest.fixture
    def rbac_service(self, mock_db):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(mock_db)
            service.enforcer = MagicMock()
            return service

    @pytest.fixture
    def customers(self) -> list[Customer]:
        """Create multiple test customers for performance testing."""
        customers = []
        for i in range(1000):
            customer = Customer()
            customer.id = i + 1
            customer.email = f"customer{i}@example.com"
            customer.contact_person = f"Customer {i}"
            customer.is_active = True
            customers.append(customer)
        return customers

    @pytest.mark.asyncio
    async def test_customer_lookup_by_email_performance(self, rbac_service, customers, mock_db):
        """Test customer lookup by email performance."""

        # Mock database query to simulate realistic lookup time
        def mock_execute(stmt):
            time.sleep(0.001)  # Simulate 1ms database query
            result = MagicMock()
            result.scalar_one_or_none.return_value = customers[0]
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        start_time = time.time()

        # Test 100 customer lookups
        for i in range(100):
            await rbac_service._find_customer_by_email(f"customer{i}@example.com")

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 100 lookups in reasonable time
        assert duration < 2.0, f"Customer lookups took {duration:.3f}s, expected < 2.0s"

        # Verify database queries were made
        assert mock_db.execute.call_count == 100

    @pytest.mark.asyncio
    async def test_accessible_customers_caching_performance(self, rbac_service, mock_db):
        """Test accessible customers caching performance."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value

        # Mock database query
        def mock_execute(stmt):
            result = MagicMock()
            result.scalar_one_or_none.return_value = 123
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute)

        # First call - should hit database
        start_time = time.time()
        result1 = await rbac_service.get_accessible_customers(user)
        first_call_time = time.time() - start_time

        # Second call - should hit cache
        start_time = time.time()
        result2 = await rbac_service.get_accessible_customers(user)
        second_call_time = time.time() - start_time

        assert result1 == result2

        # Cache hit should be significantly faster
        assert second_call_time < first_call_time / 2, (
            f"Cache hit ({second_call_time:.6f}s) not faster than first call ({first_call_time:.6f}s)"
        )

        # Only one database query should have been made
        assert mock_db.execute.call_count == 1

    @pytest.mark.asyncio
    async def test_customer_auto_creation_performance_impact(self, rbac_service, mock_db):
        """Test performance impact of customer auto-creation."""
        users = []
        for i in range(50):
            user = User()
            user.id = i + 1
            user.email = f"newuser{i}@example.com"
            user.username = f"newuser{i}"
            user.full_name = f"New User {i}"
            user.role = Role.CUSTOMER.value
            users.append(user)

        # Mock database operations
        rbac_service._find_customer_by_email = AsyncMock(return_value=None)  # No existing customer
        rbac_service.commit = AsyncMock()
        rbac_service.refresh = AsyncMock()

        def mock_add(customer):
            customer.id = len(users) + 1

        mock_db.add = MagicMock(side_effect=mock_add)

        start_time = time.time()

        # Test customer auto-creation for 50 users
        for user in users:
            await rbac_service.get_or_create_customer_for_user(user)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 50 customer creations in reasonable time
        assert duration < 3.0, f"Customer auto-creation took {duration:.3f}s, expected < 3.0s"

        # Verify all operations were performed
        assert mock_db.add.call_count == 50
        assert rbac_service.commit.call_count == 50


class TestRBACQueryFilterPerformance:
    """Test RBACQueryFilter performance impact."""

    @pytest.fixture
    def user(self):
        """Create test user."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value
        return user

    @pytest.fixture
    def superadmin_user(self):
        """Create superadmin user."""
        user = User()
        user.id = 2
        user.email = "admin@example.com"
        user.role = Role.SUPERADMIN.value
        return user

    @pytest.mark.asyncio
    async def test_configuration_filtering_performance_regular_user(self, user):
        """Test configuration filtering performance for regular user."""
        from sqlalchemy import select

        from app.models.configuration import Configuration

        # Mock query
        query = select(Configuration)

        # Mock RBACService.get_accessible_customers to simulate database lookup
        with patch("app.services.rbac.RBACService") as mock_rbac_class:
            mock_rbac = MagicMock()
            mock_rbac.get_accessible_customers = AsyncMock(return_value=[1, 2, 3])
            mock_rbac_class.return_value = mock_rbac

            with patch("app.database.connection.get_session_maker") as mock_session_maker:
                mock_session = AsyncMock()
                mock_session_maker.return_value.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_maker.return_value.return_value.__aexit__ = AsyncMock(
                    return_value=None
                )

                start_time = time.time()

                # Test filtering 100 times
                for _ in range(100):
                    filtered_query = await RBACQueryFilter.filter_configurations(query, user)

                end_time = time.time()
                duration = end_time - start_time

                # Should complete 100 filter operations quickly
                assert duration < 2.0, f"Query filtering took {duration:.3f}s, expected < 2.0s"

    @pytest.mark.asyncio
    async def test_configuration_filtering_performance_superadmin(self, superadmin_user):
        """Test configuration filtering performance for superadmin (no filtering)."""
        from sqlalchemy import select

        from app.models.configuration import Configuration

        # Mock query
        query = select(Configuration)

        start_time = time.time()

        # Test filtering 1000 times (should be very fast for superadmin)
        for _ in range(1000):
            filtered_query = await RBACQueryFilter.filter_configurations(query, superadmin_user)

        end_time = time.time()
        duration = end_time - start_time

        # Should complete 1000 filter operations very quickly (no database access)
        assert duration < 0.5, f"Superadmin query filtering took {duration:.3f}s, expected < 0.5s"

    @pytest.mark.asyncio
    async def test_multiple_filter_types_performance(self, user):
        """Test performance when applying multiple filter types."""
        from sqlalchemy import select

        from app.models.configuration import Configuration
        from app.models.order import Order
        from app.models.quote import Quote

        queries = [select(Configuration), select(Quote), select(Order)]

        # Mock RBACService
        with patch("app.services.rbac.RBACService") as mock_rbac_class:
            mock_rbac = MagicMock()
            mock_rbac.get_accessible_customers = AsyncMock(return_value=[1, 2, 3])
            mock_rbac_class.return_value = mock_rbac

            with patch("app.database.connection.get_session_maker") as mock_session_maker:
                mock_session = AsyncMock()
                mock_session_maker.return_value.return_value.__aenter__ = AsyncMock(
                    return_value=mock_session
                )
                mock_session_maker.return_value.return_value.__aexit__ = AsyncMock(
                    return_value=None
                )

                start_time = time.time()

                # Test filtering different query types
                for _ in range(50):
                    await RBACQueryFilter.filter_configurations(queries[0], user)
                    await RBACQueryFilter.filter_quotes(queries[1], user)
                    await RBACQueryFilter.filter_orders(queries[2], user)

                end_time = time.time()
                duration = end_time - start_time

                # Should complete 150 filter operations (50 * 3 types) in reasonable time
                assert duration < 3.0, (
                    f"Multiple filter types took {duration:.3f}s, expected < 3.0s"
                )


class TestCachePerformanceOptimization:
    """Test cache performance optimization."""

    @pytest.fixture
    def rbac_service(self, mock_db):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(mock_db)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_cache_hit_ratio_performance(self, rbac_service):
        """Test cache hit ratio and performance improvement."""
        user = User()
        user.id = 1
        user.email = "test@example.com"
        user.role = Role.CUSTOMER.value

        rbac_service.enforcer.enforce.return_value = True

        # Warm up cache with initial requests
        resources = ["configuration", "quote", "order"]
        actions = ["read", "create", "update", "delete"]

        # First pass - populate cache
        start_time = time.time()
        for resource in resources:
            for action in actions:
                await rbac_service.check_permission(user, resource, action)
        first_pass_time = time.time() - start_time

        # Second pass - should hit cache
        start_time = time.time()
        for resource in resources:
            for action in actions:
                await rbac_service.check_permission(user, resource, action)
        second_pass_time = time.time() - start_time

        # Cache hits should be significantly faster
        assert second_pass_time < first_pass_time / 3, (
            f"Cache hits ({second_pass_time:.6f}s) not significantly faster than misses ({first_pass_time:.6f}s)"
        )

        # Verify cache statistics
        stats = rbac_service.get_cache_stats()
        assert stats["permission_cache_size"] == 12  # 3 resources * 4 actions

        # Only initial requests should have hit the enforcer
        assert rbac_service.enforcer.enforce.call_count == 12

    @pytest.mark.asyncio
    async def test_cache_expiration_performance(self, rbac_service):
        """Test cache expiration and refresh performance."""
        user = User()
        user.id = 1
        user.email = "test@example.com"

        rbac_service.enforcer.enforce.return_value = True

        # Populate cache
        await rbac_service.check_permission(user, "configuration", "read")

        # Verify cache is not expired initially
        assert not rbac_service.is_cache_expired(max_age_minutes=30)

        # Verify cache is expired with very short max age
        assert rbac_service.is_cache_expired(max_age_minutes=0)

        # Test cache statistics
        stats = rbac_service.get_cache_stats()
        assert stats["permission_cache_size"] == 1
        assert stats["cache_age_minutes"] >= 0

    @pytest.mark.asyncio
    async def test_concurrent_cache_access_performance(self, rbac_service):
        """Test performance under concurrent cache access."""
        users = []
        for i in range(10):
            user = User()
            user.id = i + 1
            user.email = f"user{i}@example.com"
            user.role = Role.CUSTOMER.value
            users.append(user)

        rbac_service.enforcer.enforce.return_value = True

        async def check_permissions_for_user(user):
            """Check multiple permissions for a user."""
            for resource in ["configuration", "quote"]:
                for action in ["read", "create"]:
                    await rbac_service.check_permission(user, resource, action)

        start_time = time.time()

        # Simulate concurrent access
        tasks = [check_permissions_for_user(user) for user in users]
        await asyncio.gather(*tasks)

        end_time = time.time()
        duration = end_time - start_time

        # Should handle concurrent access efficiently
        assert duration < 2.0, f"Concurrent cache access took {duration:.3f}s, expected < 2.0s"

        # Verify cache contains entries for all users
        stats = rbac_service.get_cache_stats()
        assert stats["permission_cache_size"] == 40  # 10 users * 2 resources * 2 actions


class TestMemoryUsageOptimization:
    """Test memory usage optimization in RBAC operations."""

    @pytest.fixture
    def rbac_service(self, mock_db):
        """Create RBAC service with mocked database."""
        with patch("casbin.Enforcer"):
            service = RBACService(mock_db)
            service.enforcer = MagicMock()
            return service

    @pytest.mark.asyncio
    async def test_cache_memory_usage_bounds(self, rbac_service):
        """Test that cache memory usage stays within reasonable bounds."""
        users = []
        for i in range(100):
            user = User()
            user.id = i + 1
            user.email = f"user{i}@example.com"
            user.role = Role.CUSTOMER.value
            users.append(user)

        rbac_service.enforcer.enforce.return_value = True

        # Populate cache with many entries
        for user in users:
            for resource in ["configuration", "quote", "order"]:
                for action in ["read", "create"]:
                    await rbac_service.check_permission(user, resource, action)

        # Check cache size
        stats = rbac_service.get_cache_stats()

        # Should have reasonable cache size (100 users * 3 resources * 2 actions = 600 entries)
        assert stats["permission_cache_size"] == 600
        assert stats["customer_cache_size"] <= 100  # At most one entry per user

        # Cache should be manageable in size
        assert len(rbac_service._permission_cache) <= 1000
        assert len(rbac_service._customer_cache) <= 200

    @pytest.mark.asyncio
    async def test_cache_cleanup_performance(self, rbac_service):
        """Test cache cleanup performance."""
        # Populate cache with entries
        for i in range(1000):
            rbac_service._permission_cache[f"key_{i}"] = True
            if i % 10 == 0:
                rbac_service._customer_cache[i] = [1, 2, 3]

        # Measure cache cleanup time
        start_time = time.time()
        rbac_service.clear_cache()
        cleanup_time = time.time() - start_time

        # Cache cleanup should be very fast
        assert cleanup_time < 0.1, f"Cache cleanup took {cleanup_time:.6f}s, expected < 0.1s"

        # Verify cache is empty
        stats = rbac_service.get_cache_stats()
        assert stats["permission_cache_size"] == 0
        assert stats["customer_cache_size"] == 0
