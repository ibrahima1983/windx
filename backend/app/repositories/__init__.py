"""Repository pattern implementation module.

This module contains all repository implementations following the
repository pattern for clean data access layer separation.

Public Classes:
    UserRepository: Repository for User operations
    SessionRepository: Repository for Session operations
    ManufacturingTypeRepository: Repository for ManufacturingType operations
    AttributeNodeRepository: Repository for AttributeNode operations
    ConfigurationRepository: Repository for Configuration operations
    ConfigurationSelectionRepository: Repository for ConfigurationSelection operations
    CustomerRepository: Repository for Customer operations
    QuoteRepository: Repository for Quote operations
    ConfigurationTemplateRepository: Repository for ConfigurationTemplate operations
    TemplateSelectionRepository: Repository for TemplateSelection operations
    OrderRepository: Repository for Order operations
    HierarchicalRepository: Base repository for hierarchical data with LTREE

Features:
    - Repository pattern implementation
    - Generic base repository with CRUD
    - Type-safe async operations
    - Custom query methods per repository
    - Clean separation of concerns
    - LTREE-based hierarchical queries
"""

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
from app.repositories.windx_base import HierarchicalRepository

__all__ = [
    "UserRepository",
    "SessionRepository",
    "ManufacturingTypeRepository",
    "AttributeNodeRepository",
    "ConfigurationRepository",
    "ConfigurationSelectionRepository",
    "CustomerRepository",
    "QuoteRepository",
    "ConfigurationTemplateRepository",
    "TemplateSelectionRepository",
    "OrderRepository",
    "HierarchicalRepository",
]
