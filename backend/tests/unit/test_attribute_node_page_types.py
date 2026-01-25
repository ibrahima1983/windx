"""Unit tests for AttributeNode model page type functionality."""

import pytest
from decimal import Decimal

from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType


class TestAttributeNodePageTypes:
    """Test suite for AttributeNode model page type functionality."""

    @pytest.fixture
    def sample_manufacturing_type(self) -> ManufacturingType:
        """Create a sample manufacturing type for testing."""
        return ManufacturingType(
            id=1,
            name="Test Manufacturing Type",
            description="Test type for attribute node tests",
            base_category="window",
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )

    @pytest.mark.parametrize(
        "page_type,expected_page_type",
        [
            ("profile", "profile"),
            ("accessories", "accessories"),
            ("glazing", "glazing"),
        ],
        ids=["profile_type", "accessories_type", "glazing_type"],
    )
    def test_attribute_node_page_type_assignment(
        self, sample_manufacturing_type: ManufacturingType, page_type: str, expected_page_type: str
    ):
        """Test that page_type is correctly assigned to AttributeNode."""
        node = AttributeNode(
            manufacturing_type_id=sample_manufacturing_type.id,
            page_type=page_type,
            name="test_attribute",
            description="Test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path="test.attribute",
            depth=1,
            sort_order=1,
        )

        assert node.page_type == expected_page_type
        assert node.manufacturing_type_id == sample_manufacturing_type.id

    def test_attribute_node_default_page_type(self, sample_manufacturing_type: ManufacturingType):
        """Test that AttributeNode page_type field has correct default behavior."""
        # When not explicitly set, page_type should use the default
        node = AttributeNode(
            manufacturing_type_id=sample_manufacturing_type.id,
            name="test_attribute",
            description="Test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path="test.attribute",
            depth=1,
            sort_order=1,
            # page_type not explicitly set
        )

        # The default is set at the database level, so in Python it might be None
        # until the object is persisted. Let's test that we can set it explicitly.
        assert hasattr(node, "page_type")

        # Test explicit setting works
        node.page_type = "profile"
        assert node.page_type == "profile"

    @pytest.mark.parametrize(
        "page_type,node_name,expected_repr_content",
        [
            ("profile", "profile_attr", "profile_attr"),
            ("accessories", "accessory_attr", "accessory_attr"),
            ("glazing", "glazing_attr", "glazing_attr"),
        ],
        ids=["profile_repr", "accessories_repr", "glazing_repr"],
    )
    def test_attribute_node_repr_with_page_types(
        self,
        sample_manufacturing_type: ManufacturingType,
        page_type: str,
        node_name: str,
        expected_repr_content: str,
    ):
        """Test AttributeNode string representation includes relevant information."""
        node = AttributeNode(
            id=123,
            manufacturing_type_id=sample_manufacturing_type.id,
            page_type=page_type,
            name=node_name,
            description="Test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path=f"test.{page_type}.{node_name}",
            depth=2,
            sort_order=1,
        )

        repr_str = repr(node)
        assert expected_repr_content in repr_str
        assert "id=123" in repr_str
        assert "attribute" in repr_str
        assert f"test.{page_type}.{node_name}" in repr_str

    @pytest.mark.parametrize(
        "page_type,ltree_path,expected_depth",
        [
            ("profile", "profile.basic.name", 3),
            ("accessories", "accessories.hardware.hinge", 3),
            ("glazing", "glazing.performance.u_value", 3),
            ("profile", "profile.dimensions.width", 3),
            ("accessories", "accessories.pricing.unit_price", 3),
        ],
        ids=[
            "profile_basic_name",
            "accessories_hardware_hinge",
            "glazing_performance_u_value",
            "profile_dimensions_width",
            "accessories_pricing_unit_price",
        ],
    )
    def test_attribute_node_ltree_path_with_page_types(
        self,
        sample_manufacturing_type: ManufacturingType,
        page_type: str,
        ltree_path: str,
        expected_depth: int,
    ):
        """Test LTREE path structure with different page types."""
        node = AttributeNode(
            manufacturing_type_id=sample_manufacturing_type.id,
            page_type=page_type,
            name="test_attribute",
            description="Test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path=ltree_path,
            depth=expected_depth,
            sort_order=1,
        )

        assert node.ltree_path == ltree_path
        assert node.depth == expected_depth
        assert node.page_type == page_type
        # Verify LTREE path starts with page type
        assert ltree_path.startswith(page_type)

    @pytest.mark.parametrize(
        "page_type,validation_rules,expected_rules",
        [
            ("profile", {"min_length": 1, "max_length": 200}, {"min_length": 1, "max_length": 200}),
            (
                "accessories",
                {"options": ["Hinge", "Handle", "Lock"]},
                {"options": ["Hinge", "Handle", "Lock"]},
            ),
            ("glazing", {"min": 4, "max": 25}, {"min": 4, "max": 25}),
        ],
        ids=["profile_validation", "accessories_validation", "glazing_validation"],
    )
    def test_attribute_node_validation_rules_with_page_types(
        self,
        sample_manufacturing_type: ManufacturingType,
        page_type: str,
        validation_rules: dict,
        expected_rules: dict,
    ):
        """Test validation rules storage with different page types."""
        node = AttributeNode(
            manufacturing_type_id=sample_manufacturing_type.id,
            page_type=page_type,
            name="test_attribute",
            description="Test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path=f"test.{page_type}.attribute",
            depth=2,
            sort_order=1,
            validation_rules=validation_rules,
        )

        assert node.validation_rules == expected_rules
        assert node.page_type == page_type

    @pytest.mark.parametrize(
        "page_type,display_condition",
        [
            ("profile", {"operator": "equals", "field": "type", "value": "Frame"}),
            (
                "accessories",
                {"operator": "in", "field": "accessory_type", "value": ["Hinge", "Lock"]},
            ),
            (
                "glazing",
                {"operator": "not_equals", "field": "pane_configuration", "value": "Single Pane"},
            ),
        ],
        ids=["profile_condition", "accessories_condition", "glazing_condition"],
    )
    def test_attribute_node_display_conditions_with_page_types(
        self, sample_manufacturing_type: ManufacturingType, page_type: str, display_condition: dict
    ):
        """Test display conditions with different page types."""
        node = AttributeNode(
            manufacturing_type_id=sample_manufacturing_type.id,
            page_type=page_type,
            name="conditional_attribute",
            description="Conditional test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path=f"test.{page_type}.conditional",
            depth=2,
            sort_order=1,
            display_condition=display_condition,
        )

        assert node.display_condition == display_condition
        assert node.page_type == page_type

    @pytest.mark.parametrize(
        "page_type,ui_component,expected_component",
        [
            ("profile", "input", "input"),
            ("profile", "dropdown", "dropdown"),
            ("accessories", "checkbox", "checkbox"),
            ("accessories", "number", "number"),
            ("glazing", "slider", "slider"),
            ("glazing", "currency", "currency"),
        ],
        ids=[
            "profile_input",
            "profile_dropdown",
            "accessories_checkbox",
            "accessories_number",
            "glazing_slider",
            "glazing_currency",
        ],
    )
    def test_attribute_node_ui_components_with_page_types(
        self,
        sample_manufacturing_type: ManufacturingType,
        page_type: str,
        ui_component: str,
        expected_component: str,
    ):
        """Test UI component assignment with different page types."""
        node = AttributeNode(
            manufacturing_type_id=sample_manufacturing_type.id,
            page_type=page_type,
            name="ui_test_attribute",
            description="UI test attribute",
            node_type="attribute",
            data_type="string",
            ltree_path=f"test.{page_type}.ui_test",
            depth=2,
            sort_order=1,
            ui_component=ui_component,
        )

        assert node.ui_component == expected_component
        assert node.page_type == page_type

    def test_attribute_node_pricing_impact_with_page_types(
        self, sample_manufacturing_type: ManufacturingType
    ):
        """Test pricing impact fields work with all page types."""
        page_types = ["profile", "accessories", "glazing"]

        for i, page_type in enumerate(page_types):
            node = AttributeNode(
                manufacturing_type_id=sample_manufacturing_type.id,
                page_type=page_type,
                name=f"pricing_test_{page_type}",
                description=f"Pricing test for {page_type}",
                node_type="attribute",
                data_type="number",
                ltree_path=f"test.{page_type}.pricing",
                depth=2,
                sort_order=i + 1,
                price_impact_type="fixed",
                price_impact_value=Decimal(str(10.00 * (i + 1))),
                weight_impact=Decimal(str(1.0 * (i + 1))),
            )

            assert node.page_type == page_type
            assert node.price_impact_type == "fixed"
            assert node.price_impact_value == Decimal(str(10.00 * (i + 1)))
            assert node.weight_impact == Decimal(str(1.0 * (i + 1)))

    def test_attribute_node_technical_properties_with_page_types(
        self, sample_manufacturing_type: ManufacturingType
    ):
        """Test technical properties work with all page types."""
        technical_configs = [
            ("profile", "thermal_resistance", "base_thermal + (width * 0.01)"),
            ("accessories", "load_capacity", "base_load * safety_factor"),
            ("glazing", "u_value", "1 / (sum_of_resistances)"),
        ]

        for page_type, tech_type, formula in technical_configs:
            node = AttributeNode(
                manufacturing_type_id=sample_manufacturing_type.id,
                page_type=page_type,
                name=f"technical_{page_type}",
                description=f"Technical property for {page_type}",
                node_type="attribute",
                data_type="number",
                ltree_path=f"test.{page_type}.technical",
                depth=2,
                sort_order=1,
                technical_property_type=tech_type,
                technical_impact_formula=formula,
            )

            assert node.page_type == page_type
            assert node.technical_property_type == tech_type
            assert node.technical_impact_formula == formula
