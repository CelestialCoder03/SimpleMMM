"""Integration tests for authentication endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_new_user(anonymous_client: AsyncClient):
    """Test registering a new user."""
    response = await anonymous_client.post(
        "/api/v1/auth/register",
        json={
            "email": "newuser@example.com",
            "password": "securepassword123",
            "full_name": "New User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "newuser@example.com"
    assert data["full_name"] == "New User"
    assert "id" in data
    assert "hashed_password" not in data


@pytest.mark.asyncio
async def test_register_duplicate_email(anonymous_client: AsyncClient, test_user):
    """Test registering with an already-used email fails."""
    response = await anonymous_client.post(
        "/api/v1/auth/register",
        json={
            "email": test_user.email,
            "password": "securepassword123",
            "full_name": "Duplicate User",
        },
    )
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_login_success(anonymous_client: AsyncClient, test_user):
    """Test successful login returns tokens."""
    response = await anonymous_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_wrong_password(anonymous_client: AsyncClient, test_user):
    """Test login with wrong password fails."""
    response = await anonymous_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "wrongpassword",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(authenticated_client: AsyncClient, test_user):
    """Test getting current user info when authenticated."""
    response = await authenticated_client.get("/api/v1/auth/me")
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == test_user.email
    assert data["full_name"] == test_user.full_name


@pytest.mark.asyncio
async def test_get_me_unauthenticated(anonymous_client: AsyncClient):
    """Test getting current user info without auth fails."""
    response = await anonymous_client.get("/api/v1/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_refresh_token_flow(anonymous_client: AsyncClient, test_user):
    """Test full login → refresh token flow."""
    # Login first
    login_response = await anonymous_client.post(
        "/api/v1/auth/login",
        data={
            "username": test_user.email,
            "password": "testpassword123",
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    # Use refresh token
    refresh_response = await anonymous_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_response.status_code == 200
    data = refresh_response.json()
    assert "access_token" in data
    assert "refresh_token" in data


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(anonymous_client: AsyncClient):
    """Test refresh with invalid token fails."""
    response = await anonymous_client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "invalid-token"},
    )
    assert response.status_code == 401
