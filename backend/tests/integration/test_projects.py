"""Integration tests for project endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_project(authenticated_client: AsyncClient):
    """Test creating a new project."""
    response = await authenticated_client.post(
        "/api/v1/projects",
        json={
            "name": "Test MMM Project",
            "description": "A test project for integration tests",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test MMM Project"
    assert data["description"] == "A test project for integration tests"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_projects(authenticated_client: AsyncClient):
    """Test listing projects returns the user's projects."""
    # Create a project first
    await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "List Test Project"},
    )

    response = await authenticated_client.get("/api/v1/projects")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list) or "items" in data


@pytest.mark.asyncio
async def test_get_project(authenticated_client: AsyncClient):
    """Test getting a specific project."""
    # Create a project
    create_response = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Get Test Project"},
    )
    project_id = create_response.json()["id"]

    response = await authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert response.status_code == 200
    assert response.json()["id"] == project_id


@pytest.mark.asyncio
async def test_update_project(authenticated_client: AsyncClient):
    """Test updating a project."""
    # Create a project
    create_response = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Update Test Project"},
    )
    project_id = create_response.json()["id"]

    # Update it
    response = await authenticated_client.put(
        f"/api/v1/projects/{project_id}",
        json={"name": "Updated Project Name"},
    )
    assert response.status_code == 200
    assert response.json()["name"] == "Updated Project Name"


@pytest.mark.asyncio
async def test_delete_project(authenticated_client: AsyncClient):
    """Test deleting a project."""
    # Create a project
    create_response = await authenticated_client.post(
        "/api/v1/projects",
        json={"name": "Delete Test Project"},
    )
    project_id = create_response.json()["id"]

    # Delete it
    response = await authenticated_client.delete(f"/api/v1/projects/{project_id}")
    assert response.status_code in (200, 204)

    # Verify it's gone
    get_response = await authenticated_client.get(f"/api/v1/projects/{project_id}")
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_create_project_unauthenticated(anonymous_client: AsyncClient):
    """Test creating a project without auth fails."""
    response = await anonymous_client.post(
        "/api/v1/projects",
        json={"name": "Should Fail"},
    )
    assert response.status_code == 401
