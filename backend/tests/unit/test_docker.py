"""Tests for Docker configuration."""

from pathlib import Path


def test_dockerfile_exists():
    """Test that Dockerfile exists."""
    backend_dir = Path(__file__).parent.parent.parent
    dockerfile = backend_dir / "Dockerfile"
    assert dockerfile.exists()


def test_dockerfile_worker_exists():
    """Test that Dockerfile.worker exists."""
    backend_dir = Path(__file__).parent.parent.parent
    dockerfile = backend_dir / "Dockerfile.worker"
    assert dockerfile.exists()


def test_dockerignore_exists():
    """Test that .dockerignore exists."""
    backend_dir = Path(__file__).parent.parent.parent
    dockerignore = backend_dir / ".dockerignore"
    assert dockerignore.exists()


def test_docker_compose_exists():
    """Test that docker-compose.yml exists."""
    project_root = Path(__file__).parent.parent.parent.parent
    compose_file = project_root / "docker" / "docker-compose.yml"
    assert compose_file.exists()


def test_nginx_config_exists():
    """Test that nginx.conf exists."""
    project_root = Path(__file__).parent.parent.parent.parent
    nginx_conf = project_root / "docker" / "nginx" / "nginx.conf"
    assert nginx_conf.exists()


def test_dockerfile_uses_uv():
    """Test that Dockerfile uses uv for package management."""
    backend_dir = Path(__file__).parent.parent.parent
    dockerfile = backend_dir / "Dockerfile"
    content = dockerfile.read_text()
    assert "uv" in content
    assert "uv sync" in content


def test_docker_compose_has_required_services():
    """Test docker-compose has all required services."""
    project_root = Path(__file__).parent.parent.parent.parent
    compose_file = project_root / "docker" / "docker-compose.yml"
    content = compose_file.read_text()

    required_services = ["db:", "redis:", "api:", "worker:", "nginx:"]
    for service in required_services:
        assert service in content, f"Missing service: {service}"


def test_docker_compose_has_healthchecks():
    """Test docker-compose has healthchecks for db and redis."""
    project_root = Path(__file__).parent.parent.parent.parent
    compose_file = project_root / "docker" / "docker-compose.yml"
    content = compose_file.read_text()
    assert "healthcheck:" in content
