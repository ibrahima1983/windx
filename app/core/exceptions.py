"""Enhanced exception classes for RBAC and customer relationship handling.

This module provides specialized exception classes for better error handling
and diagnostics in the RBAC system and customer relationship management.

Public Classes:
    CasbinAuthorizationException: Casbin-specific authorization failures
    PolicyEvaluationException: Policy evaluation errors
    CustomerCreationException: Customer auto-creation failures
    UserCustomerMappingException: User-Customer relationship errors
    PrivilegeEvaluationException: Privilege object evaluation errors

Features:
    - Clear error messages for RBAC failures
    - Diagnostic information for troubleshooting
    - Audit logging integration
    - HTTP status code mapping
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import HTTPException

__all__ = [
    # Base exceptions
    "NotFoundException",
    "ValidationException",
    "ConflictException",
    "AuthorizationException",
    "AuthenticationException",
    "DatabaseException",
    "InvalidFormulaException",
    # RBAC-specific exceptions
    "CasbinAuthorizationException",
    "PolicyEvaluationException",
    "CustomerCreationException",
    "UserCustomerMappingException",
    "PrivilegeEvaluationException",
    "DatabaseConstraintException",
    "FeatureDisabledException",
]

logger = logging.getLogger(__name__)


# Base exceptions
class NotFoundException(HTTPException):
    """Raised when a requested resource is not found."""

    def __init__(self, resource: str = "Resource", details: Optional[dict[str, Any]] = None):
        self.resource = resource
        self.details = details or {}
        self.message = f"{resource} not found"  # Add message attribute
        detail = f"{resource} not found"
        super().__init__(status_code=404, detail=detail)


class ValidationException(HTTPException):
    """Raised when input validation fails."""

    def __init__(
        self,
        message: str,
        details: Optional[dict[str, Any]] = None,
        field_errors: Optional[dict[str, str]] = None,
    ):
        self.details = details or {}
        self.field_errors = field_errors or {}  # Add field_errors attribute
        self.message = message  # Add message attribute
        super().__init__(status_code=422, detail=message)


class ConflictException(HTTPException):
    """Raised when a resource conflict occurs."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        self.details = details or {}
        self.message = message  # Add message attribute
        super().__init__(status_code=409, detail=message)


class AuthorizationException(HTTPException):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Access denied", details: Optional[dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(status_code=403, detail=message)


class AuthenticationException(HTTPException):
    """Raised when authentication fails."""

    def __init__(
        self, message: str = "Authentication failed", details: Optional[dict[str, Any]] = None
    ):
        self.details = details or {}
        super().__init__(status_code=401, detail=message)


class DatabaseException(Exception):
    """Raised when database operations fail."""

    def __init__(self, message: str, details: Optional[dict[str, Any]] = None):
        self.details = details or {}
        super().__init__(message)


class InvalidFormulaException(Exception):
    """Raised when formula evaluation fails."""

    def __init__(
        self, message: str, formula: Optional[str] = None, details: Optional[dict[str, Any]] = None
    ):
        self.formula = formula
        self.details = details or {}  # Add details attribute
        self.message = message  # Add message attribute
        super().__init__(message)


class CasbinAuthorizationException(HTTPException):
    """Raised when Casbin policy evaluation denies access.

    Provides clear error messages and audit logging for authorization failures.
    Includes user context and resource information for security monitoring.
    """

    def __init__(
        self,
        user_email: str,
        resource: str,
        action: str,
        resource_id: Optional[int] = None,
        context: Optional[dict[str, Any]] = None,
    ):
        """Initialize Casbin authorization exception.

        Args:
            user_email: Email of user who was denied access
            resource: Resource type that was accessed
            action: Action that was attempted
            resource_id: Optional ID of specific resource
            context: Optional additional context for debugging
        """
        self.user_email = user_email
        self.resource = resource
        self.action = action
        self.resource_id = resource_id
        self.context = context or {}

        # Create detailed error message
        if resource_id:
            detail = (
                f"User '{user_email}' not authorized for '{action}' on {resource} {resource_id}"
            )
        else:
            detail = f"User '{user_email}' not authorized for '{action}' on {resource}"

        super().__init__(status_code=403, detail=detail)

        # Log security event for audit purposes
        logger.warning(
            f"Authorization denied: user={user_email}, resource={resource}, "
            f"action={action}, resource_id={resource_id}, context={context}"
        )


