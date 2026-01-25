"""Pricing service for price calculations.

This module implements business logic for pricing calculations including
configuration pricing, selection impacts, and formula evaluation.

Public Classes:
    PricingService: Pricing calculation business logic

Features:
    - Configuration price calculation
    - Individual selection impact calculation
    - Safe formula evaluation
    - Fixed, percentage, and formula-based pricing
"""

import ast
import operator
import re
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InvalidFormulaException, ValidationException
from app.models.configuration_selection import ConfigurationSelection
from app.repositories.attribute_node import AttributeNodeRepository
from app.repositories.configuration import ConfigurationRepository
from app.repositories.configuration_selection import ConfigurationSelectionRepository
from app.services.base import BaseService

__all__ = ["PricingService"]


# Safe operators for formula evaluation
SAFE_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


class PricingService(BaseService):
    """Pricing service for price calculations.

    Handles pricing calculations for configurations including
    individual selection impacts and formula evaluation.

    Attributes:
        db: Database session
        config_repo: Configuration repository
        selection_repo: Configuration selection repository
        attr_node_repo: Attribute node repository
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize pricing service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.config_repo = ConfigurationRepository(db)
        self.selection_repo = ConfigurationSelectionRepository(db)
        self.attr_node_repo = AttributeNodeRepository(db)

    async def calculate_configuration_price(self, config_id: int) -> dict[str, Decimal]:
        """Calculate total price and weight for a configuration.

        Calculates the total price and weight by summing the base price/weight
        from the manufacturing type and all selection impacts.

        Args:
            config_id (int): Configuration ID

        Returns:
            dict[str, Decimal]: Dictionary with total_price and total_weight

        Raises:
            NotFoundException: If configuration not found
        """
        from app.core.exceptions import NotFoundException

        # Get configuration with manufacturing type
        config = await self.config_repo.get(config_id)
        if not config:
            raise NotFoundException(
                resource="Configuration",
                details={"config_id": config_id},
            )

        # Start with base price and weight from manufacturing type
        total_price = config.base_price
        total_weight = Decimal("0")

        # Get manufacturing type to get base weight
        if config.manufacturing_type:
            total_weight = config.manufacturing_type.base_weight

        # Get all selections for this configuration
        selections = await self.selection_repo.get_by_configuration(config_id)

        # Calculate impacts for each selection
        for selection in selections:
            try:
                impact = await self.calculate_selection_impact(selection)
                total_price += impact["price_impact"]
                total_weight += impact["weight_impact"]
            except InvalidFormulaException as e:
                # Re-raise with configuration context
                raise InvalidFormulaException(
                    message=f"Error calculating price for configuration {config_id}: {e.message}",
                    formula=e.details.get("formula"),
                    details={
                        **e.details,
                        "configuration_id": config_id,
                        "selection_id": selection.id,
                    },
                )
            except Exception as e:
                # Catch any other unexpected errors during calculation
                raise InvalidFormulaException(
                    message=f"Unexpected error calculating price for configuration {config_id}: {str(e)}",
                    details={
                        "configuration_id": config_id,
                        "selection_id": selection.id,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )

        return {
            "total_price": total_price,
            "total_weight": total_weight,
        }

    async def calculate_selection_impact(
        self, selection: ConfigurationSelection
    ) -> dict[str, Decimal]:
        """Calculate price and weight impact for a single selection.

        Evaluates the attribute node's pricing rules (fixed, percentage, or formula)
        to determine the impact of this selection on the configuration's total.

        Args:
            selection (ConfigurationSelection): Configuration selection

        Returns:
            dict[str, Decimal]: Dictionary with price_impact and weight_impact

        Raises:
            NotFoundException: If attribute node not found
        """
        from app.core.exceptions import NotFoundException

        # Get attribute node
        attr_node = await self.attr_node_repo.get(selection.attribute_node_id)
        if not attr_node:
            raise NotFoundException(
                resource="AttributeNode",
                details={"attribute_node_id": selection.attribute_node_id},
            )

        price_impact = Decimal("0")
        weight_impact = Decimal("0")

        # Calculate price impact based on type
        if attr_node.price_impact_type == "fixed":
            # Fixed amount
            if attr_node.price_impact_value:
                price_impact = attr_node.price_impact_value

        elif attr_node.price_impact_type == "percentage":
            # Percentage of current price (requires context)
            # For now, we'll just use the value as a multiplier
            if attr_node.price_impact_value:
                # This would need the current configuration price as context
                # For simplicity, we'll treat it as a fixed value for now
                price_impact = attr_node.price_impact_value

        elif attr_node.price_impact_type == "formula":
            # Formula-based calculation
            if attr_node.price_formula:
                try:
                    context = self._build_formula_context(selection)
                    price_impact = await self.evaluate_price_formula(
                        attr_node.price_formula, context
                    )
                except InvalidFormulaException as e:
                    # Re-raise with additional context
                    raise InvalidFormulaException(
                        message=f"Error calculating price impact for attribute node {attr_node.id}: {e.message}",
                        formula=attr_node.price_formula,
                        details={
                            **e.details,
                            "attribute_node_id": attr_node.id,
                            "attribute_node_name": attr_node.name,
                            "selection_id": selection.id,
                        },
                    )

        # Calculate weight impact
        if attr_node.weight_formula:
            # Formula-based weight calculation
            try:
                context = self._build_formula_context(selection)
                weight_impact = await self.evaluate_price_formula(attr_node.weight_formula, context)
            except InvalidFormulaException as e:
                # Re-raise with additional context
                raise InvalidFormulaException(
                    message=f"Error calculating weight impact for attribute node {attr_node.id}: {e.message}",
                    formula=attr_node.weight_formula,
                    details={
                        **e.details,
                        "attribute_node_id": attr_node.id,
                        "attribute_node_name": attr_node.name,
                        "selection_id": selection.id,
                    },
                )
        elif attr_node.weight_impact:
            # Fixed weight impact
            weight_impact = attr_node.weight_impact

        return {
            "price_impact": price_impact,
            "weight_impact": weight_impact,
        }

    async def evaluate_price_formula(self, formula: str, context: dict[str, Any]) -> Decimal:
        """Evaluate a price formula with safe execution.

        Safely evaluates mathematical formulas using a restricted set of
        operators and variables from the context.

        Args:
            formula (str): Formula string (e.g., "width * height * 0.05")
            context (dict[str, Any]): Variable context for formula evaluation

        Returns:
            Decimal: Calculated result

        Raises:
            InvalidFormulaException: If formula is invalid, unsafe, or evaluation fails
        """
        try:
            # Clean and validate formula
            formula = formula.strip()
            if not formula:
                return Decimal("0")

            # Parse the formula into an AST
            try:
                tree = ast.parse(formula, mode="eval")
            except SyntaxError as e:
                raise InvalidFormulaException(
                    message=f"Formula syntax error: {str(e)}",
                    formula=formula,
                    details={"error": str(e), "error_type": "syntax_error"},
                )

            # Evaluate the AST safely
            try:
                result = self._eval_node(tree.body, context)
            except ZeroDivisionError:
                raise InvalidFormulaException(
                    message="Division by zero in formula",
                    formula=formula,
                    details={
                        "error": "Division by zero",
                        "error_type": "division_by_zero",
                        "context": context,
                    },
                )
            except KeyError as e:
                raise InvalidFormulaException(
                    message=f"Unknown variable in formula: {str(e)}",
                    formula=formula,
                    details={
                        "error": str(e),
                        "error_type": "unknown_variable",
                        "available_variables": list(context.keys()),
                    },
                )
            except (ValueError, OverflowError) as e:
                raise InvalidFormulaException(
                    message=f"Calculation error in formula: {str(e)}",
                    formula=formula,
                    details={
                        "error": str(e),
                        "error_type": "calculation_error",
                        "context": context,
                    },
                )

            # Validate result is finite and reasonable
            if not isinstance(result, (int, float)) or not (-1e10 < result < 1e10):
                raise InvalidFormulaException(
                    message="Formula result is invalid or out of range",
                    formula=formula,
                    details={
                        "result": str(result),
                        "error_type": "invalid_result",
                    },
                )

            # Convert to Decimal
            return Decimal(str(result))

        except InvalidFormulaException:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            # Catch any other unexpected errors
            raise InvalidFormulaException(
                message=f"Unexpected error evaluating formula: {str(e)}",
                formula=formula,
                details={
                    "error": str(e),
                    "error_type": "unexpected_error",
                    "exception_type": type(e).__name__,
                },
            )

    def _eval_node(self, node: ast.AST, context: dict[str, Any]) -> float:
        """Recursively evaluate an AST node.

        Args:
            node (ast.AST): AST node to evaluate
            context (dict[str, Any]): Variable context

        Returns:
            float: Evaluated result

        Raises:
            InvalidFormulaException: If node type is not allowed
            ZeroDivisionError: If division by zero occurs
            KeyError: If variable not found in context
        """
        if isinstance(node, ast.Constant):
            # Numeric constant
            value = float(node.value)
            if not (-1e10 < value < 1e10):
                raise ValueError(f"Constant value out of range: {value}")
            return value

        elif isinstance(node, ast.Name):
            # Variable lookup
            if node.id not in context:
                raise KeyError(node.id)
            value = float(context[node.id])
            if not (-1e10 < value < 1e10):
                raise ValueError(f"Variable value out of range: {node.id}={value}")
            return value

        elif isinstance(node, ast.BinOp):
            # Binary operation (e.g., a + b, a * b)
            if type(node.op) not in SAFE_OPERATORS:
                raise InvalidFormulaException(
                    message=f"Unsafe operator: {type(node.op).__name__}",
                    details={"operator": type(node.op).__name__},
                )
            left = self._eval_node(node.left, context)
            right = self._eval_node(node.right, context)

            # Special handling for division to provide better error messages
            if isinstance(node.op, ast.Div):
                if right == 0:
                    raise ZeroDivisionError("Division by zero")

            result = SAFE_OPERATORS[type(node.op)](left, right)

            # Check for overflow or invalid results
            if not isinstance(result, (int, float)) or not (-1e10 < result < 1e10):
                raise ValueError(f"Operation result out of range: {result}")

            return result

        elif isinstance(node, ast.UnaryOp):
            # Unary operation (e.g., -a, +a)
            if type(node.op) not in SAFE_OPERATORS:
                raise InvalidFormulaException(
                    message=f"Unsafe operator: {type(node.op).__name__}",
                    details={"operator": type(node.op).__name__},
                )
            operand = self._eval_node(node.operand, context)
            result = SAFE_OPERATORS[type(node.op)](operand)

            if not isinstance(result, (int, float)) or not (-1e10 < result < 1e10):
                raise ValueError(f"Operation result out of range: {result}")

            return result

        else:
            raise InvalidFormulaException(
                message=f"Unsafe node type: {type(node).__name__}",
                details={"node_type": type(node).__name__},
            )

    @staticmethod
    def _build_formula_context(selection: ConfigurationSelection) -> dict[str, Any]:
        """Build context dictionary for formula evaluation.

        Extracts relevant values from the selection to use as variables
        in formula evaluation.

        Args:
            selection (ConfigurationSelection): Configuration selection

        Returns:
            dict[str, Any]: Context dictionary with available variables
        """
        context: dict[str, Any] = {}

        # Add selection values to context
        if selection.numeric_value is not None:
            context["value"] = float(selection.numeric_value)
            # Common aliases
            context["width"] = float(selection.numeric_value)
            context["height"] = float(selection.numeric_value)
            context["depth"] = float(selection.numeric_value)
            context["quantity"] = float(selection.numeric_value)

        if selection.string_value:
            # For string values, we might have numeric patterns
            # Try to extract numbers
            numbers = re.findall(r"\d+\.?\d*", selection.string_value)
            if numbers:
                context["value"] = float(numbers[0])

        # Add calculated impacts if available
        if selection.calculated_price_impact:
            context["price_impact"] = float(selection.calculated_price_impact)

        if selection.calculated_weight_impact:
            context["weight_impact"] = float(selection.calculated_weight_impact)

        # Add default values for common variables
        context.setdefault("value", 1.0)
        context.setdefault("width", 1.0)
        context.setdefault("height", 1.0)
        context.setdefault("depth", 1.0)
        context.setdefault("quantity", 1.0)

        return context

    def validate_formula(self, formula: str) -> bool:
        """Validate formula syntax without evaluating.

        Args:
            formula (str): Formula string to validate

        Returns:
            bool: True if formula is valid, False otherwise
        """
        try:
            formula = formula.strip()
            if not formula:
                return True

            # Try to parse the formula
            tree = ast.parse(formula, mode="eval")

            # Check if all nodes are safe
            self._validate_ast_node(tree.body)

            return True

        except (SyntaxError, ValidationException):
            return False

    def _validate_ast_node(self, node: ast.AST) -> None:
        """Recursively validate an AST node.

        Args:
            node (ast.AST): AST node to validate

        Raises:
            ValidationException: If node type is not allowed
        """
        if isinstance(node, (ast.Constant, ast.Name)):
            # Safe leaf nodes
            pass

        elif isinstance(node, ast.BinOp):
            # Binary operation
            if type(node.op) not in SAFE_OPERATORS:
                raise ValidationException(
                    message=f"Unsafe operator: {type(node.op).__name__}",
                    details={"operator": type(node.op).__name__},
                )
            self._validate_ast_node(node.left)
            self._validate_ast_node(node.right)

        elif isinstance(node, ast.UnaryOp):
            # Unary operation
            if type(node.op) not in SAFE_OPERATORS:
                raise ValidationException(
                    message=f"Unsafe operator: {type(node.op).__name__}",
                    details={"operator": type(node.op).__name__},
                )
            self._validate_ast_node(node.operand)

        else:
            raise ValidationException(
                message=f"Unsafe node type: {type(node).__name__}",
                details={"node_type": type(node).__name__},
            )
