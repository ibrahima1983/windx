"""Entry Page service for business logic.

This module provides the EntryService class for handling entry page operations
including schema generation, conditional field evaluation, data validation,
and configuration management.

Public Classes:
    ConditionEvaluator: Smart condition evaluator with complex expression support
    EntryService: Service class for entry page operations

Features:
    - Schema-driven form generation from attribute hierarchy
    - Smart conditional field visibility evaluation
    - Comprehensive validation with error handling
    - Configuration creation and management
    - Preview data generation
    - Performance optimizations with caching
"""

from __future__ import annotations

import re
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import Permission, Privilege, ResourceOwnership, Role, require
from app.models.attribute_node import AttributeNode
from app.models.configuration import Configuration
from app.models.configuration_selection import ConfigurationSelection
from app.models.manufacturing_type import ManufacturingType
from app.models.user import User
from app.schemas.entry import (
    FieldDefinition,
    FormSection,
    PreviewTable,
    ProfileEntryData,
    ProfilePreviewData,
    ProfileSchema,
)
from app.services.base import BaseService
from app.services.rbac import RBACService

__all__ = ["ConditionEvaluator", "EntryService"]


# Define reusable Privilege objects for Entry Service operations
ConfigurationCreator = Privilege(
    roles=[Role.CUSTOMER, Role.SALESMAN, Role.PARTNER, Role.SUPERADMIN],
    permission=Permission("configuration", "create"),
)

ConfigurationViewer = Privilege(
    roles=Role.CUSTOMER | Role.SALESMAN | Role.PARTNER | Role.SUPERADMIN,
    permission=Permission("configuration", "read"),
    resource=ResourceOwnership("configuration"),
)

AdminAccess = Privilege(roles=Role.SUPERADMIN, permission=Permission("*", "*"))

# Targeted privileges for inline editing and deletion (TODO: Refine with role-based restrictions)
ConfigurationEditor = Privilege(
    roles=[Role.DATA_ENTRY, Role.SUPERADMIN],
    permission=Permission("configuration", "update"),
    resource=ResourceOwnership("configuration"),
)

# Bulk delete privilege without ownership requirement (superadmins can delete any configuration)
BulkConfigurationDeleter = Privilege(
    roles=[Role.SUPERADMIN],
    permission=Permission("configuration", "delete"),
)

ConfigurationDeleter = Privilege(
    roles=[Role.DATA_ENTRY, Role.SUPERADMIN],
    permission=Permission("configuration", "delete"),
    resource=ResourceOwnership("configuration"),
)


def _safe_numeric_compare(a: Any, b: Any, compare_fn) -> bool:
    """Safely compare two values numerically, handling type conversions.

    Args:
        a: First value
        b: Second value
        compare_fn: Comparison function (e.g., lambda x, y: x > y)

    Returns:
        bool: Result of comparison, False if types are incompatible
    """
    try:
        # Convert to numeric types if possible
        a_num = float(a) if a is not None and a != "" else 0
        b_num = float(b) if b is not None and b != "" else 0
        return compare_fn(a_num, b_num)
    except (TypeError, ValueError):
        # If conversion fails, return False
        return False


class ConditionEvaluator:
    """Smart condition evaluator with support for complex expressions.

    Supports a rich set of operators for comparison, string operations,
    collection operations, existence checks, and logical operations.
    Provides consistent evaluation in both Python and JavaScript.
    """

    OPERATORS = {
        # Comparison operators
        "equals": lambda a, b: a == b,
        "not_equals": lambda a, b: a != b,
        "greater_than": lambda a, b: _safe_numeric_compare(a, b, lambda x, y: x > y),
        "less_than": lambda a, b: _safe_numeric_compare(a, b, lambda x, y: x < y),
        "greater_equal": lambda a, b: _safe_numeric_compare(a, b, lambda x, y: x >= y),
        "less_equal": lambda a, b: _safe_numeric_compare(a, b, lambda x, y: x <= y),
        # String operators
        "contains": lambda a, b: str(b).lower() in str(a or "").lower(),
        "starts_with": lambda a, b: str(a or "").lower().startswith(str(b).lower()),
        "ends_with": lambda a, b: str(a or "").lower().endswith(str(b).lower()),
        "matches_pattern": lambda a, b: bool(re.match(b, str(a or ""))),
        # Collection operators
        "in": lambda a, b: a in (b if isinstance(b, list) else [b]),
        "not_in": lambda a, b: a not in (b if isinstance(b, list) else [b]),
        "any_of": lambda a, b: any(item in (a if isinstance(a, list) else [a]) for item in b),
        "all_of": lambda a, b: all(item in (a if isinstance(a, list) else [a]) for item in b),
        # Existence operators
        "exists": lambda a, b: a is not None and a != "",
        "not_exists": lambda a, b: a is None or a == "",
        "is_empty": lambda a, b: not bool(a),
        "is_not_empty": lambda a, b: bool(a),
    }

    def evaluate_condition(self, condition: dict[str, Any], form_data: dict[str, Any]) -> bool:
        """Evaluate a condition against form data.

        Args:
            condition: Condition dictionary with operator, field, value, etc.
            form_data: Form data to evaluate against

        Returns:
            bool: True if condition is met, False otherwise

        Raises:
            ValueError: If operator is unknown
        """
        if not condition:
            return True

        operator = condition.get("operator")
        if not operator:
            return True

        # Handle logical operators (and, or, not)
        if operator == "and":
            conditions = condition.get("conditions", [])
            return all(self.evaluate_condition(c, form_data) for c in conditions)
        elif operator == "or":
            conditions = condition.get("conditions", [])
            return any(self.evaluate_condition(c, form_data) for c in conditions)
        elif operator == "not":
            inner_condition = condition.get("condition", {})
            return not self.evaluate_condition(inner_condition, form_data)

        # Handle field-based operators
        field = condition.get("field")
        if not field:
            return True

        field_value = self.get_field_value(field, form_data)
        expected_value = condition.get("value")

        if operator not in self.OPERATORS:
            raise ValueError(f"Unknown operator: {operator}")

        return self.OPERATORS[operator](field_value, expected_value)

    @staticmethod
    def get_field_value(field_path: str | int, form_data: dict[str, Any]) -> Any:
        """Get field value supporting dot notation for nested fields.

        Args:
            field_path: Field path (supports dot notation like "parent.child") or field key
            form_data: Form data dictionary

        Returns:
            Any: Field value or None if not found
        """
        # Handle non-string field paths (convert to string)
        if not isinstance(field_path, str):
            field_path = str(field_path)

        if "." not in field_path:
            return form_data.get(field_path)

        # Support nested field access: "parent.child.grandchild"
        value = form_data
        for part in field_path.split("."):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                return None
        return value