class PolicyEvaluationException(Exception):
    """Raised when Casbin policy evaluation fails due to system errors.

    Distinguishes between authorization denial (user lacks permission) and
    system errors (policy engine failure, configuration issues, etc.).
    """

    def __init__(self, error: str, policy_context: Optional[dict[str, Any]] = None):
        """Initialize policy evaluation exception.

        Args:
            error: Description of the policy evaluation error
            policy_context: Optional context about policy state
        """
        self.policy_context = policy_context or {}
        self.message = f"Policy evaluation failed: {error}"  # Add message attribute
        super().__init__(f"Policy evaluation failed: {error}")

        # Log system error for diagnostics
        logger.error(f"Policy evaluation error: {error}, context={policy_context}")


class CustomerCreationException(Exception):
    """Raised when customer auto-creation fails.

    Provides detailed information about customer creation failures including
    user data, constraint violations, and suggested corrective actions.
    """

    def __init__(
        self,
        message: str,
        user_email: str,
        user_data: Optional[dict[str, Any]] = None,
        original_error: Optional[Exception] = None,
    ):
        """Initialize customer creation exception.

        Args:
            message: Human-readable error message
            user_email: Email of user for whom customer creation failed
            user_data: Optional user data that was used for creation
            original_error: Optional original exception that caused the failure
        """
        self.user_email = user_email
        self.user_data = user_data or {}
        self.original_error = original_error
        self.message = message  # Add message attribute

        super().__init__(message)

        # Log customer creation failure for diagnostics
        logger.error(
            f"Customer creation failed for user {user_email}: {message}, "
            f"user_data={user_data}, original_error={original_error}"
        )


class UserCustomerMappingException(Exception):
    """Raised when User-Customer relationship mapping fails.

    Handles errors in establishing or validating User-Customer relationships,
    including email mismatches, missing customers, and constraint violations.
    """

    def __init__(
        self,
        message: str,
        user_id: Optional[int] = None,
        customer_id: Optional[int] = None,
        mapping_context: Optional[dict[str, Any]] = None,
    ):
        """Initialize user-customer mapping exception.

        Args:
            message: Human-readable error message
            user_id: Optional user ID involved in mapping failure
            customer_id: Optional customer ID involved in mapping failure
            mapping_context: Optional context about the mapping attempt
        """
        self.user_id = user_id
        self.customer_id = customer_id
        self.mapping_context = mapping_context or {}

        super().__init__(message)

        # Log mapping failure for diagnostics
        logger.error(
            f"User-Customer mapping failed: {message}, user_id={user_id}, "
            f"customer_id={customer_id}, context={mapping_context}"
        )


class PrivilegeEvaluationException(Exception):
    """Raised when Privilege object evaluation fails.

    Handles errors in evaluating Privilege objects including role validation,
    permission checking, and resource ownership verification.
    """

    def __init__(
        self,
        message: str,
        privilege_info: Optional[dict[str, Any]] = None,
        evaluation_context: Optional[dict[str, Any]] = None,
    ):
        """Initialize privilege evaluation exception.

        Args:
            message: Human-readable error message
            privilege_info: Optional information about the privilege being evaluated
            evaluation_context: Optional context about the evaluation attempt
        """
        self.privilege_info = privilege_info or {}
        self.evaluation_context = evaluation_context or {}

        super().__init__(message)

        # Log privilege evaluation failure for diagnostics
        logger.error(
            f"Privilege evaluation failed: {message}, "
            f"privilege={privilege_info}, context={evaluation_context}"
        )


class DatabaseConstraintException(Exception):
    """Raised when database constraint violations occur.

    Provides specific handling for foreign key constraints, unique constraints,
    and other database integrity violations with suggested corrective actions.
    """

    def __init__(
        self,
        message: str,
        constraint_type: str,
        constraint_details: Optional[dict[str, Any]] = None,
        suggested_action: Optional[str] = None,
    ):
        """Initialize database constraint exception.

        Args:
            message: Human-readable error message
            constraint_type: Type of constraint violated (foreign_key, unique, etc.)
            constraint_details: Optional details about the constraint violation
            suggested_action: Optional suggested corrective action
        """
        self.constraint_type = constraint_type
        self.constraint_details = constraint_details or {}
        self.suggested_action = suggested_action

        super().__init__(message)

        # Log constraint violation for diagnostics
        logger.error(
            f"Database constraint violation: {message}, type={constraint_type}, "
            f"details={constraint_details}, suggested_action={suggested_action}"
        )


