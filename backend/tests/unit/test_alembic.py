"""Tests for Alembic configuration."""

from pathlib import Path


def test_alembic_ini_exists():
    """Test that alembic.ini exists."""
    backend_dir = Path(__file__).parent.parent.parent
    alembic_ini = backend_dir / "alembic.ini"
    assert alembic_ini.exists()


def test_alembic_env_exists():
    """Test that alembic/env.py exists."""
    backend_dir = Path(__file__).parent.parent.parent
    env_py = backend_dir / "alembic" / "env.py"
    assert env_py.exists()


def test_migration_versions_dir_exists():
    """Test that alembic/versions directory exists."""
    backend_dir = Path(__file__).parent.parent.parent
    versions_dir = backend_dir / "alembic" / "versions"
    assert versions_dir.exists()
    assert versions_dir.is_dir()


def test_initial_migration_exists():
    """Test that initial migration file exists."""
    backend_dir = Path(__file__).parent.parent.parent
    versions_dir = backend_dir / "alembic" / "versions"
    migrations = list(versions_dir.glob("*.py"))
    assert len(migrations) >= 1


def test_env_imports_models():
    """Test that env.py imports all models for autogenerate."""
    backend_dir = Path(__file__).parent.parent.parent
    env_py = backend_dir / "alembic" / "env.py"
    content = env_py.read_text()
    assert "from app.models import" in content
    assert "User" in content
    assert "Project" in content


def test_env_uses_async():
    """Test that env.py is configured for async."""
    backend_dir = Path(__file__).parent.parent.parent
    env_py = backend_dir / "alembic" / "env.py"
    content = env_py.read_text()
    assert "async_engine_from_config" in content
    assert "asyncio" in content
