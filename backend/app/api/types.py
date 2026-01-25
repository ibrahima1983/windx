"""API type aliases and dependencies.

This module provides reusable type aliases for common dependencies used
throughout the API endpoints. Using these aliases improves code readability,
reduces boilerplate, and ensures consistency.

Public Type Aliases:
    DBSession: Database session dependency
    CurrentUser: Current authenticated user dependency
    CurrentSuperuser: Current superuser dependency
    UserRepo: User repository dependency
    SessionRepo: Session repository dependency
    ManufacturingTypeRepo: Manufacturing type repository dependency
    AttributeNodeRepo: Attribute node repository dependency
    ConfigurationRepo: Configuration repository dependency
    ConfigurationSelectionRepo: Configuration selection repository dependency
    CustomerRepo: Customer repository dependency
    QuoteRepo: Quote repository dependency
    ConfigurationTemplateRepo: Configuration template repository dependency
    TemplateSelectionRepo: Template selection repository dependency
    OrderRepo: Order repository dependency

Features:
    - Type-safe dependencies with Annotated
    - Comprehensive docstrings for IDE support
    - Consistent dependency injection patterns
    - Reduced boilerplate in endpoints
    - Full Windx configurator system support
"""

from __future__ import annotations

from typing import Annotated, Optional, Union

from fastapi import Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import User
from app.repositories.attribute_node import AttributeNodeRepository
from app.repositories.configuration import ConfigurationRepository
from app.repositories.configuration_selection import ConfigurationSelectionRepository
from app.repositories.configuration_template import ConfigurationTemplateRepository
from app.repositories.customer import CustomerRepository
from app.repositories.manufacturing_type import ManufacturingTypeRepository
from app.repositories.order import OrderRepository
from app.repositories.quote import QuoteRepository
from app.repositories.session import SessionRepository
from app.repositories.template_selection import TemplateSelectionRepository
from app.repositories.user import UserRepository

# TODO: i think some of these types below is un-used

__all__ = [
    "DBSession",
    "CurrentUser",
    "CurrentSuperuser",
    "UserRepo",
    "SessionRepo",
    "ManufacturingTypeRepo",
    "AttributeNodeRepo",
    "ConfigurationRepo",
    "ConfigurationSelectionRepo",
    "CustomerRepo",
    "QuoteRepo",
    "ConfigurationTemplateRepo",
    "TemplateSelectionRepo",
    "OrderRepo",
    # Query parameter types
    "OptionalIntQuery",
    "RequiredIntQuery",
    "OptionalStrQuery",
    "RequiredStrQuery",
    "IsSuperuserQuery",
    "IsActiveQuery",
    "SearchQuery",
    "PageQuery",
    "PageSizeQuery",
    "SortOrderQuery",
    # Form parameter types
    "OptionalIntForm",
    "RequiredIntForm",
    "OptionalStrForm",
    "RequiredStrForm",
    "AllowEmptyStrForm",
    "OptionalStrOrNoneForm",
    "StrOrIntForm",
    "OptionalBoolForm",
    "RequiredBoolForm",
]


# ============================================================================
# Database Session Type Aliases
# ============================================================================

DBSession = Annotated[AsyncSession, Depends(get_db)]
"""Database session dependency.

Provides a SQLAlchemy async session for database operations.
Automatically handles session lifecycle (commit, rollback, close).

Usage:
    ```python
    @router.get("/items")
    async def list_items(db: DBSession):
        result = await db.execute(select(Item))
        return result.scalars().all()
    ```

Example:
    ```python
    from app.api.types import DBSession

    @router.post("/users", response_model=UserSchema)
    async def create_user(
        user_in: UserCreate,
        db: DBSession,
    ) -> User:
        user_repo = UserRepository(db)
        return await user_repo.create(user_in)
    ```
"""


# ============================================================================
# Query Parameter Type Aliases
# ============================================================================

