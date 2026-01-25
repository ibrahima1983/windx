"""Unit tests for factory functions.

This module tests the factory functions to ensure they:
- Create valid data that passes schema validation
- Apply traits correctly
- Generate unique values
- Handle customization properly

Features:
    - Factory validation testing
    - Trait testing
    - Schema validation testing
"""

from decimal import Decimal

from app.schemas.customer import CustomerCreate
from tests.factories.customer_factory import (
    create_customer_create_schema,
    create_customer_data,
)
from tests.factories.order_factory import create_order_data
from tests.factories.quote_factory import create_quote_data


class TestCustomerFactory:
    """Tests for customer factory."""

    def test_create_customer_data_generates_valid_data(self):
        """Test that customer factory creates valid data."""
        data = create_customer_data()

        # Verify required fields
        assert data["email"] is not None
        assert "@" in data["email"]
        assert data["contact_person"] is not None
        assert data["customer_type"] in ["commercial", "residential", "contractor"]
        assert isinstance(data["is_active"], bool)

    def test_create_customer_data_generates_unique_values(self):
        """Test that factory generates unique values per call."""
        data1 = create_customer_data()
        data2 = create_customer_data()

        # Emails should be unique
        assert data1["email"] != data2["email"]
        # Company names should be unique (if present)
        if data1["company_name"] and data2["company_name"]:
            assert data1["company_name"] != data2["company_name"]

    def test_create_customer_create_schema_is_valid(self):
        """Test that factory creates valid CustomerCreate schema."""
        schema = create_customer_create_schema()

        # Should not raise validation error
        assert isinstance(schema, CustomerCreate)
        assert schema.email is not None
        assert schema.customer_type in ["commercial", "residential", "contractor"]

    def test_customer_factory_residential_trait(self):
        """Test residential trait."""
        data = create_customer_data(residential=True)

        assert data["customer_type"] == "residential"
        assert data["company_name"] is None
        assert data["payment_terms"] == "net_30"

    def test_customer_factory_contractor_trait(self):
        """Test contractor trait."""
        data = create_customer_data(contractor=True)

        assert data["customer_type"] == "contractor"
        assert data["payment_terms"] == "net_15"
        assert data["company_name"] is not None

    def test_customer_factory_inactive_trait(self):
        """Test inactive trait."""
        data = create_customer_data(inactive=True)

        assert data["is_active"] is False

    def test_customer_factory_multiple_traits(self):
        """Test applying multiple traits."""
        data = create_customer_data(contractor=True, inactive=True)

        assert data["customer_type"] == "contractor"
        assert data["is_active"] is False
        assert data["payment_terms"] == "net_15"

    def test_customer_factory_custom_values(self):
        """Test factory with custom values."""
        custom_email = "custom@example.com"
        custom_company = "Custom Company"

        data = create_customer_data(
            email=custom_email,
            company_name=custom_company,
        )

        assert data["email"] == custom_email
        assert data["company_name"] == custom_company

    def test_customer_factory_address_structure(self):
        """Test that address has correct structure."""
        data = create_customer_data()

        assert data["address"] is not None
        assert "street" in data["address"]
        assert "city" in data["address"]
        assert "state" in data["address"]
        assert "zip" in data["address"]
        assert "country" in data["address"]


