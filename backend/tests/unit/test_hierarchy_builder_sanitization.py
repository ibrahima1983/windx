"""Unit tests for HierarchyBuilderService sanitization logic.

Tests the robust input sanitization covering all common edge cases.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.hierarchy_builder import HierarchyBuilderService


class TestSanitizeForLtree:
    """Test suite for _sanitize_for_ltree method."""

    def setup_method(self):
        """Set up test fixtures."""
        # Create a mock session (we don't need real DB for unit tests)
        from unittest.mock import MagicMock

        mock_session = MagicMock()
        self.service = HierarchyBuilderService(mock_session)

    def test_basic_sanitization(self):
        """Test basic name sanitization."""
        assert self.service._sanitize_for_ltree("Frame Material") == "frame_material"
        assert self.service._sanitize_for_ltree("UPPERCASE") == "uppercase"
        assert self.service._sanitize_for_ltree("MixedCase") == "mixedcase"

    def test_special_characters_ampersand(self):
        """Test ampersand replacement."""
        assert self.service._sanitize_for_ltree("Aluminum & Steel") == "aluminum_and_steel"
        assert self.service._sanitize_for_ltree("A & B & C") == "a_and_b_and_c"

    def test_special_characters_symbols(self):
        """Test various symbol replacements."""
        assert self.service._sanitize_for_ltree("100% Pure") == "n_100_percent_pure"
        assert self.service._sanitize_for_ltree("Price: $50") == "price_dollar_50"
        assert self.service._sanitize_for_ltree("Email@Domain") == "email_at_domain"
        assert self.service._sanitize_for_ltree("Item #5") == "item_number_5"
        assert self.service._sanitize_for_ltree("A + B") == "a_plus_b"
        assert self.service._sanitize_for_ltree("90° Angle") == "n_90_degree_angle"

    def test_unicode_characters(self):
        """Test unicode character normalization."""
        assert self.service._sanitize_for_ltree("Café") == "cafe"
        assert self.service._sanitize_for_ltree("Naïve") == "naive"
        assert self.service._sanitize_for_ltree("Résumé") == "resume"
        assert self.service._sanitize_for_ltree("Señor") == "senor"
        assert self.service._sanitize_for_ltree("Über") == "uber"

    def test_trademark_symbols(self):
        """Test trademark and copyright symbol removal."""
        assert self.service._sanitize_for_ltree("Product™") == "product"
        assert self.service._sanitize_for_ltree("Brand®") == "brand"
        assert self.service._sanitize_for_ltree("Copyright©") == "copyright"

    def test_separators(self):
        """Test various separator replacements."""
        assert self.service._sanitize_for_ltree("Hyphen-Separated") == "hyphen_separated"
        assert self.service._sanitize_for_ltree("Slash/Separated") == "slash_separated"
        assert self.service._sanitize_for_ltree("Backslash\\Separated") == "backslash_separated"
        assert self.service._sanitize_for_ltree("Pipe|Separated") == "pipe_separated"
        assert self.service._sanitize_for_ltree("Dot.Separated") == "dot_separated"
        assert self.service._sanitize_for_ltree("Comma,Separated") == "comma_separated"
        assert self.service._sanitize_for_ltree("Colon:Separated") == "colon_separated"
        assert self.service._sanitize_for_ltree("Semicolon;Separated") == "semicolon_separated"

    def test_parentheses_and_brackets(self):
        """Test parentheses and bracket handling."""
        assert self.service._sanitize_for_ltree("Item (Premium)") == "item_premium"
        assert self.service._sanitize_for_ltree("Size [Large]") == "size_large"
        assert self.service._sanitize_for_ltree("Type {Special}") == "type_special"
        assert self.service._sanitize_for_ltree("Multi (A) [B] {C}") == "multi_a_b_c"

    def test_quotes(self):
        """Test quote character handling."""
        assert self.service._sanitize_for_ltree("Single'Quote") == "single_quote"
        assert self.service._sanitize_for_ltree('Double"Quote') == "double_quote"

    def test_multiple_spaces(self):
        """Test multiple consecutive spaces."""
        assert self.service._sanitize_for_ltree("Multiple   Spaces") == "multiple_spaces"
        assert self.service._sanitize_for_ltree("  Leading Spaces") == "leading_spaces"
        assert self.service._sanitize_for_ltree("Trailing Spaces  ") == "trailing_spaces"

    def test_multiple_underscores(self):
        """Test multiple consecutive underscores are collapsed."""
        # After replacement, multiple underscores should become one
        assert self.service._sanitize_for_ltree("A___B") == "a_b"
        assert self.service._sanitize_for_ltree("A & & B") == "a_and_and_b"

    def test_leading_number(self):
        """Test names starting with numbers get 'n_' prefix."""
        assert self.service._sanitize_for_ltree("100mm") == "n_100_mm"
        assert self.service._sanitize_for_ltree("5 Star") == "n_5_star"
        assert self.service._sanitize_for_ltree("2024 Model") == "n_2024_model"

    def test_empty_input_raises_error(self):
        """Test that empty input raises ValueError."""
        with pytest.raises(ValueError, match="cannot be empty"):
            self.service._sanitize_for_ltree("")

        with pytest.raises(ValueError, match="cannot be empty"):
            self.service._sanitize_for_ltree("   ")

        with pytest.raises(ValueError, match="cannot be empty"):
            self.service._sanitize_for_ltree("\t\n")

    def test_only_special_characters_raises_error(self):
        """Test that names with only special characters raise ValueError."""
        with pytest.raises(ValueError, match="becomes empty after sanitization"):
            self.service._sanitize_for_ltree("™®©")

        with pytest.raises(ValueError, match="becomes empty after sanitization"):
            self.service._sanitize_for_ltree("---")

        with pytest.raises(ValueError, match="becomes empty after sanitization"):
            self.service._sanitize_for_ltree("!!!")

    def test_long_names_truncated(self):
        """Test that very long names are truncated to 256 chars."""
        long_name = "a" * 300
        result = self.service._sanitize_for_ltree(long_name)
        assert len(result) <= 256
        assert result == "a" * 256  # Truncated to exactly 256 chars

    def test_complex_real_world_examples(self):
        """Test complex real-world product names."""
        # Note: Numbers in the middle don't get n_ prefix, only at the start
        assert (
            self.service._sanitize_for_ltree("Premium Café-Style Door™ (100% Wood)")
            == "premium_cafe_style_door_100_percent_wood"
        )

        assert (
            self.service._sanitize_for_ltree("Energy-Efficient Window: $500-$1000")
            == "energy_efficient_window_dollar_500_dollar_1000"
        )

        # This starts with a number after sanitization, so gets n_ prefix
        assert (
            self.service._sanitize_for_ltree("90° Corner @ 45° Angle")
            == "n_90_degree_corner_at_45_degree_angle"
        )

    def test_mathematical_operators(self):
        """Test mathematical operator handling."""
        assert self.service._sanitize_for_ltree("A × B") == "a_x_b"
        assert self.service._sanitize_for_ltree("A ÷ B") == "a_div_b"
        assert self.service._sanitize_for_ltree("A = B") == "a_equals_b"
        assert self.service._sanitize_for_ltree("A < B") == "a_lt_b"
        assert self.service._sanitize_for_ltree("A > B") == "a_gt_b"

    def test_currency_symbols(self):
        """Test various currency symbol handling."""
        assert self.service._sanitize_for_ltree("$100") == "dollar_100"
        assert self.service._sanitize_for_ltree("€50") == "euro_50"
        assert self.service._sanitize_for_ltree("£75") == "pound_75"
        assert self.service._sanitize_for_ltree("¥1000") == "yen_1000"

    def test_idempotency(self):
        """Test that sanitizing an already sanitized name returns the same result."""
        name = "Frame Material"
        first_pass = self.service._sanitize_for_ltree(name)
        second_pass = self.service._sanitize_for_ltree(first_pass)
        assert first_pass == second_pass

    def test_preserves_alphanumeric(self):
        """Test that alphanumeric characters are preserved."""
        assert self.service._sanitize_for_ltree("abc123xyz") == "abc_123_xyz"
        assert self.service._sanitize_for_ltree("Test123") == "test_123"

    def test_mixed_case_with_numbers(self):
        """Test mixed case with numbers."""
        assert self.service._sanitize_for_ltree("Model2024XL") == "model_2024_xl"
        assert self.service._sanitize_for_ltree("Type3Premium") == "type_3_premium"


@pytest.mark.asyncio
async def test_create_node_with_special_characters(db_session: AsyncSession):
    """Integration test: Create nodes with special character names."""
    from decimal import Decimal

    from app.services.hierarchy_builder import HierarchyBuilderService

    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Special Characters Test",
        base_price=Decimal("100.00"),
    )

    # Test various special character names
    test_cases = [
        ("Café-Style Door™", "cafe_style_door"),
        ("100% Pure Aluminum", "n_100_percent_pure_aluminum"),
        ("Premium & Deluxe", "premium_and_deluxe"),
        ("Price: $50-$100", "price_dollar_50_dollar_100"),
    ]

    for display_name, expected_path in test_cases:
        node = await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name=display_name,
            node_type="option",
        )
        assert node.ltree_path == expected_path
        assert node.name == display_name  # Original name preserved


@pytest.mark.asyncio
async def test_create_node_validation_errors(db_session: AsyncSession):
    """Integration test: Test input validation in create_node."""
    from decimal import Decimal

    from app.services.hierarchy_builder import HierarchyBuilderService

    service = HierarchyBuilderService(db_session)

    # Create manufacturing type
    mfg_type = await service.create_manufacturing_type(
        name="Validation Test",
        base_price=Decimal("100.00"),
    )

    # Test empty name
    with pytest.raises(ValueError, match="cannot be empty"):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="",
            node_type="option",
        )

    # Test whitespace-only name
    with pytest.raises(ValueError, match="cannot be empty"):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="   ",
            node_type="option",
        )

    # Test invalid manufacturing_type_id
    with pytest.raises(ValueError, match="must be greater than 0"):
        await service.create_node(
            manufacturing_type_id=0,
            name="Test",
            node_type="option",
        )

    # Test invalid node_type
    from app.core.exceptions import ValidationException

    with pytest.raises(ValidationException, match="Invalid node_type"):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="Test",
            node_type="invalid_type",
        )

    # Test invalid data_type
    with pytest.raises(ValueError, match="Invalid data_type"):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="Test",
            node_type="option",
            data_type="invalid_data_type",
        )

    # Test negative price_impact_value
    with pytest.raises(ValueError, match="cannot be negative"):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="Test",
            node_type="option",
            price_impact_value=Decimal("-10.00"),
        )

    # Test negative weight_impact
    with pytest.raises(ValueError, match="cannot be negative"):
        await service.create_node(
            manufacturing_type_id=mfg_type.id,
            name="Test",
            node_type="option",
            weight_impact=Decimal("-5.00"),
        )


@pytest.mark.asyncio
async def test_parent_manufacturing_type_validation(db_session: AsyncSession):
    """Integration test: Validate parent belongs to same manufacturing type."""
    from decimal import Decimal

    from app.services.hierarchy_builder import HierarchyBuilderService

    service = HierarchyBuilderService(db_session)

    # Create two different manufacturing types
    mfg_type1 = await service.create_manufacturing_type(
        name="Type 1",
        base_price=Decimal("100.00"),
    )

    mfg_type2 = await service.create_manufacturing_type(
        name="Type 2",
        base_price=Decimal("200.00"),
    )

    # Create node in type 1
    node1 = await service.create_node(
        manufacturing_type_id=mfg_type1.id,
        name="Node in Type 1",
        node_type="category",
    )

    # Try to create child in type 2 with parent from type 1 (should fail)
    with pytest.raises(ValueError, match="Parent node belongs to manufacturing type"):
        await service.create_node(
            manufacturing_type_id=mfg_type2.id,
            name="Child in Type 2",
            node_type="option",
            parent_node_id=node1.id,
        )
