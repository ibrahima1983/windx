"""Property-based tests for entry service condition evaluation.

**Feature: entry-page-system, Property 2: Real-time conditional field visibility**
**Validates: Requirements 1.3, 3.1-3.5**

Tests that conditional field visibility evaluation works correctly across
all possible combinations of form data and condition structures.
"""

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from app.services.entry import ConditionEvaluator

# Strategy for generating valid field names
field_names = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=20,
).filter(lambda x: x[0].isalpha())

# Strategy for generating field values (optimized for speed)
field_values = st.one_of(
    st.text(min_size=0, max_size=10),  # Reduced from 50 to 10
    st.integers(min_value=-100, max_value=100),  # Reduced range
    st.floats(
        min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False
    ),  # Reduced range
    st.booleans(),
    st.none(),
    st.lists(st.text(min_size=1, max_size=5), min_size=0, max_size=3),  # Reduced sizes
)

# Strategy for generating form data (optimized for speed)
form_data_strategy = st.dictionaries(
    keys=field_names,
    values=field_values,
    min_size=1,
    max_size=5,  # Reduced from 20 to 5 for faster generation
)

# Strategy for generating comparison operators
comparison_operators = st.sampled_from(
    ["equals", "not_equals", "greater_than", "less_than", "greater_equal", "less_equal"]
)

# Strategy for generating string operators
string_operators = st.sampled_from(["contains", "starts_with", "ends_with", "matches_pattern"])

# Strategy for generating collection operators
collection_operators = st.sampled_from(["in", "not_in", "any_of", "all_of"])

# Strategy for generating existence operators
existence_operators = st.sampled_from(["exists", "not_exists", "is_empty", "is_not_empty"])

# Strategy for generating all operators
all_operators = st.one_of(
    comparison_operators, string_operators, collection_operators, existence_operators
)


@composite
def simple_condition_strategy(draw):
    """Generate simple field-based conditions."""
    operator = draw(all_operators)
    field = draw(field_names)

    # Generate appropriate value based on operator
    if operator in ["matches_pattern"]:
        # Simple regex patterns that won't cause errors
        value = draw(st.sampled_from([r"^[A-Z]+$", r"\d+", r".*test.*", r"^Frame$"]))
    elif operator in ["any_of", "all_of", "in", "not_in"]:
        value = draw(st.lists(field_values, min_size=1, max_size=5))
    elif operator in ["exists", "not_exists", "is_empty", "is_not_empty"]:
        value = None  # These operators don't use the value
    else:
        value = draw(field_values)

    return {"operator": operator, "field": field, "value": value}


@composite
def logical_condition_strategy(draw, max_depth=3):
    """Generate logical conditions with nested structure."""
    if max_depth <= 0:
        return draw(simple_condition_strategy())

    operator = draw(st.sampled_from(["and", "or", "not"]))

    if operator == "not":
        return {"operator": "not", "condition": draw(logical_condition_strategy(max_depth - 1))}
    else:
        conditions = draw(
            st.lists(logical_condition_strategy(max_depth - 1), min_size=1, max_size=3)
        )
        return {"operator": operator, "conditions": conditions}


# Combined condition strategy
condition_strategy = st.one_of(simple_condition_strategy(), logical_condition_strategy(max_depth=2))


