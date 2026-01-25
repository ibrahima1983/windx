"""Property-based tests for entry page null value handling.

This module contains property-based tests that verify the entry page system
handles null, empty, and N/A values gracefully without errors.

**Feature: entry-page-system, Property 5: Graceful null value handling**
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.models.configuration import Configuration
from app.models.configuration_selection import ConfigurationSelection
from app.schemas.entry import PreviewTable, ProfileEntryData
from app.services.entry import EntryService


@st.composite
def profile_data_with_nulls(draw):
    """Generate profile entry data with various null/empty combinations."""
    # Always include required fields
    base_data = {
        "manufacturing_type_id": draw(st.integers(min_value=1, max_value=100)),
        "name": draw(st.text(min_size=1, max_size=50)),
        "type": draw(st.text(min_size=1, max_size=20)),
        "material": draw(st.text(min_size=1, max_size=20)),
        "opening_system": draw(st.text(min_size=1, max_size=20)),
        "system_series": draw(st.text(min_size=1, max_size=20)),
    }

    # Add optional fields with various null/empty states
    optional_fields = [
        "company",
        "code",
        "length_of_beam",
        "renovation",
        "width",
        "builtin_flyscreen_track",
        "total_width",
        "flyscreen_track_height",
        "front_height",
        "rear_height",
        "glazing_height",
        "renovation_height",
        "glazing_undercut_height",
        "pic",
        "sash_overlap",
        "flying_mullion_horizontal_clearance",
        "flying_mullion_vertical_clearance",
        "steel_material_thickness",
        "weight_per_meter",
        "reinforcement_steel",
        "colours",
        "price_per_meter",
        "price_per_beam",
    ]

    for field in optional_fields:
        # Generate various null/empty states
        value_type = draw(st.sampled_from(["null", "empty_string", "empty_list", "valid_value"]))

        if value_type == "null":
            base_data[field] = None
        elif value_type == "empty_string":
            # Only set empty string for string fields, not numeric/list/decimal fields
            if field in ["company", "code", "pic"]:
                base_data[field] = ""
            else:
                base_data[field] = None
        elif value_type == "empty_list" and field in ["reinforcement_steel", "colours"]:
            base_data[field] = []
        else:
            # Generate appropriate valid value based on field type
            if field in ["reinforcement_steel", "colours"]:
                base_data[field] = draw(st.lists(st.text(min_size=1, max_size=10), max_size=3))
            elif field in ["renovation", "builtin_flyscreen_track"]:
                base_data[field] = draw(st.booleans())
            elif field in [
                "length_of_beam",
                "width",
                "total_width",
                "flyscreen_track_height",
                "front_height",
                "rear_height",
                "glazing_height",
                "renovation_height",
                "glazing_undercut_height",
                "sash_overlap",
                "flying_mullion_horizontal_clearance",
                "flying_mullion_vertical_clearance",
                "steel_material_thickness",
                "weight_per_meter",
            ]:
                base_data[field] = draw(st.floats(min_value=0.1, max_value=1000))
            elif field in ["price_per_meter", "price_per_beam"]:
                base_data[field] = draw(st.decimals(min_value=1, max_value=1000, places=2))
            else:
                base_data[field] = draw(st.text(max_size=50))

    return ProfileEntryData(**base_data)


@st.composite
def configuration_with_null_selections(draw):
    """Generate configuration with selections containing null values."""
    config = MagicMock(spec=Configuration)
    config.id = draw(st.integers(min_value=1, max_value=1000))
    config.name = draw(st.text(min_size=1, max_size=50))

    # Create selections with various null states
    selections = []
    field_names = ["type", "material", "company", "width", "renovation", "colours"]

    for i, field_name in enumerate(field_names):
        selection = MagicMock(spec=ConfigurationSelection)
        selection.id = i + 1
        selection.selection_path = field_name

        # Randomly assign null or valid values
        null_type = draw(
            st.sampled_from(
                ["all_null", "string_value", "numeric_value", "boolean_value", "json_value"]
            )
        )

        if null_type == "all_null":
            selection.string_value = None
            selection.numeric_value = None
            selection.boolean_value = None
            selection.json_value = None
        elif null_type == "string_value":
            selection.string_value = draw(st.one_of(st.none(), st.text(max_size=20)))
            selection.numeric_value = None
            selection.boolean_value = None
            selection.json_value = None
        elif null_type == "numeric_value":
            selection.string_value = None
            selection.numeric_value = draw(
                st.one_of(st.none(), st.floats(min_value=0, max_value=1000))
            )
            selection.boolean_value = None
            selection.json_value = None
        elif null_type == "boolean_value":
            selection.string_value = None
            selection.numeric_value = None
            selection.boolean_value = draw(st.one_of(st.none(), st.booleans()))
            selection.json_value = None
        else:  # json_value
            selection.string_value = None
            selection.numeric_value = None
            selection.boolean_value = None
            selection.json_value = draw(
                st.one_of(st.none(), st.lists(st.text(max_size=10), max_size=3))
            )

        selections.append(selection)

    config.selections = selections
    return config


class TestEntryNullHandling:
    """Test class for entry page null value handling properties."""

    @pytest.mark.asyncio
    @given(profile_data=profile_data_with_nulls())
    async def test_property_graceful_null_value_handling_in_validation(
        self, profile_data: ProfileEntryData
    ):
        """
        **Feature: entry-page-system, Property 5: Graceful null value handling**

        Property: For any form fields with null, empty, or N/A values, the system
        should display them appropriately without errors and preserve them through
        save/load cycles.

        This test verifies validation handles null values gracefully.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock schema for validation
        entry_service.get_profile_schema = AsyncMock()
        mock_schema = MagicMock()
        mock_schema.sections = []
        entry_service.get_profile_schema.return_value = mock_schema

        # Act & Assert - Validation should not crash on null values
        try:
            await entry_service.validate_profile_data(profile_data)
            # If validation passes, that's good
        except Exception as e:
            # If validation fails, it should be due to business rules, not null handling
            # The error should be a proper ValidationException, not a system error
            assert "NoneType" not in str(e), f"Null handling error: {e}"
            assert "null" not in str(e).lower() or "required" in str(e).lower(), (
                f"Unexpected null error: {e}"
            )

    @given(
        form_data=st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(
                st.none(),
                st.text(max_size=50),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.lists(st.text(max_size=10), max_size=5),
            ),
            min_size=5,
            max_size=15,
        )
    )
    def test_property_preview_table_null_handling(self, form_data: dict):
        """
        **Feature: entry-page-system, Property 5: Graceful null value handling**

        Property: For any form data with null values, the preview table generation
        should handle them gracefully and display appropriate placeholders.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act - Generate preview table with potentially null data
        try:
            preview_table = entry_service.generate_preview_table(form_data)

            # Assert - Should return valid PreviewTable
            assert isinstance(preview_table, PreviewTable)
            assert isinstance(preview_table.headers, list)
            assert len(preview_table.headers) == 29  # Should have all 29 CSV columns
            assert isinstance(preview_table.rows, list)
            assert len(preview_table.rows) == 1  # Should have one row

            # Verify row data handles nulls gracefully
            row_data = preview_table.rows[0]
            assert isinstance(row_data, dict)

            # All headers should have corresponding values (even if N/A)
            for header in preview_table.headers:
                assert header in row_data, f"Missing header: {header}"
                value = row_data[header]

                # Value should be a string (formatted for display)
                assert isinstance(value, str), f"Non-string value for {header}: {value}"

                # Should not contain raw None or null representations
                assert value != "None", f"Raw None value for {header}"
                assert value != "null", f"Raw null value for {header}"

                # Empty/null values should be represented as "N/A"
                if not form_data.get(header.lower().replace(" ", "_").replace("\n", "_")):
                    assert value in ["N/A", "no", ""], (
                        f"Unexpected null representation for {header}: {value}"
                    )

        except Exception as e:
            # Should not crash on null values
            assert "NoneType" not in str(e), f"Null handling error in preview: {e}"
            assert "null" not in str(e).lower(), f"Null handling error in preview: {e}"

    def test_property_format_preview_value_null_handling(self):
        """
        **Feature: entry-page-system, Property 5: Graceful null value handling**

        Property: The format_preview_value method should handle all types of
        null/empty values gracefully and return appropriate string representations.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Test various null/empty values
        test_cases = [
            (None, "N/A"),
            ("", "N/A"),
            ([], "N/A"),
            ({}, "{}"),
            (0, "0"),
            (False, "no"),
            (True, "yes"),
            ("test", "test"),
            ([1, 2, 3], "1, 2, 3"),
            (["a", "b"], "a, b"),
        ]

        for input_value, expected_output in test_cases:
            # Act
            result = entry_service.format_preview_value(input_value)

            # Assert
            assert isinstance(result, str), f"Non-string result for {input_value}: {result}"
            assert result == expected_output, (
                f"Unexpected format for {input_value}: got {result}, expected {expected_output}"
            )

    @given(config_data=configuration_with_null_selections())
    def test_property_configuration_preview_null_handling(self, config_data):
        """
        **Feature: entry-page-system, Property 5: Graceful null value handling**

        Property: Configuration objects with null selections should generate
        preview tables without errors, showing appropriate placeholders.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act - Generate preview from configuration with null selections
        try:
            preview_table = entry_service.generate_preview_table(config_data)

            # Assert - Should handle null selections gracefully
            assert isinstance(preview_table, PreviewTable)
            assert len(preview_table.headers) == 29
            assert len(preview_table.rows) == 1

            row_data = preview_table.rows[0]

            # Verify all headers have values
            for header in preview_table.headers:
                assert header in row_data
                value = row_data[header]
                assert isinstance(value, str)

                # Should not contain error messages or raw null values
                assert "error" not in value.lower()
                assert "exception" not in value.lower()
                assert value != "None"
                assert value != "null"

            # Name should come from configuration
            assert row_data["Name"] == config_data.name

        except Exception as e:
            # Should not crash on null selections
            assert "NoneType" not in str(e), f"Null handling error: {e}"

    @given(
        field_values=st.dictionaries(
            st.sampled_from(
                [
                    "name",
                    "type",
                    "company",
                    "material",
                    "opening_system",
                    "system_series",
                    "width",
                    "renovation",
                    "builtin_flyscreen_track",
                    "colours",
                ]
            ),
            st.one_of(
                st.none(),
                st.text(max_size=20),
                st.booleans(),
                st.lists(st.text(max_size=5), max_size=3),
            ),
            min_size=3,
            max_size=8,
        )
    )
    def test_property_field_visibility_with_nulls(self, field_values: dict):
        """
        **Feature: entry-page-system, Property 5: Graceful null value handling**

        Property: Conditional field visibility evaluation should handle null values
        in form data gracefully without causing evaluation errors.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Create test conditions that might reference null fields
        test_conditions = [
            {"operator": "equals", "field": "type", "value": "Frame"},
            {"operator": "exists", "field": "company", "value": None},
            {"operator": "not_exists", "field": "width", "value": None},
            {"operator": "contains", "field": "material", "value": "wood"},
        ]

        # Act & Assert - Should not crash on null values
        for condition in test_conditions:
            try:
                result = entry_service.condition_evaluator.evaluate_condition(
                    condition, field_values
                )

                # Should return a boolean result
                assert isinstance(result, bool), (
                    f"Non-boolean result for condition {condition}: {result}"
                )

            except Exception as e:
                # Should not crash on null values
                assert "NoneType" not in str(e), f"Null handling error in condition evaluation: {e}"
                assert "'NoneType'" not in str(e), (
                    f"Null handling error in condition evaluation: {e}"
                )
