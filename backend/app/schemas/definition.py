from typing import TypedDict, List, Optional, Any, Union, Dict

class MetadataField(TypedDict):
    name: str
    type: str  # text, number, boolean, textarea
    label: str
    hidden: Optional[bool]

class SpecialConfig(TypedDict):
    field_name: str
    target_entity: str
    label: str
    required: bool
    help_text: str

class SpecialUI(TypedDict):
    type: str  # relation_selector
    config: SpecialConfig

class DependencyAction(TypedDict):
    type: str  # "autofill", "disable"
    source_property: Optional[str]
    target_field: str
    disable_target: Optional[bool]
    lookup_source: Optional[str]
    lookup_key: Optional[str]
    chain: Optional['DependencyAction']

class DependencyRule(TypedDict):
    trigger_field: str
    actions: List[DependencyAction]

class EntityDef(TypedDict):
    label: str
    icon: str
    name_placeholder: Optional[str]
    description_placeholder: Optional[str]
    metadata_fields: List[MetadataField]
    special_ui: Optional[SpecialUI]

class ScopeDef(TypedDict):
    label: str
    entities: Dict[str, EntityDef]
    hierarchy: Optional[Dict[int, str]]
    dependencies: Optional[List[DependencyRule]]