OptionalIntQuery = Annotated[Optional[int], Query()]
"""Optional integer query parameter.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        manufacturing_type_id: OptionalIntQuery = None,
    ):
        # manufacturing_type_id is optional
        pass
    ```
"""

RequiredIntQuery = Annotated[int, Query()]
"""Required integer query parameter.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        manufacturing_type_id: RequiredIntQuery,
    ):
        # manufacturing_type_id is required
        pass
    ```
"""

OptionalStrQuery = Annotated[Optional[str], Query()]
"""Optional string query parameter.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        search: OptionalStrQuery = None,
    ):
        # search is optional
        pass
    ```
"""

RequiredStrQuery = Annotated[str, Query()]
"""Required string query parameter.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        name: RequiredStrQuery,
    ):
        # name is required
        pass
    ```
"""

IsSuperuserQuery = Annotated[Optional[bool], Query()]
"""Optional boolean query parameter for filtering by superuser status.

Usage:
    ```python
    @router.get("/users")
    async def list_users(
        is_superuser: IsSuperuserQuery = None,
    ):
        # Filter users by superuser status if provided
        pass
    ```
"""

IsActiveQuery = Annotated[Optional[bool], Query()]
"""Optional boolean query parameter for filtering by active status.

Usage:
    ```python
    @router.get("/customers")
    async def list_customers(
        is_active: IsActiveQuery = None,
    ):
        # Filter customers by active status if provided
        pass
    ```
"""

SearchQuery = Annotated[Optional[str], Query(min_length=1, max_length=200)]
"""Optional string query parameter for search with validation.

Validates that search string is between 1 and 200 characters.

Usage:
    ```python
    @router.get("/customers")
    async def list_customers(
        search: SearchQuery = None,
    ):
        # Search customers by name, email, etc.
        pass
    ```
"""

PageQuery = Annotated[int, Query(ge=1)]
"""Required integer query parameter for pagination page number.

Validates that page number is >= 1.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        page: PageQuery = 1,
    ):
        # page is validated to be >= 1
        pass
    ```
"""

PageSizeQuery = Annotated[int, Query(ge=1, le=100)]
"""Required integer query parameter for pagination page size.

Validates that page size is between 1 and 100.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        page_size: PageSizeQuery = 50,
    ):
        # page_size is validated to be between 1 and 100
        pass
    ```
"""

SortOrderQuery = Annotated[str, Query(pattern="^(asc|desc)$")]
"""Required string query parameter for sort order.

Validates that sort order is either 'asc' or 'desc'.

Usage:
    ```python
    @router.get("/items")
    async def list_items(
        sort_order: SortOrderQuery = "asc",
    ):
        # sort_order is validated to be 'asc' or 'desc'
        pass
    ```
"""


# ============================================================================
# Form Parameter Type Aliases
# ============================================================================

OptionalIntForm = Annotated[Optional[int], Form()]
"""Optional integer form parameter.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        node_id: OptionalIntForm = None,
    ):
        # node_id is optional
        pass
    ```
"""

RequiredIntForm = Annotated[int, Form()]
"""Required integer form parameter.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        manufacturing_type_id: RequiredIntForm,
    ):
        # manufacturing_type_id is required
        pass
    ```
"""

OptionalStrForm = Annotated[Optional[str], Form()]
"""Optional string form parameter.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        description: OptionalStrForm = None,
    ):
        # description is optional
        pass
    ```
"""

RequiredStrForm = Annotated[str, Form()]
"""Required string form parameter.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        name: RequiredStrForm,
    ):
        # name is required
        pass
    ```
"""

AllowEmptyStrForm = Annotated[str, Form()]
"""String form parameter that allows empty strings.

This type allows empty strings to pass through FastAPI validation
so they can be validated by Pydantic schemas with custom error messages.
Use this when you want to provide better validation error messages
for empty/invalid strings rather than FastAPI's default "field required" error.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        name: AllowEmptyStrForm,  # Allows "" to reach Pydantic validation
    ):
        # name can be empty string, will be validated by Pydantic schema
        pass
    ```
"""

