"""Property-based tests for entry page validation enforcement.

This module contains property-based tests that verify the entry page system
enforces schema-based validation correctly.

Property 6: Schema-based validation enforcement
- For any form submission, validation should be applied according to the
  attribute schema rules, preventing invalid data submission and displaying
  clear error messages
"""

from unittest.mock import AsyncMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.exceptions import ValidationException
from app.schemas.entry import FieldDefinition, FormSection, ProfileEntryData, ProfileSchema
from app.services.entry import EntryService


@st.composite
def validation_rules(draw):
    """Generate various validation rule combinations."""
    rule_type = draw(
        st.sampled_from(
            ["range", "pattern", "email", "url", "positive", "non_negative", "choices", "length"]
        )
    )

    if rule_type == "range":
        min_val = draw(st.integers(min_value=1, max_value=50))
        max_val = draw(st.integers(min_value=min_val + 1, max_value=100))
        return {
            "rule_type": "range",
            "min": min_val,
            "max": max_val,
            "message": f"Value must be between {min_val} and {max_val}",
        }
    elif rule_type == "pattern":
        patterns = [
            r"^[A-Z]{2}\d{5}$",  # Two letters followed by 5 digits
            r"^\d{3}-\d{3}-\d{4}$",  # Phone number format
            r"^[A-Za-z\s]+$",  # Letters and spaces only
            r"^\d+(\.\d{1,2})?$",  # Decimal with up to 2 places
        ]
        pattern = draw(st.sampled_from(patterns))
        return {"pattern": pattern, "message": f"Value must match pattern {pattern}"}
    elif rule_type == "email":
        return {"rule_type": "email", "message": "Must be a valid email address"}
    elif rule_type == "url":
        return {"rule_type": "url", "message": "Must be a valid URL"}
    elif rule_type == "positive":
        return {"rule_type": "positive", "message": "Value must be positive"}
    elif rule_type == "non_negative":
        return {"rule_type": "non_negative", "message": "Value must be non-negative"}
    elif rule_type == "choices":
        choices = draw(
            st.lists(st.text(min_size=1, max_size=20), min_size=2, max_size=5, unique=True)
        )
        return {"choices": choices, "message": f"Must be one of: {', '.join(choices)}"}
    elif rule_type == "length":
        min_len = draw(st.integers(min_value=1, max_value=10))
        max_len = draw(st.integers(min_value=min_len + 1, max_value=50))
        return {
            "min_length": min_len,
            "max_length": max_len,
            "message": f"Length must be between {min_len} and {max_len} characters",
        }


@st.composite
def field_with_validation(draw):
    """Generate field definition with validation rules."""
    return FieldDefinition(
        name=draw(st.text(min_size=1, max_size=20)),
        label=draw(st.text(min_size=1, max_size=50)),
        data_type=draw(st.sampled_from(["string", "number", "boolean"])),
        required=draw(st.booleans()),
        validation_rules=draw(st.one_of(st.none(), validation_rules())),
    )


@st.composite
def profile_schema_with_validation(draw, manufacturing_type_id):
    """Generate profile schema with validation rules."""
    fields = draw(st.lists(field_with_validation(), min_size=3, max_size=10))

    section = FormSection(title="Test Section", fields=fields, sort_order=0)

    return ProfileSchema(
        manufacturing_type_id=manufacturing_type_id, sections=[section], conditional_logic={}
    )


@st.composite
def invalid_profile_data(draw, schema: ProfileSchema):
    """Generate profile data that violates validation rules."""
    base_data = {
        "manufacturing_type_id": schema.manufacturing_type_id,
        "name": draw(st.text(min_size=1, max_size=100)),
        "type": "Frame",
        "material": "Aluminum",
        "opening_system": "Casement",
        "system_series": "Kom800",
    }

    # Add invalid values for fields with validation rules
    for section in schema.sections:
        for field in section.fields:
            if field.validation_rules:
                rules = field.validation_rules

                # Generate invalid values based on rule type
                if "min" in rules and "max" in rules:
                    # Generate value outside range
                    invalid_value = draw(
                        st.one_of(
                            st.integers(max_value=rules["min"] - 1),
                            st.integers(min_value=rules["max"] + 1),
                        )
                    )
                    base_data[field.name] = invalid_value

                elif "pattern" in rules:
                    # Generate string that doesn't match pattern
                    base_data[field.name] = "INVALID_PATTERN_123!@#"

                elif rules.get("rule_type") == "email":
                    # Generate invalid email
                    base_data[field.name] = draw(
                        st.sampled_from(["invalid-email", "@invalid.com", "test@", "test.com"])
                    )

                elif rules.get("rule_type") == "url":
                    # Generate invalid URL
                    base_data[field.name] = draw(
                        st.sampled_from(["not-a-url", "ftp://invalid", "http://", "invalid.com"])
                    )

                elif rules.get("rule_type") == "positive":
                    # Generate non-positive value
                    base_data[field.name] = draw(st.integers(max_value=0))

                elif rules.get("rule_type") == "non_negative":
                    # Generate negative value
                    base_data[field.name] = draw(st.integers(max_value=-1))

                elif "choices" in rules:
                    # Generate value not in choices
                    base_data[field.name] = "NOT_IN_CHOICES"

                elif "min_length" in rules:
                    # Generate string too short
                    base_data[field.name] = draw(st.text(max_size=rules["min_length"] - 1))

                elif "max_length" in rules:
                    # Generate string too long
                    base_data[field.name] = draw(
                        st.text(min_size=rules["max_length"] + 1, max_size=rules["max_length"] + 10)
                    )

    return ProfileEntryData(**base_data)


