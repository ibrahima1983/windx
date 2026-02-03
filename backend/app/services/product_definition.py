"""Relations Service for hierarchical option dependencies.

⚠️  DEPRECATION WARNING: This module is deprecated and will be removed in a future version.
    Please use the new scope-based services in app.services.product_definition instead.

This module provides the RelationsService for managing hierarchical
option dependencies (Company → Material → Opening System → System Series → Colors)
using the existing EAV pattern with AttributeNode and LTREE.

The service now reads definition scopes from the database instead of hard-coded constants,
making the system more flexible and configurable.

Public Classes:
    ProductDefinitionService: Service for managing relation entities and dependency paths (DEPRECATED)
"""

from __future__ import annotations

import logging
import re
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.schemas.definition import ScopeDef
from app.services.base import BaseService

__all__ = ["ProductDefinitionService"]

logger = logging.getLogger("ProductDefinitionService")


# noinspection PyTypeChecker
class ProductDefinitionService(BaseService):
    """Service for managing hierarchical option dependencies.
    
    Manages entities (Company, Material, Opening System, System Series, Color, Unit Type)
    and their dependency paths using the existing AttributeNode model with LTREE.
    
    Definition scopes are now loaded from the database instead of hard-coded constants.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize RelationsService.

        Args:
            db: Database session
        """
        super().__init__(db)
        self._definition_scopes_cache: dict[str, ScopeDef] | None = None

    async def get_definition_scopes(self) -> dict[str, ScopeDef]:
        """Get all definition scopes from the database.
        
        Returns:
            Dictionary mapping scope names to their definitions
        """
        if self._definition_scopes_cache is not None:
            return self._definition_scopes_cache

        # Load scope metadata from database
        scope_stmt = select(AttributeNode).where(
            AttributeNode.node_type == "scope_metadata"
        )
        scope_result = await self.db.execute(scope_stmt)
        scope_nodes = scope_result.scalars().all()

        if not scope_nodes:
            # Fallback to empty dict if no scopes are configured
            print("[WARNING] No product definition scopes found in database. Run setup_product_definitions.py")
            self._definition_scopes_cache = {}
            return self._definition_scopes_cache

        scopes = {}

        for scope_node in scope_nodes:
            scope_name = scope_node.name
            scope_metadata = scope_node.metadata_ or {}

            # Load entity definitions for this scope
            entity_stmt = select(AttributeNode).where(
                and_(
                    AttributeNode.node_type == "entity_definition",
                    AttributeNode.page_type == scope_name
                )
            )
            entity_result = await self.db.execute(entity_stmt)
            entity_nodes = entity_result.scalars().all()

            # Build entities dict
            entities = {}
            for entity_node in entity_nodes:
                entity_metadata = entity_node.metadata_ or {}
                entity_type = entity_metadata.get("entity_type", entity_node.name)

                entities[entity_type] = {
                    "label": entity_metadata.get("label", entity_type.replace('_', ' ').title()),
                    "icon": entity_metadata.get("icon", "pi pi-box"),
                    "placeholders": entity_metadata.get("placeholders", {}),
                    "metadata_fields": entity_metadata.get("metadata_fields", []),
                }

                # Add special_ui if present
                if "special_ui" in entity_metadata:
                    entities[entity_type]["special_ui"] = entity_metadata["special_ui"]

            # Build scope definition
            scopes[scope_name] = {
                "label": scope_metadata.get("label", scope_name.title()),
                "entities": entities,
                "hierarchy": scope_metadata.get("hierarchy", {}),
                "dependencies": scope_metadata.get("dependencies", [])
            }

        self._definition_scopes_cache = scopes
        return scopes

    def clear_definition_scopes_cache(self) -> None:
        """Clear the cached definition scopes to force reload from database."""
        self._definition_scopes_cache = None

    @staticmethod
    def _slugify(name: str) -> str:
        """Convert name to LTREE-safe slug.
        
        Args:
            name: Entity name
            
        Returns:
            LTREE-safe slug (lowercase, underscores, no special chars)
        """
        # Convert to lowercase
        slug = name.lower()
        # Replace spaces and hyphens with underscores
        slug = re.sub(r"[\s\-]+", "_", slug)
        # Remove any characters that aren't alphanumeric or underscore
        slug = re.sub(r"[^a-z0-9_]", "", slug)
        # Remove leading/trailing underscores
        slug = slug.strip("_")
        # Ensure it doesn't start with a number (LTREE requirement)
        if slug and slug[0].isdigit():
            slug = "n" + slug
        return slug or "unnamed"

    async def get_scope_for_entity(self, entity_type: str) -> str:
        """Resolve definition scope for an entity type."""
        scopes = await self.get_definition_scopes()
        for scope, data in scopes.items():
            if entity_type in data["entities"]:
                return scope
        return "profile"  # Default fallback

    async def get_hierarchy_level(self, entity_type: str) -> int:
        """Get hierarchy level for an entity type within its scope."""
        scope = await self.get_scope_for_entity(entity_type)
        scopes = await self.get_definition_scopes()
        hierarchy = scopes[scope]["hierarchy"]
        # Reverse lookup level by type
        for level, type_name in hierarchy.items():
            if type_name == entity_type:
                # Ensure we return an integer, not a string
                return int(level)
        return 0  # Default to root if not in hierarchy

    async def create_entity(
            self,
            entity_type: str,
            name: str,
            image_url: str | None = None,
            price_from: Decimal | None = None,
            description: str | None = None,
            metadata: dict[str, Any] | None = None,
    ) -> AttributeNode:
        """Create a new relation entity.
        
        Args:
            entity_type: Type of entity (company, material, etc.)
            name: Entity name
            image_url: Optional image/logo URL
            price_from: Optional "from €XX" price
            description: Optional description
            metadata: Optional extra metadata (density, u_value, etc.)
            
        Returns:
            Created AttributeNode
            
        Raises:
            ValueError: If entity_type is invalid
        """
        # Resolve scope
        scope = await self.get_scope_for_entity(entity_type)
        scopes = await self.get_definition_scopes()
        scope_data = scopes.get(scope)

        if not scope_data or entity_type not in scope_data["entities"]:
            # Fallback check against old metadata for backward compat or fail
            raise ValueError(f"Invalid entity type: {entity_type}")

        # Get entity definition
        entity_def = scope_data["entities"][entity_type]

        # Determine depth based on hierarchy
        depth = await self.get_hierarchy_level(entity_type)

        # Build LTREE path (just the slug for standalone entities)
        slug = self._slugify(name)

        # Build validation_rules with metadata
        validation_rules = {"is_relation_entity": True}
        if metadata:
            # Validate against allowed metadata fields
            allowed_fields = entity_def.get("metadata_fields", [])
            # Extract names if they are objects
            field_names = [f["name"] if isinstance(f, dict) else f for f in allowed_fields]

            for key in field_names:
                if key in metadata:
                    validation_rules[key] = metadata[key]

        # Get UI metadata for this entity type (constructed from definition)
        ui_metadata = {
            "label": entity_def.get("label", entity_type),
            "icon": entity_def.get("icon", "pi pi-box"),
            "help_text": f"Define {entity_type} for {scope}",
            # Add placeholders based on name convention if needed
            "name_placeholder": f"e.g. {entity_def.get('label')} Name",
            "description_placeholder": f"Optional description for {entity_def.get('label')}"
        }

        # Merge provided metadata into ui_metadata so it is stored in the metadata_ column
        # This is critical for Dependency Engine fields (linked_company_material, etc.)
        if metadata:
            ui_metadata.update(metadata)

        # Create the entity
        entity = AttributeNode(
            name=name,
            node_type=entity_type,
            data_type="string",
            ltree_path=slug,
            depth=depth,
            image_url=image_url,
            price_impact_value=price_from,
            price_impact_type="fixed" if price_from else "fixed",
            description=description,
            validation_rules=validation_rules,
            metadata_=ui_metadata,
            page_type=scope,  # Use scope as page_type
        )

        self.db.add(entity)
        await self.commit()
        await self.refresh(entity)
        return entity

    async def update_entity(
            self,
            entity_id: int,
            name: str | None = None,
            image_url: str | None = None,
            price_from: Decimal | None = None,
            description: str | None = None,
            metadata: dict[str, Any] | None = None,
    ) -> AttributeNode | None:
        """Update an existing relation entity.
        
        Args:
            entity_id: Entity ID
            name: Optional new name
            image_url: Optional new image URL
            price_from: Optional new price
            description: Optional new description
            metadata: Optional metadata containing validation_rules and other metadata
            
        Returns:
            Updated AttributeNode or None if not found
        """
        logger.info(f"Updating entity {entity_id}", extra={
            "entity_id": entity_id,
            "name": name,
            "image_url": image_url,
            "price_from": price_from,
            "description": description,
            "metadata": metadata
        })

        result = await self.db.execute(
            select(AttributeNode).where(AttributeNode.id == entity_id)
        )
        entity = result.scalar_one_or_none()

        if not entity:
            logger.warning(f"Entity {entity_id} not found for update")
            return None

        logger.debug(f"Found entity {entity_id}: {entity.name} (type: {entity.node_type})")

        if name is not None:
            old_name = entity.name
            entity.name = name
            logger.debug(f"Updated name: {old_name} -> {name}")
            # Update slug in ltree_path if it's a standalone entity
            if "." not in entity.ltree_path:
                old_path = entity.ltree_path
                entity.ltree_path = self._slugify(name)
                logger.debug(f"Updated ltree_path: {old_path} -> {entity.ltree_path}")

        if image_url is not None:
            old_url = entity.image_url
            entity.image_url = image_url
            logger.debug(f"Updated image_url: {old_url} -> {image_url}")

        if price_from is not None:
            old_price = entity.price_impact_value
            entity.price_impact_value = price_from
            logger.debug(f"Updated price_impact_value: {old_price} -> {price_from}")

        if description is not None:
            old_desc = entity.description
            entity.description = description
            logger.debug(f"Updated description: {old_desc} -> {description}")

        if metadata is not None:
            # Handle validation_rules separately
            if "validation_rules" in metadata:
                old_rules = entity.validation_rules or {}
                current_rules = old_rules.copy()
                current_rules.update(metadata["validation_rules"])
                entity.validation_rules = current_rules
                logger.debug(f"Updated validation_rules: {old_rules} -> {current_rules}")

            # Handle other metadata (excluding validation_rules)
            other_metadata = {k: v for k, v in metadata.items() if k != "validation_rules"}
            if other_metadata:
                old_meta = entity.metadata_ or {}
                current_meta = old_meta.copy()
                current_meta.update(other_metadata)
                entity.metadata_ = current_meta
                logger.debug(f"Updated metadata_: {old_meta} -> {current_meta}")

        await self.commit()
        await self.refresh(entity)

        logger.info(f"Successfully updated entity {entity_id}: {entity.name}")
        return entity

    async def delete_entity(self, entity_id: int) -> dict[str, Any]:
        """Delete a relation entity.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Result dict with success status
        """
        result = await self.db.execute(
            select(AttributeNode).where(AttributeNode.id == entity_id)
        )
        entity = result.scalar_one_or_none()

        if not entity:
            return {"success": False, "message": "Entity not found"}

        await self.db.delete(entity)
        await self.commit()
        return {"success": True, "message": f"Entity '{entity.name}' deleted"}

    async def get_entities_by_type(self, entity_type: str, scope: str = None) -> list[AttributeNode]:
        """Get all entities of a specific type.
        
        Args:
            entity_type: Type of entity (company, material, etc.)
            scope: Optional scope filter (profile, glazing, etc.). If None, inferred from type.
            
        Returns:
            List of AttributeNode entities
        """
        # Resolve scope if not provided (though filtering by type usually implies scope)
        if not scope:
            scope = await self.get_scope_for_entity(entity_type)

        result = await self.db.execute(
            select(AttributeNode)
            .where(
                and_(
                    AttributeNode.node_type == entity_type,
                    AttributeNode.page_type == scope,
                )
            )
            .order_by(AttributeNode.name)
        )
        return list(result.scalars().all())

    async def get_entity_by_id(self, entity_id: int) -> AttributeNode | None:
        """Get entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            AttributeNode or None
        """
        result = await self.db.execute(
            select(AttributeNode).where(AttributeNode.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_all_entities(self) -> dict[str, list[AttributeNode]]:
        """Get all relation entities grouped by type.
        
        Returns:
            Dict mapping entity type to list of entities
        """
        entities = {}
        # Iterate over all scopes and their entities
        scopes = await self.get_definition_scopes()
        for scope_data in scopes.values():
            for entity_type in scope_data["entities"]:
                entities[entity_type] = await self.get_entities_by_type(entity_type)
        return entities

    async def create_dependency_path(
            self,
            company_id: int,
            material_id: int,
            opening_system_id: int,
            system_series_id: int,
            color_id: int,
    ) -> AttributeNode:
        """Create a complete dependency path.
        
        Creates LTREE path: company.material.opening_system.system_series.color
        
        Args:
            company_id: Company entity ID
            material_id: Material entity ID
            opening_system_id: Opening System entity ID
            system_series_id: System Series entity ID
            color_id: Color entity ID
            
        Returns:
            Created path node (the leaf color node with full path)
            
        Raises:
            ValueError: If any entity not found or invalid type
        """
        # Fetch all entities
        entities = {}
        for entity_id, expected_type in [
            (company_id, "company"),
            (material_id, "material"),
            (opening_system_id, "opening_system"),
            (system_series_id, "system_series"),
            (color_id, "color"),
        ]:
            result = await self.db.execute(
                select(AttributeNode).where(AttributeNode.id == entity_id)
            )
            entity = result.scalar_one_or_none()
            if not entity:
                raise ValueError(f"{expected_type.replace('_', ' ').title()} with ID {entity_id} not found")
            if entity.node_type != expected_type:
                raise ValueError(f"Entity {entity_id} is not a {expected_type}")
            entities[expected_type] = entity

        # Build the LTREE path
        path_parts = [
            self._slugify(entities["company"].name),
            self._slugify(entities["material"].name),
            self._slugify(entities["opening_system"].name),
            self._slugify(entities["system_series"].name),
            self._slugify(entities["color"].name),
        ]
        full_path = ".".join(path_parts)

        # Check if path already exists
        result = await self.db.execute(
            select(AttributeNode).where(
                and_(
                    AttributeNode.ltree_path == full_path,
                    AttributeNode.page_type == "profile",
                )
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            raise ValueError(f"Path already exists: {full_path}")

        # Create intermediate nodes if they don't exist
        await self._ensure_path_nodes(entities, path_parts)

        # Create the leaf node (color with full path)
        color_entity = entities["color"]
        path_node = AttributeNode(
            name=color_entity.name,
            node_type="color_path",  # Mark as path node
            data_type="string",
            ltree_path=full_path,
            depth=4,
            image_url=color_entity.image_url,
            price_impact_value=color_entity.price_impact_value,
            price_impact_type="fixed",
            description=f"Path: {' → '.join([e.name for e in entities.values()])}",
            validation_rules={
                "is_dependency_path": True,
                "company_id": company_id,
                "material_id": material_id,
                "opening_system_id": opening_system_id,
                "system_series_id": system_series_id,
                "color_id": color_id,
            },
            page_type="profile",
        )

        self.db.add(path_node)

        # NEW: Synchronize metadata to the standalone system_series entity to support auto-fill
        # Find the standalone system_series entity
        series_entity = entities["system_series"]
        series_metadata = series_entity.metadata_ or {}

        # Inject parent NAMES for frontend auto-fill logic
        series_updated = False
        company_name = entities["company"].name
        opening_name = entities["opening_system"].name
        material_name = entities["material"].name

        if series_metadata.get("linked_company_material") != company_name:
            series_metadata["linked_company_material"] = company_name
            series_updated = True

        if series_metadata.get("opening_system_id") != opening_name:
            series_metadata["opening_system_id"] = opening_name
            series_updated = True

        if series_metadata.get("linked_material_id") != material_name:
            series_metadata["linked_material_id"] = material_name
            series_updated = True

        if series_updated:
            series_entity.metadata_ = series_metadata

        await self.commit()
        await self.refresh(path_node)
        return path_node

    async def _ensure_path_nodes(
            self,
            entities: dict[str, AttributeNode],
            path_parts: list[str],
    ) -> None:
        """Ensure intermediate path nodes exist.
        
        Creates nodes for each level of the path if they don't exist.
        """
        # Get profile hierarchy
        scopes = await self.get_definition_scopes()
        hierarchy = scopes["profile"]["hierarchy"]

        # Create intermediate paths (company, company.material, etc.)
        for depth in range(4):  # 0 to 3 (not including the leaf)
            partial_path = ".".join(path_parts[:depth + 1])
            entity_type = hierarchy[str(depth)]  # Convert depth to string for dictionary lookup
            entity = entities[entity_type]

            # Check if this path node exists
            result = await self.db.execute(
                select(AttributeNode).where(
                    and_(
                        AttributeNode.ltree_path == partial_path,
                        AttributeNode.page_type == "profile",
                        AttributeNode.node_type == f"{entity_type}_path",
                    )
                )
            )
            existing = result.scalar_one_or_none()

            if not existing:
                # Create the path node
                path_node = AttributeNode(
                    name=entity.name,
                    node_type=f"{entity_type}_path",
                    data_type="string",
                    ltree_path=partial_path,
                    depth=depth,
                    image_url=entity.image_url,
                    price_impact_value=entity.price_impact_value,
                    price_impact_type="fixed",
                    validation_rules={
                        "is_dependency_path": True,
                        f"{entity_type}_id": entity.id,
                    },
                    page_type="profile",
                )
                self.db.add(path_node)

    async def delete_dependency_path(self, ltree_path: str) -> dict[str, Any]:
        """Delete a dependency path and its descendants.
        
        Args:
            ltree_path: LTREE path to delete
            
        Returns:
            Result dict with success status
        """
        # Delete all nodes with this path or descendants

        # Use LTREE operator to find path and descendants
        result = await self.db.execute(
            select(AttributeNode).where(
                and_(
                    AttributeNode.page_type == "profile",
                    or_(
                        AttributeNode.ltree_path == ltree_path,
                        # Use text for LTREE descendant operator
                        AttributeNode.ltree_path.op("<@")(ltree_path),
                    ),
                )
            )
        )
        nodes = list(result.scalars().all())

        if not nodes:
            return {"success": False, "message": "Path not found"}

        for node in nodes:
            await self.db.delete(node)

        await self.commit()
        return {"success": True, "message": f"Deleted {len(nodes)} path node(s)"}

    async def get_path_details(self, path_id: int) -> dict[str, Any] | None:
        """Get detailed path information with all related entities.
        
        Args:
            path_id: Path node ID
            
        Returns:
            Dict with path info and all related entity details, or None if not found
        """
        # Get the path node
        result = await self.db.execute(
            select(AttributeNode).where(AttributeNode.id == path_id)
        )
        path_node = result.scalar_one_or_none()

        if not path_node:
            return None

        # Extract entity IDs from validation_rules
        rules = path_node.validation_rules or {}
        entity_ids = {
            "company_id": rules.get("company_id"),
            "material_id": rules.get("material_id"),
            "opening_system_id": rules.get("opening_system_id"),
            "system_series_id": rules.get("system_series_id"),
            "color_id": rules.get("color_id"),
        }

        # Load all related entities
        entities = {}
        for entity_type, entity_id in entity_ids.items():
            if entity_id:
                entity_type_name = entity_type.replace("_id", "")
                entity = await self.get_entity_by_id(entity_id)
                if entity:
                    entities[entity_type_name] = {
                        "id": entity.id,
                        "name": entity.name,
                        "description": entity.description,
                        "image_url": entity.image_url,
                        "price_impact_value": str(entity.price_impact_value) if entity.price_impact_value else "0.00",
                        "validation_rules": entity.validation_rules or {},
                        "metadata_": entity.metadata_ or {},
                        "node_type": entity.node_type,
                    }

        # Handle grouped colors (if this is a grouped path)
        if path_node.node_type == "color_path" and "color" in entities:
            # For now, just wrap single color in array
            # In a real grouped scenario, you'd load all colors in the group
            entities["colors"] = [entities.pop("color")]

        return {
            "id": path_node.id,
            "ltree_path": path_node.ltree_path,
            "display_path": path_node.description or path_node.ltree_path,
            "created_at": path_node.created_at.isoformat() if path_node.created_at else None,
            "updated_at": path_node.updated_at.isoformat() if path_node.updated_at else None,
            "entities": entities,
            "validation_rules": path_node.validation_rules or {},
        }

    async def get_all_paths(self) -> list[dict[str, Any]]:
        """Get all complete dependency paths.
        
        Returns:
            List of path dicts with entity names and IDs
        """
        # Get all leaf nodes (color_path with depth 4)
        result = await self.db.execute(
            select(AttributeNode).where(
                and_(
                    AttributeNode.node_type == "color_path",
                    AttributeNode.page_type == "profile",
                    AttributeNode.depth == 4,
                )
            ).order_by(AttributeNode.ltree_path)
        )
        path_nodes = list(result.scalars().all())

        paths = []
        for node in path_nodes:
            rules = node.validation_rules or {}
            path_parts = node.ltree_path.split(".")
            paths.append({
                "id": node.id,
                "ltree_path": node.ltree_path,
                "display_path": node.description or " → ".join(path_parts),
                "company_id": rules.get("company_id"),
                "material_id": rules.get("material_id"),
                "opening_system_id": rules.get("opening_system_id"),
                "system_series_id": rules.get("system_series_id"),
                "color_id": rules.get("color_id"),
            })

        return paths

    async def get_dependent_options(
            self,
            parent_selections: dict[str, int | None],
    ) -> dict[str, list[dict[str, Any]]]:
        """Get available options based on parent selections.
        
        Used for cascading dropdowns in profile entry.
        
        Hierarchy: company → material → opening_system → system_series → color
        
        Args:
            parent_selections: Dict of entity_type_id -> selected entity ID
                e.g., {"company_id": 1, "material_id": 2}
                
        Returns:
            Dict of entity_type -> list of available options
        """
        result = {}

        # Get all complete paths (leaf nodes)
        all_paths = await self.get_all_paths()

        # Extract selection values
        company_id = parent_selections.get("company_id")
        material_id = parent_selections.get("material_id")
        opening_system_id = parent_selections.get("opening_system_id")
        system_series_id = parent_selections.get("system_series_id")

        # Special case: If only system_series_id is provided, find all related options
        if system_series_id and not any([company_id, material_id, opening_system_id]):
            # Filter paths by system series
            filtered_paths = [p for p in all_paths if p.get("system_series_id") == system_series_id]

            if filtered_paths:
                # Get unique companies from filtered paths
                company_ids = {p.get("company_id") for p in filtered_paths if p.get("company_id")}
                companies = await self.get_entities_by_type("company")
                result["company"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in companies if e.id in company_ids
                ]

                # Get unique materials from filtered paths
                material_ids = {p.get("material_id") for p in filtered_paths if p.get("material_id")}
                materials = await self.get_entities_by_type("material")
                result["material"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in materials if e.id in material_ids
                ]

                # Get unique opening systems from filtered paths
                opening_ids = {p.get("opening_system_id") for p in filtered_paths if p.get("opening_system_id")}
                openings = await self.get_entities_by_type("opening_system")
                result["opening_system"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in openings if e.id in opening_ids
                ]

                # Get unique colors from filtered paths
                color_ids = {p.get("color_id") for p in filtered_paths if p.get("color_id")}
                colors = await self.get_entities_by_type("color")
                result["colors"] = [  # Note: using "colors" (plural) to match frontend expectation
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in colors if e.id in color_ids
                ]

            return result

        # Standard forward hierarchy logic
        # Always return all companies
        companies = await self.get_entities_by_type("company")
        result["company"] = [
            {"id": e.id, "name": e.name, "image_url": e.image_url}
            for e in companies
        ]

        # Filter paths by company
        if company_id:
            filtered_paths = [p for p in all_paths if p.get("company_id") == company_id]

            # Get unique materials from filtered paths
            material_ids = {p.get("material_id") for p in filtered_paths if p.get("material_id")}
            materials = await self.get_entities_by_type("material")
            result["material"] = [
                {"id": e.id, "name": e.name, "image_url": e.image_url}
                for e in materials if e.id in material_ids
            ]

            # Filter by material
            if material_id:
                filtered_paths = [p for p in filtered_paths if p.get("material_id") == material_id]

                # Get unique opening systems from filtered paths
                opening_ids = {p.get("opening_system_id") for p in filtered_paths if p.get("opening_system_id")}
                openings = await self.get_entities_by_type("opening_system")
                result["opening_system"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in openings if e.id in opening_ids
                ]

                # Filter by opening system
                if opening_system_id:
                    filtered_paths = [p for p in filtered_paths if p.get("opening_system_id") == opening_system_id]

                    # Get unique system series from filtered paths
                    series_ids = {p.get("system_series_id") for p in filtered_paths if p.get("system_series_id")}
                    series = await self.get_entities_by_type("system_series")
                    result["system_series"] = [
                        {"id": e.id, "name": e.name, "image_url": e.image_url}
                        for e in series if e.id in series_ids
                    ]

                    # Filter by system series
                    if system_series_id:
                        filtered_paths = [p for p in filtered_paths if p.get("system_series_id") == system_series_id]

                        # Get unique colors from filtered paths
                        color_ids = {p.get("color_id") for p in filtered_paths if p.get("color_id")}
                        colors = await self.get_entities_by_type("color")
                        result["colors"] = [  # Note: using "colors" (plural) to match frontend expectation
                            {"id": e.id, "name": e.name, "image_url": e.image_url}
                            for e in colors if e.id in color_ids
                        ]

        return result
