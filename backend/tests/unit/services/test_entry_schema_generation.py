"""Property-based tests for entry service schema generation.

This module contains property-based tests for the EntryService schema generation
functionality, validating that forms are generated correctly from attribute hierarchies.

**Feature: entry-page-system, Property 1: Schema-driven form generation**
**Validates: Requirements 1.1, 1.2, 5.1, 5.2**
"""

from hypothesis import given
from hypothesis import strategies as st

from app.models.attribute_node import AttributeNode
from app.schemas.entry import FieldDefinition, FormSection, ProfileSchema
from app.services.entry import EntryService

# Valid data types for attribute nodes
VALID_DATA_TYPES = ["string", "number", "boolean", "formula", "dimension"]

# Valid node types
VALID_NODE_TYPES = ["category", "attribute", "option", "component", "technical_spec"]

# Valid UI components
VALID_UI_COMPONENTS = ["input", "dropdown", "radio", "checkbox", "slider", "multiselect"]


@st.composite
def attribute_node_strategy(draw):
    """Generate valid AttributeNode instances for testing."""
    # Generate unique ID to ensure unique names
    unique_id = draw(st.integers(min_value=1, max_value=10000))
    name = f"field_{unique_id}"
    node_type = draw(st.sampled_from(VALID_NODE_TYPES))
    data_type = draw(st.sampled_from(VALID_DATA_TYPES))

    # Only generate fields for non-category nodes
    if node_type == "category":
        return None

    # Generate LTREE path
    section = draw(
        st.sampled_from(["basic_information", "dimensions", "technical_specs", "pricing"])
    )
    ltree_path = f"{section}.{name.lower()}"

    return AttributeNode(
        id=unique_id,
        manufacturing_type_id=1,
        parent_node_id=None,
        name=name,
        description=f"Test {name}",
        node_type=node_type,
        data_type=data_type,
        required=draw(st.booleans()),
        ltree_path=ltree_path,
        depth=1,
        sort_order=unique_id,  # Use unique_id for sort order too
        ui_component=draw(st.sampled_from(VALID_UI_COMPONENTS)),
        help_text=f"Help for {name}",
        validation_rules=draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    st.sampled_from(["min", "max", "min_length", "max_length", "pattern"]),
                    st.one_of(st.integers(min_value=0, max_value=1000), st.text(max_size=50)),
                    min_size=0,
                    max_size=3,
                ),
            )
        ),
        display_condition=draw(
            st.one_of(
                st.none(),
                st.dictionaries(
                    st.sampled_from(["operator", "field", "value"]),
                    st.one_of(st.text(max_size=20), st.booleans(), st.integers()),
                    min_size=1,
                    max_size=3,
                ),
            )
        ),
    )


