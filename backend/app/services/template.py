"""Template service for business logic.

This module implements business logic for configuration template management
including template creation, application, and usage tracking.

Public Classes:
    TemplateService: Template management business logic

Features:
    - Template creation from configurations
    - Template application to create configurations
    - Template usage tracking
    - Template metrics calculation
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import PositiveInt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import Permission, Privilege, Role, require
from app.models.configuration import Configuration
from app.models.configuration_template import ConfigurationTemplate
from app.models.template_selection import TemplateSelection
from app.repositories.attribute_node import AttributeNodeRepository
from app.repositories.configuration import ConfigurationRepository
from app.repositories.configuration_selection import ConfigurationSelectionRepository
from app.repositories.configuration_template import ConfigurationTemplateRepository
from app.repositories.template_selection import TemplateSelectionRepository
from app.schemas.configuration import ConfigurationCreate
from app.schemas.configuration_selection import ConfigurationSelectionValue
from app.schemas.configuration_template import (
    ConfigurationTemplateCreate,
    ConfigurationTemplateUpdate,
)
from app.services.base import BaseService
from app.services.configuration import ConfigurationService
from app.services.rbac import RBACService

__all__ = ["TemplateService"]


# Define reusable Privilege objects for Template Service operations
TemplateManagement = Privilege(
    roles=[Role.DATA_ENTRY, Role.SALESMAN], permission=Permission("template", "create")
)

TemplateReader = Privilege(
    roles=[Role.CUSTOMER, Role.SALESMAN, Role.PARTNER, Role.DATA_ENTRY],
    permission=Permission("template", "read"),
)

AdminTemplateAccess = Privilege(roles=Role.SUPERADMIN, permission=Permission("*", "*"))


class TemplateService(BaseService):
    """Template service for business logic.

    Handles template management operations including creation,
    application, and usage tracking.

    Attributes:
        db: Database session
        template_repo: Configuration template repository
        template_selection_repo: Template selection repository
        config_repo: Configuration repository
        config_selection_repo: Configuration selection repository
        attr_node_repo: Attribute node repository
        config_service: Configuration service for creating configurations
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize template service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.template_repo = ConfigurationTemplateRepository(db)
        self.template_selection_repo = TemplateSelectionRepository(db)
        self.config_repo = ConfigurationRepository(db)
        self.config_selection_repo = ConfigurationSelectionRepository(db)
        self.attr_node_repo = AttributeNodeRepository(db)
        self.config_service = ConfigurationService(db)
        self.rbac_service = RBACService(db)

    async def create_template_from_configuration(
        self,
        config_id: int,
        template_name: str,
        template_description: str | None = None,
        template_type: str = "standard",
        is_public: bool = True,
        created_by: int | None = None,
    ) -> ConfigurationTemplate:
        """Create a template from an existing configuration.

        Copies all selections from the configuration to create a reusable template.

        Args:
            config_id (int): Configuration ID to copy from
            template_name (str): Name for the new template
            template_description (str | None): Optional description
            template_type (str): Template type (standard, premium, economy, custom)
            is_public (bool): Whether template is visible to customers
            created_by (int | None): User ID of creator

        Returns:
            ConfigurationTemplate: Created template instance

        Raises:
            NotFoundException: If configuration not found
            ValidationException: If configuration is invalid
        """
        # Get configuration with selections
        config = await self.config_service.get_configuration_with_details(config_id)

        # Create template
        template_data = ConfigurationTemplateCreate(
            name=template_name,
            description=template_description,
            manufacturing_type_id=config.manufacturing_type_id,
            template_type=template_type,
            is_public=is_public,
            estimated_price=config.total_price,
            estimated_weight=config.calculated_weight,
            created_by=created_by,
        )

        template = await self.template_repo.create(template_data)
        await self.commit()
        await self.refresh(template)

        # Copy selections from configuration to template
        for selection in config.selections:
            # Get attribute node for ltree path
            attr_node = await self.attr_node_repo.get(selection.attribute_node_id)
            if not attr_node:
                continue

            template_selection = TemplateSelection(
                template_id=template.id,
                attribute_node_id=selection.attribute_node_id,
                string_value=selection.string_value,
                numeric_value=selection.numeric_value,
                boolean_value=selection.boolean_value,
                json_value=selection.json_value,
                selection_path=attr_node.ltree_path,
            )

            self.template_selection_repo.db.add(template_selection)

        await self.commit()
        await self.refresh(template)

        return template

    @require(Permission("template", "apply"))
    async def apply_template_to_configuration(
        self,
        template_id: int,
        user: Any,
        config_name: str | None = None,
    ) -> Configuration:
        """Apply a template to create a new configuration with proper customer relationship.

        Creates a new configuration with all selections from the template.

        Args:
            template_id (int): Template ID to apply
            user (Any): Current user (for customer relationship)
            config_name (str | None): Optional configuration name

        Returns:
            Configuration: Created configuration instance

        Raises:
            NotFoundException: If template not found
            ValidationException: If template is invalid
        """
        # Get template with selections
        template = await self.template_repo.get(template_id)
        if not template:
            raise NotFoundException(
                resource="ConfigurationTemplate",
                details={"template_id": template_id},
            )

        # Validate template is active
        if not template.is_active:
            raise ValidationException(
                message="Template is not active",
                details={"template_id": template_id},
            )

        # Get template selections
        template_selections = await self.template_selection_repo.get_by_template(template_id)

        # Create configuration name if not provided
        if not config_name:
            config_name = f"{template.name} - Copy"

        # Get or create customer for user using RBAC service
        customer = await self.rbac_service.get_or_create_customer_for_user(user)

        # Create configuration without selections first
        config_data = ConfigurationCreate(
            name=config_name,
            manufacturing_type_id=template.manufacturing_type_id,
            customer_id=customer.id,  # Use proper customer ID
        )

        config = await self.config_service.create_configuration(config_data, user)

        # Add selections from template to the new configuration
        for ts in template_selections:
            selection_value = ConfigurationSelectionValue(
                attribute_node_id=ts.attribute_node_id,
                string_value=ts.string_value,
                numeric_value=ts.numeric_value,
                boolean_value=ts.boolean_value,
                json_value=ts.json_value,
            )
            # Add each selection to the configuration
            await self.config_service.add_selection(config.id, selection_value)

        # Recalculate totals after adding all selections
        if template_selections:
            await self.config_service.calculate_totals(config.id)
            await self.refresh(config)

        # Track template usage with proper customer association
        await self.track_template_usage(template_id, config.id, customer.id)

        return config

    async def track_template_usage(
        self,
        template_id: int,
        config_id: int,
        customer_id: int | None = None,
    ) -> None:
        """Track template usage.

        Increments the template's usage count.

        Args:
            template_id (int): Template ID
            config_id (int): Configuration ID created from template
            customer_id (int | None): Optional customer ID

        Raises:
            NotFoundException: If template not found
        """
        template = await self.template_repo.get(template_id)
        if not template:
            raise NotFoundException(
                resource="ConfigurationTemplate",
                details={"template_id": template_id},
            )

        # Increment usage count
        template.usage_count += 1

        await self.commit()
        await self.refresh(template)

        # TODO: Create TemplateUsage record when model is available
        # This would track:
        # - template_id
        # - configuration_id
        # - customer_id
        # - used_by (user_id)
        # - usage_type
        # - converted_to_quote
        # - converted_to_order

    @require(TemplateReader)
    @require(AdminTemplateAccess)
    async def get_template(
        self, template_id: PositiveInt, user: Any = None
    ) -> ConfigurationTemplate:
        """Get template by ID.

        Args:
            template_id (PositiveInt): Template ID

        Returns:
            ConfigurationTemplate: Template instance

        Raises:
            NotFoundException: If template not found
        """
        template = await self.template_repo.get(template_id)
        if not template:
            raise NotFoundException(
                resource="ConfigurationTemplate",
                details={"template_id": template_id},
            )
        return template

    async def update_template(
        self, template_id: PositiveInt, template_update: ConfigurationTemplateUpdate
    ) -> ConfigurationTemplate:
        """Update template.

        Args:
            template_id (PositiveInt): Template ID
            template_update (ConfigurationTemplateUpdate): Update data

        Returns:
            ConfigurationTemplate: Updated template instance

        Raises:
            NotFoundException: If template not found
        """
        template = await self.get_template(template_id)

        # Update template fields
        update_data = template_update.model_dump(exclude_unset=True)
        updated_template = await self.template_repo.update(template, update_data)

        await self.commit()
        await self.refresh(updated_template)

        return updated_template

    async def delete_template(self, template_id: PositiveInt) -> None:
        """Delete a template.

        Deletes the template and all related selections (cascade).

        Args:
            template_id (PositiveInt): Template ID

        Raises:
            NotFoundException: If template not found
        """
        template = await self.get_template(template_id)
        await self.template_repo.delete(template.id)
        await self.commit()

    async def deactivate_template(self, template_id: PositiveInt) -> ConfigurationTemplate:
        """Deactivate a template (soft delete).

        Args:
            template_id (PositiveInt): Template ID

        Returns:
            ConfigurationTemplate: Updated template instance

        Raises:
            NotFoundException: If template not found
        """
        template = await self.get_template(template_id)
        template.is_active = False

        await self.commit()
        await self.refresh(template)

        return template

    async def list_templates(
        self,
        skip: int = 0,
        limit: int = 100,
        manufacturing_type_id: int | None = None,
        template_type: str | None = None,
        is_public: bool | None = None,
        is_active: bool = True,
    ) -> list[ConfigurationTemplate]:
        """List templates with filters.

        Args:
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            manufacturing_type_id (int | None): Filter by manufacturing type
            template_type (str | None): Filter by template type
            is_public (bool | None): Filter by public visibility
            is_active (bool): Filter by active status (default True)

        Returns:
            list[ConfigurationTemplate]: List of templates
        """
        if manufacturing_type_id:
            templates = await self.template_repo.get_by_manufacturing_type(manufacturing_type_id)
        elif is_public is not None and is_public:
            templates = await self.template_repo.get_public_templates()
        else:
            templates = await self.template_repo.get_multi(skip=skip, limit=limit)

        # Apply additional filters
        if template_type:
            templates = [t for t in templates if t.template_type == template_type]

        if is_active:
            templates = [t for t in templates if t.is_active]

        return templates

    async def get_popular_templates(self, limit: int = 10) -> list[ConfigurationTemplate]:
        """Get most popular templates by usage count.

        Args:
            limit (int): Maximum number of templates to return

        Returns:
            list[ConfigurationTemplate]: List of popular templates
        """
        return await self.template_repo.get_popular(limit=limit)

    async def update_template_estimates(self, template_id: PositiveInt) -> ConfigurationTemplate:
        """Update template estimated price and weight.

        Recalculates estimates based on current template selections.

        Args:
            template_id (PositiveInt): Template ID

        Returns:
            ConfigurationTemplate: Updated template instance

        Raises:
            NotFoundException: If template not found
        """
        template = await self.get_template(template_id)

        # Get template selections
        selections = await self.template_selection_repo.get_by_template(template_id)

        # Calculate estimated price and weight
        # Start with base from manufacturing type
        estimated_price = Decimal("0")
        estimated_weight = Decimal("0")

        if template.manufacturing_type:
            estimated_price = template.manufacturing_type.base_price
            estimated_weight = template.manufacturing_type.base_weight

        # Add impacts from selections
        for selection in selections:
            attr_node = await self.attr_node_repo.get(selection.attribute_node_id)
            if not attr_node:
                continue

            # Add price impact
            if attr_node.price_impact_value:
                estimated_price += attr_node.price_impact_value

            # Add weight impact
            if attr_node.weight_impact:
                estimated_weight += attr_node.weight_impact

        # Update template
        template.estimated_price = estimated_price
        template.estimated_weight = estimated_weight

        await self.commit()
        await self.refresh(template)

        return template

    @require(TemplateManagement)
    @require(AdminTemplateAccess)
    async def create_template(
        self, template_in: ConfigurationTemplateCreate, user: Any
    ) -> ConfigurationTemplate:
        """Create template with user association.

        Args:
            template_in (ConfigurationTemplateCreate): Template creation data
            user: Current user

        Returns:
            ConfigurationTemplate: Created template

        Raises:
            NotFoundException: If manufacturing type not found
        """
        from app.core.exceptions import NotFoundException
        from app.repositories.manufacturing_type import ManufacturingTypeRepository

        mfg_type_repo = ManufacturingTypeRepository(self.db)

        # Validate manufacturing type exists
        mfg_type = await mfg_type_repo.get(template_in.manufacturing_type_id)
        if not mfg_type:
            raise NotFoundException(
                resource="ManufacturingType",
                details={"manufacturing_type_id": template_in.manufacturing_type_id},
            )

        # Create template
        template_data = template_in.model_dump()
        template_data["created_by"] = user.id

        template = ConfigurationTemplate(**template_data)
        self.template_repo.db.add(template)
        await self.db.commit()
        await self.db.refresh(template)

        return template

    async def apply_template(
        self, template_id: PositiveInt, user: Any, configuration_name: str | None = None
    ) -> Configuration:
        """Apply template to create new configuration.

        Args:
            template_id (PositiveInt): Template ID
            user: Current user
            configuration_name (str | None): Name for new configuration

        Returns:
            Configuration: Created configuration

        Raises:
            NotFoundException: If template not found
        """
        from app.core.exceptions import NotFoundException
        from app.services.configuration import ConfigurationService

        # Get template with selections
        template = await self.template_repo.get_with_selections(template_id)
        if not template:
            raise NotFoundException(
                resource="ConfigurationTemplate",
                details={"template_id": template_id},
            )

        # Create configuration from template
        config_service = ConfigurationService(self.db)

        # Build configuration data
        from app.schemas.configuration import ConfigurationCreate

        # Create configuration without selections first
        config_in = ConfigurationCreate(
            manufacturing_type_id=template.manufacturing_type_id,
            customer_id=user.id,
            name=configuration_name or f"{template.name} - Copy",
            description=f"Created from template: {template.name}",
        )

        config = await config_service.create_configuration(config_in, user)

        # Add selections from template to the new configuration
        for ts in template.selections:
            selection_value = ConfigurationSelectionValue(
                attribute_node_id=ts.attribute_node_id,
                string_value=ts.string_value,
                numeric_value=ts.numeric_value,
                boolean_value=ts.boolean_value,
                json_value=ts.json_value,
            )
            await config_service.add_selection(config.id, selection_value)

        # Recalculate totals after adding all selections
        if template.selections:
            await config_service.calculate_totals(config.id)
            # Refresh config to get updated totals
            from sqlalchemy import select

            result = await self.db.execute(
                select(Configuration).where(Configuration.id == config.id)
            )
            config = result.scalar_one()

        # Track template usage
        await self.track_template_usage(template_id, config.id, user.id)

        return config
