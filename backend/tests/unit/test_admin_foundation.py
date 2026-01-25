"""Unit tests for admin foundation components.

This module tests the admin utilities, type definitions, and helper functions
that provide the foundation for admin endpoints.

Features:
    - Query parameter validation
    - Form parameter validation
    - Admin context generation
    - Feature flag checking
    - Redirect response building
    - Validation error formatting
    - Form data processing
"""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, ValidationError
from starlette.requests import Request

from app.api.admin_utils import (
    FormDataProcessor,
    build_redirect_response,
    check_feature_flag,
    format_validation_errors,
)
from app.api.deps import get_admin_context
from app.api.types import (
    IsActiveQuery,
    IsSuperuserQuery,
    OptionalStrForm,
    PageQuery,
    PageSizeQuery,
    RequiredStrForm,
    SearchQuery,
    SortOrderQuery,
)
from app.core.exceptions import FeatureDisabledException


class TestQueryParameterTypes:
    """Tests for query parameter type definitions.

    Note: These are FastAPI dependency types, not callable validators.
    We test that they are properly defined with correct annotations.
    """

    def test_page_query_type_definition(self):
        """Test PageQuery is properly defined."""
        # PageQuery should be an Annotated type with Query dependency
        assert hasattr(PageQuery, "__metadata__")
        assert len(PageQuery.__metadata__) > 0

    def test_page_size_query_type_definition(self):
        """Test PageSizeQuery is properly defined."""
        assert hasattr(PageSizeQuery, "__metadata__")
        assert len(PageSizeQuery.__metadata__) > 0

    def test_search_query_type_definition(self):
        """Test SearchQuery is properly defined."""
        assert hasattr(SearchQuery, "__metadata__")
        assert len(SearchQuery.__metadata__) > 0

    def test_is_active_query_type_definition(self):
        """Test IsActiveQuery is properly defined."""
        assert hasattr(IsActiveQuery, "__metadata__")
        assert len(IsActiveQuery.__metadata__) > 0

    def test_is_superuser_query_type_definition(self):
        """Test IsSuperuserQuery is properly defined."""
        assert hasattr(IsSuperuserQuery, "__metadata__")
        assert len(IsSuperuserQuery.__metadata__) > 0

    def test_sort_order_query_type_definition(self):
        """Test SortOrderQuery is properly defined."""
        assert hasattr(SortOrderQuery, "__metadata__")
        assert len(SortOrderQuery.__metadata__) > 0


class TestFormParameterTypes:
    """Tests for form parameter type definitions.

    Note: These are FastAPI dependency types, not callable validators.
    We test that they are properly defined with correct annotations.
    """

    def test_required_str_form_type_definition(self):
        """Test RequiredStrForm is properly defined."""
        assert hasattr(RequiredStrForm, "__metadata__")

    def test_optional_str_form_type_definition(self):
        """Test OptionalStrForm is properly defined."""
        assert hasattr(OptionalStrForm, "__metadata__")


class TestGetAdminContext:
    """Tests for get_admin_context function."""

    @patch("app.core.rbac_template_helpers.RBACHelper")
    @patch("app.api.deps.get_settings")
    def test_get_admin_context_basic(self, mock_get_settings, mock_rbac_helper_class):
        """Test get_admin_context returns basic context."""
        # Mock settings
        mock_settings = MagicMock()
        mock_settings.windx.experimental_customers_page = True
        mock_settings.windx.experimental_orders_page = False
        mock_get_settings.return_value = mock_settings

        # Mock RBAC helper
        mock_rbac_helper = MagicMock()
        mock_rbac_helper.can = MagicMock()
        mock_rbac_helper.has = MagicMock()
        mock_rbac_helper_class.return_value = mock_rbac_helper

        # Mock request and user
        mock_request = MagicMock(spec=Request)
        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.email = "test@example.com"

        context = get_admin_context(mock_request, mock_user)

        assert context["request"] == mock_request
        assert context["current_user"] == mock_user
        assert context["active_page"] == "dashboard"
        assert context["enable_customers"] is True
        assert context["enable_orders"] is False
        # Check RBAC helpers are included
        assert context["rbac"] == mock_rbac_helper
        assert context["can"] == mock_rbac_helper.can
        assert context["has"] == mock_rbac_helper.has
        # Verify RBACHelper was created with the user
        mock_rbac_helper_class.assert_called_once_with(mock_user)

    @patch("app.core.rbac_template_helpers.RBACHelper")
    @patch("app.api.deps.get_settings")
    def test_get_admin_context_custom_page(self, mock_get_settings, mock_rbac_helper_class):
        """Test get_admin_context with custom active page."""
        mock_settings = MagicMock()
        mock_settings.windx.experimental_customers_page = True
        mock_settings.windx.experimental_orders_page = True
        mock_get_settings.return_value = mock_settings

        # Mock RBAC helper
        mock_rbac_helper = MagicMock()
        mock_rbac_helper_class.return_value = mock_rbac_helper

        mock_request = MagicMock(spec=Request)
        mock_user = MagicMock()

        context = get_admin_context(mock_request, mock_user, active_page="customers")

        assert context["active_page"] == "customers"
        assert "rbac" in context
        assert "can" in context
        assert "has" in context

    @patch("app.core.rbac_template_helpers.RBACHelper")
    @patch("app.api.deps.get_settings")
    def test_get_admin_context_extra_kwargs(self, mock_get_settings, mock_rbac_helper_class):
        """Test get_admin_context with extra keyword arguments."""
        mock_settings = MagicMock()
        mock_settings.windx.experimental_customers_page = True
        mock_settings.windx.experimental_orders_page = True
        mock_get_settings.return_value = mock_settings

        # Mock RBAC helper
        mock_rbac_helper = MagicMock()
        mock_rbac_helper_class.return_value = mock_rbac_helper

        mock_request = MagicMock(spec=Request)
        mock_user = MagicMock()

        context = get_admin_context(
            mock_request,
            mock_user,
            custom_key="custom_value",
            another_key=123,
        )

        assert context["custom_key"] == "custom_value"
        assert context["another_key"] == 123
        # RBAC helpers should still be present
        assert "rbac" in context
        assert "can" in context
        assert "has" in context


