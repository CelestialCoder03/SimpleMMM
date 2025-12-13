"""Tests for health check endpoint."""


def test_health_check(client):
    """Test that health check returns healthy status."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "checks" in data


def test_api_root(client):
    """Test that API v1 root returns expected message."""
    response = client.get("/api/v1/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Marketing Mix Model" in data["message"]
