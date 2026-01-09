"""Configuration service for business logic.

This module implements business logic for configuration management including
creation, updates, selection management, and calculations.

Public Classes:
    ConfigurationService: Configuration management business logic

Features:
    - Configuration creation with initial selections
    - Selection management (add, update, remove)
    - Price and weight calculation
    - Configuration validation
    - Detailed configuration retrieval
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import PositiveInt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import Permission, Privilege, ResourceOwnership, Role, require
from app.models.configuration import Configuration
from app.models.configuration_selection import ConfigurationSelection
from app.repositories.attribute_node import AttributeNodeRepository
from app.repositories.configuration import ConfigurationRepository
from app.repositories.configuration_selection import ConfigurationSelectionRepository
from app.repositories.manufacturing_type import ManufacturingTypeRepository
from app.schemas.configuration import ConfigurationCreate, ConfigurationUpdate
from app.schemas.configuration_selection import (
    ConfigurationSelectionCreate,
    ConfigurationSelectionValue,
)
from app.services.base import BaseService
from app.services.pricing import PricingService
from app.services.rbac import RBACService

__all__ = ["ConfigurationService"]


# Define reusable Privilege objects for Configuration Service operations
ConfigurationManagement = Privilege(
    roles=[Role.SALESMAN, Role.PARTNER],
    permission=Permission("configuration", "update"),
    resource=ResourceOwnership("customer", id_param="customer_id"),
)

ConfigurationOwnership = Privilege(
    roles=Role.CUSTOMER,
    permission=Permission("configuration", "update"),
    resource=ResourceOwnership("configuration", id_param="config_id"),
)

ConfigurationReader = Privilege(
    roles=[Role.CUSTOMER, Role.SALESMAN, Role.PARTNER],
    permission=Permission("configuration", "read"),
    resource=ResourceOwnership("configuration", id_param="config_id"),
)

AdminPrivileges = Privilege(roles=Role.SUPERADMIN, permission=Permission("*", "*"))


class ConfigurationService(BaseService):
    """Configuration service for business logic.

    Handles configuration management operations including creation,
    updates, selection management, and calculations.

    Attributes:
        db: Database session
        config_repo: Configuration repository
        selection_repo: Configuration selection repository
        mfg_type_repo: Manufacturing type repository
        attr_node_repo: Attribute node repository
        pricing_service: Pricing service for calculations
    """

    def __init__(self, db: AsyncSession) -> None:
        """Initialize configuration service.

        Args:
            db (AsyncSession): Database session
        """
        super().__init__(db)
        self.config_repo = ConfigurationRepository(db)
        self.selection_repo = ConfigurationSelectionRepository(db)
        self.mfg_type_repo = ManufacturingTypeRepository(db)
        self.attr_node_repo = AttributeNodeRepository(db)
        self.pricing_service = PricingService(db)
        self.rbac_service = RBACService(db)

    @require(Permission("configuration", "read"))
    async def get_configuration(self, config_id: PositiveInt, user: Any = None) -> Configuration:
        """Get configuration by ID.

        Args:
            config_id (PositiveInt): Configuration ID

        Returns:
            Configuration: Configuration instance

        Raises:
            NotFoundException: If configuration not found
        """
        config = await self.config_repo.get(config_id)
        if not config:
            raise NotFoundException(
                resource="Configuration",
                details={"config_id": config_id},
            )
        return config

    @require(ConfigurationReader)
    async def get_configuration_with_details(
        self, config_id: PositiveInt, user: Any = None
    ) -> Configuration:
        """Get configuration with full selection data.

        Loads configuration with all related data including selections,
        manufacturing type, and customer.

        Args:
            config_id (PositiveInt): Configuration ID

        Returns:
            Configuration: Configuration with loaded relationships

        Raises:
            NotFoundException: If configuration not found
        """
        result = await self.db.execute(
            select(Configuration)
            .where(Configuration.id == config_id)
            .options(
                selectinload(Configuration.selections),
                selectinload(Configuration.manufacturing_type),
                selectinload(Configuration.customer),
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            raise NotFoundException(
                resource="Configuration",
                details={"config_id": config_id},
            )

        return config

    async def add_selection(
        self, config_id: PositiveInt, selection_value: ConfigurationSelectionValue
    ) -> ConfigurationSelection:
        """Add a single selection to a configuration.

        Args:
            config_id (PositiveInt): Configuration ID
            selection_value (ConfigurationSelectionValue): Selection data

        Returns:
            ConfigurationSelection: Created selection

        Raises:
            NotFoundException: If configuration or attribute node not found
            ConflictException: If selection already exists
            ValidationException: If selection is invalid
        """
        # Verify configuration exists
        await self.get_configuration(config_id)

        # Add selection
        selection = await self._add_selection_internal(config_id, selection_value)

        # Recalculate totals
        await self.calculate_totals(config_id)

        return selection

    async def _add_selection_internal(
        self, config_id: int, selection_value: ConfigurationSelectionValue
    ) -> ConfigurationSelection:
        """Internal method to add a selection without recalculating totals.

        Args:
            config_id (int): Configuration ID
            selection_value (ConfigurationSelectionValue): Selection data

        Returns:
            ConfigurationSelection: Created selection

        Raises:
            NotFoundException: If attribute node not found
            ValidationException: If selection is invalid
        """
        # Validate attribute node exists
        attr_node = await self.attr_node_repo.get(selection_value.attribute_node_id)
        if not attr_node:
            raise NotFoundException(
                resource="AttributeNode",
                details={"attribute_node_id": selection_value.attribute_node_id},
            )

        # Create selection with ltree path from attribute node
        selection_data = selection_value.model_dump()
        selection = ConfigurationSelection(
            configuration_id=config_id,
            **selection_data,
            selection_path=attr_node.ltree_path,
        )

        # Calculate impacts
        impacts = await self.pricing_service.calculate_selection_impact(selection)
        selection.calculated_price_impact = impacts["price_impact"]
        selection.calculated_weight_impact = impacts["weight_impact"]

        self.selection_repo.db.add(selection)
        await self.commit()
        await self.refresh(selection)

        return selection

    async def remove_selection(self, config_id: PositiveInt, selection_id: PositiveInt) -> None:
        """Remove a selection from a configuration.

        Args:
            config_id (PositiveInt): Configuration ID
            selection_id (PositiveInt): Selection ID

        Raises:
            NotFoundException: If configuration or selection not found
        """
        # Verify configuration exists
        await self.get_configuration(config_id)

        # Get and verify selection belongs to configuration
        selection = await self.selection_repo.get(selection_id)
        if not selection:
            raise NotFoundException(
                resource="ConfigurationSelection",
                details={"selection_id": selection_id},
            )

        if selection.configuration_id != config_id:
            raise ValidationException(
                message="Selection does not belong to this configuration",
                details={
                    "selection_id": selection_id,
                    "config_id": config_id,
                    "selection_config_id": selection.configuration_id,
                },
            )

        # Delete selection
        await self.selection_repo.delete(selection_id)
        await self.commit()

        # Recalculate totals
        await self.calculate_totals(config_id)

    async def calculate_totals(self, config_id: PositiveInt) -> dict[str, Decimal]:
        """Calculate and update total price and weight for a configuration.

        Recalculates the configuration's total price and weight based on
        the base values and all selection impacts.

        Args:
            config_id (PositiveInt): Configuration ID

        Returns:
            dict[str, Decimal]: Dictionary with total_price and total_weight

        Raises:
            NotFoundException: If configuration not found
        """
        config = await self.get_configuration(config_id)

        # Calculate totals using pricing service
        totals = await self.pricing_service.calculate_configuration_price(config_id)

        # Update configuration
        config.total_price = totals["total_price"]
        config.calculated_weight = totals["total_weight"]

        await self.commit()
        await self.refresh(config)

        return totals

    @require(Permission("configuration", "read"))
    async def list_configurations(
        self,
        user: Any,
        skip: int = 0,
        limit: int = 100,
        manufacturing_type_id: int | None = None,
        customer_id: int | None = None,
        status: str | None = None,
    ) -> list[Configuration]:
        """List configurations with automatic RBAC filtering.

        Args:
            user: Current user for RBAC filtering
            skip (int): Number of records to skip
            limit (int): Maximum number of records to return
            manufacturing_type_id (int | None): Filter by manufacturing type
            customer_id (int | None): Filter by customer
            status (str | None): Filter by status

        Returns:
            list[Configuration]: List of configurations accessible to user
        """
        query = select(Configuration)

        # Apply RBAC filtering using the same database session
        # Get accessible customers for user using existing session
        accessible_customers = await self.rbac_service.get_accessible_customers(user)

        if user.role != Role.SUPERADMIN.value:
            if not accessible_customers:
                # User has no accessible customers - return empty result
                query = query.where(False)
            else:
                # Filter by accessible customers
                query = query.where(Configuration.customer_id.in_(accessible_customers))

        if manufacturing_type_id:
            query = query.where(Configuration.manufacturing_type_id == manufacturing_type_id)

        if customer_id:
            query = query.where(Configuration.customer_id == customer_id)

        if status:
            query = query.where(Configuration.status == status)

        query = query.offset(skip).limit(limit).order_by(Configuration.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    @staticmethod
    def get_user_configurations_query(
        user: Any,
        manufacturing_type_id: int | None = None,
        status: str | None = None,
    ):
        """Build query for user's configurations with authorization.

        Regular users see only their own configurations.
        Superusers see all configurations.

        Args:
            user: Current user
            manufacturing_type_id (int | None): Filter by manufacturing type
            status (str | None): Filter by status

        Returns:
            Select: SQLAlchemy select statement
        """
        from sqlalchemy import Select, select

        query: Select = select(Configuration)

        # Authorization: regular users see only their own
        if not user.is_superuser:
            query = query.where(Configuration.customer_id == user.id)

        # Apply filters
        if manufacturing_type_id is not None:
            query = query.where(Configuration.manufacturing_type_id == manufacturing_type_id)

        if status:
            query = query.where(Configuration.status == status)

        # Order by most recent first
        query = query.order_by(Configuration.created_at.desc())

        return query

    async def get_configuration_with_auth(self, config_id: PositiveInt, user: Any) -> Configuration:
        """Get configuration with authorization check.

        Users can only access their own configurations unless they are superusers.

        Args:
            config_id (PositiveInt): Configuration ID
            user: Current user

        Returns:
            Configuration: Configuration with selections

        Raises:
            NotFoundException: If configuration not found
            AuthorizationException: If user lacks permission
        """
        from app.core.exceptions import AuthorizationException

        config = await self.get_configuration_with_details(config_id, user)

        # Authorization check using RBAC service
        accessible_customers = await self.rbac_service.get_accessible_customers(user)
        if user.role != Role.SUPERADMIN.value and config.customer_id not in accessible_customers:
            raise AuthorizationException("You do not have permission to access this configuration")

        return config

    @require(ConfigurationManagement)  # Salesmen can update configurations for their customers
    @require(ConfigurationOwnership)  # Customers can update their own configurations
    @require(AdminPrivileges)  # Superadmins can update any configuration
    async def update_configuration(
        self, config_id: PositiveInt, config_update: ConfigurationUpdate, user: Any
    ) -> Configuration:
        """Update configuration with Casbin authorization.

        Args:
            config_id (PositiveInt): Configuration ID
            config_update (ConfigurationUpdate): Update data
            user: Current user

        Returns:
            Configuration: Updated configuration

        Raises:
            NotFoundException: If configuration not found
            HTTPException: 403 if user lacks permission (handled by Casbin decorator)
        """
        config = await self.get_configuration(config_id, user)

        # Update configuration fields
        update_data = config_update.model_dump(exclude_unset=True, exclude={"selections"})
        for field, value in update_data.items():
            setattr(config, field, value)

        await self.commit()
        await self.refresh(config)

        return config

    @require(ConfigurationManagement)  # Salesmen can update selections for their customers
    @require(ConfigurationOwnership)  # Customers can update their own selections
    @require(AdminPrivileges)  # Superadmins can update any selections
    async def update_selections(
        self, config_id: PositiveInt, selections: list[ConfigurationSelectionCreate], user: Any
    ) -> Configuration:
        """Update selections with Casbin authorization.

        Args:
            config_id (PositiveInt): Configuration ID
            selections (list[ConfigurationSelectionCreate]): New selections
            user: Current user

        Returns:
            Configuration: Updated configuration

        Raises:
            NotFoundException: If configuration not found
            HTTPException: 403 if user lacks permission (handled by Casbin decorator)
        """
        config = await self.get_configuration(config_id, user)

        # Delete existing selections
        await self.selection_repo.delete_by_configuration(config_id)

        # Add new selections
        for selection_value in selections:
            await self._add_selection_internal(config_id, selection_value)

        # Recalculate totals
        await self.calculate_totals(config_id)

        await self.refresh(config)
        return config

    @require(ConfigurationManagement)  # Salesmen can delete configurations for their customers
    @require(ConfigurationOwnership)  # Customers can delete their own configurations
    @require(AdminPrivileges)  # Superadmins can delete any configuration
    async def delete_configuration(self, config_id: PositiveInt, user: Any) -> None:
        """Delete configuration with Casbin authorization.

        Args:
            config_id (PositiveInt): Configuration ID
            user: Current user

        Raises:
            NotFoundException: If configuration not found
            HTTPException: 403 if user lacks permission (handled by Casbin decorator)
        """
        config = await self.get_configuration(config_id, user)

        await self.config_repo.delete(config_id)
        await self.commit()

    @require(Permission("configuration", "create"))
    async def create_configuration(
        self, config_in: ConfigurationCreate, user: Any
    ) -> Configuration:
        """Create new configuration with proper customer relationship.

        Args:
            config_in (ConfigurationCreate): Configuration creation data
            user: Current user

        Returns:
            Configuration: Created configuration

        Raises:
            NotFoundException: If manufacturing type not found
        """
        # Validate manufacturing type exists
        mfg_type = await self.mfg_type_repo.get(config_in.manufacturing_type_id)
        if not mfg_type:
            raise NotFoundException(
                resource="ManufacturingType",
                details={"manufacturing_type_id": config_in.manufacturing_type_id},
            )

        # Get or create customer for user using RBAC service
        customer = await self.rbac_service.get_or_create_customer_for_user(user)

        # Create configuration with base price from manufacturing type
        config_data = config_in.model_dump(exclude={"selections"})
        config_data["customer_id"] = customer.id  # Use proper customer ID

        config = Configuration(
            **config_data,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            calculated_weight=mfg_type.base_weight,
        )

        self.config_repo.db.add(config)
        await self.commit()
        await self.refresh(config)

        # Add initial selections if provided
        if hasattr(config_in, "selections") and config_in.selections:
            for selection_value in config_in.selections:
                await self._add_selection_internal(config.id, selection_value)

            # Recalculate totals after adding selections
            await self.calculate_totals(config.id)

        return config
