"""Service factory for product definition services.

This module provides a factory for creating scope-specific product definition services
and a convenience function for getting service instances.
"""

from __future__ import annotations

from typing import Dict, List, Type

from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseProductDefinitionService
from .profile import ProfileProductDefinitionService
from .glazing import GlazingProductDefinitionService

__all__ = ["ProductDefinitionServiceFactory", "get_product_definition_service"]


class ProductDefinitionServiceFactory:
    """Factory for creating scope-specific product definition services.
    
    This factory manages the registration and creation of service instances
    for different product definition scopes (profile, glazing, etc.).
    """
    
    _services: Dict[str, Type[BaseProductDefinitionService]] = {
        "profile": ProfileProductDefinitionService,
        "glazing": GlazingProductDefinitionService,
    }
    
    @classmethod
    def get_service(cls, scope: str, db: AsyncSession) -> BaseProductDefinitionService:
        """Get service instance for specified scope.
        
        Args:
            scope: Scope name (e.g., 'profile', 'glazing')
            db: Database session
            
        Returns:
            Service instance for the specified scope
            
        Raises:
            ValueError: If scope is unknown
        """
        if scope not in cls._services:
            available_scopes = list(cls._services.keys())
            raise ValueError(f"Unknown scope: {scope}. Available scopes: {available_scopes}")
        
        service_class = cls._services[scope]
        return service_class(db)
    
    @classmethod
    def register_service(cls, scope: str, service_class: Type[BaseProductDefinitionService]) -> None:
        """Register a new scope service.
        
        Args:
            scope: Scope name
            service_class: Service class for the scope
            
        Raises:
            TypeError: If service_class is not a subclass of BaseProductDefinitionService
        """
        if not issubclass(service_class, BaseProductDefinitionService):
            raise TypeError(f"Service class must be a subclass of BaseProductDefinitionService")
        
        cls._services[scope] = service_class
    
    @classmethod
    def unregister_service(cls, scope: str) -> bool:
        """Unregister a scope service.
        
        Args:
            scope: Scope name to unregister
            
        Returns:
            True if service was unregistered, False if scope was not found
        """
        if scope in cls._services:
            del cls._services[scope]
            return True
        return False
    
    @classmethod
    def get_available_scopes(cls) -> List[str]:
        """Get list of available scopes.
        
        Returns:
            List of scope names
        """
        return list(cls._services.keys())
    
    @classmethod
    def is_scope_available(cls, scope: str) -> bool:
        """Check if a scope is available.
        
        Args:
            scope: Scope name to check
            
        Returns:
            True if scope is available
        """
        return scope in cls._services
    
    @classmethod
    def get_service_class(cls, scope: str) -> Type[BaseProductDefinitionService]:
        """Get service class for specified scope.
        
        Args:
            scope: Scope name
            
        Returns:
            Service class for the specified scope
            
        Raises:
            ValueError: If scope is unknown
        """
        if scope not in cls._services:
            available_scopes = list(cls._services.keys())
            raise ValueError(f"Unknown scope: {scope}. Available scopes: {available_scopes}")
        
        return cls._services[scope]
    
    @classmethod
    def get_factory_info(cls) -> Dict[str, any]:
        """Get information about the factory and registered services.
        
        Returns:
            Factory information dictionary
        """
        return {
            "factory_class": cls.__name__,
            "registered_scopes": list(cls._services.keys()),
            "service_classes": {
                scope: service_class.__name__ 
                for scope, service_class in cls._services.items()
            },
            "total_services": len(cls._services)
        }


def get_product_definition_service(scope: str, db: AsyncSession) -> BaseProductDefinitionService:
    """Convenience function to get a product definition service instance.
    
    Args:
        scope: Scope name (e.g., 'profile', 'glazing')
        db: Database session
        
    Returns:
        Service instance for the specified scope
        
    Raises:
        ValueError: If scope is unknown
        
    Example:
        ```python
        from app.services.product_definition import get_product_definition_service
        
        # Get profile service
        profile_service = get_product_definition_service("profile", db)
        
        # Get glazing service
        glazing_service = get_product_definition_service("glazing", db)
        ```
    """
    return ProductDefinitionServiceFactory.get_service(scope, db)