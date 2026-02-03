"""Glazing-specific product definition service.

This module provides the service implementation for glazing product definitions
with compositional structure (glass types, spacers, gases, and glazing units).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.attribute_node import AttributeNode
from .base import BaseProductDefinitionService
from .types import EntityCreateData, EntityUpdateData, GlazingComponentData, GlazingUnitData, CalculationResult

__all__ = ["GlazingProductDefinitionService"]


class GlazingProductDefinitionService(BaseProductDefinitionService):
    """Service for glazing product definitions with compositional structure.
    
    This service handles the glazing scope which includes:
    - Components: glass_type, spacer, gas
    - Glazing units: single, double, triple compositions
    - Technical calculations: U-value, thickness, price, weight
    """

    def __init__(self, db: AsyncSession):
        """Initialize glazing service.
        
        Args:
            db: Database session
        """
        super().__init__(db, "glazing")

    # ============================================================================
    # Base Class Implementation
    # ============================================================================

    async def get_entities(self, entity_type: str) -> List[Any]:
        """Get glazing entities of specific type.
        
        Args:
            entity_type: Type of entities (glass_type, spacer, gas)
            
        Returns:
            List of entities
        """
        try:
            # Validate entity type for glazing scope
            if not self._validate_entity_type(entity_type):
                raise ValueError(f"Invalid entity type for glazing scope: {entity_type}")

            # Query entities from database
            result = await self.db.execute(
                select(AttributeNode)
                .where(
                    AttributeNode.node_type == entity_type,
                    AttributeNode.page_type == "glazing"
                )
                .order_by(AttributeNode.name)
            )
            entities = list(result.scalars().all())
            return entities
            
        except Exception as e:
            self._handle_service_error(e, f"getting {entity_type} entities")

    async def create_entity(self, data: EntityCreateData) -> Any:
        """Create glazing entity (component).
        
        Args:
            data: Entity creation data
            
        Returns:
            Created entity
        """
        try:
            # Validate entity type for glazing scope
            if not self._validate_entity_type(data.entity_type):
                raise ValueError(f"Invalid entity type for glazing scope: {data.entity_type}")

            # Prepare metadata for glazing component
            metadata = self._prepare_entity_metadata(data)
            
            # Add component-specific metadata if provided
            if data.metadata:
                metadata.update(data.metadata)

            # Create the entity
            entity = AttributeNode(
                name=data.name,
                node_type=data.entity_type,
                data_type="string",
                ltree_path=self._slugify(data.name),
                depth=0,  # Components are root-level entities
                image_url=data.image_url,
                price_impact_value=data.price_from,
                price_impact_type="fixed" if data.price_from else "fixed",
                description=data.description,
                validation_rules={"is_glazing_component": True},
                metadata_=metadata,
                page_type="glazing",
            )

            self.db.add(entity)
            await self.commit()
            await self.refresh(entity)
            return entity
            
        except Exception as e:
            self._handle_service_error(e, f"creating {data.entity_type} entity")

    async def update_entity(self, entity_id: int, data: EntityUpdateData) -> Optional[Any]:
        """Update glazing entity.
        
        Args:
            entity_id: Entity ID to update
            data: Update data
            
        Returns:
            Updated entity or None if not found
        """
        try:
            # Get existing entity
            result = await self.db.execute(
                select(AttributeNode).where(
                    AttributeNode.id == entity_id,
                    AttributeNode.page_type == "glazing"
                )
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return None

            # Update fields
            if data.name is not None:
                entity.name = data.name
                entity.ltree_path = self._slugify(data.name)

            if data.image_url is not None:
                entity.image_url = data.image_url

            if data.price_from is not None:
                entity.price_impact_value = data.price_from

            if data.description is not None:
                entity.description = data.description

            if data.metadata is not None:
                # Merge with existing metadata
                current_metadata = entity.metadata_ or {}
                current_metadata.update(data.metadata)
                entity.metadata_ = current_metadata

            await self.commit()
            await self.refresh(entity)
            return entity
            
        except Exception as e:
            self._handle_service_error(e, f"updating entity {entity_id}")

    async def delete_entity(self, entity_id: int) -> Dict[str, Any]:
        """Delete glazing entity.
        
        Args:
            entity_id: Entity ID to delete
            
        Returns:
            Result dict with success status
        """
        try:
            # Get existing entity
            result = await self.db.execute(
                select(AttributeNode).where(
                    AttributeNode.id == entity_id,
                    AttributeNode.page_type == "glazing"
                )
            )
            entity = result.scalar_one_or_none()

            if not entity:
                return {"success": False, "message": "Entity not found"}

            # Check if entity is referenced by glazing units
            # TODO: Implement reference checking when glazing units are stored in database

            await self.db.delete(entity)
            await self.commit()
            
            return {"success": True, "message": f"Entity '{entity.name}' deleted"}
            
        except Exception as e:
            self._handle_service_error(e, f"deleting entity {entity_id}")

    async def get_entity_by_id(self, entity_id: int) -> Optional[Any]:
        """Get glazing entity by ID.
        
        Args:
            entity_id: Entity ID
            
        Returns:
            Entity or None if not found
        """
        try:
            result = await self.db.execute(
                select(AttributeNode).where(
                    AttributeNode.id == entity_id,
                    AttributeNode.page_type == "glazing"
                )
            )
            entity = result.scalar_one_or_none()
            return entity
            
        except Exception as e:
            self._handle_service_error(e, f"getting entity {entity_id}")

    # ============================================================================
    # Glazing-Specific Methods
    # ============================================================================

    async def create_glazing_component(self, data: GlazingComponentData) -> Any:
        """Create glazing component with specific properties.
        
        Args:
            data: Component creation data
            
        Returns:
            Created component entity
        """
        try:
            # Convert to EntityCreateData and add component-specific metadata
            entity_data = EntityCreateData(
                entity_type=data.component_type,
                name=data.name,
                description=data.description,
                price_from=data.price_per_sqm,
                metadata={
                    "component_type": data.component_type,
                    "thickness": data.thickness,
                    "light_transmittance": data.light_transmittance,
                    "u_value": data.u_value,
                    "material": data.material,
                    "thermal_conductivity": data.thermal_conductivity,
                    "density": data.density,
                }
            )
            
            return await self.create_entity(entity_data)
            
        except Exception as e:
            self._handle_service_error(e, f"creating {data.component_type} component")

    async def get_all_components(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get all glazing components grouped by type.
        
        Returns:
            Dict with component types as keys and lists of components as values
        """
        try:
            components = {
                "glass_types": [],
                "spacers": [],
                "gases": []
            }
            
            # Get each component type
            for component_type, key in [
                ("glass_type", "glass_types"),
                ("spacer", "spacers"),
                ("gas", "gases")
            ]:
                entities = await self.get_entities(component_type)
                components[key] = [
                    {
                        "id": e.id,
                        "name": e.name,
                        "description": e.description,
                        "image_url": e.image_url,
                        "price_per_sqm": float(e.price_impact_value) if e.price_impact_value else 0.0,
                        "metadata": e.metadata_ or {},
                    }
                    for e in entities
                ]
            
            return components
            
        except Exception as e:
            self._handle_service_error(e, "getting all components")

    async def create_glazing_unit(self, data: GlazingUnitData) -> Dict[str, Any]:
        """Create glazing unit from components.
        
        Args:
            data: Glazing unit creation data
            
        Returns:
            Created glazing unit data
        """
        try:
            # Validate components exist
            component_ids = [
                data.outer_glass_id,
                data.middle_glass_id,
                data.inner_glass_id,
                data.spacer1_id,
                data.spacer2_id,
                data.gas_id
            ]
            
            components = {}
            for comp_id in component_ids:
                if comp_id is not None:
                    component = await self.get_entity_by_id(comp_id)
                    if component:
                        components[comp_id] = component
                    else:
                        raise ValueError(f"Component with ID {comp_id} not found")

            # Calculate glazing unit properties
            calculation_result = await self._calculate_glazing_properties(data, components)
            
            # For now, return the glazing unit data with calculated properties
            # In a full implementation, this would be stored in the database
            glazing_unit = {
                "name": data.name,
                "glazing_type": data.glazing_type,
                "description": data.description,
                "components": {
                    "outer_glass_id": data.outer_glass_id,
                    "middle_glass_id": data.middle_glass_id,
                    "inner_glass_id": data.inner_glass_id,
                    "spacer1_id": data.spacer1_id,
                    "spacer2_id": data.spacer2_id,
                    "gas_id": data.gas_id,
                },
                "calculated_properties": {
                    "total_thickness": calculation_result.total_thickness,
                    "u_value": calculation_result.u_value,
                    "price_per_sqm": float(calculation_result.price_per_sqm),
                    "weight_per_sqm": calculation_result.weight_per_sqm,
                    "technical_properties": calculation_result.technical_properties,
                }
            }
            
            return glazing_unit
            
        except Exception as e:
            self._handle_service_error(e, "creating glazing unit")

    async def calculate_glazing_properties(self, unit_data: Dict[str, Any]) -> CalculationResult:
        """Calculate technical properties for a glazing unit configuration.
        
        Args:
            unit_data: Glazing unit configuration data
            
        Returns:
            Calculated properties
        """
        try:
            # Convert dict to GlazingUnitData
            glazing_data = GlazingUnitData(**unit_data)
            
            # Get component data
            component_ids = [
                glazing_data.outer_glass_id,
                glazing_data.middle_glass_id,
                glazing_data.inner_glass_id,
                glazing_data.spacer1_id,
                glazing_data.spacer2_id,
                glazing_data.gas_id
            ]
            
            components = {}
            for comp_id in component_ids:
                if comp_id is not None:
                    component = await self.get_entity_by_id(comp_id)
                    if component:
                        components[comp_id] = component

            return await self._calculate_glazing_properties(glazing_data, components)
            
        except Exception as e:
            self._handle_service_error(e, "calculating glazing properties")

    async def _calculate_glazing_properties(self, data: GlazingUnitData, components: Dict[int, Any]) -> CalculationResult:
        """Internal method to calculate glazing properties.
        
        Args:
            data: Glazing unit data
            components: Dictionary of component ID -> component entity
            
        Returns:
            Calculated properties
        """
        total_thickness = 0.0
        total_price = Decimal("0.00")
        total_weight = 0.0
        u_values = []
        
        # Calculate based on glazing type
        if data.glazing_type == "single":
            # Single glazing: just one glass
            if data.outer_glass_id and data.outer_glass_id in components:
                glass = components[data.outer_glass_id]
                metadata = glass.metadata_ or {}
                
                # Handle None values properly
                thickness_value = metadata.get("thickness")
                total_thickness = thickness_value if thickness_value is not None else 6.0
                total_price = glass.price_impact_value or Decimal("35.00")
                weight_value = metadata.get("weight_per_sqm")
                total_weight = weight_value if weight_value is not None else 15.0
                u_value = metadata.get("u_value")
                u_values.append(u_value if u_value is not None else 5.8)
                
        elif data.glazing_type == "double":
            # Double glazing: outer glass + spacer + inner glass + optional gas
            glass_thickness = 0.0
            spacer_thickness = 0.0  # Always initialize to 0
            
            # Outer glass
            if data.outer_glass_id and data.outer_glass_id in components:
                glass = components[data.outer_glass_id]
                metadata = glass.metadata_ or {}
                # Handle None values properly
                thickness_value = metadata.get("thickness")
                glass_thickness += thickness_value if thickness_value is not None else 6.0
                total_price += glass.price_impact_value or Decimal("0.00")
                weight_value = metadata.get("weight_per_sqm")
                total_weight += weight_value if weight_value is not None else 15.0
                u_value = metadata.get("u_value")
                u_values.append(u_value if u_value is not None else 5.8)
            
            # Inner glass
            if data.inner_glass_id and data.inner_glass_id in components:
                glass = components[data.inner_glass_id]
                metadata = glass.metadata_ or {}
                # Handle None values properly
                thickness_value = metadata.get("thickness")
                glass_thickness += thickness_value if thickness_value is not None else 4.0
                total_price += glass.price_impact_value or Decimal("0.00")
                weight_value = metadata.get("weight_per_sqm")
                total_weight += weight_value if weight_value is not None else 10.0
                u_value = metadata.get("u_value")
                u_values.append(u_value if u_value is not None else 5.8)
            
            # Spacer - update the initialized value
            if data.spacer1_id and data.spacer1_id in components:
                spacer = components[data.spacer1_id]
                metadata = spacer.metadata_ or {}
                # Handle None values properly - use default if value is None or missing
                thickness_value = metadata.get("thickness")
                spacer_thickness = thickness_value if thickness_value is not None else 16.0
                total_price += spacer.price_impact_value or Decimal("0.00")
            
            total_thickness = glass_thickness + spacer_thickness
            
        elif data.glazing_type == "triple":
            # Triple glazing: outer + middle + inner glass + 2 spacers + optional gas
            glass_thickness = 0.0
            spacer_thickness = 0.0
            
            # All three glasses
            for glass_id in [data.outer_glass_id, data.middle_glass_id, data.inner_glass_id]:
                if glass_id and glass_id in components:
                    glass = components[glass_id]
                    metadata = glass.metadata_ or {}
                    # Handle None values properly
                    thickness_value = metadata.get("thickness")
                    glass_thickness += thickness_value if thickness_value is not None else 6.0
                    total_price += glass.price_impact_value or Decimal("0.00")
                    # Handle None values for weight
                    weight_value = metadata.get("weight_per_sqm")
                    total_weight += weight_value if weight_value is not None else 15.0
                    # Handle None values for u_value
                    u_value = metadata.get("u_value")
                    u_values.append(u_value if u_value is not None else 5.8)
            
            # Both spacers
            for spacer_id in [data.spacer1_id, data.spacer2_id]:
                if spacer_id and spacer_id in components:
                    spacer = components[spacer_id]
                    metadata = spacer.metadata_ or {}
                    # Handle None values properly
                    thickness_value = metadata.get("thickness")
                    spacer_thickness += thickness_value if thickness_value is not None else 12.0
                    total_price += spacer.price_impact_value or Decimal("0.00")
            
            total_thickness = glass_thickness + spacer_thickness

        # Calculate combined U-value (simplified calculation)
        if u_values:
            # For multiple panes, U-value is roughly 1/sum(1/u_value_i)
            if len(u_values) == 1:
                combined_u_value = u_values[0]
            else:
                reciprocal_sum = sum(1/u for u in u_values if u > 0)
                combined_u_value = 1/reciprocal_sum if reciprocal_sum > 0 else 5.8
        else:
            combined_u_value = 5.8  # Default

        # Add gas cost if present
        if data.gas_id and data.gas_id in components:
            gas = components[data.gas_id]
            total_price += gas.price_impact_value or Decimal("0.00")
            # Gas can improve U-value slightly
            combined_u_value *= 0.9  # 10% improvement

        return CalculationResult(
            total_thickness=total_thickness,
            u_value=round(combined_u_value, 2),
            price_per_sqm=total_price,
            weight_per_sqm=total_weight,
            technical_properties={
                "glazing_type": data.glazing_type,
                "component_count": len([c for c in components.values() if c]),
                "has_gas_filling": data.gas_id is not None,
                "calculation_method": "simplified"
            }
        )

    # ============================================================================
    # Glazing-Specific Scope Metadata
    # ============================================================================

    async def get_scope_metadata(self) -> Dict[str, Any]:
        """Get glazing scope metadata.
        
        Returns:
            Glazing scope metadata
        """
        if self._scope_metadata_cache is not None:
            return self._scope_metadata_cache

        metadata = {
            "scope": self.scope,
            "label": "Glazing System",
            "service_class": self.__class__.__name__,
            "supports_hierarchy": False,
            "supports_composition": True,
            "supports_calculations": True,
            "entity_types": ["glass_type", "spacer", "gas"],
            "glazing_types": ["single", "double", "triple"],
            "entities": {
                "glass_type": {
                    "label": "Glass Type",
                    "icon": "pi pi-stop",
                    "metadata_fields": [
                        {"name": "thickness", "type": "number", "label": "Thickness (mm)"},
                        {"name": "light_transmittance", "type": "number", "label": "Light Transmittance (%)"},
                        {"name": "u_value", "type": "number", "label": "U-Value (W/m²K)"},
                        {"name": "weight_per_sqm", "type": "number", "label": "Weight per m² (kg)"},
                    ]
                },
                "spacer": {
                    "label": "Spacer",
                    "icon": "pi pi-minus",
                    "metadata_fields": [
                        {"name": "material", "type": "text", "label": "Material"},
                        {"name": "thickness", "type": "number", "label": "Thickness (mm)"},
                        {"name": "thermal_conductivity", "type": "number", "label": "Thermal Conductivity (W/m·K)"},
                    ]
                },
                "gas": {
                    "label": "Gas Filling",
                    "icon": "pi pi-cloud",
                    "metadata_fields": [
                        {"name": "density", "type": "number", "label": "Density (kg/m³)"},
                        {"name": "thermal_conductivity", "type": "number", "label": "Thermal Conductivity (W/m·K)"},
                    ]
                }
            }
        }
        
        self._scope_metadata_cache = metadata
        return metadata

    # ============================================================================
    # Validation Methods
    # ============================================================================

    def _validate_entity_type(self, entity_type: str) -> bool:
        """Validate entity type for glazing scope.
        
        Args:
            entity_type: Type of entity to validate
            
        Returns:
            True if valid for glazing scope
        """
        valid_types = ["glass_type", "spacer", "gas"]
        return entity_type in valid_types

    async def validate_entity_references(self, data: Dict[str, Any]) -> bool:
        """Validate entity references for glazing scope.
        
        Args:
            data: Data containing entity references
            
        Returns:
            True if all references are valid
        """
        # For glazing scope, validate that referenced components exist
        component_ids = []
        
        # Extract component IDs from data
        for key in ["outer_glass_id", "middle_glass_id", "inner_glass_id", "spacer1_id", "spacer2_id", "gas_id"]:
            if key in data and data[key] is not None:
                component_ids.append(data[key])
        
        # Check that all referenced components exist
        for comp_id in component_ids:
            component = await self.get_entity_by_id(comp_id)
            if not component:
                return False
        
        return True