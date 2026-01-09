"""RBAC Template Context for testing and template rendering.

This module provides the RBACTemplateContext class that wraps the RBAC service
for use in template testing and rendering contexts.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.models.user import User
    from app.services.rbac import RBACService
    from app.core.rbac import Privilege


class RBACTemplateContext:
    """Template context wrapper for RBAC functionality.

    This class provides a testing-friendly interface to RBAC functionality
    that can be used in both template rendering and unit tests.
    """

    def __init__(self, rbac_service: "RBACService"):
        """Initialize the RBAC template context.

        Args:
            rbac_service: The RBAC service instance to use for permission checks
        """
        self.rbac_service = rbac_service

    async def can(self, user: "User", resource: str, action: str) -> bool:
        """Check if user can perform action on resource.

        Args:
            user: User to check permissions for
            resource: Resource type (e.g., "customer", "configuration")
            action: Action to perform (e.g., "read", "create", "update", "delete")

        Returns:
            True if user has permission, False otherwise
        """
        try:
            return await self.rbac_service.check_permission(user, resource, action)
        except Exception:
            return False

    def has_role(self, user: "User", role: str) -> bool:
        """Check if user has specific role.

        Args:
            user: User to check role for
            role: Role to check (e.g., "superadmin", "salesman", "customer")

        Returns:
            True if user has the role, False otherwise
        """
        try:
            # Superadmin has all roles
            if hasattr(user, "role") and user.role == "superadmin":
                return True

            # Check exact role match (case-insensitive)
            user_role = user.role.lower() if hasattr(user, "role") and user.role else ""
            check_role = role.lower() if role else ""

            return user_role == check_role
        except Exception:
            return False

    async def owns(self, user: "User", resource_type: str, resource_id: int) -> bool:
        """Check if user owns or has access to specific resource.

        Args:
            user: User to check ownership for
            resource_type: Type of resource (e.g., "customer", "configuration")
            resource_id: ID of the resource

        Returns:
            True if user owns or has access to resource, False otherwise
        """
        try:
            return await self.rbac_service.check_resource_ownership(
                user, resource_type, resource_id
            )
        except Exception:
            return False

    async def has_privilege(self, user: "User", privilege: "Privilege") -> bool:
        """Check if user has specific privilege.

        Args:
            user: User to check privilege for
            privilege: Privilege object containing roles and permissions

        Returns:
            True if user has the privilege, False otherwise
        """
        try:
            return await self.rbac_service.check_privilege(user, privilege)
        except Exception:
            return False
