"""Property-based tests for entry page data persistence.

This module contains property-based tests that verify configuration data
persistence works correctly for the entry page system.

Property 7: Configuration data persistence
- For any valid profile data submission, the system should create proper
  Configuration and ConfigurationSelection records that can be accurately
  retrieved and restored to the form
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from app.core.rbac import Role
from app.models.attribute_node import AttributeNode
from app.models.configuration import Configuration
from app.models.configuration_selection import ConfigurationSelection
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import ProfileEntryData
from app.services.entry import EntryService


@st.composite
def manufacturing_type_data(draw):
    """Generate manufacturing type data for testing."""
    return ManufacturingType(
        id=draw(st.integers(min_value=1, max_value=1000)),
        name=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.text(min_size=1, max_size=200)),
        base_price=draw(st.decimals(min_value=1, max_value=1000, places=2)),
        base_weight=draw(st.decimals(min_value=1, max_value=100, places=2)),
        is_active=True,
    )


@st.composite
def attribute_node_data(draw, manufacturing_type_id):
    """Generate attribute node data for testing."""
    field_names = [
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

    nodes = []
    for i, field_name in enumerate(field_names):
        node = AttributeNode(
            id=i + 1,
            manufacturing_type_id=manufacturing_type_id,
            name=field_name,
            node_type="attribute",
            data_type=draw(st.sampled_from(["string", "number", "boolean"])),
            ltree_path=f"section.{field_name}",
            depth=2,
            sort_order=i,
        )
        nodes.append(node)

    return nodes


@st.composite
def user_data(draw):
    """Generate user data for testing."""
    return User(
        id=draw(st.integers(min_value=1, max_value=1000)),
        email=draw(st.emails()),
        username=draw(st.text(min_size=1, max_size=50)),
        role=draw(st.sampled_from([Role.CUSTOMER.value, Role.SALESMAN.value, Role.PARTNER.value])),
        is_active=True,
    )


@st.composite
def customer_data(draw, user_id):
    """Generate customer data for testing."""
    return Customer(
        id=draw(st.integers(min_value=1, max_value=1000)),
        company_name=draw(st.text(min_size=1, max_size=100)),
        contact_person=draw(st.text(min_size=1, max_size=100)),
        email=draw(st.emails()),
        phone=draw(st.text(min_size=10, max_size=20)),
        address={"street": "123 Test St", "city": "Test City"},
        customer_type="individual",
        is_active=True,
    )


@st.composite
def profile_entry_data(draw, manufacturing_type_id):
    """Generate valid profile entry data for testing."""
    return ProfileEntryData(
        manufacturing_type_id=manufacturing_type_id,
        name=draw(st.text(min_size=1, max_size=100)),
        type=draw(st.sampled_from(["Frame", "Flying mullion"])),
        company=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        material=draw(st.sampled_from(["Aluminum", "Vinyl", "Wood"])),
        opening_system=draw(st.sampled_from(["Casement", "Sliding", "Double-hung"])),
        system_series=draw(st.sampled_from(["Kom800", "Series100", "Premium"])),
        code=draw(st.one_of(st.none(), st.text(min_size=1, max_size=20))),
        length_of_beam=draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0))),
        renovation=draw(st.one_of(st.none(), st.booleans())),
        width=draw(st.one_of(st.none(), st.floats(min_value=10.0, max_value=200.0))),
        builtin_flyscreen_track=draw(st.one_of(st.none(), st.booleans())),
        total_width=draw(st.one_of(st.none(), st.floats(min_value=10.0, max_value=250.0))),
        flyscreen_track_height=draw(
            st.one_of(st.none(), st.floats(min_value=5.0, max_value=100.0))
        ),
        front_height=draw(st.one_of(st.none(), st.floats(min_value=20.0, max_value=300.0))),
        rear_height=draw(st.one_of(st.none(), st.floats(min_value=20.0, max_value=300.0))),
        glazing_height=draw(st.one_of(st.none(), st.floats(min_value=15.0, max_value=250.0))),
        renovation_height=draw(st.one_of(st.none(), st.floats(min_value=15.0, max_value=250.0))),
        glazing_undercut_height=draw(
            st.one_of(st.none(), st.floats(min_value=10.0, max_value=200.0))
        ),
        pic=draw(st.one_of(st.none(), st.text(min_size=1, max_size=100))),
        sash_overlap=draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=10.0))),
        flying_mullion_horizontal_clearance=draw(
            st.one_of(st.none(), st.floats(min_value=0.1, max_value=5.0))
        ),
        flying_mullion_vertical_clearance=draw(
            st.one_of(st.none(), st.floats(min_value=0.1, max_value=5.0))
        ),
        steel_material_thickness=draw(
            st.one_of(st.none(), st.floats(min_value=0.5, max_value=5.0))
        ),
        weight_per_meter=draw(st.one_of(st.none(), st.floats(min_value=0.1, max_value=20.0))),
        reinforcement_steel=draw(
            st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=50), min_size=1, max_size=3))
        ),
        colours=draw(
            st.one_of(st.none(), st.lists(st.text(min_size=1, max_size=20), min_size=1, max_size=5))
        ),
        price_per_meter=draw(
            st.one_of(st.none(), st.decimals(min_value=1, max_value=500, places=2))
        ),
        price_per_beam=draw(
            st.one_of(st.none(), st.decimals(min_value=10, max_value=2000, places=2))
        ),
        upvc_profile_discount=draw(st.one_of(st.none(), st.floats(min_value=0.0, max_value=50.0))),
    )


class TestEntryDataPersistence:
    """Test class for entry page data persistence properties."""

    @pytest.mark.asyncio
    @given(
        user=user_data(),
        manufacturing_type=manufacturing_type_data(),
        profile_data=profile_entry_data(1),  # Use fixed ID for simplicity
    )
    @settings(max_examples=100, deadline=None)
    async def test_property_configuration_data_persistence(
        self, user: User, manufacturing_type: ManufacturingType, profile_data: ProfileEntryData
    ):
        """
        **Feature: entry-page-system, Property 7: Configuration data persistence**

        Property: For any valid profile data submission, the system should create proper
        Configuration and ConfigurationSelection records that can be accurately retrieved
        and restored to the form.

        This property ensures that all data saved through the entry service can be
        round-tripped without loss, maintaining data integrity throughout the save/load cycle.
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Set manufacturing type ID to match profile data
        manufacturing_type.id = profile_data.manufacturing_type_id

        # Create fixed attribute nodes for testing
        attribute_nodes = [
            AttributeNode(
                id=i + 1,
                manufacturing_type_id=profile_data.manufacturing_type_id,
                name=field_name,
                node_type="attribute",
                data_type="string",
                ltree_path=f"section.{field_name}",
                depth=2,
                sort_order=i,
            )
            for i, field_name in enumerate(
                [
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
            )
        ]

        # Mock manufacturing type lookup and attribute nodes query
        def mock_execute_side_effect(stmt):
            mock_result = MagicMock()
            if "manufacturing_types" in str(stmt):
                mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
            elif "attribute_nodes" in str(stmt):
                mock_scalars = MagicMock()
                mock_scalars.all = MagicMock(return_value=attribute_nodes)
                mock_result.scalars = MagicMock(return_value=mock_scalars)
            return mock_result

        mock_db.execute.side_effect = mock_execute_side_effect

        # Mock customer creation
        customer = Customer(
            id=1,
            company_name="Test Company",
            contact_person="Test Person",
            email="test@example.com",
            phone="1234567890",
            address={"street": "123 Test St", "city": "Test City"},
            customer_type="individual",
            is_active=True,
        )
        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user.return_value = customer

        # Mock configuration creation
        created_config = Configuration(
            id=1,
            manufacturing_type_id=profile_data.manufacturing_type_id,
            customer_id=customer.id,
            name=profile_data.name,
            description=f"Profile entry for {profile_data.type}",
            status="draft",
            base_price=manufacturing_type.base_price,
            total_price=manufacturing_type.base_price,
            calculated_weight=manufacturing_type.base_weight,
            calculated_technical_data={},
        )

        # Mock database operations
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()
        mock_db.add = MagicMock()

        # Mock validation (assume it passes)
        entry_service.validate_profile_data = AsyncMock(return_value={"valid": True})

        # Act - Save configuration
        result = await entry_service.save_profile_configuration(profile_data, user)

        # Assert - Verify save operations were called correctly
        assert entry_service.validate_profile_data.called
        assert entry_service.rbac_service.get_or_create_customer_for_user.called
        assert mock_db.add.called
        assert entry_service.commit.called

        # Verify configuration data structure
        # The actual configuration object would be created and added to the database
        # We verify the service was called with correct parameters
        add_calls = mock_db.add.call_args_list
        assert len(add_calls) >= 1  # At least configuration was added

        # Mock load operation
        created_config.selections = []
        form_data = profile_data.model_dump(exclude={"manufacturing_type_id", "name"})

        # Create mock selections for non-null fields
        for field_name, field_value in form_data.items():
            if field_value is not None:
                # Find matching attribute node
                matching_node = next(
                    (node for node in attribute_nodes if node.name == field_name), None
                )
                if matching_node:
                    selection = ConfigurationSelection(
                        id=len(created_config.selections) + 1,
                        configuration_id=created_config.id,
                        attribute_node_id=matching_node.id,
                        selection_path=matching_node.ltree_path,
                    )

                    # Set appropriate value field
                    if isinstance(field_value, bool):
                        selection.boolean_value = field_value
                    elif isinstance(field_value, (int, float)):
                        selection.numeric_value = field_value
                    elif isinstance(field_value, (list, dict)):
                        selection.json_value = field_value
                    else:
                        selection.string_value = str(field_value)

                    created_config.selections.append(selection)

        # Mock load configuration
        mock_load_result = MagicMock()
        mock_load_result.scalar_one_or_none = MagicMock(return_value=created_config)

        # Create a separate mock for the load operation
        def mock_load_execute(stmt):
            return mock_load_result

        # Update mock_db.execute to handle load operation
        mock_db.execute = MagicMock(side_effect=mock_load_execute)

        # Act - Load configuration
        loaded_data = await entry_service.load_profile_configuration(created_config.id, user)

        # Assert - Verify round-trip data integrity
        assert loaded_data.manufacturing_type_id == profile_data.manufacturing_type_id
        assert loaded_data.name == profile_data.name
        assert loaded_data.type == profile_data.type
        assert loaded_data.material == profile_data.material
        assert loaded_data.opening_system == profile_data.opening_system
        assert loaded_data.system_series == profile_data.system_series

        # Verify all non-null fields are preserved
        original_data = profile_data.model_dump()
        loaded_data_dict = loaded_data.model_dump()

        for field_name, original_value in original_data.items():
            if original_value is not None:
                loaded_value = loaded_data_dict.get(field_name)
                # Allow for type conversions (e.g., float to Decimal)
                if isinstance(original_value, (int, float)) and isinstance(
                    loaded_value, (int, float)
                ):
                    assert abs(float(original_value) - float(loaded_value)) < 0.01
                else:
                    assert loaded_value == original_value, (
                        f"Field {field_name}: {loaded_value} != {original_value}"
                    )

    @pytest.mark.asyncio
    @given(
        user=user_data(),
        manufacturing_type=manufacturing_type_data(),
        profile_data=profile_entry_data(1),
    )
    @settings(max_examples=50, deadline=None)
    async def test_property_configuration_selection_mapping(
        self, user: User, manufacturing_type: ManufacturingType, profile_data: ProfileEntryData
    ):
        """
        Property: For any profile data with multiple field types, the system should
        correctly map each field to its corresponding attribute node and store values
        in the appropriate ConfigurationSelection field (string_value, numeric_value,
        boolean_value, json_value).
        """
        # Arrange
        mock_db = AsyncMock()
        entry_service = EntryService(mock_db)

        # Mock manufacturing type and attribute nodes
        manufacturing_type.id = profile_data.manufacturing_type_id

        # Create fixed attribute nodes for testing
        attribute_nodes = [
            AttributeNode(
                id=i + 1,
                manufacturing_type_id=profile_data.manufacturing_type_id,
                name=field_name,
                node_type="attribute",
                data_type="string",
                ltree_path=f"section.{field_name}",
                depth=2,
                sort_order=i,
            )
            for i, field_name in enumerate(
                [
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
            )
        ]

        # Set up mocks
        mock_result = MagicMock()
        mock_result.scalar_one_or_none = MagicMock(return_value=manufacturing_type)
        mock_scalars = MagicMock()
        mock_scalars.all = MagicMock(return_value=attribute_nodes)
        mock_result.scalars = MagicMock(return_value=mock_scalars)
        mock_db.execute = MagicMock(return_value=mock_result)

        customer = Customer(
            id=1,
            company_name="Test Company",
            contact_person="Test Person",
            email="test@example.com",
            phone="1234567890",
            address={"street": "123 Test St", "city": "Test City"},
            customer_type="individual",
            is_active=True,
        )
        entry_service.rbac_service = AsyncMock()
        entry_service.rbac_service.get_or_create_customer_for_user.return_value = customer
        entry_service.validate_profile_data = AsyncMock(return_value={"valid": True})
        entry_service.commit = AsyncMock()
        entry_service.refresh = AsyncMock()

        # Track what gets added to the database
        added_objects = []
        mock_db.add = MagicMock(side_effect=lambda obj: added_objects.append(obj))

        # Act
        await entry_service.save_profile_configuration(profile_data, user)

        # Assert - Verify correct field mapping and value storage
        configuration_selections = [
            obj for obj in added_objects if isinstance(obj, ConfigurationSelection)
        ]

        form_data = profile_data.model_dump(exclude={"manufacturing_type_id", "name"})
        non_null_fields = {k: v for k, v in form_data.items() if v is not None}

        # Should have created selections for all non-null fields that have matching attribute nodes
        field_to_node = {node.name: node for node in attribute_nodes}
        expected_selections = {k: v for k, v in non_null_fields.items() if k in field_to_node}

        assert len(configuration_selections) == len(expected_selections)

        # Verify each selection has correct attribute node mapping and value storage
        for selection in configuration_selections:
            # Find the corresponding field
            node = next(node for node in attribute_nodes if node.id == selection.attribute_node_id)
            field_name = node.name
            original_value = expected_selections[field_name]

            # Verify correct value field is used
            if isinstance(original_value, bool):
                assert selection.boolean_value == original_value
                assert selection.string_value is None
                assert selection.numeric_value is None
                assert selection.json_value is None
            elif isinstance(original_value, (int, float)):
                assert selection.numeric_value == original_value
                assert selection.string_value is None
                assert selection.boolean_value is None
                assert selection.json_value is None
            elif isinstance(original_value, (list, dict)):
                assert selection.json_value == original_value
                assert selection.string_value is None
                assert selection.numeric_value is None
                assert selection.boolean_value is None
            else:
                assert selection.string_value == str(original_value)
                assert selection.numeric_value is None
                assert selection.boolean_value is None
                assert selection.json_value is None

            # Verify ltree path is set correctly
            assert selection.selection_path == node.ltree_path
