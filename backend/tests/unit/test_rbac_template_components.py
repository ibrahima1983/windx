"""
Unit tests for RBAC template components.

This module tests the RBAC-aware Jinja2 macros to ensure they correctly
filter UI elements based on user permissions and roles.

Tests cover:
- rbac_button macro with permission and role filtering
- rbac_nav_item macro with active state and badges
- protected_content macro with fallback messages
- rbac_page_header macro with conditional actions
- rbac_table_actions macro with RBAC filtering
- Navigation components (sidebar, navbar)
- Table utility components (empty_state, status_badge)
"""

from pathlib import Path
from unittest.mock import Mock

import pytest
from jinja2 import Environment, FileSystemLoader, select_autoescape


@pytest.fixture
def jinja_env():
    """Create a Jinja2 environment with the templates directory."""
    template_dir = Path(__file__).parent.parent.parent / "app" / "templates"
    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(["html", "jinja", "jinja2"]),
    )
    return env


@pytest.fixture
def mock_user_superadmin():
    """Create a mock SUPERADMIN user."""
    user = Mock()
    user.id = 1
    user.username = "admin"
    user.email = "admin@example.com"
    user.role = "SUPERADMIN"
    user.is_active = True
    return user


@pytest.fixture
def mock_user_salesman():
    """Create a mock SALESMAN user."""
    user = Mock()
    user.id = 2
    user.username = "salesman"
    user.email = "salesman@example.com"
    user.role = "SALESMAN"
    user.is_active = True
    return user


@pytest.fixture
def mock_user_customer():
    """Create a mock CUSTOMER user."""
    user = Mock()
    user.id = 3
    user.username = "customer"
    user.email = "customer@example.com"
    user.role = "CUSTOMER"
    user.is_active = True
    return user


@pytest.fixture
def mock_can_helper():
    """Create a mock 'can' permission helper."""

    def can(permission):
        """Mock permission checker - grants all permissions for testing."""
        return True

    return can


@pytest.fixture
def mock_can_helper_restricted():
    """Create a mock 'can' helper that denies all permissions."""

    def can(permission):
        """Mock permission checker - denies all permissions."""
        return False

    return can


@pytest.fixture
def mock_has_helper():
    """Create a mock 'has' role helper."""

    class HasHelper:
        def __init__(self, user):
            self.user = user

        def role(self, role_name):
            """Check if user has specific role."""
            return self.user.role == role_name or self.user.role == "SUPERADMIN"

        def any_role(self, *roles):
            """Check if user has any of the specified roles."""
            return any(self.role(role) for role in roles)

        def admin_access(self):
            """Check if user has admin-level access."""
            return self.role("SUPERADMIN") or self.role("SALESMAN") or self.role("DATA_ENTRY")

        def customer_access(self):
            """Check if user is a customer."""
            return self.role("CUSTOMER")

    return HasHelper


