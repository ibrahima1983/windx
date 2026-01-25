"""OpenAPI response models for consistent error handling across all endpoints.

This module defines reusable response schemas for common HTTP status codes
to improve API documentation and maintain consistency.

Public Classes:
    ErrorDetail: Standard error detail model
    ErrorResponse: Standard error response model

Public Functions:
    get_common_responses: Get common response schemas for specified status codes

Features:
    - Consistent error response format
    - OpenAPI documentation support
    - Reusable response schemas
    - Type-safe error handling
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

__all__ = [
    "ErrorDetail",
    "ErrorResponse",
    "get_common_responses",
    "RESPONSES_401",
    "RESPONSES_403",
    "RESPONSES_404",
    "RESPONSES_422",
    "RESPONSES_429",
    "RESPONSES_500",
    "RESPONSES_503",
]


class ErrorDetail(BaseModel):
    """Standard error detail model.

    Attributes:
        detail: Error message describing what went wrong
        error_code: Machine-readable error code for programmatic handling
        field: Field name if validation error (dot notation for nested fields)
    """

    detail: str = Field(
        description="Error message describing what went wrong",
        min_length=1,
        max_length=500,
        examples=[
            "Invalid email format",
            "Field is required",
            "Value must be greater than 0",
        ],
    )
    error_code: str | None = Field(
        None,
        description="Machine-readable error code for programmatic handling",
        pattern=r"^[A-Z_]+$",
        examples=["VALIDATION_ERROR", "NOT_FOUND", "UNAUTHORIZED"],
        max_length=50,
    )
    field: str | None = Field(
        None,
        description="Field name if validation error (dot notation for nested fields)",
        pattern=r"^[a-zA-Z_][a-zA-Z0-9_.]*$",
        examples=["email", "user.profile.name", "items.0.quantity"],
        max_length=100,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "detail": "Email address is already registered",
                    "error_code": "DUPLICATE_EMAIL",
                    "field": "email",
                },
                {
                    "detail": "Value must be between 1 and 100",
                    "error_code": "VALUE_OUT_OF_RANGE",
                    "field": "max_images",
                },
            ]
        }
    }


class ErrorResponse(BaseModel):
    """Standard error response model.

    Attributes:
        message: Human-readable error message
        details: Detailed error information for debugging
        request_id: Unique request ID for tracking and debugging
    """

    message: str = Field(
        description="Human-readable error message",
        min_length=1,
        max_length=200,
        examples=[
            "Validation Error",
            "Resource Not Found",
            "Authentication Required",
            "Internal Server Error",
        ],
    )
    details: list[ErrorDetail] | None = Field(
        None,
        description="Detailed error information for debugging",
        max_length=10,
        examples=[
            [
                {
                    "detail": "Field is required",
                    "error_code": "VALUE_ERROR_MISSING",
                    "field": "email",
                }
            ]
        ],
    )
    request_id: str | None = Field(
        None,
        description="Unique request ID for tracking and debugging",
        pattern=r"^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
        max_length=36,
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "message": "Validation Error",
                    "details": [
                        {
                            "detail": "Email address is required",
                            "error_code": "VALUE_ERROR_MISSING",
                            "field": "email",
                        },
                        {
                            "detail": "Password must be at least 8 characters",
                            "error_code": "VALUE_ERROR_TOO_SHORT",
                            "field": "password",
                        },
                    ],
                    "request_id": "550e8400-e29b-41d4-a716-446655440000",
                },
                {
                    "message": "Resource Not Found",
                    "details": [
                        {
                            "detail": "User with ID 123 does not exist",
                            "error_code": "NOT_FOUND",
                        }
                    ],
                    "request_id": "660e8400-e29b-41d4-a716-446655440001",
                },
            ]
        }
    }


# Common OpenAPI response schemas
RESPONSES_401: dict[str, Any] = {
    "description": "Authentication required or invalid token",
    "content": {
        "application/json": {
            "example": {
                "message": "Could not validate credentials",
                "details": [{"detail": "Invalid or expired authentication token"}],
            }
        }
    },
}

RESPONSES_403: dict[str, Any] = {
    "description": "Insufficient permissions",
    "content": {
        "application/json": {
            "example": {
                "message": "Forbidden",
                "details": [{"detail": "You don't have permission to access this resource"}],
            }
        }
    },
}

RESPONSES_404: dict[str, Any] = {
    "description": "Resource not found",
    "content": {
        "application/json": {
            "example": {
                "message": "Not Found",
                "details": [{"detail": "The requested resource does not exist"}],
            }
        }
    },
}

RESPONSES_422: dict[str, Any] = {
    "description": "Validation error",
    "content": {
        "application/json": {
            "example": {
                "message": "Validation Error",
                "details": [
                    {
                        "detail": "Field is required",
                        "field": "email",
                        "error_code": "value_error.missing",
                    }
                ],
            }
        }
    },
}

RESPONSES_429: dict[str, Any] = {
    "description": "Rate limit exceeded",
    "content": {
        "application/json": {
            "example": {
                "message": "Too Many Requests",
                "details": [{"detail": "Rate limit exceeded. Please try again later."}],
            }
        }
    },
}

RESPONSES_500: dict[str, Any] = {
    "description": "Internal server error",
    "content": {
        "application/json": {
            "example": {
                "message": "Internal Server Error",
                "details": [{"detail": "An unexpected error occurred. Please try again later."}],
            }
        }
    },
}

RESPONSES_503: dict[str, Any] = {
    "description": "Service unavailable",
    "content": {
        "application/json": {
            "example": {
                "message": "Service Unavailable",
                "details": [
                    {"detail": "The service is temporarily unavailable. Please try again later."}
                ],
            }
        }
    },
}

# Response map is a module-level constant
_RESPONSE_MAP: dict[int, dict[str, Any]] = {
    401: RESPONSES_401,
    403: RESPONSES_403,
    404: RESPONSES_404,
    422: RESPONSES_422,
    429: RESPONSES_429,
    500: RESPONSES_500,
    503: RESPONSES_503,
}


def get_common_responses(*status_codes: int) -> dict[int, dict[str, Any]]:
    """Get common response schemas for specified status codes.

    This function is lightweight and doesn't need @lru_cache because:
    1. It only does dictionary lookups (O(1) operations)
    2. The response_map is a module-level constant
    3. The result is a small dict that's immediately used in decorator
    4. Caching would add overhead without meaningful performance gain

    Args:
        *status_codes: HTTP status codes to include

    Returns:
        dict[int, dict[str, Any]]: Dictionary mapping status codes to response schemas

    Example:
        ```python
        responses = get_common_responses(401, 404, 500)
        ```
    """
    return {code: _RESPONSE_MAP[code] for code in status_codes if code in _RESPONSE_MAP}