class TestCheckFeatureFlag:
    """Tests for check_feature_flag function."""

    @patch("app.api.admin_utils.get_settings")
    def test_check_feature_flag_enabled(self, mock_get_settings):
        """Test check_feature_flag passes when flag is enabled."""
        mock_settings = MagicMock()
        mock_settings.windx.experimental_customers_page = True
        mock_get_settings.return_value = mock_settings

        # Should not raise exception
        check_feature_flag("experimental_customers_page")

    @patch("app.api.admin_utils.get_settings")
    def test_check_feature_flag_disabled(self, mock_get_settings):
        """Test check_feature_flag raises FeatureDisabledException when flag is disabled."""
        mock_settings = MagicMock()
        mock_settings.windx.experimental_customers_page = False
        mock_get_settings.return_value = mock_settings

        with pytest.raises(FeatureDisabledException) as exc_info:
            check_feature_flag("experimental_customers_page")

        assert exc_info.value.status_code == 503
        assert "disabled" in exc_info.value.detail.lower()
        assert exc_info.value.feature_name == "experimental_customers_page"
        assert exc_info.value.reason == "Experimental Customers Page is currently disabled"

    @patch("app.api.admin_utils.get_settings")
    def test_check_feature_flag_nonexistent(self, mock_get_settings):
        """Test check_feature_flag raises FeatureDisabledException for nonexistent flag."""
        mock_settings = MagicMock()
        mock_settings.windx = MagicMock(spec=[])  # No attributes
        mock_get_settings.return_value = mock_settings

        with pytest.raises(FeatureDisabledException) as exc_info:
            check_feature_flag("nonexistent_flag")

        assert exc_info.value.status_code == 503
        assert exc_info.value.feature_name == "nonexistent_flag"
        assert exc_info.value.reason == "Nonexistent Flag is currently disabled"


class TestBuildRedirectResponse:
    """Tests for build_redirect_response function."""

    def test_build_redirect_response_no_message(self):
        """Test build_redirect_response without message."""
        response = build_redirect_response("/admin/customers")

        assert isinstance(response, RedirectResponse)
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.headers["location"] == "/admin/customers"

    def test_build_redirect_response_success_message(self):
        """Test build_redirect_response with success message."""
        response = build_redirect_response(
            "/admin/customers",
            message="Customer created successfully",
            message_type="success",
        )

        assert isinstance(response, RedirectResponse)
        location = response.headers["location"]
        assert "success=" in location
        assert "Customer" in location

    def test_build_redirect_response_error_message(self):
        """Test build_redirect_response with error message."""
        response = build_redirect_response(
            "/admin/customers",
            message="Customer not found",
            message_type="error",
        )

        location = response.headers["location"]
        assert "error=" in location
        assert "Customer" in location

    def test_build_redirect_response_warning_message(self):
        """Test build_redirect_response with warning message."""
        response = build_redirect_response(
            "/admin/customers",
            message="Customer updated with warnings",
            message_type="warning",
        )

        location = response.headers["location"]
        assert "warning=" in location
        assert "Customer" in location

    def test_build_redirect_response_info_message(self):
        """Test build_redirect_response with info message."""
        response = build_redirect_response(
            "/admin/customers",
            message="Customer details",
            message_type="info",
        )

        location = response.headers["location"]
        assert "info=" in location
        assert "Customer" in location

    def test_build_redirect_response_url_with_query_params(self):
        """Test build_redirect_response with URL that already has query params."""
        response = build_redirect_response(
            "/admin/customers?page=2",
            message="Success",
            message_type="success",
        )

        location = response.headers["location"]
        assert "page=2" in location
        assert "&success=Success" in location

    def test_build_redirect_response_custom_status_code(self):
        """Test build_redirect_response with custom status code."""
        response = build_redirect_response(
            "/admin/customers",
            message="Moved",
            status_code=status.HTTP_302_FOUND,
        )

        assert response.status_code == status.HTTP_302_FOUND


