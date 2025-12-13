"""Tests for API endpoint registration and router structure."""

import pytest
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Tests for the health check endpoint."""

    def test_health_check(self, client: TestClient):
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthRouterRegistration:
    """Verify auth routes are properly registered on the app."""

    def test_auth_register_route_exists(self, client: TestClient):
        response = client.post("/api/v1/auth/register", json={})
        assert response.status_code != 404

    def test_auth_login_route_exists(self, client: TestClient):
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "x", "password": "x"},
        )
        assert response.status_code != 404

    def test_auth_refresh_route_exists(self, client: TestClient):
        response = client.post("/api/v1/auth/refresh", json={})
        assert response.status_code != 404

    def test_auth_me_route_requires_auth(self, client: TestClient):
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestProtectedRoutesRequireAuth:
    """Verify protected routes reject unauthenticated requests."""

    @pytest.mark.parametrize(
        "method,path",
        [
            ("GET", "/api/v1/projects"),
            ("POST", "/api/v1/projects"),
        ],
    )
    def test_protected_route_returns_401(self, client: TestClient, method: str, path: str):
        response = client.request(method, path)
        assert response.status_code == 401


class TestDepsModule:
    """Verify dependency injection setup."""

    def test_deps_exports(self):
        from app.core.deps import CurrentUser, DbSession, get_current_user, get_db

        assert callable(get_db)
        assert callable(get_current_user)
        assert DbSession is not None
        assert CurrentUser is not None
