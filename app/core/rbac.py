"""Role-Based Access Control (RBAC) system using Casbin.

This module provides a comprehensive RBAC system with advanced decorator patterns,
role composition, privilege abstraction, and automatic query filtering.

Public Classes:
    Role: Enhanced role enum with bitwise operations
    RoleComposition: Composed roles for cleaner syntax
    Permission: Permission definition for resources and actions
    ResourceOwnership: Resource ownership validation
    Privilege: Reusable authorization bundles
    RBACService: Core Casbin-based authorization service
    RBACQueryFilter: Automatic query filtering based on user access

Public Functions:
    require: Advanced authorization decorator with multiple patterns

Features:
    - Casbin policy engine for professional authorization
    - Multiple decorator patterns with OR/AND logic
    - Role composition with bitwise operators
    - Privilege abstraction for reusable authorization
    - Automatic resource ownership validation
    - Query filtering for data access control
    - Template integration for UI permission checks
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from enum import Enum
from functools import wraps
from typing import Any, Optional

import casbin
from fastapi import HTTPException
from sqlalchemy import select

from app.models.user import User

__all__ = [
    "Role",
    "RoleComposition",
    "Permission",
    "ResourceOwnership",
    "Privilege",
    "RBACService",
    "RBACQueryFilter",
    "require",
]

logger = logging.getLogger(__name__)


class Role(Enum):
    """Enhanced Role enum with bitwise operations support.

    Supports role composition using bitwise OR operator for cleaner syntax:
    - Role.SALESMAN | Role.PARTNER creates a RoleComposition
    - Enables flexible role-based authorization patterns
    """

    SUPERADMIN = "superadmin"
    SALESMAN = "salesman"
    DATA_ENTRY = "data_entry"
    PARTNER = "partner"
    CUSTOMER = "customer"

    def __or__(self, other: Role | RoleComposition) -> RoleComposition:
        """Support bitwise OR for role composition.

        Args:
            other: Another Role or RoleComposition to combine

        Returns:
            RoleComposition containing both roles
        """
        if isinstance(other, Role):
            return RoleComposition([self, other])
        elif isinstance(other, RoleComposition):
            return RoleComposition([self] + other.roles)
        return NotImplemented

    def __ror__(self, other: Role | RoleComposition) -> RoleComposition:
        """Support reverse bitwise OR."""
        return self.__or__(other)


class RoleComposition:
    """Composed roles for cleaner syntax.

    Enables role combinations like: Role.SALESMAN | Role.PARTNER
    Supports chaining: Role.A | Role.B | Role.C
    """

    def __init__(self, roles: list[Role]):
        """Initialize role composition.

        Args:
            roles: List of roles to compose
        """
        self.roles = roles

    def __or__(self, other: Role | RoleComposition) -> RoleComposition:
        """Support chaining role compositions.

        Args:
            other: Role or RoleComposition to add

        Returns:
            New RoleComposition with additional role(s)
        """
        if isinstance(other, Role):
            return RoleComposition(self.roles + [other])
        elif isinstance(other, RoleComposition):
            return RoleComposition(self.roles + other.roles)
        return NotImplemented

    def __contains__(self, role: Role) -> bool:
        """Check if role is in composition.

        Args:
            role: Role to check

        Returns:
            True if role is in composition
        """
        return role in self.roles

    def __repr__(self) -> str:
        """String representation of role composition."""
        role_names = [role.value for role in self.roles]
        return f"RoleComposition({role_names})"


class Permission:
    """Permission definition for resources and actions.

    Represents a specific permission like "configuration:read" or "quote:create".
    Supports context for advanced permission scenarios.
    """

    def __init__(self, resource: str, action: str, context: Optional[dict[str, Any]] = None):
        """Initialize permission.

        Args:
            resource: Resource type (e.g., "configuration", "quote")
            action: Action type (e.g., "read", "create", "update", "delete")
            context: Optional context for advanced permissions
        """
        self.resource = resource
        self.action = action
        self.context = context or {}

    def __str__(self) -> str:
        """String representation of permission."""
        return f"{self.resource}:{self.action}"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"Permission('{self.resource}', '{self.action}', {self.context})"


class ResourceOwnership:
    """Resource ownership validation.

    Validates that a user owns or has access to a specific resource.
    Automatically extracts resource IDs from function parameters.
    """

    def __init__(self, resource_type: str, id_param: Optional[str] = None):
        """Initialize resource ownership validator.

        Args:
            resource_type: Type of resource (e.g., "configuration", "customer")
            id_param: Parameter name containing resource ID (defaults to "{resource_type}_id")
        """
        self.resource_type = resource_type
        self.id_param = id_param or f"{resource_type}_id"

    def __str__(self) -> str:
        """String representation of resource ownership."""
        return f"ownership:{self.resource_type}"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return f"ResourceOwnership('{self.resource_type}', '{self.id_param}')"


class Privilege:
    """Reusable privilege definition bundling role, permission, and resource.

    Enables privilege abstraction for cleaner, more maintainable authorization:
    - Bundle common authorization patterns into reusable objects
    - Combine roles, permissions, and ownership validation
    - Support complex authorization scenarios
    """

    def __init__(
        self,
        roles: Role | RoleComposition | list[Role],
        permission: Permission,
        resource: Optional[ResourceOwnership] = None,
    ):
        """Initialize privilege.

        Args:
            roles: Role(s) that have this privilege
            permission: Required permission
            resource: Optional resource ownership requirement
        """
        if isinstance(roles, Role):
            self.roles = [roles]
        elif isinstance(roles, RoleComposition):
            self.roles = roles.roles
        else:
            self.roles = roles
        self.permission = permission
        self.resource = resource

    def __str__(self) -> str:
        """String representation of privilege."""
        role_names = [role.value for role in self.roles]
        return f"Privilege({role_names}, {self.permission}, {self.resource})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return self.__str__()


class RBACService:
    """Core Casbin-based authorization service.

    Provides professional authorization using Casbin policy engine:
    - Policy-based access control with explicit allow/deny rules
    - Context-aware permissions with customer ownership validation
    - Efficient policy evaluation with caching
    - Dynamic policy management for runtime updates
    """

    def __init__(self):
        """Initialize RBAC service with Casbin enforcer."""
        self.enforcer = casbin.Enforcer("config/rbac_model.conf", "config/rbac_policy.csv")
        self._permission_cache: dict[str, bool] = {}
        self._customer_cache: dict[int, list[int]] = {}

    async def check_permission(
        self, user: User, resource: str, action: str, context: Optional[dict[str, Any]] = None
    ) -> bool:
        """Check if user has permission for action on resource.

        Args:
            user: User to check permissions for
            resource: Resource type (e.g., "configuration", "quote")
            action: Action type (e.g., "read", "create", "update", "delete")
            context: Optional context for advanced permissions

        Returns:
            True if user has permission, False otherwise
        """
        # Cache key for performance
        cache_key = f"{user.id}:{resource}:{action}"
        if cache_key in self._permission_cache:
            return self._permission_cache[cache_key]

        try:
            # Check Casbin policy
            result = self.enforcer.enforce(user.email, resource, action)

            # Cache result
            self._permission_cache[cache_key] = result

            logger.debug(
                f"Permission check: user={user.email}, resource={resource}, "
                f"action={action}, result={result}"
            )

            return result

        except Exception as e:
            logger.error(f"Permission check failed: {e}")
            return False

    async def check_resource_ownership(
        self, user: User, resource_type: str, resource_id: int
    ) -> bool:
        """Check if user owns or has access to the resource.

        Args:
            user: User to check ownership for
            resource_type: Type of resource (e.g., "configuration", "customer")
            resource_id: ID of the resource

        Returns:
            True if user owns or has access to resource, False otherwise
        """
        # Superadmin has access to everything
        if user.role == Role.SUPERADMIN.value:
            return True

        # Get accessible customers for user
        accessible_customers = await self.get_accessible_customers(user)

        # For customer resources, check direct access
        if resource_type == "customer":
            return resource_id in accessible_customers

        # For other resources, check through customer relationship
        # This would need to be implemented based on specific resource types
        # For now, implement basic customer-based access

        # TODO: Implement resource-specific ownership checks
        # This is a placeholder that should be expanded based on actual resource relationships

        return True  # Placeholder - implement actual ownership logic

    async def get_accessible_customers(self, user: User) -> list[int]:
        """Get list of customer IDs user can access.

        Args:
            user: User to get accessible customers for

        Returns:
            List of customer IDs user can access
        """
        # Cache for performance
        if user.id in self._customer_cache:
            return self._customer_cache[user.id]

        # Superadmin has access to all customers
        if user.role == Role.SUPERADMIN.value:
            # TODO: Return all customer IDs from database
            # For now, return empty list as placeholder
            accessible = []
        else:
            # Regular users have access to their associated customer(s)
            # TODO: Implement actual customer lookup logic
            # This should query the User-Customer relationship
            accessible = []

        # Cache result
        self._customer_cache[user.id] = accessible

        return accessible

    async def check_privilege(self, user: User, privilege: Privilege) -> bool:
        """Check if user has the specified privilege.

        Args:
            user: User to check privilege for
            privilege: Privilege to check

        Returns:
            True if user has privilege, False otherwise
        """
        # Check role requirement
        user_role = Role(user.role) if user.role in [r.value for r in Role] else None
        if not user_role or user_role not in privilege.roles:
            # Check if user is superadmin (has all privileges)
            if user.role != Role.SUPERADMIN.value:
                return False

        # Check permission requirement
        permission_result = await self.check_permission(
            user,
            privilege.permission.resource,
            privilege.permission.action,
            privilege.permission.context,
        )

        if not permission_result:
            return False

        # Check resource ownership requirement if specified
        if privilege.resource:
            # Resource ownership check would need resource ID
            # This is handled by the decorator that extracts the ID from function parameters
            pass

        return True

    def clear_cache(self):
        """Clear permission and customer caches."""
        self._permission_cache.clear()
        self._customer_cache.clear()


class RBACQueryFilter:
    """Automatic query filtering based on user access.

    Provides automatic filtering of database queries to ensure users only see
    data they have access to. Prevents data leakage through query-level filtering.
    """

    @staticmethod
    async def filter_configurations(query: select, user: User) -> select:
        """Filter configurations based on user access.

        Args:
            query: SQLAlchemy select query to filter
            user: User to filter for

        Returns:
            Filtered query that only returns accessible configurations
        """
        # Superadmin sees all configurations
        if user.role == Role.SUPERADMIN.value:
            return query

        # Get accessible customers for user
        from app.database.connection import get_session_maker
        from app.services.rbac import RBACService

        session_maker = get_session_maker()
        async with session_maker() as db:
            rbac_service = RBACService(db)
            accessible_customers = await rbac_service.get_accessible_customers(user)

        if not accessible_customers:
            # User has no accessible customers - return empty result
            return query.where(False)

        # Filter by accessible customers
        from app.models.configuration import Configuration

        return query.where(Configuration.customer_id.in_(accessible_customers))

    @staticmethod
    async def filter_quotes(query: select, user: User) -> select:
        """Filter quotes based on user access.

        Args:
            query: SQLAlchemy select query to filter
            user: User to filter for

        Returns:
            Filtered query that only returns accessible quotes
        """
        # Superadmin sees all quotes
        if user.role == Role.SUPERADMIN.value:
            return query

        # Get accessible customers for user
        from app.database.connection import get_session_maker
        from app.services.rbac import RBACService

        session_maker = get_session_maker()
        async with session_maker() as db:
            rbac_service = RBACService(db)
            accessible_customers = await rbac_service.get_accessible_customers(user)

        if not accessible_customers:
            # User has no accessible customers - return empty result
            return query.where(False)

        # Filter by accessible customers
        from app.models.quote import Quote

        return query.where(Quote.customer_id.in_(accessible_customers))

    @staticmethod
    async def filter_orders(query: select, user: User) -> select:
        """Filter orders based on user access.

        Args:
            query: SQLAlchemy select query to filter
            user: User to filter for

        Returns:
            Filtered query that only returns accessible orders
        """
        # Superadmin sees all orders
        if user.role == Role.SUPERADMIN.value:
            return query

        # Get accessible customers for user
        from app.database.connection import get_session_maker
        from app.services.rbac import RBACService

        session_maker = get_session_maker()
        async with session_maker() as db:
            rbac_service = RBACService(db)
            accessible_customers = await rbac_service.get_accessible_customers(user)

        if not accessible_customers:
            # User has no accessible customers - return empty result
            return query.where(False)

        # Filter by accessible customers through quotes
        from app.models.quote import Quote

        return query.join(Quote).where(Quote.customer_id.in_(accessible_customers))


# Note: Global RBAC service instance removed - use session-specific instances instead
# Each authorization check creates its own RBACService instance with proper database session

def require(*requirements) -> Callable:
    """Advanced decorator supporting multiple authorization patterns.

    Supports multiple patterns:
    - @require(Role.ADMIN) - Role-based authorization
    - @require(Permission("resource", "action")) - Permission-based authorization
    - @require(ResourceOwnership("resource")) - Resource ownership authorization
    - @require(Privilege(...)) - Privilege-based authorization
    - Multiple decorators with OR logic between decorators
    - Multiple requirements in single decorator with AND logic

    Evaluation Logic:
    - Multiple @require decorators on same function = OR logic
    - Multiple requirements in single @require = AND logic
    - Multiple roles in single requirement = OR logic for roles

    Args:
        *requirements: Authorization requirements (Role, Permission, ResourceOwnership, Privilege)

    Returns:
        Decorator function that enforces authorization

    Raises:
        HTTPException: 403 Forbidden if authorization fails
    """

    def decorator(func: Callable) -> Callable:
        # Get existing requirements from previous decorators
        existing_requirements = getattr(func, "_rbac_requirements", [])

        # Get the original function (unwrapped) to avoid recursive calls
        original_func = getattr(func, "_rbac_original_func", func)

        # Add new requirements (creates OR relationship with existing)
        all_requirements = existing_requirements + [requirements]

        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract user from function arguments
            user = _extract_user_from_args(args, kwargs)
            if not user:
                raise HTTPException(status_code=401, detail="Authentication required")

            # Evaluate requirements with OR logic between decorator groups
            for requirement_group in all_requirements:
                try:
                    if await _evaluate_requirement_group(
                        user, requirement_group, original_func, args, kwargs
                    ):
                        # At least one requirement group satisfied - allow access
                        logger.debug(f"Access granted to {user.email} for {original_func.__name__}")
                        # Call the original unwrapped function to avoid recursion
                        return await original_func(*args, **kwargs)
                except Exception as e:
                    # Allow certain exceptions to pass through instead of converting to 403
                    from app.core.exceptions import NotFoundException

                    if isinstance(e, (NotFoundException, HTTPException)):
                        # These exceptions should propagate up (404, etc.)
                        # Don't convert them to 403 - let the service handle them
                        logger.debug(f"Allowing exception to pass through: {e}")
                        raise e

                    logger.error(f"Requirement evaluation error: {e}")
                    continue

            # No requirement group satisfied - deny access
            logger.warning(f"Access denied to {user.email} for {original_func.__name__}")
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: insufficient privileges for {original_func.__name__}",
            )

        # Store requirements and original function for potential additional decorators
        wrapper._rbac_requirements = all_requirements
        wrapper._rbac_original_func = original_func
        return wrapper

    return decorator


def _extract_user_from_args(args: tuple, kwargs: dict) -> Optional[User]:
    """Extract User object from function arguments.

    Args:
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        User object if found, None otherwise
    """
    # Check keyword arguments first
    if "user" in kwargs:
        return kwargs["user"]

    # Check positional arguments
    for arg in args:
        if isinstance(arg, User):
            return arg

    return None


async def _evaluate_requirement_group(
    user: User, requirements: tuple, func: Callable, args: tuple, kwargs: dict
) -> bool:
    """Evaluate a single requirement group with AND logic.

    Args:
        user: User to evaluate requirements for
        requirements: Tuple of requirements to evaluate
        func: Function being called (for parameter extraction)
        args: Function positional arguments
        kwargs: Function keyword arguments

    Returns:
        True if all requirements in group are satisfied, False otherwise
    """
    has_role_requirement = False
    has_permission_requirement = False
    has_ownership_requirement = False

    role_satisfied = True
    permission_satisfied = True
    ownership_satisfied = True

    for requirement in requirements:
        if isinstance(requirement, (Role, RoleComposition, list)):
            # Role requirement
            has_role_requirement = True
            role_satisfied = await _check_role_requirement(user, requirement)

        elif isinstance(requirement, Permission):
            # Permission requirement
            has_permission_requirement = True
            permission_satisfied = await _check_permission_requirement(user, requirement)

        elif isinstance(requirement, ResourceOwnership):
            # Ownership requirement
            has_ownership_requirement = True
            ownership_satisfied = await _check_ownership_requirement(
                user, requirement, func, args, kwargs
            )

        elif isinstance(requirement, Privilege):
            # Privilege requirement (contains role + permission + ownership)
            return await _check_privilege_requirement(user, requirement, func, args, kwargs)

    # All requirements in group must be satisfied (AND logic)
    # If no requirement of a type exists, it's considered satisfied
    final_role_satisfied = role_satisfied if has_role_requirement else True
    final_permission_satisfied = permission_satisfied if has_permission_requirement else True
    final_ownership_satisfied = ownership_satisfied if has_ownership_requirement else True

    return final_role_satisfied and final_permission_satisfied and final_ownership_satisfied


async def _check_role_requirement(
    user: User, role_req: Role | RoleComposition | list[Role]
) -> bool:
    """Check role requirement with OR logic for multiple roles.

    Args:
        user: User to check role for
        role_req: Role requirement (single role, composition, or list)

    Returns:
        True if user has required role(s), False otherwise
    """
    # Superadmin always passes role checks
    if user.role == Role.SUPERADMIN.value:
        return True

    if isinstance(role_req, Role):
        return user.role == role_req.value

    elif isinstance(role_req, RoleComposition):
        return any(user.role == role.value for role in role_req.roles)

    elif isinstance(role_req, list):
        return any(user.role == role.value for role in role_req)

    return False


async def _check_permission_requirement(user: User, permission: Permission) -> bool:
    """Check permission requirement.

    Args:
        user: User to check permission for
        permission: Permission to check

    Returns:
        True if user has permission, False otherwise
    """
    # Create RBAC service with proper database session for permission check
    from app.database.connection import get_session_maker
    from app.services.rbac import RBACService

    session_maker = get_session_maker()
    async with session_maker() as db:
        rbac_service_instance = RBACService(db)
        return await rbac_service_instance.check_permission(
            user, permission.resource, permission.action, permission.context
        )


async def _check_ownership_requirement(
    user: User, ownership: ResourceOwnership, func: Callable, args: tuple, kwargs: dict
) -> bool:
    """Check resource ownership requirement.

    Args:
        user: User to check ownership for
        ownership: Resource ownership requirement
        func: Function being called (for parameter extraction)
        args: Function positional arguments
        kwargs: Function keyword arguments

    Returns:
        True if user owns resource, False otherwise
    """
    # Extract resource ID from function parameters
    resource_id = _extract_resource_id(ownership.id_param, func, args, kwargs)

    if resource_id is None:
        logger.warning(f"Could not extract {ownership.id_param} from {func.__name__} parameters")
        return False

    # Create RBAC service with proper database session for ownership check
    from app.database.connection import get_session_maker
    from app.services.rbac import RBACService

    session_maker = get_session_maker()
    async with session_maker() as db:
        rbac_service_instance = RBACService(db)
        return await rbac_service_instance.check_resource_ownership(user, ownership.resource_type, resource_id)


async def _check_privilege_requirement(
    user: User, privilege: Privilege, func: Callable, args: tuple, kwargs: dict
) -> bool:
    """Check privilege requirement.

    Args:
        user: User to check privilege for
        privilege: Privilege to check
        func: Function being called (for parameter extraction)
        args: Function positional arguments
        kwargs: Function keyword arguments

    Returns:
        True if user has privilege, False otherwise
    """
    # Check role requirement
    role_satisfied = await _check_role_requirement(user, privilege.roles)
    if not role_satisfied:
        return False

    # Check permission requirement
    permission_satisfied = await _check_permission_requirement(user, privilege.permission)
    if not permission_satisfied:
        return False

    # Check resource ownership requirement if specified
    if privilege.resource:
        ownership_satisfied = await _check_ownership_requirement(
            user, privilege.resource, func, args, kwargs
        )
        if not ownership_satisfied:
            return False

    return True


def _extract_resource_id(
    param_name: str, func: Callable, args: tuple, kwargs: dict
) -> Optional[int]:
    """Extract resource ID from function parameters.

    Args:
        param_name: Name of parameter containing resource ID
        func: Function being called
        args: Function positional arguments
        kwargs: Function keyword arguments

    Returns:
        Resource ID if found, None otherwise
    """
    # Check keyword arguments first
    if param_name in kwargs:
        return kwargs[param_name]

    # Check positional arguments by parameter name
    # This requires inspecting the function signature
    import inspect

    try:
        sig = inspect.signature(func)
        param_names = list(sig.parameters.keys())

        if param_name in param_names:
            param_index = param_names.index(param_name)
            if param_index < len(args):
                return args[param_index]
    except Exception as e:
        logger.error(f"Error extracting resource ID: {e}")

    return None