class TestFormatValidationErrors:
    """Tests for format_validation_errors function."""

    def test_format_validation_errors_single_error(self):
        """Test format_validation_errors with single error."""

        class TestModel(BaseModel):
            email: str

        try:
            TestModel(email=123)  # Invalid type
        except ValidationError as e:
            errors = format_validation_errors(e)

        assert len(errors) == 1
        assert "email" in errors[0]

    def test_format_validation_errors_multiple_errors(self):
        """Test format_validation_errors with multiple errors."""

        class TestModel(BaseModel):
            email: str
            age: int

        try:
            TestModel(email=123, age="not a number")  # Both invalid
        except ValidationError as e:
            errors = format_validation_errors(e)

        assert len(errors) == 2
        assert any("email" in error for error in errors)
        assert any("age" in error for error in errors)

    def test_format_validation_errors_nested_field(self):
        """Test format_validation_errors with nested field errors."""

        class Address(BaseModel):
            street: str
            city: str

        class User(BaseModel):
            name: str
            address: Address

        try:
            User(name="John", address={"street": 123})  # Missing city, invalid street
        except ValidationError as e:
            errors = format_validation_errors(e)

        assert len(errors) > 0
        # Should contain field path information
        assert any("address" in error for error in errors)


class TestFormDataProcessor:
    """Tests for FormDataProcessor utility class."""

    def test_normalize_optional_string_valid(self):
        """Test normalize_optional_string with valid strings."""
        assert FormDataProcessor.normalize_optional_string("test") == "test"
        assert FormDataProcessor.normalize_optional_string("  test  ") == "test"
        assert FormDataProcessor.normalize_optional_string("test value") == "test value"

    def test_normalize_optional_string_empty(self):
        """Test normalize_optional_string with empty strings."""
        assert FormDataProcessor.normalize_optional_string("") is None
        assert FormDataProcessor.normalize_optional_string("   ") is None
        assert FormDataProcessor.normalize_optional_string("\t\n") is None

    def test_normalize_optional_string_none(self):
        """Test normalize_optional_string with None."""
        assert FormDataProcessor.normalize_optional_string(None) is None

    def test_convert_to_decimal_valid(self):
        """Test convert_to_decimal with valid strings."""
        assert FormDataProcessor.convert_to_decimal("123.45") == Decimal("123.45")
        assert FormDataProcessor.convert_to_decimal("100") == Decimal("100")
        assert FormDataProcessor.convert_to_decimal("0.01") == Decimal("0.01")
        assert FormDataProcessor.convert_to_decimal("-50.25") == Decimal("-50.25")

    def test_convert_to_decimal_empty(self):
        """Test convert_to_decimal with empty strings."""
        assert FormDataProcessor.convert_to_decimal("") is None
        assert FormDataProcessor.convert_to_decimal("   ") is None
        assert FormDataProcessor.convert_to_decimal(None) is None

    def test_convert_to_decimal_with_default(self):
        """Test convert_to_decimal with default value."""
        default = Decimal("0.00")
        assert FormDataProcessor.convert_to_decimal("", default=default) == default
        assert FormDataProcessor.convert_to_decimal(None, default=default) == default
        assert FormDataProcessor.convert_to_decimal("   ", default=default) == default

    def test_convert_to_decimal_invalid(self):
        """Test convert_to_decimal with invalid strings."""
        with pytest.raises(ValueError) as exc_info:
            FormDataProcessor.convert_to_decimal("invalid")
        assert "Invalid decimal value" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            FormDataProcessor.convert_to_decimal("12.34.56")
        assert "Invalid decimal value" in str(exc_info.value)

        with pytest.raises(ValueError) as exc_info:
            FormDataProcessor.convert_to_decimal("abc123")
        assert "Invalid decimal value" in str(exc_info.value)

    def test_convert_to_decimal_precision(self):
        """Test convert_to_decimal preserves precision."""
        result = FormDataProcessor.convert_to_decimal("123.456789")
        assert result == Decimal("123.456789")
        assert str(result) == "123.456789"

    def test_convert_to_decimal_scientific_notation(self):
        """Test convert_to_decimal with scientific notation."""
        result = FormDataProcessor.convert_to_decimal("1.23E+2")
        assert result == Decimal("123")

        result = FormDataProcessor.convert_to_decimal("1.23E-2")
        assert result == Decimal("0.0123")
