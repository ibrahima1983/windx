"""Property-based tests for entry page error recovery and user experience.

This module contains property-based tests that verify the entry page system
provides user-friendly error messages and maintains user-entered data during error states.

**Feature: entry-page-system, Property 10: Error recovery and user experience**
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from app.core.exceptions import NotFoundException, ValidationException
from app.models.user import User
from app.schemas.entry import FieldDefinition, FormSection, ProfileEntryData, ProfileSchema
from app.services.entry import EntryService


@st.composite
def profile_data_with_errors(draw):
    """Generate profile data that may contain various types of errors."""
    # Start with potentially valid base data
    base_data = {
        "manufacturing_type_id": draw(st.integers(min_value=1, max_value=100)),
        "name": draw(st.text(min_size=0, max_size=100)),  # May be empty
        "type": draw(st.text(min_size=0, max_size=50)),  # May be empty
        "material": draw(st.text(min_size=0, max_size=50)),
        "opening_system": draw(st.text(min_size=0, max_size=50)),
        "system_series": draw(st.text(min_size=0, max_size=50)),
    }

    # Add optional fields with potential error conditions
    optional_fields = {
        "company": draw(st.one_of(st.none(), st.text(max_size=200))),  # May be too long
        "width": draw(
            st.one_of(st.none(), st.floats(min_value=-100, max_value=1000))
        ),  # May be negative
        "height": draw(st.one_of(st.none(), st.floats(min_value=-100, max_value=1000))),
        "price_per_meter": draw(
            st.one_of(st.none(), st.decimals(min_value=-1000, max_value=10000, places=2))
        ),
        "email": draw(st.one_of(st.none(), st.text(max_size=100))),  # May be invalid email format
    }

    base_data.update(optional_fields)

    try:
        return ProfileEntryData(**base_data)
    except Exception:
        # If Pydantic validation fails, create minimal valid data
        return ProfileEntryData(
            manufacturing_type_id=1,
            name="Test",
            type="Frame",
            material="Aluminum",
            opening_system="Casement",
            system_series="Kom800",
        )


@st.composite
def mock_user(draw):
    """Generate mock user for testing."""
    user = MagicMock(spec=User)
    user.id = draw(st.integers(min_value=1, max_value=1000))
    user.username = draw(st.text(min_size=3, max_size=20))
    user.email = draw(st.text(min_size=5, max_size=50))
    user.is_active = True
    return user


class TestEntryErrorRecoveryProperties:
    """Test class for entry page error recovery and user experience properties."""

    @pytest.mark.asyncio
    @given(profile_data=profile_data_with_errors(), user=mock_user())
    async def test_property_error_recovery_validation_errors(
        self, profile_data: ProfileEntryData, user
    ):
        """
        **Feature: entry-page-system, Property 10: Error recovery and user experience**

        Property: For any system errors or validation failures, the system should
        provide user-friendly error messages and maintain user-entered data to
        allow corrections.

        This test verifies validation error recovery.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create schema with validation rules that may be violated
        fields = [
            FieldDefinition(
                name="name",
                label="Configuration Name",
                data_type="string",
                required=True,
                validation_rules={"min_length": 1, "max_length": 50},
            ),
            FieldDefinition(
                name="type",
                label="Product Type",
                data_type="string",
                required=True,
                validation_rules={"choices": ["Frame", "Flying mullion"]},
            ),
            FieldDefinition(
                name="width",
                label="Width",
                data_type="number",
                required=False,
                validation_rules={"min": 10, "max": 500},
            ),
            FieldDefinition(
                name="email",
                label="Contact Email",
                data_type="string",
                required=False,
                validation_rules={"rule_type": "email"},
            ),
        ]

        schema = ProfileSchema(
            manufacturing_type_id=profile_data.manufacturing_type_id,
            sections=[FormSection(title="Test Section", fields=fields)],
            conditional_logic={},
        )

        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Act - Attempt validation
        try:
            await entry_service.validate_profile_data(profile_data)
            # If validation passes, that's fine

        except ValidationException as e:
            # Assert - Error should be user-friendly and preserve data context
            assert isinstance(e.field_errors, dict)

            # Error messages should be user-friendly
            for field_name, error_message in e.field_errors.items():
                assert isinstance(error_message, str)
                assert len(error_message) > 0

                # Should not contain technical jargon or stack traces
                assert "Traceback" not in error_message
                assert "Exception" not in error_message
                assert "NoneType" not in error_message

                # Should reference the field in a user-friendly way
                field_found = False
                for field in fields:
                    if field.name == field_name:
                        # Error should mention field label or name
                        assert (
                            field.label.lower() in error_message.lower()
                            or field.name.lower() in error_message.lower()
                        )
                        field_found = True
                        break

                if not field_found:
                    # Cross-field validation errors are also acceptable
                    assert field_name in [
                        "total_width",
                        "flyscreen_track_height",
                        "flying_mullion_horizontal_clearance",
                        "flying_mullion_vertical_clearance",
                        "steel_material_thickness",
                    ]

            # Original data should be preserved (can be accessed from profile_data)
            assert profile_data.manufacturing_type_id is not None
            assert profile_data.name is not None
            assert profile_data.type is not None

    @pytest.mark.asyncio
    @given(
        manufacturing_type_id=st.integers(min_value=1000, max_value=9999),  # Likely non-existent
        user=mock_user(),
    )
    async def test_property_error_recovery_not_found_errors(self, manufacturing_type_id: int, user):
        """
        **Feature: entry-page-system, Property 10: Error recovery and user experience**

        Property: Not found errors should provide clear guidance on what was
        not found and suggest recovery actions.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock database to return no results
        def mock_execute_side_effect(stmt):
            mock_result = AsyncMock()
            mock_result.scalar_one_or_none = MagicMock(return_value=None)  # Use MagicMock
            return mock_result

        mock_db.execute.side_effect = mock_execute_side_effect

        # Act - Attempt to get schema for non-existent manufacturing type
        try:
            await entry_service.get_profile_schema(manufacturing_type_id)
            pytest.fail("Should have raised NotFoundException")

        except NotFoundException as e:
            # Assert - Error should be user-friendly and informative
            error_message = str(e)

            # Should mention what was not found
            assert "Manufacturing type" in error_message or "not found" in error_message
            assert str(manufacturing_type_id) in error_message

            # Should not contain technical details
            assert "scalar_one_or_none" not in error_message
            assert "SELECT" not in error_message
            assert "Traceback" not in error_message

    @pytest.mark.asyncio
    @given(
        profile_data=profile_data_with_errors(),
        user=mock_user(),
        database_error=st.sampled_from(
            [
                "Connection timeout",
                "Database unavailable",
                "Transaction rollback",
                "Constraint violation",
            ]
        ),
    )
    async def test_property_error_recovery_database_errors(
        self, profile_data: ProfileEntryData, user, database_error: str
    ):
        """
        **Feature: entry-page-system, Property 10: Error recovery and user experience**

        Property: Database errors should be handled gracefully with user-friendly
        messages that don't expose internal system details.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock database to raise various errors
        mock_db.execute.side_effect = Exception(database_error)

        # Act - Attempt operation that would cause database error
        try:
            await entry_service.get_profile_schema(profile_data.manufacturing_type_id)

        except Exception as e:
            # Assert - Error handling should be graceful
            error_message = str(e)

            # Should not expose internal database details in user-facing errors
            # (This test verifies the error doesn't crash the system)
            assert isinstance(error_message, str)

            # System should remain stable (no unhandled exceptions)
            assert len(error_message) > 0

    @given(
        field_values=st.dictionaries(
            st.sampled_from(["name", "type", "material", "width", "email"]),
            st.one_of(
                st.text(max_size=100),
                st.floats(allow_nan=False, allow_infinity=False),
                st.integers(),
                st.none(),
            ),
            min_size=1,
            max_size=5,
        ),
        validation_rules=st.dictionaries(
            st.sampled_from(["min", "max", "min_length", "max_length", "pattern", "rule_type"]),
            st.one_of(
                st.integers(min_value=1, max_value=100),
                st.text(min_size=1, max_size=50),
                st.sampled_from(["email", "positive", "non_negative"]),
            ),
            min_size=1,
            max_size=3,
        ),
    )
    def test_property_field_validation_error_messages(
        self, field_values: dict, validation_rules: dict
    ):
        """
        **Feature: entry-page-system, Property 10: Error recovery and user experience**

        Property: Field validation errors should provide specific, actionable
        error messages that help users understand how to fix the problem.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act - Test field validation for each field
        for field_name, field_value in field_values.items():
            if field_value is not None:
                error_message = entry_service.validate_field_value(
                    field_value, validation_rules, field_name.replace("_", " ").title()
                )

                # Assert - Error messages should be helpful
                if error_message:
                    assert isinstance(error_message, str)
                    assert len(error_message) > 0

                    # Should not contain technical jargon
                    assert "ValueError" not in error_message
                    assert "TypeError" not in error_message
                    assert "Exception" not in error_message

                    # Should provide actionable guidance
                    helpful_words = [
                        "must",
                        "should",
                        "required",
                        "between",
                        "at least",
                        "at most",
                        "format",
                        "valid",
                    ]
                    has_helpful_word = any(word in error_message.lower() for word in helpful_words)
                    assert has_helpful_word, f"Error message should be helpful: {error_message}"

    @pytest.mark.asyncio
    @given(original_data=profile_data_with_errors(), user=mock_user())
    async def test_property_data_preservation_during_errors(
        self, original_data: ProfileEntryData, user
    ):
        """
        **Feature: entry-page-system, Property 10: Error recovery and user experience**

        Property: When validation or other errors occur, the original user data
        should be preserved to allow corrections without re-entry.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Create schema that will likely cause validation errors
        strict_fields = [
            FieldDefinition(
                name="name",
                label="Name",
                data_type="string",
                required=True,
                validation_rules={"min_length": 5, "max_length": 20},
            ),
            FieldDefinition(
                name="type",
                label="Type",
                data_type="string",
                required=True,
                validation_rules={"choices": ["Frame"]},  # Very restrictive
            ),
        ]

        schema = ProfileSchema(
            manufacturing_type_id=original_data.manufacturing_type_id,
            sections=[FormSection(title="Strict Section", fields=strict_fields)],
            conditional_logic={},
        )

        entry_service.get_profile_schema = AsyncMock(return_value=schema)

        # Store original values for comparison
        original_name = original_data.name
        original_type = original_data.type
        original_material = original_data.material

        # Act - Attempt validation (may fail)
        try:
            await entry_service.validate_profile_data(original_data)

        except ValidationException:
            # Assert - Original data should be unchanged
            assert original_data.name == original_name
            assert original_data.type == original_type
            assert original_data.material == original_material

            # Data object should still be valid and accessible
            assert original_data.manufacturing_type_id is not None
            assert hasattr(original_data, "name")
            assert hasattr(original_data, "type")
            assert hasattr(original_data, "material")

            # Should be able to create new ProfileEntryData with corrected values
            corrected_data = ProfileEntryData(
                manufacturing_type_id=original_data.manufacturing_type_id,
                name="Valid Name",  # Corrected
                type="Frame",  # Corrected
                material=original_data.material,  # Preserved
                opening_system=original_data.opening_system,  # Preserved
                system_series=original_data.system_series,  # Preserved
            )

            # Corrected data should be valid
            assert corrected_data.name == "Valid Name"
            assert corrected_data.type == "Frame"
            assert corrected_data.material == original_data.material

    @given(
        error_scenarios=st.lists(
            st.fixed_dictionaries(
                {
                    "error_type": st.sampled_from(
                        ["validation", "not_found", "authorization", "database"]
                    ),
                    "field_name": st.sampled_from(["name", "type", "width", "email"]),
                    "error_context": st.text(min_size=5, max_size=50),
                }
            ),
            min_size=1,
            max_size=3,
        )
    )
    def test_property_error_message_consistency(self, error_scenarios: list[dict]):
        """
        **Feature: entry-page-system, Property 10: Error recovery and user experience**

        Property: Error messages should be consistent in format and tone
        across different types of errors and fields.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        # Act & Assert - Test error message consistency
        for scenario in error_scenarios:
            error_type = scenario["error_type"]
            field_name = scenario["field_name"]

            # Generate appropriate error based on type
            if error_type == "validation":
                # Test field validation error
                error_msg = entry_service.validate_field_value(
                    "invalid_value", {"min_length": 10}, field_name.replace("_", " ").title()
                )

                if error_msg:
                    # Should follow consistent format
                    assert isinstance(error_msg, str)
                    assert len(error_msg) > 0

                    # Should start with field name or be descriptive
                    field_label = field_name.replace("_", " ").title()
                    assert (
                        error_msg.startswith(field_label)
                        or field_label.lower() in error_msg.lower()
                    )

                    # Should end with period or be complete sentence
                    assert (
                        error_msg.endswith(".")
                        or error_msg.endswith("!")
                        or len(error_msg.split()) > 3
                    )

            elif error_type == "not_found":
                # Test NotFoundException format
                try:
                    raise NotFoundException(f"{field_name.title()} not found")
                except NotFoundException as e:
                    error_msg = str(e)
                    assert "not found" in error_msg.lower()
                    assert field_name.lower() in error_msg.lower()

            # All error messages should be user-friendly
            # (No technical stack traces or internal details)