OptionalStrOrNoneForm = Annotated[Optional[str], Form()]
"""Optional string form parameter that can be None or string.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        parent_id: OptionalStrOrNoneForm = None,
    ):
        # parent_id can be None or string
        pass
    ```
"""

StrOrIntForm = Annotated[Union[str, int], Form()]
"""Form parameter that accepts either string or integer.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        sort_order: StrOrIntForm = 0,
    ):
        # sort_order can be string or int
        pass
    ```
"""

OptionalBoolForm = Annotated[bool, Form()]
"""Optional boolean form parameter (defaults to False).

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        required: OptionalBoolForm = False,
    ):
        # required is optional, defaults to False
        pass
    ```
"""

RequiredBoolForm = Annotated[bool, Form()]
"""Required boolean form parameter.

Usage:
    ```python
    @router.post("/items")
    async def create_item(
        is_active: RequiredBoolForm,
    ):
        # is_active is required
        pass
    ```
"""


# ============================================================================
# Authentication Type Aliases
# ============================================================================


def _get_current_user_dep():
    """Import dependency to avoid circular imports."""
    from app.api.deps import get_current_user

    return get_current_user


def _get_current_superuser_dep():
    """Import dependency to avoid circular imports."""
    from app.api.deps import get_current_active_superuser

    return get_current_active_superuser


CurrentUser = Annotated[User, Depends(_get_current_user_dep())]
"""Current authenticated user dependency.

Provides the currently authenticated user from JWT token.
Raises 401 if token is invalid or user not found.
Raises 400 if user is inactive.

Usage:
    ```python
    @router.get("/me")
    async def get_current_user_info(current_user: CurrentUser):
        return current_user
    ```

Example:
    ```python
    from app.api.types import CurrentUser, DBSession

    @router.patch("/me", response_model=UserSchema)
    async def update_current_user(
        user_update: UserUpdate,
        current_user: CurrentUser,
        db: DBSession,
    ) -> User:
        user_repo = UserRepository(db)
        return await user_repo.update(current_user, user_update)
    ```
"""

CurrentSuperuser = Annotated[User, Depends(_get_current_superuser_dep())]
"""Current superuser dependency.

Provides the currently authenticated superuser.
Raises 401 if token is invalid or user not found.
Raises 403 if user is not a superuser.

Usage:
    ```python
    @router.delete("/users/{user_id}")
    async def delete_user(
        user_id: int,
        current_superuser: CurrentSuperuser,
        db: DBSession,
    ):
        user_repo = UserRepository(db)
        await user_repo.delete(user_id)
    ```

Example:
    ```python
    from app.api.types import CurrentSuperuser, DBSession

    @router.get("/admin/users", response_model=list[UserSchema])
    async def list_all_users(
        current_superuser: CurrentSuperuser,
        db: DBSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[User]:
        user_repo = UserRepository(db)
        return await user_repo.get_multi(skip=skip, limit=limit)
    ```
"""




# ============================================================================
# Repository Type Aliases
# ============================================================================


def get_user_repository(db: DBSession) -> UserRepository:
    """Get user repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        UserRepository: User repository instance
    """
    return UserRepository(db)


def get_session_repository(db: DBSession) -> SessionRepository:
    """Get session repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        SessionRepository: Session repository instance
    """
    return SessionRepository(db)


