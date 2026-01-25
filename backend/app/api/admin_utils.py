"""Shared utilities for admin endpoints.

This module provides common utilities used across admin endpoints to ensure
consistency in error handling, redirects, validation, and data processing.

Public Functions:
    check_feature_flag: Check if a feature flag is enabled
    build_redirect_response: Build redirect response with optional message
    format_validation_errors: Convert Pydantic validation errors to user-friendly messages

Public Classes:
    FormDataProcessor: Utility class for processing form data

Note:
    get_admin_context() is available in app.api.deps and should be imported from there.

Features:
    - Feature flag validation
    - Consistent redirect handling with message types
    - Pydantic validation error formatting
    - Form data normalization and conversion
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING

from fastapi import status
from fastapi.responses import RedirectResponse

from app.core.config import get_settings
from app.core.exceptions import FeatureDisabledException

if TYPE_CHECKING:
    from pydantic import ValidationError

__all__ = [
    "check_feature_flag",
    "build_redirect_response",
    "format_validation_errors",
    "FormDataProcessor",
]


def check_feature_flag(flag_name: str) -> None:
    """Check if a feature flag is enabled, raise exception if not.

    This function validates that a specific experimental feature is enabled
    in the application settings. If the feature is disabled, it raises a
    FeatureDisabledException.

    Args:
        flag_name: Name of the feature flag to check (e.g., 'experimental_customers_page')

    Raises:
        FeatureDisabledException: If feature is disabled

    Example:
        >>> check_feature_flag('experimental_customers_page')
        # Raises FeatureDisabledException if customers page is disabled

    Note:
        This function is typically called at the beginning of admin endpoints
        to ensure the feature is available before processing the request.
    """
    settings = get_settings()
    flag_value = getattr(settings.windx, flag_name, False)

    if not flag_value:
        # Convert flag name to human-readable format
        # e.g., 'experimental_customers_page' -> 'Experimental Customers Page'
        readable_name = flag_name.replace("_", " ").title()
        raise FeatureDisabledException(
            feature_name=flag_name,
            reason=f"{readable_name} is currently disabled",
        )


def build_redirect_response(
    url: str,
    message: str | None = None,
    message_type: str = "success",
    status_code: int = status.HTTP_303_SEE_OTHER,
) -> RedirectResponse:
    """Build redirect response with optional message.

    Creates a redirect response with an optional message that can be displayed
    to the user. The message is added as a query parameter with the specified
    message type (success, error, warning, info).

    Args:
        url: Target URL for the redirect
        message: Optional message to display to the user
        message_type: Type of message (success, error, warning, info). Defaults to 'success'
        status_code: HTTP status code for redirect. Defaults to 303 (See Other)

    Returns:
        RedirectResponse: FastAPI redirect response with message in query params

    Example:
        >>> build_redirect_response(
        ...     url="/admin/customers",
        ...     message="Customer created successfully",
        ...     message_type="success"
        ... )
        RedirectResponse(url="/admin/customers?success=Customer created successfully")

        >>> build_redirect_response(
        ...     url="/admin/customers",
        ...     message="Customer not found",
        ...     message_type="error"
        ... )
        RedirectResponse(url="/admin/customers?error=Customer not found")

    Note:
        - Uses 303 See Other by default (POST-Redirect-GET pattern)
        - Message types should match template expectations
        - URL encoding is handled automatically by RedirectResponse
    """
    if message:
        # Determine separator based on whether URL already has query params
        separator = "&" if "?" in url else "?"
        # Append message as query parameter with appropriate type
        url = f"{url}{separator}{message_type}={message}"

    return RedirectResponse(url=url, status_code=status_code)


def format_validation_errors(validation_error: ValidationError) -> list[str]:
    """Convert Pydantic validation errors to user-friendly messages.

    Takes a Pydantic ValidationError and converts it into a list of
    human-readable error messages suitable for display in templates.

    Args:
        validation_error: Pydantic ValidationError from schema validation

    Returns:
        list[str]: List of formatted error messages

    Example:
        >>> from pydantic import BaseModel, ValidationError
        >>> class User(BaseModel):
        ...     email: str
        ...     age: int
        >>> try:
        ...     User(email="invalid", age="not a number")
        ... except ValidationError as e:
        ...     errors = format_validation_errors(e)
        >>> errors
        ['email: value is not a valid email address', 'age: value is not a valid integer']

    Note:
        - Extracts field name from error location
        - Uses Pydantic's error message for clarity
        - Returns 'unknown' as field name if location is empty
    """
    return [
        f"{error['loc'][0] if error['loc'] else 'unknown'}: {error['msg']}"
        for error in validation_error.errors()
    ]


class FormDataProcessor:
    """Utility class for processing form data.

    Provides static methods for common form data transformations such as
    normalizing optional strings and converting string values to Decimal.

    Example:
        >>> FormDataProcessor.normalize_optional_string("  test  ")
        'test'
        >>> FormDataProcessor.normalize_optional_string("   ")
        None
        >>> FormDataProcessor.convert_to_decimal("123.45")
        Decimal('123.45')
        >>> FormDataProcessor.convert_to_decimal("", default=Decimal('0'))
        Decimal('0')
    """

    @staticmethod
    def normalize_optional_string(value: str | None) -> str | None:
        """Return None for empty strings, otherwise return stripped value.

        This method is useful for processing optional form fields where
        empty strings should be treated as None in the database.

        Args:
            value: String value from form input, may be None or empty

        Returns:
            str | None: Stripped string if non-empty, None otherwise

        Example:
            >>> FormDataProcessor.normalize_optional_string("  hello  ")
            'hello'
            >>> FormDataProcessor.normalize_optional_string("   ")
            None
            >>> FormDataProcessor.normalize_optional_string("")
            None
            >>> FormDataProcessor.normalize_optional_string(None)
            None

        Note:
            - Strips leading and trailing whitespace
            - Treats whitespace-only strings as empty
            - Returns None for None input
        """
        if value is None:
            return None
        stripped = value.strip()
        return stripped if stripped else None

    @staticmethod
    def convert_to_decimal(value: str | None, default: Decimal | None = None) -> Decimal | None:
        """Convert string to Decimal, returning default if empty or invalid.

        This method safely converts string values to Decimal, handling
        empty strings and invalid formats gracefully.

        Args:
            value: String value to convert, may be None or empty
            default: Default value to return if conversion fails or value is empty

        Returns:
            Decimal | None: Converted Decimal value, default, or None

        Raises:
            ValueError: If value is invalid and cannot be converted to Decimal

        Example:
            >>> FormDataProcessor.convert_to_decimal("123.45")
            Decimal('123.45')
            >>> FormDataProcessor.convert_to_decimal("", default=Decimal('0'))
            Decimal('0')
            >>> FormDataProcessor.convert_to_decimal(None, default=Decimal('0'))
            Decimal('0')
            >>> FormDataProcessor.convert_to_decimal("invalid")
            Traceback (most recent call last):
                ...
            ValueError: Invalid decimal value: invalid

        Note:
            - Returns default for None or empty string
            - Raises ValueError with descriptive message for invalid input
            - Preserves Decimal precision
        """
        if not value or not value.strip():
            return default

        try:
            return Decimal(value)
        except InvalidOperation as e:
            raise ValueError(f"Invalid decimal value: {value}") from e
