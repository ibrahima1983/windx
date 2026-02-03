"""Base endpoint classes and common schemas for product definitions.

This module provides the foundation for scope-specific product definition endpoints.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.api.types import CurrentSuperuser
from app.schemas.product_definition import (
    BaseEntityCreate,
    BaseEntityUpdate,
    BaseEntityResponse,
    BaseResponse,
    ErrorResponse
)

__all__ = [
    "BaseProductDefinitionEndpoints"
]


# ============================================================================
# Type Aliases for Backward Compatibility
# ============================================================================

# Use the new schema classes
EntityCreateRequest = BaseEntityCreate
EntityUpdateRequest = BaseEntityUpdate
EntityResponse = BaseEntityResponse


# ============================================================================
# Base Endpoint Class
# ============================================================================

class BaseProductDefinitionEndpoints(ABC):
    """Base class for scope-specific product definition endpoints.
    
    This abstract class provides the foundation for implementing
    scope-specific endpoints (profile, glazing, etc.).
    """

    def __init__(self, scope: str):
        """Initialize base endpoints.
        
        Args:
            scope: The scope name (e.g., 'profile', 'glazing')
        """
        self.scope = scope
        self.router = APIRouter(
            prefix=f"/product-definitions/{scope}",
            tags=[f"{scope}-definitions"]
        )
        self._setup_common_routes()
        self._setup_scope_routes()

    def _setup_common_routes(self) -> None:
        """Setup common routes available to all scopes."""
        
        @self.router.post("/entities", status_code=status.HTTP_201_CREATED)
        async def create_entity(
                data: EntityCreateRequest,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> BaseResponse:
            """Create a new entity for this scope."""
            try:
                entity = await self.create_entity_impl(data, db)
                return BaseResponse(
                    success=True,
                    message=f"{data.entity_type.replace('_', ' ').title()} '{data.name}' created"
                )
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                self._handle_database_error(e, f"creating {data.entity_type}")

        @self.router.put("/entities/{entity_id}")
        async def update_entity(
                entity_id: int,
                data: EntityUpdateRequest,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> BaseResponse:
            """Update an existing entity."""
            try:
                entity = await self.update_entity_impl(entity_id, data, db)
                if not entity:
                    raise HTTPException(status_code=404, detail="Entity not found")

                return BaseResponse(
                    success=True,
                    message=f"Entity '{entity.name}' updated successfully"
                )
            except HTTPException:
                raise
            except Exception as e:
                self._handle_database_error(e, f"updating entity {entity_id}")

        @self.router.delete("/entities/{entity_id}")
        async def delete_entity(
                entity_id: int,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> BaseResponse:
            """Delete an entity."""
            try:
                result = await self.delete_entity_impl(entity_id, db)
                if not result["success"]:
                    raise HTTPException(status_code=404, detail=result["message"])
                return BaseResponse(**result)
            except HTTPException:
                raise
            except Exception as e:
                self._handle_database_error(e, f"deleting entity {entity_id}")

        @self.router.get("/entities/{entity_type}")
        async def get_entities_by_type(
                entity_type: str,
                db: AsyncSession = Depends(get_db),
                current_user: CurrentSuperuser = None,
        ) -> dict[str, Any]:
            """Get all entities of a specific type for this scope."""
            try:
                entities, type_metadata = await self.get_entities_by_type_impl(entity_type, db)
                return {
                    "success": True,
                    "entities": [
                        {
                            "id": e.id,
                            "name": e.name,
                            "node_type": e.node_type,
                            "image_url": e.image_url,
                            "price_impact_value": str(e.price_impact_value) if e.price_impact_value else None,
                            "description": e.description,
                            "validation_rules": e.validation_rules,
                            "metadata_": e.metadata_,
                        }
                        for e in entities
                    ],
                    "type_metadata": type_metadata,
                }
            except ValueError as e:
                raise HTTPException(status_code=400, detail=str(e))
            except Exception as e:
                self._handle_database_error(e, f"loading {entity_type} entities")

    @abstractmethod
    def _setup_scope_routes(self) -> None:
        """Setup scope-specific routes.
        
        This method should be implemented by each scope to add
        their specific endpoints (e.g., paths for profile, glazing units for glazing).
        """
        pass

    @abstractmethod
    async def create_entity_impl(self, data: EntityCreateRequest, db: AsyncSession) -> Any:
        """Implementation for creating entities.
        
        Args:
            data: Entity creation data
            db: Database session
            
        Returns:
            Created entity
        """
        pass

    @abstractmethod
    async def update_entity_impl(self, entity_id: int, data: EntityUpdateRequest, db: AsyncSession) -> Any:
        """Implementation for updating entities.
        
        Args:
            entity_id: Entity ID to update
            data: Update data
            db: Database session
            
        Returns:
            Updated entity or None if not found
        """
        pass

    @abstractmethod
    async def delete_entity_impl(self, entity_id: int, db: AsyncSession) -> dict[str, Any]:
        """Implementation for deleting entities.
        
        Args:
            entity_id: Entity ID to delete
            db: Database session
            
        Returns:
            Result dict with success status
        """
        pass

    @abstractmethod
    async def get_entities_by_type_impl(self, entity_type: str, db: AsyncSession) -> tuple[list[Any], dict[str, Any]]:
        """Implementation for getting entities by type.
        
        Args:
            entity_type: Type of entities to retrieve
            db: Database session
            
        Returns:
            Tuple of (entities list, type metadata dict)
        """
        pass

    def _handle_database_error(self, error: Exception, operation: str) -> None:
        """Handle database errors with user-friendly messages.
        
        Args:
            error: The exception that occurred
            operation: Description of the operation that failed
        """
        error_msg = str(error)
        
        if "duplicate key" in error_msg.lower() or "already exists" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="An entity with this name already exists. Please use a different name."
            )
        elif "foreign key" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Referenced item not found. Please check your selections and try again."
            )
        elif "invalid input" in error_msg.lower() or "cannot be interpreted" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Invalid data format provided. Please check your input values."
            )
        elif "not null" in error_msg.lower():
            raise HTTPException(
                status_code=400,
                detail="Required field is missing. Please fill in all required information."
            )
        else:
            print(f"[ERROR] Unexpected error {operation}: {error_msg}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to complete operation due to a server error. Please try again or contact support."
            )