UserRepo = Annotated[UserRepository, Depends(get_user_repository)]
"""User repository dependency.

Provides access to user data access layer with repository pattern.
Includes methods for user CRUD operations and custom queries.

Usage:
    ```python
    @router.get("/users/{user_id}")
    async def get_user(user_id: int, user_repo: UserRepo):
        return await user_repo.get(user_id)
    ```

Example:
    ```python
    from app.api.types import UserRepo, CurrentSuperuser

    @router.get("/users/email/{email}", response_model=UserSchema)
    async def get_user_by_email(
        email: str,
        user_repo: UserRepo,
        current_superuser: CurrentSuperuser,
    ) -> User:
        user = await user_repo.get_by_email(email)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user
    ```

Available Methods:
    - get(id): Get user by ID
    - get_by_email(email): Get user by email
    - get_by_username(username): Get user by username
    - get_multi(skip, limit): Get multiple users with pagination
    - get_active_users(skip, limit): Get active users only
    - create(obj_in): Create new user
    - update(db_obj, obj_in): Update existing user
    - delete(id): Delete user by ID
"""

SessionRepo = Annotated[SessionRepository, Depends(get_session_repository)]
"""Session repository dependency.

Provides access to session data access layer with repository pattern.
Includes methods for session CRUD operations and token validation.

Usage:
    ```python
    @router.get("/sessions")
    async def list_sessions(
        session_repo: SessionRepo,
        current_user: CurrentUser,
    ):
        return await session_repo.get_user_sessions(current_user.id)
    ```

Example:
    ```python
    from app.api.types import SessionRepo, CurrentUser

    @router.delete("/sessions/{session_id}")
    async def delete_session(
        session_id: int,
        session_repo: SessionRepo,
        current_user: CurrentUser,
    ):
        session = await session_repo.get(session_id)
        if not session or session.user_id != current_user.id:
            raise HTTPException(status_code=404, detail="Session not found")
        await session_repo.delete(session_id)
        return {"message": "Session deleted"}
    ```

Available Methods:
    - get(id): Get session by ID
    - get_by_token(token): Get session by token
    - get_active_by_token(token): Get active session by token
    - get_user_sessions(user_id, active_only): Get all user sessions
    - deactivate_session(token): Deactivate a session
    - create(obj_in): Create new session
    - update(db_obj, obj_in): Update existing session
    - delete(id): Delete session by ID
"""


# ============================================================================
# Windx Repository Type Aliases
# ============================================================================


def get_manufacturing_type_repository(db: DBSession) -> ManufacturingTypeRepository:
    """Get manufacturing type repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        ManufacturingTypeRepository: Manufacturing type repository instance
    """
    return ManufacturingTypeRepository(db)


def get_attribute_node_repository(db: DBSession) -> AttributeNodeRepository:
    """Get attribute node repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        AttributeNodeRepository: Attribute node repository instance
    """
    return AttributeNodeRepository(db)


def get_configuration_repository(db: DBSession) -> ConfigurationRepository:
    """Get configuration repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        ConfigurationRepository: Configuration repository instance
    """
    return ConfigurationRepository(db)


def get_configuration_selection_repository(
    db: DBSession,
) -> ConfigurationSelectionRepository:
    """Get configuration selection repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        ConfigurationSelectionRepository: Configuration selection repository instance
    """
    return ConfigurationSelectionRepository(db)


def get_customer_repository(db: DBSession) -> CustomerRepository:
    """Get customer repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        CustomerRepository: Customer repository instance
    """
    return CustomerRepository(db)


def get_quote_repository(db: DBSession) -> QuoteRepository:
    """Get quote repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        QuoteRepository: Quote repository instance
    """
    return QuoteRepository(db)


def get_configuration_template_repository(
    db: DBSession,
) -> ConfigurationTemplateRepository:
    """Get configuration template repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        ConfigurationTemplateRepository: Configuration template repository instance
    """
    return ConfigurationTemplateRepository(db)


def get_template_selection_repository(db: DBSession) -> TemplateSelectionRepository:
    """Get template selection repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        TemplateSelectionRepository: Template selection repository instance
    """
    return TemplateSelectionRepository(db)


def get_order_repository(db: DBSession) -> OrderRepository:
    """Get order repository instance.

    Args:
        db (AsyncSession): Database session

    Returns:
        OrderRepository: Order repository instance
    """
    return OrderRepository(db)


