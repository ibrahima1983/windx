"""Profile scope setup script.

This script migrates the existing profile setup logic into the new scope-based architecture.
It creates profile scope metadata and seeds sample profile data.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .base import BaseProductDefinitionSetup
from app.models.attribute_node import AttributeNode
from app.services.product_definition.factory import ProductDefinitionServiceFactory


class ProfileSetup(BaseProductDefinitionSetup):
    """Setup script for profile scope with hierarchical dependencies."""

    def __init__(self):
        super().__init__("profile")

    async def create_scope_metadata(self, db: AsyncSession) -> None:
        """Create profile scope metadata."""
        print(f"  [METADATA] Creating scope metadata for {self.scope}")
        
        # Clean existing scope data first
        await self._clean_existing_scope_data(db)
        
        # Create scope metadata node
        scope_metadata = {
            "scope": "profile",
            "label": "Profile System",
            "description": "Hierarchical profile system with dependencies",
            "hierarchy": {
                "0": "company",
                "1": "material", 
                "2": "opening_system",
                "3": "system_series",
                "4": "color"
            },
            "dependencies": [
                {
                    "parent": "company",
                    "child": "material",
                    "type": "one_to_many"
                },
                {
                    "parent": "material", 
                    "child": "opening_system",
                    "type": "one_to_many"
                },
                {
                    "parent": "opening_system",
                    "child": "system_series", 
                    "type": "one_to_many"
                },
                {
                    "parent": "system_series",
                    "child": "color",
                    "type": "one_to_many"
                }
            ],
            "entity_count": 5
        }
        
        scope_node = AttributeNode(
            name="profile",
            display_name="Profile System",
            description="Hierarchical profile system with cascading dependencies",
            node_type="scope_metadata",
            data_type="object",
            ltree_path="definitions.profile",
            depth=1,
            page_type="profile",
            metadata_=scope_metadata,
            validation_rules={
                "is_scope_metadata": True,
                "scope": "profile"
            }
        )
        
        db.add(scope_node)
        await db.flush()
        print(f"  [METADATA] Created scope metadata (ID: {scope_node.id})")
        
        # Create entity definitions
        await self._create_entity_definitions(db)
        await db.commit()

    async def _clean_existing_scope_data(self, db: AsyncSession) -> None:
        """Clean existing data for profile scope."""
        print(f"  [CLEAN] Cleaning existing data for scope: {self.scope}")
        
        # Delete existing definition metadata nodes for this scope
        delete_stmt = delete(AttributeNode).where(
            AttributeNode.page_type == self.scope,
            AttributeNode.node_type.in_(['scope_metadata', 'entity_definition'])
        )
        result = await db.execute(delete_stmt)
        deleted_count = result.rowcount
        
        await db.commit()
        print(f"  [CLEAN] Deleted {deleted_count} existing definition records")

    async def _create_entity_definitions(self, db: AsyncSession) -> None:
        """Create entity definition records for profile scope."""
        print(f"  [ENTITIES] Creating entity definitions for {self.scope}")
        
        # Define profile entities with their metadata
        entities = {
            "company": {
                "label": "Company",
                "icon": "pi pi-building",
                "placeholders": {
                    "name": "Enter company name (e.g., Komben)"
                },
                "metadata_fields": [
                    {"name": "website", "type": "text", "label": "Website"},
                    {"name": "contact_email", "type": "email", "label": "Contact Email"}
                ]
            },
            "material": {
                "label": "Material",
                "icon": "pi pi-box",
                "placeholders": {
                    "name": "Enter material type (e.g., UPVC, Aluminum)"
                },
                "metadata_fields": [
                    {"name": "density", "type": "number", "label": "Density (kg/m³)"},
                    {"name": "thermal_conductivity", "type": "number", "label": "Thermal Conductivity"}
                ]
            },
            "opening_system": {
                "label": "Opening System",
                "icon": "pi pi-arrows-alt",
                "placeholders": {
                    "name": "Enter opening system (e.g., Casement, Sliding)"
                },
                "metadata_fields": [
                    {"name": "operation_type", "type": "text", "label": "Operation Type"},
                    {"name": "max_sash_weight", "type": "number", "label": "Max Sash Weight (kg)"}
                ]
            },
            "system_series": {
                "label": "System Series",
                "icon": "pi pi-list",
                "placeholders": {
                    "name": "Enter system series (e.g., K700, K600)"
                },
                "metadata_fields": [
                    {"name": "profile_depth", "type": "number", "label": "Profile Depth (mm)"},
                    {"name": "chambers", "type": "number", "label": "Number of Chambers"}
                ]
            },
            "color": {
                "label": "Color",
                "icon": "pi pi-palette",
                "placeholders": {
                    "name": "Enter color name (e.g., White, Red)"
                },
                "metadata_fields": [
                    {"name": "color_code", "type": "text", "label": "Color Code"},
                    {"name": "finish_type", "type": "text", "label": "Finish Type"}
                ]
            }
        }
        
        for entity_type, config in entities.items():
            await self._create_entity_definition(db, entity_type, config)

    async def _create_entity_definition(self, db: AsyncSession, entity_type: str, config: Dict[str, Any]) -> None:
        """Create a single entity definition record."""
        print(f"    [ENTITY] Creating definition for {entity_type}")
        
        label = config.get('label', entity_type.replace('_', ' ').title())
        icon = config.get('icon', 'pi pi-box')
        placeholders = config.get('placeholders', {})
        metadata_fields = config.get('metadata_fields', [])
        
        # Create entity definition node
        entity_node = AttributeNode(
            name=entity_type,
            display_name=label,
            description=f"Entity definition for {label}",
            node_type="entity_definition",
            data_type="object",
            ltree_path=f"definitions.profile.{entity_type}",
            depth=2,
            page_type="profile",
            metadata_={
                "entity_type": entity_type,
                "label": label,
                "icon": icon,
                "placeholders": placeholders,
                "metadata_fields": metadata_fields,
                "scope": "profile"
            },
            validation_rules={
                "is_entity_definition": True,
                "entity_type": entity_type,
                "scope": "profile"
            }
        )
        
        db.add(entity_node)
        await db.flush()
        print(f"    [ENTITY] Created {entity_type} definition (ID: {entity_node.id})")

    async def seed_sample_data(self, db: AsyncSession) -> None:
        """Seed sample profile data."""
        print(f"  [SEED] Seeding sample data for {self.scope}")
        
        # Get the profile service
        service = ProductDefinitionServiceFactory.get_service("profile", db)
        
        # Import the required types
        from app.services.product_definition.types import EntityCreateData
        
        # Define entities to create
        entities_to_create = {
            "company": ["Komben"],
            "material": ["UPVC", "Aluminum"],
            "opening_system": ["Casement", "Sliding"],
            "system_series": ["K700", "K600", "K701", "K800"],
            "color": ["White", "Red", "Green", "Blue"],
        }
        
        # Store created entity IDs
        entity_ids = {}
        
        # Create entities
        for entity_type, names in entities_to_create.items():
            entity_ids[entity_type] = {}
            print(f"    [ENTITIES] Creating {entity_type} entities...")
            
            for name in names:
                try:
                    entity_data = EntityCreateData(
                        entity_type=entity_type,
                        name=name,
                    )
                    entity = await service.create_entity(entity_data)
                    entity_ids[entity_type][name] = entity.id
                    print(f"       ✅ Created: {name} (ID: {entity.id})")
                except ValueError as e:
                    # Entity might already exist, try to find it
                    print(f"       ⚠️  {name}: {e}")
                    existing = await service.get_entities(entity_type)
                    for ent in existing:
                        if ent.name == name:
                            entity_ids[entity_type][name] = ent.id
                            print(f"       📌 Found existing: {name} (ID: {ent.id})")
                            break
        
        # Create dependency paths
        print(f"    [PATHS] Creating dependency paths...")
        
        # Import the required types
        from app.services.product_definition.types import ProfilePathData
        
        # Define paths to create
        # Format: (company, material, opening_system, system_series, color)
        paths_to_create = [
            ("Komben", "UPVC", "Casement", "K700", "White"),
            ("Komben", "UPVC", "Casement", "K600", "Red"),
            ("Komben", "Aluminum", "Casement", "K701", "Green"),
            ("Komben", "Aluminum", "Sliding", "K800", "Blue"),
        ]
        
        for path in paths_to_create:
            company, material, opening_system, system_series, color = path
            path_str = f"{company} → {material} → {opening_system} → {system_series} → {color}"
            
            try:
                # Get IDs
                company_id = entity_ids["company"].get(company)
                material_id = entity_ids["material"].get(material)
                opening_system_id = entity_ids["opening_system"].get(opening_system)
                system_series_id = entity_ids["system_series"].get(system_series)
                color_id = entity_ids["color"].get(color)
                
                if not all([company_id, material_id, opening_system_id, system_series_id, color_id]):
                    print(f"       ❌ Missing entity IDs for path: {path_str}")
                    continue
                
                path_data = ProfilePathData(
                    company_id=company_id,
                    material_id=material_id,
                    opening_system_id=opening_system_id,
                    system_series_id=system_series_id,
                    color_id=color_id,
                )
                path_node = await service.create_dependency_path(path_data)
                print(f"       ✅ Created path: {path_str}")
                
            except ValueError as e:
                print(f"       ⚠️  Path exists or error: {path_str} - {e}")
        
        await db.commit()
        print(f"  [SEED] Sample data seeding complete")


# Script execution
if __name__ == "__main__":
    from .base import run_async_script
    
    async def main():
        setup = ProfileSetup()
        await setup.run_setup()
    
    run_async_script(main())