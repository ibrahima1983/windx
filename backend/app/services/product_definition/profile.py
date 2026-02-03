"""Profile-specific product definition service.

This module provides the service implementation for profile product definitions
with hierarchical dependencies (Company → Material → Opening System → System Series → Colors).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

if TYPE_CHECKING:
    from app.services.product_definition import ProductDefinitionService

from .base import BaseProductDefinitionService
from .types import EntityCreateData, EntityUpdateData, ProfilePathData, ProfileDependentOptions

__all__ = ["ProfileProductDefinitionService"]


class ProfileProductDefinitionService(BaseProductDefinitionService):
    """Service for profile product definitions with hierarchical dependencies.
    
    This service handles the profile scope which includes:
    - Hierarchical entities: company → material → opening_system → system_series → color
    - Dependency path management
    - Cascading option selection
    """

    def __init__(self, db: AsyncSession):
        """Initialize profile service.
        
        Args:
            db: Database session
        """
        super().__init__(db, "profile")
        # Use existing service for backward compatibility during migration
        self._legacy_service: Optional[Any] = None

    def _get_legacy_service(self) -> "ProductDefinitionService":
        """Get the legacy ProductDefinitionService for delegation.
        
        Returns:
            Legacy service instance
        """
        if self._legacy_service is None:
            # Import dynamically to avoid circular import
            import importlib
            module = importlib.import_module("app.services.product_definition")
            ProductDefinitionService = getattr(module, "ProductDefinitionService")
            self._legacy_service = ProductDefinitionService(self.db)
        return self._legacy_service

    # ============================================================================
    # Base Class Implementation
    # ============================================================================

    async def get_entities(self, entity_type: str) -> List[Any]:
        """Get profile entities of specific type.
        
        Args:
            entity_type: Type of entities (company, material, opening_system, system_series, color)
            
        Returns:
            List of entities
        """
        try:
            legacy_service = self._get_legacy_service()
            entities = await legacy_service.get_entities_by_type(entity_type, scope="profile")
            return entities
        except Exception as e:
            self._handle_service_error(e, f"getting {entity_type} entities")

    async def create_entity(self, data: EntityCreateData) -> Any:
        """Create profile entity.
        
        Args:
            data: Entity creation data
            
        Returns:
            Created entity
        """
        try:
            # Validate entity type for profile scope
            valid_types = ["company", "material", "opening_system", "system_series", "color"]
            if data.entity_type not in valid_types:
                raise ValueError(f"Invalid entity type for profile scope: {data.entity_type}. Valid types: {valid_types}")

            legacy_service = self._get_legacy_service()
            entity = await legacy_service.create_entity(
                entity_type=data.entity_type,
                name=data.name,
                image_url=data.image_url,
                price_from=data.price_from,
                description=data.description,
                metadata=data.metadata,
            )
            return entity
        except Exception as e:
            self._handle_service_error(e, f"creating {data.entity_type} entity")

    async def update_entity(self, entity_id: int, data: EntityUpdateData) -> Optional[Any]:
        """Update profile entity.
        
        Args:
            entity_id: Entity ID to update
            data: Update data
            
        Returns:
            Updated entity or None if not found
        """
        try:
            legacy_service = self._get_legacy_service()
            entity = await legacy_service.update_entity(
                entity_id=entity_id,
                name=data.name,
                image_url=data.image_url,
                price_from=data.price_from,
                description=data.description,
                metadata=data.metadata,
            )
            return entity
        except Exception as e:
            self._handle_service_error(e, f"updating entity {entity_id}")

    async def delete_entity(self, entity_id: int) -> Dict[str, Any]:
        """Delete profile entity.
        
        Args:
            entity_id: Entity ID to delete
            
        Returns:
            Result dict with success status
        """
        try:
            legacy_service = self._get_legacy_service()
            result = await legacy_service.delete_entity(entity_id)
            return result
        except Exception as e:
            self._handle_service_error(e, f"deleting entity {entity_id}")

    async def get_entity_by_id(self, entity_id: int) -> Optional[Any]:
        """Get profile entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity or None if not found
        """
        try:
            legacy_service = self._get_legacy_service()
            entity = await legacy_service.get_entity_by_id(entity_id)
            return entity
        except Exception as e:
            self._handle_service_error(e, f"getting entity {entity_id}")

    # ============================================================================
    # Profile-Specific Methods
    # ============================================================================

    async def create_dependency_path(self, data: ProfilePathData) -> Any:
        """Create profile dependency path.
        
        Args:
            data: Path creation data with entity IDs
            
        Returns:
            Created path node
        """
        try:
            legacy_service = self._get_legacy_service()
            path_node = await legacy_service.create_dependency_path(
                company_id=data.company_id,
                material_id=data.material_id,
                opening_system_id=data.opening_system_id,
                system_series_id=data.system_series_id,
                color_id=data.color_id,
            )
            return path_node
        except Exception as e:
            self._handle_service_error(e, "creating dependency path")

    async def delete_dependency_path(self, ltree_path: str) -> Dict[str, Any]:
        """Delete profile dependency path.
        
        Args:
            ltree_path: LTREE path to delete
            
        Returns:
            Result dict with success status
        """
        try:
            legacy_service = self._get_legacy_service()
            result = await legacy_service.delete_dependency_path(ltree_path)
            return result
        except Exception as e:
            self._handle_service_error(e, f"deleting dependency path {ltree_path}")

    async def get_all_paths(self) -> List[Dict[str, Any]]:
        """Get all profile dependency paths.
        
        Returns:
            List of path dictionaries
        """
        try:
            legacy_service = self._get_legacy_service()
            paths = await legacy_service.get_all_paths()
            return paths
        except Exception as e:
            self._handle_service_error(e, "getting all paths")

    async def get_path_details(self, path_id: int) -> Optional[Dict[str, Any]]:
        """Get detailed path information.
        
        Args:
            path_id: Path node ID
            
        Returns:
            Path details or None if not found
        """
        try:
            legacy_service = self._get_legacy_service()
            path_details = await legacy_service.get_path_details(path_id)
            return path_details
        except Exception as e:
            self._handle_service_error(e, f"getting path details {path_id}")

    async def get_dependent_options(self, selections: ProfileDependentOptions) -> Dict[str, List[Dict[str, Any]]]:
        """Get dependent options based on parent selections.
        
        Used for cascading dropdowns in profile entry.
        
        Args:
            selections: Parent selections
            
        Returns:
            Dict of entity_type -> list of available options
        """
        try:
            legacy_service = self._get_legacy_service()
            
            parent_selections = {
                "company_id": selections.company_id,
                "material_id": selections.material_id,
                "opening_system_id": selections.opening_system_id,
                "system_series_id": selections.system_series_id,
            }
            
            options = await legacy_service.get_dependent_options(parent_selections)
            return options
        except Exception as e:
            self._handle_service_error(e, "getting dependent options")

    async def get_definition_scopes(self) -> Dict[str, Any]:
        """Get profile definition scopes.
        
        Returns:
            Scopes configuration
        """
        try:
            legacy_service = self._get_legacy_service()
            scopes = await legacy_service.get_definition_scopes()
            return scopes
        except Exception as e:
            self._handle_service_error(e, "getting definition scopes")

    async def get_scope_for_entity(self, entity_type: str) -> str:
        """Get scope for an entity type.
        
        Args:
            entity_type: Type of entity
            
        Returns:
            Scope name
        """
        try:
            legacy_service = self._get_legacy_service()
            scope = await legacy_service.get_scope_for_entity(entity_type)
            return scope
        except Exception as e:
            self._handle_service_error(e, f"getting scope for entity type {entity_type}")

    # ============================================================================
    # Profile-Specific Scope Metadata
    # ============================================================================

    async def get_scope_metadata(self) -> Dict[str, Any]:
        """Get profile scope metadata.
        
        Returns:
            Profile scope metadata
        """
        if self._scope_metadata_cache is not None:
            return self._scope_metadata_cache

        try:
            # Get metadata from legacy service
            legacy_service = self._get_legacy_service()
            scopes = await legacy_service.get_definition_scopes()
            profile_metadata = scopes.get("profile", {})
            
            # Enhance with service-specific information
            profile_metadata.update({
                "service_class": self.__class__.__name__,
                "scope": self.scope,
                "supports_hierarchy": True,
                "supports_paths": True,
                "supports_cascading_options": True,
                "entity_types": ["company", "material", "opening_system", "system_series", "color"]
            })
            
            self._scope_metadata_cache = profile_metadata
            return profile_metadata
            
        except Exception as e:
            # Fallback to basic metadata if legacy service fails
            print(f"[WARNING] Failed to get profile metadata from legacy service: {e}")
            return await super().get_scope_metadata()

    # ============================================================================
    # Validation Methods
    # ============================================================================

    def _validate_entity_type(self, entity_type: str) -> bool:
        """Validate entity type for profile scope.
        
        Args:
            entity_type: Type of entity to validate
            
        Returns:
            True if valid for profile scope
        """
        valid_types = ["company", "material", "opening_system", "system_series", "color"]
        return entity_type in valid_types

    async def validate_entity_references(self, data: Dict[str, Any]) -> bool:
        """Validate entity references for profile scope.
        
        Args:
            data: Data containing entity references
            
        Returns:
            True if all references are valid
        """
        # For profile scope, validate that referenced entities exist
        # This is a placeholder - could be enhanced with specific validation logic
        return True