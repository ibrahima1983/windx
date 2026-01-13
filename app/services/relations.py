"""Relations Service for hierarchical option dependencies.

This module provides the RelationsService for managing hierarchical
option dependencies (Company → Material → Opening System → System Series → Colors)
using the existing EAV pattern with AttributeNode and LTREE.

Public Classes:
    RelationsService: Service for managing relation entities and dependency paths
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any

from sqlalchemy import select, and_, or_, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attribute_node import AttributeNode
from app.services.base import BaseService

__all__ = ["RelationsService"]


class RelationsService(BaseService):
    """Service for managing hierarchical option dependencies.
    
    Manages entities (Company, Material, Opening System, System Series, Color, Unit Type)
    and their dependency paths using the existing AttributeNode model with LTREE.
    
    Hierarchy Levels:
        0: Company
        1: Material
        2: Opening System
        3: System Series
        4: Color
        
    Unit Type is independent (no hierarchy).
    """
    
    # Hierarchy levels mapping
    RELATION_LEVELS = {
        0: "company",
        1: "material",
        2: "opening_system",
        3: "system_series",
        4: "color",
    }
    
    LEVEL_BY_TYPE = {v: k for k, v in RELATION_LEVELS.items()}
    
    # Entity types with their metadata fields (stored in validation_rules JSONB)
    ENTITY_METADATA = {
        "company": [],  # No extra metadata, just name, image_url, price_impact_value
        "material": ["density"],
        "opening_system": [],  # Uses description field
        "system_series": ["width", "number_of_chambers", "u_value", "number_of_seals", "characteristics"],
        "color": ["code", "has_lamination"],
        "unit_type": [],  # Independent, uses description field
    }
    
    def __init__(self, db: AsyncSession) -> None:
        """Initialize RelationsService.
        
        Args:
            db: Database session
        """
        super().__init__(db)
    
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
        if entity_type not in self.ENTITY_METADATA:
            raise ValueError(f"Invalid entity type: {entity_type}")
        
        # Determine depth based on entity type
        depth = self.LEVEL_BY_TYPE.get(entity_type, 0)
        
        # Build LTREE path (just the slug for standalone entities)
        slug = self._slugify(name)
        
        # Build validation_rules with metadata
        validation_rules = {"is_relation_entity": True}
        if metadata:
            for key in self.ENTITY_METADATA.get(entity_type, []):
                if key in metadata:
                    validation_rules[key] = metadata[key]
        
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
            page_type="relations",  # Mark as relations entity
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
            metadata: Optional new metadata
            
        Returns:
            Updated AttributeNode or None if not found
        """
        result = await self.db.execute(
            select(AttributeNode).where(AttributeNode.id == entity_id)
        )
        entity = result.scalar_one_or_none()
        
        if not entity:
            return None
        
        if name is not None:
            entity.name = name
            # Update slug in ltree_path if it's a standalone entity
            if "." not in entity.ltree_path:
                entity.ltree_path = self._slugify(name)
        
        if image_url is not None:
            entity.image_url = image_url
        
        if price_from is not None:
            entity.price_impact_value = price_from
        
        if description is not None:
            entity.description = description
        
        if metadata is not None:
            current_rules = entity.validation_rules or {}
            current_rules.update(metadata)
            entity.validation_rules = current_rules
        
        await self.commit()
        await self.refresh(entity)
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
    
    async def get_entities_by_type(self, entity_type: str) -> list[AttributeNode]:
        """Get all entities of a specific type.
        
        Args:
            entity_type: Type of entity (company, material, etc.)
            
        Returns:
            List of AttributeNode entities
        """
        result = await self.db.execute(
            select(AttributeNode)
            .where(
                and_(
                    AttributeNode.node_type == entity_type,
                    AttributeNode.page_type == "relations",
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
        for entity_type in self.ENTITY_METADATA:
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
                    AttributeNode.page_type == "relations",
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
            page_type="relations",
        )
        
        self.db.add(path_node)
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
        # Create intermediate paths (company, company.material, etc.)
        for depth in range(4):  # 0 to 3 (not including the leaf)
            partial_path = ".".join(path_parts[:depth + 1])
            entity_type = self.RELATION_LEVELS[depth]
            entity = entities[entity_type]
            
            # Check if this path node exists
            result = await self.db.execute(
                select(AttributeNode).where(
                    and_(
                        AttributeNode.ltree_path == partial_path,
                        AttributeNode.page_type == "relations",
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
                    page_type="relations",
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
        from sqlalchemy import text
        
        # Use LTREE operator to find path and descendants
        result = await self.db.execute(
            select(AttributeNode).where(
                and_(
                    AttributeNode.page_type == "relations",
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
                    AttributeNode.page_type == "relations",
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
                company_ids = set(p.get("company_id") for p in filtered_paths if p.get("company_id"))
                companies = await self.get_entities_by_type("company")
                result["company"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in companies if e.id in company_ids
                ]
                
                # Get unique materials from filtered paths
                material_ids = set(p.get("material_id") for p in filtered_paths if p.get("material_id"))
                materials = await self.get_entities_by_type("material")
                result["material"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in materials if e.id in material_ids
                ]
                
                # Get unique opening systems from filtered paths
                opening_ids = set(p.get("opening_system_id") for p in filtered_paths if p.get("opening_system_id"))
                openings = await self.get_entities_by_type("opening_system")
                result["opening_system"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in openings if e.id in opening_ids
                ]
                
                # Get unique colors from filtered paths
                color_ids = set(p.get("color_id") for p in filtered_paths if p.get("color_id"))
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
            material_ids = set(p.get("material_id") for p in filtered_paths if p.get("material_id"))
            materials = await self.get_entities_by_type("material")
            result["material"] = [
                {"id": e.id, "name": e.name, "image_url": e.image_url}
                for e in materials if e.id in material_ids
            ]
            
            # Filter by material
            if material_id:
                filtered_paths = [p for p in filtered_paths if p.get("material_id") == material_id]
                
                # Get unique opening systems from filtered paths
                opening_ids = set(p.get("opening_system_id") for p in filtered_paths if p.get("opening_system_id"))
                openings = await self.get_entities_by_type("opening_system")
                result["opening_system"] = [
                    {"id": e.id, "name": e.name, "image_url": e.image_url}
                    for e in openings if e.id in opening_ids
                ]
                
                # Filter by opening system
                if opening_system_id:
                    filtered_paths = [p for p in filtered_paths if p.get("opening_system_id") == opening_system_id]
                    
                    # Get unique system series from filtered paths
                    series_ids = set(p.get("system_series_id") for p in filtered_paths if p.get("system_series_id"))
                    series = await self.get_entities_by_type("system_series")
                    result["system_series"] = [
                        {"id": e.id, "name": e.name, "image_url": e.image_url}
                        for e in series if e.id in series_ids
                    ]
                    
                    # Filter by system series
                    if system_series_id:
                        filtered_paths = [p for p in filtered_paths if p.get("system_series_id") == system_series_id]
                        
                        # Get unique colors from filtered paths
                        color_ids = set(p.get("color_id") for p in filtered_paths if p.get("color_id"))
                        colors = await self.get_entities_by_type("color")
                        result["colors"] = [  # Note: using "colors" (plural) to match frontend expectation
                            {"id": e.id, "name": e.name, "image_url": e.image_url}
                            for e in colors if e.id in color_ids
                        ]
        
        return result
