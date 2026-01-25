"""RBAC service for Role-Based Access Control operations.

This module provides the RBAC service for managing authorization,
role assignments, and policy evaluation using Casbin.

Public Classes:
    RBACService: Service for RBAC operations

Features:
    - Casbin policy engine integration
    - User-Customer relationship management
    - Permission checking and caching
    - Resource ownership validation
    - Query filtering for data access control
    - Request-scoped caching for performance
    - Enhanced error handling and logging
    - Privilege object evaluation
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

import casbin
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    CustomerCreationException,
    DatabaseConstraintException,
    PolicyEvaluationException,
)
from app.core.rbac import Privilege, Role
from app.models.customer import Customer
from app.models.user import User
from app.services.base import BaseService

__all__ = ["RBACService"]

logger = logging.getLogger(__name__)

# Shared Casbin enforcer instance to ensure policy consistency across all RBAC service instances
_shared_enforcer = None


def get_shared_enforcer():
    """Get or create the shared Casbin enforcer instance."""
    global _shared_enforcer
    if _shared_enforcer is None:
        try:
            _shared_enforcer = casbin.Enforcer("config/rbac_model.conf", "config/rbac_policy.csv")
            # Enable auto-save for policy changes
            _shared_enforcer.enable_auto_save(True)
            logger.info("Initialized shared Casbin enforcer")
        except Exception as e:
            logger.error(f"Failed to initialize shared Casbin enforcer: {e}")
            raise PolicyEvaluationException("Failed to initialize RBAC system", {"error": str(e)})
    else:
        # Reload policies to pick up any changes
        _shared_enforcer.load_policy()
        logger.debug("Reloaded Casbin policies")
    return _shared_enforcer


class RBACService(BaseService):
    """Service for RBAC operations using Casbin.

    Provides comprehensive authorization services including:
    - Policy-based access control with Casbin
    - User-Customer relationship management
    - Permission checking with caching
    - Resource ownership validation
    - Automatic query filtering
    - Request-scoped caching for performance
    - Enhanced error handling and diagnostics
    - Privilege object evaluation
    """

    def __init__(self, db: AsyncSession):
        """Initialize RBAC service.

        Args:
            db: Database session for operations
        """
        super().__init__(db)
        # Use shared Casbin enforcer to ensure policy consistency across instances
        self.enforcer = get_shared_enforcer()

        # Request-scoped caches for performance
        self._permission_cache: dict[str, bool] = {}
        self._customer_cache: dict[int, list[int]] = {}
        self._privilege_cache: dict[str, bool] = {}
        self._cache_timestamp = datetime.utcnow()

    async def check_permission(
        self, user: User, resource: str, action: str, context: Optional[dict] = None
    ) -> bool:
        """Check if user has permission for action on resource.

        Args:
            user: User to check permissions for
            resource: Resource type (e.g., "configuration", "quote")
            action: Action type (e.g., "read", "create", "update", "delete")
            context: Optional context for advanced permissions

        Returns:
            True if user has permission, False otherwise

        Raises:
            PolicyEvaluationException: If policy evaluation fails
        """
        # Cache key for performance
        cache_key = f"{user.id}:{resource}:{action}"
        if cache_key in self._permission_cache:
            logger.debug(f"Permission cache hit: {cache_key}")
            return self._permission_cache[cache_key]

        try:
            # Ensure user is assigned to their role in Casbin (dynamic assignment)
            # This ensures role assignments work even if they weren't persisted
            if not self.enforcer.has_grouping_policy(user.email, user.role):
                logger.debug(f"Adding missing role assignment: {user.email} -> {user.role}")
                self.enforcer.add_grouping_policy(user.email, user.role)

            # Check Casbin policy using user email as subject
            result = self.enforcer.enforce(user.email, resource, action)

            # Cache result with timestamp
            self._permission_cache[cache_key] = result

            logger.debug(
                f"Permission check: user={user.email}, resource={resource}, "
                f"action={action}, result={result}, context={context}"
            )

            # Log authorization failures for security monitoring
            if not result:
                logger.warning(
                    f"Authorization denied: user={user.email}, resource={resource}, "
                    f"action={action}, role={user.role}"
                )

            return result

        except Exception as e:
            logger.error(
                f"Permission check failed: user={user.email}, resource={resource}, "
                f"action={action}, error={e}"
            )
            raise PolicyEvaluationException(
                f"Failed to check permission for {user.email}",
                {"user_email": user.email, "resource": resource, "action": action, "error": str(e)},
            )

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

        Raises:
            NotFoundException: If the resource doesn't exist (to allow proper 404 handling)
        """
        # Superadmin has access to everything (but still need to check if resource exists)
        if user.role == Role.SUPERADMIN.value:
            # For superadmin, we still need to verify the resource exists
            # but we don't need to check ownership
            resource_exists = await self._check_resource_exists(resource_type, resource_id)
            if not resource_exists:
                from app.core.exceptions import NotFoundException

                raise NotFoundException(f"{resource_type.title()} not found")
            return True

        # Get accessible customers for user
        accessible_customers = await self.get_accessible_customers(user)

        # For customer resources, check direct access
        if resource_type == "customer":
            # Check if customer exists first
            from app.models.customer import Customer

            stmt = select(Customer.id).where(Customer.id == resource_id)
            result = await self.db.execute(stmt)
            if result.scalar_one_or_none() is None:
                from app.core.exceptions import NotFoundException

                raise NotFoundException("Customer not found")

            return resource_id in accessible_customers

        # For configuration resources, check through customer relationship
        if resource_type == "configuration":
            from app.models.configuration import Configuration

            stmt = select(Configuration.customer_id).where(Configuration.id == resource_id)
            result = await self.db.execute(stmt)
            customer_id = result.scalar_one_or_none()

            if customer_id is None:
                from app.core.exceptions import NotFoundException

                raise NotFoundException("Configuration not found")

            return customer_id in accessible_customers

        # For quote resources, check through customer relationship
        if resource_type == "quote":
            from app.models.quote import Quote

            stmt = select(Quote.customer_id).where(Quote.id == resource_id)
            result = await self.db.execute(stmt)
            customer_id = result.scalar_one_or_none()

            if customer_id is None:
                from app.core.exceptions import NotFoundException

                raise NotFoundException("Quote not found")

            return customer_id in accessible_customers

        # For order resources, check through quote -> customer relationship
        if resource_type == "order":
            from app.models.order import Order
            from app.models.quote import Quote

            stmt = (
                select(Quote.customer_id)
                .select_from(Order)
                .join(Quote)
                .where(Order.id == resource_id)
            )
            result = await self.db.execute(stmt)
            customer_id = result.scalar_one_or_none()

            if customer_id is None:
                from app.core.exceptions import NotFoundException

                raise NotFoundException("Order not found")

            return customer_id in accessible_customers

        # Default: deny access for unknown resource types
        logger.warning(f"Unknown resource type for ownership check: {resource_type}")
        return False

    async def _check_resource_exists(self, resource_type: str, resource_id: int) -> bool:
        """Check if a resource exists without checking ownership.

        Args:
            resource_type: Type of resource to check
            resource_id: ID of the resource

        Returns:
            True if resource exists, False otherwise
        """
        if resource_type == "configuration":
            from app.models.configuration import Configuration

            stmt = select(Configuration.id).where(Configuration.id == resource_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        elif resource_type == "quote":
            from app.models.quote import Quote

            stmt = select(Quote.id).where(Quote.id == resource_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        elif resource_type == "order":
            from app.models.order import Order

            stmt = select(Order.id).where(Order.id == resource_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        elif resource_type == "customer":
            from app.models.customer import Customer

            stmt = select(Customer.id).where(Customer.id == resource_id)
            result = await self.db.execute(stmt)
            return result.scalar_one_or_none() is not None

        # Unknown resource type
        return False

    async def get_accessible_customers(self, user: User) -> list[int]:
        """Get list of customer IDs user can access.

        Args:
            user: User to get accessible customers for

        Returns:
            List of customer IDs user can access
        """
        # Cache for performance
        if user.id in self._customer_cache:
            logger.debug(
                f"Customer cache hit for user {user.email}: {self._customer_cache[user.id]}"
            )
            return self._customer_cache[user.id]

        accessible = []

        # Superadmin has access to all customers
        if user.role == Role.SUPERADMIN.value:
            stmt = select(Customer.id)
            result = await self.db.execute(stmt)
            accessible = [row[0] for row in result.fetchall()]
        # Salesmen, partners, and data entry staff have access to all customers
        elif user.role in [Role.SALESMAN.value, Role.PARTNER.value, Role.DATA_ENTRY.value]:
            stmt = select(Customer.id)
            result = await self.db.execute(stmt)
            accessible = [row[0] for row in result.fetchall()]
            logger.debug(f"Staff user {user.email} has access to all customers: {accessible}")
        else:
            # Regular users (customers) have access to their associated customer(s)
            # Find ALL customers by email match (auto-creation pattern)
            # This handles cases where multiple customers might exist with the same email
            stmt = select(Customer.id).where(Customer.email == user.email)
            result = await self.db.execute(stmt)
            customer_ids = [row[0] for row in result.fetchall()]

            logger.debug(f"Customer lookup for {user.email}: found customer_ids={customer_ids}")

            accessible = customer_ids

        # Cache result
        self._customer_cache[user.id] = accessible

        logger.debug(f"Accessible customers for {user.email}: {accessible}")
        return accessible

    async def get_or_create_customer_for_user(self, user: User) -> Customer:
        """Get existing customer or create one for the user.

        This implements the auto-creation pattern where users get associated
        customers automatically when they first create configurations.

        Args:
            user: User to get or create customer for

        Returns:
            Customer associated with the user

        Raises:
            DatabaseException: If customer creation fails
        """
        # First try to find existing customer by email
        customer = await self._find_customer_by_email(user.email)

        if customer:
            logger.debug(f"Found existing customer {customer.id} for user {user.email}")
            return customer

        # Create new customer from user data
        logger.info(f"Creating new customer for user {user.email}")
        customer = await self._create_customer_from_user(user)

        # Clear customer cache since we added a new customer
        self._customer_cache.clear()

        return customer

    async def _find_customer_by_email(self, email: str) -> Optional[Customer]:
        """Find existing customer by email address.

        Args:
            email: Email address to search for

        Returns:
            Customer if found, None otherwise
        """
        stmt = select(Customer).where(Customer.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def _create_customer_from_user(self, user: User) -> Customer:
        """Create new customer record from user data.

        Args:
            user: User to create customer from

        Returns:
            Newly created customer

        Raises:
            CustomerCreationException: If customer creation fails
            DatabaseConstraintException: If constraint violations occur
        """
        try:
            # Validate user data
            if not user.email:
                raise CustomerCreationException(
                    "Cannot create customer: user email is required",
                    user_email="<missing>",
                    user_data={"username": user.username, "full_name": user.full_name},
                )

            # Create customer with user data
            customer_data = {
                "email": user.email,
                "contact_person": user.full_name or user.username or "Unknown",
                "customer_type": "residential",  # Default for entry page users
                "is_active": True,
                "notes": f"Auto-created from user: {user.username or user.email}",
            }

            logger.info(f"Creating customer for user {user.email} with data: {customer_data}")

            customer = Customer(**customer_data)
            self.db.add(customer)
            await self.commit()
            await self.refresh(customer)

            logger.info(f"Successfully created customer {customer.id} for user {user.email}")
            return customer

        except IntegrityError as e:
            await self.rollback()

            # Handle specific constraint violations
            error_str = str(e)
            if "unique constraint" in error_str.lower() and "email" in error_str.lower():
                logger.info(f"Customer with email {user.email} already exists (race condition)")

                # Check if another process created the customer
                customer = await self._find_customer_by_email(user.email)
                if customer:
                    logger.info(f"Found customer {customer.id} created by another process")
                    return customer

                raise DatabaseConstraintException(
                    f"Customer with email {user.email} already exists",
                    constraint_type="unique",
                    constraint_details={"field": "email", "value": user.email},
                    suggested_action="Use existing customer or verify email uniqueness",
                )

            elif "foreign key" in error_str.lower():
                raise DatabaseConstraintException(
                    "Foreign key constraint violation during customer creation",
                    constraint_type="foreign_key",
                    constraint_details={"error": error_str},
                    suggested_action="Verify referenced records exist",
                )

            else:
                logger.error(f"Database integrity error creating customer: {e}")
                raise CustomerCreationException(
                    "Database constraint violation during customer creation",
                    user_email=user.email,
                    user_data=customer_data,
                    original_error=e,
                )

        except Exception as e:
            await self.rollback()
            logger.error(f"Unexpected error creating customer for user {user.email}: {e}")

            # Check if it was a race condition - another process created the customer
            try:
                customer = await self._find_customer_by_email(user.email)
                if customer:
                    logger.info(
                        f"Customer {customer.id} was created by another process during error recovery"
                    )
                    return customer
            except Exception as recovery_error:
                logger.error(f"Error during customer recovery check: {recovery_error}")

            # Re-raise as CustomerCreationException
            raise CustomerCreationException(
                f"Failed to create customer record: {str(e)}",
                user_email=user.email,
                user_data=customer_data,
                original_error=e,
            )

    async def assign_role_to_user(self, user: User, role: Role) -> None:
        """Assign role to user and update Casbin policies.

        Args:
            user: User to assign role to
            role: Role to assign
        """
        # Update user role in database
        user.role = role.value
        await self.commit()

        # Update Casbin role assignment
        # Remove existing role assignments
        self.enforcer.remove_grouping_policy(user.email)

        # Add new role assignment
        self.enforcer.add_grouping_policy(user.email, role.value)

        # Clear caches
        self.clear_cache()

        logger.info(f"Assigned role {role.value} to user {user.email}")

    async def assign_customer_to_user(self, user: User, customer_id: int) -> None:
        """Assign customer access to user (for salesmen/partners).

        Args:
            user: User to assign customer access to
            customer_id: Customer ID to grant access to
        """
        # Add customer assignment in Casbin
        # This uses the g2 grouping for customer assignments
        self.enforcer.add_grouping_policy(user.email, "customer", str(customer_id))

        # Clear customer cache
        if user.id in self._customer_cache:
            del self._customer_cache[user.id]

        logger.info(f"Assigned customer {customer_id} access to user {user.email}")

    async def check_privilege(self, user: User, privilege: Privilege) -> bool:
        """Check if user has the specified privilege.

        Args:
            user: User to check privilege for
            privilege: Privilege to check

        Returns:
            True if user has privilege, False otherwise

        Raises:
            PrivilegeEvaluationException: If privilege evaluation fails
        """
        # Cache key for performance
        cache_key = f"{user.id}:privilege:{hash(str(privilege))}"
        if cache_key in self._privilege_cache:
            logger.debug(f"Privilege cache hit: {cache_key}")
            return self._privilege_cache[cache_key]

        try:
            # Check role requirement
            user_role = Role(user.role) if user.role in [r.value for r in Role] else None
            role_satisfied = False

            if user_role:
                # Check if user has any of the required roles
                role_satisfied = (
                    any(user.role == role.value for role in privilege.roles)
                    or user.role == Role.SUPERADMIN.value
                )

            if not role_satisfied:
                self._privilege_cache[cache_key] = False
                return False

            # Check permission requirement
            permission_satisfied = await self.check_permission(
                user,
                privilege.permission.resource,
                privilege.permission.action,
                privilege.permission.context,
            )

            if not permission_satisfied:
                self._privilege_cache[cache_key] = False
                return False

            # Resource ownership is checked by the decorator that calls this
            # since it needs access to function parameters

            result = True
            self._privilege_cache[cache_key] = result

            logger.debug(
                f"Privilege check: user={user.email}, privilege={privilege}, result={result}"
            )

            return result

        except Exception as e:
            logger.error(
                f"Privilege evaluation failed: user={user.email}, privilege={privilege}, error={e}"
            )
            from app.core.exceptions import PrivilegeEvaluationException

            raise PrivilegeEvaluationException(
                f"Failed to evaluate privilege for {user.email}",
                privilege_info={"privilege": str(privilege)},
                evaluation_context={"user_email": user.email, "error": str(e)},
            )

    def clear_cache(self) -> None:
        """Clear permission and customer caches."""
        self._permission_cache.clear()
        self._customer_cache.clear()
        self._privilege_cache.clear()
        self._cache_timestamp = datetime.utcnow()
        logger.debug("Cleared RBAC caches")

    def is_cache_expired(self, max_age_minutes: int = 30) -> bool:
        """Check if cache is expired based on timestamp.

        Args:
            max_age_minutes: Maximum age of cache in minutes

        Returns:
            True if cache is expired
        """
        age = datetime.utcnow() - self._cache_timestamp
        return age > timedelta(minutes=max_age_minutes)

    def get_cache_stats(self) -> dict[str, int]:
        """Get cache statistics for monitoring.

        Returns:
            Dictionary with cache statistics
        """
        return {
            "permission_cache_size": len(self._permission_cache),
            "customer_cache_size": len(self._customer_cache),
            "privilege_cache_size": len(self._privilege_cache),
            "cache_age_minutes": int(
                (datetime.utcnow() - self._cache_timestamp).total_seconds() / 60
            ),
        }

    async def initialize_user_policies(self, user: User) -> None:
        """Initialize Casbin policies for a user.

        This should be called when a user is created or their role changes.

        Args:
            user: User to initialize policies for
        """
        # Add role assignment
        logger.info(f"Adding role assignment: {user.email} -> {user.role}")
        result = self.enforcer.add_grouping_policy(user.email, user.role)
        logger.info(f"Role assignment result: {result}")

        # For customers, assign them to their own customer record
        if user.role == Role.CUSTOMER.value:
            customer = await self.get_or_create_customer_for_user(user)
            logger.info(f"Adding customer assignment: {user.email} -> customer -> {customer.id}")
            customer_result = self.enforcer.add_grouping_policy(
                user.email, "customer", str(customer.id)
            )
            logger.info(f"Customer assignment result: {customer_result}")

        # Log current grouping policies for debugging
        grouping_policies = self.enforcer.get_grouping_policy()
        logger.info(f"Current grouping policies: {grouping_policies}")

        logger.info(f"Initialized policies for user {user.email} with role {user.role}")
