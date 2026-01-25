"""Services layer for business logic.

This package contains service classes that implement business logic
and orchestrate operations between repositories.

Public Classes:
    UserService: User management business logic
    AuthService: Authentication and authorization logic
    SessionService: Session management logic
    DashboardService: Dashboard statistics and metrics
    PricingService: Pricing calculation business logic
    ConfigurationService: Configuration management business logic
    QuoteService: Quote management business logic
    TemplateService: Template management business logic

Features:
    - Business logic separation from data access
    - Transaction management
    - Complex operations orchestration
    - Validation and business rules
"""

from app.services.auth import AuthService
from app.services.configuration import ConfigurationService
from app.services.dashboard import DashboardService
from app.services.hierarchy_builder import HierarchyBuilderService
from app.services.pricing import PricingService
from app.services.quote import QuoteService
from app.services.session import SessionService
from app.services.template import TemplateService
from app.services.user import UserService

__all__ = [
    "UserService",
    "AuthService",
    "SessionService",
    "DashboardService",
    "PricingService",
    "ConfigurationService",
    "QuoteService",
    "TemplateService",
    "HierarchyBuilderService",
]
