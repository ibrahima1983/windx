"""Product Definition Schemas (DEPRECATED).

⚠️  DEPRECATION WARNING: This module is deprecated and will be removed in a future version.
    Please use the new scope-based schemas in app.schemas.product_definition instead.

This module provides legacy schema definitions for product definitions.
New code should use the scope-specific schemas in the product_definition package.

Migration Guide:
    - Replace imports from app.schemas.definition with app.schemas.product_definition
    - Use scope-specific schemas (ProfileEntityCreate, GlazingComponentCreate, etc.)
    - Update to use the new BaseEntityCreate, BaseEntityUpdate patterns
"""

import warnings
from typing import Dict, List, Optional, TypedDict

# Issue deprecation warning when this module is imported
warnings.warn(
    "app.schemas.definition is deprecated. Use app.schemas.product_definition instead.",
    DeprecationWarning,
    stacklevel=2
)

# Re-export new schemas for backward compatibility
try:
    from app.schemas.product_definition import (
        BaseEntityCreate,
        BaseEntityUpdate,
        BaseEntityResponse,
        BaseResponse,
        ProfileEntityCreate,
        ProfilePathCreate,
        GlazingComponentCreate,
        GlazingUnitCreate,
        MetadataField as NewMetadataField
    )
    
    # Provide backward compatibility aliases
    EntityCreate = BaseEntityCreate
    EntityUpdate = BaseEntityUpdate
    EntityResponse = BaseEntityResponse
    
except ImportError:
    # Fallback if new schemas are not available yet
    pass


# ============================================================================
# Legacy Schema Definitions (DEPRECATED)
# ============================================================================

class EntityPlaceholders(TypedDict):
    """Standard placeholders for entity fields.
    
    DEPRECATED: Use the new schema system instead.
    """
    name: str
    description: str
    price: str


class MetadataField(TypedDict):
    """Metadata field definition.
    
    DEPRECATED: Use app.schemas.product_definition.base.MetadataField instead.
    """
    name: str
    type: str  # text, number, boolean, textarea
    label: str
    hidden: Optional[bool]


class SpecialConfig(TypedDict):
    """Special configuration for UI components.
    
    DEPRECATED: Use the new schema system instead.
    """
    field_name: str
    target_entity: str
    label: str
    required: bool
    help_text: str


class SpecialUI(TypedDict):
    """Special UI configuration.
    
    DEPRECATED: Use the new schema system instead.
    """
    type: str  # relation_selector
    config: SpecialConfig


class DependencyAction(TypedDict):
    """Dependency action definition.
    
    DEPRECATED: Use the new schema system instead.
    """
    type: str  # "autofill", "disable"
    source_property: Optional[str]
    target_field: str
    disable_target: Optional[bool]
    lookup_source: Optional[str]
    lookup_key: Optional[str]
    chain: Optional['DependencyAction']


class DependencyRule(TypedDict):
    """Dependency rule definition.
    
    DEPRECATED: Use the new schema system instead.
    """
    trigger_field: str
    actions: List[DependencyAction]


class EntityDef(TypedDict):
    """Entity definition.
    
    DEPRECATED: Use app.schemas.product_definition.base.ScopeEntityConfig instead.
    """
    label: str
    icon: str
    placeholders: EntityPlaceholders
    metadata_fields: List[MetadataField]
    special_ui: Optional[SpecialUI]


class ScopeDef(TypedDict):
    """Scope definition.
    
    DEPRECATED: Use app.schemas.product_definition.base.ScopeMetadata instead.
    """
    label: str
    entities: Dict[str, EntityDef]
    hierarchy: Optional[Dict[int, str]]
    dependencies: Optional[List[DependencyRule]]


# ============================================================================
# Migration Helpers
# ============================================================================

def migrate_entity_def_to_scope_config(entity_def: EntityDef) -> dict:
    """Migrate legacy EntityDef to new ScopeEntityConfig format.
    
    Args:
        entity_def: Legacy entity definition
        
    Returns:
        Dictionary compatible with ScopeEntityConfig
        
    DEPRECATED: This is a temporary migration helper.
    """
    warnings.warn(
        "migrate_entity_def_to_scope_config is deprecated. Use new schemas directly.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return {
        "label": entity_def["label"],
        "icon": entity_def.get("icon"),
        "description": None,
        "metadata_fields": [
            {
                "name": field["name"],
                "type": field["type"],
                "label": field["label"],
                "required": not field.get("hidden", False)
            }
            for field in entity_def.get("metadata_fields", [])
        ],
        "validation_rules": None
    }


def migrate_scope_def_to_metadata(scope_def: ScopeDef) -> dict:
    """Migrate legacy ScopeDef to new ScopeMetadata format.
    
    Args:
        scope_def: Legacy scope definition
        
    Returns:
        Dictionary compatible with ScopeMetadata
        
    DEPRECATED: This is a temporary migration helper.
    """
    warnings.warn(
        "migrate_scope_def_to_metadata is deprecated. Use new schemas directly.",
        DeprecationWarning,
        stacklevel=2
    )
    
    return {
        "scope": "unknown",  # Must be set by caller
        "label": scope_def["label"],
        "description": None,
        "entities": {
            entity_type: migrate_entity_def_to_scope_config(entity_def)
            for entity_type, entity_def in scope_def.get("entities", {}).items()
        },
        "supports_hierarchy": scope_def.get("hierarchy") is not None,
        "supports_composition": False,
        "supports_calculations": False
    }
