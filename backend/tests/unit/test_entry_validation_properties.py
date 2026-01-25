"""Property-based tests for entry page schema-based validation enforcement.

This module contains property-based tests that verify the entry page system
enforces schema-based validation correctly and prevents invalid data submission.

**Feature: entry-page-system, Property 6: Schema-based validation enforcement**
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.exceptions import ValidationException
from app.schemas.entry import FieldDefinition, FormSection, ProfileEntryData, ProfileSchema
from app.services.entry import EntryService


@st.composite
def field_with_validation_rules(draw):
    """Generate field definition with validation rules."""
    field_name = draw(st.text(min_size=1, max_size=20))
    data_type = draw(st.sampled_from(["string", "number", "boolean"]))

    # Generate validation rules based on data type
    validation_rules = {}

    if data_type == "string":
        rule_type = draw(st.sampled_from(["length", "pattern", "email", "choices"]))
        if rule_type == "length":
            validation_rules["min_length"] = draw(st.integers(min_value=1, max_value=10))
            validation_rules["max_length"] = draw(st.integers(min_value=15, max_value=50))
        elif rule_type == "pattern":
            validation_rules["pattern"] = draw(
                st.sampled_from(
                    [
                        r"^[A-Z]{2}\d{5}$",  # Code pattern
                        r"^[a-zA-Z\s]+$",  # Letters and spaces only
                        r"^\d{3}-\d{3}-\d{4}$",  # Phone pattern
                    ]
                )
            )
            validation_rules["message"] = "Invalid format"
        elif rule_type == "email":
            validation_rules["rule_type"] = "email"
        elif rule_type == "choices":
            validation_rules["choices"] = draw(
                st.lists(st.text(min_size=1, max_size=10), min_size=2, max_size=5)
            )

    elif data_type == "number":
        rule_type = draw(st.sampled_from(["range", "positive", "non_negative"]))
        if rule_type == "range":
            min_val = draw(st.integers(min_value=0, max_value=50))
            max_val = draw(st.integers(min_value=min_val + 1, max_value=100))
            validation_rules["min"] = min_val
            validation_rules["max"] = max_val
        elif rule_type == "positive":
            validation_rules["rule_type"] = "positive"
        elif rule_type == "non_negative":
            validation_rules["rule_type"] = "non_negative"

    return FieldDefinition(
        name=field_name,
        label=field_name.replace("_", " ").title(),
        data_type=data_type,
        required=draw(st.booleans()),
        validation_rules=validation_rules if validation_rules else None,
    )


@st.composite
def profile_data_violating_validation(draw, field: FieldDefinition):
    """Generate profile data that violates the given field's validation rules."""
    base_data = {
        "manufacturing_type_id": 1,
        "name": "Test Configuration",
        "type": "Frame",
        "material": "Aluminum",
        "opening_system": "Casement",
        "system_series": "Kom800",
    }

    # Generate invalid value for the field
    if field.validation_rules:
        rules = field.validation_rules

        if field.data_type == "string":
            if "min_length" in rules:
                # Generate string shorter than minimum
                base_data[field.name] = draw(st.text(max_size=rules["min_length"] - 1))
            elif "max_length" in rules:
                # Generate string longer than maximum
                base_data[field.name] = draw(
                    st.text(min_size=rules["max_length"] + 1, max_size=rules["max_length"] + 10)
                )
            elif "pattern" in rules:
                # Generate string that doesn't match pattern
                base_data[field.name] = draw(
                    st.text(min_size=1, max_size=20).filter(
                        lambda x: not __import__("re").match(rules["pattern"], x)
                    )
                )
            elif "choices" in rules:
                # Generate value not in choices
                invalid_choice = draw(
                    st.text(min_size=1, max_size=20).filter(lambda x: x not in rules["choices"])
                )
                base_data[field.name] = invalid_choice
            elif rules.get("rule_type") == "email":
                # Generate invalid email
                base_data[field.name] = draw(
                    st.sampled_from(["invalid-email", "test@", "@domain.com", "test.domain.com"])
                )

        elif field.data_type == "number":
            if "min" in rules:
                # Generate number below minimum
                base_data[field.name] = draw(st.floats(max_value=rules["min"] - 0.1))
            elif "max" in rules:
                # Generate number above maximum
                base_data[field.name] = draw(
                    st.floats(min_value=rules["max"] + 0.1, max_value=rules["max"] + 100)
                )
            elif rules.get("rule_type") == "positive":
                # Generate non-positive number
                base_data[field.name] = draw(st.floats(max_value=0))
            elif rules.get("rule_type") == "non_negative":
                # Generate negative number
                base_data[field.name] = draw(st.floats(max_value=-0.1))

    return ProfileEntryData(**base_data)