ManufacturingTypeRepo = Annotated[
    ManufacturingTypeRepository, Depends(get_manufacturing_type_repository)
]
"""Manufacturing type repository dependency.

Provides access to manufacturing type data access layer with repository pattern.
Includes methods for product category CRUD operations and custom queries.

Usage:
    ```python
    @router.get("/manufacturing-types")
    async def list_manufacturing_types(mfg_repo: ManufacturingTypeRepo):
        return await mfg_repo.get_active()
    ```

Example:
    ```python
    from app.api.types import ManufacturingTypeRepo, CurrentSuperuser

    @router.post("/manufacturing-types", response_model=ManufacturingTypeSchema)
    async def create_manufacturing_type(
        mfg_in: ManufacturingTypeCreate,
        mfg_repo: ManufacturingTypeRepo,
        current_superuser: CurrentSuperuser,
    ):
        return await mfg_repo.create(mfg_in)
    ```

Available Methods:
    - get(id): Get manufacturing type by ID
    - get_by_name(name): Get manufacturing type by name
    - get_active(): Get all active manufacturing types
    - get_by_category(category): Get manufacturing types by category
    - get_multi(skip, limit): Get multiple manufacturing types with pagination
    - create(obj_in): Create new manufacturing type
    - update(db_obj, obj_in): Update existing manufacturing type
    - delete(id): Delete manufacturing type by ID
"""

AttributeNodeRepo = Annotated[AttributeNodeRepository, Depends(get_attribute_node_repository)]
"""Attribute node repository dependency.

Provides access to hierarchical attribute node data with LTREE support.
Includes methods for tree traversal, descendant/ancestor queries, and CRUD operations.

Usage:
    ```python
    @router.get("/attribute-nodes/tree/{type_id}")
    async def get_attribute_tree(
        type_id: int,
        attr_repo: AttributeNodeRepo,
    ):
        return await attr_repo.get_by_manufacturing_type(type_id)
    ```

Example:
    ```python
    from app.api.types import AttributeNodeRepo, CurrentSuperuser

    @router.get("/attribute-nodes/{node_id}/descendants")
    async def get_node_descendants(
        node_id: int,
        attr_repo: AttributeNodeRepo,
        current_superuser: CurrentSuperuser,
    ):
        return await attr_repo.get_descendants(node_id)
    ```

Available Methods:
    - get(id): Get attribute node by ID
    - get_by_manufacturing_type(type_id): Get all nodes for a manufacturing type
    - get_root_nodes(type_id): Get top-level nodes for a manufacturing type
    - get_children(parent_id): Get direct children of a node
    - get_descendants(node_id): Get all descendants using LTREE
    - get_ancestors(node_id): Get all ancestors using LTREE
    - get_tree(root_id): Get entire tree structure
    - create(obj_in): Create new attribute node
    - update(db_obj, obj_in): Update existing attribute node
    - delete(id): Delete attribute node by ID
"""

ConfigurationRepo = Annotated[ConfigurationRepository, Depends(get_configuration_repository)]
"""Configuration repository dependency.

Provides access to customer product configuration data access layer.
Includes methods for configuration CRUD, selection management, and calculations.

Usage:
    ```python
    @router.get("/configurations")
    async def list_configurations(
        config_repo: ConfigurationRepo,
        current_user: CurrentUser,
    ):
        return await config_repo.get_by_customer(current_user.id)
    ```

Example:
    ```python
    from app.api.types import ConfigurationRepo, CurrentUser

    @router.post("/configurations", response_model=ConfigurationSchema)
    async def create_configuration(
        config_in: ConfigurationCreate,
        config_repo: ConfigurationRepo,
        current_user: CurrentUser,
    ):
        return await config_repo.create(config_in)
    ```

Available Methods:
    - get(id): Get configuration by ID
    - get_by_customer(customer_id): Get all configurations for a customer
    - get_by_manufacturing_type(type_id): Get configurations by product type
    - get_by_status(status): Get configurations by status
    - get_with_selections(config_id): Get configuration with all selections
    - get_multi(skip, limit): Get multiple configurations with pagination
    - create(obj_in): Create new configuration
    - update(db_obj, obj_in): Update existing configuration
    - delete(id): Delete configuration by ID
"""

