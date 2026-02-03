"""Glazing scope setup script.

This script creates the glazing scope metadata and seeds sample glazing data.
The glazing system uses a compositional structure rather than hierarchical dependencies.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from .base import BaseProductDefinitionSetup
from app.models.attribute_node import AttributeNode
from app.services.product_definition.factory import ProductDefinitionServiceFactory


class GlazingSetup(BaseProductDefinitionSetup):
    """Setup script for glazing scope with compositional structure."""

    def __init__(self):
        super().__init__("glazing")

    async def create_scope_metadata(self, db: AsyncSession) -> None:
        """Create glazing scope metadata."""
        print(f"  [METADATA] Creating scope metadata for {self.scope}")
        
        # Clean existing scope data first
        await self._clean_existing_scope_data(db)
        
        # Create scope metadata node
        scope_metadata = {
            "scope": "glazing",
            "label": "Glazing System",
            "description": "Compositional glazing system with glass types, spacers, and gas fillings",
            "entities": {
                "glass_type": {
                    "label": "Glass Type",
                    "icon": "pi pi-stop",
                    "description": "Different types of glass with thermal and optical properties"
                },
                "spacer": {
                    "label": "Spacer",
                    "icon": "pi pi-minus",
                    "description": "Spacer bars that separate glass panes"
                },
                "gas": {
                    "label": "Gas Filling",
                    "icon": "pi pi-cloud",
                    "description": "Gas fillings between glass panes for insulation"
                }
            },
            "glazing_types": ["single", "double", "triple"],
            "entity_count": 3
        }
        
        scope_node = AttributeNode(
            name="glazing",
            display_name="Glazing System",
            description="Compositional glazing system for windows and doors",
            node_type="scope_metadata",
            data_type="object",
            ltree_path="definitions.glazing",
            depth=1,
            page_type="glazing",
            metadata_=scope_metadata,
            validation_rules={
                "is_scope_metadata": True,
                "scope": "glazing"
            }
        )
        
        db.add(scope_node)
        await db.flush()
        print(f"  [METADATA] Created scope metadata (ID: {scope_node.id})")
        
        # Create entity definitions
        await self._create_entity_definitions(db)
        await db.commit()

    async def _clean_existing_scope_data(self, db: AsyncSession) -> None:
        """Clean existing data for glazing scope."""
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
        """Create entity definition records for glazing scope."""
        print(f"  [ENTITIES] Creating entity definitions for {self.scope}")
        
        # Define glazing entities with their metadata
        entities = {
            "glass_type": {
                "label": "Glass Type",
                "icon": "pi pi-stop",
                "placeholders": {
                    "name": "Enter glass type (e.g., Clear Float, Low-E)"
                },
                "metadata_fields": [
                    {"name": "thickness", "type": "number", "label": "Thickness (mm)", "required": True},
                    {"name": "u_value", "type": "number", "label": "U-Value (W/m²K)", "step": 0.01},
                    {"name": "light_transmittance", "type": "number", "label": "Light Transmittance (%)", "min": 0, "max": 100},
                    {"name": "solar_factor", "type": "number", "label": "Solar Factor (g-value)", "step": 0.01},
                    {"name": "price_per_sqm", "type": "number", "label": "Price per m² (€)", "step": 0.01},
                    {"name": "weight_per_sqm", "type": "number", "label": "Weight per m² (kg)", "step": 0.1}
                ]
            },
            "spacer": {
                "label": "Spacer",
                "icon": "pi pi-minus",
                "placeholders": {
                    "name": "Enter spacer type (e.g., Aluminum, Warm Edge)"
                },
                "metadata_fields": [
                    {"name": "material", "type": "text", "label": "Material", "required": True},
                    {"name": "thermal_conductivity", "type": "number", "label": "Thermal Conductivity (W/mK)", "step": 0.001},
                    {"name": "width", "type": "number", "label": "Width (mm)", "required": True},
                    {"name": "color", "type": "text", "label": "Color"},
                    {"name": "price_per_meter", "type": "number", "label": "Price per meter (€)", "step": 0.01}
                ]
            },
            "gas": {
                "label": "Gas Filling",
                "icon": "pi pi-cloud",
                "placeholders": {
                    "name": "Enter gas type (e.g., Air, Argon, Krypton)"
                },
                "metadata_fields": [
                    {"name": "density", "type": "number", "label": "Density (kg/m³)", "step": 0.001},
                    {"name": "thermal_conductivity", "type": "number", "label": "Thermal Conductivity (W/mK)", "step": 0.0001},
                    {"name": "viscosity", "type": "number", "label": "Dynamic Viscosity (Pa·s)", "step": 0.000001},
                    {"name": "price_per_liter", "type": "number", "label": "Price per liter (€)", "step": 0.001}
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
            ltree_path=f"definitions.glazing.{entity_type}",
            depth=2,
            page_type="glazing",
            metadata_={
                "entity_type": entity_type,
                "label": label,
                "icon": icon,
                "placeholders": placeholders,
                "metadata_fields": metadata_fields,
                "scope": "glazing"
            },
            validation_rules={
                "is_entity_definition": True,
                "entity_type": entity_type,
                "scope": "glazing"
            }
        )
        
        db.add(entity_node)
        await db.flush()
        print(f"    [ENTITY] Created {entity_type} definition (ID: {entity_node.id})")

    async def seed_sample_data(self, db: AsyncSession) -> None:
        """Seed sample glazing data."""
        print(f"  [SEED] Seeding sample data for {self.scope}")
        
        # Get the glazing service
        service = ProductDefinitionServiceFactory.get_service("glazing", db)
        
        # Define sample glass types
        glass_types = [
            {
                "name": "Clear Float 4mm",
                "metadata": {
                    "thickness": 4.0,
                    "u_value": 5.8,
                    "light_transmittance": 90.0,
                    "solar_factor": 0.85,
                    "price_per_sqm": 15.50,
                    "weight_per_sqm": 10.0
                }
            },
            {
                "name": "Clear Float 6mm",
                "metadata": {
                    "thickness": 6.0,
                    "u_value": 5.7,
                    "light_transmittance": 88.0,
                    "solar_factor": 0.83,
                    "price_per_sqm": 18.75,
                    "weight_per_sqm": 15.0
                }
            },
            {
                "name": "Low-E 4mm",
                "metadata": {
                    "thickness": 4.0,
                    "u_value": 3.9,
                    "light_transmittance": 81.0,
                    "solar_factor": 0.70,
                    "price_per_sqm": 28.90,
                    "weight_per_sqm": 10.0
                }
            },
            {
                "name": "Laminated 6.38mm",
                "metadata": {
                    "thickness": 6.38,
                    "u_value": 5.6,
                    "light_transmittance": 87.0,
                    "solar_factor": 0.81,
                    "price_per_sqm": 45.20,
                    "weight_per_sqm": 16.0
                }
            }
        ]
        
        # Define sample spacers
        spacers = [
            {
                "name": "Aluminum 16mm",
                "metadata": {
                    "material": "Aluminum",
                    "thermal_conductivity": 160.0,
                    "thickness": 16.0,  # Add thickness here
                    "width": 16.0,
                    "color": "Silver",
                    "price_per_meter": 2.50
                }
            },
            {
                "name": "Warm Edge 16mm",
                "metadata": {
                    "material": "Stainless Steel/Plastic",
                    "thermal_conductivity": 1.8,
                    "thickness": 16.0,  # Add thickness here
                    "width": 16.0,
                    "color": "Black",
                    "price_per_meter": 4.20
                }
            },
            {
                "name": "Aluminum 20mm",
                "metadata": {
                    "material": "Aluminum",
                    "thermal_conductivity": 160.0,
                    "thickness": 20.0,  # Add thickness here
                    "width": 20.0,
                    "color": "Silver",
                    "price_per_meter": 2.80
                }
            }
        ]
        
        # Define sample gases
        gases = [
            {
                "name": "Air",
                "metadata": {
                    "density": 1.225,
                    "thermal_conductivity": 0.0262,
                    "viscosity": 0.0000184,
                    "price_per_liter": 0.0
                }
            },
            {
                "name": "Argon",
                "metadata": {
                    "density": 1.784,
                    "thermal_conductivity": 0.0177,
                    "viscosity": 0.0000227,
                    "price_per_liter": 0.15
                }
            },
            {
                "name": "Krypton",
                "metadata": {
                    "density": 3.749,
                    "thermal_conductivity": 0.0094,
                    "viscosity": 0.0000251,
                    "price_per_liter": 2.50
                }
            }
        ]
        
        # Create sample data
        sample_data = {
            "glass_type": glass_types,
            "spacer": spacers,
            "gas": gases
        }
        
        for entity_type, entities in sample_data.items():
            print(f"    [ENTITIES] Creating {entity_type} entities...")
            
            for entity_data in entities:
                try:
                    # Use the correct method for creating glazing components
                    from app.services.product_definition.types import GlazingComponentData
                    
                    component_data = GlazingComponentData(
                        component_type=entity_type,
                        name=entity_data["name"],
                        **entity_data.get("metadata", {})
                    )
                    entity = await service.create_glazing_component(component_data)
                    print(f"       ✅ Created: {entity_data['name']} (ID: {entity.id})")
                except Exception as e:
                    print(f"       ⚠️  Error creating {entity_data['name']}: {e}")
        
        await db.commit()
        print(f"  [SEED] Sample data seeding complete")


# Script execution
if __name__ == "__main__":
    from .base import run_async_script
    
    async def main():
        setup = GlazingSetup()
        await setup.run_setup()
    
    run_async_script(main())