class TestOrderFactory:
    """Tests for order factory."""

    def test_create_order_data_generates_valid_data(self):
        """Test that order factory creates valid data."""
        data = create_order_data(quote_id=1)

        # Verify required fields
        assert data["quote_id"] == 1
        assert data["order_number"] is not None
        assert data["order_date"] is not None
        assert data["status"] in ["confirmed", "production", "shipped", "installed"]

    def test_create_order_data_generates_unique_values(self):
        """Test that factory generates unique values per call."""
        data1 = create_order_data(quote_id=1)
        data2 = create_order_data(quote_id=1)

        # Order numbers should be unique
        assert data1["order_number"] != data2["order_number"]

    def test_order_factory_in_production_trait(self):
        """Test in_production trait."""
        data = create_order_data(quote_id=1, in_production=True)

        assert data["status"] == "production"

    def test_order_factory_shipped_trait(self):
        """Test shipped trait."""
        data = create_order_data(quote_id=1, shipped=True)

        assert data["status"] == "shipped"

    def test_order_factory_completed_trait(self):
        """Test completed trait."""
        data = create_order_data(quote_id=1, completed=True)

        assert data["status"] == "installed"

    def test_order_factory_trait_precedence(self):
        """Test that completed trait takes precedence over shipped."""
        data = create_order_data(quote_id=1, shipped=True, completed=True)

        # Completed should take precedence
        assert data["status"] == "installed"

    def test_order_factory_custom_values(self):
        """Test factory with custom values."""
        custom_order_number = "ORD-CUSTOM-001"
        custom_instructions = "Custom instructions"

        data = create_order_data(
            quote_id=1,
            order_number=custom_order_number,
            special_instructions=custom_instructions,
        )

        assert data["order_number"] == custom_order_number
        assert data["special_instructions"] == custom_instructions

    def test_order_factory_installation_address_structure(self):
        """Test that installation address has correct structure."""
        data = create_order_data(quote_id=1)

        assert data["installation_address"] is not None
        assert "street" in data["installation_address"]
        assert "city" in data["installation_address"]
        assert "state" in data["installation_address"]
        assert "zip" in data["installation_address"]
        assert "country" in data["installation_address"]
        assert "contact_name" in data["installation_address"]
        assert "contact_phone" in data["installation_address"]

    def test_order_factory_date_defaults(self):
        """Test that dates are set correctly."""
        from datetime import date

        data = create_order_data(quote_id=1)

        assert data["order_date"] is not None
        assert isinstance(data["order_date"], date)
        assert data["required_date"] is not None
        assert isinstance(data["required_date"], date)
        # Required date should be after order date
        assert data["required_date"] >= data["order_date"]


class TestQuoteFactory:
    """Tests for quote factory."""

    def test_create_quote_data_generates_valid_data(self):
        """Test that quote factory creates valid data."""
        data = create_quote_data(configuration_id=1)

        # Verify required fields
        assert data["configuration_id"] == 1
        assert data["quote_number"] is not None
        assert data["subtotal"] is not None
        assert isinstance(data["subtotal"], Decimal)
        assert data["status"] in ["draft", "sent", "accepted", "expired"]

    def test_create_quote_data_generates_unique_values(self):
        """Test that factory generates unique values per call."""
        data1 = create_quote_data(configuration_id=1)
        data2 = create_quote_data(configuration_id=1)

        # Quote numbers should be unique
        assert data1["quote_number"] != data2["quote_number"]

    def test_quote_factory_pricing_calculation(self):
        """Test that pricing is calculated correctly."""
        subtotal = Decimal("1000.00")
        tax_rate = Decimal("10.00")

        data = create_quote_data(
            configuration_id=1,
            subtotal=subtotal,
            tax_rate=tax_rate,
        )

        # Tax amount should be calculated
        expected_tax = Decimal("100.00")
        assert data["tax_amount"] == expected_tax

        # Total should include tax
        expected_total = Decimal("1100.00")
        assert data["total_amount"] == expected_total

    def test_quote_factory_with_discount(self):
        """Test quote with discount."""
        subtotal = Decimal("1000.00")
        tax_rate = Decimal("10.00")
        discount = Decimal("50.00")

        data = create_quote_data(
            configuration_id=1,
            subtotal=subtotal,
            tax_rate=tax_rate,
            discount_amount=discount,
        )

        # Total should be subtotal + tax - discount
        expected_total = Decimal("1050.00")
        assert data["total_amount"] == expected_total

    def test_quote_factory_custom_values(self):
        """Test factory with custom values."""
        custom_quote_number = "Q-CUSTOM-001"
        custom_subtotal = Decimal("750.00")

        data = create_quote_data(
            configuration_id=1,
            quote_number=custom_quote_number,
            subtotal=custom_subtotal,
        )

        assert data["quote_number"] == custom_quote_number
        assert data["subtotal"] == custom_subtotal

    def test_quote_factory_validity_period(self):
        """Test that valid_until is set correctly."""
        from datetime import date

        data = create_quote_data(configuration_id=1)

        assert data["valid_until"] is not None
        assert isinstance(data["valid_until"], date)
        # Should be in the future
        assert data["valid_until"] >= date.today()
