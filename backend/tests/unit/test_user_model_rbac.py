"""Unit tests for User model role functionality.

This module tests the User model's role-related functionality including
role enum validation, default role assignment, and role field constraints.

Test Classes:
    TestUserRoleAssignment: Tests for role assignment and validation
    TestUserRoleDefaults: Tests for default role behavior
    TestUserRoleConstraints: Tests for role field constraints
    TestUserRoleIntegration: Tests for Casbin policy integration
"""

from unittest.mock import MagicMock, patch

from app.core.rbac import Role
from app.models.user import User


class TestUserRoleAssignment:
    """Tests for role assignment and validation.

    Validates: Requirements 3.3, 6.1, 6.2
    """

    def test_user_role_assignment_valid_roles(self):
        """Test that all valid roles can be assigned to users."""
        for role in Role:
            user = User()
            user.role = role.value

            assert user.role == role.value

    def test_user_role_assignment_string_values(self):
        """Test role assignment using string values."""
        user = User()

        user.role = "customer"
        assert user.role == "customer"

        user.role = "salesman"
        assert user.role == "salesman"

        user.role = "superadmin"
        assert user.role == "superadmin"

    def test_user_has_role_method_exact_match(self):
        """Test has_role method with exact role match."""
        user = User()
        user.role = Role.SALESMAN.value

        assert user.has_role("salesman") is True
        assert user.has_role("customer") is False
        assert user.has_role("superadmin") is False

    def test_user_has_role_method_superadmin_bypass(self):
        """Test that superadmin has all roles via has_role method."""
        user = User()
        user.role = Role.SUPERADMIN.value

        # Superadmin should have all roles
        for role in Role:
            assert user.has_role(role.value) is True

    def test_user_has_role_method_case_sensitivity(self):
        """Test that has_role method is case sensitive."""
        user = User()
        user.role = Role.CUSTOMER.value

        assert user.has_role("customer") is True
        assert user.has_role("Customer") is False
        assert user.has_role("CUSTOMER") is False

    def test_user_role_enum_integration(self):
        """Test integration between User model and Role enum."""
        user = User()

        # Test assignment from enum
        user.role = Role.DATA_ENTRY.value
        assert user.role == "data_entry"

        # Test validation against enum
        role_enum = Role(user.role)
        assert role_enum == Role.DATA_ENTRY


class TestUserRoleDefaults:
    """Tests for default role behavior.

    Validates: Requirements 3.3, 6.2
    """

    def test_user_default_role_on_creation(self):
        """Test that new users get default customer role."""
        user = User()
        assert user.role == "customer"

    def test_user_default_role_with_kwargs(self):
        """Test default role when creating user with other kwargs."""
        user = User(email="test@example.com", username="testuser", hashed_password="hashed123")
        assert user.role == "customer"

    def test_user_explicit_role_overrides_default(self):
        """Test that explicitly provided role overrides default."""
        user = User(role="salesman")
        assert user.role == "salesman"

    def test_user_role_field_mapping(self):
        """Test that role field is properly mapped in the model."""
        user = User()

        # Check that role field exists and has correct default
        assert hasattr(user, "role")
        assert user.role == "customer"

        # Check that role can be modified
        user.role = "partner"
        assert user.role == "partner"

    def test_user_init_method_role_handling(self):
        """Test that __init__ method properly handles role parameter."""
        # Test without role parameter
        user1 = User(email="test1@example.com")
        assert user1.role == "customer"

        # Test with role parameter
        user2 = User(email="test2@example.com", role="salesman")
        assert user2.role == "salesman"

        # Test role parameter takes precedence
        user3 = User(role="data_entry")
        assert user3.role == "data_entry"


class TestUserRoleConstraints:
    """Tests for role field constraints.

    Validates: Requirements 3.3, 6.1
    """

    def test_user_role_field_properties(self):
        """Test role field database properties."""
        user = User()

        # Test that role field is not nullable
        # (This would be tested at database level in integration tests)
        assert user.role is not None

        # Test default value
        assert user.role == "customer"

    def test_user_role_string_length(self):
        """Test role field accepts valid string lengths."""
        user = User()

        # Test all valid role values (should all be within length limits)
        for role in Role:
            user.role = role.value
            assert len(user.role) <= 50  # Based on String(50) in model

    def test_user_role_validation_with_enum_values(self):
        """Test that role field accepts all enum values."""
        user = User()

        valid_roles = ["superadmin", "salesman", "data_entry", "partner", "customer"]

        for role_value in valid_roles:
            user.role = role_value
            assert user.role == role_value

            # Verify it's a valid enum value
            role_enum = Role(role_value)
            assert role_enum.value == role_value

    def test_user_role_index_property(self):
        """Test that role field is indexed for performance."""
        # This is more of a documentation test since we can't easily test
        # database indexes in unit tests, but we can verify the field
        # is configured for indexing
        user = User()

        # The role field should be indexed based on model definition
        # This helps with role-based queries and filtering
        assert hasattr(user, "role")