# noinspection PyTypeChecker
class EntryService(BaseService):
    """Service class for entry page operations.

    Provides business logic for schema generation, conditional field evaluation,
    data validation, and configuration management.
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize entry service.

        Args:
            db: Database session
        """
        super().__init__(db)
        self.condition_evaluator = ConditionEvaluator()
        self.rbac_service = RBACService(db)

    async def get_profile_schema(
        self, manufacturing_type_id: int, page_type: str = "profile"
    ) -> ProfileSchema:
        """Get profile form schema for a manufacturing type and page type.

        Args:
            manufacturing_type_id: Manufacturing type ID
            page_type: Page type (profile, accessories, glazing)

        Returns:
            ProfileSchema: Generated form schema

        Raises:
            NotFoundException: If manufacturing type not found
        """
        # Verify manufacturing type exists
        stmt = select(ManufacturingType).where(ManufacturingType.id == manufacturing_type_id)
        result = await self.db.execute(stmt)
        manufacturing_type = result.scalar_one_or_none()

        if not manufacturing_type:
            raise NotFoundException(f"Manufacturing type {manufacturing_type_id} not found")

        # Get attribute nodes for this manufacturing type and page type
        stmt = (
            select(AttributeNode)
            .where(
                AttributeNode.manufacturing_type_id == manufacturing_type_id,
                AttributeNode.page_type == page_type,
            )
            .order_by(AttributeNode.ltree_path, AttributeNode.sort_order)
        )
        result = await self.db.execute(stmt)
        attribute_nodes = result.scalars().all()

        # Generate form schema
        return await self.generate_form_schema(manufacturing_type_id, attribute_nodes)

    async def generate_form_schema(
        self, manufacturing_type_id: int, attribute_nodes: list[AttributeNode]
    ) -> ProfileSchema:
        """Generate form schema from attribute nodes.

        Args:
            manufacturing_type_id: Manufacturing type ID
            attribute_nodes: List of attribute nodes

        Returns:
            ProfileSchema: Generated form schema
        """
        sections_dict: dict[str, FormSection] = {}
        conditional_logic: dict[str, Any] = {}

        for node in attribute_nodes:
            # Skip category and option nodes - only process attribute nodes
            if node.node_type in ["category", "option"]:
                continue

            # Determine section based on LTREE path
            section_name = self.get_section_name(node.ltree_path)

            # Create section if it doesn't exist
            if section_name not in sections_dict:
                sections_dict[section_name] = FormSection(
                    title=section_name, fields=[], sort_order=len(sections_dict)
                )

            # Create field definition (now async)
            field = await self.create_field_definition(node)
            sections_dict[section_name].fields.append(field)

            # Add conditional logic if present
            if node.display_condition:
                conditional_logic[node.name] = node.display_condition

        # Convert to list and sort by sort_order
        sections = list(sections_dict.values())

        # Sort fields within each section first
        for section in sections:
            section.fields.sort(key=lambda f: f.sort_order)

            if section.fields:
                section.sort_order = section.fields[0].sort_order

        # Then sort sections
        sections.sort(key=lambda s: s.sort_order)

        return ProfileSchema(
            manufacturing_type_id=manufacturing_type_id,
            sections=sections,
            conditional_logic=conditional_logic,
        )

    @staticmethod
    def get_section_name(ltree_path: str) -> str:
        """Get section name from LTREE path.

        Args:
            ltree_path: LTREE path string

        Returns:
            str: Section name
        """
        if not ltree_path or ltree_path.strip() == "":
            return "general"

        # Use the first part of the path as section name
        parts = ltree_path.split(".")
        if len(parts) >= 1 and parts[0].strip():
            section_name = parts[0].strip()
            # Convert snake_case to Title Case
            return section_name.replace("_", " ").title()
        return "General"

    async def create_field_definition(self, node: AttributeNode) -> FieldDefinition:
        """Create field definition from attribute node.

        Args:
            node: Attribute node

        Returns:
            FieldDefinition: Field definition
        """
        # Use display_name from the node, with fallback to auto-generated name
        label = node.get_display_name()

        # Map ui_component values to match template expectations
        # Handle variations like 'input', 'string', etc. to ensure they map to 'text'
        ui_component = (node.ui_component or "").lower()
        if ui_component in ["input", "text", "string", "textinput"]:
            ui_component = "text"
        elif ui_component == "multiselect":
            ui_component = "text"
        elif not ui_component:
            # Fallback based on data_type
            if node.data_type == "boolean":
                ui_component = "checkbox"
            elif node.data_type in ["number", "float"]:
                ui_component = "number"
            else:
                ui_component = "text"

        # Extract options from child nodes if this is a dropdown/radio/multi-select field
        options = None
        options_data = None
        if ui_component in ["dropdown", "radio", "multi-select"]:
            options = await self._extract_options_from_children(node)
            options_data = await self._extract_options_with_metadata(node)

        return FieldDefinition(
            name=node.name,
            label=label,
            data_type=node.data_type or "string",
            required=node.required or False,
            validation_rules=node.validation_rules,
            display_condition=node.display_condition,
            ui_component=ui_component,
            description=node.description,  # Contains HTML for tooltips
            help_text=node.help_text,  # Short subtitle below field
            options=options,
            options_data=options_data,
            sort_order=node.sort_order or 0,
        )

    async def _extract_options_from_children(self, parent_node: AttributeNode) -> list[str]:
        """Extract option values from child nodes.

        Args:
            parent_node: Parent attribute node

        Returns:
            list[str]: List of option values
        """
        stmt = (
            select(AttributeNode)
            .where(
                AttributeNode.parent_node_id == parent_node.id, AttributeNode.node_type == "option"
            )
            .order_by(AttributeNode.sort_order, AttributeNode.name)
        )
        result = await self.db.execute(stmt)
        option_nodes = result.scalars().all()

        return [node.name for node in option_nodes]

    async def _extract_options_with_metadata(
        self, parent_node: AttributeNode
    ) -> list[dict[str, Any]]:
        """Extract option values and metadata from child nodes.

        Args:
            parent_node: Parent attribute node

        Returns:
            list[dict]: List of option dictionaries with id, name, and other metadata
        """
        stmt = (
            select(AttributeNode)
            .where(
                AttributeNode.parent_node_id == parent_node.id, AttributeNode.node_type == "option"
            )
            .order_by(AttributeNode.sort_order, AttributeNode.name)
        )
        result = await self.db.execute(stmt)
        option_nodes = result.scalars().all()

        return [
            {
                "id": node.id,
                "name": node.name,
                "description": node.description,
                "price_impact_value": float(node.price_impact_value)
                if node.price_impact_value
                else None,
                "sort_order": node.sort_order,
            }
            for node in option_nodes
        ]

    async def evaluate_display_conditions(
        self, form_data: dict[str, Any], schema: ProfileSchema
    ) -> dict[str, bool]:
        """Evaluate display conditions for all fields.

        Args:
            form_data: Current form data
            schema: Form schema with conditional logic

        Returns:
            dict[str, bool]: Field visibility map
        """
        visibility: dict[str, bool] = {}

        # Evaluate each field's display condition
        for field_name, condition in schema.conditional_logic.items():
            try:
                visibility[field_name] = self.condition_evaluator.evaluate_condition(
                    condition, form_data
                )
            except Exception as e:
                # Log error and default to visible
                print(f"Error evaluating condition for {field_name}: {e}")
                visibility[field_name] = True

        # Apply business rules for field availability
        business_rules_visibility = self.evaluate_business_rules(form_data)
        visibility.update(business_rules_visibility)

        return visibility

    @staticmethod
    def evaluate_business_rules(form_data: dict[str, Any]) -> dict[str, bool]:
        """Evaluate business rules for field availability based on Type selection.

        Args:
            form_data: Current form data

        Returns:
            dict[str, bool]: Field visibility map based on business rules
        """
        visibility: dict[str, bool] = {}
        product_type = form_data.get("type", "").lower()
        opening_system = form_data.get("opening_system", "").lower()

        # Business Rule 1: "Renovation only for frame" → Only when Type = "Frame"
        renovation_field = "renovation"
        visibility[renovation_field] = product_type == "frame"

        # Business Rule 2: "builtin Flyscreen track only for sliding frame" → Only for sliding frames
        flyscreen_field = "builtin_flyscreen_track"
        visibility[flyscreen_field] = product_type == "frame" and "sliding" in opening_system

        # Business Rule 3: "Total width only for frame with builtin flyscreen"
        total_width_field = "total_width"
        visibility[total_width_field] = (
            product_type == "frame" and form_data.get("builtin_flyscreen_track") is True
        )

        # Business Rule 4: "flyscreen track height only for frame with builtin flyscreen"
        flyscreen_height_field = "flyscreen_track_height"
        visibility[flyscreen_height_field] = (
            product_type == "frame" and form_data.get("builtin_flyscreen_track") is True
        )

        # Business Rule 5: "Sash overlap only for sashs" → Only when Type = "sash"
        sash_overlap_field = "sash_overlap"
        visibility[sash_overlap_field] = product_type == "sash"

        # Business Rule 6: "Flying mullion clearances" → Only when Type = "Flying mullion"
        flying_mullion_horizontal_field = "flying_mullion_horizontal_clearance"
        flying_mullion_vertical_field = "flying_mullion_vertical_clearance"
        visibility[flying_mullion_horizontal_field] = product_type == "flying mullion"
        visibility[flying_mullion_vertical_field] = product_type == "flying mullion"

        # Business Rule 7: "Glazing undercut height only for glazing bead" → Only when Type = "glazing bead"
        glazing_undercut_field = "glazing_undercut_height"
        visibility[glazing_undercut_field] = product_type == "glazing bead"

        # Business Rule 8: "Renovation height mm only for frame"
        renovation_height_field = "renovation_height"
        visibility[renovation_height_field] = product_type == "frame"

        # Business Rule 9: "Steel material thickness only for reinforcement"
        steel_thickness_field = "steel_material_thickness"
        visibility[steel_thickness_field] = product_type == "reinforcement"

        return visibility

    def get_field_display_value(
        self, field_name: str, value: Any, form_data: dict[str, Any]
    ) -> str:
        """Get display value for a field, showing 'N/A' for fields that don't apply to current type.

        Args:
            field_name: Field name
            value: Field value
            form_data: Current form data

        Returns:
            str: Display value or 'N/A' if field doesn't apply
        """
        # Check if field should be visible based on business rules
        business_rules_visibility = self.evaluate_business_rules(form_data)

        if field_name in business_rules_visibility and not business_rules_visibility[field_name]:
            return "N/A"

        # Format the value normally if field is applicable
        return self.format_preview_value(value)

    async def validate_profile_data(
        self, data: ProfileEntryData, page_type: str = "profile"
    ) -> dict[str, Any]:
        """Validate profile data against schema rules.

        Args:
            data: Profile data to validate
            page_type: Page type (profile, accessories, glazing)

        Returns:
            dict[str, Any]: Validation result with errors if any

        Raises:
            ValidationException: If validation fails
        """
        errors: dict[str, str] = {}

        # Get schema for validation rules
        try:
            schema = await self.get_profile_schema(data.manufacturing_type_id, page_type)
        except NotFoundException as nfe:
            raise ValidationException(
                "Invalid manufacturing type", field_errors={"manufacturing_type_id": "Not found"}
            ) from nfe

        # Validate each field against its rules
        form_data = data.model_dump()

        for section in schema.sections:
            for field in section.fields:
                field_value = form_data.get(field.name)

                # Check required fields
                if field.required and (field_value is None or field_value == ""):
                    errors[field.name] = f"{field.label} is required"
                    continue

                # Apply validation rules if present
                if field.validation_rules and field_value is not None:
                    field_errors = self.validate_field_value(
                        field_value, field.validation_rules, field.label
                    )
                    if field_errors:
                        errors[field.name] = field_errors

        # Cross-field validation
        cross_field_errors = self.validate_cross_field_rules(form_data, schema)
        errors.update(cross_field_errors)

        # Business rules validation
        business_rule_errors = await self.validate_business_rules(form_data)
        errors.update(business_rule_errors)

        if errors:
            raise ValidationException("Validation failed", field_errors=errors)

        return {"valid": True}

    @staticmethod
    def validate_field_value(
            value: Any, rules: dict[str, Any], field_label: str
    ) -> str | None:
        """Validate a field value against validation rules.

        Args:
            value: Field value to validate
            rules: Validation rules
            field_label: Field label for error messages

        Returns:
            str | None: Error message if validation fails, None if valid
        """
        try:
            # Handle Decimal and ensure numeric types for comparison
            # Import Decimal inside function to avoid circular imports if needed,
            # but usually top-level is fine. Assuming simple float conversion for range check.
            from decimal import Decimal

            is_numeric = isinstance(value, (int, float, Decimal))
            if is_numeric:
                try:
                    num_value = float(value)
                except (ValueError, TypeError):
                    return None  # Cannot convert to float for comparison

            # Range validation for numbers
            if "min" in rules and is_numeric:
                min_val = (
                    float(rules["min"])
                    if isinstance(rules["min"], (int, float, Decimal))
                    else rules["min"]
                )
                if num_value < min_val:
                    return f"{field_label} must be at least {rules['min']}"

            if "max" in rules and is_numeric:
                max_val = (
                    float(rules["max"])
                    if isinstance(rules["max"], (int, float, Decimal))
                    else rules["max"]
                )
                if num_value > max_val:
                    return f"{field_label} must be at most {rules['max']}"

            # Pattern validation for strings
            if "pattern" in rules and isinstance(value, str) and isinstance(rules["pattern"], str):
                if not re.match(rules["pattern"], value):
                    custom_message = rules.get("message", f"{field_label} format is invalid")
                    return custom_message

            # Length validation for strings
            if (
                "min_length" in rules
                and isinstance(value, str)
                and isinstance(rules["min_length"], (int, float))
                and len(value) < rules["min_length"]
            ):
                return f"{field_label} must be at least {rules['min_length']} characters"
            if (
                "max_length" in rules
                and isinstance(value, str)
                and isinstance(rules["max_length"], (int, float))
                and len(value) > rules["max_length"]
            ):
                return f"{field_label} must be at most {rules['max_length']} characters"

            # Enum/choice validation
            if "choices" in rules and value not in rules["choices"]:
                choices_str = ", ".join(str(c) for c in rules["choices"])
                return f"{field_label} must be one of: {choices_str}"

            # Custom validation rules
            if "rule_type" in rules:
                rule_type = rules["rule_type"]

                if rule_type == "range" and is_numeric:
                    min_val = float(rules.get("min", float("-inf")))
                    max_val = float(rules.get("max", float("inf")))

                    if not (min_val <= num_value <= max_val):
                        custom_message = rules.get(
                            "message", f"{field_label} must be between {min_val} and {max_val}"
                        )
                        return custom_message

                elif rule_type == "email" and isinstance(value, str):
                    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
                    if not re.match(email_pattern, value):
                        custom_message = rules.get(
                            "message", f"{field_label} must be a valid email address"
                        )
                        return custom_message

                elif rule_type == "url" and isinstance(value, str):
                    url_pattern = r"^https?://[^\s/$.?#].[^\s]*$"
                    if not re.match(url_pattern, value):
                        custom_message = rules.get("message", f"{field_label} must be a valid URL")
                        return custom_message

                elif rule_type == "positive" and isinstance(value, (int, float)):
                    if value <= 0:
                        custom_message = rules.get("message", f"{field_label} must be positive")
                        return custom_message

                elif rule_type == "non_negative" and isinstance(value, (int, float)):
                    if value < 0:
                        custom_message = rules.get("message", f"{field_label} must be non-negative")
                        return custom_message

        except (TypeError, ValueError, re.error):
            # Handle any type errors or regex errors gracefully
            # Return None to indicate validation passed (fail-safe approach)
            return None

        return None

    @staticmethod
    def _has_meaningful_value(value: Any) -> bool:
        """Check if a field value is meaningful (not null, empty, or default false for booleans).

        Args:
            value: Field value to check

        Returns:
            bool: True if value is meaningful, False otherwise
        """
        if value is None or value == "":
            return False
        # For boolean fields, False is not considered meaningful in this context
        # because unchecked checkboxes should not trigger validation errors
        if isinstance(value, bool) and value is False:
            return False
        return True

    async def validate_business_rules(self, form_data: dict[str, Any]) -> dict[str, str]:
        """Validate business rules and return field-specific errors.

        Args:
            form_data: Form data to validate

        Returns:
            dict[str, str]: Field errors from business rule violations
        """
        errors: dict[str, str] = {}
        product_type = form_data.get("type", "").lower()
        opening_system = form_data.get("opening_system", "").lower()

        # Validate business rule violations

        # Rule 1: Renovation should only have values for frames
        if self._has_meaningful_value(form_data.get("renovation")) and product_type != "frame":
            errors["renovation"] = "Renovation is only applicable for frame types"

        # Rule 2: Builtin flyscreen track should only be set for sliding frames
        if self._has_meaningful_value(form_data.get("builtin_flyscreen_track")) and not (
            product_type == "frame" and "sliding" in opening_system
        ):
            errors["builtin_flyscreen_track"] = (
                "Builtin flyscreen track is only applicable for sliding frames"
            )

        # Rule 3: Total width should only be set when builtin flyscreen is enabled
        if self._has_meaningful_value(form_data.get("total_width")) and not (
            product_type == "frame" and form_data.get("builtin_flyscreen_track") is True
        ):
            errors["total_width"] = (
                "Total width is only applicable when builtin flyscreen track is enabled"
            )

        # Rule 4: Flyscreen track height should only be set when builtin flyscreen is enabled
        if self._has_meaningful_value(form_data.get("flyscreen_track_height")) and not (
            product_type == "frame" and form_data.get("builtin_flyscreen_track") is True
        ):
            errors["flyscreen_track_height"] = (
                "Flyscreen track height is only applicable when builtin flyscreen track is enabled"
            )

        # Rule 5: Sash overlap should only have values for sash types
        if self._has_meaningful_value(form_data.get("sash_overlap")) and product_type != "sash":
            errors["sash_overlap"] = "Sash overlap is only applicable for sash types"

        # Rule 6: Flying mullion clearances should only have values for flying mullion types
        if (
            self._has_meaningful_value(form_data.get("flying_mullion_horizontal_clearance"))
            and product_type != "flying mullion"
        ):
            errors["flying_mullion_horizontal_clearance"] = (
                "Flying mullion horizontal clearance is only applicable for flying mullion types"
            )

        if (
            self._has_meaningful_value(form_data.get("flying_mullion_vertical_clearance"))
            and product_type != "flying mullion"
        ):
            errors["flying_mullion_vertical_clearance"] = (
                "Flying mullion vertical clearance is only applicable for flying mullion types"
            )

        # Rule 7: Glazing undercut height should only have values for glazing bead types
        if (
            self._has_meaningful_value(form_data.get("glazing_undercut_height"))
            and product_type != "glazing bead"
        ):
            errors["glazing_undercut_height"] = (
                "Glazing undercut height is only applicable for glazing bead types"
            )

        # Rule 8: Renovation height should only have values for frame types
        if (
            self._has_meaningful_value(form_data.get("renovation_height"))
            and product_type != "frame"
        ):
            errors["renovation_height"] = "Renovation height is only applicable for frame types"

        # Rule 9: Steel material thickness should only have values for reinforcement types
        if (
            self._has_meaningful_value(form_data.get("steel_material_thickness"))
            and product_type != "reinforcement"
        ):
            errors["steel_material_thickness"] = (
                "Steel material thickness is only applicable for reinforcement types"
            )

        return errors

    @staticmethod
    def validate_cross_field_rules(
            form_data: dict[str, Any], schema: ProfileSchema
    ) -> dict[str, str]:
        """Validate cross-field rules and dependencies.

        Args:
            form_data: Form data to validate
            schema: Form schema with field definitions

        Returns:
            dict[str, str]: Field errors from cross-field validation
        """
        errors: dict[str, str] = {}

        # Business logic validations for profile entry

        # If builtin_flyscreen_track is True, total_width and flyscreen_track_height should be provided
        if form_data.get("builtin_flyscreen_track") is True:
            if not form_data.get("total_width"):
                errors["total_width"] = (
                    "Total width is required when builtin flyscreen track is enabled"
                )
            if not form_data.get("flyscreen_track_height"):
                errors["flyscreen_track_height"] = (
                    "Flyscreen track height is required when builtin flyscreen track is enabled"
                )

        # If type is "Flying mullion", clearance fields should be provided
        if form_data.get("type") == "Flying mullion":
            if not form_data.get("flying_mullion_horizontal_clearance"):
                errors["flying_mullion_horizontal_clearance"] = (
                    "Horizontal clearance is required for flying mullion type"
                )
            if not form_data.get("flying_mullion_vertical_clearance"):
                errors["flying_mullion_vertical_clearance"] = (
                    "Vertical clearance is required for flying mullion type"
                )

            # Logical validations
        if form_data.get("front_height") and form_data.get("rear_height"):
            front_height = form_data["front_height"]
            rear_height = form_data["rear_height"]
            if abs(front_height - rear_height) > 50:  # Example business rule
                errors["rear_height"] = (
                    "Rear height should not differ from front height by more than 50mm"
                )

        # Price validation
        if form_data.get("price_per_meter") and form_data.get("price_per_beam"):
            if form_data.get("length_of_beam"):
                # Handle Decimal types for price calculations
                price_per_meter = float(form_data["price_per_meter"])
                price_per_beam = float(form_data["price_per_beam"])

                expected_beam_price = price_per_meter * form_data["length_of_beam"]
                if (
                    abs(expected_beam_price - price_per_beam) > expected_beam_price * 0.1
                ):  # 10% tolerance
                    errors["price_per_beam"] = (
                        "Price per beam should be approximately price per meter × length of beam"
                    )

        return errors

    # @require(ConfigurationCreator)
    # @require(AdminAccess)  # Allow admins to save configurations
    async def save_profile_configuration(
        self, data: ProfileEntryData, user: User, page_type: str = "profile"
    ) -> Configuration:
        """Save profile configuration data with proper customer relationship.

        Args:
            data: Profile data to save
            user: Current user
            page_type: Page type (profile, accessories, glazing)

        Returns:
            Configuration: Created configuration

        Raises:
            ValidationException: If validation fails
            NotFoundException: If manufacturing type not found
        """
        # Validate data first
        await self.validate_profile_data(data, page_type)

        # Get manufacturing type for base price/weight
        stmt = select(ManufacturingType).where(ManufacturingType.id == data.manufacturing_type_id)
        result = await self.db.execute(stmt)
        manufacturing_type = result.scalar_one_or_none()

        if not manufacturing_type:
            raise NotFoundException(f"Manufacturing type {data.manufacturing_type_id} not found")

        # Get attribute nodes for field mapping
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == data.manufacturing_type_id
        )
        result = await self.db.execute(stmt)
        attribute_nodes = result.scalars().all()

        # Create field name to attribute node mapping
        field_to_node = {node.name: node for node in attribute_nodes}

        # Get or create customer for user using RBAC service
        customer = await self.rbac_service.get_or_create_customer_for_user(user)

        # Create configuration with proper customer relationship
        config_data = {
            "manufacturing_type_id": data.manufacturing_type_id,
            "customer_id": customer.id,  # Use proper customer ID instead of user.id
            "name": data.name,
            "description": f"Profile entry for {data.type}",
            "status": "draft",
            "base_price": manufacturing_type.base_price,
            "total_price": manufacturing_type.base_price,  # TODO: Calculate with selections
            "calculated_weight": manufacturing_type.base_weight,  # TODO: Calculate with selections
            "calculated_technical_data": {},
        }

        configuration = Configuration(**config_data)
        self.db.add(configuration)
        await self.commit()
        await self.refresh(configuration)

        # Create configuration selections for non-null fields
        form_data = data.model_dump(exclude={"manufacturing_type_id", "name"})

        for field_name, field_value in form_data.items():
            if field_value is not None and field_name in field_to_node:
                attribute_node = field_to_node[field_name]

                # Create selection with proper attribute node mapping
                selection_data = {
                    "configuration_id": configuration.id,
                    "attribute_node_id": attribute_node.id,
                    "selection_path": attribute_node.ltree_path,
                }

                # Store value in appropriate field based on data type
                if isinstance(field_value, bool):
                    selection_data["boolean_value"] = field_value
                elif isinstance(field_value, (int, float)):
                    selection_data["numeric_value"] = field_value
                elif isinstance(field_value, (list, dict)):
                    selection_data["json_value"] = field_value
                else:
                    selection_data["string_value"] = str(field_value)

                selection = ConfigurationSelection(**selection_data)
                self.db.add(selection)

        await self.commit()
        return configuration

    # @require(ConfigurationViewer)
    # @require(AdminAccess)  # Admins can view any configuration
    async def load_profile_configuration(
        self, configuration_id: int, user: User
    ) -> ProfileEntryData:
        """Load profile configuration data and populate form fields.

        Args:
            configuration_id: Configuration ID to load
            user: Current user

        Returns:
            ProfileEntryData: Populated form data

        Raises:
            NotFoundException: If configuration not found
            AuthorizationException: If user lacks permission
        """
        # Get configuration with selections
        stmt = (
            select(Configuration)
            .options(selectinload(Configuration.selections))
            .where(Configuration.id == configuration_id)
        )
        result = await self.db.execute(stmt)
        configuration = result.scalar_one_or_none()

        if not configuration:
            raise NotFoundException(f"Configuration {configuration_id} not found")

        # Authorization is handled by the @require decorator
        # No need for manual authorization checks

        # Get attribute nodes for field mapping
        stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == configuration.manufacturing_type_id
        )
        result = await self.db.execute(stmt)
        attribute_nodes = result.scalars().all()

        # Create attribute node ID to field name mapping
        node_to_field = {node.id: node.name for node in attribute_nodes}

        # Start with base configuration data
        form_data = {
            "manufacturing_type_id": configuration.manufacturing_type_id,
            "name": configuration.name,
        }

        # Populate form data from selections
        for selection in configuration.selections:
            field_name = node_to_field.get(selection.attribute_node_id)
            if field_name:
                # Get value from appropriate field
                if selection.boolean_value is not None:
                    form_data[field_name] = selection.boolean_value
                elif selection.numeric_value is not None:
                    form_data[field_name] = selection.numeric_value
                elif selection.json_value is not None:
                    form_data[field_name] = selection.json_value
                elif selection.string_value is not None:
                    form_data[field_name] = selection.string_value

        # Create ProfileEntryData with validation
        return ProfileEntryData(**form_data)

    @require(ConfigurationViewer)
    @require(ConfigurationViewer)
    @require(AdminAccess)  # Admins can view any configuration
    async def generate_preview_data(self, configuration_id: int, user: User) -> ProfilePreviewData:
        """Generate preview data for a configuration.

        Args:
            configuration_id: Configuration ID
            user: Current user

        Returns:
            ProfilePreviewData: Preview data

        Raises:
            NotFoundException: If configuration not found
            AuthorizationException: If user lacks permission
        """
        # Get configuration with selections
        stmt = (
            select(Configuration)
            .options(selectinload(Configuration.selections))
            .where(Configuration.id == configuration_id)
        )
        result = await self.db.execute(stmt)
        configuration = result.scalar_one_or_none()

        if not configuration:
            raise NotFoundException(f"Configuration {configuration_id} not found")

        # Authorization is handled by the @require decorator
        # No need for manual authorization checks

        # Generate preview table with manufacturing_type_id
        preview_table = await self.generate_preview_table(
            configuration, configuration.manufacturing_type_id
        )

        return ProfilePreviewData(
            configuration_id=configuration.id,
            table=preview_table,
            last_updated=configuration.updated_at,
        )

    # Cache for generated headers and mappings to improve performance
    _header_cache: dict[int, list[str]] = {}
    _mapping_cache: dict[int, dict[str, str]] = {}
    _reverse_mapping_cache: dict[int, dict[str, str]] = {}

    async def generate_preview_headers(
        self, manufacturing_type_id: int, page_type: str = "profile"
    ) -> list[str]:
        """Generate dynamic preview headers from attribute nodes.

        Args:
            manufacturing_type_id: Manufacturing type ID
            page_type: Page type (profile, accessories, glazing)

        Returns:
            list[str]: Ordered list of preview headers
        """
        # Create cache key that includes page_type
        cache_key = f"{manufacturing_type_id}_{page_type}"

        # Check cache first
        if cache_key in self._header_cache:
            return self._header_cache[cache_key]

        # Get attribute nodes for this manufacturing type and page type, ordered by sort_order
        stmt = (
            select(AttributeNode)
            .where(
                AttributeNode.manufacturing_type_id == manufacturing_type_id,
                AttributeNode.page_type == page_type,
                AttributeNode.node_type == "attribute",  # Only attributes generate headers
            )
            .order_by(AttributeNode.sort_order, AttributeNode.name)
        )
        result = await self.db.execute(stmt)
        attribute_nodes = result.scalars().all()

        # Generate headers list starting with id only
        # All attributes including "name" will be processed and get proper labels
        headers = ["id"]

        for node in attribute_nodes:
            # Use display_name from the node, with fallback to auto-generated name
            header = node.get_display_name()
            headers.append(header)

        # Cache the result
        self._header_cache[cache_key] = headers
        return headers

    async def generate_header_mapping(self, manufacturing_type_id: int) -> dict[str, str]:
        """Generate dynamic header-to-field mapping from attribute nodes.

        Args:
            manufacturing_type_id: Manufacturing type ID

        Returns:
            dict[str, str]: Mapping from header names to field names
        """
        # Check cache first
        if manufacturing_type_id in self._mapping_cache:
            return self._mapping_cache[manufacturing_type_id]

        # Get attribute nodes for this manufacturing type, ordered by sort_order
        stmt = (
            select(AttributeNode)
            .where(
                AttributeNode.manufacturing_type_id == manufacturing_type_id,
                AttributeNode.node_type == "attribute",  # Only attributes generate mappings
            )
            .order_by(AttributeNode.sort_order, AttributeNode.name)
        )
        result = await self.db.execute(stmt)
        attribute_nodes = result.scalars().all()

        # Generate mapping starting with special cases
        mapping = {"id": "id"}

        for node in attribute_nodes:
            # Map human-readable header to field name using display_name
            header = node.get_display_name()
            mapping[header] = node.name

        # Cache the result
        self._mapping_cache[manufacturing_type_id] = mapping
        return mapping

    async def get_reverse_header_mapping(self, manufacturing_type_id: int) -> dict[str, str]:
        """Get reverse mapping from field names to headers.

        Args:
            manufacturing_type_id: Manufacturing type ID

        Returns:
            dict[str, str]: Mapping from field names to header names
        """
        # Check cache first
        if manufacturing_type_id in self._reverse_mapping_cache:
            return self._reverse_mapping_cache[manufacturing_type_id]

        # Generate forward mapping first
        forward_mapping = await self.generate_header_mapping(manufacturing_type_id)

        # Create reverse mapping
        reverse_mapping = {v: k for k, v in forward_mapping.items()}

        # Cache the result
        self._reverse_mapping_cache[manufacturing_type_id] = reverse_mapping
        return reverse_mapping

    def clear_header_cache(self, manufacturing_type_id: int | None = None) -> None:
        """Clear header cache for a specific manufacturing type or all types.

        Args:
            manufacturing_type_id: Manufacturing type ID to clear, or None for all
        """
        if manufacturing_type_id is None:
            self._header_cache.clear()
            self._mapping_cache.clear()
            self._reverse_mapping_cache.clear()
        else:
            self._header_cache.pop(manufacturing_type_id, None)
            self._mapping_cache.pop(manufacturing_type_id, None)
            self._reverse_mapping_cache.pop(manufacturing_type_id, None)

    @require(ConfigurationViewer)
    @require(AdminAccess)  # Admins can view any configuration
    async def list_previews(self, manufacturing_type_id: int, user: User) -> PreviewTable:
        """List all profile configuration previews for a manufacturing type.

        Args:
            manufacturing_type_id: Manufacturing type ID
            user: Current user

        Returns:
            PreviewTable: Table with all configurations
        """
        # Fetch all configurations for this manufacturing type and user
        # In admin context, we might want to see all for this type
        stmt = (
            select(Configuration)
            .where(Configuration.manufacturing_type_id == manufacturing_type_id)
            .options(selectinload(Configuration.selections))
            .order_by(Configuration.updated_at.desc())
        )

        # Apply RBAC filtering if not superadmin
        if user.role != Role.SUPERADMIN.value:
            from app.services.rbac import RBACService

            rbac_service = RBACService(self.db)
            accessible_customers = await rbac_service.get_accessible_customers(user)
            if accessible_customers:
                stmt = stmt.where(Configuration.customer_id.in_(accessible_customers))
            else:
                # If no accessible customers, return empty table
                headers = await self.generate_preview_headers(manufacturing_type_id)
                return PreviewTable(headers=headers, rows=[])

        result = await self.db.execute(stmt)
        configurations = result.scalars().all()

        return await self.generate_preview_table(configurations, manufacturing_type_id)

    async def generate_preview_table(
        self,
        data: Configuration | list[Configuration] | dict[str, Any],
        manufacturing_type_id: int | None = None,
    ) -> PreviewTable:
        """Generate preview table from configuration data or form data.

        Args:
            data: Configuration(s) or form data dictionary
            manufacturing_type_id: Manufacturing type ID (required for dynamic headers)

        Returns:
            PreviewTable: Preview table structure
        """
        # Determine manufacturing_type_id if not provided
        if manufacturing_type_id is None:
            if isinstance(data, Configuration):
                manufacturing_type_id = data.manufacturing_type_id
            elif isinstance(data, list) and data:
                manufacturing_type_id = data[0].manufacturing_type_id
            elif isinstance(data, dict):
                manufacturing_type_id = data.get("manufacturing_type_id")

            if manufacturing_type_id is None:
                raise ValueError("manufacturing_type_id is required for dynamic header generation")

        # Generate dynamic headers
        headers = await self.generate_preview_headers(manufacturing_type_id)
        rows = []

        if isinstance(data, list):
            for item in data:
                rows.append(await self._create_row(item, manufacturing_type_id))
        else:
            rows.append(await self._create_row(data, manufacturing_type_id))

        return PreviewTable(headers=headers, rows=rows)

    async def _create_row(
        self, data: Configuration | dict[str, Any], manufacturing_type_id: int
    ) -> dict[str, Any]:
        """Create a single table row.

        Args:
            data: Configuration or form data dictionary
            manufacturing_type_id: Manufacturing type ID for dynamic mapping

        Returns:
            dict: Row data
        """
        row_data: dict[str, Any] = {}

        # Get dynamic mappings
        header_mapping = await self.generate_header_mapping(manufacturing_type_id)
        reverse_mapping = await self.get_reverse_header_mapping(manufacturing_type_id)

        if isinstance(data, Configuration):
            row_data["id"] = data.id

            # Use the correct header name for the name field
            name_header = reverse_mapping.get(
                "name", "Product Name"
            )  # Default to "Product Name" if not found
            row_data[name_header] = data.name

            # Preload attribute nodes for this configuration's manufacturing type
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == data.manufacturing_type_id
            )
            result = await self.db.execute(stmt)
            attribute_nodes = {node.id: node.name for node in result.scalars().all()}

            # Create form data for business rules evaluation
            form_data = {"name": data.name}
            for selection in data.selections:
                field_name = attribute_nodes.get(selection.attribute_node_id)
                if field_name:
                    value = (
                        selection.string_value
                        if selection.string_value is not None
                        else selection.json_value
                        if selection.json_value is not None
                        else selection.numeric_value
                        if selection.numeric_value is not None
                        else selection.boolean_value
                    )
                    form_data[field_name] = value

            # Map selections to CSV columns using attribute node names
            for selection in data.selections:
                field_name = attribute_nodes.get(selection.attribute_node_id)
                if field_name:
                    value = (
                        selection.string_value
                        if selection.string_value is not None
                        else selection.json_value
                        if selection.json_value is not None
                        else selection.numeric_value
                        if selection.numeric_value is not None
                        else selection.boolean_value
                    )

                    header = reverse_mapping.get(field_name)
                    if header:
                        # Use business rules to determine display value
                        row_data[header] = self.get_field_display_value(
                            field_name, value, form_data
                        )
        else:
            # Handle dictionary (form data)
            row_data["id"] = data.get("id", "N/A")
            for header, field_name in header_mapping.items():
                if header == "id":
                    continue
                value = data.get(field_name)
                # Use business rules to determine display value
                row_data[header] = self.get_field_display_value(field_name, value, data)

        # Fill missing columns with N/A
        for header in header_mapping.keys():
            if header not in row_data:
                row_data[header] = "N/A"

        return row_data

    @staticmethod
    def format_preview_value(value: Any) -> str:
        """Format value for preview display.

        Args:
            value: Value to format

        Returns:
            str: Formatted value
        """
        if value is None or value == "":
            return "N/A"
        elif isinstance(value, bool):
            return "yes" if value else "no"  # Lowercase to match CSV format
        elif isinstance(value, list):
            if len(value) == 0:
                return "N/A"
            return ", ".join(str(v) for v in value)
        elif isinstance(value, (int, float)):
            # Format numbers appropriately
            return str(value)
        elif hasattr(value, "__str__"):  # Handle Decimal and other numeric types
            return str(value)
        elif isinstance(value, dict):
            return str(value)  # TODO: Better dict formatting
        else:
            return str(value)

    @require(AdminAccess)  # Allow admins to edit configurations
    async def update_preview_value(
        self, configuration_id: int, field: str, value: Any, user: User
    ) -> Configuration:
        """Update a specific field in a configuration from table preview.

        Args:
            configuration_id: Configuration ID
            field: Header name or field path
            value: New value
            user: Current user

        Returns:
            Configuration: Updated configuration
        """
        print(
            f"🦆 [UPDATE DEBUG] Updating field '{field}' with value '{value}' for config {configuration_id}"
        )

        # Load configuration with selections
        stmt = (
            select(Configuration)
            .where(Configuration.id == configuration_id)
            .options(selectinload(Configuration.selections))
        )
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise NotFoundException(f"Configuration {configuration_id} not found")

        # Get dynamic header mapping for this manufacturing type
        header_mapping = await self.generate_header_mapping(config.manufacturing_type_id)

        # Resolve field name from header if needed
        field_path = header_mapping.get(field, field)
        print(f"🦆 [UPDATE DEBUG] Resolved field_path: '{field_path}'")

        if field_path == "name":
            config.name = str(value)
            print(f"🦆 [UPDATE DEBUG] Updated config name to: {config.name}")
        else:
            # Get attribute node by name (not ltree_path!)
            stmt = select(AttributeNode).where(
                AttributeNode.manufacturing_type_id == config.manufacturing_type_id,
                AttributeNode.name == field_path,  # Use name instead of ltree_path
            )
            res = await self.db.execute(stmt)
            node = res.scalar_one_or_none()

            print(f"🦆 [UPDATE DEBUG] Found attribute node: {node}")
            print(f"🦆 [UPDATE DEBUG] Node name: {node.name if node else 'None'}")
            print(f"🦆 [UPDATE DEBUG] Node data_type: {node.data_type if node else 'None'}")

            if not node:
                raise ValidationException(f"Field {field_path} not found for this product type")

            # Find existing selection or create new
            selection = next((s for s in config.selections if s.attribute_node_id == node.id), None)
            print(f"🦆 [UPDATE DEBUG] Found existing selection: {selection}")

            if not selection:
                selection = ConfigurationSelection(
                    configuration_id=config.id,
                    attribute_node_id=node.id,
                    selection_path=node.ltree_path,
                )
                self.db.add(selection)
                print("🦆 [UPDATE DEBUG] Created new selection")

            # Store value in appropriate field based on data type
            # (matches logic in save_profile_configuration)
            data_type = node.data_type
            print("🦆 [UPDATE DEBUG] Data type: {data_type}")

            # Clear all value fields first
            selection.string_value = None
            selection.numeric_value = None
            selection.boolean_value = None
            selection.json_value = None

            if data_type == "boolean" or isinstance(value, bool):
                selection.boolean_value = (
                    bool(value) if isinstance(value, bool) else (str(value).lower() == "yes")
                )
                print(f"🦆 [UPDATE DEBUG] Set boolean_value: {selection.boolean_value}")
            elif data_type in ["number", "dimension"] or isinstance(value, (int, float)):
                try:
                    selection.numeric_value = Decimal(str(value))
                    print(f"🦆 [UPDATE DEBUG] Set numeric_value: {selection.numeric_value}")
                except (TypeError, ValueError) as e:
                    raise ValidationException(f"Invalid numeric value: {value}") from e
            elif data_type == "selection" and isinstance(value, (list, dict)):
                selection.json_value = value
                print(f"🦆 [UPDATE DEBUG] Set json_value: {selection.json_value}")
            else:
                selection.string_value = str(value)
                print(f"🦆 [UPDATE DEBUG] Set string_value: {selection.string_value}")

        config.updated_at = datetime.now()
        await self.commit()
        await self.refresh(config)
        print("🦆 [UPDATE DEBUG] Successfully updated configuration")
        return config

    @require(ConfigurationDeleter)
    async def delete_profile_configuration(self, configuration_id: int, user: User) -> None:
        """Delete a profile configuration.

        Args:
            configuration_id: Configuration ID
            user: Current user
        """
        stmt = select(Configuration).where(Configuration.id == configuration_id)
        result = await self.db.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            raise NotFoundException(f"Configuration {configuration_id} not found")

        await self.db.delete(config)
        await self.commit()

    @require(BulkConfigurationDeleter)
    async def bulk_delete_profile_configurations(
        self, configuration_ids: list[int], user: User
    ) -> dict[str, Any]:
        """Bulk delete multiple profile configurations.

        Args:
            configuration_ids: List of configuration IDs to delete
            user: Current user

        Returns:
            dict: Result with success/error counts and details
        """
        if not configuration_ids:
            return {"success_count": 0, "error_count": 0, "errors": [], "total_requested": 0}

        # Validate all configurations exist and user has permission to delete them
        stmt = select(Configuration).where(Configuration.id.in_(configuration_ids))
        result = await self.db.execute(stmt)
        existing_configs = result.scalars().all()

        existing_ids = {config.id for config in existing_configs}
        missing_ids = set(configuration_ids) - existing_ids

        success_count = 0
        error_count = 0
        errors = []

        # Add errors for missing configurations
        for missing_id in missing_ids:
            errors.append(f"Configuration {missing_id} not found")
            error_count += 1

        # Bulk delete existing configurations
        if existing_configs:
            try:
                # Use bulk delete for efficiency
                from sqlalchemy import delete

                delete_stmt = delete(Configuration).where(Configuration.id.in_(existing_ids))
                await self.db.execute(delete_stmt)
                await self.commit()
                success_count = len(existing_configs)

                print(f"🦆 [BULK DELETE] Successfully deleted {success_count} configurations")

            except Exception as e:
                print(f"🦆 [BULK DELETE] Error during bulk delete: {e}")
                # Rollback and try individual deletes as fallback
                await self.db.rollback()

                for config in existing_configs:
                    try:
                        await self.db.delete(config)
                        await self.commit()
                        success_count += 1
                    except Exception as individual_error:
                        errors.append(
                            f"Failed to delete configuration {config.id}: {str(individual_error)}"
                        )
                        error_count += 1
                        await self.db.rollback()

        return {
            "success_count": success_count,
            "error_count": error_count,
            "errors": errors,
            "total_requested": len(configuration_ids),
        }

    async def add_field_option(
        self,
        manufacturing_type_id: int,
        field_name: str,
        option_value: str,
        page_type: str = "profile",
    ) -> dict[str, Any]:
        """Add a new option to an attribute field.

        Creates a new attribute node of type 'option' under the specified field.

        Args:
            manufacturing_type_id (int): Manufacturing type ID
            field_name (str): Name of the field to add option to
            option_value (str): Value of the new option
            page_type (str): Page type (profile, accessories, glazing)

        Returns:
            dict: Result with success status and details

        Raises:
            NotFoundException: If field not found
            ValidationException: If option already exists
        """
        from decimal import Decimal

        from sqlalchemy import func

        from app.models.attribute_node import AttributeNode


        # Check if this is a protected field that shouldn't be modified
        if field_name.lower() == "type":
            return {
                "success": False,
                "error": "Type options cannot be modified here. Please edit in Node Hierarchy.",
            }

        # Find the parent attribute node
        parent_stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type_id,
            AttributeNode.name == field_name,
            AttributeNode.page_type == page_type,
            AttributeNode.node_type == "attribute",
        )
        parent_result = await self.db.execute(parent_stmt)
        parent_node = parent_result.scalar_one_or_none()

        if not parent_node:
            raise NotFoundException(
                f"Field '{field_name}' not found for manufacturing type {manufacturing_type_id}"
            )

        # Check if option already exists
        existing_stmt = select(AttributeNode).where(
            AttributeNode.parent_node_id == parent_node.id,
            AttributeNode.name == option_value,
            AttributeNode.node_type == "option",
        )
        existing_result = await self.db.execute(existing_stmt)
        existing_option = existing_result.scalar_one_or_none()

        if existing_option:
            return {
                "success": False,
                "error": f"Option '{option_value}' already exists for field '{field_name}'",
            }

        # Get the next sort order
        sort_stmt = select(func.max(AttributeNode.sort_order)).where(
            AttributeNode.parent_node_id == parent_node.id, AttributeNode.node_type == "option"
        )
        sort_result = await self.db.execute(sort_stmt)
        max_sort_order = sort_result.scalar() or 0

        # Create new option node
        new_option = AttributeNode(
            manufacturing_type_id=manufacturing_type_id,
            parent_node_id=parent_node.id,
            page_type=page_type,
            name=option_value,
            node_type="option",
            data_type="selection",
            ltree_path=f"{parent_node.ltree_path}.{option_value.lower().replace(' ', '_')}",
            depth=parent_node.depth + 1,
            sort_order=max_sort_order + 1,
            price_impact_type="fixed",
            price_impact_value=Decimal("0.00"),
            weight_impact=Decimal("0.00"),
        )

        self.db.add(new_option)
        await self.commit()
        await self.refresh(new_option)

        return {
            "success": True,
            "message": f"Option '{option_value}' added successfully to field '{field_name}'",
            "option_id": new_option.id,
            "field_name": field_name,
            "option_value": option_value,
            "manufacturing_type_id": manufacturing_type_id,
        }

    async def remove_field_option(self, option_id: int) -> dict[str, Any]:
        """Remove an option from an attribute field.

        Deletes the attribute node of type 'option' with the specified ID.

        Args:
            option_id (int): ID of the option to remove

        Returns:
            dict: Result with success status and details

        Raises:
            NotFoundException: If option not found
        """
        from app.models.attribute_node import AttributeNode

        # Find the option node
        option_stmt = select(AttributeNode).where(
            AttributeNode.id == option_id, AttributeNode.node_type == "option"
        )
        option_result = await self.db.execute(option_stmt)
        option_node = option_result.scalar_one_or_none()

        if not option_node:
            raise NotFoundException(f"Option {option_id} not found")

        # Store details for response
        option_name = option_node.name
        parent_field_id = option_node.parent_node_id

        # Get parent field name for response
        parent_stmt = select(AttributeNode).where(AttributeNode.id == parent_field_id)
        parent_result = await self.db.execute(parent_stmt)
        parent_field = parent_result.scalar_one_or_none()
        parent_field_name = parent_field.name if parent_field else "unknown"

        # Delete the option node
        await self.db.delete(option_node)
        await self.db.commit()

        return {
            "success": True,
            "message": f"Option '{option_name}' removed successfully from field '{parent_field_name}'",
            "option_id": option_id,
            "option_name": option_name,
            "field_name": parent_field_name,
        }

    async def remove_field_option_by_name(
        self,
        manufacturing_type_id: int,
        field_name: str,
        option_value: str,
        page_type: str = "profile",
    ) -> dict[str, Any]:
        """Remove an option from an attribute field by name.

        Finds and deletes the attribute node of type 'option' with the specified name.

        Args:
            manufacturing_type_id: Manufacturing type ID
            field_name: Name of the field to remove option from
            option_value: Value of the option to remove
            page_type: Page type (profile, accessories, glazing)

        Returns:
            dict: Result with success status and details

        Raises:
            NotFoundException: If field or option not found
        """
        from app.models.attribute_node import AttributeNode

        # Check if this is a protected field that shouldn't be modified
        if field_name.lower() == "type":
            return {
                "success": False,
                "error": "Type options cannot be modified here. Please edit in Node Hierarchy.",
            }

        # Find the parent attribute node
        parent_stmt = select(AttributeNode).where(
            AttributeNode.manufacturing_type_id == manufacturing_type_id,
            AttributeNode.name == field_name,
            AttributeNode.page_type == page_type,
            AttributeNode.node_type == "attribute",
        )
        parent_result = await self.db.execute(parent_stmt)
        parent_node = parent_result.scalar_one_or_none()

        if not parent_node:
            raise NotFoundException(
                f"Field '{field_name}' not found for manufacturing type {manufacturing_type_id}"
            )

        # Find the option node
        option_stmt = select(AttributeNode).where(
            AttributeNode.parent_node_id == parent_node.id,
            AttributeNode.name == option_value,
            AttributeNode.node_type == "option",
        )
        option_result = await self.db.execute(option_stmt)
        option_node = option_result.scalar_one_or_none()

        if not option_node:
            return {
                "success": False,
                "error": f"Option '{option_value}' not found in field '{field_name}'",
            }

        # Store details for response
        option_id = option_node.id

        # Delete any configuration selections that reference this option
        from app.models.configuration_selection import ConfigurationSelection

        stmt = delete(ConfigurationSelection).where(
            ConfigurationSelection.attribute_node_id == option_id
        )
        await self.db.execute(stmt)

        # Delete the option node
        await self.db.delete(option_node)
        await self.commit()

        return {
            "success": True,
            "message": f"Option '{option_value}' removed successfully from field '{field_name}'",
            "option_id": option_id,
            "field_name": field_name,
            "option_value": option_value,
            "manufacturing_type_id": manufacturing_type_id,
        }

    # Customer management is now handled by RBACService
    # This method is deprecated - use rbac_service.get_or_create_customer_for_user() instead


