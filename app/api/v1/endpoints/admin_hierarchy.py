"""Admin Hierarchy Management Endpoints.

This module provides FastAPI endpoints for the admin dashboard to manage
hierarchical attribute data through server-rendered Jinja2 templates.

Endpoints:
    GET /admin/hierarchy - Dashboard view with tree visualization
    GET /admin/hierarchy/node/create - Node creation form
    POST /admin/hierarchy/node/save - Save node (create or update)
    GET /admin/hierarchy/node/{node_id}/edit - Node edit form
    POST /admin/hierarchy/node/{node_id}/delete - Delete node
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Form, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError

from app.api.admin_utils import (
    FormDataProcessor,
    build_redirect_response,
    format_validation_errors,
)
from app.api.deps import get_admin_context
from app.api.types import (
    AttributeNodeRepo,
    CurrentSuperuser,
    DBSession,
    ManufacturingTypeRepo,
    OptionalBoolForm,
    OptionalIntForm,
    OptionalIntQuery,
    OptionalStrForm,
    OptionalStrQuery,
    RequiredIntForm,
    RequiredIntQuery,
    AllowEmptyStrForm,
    OptionalStrOrNoneForm,
    StrOrIntForm,
)
from app.schemas import AttributeNodeCreate, AttributeNodeUpdate
from app.schemas.responses import get_common_responses
from app.services.hierarchy_builder import HierarchyBuilderService

# Configure Jinja2 templates
templates = Jinja2Templates(directory="app/templates")

# Create router (prefix will be added in router.py)
router = APIRouter()


def _format_nodes_for_selector(nodes: list) -> list[dict]:
    """Format attribute nodes for parent selector dropdown.

    Converts nodes into a format suitable for dropdown display with
    hierarchical paths (e.g., "Frame > Material > Aluminum").

    Args:
        nodes: List of AttributeNode objects

    Returns:
        List of dicts with id, name, depth, node_type, and hierarchical_path

    Example:
        Input node with ltree_path: "frame_options.material_type.aluminum"
        Output: {
            "id": 42,
            "name": "Aluminum",
            "depth": 2,
            "node_type": "option",
            "hierarchical_path": "Frame Options > Material Type > Aluminum"
        }
    """
    formatted = []

    for node in nodes:
        # Convert ltree_path to readable hierarchical path
        # Example: "frame_options.material_type.aluminum" -> "Frame Options > Material Type > Aluminum"
        path_parts = node.ltree_path.split(".")

        # Convert each part from snake_case to Title Case
        readable_parts = []
        for part in path_parts:
            # Replace underscores with spaces and title case
            readable_part = part.replace("_", " ").title()
            readable_parts.append(readable_part)

        # Join with " > " separator
        hierarchical_path = " > ".join(readable_parts)

        formatted.append(
            {
                "id": node.id,
                "name": node.name,
                "depth": node.depth,
                "node_type": node.node_type,
                "hierarchical_path": hierarchical_path,
                "ltree_path": node.ltree_path,
            }
        )

    return formatted


@router.get(
    "/",
    response_class=HTMLResponse,
    summary="Hierarchy Management Dashboard",
    description="View and manage hierarchical attribute trees for manufacturing types",
    response_description="HTML page with hierarchy visualization",
    operation_id="hierarchyDashboard",
    responses={
        200: {
            "description": "Successfully retrieved hierarchy dashboard",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 403, 500),
    },
)
async def hierarchy_dashboard(
    request: Request,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    mfg_repo: ManufacturingTypeRepo,
    attr_repo: AttributeNodeRepo,
    manufacturing_type_id: OptionalIntQuery = None,
    success: OptionalStrQuery = None,
    error: OptionalStrQuery = None,
    warning: OptionalStrQuery = None,
    info: OptionalStrQuery = None,
):
    """Render hierarchy management dashboard.

    Displays the hierarchy management interface with tree visualization,
    ASCII representation, and diagram for a selected manufacturing type.

    Args:
        request: FastAPI request object
        current_superuser: Current authenticated superuser
        db: Database session
        mfg_repo: Manufacturing type repository
        attr_repo: Attribute node repository
        manufacturing_type_id: Optional manufacturing type ID to display
        success: Optional success message from query params
        error: Optional error message from query params
        warning: Optional warning message from query params
        info: Optional info message from query params

    Returns:
        HTMLResponse: Rendered dashboard template with hierarchy data
    """
    # Get all manufacturing types for selector
    manufacturing_types = await mfg_repo.get_active()

    # Initialize context
    context = get_admin_context(
        request,
        current_superuser,
        active_page="hierarchy",
        manufacturing_types=manufacturing_types,
        selected_type_id=manufacturing_type_id,
        selected_manufacturing_type=None,
        tree_nodes=None,
        ascii_tree=None,
        diagram_tree=None,
        # Flash messages
        success=success,
        error=error,
        warning=warning,
        info=info,
    )

    # If manufacturing type selected, get tree data
    if manufacturing_type_id:
        # Get the selected manufacturing type
        selected_mfg_type = await mfg_repo.get(manufacturing_type_id)
        if selected_mfg_type:
            context["selected_manufacturing_type"] = selected_mfg_type

            hierarchy_service = HierarchyBuilderService(db)

            # Get tree as Pydantic models
            tree = await hierarchy_service.pydantify(manufacturing_type_id)

            # Convert to dict for template
            if tree:
                context["tree_nodes"] = [node.model_dump() for node in tree]

                # Flatten tree for attribute_nodes (needed for JavaScript nodeData)
                def flatten_tree(nodes):
                    """Flatten nested tree structure into a flat list of all nodes."""
                    flat_list = []
                    for node in nodes:
                        # Add the node itself (without children to avoid circular refs)
                        node_dict = node.model_dump()
                        children = node_dict.pop("children", [])
                        flat_list.append(node_dict)
                        # Recursively add children
                        if children:
                            flat_list.extend(
                                flatten_tree([type(node)(**child) for child in children])
                            )
                    return flat_list

                context["attribute_nodes"] = flatten_tree(tree)

            # Get ASCII tree visualization
            context["ascii_tree"] = await hierarchy_service.asciify(manufacturing_type_id)

            # Get diagram tree visualization (base64 encoded image)
            try:
                import base64
                import io

                fig = await hierarchy_service.plot_tree(manufacturing_type_id)
                if fig is not None:
                    # Convert matplotlib figure to base64 PNG
                    buf = io.BytesIO()
                    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
                    buf.seek(0)
                    img_base64 = base64.b64encode(buf.read()).decode("utf-8")
                    context["diagram_tree"] = img_base64
                    buf.close()

                    # Close the figure to free memory
                    import matplotlib.pyplot as plt

                    plt.close(fig)
                else:
                    context["diagram_tree"] = None
            except Exception as e:
                # If diagram generation fails, just skip it
                print(f"Diagram generation failed: {e}")
                context["diagram_tree"] = None

    return templates.TemplateResponse(
        request=request, name="admin/hierarchy_dashboard_enhanced.html.jinja", context=context
    )


@router.get(
    "/node/create",
    response_class=HTMLResponse,
    summary="Create Node Form",
    description="Display form for creating a new attribute node",
    response_description="HTML page with node creation form",
    operation_id="createNodeForm",
    responses={
        200: {
            "description": "Successfully rendered node creation form",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        302: {
            "description": "Redirect if manufacturing type not found",
        },
        **get_common_responses(401, 403, 404, 500),
    },
)
async def create_node_form(
    request: Request,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    mfg_repo: ManufacturingTypeRepo,
    attr_repo: AttributeNodeRepo,
    manufacturing_type_id: RequiredIntQuery,
    parent_id: OptionalIntQuery = None,
):
    """Render node creation form.

    Displays an empty form for creating a new attribute node within
    a manufacturing type's hierarchy.

    Args:
        request: FastAPI request object
        current_superuser: Current authenticated superuser
        db: Database session
        mfg_repo: Manufacturing type repository
        attr_repo: Attribute node repository
        manufacturing_type_id: Manufacturing type ID (required)
        parent_id: Optional parent node ID

    Returns:
        HTMLResponse: Rendered node form template
        RedirectResponse: Redirect if manufacturing type not found
    """
    # Get manufacturing type
    manufacturing_type = await mfg_repo.get(manufacturing_type_id)
    if not manufacturing_type:
        return build_redirect_response(
            url="/api/v1/admin/hierarchy",
            message="Manufacturing type not found",
            message_type="error",
        )

    # Get parent node if provided
    parent_node = None
    if parent_id:
        parent_node = await attr_repo.get(parent_id)
        if not parent_node:
            return build_redirect_response(
                url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
                message="Parent node not found",
                message_type="error",
            )

    # Get all nodes for manufacturing type (for parent selector)
    all_nodes = await attr_repo.get_by_manufacturing_type(manufacturing_type_id)

    # Format nodes with hierarchical paths for dropdown
    formatted_nodes = _format_nodes_for_selector(all_nodes)

    context = get_admin_context(
        request,
        current_superuser,
        active_page="hierarchy",
        manufacturing_type=manufacturing_type,
        parent_node=parent_node,
        all_nodes=formatted_nodes,
        node=None,  # No existing node (create mode)
        is_edit=False,
    )

    return templates.TemplateResponse(
        request=request, name="admin/node_form.html.jinja", context=context
    )


class NodeFormDataProcessor:
    """Handles conversion and preparation of form data for node operations."""

    @classmethod
    def prepare_form_data(
        cls,
        name: str,
        node_type: str,
        parent_node_id: int | None,
        data_type: str | None,
        required: bool,
        price_impact_type: str,
        price_impact_value: str | None,
        price_formula: str | None,
        weight_impact: str,
        weight_formula: str | None,
        technical_property_type: str | None,
        technical_impact_formula: str | None,
        sort_order: int,
        ui_component: str | None,
        description: str | None,
        help_text: str | None,
        manufacturing_type_id: int | None = None,
    ) -> dict[str, Any]:
        """Prepare and normalize form data for validation.

        Uses shared FormDataProcessor for string normalization and decimal conversion.
        """
        from decimal import Decimal

        # Convert parent_node_id: empty string -> None, string number -> int
        parsed_parent_id = None
        if parent_node_id and str(parent_node_id).strip():
            try:
                parsed_parent_id = int(parent_node_id)
            except (ValueError, TypeError):
                parsed_parent_id = None

        # Convert sort_order: ensure it's an int
        parsed_sort_order = 0
        if sort_order is not None:
            try:
                parsed_sort_order = int(sort_order)
            except (ValueError, TypeError):
                parsed_sort_order = 0

        return {
            "manufacturing_type_id": manufacturing_type_id,
            "name": name,
            "node_type": node_type,
            "parent_node_id": parsed_parent_id,
            "data_type": data_type or None,
            "required": required,
            "price_impact_type": price_impact_type,
            "price_impact_value": FormDataProcessor.convert_to_decimal(price_impact_value),
            "price_formula": FormDataProcessor.normalize_optional_string(price_formula),
            "weight_impact": FormDataProcessor.convert_to_decimal(weight_impact, Decimal("0")),
            "weight_formula": FormDataProcessor.normalize_optional_string(weight_formula),
            "technical_property_type": FormDataProcessor.normalize_optional_string(
                technical_property_type
            ),
            "technical_impact_formula": FormDataProcessor.normalize_optional_string(
                technical_impact_formula
            ),
            "sort_order": parsed_sort_order,
            "ui_component": ui_component or None,
            "description": FormDataProcessor.normalize_optional_string(description),
            "help_text": FormDataProcessor.normalize_optional_string(help_text),
        }


class ValidationErrorFormatter:
    """Formats validation errors for user-friendly display."""

    @staticmethod
    def format_errors(validation_error: ValidationError) -> list[str]:
        """Convert Pydantic validation errors to readable messages.

        Uses shared format_validation_errors function for consistency.
        """
        return format_validation_errors(validation_error)


class NodeUpdater:
    """Handles updating node attributes and recalculating hierarchical properties."""

    def __init__(self, hierarchy_service, attr_repo):
        self.hierarchy_service = hierarchy_service
        self.attr_repo = attr_repo

    @staticmethod
    def update_node_fields(node, validated_data: AttributeNodeUpdate) -> None:
        """Update node fields from validated data, preserving existing values for None."""
        fields_to_update = [
            "name",
            "node_type",
            "parent_node_id",
            "data_type",
            "required",
            "price_impact_type",
            "price_impact_value",
            "price_formula",
            "weight_impact",
            "weight_formula",
            "technical_property_type",
            "technical_impact_formula",
            "sort_order",
            "ui_component",
            "description",
            "help_text",
        ]

        for field in fields_to_update:
            new_value = getattr(validated_data, field)
            if new_value is not None:
                setattr(node, field, new_value)

    async def recalculate_hierarchy(self, node, parent_node_id: int | None) -> None:
        """Recalculate node path and depth if parent changed."""
        if parent_node_id is None:
            return

        if parent_node_id:
            parent = await self.attr_repo.get(parent_node_id)
            if parent:
                node.ltree_path = self.hierarchy_service._calculate_ltree_path(parent, node.name)
                node.depth = self.hierarchy_service._calculate_depth(parent)
        else:
            node.ltree_path = self.hierarchy_service._calculate_ltree_path(None, node.name)
            node.depth = 0


class NodeFormRenderer:
    """Handles rendering of node forms with validation errors."""

    def __init__(self, templates, get_admin_context_fn, format_nodes_fn):
        self.templates = templates
        self.get_admin_context = get_admin_context_fn
        self.format_nodes = format_nodes_fn

    async def render_update_form_with_errors(
        self,
        request,
        current_superuser,
        node,
        manufacturing_type,
        all_nodes,
        validation_errors: list[str],
        form_data: dict[str, Any],
        attr_repo,
        node_id: int,
    ) -> HTMLResponse:
        """Render update form with validation errors."""
        descendants = await attr_repo.get_descendants(node_id)
        descendant_ids = {d.id for d in descendants}
        descendant_ids.add(node_id)
        available_parents = [n for n in all_nodes if n.id not in descendant_ids]
        formatted_nodes = self.format_nodes(available_parents)

        # noinspection PyTestUnpassedFixture
        context = self.get_admin_context(
            request,
            current_superuser,
            active_page="hierarchy",
            manufacturing_type=manufacturing_type,
            parent_node=None,
            all_nodes=formatted_nodes,
            node=node,
            is_edit=True,
            validation_errors=validation_errors,
            form_data=form_data,
        )

        return self.templates.TemplateResponse(
            request=request,
            name="admin/node_form.html.jinja",
            context=context,
            status_code=422,
        )

    async def render_create_form_with_errors(
        self,
        request,
        current_superuser,
        manufacturing_type,
        all_nodes,
        validation_errors: list[str],
        form_data: dict[str, Any],
    ) -> HTMLResponse:
        """Render create form with validation errors."""
        formatted_nodes = self.format_nodes(all_nodes)

        # noinspection PyTestUnpassedFixture
        context = self.get_admin_context(
            request,
            current_superuser,
            active_page="hierarchy",
            manufacturing_type=manufacturing_type,
            parent_node=None,
            all_nodes=formatted_nodes,
            node=None,
            is_edit=False,
            validation_errors=validation_errors,
            form_data=form_data,
        )

        return self.templates.TemplateResponse(
            request=request,
            name="admin/node_form.html.jinja",
            context=context,
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        )


class NodeSaveHandler:
    """Orchestrates node save operations (create and update)."""

    def __init__(self, db, attr_repo, mfg_repo, hierarchy_service, form_renderer: NodeFormRenderer):
        self.db = db
        self.attr_repo = attr_repo
        self.mfg_repo = mfg_repo
        self.hierarchy_service = hierarchy_service
        self.form_renderer = form_renderer
        self.node_updater = NodeUpdater(hierarchy_service, attr_repo)

    async def handle_update(
        self,
        request,
        current_superuser,
        node_id: int,
        manufacturing_type_id: int,
        form_data: dict[str, Any],
    ):
        """Handle node update operation."""
        # Validate data
        try:
            validated_data = AttributeNodeUpdate(**form_data)
        except ValidationError as ve:
            return await self._render_update_error(
                request, current_superuser, node_id, manufacturing_type_id, form_data, ve
            )

        # Get and verify node exists
        node = await self.attr_repo.get(node_id)
        if not node:
            return self._redirect_with_error(manufacturing_type_id, "Node not found")

        # Update node
        self.node_updater.update_node_fields(node, validated_data)
        await self.node_updater.recalculate_hierarchy(node, validated_data.parent_node_id)

        # Commit changes
        await self.db.commit()
        await self.db.refresh(node)

        return self._redirect_with_success(manufacturing_type_id, "Node updated successfully")

    async def handle_create(
        self,
        request,
        current_superuser,
        manufacturing_type_id: int,
        form_data: dict[str, Any],
    ):
        """Handle node creation operation."""
        # Add manufacturing_type_id to form data
        form_data["manufacturing_type_id"] = manufacturing_type_id

        # Validate data
        try:
            validated_data = AttributeNodeCreate(**form_data)
        except ValidationError as ve:
            return await self._render_create_error(
                request, current_superuser, manufacturing_type_id, form_data, ve
            )

        # Create node
        await self.hierarchy_service.create_node(
            manufacturing_type_id=validated_data.manufacturing_type_id,
            name=validated_data.name,
            node_type=validated_data.node_type,
            parent_node_id=validated_data.parent_node_id,
            data_type=validated_data.data_type,
            required=validated_data.required,
            price_impact_type=validated_data.price_impact_type,
            price_impact_value=validated_data.price_impact_value,
            price_formula=validated_data.price_formula,
            weight_impact=validated_data.weight_impact,
            weight_formula=validated_data.weight_formula,
            technical_property_type=validated_data.technical_property_type,
            technical_impact_formula=validated_data.technical_impact_formula,
            sort_order=validated_data.sort_order,
            ui_component=validated_data.ui_component,
            description=validated_data.description,
            help_text=validated_data.help_text,
        )

        return self._redirect_with_success(manufacturing_type_id, "Node created successfully")

    async def _render_update_error(
        self,
        request,
        current_superuser,
        node_id,
        manufacturing_type_id,
        form_data,
        validation_error,
    ):
        """Render update form with validation errors."""
        node = await self.attr_repo.get(node_id)
        manufacturing_type = await self.mfg_repo.get(manufacturing_type_id)
        all_nodes = await self.attr_repo.get_by_manufacturing_type(manufacturing_type_id)

        validation_errors = ValidationErrorFormatter.format_errors(validation_error)

        return await self.form_renderer.render_update_form_with_errors(
            request,
            current_superuser,
            node,
            manufacturing_type,
            all_nodes,
            validation_errors,
            form_data,
            self.attr_repo,
            node_id,
        )

    async def _render_create_error(
        self, request, current_superuser, manufacturing_type_id, form_data, validation_error
    ):
        """Render create form with validation errors."""
        manufacturing_type = await self.mfg_repo.get(manufacturing_type_id)
        all_nodes = await self.attr_repo.get_by_manufacturing_type(manufacturing_type_id)

        validation_errors = ValidationErrorFormatter.format_errors(validation_error)

        return await self.form_renderer.render_create_form_with_errors(
            request, current_superuser, manufacturing_type, all_nodes, validation_errors, form_data
        )

    @staticmethod
    def _redirect_with_success(manufacturing_type_id: int, message: str):
        """Create redirect response with success message."""
        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message=message,
            message_type="success",
        )

    @staticmethod
    def _redirect_with_error(manufacturing_type_id: int, message: str):
        """Create redirect response with error message."""
        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message=message,
            message_type="error",
        )


@router.post(
    "/node/save",
    summary="Save Node",
    description="Create or update an attribute node with validation",
    response_description="Redirect to hierarchy dashboard with success or error message",
    operation_id="saveNode",
    responses={
        302: {
            "description": "Redirect to hierarchy dashboard after save attempt",
        },
        422: {
            "description": "Validation error, re-render form with errors",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        **get_common_responses(401, 403, 404, 500),
    },
)
async def save_node(
    request: Request,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    attr_repo: AttributeNodeRepo,
    mfg_repo: ManufacturingTypeRepo,
    manufacturing_type_id: RequiredIntForm,
    name: AllowEmptyStrForm,  # Allow empty strings to reach validation
    node_type: AllowEmptyStrForm,  # Allow empty strings to reach validation
    node_id: OptionalIntForm = None,
    parent_node_id: OptionalStrOrNoneForm = None,
    data_type: OptionalStrForm = None,
    required: OptionalBoolForm = False,
    price_impact_type: AllowEmptyStrForm = "fixed",  # Allow empty strings
    price_impact_value: OptionalStrForm = None,
    price_formula: OptionalStrForm = None,
    weight_impact: AllowEmptyStrForm = "0",  # Allow empty strings
    weight_formula: OptionalStrForm = None,
    technical_property_type: OptionalStrForm = None,
    technical_impact_formula: OptionalStrForm = None,
    sort_order: StrOrIntForm = 0,
    ui_component: OptionalStrForm = None,
    description: OptionalStrForm = None,
    help_text: OptionalStrForm = None,
):
    """Save node (create or update) with Pydantic validation.

    Handles both node creation and updates, with proper validation,
    error handling, and user feedback. Automatically calculates LTREE
    paths and depth based on parent relationships.

    Args:
        request: FastAPI request object
        current_superuser: Current authenticated superuser
        db: Database session
        attr_repo: Attribute node repository
        mfg_repo: Manufacturing type repository
        node_id: Optional node ID (None for create, ID for update)
        manufacturing_type_id: Manufacturing type ID
        name: Node name
        node_type: Node type (category, attribute, option, etc.)
        parent_node_id: Optional parent node ID
        data_type: Data type for attribute values
        required: Whether the attribute is required
        price_impact_type: How price is affected (fixed, percentage, formula)
        price_impact_value: Price impact value
        price_formula: Dynamic pricing formula
        weight_impact: Weight impact value
        weight_formula: Dynamic weight formula
        technical_property_type: Technical property type
        technical_impact_formula: Technical impact formula
        sort_order: Display order
        ui_component: UI component type
        description: Node description
        help_text: Help text for users

    Returns:
        RedirectResponse: Redirect to hierarchy dashboard with success or error
        HTMLResponse: Re-rendered form with validation errors
    """
    try:
        # Prepare form data
        form_data = NodeFormDataProcessor.prepare_form_data(
            name=name,
            node_type=node_type,
            parent_node_id=parent_node_id,
            data_type=data_type,
            required=required,
            price_impact_type=price_impact_type,
            price_impact_value=price_impact_value,
            price_formula=price_formula,
            weight_impact=weight_impact,
            weight_formula=weight_formula,
            technical_property_type=technical_property_type,
            technical_impact_formula=technical_impact_formula,
            sort_order=sort_order,
            ui_component=ui_component,
            description=description,
            help_text=help_text,
        )

        # Initialize services
        hierarchy_service = HierarchyBuilderService(db)
        form_renderer = NodeFormRenderer(templates, get_admin_context, _format_nodes_for_selector)
        handler = NodeSaveHandler(db, attr_repo, mfg_repo, hierarchy_service, form_renderer)

        # Route to appropriate handler
        if node_id:
            return await handler.handle_update(
                request, current_superuser, node_id, manufacturing_type_id, form_data
            )
        else:
            return await handler.handle_create(
                request, current_superuser, manufacturing_type_id, form_data
            )

    except ValueError as ve:
        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message=f"Invalid numeric value: {str(ve)}",
            message_type="error",
        )
    except Exception as e:
        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message=f"Error saving node: {str(e)}",
            message_type="error",
        )


@router.get(
    "/node/{node_id}/edit",
    response_class=HTMLResponse,
    summary="Edit Node Form",
    description="Display form for editing an existing attribute node",
    response_description="HTML page with pre-filled node form",
    operation_id="editNodeForm",
    responses={
        200: {
            "description": "Successfully rendered node edit form",
            "content": {"text/html": {"example": "<html>...</html>"}},
        },
        302: {
            "description": "Redirect if node not found",
        },
        **get_common_responses(401, 403, 404, 500),
    },
)
async def edit_node_form(
    request: Request,
    node_id: int,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    mfg_repo: ManufacturingTypeRepo,
    attr_repo: AttributeNodeRepo,
):
    """Render node edit form.

    Displays a form pre-filled with existing node data for editing.
    Excludes the node itself and its descendants from the parent selector
    to prevent circular references.

    Args:
        request: FastAPI request object
        node_id: Node ID to edit
        current_superuser: Current authenticated superuser
        db: Database session
        mfg_repo: Manufacturing type repository
        attr_repo: Attribute node repository

    Returns:
        HTMLResponse: Rendered node form template with pre-filled data
        RedirectResponse: Redirect if node not found
    """
    # Get node by ID
    node = await attr_repo.get(node_id)
    if not node:
        return build_redirect_response(
            url="/api/v1/admin/hierarchy",
            message="Node not found",
            message_type="error",
        )

    # Get manufacturing type
    manufacturing_type = await mfg_repo.get(node.manufacturing_type_id)
    if not manufacturing_type:
        return build_redirect_response(
            url="/api/v1/admin/hierarchy",
            message="Manufacturing type not found",
            message_type="error",
        )

    # Get all nodes for manufacturing type (for parent selector)
    # Exclude current node and its descendants to prevent circular references
    all_nodes = await attr_repo.get_by_manufacturing_type(node.manufacturing_type_id)

    # Get descendants to exclude them from parent selector
    descendants = await attr_repo.get_descendants(node_id)
    descendant_ids = {d.id for d in descendants}
    descendant_ids.add(node_id)  # Also exclude the node itself

    # Filter out node and descendants
    available_parents = [n for n in all_nodes if n.id not in descendant_ids]

    # Format nodes with hierarchical paths for dropdown
    formatted_nodes = _format_nodes_for_selector(available_parents)

    # Get parent node if exists
    parent_node = None
    if node.parent_node_id:
        parent_node = await attr_repo.get(node.parent_node_id)

    context = get_admin_context(
        request,
        current_superuser,
        active_page="hierarchy",
        manufacturing_type=manufacturing_type,
        parent_node=parent_node,
        all_nodes=formatted_nodes,
        node=node,
        is_edit=True,
    )

    return templates.TemplateResponse(
        request=request, name="admin/node_form.html.jinja", context=context
    )


@router.post(
    "/node/{node_id}/delete",
    summary="Delete Node",
    description="Delete an attribute node (must not have children)",
    response_description="Redirect to hierarchy dashboard with success or error message",
    operation_id="deleteNode",
    responses={
        302: {
            "description": "Redirect to hierarchy dashboard after deletion attempt",
        },
        **get_common_responses(401, 403, 404, 500),
    },
)
async def delete_node(
    node_id: int,
    current_superuser: CurrentSuperuser,
    db: DBSession,
    attr_repo: AttributeNodeRepo,
):
    """Delete node.

    Removes an attribute node from the hierarchy. The node must not have
    any children - child nodes must be deleted first to prevent orphaned data.

    Args:
        node_id: Node ID to delete
        current_superuser: Current authenticated superuser
        db: Database session
        attr_repo: Attribute node repository

    Returns:
        RedirectResponse: Redirect to dashboard with success or error message
    """
    # Get node by ID
    node = await attr_repo.get(node_id)
    if not node:
        return build_redirect_response(
            url="/api/v1/admin/hierarchy",
            message="Node not found",
            message_type="error",
        )

    manufacturing_type_id = node.manufacturing_type_id

    # Check for children
    children = await attr_repo.get_children(node_id)
    if children:
        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message="Cannot delete node with children. Delete children first.",
            message_type="error",
        )

    # Delete node
    try:
        await attr_repo.delete(node_id)
        await db.commit()

        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message="Node deleted successfully",
            message_type="success",
        )

    except Exception as e:
        return build_redirect_response(
            url=f"/api/v1/admin/hierarchy?manufacturing_type_id={manufacturing_type_id}",
            message=f"Failed to delete node: {str(e)}",
            message_type="error",
        )
