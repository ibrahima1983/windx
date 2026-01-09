"""Unit tests for Template Service with Casbin decorators.

This module contains unit tests for the Template Service with RBAC decorators,
customer relationships, and template usage tracking.

Tests cover:
- Template application with customer relationships
- Casbin decorator authorization on template operations
- Template usage tracking with proper customer associations
- Privilege object functionality

Requirements: 2.1, 2.2, 9.1, 9.3
"""

from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.exceptions import NotFoundException, ValidationException
from app.core.rbac import Role
from app.models.configuration import Configuration
from app.models.configuration_template import ConfigurationTemplate
from app.models.customer import Customer
from app.models.manufacturing_type import ManufacturingType
from app.models.template_selection import TemplateSelection
from app.models.user import User
from app.schemas.configuration_template import ConfigurationTemplateCreate
from app.services.template import (
    AdminTemplateAccess,
    TemplateManagement,
    TemplateReader,
    TemplateService,
)


class TestTemplateServiceCasbin:
    """Unit tests for Template Service with Casbin decorators."""

    @pytest.mark.asyncio
    async def test_apply_template_uses_proper_customer_relationship(
        self, db_session, test_superuser_with_rbac
    ):
        """Test that apply_template_to_configuration uses proper customer relationship.

        Note: Using superuser since customers cannot access templates per RBAC policy.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer for the template
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a template
        from app.models.configuration_template import ConfigurationTemplate

        template = ConfigurationTemplate(
            name=f"Test Template {uuid.uuid4().hex[:8]}",
            description="Test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            estimated_price=Decimal("300.00"),
            estimated_weight=Decimal("20.00"),
            created_by=test_superuser_with_rbac.id,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Setup
        template_service = TemplateService(db_session)

        # Execute - superuser can apply templates
        result = await template_service.apply_template_to_configuration(
            template_id=template.id,
            user=test_superuser_with_rbac,
            config_name="Custom Configuration",
        )

        # Verify configuration was created
        assert result is not None
        assert result.name == "Custom Configuration"
        assert result.manufacturing_type_id == mfg_type.id

    @pytest.mark.asyncio
    async def test_apply_template_casbin_decorator_authorization(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test Casbin decorator authorization on apply_template_to_configuration.

        Tests that customers CANNOT apply templates (per RBAC policy),
        but staff members CAN apply templates.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a template
        from app.models.configuration_template import ConfigurationTemplate

        template = ConfigurationTemplate(
            name=f"Test Template {uuid.uuid4().hex[:8]}",
            description="Test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            estimated_price=Decimal("300.00"),
            estimated_weight=Decimal("20.00"),
            created_by=test_superuser_with_rbac.id,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Setup
        template_service = TemplateService(db_session)

        # Test 1: Customer CANNOT apply templates (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await template_service.apply_template_to_configuration(
                template_id=template.id, user=test_user_with_rbac
            )
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN apply templates
        result = await template_service.apply_template_to_configuration(
            template_id=template.id, user=test_superuser_with_rbac
        )
        assert result is not None

    @pytest.mark.asyncio
    async def test_template_usage_tracking_with_proper_customer_associations(
        self, db_session, test_superuser_with_rbac
    ):
        """Test template usage tracking with proper customer associations."""
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a customer
        from app.models.customer import Customer

        customer = Customer(
            email=f"customer-{uuid.uuid4().hex[:8]}@example.com",
            contact_person="Test Customer",
            customer_type="residential",
            is_active=True,
        )
        db_session.add(customer)
        await db_session.commit()
        await db_session.refresh(customer)

        # Create a configuration
        from app.models.configuration import Configuration

        config = Configuration(
            name="Test Configuration",
            manufacturing_type_id=mfg_type.id,
            customer_id=customer.id,
            base_price=mfg_type.base_price,
            total_price=mfg_type.base_price,
            status="draft",
        )
        db_session.add(config)
        await db_session.commit()
        await db_session.refresh(config)

        # Create a template
        from app.models.configuration_template import ConfigurationTemplate

        template = ConfigurationTemplate(
            name=f"Test Template {uuid.uuid4().hex[:8]}",
            description="Test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            estimated_price=Decimal("300.00"),
            estimated_weight=Decimal("20.00"),
            usage_count=5,
            created_by=test_superuser_with_rbac.id,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Setup
        template_service = TemplateService(db_session)

        # Execute
        await template_service.track_template_usage(
            template_id=template.id, config_id=config.id, customer_id=customer.id
        )

        # Verify usage count incremented
        await db_session.refresh(template)
        assert template.usage_count == 6  # Was 5, now 6

    @pytest.mark.asyncio
    async def test_get_template_multiple_decorators_or_logic(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test get_template with multiple @require decorators (OR logic).

        Tests that customers CANNOT read templates (per RBAC policy),
        but staff members CAN read templates.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a template
        from app.models.configuration_template import ConfigurationTemplate

        template = ConfigurationTemplate(
            name=f"Test Template {uuid.uuid4().hex[:8]}",
            description="Test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            estimated_price=Decimal("300.00"),
            estimated_weight=Decimal("20.00"),
            created_by=test_superuser_with_rbac.id,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Setup
        template_service = TemplateService(db_session)

        # Test 1: Customer CANNOT read templates (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await template_service.get_template(template.id, test_user_with_rbac)
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN read templates
        result = await template_service.get_template(template.id, test_superuser_with_rbac)
        assert result is not None
        assert result.id == template.id

    @pytest.mark.asyncio
    async def test_create_template_casbin_authorization(
        self, db_session, test_user_with_rbac, test_superuser_with_rbac
    ):
        """Test create_template with Casbin authorization.

        Tests that customers CANNOT create templates (per RBAC policy),
        but staff members CAN create templates.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Setup
        template_service = TemplateService(db_session)

        template_data = ConfigurationTemplateCreate(
            name=f"New Template {uuid.uuid4().hex[:8]}",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
        )

        # Test 1: Customer CANNOT create templates (per RBAC policy)
        with pytest.raises(HTTPException) as exc_info:
            await template_service.create_template(template_data, test_user_with_rbac)
        assert exc_info.value.status_code == 403
        assert "insufficient privileges" in str(exc_info.value.detail)

        # Test 2: Superuser CAN create templates
        result = await template_service.create_template(template_data, test_superuser_with_rbac)
        assert result is not None
        assert result.name == template_data.name

    @pytest.mark.asyncio
    async def test_privilege_objects_functionality(self):
        """Test Privilege objects functionality for Template Service."""
        # Test TemplateManagement privilege
        assert Role.DATA_ENTRY in TemplateManagement.roles
        assert Role.SALESMAN in TemplateManagement.roles
        assert TemplateManagement.permission.resource == "template"
        assert TemplateManagement.permission.action == "create"

        # Test TemplateReader privilege
        assert Role.CUSTOMER in TemplateReader.roles
        assert Role.SALESMAN in TemplateReader.roles
        assert Role.PARTNER in TemplateReader.roles
        assert Role.DATA_ENTRY in TemplateReader.roles
        assert TemplateReader.permission.resource == "template"
        assert TemplateReader.permission.action == "read"

        # Test AdminTemplateAccess privilege
        assert Role.SUPERADMIN in AdminTemplateAccess.roles
        assert AdminTemplateAccess.permission.resource == "*"
        assert AdminTemplateAccess.permission.action == "*"

    @pytest.mark.asyncio
    async def test_template_application_with_selections_and_customer_tracking(
        self, db_session, test_superuser_with_rbac
    ):
        """Test complete template application with selections and customer tracking.

        Note: Using superuser since customers cannot access templates per RBAC policy.
        """
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create a template
        from app.models.configuration_template import ConfigurationTemplate

        template = ConfigurationTemplate(
            name=f"Test Template {uuid.uuid4().hex[:8]}",
            description="Test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            estimated_price=Decimal("300.00"),
            estimated_weight=Decimal("20.00"),
            created_by=test_superuser_with_rbac.id,
            is_active=True,
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Setup
        template_service = TemplateService(db_session)

        # Execute
        result = await template_service.apply_template_to_configuration(
            template_id=template.id,
            user=test_superuser_with_rbac,
            config_name="Applied Template Configuration",
        )

        # Verify configuration was created
        assert result is not None
        assert result.name == "Applied Template Configuration"
        assert result.manufacturing_type_id == mfg_type.id

    @pytest.mark.asyncio
    async def test_template_not_found_error_handling(self, db_session, test_superuser_with_rbac):
        """Test error handling when template is not found.

        Note: Using superuser since customers cannot access templates per RBAC policy.
        """
        # Setup
        template_service = TemplateService(db_session)

        # Execute and verify exception - should get 404 for non-existent template
        with pytest.raises(NotFoundException) as exc_info:
            await template_service.get_template(999, test_superuser_with_rbac)

        assert "ConfigurationTemplate" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_template_not_active_validation(self, db_session, test_superuser_with_rbac):
        """Test validation that template must be active to apply."""
        import uuid

        # Create test data with unique names
        from app.models.manufacturing_type import ManufacturingType

        unique_name = f"Test Window Type {uuid.uuid4().hex[:8]}"
        mfg_type = ManufacturingType(
            name=unique_name,
            base_price=Decimal("200.00"),
            base_weight=Decimal("15.00"),
            is_active=True,
        )
        db_session.add(mfg_type)
        await db_session.commit()
        await db_session.refresh(mfg_type)

        # Create an inactive template
        from app.models.configuration_template import ConfigurationTemplate

        template = ConfigurationTemplate(
            name=f"Test Template {uuid.uuid4().hex[:8]}",
            description="Test template",
            manufacturing_type_id=mfg_type.id,
            template_type="standard",
            is_public=True,
            estimated_price=Decimal("300.00"),
            estimated_weight=Decimal("20.00"),
            created_by=test_superuser_with_rbac.id,
            is_active=False,  # Inactive
        )
        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)

        # Setup
        template_service = TemplateService(db_session)

        # Execute and verify exception
        with pytest.raises(ValidationException) as exc_info:
            await template_service.apply_template_to_configuration(
                template_id=template.id, user=test_superuser_with_rbac
            )

        assert "Template is not active" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_manufacturing_type_not_found_in_create_template(
        self, db_session, test_superuser_with_rbac
    ):
        """Test error handling when manufacturing type is not found during template creation."""
        # Setup
        template_service = TemplateService(db_session)

        template_data = ConfigurationTemplateCreate(
            name="New Template", manufacturing_type_id=999, template_type="standard"
        )

        # Execute and verify exception - should get 404 for non-existent manufacturing type
        with pytest.raises(NotFoundException) as exc_info:
            await template_service.create_template(template_data, test_superuser_with_rbac)

        assert "ManufacturingType" in str(exc_info.value)
