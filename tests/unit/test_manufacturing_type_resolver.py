"""Unit tests for ManufacturingTypeResolver page type functionality."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from app.core.manufacturing_type_resolver import ManufacturingTypeResolver
from app.models.manufacturing_type import ManufacturingType


class TestManufacturingTypeResolver:
    """Test suite for ManufacturingTypeResolver page type functionality."""

    @pytest.mark.parametrize(
        "page_type,expected",
        [
            # Valid page types
            ("profile", True),
            ("accessories", True),
            ("glazing", True),
            # Invalid page types
            ("invalid", False),
            ("", False),
            ("PROFILE", False),  # Case sensitive
            ("Profile", False),  # Case sensitive
            ("profiles", False),  # Plural
            ("accessory", False),  # Singular
            ("glass", False),  # Different term
            ("window", False),  # Manufacturing category, not page type
            ("door", False),  # Manufacturing category, not page type
            ("123", False),  # Numeric
            ("profile ", False),  # Trailing space
            (" profile", False),  # Leading space
            ("pro-file", False),  # Hyphenated
            ("pro_file", False),  # Underscore
            (None, False),  # None input
        ],
        ids=[
            "valid_profile",
            "valid_accessories",
            "valid_glazing",
            "invalid_random",
            "invalid_empty",
            "invalid_uppercase",
            "invalid_titlecase",
            "invalid_plural_profiles",
            "invalid_singular_accessory",
            "invalid_glass_term",
            "invalid_window_category",
            "invalid_door_category",
            "invalid_numeric",
            "invalid_trailing_space",
            "invalid_leading_space",
            "invalid_hyphenated",
            "invalid_underscore",
            "invalid_none",
        ],
    )
    def test_validate_page_type(self, page_type: str | None, expected: bool):
        """Test page type validation with various inputs."""
        result = ManufacturingTypeResolver.validate_page_type(page_type)
        assert result == expected, f"Expected {expected} for page_type '{page_type}', got {result}"

    def test_page_type_constants(self):
        """Test that page type constants are correctly defined."""
        assert ManufacturingTypeResolver.PAGE_TYPE_PROFILE == "profile"
        assert ManufacturingTypeResolver.PAGE_TYPE_ACCESSORIES == "accessories"
        assert ManufacturingTypeResolver.PAGE_TYPE_GLAZING == "glazing"

        # Verify VALID_PAGE_TYPES contains all constants
        expected_types = {
            ManufacturingTypeResolver.PAGE_TYPE_PROFILE,
            ManufacturingTypeResolver.PAGE_TYPE_ACCESSORIES,
            ManufacturingTypeResolver.PAGE_TYPE_GLAZING,
        }
        assert ManufacturingTypeResolver.VALID_PAGE_TYPES == expected_types

    @pytest.mark.parametrize(
        "page_type,manufacturing_category",
        [
            ("profile", "window"),
            ("accessories", "window"),
            ("glazing", "window"),
            ("profile", "door"),
            ("accessories", "door"),
            ("glazing", "door"),
        ],
        ids=[
            "profile_window",
            "accessories_window",
            "glazing_window",
            "profile_door",
            "accessories_door",
            "glazing_door",
        ],
    )
    @pytest.mark.asyncio
    async def test_get_default_for_page_type_valid(
        self, page_type: str, manufacturing_category: str
    ):
        """Test get_default_for_page_type with valid inputs."""
        # Mock database session
        mock_db = AsyncMock()

        # Mock manufacturing type
        mock_mfg_type = ManufacturingType(
            id=1,
            name="Test Manufacturing Type",
            base_category=manufacturing_category,
            is_active=True,
        )

        # Mock the database query results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mfg_type
        mock_db.execute.return_value = mock_result

        result = await ManufacturingTypeResolver.get_default_for_page_type(
            mock_db, page_type, manufacturing_category
        )

        assert result is not None
        assert result.base_category == manufacturing_category
        assert mock_db.execute.called

    @pytest.mark.parametrize(
        "invalid_page_type",
        [
            "invalid",
            "",
            "PROFILE",
            "Profile",
            "profiles",
            "accessory",
            "glass",
            "window",
            "123",
        ],
        ids=[
            "random_invalid",
            "empty_string",
            "uppercase",
            "titlecase",
            "plural",
            "singular",
            "different_term",
            "category_name",
            "numeric",
        ],
    )
    @pytest.mark.asyncio
    async def test_get_default_for_page_type_invalid(self, invalid_page_type: str):
        """Test get_default_for_page_type with invalid page types."""
        mock_db = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await ManufacturingTypeResolver.get_default_for_page_type(
                mock_db, invalid_page_type, "window"
            )

        assert "Invalid page_type" in str(exc_info.value)
        assert invalid_page_type in str(exc_info.value)
        assert "Must be one of:" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_get_default_for_page_type_profile_fallback(self):
        """Test that profile page type uses the existing profile entry logic."""
        mock_db = AsyncMock()

        # Mock the get_default_profile_entry_type method
        mock_mfg_type = ManufacturingType(
            id=1, name="Window Profile Entry", base_category="window", is_active=True
        )

        # Mock database query for profile entry type
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_mfg_type
        mock_db.execute.return_value = mock_result

        result = await ManufacturingTypeResolver.get_default_for_page_type(
            mock_db, "profile", "window"
        )

        assert result is not None
        assert result.name == "Window Profile Entry"

    @pytest.mark.asyncio
    async def test_get_default_for_page_type_no_manufacturing_types(self):
        """Test behavior when no manufacturing types exist."""
        mock_db = AsyncMock()

        # Mock empty database results
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await ManufacturingTypeResolver.get_default_for_page_type(
            mock_db, "accessories", "window"
        )

        assert result is None

    def test_clear_cache(self):
        """Test cache clearing functionality."""
        # Add something to cache
        ManufacturingTypeResolver._cache["test"] = 123
        assert "test" in ManufacturingTypeResolver._cache

        # Clear cache
        ManufacturingTypeResolver.clear_cache()
        assert len(ManufacturingTypeResolver._cache) == 0

    @pytest.mark.parametrize(
        "page_type,expected_error_message",
        [
            (
                "invalid",
                "Invalid page_type 'invalid'. Must be one of: {'profile', 'accessories', 'glazing'}",
            ),
            ("", "Invalid page_type ''. Must be one of: {'profile', 'accessories', 'glazing'}"),
            (
                "PROFILE",
                "Invalid page_type 'PROFILE'. Must be one of: {'profile', 'accessories', 'glazing'}",
            ),
        ],
        ids=["invalid_word", "empty_string", "wrong_case"],
    )
    @pytest.mark.asyncio
    async def test_error_message_format(self, page_type: str, expected_error_message: str):
        """Test that error messages are properly formatted."""
        mock_db = AsyncMock()

        with pytest.raises(ValueError) as exc_info:
            await ManufacturingTypeResolver.get_default_for_page_type(mock_db, page_type, "window")

        # Note: The exact set order might vary, so we check components
        error_msg = str(exc_info.value)
        assert f"Invalid page_type '{page_type}'" in error_msg
        assert "Must be one of:" in error_msg
        assert "profile" in error_msg
        assert "accessories" in error_msg
        assert "glazing" in error_msg

    def test_valid_page_types_immutable(self):
        """Test that VALID_PAGE_TYPES is a set and contains expected values."""
        original_types = ManufacturingTypeResolver.VALID_PAGE_TYPES.copy()

        # Verify it's a set with expected values
        assert isinstance(ManufacturingTypeResolver.VALID_PAGE_TYPES, set)
        assert len(ManufacturingTypeResolver.VALID_PAGE_TYPES) == 3
        assert "profile" in ManufacturingTypeResolver.VALID_PAGE_TYPES
        assert "accessories" in ManufacturingTypeResolver.VALID_PAGE_TYPES
        assert "glazing" in ManufacturingTypeResolver.VALID_PAGE_TYPES

        # The set should remain unchanged
        assert ManufacturingTypeResolver.VALID_PAGE_TYPES == original_types
