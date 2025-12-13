"""Tests for configuration."""

from app.core.config import settings


def test_settings_defaults():
    """Test that settings have expected default values."""
    assert settings.PROJECT_NAME == "Marketing Mix Model API"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_PREFIX == "/api/v1"


def test_cors_origins():
    """Test that CORS origins are configured."""
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0