class TestRBACButton:
    """Tests for rbac_button macro."""

    def test_button_renders_with_permission(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that button renders when user has permission."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_button %}
            {{ rbac_button("New Customer", "/customers/new", permission="customer:create") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "New Customer" in result
        assert "/customers/new" in result
        assert "btn btn-primary" in result

    def test_button_hidden_without_permission(
        self, jinja_env, mock_user_customer, mock_can_helper_restricted, mock_has_helper
    ):
        """Test that button is hidden when user lacks permission."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_button %}
            {{ rbac_button("Delete", "/delete", permission="customer:delete") }}
        """)

        result = template.render(
            current_user=mock_user_customer,
            can=mock_can_helper_restricted,
            has=mock_has_helper(mock_user_customer),
        )

        assert "Delete" not in result
        assert "/delete" not in result

    def test_button_renders_with_role(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that button renders when user has required role."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_button %}
            {{ rbac_button("Settings", "/settings", role="SUPERADMIN") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Settings" in result
        assert "/settings" in result

    def test_button_hidden_without_role(
        self, jinja_env, mock_user_customer, mock_can_helper, mock_has_helper
    ):
        """Test that button is hidden when user lacks required role."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_button %}
            {{ rbac_button("Admin Panel", "/admin", role="SUPERADMIN") }}
        """)

        result = template.render(
            current_user=mock_user_customer,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_customer),
        )

        assert "Admin Panel" not in result
        assert "/admin" not in result

    def test_button_with_icon(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that button renders with icon."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_button %}
            {{ rbac_button("New", "/new", icon="➕") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "➕" in result
        assert "New" in result

    def test_button_with_custom_class(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that button renders with custom CSS class."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_button %}
            {{ rbac_button("Delete", "/delete", class="btn btn-danger") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "btn btn-danger" in result


class TestRBACNavItem:
    """Tests for rbac_nav_item macro."""

    def test_nav_item_renders_with_permission(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that nav item renders when user has permission."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_nav_item %}
            {{ rbac_nav_item("Customers", "/customers", permission="customer:read", icon="👥") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Customers" in result
        assert "/customers" in result
        assert "👥" in result
        assert "nav-link" in result

    def test_nav_item_hidden_without_permission(
        self, jinja_env, mock_user_customer, mock_can_helper_restricted, mock_has_helper
    ):
        """Test that nav item is hidden when user lacks permission."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_nav_item %}
            {{ rbac_nav_item("Admin", "/admin", permission="admin:access") }}
        """)

        result = template.render(
            current_user=mock_user_customer,
            can=mock_can_helper_restricted,
            has=mock_has_helper(mock_user_customer),
        )

        assert "Admin" not in result
        assert "/admin" not in result

    def test_nav_item_active_state(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that nav item shows active state."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_nav_item %}
            {{ rbac_nav_item("Dashboard", "/dashboard", active=True) }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "active" in result
        assert "Dashboard" in result

    def test_nav_item_with_badge(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that nav item renders with badge."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_nav_item %}
            {{ rbac_nav_item("Orders", "/orders", badge="Beta") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Beta" in result
        assert "badge-beta" in result

    def test_nav_item_disabled(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that nav item renders as disabled."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_nav_item %}
            {{ rbac_nav_item("Reports", "#", badge="Soon", disabled=True) }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "disabled" in result
        assert "Soon" in result
        assert "badge-soon" in result


class TestProtectedContent:
    """Tests for protected_content macro."""

    def test_content_renders_with_permission(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that content renders when user has permission."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import protected_content %}
            {% call protected_content(permission="customer:delete") %}
                <button>Delete Customer</button>
            {% endcall %}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Delete Customer" in result

    def test_content_hidden_without_permission(
        self, jinja_env, mock_user_customer, mock_can_helper_restricted, mock_has_helper
    ):
        """Test that content is hidden when user lacks permission."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import protected_content %}
            {% call protected_content(permission="admin:access") %}
                <div>Admin Content</div>
            {% endcall %}
        """)

        result = template.render(
            current_user=mock_user_customer,
            can=mock_can_helper_restricted,
            has=mock_has_helper(mock_user_customer),
        )

        assert "Admin Content" not in result

    def test_content_shows_fallback_message(
        self, jinja_env, mock_user_customer, mock_can_helper_restricted, mock_has_helper
    ):
        """Test that fallback message is shown when access is denied."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import protected_content %}
            {% call protected_content(permission="admin:access", fallback_message="Access Denied") %}
                <div>Admin Content</div>
            {% endcall %}
        """)

        result = template.render(
            current_user=mock_user_customer,
            can=mock_can_helper_restricted,
            has=mock_has_helper(mock_user_customer),
        )

        assert "Access Denied" in result
        assert "Admin Content" not in result


class TestRBACPageHeader:
    """Tests for rbac_page_header macro."""

    def test_page_header_with_title(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that page header renders with title."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_page_header %}
            {{ rbac_page_header("Manufacturing Types") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Manufacturing Types" in result
        assert "page-header" in result

    def test_page_header_with_subtitle(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that page header renders with subtitle."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_page_header %}
            {{ rbac_page_header("Customers", subtitle="Manage customer accounts") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Customers" in result
        assert "Manage customer accounts" in result

    def test_page_header_with_actions(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that page header renders with action buttons."""
        template = jinja_env.from_string("""
            {% from "components/rbac_helpers.html.jinja" import rbac_page_header %}
            {{ rbac_page_header(
                "Types",
                actions=[
                    {"text": "New Type", "href": "/new", "icon": "➕"}
                ]
            ) }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "New Type" in result
        assert "/new" in result
        assert "➕" in result


class TestRBACTableActions:
    """Tests for rbac_table_actions macro."""

    def test_table_actions_render_with_permission(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that table actions render when user has permission."""
        template = jinja_env.from_string("""
            {% from "components/tables.html.jinja" import rbac_table_actions %}
            {{ rbac_table_actions(
                {"id": 1, "name": "Test"},
                [
                    {"title": "Edit", "icon": "✏️", "url": "/edit/{id}", "permission": "item:update"}
                ]
            ) }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "Edit" in result
        assert "/edit/1" in result
        assert "✏️" in result

    def test_table_actions_hidden_without_permission(
        self, jinja_env, mock_user_customer, mock_can_helper_restricted, mock_has_helper
    ):
        """Test that table actions are hidden when user lacks permission."""
        template = jinja_env.from_string("""
            {% from "components/tables.html.jinja" import rbac_table_actions %}
            {{ rbac_table_actions(
                {"id": 1, "name": "Test"},
                [
                    {"title": "Delete", "icon": "🗑️", "url": "/delete/{id}", "permission": "item:delete"}
                ]
            ) }}
        """)

        result = template.render(
            current_user=mock_user_customer,
            can=mock_can_helper_restricted,
            has=mock_has_helper(mock_user_customer),
        )

        # Should render the container but not the action
        assert "Delete" not in result
        assert "/delete/1" not in result


class TestNavigationComponents:
    """Tests for navigation components."""

    def test_sidebar_renders(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that sidebar renders with navigation items."""
        template = jinja_env.from_string("""
            {% from "components/navigation.html.jinja" import rbac_sidebar %}
            {{ rbac_sidebar(active_page="dashboard") }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
            enable_customers=True,
            enable_orders=True,
        )

        assert "sidebar" in result
        assert "Dashboard" in result
        assert "Manufacturing Types" in result
        assert "WindX Admin" in result

    def test_navbar_renders(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that navbar renders with user info."""
        template = jinja_env.from_string("""
            {% from "components/navigation.html.jinja" import rbac_navbar %}
            {{ rbac_navbar() }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "navbar" in result
        assert "admin" in result
        assert "WindX Admin" in result


class TestTableUtilities:
    """Tests for table utility components."""

    def test_empty_state_renders(
        self, jinja_env, mock_user_superadmin, mock_can_helper, mock_has_helper
    ):
        """Test that empty state renders correctly."""
        template = jinja_env.from_string("""
            {% from "components/tables.html.jinja" import empty_state %}
            {{ empty_state(
                icon="🏭",
                title="No Data",
                message="Get started by adding items."
            ) }}
        """)

        result = template.render(
            current_user=mock_user_superadmin,
            can=mock_can_helper,
            has=mock_has_helper(mock_user_superadmin),
        )

        assert "🏭" in result
        assert "No Data" in result
        assert "Get started by adding items." in result

    def test_status_badge_renders(self, jinja_env):
        """Test that status badge renders with correct styling."""
        template = jinja_env.from_string("""
            {% from "components/tables.html.jinja" import status_badge %}
            {{ status_badge("active", type="success") }}
        """)

        result = template.render()

        assert "Active" in result
        assert "#dcfce7" in result  # Success background color
        assert "#15803d" in result  # Success text color


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
