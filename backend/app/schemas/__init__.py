"""Pydantic schemas module.

This module contains all Pydantic schemas for data validation,
serialization, and API request/response handling.

Public Classes:
    User: User response schema
    UserCreate: User creation schema
    UserUpdate: User update schema
    UserInDB: User database schema with password
    Session: Session response schema
    SessionCreate: Session creation schema
    SessionInDB: Session database schema with token
    LoginRequest: Login request schema
    Token: Token response schema
    ManufacturingType: Manufacturing type response schema
    ManufacturingTypeCreate: Manufacturing type creation schema
    ManufacturingTypeUpdate: Manufacturing type update schema
    AttributeNode: Attribute node response schema
    AttributeNodeCreate: Attribute node creation schema
    AttributeNodeUpdate: Attribute node update schema
    AttributeNodeTree: Attribute node with children for tree representation
    DisplayCondition: Conditional display logic schema
    ValidationRule: Validation rule schema
    Configuration: Configuration response schema
    ConfigurationCreate: Configuration creation schema
    ConfigurationUpdate: Configuration update schema
    ConfigurationWithSelections: Configuration with selections
    ConfigurationSelection: Configuration selection response schema
    ConfigurationSelectionCreate: Configuration selection creation schema
    ConfigurationSelectionUpdate: Configuration selection update schema
    ConfigurationSelectionValue: Flexible value container for selections
    Customer: Customer response schema
    CustomerCreate: Customer creation schema
    CustomerUpdate: Customer update schema
    Quote: Quote response schema
    QuoteCreate: Quote creation schema
    QuoteUpdate: Quote update schema
    Order: Order response schema
    OrderCreate: Order creation schema
    OrderUpdate: Order update schema
    OrderItem: Order item response schema
    OrderItemCreate: Order item creation schema
    OrderItemUpdate: Order item update schema
    ConfigurationTemplate: Configuration template response schema
    ConfigurationTemplateCreate: Configuration template creation schema
    ConfigurationTemplateUpdate: Configuration template update schema
    ConfigurationTemplateWithSelections: Configuration template with selections
    TemplateSelection: Template selection response schema
    TemplateSelectionCreate: Template selection creation schema
    TemplateSelectionUpdate: Template selection update schema

Features:
    - Composed schemas (not monolithic)
    - Semantic types (EmailStr, PositiveInt)
    - Field validation with constraints
    - Type-safe with Annotated types
    - ORM mode support
"""

from app.schemas.attribute_node import (
    AttributeNode,
    AttributeNodeCreate,
    AttributeNodeTree,
    AttributeNodeUpdate,
    AttributeNodeWithParent,
    DisplayCondition,
    ValidationRule,
)
from app.schemas.auth import LoginRequest, Token
from app.schemas.configuration import (
    Configuration,
    ConfigurationCreate,
    ConfigurationUpdate,
    ConfigurationWithSelections,
)
from app.schemas.configuration_selection import (
    ConfigurationSelection,
    ConfigurationSelectionCreate,
    ConfigurationSelectionUpdate,
    ConfigurationSelectionValue,
)
from app.schemas.configuration_template import (
    ConfigurationTemplate,
    ConfigurationTemplateCreate,
    ConfigurationTemplateUpdate,
    ConfigurationTemplateWithSelections,
)
from app.schemas.customer import (
    Customer,
    CustomerCreate,
    CustomerUpdate,
)
from app.schemas.manufacturing_type import (
    ManufacturingType,
    ManufacturingTypeCreate,
    ManufacturingTypeUpdate,
)
from app.schemas.order import (
    Order,
    OrderCreate,
    OrderUpdate,
)
from app.schemas.order_item import (
    OrderItem,
    OrderItemCreate,
    OrderItemUpdate,
)
from app.schemas.quote import (
    Quote,
    QuoteCreate,
    QuoteUpdate,
)
from app.schemas.responses import (
    ErrorDetail,
    ErrorResponse,
    get_common_responses,
)
from app.schemas.session import Session, SessionCreate, SessionInDB
from app.schemas.template_selection import (
    TemplateSelection,
    TemplateSelectionCreate,
    TemplateSelectionUpdate,
)
from app.schemas.user import User, UserCreate, UserInDB, UserUpdate

__all__ = [
    "User",
    "UserCreate",
    "UserUpdate",
    "UserInDB",
    "Session",
    "SessionCreate",
    "SessionInDB",
    "LoginRequest",
    "Token",
    "ManufacturingType",
    "ManufacturingTypeCreate",
    "ManufacturingTypeUpdate",
    "AttributeNode",
    "AttributeNodeCreate",
    "AttributeNodeUpdate",
    "AttributeNodeTree",
    "AttributeNodeWithParent",
    "DisplayCondition",
    "ValidationRule",
    "Configuration",
    "ConfigurationCreate",
    "ConfigurationUpdate",
    "ConfigurationWithSelections",
    "ConfigurationSelection",
    "ConfigurationSelectionCreate",
    "ConfigurationSelectionUpdate",
    "ConfigurationSelectionValue",
    "Customer",
    "CustomerCreate",
    "CustomerUpdate",
    "Quote",
    "QuoteCreate",
    "QuoteUpdate",
    "Order",
    "OrderCreate",
    "OrderUpdate",
    "OrderItem",
    "OrderItemCreate",
    "OrderItemUpdate",
    "ConfigurationTemplate",
    "ConfigurationTemplateCreate",
    "ConfigurationTemplateUpdate",
    "ConfigurationTemplateWithSelections",
    "TemplateSelection",
    "TemplateSelectionCreate",
    "TemplateSelectionUpdate",
    "ErrorDetail",
    "ErrorResponse",
    "get_common_responses",
]
