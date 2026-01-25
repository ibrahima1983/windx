"""Test Redis availability check function."""

import pytest

from tests.config import check_redis_available


class TestRedisCheck:
    """Tests for Redis availability check."""

    def test_check_redis_available_returns_bool(self):
        """Test that check_redis_available returns a boolean."""
        result = check_redis_available()
        assert isinstance(result, bool)

    def test_check_redis_available_with_invalid_host(self):
        """Test that check_redis_available returns False for invalid host."""
        result = check_redis_available(host="invalid-host-that-does-not-exist", timeout=0.5)
        assert result is False

    def test_check_redis_available_with_invalid_port(self):
        """Test that check_redis_available returns False for invalid port."""
        result = check_redis_available(port=9999, timeout=0.5)
        assert result is False

    @pytest.mark.redis
    def test_redis_test_settings_fixture_enables_redis(self, redis_test_settings):
        """Test that redis_test_settings fixture enables cache and limiter."""
        # This test will be skipped if Redis is not available
        assert redis_test_settings.cache.enabled is True
        assert redis_test_settings.limiter.enabled is True

    def test_regular_test_settings_keeps_redis_disabled(self, test_settings):
        """Test that regular test_settings keeps Redis disabled."""
        # Regular tests should have Redis disabled
        assert test_settings.cache.enabled is False
        assert test_settings.limiter.enabled is False
