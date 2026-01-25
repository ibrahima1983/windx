"""Property-based tests for Entry Page real-time preview synchronization.

This module tests that the preview table updates in real-time as form data changes
using property-based testing to ensure correctness across various data combinations.

**Feature: entry-page-system, Property 3: Real-time preview synchronization**
**Validates: Requirements 2.1, 2.4, 6.4**
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services.entry import EntryService


class TestRealTimePreviewSynchronization:
    """Property-based tests for real-time preview synchronization."""

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Set up test fixtures."""
        self.entry_service = EntryService(db_session)

        # Header to field mapping for validation
        self.header_field_mapping = {
            "Name": "name",
            "Type": "type",
            "Company": "company",
            "Material": "material",
            "opening system": "opening_system",
            "system series": "system_series",
            "Code": "code",
            "Length of Beam\nm": "length_of_beam",
            "Renovation\nonly for frame": "renovation",
            "width": "width",
            "builtin Flyscreen track only for sliding frame": "builtin_flyscreen_track",
            "Total width\nonly for frame with builtin flyscreen": "total_width",
            "flyscreen track height\nonly for frame with builtin flyscreen": "flyscreen_track_height",
            "front Height mm": "front_height",
            "Rear heightt": "rear_height",
            "Glazing height": "glazing_height",
            "Renovation height mm\nonly for frame": "renovation_height",
            "Glazing undercut heigth\nonly for glazing bead": "glazing_undercut_height",
            "Pic": "pic",
            "Sash overlap only for sashs": "sash_overlap",
            "flying mullion horizontal clearance": "flying_mullion_horizontal_clearance",
            "flying mullion vertical clearance": "flying_mullion_vertical_clearance",
            "Steel material thickness\nonly for reinforcement": "steel_material_thickness",
            "Weight/m kg": "weight_per_meter",
            "Reinforcement steel": "reinforcement_steel",
            "Colours": "colours",
            "Price/m": "price_per_meter",
            "Price per/beam": "price_per_beam",
            "UPVC Profile Discount%": "upvc_profile_discount",
        }

    @given(
        initial_data=st.fixed_dictionaries(
            {
                "manufacturing_type_id": st.integers(min_value=1, max_value=100),
                "name": st.text(min_size=1, max_size=100),
                "type": st.sampled_from(["Frame", "sash", "Mullion"]),
                "material": st.sampled_from(["UPVC", "Aluminum", "Wood"]),
                "opening_system": st.sampled_from(["Casement", "Sliding", "Fixed"]),
                "system_series": st.sampled_from(["Kom700", "Kom701", "Kom800"]),
            }
        ),
        field_updates=st.dictionaries(
            keys=st.sampled_from(
                [
                    "company",
                    "code",
                    "width",
                    "front_height",
                    "rear_height",
                    "glazing_height",
                    "pic",
                    "weight_per_meter",
                    "price_per_meter",
                ]
            ),
            values=st.one_of(
                st.text(min_size=1, max_size=50),
                st.floats(min_value=0.1, max_value=5000.0),
                st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00")),
            ),
            min_size=1,
            max_size=5,
        ),
    )
    def test_preview_updates_reflect_form_changes(self, initial_data, field_updates):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        For any initial form data and subsequent field updates, the preview table
        should immediately reflect all changes without requiring manual refresh.
        """
        # Generate initial preview
        initial_preview = self.entry_service.generate_preview_table(initial_data)

        # Apply field updates
        updated_data = {**initial_data, **field_updates}
        updated_preview = self.entry_service.generate_preview_table(updated_data)

        # Test that preview structure remains consistent
        assert len(initial_preview.headers) == len(updated_preview.headers), (
            "Preview structure should remain consistent"
        )
        assert initial_preview.headers == updated_preview.headers, "Headers should remain the same"

        # Test that updated fields are reflected in preview
        initial_row = initial_preview.rows[0]
        updated_row = updated_preview.rows[0]

        for field_name, new_value in field_updates.items():
            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field_name:
                    header = h
                    break

            if header:
                # Value should have changed in preview
                if field_name not in initial_data or initial_data[field_name] != new_value:
                    assert initial_row[header] != updated_row[header], (
                        f"Preview should reflect change in field {field_name}"
                    )

                # New value should be properly formatted in preview
                formatted_value = self._format_value_for_preview(new_value, field_name)
                assert updated_row[header] == formatted_value, (
                    f"Preview should show formatted value for {field_name}"
                )

    @given(
        form_data=st.fixed_dictionaries(
            {
                "manufacturing_type_id": st.integers(min_value=1, max_value=100),
                "name": st.text(min_size=1, max_size=100),
                "type": st.sampled_from(["Frame", "sash"]),
                "material": st.sampled_from(["UPVC", "Aluminum"]),
                "opening_system": st.sampled_from(["Casement", "Sliding"]),
                "system_series": st.sampled_from(["Kom700", "Kom800"]),
                "renovation": st.booleans(),
                "builtin_flyscreen_track": st.booleans(),
            }
        )
    )
    def test_conditional_field_changes_update_preview(self, form_data):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        For any form data with conditional fields, when trigger fields change,
        the preview should immediately show or hide dependent field values.
        """
        # Generate preview with current data
        preview = self.entry_service.generate_preview_table(form_data)
        row = preview.rows[0]

        # Test renovation field visibility in preview
        renovation_header = "Renovation\nonly for frame"
        if form_data.get("renovation") is not None:
            expected_value = "yes" if form_data["renovation"] else "no"
            assert row[renovation_header] == expected_value, (
                "Renovation field should show boolean value when set"
            )
        else:
            assert row[renovation_header] == "N/A", "Renovation field should show N/A when not set"

        # Test flyscreen field visibility in preview
        flyscreen_header = "builtin Flyscreen track only for sliding frame"
        if form_data.get("builtin_flyscreen_track") is not None:
            expected_value = "yes" if form_data["builtin_flyscreen_track"] else "no"
            assert row[flyscreen_header] == expected_value, (
                "Flyscreen field should show boolean value when set"
            )
        else:
            assert row[flyscreen_header] == "N/A", "Flyscreen field should show N/A when not set"

    @given(
        field_sequence=st.lists(
            st.tuples(
                st.sampled_from(["name", "company", "code", "pic"]),
                st.one_of(st.text(min_size=1, max_size=50), st.none()),
            ),
            min_size=1,
            max_size=10,
        )
    )
    def test_sequential_field_updates_maintain_sync(self, field_sequence):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        For any sequence of field updates, each update should be immediately
        reflected in the preview, maintaining synchronization throughout.
        """
        # Start with minimal data
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Initial Name",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
        }

        # Apply each update and verify preview synchronization
        for field_name, field_value in field_sequence:
            # Update form data
            if field_value is not None:
                form_data[field_name] = field_value
            else:
                form_data.pop(field_name, None)

            # Generate preview
            preview = self.entry_service.generate_preview_table(form_data)
            row = preview.rows[0]

            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field_name:
                    header = h
                    break

            if header:
                # Verify field is correctly reflected in preview
                if field_value is not None and field_value != "":
                    formatted_value = self._format_value_for_preview(field_value, field_name)
                    assert row[header] == formatted_value, (
                        f"Field {field_name} should be synchronized in preview"
                    )
                else:
                    assert row[header] == "N/A", (
                        f"Empty/null field {field_name} should show as N/A in preview"
                    )

    @given(
        numeric_updates=st.dictionaries(
            keys=st.sampled_from(["width", "front_height", "rear_height", "weight_per_meter"]),
            values=st.floats(
                min_value=0.1, max_value=5000.0, allow_nan=False, allow_infinity=False
            ),
            min_size=1,
            max_size=4,
        )
    )
    def test_numeric_field_updates_preserve_precision(self, numeric_updates):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        For any numeric field updates, the preview should maintain proper
        precision and formatting without loss of data.
        """
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            **numeric_updates,
        }

        preview = self.entry_service.generate_preview_table(form_data)
        row = preview.rows[0]

        for field_name, field_value in numeric_updates.items():
            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field_name:
                    header = h
                    break

            if header:
                # Verify numeric value is properly formatted
                expected_value = str(field_value)
                assert row[header] == expected_value, (
                    f"Numeric field {field_name} should preserve precision in preview"
                )

    @given(
        array_updates=st.dictionaries(
            keys=st.sampled_from(["reinforcement_steel", "colours"]),
            values=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
            min_size=1,
            max_size=2,
        )
    )
    def test_array_field_updates_maintain_structure(self, array_updates):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        For any array field updates, the preview should maintain proper
        array structure and formatting (comma-separated values).
        """
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            **array_updates,
        }

        preview = self.entry_service.generate_preview_table(form_data)
        row = preview.rows[0]

        for field_name, field_value in array_updates.items():
            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field_name:
                    header = h
                    break

            if header:
                if len(field_value) > 0:
                    expected_value = ", ".join(field_value)
                    assert row[header] == expected_value, (
                        f"Array field {field_name} should be comma-separated in preview"
                    )
                else:
                    assert row[header] == "N/A", (
                        f"Empty array field {field_name} should show as N/A in preview"
                    )

    def test_preview_synchronization_performance(self):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        Test that preview generation is fast enough for real-time updates
        (should complete within reasonable time limits).
        """
        import time

        form_data = {
            "manufacturing_type_id": 1,
            "name": "Performance Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            "company": "Test Company",
            "code": "TEST001",
            "width": 1200.0,
            "front_height": 1500.0,
            "rear_height": 1500.0,
            "glazing_height": 1400.0,
            "renovation": True,
            "builtin_flyscreen_track": True,
            "total_width": 1250.0,
            "flyscreen_track_height": 50.0,
            "reinforcement_steel": ["Steel Type A", "Steel Type B"],
            "colours": ["White", "Brown"],
            "price_per_meter": Decimal("125.50"),
            "upvc_profile_discount": 20.0,
        }

        # Measure preview generation time
        start_time = time.time()
        preview = self.entry_service.generate_preview_table(form_data)
        end_time = time.time()

        generation_time = end_time - start_time

        # Should complete within 100ms for real-time feel
        assert generation_time < 0.1, (
            f"Preview generation should be fast (<100ms), took {generation_time:.3f}s"
        )

        # Verify preview was generated correctly
        assert len(preview.headers) == 29, "Preview should have all headers"
        assert len(preview.rows) == 1, "Preview should have one row"

        # Verify some key fields are present
        row = preview.rows[0]
        assert row["Name"] == "Performance Test Profile"
        assert row["Type"] == "Frame"
        assert row["Material"] == "UPVC"

    def test_empty_to_filled_form_synchronization(self):
        """**Feature: entry-page-system, Property 3: Real-time preview synchronization**

        Test synchronization when transitioning from empty form to filled form.
        """
        # Start with minimal data (empty form)
        empty_data = {
            "manufacturing_type_id": 1,
            "name": "",
            "type": "",
            "material": "",
            "opening_system": "",
            "system_series": "",
        }

        empty_preview = self.entry_service.generate_preview_table(empty_data)
        empty_row = empty_preview.rows[0]

        # Most fields should show N/A
        na_count = sum(1 for value in empty_row.values() if value == "N/A")
        assert na_count > 20, "Empty form should show mostly N/A values in preview"

        # Fill form with data
        filled_data = {
            "manufacturing_type_id": 1,
            "name": "Complete Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            "company": "Test Company",
            "code": "COMP001",
            "width": 1200.0,
            "renovation": True,
            "builtin_flyscreen_track": False,
        }

        filled_preview = self.entry_service.generate_preview_table(filled_data)
        filled_row = filled_preview.rows[0]

        # Fewer fields should show N/A
        filled_na_count = sum(1 for value in filled_row.values() if value == "N/A")
        assert filled_na_count < na_count, (
            "Filled form should have fewer N/A values than empty form"
        )

        # Specific fields should be populated
        assert filled_row["Name"] == "Complete Profile"
        assert filled_row["Type"] == "Frame"
        assert filled_row["Material"] == "UPVC"
        assert filled_row["Renovation\nonly for frame"] == "yes"
        assert filled_row["builtin Flyscreen track only for sliding frame"] == "no"

    def _format_value_for_preview(self, value: Any, field_name: str) -> str:
        """Helper method to format values as they would appear in preview."""
        if value is None or value == "":
            return "N/A"

        if isinstance(value, bool):
            return "yes" if value else "no"
        elif isinstance(value, list):
            return ", ".join(value) if value else "N/A"
        elif isinstance(value, (int, float)):
            return str(value)
        elif isinstance(value, Decimal):
            return str(value)
        else:
            return str(value)
