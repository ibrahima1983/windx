"""Integration tests for enhanced error handling in admin entry endpoints.

This module tests the enhanced error handling implemented in the admin entry
save endpoint, specifically testing ValidationException and generic exception
handling with structured error responses.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock, patch

from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.core.exceptions import ValidationException


@pytest.fixture
async def simple_manufacturing_type(db_session: AsyncSession) -> ManufacturingType:
    """Create a simple manufacturing type for testing."""
    from decimal import Decimal
    import uuid

    # Use a unique name to avoid conflicts
    unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"

    mfg_type = ManufacturingType(
        name=unique_name,
        description="Test window type for error handling tests",
        base_price=Decimal("200.00"),
        base_weight=Decimal("25.00"),
        is_active=True,
    )

    db_session.add(mfg_type)
    await db_session.commit()
    await db_session.refresh(mfg_type)

    return mfg_type


class TestEnhancedErrorHandling:
    """Test enhanced error handling in admin entry endpoints."""

    @pytest.mark.asyncio
    async def test_save_profile_validation_error_with_field_errors(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that ValidationException with field_errors returns structured error response."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Mock the EntryService to raise ValidationException with field_errors
        field_errors = {
            "renovation": "Renovation is only applicable for frame types",
            "sash_overlap": "Sash overlap is only applicable for sash types",
        }
        validation_exception = ValidationException(
            message="Business rule validation failed", field_errors=field_errors
        )

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = validation_exception

            # Attempt to save profile data with all required fields
            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "sash",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
                "renovation": True,  # Invalid for sash type
                "sash_overlap": 8,  # Valid for sash type
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            # Assert structured error response
            assert response.status_code == 422
            error_data = response.json()

            # Check error structure
            assert "detail" in error_data
            detail = error_data["detail"]
            assert detail["message"] == "Business rule validation failed"
            assert detail["field_errors"] == field_errors
            assert detail["error_type"] == "validation_error"

    @pytest.mark.asyncio
    async def test_save_profile_validation_error_without_field_errors(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that ValidationException without field_errors returns generic validation error."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Mock the EntryService to raise ValidationException without field_errors
        validation_exception = ValidationException(message="Generic validation error")

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = validation_exception

            # Attempt to save profile data with all required fields
            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "frame",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            # Assert generic validation error response
            assert response.status_code == 422
            error_data = response.json()

            # Check error structure
            assert "detail" in error_data
            detail = error_data["detail"]
            assert (
                detail["message"] == "422: Generic validation error"
            )  # HTTPException includes status code
            assert detail["error_type"] == "validation_error"
            # field_errors should not be present for generic validation errors
            assert "field_errors" not in detail

    @pytest.mark.asyncio
    async def test_save_profile_unexpected_error_handling(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that unexpected exceptions return structured server error response."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Mock the EntryService to raise an unexpected exception
        unexpected_exception = RuntimeError("Database connection failed")

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = unexpected_exception

            # Attempt to save profile data with all required fields
            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "frame",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            # Assert server error response
            assert response.status_code == 500
            error_data = response.json()

            # Check error structure
            assert "detail" in error_data
            detail = error_data["detail"]
            assert (
                detail["message"] == "An unexpected error occurred while saving the configuration"
            )
            assert detail["error_type"] == "server_error"

    @pytest.mark.asyncio
    async def test_save_profile_unexpected_error_with_field_errors_attribute(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that unexpected exceptions with field_errors attribute are logged properly."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create a custom exception with field_errors attribute
        class CustomException(Exception):
            def __init__(self, message):
                super().__init__(message)
                self.field_errors = {"custom_field": "Custom error message"}

        unexpected_exception = CustomException("Custom exception with field errors")

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = unexpected_exception

            # Attempt to save profile data with all required fields
            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "frame",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            # Assert server error response (field_errors should not be exposed for non-ValidationException)
            assert response.status_code == 500
            error_data = response.json()

            # Check error structure
            assert "detail" in error_data
            detail = error_data["detail"]
            assert (
                detail["message"] == "An unexpected error occurred while saving the configuration"
            )
            assert detail["error_type"] == "server_error"
            # field_errors should not be exposed for unexpected exceptions
            assert "field_errors" not in detail

    @pytest.mark.asyncio
    async def test_save_profile_success_case_still_works(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that successful save operations still work after error handling changes."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Save valid profile data (this should work without mocking)
        profile_data = {
            "manufacturing_type_id": simple_manufacturing_type.id,
            "name": "Successful Test Configuration",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Test800",
        }

        response = await client.post(
            "/api/v1/admin/entry/profile/save",
            json=profile_data,
            headers={"Authorization": f"Bearer {token}"},
        )

        # Assert successful response
        assert response.status_code == 201
        configuration = response.json()
        assert configuration["name"] == "Successful Test Configuration"
        assert configuration["manufacturing_type_id"] == simple_manufacturing_type.id

    @pytest.mark.asyncio
    async def test_error_logging_behavior(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
        caplog,
    ):
        """Test that errors are properly logged with appropriate detail levels."""
        import logging

        # Set logging level to capture error logs
        caplog.set_level(logging.ERROR)

        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Test ValidationException logging
        field_errors = {"test_field": "Test error message"}
        validation_exception = ValidationException(
            message="Test validation error", field_errors=field_errors
        )

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = validation_exception

            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "frame",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 422

            # Check that validation error was logged
            validation_logs = [
                record
                for record in caplog.records
                if "Save Profile Validation Error" in record.message
            ]
            assert len(validation_logs) > 0

            # Check that field errors were logged
            field_error_logs = [
                record for record in caplog.records if "Field Errors" in record.message
            ]
            assert len(field_error_logs) > 0

        # Clear logs for next test
        caplog.clear()

        # Test unexpected exception logging
        unexpected_exception = RuntimeError("Test runtime error")

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = unexpected_exception

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 500

            # Check that unexpected error was logged
            unexpected_logs = [
                record
                for record in caplog.records
                if "Save Profile Unexpected Error" in record.message
            ]
            assert len(unexpected_logs) > 0

            # Check that error type was logged
            error_type_logs = [
                record for record in caplog.records if "Error Type" in record.message
            ]
            assert len(error_type_logs) > 0

    @pytest.mark.asyncio
    async def test_validation_exception_field_errors_structure(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test that ValidationException field_errors are properly structured in response."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create complex field errors structure
        field_errors = {
            "width": "Width must be between 24 and 96 inches",
            "height": "Height must be between 24 and 120 inches",
            "type": "Type is required",
            "material": "Material selection is invalid for this type",
            "opening_system": "Opening system must be compatible with frame type",
        }

        validation_exception = ValidationException(
            message="Multiple validation errors occurred", field_errors=field_errors
        )

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = validation_exception

            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "frame",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
                "width": 200,  # Invalid - too wide
                "height": 150,  # Invalid - too tall
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 422
            error_data = response.json()

            # Verify complete field_errors structure is preserved
            detail = error_data["detail"]
            assert detail["field_errors"] == field_errors
            assert len(detail["field_errors"]) == 5

            # Verify each field error is present
            for field_name, error_message in field_errors.items():
                assert detail["field_errors"][field_name] == error_message

    @pytest.mark.asyncio
    async def test_validation_exception_empty_field_errors(
        self,
        client: AsyncClient,
        test_superuser_with_rbac: User,
        simple_manufacturing_type: ManufacturingType,
    ):
        """Test ValidationException with empty field_errors dict is handled as generic error."""
        # Login as superuser
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "username": test_superuser_with_rbac.username,
                "password": "AdminPassword123!",
            },
        )
        assert login_response.status_code == 200
        token = login_response.json()["access_token"]

        # Create ValidationException with empty field_errors
        validation_exception = ValidationException(
            message="Validation failed",
            field_errors={},  # Empty dict
        )

        with patch("app.services.entry.EntryService.save_profile_configuration") as mock_save:
            mock_save.side_effect = validation_exception

            profile_data = {
                "manufacturing_type_id": simple_manufacturing_type.id,
                "name": "Test Configuration",
                "type": "frame",
                "material": "Aluminum",  # Required field
                "opening_system": "Casement",  # Required field
                "system_series": "Test800",  # Required field
            }

            response = await client.post(
                "/api/v1/admin/entry/profile/save",
                json=profile_data,
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 422
            error_data = response.json()

            # Should be treated as generic validation error (no field_errors in response)
            detail = error_data["detail"]
            assert (
                detail["message"] == "422: Validation failed"
            )  # HTTPException includes status code
            assert detail["error_type"] == "validation_error"
            assert "field_errors" not in detail  # Empty dict should not be included
