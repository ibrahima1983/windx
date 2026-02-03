"""Router factory for product definition endpoints.

This module provides a factory function to create scope-aware routers
for product definition endpoints.
"""

from __future__ import annotations

from typing import Dict, Type

from fastapi import APIRouter

from .base import BaseProductDefinitionEndpoints
from .profile import ProfileProductDefinitionEndpoints
from .glazing import GlazingProductDefinitionEndpoints

__all__ = ["get_product_definition_router", "ProductDefinitionRouterFactory"]


class ProductDefinitionRouterFactory:
    """Factory for creating scope-specific product definition routers."""
    
    _endpoints: Dict[str, Type[BaseProductDefinitionEndpoints]] = {
        "profile": ProfileProductDefinitionEndpoints,
        "glazing": GlazingProductDefinitionEndpoints,
    }
    
    @classmethod
    def get_router(cls, scope: str | None = None) -> APIRouter:
        """Get router for specified scope or combined router for all scopes.
        
        Args:
            scope: Specific scope to get router for, or None for all scopes
            
        Returns:
            FastAPI router with scope-specific endpoints
            
        Raises:
            ValueError: If scope is unknown
        """
        if scope is None:
            # Return combined router with all scopes
            return cls._get_combined_router()
        
        if scope not in cls._endpoints:
            raise ValueError(f"Unknown scope: {scope}. Available: {list(cls._endpoints.keys())}")
        
        endpoint_class = cls._endpoints[scope]
        endpoint_instance = endpoint_class()
        return endpoint_instance.router
    
    @classmethod
    def _get_combined_router(cls) -> APIRouter:
        """Get combined router with all scope endpoints."""
        combined_router = APIRouter()
        
        for scope, endpoint_class in cls._endpoints.items():
            endpoint_instance = endpoint_class()
            combined_router.include_router(
                endpoint_instance.router,
                tags=[f"product-definitions-{scope}"]
            )
        
        return combined_router
    
    @classmethod
    def register_scope(cls, scope: str, endpoint_class: Type[BaseProductDefinitionEndpoints]) -> None:
        """Register a new scope endpoint class.
        
        Args:
            scope: Scope name
            endpoint_class: Endpoint class for the scope
        """
        cls._endpoints[scope] = endpoint_class
    
    @classmethod
    def get_available_scopes(cls) -> list[str]:
        """Get list of available scopes.
        
        Returns:
            List of scope names
        """
        return list(cls._endpoints.keys())


def get_product_definition_router(scope: str | None = None) -> APIRouter:
    """Convenience function to get product definition router.
    
    Args:
        scope: Specific scope to get router for, or None for all scopes
        
    Returns:
        FastAPI router with product definition endpoints
    """
    return ProductDefinitionRouterFactory.get_router(scope)