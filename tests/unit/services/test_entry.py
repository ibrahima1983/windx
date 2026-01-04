"""Unit tests for entry service and condition evaluators.

Tests service creation with database session and authentication integration,
operator parity between Python and JavaScript versions, and complex nested
conditions with performance considerations.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.models.attribute_node import AttributeNode
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import ConditionEvaluator, EntryService


class TestEntryServiceBusinessRules:
    """Test business rules functionality in EntryService."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = AsyncMock()
        self.service = EntryService(self.mock_db)

    def test_evaluate_business_rules_frame_type(self):
        """Test business rules for frame type."""
        form_data = {
            "type": "Frame",
            "opening_system": "sliding",
            "builtin_flyscreen_track": True
        }
        
        visibility = self.service.evaluate_business_rules(form_data)
        
        # Frame-specific fields should be visible
        assert visibility["renovation"] is True
        assert visibility["renovation_height"] is True
        assert visibility["builtin_flyscreen_track"] is True
        assert visibility["total_width"] is True  # Because builtin_flyscreen_track is True
        assert visibility["flyscreen_track_height"] is True  # Because builtin_flyscreen_track is True
        
        # Non-frame fields should be hidden
        assert visibility["sash_overlap"] is False
        assert visibility["flying_mullion_horizontal_clearance"] is False
        assert visibility["glazing_undercut_height"] is False

    def test_evaluate_business_rules_sash_type(self):
        """Test business rules for sash type."""
        form_data = {
            "type": "sash",
            "opening_system": "casement"
        }
        
        visibility = self.service.evaluate_business_rules(form_data)
        
        # Sash-specific fields should be visible
        assert visibility["sash_overlap"] is True
        
        # Non-sash fields should be hidden
        assert visibility["renovation"] is False
        assert visibility["flying_mullion_horizontal_clearance"] is False
        assert visibility["glazing_undercut_height"] is False
        assert visibility["builtin_flyscreen_track"] is False

    def test_evaluate_business_rules_flying_mullion_type(self):
        """Test business rules for flying mullion type."""
        form_data = {
            "type": "Flying mullion",
            "opening_system": "casement"
        }
        
        visibility = self.service.evaluate_business_rules(form_data)
        
        # Flying mullion-specific fields should be visible
        assert visibility["flying_mullion_horizontal_clearance"] is True
        assert visibility["flying_mullion_vertical_clearance"] is True
        
        # Non-flying mullion fields should be hidden
        assert visibility["renovation"] is False
        assert visibility["sash_overlap"] is False
        assert visibility["glazing_undercut_height"] is False

    async def test_add_field_option_success(self):
        """Test successful field option addition."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        self.db.add(mfg_type)
        await self.db.commit()
        await self.db.refresh(mfg_type)
        
        # Create parent field
        parent_field = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="material",
            node_type="attribute",
            ltree_path=f"mfg_{mfg_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True
        )
        self.db.add(parent_field)
        await self.db.commit()
        await self.db.refresh(parent_field)
        
        # Add new option
        result = await self.service.add_field_option(
            mfg_type.id, "material", "Steel", "profile"
        )
        
        assert result["success"] is True
        assert "Steel" in result["message"]
        assert result["field_name"] == "material"
        assert result["option_value"] == "Steel"
        assert "option_id" in result

    async def test_add_field_option_manufacturing_type_not_found(self):
        """Test add field option with non-existent manufacturing type."""
        from app.core.exceptions import NotFoundException
        
        with pytest.raises(NotFoundException) as exc_info:
            await self.service.add_field_option(99999, "material", "Steel", "profile")
        
        assert "Manufacturing type 99999 not found" in str(exc_info.value)

    async def test_add_field_option_field_not_found(self):
        """Test add field option with non-existent field."""
        from app.core.exceptions import NotFoundException
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        self.db.add(mfg_type)
        await self.db.commit()
        await self.db.refresh(mfg_type)
        
        with pytest.raises(NotFoundException) as exc_info:
            await self.service.add_field_option(mfg_type.id, "nonexistent_field", "Steel", "profile")
        
        assert "Field 'nonexistent_field' not found" in str(exc_info.value)

    async def test_add_field_option_duplicate(self):
        """Test adding duplicate field option."""
        from app.models.attribute_node import AttributeNode
        from app.core.exceptions import ValidationException
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        self.db.add(mfg_type)
        await self.db.commit()
        await self.db.refresh(mfg_type)
        
        # Create parent field and existing option
        parent_field = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="material",
            node_type="attribute",
            ltree_path=f"mfg_{mfg_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True
        )
        self.db.add(parent_field)
        await self.db.commit()
        await self.db.refresh(parent_field)
        
        existing_option = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=parent_field.id,
            name="Steel",
            node_type="option",
            ltree_path=f"mfg_{mfg_type.id}.material.steel",
            depth=2,
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            is_required=False,
            is_active=True
        )
        self.db.add(existing_option)
        await self.db.commit()
        
        # Try to add duplicate option
        with pytest.raises(ValidationException) as exc_info:
            await self.service.add_field_option(mfg_type.id, "material", "Steel", "profile")
        
        assert "Option 'Steel' already exists" in str(exc_info.value)

    async def test_remove_field_option_success(self):
        """Test successful field option removal."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        self.db.add(mfg_type)
        await self.db.commit()
        await self.db.refresh(mfg_type)
        
        # Create parent field and option to remove
        parent_field = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="material",
            node_type="attribute",
            ltree_path=f"mfg_{mfg_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True
        )
        self.db.add(parent_field)
        await self.db.commit()
        await self.db.refresh(parent_field)
        
        option_to_remove = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=parent_field.id,
            name="Steel",
            node_type="option",
            ltree_path=f"mfg_{mfg_type.id}.material.steel",
            depth=2,
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            is_required=False,
            is_active=True
        )
        self.db.add(option_to_remove)
        await self.db.commit()
        await self.db.refresh(option_to_remove)
        
        # Remove the option
        result = await self.service.remove_field_option(option_to_remove.id)
        
        assert result["success"] is True
        assert "Steel" in result["message"]
        assert result["option_id"] == option_to_remove.id
        assert result["option_name"] == "Steel"
        assert result["field_name"] == "material"

    async def test_remove_field_option_not_found(self):
        """Test remove field option with non-existent option."""
        from app.core.exceptions import NotFoundException
        
        with pytest.raises(NotFoundException) as exc_info:
            await self.service.remove_field_option(99999)
        
        assert "Option 99999 not found" in str(exc_info.value)

    def test_get_field_display_value_with_business_rules(self):
        """Test field display value with business rules applied."""
        form_data = {
            "type": "sash",
            "sash_overlap": "8",
            "renovation": "yes"  # Not applicable for sash
        }
        
        # Field that applies to current type should show value
        display_value = self.service.get_field_display_value("sash_overlap", "8", form_data)
        assert display_value == "8"
        
        # Field that doesn't apply to current type should show N/A
        display_value = self.service.get_field_display_value("renovation", "yes", form_data)
        assert display_value == "N/A"


