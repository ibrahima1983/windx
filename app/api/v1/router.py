"""API v1 router configuration.

This module configures the main API v1 router by including all endpoint
routers with their respective prefixes and tags.

Public Variables:
    api_router: Main API v1 router

Features:
    - Centralized router configuration
    - Endpoint organization by feature
    - Tag-based API documentation
"""

from fastapi import APIRouter

from app.api.v1 import policy
from app.api.v1.endpoints import (
    admin_auth,
    admin_customers,
    admin_documentation,
    admin_entry,
    admin_hierarchy,
    admin_manufacturing,
    admin_orders,
    admin_settings,
    attribute_nodes,
    auth,
    configurations,
    customers,
    dashboard,
    entry,
    export,
    manufacturing_types,
    metrics,
    orders,
    quotes,
    templates,
    users,
)

__all__ = ["api_router"]

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth")
api_router.include_router(admin_auth.router, prefix="/admin", tags=["Admin Auth"])
api_router.include_router(
    admin_manufacturing.router, prefix="/admin/manufacturing-types", tags=["Admin Manufacturing"]
)
api_router.include_router(admin_orders.router, prefix="/admin/orders", tags=["Admin Orders"])
api_router.include_router(
    admin_customers.router, prefix="/admin/customers", tags=["Admin Customers"]
)
api_router.include_router(
    admin_documentation.router, prefix="/admin/documentation", tags=["Admin Documentation"]
)
api_router.include_router(admin_entry.router, prefix="/admin/entry", tags=["Admin Entry"])
api_router.include_router(admin_settings.router, prefix="/admin", tags=["Admin Settings"])
api_router.include_router(users.router, prefix="/users")
api_router.include_router(export.router, prefix="/export")
api_router.include_router(dashboard.router, prefix="/dashboard")
api_router.include_router(metrics.router, prefix="/metrics")
api_router.include_router(manufacturing_types.router, prefix="/manufacturing-types")
api_router.include_router(attribute_nodes.router, prefix="/attribute-nodes")
api_router.include_router(configurations.router, prefix="/configurations")
api_router.include_router(quotes.router, prefix="/quotes")
api_router.include_router(templates.router, prefix="/templates")
api_router.include_router(customers.router, prefix="/customers")
api_router.include_router(orders.router, prefix="/orders")
api_router.include_router(
    admin_hierarchy.router, prefix="/admin/hierarchy", tags=["Admin Hierarchy"]
)
api_router.include_router(policy.router, prefix="/admin")
api_router.include_router(entry.router)
