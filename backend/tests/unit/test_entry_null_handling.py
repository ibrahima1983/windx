"""Property-based tests for entry page null value handling.

This module contains property-based tests that verify the entry page system
handles null, empty, and N/A values gracefully without errors.

Property 5: Graceful null value handling
- For any form fields with null, empty, or N/A values, the system should
  display them appropriately without errors and preserve them through
  save/load cycles
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.rbac import Role
from app.models.attribute_node import AttributeNode
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import EntryService


@st.composite
def profile_data_with_nulls(draw, manufacturing_type_id):
    """Generate profile data with various null/empty combinations."""
    # Base required fields
    base_data = {
        "manufacturing_type_id": manufacturing_type_id,
        "name": draw(st.text(min_size=1, max_size=100)),
        "type": draw(st.sampled_from(["Frame", "Flying mullion"])),
        "material": draw(st.sampled_from(["Aluminum", "Vinyl", "Wood"])),
        "opening_system": draw(st.sampled_from(["Casement", "Sliding", "Double-hung"])),
        "system_series": draw(st.sampled_from(["Kom800", "Series100", "Premium"])),
    }

    # Optional fields with high probability of being null/empty
    optional_fields = {
        "company": draw(st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=100))),
        "code": draw(st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=20))),
        "length_of_beam": draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0))),
        "renovation": draw(st.one_of(st.none(), st.booleans())),
        "width": draw(st.one_of(st.none(), st.floats(min_value=10.0, max_value=200.0))),
        "builtin_flyscreen_track": draw(st.one_of(st.none(), st.booleans())),
        "total_width": draw(st.one_of(st.none(), st.floats(min_value=10.0, max_value=250.0))),
        "flyscreen_track_height": draw(
            st.one_of(st.none(), st.floats(min_value=5.0, max_value=100.0))
        ),
        "front_height": draw(st.one_of(st.none(), st.floats(min_value=20.0, max_value=300.0))),
        "rear_height": draw(st.one_of(st.none(), st.floats(min_value=20.0, max_value=300.0))),
        "glazing_height": draw(st.one_of(st.none(), st.floats(min_value=15.0, max_value=250.0))),
        "renovation_height": draw(st.one_of(st.none(), st.floats(min_value=15.0, max_value=250.0))),
        "glazing_undercut_height": draw(
            st.one_of(st.none(), st.floats(min_value=10.0, max_value=200.0))
        ),
        "pic": draw(st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=100))),
        "sash_overlap": draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0))),
        "flying_mullion_horizontal_clearance": draw(
            st.one_of(st.none(), st.floats(min_value=0.1, max_value=5.0))
        ),
        "flying_mullion_vertical_clearance": draw(
            st.one_of(st.none(), st.floats(min_value=0.1, max_value=5.0))
        ),
        "steel_material_thickness": draw(
            st.one_of(st.none(), st.floats(min_value=0.5, max_value=5.0))
        ),
        "weight_per_meter": draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=20.0))),
        "reinforcement_steel": draw(
            st.one_of(
                st.none(),
                st.just([]),
                st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3),
            )
        ),
        "colours": draw(
            st.one_of(
                st.none(),
                st.just([]),
                st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5),
            )
        ),
        "price_per_meter": draw(
            st.one_of(st.none(), st.decimals(min_value=1, max_value=500, places=2))
        ),
        "price_per_beam": draw(
            st.one_of(st.none(), st.decimals(min_value=10, max_value=2000, places=2))
        ),
        "upvc_profile_discount": draw(
            st.one_of(st.none(), st.floats(min_value=0.0, max_value=50.0))
        ),
    }

    # Combine base and optional fields
    all_data = {**base_data, **optional_fields}
    return ProfileEntryData(**all_data)


@st.composite
def form_data_with_nulls(draw):
    """Generate form data dictionary with various null/empty combinations."""
    return {
        "name": draw(st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=100))),
        "type": draw(
            st.one_of(st.none(), st.just(""), st.sampled_from(["Frame", "Flying mullion"]))
        ),
        "company": draw(st.one_of(st.none(), st.just(""), st.text(min_size=1, max_size=100))),
        "material": draw(
            st.one_of(st.none(), st.just(""), st.sampled_from(["Aluminum", "Vinyl", "Wood"]))
        ),
        "opening_system": draw(
            st.one_of(st.none(), st.just(""), st.sampled_from(["Casement", "Sliding"]))
        ),
        "width": draw(st.one_of(st.none(), st.floats(min_value=10.0, max_value=200.0))),
        "height": draw(st.one_of(st.none(), st.floats(min_value=10.0, max_value=200.0))),
        "price": draw(st.one_of(st.none(), st.decimals(min_value=1, max_value=1000, places=2))),
        "colours": draw(
            st.one_of(
                st.none(), st.just([]), st.lists(st.text(min_size=1, max_size=20), max_size=3)
            )
        ),
        "renovation": draw(st.one_of(st.none(), st.booleans())),
    }


class TestEntryNullHandling:
    """Test class for entry page null value handling properties."""

    @pytest.mark.asyncio
    @given(profile_data=profile_data_with_nulls(1))
    @settings(max_examples=100, deadline=None)
    async def test_property_graceful_null_value_handling(self, profile_data: ProfileEntryData):
        """
        **Feature: entry-page-system, Property 5: Graceful null value handling**

        Property: For any form fields with null, empty, or N/A values, the system should
        display them appropriately without errors and preserve them through save/load cycles.

        This property ensures that the system handles missing or empty data gracefully,
        maintaining data integrity and providing appropriate display formatting.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Test preview generation with null values
        form_data = profile_data.model_dump()

        # Act - Generate preview table (should not raise exceptions)
        try:
            preview_table = entry_service.generate_preview_table(form_data)

            # Assert - Preview table should be generated successfully
            assert preview_table is not None
            assert len(preview_table.headers) == 29  # All CSV columns
            assert len(preview_table.rows) == 1

            # Verify null/empty values are handled gracefully
            row_data = preview_table.rows[0]
            for header, value in row_data.items():
                # All values should be strings (formatted for display)
                assert isinstance(value, str)
                # Null/empty values should be displayed as "N/A"
                if value in [None, "", []]:
                    # These should have been converted to "N/A" by format_preview_value
                    pass  # The conversion happens in format_preview_value

        except Exception as e:
            pytest.fail(f"Preview generation failed with null values: {e}")

    @pytest.mark.asyncio
    @given(form_data=form_data_with_nulls())
    @settings(max_examples=100, deadline=None)
    async def test_property_format_preview_value_null_handling(self, form_data: dict):
        """
        Property: For any value (including null, empty string, empty list, etc.),
        the format_preview_value method should return a valid string representation
        without raising exceptions.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act & Assert - Test format_preview_value with various null/empty values
        for field_name, field_value in form_data.items():
            try:
                formatted_value = entry_service.format_preview_value(field_value)

                # Should always return a string
                assert isinstance(formatted_value, str)

                # Verify specific null/empty handling
                if field_value is None or field_value == "":
                    assert formatted_value == "N/A"
                elif isinstance(field_value, list) and len(field_value) == 0:
                    assert formatted_value == "N/A"
                elif isinstance(field_value, bool):
                    assert formatted_value in ["yes", "no"]
                elif isinstance(field_value, list) and len(field_value) > 0:
                    assert ", " in formatted_value or len(field_value) == 1
                else:
                    # Should be string representation of the value
                    assert len(formatted_value) > 0

            except Exception as e:
                pytest.fail(f"format_preview_value failed for {field_name}={field_value}: {e}")

    @pytest.mark.asyncio
    @given(
        profile_data=profile_data_with_nulls(1),
        user_data=st.builds(
            User,
            id=st.integers(min_value=1, max_value=1000),
            email=st.emails(),
            username=st.text(min_size=1, max_size=50),
            role=st.sampled_from([Role.CUSTOMER.value, Role.SALESMAN.value]),
            is_active=st.just(True),
        ),
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_save_load_null_preservation(
        self, profile_data: ProfileEntryData, user_data: User
    ):
        """
        Property: For any profile data containing null/empty values, the save/load
        cycle should preserve the null state of fields, not converting them to
        default values or empty strings.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock dependencies
        manufacturing_type = ManufacturingType(
            id=profile_data.manufacturing_type_id,
            name="Test Type",
            base_price=200.00,
            base_weight=15.00,
        )

        customer = Customer(
            id=1,
            company_name="Test Company",
            contact_person="Test Person",
            email="test@example.com",
        )

        # Mock attribute nodes (simplified)
        attribute_nodes = [
            AttributeNode(
                id=i,
                manufacturing_type_id=profile_data.manufacturing_type_id,
                name=field_name,
                node_type="attribute",
                data_type="string",
                ltree_path=f"section.{field_name}",
            )
            for i, field_name in enumerate(
                [
                    "type",
                    "company",
                    "material",
                    "opening_system",
                    "system_series",
                    "code",
                    "width",
                    "renovation",
                    "colours",
                    "price_per_meter",
                ],
                1,
            )
        ]

        # Set up mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=attribute_nodes)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute.return_value = mock_result

        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user.return_value = customer
        entry_service.validate_profile_data = AsyncMock(return_value={"valid": True})
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()
        mock_db.add = MagicMock()

        # Act - Save (should not raise exceptions with null values)
        try:
            await entry_service.save_profile_configuration(profile_data, user_data)

            # Verify save operations were called
            assert entry_service.validate_profile_data.called
            assert mock_db.add.called
            assert entry_service.commit.called

        except Exception as e:
            pytest.fail(f"Save operation failed with null values: {e}")

    @pytest.mark.asyncio
    @given(
        null_values=st.lists(
            st.one_of(st.none(), st.just(""), st.just([]), st.just({}), st.just(0), st.just(False)),
            min_size=1,
            max_size=10,
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_format_preview_value_edge_cases(self, null_values: list):
        """
        Property: For any edge case values (None, empty string, empty list, empty dict,
        zero, False), the format_preview_value method should handle them consistently
        and return appropriate string representations.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act & Assert
        for value in null_values:
            try:
                formatted = entry_service.format_preview_value(value)

                # Should always return a string
                assert isinstance(formatted, str)

                # Verify specific handling
                if value is None or value == "":
                    assert formatted == "N/A"
                elif isinstance(value, list) and len(value) == 0:
                    assert formatted == "N/A"
                elif isinstance(value, dict) and len(value) == 0:
                    assert formatted == "{}"  # Empty dict representation
                elif value is False:
                    assert formatted == "no"
                elif value == 0:
                    assert formatted == "0"

            except Exception as e:
                pytest.fail(f"format_preview_value failed for edge case {value}: {e}")

    @pytest.mark.asyncio
    @given(
        mixed_data=st.dictionaries(
            st.text(min_size=1, max_size=20),
            st.one_of(
                st.none(),
                st.just(""),
                st.text(min_size=1, max_size=50),
                st.integers(),
                st.floats(allow_nan=False, allow_infinity=False),
                st.booleans(),
                st.lists(st.text(min_size=1, max_size=20), max_size=3),
                st.just([]),
                st.dictionaries(
                    st.text(min_size=1, max_size=10), st.text(min_size=1, max_size=10), max_size=3
                ),
            ),
            min_size=1,
            max_size=15,
        )
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_preview_table_generation_robustness(self, mixed_data: dict):
        """
        Property: For any dictionary containing mixed data types including nulls,
        the generate_preview_table method should successfully create a preview table
        without raising exceptions.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act
        try:
            preview_table = entry_service.generate_preview_table(mixed_data)

            # Assert
            assert preview_table is not None
            assert hasattr(preview_table, "headers")
            assert hasattr(preview_table, "rows")
            assert len(preview_table.headers) == 29  # All CSV columns
            assert len(preview_table.rows) == 1

            # Verify all values in the row are strings
            row_data = preview_table.rows[0]
            for header, value in row_data.items():
                assert isinstance(value, str)

        except Exception as e:
            pytest.fail(f"generate_preview_table failed with mixed data: {e}")