ConfigurationSelectionRepo = Annotated[
    ConfigurationSelectionRepository, Depends(get_configuration_selection_repository)
]
"""Configuration selection repository dependency.

Provides access to individual attribute selections within configurations.
Includes methods for selection CRUD and bulk operations.

Usage:
    ```python
    @router.get("/configurations/{config_id}/selections")
    async def get_selections(
        config_id: int,
        selection_repo: ConfigurationSelectionRepo,
    ):
        return await selection_repo.get_by_configuration(config_id)
    ```

Example:
    ```python
    from app.api.types import ConfigurationSelectionRepo

    @router.post("/configurations/{config_id}/selections")
    async def add_selection(
        config_id: int,
        selection_in: ConfigurationSelectionCreate,
        selection_repo: ConfigurationSelectionRepo,
    ):
        return await selection_repo.create(selection_in)
    ```

Available Methods:
    - get(id): Get selection by ID
    - get_by_configuration(config_id): Get all selections for a configuration
    - get_by_attribute_node(node_id): Get selections for an attribute node
    - bulk_create(selections): Create multiple selections at once
    - delete_by_configuration(config_id): Delete all selections for a configuration
    - create(obj_in): Create new selection
    - update(db_obj, obj_in): Update existing selection
    - delete(id): Delete selection by ID
"""

CustomerRepo = Annotated[CustomerRepository, Depends(get_customer_repository)]
"""Customer repository dependency.

Provides access to customer data access layer with repository pattern.
Includes methods for customer CRUD operations and custom queries.

Usage:
    ```python
    @router.get("/customers")
    async def list_customers(
        customer_repo: CustomerRepo,
        current_superuser: CurrentSuperuser,
    ):
        return await customer_repo.get_active()
    ```

Example:
    ```python
    from app.api.types import CustomerRepo, CurrentSuperuser

    @router.get("/customers/email/{email}")
    async def get_customer_by_email(
        email: str,
        customer_repo: CustomerRepo,
        current_superuser: CurrentSuperuser,
    ):
        customer = await customer_repo.get_by_email(email)
        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found")
        return customer
    ```

Available Methods:
    - get(id): Get customer by ID
    - get_by_email(email): Get customer by email
    - get_active(): Get all active customers
    - get_multi(skip, limit): Get multiple customers with pagination
    - create(obj_in): Create new customer
    - update(db_obj, obj_in): Update existing customer
    - delete(id): Delete customer by ID
"""

QuoteRepo = Annotated[QuoteRepository, Depends(get_quote_repository)]
"""Quote repository dependency.

Provides access to quote data access layer with repository pattern.
Includes methods for quote CRUD, snapshot management, and status tracking.

Usage:
    ```python
    @router.get("/quotes")
    async def list_quotes(
        quote_repo: QuoteRepo,
        current_user: CurrentUser,
    ):
        return await quote_repo.get_by_customer(current_user.id)
    ```

Example:
    ```python
    from app.api.types import QuoteRepo, CurrentUser

    @router.post("/quotes", response_model=QuoteSchema)
    async def create_quote(
        quote_in: QuoteCreate,
        quote_repo: QuoteRepo,
        current_user: CurrentUser,
    ):
        return await quote_repo.create(quote_in)
    ```

Available Methods:
    - get(id): Get quote by ID
    - get_by_quote_number(number): Get quote by quote number
    - get_by_customer(customer_id): Get all quotes for a customer
    - get_by_configuration(config_id): Get quotes for a configuration
    - get_by_status(status): Get quotes by status
    - get_multi(skip, limit): Get multiple quotes with pagination
    - create(obj_in): Create new quote
    - update(db_obj, obj_in): Update existing quote
    - delete(id): Delete quote by ID
"""

