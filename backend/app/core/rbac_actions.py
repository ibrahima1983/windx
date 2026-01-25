"""Action configuration classes for RBAC-aware UI components.

This module provides dataclasses for configuring page actions and table actions
with RBAC permissions, enabling declarative UI component configuration.

Public Classes:
    PageAction: Configuration for page-level action buttons
    TableAction: Configuration for table row action buttons

Features:
    - Declarative action configuration with RBAC
    - Support for both permission and role-based filtering
    - Flexible URL generation (string templates or callables)
    - Icon and styling support
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Optional

__all__ = ["PageAction", "TableAction"]


@dataclass
class PageAction:
    """Configuration for page-level action buttons.

    Used to define action buttons in page headers with automatic RBAC filtering.

    Example:
        PageAction(
            text="New Customer",
            href="/api/v1/admin/customers/new",
            permission="customer:create",
            icon="➕"
        )

    Attributes:
        text: Button text to display
        href: URL to navigate to when clicked
        permission: Optional permission required (format: "resource:action")
        role: Optional role required (e.g., "SUPERADMIN")
        class_: CSS classes for button styling
        icon: Optional icon to display (emoji or icon class)
    """

    text: str
    href: str
    permission: Optional[str] = None
    role: Optional[str] = None
    class_: str = "btn btn-primary"
    icon: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template context.

        Returns:
            Dictionary representation of action
        """
        return {
            "text": self.text,
            "href": self.href,
            "permission": self.permission,
            "role": self.role,
            "class": self.class_,
            "icon": self.icon,
        }


@dataclass
class TableAction:
    """Configuration for table row action buttons.

    Used to define action buttons in table rows with automatic RBAC filtering.

    Example:
        TableAction(
            title="Edit",
            icon="✏️",
            url="/api/v1/admin/customers/{id}/edit",
            permission="customer:update"
        )

    Attributes:
        title: Tooltip text for the action
        icon: Icon to display (emoji or icon class)
        url: URL template or callable for generating URL
             - String: Format string with {id} placeholder
             - Callable: Function that takes item and returns URL
        permission: Optional permission required (format: "resource:action")
        role: Optional role required (e.g., "SUPERADMIN")
    """

    title: str
    icon: str
    url: str | Callable[[Any], str]
    permission: Optional[str] = None
    role: Optional[str] = None

    def get_url(self, item: Any) -> str:
        """Generate URL for specific item.

        Args:
            item: Database model instance with id attribute

        Returns:
            Generated URL string
        """
        if callable(self.url):
            return self.url(item)
        else:
            return self.url.format(id=item.id)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for template context.

        Returns:
            Dictionary representation of action
        """
        return {
            "title": self.title,
            "icon": self.icon,
            "url": self.url,
            "permission": self.permission,
            "role": self.role,
        }