class TestConditionEvaluator:
    """Test the ConditionEvaluator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ConditionEvaluator()
        self.sample_form_data = {
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "sliding",
            "width": 48.5,
            "builtin_flyscreen_track": True,
            "nested": {"child": {"value": "test"}},
        }

    def test_comparison_operators(self):
        """Test comparison operators work correctly."""
        # Equals
        condition = {"operator": "equals", "field": "type", "value": "Frame"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        condition = {"operator": "equals", "field": "type", "value": "Door"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

        # Not equals
        condition = {"operator": "not_equals", "field": "type", "value": "Door"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        # Greater than
        condition = {"operator": "greater_than", "field": "width", "value": 40}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        condition = {"operator": "greater_than", "field": "width", "value": 50}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

    def test_string_operators(self):
        """Test string operators work correctly."""
        # Contains
        condition = {"operator": "contains", "field": "opening_system", "value": "slid"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        condition = {"operator": "contains", "field": "opening_system", "value": "casement"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

        # Starts with
        condition = {"operator": "starts_with", "field": "material", "value": "Alum"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        # Ends with
        condition = {"operator": "ends_with", "field": "material", "value": "inum"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        # Pattern matching
        condition = {"operator": "matches_pattern", "field": "type", "value": "^Frame$"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

    def test_collection_operators(self):
        """Test collection operators work correctly."""
        # In
        condition = {"operator": "in", "field": "type", "value": ["Frame", "Door"]}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        condition = {"operator": "in", "field": "type", "value": ["Door", "Window"]}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

        # Not in
        condition = {"operator": "not_in", "field": "type", "value": ["Door", "Window"]}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

    def test_existence_operators(self):
        """Test existence operators work correctly."""
        # Exists
        condition = {"operator": "exists", "field": "type", "value": None}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        condition = {"operator": "exists", "field": "nonexistent", "value": None}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

        # Not exists
        condition = {"operator": "not_exists", "field": "nonexistent", "value": None}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        # Is empty
        empty_data = {"empty_field": ""}
        condition = {"operator": "is_empty", "field": "empty_field", "value": None}
        assert self.evaluator.evaluate_condition(condition, empty_data) is True

        # Is not empty
        condition = {"operator": "is_not_empty", "field": "type", "value": None}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

    def test_logical_operators(self):
        """Test logical operators work correctly."""
        # AND
        condition = {
            "operator": "and",
            "conditions": [
                {"operator": "equals", "field": "type", "value": "Frame"},
                {"operator": "equals", "field": "material", "value": "Aluminum"},
            ],
        }
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        condition = {
            "operator": "and",
            "conditions": [
                {"operator": "equals", "field": "type", "value": "Frame"},
                {"operator": "equals", "field": "material", "value": "Wood"},
            ],
        }
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

        # OR
        condition = {
            "operator": "or",
            "conditions": [
                {"operator": "equals", "field": "type", "value": "Door"},
                {"operator": "equals", "field": "material", "value": "Aluminum"},
            ],
        }
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        # NOT
        condition = {
            "operator": "not",
            "condition": {"operator": "equals", "field": "type", "value": "Door"},
        }
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

    def test_nested_field_access(self):
        """Test nested field access with dot notation."""
        # Simple nested access
        condition = {"operator": "equals", "field": "nested.child.value", "value": "test"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

        # Non-existent nested field
        condition = {"operator": "equals", "field": "nested.nonexistent.value", "value": "test"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is False

    def test_complex_nested_conditions(self):
        """Test complex nested conditions with multiple levels."""
        condition = {
            "operator": "and",
            "conditions": [
                {
                    "operator": "or",
                    "conditions": [
                        {"operator": "equals", "field": "type", "value": "Frame"},
                        {"operator": "equals", "field": "type", "value": "Door"},
                    ],
                },
                {
                    "operator": "and",
                    "conditions": [
                        {"operator": "contains", "field": "opening_system", "value": "sliding"},
                        {"operator": "greater_than", "field": "width", "value": 40},
                    ],
                },
            ],
        }
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True

    def test_invalid_operator_handling(self):
        """Test handling of invalid operators."""
        condition = {"operator": "invalid_operator", "field": "type", "value": "Frame"}

        with pytest.raises(ValueError, match="Unknown operator"):
            self.evaluator.evaluate_condition(condition, self.sample_form_data)

    def test_empty_conditions(self):
        """Test handling of empty or None conditions."""
        # Empty condition should return True
        assert self.evaluator.evaluate_condition({}, self.sample_form_data) is True
        assert self.evaluator.evaluate_condition(None, self.sample_form_data) is True

        # Condition without operator should return True
        condition = {"field": "type", "value": "Frame"}
        assert self.evaluator.evaluate_condition(condition, self.sample_form_data) is True


class TestEntryService:
    """Test the EntryService class."""

    @pytest.fixture
    def mock_db(self):
        """Create mock database session."""
        db = AsyncMock()
        return db

    @pytest.fixture
    def entry_service(self, mock_db):
        """Create EntryService instance with mock database."""
        return EntryService(mock_db)

    @pytest.fixture
    def sample_manufacturing_type(self):
        """Create sample manufacturing type."""
        return ManufacturingType(
            id=1,
            name="Test Window",
            description="Test window type",
            base_price=200.00,
            base_weight=15.00,
            is_active=True,
        )

    @pytest.fixture
    def sample_attribute_nodes(self):
        """Create sample attribute nodes."""
        return [
            AttributeNode(
                id=1,
                manufacturing_type_id=1,
                name="type",
                node_type="attribute",
                data_type="string",
                required=True,
                ltree_path="basic.type",
                description="Product type",
                ui_component="dropdown",
            ),
            AttributeNode(
                id=2,
                manufacturing_type_id=1,
                name="material",
                node_type="attribute",
                data_type="string",
                required=True,
                ltree_path="basic.material",
                description="Material type",
                ui_component="dropdown",
            ),
            AttributeNode(
                id=3,
                manufacturing_type_id=1,
                name="width",
                node_type="attribute",
                data_type="number",
                required=False,
                ltree_path="dimensions.width",
                description="Width in inches",
                ui_component="input",
                validation_rules={"min": 10, "max": 100},
            ),
        ]

    @pytest.fixture
    def sample_user(self):
        """Create sample user."""
        return User(
            id=1, email="test@example.com", username="testuser", is_active=True, is_superuser=False
        )

    @pytest.mark.asyncio
    async def test_service_initialization(self, mock_db):
        """Test service creation with database session."""
        service = EntryService(mock_db)

        assert service.db == mock_db
        assert isinstance(service.condition_evaluator, ConditionEvaluator)

    @pytest.mark.asyncio
    async def test_get_profile_schema_success(
        self, entry_service, sample_manufacturing_type, sample_attribute_nodes
    ):
        """Test successful profile schema generation."""
        # Mock database queries
        entry_service.db.execute = AsyncMock()

        # Mock manufacturing type query
        mfg_result = MagicMock()
        mfg_result.scalar_one_or_none.return_value = sample_manufacturing_type

        # Mock attribute nodes query
        attr_result = MagicMock()
        attr_result.scalars.return_value.all.return_value = sample_attribute_nodes

        entry_service.db.execute.side_effect = [mfg_result, attr_result]

        # Test schema generation
        schema = await entry_service.get_profile_schema(1)

        assert schema.manufacturing_type_id == 1
        assert len(schema.sections) > 0

        # Check that fields were created
        all_fields = []
        for section in schema.sections:
            all_fields.extend(section.fields)

        field_names = [field.name for field in all_fields]
        assert "type" in field_names
        assert "material" in field_names
        assert "width" in field_names

    @pytest.mark.asyncio
    async def test_get_profile_schema_not_found(self, entry_service):
        """Test profile schema generation with non-existent manufacturing type."""
        # Mock database query to return None
        entry_service.db.execute = AsyncMock()
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        entry_service.db.execute.return_value = result

        with pytest.raises(NotFoundException, match="Manufacturing type 999 not found"):
            await entry_service.get_profile_schema(999)

    def test_generate_form_schema(self, entry_service, sample_attribute_nodes):
        """Test form schema generation from attribute nodes."""
        schema = entry_service.generate_form_schema(1, sample_attribute_nodes)

        assert schema.manufacturing_type_id == 1
        assert len(schema.sections) > 0

        # Check sections were created based on LTREE paths
        section_titles = [section.title for section in schema.sections]
        assert "Basic" in section_titles
        assert "Dimensions" in section_titles

    def test_create_field_definition(self, entry_service, sample_attribute_nodes):
        """Test field definition creation from attribute node."""
        node = sample_attribute_nodes[2]  # width field with validation
        field = entry_service.create_field_definition(node)

        assert field.name == "width"
        assert field.label == "Width (mm)"  # Updated to match new implementation
        assert field.data_type == "number"
        assert field.required is False
        assert field.validation_rules == {"min": 10, "max": 100}
        assert field.ui_component == "text"  # Updated to match new implementation

    async def test_generate_preview_headers(self, entry_service, sample_manufacturing_type, sample_attribute_nodes):
        """Test dynamic preview header generation."""
        # Mock database query
        entry_service.db.execute = AsyncMock()
        attr_result = MagicMock()
        attr_result.scalars.return_value.all.return_value = sample_attribute_nodes
        entry_service.db.execute.return_value = attr_result
        
        headers = await entry_service.generate_preview_headers(sample_manufacturing_type.id)
        
        # Should start with id and Name
        assert headers[0] == "id"
        assert headers[1] == "Name"
        
        # Should include headers for attribute nodes (not categories)
        assert "Product Type" in headers
        assert "Material" in headers
        assert "Width (mm)" in headers
        
        # The actual order based on the test output
        expected_order = ["id", "Name", "Product Type", "Material", "Width (mm)"]
        assert headers == expected_order

    async def test_generate_header_mapping(self, entry_service, sample_manufacturing_type, sample_attribute_nodes):
        """Test dynamic header mapping generation."""
        # Mock database query
        entry_service.db.execute = AsyncMock()
        attr_result = MagicMock()
        attr_result.scalars.return_value.all.return_value = sample_attribute_nodes
        entry_service.db.execute.return_value = attr_result
        
        mapping = await entry_service.generate_header_mapping(sample_manufacturing_type.id)
        
        # Should include special cases
        assert mapping["id"] == "id"
        assert mapping["Name"] == "name"
        
        # Should map headers to field names
        assert mapping["Product Type"] == "type"  # Updated to match actual implementation
        assert mapping["Material"] == "material"
        assert mapping["Width (mm)"] == "width"

    async def test_get_reverse_header_mapping(self, entry_service, sample_manufacturing_type, sample_attribute_nodes):
        """Test reverse header mapping generation."""
        # Mock database query
        entry_service.db.execute = AsyncMock()
        attr_result = MagicMock()
        attr_result.scalars.return_value.all.return_value = sample_attribute_nodes
        entry_service.db.execute.return_value = attr_result
        
        reverse_mapping = await entry_service.get_reverse_header_mapping(sample_manufacturing_type.id)
        
        # Should map field names to headers
        assert reverse_mapping["id"] == "id"
        assert reverse_mapping["name"] == "Name"
        assert reverse_mapping["type"] == "Product Type"  # Updated to match actual implementation
        assert reverse_mapping["material"] == "Material"
        assert reverse_mapping["width"] == "Width (mm)"

    def test_clear_header_cache(self, entry_service):
        """Test header cache clearing."""
        # Add some test data to cache
        entry_service._header_cache[1] = ["test"]
        entry_service._mapping_cache[1] = {"test": "test"}
        entry_service._reverse_mapping_cache[1] = {"test": "test"}
        
        # Clear specific manufacturing type
        entry_service.clear_header_cache(1)
        assert 1 not in entry_service._header_cache
        assert 1 not in entry_service._mapping_cache
        assert 1 not in entry_service._reverse_mapping_cache
        
        # Add test data again
        entry_service._header_cache[1] = ["test"]
        entry_service._mapping_cache[1] = {"test": "test"}
        
        # Clear all
        entry_service.clear_header_cache()
        assert len(entry_service._header_cache) == 0
        assert len(entry_service._mapping_cache) == 0
        assert len(entry_service._reverse_mapping_cache) == 0

    def test_get_section_name(self, entry_service):
        """Test section name extraction from LTREE path."""
        assert entry_service.get_section_name("basic.type") == "Basic"
        assert entry_service.get_section_name("dimensions.width.value") == "Dimensions"
        assert entry_service.get_section_name("") == "general"
        assert entry_service.get_section_name("single") == "Single"

    @pytest.mark.asyncio
    async def test_evaluate_display_conditions(self, entry_service):
        """Test display condition evaluation."""
        from app.schemas.entry import ProfileSchema

        # Create schema with conditional logic
        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[],
            conditional_logic={
                "renovation": {"operator": "equals", "field": "type", "value": "Frame"},
                "flyscreen_width": {
                    "operator": "and",
                    "conditions": [
                        {"operator": "equals", "field": "type", "value": "Frame"},
                        {"operator": "equals", "field": "builtin_flyscreen_track", "value": True},
                    ],
                },
            },
        )

        form_data = {"type": "Frame", "builtin_flyscreen_track": True}

        visibility = await entry_service.evaluate_display_conditions(form_data, schema)

        assert visibility["renovation"] is True
        assert visibility["flyscreen_width"] is True

        # Test with different form data
        form_data["type"] = "Door"
        visibility = await entry_service.evaluate_display_conditions(form_data, schema)

        assert visibility["renovation"] is False
        assert visibility["flyscreen_width"] is False

    def test_validate_field_value(self, entry_service):
        """Test field value validation against rules."""
        # Range validation
        error = entry_service.validate_field_value(5, {"min": 10, "max": 100}, "Width")
        assert "must be at least 10" in error

        error = entry_service.validate_field_value(150, {"min": 10, "max": 100}, "Width")
        assert "must be at most 100" in error

        error = entry_service.validate_field_value(50, {"min": 10, "max": 100}, "Width")
        assert error is None

        # Pattern validation
        error = entry_service.validate_field_value(
            "invalid", {"pattern": "^[A-Z]{2}\\d{5}$"}, "Code"
        )
        assert "format is invalid" in error

        error = entry_service.validate_field_value(
            "AB12345", {"pattern": "^[A-Z]{2}\\d{5}$"}, "Code"
        )
        assert error is None

        # Length validation
        error = entry_service.validate_field_value("ab", {"min_length": 5}, "Name")
        assert "must be at least 5 characters" in error

        error = entry_service.validate_field_value("a" * 200, {"max_length": 100}, "Name")
        assert "must be at most 100 characters" in error

    @pytest.mark.asyncio
    async def test_validate_profile_data_success(
        self, entry_service, sample_manufacturing_type, sample_attribute_nodes
    ):
        """Test successful profile data validation."""
        # Mock get_profile_schema
        entry_service.get_profile_schema = AsyncMock()
        from app.schemas.entry import FieldDefinition, FormSection, ProfileSchema

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[
                FormSection(
                    title="Basic",
                    fields=[
                        FieldDefinition(
                            name="type", label="Type", data_type="string", required=True
                        ),
                        FieldDefinition(
                            name="width",
                            label="Width",
                            data_type="number",
                            validation_rules={"min": 10, "max": 100},
                        ),
                    ],
                )
            ],
        )
        entry_service.get_profile_schema.return_value = schema

        # Valid profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=1,
            name="Test Window",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Series100",
            width=50.0,
        )

        result = await entry_service.validate_profile_data(profile_data)
        assert result["valid"] is True

    @pytest.mark.asyncio
    async def test_validate_profile_data_validation_errors(self, entry_service):
        """Test profile data validation with errors."""
        # Mock get_profile_schema
        entry_service.get_profile_schema = AsyncMock()
        from app.schemas.entry import FieldDefinition, FormSection, ProfileSchema

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[
                FormSection(
                    title="Basic",
                    fields=[
                        FieldDefinition(
                            name="type", label="Type", data_type="string", required=True
                        ),
                        FieldDefinition(
                            name="width",
                            label="Width",
                            data_type="number",
                            validation_rules={"min": 10, "max": 100},
                        ),
                    ],
                )
            ],
        )
        entry_service.get_profile_schema.return_value = schema

        # Invalid profile data (missing required field, invalid width)
        profile_data = ProfileEntryData(
            manufacturing_type_id=1,
            name="Test Window",
            type="",  # Empty required field
            material="Aluminum",
            opening_system="Casement",
            system_series="Series100",
            width=150.0,  # Exceeds max
        )

        with pytest.raises(ValidationException) as exc_info:
            await entry_service.validate_profile_data(profile_data)

        assert "Validation failed" in str(exc_info.value)
        # Check field_errors attribute instead of converting to string
        assert "Type is required" in exc_info.value.field_errors.get("type", "")
        assert "must be at most 100" in exc_info.value.field_errors.get("width", "")

    def test_format_preview_value(self, entry_service):
        """Test preview value formatting."""
        assert entry_service.format_preview_value(None) == "N/A"
        assert entry_service.format_preview_value(True) == "yes"
        assert entry_service.format_preview_value(False) == "no"
        assert entry_service.format_preview_value(["A", "B", "C"]) == "A, B, C"
        assert entry_service.format_preview_value({"key": "value"}) == "{'key': 'value'}"
        assert entry_service.format_preview_value("test") == "test"
        assert entry_service.format_preview_value(42) == "42"


class TestEntryServiceWithDatabase:
    """Test EntryService methods that require real database operations."""

    @pytest_asyncio.fixture
    async def entry_service(self, db_session: AsyncSession):
        """Create EntryService instance with real database session."""
        return EntryService(db_session)

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_success(
        self, entry_service: EntryService, db_session: AsyncSession
    ):
        """Test successful field option removal by name."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)
        
        # Create parent field and option to remove
        parent_field = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="material",
            node_type="attribute",
            page_type="profile",
            ltree_path=f"mfg_{mfg_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)
        
        option_to_remove = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            parent_node_id=parent_field.id,
            name="Steel",
            node_type="option",
            page_type="profile",
            ltree_path=f"mfg_{mfg_type.id}.material.steel",
            depth=2,
            data_type="string",
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            is_required=False,
            is_active=True
        )
        db_session.add(option_to_remove)
        await db_session.commit()
        await db_session.refresh(option_to_remove)
        
        # Remove the option by name
        result = await entry_service.remove_field_option_by_name(
            mfg_type.id, "material", "Steel", "profile"
        )
        
        assert result["success"] is True
        assert "Steel" in result["message"]
        assert result["option_id"] == option_to_remove.id
        assert result["field_name"] == "material"
        assert result["option_value"] == "Steel"
        assert result["manufacturing_type_id"] == mfg_type.id

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_field_not_found(
        self, entry_service: EntryService, db_session: AsyncSession
    ):
        """Test remove field option by name with non-existent field."""
        from app.core.exceptions import NotFoundException
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)
        
        with pytest.raises(NotFoundException) as exc_info:
            await entry_service.remove_field_option_by_name(
                mfg_type.id, "nonexistent_field", "Steel", "profile"
            )
        
        assert "Field 'nonexistent_field' not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_remove_field_option_by_name_option_not_found(
        self, entry_service: EntryService, db_session: AsyncSession
    ):
        """Test remove field option by name with non-existent option."""
        from app.models.attribute_node import AttributeNode
        from decimal import Decimal
        
        # Create a manufacturing type
        mfg_type = ManufacturingType(
            name="Test Window",
            description="Test window type",
            base_price=Decimal("200.00"),
            base_weight=Decimal("25.00"),
            is_active=True
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)
        
        # Create parent field but no option
        parent_field = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="material",
            node_type="attribute",
            page_type="profile",
            ltree_path=f"mfg_{mfg_type.id}.material",
            depth=1,
            data_type="string",
            is_required=False,
            is_active=True
        )
        db_session.add(parent_field)
        await db_session.commit()
        await db_session.refresh(parent_field)
        
        # Try to remove non-existent option
        result = await entry_service.remove_field_option_by_name(
            mfg_type.id, "material", "NonexistentOption", "profile"
        )
        
        assert result["success"] is False
        assert "Option 'NonexistentOption' not found in field 'material'" in result["error"]