ConfigurationTemplateRepo = Annotated[
    ConfigurationTemplateRepository, Depends(get_configuration_template_repository)
]
"""Configuration template repository dependency.

Provides access to pre-defined configuration templates.
Includes methods for template CRUD, usage tracking, and metrics.

Usage:
    ```python
    @router.get("/templates")
    async def list_templates(template_repo: ConfigurationTemplateRepo):
        return await template_repo.get_public_templates()
    ```

Example:
    ```python
    from app.api.types import ConfigurationTemplateRepo, CurrentUser

    @router.post("/templates/{template_id}/apply")
    async def apply_template(
        template_id: int,
        template_repo: ConfigurationTemplateRepo,
        current_user: CurrentUser,
    ):
        template = await template_repo.get(template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        # Apply template logic here
        return {"message": "Template applied"}
    ```

Available Methods:
    - get(id): Get template by ID
    - get_by_manufacturing_type(type_id): Get templates for a product type
    - get_public_templates(): Get all public templates
    - get_active(): Get all active templates
    - increment_usage_count(template_id): Increment template usage counter
    - get_multi(skip, limit): Get multiple templates with pagination
    - create(obj_in): Create new template
    - update(db_obj, obj_in): Update existing template
    - delete(id): Delete template by ID
"""

TemplateSelectionRepo = Annotated[
    TemplateSelectionRepository, Depends(get_template_selection_repository)
]
"""Template selection repository dependency.

Provides access to pre-defined attribute selections within templates.
Includes methods for selection CRUD and bulk operations.

Usage:
    ```python
    @router.get("/templates/{template_id}/selections")
    async def get_template_selections(
        template_id: int,
        selection_repo: TemplateSelectionRepo,
    ):
        return await selection_repo.get_by_template(template_id)
    ```

Example:
    ```python
    from app.api.types import TemplateSelectionRepo

    @router.post("/templates/{template_id}/selections")
    async def add_template_selection(
        template_id: int,
        selection_in: TemplateSelectionCreate,
        selection_repo: TemplateSelectionRepo,
    ):
        return await selection_repo.create(selection_in)
    ```

Available Methods:
    - get(id): Get template selection by ID
    - get_by_template(template_id): Get all selections for a template
    - bulk_create(selections): Create multiple selections at once
    - delete_by_template(template_id): Delete all selections for a template
    - create(obj_in): Create new template selection
    - update(db_obj, obj_in): Update existing template selection
    - delete(id): Delete template selection by ID
"""

OrderRepo = Annotated[OrderRepository, Depends(get_order_repository)]
"""Order repository dependency.

Provides access to order data access layer with repository pattern.
Includes methods for order CRUD, item management, and status tracking.

Usage:
    ```python
    @router.get("/orders")
    async def list_orders(
        order_repo: OrderRepo,
        current_user: CurrentUser,
    ):
        return await order_repo.get_by_customer(current_user.id)
    ```

Example:
    ```python
    from app.api.types import OrderRepo, CurrentUser

    @router.post("/orders", response_model=OrderSchema)
    async def create_order(
        order_in: OrderCreate,
        order_repo: OrderRepo,
        current_user: CurrentUser,
    ):
        return await order_repo.create(order_in)
    ```

Available Methods:
    - get(id): Get order by ID
    - get_by_order_number(number): Get order by order number
    - get_by_quote(quote_id): Get order by quote
    - get_by_status(status): Get orders by status
    - get_with_items(order_id): Get order with all items
    - get_multi(skip, limit): Get multiple orders with pagination
    - create(obj_in): Create new order
    - update(db_obj, obj_in): Update existing order
    - delete(id): Delete order by ID
"""
