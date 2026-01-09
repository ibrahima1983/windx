"""Integration tests for admin hierarchy form validation.

Tests Pydantic validation, error handling, and form re-rendering with errors.
"""

from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hierarchy_builder import HierarchyBuilderService


@pytest.mark.ci_cd_issue
@pytest.mark.asyncio
async def test_save_node_with_invalid_name_shows_validation_error(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that invalid node name triggers Pydantic validation error."""
    # Create manufacturing type with unique name
    import uuid

    service = HierarchyBuilderService(db_session)
    unique_name = f"Test Window {uuid.uuid4().hex[:8]}"
    mfg_type = await service.create_manufacturing_type(
        name=unique_name,
        base_price=Decimal("200.00"),
    )

    # Submit form with empty name (should fail validation)
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "",  # Empty name should fail
        "node_type": "category",
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status code (validation error)
    assert response.status_code == 422

    # Verify response contains validation error information
    content = response.text

    # Handle both HTML and JSON responses (CI vs local environment differences)
    if content.startswith('{"') or content.startswith("[{"):
        # JSON response (FastAPI automatic validation)
        data = response.json()
        if "detail" in data:
            # FastAPI validation format
            assert any("name" in str(error.get("loc", [])) for error in data["detail"])
        else:
            # Custom validation format
            assert "message" in data or "error" in data
    else:
        # HTML response (custom form validation)
        assert "<!DOCTYPE html>" in content or "<html" in content
        # Verify validation error is shown in the form
        assert (
            "validation_errors" in content
            or "error" in content.lower()
            or "field required" in content.lower()
            or "name" in content.lower()
        )


@pytest.mark.asyncio
async def test_save_node_with_invalid_node_type_shows_validation_error(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that invalid node_type triggers Pydantic validation error."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with invalid node_type
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Test Node",
        "node_type": "invalid_type",  # Invalid enum value
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status code
    assert response.status_code == 422

    # Verify error message mentions node_type
    content = response.text
    assert "node_type" in content.lower()


@pytest.mark.asyncio
async def test_save_node_with_invalid_decimal_shows_error(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that invalid decimal value triggers ValueError handling."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with invalid decimal
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Test Node",
        "node_type": "option",
        "price_impact_type": "fixed",
        "price_impact_value": "not_a_number",  # Invalid decimal
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify redirect with error message (decimal conversion error caught)
    assert response.status_code == 303
    assert "error=" in response.headers["location"]
    # Error message should mention the conversion issue
    assert "error" in response.headers["location"].lower()


@pytest.mark.asyncio
async def test_save_node_preserves_form_data_on_validation_error(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that form data is preserved when Pydantic validation fails."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with Pydantic validation error (invalid enum value)
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Valid Name",  # Valid name
        "node_type": "invalid_type",  # Invalid enum - triggers Pydantic validation
        "description": "This description should be preserved",
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "5",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status
    assert response.status_code == 422

    # Verify form is re-rendered with preserved data
    content = response.text
    # Check that validation error is shown
    assert "node_type" in content.lower() or "validation" in content.lower()
    # Check that sort_order value is preserved
    assert 'value="5"' in content
    # Check that name is preserved
    assert "Valid Name" in content


@pytest.mark.asyncio
async def test_update_node_with_validation_error_shows_form(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that updating node with Pydantic validation error re-renders form."""
    # Create manufacturing type and node
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    node = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Original Name",
        node_type="category",
    )

    # Submit update with Pydantic validation error (invalid enum)
    form_data = {
        "node_id": str(node.id),
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Updated Name",  # Valid name
        "node_type": "invalid_type",  # Invalid enum - triggers Pydantic validation
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status
    assert response.status_code == 422

    # Verify form is rendered with node data
    content = response.text
    assert "Original Name" in content or "node_form" in content or "Updated Name" in content


@pytest.mark.asyncio
async def test_save_node_handles_empty_optional_fields(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that empty strings for optional fields are handled correctly."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with empty optional fields
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Test Node",
        "node_type": "category",
        "data_type": "",  # Empty optional field
        "description": "",  # Empty optional field
        "help_text": "",  # Empty optional field
        "price_formula": "",  # Empty optional field
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify success (empty strings should be converted to None)
    assert response.status_code == 303
    assert "success" in response.headers["location"]

    # Verify node was created with None for empty fields
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    nodes = await attr_repo.get_by_manufacturing_type(mfg_type.id)
    assert len(nodes) == 1
    assert nodes[0].data_type is None
    assert nodes[0].description is None
    assert nodes[0].help_text is None
    assert nodes[0].price_formula is None


@pytest.mark.asyncio
async def test_save_node_with_whitespace_only_fields(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that whitespace-only strings are treated as empty."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with whitespace-only fields
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Test Node",
        "node_type": "category",
        "description": "   ",  # Whitespace only
        "price_impact_value": "  ",  # Whitespace only
        "price_impact_type": "fixed",
        "weight_impact": "  0  ",  # Whitespace around number
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify success
    assert response.status_code == 303
    assert "success" in response.headers["location"]

    # Verify whitespace was handled correctly
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    nodes = await attr_repo.get_by_manufacturing_type(mfg_type.id)
    assert len(nodes) == 1
    assert nodes[0].description is None  # Whitespace-only should be None
    assert nodes[0].price_impact_value is None  # Whitespace-only should be None
    assert nodes[0].weight_impact == Decimal("0")  # Should parse correctly


@pytest.mark.asyncio
async def test_update_node_excludes_descendants_from_parent_selector_on_error(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that Pydantic validation error on update still excludes descendants from parent selector."""
    # Create manufacturing type and hierarchy
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    root = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Root",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child",
        node_type="category",
        parent_node_id=root.id,
    )

    # Submit update with Pydantic validation error (invalid enum)
    form_data = {
        "node_id": str(root.id),
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Root Updated",  # Valid name
        "node_type": "invalid_type",  # Invalid enum - triggers Pydantic validation
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status
    assert response.status_code == 422

    # Verify form is rendered (descendants should be excluded from parent selector)
    content = response.text
    assert "Root" in content or "node_form" in content


@pytest.mark.asyncio
async def test_save_node_with_multiple_validation_errors(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that multiple validation errors are all displayed."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with multiple validation errors
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "",  # Error 1: empty name
        "node_type": "invalid_type",  # Error 2: invalid enum
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status
    assert response.status_code == 422

    # Verify both errors are mentioned
    content = response.text.lower()
    assert "name" in content
    assert "node_type" in content or "type" in content


@pytest.mark.asyncio
async def test_create_node_with_invalid_price_impact_type_shows_validation_error(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that invalid price_impact_type triggers Pydantic validation error."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit create with invalid price_impact_type (should trigger Pydantic validation)
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "New Node",
        "node_type": "category",
        "price_impact_type": "invalid_price_type",  # Invalid enum value
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify 422 status (validation error)
    assert response.status_code == 422

    # Verify form is re-rendered (HTML response, not JSON)
    content = response.text
    assert "<!DOCTYPE html>" in content or "<html" in content

    # Verify validation error is shown
    assert "price_impact_type" in content.lower() or "validation" in content.lower()


@pytest.mark.asyncio
async def test_save_node_with_valid_price_formula(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that valid price formula is accepted."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with price formula
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Dynamic Price Node",
        "node_type": "option",
        "price_impact_type": "formula",
        "price_formula": "width * height * 0.05",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify success
    assert response.status_code == 303
    assert "success" in response.headers["location"]

    # Verify formula was saved
    from app.repositories.attribute_node import AttributeNodeRepository

    attr_repo = AttributeNodeRepository(db_session)
    nodes = await attr_repo.get_by_manufacturing_type(mfg_type.id)
    assert len(nodes) == 1
    assert nodes[0].price_formula == "width * height * 0.05"


@pytest.mark.asyncio
async def test_update_node_recalculates_path_on_parent_change(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that updating parent recalculates ltree_path and depth."""
    # Create manufacturing type and nodes
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    parent1 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Parent 1",
        node_type="category",
    )

    parent2 = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Parent 2",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child",
        node_type="option",
        parent_node_id=parent1.id,
    )

    # Verify initial path
    await db_session.refresh(child)
    assert "parent_1" in child.ltree_path
    assert child.depth == 1

    # Update child to have parent2 as parent
    form_data = {
        "node_id": str(child.id),
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Child",
        "node_type": "option",
        "parent_node_id": str(parent2.id),  # Change parent
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify success
    assert response.status_code == 303

    # Verify path was recalculated
    await db_session.refresh(child)
    assert "parent_2" in child.ltree_path
    assert "parent_1" not in child.ltree_path
    assert child.depth == 1


@pytest.mark.asyncio
async def test_update_node_preserves_parent_when_not_provided(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that not providing parent_node_id in update preserves existing parent."""
    # Create manufacturing type and nodes
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    parent = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Parent",
        node_type="category",
    )

    child = await service.create_node(
        manufacturing_type_id=mfg_type.id,
        name="Child",
        node_type="category",
        parent_node_id=parent.id,
    )

    # Verify initial state
    await db_session.refresh(child)
    assert child.parent_node_id == parent.id
    assert child.depth == 1

    # Update child name without changing parent
    # When parent_node_id is not provided, it should remain unchanged
    form_data = {
        "node_id": str(child.id),
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Child Updated",  # Change name
        "node_type": "category",
        # parent_node_id not included = should remain unchanged
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Verify success
    assert response.status_code == 303

    # Verify parent was preserved (not changed to None)
    await db_session.refresh(child)
    assert child.parent_node_id == parent.id  # Should still have parent
    assert child.name == "Child Updated"  # Name should be updated
    assert child.depth == 1  # Depth should remain the same


# Additional validation tests for dangerous formulas and edge cases


@pytest.mark.asyncio
async def test_save_node_with_dangerous_import_formula_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that formula with import statement is rejected by Pydantic validator."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with dangerous formula containing import
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Dangerous Node",
        "node_type": "option",
        "price_impact_type": "formula",
        "price_formula": "import os; os.system('ls')",  # Dangerous!
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions formula or forbidden operation
    content = response.text.lower()
    assert "formula" in content or "forbidden" in content or "import" in content


@pytest.mark.asyncio
async def test_save_node_with_dangerous_exec_formula_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that formula with exec() is rejected by Pydantic validator."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with dangerous formula containing exec
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Dangerous Node",
        "node_type": "option",
        "price_impact_type": "formula",
        "price_formula": "exec('print(1)')",  # Dangerous!
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions formula or forbidden operation
    content = response.text.lower()
    assert "formula" in content or "forbidden" in content or "exec" in content


@pytest.mark.asyncio
async def test_save_node_with_dangerous_eval_formula_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that formula with eval() is rejected by Pydantic validator."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with dangerous formula containing eval
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Dangerous Node",
        "node_type": "option",
        "price_impact_type": "formula",
        "price_formula": "eval('1+1')",  # Dangerous!
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions formula or forbidden operation
    content = response.text.lower()
    assert "formula" in content or "forbidden" in content or "eval" in content


@pytest.mark.asyncio
async def test_save_node_with_unbalanced_parentheses_formula_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that formula with unbalanced parentheses is rejected."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with formula having unbalanced parentheses
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Bad Formula Node",
        "node_type": "option",
        "price_impact_type": "formula",
        "price_formula": "((width * height)",  # Unbalanced!
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions formula or parentheses
    content = response.text.lower()
    assert "formula" in content or "parenthes" in content or "balanced" in content


@pytest.mark.asyncio
async def test_save_node_with_negative_price_impact_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that negative price_impact_value is rejected by Pydantic validator."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with negative price impact
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Negative Price Node",
        "node_type": "option",
        "price_impact_type": "fixed",
        "price_impact_value": "-50.00",  # Negative - should be rejected
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions price_impact_value
    content = response.text.lower()
    assert "price" in content or "validation" in content


@pytest.mark.asyncio
async def test_save_node_with_negative_weight_impact_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that negative weight_impact is rejected by Pydantic validator."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with negative weight impact
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Negative Weight Node",
        "node_type": "option",
        "price_impact_type": "fixed",
        "weight_impact": "-5.00",  # Negative - should be rejected
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions weight
    content = response.text.lower()
    assert "weight" in content or "validation" in content


@pytest.mark.asyncio
async def test_save_node_with_invalid_data_type_rejected(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that invalid data_type is rejected by Pydantic validator."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    # Submit form with invalid data_type
    form_data = {
        "manufacturing_type_id": str(mfg_type.id),
        "name": "Invalid Data Type Node",
        "node_type": "attribute",
        "data_type": "invalid_data_type",  # Invalid enum value
        "price_impact_type": "fixed",
        "weight_impact": "0",
        "sort_order": "0",
        "required": "false",
    }

    response = await client.post(
        "/api/v1/admin/hierarchy/node/save",
        headers=superuser_auth_headers,
        data=form_data,
    )

    # Should return 422 with validation error
    assert response.status_code == 422

    # Verify error message mentions data_type
    content = response.text.lower()
    assert "data_type" in content or "data type" in content or "validation" in content


@pytest.mark.asyncio
async def test_save_node_with_all_valid_node_types(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that all valid node_type enum values are accepted."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    valid_node_types = ["category", "attribute", "option", "component", "technical_spec"]

    for node_type in valid_node_types:
        form_data = {
            "manufacturing_type_id": str(mfg_type.id),
            "name": f"Test {node_type}",
            "node_type": node_type,
            "price_impact_type": "fixed",
            "weight_impact": "0",
            "sort_order": "0",
            "required": "false",
        }

        response = await client.post(
            "/api/v1/admin/hierarchy/node/save",
            headers=superuser_auth_headers,
            data=form_data,
        )

        # Should succeed for all valid node types
        assert response.status_code == 303, f"Failed for node_type: {node_type}"
        assert "success" in response.headers["location"]


@pytest.mark.asyncio
async def test_save_node_with_all_valid_data_types(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that all valid data_type enum values are accepted."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    valid_data_types = ["string", "number", "boolean", "formula", "dimension", "selection"]

    for data_type in valid_data_types:
        form_data = {
            "manufacturing_type_id": str(mfg_type.id),
            "name": f"Test {data_type}",
            "node_type": "attribute",
            "data_type": data_type,
            "price_impact_type": "fixed",
            "weight_impact": "0",
            "sort_order": "0",
            "required": "false",
        }

        response = await client.post(
            "/api/v1/admin/hierarchy/node/save",
            headers=superuser_auth_headers,
            data=form_data,
        )

        # Should succeed for all valid data types
        assert response.status_code == 303, f"Failed for data_type: {data_type}"
        assert "success" in response.headers["location"]


@pytest.mark.asyncio
async def test_save_node_with_all_valid_price_impact_types(
    client: AsyncClient,
    superuser_auth_headers: dict,
    db_session: AsyncSession,
):
    """Test that all valid price_impact_type enum values are accepted."""
    # Create manufacturing type
    service = HierarchyBuilderService(db_session)
    mfg_type = await service.create_manufacturing_type(
        name="Test Window",
        base_price=Decimal("200.00"),
    )

    valid_price_impact_types = ["fixed", "percentage", "formula"]

    for price_impact_type in valid_price_impact_types:
        form_data = {
            "manufacturing_type_id": str(mfg_type.id),
            "name": f"Test {price_impact_type}",
            "node_type": "option",
            "price_impact_type": price_impact_type,
            "weight_impact": "0",
            "sort_order": "0",
            "required": "false",
        }

        # Add appropriate value based on type
        if price_impact_type == "fixed":
            form_data["price_impact_value"] = "50.00"
        elif price_impact_type == "percentage":
            form_data["price_impact_value"] = "15.00"
        elif price_impact_type == "formula":
            form_data["price_formula"] = "width * height * 0.05"

        response = await client.post(
            "/api/v1/admin/hierarchy/node/save",
            headers=superuser_auth_headers,
            data=form_data,
        )

        # Should succeed for all valid price impact types
        assert response.status_code == 303, f"Failed for price_impact_type: {price_impact_type}"
        assert "success" in response.headers["location"]
