"""Unit tests for PricingService error handling.

Tests error handling for price calculations including:
- Division by zero
- Invalid operations
- Unknown variables
- Syntax errors
- Out of range values
"""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidFormulaException, NotFoundException
from app.models.attribute_node import AttributeNode
from app.models.configuration import Configuration
from app.models.configuration_selection import ConfigurationSelection
from app.models.manufacturing_type import ManufacturingType
from app.services.pricing import PricingService


@pytest.fixture
def pricing_service(db_session: AsyncSession) -> PricingService:
    """Create pricing service instance."""
    return PricingService(db_session)


@pytest.mark.asyncio
class TestPricingServiceErrorHandling:
    """Test error handling in PricingService."""

    async def test_evaluate_formula_division_by_zero(self, pricing_service: PricingService):
        """Test that division by zero raises InvalidFormulaException."""
        formula = "100 / 0"
        context = {}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        assert "Division by zero" in exc_info.value.message
        assert exc_info.value.details["error_type"] == "division_by_zero"
        assert exc_info.value.formula == formula

    async def test_evaluate_formula_division_by_zero_variable(
        self, pricing_service: PricingService
    ):
        """Test that division by zero with variable raises InvalidFormulaException."""
        formula = "width / height"
        context = {"width": 100, "height": 0}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        assert "Division by zero" in exc_info.value.message
        assert exc_info.value.details["error_type"] == "division_by_zero"

    async def test_evaluate_formula_unknown_variable(self, pricing_service: PricingService):
        """Test that unknown variable raises InvalidFormulaException."""
        formula = "width * unknown_var"
        context = {"width": 100}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        assert "Unknown variable" in exc_info.value.message
        assert exc_info.value.details["error_type"] == "unknown_variable"
        assert "available_variables" in exc_info.value.details

    async def test_evaluate_formula_syntax_error(self, pricing_service: PricingService):
        """Test that syntax error raises InvalidFormulaException."""
        formula = "width * * height"  # Invalid syntax
        context = {"width": 100, "height": 50}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        assert "syntax error" in exc_info.value.message.lower()
        assert exc_info.value.details["error_type"] == "syntax_error"

    async def test_evaluate_formula_overflow(self, pricing_service: PricingService):
        """Test that overflow raises InvalidFormulaException."""
        formula = "width ** 1000"  # Will overflow
        context = {"width": 10}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        assert (
            "Calculation error" in exc_info.value.message
            or "out of range" in exc_info.value.message.lower()
        )

    async def test_evaluate_formula_invalid_result(self, pricing_service: PricingService):
        """Test that invalid result raises InvalidFormulaException."""
        # This will be caught by the range check
        formula = "width * 1e20"  # Result too large
        context = {"width": 100}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        assert (
            "invalid" in exc_info.value.message.lower()
            or "out of range" in exc_info.value.message.lower()
        )

    async def test_evaluate_formula_empty_formula(self, pricing_service: PricingService):
        """Test that empty formula returns zero."""
        formula = ""
        context = {}

        result = await pricing_service.evaluate_price_formula(formula, context)

        assert result == Decimal("0")

    async def test_evaluate_formula_whitespace_only(self, pricing_service: PricingService):
        """Test that whitespace-only formula returns zero."""
        formula = "   "
        context = {}

        result = await pricing_service.evaluate_price_formula(formula, context)

        assert result == Decimal("0")

    async def test_calculate_selection_impact_invalid_formula(
        self, pricing_service: PricingService, db_session: AsyncSession
    ):
        """Test that invalid formula in selection raises InvalidFormulaException with context."""
        # Create test data
        mfg_type = ManufacturingType(
            name="Test Window Selection Impact",
            base_price=Decimal("200"),
            base_weight=Decimal("15"),
        )
        db_session.add(mfg_type)
        await db_session.flush()

        attr_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="Width",
            node_type="attribute",
            data_type="number",
            price_impact_type="formula",
            price_formula="width / 0",  # Division by zero
            ltree_path="test.width",
        )
        db_session.add(attr_node)
        await db_session.flush()

        config = Configuration(
            manufacturing_type_id=mfg_type.id,
            name="Test Config",
            base_price=mfg_type.base_price,
        )
        db_session.add(config)
        await db_session.flush()

        selection = ConfigurationSelection(
            configuration_id=config.id,
            attribute_node_id=attr_node.id,
            numeric_value=Decimal("48"),
            selection_path="test.width",
        )
        db_session.add(selection)
        await db_session.flush()

        # Test that error includes context
        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.calculate_selection_impact(selection)

        assert "attribute node" in exc_info.value.message.lower()
        assert exc_info.value.details["attribute_node_id"] == attr_node.id
        assert exc_info.value.details["attribute_node_name"] == attr_node.name
        assert exc_info.value.details["selection_id"] == selection.id

    async def test_calculate_configuration_price_selection_error(
        self, pricing_service: PricingService, db_session: AsyncSession
    ):
        """Test that error in selection calculation includes configuration context."""
        # Create test data
        mfg_type = ManufacturingType(
            name="Test Window Config Price",
            base_price=Decimal("200"),
            base_weight=Decimal("15"),
        )
        db_session.add(mfg_type)
        await db_session.flush()

        attr_node = AttributeNode(
            manufacturing_type_id=mfg_type.id,
            name="Width",
            node_type="attribute",
            data_type="number",
            price_impact_type="formula",
            price_formula="width / 0",  # Direct division by zero
            ltree_path="test.width",
        )
        db_session.add(attr_node)
        await db_session.flush()

        config = Configuration(
            manufacturing_type_id=mfg_type.id,
            name="Test Config",
            base_price=mfg_type.base_price,
        )
        db_session.add(config)
        await db_session.flush()

        selection = ConfigurationSelection(
            configuration_id=config.id,
            attribute_node_id=attr_node.id,
            numeric_value=Decimal("48"),
            selection_path="test.width",
        )
        db_session.add(selection)
        await db_session.flush()

        # Test that error includes configuration context
        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.calculate_configuration_price(config.id)

        assert "configuration" in exc_info.value.message.lower()
        assert exc_info.value.details["configuration_id"] == config.id
        assert exc_info.value.details["selection_id"] == selection.id

    async def test_calculate_configuration_price_not_found(self, pricing_service: PricingService):
        """Test that non-existent configuration raises NotFoundException."""
        with pytest.raises(NotFoundException) as exc_info:
            await pricing_service.calculate_configuration_price(99999)

        assert "Configuration" in exc_info.value.message

    async def test_validate_formula_valid(self, pricing_service: PricingService):
        """Test that valid formula passes validation."""
        assert pricing_service.validate_formula("width * height * 0.05")
        assert pricing_service.validate_formula("(width + height) / 2")
        assert pricing_service.validate_formula("width ** 2")

    async def test_validate_formula_invalid_syntax(self, pricing_service: PricingService):
        """Test that invalid syntax fails validation."""
        assert not pricing_service.validate_formula("width * * height")
        assert not pricing_service.validate_formula("width +")

    async def test_validate_formula_unsafe_operation(self, pricing_service: PricingService):
        """Test that unsafe operations fail validation."""
        # These should fail because they use unsafe operations
        assert not pricing_service.validate_formula("import os")
        assert not pricing_service.validate_formula("__import__('os')")

    async def test_validate_formula_empty(self, pricing_service: PricingService):
        """Test that empty formula is valid."""
        assert pricing_service.validate_formula("")
        assert pricing_service.validate_formula("   ")

    async def test_meaningful_error_messages(self, pricing_service: PricingService):
        """Test that error messages are meaningful and helpful."""
        # Division by zero
        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula("10 / 0", {})
        assert "Division by zero" in exc_info.value.message
        assert exc_info.value.formula == "10 / 0"

        # Unknown variable
        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula("unknown", {})
        assert "Unknown variable" in exc_info.value.message
        assert "available_variables" in exc_info.value.details

        # Syntax error
        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula("1 +", {})
        assert "syntax error" in exc_info.value.message.lower()

    async def test_error_details_include_context(self, pricing_service: PricingService):
        """Test that error details include helpful context."""
        formula = "width / height"
        context = {"width": 100, "height": 0}

        with pytest.raises(InvalidFormulaException) as exc_info:
            await pricing_service.evaluate_price_formula(formula, context)

        # Check that details include useful information
        assert exc_info.value.formula == formula
        assert "error_type" in exc_info.value.details
        assert "context" in exc_info.value.details
