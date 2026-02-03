"""Product Definition Services package.

This package provides scope-based services for managing product definitions.
Each scope (profile, glazing, etc.) has its own service implementation.
"""

from .factory import ProductDefinitionServiceFactory, get_product_definition_service

# Import legacy service for backward compatibility
import sys
from pathlib import Path

# Import the legacy ProductDefinitionService from the parent module
parent_dir = Path(__file__).parent.parent
legacy_module_path = parent_dir / "product_definition.py"

if legacy_module_path.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("legacy_product_definition", legacy_module_path)
    legacy_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(legacy_module)
    ProductDefinitionService = legacy_module.ProductDefinitionService
else:
    ProductDefinitionService = None

__all__ = ["ProductDefinitionServiceFactory", "get_product_definition_service", "ProductDefinitionService"]