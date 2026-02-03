"""Product Definitions API endpoints package.

This package provides scope-based API endpoints for managing product definitions.
Each scope (profile, glazing, etc.) has its own endpoint implementation.
"""

from .router import get_product_definition_router

__all__ = ["get_product_definition_router"]