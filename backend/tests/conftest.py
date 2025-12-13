"""Pytest fixtures for testing."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.core.deps import get_db
from app.main import app


@pytest.fixture
def mock_db_session():
    """Create a mock async database session."""
    session = AsyncMock()
    # Make execute return a result with scalar_one_or_none() → None (no rows)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_result.scalars.return_value.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.refresh = AsyncMock()
    return session


@pytest.fixture
def client(mock_db_session):
    """Create a test client with mocked DB dependency."""

    async def override_get_db():
        yield mock_db_session

    app.dependency_overrides[get_db] = override_get_db

    # Patch async_session (used directly by health endpoints) and Redis
    mock_session_ctx = AsyncMock()
    mock_session_ctx.__aenter__ = AsyncMock(return_value=mock_db_session)
    mock_session_ctx.__aexit__ = AsyncMock(return_value=None)

    mock_redis = MagicMock()
    mock_redis.ping.return_value = True
    mock_redis.close = MagicMock()

    with (
        patch("app.main.async_session", return_value=mock_session_ctx),
        patch("app.main.Redis") as mock_redis_cls,
    ):
        mock_redis_cls.from_url.return_value = mock_redis
        yield TestClient(app)

    app.dependency_overrides.clear()
