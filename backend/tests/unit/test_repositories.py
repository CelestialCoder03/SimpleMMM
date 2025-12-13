"""Tests for repository classes."""

from pathlib import Path


def test_base_repository_exists():
    """Test that base repository file exists."""
    repo_file = Path(__file__).parent.parent.parent / "app" / "repositories" / "base.py"
    assert repo_file.exists()


def test_user_repository_exists():
    """Test that user repository file exists."""
    repo_file = Path(__file__).parent.parent.parent / "app" / "repositories" / "user.py"
    assert repo_file.exists()


def test_project_repository_exists():
    """Test that project repository file exists."""
    repo_file = Path(__file__).parent.parent.parent / "app" / "repositories" / "project.py"
    assert repo_file.exists()


def test_dataset_repository_exists():
    """Test that dataset repository file exists."""
    repo_file = Path(__file__).parent.parent.parent / "app" / "repositories" / "dataset.py"
    assert repo_file.exists()


def test_model_config_repository_exists():
    """Test that model config repository file exists."""
    repo_file = Path(__file__).parent.parent.parent / "app" / "repositories" / "model_config.py"
    assert repo_file.exists()


def test_repository_imports():
    """Test that all repositories can be imported."""
    from app.repositories import (
        BaseRepository,
        DatasetRepository,
        ModelConfigRepository,
        ProjectRepository,
        UserRepository,
    )

    assert BaseRepository is not None
    assert UserRepository is not None
    assert ProjectRepository is not None
    assert DatasetRepository is not None
    assert ModelConfigRepository is not None


def test_user_repository_has_methods():
    """Test UserRepository has expected methods."""
    from app.repositories.user import UserRepository

    assert hasattr(UserRepository, "get_by_email")
    assert hasattr(UserRepository, "create_user")
    assert hasattr(UserRepository, "authenticate")


def test_project_repository_has_methods():
    """Test ProjectRepository has expected methods."""
    from app.repositories.project import ProjectRepository

    assert hasattr(ProjectRepository, "get_user_projects")
    assert hasattr(ProjectRepository, "create_project")
    assert hasattr(ProjectRepository, "is_owner")


def test_dataset_repository_has_methods():
    """Test DatasetRepository has expected methods."""
    from app.repositories.dataset import DatasetRepository

    assert hasattr(DatasetRepository, "get_project_datasets")
    assert hasattr(DatasetRepository, "create_dataset")
    assert hasattr(DatasetRepository, "update_status")