# JavaScivalent for client-side evaluation
JAVASCRIPT_CONDITION_EVALUATOR = """
class ConditionEvaluator {
    static OPERATORS = {
        // Comparison operators
        equals: (a, b) => a == b,
        not_equals: (a, b) => a != b,
        greater_than: (a, b) => (a || 0) > (b || 0),
        less_than: (a, b) => (a || 0) < (b || 0),
        greater_equal: (a, b) => (a || 0) >= (b || 0),
        al: (a, b) => (a || 0) <= (b || 0),
        
        // String operators
        contains: (a, b) => String(a || '').toLowerCase().includes(String(b).toLowerCase()),
        starts_with: (a, b) => String(a || '').toLowerCase().startsWith(String(b).toLowerCase()),
        ends_with: (a, b) => String(a || '').toLowerCase().endsWith(String(b).toLowerCase()),
        matches_pattern: (a, b) => new RegExp(b).test(String(a || '')),
        
        // Collection operators
        in: (a, b) => (Array.isArray(b) ? b : [b]).includes(a),
        not_in: (a, b) => !(Array.isArray(b) ? b : [b]).includes(a),
        any_of: (a, b) => b.some(item => (Array.isArray(a) ? a : [a]).includes(item)),
        all_of: (a, b) => b.every(item => (Array.isArray(a) ? a : [a]).includes(item)),
        
        // Existence operators
        exists: (a, b) => a !== null && a !== undefined && a !== '',
        not_exists: (a, b) => a === null || a === undefined || a === '',
        is_empty: (a, b) => !Boolean(a),
        is_not_empty: (a, b) => Boolean(a),
    };
    
    static evaluateCondition(condition, formData) {
        if (!condition) return true;
        
        const operator = condition.operator;
        if (!operator) return true;
        
        // Handle logical operators
        if (operator === 'and') {
            return (condition.conditions || []).every(c =>
                ConditionEvaluator.evaluateCondition(c, formData)
            );
        } else if (operator === 'or') {
            return (condition.conditions || []).some(c =>
                ConditionEvaluator.evaluateCondition(c, formData)
            );
        } else if (operator === 'not') {
            return !ConditionEvaluator.evaluateCondition(condition.condition, formData);
        }
        
        // Handle field-based operators
        const field = condition.field;
        if (!field) return true;
        
        const fieldValue = ConditionEvaluator.getFieldValue(field, formData);
        const expectedValue = condition.value;
        
        const operatorFn = ConditionEvaluator.OPERATORS[operator];
        if (!operatorFn) {
            throw new Error(`Unknown operator: ${operator}`);
        }
        
        return operatorFn(fieldValue, expectedValue);
    }
    
    static getFieldValue(fieldPath, formData) {
        if (!fieldPath.includes('.')) {
            return formData[fieldPath];
        }
        
        // Support nested field access
        let value = formData;
        for (const part of fieldPath.split('.')) {
            if (value && typeof value === 'object') {
                value = value[part];
            } else {
                return undefined;
            }
        }
        return value;
    }
}
"""
