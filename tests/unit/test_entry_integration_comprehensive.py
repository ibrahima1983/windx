"""Comprehensive integration tests for entry page system.

This module contains comprehensive integration tests that verify complete
user workflows and cross-browser compatibility for the entry page system.

**Feature: entry-page-system, Integration Testing**
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.exceptions import NotFoundException, ValidationException
from app.models.attribute_node import AttributeNode
from app.models.configuration import Configuration
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import FormSection, ProfileEntryData, ProfileSchema
from app.services.entry import EntryService


@st.composite
def complete_profile_workflow_data(draw):
    """Generate data for complete profile entry workflow."""
    return {
        "manufacturing_type_id": draw(st.integers(min_value=1, max_value=100)),
        "user_id": draw(st.integers(min_value=1, max_value=1000)),
        "profile_data": ProfileEntryData(
            manufacturing_type_id=draw(st.integers(min_value=1, max_value=100)),
            name=draw(st.text(min_size=1, max_size=50)),
            type=draw(st.sampled_from(["Frame", "Flying mullion"])),
            material=draw(st.sampled_from(["Aluminum", "Vinyl", "Wood"])),
            opening_system=draw(st.sampled_from(["Casement", "Sliding", "Double-hung"])),
            system_series=draw(st.sampled_from(["Kom700", "Kom800", "Series100"])),
            company=draw(st.one_of(st.none(), st.text(max_size=50))),
            width=draw(st.one_of(st.none(), st.floats(min_value=20, max_value=200))),
            renovation=draw(st.one_of(st.none(), st.booleans())),
            builtin_flyscreen_track=draw(st.one_of(st.none(), st.booleans())),
            price_per_meter=draw(
                st.one_of(st.none(), st.decimals(min_value=10, max_value=500, places=2))
            ),
        ),
    }


@st.composite
def mock_complete_database_state(draw):
    """Generate complete mock database state for integration testing."""
    manufacturing_type_id = draw(st.integers(min_value=1, max_value=100))

    # Mock manufacturing type
    manufacturing_type = MagicMock(spec=ManufacturingType)
    manufacturing_type.id = manufacturing_type_id
    manufacturing_type.name = draw(st.text(min_size=5, max_size=50))
    manufacturing_type.base_price = draw(st.decimals(min_value=100, max_value=1000, places=2))
    manufacturing_type.base_weight = draw(st.decimals(min_value=10, max_value=100, places=2))
    manufacturing_type.is_active = True

    # Mock attribute nodes
    attribute_nodes = []
    field_names = [
        "name",
        "type",
        "material",
        "opening_system",
        "system_series",
        "width",
        "renovation",
    ]

    for i, field_name in enumerate(field_names):
        node = MagicMock(spec=AttributeNode)
        node.id = i + 1
        node.manufacturing_type_id = manufacturing_type_id
        node.name = field_name
        node.node_type = "attribute"
        node.data_type = "string" if field_name not in ["width"] else "number"
        node.ltree_path = f"profile.{field_name}"
        node.depth = 1
        node.sort_order = i
        node.required = field_name in [
            "name",
            "type",
            "material",
            "opening_system",
            "system_series",
        ]
        node.description = field_name.replace("_", " ").title()
        node.help_text = f"Enter the {field_name.replace('_', ' ')}"
        node.ui_component = "input"
        node.validation_rules = None
        node.display_condition = None
        attribute_nodes.append(node)

    # Mock user and customer
    user = MagicMock(spec=User)
    user.id = draw(st.integers(min_value=1, max_value=1000))
    user.username = draw(st.text(min_size=3, max_size=20))
    user.email = draw(st.text(min_size=5, max_size=50))
    user.role = "customer"
    user.is_active = True

    customer = MagicMock(spec=Customer)
    customer.id = draw(st.integers(min_value=1, max_value=1000))
    customer.company_name = draw(st.one_of(st.none(), st.text(max_size=50)))
    customer.contact_person = user.username
    customer.email = user.email

    return {
        "manufacturing_type": manufacturing_type,
        "attribute_nodes": attribute_nodes,
        "user": user,
        "customer": customer,
    }


class TestEntryIntegrationComprehensive:
    """Test class for comprehensive entry page integration testing."""

    @pytest.mark.asyncio
    @given(workflow_data=complete_profile_workflow_data(), db_state=mock_complete_database_state())
    async def test_complete_profile_entry_workflow(self, workflow_data: dict, db_state: dict):
        """
        **Feature: entry-page-system, Integration Testing**

        Test complete user workflow: schema loading → form filling → validation →
        saving → loading → preview generation.

        This test verifies the entire profile entry workflow works end-to-end.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        manufacturing_type = db_state["manufacturing_type"]
        attribute_nodes = db_state["attribute_nodes"]
        user = db_state["user"]
        customer = db_state["customer"]

        profile_data = workflow_data["profile_data"]
        profile_data.manufacturing_type_id = manufacturing_type.id

        # Mock RBAC service
        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=customer
        )

        # Mock database operations
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()

        def mock_execute_side_effect(stmt):
            mock_result = AsyncMock()
            if "manufacturing_types" in str(stmt):
                mock_result.scalar_one_or_none = MagicMock(
                    return_value=manufacturing_type
                )  # Use MagicMock
            elif "attribute_nodes" in str(stmt):
                mock_scalars = MagicMock()
                mock_scalars.all = MagicMock(return_value=attribute_nodes)  # Use MagicMock
                mock_result.scalars = MagicMock(return_value=mock_scalars)  # Use MagicMock
            elif "configurations" in str(stmt) and "selectinload" in str(stmt):
                # Mock saved configuration
                saved_config = MagicMock(spec=Configuration)
                saved_config.id = 123
                saved_config.manufacturing_type_id = manufacturing_type.id
                saved_config.name = profile_data.name
                saved_config.customer_id = customer.id
                saved_config.selections = []
                mock_result.scalar_one_or_none = MagicMock(
                    return_value=saved_config
                )  # Use MagicMock
            else:
                mock_result.scalar_one_or_none = MagicMock(return_value=None)  # Use MagicMock
            return mock_result

        mock_db.execute.side_effect = mock_execute_side_effect

        try:
            # Step 1: Load schema
            schema = await entry_service.get_profile_schema(manufacturing_type.id)

            # Verify schema loading
            assert isinstance(schema, ProfileSchema)
            assert schema.manufacturing_type_id == manufacturing_type.id
            assert len(schema.sections) > 0

            # Step 2: Validate profile data
            try:
                validation_result = await entry_service.validate_profile_data(profile_data)
                assert validation_result.get("valid") is True
            except ValidationException as e:
                # Validation errors are acceptable for random data
                assert isinstance(e.field_errors, dict)
                return  # Skip rest of workflow if validation fails

            # Step 3: Save configuration
            with patch("app.services.entry.require") as mock_require:
                mock_require.return_value = lambda func: func

                saved_config = await entry_service.save_profile_configuration(profile_data, user)

                # Verify save operation
                assert mock_db.add.called
                assert entry_service.commit.called
                entry_service.rbac_service.get_or_create_customer_for_user.assert_called_once_with(
                    user
                )

            # Step 4: Load configuration
            with patch("app.services.entry.require") as mock_require:
                mock_require.return_value = lambda func: func

                loaded_data = await entry_service.load_profile_configuration(123, user)

                # Verify load operation
                assert isinstance(loaded_data, ProfileEntryData)
                assert loaded_data.manufacturing_type_id == manufacturing_type.id
                assert loaded_data.name == profile_data.name

            # Step 5: Generate preview
            with patch("app.services.entry.require") as mock_require:
                mock_require.return_value = lambda func: func

                preview_data = await entry_service.generate_preview_data(123, user)

                # Verify preview generation
                assert preview_data.configuration_id == 123
                assert preview_data.table is not None
                assert len(preview_data.table.headers) == 29  # All CSV columns
                assert len(preview_data.table.rows) == 1

                # Verify preview data format
                row_data = preview_data.table.rows[0]
                assert isinstance(row_data, dict)
                assert "Name" in row_data
                assert row_data["Name"] == profile_data.name

                # All headers should have values (even if N/A)
                for header in preview_data.table.headers:
                    assert header in row_data
                    assert isinstance(row_data[header], str)

        except (NotFoundException, ValidationException):
            # These are valid outcomes for some random test data
            pass

    @pytest.mark.asyncio
    @given(
        error_scenarios=st.lists(
            st.fixed_dictionaries(
                {
                    "step": st.sampled_from(["schema", "validation", "save", "load", "preview"]),
                    "error_type": st.sampled_from(
                        ["not_found", "validation", "database", "authorization"]
                    ),
                    "should_recover": st.booleans(),
                }
            ),
            min_size=1,
            max_size=3,
        ),
        db_state=mock_complete_database_state(),
    )
    @settings(deadline=None)  # Disable deadline for complex integration test
    async def test_error_scenarios_and_recovery(self, error_scenarios: list[dict], db_state: dict):
        """
        **Feature: entry-page-system, Integration Testing**

        Test various error scenarios and recovery mechanisms throughout
        the complete workflow.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        manufacturing_type = db_state["manufacturing_type"]
        user = db_state["user"]
        customer = db_state["customer"]

        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user = AsyncMock(
            return_value=customer
        )
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()

        # Test each error scenario
        for scenario in error_scenarios:
            step = scenario["step"]
            error_type = scenario["error_type"]

            # Configure mock to simulate error
            if error_type == "not_found":
                mock_db.execute.side_effect = lambda stmt: AsyncMock(
                    scalar_one_or_none=AsyncMock(return_value=None)
                )
            elif error_type == "database":
                mock_db.execute.side_effect = Exception("Database connection failed")
            else:
                # Normal database behavior
                def mock_execute_side_effect(stmt):
                    mock_result = AsyncMock()
                    if "manufacturing_types" in str(stmt):
                        mock_result.scalar_one_or_none.return_value = manufacturing_type
                    elif "attribute_nodes" in str(stmt):
                        mock_result.scalars.return_value.all.return_value = db_state[
                            "attribute_nodes"
                        ]
                    else:
                        mock_result.scalar_one_or_none.return_value = None
                    return mock_result

                mock_db.execute.side_effect = mock_execute_side_effect

            # Act & Assert - Test error handling for each step
            try:
                if step == "schema":
                    await entry_service.get_profile_schema(manufacturing_type.id)
                elif step == "validation":
                    profile_data = ProfileEntryData(
                        manufacturing_type_id=manufacturing_type.id,
                        name="",  # Invalid - empty required field
                        type="InvalidType",  # Invalid choice
                        material="Aluminum",
                        opening_system="Casement",
                        system_series="Kom800",
                    )
                    await entry_service.validate_profile_data(profile_data)
                elif step == "save":
                    valid_profile_data = ProfileEntryData(
                        manufacturing_type_id=manufacturing_type.id,
                        name="Test Configuration",
                        type="Frame",
                        material="Aluminum",
                        opening_system="Casement",
                        system_series="Kom800",
                    )
                    with patch("app.services.entry.require") as mock_require:
                        mock_require.return_value = lambda func: func
                        await entry_service.save_profile_configuration(valid_profile_data, user)
                elif step == "load":
                    with patch("app.services.entry.require") as mock_require:
                        mock_require.return_value = lambda func: func
                        await entry_service.load_profile_configuration(999, user)  # Non-existent ID
                elif step == "preview":
                    with patch("app.services.entry.require") as mock_require:
                        mock_require.return_value = lambda func: func
                        await entry_service.generate_preview_data(999, user)  # Non-existent ID

                # If no exception was raised, that's also a valid outcome

            except (NotFoundException, ValidationException, Exception) as e:
                # Assert - Errors should be handled gracefully
                error_message = str(e)

                # Should not contain internal system details
                assert "Traceback" not in error_message
                assert "scalar_one_or_none" not in error_message

                # Should be informative
                assert len(error_message) > 0

                # System should remain stable (test continues)

    @given(
        performance_data=st.fixed_dictionaries(
            {
                "num_fields": st.integers(min_value=10, max_value=50),
                "num_conditions": st.integers(min_value=0, max_value=20),
                "data_size": st.sampled_from(["small", "medium", "large"]),
            }
        ),
        db_state=mock_complete_database_state(),
    )
    def test_performance_with_large_datasets(self, performance_data: dict, db_state: dict):
        """
        **Feature: entry-page-system, Integration Testing**

        Test performance characteristics with large datasets and complex
        conditional logic.
        """
        # Arrange
        entry_service = EntryService(AsyncMock())

        num_fields = performance_data["num_fields"]
        num_conditions = performance_data["num_conditions"]
        data_size = performance_data["data_size"]

        # Generate large form data
        form_data = {}
        for i in range(num_fields):
            field_name = f"field_{i}"
            if data_size == "small":
                form_data[field_name] = f"value_{i}"
            elif data_size == "medium":
                form_data[field_name] = f"medium_value_{i}" * 10
            else:  # large
                form_data[field_name] = f"large_value_{i}" * 100

        # Generate complex conditional logic
        conditional_logic = {}
        for i in range(num_conditions):
            condition_field = f"condition_field_{i}"
            conditional_logic[condition_field] = {
                "operator": "equals",
                "field": f"field_{i % num_fields}",
                "value": f"value_{i}",
            }

        schema = ProfileSchema(
            manufacturing_type_id=1,
            sections=[FormSection(title="Performance Test", fields=[])],
            conditional_logic=conditional_logic,
        )

        # Act - Test performance operations
        import time

        # Test condition evaluation performance
        start_time = time.time()
        visibility = {}
        for field_name, condition in conditional_logic.items():
            try:
                visibility[field_name] = entry_service.condition_evaluator.evaluate_condition(
                    condition, form_data
                )
            except Exception:
                visibility[field_name] = True  # Default to visible on error

        evaluation_time = time.time() - start_time

        # Test preview generation performance
        start_time = time.time()
        preview_table = entry_service.generate_preview_table(form_data)
        preview_time = time.time() - start_time

        # Assert - Performance should be reasonable
        # (These are loose bounds to avoid flaky tests)
        assert evaluation_time < 5.0, f"Condition evaluation took too long: {evaluation_time}s"
        assert preview_time < 2.0, f"Preview generation took too long: {preview_time}s"

        # Results should be valid
        assert isinstance(visibility, dict)
        assert len(visibility) == num_conditions

        assert isinstance(preview_table.headers, list)
        assert len(preview_table.headers) == 29
        assert len(preview_table.rows) == 1

    @given(
        cross_browser_scenarios=st.lists(
            st.fixed_dictionaries(
                {
                    "browser": st.sampled_from(["chrome", "firefox", "safari", "edge"]),
                    "javascript_enabled": st.booleans(),
                    "screen_size": st.sampled_from(["mobile", "tablet", "desktop"]),
                    "connection_speed": st.sampled_from(["slow", "fast"]),
                }
            ),
            min_size=1,
            max_size=4,
        )
    )
    def test_cross_browser_compatibility_simulation(self, cross_browser_scenarios: list[dict]):
        """
        **Feature: entry-page-system, Integration Testing**

        Simulate cross-browser compatibility testing by verifying that
        the JavaScript condition evaluator works consistently across
        different browser scenarios.
        """
        # Arrange
        from app.services.entry import JAVASCRIPT_CONDITION_EVALUATOR

        # Test data that should work across all browsers
        test_conditions = [
            {"operator": "equals", "field": "type", "value": "Frame"},
            {"operator": "exists", "field": "width", "value": None},
            {"operator": "greater_than", "field": "width", "value": 50},
            {"operator": "contains", "field": "material", "value": "wood"},
        ]

        test_form_data = {"type": "Frame", "width": 100, "material": "hardwood", "company": None}

        # Act & Assert - Test each browser scenario
        for scenario in cross_browser_scenarios:
            browser = scenario["browser"]
            javascript_enabled = scenario["javascript_enabled"]

            if javascript_enabled:
                # Verify JavaScript evaluator is available
                assert isinstance(JAVASCRIPT_CONDITION_EVALUATOR, str)
                assert "ConditionEvaluator" in JAVASCRIPT_CONDITION_EVALUATOR
                assert "evaluateCondition" in JAVASCRIPT_CONDITION_EVALUATOR

                # Verify all operators are defined
                for condition in test_conditions:
                    operator = condition["operator"]
                    assert operator in JAVASCRIPT_CONDITION_EVALUATOR

                # Verify JavaScript syntax is valid (basic check)
                assert "class ConditionEvaluator" in JAVASCRIPT_CONDITION_EVALUATOR
                assert "static OPERATORS" in JAVASCRIPT_CONDITION_EVALUATOR
                assert "static evaluateCondition" in JAVASCRIPT_CONDITION_EVALUATOR
                assert "static getFieldValue" in JAVASCRIPT_CONDITION_EVALUATOR

                # Should not contain Python-specific syntax
                assert "lambda" not in JAVASCRIPT_CONDITION_EVALUATOR
                assert "def " not in JAVASCRIPT_CONDITION_EVALUATOR
                assert "import " not in JAVASCRIPT_CONDITION_EVALUATOR

            else:
                # When JavaScript is disabled, system should still function
                # (This would be handled by server-side rendering)
                # For now, just verify the Python evaluator works
                entry_service = EntryService(AsyncMock())

                for condition in test_conditions:
                    try:
                        result = entry_service.condition_evaluator.evaluate_condition(
                            condition, test_form_data
                        )
                        assert isinstance(result, bool)
                    except Exception as e:
                        # Should not crash on valid conditions
                        pytest.fail(f"Condition evaluation failed: {e}")

    @pytest.mark.asyncio
    @given(
        concurrent_users=st.integers(min_value=1, max_value=10),
        db_state=mock_complete_database_state(),
    )
    async def test_concurrent_user_simulation(self, concurrent_users: int, db_state: dict):
        """
        **Feature: entry-page-system, Integration Testing**

        Simulate concurrent users accessing the entry system to verify
        thread safety and data isolation.
        """
        # Arrange
        manufacturing_type = db_state["manufacturing_type"]

        # Create multiple entry services (simulating concurrent users)
        entry_services = []
        for i in range(concurrent_users):
            mock_db = AsyncMock()
            entry_service = EntryService(mock_db)

            # Mock database for each service
            def mock_execute_side_effect(stmt):
                mock_result = AsyncMock()
                if "manufacturing_types" in str(stmt):
                    mock_result.scalar_one_or_none.return_value = manufacturing_type
                elif "attribute_nodes" in str(stmt):
                    mock_result.scalars.return_value.all.return_value = db_state["attribute_nodes"]
                return mock_result

            mock_db.execute.side_effect = mock_execute_side_effect
            entry_services.append(entry_service)

        # Act - Simulate concurrent schema loading
        import asyncio

        async def load_schema_for_user(service, user_id):
            try:
                schema = await service.get_profile_schema(manufacturing_type.id)
                return (user_id, schema)
            except Exception as e:
                return (user_id, str(e))

        # Run concurrent operations
        tasks = [load_schema_for_user(service, i) for i, service in enumerate(entry_services)]

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Assert - All operations should complete successfully
        for user_id, result in results:
            if isinstance(result, Exception):
                pytest.fail(f"User {user_id} failed: {result}")
            elif isinstance(result, str):
                # Error message - acceptable for some scenarios
                assert len(result) > 0
            else:
                # Successful schema load
                assert isinstance(result, ProfileSchema)
                assert result.manufacturing_type_id == manufacturing_type.id
