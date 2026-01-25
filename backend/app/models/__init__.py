"""Database models module.

This module contains all SQLAlchemy ORM models for database tables
using modern SQLAlchemy 2.0 with Mapped columns.

Public Classes:
    User: User model for authentication
    Session: Session model for tracking user sessions
    ManufacturingType: Product category model for Windx configurator
    AttributeNode: Hierarchical attribute tree node for product configuration
    Configuration: Customer product design model
    ConfigurationSelection: Individual attribute selection model
    Customer: Customer management model
    Quote: Quotation system model
    Order: Order management model
    OrderItem: Order line item model
    ConfigurationTemplate: Pre-defined configuration template model
    TemplateSelection: Pre-selected attribute in template model

Features:
    - SQLAlchemy 2.0 Mapped columns
    - Relationship management
    - Automatic timestamps
    - Type-safe model definitions
"""

from app.models.attribute_node import AttributeNode
from app.models.configuration import Configuration
from app.models.configuration_selection import ConfigurationSelection
from app.models.configuration_template import ConfigurationTemplate
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.quote import Quote
from app.models.session import Session
from app.models.template_selection import TemplateSelection
from app.models.user import User

__all__ = [
    "User",
    "Session",
    "ManufacturingType",
    "AttributeNode",
    "Configuration",
    "ConfigurationSelection",
    "Customer",
    "Quote",
    "Order",
    "OrderItem",
    "ConfigurationTemplate",
    "TemplateSelection",
]