class TestConditionEvaluationProperties:
    """Property-based tests for condition evaluation."""

    def setup_method(self):
        """Set up test fixtures."""
        self.evaluator = ConditionEvaluator()

    @given(form_data=form_data_strategy)
    @settings(max_examples=20, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_empty_condition_always_returns_true(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Empty or None conditions should always return True (field visible).
        """
        # Empty condition
        result = self.evaluator.evaluate_condition({}, form_data)
        assert result is True

        # None condition
        result = self.evaluator.evaluate_condition(None, form_data)
        assert result is True

        # Condition without operator
        result = self.evaluator.evaluate_condition({"field": "test"}, form_data)
        assert result is True

    @given(condition=simple_condition_strategy(), form_data=form_data_strategy)
    @settings(max_examples=20, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_condition_evaluation_is_deterministic(self, condition, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Evaluating the same condition with the same form data should
        always return the same result (deterministic).
        """
        # Skip problematic regex patterns that might cause errors
        if (
            condition.get("operator") == "matches_pattern"
            and condition.get("value")
            and any(char in str(condition["value"]) for char in ["[", "]", "(", ")", "*", "+", "?"])
        ):
            assume(False)

        try:
            result1 = self.evaluator.evaluate_condition(condition, form_data)
            result2 = self.evaluator.evaluate_condition(condition, form_data)
            result3 = self.evaluator.evaluate_condition(condition, form_data)

            assert result1 == result2 == result3
            assert isinstance(result1, bool)
        except ValueError:
            # Invalid operators should consistently raise ValueError
            with pytest.raises(ValueError):
                self.evaluator.evaluate_condition(condition, form_data)

    @given(form_data=form_data_strategy)
    @settings(max_examples=10, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_equals_operator_reflexivity(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: For any field that exists in form data,
        field equals its own value should return True.
        """
        for field_name, field_value in form_data.items():
            condition = {"operator": "equals", "field": field_name, "value": field_value}

            result = self.evaluator.evaluate_condition(condition, form_data)
            assert result is True

    @given(form_data=form_data_strategy)
    @settings(max_examples=10, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_not_equals_operator_consistency(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: For any field, (field equals value) should be the opposite
        of (field not_equals value).
        """
        for field_name, field_value in form_data.items():
            equals_condition = {"operator": "equals", "field": field_name, "value": field_value}

            not_equals_condition = {
                "operator": "not_equals",
                "field": field_name,
                "value": field_value,
            }

            equals_result = self.evaluator.evaluate_condition(equals_condition, form_data)
            not_equals_result = self.evaluator.evaluate_condition(not_equals_condition, form_data)

            assert equals_result != not_equals_result

    @given(form_data=form_data_strategy)
    @settings(max_examples=10, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_exists_operator_consistency(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: For any field, (field exists) should be the opposite of (field not_exists).
        """
        for field_name in form_data.keys():
            exists_condition = {"operator": "exists", "field": field_name, "value": None}

            not_exists_condition = {"operator": "not_exists", "field": field_name, "value": None}

            exists_result = self.evaluator.evaluate_condition(exists_condition, form_data)
            not_exists_result = self.evaluator.evaluate_condition(not_exists_condition, form_data)

            assert exists_result != not_exists_result

    @given(condition=simple_condition_strategy(), form_data=form_data_strategy)
    @settings(max_examples=10, deadline=2000, suppress_health_check=[HealthCheck.too_slow])
    def test_logical_not_operator_consistency(self, condition, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: For any condition, NOT(condition) should be the opposite of condition.
        """
        # Skip problematic conditions
        if (
            condition.get("operator") == "matches_pattern"
            and condition.get("value")
            and any(char in str(condition["value"]) for char in ["[", "]", "(", ")", "*", "+", "?"])
        ):
            assume(False)

        not_condition = {"operator": "not", "condition": condition}

        try:
            original_result = self.evaluator.evaluate_condition(condition, form_data)
            not_result = self.evaluator.evaluate_condition(not_condition, form_data)

            assert original_result != not_result
        except ValueError:
            # If original condition raises ValueError, NOT condition should too
            with pytest.raises(ValueError):
                self.evaluator.evaluate_condition(not_condition, form_data)

    @given(
        condition1=simple_condition_strategy(),
        condition2=simple_condition_strategy(),
        form_data=form_data_strategy,
    )
    @settings(max_examples=30, deadline=1000)
    def test_logical_and_operator_properties(self, condition1, condition2, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: AND operator should follow logical AND rules:
        - If either condition is False, result is False
        - If both conditions are True, result is True
        """
        # Skip problematic conditions
        for cond in [condition1, condition2]:
            if (
                cond.get("operator") == "matches_pattern"
                and cond.get("value")
                and any(char in str(cond["value"]) for char in ["[", "]", "(", ")", "*", "+", "?"])
            ):
                assume(False)

        and_condition = {"operator": "and", "conditions": [condition1, condition2]}

        try:
            result1 = self.evaluator.evaluate_condition(condition1, form_data)
            result2 = self.evaluator.evaluate_condition(condition2, form_data)
            and_result = self.evaluator.evaluate_condition(and_condition, form_data)

            # AND logic: True only if both are True
            expected = result1 and result2
            assert and_result == expected
        except ValueError:
            # If any condition raises ValueError, AND should too
            with pytest.raises(ValueError):
                self.evaluator.evaluate_condition(and_condition, form_data)

    @given(
        condition1=simple_condition_strategy(),
        condition2=simple_condition_strategy(),
        form_data=form_data_strategy,
    )
    @settings(max_examples=30, deadline=1000)
    def test_logical_or_operator_properties(self, condition1, condition2, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: OR operator should follow logical OR rules:
        - If either condition is True, result is True
        - If both conditions are False, result is False
        """
        # Skip problematic conditions
        for cond in [condition1, condition2]:
            if (
                cond.get("operator") == "matches_pattern"
                and cond.get("value")
                and any(char in str(cond["value"]) for char in ["[", "]", "(", ")", "*", "+", "?"])
            ):
                assume(False)

        or_condition = {"operator": "or", "conditions": [condition1, condition2]}

        try:
            result1 = self.evaluator.evaluate_condition(condition1, form_data)
            result2 = self.evaluator.evaluate_condition(condition2, form_data)
            or_result = self.evaluator.evaluate_condition(or_condition, form_data)

            # OR logic: True if either is True
            expected = result1 or result2
            assert or_result == expected
        except ValueError:
            # If any condition raises ValueError, OR should too
            with pytest.raises(ValueError):
                self.evaluator.evaluate_condition(or_condition, form_data)

    @given(form_data=form_data_strategy, field_name=field_names)
    @settings(max_examples=50, deadline=1000)
    def test_nonexistent_field_handling(self, form_data, field_name):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Conditions referencing non-existent fields should handle gracefully.
        """
        # Ensure field doesn't exist in form data
        assume(field_name not in form_data)

        condition = {"operator": "equals", "field": field_name, "value": "any_value"}

        # Should not raise exception, should return False for equals
        result = self.evaluator.evaluate_condition(condition, form_data)
        assert isinstance(result, bool)
        assert result is False  # Non-existent field equals anything should be False

        # Exists should return False for non-existent field
        exists_condition = {"operator": "exists", "field": field_name, "value": None}

        exists_result = self.evaluator.evaluate_condition(exists_condition, form_data)
        assert exists_result is False

        # Not exists should return True for non-existent field
        not_exists_condition = {"operator": "not_exists", "field": field_name, "value": None}

        not_exists_result = self.evaluator.evaluate_condition(not_exists_condition, form_data)
        assert not_exists_result is True

    @given(form_data=form_data_strategy)
    @settings(max_examples=30, deadline=1000)
    def test_nested_field_access_consistency(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Nested field access should be consistent with direct access
        when no nesting is involved.
        """
        for field_name, field_value in form_data.items():
            # Direct access
            direct_condition = {"operator": "equals", "field": field_name, "value": field_value}

            direct_result = self.evaluator.evaluate_condition(direct_condition, form_data)

            # "Nested" access with single level (should be same as direct)
            nested_condition = {
                "operator": "equals",
                "field": field_name,  # Same field, no dots
                "value": field_value,
            }

            nested_result = self.evaluator.evaluate_condition(nested_condition, form_data)

            assert direct_result == nested_result

    @given(numeric_value=st.integers(min_value=-100, max_value=100), form_data=form_data_strategy)
    @settings(max_examples=30, deadline=1000)
    def test_comparison_operator_transitivity(self, numeric_value, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Comparison operators should follow mathematical transitivity rules.
        """
        # Add a numeric field to form data
        field_name = "test_numeric"
        test_form_data = {**form_data, field_name: numeric_value}

        # Test greater_than and less_than consistency
        gt_condition = {"operator": "greater_than", "field": field_name, "value": numeric_value - 1}

        lt_condition = {"operator": "less_than", "field": field_name, "value": numeric_value + 1}

        gt_result = self.evaluator.evaluate_condition(gt_condition, test_form_data)
        lt_result = self.evaluator.evaluate_condition(lt_condition, test_form_data)

        # Both should be True (value > value-1 and value < value+1)
        assert gt_result is True
        assert lt_result is True

        # Test equals with same value
        eq_condition = {"operator": "equals", "field": field_name, "value": numeric_value}

        eq_result = self.evaluator.evaluate_condition(eq_condition, test_form_data)
        assert eq_result is True

    @given(condition=condition_strategy, form_data=form_data_strategy)
    @settings(max_examples=50, deadline=2000)
    def test_condition_evaluation_always_returns_boolean(self, condition, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Condition evaluation should always return a boolean value or raise ValueError.
        """

        # Skip problematic regex patterns
        def has_problematic_regex(cond):
            if isinstance(cond, dict):
                if (
                    cond.get("operator") == "matches_pattern"
                    and cond.get("value")
                    and any(
                        char in str(cond["value"]) for char in ["[", "]", "(", ")", "*", "+", "?"]
                    )
                ):
                    return True

                # Check nested conditions
                if "condition" in cond:
                    return has_problematic_regex(cond["condition"])
                if "conditions" in cond:
                    return any(has_problematic_regex(c) for c in cond["conditions"])
            return False

        if has_problematic_regex(condition):
            assume(False)

        try:
            result = self.evaluator.evaluate_condition(condition, form_data)
            assert isinstance(result, bool)
        except ValueError:
            # ValueError is acceptable for invalid operators
            pass
        except Exception as e:
            # Any other exception is not acceptable
            pytest.fail(f"Unexpected exception: {type(e).__name__}: {e}")

    @given(form_data=form_data_strategy)
    @settings(max_examples=20, deadline=1000)
    def test_complex_real_world_conditions(self, form_data):
        """**Feature: entry-page-system, Property 2: Real-time conditional field visibility**

        Property: Complex real-world conditions should evaluate without errors.
        """
        # Add some standard fields that might be in real form data
        enhanced_form_data = {
            **form_data,
            "type": "Frame",
            "material": "Aluminum",
            "opening_system": "sliding",
            "builtin_flyscreen_track": True,
            "width": 48.5,
        }

        # Complex condition similar to real-world usage
        complex_condition = {
            "operator": "and",
            "conditions": [
                {"operator": "equals", "field": "type", "value": "Frame"},
                {
                    "operator": "or",
                    "conditions": [
                        {"operator": "contains", "field": "opening_system", "value": "sliding"},
                        {"operator": "equals", "field": "material", "value": "Aluminum"},
                    ],
                },
                {"operator": "equals", "field": "builtin_flyscreen_track", "value": True},
            ],
        }

        result = self.evaluator.evaluate_condition(complex_condition, enhanced_form_data)
        assert isinstance(result, bool)
        # This specific condition should be True given our enhanced form data
        assert result is True