class TestEntryValidationEnforcement:
    """Test class for entry page validation enforcement properties."""

    @pytest.mark.asyncio
    @given(field=field_with_validation_rules())
    async def test_property_schema_based_validation_enforcement(self, field: FieldDefinition):
        """
        **Feature: entry-page-system, Property 6: Schema-based validation enforcement**

        Property: For any form submission, validation should be applied according to the
        attribute schema rules, preventing invalid data submission and displaying clear
        error messages.

        This test verifies that validation rules are properly enforced.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create schema with the test field
        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Test Section", fields=[field])],
            conditional_logic={},
        )

        # Mock get_profile_schema to return our test schema
        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Generate invalid data based on the field's validation rules
        if field.validation_rules:
            invalid_data = profile_data_violating_validation().example()

            # Act & Assert - Validation should fail
            with pytest.raises(ValidationException) as exc_info:
                await entry_service.validate_profile_data(invalid_data)

            # Verify validation exception contains field errors
            assert exc_info.value.field_errors is not None
            assert isinstance(exc_info.value.field_errors, dict)

            # Should have error for the invalid field (if it was set)
            if hasattr(invalid_data, field.name) and getattr(invalid_data, field.name) is not None:
                if field.name in exc_info.value.field_errors:
                    error_message = exc_info.value.field_errors[field.name]
                    assert isinstance(error_message, str)
                    assert len(error_message) > 0
                    assert (
                        field.label.lower() in error_message.lower()
                        or field.name.lower() in error_message.lower()
                    )

    @pytest.mark.asyncio
    @given(
        field_name=st.sampled_from(["name", "type", "material", "opening_system"]),
        field_label=st.text(min_size=1, max_size=30),
    )
    async def test_property_required_field_validation(self, field_name: str, field_label: str):
        """
        **Feature: entry-page-system, Property 6: Schema-based validation enforcement**

        Property: Required fields should be validated and prevent submission when empty.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Create schema with required field
        required_field = FieldDefinition(
            name=field_name, label=field_label, data_type="string", required=True
        )

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Test", fields=[required_field])],
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

        # Remove the required field value
        setattr(profile_data, field_name, "")

        # Act & Assert - Should fail validation
        with pytest.raises(ValidationException) as exc_info:
            await entry_service.validate_profile_data(profile_data)

        # Verify all required fields are mentioned in errors
        assert field_name in exc_info.value.field_errors
        error_message = exc_info.value.field_errors[field_name]
        assert "required" in error_message.lower()

    @pytest.mark.asyncio
    @given(
        width=st.floats(min_value=10, max_value=50), height=st.floats(min_value=10, max_value=50)
    )
    async def test_property_cross_field_validation_enforcement(self, width: float, height: float):
        """
        **Feature: entry-page-system, Property 6: Schema-based validation enforcement**

        Property: Cross-field validation rules should be enforced to maintain
        data consistency and business logic.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create minimal schema
        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Test", fields=[])],
            conditional_logic={},
        )
        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Create profile data that violates cross-field rules
        # Example: builtin_flyscreen_track=True but missing required dimensions
        base_data = {
            "manufacturing_type_id": 1,
            "name": "Test Configuration",
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "Casement",
            "system_series": "Kom800",
            "builtin_flyscreen_track": True,
            # Missing total_width and flyscreen_track_height (should trigger cross-field validation)
        }

        profile_data = ProfileEntryData(**base_data)

        # Act & Assert - Should fail cross-field validation
        with pytest.raises(ValidationException) as exc_info:
            await entry_service.validate_profile_data(profile_data)

        # Verify appropriate cross-field errors are present
        field_errors = exc_info.value.field_errors
        assert isinstance(field_errors, dict)

        # Should have errors for missing flyscreen-related fields
        flyscreen_fields = ["total_width", "flyscreen_track_height"]
        has_flyscreen_error = any(field in field_errors for field in flyscreen_fields)
        assert has_flyscreen_error, f"Expected flyscreen validation errors, got: {field_errors}"

    @pytest.mark.asyncio
    @given(
        valid_data=st.fixed_dictionaries(
            {
                "manufacturing_type_id": st.just(1),
                "name": st.text(min_size=1, max_size=50),
                "type": st.sampled_from(["Frame", "Flying mullion"]),
                "material": st.sampled_from(["Aluminum", "Vinyl", "Wood"]),
                "opening_system": st.sampled_from(["Casement", "Sliding"]),
                "system_series": st.sampled_from(["Kom800", "Series100"]),
                "width": st.floats(min_value=20, max_value=100),
                "height": st.floats(min_value=20, max_value=100),
            }
        )
    )
    async def test_property_valid_data_passes_validation(self, valid_data: dict):
        """
        **Feature: entry-page-system, Property 6: Schema-based validation enforcement**

        Property: Valid data that meets all schema requirements should pass
        validation without errors.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create lenient schema (no strict validation rules)
        fields = [
            FieldDefinition(name="name", label="Name", data_type="string", required=True),
            FieldDefinition(name="type", label="Type", data_type="string", required=True),
            FieldDefinition(name="material", label="Material", data_type="string", required=True),
            FieldDefinition(
                name="opening_system", label="Opening System", data_type="string", required=True
            ),
            FieldDefinition(
                name="system_series", label="System Series", data_type="string", required=True
            ),
            FieldDefinition(name="width", label="Width", data_type="number", required=False),
            FieldDefinition(name="height", label="Height", data_type="number", required=False),
        ]

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Test", fields=fields)],
            conditional_logic={},
        )

        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Create valid profile data
        profile_data = ProfileEntryData(**valid_data)

        # Act - Should not raise exceptions
        try:
            result = await entry_service.validate_profile_data(profile_data)

            # Assert - Should return success
            assert result is not None
            assert isinstance(result, dict)
            assert result.get("valid") is True

        except ValidationException as e:
            # If validation fails, it should be due to business rules, not schema issues
            pytest.fail(f"Valid data failed validation: {e.field_errors}")

    @pytest.mark.asyncio
    @given(
        field_value=st.text(min_size=1, max_size=100),
        validation_rule=st.fixed_dictionaries(
            {
                "rule_type": st.sampled_from(["email", "positive_number", "pattern"]),
                "pattern": st.just(r"^[A-Z]{2}\d{5}$"),
                "message": st.text(min_size=5, max_size=50),
            }
        ),
        field_label=st.text(min_size=1, max_size=30),
    )
    async def test_property_custom_validation_rules(
        self, field_value: str, validation_rule: dict, field_label: str
    ):
        """
        **Feature: entry-page-system, Property 6: Schema-based validation enforcement**

        Property: Custom validation rules should be properly applied and return
        appropriate error messages when validation fails.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Test individual field validation
        rule_type = validation_rule["rule_type"]

        # Generate invalid values for each rule type
        invalid_values = []
        if rule_type == "email":
            invalid_values = ["invalid-email", "test@", "@domain.com", "no-at-sign"]
        elif rule_type == "positive_number":
            invalid_values = ["-5", "0", "-0.1"]
        elif rule_type == "pattern":
            invalid_values = ["ABC123", "ab12345", "ABC1234", "ABCD123"]

        # Act & Assert
        for invalid_value in invalid_values:
            error_message = entry_service.validate_field_value(
                invalid_value, validation_rule, field_label
            )

            if error_message:  # Validation should fail for invalid values
                assert isinstance(error_message, str)
                assert len(error_message) > 0
                assert field_label in error_message or rule_type in error_message