class TestEntryValidation:
    """Test class for entry page validation enforcement properties."""

    @pytest.mark.asyncio
    @given(schema=profile_schema_with_validation(1), seed=st.integers())
    @settings(max_examples=100, deadline=None)
    async def test_property_schema_based_validation_enforcement(
        self, schema: ProfileSchema, seed: int
    ):
        """
        **Feature: entry-page-system, Property 6: Schema-based validation enforcement**

        Property: For any form submission, validation should be applied according to the
        attribute schema rules, preventing invalid data submission and displaying clear
        error messages.

        This property ensures that all validation rules defined in the attribute schema
        are properly enforced, preventing invalid data from being saved.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock get_profile_schema to return our test schema
        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Generate invalid data based on the schema
        st.seed(seed)
        invalid_data = invalid_profile_data(schema).example()

        # Act & Assert - Validation should fail
        with pytest.raises(ValidationException) as exc_info:
            await entry_service.validate_profile_data(invalid_data)

        # Verify validation exception contains field errors
        assert exc_info.value.field_errors is not None
        assert len(exc_info.value.field_errors) > 0

        # Verify error messages are meaningful
        for field_name, error_message in exc_info.value.field_errors.items():
            assert isinstance(error_message, str)
            assert len(error_message) > 0
            # Error message should mention the field or validation rule
            assert any(
                keyword in error_message.lower()
                for keyword in [
                    field_name.lower(),
                    "required",
                    "invalid",
                    "must",
                    "between",
                    "pattern",
                    "format",
                ]
            )

    @pytest.mark.asyncio
    @given(validation_rule=validation_rules(), seed=st.integers())
    @settings(max_examples=100, deadline=None)
    async def test_property_individual_validation_rules(self, validation_rule: dict, seed: int):
        """
        Property: For any validation rule, the validate_field_value method should
        correctly identify invalid values and return appropriate error messages.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())
        field_label = "Test Field"

        # Generate invalid values based on rule type
        st.seed(seed)

        if validation_rule.get("rule_type") == "range":
            # Test values outside range
            invalid_values = [validation_rule["min"] - 1, validation_rule["max"] + 1]
        elif validation_rule.get("pattern"):
            # Test values that don't match pattern
            invalid_values = ["INVALID", "123!@#", ""]
        elif validation_rule.get("rule_type") == "email":
            invalid_values = ["invalid", "@test.com", "test@", "test.com"]
        elif validation_rule.get("rule_type") == "url":
            invalid_values = ["invalid", "ftp://test", "http://"]
        elif validation_rule.get("rule_type") == "positive":
            invalid_values = [0, -1, -10]
        elif validation_rule.get("rule_type") == "non_negative":
            invalid_values = [-1, -10, -0.1]
        elif validation_rule.get("choices"):
            invalid_values = ["NOT_IN_CHOICES", "", "INVALID"]
        elif validation_rule.get("min_length"):
            invalid_values = ["", "a" * (validation_rule["min_length"] - 1)]
        elif validation_rule.get("max_length"):
            invalid_values = ["a" * (validation_rule["max_length"] + 1)]
        else:
            invalid_values = []

        # Act & Assert
        for invalid_value in invalid_values:
            error_message = entry_service.validate_field_value(
                invalid_value, validation_rule, field_label
            )

            # Should return an error message
            assert error_message is not None
            assert isinstance(error_message, str)
            assert len(error_message) > 0

            # Error message should be meaningful
            if "message" in validation_rule:
                # Custom message should be used
                assert validation_rule["message"] in error_message or field_label in error_message

    @pytest.mark.asyncio
    @given(
        required_fields=st.lists(
            st.text(min_size=1, max_size=20), min_size=1, max_size=5, unique=True
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_required_field_validation(self, required_fields: list[str]):
        """
        Property: For any fields marked as required in the schema, validation should
        fail if those fields are missing, empty, or None.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create schema with required fields
        fields = [
            FieldDefinition(
                name=field_name, label=field_name.title(), data_type="string", required=True
            )
            for field_name in required_fields
        ]

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Test", fields=fields, sort_order=0)],
            conditional_logic={},
        )

        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Create profile data missing required fields
        profile_data = ProfileEntryData(
            manufacturing_type_id=1,
            name="Test",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Kom800",
        )

        # Act & Assert - Should fail validation
        with pytest.raises(ValidationException) as exc_info:
            await entry_service.validate_profile_data(profile_data)

        # Verify all required fields are mentioned in errors
        field_errors = exc_info.value.field_errors
        for required_field in required_fields:
            if required_field not in [
                "name",
                "type",
                "material",
                "opening_system",
                "system_series",
            ]:
                # These are provided in the base data, others should cause errors
                assert required_field in field_errors
                assert "required" in field_errors[required_field].lower()

    @pytest.mark.asyncio
    @given(
        cross_field_scenario=st.sampled_from(
            [
                "builtin_flyscreen_missing_dimensions",
                "flying_mullion_missing_clearance",
                "reinforcement_steel_missing_thickness",
                "height_difference_too_large",
                "price_inconsistency",
            ]
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_cross_field_validation(self, cross_field_scenario: str):
        """
        Property: For any cross-field validation rules, the system should detect
        violations and provide appropriate error messages.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create minimal schema
        schema = ProfileSchema(manufacturing_type_id=1, sections=[], conditional_logic={})
        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Create profile data that violates cross-field rules
        base_data = {
            "manufacturing_type_id": 1,
            "name": "Test Configuration",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
        }

        if cross_field_scenario == "builtin_flyscreen_missing_dimensions":
            base_data.update(
                {
                    "builtin_flyscreen_track": True,
                    # Missing total_width and flyscreen_track_height
                }
            )
        elif cross_field_scenario == "flying_mullion_missing_clearance":
            base_data.update(
                {
                    "type": "Flying mullion",
                    # Missing clearance fields
                }
            )
        elif cross_field_scenario == "reinforcement_steel_missing_thickness":
            base_data.update(
                {
                    "reinforcement_steel": ["Standard"],
                    # Missing steel_material_thickness
                }
            )
        elif cross_field_scenario == "height_difference_too_large":
            base_data.update(
                {
                    "front_height": 100.0,
                    "rear_height": 200.0,  # Difference > 50mm
                }
            )
        elif cross_field_scenario == "price_inconsistency":
            base_data.update(
                {
                    "price_per_meter": 10.0,
                    "length_of_beam": 2.0,
                    "price_per_beam": 50.0,  # Should be ~20.0 (10 * 2)
                }
            )

        profile_data = ProfileEntryData(**base_data)

        # Act & Assert - Should fail cross-field validation
        with pytest.raises(ValidationException) as exc_info:
            await entry_service.validate_profile_data(profile_data)

        # Verify appropriate cross-field errors are present
        field_errors = exc_info.value.field_errors
        assert len(field_errors) > 0

        # Check for expected error fields based on scenario
        if cross_field_scenario == "builtin_flyscreen_missing_dimensions":
            assert any(field in field_errors for field in ["total_width", "flyscreen_track_height"])
        elif cross_field_scenario == "flying_mullion_missing_clearance":
            assert any(
                field in field_errors
                for field in [
                    "flying_mullion_horizontal_clearance",
                    "flying_mullion_vertical_clearance",
                ]
            )
        elif cross_field_scenario == "reinforcement_steel_missing_thickness":
            assert "steel_material_thickness" in field_errors
        elif cross_field_scenario == "height_difference_too_large":
            assert "rear_height" in field_errors
        elif cross_field_scenario == "price_inconsistency":
            assert "price_per_beam" in field_errors

    @pytest.mark.asyncio
    @given(
        valid_values=st.lists(
            st.one_of(
                st.text(min_size=1, max_size=50),
                st.integers(min_value=1, max_value=1000),
                st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False),
                st.booleans(),
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_valid_data_passes_validation(self, valid_values: list):
        """
        Property: For any valid data that meets all schema requirements, validation
        should pass without errors.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create lenient schema (no strict validation rules)
        fields = [
            FieldDefinition(
                name=f"field_{i}",
                label=f"Field {i}",
                data_type="string",
                required=False,
                validation_rules=None,
            )
            for i in range(len(valid_values))
        ]

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Test", fields=fields, sort_order=0)],
            conditional_logic={},
        )

        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Create valid profile data
        profile_data = ProfileEntryData(
            manufacturing_type_id=1,
            name="Valid Configuration",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Kom800",
        )

        # Act - Should not raise exceptions
        try:
            result = await entry_service.validate_profile_data(profile_data)

            # Assert - Should return success
            assert result is not None
            assert result.get("valid") is True

        except ValidationException:
            pytest.fail("Validation failed for valid data")