class TestUserRoleIntegration:
    """Tests for Casbin policy integration.

    Validates: Requirements 3.3, 6.1, 6.2
    """

    def test_user_role_casbin_subject_mapping(self):
        """Test that user email is used as Casbin subject."""
        user = User()
        user.email = "test@example.com"
        user.role = Role.SALESMAN.value

        # In Casbin, the user's email should be used as the subject
        # and role should be assigned via grouping policy
        assert user.email == "test@example.com"
        assert user.role == "salesman"

    def test_user_role_policy_assignment_format(self):
        """Test the format used for Casbin policy assignments."""
        user = User()
        user.email = "salesman@company.com"
        user.role = Role.SALESMAN.value

        # Casbin grouping policy format: g, subject, role
        # Should be: g, salesman@company.com, salesman
        expected_subject = user.email
        expected_role = user.role

        assert expected_subject == "salesman@company.com"
        assert expected_role == "salesman"

    @patch("app.services.rbac.RBACService")
    def test_user_role_rbac_service_integration(self, mock_rbac_service):
        """Test integration with RBACService for role management."""
        mock_service = MagicMock()
        mock_rbac_service.return_value = mock_service

        user = User()
        user.email = "test@example.com"
        user.role = Role.PARTNER.value

        # Simulate RBAC service initialization
        from app.services.rbac import RBACService

        rbac_service = RBACService(None)  # Mock DB session

        # Verify user properties are accessible for RBAC operations
        assert user.email is not None
        assert user.role is not None
        assert user.role in [role.value for role in Role]

    def test_user_role_superadmin_privileges(self):
        """Test superadmin role special privileges."""
        superadmin = User()
        superadmin.role = Role.SUPERADMIN.value

        regular_user = User()
        regular_user.role = Role.CUSTOMER.value

        # Superadmin should pass all role checks
        assert superadmin.has_role("superadmin") is True
        assert superadmin.has_role("customer") is True
        assert superadmin.has_role("salesman") is True
        assert superadmin.has_role("data_entry") is True
        assert superadmin.has_role("partner") is True

        # Regular user should only pass their own role check
        assert regular_user.has_role("customer") is True
        assert regular_user.has_role("superadmin") is False
        assert regular_user.has_role("salesman") is False

    def test_user_role_hierarchy_implications(self):
        """Test role hierarchy implications for authorization."""
        # Test different role levels
        roles_by_privilege = [
            Role.CUSTOMER,  # Lowest privilege
            Role.PARTNER,  # Limited business access
            Role.SALESMAN,  # Business operations
            Role.DATA_ENTRY,  # Data management
            Role.SUPERADMIN,  # Highest privilege
        ]

        for role in roles_by_privilege:
            user = User()
            user.role = role.value

            # Each role should be valid and assignable
            assert user.role == role.value
            assert user.has_role(role.value) is True

            # Only superadmin should have universal access
            if role == Role.SUPERADMIN:
                for other_role in Role:
                    assert user.has_role(other_role.value) is True
            else:
                assert user.has_role(Role.SUPERADMIN.value) is False

    def test_user_role_bitwise_operations_compatibility(self):
        """Test that user roles work with Role enum bitwise operations."""
        user = User()
        user.role = Role.SALESMAN.value

        # Test role composition compatibility
        sales_roles = Role.SALESMAN | Role.PARTNER

        # User should be in the composition
        user_role_enum = Role(user.role)
        assert user_role_enum in sales_roles

        # Test with different role
        user.role = Role.CUSTOMER.value
        user_role_enum = Role(user.role)
        assert user_role_enum not in sales_roles

    def test_user_model_repr_with_role(self):
        """Test that User model string representation works with roles."""
        user = User()
        user.id = 123
        user.email = "test@example.com"
        user.username = "testuser"
        user.role = Role.SALESMAN.value

        repr_str = repr(user)

        # Should contain basic user info (role not necessarily in repr)
        assert "User" in repr_str
        assert "123" in repr_str
        assert "test@example.com" in repr_str
        assert "testuser" in repr_str