class FeatureDisabledException(HTTPException):
    """Raised when a feature is disabled or not available.

    Used for feature flags and conditional functionality.
    """

    def __init__(self, feature_name: str, reason: Optional[str] = None):
        """Initialize feature disabled exception.

        Args:
            feature_name: Name of the disabled feature
            reason: Optional reason why the feature is disabled
        """
        self.feature_name = feature_name
        self.reason = reason

        detail = f"Feature '{feature_name}' is disabled"
        if reason:
            detail += f": {reason}"

        super().__init__(status_code=503, detail=detail)

        # Log feature access attempt
        logger.info(f"Access attempted to disabled feature: {feature_name}, reason: {reason}")


def setup_exception_handlers(app):
    """Setup exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(ConflictException)
    async def conflict_exception_handler(request: Request, exc: ConflictException):
        """Handle ConflictException with standardized error response."""
        return JSONResponse(
            status_code=409,
            content={
                "error": "conflict_error",
                "message": exc.detail,
                "details": getattr(exc, "details", {}),
            },
        )

    @app.exception_handler(AuthenticationException)
    async def authentication_exception_handler(request: Request, exc: AuthenticationException):
        """Handle AuthenticationException with standardized error response."""
        return JSONResponse(
            status_code=401,
            content={
                "error": "authentication_error",
                "message": exc.detail,
                "details": getattr(exc, "details", {}),
            },
        )

    @app.exception_handler(AuthorizationException)
    async def authorization_exception_handler(request: Request, exc: AuthorizationException):
        """Handle AuthorizationException with standardized error response."""
        return JSONResponse(
            status_code=403,
            content={
                "error": "authorization_error",
                "message": exc.detail,
                "details": getattr(exc, "details", {}),
            },
        )

    @app.exception_handler(NotFoundException)
    async def not_found_exception_handler(request: Request, exc: NotFoundException):
        """Handle NotFoundException with standardized error response."""
        return JSONResponse(
            status_code=404,
            content={
                "error": "not_found_error",
                "message": exc.detail,
                "details": getattr(exc, "details", {}),
            },
        )

    @app.exception_handler(ValidationException)
    async def validation_exception_handler(request: Request, exc: ValidationException):
        """Handle ValidationException with standardized error response."""
        return JSONResponse(
            status_code=422,
            content={
                "error": "validation_error",
                "message": exc.detail,
                "details": getattr(exc, "details", {}),
            },
        )


# Exception mapping for HTTP responses
EXCEPTION_STATUS_MAPPING = {
    # Base exceptions
    NotFoundException: 404,
    ValidationException: 422,
    ConflictException: 409,
    AuthorizationException: 403,
    AuthenticationException: 401,
    DatabaseException: 500,
    InvalidFormulaException: 400,
    # RBAC-specific exceptions
    CasbinAuthorizationException: 403,
    PolicyEvaluationException: 500,
    CustomerCreationException: 500,
    UserCustomerMappingException: 500,
    PrivilegeEvaluationException: 500,
    DatabaseConstraintException: 400,
    FeatureDisabledException: 503,
}


def get_http_status_for_exception(exception: Exception) -> int:
    """Get appropriate HTTP status code for exception.

    Args:
        exception: Exception to get status code for

    Returns:
        HTTP status code (default: 500)
    """
    return EXCEPTION_STATUS_MAPPING.get(type(exception), 500)


def create_error_response(exception: Exception) -> dict[str, Any]:
    """Create standardized error response for exception.

    Args:
        exception: Exception to create response for

    Returns:
        Dictionary containing error response data
    """
    response = {
        "error": type(exception).__name__,
        "message": str(exception),
        "status_code": get_http_status_for_exception(exception),
    }

    # Add exception-specific details
    if isinstance(exception, CasbinAuthorizationException):
        response["details"] = {
            "user_email": exception.user_email,
            "resource": exception.resource,
            "action": exception.action,
            "resource_id": exception.resource_id,
        }
    elif isinstance(exception, CustomerCreationException):
        response["details"] = {"user_email": exception.user_email, "user_data": exception.user_data}
    elif isinstance(exception, DatabaseConstraintException):
        response["details"] = {
            "constraint_type": exception.constraint_type,
            "constraint_details": exception.constraint_details,
            "suggested_action": exception.suggested_action,
        }

    return response