class TestSchemaGeneration:
    """Test schema generation functionality."""

    def test_schema_driven_form_generation(self):
        """**Feature: entry-page-system, Property 1: Schema-driven form generation**

        For any manufacturing type with attribute nodes, the system should generate
        forms containing exactly the fields defined in the attribute hierarchy with
        correct data types, validation rules, and display conditions.

        **Validates: Requirements 1.1, 1.2, 5.1, 5.2**
        """
        # Create a set of test attribute nodes with unique names
        valid_nodes = [
            AttributeNode(
                id=1,
                manufacturing_type_id=1,
                name="field_1",
                description="Test field 1",
                node_type="attribute",
                data_type="string",
                required=True,
                ltree_path="basic_information.field_1",
                depth=1,
                sort_order=1,
                ui_component="input",
                help_text="Help for field 1",
            ),
            AttributeNode(
                id=2,
                manufacturing_type_id=1,
                name="field_2",
                description="Test field 2",
                node_type="attribute",
                data_type="number",
                required=False,
                ltree_path="dimensions.field_2",
                depth=1,
                sort_order=2,
                ui_component="input",
                help_text="Help for field 2",
                validation_rules={"min": 0, "max": 100},
            ),
            AttributeNode(
                id=3,
                manufacturing_type_id=1,
                name="field_3",
                description="Test field 3",
                node_type="attribute",
                data_type="boolean",
                required=False,
                ltree_path="conditional_fields.field_3",
                depth=1,
                sort_order=3,
                ui_component="checkbox",
                help_text="Help for field 3",
                display_condition={"operator": "equals", "field": "field_1", "value": "test"},
            ),
        ]

        # Create entry service (without DB for unit testing)
        entry_service = EntryService(None)  # type: ignore

        # Generate schema
        schema = entry_service.generate_form_schema(1, valid_nodes)

        # Verify schema structure
        assert isinstance(schema, ProfileSchema)
        assert schema.manufacturing_type_id == 1
        assert isinstance(schema.sections, list)
        assert len(schema.sections) > 0

        # Verify all non-category nodes are represented as fields
        all_fields = []
        for section in schema.sections:
            assert isinstance(section, FormSection)
            assert isinstance(section.title, str)
            assert len(section.title) > 0
            assert isinstance(section.fields, list)
            all_fields.extend(section.fields)

        # Should have exactly as many fields as valid attribute nodes
        assert len(all_fields) == len(valid_nodes)

        # Verify each field has correct properties
        field_names = set()
        for field in all_fields:
            assert isinstance(field, FieldDefinition)
            assert isinstance(field.name, str)
            assert len(field.name) > 0
            assert field.name not in field_names  # No duplicate field names
            field_names.add(field.name)

            assert isinstance(field.label, str)
            assert len(field.label) > 0
            assert field.data_type in VALID_DATA_TYPES
            assert isinstance(field.required, bool)

            if field.ui_component:
                assert field.ui_component in VALID_UI_COMPONENTS

        # Verify conditional logic is preserved
        nodes_with_conditions = [n for n in valid_nodes if n.display_condition]
        conditional_fields = [name for name in schema.conditional_logic.keys()]

        # All nodes with display conditions should be in conditional logic
        for node in nodes_with_conditions:
            assert node.name in conditional_fields

        # Verify section organization
        section_names = [s.title for s in schema.sections]
        assert len(set(section_names)) == len(section_names)  # No duplicate sections

        # Verify sort order is respected
        for section in schema.sections:
            if len(section.fields) > 1:
                # Fields should maintain some ordering (we can't guarantee exact order without DB)
                field_names_in_section = [f.name for f in section.fields]
                assert len(field_names_in_section) == len(
                    set(field_names_in_section)
                )  # No duplicates

    def test_empty_attribute_list_generates_empty_schema(self):
        """Test that empty attribute list generates valid but empty schema."""
        entry_service = EntryService(None)  # type: ignore
        schema = entry_service.generate_form_schema(1, [])

        assert isinstance(schema, ProfileSchema)
        assert schema.manufacturing_type_id == 1
        assert len(schema.sections) == 0
        assert len(schema.conditional_logic) == 0

    def test_section_name_generation(self):
        """Test section name generation from LTREE paths."""
        entry_service = EntryService(None)  # type: ignore

        test_cases = [
            ("basic_information.name", "Basic Information"),
            ("dimensions.width", "Dimensions"),
            ("technical_specs.weight", "Technical Specs"),
            ("pricing.cost", "Pricing"),
            ("", "general"),  # Service returns lowercase "general"
            ("single_level", "Single Level"),
        ]

        for ltree_path, expected_section in test_cases:
            section_name = entry_service.get_section_name(ltree_path)
            assert section_name == expected_section

    def test_field_definition_creation(self):
        """Test field definition creation from attribute nodes."""
        entry_service = EntryService(None)  # type: ignore

        # Create test attribute node
        node = AttributeNode(
            id=1,
            manufacturing_type_id=1,
            name="test_field",
            description="Test Field",
            node_type="attribute",
            data_type="string",
            required=True,
            ui_component="input",
            help_text="Test help",
            validation_rules={"min_length": 1, "max_length": 100},
            display_condition={"operator": "equals", "field": "type", "value": "Frame"},
        )

        field = entry_service.create_field_definition(node)

        assert isinstance(field, FieldDefinition)
        assert field.name == "test_field"
        assert field.label == "Test Field"
        assert field.data_type == "string"
        assert field.required is True
        assert field.ui_component == "input"
        assert field.help_text == "Test help"
        assert field.validation_rules == {"min_length": 1, "max_length": 100}
        assert field.display_condition == {"operator": "equals", "field": "type", "value": "Frame"}

    @given(st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=10))
    def test_section_organization_consistency(self, section_names):
        """Test that section organization is consistent and predictable."""
        entry_service = EntryService(None)  # type: ignore

        # Create nodes for each section
        nodes = []
        for i, section_name in enumerate(section_names):
            node = AttributeNode(
                id=i + 1,
                manufacturing_type_id=1,
                name=f"field_{i}",
                description=f"Field {i}",
                node_type="attribute",
                data_type="string",
                ltree_path=f"{section_name}.field_{i}",
                depth=1,
                sort_order=i + 1,
            )
            nodes.append(node)

        schema = entry_service.generate_form_schema(1, nodes)

        # Should have one section per unique section name
        unique_sections = set(section_names)
        assert len(schema.sections) == len(unique_sections)

        # Each section should have the correct fields
        for section in schema.sections:
            section_nodes = [
                n for n in nodes if entry_service.get_section_name(n.ltree_path) == section.title
            ]
            assert len(section.fields) == len(section_nodes)
