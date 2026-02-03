"""Product Definition Services package.

This package provides scope-based services for managing product definitions.
Each scope (profile, glazing, etc.) has its own service implementation.
"""

from .factory import ProductDefinitionServiceFactory, get_product_definition_service

__all__ = ["ProductDefinitionServiceFactory", "get_product_definition_service"]