"""RBAC Template Helper Classes for Jinja2 Templates.

This module provides helper classes for automatic RBAC context injection into
Jinja2 templates, enabling intuitive permission checking and role-based UI rendering.

Public Classes:
    Can: Helper class for permission checks in templates
    Has: Helper class for role checks in templates
    RBACHelper: Main RBAC helper that provides Can and Has instances
    RBACTemplateMiddleware: Middleware for automatic RBAC context injection

Features:
    - Intuitive template API: can('permission'), has.role('role')
    - CRUD shortcuts: can.create('resource'), can.read('resource')
    - Resource ownership checking: can.access('resource_type', resource_id)
    - Role composition: has.any_role('SALESMAN', 'PARTNER')
    - Automatic context injection into all templates
    - Safe error handling with graceful degradation
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any, Optional

from fastapi.templating import Jinja2Templates
from starlette.requests import Request

if TYPE_CHECKING:
    from app.models.user import User

__all__ = ["Can", "Has", "RBACHelper", "RBACTemplateMiddleware"]

logger = logging.getLogger(__name__)


class Can:
    """Helper class for permission checks in templates.

    Provides intuitive API for checking user permissions in Jinja2 templates:
    - can('customer:read') - Check specific permission
    - can.create('customer') - Check create permission
    - can.access('customer', 123) - Check resource ownership

    All methods fail safely, returning False on errors to prevent template breakage.
    """

    def __init__(self, user: User):
        """Initialize Can helper with user context.

        Args:
            user: User to check permissions for
        """
        self.user = user
        self._rbac_service = None

    @property
    def rbac_service(self):
        """Get shared Casbin enforcer for permission checks."""
        from app.services.rbac import get_shared_enforcer

        return get_shared_enforcer()

    def __call__(self, permission: str) -> bool:
        """Check if user has specific permission.

        Usage in templates:
            {% if can('customer:read') %}
                <a href="/customers">View Customers</a>
            {% endif %}

        Args:
            permission: Permission string in format "resource:action"
                       (e.g., "customer:read", "order:create")

        Returns:
            True if user has permission, False otherwise
        """
        try:
            # Validate permission format
            if ":" not in permission:
                logger.warning(f"Invalid permission format: {permission}")
                return False

            resource, action = permission.split(":", 1)

            # Quick check: SUPERADMIN has all permissions
            if hasattr(self.user, "role") and self.user.role == "superadmin":
                return True

            # For other users, use shared Casbin enforcer directly (synchronous)
            # This avoids async event loop issues in template rendering
            try:
                result = self.rbac_service.enforce(self.user.email, resource, action)
                logger.debug(
                    f"Permission check: user={self.user.email}, "
                    f"resource={resource}, action={action}, result={result}"
                )
                return result
            except Exception as e:
                logger.error(f"Casbin enforcer check failed for {permission}: {e}")
                return False

        except Exception as e:
            logger.error(f"Permission check failed for {permission}: {e}")
            return False

    def access(self, resource_type: str, resource_id: int) -> bool:
        """Check if user can access specific resource.

        Usage in templates:
            {% if can.access('customer', customer.id) %}
                <button>Edit Customer</button>
            {% endif %}

        Args:
            resource_type: Type of resource (e.g., "customer", "configuration")
            resource_id: ID of the resource

        Returns:
            True if user can access resource, False otherwise
        """
        try:
            # Quick check: SUPERADMIN has access to everything
            if hasattr(self.user, "role") and self.user.role == "superadmin":
                return True

            # For resource ownership, we need to run async code in sync context
            # This is safe because we're creating a new event loop if needed
            return self._run_async_check(self._check_resource_ownership, resource_type, resource_id)

        except Exception as e:
            logger.error(f"Resource access check failed for {resource_type}:{resource_id}: {e}")
            return False

    @staticmethod
    def _run_async_check(async_func, *args) -> bool:
        """Run async function in sync context safely.

        This handles the event loop creation needed for async operations
        in template rendering context.

        Args:
            async_func: Async function to run
            *args: Arguments to pass to the function

        Returns:
            Result of the async function, or False on error
        """
        try:
            # Try to get current event loop
            try:
                asyncio.get_running_loop()
                # If we're in an event loop, we can't use asyncio.run()
                # Instead, we'll use a thread pool to run the async code
                import concurrent.futures

                def run_in_thread():
                    # Create new event loop in thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(async_func(*args))
                    finally:
                        new_loop.close()

                # Run in thread with timeout
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    return future.result(timeout=5.0)  # 5 second timeout

            except RuntimeError:
                # No event loop running, we can use asyncio.run()
                return asyncio.run(async_func(*args))

        except Exception as e:
            logger.error(f"Async check failed: {e}")
            return False

    async def _check_resource_ownership(self, resource_type: str, resource_id: int) -> bool:
        """Check resource ownership asynchronously.

        Args:
            resource_type: Type of resource
            resource_id: ID of the resource

        Returns:
            True if user owns or has access to resource
        """
        from app.database import get_db

        # Get database session
        db_gen = get_db()
        # noinspection PyCompatibility
        db = await anext(db_gen)

        try:
            # Create RBAC service instance
            from app.services.rbac import RBACService

            rbac_service = RBACService(db)

            # Check resource ownership
            result = await rbac_service.check_resource_ownership(
                self.user, resource_type, resource_id
            )

            return result

        finally:
            await db.close()

    def create(self, resource: str) -> bool:
        """Check if user can create resource.

        Usage in templates:
            {% if can.create('customer') %}
                <button>New Customer</button>
            {% endif %}

        Args:
            resource: Resource type (e.g., "customer", "order")

        Returns:
            True if user can create resource, False otherwise
        """
        return self(f"{resource}:create")

    def read(self, resource: str) -> bool:
        """Check if user can read resource.

        Usage in templates:
            {% if can.read('customer') %}
                <a href="/customers">View Customers</a>
            {% endif %}

        Args:
            resource: Resource type (e.g., "customer", "order")

        Returns:
            True if user can read resource, False otherwise
        """
        return self(f"{resource}:read")

    def update(self, resource: str) -> bool:
        """Check if user can update resource.

        Usage in templates:
            {% if can.update('customer') %}
                <button>Edit</button>
            {% endif %}

        Args:
            resource: Resource type (e.g., "customer", "order")

        Returns:
            True if user can update resource, False otherwise
        """
        return self(f"{resource}:update")

    def delete(self, resource: str) -> bool:
        """Check if user can delete resource.

        Usage in templates:
            {% if can.delete('customer') %}
                <button class="btn-danger">Delete</button>
            {% endif %}

        Args:
            resource: Resource type (e.g., "customer", "order")

        Returns:
            True if user can delete resource, False otherwise
        """
        return self(f"{resource}:delete")


class Has:
    """Helper class for role checks in templates.

    Provides intuitive API for checking user roles in Jinja2 templates:
    - has.role('SALESMAN') - Check specific role
    - has.any_role('SALESMAN', 'PARTNER') - Check multiple roles
    - has.admin_access() - Check admin-level access

    SUPERADMIN role automatically passes all role checks.
    """

    def __init__(self, user: User):
        """Initialize Has helper with user context.

        Args:
            user: User to check roles for
        """
        self.user = user

    def role(self, role: str) -> bool:
        """Check if user has specific role.

        Usage in templates:
            {% if has.role('SUPERADMIN') %}
                <div class="admin-panel">...</div>
            {% endif %}

        Args:
            role: Role to check (e.g., "SUPERADMIN", "SALESMAN", "CUSTOMER")

        Returns:
            True if user has the role or is SUPERADMIN, False otherwise
        """
        try:
            # SUPERADMIN has all roles
            if self.user.role == "superadmin":
                return True

            # Normalize role comparison (case-insensitive)
            user_role = self.user.role.lower() if self.user.role else ""
            check_role = role.lower() if role else ""

            return user_role == check_role

        except Exception as e:
            logger.error(f"Role check failed for {role}: {e}")
            return False

    def any_role(self, *roles: str) -> bool:
        """Check if user has any of the specified roles.

        Usage in templates:
            {% if has.any_role('SALESMAN', 'PARTNER') %}
                <div class="sales-tools">...</div>
            {% endif %}

        Args:
            *roles: Variable number of roles to check

        Returns:
            True if user has any of the roles, False otherwise
        """
        try:
            return any(self.role(role) for role in roles)
        except Exception as e:
            logger.error(f"Multiple role check failed: {e}")
            return False

    def admin_access(self) -> bool:
        """Check if user has admin-level access.

        Admin access includes: SUPERADMIN, SALESMAN, DATA_ENTRY

        Usage in templates:
            {% if has.admin_access() %}
                {{ rbac_sidebar(active_page) }}
            {% endif %}

        Returns:
            True if user has admin access, False otherwise
        """
        try:
            return self.any_role("superadmin", "salesman", "data_entry")
        except Exception as e:
            logger.error(f"Admin access check failed: {e}")
            return False

    def customer_access(self) -> bool:
        """Check if user is a customer.

        Usage in templates:
            {% if has.customer_access() %}
                <div class="customer-dashboard">...</div>
            {% endif %}

        Returns:
            True if user is a customer, False otherwise
        """
        try:
            return self.role("customer")
        except Exception as e:
            logger.error(f"Customer access check failed: {e}")
            return False


class RBACHelper:
    """Main RBAC helper that provides Can and Has instances.

    This is the primary interface injected into template context.
    Provides both can and has helper objects for comprehensive RBAC support.
    """

    def __init__(self, user: User):
        """Initialize RBAC helper with user context.

        Args:
            user: User to create helpers for
        """
        self.user = user
        self.can = Can(user)
        self.has = Has(user)


class RBACTemplateMiddleware:
    """Middleware for automatic RBAC context injection into templates.

    Wraps Jinja2Templates to automatically inject RBAC helper objects
    into all template contexts, enabling permission-aware UI rendering.

    Usage:
        rbac_templates = RBACTemplateMiddleware(templates)

        @router.get("/customers")
        async def list_customers(request: Request, user: User = Depends(get_current_user)):
            return await rbac_templates.render_with_rbac(
                "admin/customers_list.html.jinja",
                request,
                {"customers": customers}
            )
    """

    def __init__(self, templates: Jinja2Templates):
        """Initialize RBAC template middleware.

        Args:
            templates: Jinja2Templates instance to wrap
        """
        self.templates = templates

    async def render_with_rbac(
        self, template_name: str, request: Request, context: Optional[dict[str, Any]] = None
    ):
        """Render template with automatic RBAC context injection.

        Automatically extracts user from request and injects RBAC helpers
        into template context. Maintains backward compatibility with existing
        template rendering.

        Args:
            template_name: Name of template to render
            request: FastAPI request object
            context: Optional context dictionary to enhance

        Returns:
            TemplateResponse with enhanced RBAC context

        Raises:
            HTTPException: If user extraction fails (401 Unauthorized)
        """
        try:
            logger.info(f"render_with_rbac called for template: {template_name}")
            # Extract user from request
            user = await self._extract_user_from_request(request)
            logger.info(f"User extracted: {user.username if user else 'None'}")

            # Create RBAC helper
            rbac_helper = RBACHelper(user)
            logger.info("RBAC helper created")

            # Build enhanced context (must include request)
            enhanced_context = {
                "request": request,
                **(context or {}),
                "current_user": user,
                "rbac": rbac_helper,
                "can": rbac_helper.can,
                "has": rbac_helper.has,
            }

            logger.info(f"RBAC context keys: {list(enhanced_context.keys())}")
            logger.info(f"Can object type: {type(rbac_helper.can)}")
            logger.info(f"Has object type: {type(rbac_helper.has)}")

            # Render template with enhanced context
            logger.info("About to render template")
            result = self.templates.TemplateResponse(
                request=request, name=template_name, context=enhanced_context
            )
            logger.info("Template rendered successfully")
            return result

        except Exception as e:
            logger.error(f"RBAC template rendering failed: {e}", exc_info=True)
            raise

    @staticmethod
    async def _extract_user_from_request(request: Request) -> User:
        """Extract authenticated user from request.

        Uses the same authentication logic as get_current_user dependency.

        Args:
            request: FastAPI request object

        Returns:
            Authenticated User object

        Raises:
            HTTPException: If authentication fails
        """
        # Check if user is already in request state (set by dependency)
        if hasattr(request.state, "user"):
            return request.state.user

        # Otherwise, extract from token
        from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

        from app.api.deps import get_current_user
        from app.database import get_db

        # Get database session
        db_gen = get_db()
        # noinspection PyCompatibility
        db = await anext(db_gen)

        try:
            # Extract credentials
            HTTPBearer(auto_error=False)
            credentials = None

            # Check Authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                credentials = HTTPAuthorizationCredentials(
                    scheme="Bearer", credentials=auth_header.split(" ")[1]
                )

            # Check cookie
            if not credentials:
                token = request.cookies.get("access_token")
                if token:
                    # Handle "Bearer " prefix in cookie if present
                    if token.startswith("Bearer "):
                        token = token.split(" ")[1]
                    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

            # Get current user using existing dependency logic
            user = await get_current_user(request, credentials, db)
            return user

        finally:
            # Close database session
            await db.close()