class TestOperatorParity:
    """Test parity between Python and JavaScript operators."""

    def test_comparison_operator_parity(self):
        """Test that comparison operators work identically."""
        evaluator = ConditionEvaluator()
        test_cases = [
            (5, 5, True),  # equals
            (5, 3, False),  # equals
            (5, 3, True),  # not_equals
            (5, 5, False),  # not_equals
            (5, 3, True),  # greater_than
            (3, 5, False),  # greater_than
            (5, 3, False),  # less_than
            (3, 5, True),  # less_than
        ]

        operators = ["equals", "not_equals", "greater_than", "less_than"]

        for i, (a, b, expected) in enumerate(test_cases):
            operator = operators[i // 2]
            result = evaluator.OPERATORS[operator](a, b)
            assert result == expected, f"Operator {operator} failed for {a}, {b}"

    def test_string_operator_parity(self):
        """Test that string operators work identically."""
        evaluator = ConditionEvaluator()

        # Contains (case insensitive)
        assert evaluator.OPERATORS["contains"]("Hello World", "hello") is True
        assert evaluator.OPERATORS["contains"]("Hello World", "xyz") is False

        # Starts with (case insensitive)
        assert evaluator.OPERATORS["starts_with"]("Hello World", "hello") is True
        assert evaluator.OPERATORS["starts_with"]("Hello World", "world") is False

        # Ends with (case insensitive)
        assert evaluator.OPERATORS["ends_with"]("Hello World", "world") is True
        assert evaluator.OPERATORS["ends_with"]("Hello World", "hello") is False

    def test_collection_operator_parity(self):
        """Test that collection operators work identically."""
        evaluator = ConditionEvaluator()

        # In operator
        assert evaluator.OPERATORS["in"]("apple", ["apple", "banana"]) is True
        assert evaluator.OPERATORS["in"]("orange", ["apple", "banana"]) is False
        assert evaluator.OPERATORS["in"]("apple", "apple") is True  # Single value

        # Not in operator
        assert evaluator.OPERATORS["not_in"]("orange", ["apple", "banana"]) is True
        assert evaluator.OPERATORS["not_in"]("apple", ["apple", "banana"]) is False

    def test_existence_operator_parity(self):
        """Test that existence operators work identically."""
        evaluator = ConditionEvaluator()

        # Exists
        assert evaluator.OPERATORS["exists"]("value", None) is True
        assert evaluator.OPERATORS["exists"]("", None) is False
        assert evaluator.OPERATORS["exists"](None, None) is False

        # Not exists
        assert evaluator.OPERATORS["not_exists"](None, None) is True
        assert evaluator.OPERATORS["not_exists"]("", None) is True
        assert evaluator.OPERATORS["not_exists"]("value", None) is False

        # Is empty
        assert evaluator.OPERATORS["is_empty"]("", None) is True
        assert evaluator.OPERATORS["is_empty"](0, None) is True
        assert evaluator.OPERATORS["is_empty"](False, None) is True
        assert evaluator.OPERATORS["is_empty"]("value", None) is False

        # Is not empty
        assert evaluator.OPERATORS["is_not_empty"]("value", None) is True
        assert evaluator.OPERATORS["is_not_empty"](1, None) is True
        assert evaluator.OPERATORS["is_not_empty"](True, None) is True
        assert evaluator.OPERATORS["is_not_empty"]("", None) is False


class TestPerformanceAndComplexity:
    """Test performance with large condition sets and complex scenarios."""

    def test_large_condition_set_performance(self):
        """Test performance with large number of conditions."""
        evaluator = ConditionEvaluator()

        # Create large form data
        large_form_data = {f"field_{i}": f"value_{i}" for i in range(1000)}

        # Create complex nested condition
        conditions = []
        for i in range(100):
            conditions.append({"operator": "equals", "field": f"field_{i}", "value": f"value_{i}"})

        complex_condition = {"operator": "and", "conditions": conditions}

        # This should complete without timeout
        import time

        start_time = time.time()
        result = evaluator.evaluate_condition(complex_condition, large_form_data)
        end_time = time.time()

        assert result is True
        assert end_time - start_time < 1.0  # Should complete in under 1 second

    def test_deeply_nested_conditions(self):
        """Test deeply nested condition structures."""
        evaluator = ConditionEvaluator()
        form_data = {"a": 1, "b": 2, "c": 3}

        # Create deeply nested condition (10 levels)
        condition = {"operator": "equals", "field": "a", "value": 1}
        for i in range(10):
            condition = {
                "operator": "and",
                "conditions": [condition, {"operator": "equals", "field": "b", "value": 2}],
            }

        result = evaluator.evaluate_condition(condition, form_data)
        assert result is True

    def test_complex_real_world_scenario(self):
        """Test complex real-world conditional logic scenario."""
        evaluator = ConditionEvaluator()

        # Simulate complex product configuration conditions
        form_data = {
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "sliding",
            "width": 48.5,
            "height": 60.0,
            "builtin_flyscreen_track": True,
            "system_series": "Kom800",
            "renovation": True,
        }

        # Complex condition: Show flyscreen fields if Frame + sliding + builtin track
        condition = {
            "operator": "and",
            "conditions": [
                {"operator": "equals", "field": "type", "value": "Frame"},
                {
                    "operator": "or",
                    "conditions": [
                        {"operator": "contains", "field": "opening_system", "value": "sliding"},
                        {"operator": "equals", "field": "system_series", "value": "Kom800"},
                    ],
                },
                {"operator": "equals", "field": "builtin_flyscreen_track", "value": True},
                {
                    "operator": "and",
                    "conditions": [
                        {"operator": "greater_than", "field": "width", "value": 40},
                        {"operator": "greater_than", "field": "height", "value": 50},
                    ],
                },
            ],
        }

        result = evaluator.evaluate_condition(condition, form_data)
        assert result is True

        # Change one condition to make it false
        form_data["builtin_flyscreen_track"] = False
        result = evaluator.evaluate_condition(condition, form_data)
        assert result is False
