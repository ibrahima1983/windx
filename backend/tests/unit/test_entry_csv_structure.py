"""Property-based tests for Entry Page CSV structure preservation.

This module tests that the preview table maintains exact CSV structure
using property-based testing to ensure correctness across various configurations.

**Feature: entry-page-system, Property 4: CSV structure preservation**
**Validates: Requirements 2.2, 7.1, 7.2**
"""

from __future__ import annotations

from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.services.entry import EntryService


class TestCSVStructurePreservation:
    """Property-based tests for CSV structure preservation."""

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        """Set up test fixtures."""
        self.entry_service = EntryService(db_session)

        # Expected CSV headers from the profile table example (all 29 columns)
        self.expected_headers = [
            "Name",
            "Type",
            "Company",
            "Material",
            "opening system",
            "system series",
            "Code",
            "Length of Beam\nm",
            "Renovation\nonly for frame",
            "width",
            "builtin Flyscreen track only for sliding frame",
            "Total width\nonly for frame with builtin flyscreen",
            "flyscreen track height\nonly for frame with builtin flyscreen",
            "front Height mm",
            "Rear heightt",
            "Glazing height",
            "Renovation height mm\nonly for frame",
            "Glazing undercut heigth\nonly for glazing bead",
            "Pic",
            "Sash overlap only for sashs",
            "flying mullion horizontal clearance",
            "flying mullion vertical clearance",
            "Steel material thickness\nonly for reinforcement",
            "Weight/m kg",
            "Reinforcement steel",
            "Colours",
            "Price/m",
            "Price per/beam",
            "UPVC Profile Discount%",
        ]

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
        profile_data=st.fixed_dictionaries(
            {
                "manufacturing_type_id": st.integers(min_value=1, max_value=100),
                "name": st.text(min_size=1, max_size=100),
                "type": st.sampled_from(
                    [
                        "Frame",
                        "sash",
                        "Mullion",
                        "Flying mullion",
                        "glazing bead",
                        "Interlock",
                        "Track",
                        "auxilary",
                    ]
                ),
                "company": st.one_of(st.none(), st.text(min_size=1, max_size=50)),
                "material": st.sampled_from(["UPVC", "Aluminum", "Wood"]),
                "opening_system": st.sampled_from(["Casement", "Sliding", "Fixed", "Tilt & Turn"]),
                "system_series": st.sampled_from(["Kom700", "Kom701", "Kom800", "All"]),
                "code": st.one_of(st.none(), st.text(min_size=1, max_size=20)),
                "length_of_beam": st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0)),
                "renovation": st.one_of(st.none(), st.booleans()),
                "width": st.one_of(st.none(), st.floats(min_value=100, max_value=3000)),
                "builtin_flyscreen_track": st.one_of(st.none(), st.booleans()),
                "total_width": st.one_of(st.none(), st.floats(min_value=100, max_value=3000)),
                "flyscreen_track_height": st.one_of(
                    st.none(), st.floats(min_value=10, max_value=100)
                ),
                "front_height": st.one_of(st.none(), st.floats(min_value=100, max_value=3000)),
                "rear_height": st.one_of(st.none(), st.floats(min_value=100, max_value=3000)),
                "glazing_height": st.one_of(st.none(), st.floats(min_value=100, max_value=3000)),
                "renovation_height": st.one_of(st.none(), st.floats(min_value=100, max_value=3000)),
                "glazing_undercut_height": st.one_of(
                    st.none(), st.floats(min_value=1, max_value=50)
                ),
                "pic": st.one_of(st.none(), st.text(min_size=1, max_size=100)),
                "sash_overlap": st.one_of(st.none(), st.floats(min_value=1, max_value=50)),
                "flying_mullion_horizontal_clearance": st.one_of(
                    st.none(), st.floats(min_value=1, max_value=100)
                ),
                "flying_mullion_vertical_clearance": st.one_of(
                    st.none(), st.floats(min_value=1, max_value=100)
                ),
                "steel_material_thickness": st.one_of(
                    st.none(), st.floats(min_value=0.5, max_value=10.0)
                ),
                "weight_per_meter": st.one_of(st.none(), st.floats(min_value=0.1, max_value=50.0)),
                "reinforcement_steel": st.one_of(
                    st.none(), st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5)
                ),
                "colours": st.one_of(
                    st.none(), st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5)
                ),
                "price_per_meter": st.one_of(
                    st.none(), st.decimals(min_value=Decimal("0.01"), max_value=Decimal("1000.00"))
                ),
                "price_per_beam": st.one_of(
                    st.none(), st.decimals(min_value=Decimal("0.01"), max_value=Decimal("10000.00"))
                ),
                "upvc_profile_discount": st.one_of(
                    st.none(), st.floats(min_value=0.0, max_value=100.0)
                ),
            }
        )
    )
    def test_preview_table_has_exact_csv_structure(self, profile_data):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        For any profile configuration data, the preview table should contain
        exactly 29 columns with headers matching the CSV structure.
        """
        preview_table = self.entry_service.generate_preview_table(profile_data)

        # Test header count
        assert len(preview_table.headers) == 29, (
            f"Preview table should have exactly 29 headers, got {len(preview_table.headers)}"
        )

        # Test header content matches expected CSV headers
        assert preview_table.headers == self.expected_headers, (
            "Preview table headers should match exact CSV structure"
        )

        # Test that table has exactly one row (current configuration)
        assert len(preview_table.rows) == 1, "Preview table should have exactly one row"

        # Test that row has data for all headers
        row = preview_table.rows[0]
        for header in self.expected_headers:
            assert header in row, f"Row should contain data for header: {header}"

    @given(
        form_data=st.dictionaries(
            keys=st.sampled_from(
                [
                    "name",
                    "type",
                    "company",
                    "material",
                    "opening_system",
                    "system_series",
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
                    "upvc_profile_discount",
                ]
            ),
            values=st.one_of(
                st.none(),
                st.text(min_size=0, max_size=100),
                st.integers(min_value=0, max_value=10000),
                st.floats(min_value=0.0, max_value=10000.0),
                st.booleans(),
                st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
            ),
            min_size=0,
            max_size=29,
        )
    )
    def test_header_to_field_mapping_consistency(self, form_data):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        For any form data, the mapping between CSV headers and form fields
        should be consistent and complete.
        """
        preview_table = self.entry_service.generate_preview_table(form_data)

        # Test that all headers have corresponding field mappings
        for header in preview_table.headers:
            assert header in self.header_field_mapping, (
                f"Header '{header}' should have field mapping"
            )

            field_name = self.header_field_mapping[header]
            row_value = preview_table.rows[0][header]

            # Test that field mapping produces consistent results
            if field_name in form_data:
                form_value = form_data[field_name]
                if (
                    form_value is not None
                    and form_value != ""
                    and not (isinstance(form_value, list) and len(form_value) == 0)
                ):
                    # Value should be present in preview (not N/A)
                    assert row_value != "N/A", (
                        f"Non-empty field {field_name} should not show as N/A in preview"
                    )
                else:
                    # Empty/null values should show as N/A
                    assert row_value == "N/A", (
                        f"Empty field {field_name} should show as N/A in preview"
                    )
            else:
                # Missing fields should show as N/A
                assert row_value == "N/A", (
                    f"Missing field {field_name} should show as N/A in preview"
                )

    @given(
        null_fields=st.lists(
            st.sampled_from(
                [
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
                    "upvc_profile_discount",
                ]
            ),
            min_size=0,
            max_size=10,
            unique=True,
        )
    )
    def test_null_value_handling_in_csv_structure(self, null_fields):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        For any combination of null/empty fields, the CSV structure should
        handle them gracefully with N/A values without breaking the table structure.
        """
        # Create form data with some null fields
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
        }

        # Set specified fields to null/empty
        for field in null_fields:
            form_data[field] = None

        preview_table = self.entry_service.generate_preview_table(form_data)

        # Test that table structure is maintained
        assert len(preview_table.headers) == 29, (
            "Table should maintain 29 columns even with null values"
        )
        assert len(preview_table.rows) == 1, "Table should have exactly one row"

        # Test that null fields show as N/A
        row = preview_table.rows[0]
        for field in null_fields:
            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field:
                    header = h
                    break

            if header:
                assert row[header] == "N/A", (
                    f"Null field {field} should show as N/A in column {header}"
                )

    @given(
        boolean_fields=st.dictionaries(
            keys=st.sampled_from(["renovation", "builtin_flyscreen_track"]),
            values=st.booleans(),
            min_size=0,
            max_size=2,
        )
    )
    def test_boolean_field_formatting_in_csv(self, boolean_fields):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        For any boolean field values, they should be formatted consistently
        in the CSV structure (true -> "yes", false -> "no").
        """
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            **boolean_fields,
        }

        preview_table = self.entry_service.generate_preview_table(form_data)
        row = preview_table.rows[0]

        # Test boolean formatting
        for field_name, field_value in boolean_fields.items():
            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field_name:
                    header = h
                    break

            if header:
                expected_value = "yes" if field_value else "no"
                assert row[header] == expected_value, (
                    f"Boolean field {field_name} should format as '{expected_value}'"
                )

    @given(
        array_fields=st.dictionaries(
            keys=st.sampled_from(["reinforcement_steel", "colours"]),
            values=st.lists(st.text(min_size=1, max_size=20), min_size=0, max_size=5),
            min_size=0,
            max_size=2,
        )
    )
    def test_array_field_formatting_in_csv(self, array_fields):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        For any array field values, they should be formatted consistently
        in the CSV structure (joined with commas or N/A if empty).
        """
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            **array_fields,
        }

        preview_table = self.entry_service.generate_preview_table(form_data)
        row = preview_table.rows[0]

        # Test array formatting
        for field_name, field_value in array_fields.items():
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
                        f"Array field {field_name} should format as comma-separated list"
                    )
                else:
                    assert row[header] == "N/A", (
                        f"Empty array field {field_name} should show as N/A"
                    )

    @given(
        numeric_fields=st.dictionaries(
            keys=st.sampled_from(["price_per_meter", "price_per_beam"]),
            values=st.decimals(min_value=Decimal("0.01"), max_value=Decimal("9999.99"), places=2),
            min_size=0,
            max_size=2,
        )
    )
    def test_price_field_formatting_in_csv(self, numeric_fields):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        For any price field values, they should be formatted consistently
        in the CSV structure with proper decimal places.
        """
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
            **numeric_fields,
        }

        preview_table = self.entry_service.generate_preview_table(form_data)
        row = preview_table.rows[0]

        # Test price formatting
        for field_name, field_value in numeric_fields.items():
            # Find corresponding header
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field_name:
                    header = h
                    break

            if header:
                expected_value = f"{field_value:.2f}"
                assert row[header] == expected_value, (
                    f"Price field {field_name} should format with 2 decimal places"
                )

    def test_csv_structure_completeness(self):
        """**Feature: entry-page-system, Property 4: CSV structure preservation**

        Test that the CSV structure includes all required fields and maintains
        the exact order and naming from the reference CSV.
        """
        # Test with minimal required data
        form_data = {
            "manufacturing_type_id": 1,
            "name": "Test Profile",
            "type": "Frame",
            "material": "UPVC",
            "opening_system": "Casement",
            "system_series": "Kom700",
        }

        preview_table = self.entry_service.generate_preview_table(form_data)

        # Test header completeness
        assert len(preview_table.headers) == 29, "Should have all 29 CSV columns"

        # Test header order matches expected order
        for i, expected_header in enumerate(self.expected_headers):
            assert preview_table.headers[i] == expected_header, (
                f"Header at position {i} should be '{expected_header}'"
            )

        # Test that all field mappings are bidirectional
        mapped_fields = set(self.header_field_mapping.values())
        expected_fields = {
            "name",
            "type",
            "company",
            "material",
            "opening_system",
            "system_series",
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
            "upvc_profile_discount",
        }

        assert mapped_fields == expected_fields, "All expected fields should have header mappings"

        # Test row structure
        row = preview_table.rows[0]
        assert len(row) == 29, "Row should have values for all 29 columns"

        # Test that required fields show values, optional fields show N/A
        required_fields = ["name", "type", "material", "opening_system", "system_series"]
        for field in required_fields:
            header = None
            for h, f in self.header_field_mapping.items():
                if f == field:
                    header = h
                    break
            if header:
                assert row[header] != "N/A", f"Required field {field} should not show as N/A"
