"""Entry Page Pydantic schemas for validation and serialization.

This module defines Pydantic schemas for the Entry Page system including
profile data entry, form schema generation, and preview data structures.

Public Classes:
    FieldDefinition: Individual form field definition
    FormSection: Logical grouping of form fields
    ProfileSchema: Complete profile form schema
    ProfileEntryData: Profile page form data
    PreviewTable: Preview table structure
    ProfilePreviewData: Profile preview response

Features:
    - Schema-driven form generation
    - Conditional field visibility support
    - CSV structure preservation
    - Comprehensive validation rules
    - Type-safe with Annotated types
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, PositiveInt

__all__ = [
    "FieldDefinition",
    "FormSection",
    "ProfileSchema",
    "ProfileEntryData",
    "PreviewTable",
    "ProfilePreviewData",
]


class FieldDefinition(BaseModel):
    """Individual form field definition.

    Attributes:
        name: Field name/identifier
        label: Display label for the field
        data_type: Field data type (string, number, boolean, etc.)
        required: Whether field is required
        validation_rules: Optional validation rules
        display_condition: Optional conditional display logic
        ui_component: UI component type (dropdown, radio, input, etc.)
        description: Field description
        help_text: Additional help text
        options: Available options for select/radio fields
    """

    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=100,
            description="Field name/identifier",
            examples=["type", "material", "width"],
        ),
    ]
    label: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Display label for the field",
            examples=["Type", "Material", "Width (inches)"],
        ),
    ]
    data_type: Annotated[
        str,
        Field(
            description="Field data type",
            examples=["string", "number", "boolean", "formula", "dimension"],
        ),
    ]
    required: Annotated[
        bool,
        Field(
            default=False,
            description="Whether field is required",
        ),
    ] = False
    validation_rules: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Optional validation rules",
            examples=[{"min": 10, "max": 100}, {"pattern": "^[A-Z]{2}\\d{5}$"}],
        ),
    ] = None
    display_condition: Annotated[
        dict[str, Any] | None,
        Field(
            default=None,
            description="Optional conditional display logic",
            examples=[{"operator": "equals", "field": "type", "value": "Frame"}],
        ),
    ] = None
    ui_component: Annotated[
        str | None,
        Field(
            default=None,
            description="UI component type",
            examples=["dropdown", "radio", "input", "checkbox", "slider"],
        ),
    ] = None
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Field description",
            examples=["Select the product type"],
        ),
    ] = None
    help_text: Annotated[
        str | None,
        Field(
            default=None,
            description="Additional help text",
            examples=["Frame type affects available options"],
        ),
    ] = None
    options: Annotated[
        list[str] | None,
        Field(
            default=None,
            description="Available options for select/radio fields",
            examples=[["Frame", "Flying mullion"], ["Aluminum", "Vinyl", "Wood"]],
        ),
    ] = None
    options_data: Annotated[
        list[dict[str, Any]] | None,
        Field(
            default=None,
            description="Detailed option data with IDs and metadata for select/radio fields",
            examples=[[{"id": 1, "name": "Frame", "price_impact_value": 50.0}]],
        ),
    ] = None
    sort_order: Annotated[
        int,
        Field(
            default=0,
            description="Display order",
            examples=[1, 10, 100],
        ),
    ] = 0


class FormSection(BaseModel):
    """Logical grouping of form fields.

    Attributes:
        title: Section title
        description: Optional section description
        fields: List of fields in this section
        sort_order: Display order
    """

    title: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Section title",
            examples=["Basic Information", "Dimensions", "Technical Specifications"],
        ),
    ]
    description: Annotated[
        str | None,
        Field(
            default=None,
            description="Optional section description",
            examples=["Enter basic product information"],
        ),
    ] = None
    fields: Annotated[
        list[FieldDefinition],
        Field(
            description="List of fields in this section",
        ),
    ]
    sort_order: Annotated[
        int,
        Field(
            default=0,
            description="Display order",
        ),
    ] = 0


class ProfileSchema(BaseModel):
    """Complete profile form schema.

    Attributes:
        manufacturing_type_id: Manufacturing type ID
        sections: List of form sections
        conditional_logic: Conditional display logic
    """

    manufacturing_type_id: Annotated[
        PositiveInt,
        Field(
            description="Manufacturing type ID",
        ),
    ]
    sections: Annotated[
        list[FormSection],
        Field(
            description="List of form sections",
        ),
    ]
    conditional_logic: Annotated[
        dict[str, Any],
        Field(
            default_factory=dict,
            description="Conditional display logic",
        ),
    ]


class ProfileEntryData(BaseModel):
    """Profile page form data.

    Attributes:
        manufacturing_type_id: Manufacturing type ID
        name: Configuration name
        type: Product type
        company: Company name
        material: Material type
        opening_system: Opening system
        system_series: System series
        code: Product code
        length_of_beam: Length of beam
        renovation: Renovation flag
        width: Width dimension
        builtin_flyscreen_track: Built-in flyscreen track flag
        total_width: Total width
        flyscreen_track_height: Flyscreen track height
        front_height: Front height
        rear_height: Rear height
        glazing_height: Glazing height
        renovation_height: Renovation height
        glazing_undercut_height: Glazing undercut height
        pic: Picture/image reference
        sash_overlap: Sash overlap
        flying_mullion_horizontal_clearance: Flying mullion horizontal clearance
        flying_mullion_vertical_clearance: Flying mullion vertical clearance
        steel_material_thickness: Steel material thickness
        weight_per_meter: Weight per meter
        reinforcement_steel: Reinforcement steel options
        colours: Available colors
        price_per_meter: Price per meter
        price_per_beam: Price per beam
        upvc_profile_discount: UPVC profile discount percentage
    """

    manufacturing_type_id: Annotated[
        PositiveInt,
        Field(
            description="Manufacturing type ID",
        ),
    ]
    name: Annotated[
        str,
        Field(
            min_length=1,
            max_length=200,
            description="Configuration name",
            examples=["Living Room Window"],
        ),
    ]
    type: Annotated[
        str,
        Field(
            description="Product type",
            examples=["Frame", "Flying mullion"],
        ),
    ]
    company: Annotated[
        str | None,
        Field(
            default=None,
            description="Company name",
            examples=["ABC Construction"],
        ),
    ] = None
    material: Annotated[
        str,
        Field(
            description="Material type",
            examples=["Aluminum", "Vinyl", "Wood"],
        ),
    ]
    opening_system: Annotated[
        str,
        Field(
            description="Opening system",
            examples=["Casement", "Sliding", "Double-hung"],
        ),
    ]
    system_series: Annotated[
        str,
        Field(
            description="System series",
            examples=["K700", "K800"],
        ),
    ]
    code: Annotated[
        str | None,
        Field(
            default=None,
            description="Product code",
            examples=["WIN-001", "DOOR-002"],
        ),
    ] = None
    length_of_beam: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Length of beam in meters",
            examples=[2.5, 3.0],
        ),
    ] = None
    renovation: Annotated[
        bool | None,
        Field(
            default=None,
            description="Renovation flag",
        ),
    ] = None
    width: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Width dimension",
            examples=[48.5, 60.0],
        ),
    ] = None
    builtin_flyscreen_track: Annotated[
        bool | None,
        Field(
            default=None,
            description="Built-in flyscreen track flag",
        ),
    ] = None
    total_width: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Total width",
            examples=[50.0, 72.0],
        ),
    ] = None
    flyscreen_track_height: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Flyscreen track height",
            examples=[24.0, 36.0],
        ),
    ] = None
    front_height: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Front height",
            examples=[48.0, 60.0],
        ),
    ] = None
    rear_height: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Rear height",
            examples=[46.0, 58.0],
        ),
    ] = None
    glazing_height: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Glazing height",
            examples=[42.0, 54.0],
        ),
    ] = None
    renovation_height: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Renovation height",
            examples=[44.0, 56.0],
        ),
    ] = None
    glazing_undercut_height: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Glazing undercut height",
            examples=[40.0, 52.0],
        ),
    ] = None
    pic: Annotated[
        str | None,
        Field(
            default=None,
            description="Picture/image reference",
            examples=["image001.jpg", "profile_pic.png"],
        ),
    ] = None
    sash_overlap: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Sash overlap",
            examples=[2.0, 3.5],
        ),
    ] = None
    flying_mullion_horizontal_clearance: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Flying mullion horizontal clearance",
            examples=[1.5, 2.0],
        ),
    ] = None
    flying_mullion_vertical_clearance: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Flying mullion vertical clearance",
            examples=[1.0, 1.5],
        ),
    ] = None
    steel_material_thickness: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Steel material thickness",
            examples=[1.2, 1.5],
        ),
    ] = None
    weight_per_meter: Annotated[
        float | None,
        Field(
            default=None,
            ge=0,
            description="Weight per meter in kg",
            examples=[2.5, 3.2],
        ),
    ] = None
    reinforcement_steel: Annotated[
        str | None,
        Field(
            default=None,
            description="Reinforcement steel options",
            examples=["Standard", "Heavy duty"],
        ),
    ] = None
    colours: Annotated[
        str | None,
        Field(
            default=None,
            description="Available colors",
            examples=["White", "Black", "Brown"],
        ),
    ] = None
    price_per_meter: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Price per meter",
            examples=[25.50, 45.75],
        ),
    ] = None
    price_per_beam: Annotated[
        Decimal | None,
        Field(
            default=None,
            ge=0,
            decimal_places=2,
            description="Price per beam",
            examples=[125.00, 250.00],
        ),
    ] = None
    upvc_profile_discount: Annotated[
        float | None,
        Field(
            default=20.0,
            ge=0,
            le=100,
            description="UPVC profile discount percentage",
            examples=[15.0, 20.0, 25.0],
        ),
    ] = 20.0


class PreviewTable(BaseModel):
    """Preview table structure.

    Attributes:
        headers: Column headers
        rows: Table rows data
    """

    headers: Annotated[
        list[str],
        Field(
            description="Column headers",
            examples=[["Name", "Type", "Material", "Width", "Height"]],
        ),
    ]
    rows: Annotated[
        list[dict[str, Any]],
        Field(
            description="Table rows data",
            examples=[[{"Name": "Window 1", "Type": "Frame", "Material": "Aluminum"}]],
        ),
    ]


class ProfilePreviewData(BaseModel):
    """Profile preview response.

    Attributes:
        configuration_id: Configuration ID
        table: Preview table
        last_updated: Last update timestamp
    """

    configuration_id: Annotated[
        PositiveInt,
        Field(
            description="Configuration ID",
        ),
    ]
    table: Annotated[
        PreviewTable,
        Field(
            description="Preview table",
        ),
    ]
    last_updated: Annotated[
        datetime,
        Field(
            description="Last update timestamp",
        ),
    ]

    model_config = ConfigDict(from_attributes=True)


class InlineEditRequest(BaseModel):
    """Request schema for inline table editing.

    Attributes:
        field: Field name (header) to edit
        value: New value for the field
    """

    field: Annotated[
        str,
        Field(
            description="Field name (header) to edit",
            examples=["width_inches", "material_type"],
        ),
    ]
    value: Annotated[
        Any,
        Field(
            description="New value for the field",
            examples=["Aluminum", 48.5],
        ),
    ]
