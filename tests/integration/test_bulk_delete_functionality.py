"""Integration tests for bulk delete functionality.

This module tests the bulk delete feature including:
- Backend bulk delete service method
- API endpoint for bulk deletion
- Error handling for missing configurations
- Permission validation
"""

import json
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.configuration import Configuration
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.services.entry import EntryService


class TestBulkDeleteFunctionality:
    """Test bulk delete functionality."""

    @pytest.fixture
    async def sample_configurations(
        self, db_session: AsyncSession, test_superuser: User
    ) -> list[Configuration]:
        """Create sample configurations for testing."""
        # Commit the test_superuser to ensure it's available for RBAC
        await db_session.commit()

        # Create a manufacturing type first
        from app.models.manufacturing_type import ManufacturingType
        import uuid

        # Use unique name to avoid conflicts
        unique_name = f"Test Manufacturing Type {uuid.uuid4().hex[:8]}"

        manufacturing_type = ManufacturingType(
            name=unique_name,
            description="Test type for bulk delete",
            base_price=200.00,
            base_weight=10.0,
            is_active=True,
        )
        db_session.add(manufacturing_type)
        await db_session.commit()
        await db_session.refresh(manufacturing_type)

        configurations = []

        for i in range(5):
            config = Configuration(
                manufacturing_type_id=manufacturing_type.id,
                customer_id=None,  # Admin-created configurations
                name=f"Test Configuration {i + 1}",
                description=f"Test configuration for bulk delete {i + 1}",
                status="draft",
                base_price=200.00,
                total_price=250.00 + (i * 10),  # Varying prices
                calculated_weight=10.0 + i,
                calculated_technical_data={"test": f"value_{i}"},
            )
            db_session.add(config)
            configurations.append(config)

        await db_session.commit()

        # Refresh to get IDs
        for config in configurations:
            await db_session.refresh(config)

        return configurations

    @pytest.mark.asyncio
    async def test_bulk_delete_service_success(
        self,
        db_session: AsyncSession,
        sample_configurations: list[Configuration],
        test_superuser: User,
    ):
        """Test successful bulk delete via service layer."""
        entry_service = EntryService(db_session)

        # Get IDs of first 3 configurations
        config_ids = [config.id for config in sample_configurations[:3]]

        # Perform bulk delete
        result = await entry_service.bulk_delete_profile_configurations(config_ids, test_superuser)

        # Verify result
        assert result["success_count"] == 3
        assert result["error_count"] == 0
        assert result["total_requested"] == 3
        assert len(result["errors"]) == 0

        # Verify configurations are deleted from database
        from sqlalchemy import select

        stmt = select(Configuration).where(Configuration.id.in_(config_ids))
        result_db = await db_session.execute(stmt)
        remaining_configs = result_db.scalars().all()
        assert len(remaining_configs) == 0

        # Verify other configurations still exist
        remaining_ids = [config.id for config in sample_configurations[3:]]
        stmt = select(Configuration).where(Configuration.id.in_(remaining_ids))
        result_db = await db_session.execute(stmt)
        existing_configs = result_db.scalars().all()
        assert len(existing_configs) == 2

    @pytest.mark.asyncio
    async def test_bulk_delete_service_partial_success(
        self,
        db_session: AsyncSession,
        sample_configurations: list[Configuration],
        test_superuser: User,
    ):
        """Test bulk delete with some missing configurations."""
        entry_service = EntryService(db_session)

        # Mix of existing and non-existing IDs
        existing_ids = [sample_configurations[0].id, sample_configurations[1].id]
        non_existing_ids = [99999, 99998]
        mixed_ids = existing_ids + non_existing_ids

        # Perform bulk delete
        result = await entry_service.bulk_delete_profile_configurations(mixed_ids, test_superuser)

        # Verify result
        assert result["success_count"] == 2
        assert result["error_count"] == 2
        assert result["total_requested"] == 4
        assert len(result["errors"]) == 2
        assert "Configuration 99999 not found" in result["errors"]
        assert "Configuration 99998 not found" in result["errors"]

        # Verify existing configurations are deleted
        from sqlalchemy import select

        stmt = select(Configuration).where(Configuration.id.in_(existing_ids))
        result_db = await db_session.execute(stmt)
        deleted_configs = result_db.scalars().all()
        assert len(deleted_configs) == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_service_empty_list(
        self, db_session: AsyncSession, test_superuser: User
    ):
        """Test bulk delete with empty list."""
        entry_service = EntryService(db_session)

        # Perform bulk delete with empty list
        result = await entry_service.bulk_delete_profile_configurations([], test_superuser)

        # Verify result
        assert result["success_count"] == 0
        assert result["error_count"] == 0
        assert result["total_requested"] == 0
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_api_endpoint_success(
        self,
        client: AsyncClient,
        sample_configurations: list[Configuration],
        superuser_auth_headers: dict[str, str],
    ):
        """Test bulk delete API endpoint with successful deletion."""
        # Get IDs of first 3 configurations
        config_ids = [config.id for config in sample_configurations[:3]]

        # Make API request
        response = await client.request(
            "DELETE",
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=config_ids,
            headers=superuser_auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        result = response.json()

        assert result["success_count"] == 3
        assert result["error_count"] == 0
        assert result["total_requested"] == 3
        assert len(result["errors"]) == 0

    @pytest.mark.asyncio
    async def test_bulk_delete_api_endpoint_empty_list(
        self, client: AsyncClient, superuser_auth_headers: dict[str, str]
    ):
        """Test bulk delete API endpoint with empty list."""
        # Make API request with empty list
        response = await client.request(
            "DELETE",
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=[],
            headers=superuser_auth_headers,
        )

        # Verify response
        assert response.status_code == 400
        result = response.json()
        assert "No configuration IDs provided" in result["detail"]

    @pytest.mark.asyncio
    async def test_bulk_delete_api_endpoint_unauthorized(
        self, client: AsyncClient, sample_configurations: list[Configuration]
    ):
        """Test bulk delete API endpoint without authentication."""
        config_ids = [sample_configurations[0].id]

        # Make API request without auth headers
        response = await client.request(
            "DELETE", "/api/v1/admin/entry/profile/configurations/bulk", json=config_ids
        )

        # Verify unauthorized response
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_bulk_delete_api_endpoint_partial_success(
        self,
        client: AsyncClient,
        sample_configurations: list[Configuration],
        superuser_auth_headers: dict[str, str],
    ):
        """Test bulk delete API endpoint with mixed existing/non-existing IDs."""
        # Mix of existing and non-existing IDs
        existing_ids = [sample_configurations[0].id, sample_configurations[1].id]
        non_existing_ids = [99999, 99998]
        mixed_ids = existing_ids + non_existing_ids

        # Make API request
        response = await client.request(
            "DELETE",
            "/api/v1/admin/entry/profile/configurations/bulk",
            json=mixed_ids,
            headers=superuser_auth_headers,
        )

        # Verify response
        assert response.status_code == 200
        result = response.json()

        assert result["success_count"] == 2
        assert result["error_count"] == 2
        assert result["total_requested"] == 4
        assert len(result["errors"]) == 2

    @pytest.mark.asyncio
    async def test_bulk_delete_performance(
        self,
        db_session: AsyncSession,
        sample_configurations: list[Configuration],
        test_superuser: User,
    ):
        """Test bulk delete performance with larger dataset."""
        import time
        import uuid

        # Use the manufacturing type from sample configurations
        manufacturing_type_id = sample_configurations[0].manufacturing_type_id

        # Create 15 additional configurations for performance test (we already have 5 from sample_configurations)
        configurations = []
        for i in range(15):
            config = Configuration(
                manufacturing_type_id=manufacturing_type_id,
                customer_id=None,
                name=f"Performance Test Config {i + 1} {uuid.uuid4().hex[:6]}",
                description=f"Performance test configuration {i + 1}",
                status="draft",
                base_price=200.00,
                total_price=250.00 + i,
                calculated_weight=10.0 + i,
                calculated_technical_data={"test": f"perf_value_{i}"},
            )
            db_session.add(config)
            configurations.append(config)

        await db_session.commit()

        # Refresh to get IDs
        for config in configurations:
            await db_session.refresh(config)

        # Combine sample configurations with new ones for total of 20
        all_configs = sample_configurations + configurations
        config_ids = [config.id for config in all_configs]

        # Measure bulk delete performance
        entry_service = EntryService(db_session)
        start_time = time.time()

        result = await entry_service.bulk_delete_profile_configurations(config_ids, test_superuser)

        end_time = time.time()
        execution_time = end_time - start_time

        # Verify all configurations were deleted
        assert result["success_count"] == 20
        assert result["error_count"] == 0

        # Performance should be reasonable (less than 2 seconds for 20 items)
        assert execution_time < 2.0, (
            f"Bulk delete took {execution_time:.2f} seconds, expected < 2.0"
        )

        print(f"✅ Bulk delete of 20 configurations completed in {execution_time:.3f} seconds")

    @pytest.mark.asyncio
    async def test_bulk_delete_maintains_data_integrity(
        self,
        db_session: AsyncSession,
        sample_configurations: list[Configuration],
        test_superuser: User,
    ):
        """Test that bulk delete maintains database integrity."""
        entry_service = EntryService(db_session)

        # Get initial count of all configurations
        from sqlalchemy import select, func

        stmt = select(func.count(Configuration.id))
        result = await db_session.execute(stmt)
        initial_count = result.scalar()

        # Delete first 2 configurations
        config_ids = [sample_configurations[0].id, sample_configurations[1].id]
        delete_result = await entry_service.bulk_delete_profile_configurations(
            config_ids, test_superuser
        )

        # Verify deletion result
        assert delete_result["success_count"] == 2

        # Verify final count
        result = await db_session.execute(stmt)
        final_count = result.scalar()

        assert final_count == initial_count - 2

        # Verify specific configurations are gone
        stmt = select(Configuration).where(Configuration.id.in_(config_ids))
        result = await db_session.execute(stmt)
        deleted_configs = result.scalars().all()
        assert len(deleted_configs) == 0

        # Verify other configurations still exist
        remaining_ids = [config.id for config in sample_configurations[2:]]
        stmt = select(Configuration).where(Configuration.id.in_(remaining_ids))
        result = await db_session.execute(stmt)
        remaining_configs = result.scalars().all()
        assert len(remaining_configs) == 3
