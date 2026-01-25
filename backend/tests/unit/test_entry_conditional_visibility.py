"""Property-based tests for Entry Page conditional field visibility.

This module tests the real-time conditional field visibility functionality
using property-based testing to ensure correctness across various input combinations.

**Feature: entry-page-system, Property 2: Real-time conditional field visibility**
**Validates: Requirements 1.3, 3.1-3.5**
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from app.services.entry import ConditionEvaluator


class TestConditionalFieldVisibility:
    """Property-based tests for conditional field visibility."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ConditionEvaluator()

    @given(
        field_value=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(min_value=0, max_value=1000),
            st.booleans(),
            st.none(),
        ),
        expected_value=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(min_value=0, max_value=1000),
            st.booleans(),
        ),
    )
    def test_equals_operator_consistency(self, field_value, expected_value):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any field value and expected value, the equals operator should
        return True if and only if the values are equal.
        """
        condition = {"operator": "equals", "field": "test_field", "value": expected_value}

        form_data = {"test_field": field_value}

        result = self.evaluator.evaluate_condition(condition, form_data)
        expected_result = field_value == expected_value

        assert result == expected_result, (
            f"equals({field_value}, {expected_value}) should be {expected_result}"
        )

    @given(
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=10,
        )
    )
    def test_frame_type_shows_renovation_fields(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any form data, when type equals "Frame", renovation fields should be visible.
        """
        # Set type to Frame
        form_data["type"] = "Frame"

        # Test renovation field visibility condition
        renovation_condition = {"operator": "equals", "field": "type", "value": "Frame"}

        result = self.evaluator.evaluate_condition(renovation_condition, form_data)

        # Should always be True when type is Frame
        assert result is True, "Renovation fields should be visible when type is Frame"

    @given(
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=10,
        ),
        type_value=st.sampled_from(
            ["sash", "Mullion", "Flying mullion", "glazing bead", "Interlock", "Track", "auxilary"]
        ),
    )
    def test_non_frame_types_hide_renovation_fields(self, form_data, type_value):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any form data, when type is not "Frame", renovation fields should be hidden.
        """
        # Set type to non-Frame value
        form_data["type"] = type_value

        # Test renovation field visibility condition
        renovation_condition = {"operator": "equals", "field": "type", "value": "Frame"}

        result = self.evaluator.evaluate_condition(renovation_condition, form_data)

        # Should always be False when type is not Frame
        assert result is False, f"Renovation fields should be hidden when type is {type_value}"

    @given(
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=10,
        ),
        flyscreen_value=st.booleans(),
    )
    def test_flyscreen_conditional_visibility(self, form_data, flyscreen_value):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any form data, flyscreen width and height fields should be visible
        if and only if builtin_flyscreen_track is True.
        """
        form_data["builtin_flyscreen_track"] = flyscreen_value

        # Test flyscreen width/height visibility condition
        flyscreen_condition = {
            "operator": "equals",
            "field": "builtin_flyscreen_track",
            "value": True,
        }

        result = self.evaluator.evaluate_condition(flyscreen_condition, form_data)

        # Should match the flyscreen value
        assert result == flyscreen_value, (
            f"Flyscreen fields visibility should match builtin_flyscreen_track value: {flyscreen_value}"
        )

    @given(
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=10,
        )
    )
    def test_flying_mullion_clearance_fields(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any form data, flying mullion clearance fields should be visible
        if and only if type equals "Flying mullion".
        """
        # Test with Flying mullion type
        form_data["type"] = "Flying mullion"

        flying_mullion_condition = {
            "operator": "equals",
            "field": "type",
            "value": "Flying mullion",
        }

        result = self.evaluator.evaluate_condition(flying_mullion_condition, form_data)
        assert result is True, (
            "Flying mullion clearance fields should be visible when type is Flying mullion"
        )

        # Test with other type
        form_data["type"] = "Frame"
        result = self.evaluator.evaluate_condition(flying_mullion_condition, form_data)
        assert result is False, (
            "Flying mullion clearance fields should be hidden when type is not Flying mullion"
        )

    @given(
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=5,
        )
    )
    def test_and_operator_logical_consistency(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any form data, the AND operator should return True if and only if
        ALL individual conditions are True.
        """
        # Create simple test conditions using available form data keys
        field_keys = list(form_data.keys())
        if len(field_keys) >= 2:
            # Create two conditions using different fields
            condition1 = {"operator": "exists", "field": field_keys[0], "value": True}
            condition2 = {"operator": "exists", "field": field_keys[1], "value": True}

            and_condition = {"operator": "and", "conditions": [condition1, condition2]}

            # Evaluate AND condition
            and_result = self.evaluator.evaluate_condition(and_condition, form_data)

            # Evaluate individual conditions
            result1 = self.evaluator.evaluate_condition(condition1, form_data)
            result2 = self.evaluator.evaluate_condition(condition2, form_data)

            expected_result = result1 and result2
            assert and_result == expected_result, (
                f"AND operator should return {expected_result} for results [{result1}, {result2}]"
            )

    @given(
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=5,
        )
    )
    def test_or_operator_logical_consistency(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any form data, the OR operator should return True if and only if
        AT LEAST ONE individual condition is True.
        """
        # Create simple test conditions using available form data keys
        field_keys = list(form_data.keys())
        if len(field_keys) >= 2:
            # Create two conditions using different fields
            condition1 = {"operator": "exists", "field": field_keys[0], "value": True}
            condition2 = {
                "operator": "not_exists",  # This will likely be False
                "field": field_keys[1],
                "value": True,
            }

            or_condition = {"operator": "or", "conditions": [condition1, condition2]}

            # Evaluate OR condition
            or_result = self.evaluator.evaluate_condition(or_condition, form_data)

            # Evaluate individual conditions
            result1 = self.evaluator.evaluate_condition(condition1, form_data)
            result2 = self.evaluator.evaluate_condition(condition2, form_data)

            expected_result = result1 or result2
            assert or_result == expected_result, (
                f"OR operator should return {expected_result} for results [{result1}, {result2}]"
            )

    @given(
        field_path=st.text(
            min_size=1,
            max_size=50,
            alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd", "Pc")),
        ),
        form_data=st.dictionaries(
            keys=st.text(
                min_size=1,
                max_size=20,
                alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
            ),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=10,
        ),
    )
    def test_field_value_retrieval_consistency(self, field_path, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        For any field path and form data, field value retrieval should be consistent
        and return the correct value or None if not found.
        """
        result = self.evaluator.get_field_value(field_path, form_data)

        if "." not in field_path:
            # Simple field access
            expected = form_data.get(field_path)
            assert result == expected, (
                f"Simple field access should return {expected} for field {field_path}"
            )
        else:
            # Nested field access - should handle gracefully
            assert result is None or isinstance(result, (str, int, bool, type(None))), (
                "Nested field access should return valid type or None"
            )

    def test_real_world_conditional_scenarios(self):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Test real-world conditional scenarios from the CSV data analysis.
        """
        # Scenario 1: Frame type with renovation
        form_data = {"type": "Frame", "renovation": True}

        renovation_condition = {
            "operator": "and",
            "conditions": [
                {"operator": "equals", "field": "type", "value": "Frame"},
                {"operator": "equals", "field": "renovation", "value": True},
            ],
        }

        result = self.evaluator.evaluate_condition(renovation_condition, form_data)
        assert result is True, (
            "Renovation height should be visible for Frame type with renovation enabled"
        )

        # Scenario 2: Sliding frame with flyscreen
        form_data = {"system_series": "Kom800", "builtin_flyscreen_track": True}

        flyscreen_condition = {
            "operator": "and",
            "conditions": [
                {"operator": "equals", "field": "system_series", "value": "Kom800"},
                {"operator": "equals", "field": "builtin_flyscreen_track", "value": True},
            ],
        }

        result = self.evaluator.evaluate_condition(flyscreen_condition, form_data)
        assert result is True, (
            "Flyscreen dimensions should be visible for Kom800 series with flyscreen enabled"
        )

        # Scenario 3: Sash type for overlap field
        form_data = {"type": "sash"}

        sash_condition = {"operator": "equals", "field": "type", "value": "sash"}

        result = self.evaluator.evaluate_condition(sash_condition, form_data)
        assert result is True, "Sash overlap should be visible for sash type"
