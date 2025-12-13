"""Tests for Celery configuration and tasks."""

from app.core.config import settings
from app.workers.celery_app import celery_app
from app.workers.tasks import train_mmm_model


def test_celery_broker_url():
    """Test Celery broker URL is configured."""
    assert celery_app.conf.broker_url == settings.CELERY_BROKER_URL


def test_celery_result_backend():
    """Test Celery result backend is configured."""
    assert celery_app.conf.result_backend == settings.CELERY_RESULT_BACKEND


def test_celery_task_serializer():
    """Test Celery uses JSON serialization."""
    assert celery_app.conf.task_serializer == "json"
    assert celery_app.conf.result_serializer == "json"


def test_celery_timezone():
    """Test Celery timezone is UTC."""
    assert celery_app.conf.timezone == "UTC"
    assert celery_app.conf.enable_utc is True


def test_train_mmm_model_task_registered():
    """Test train_mmm_model task is registered."""
    assert "app.workers.tasks.train_mmm_model" in celery_app.tasks


def test_process_dataset_file_task_registered():
    """Test process_dataset_file task is registered."""
    assert "app.workers.tasks.process_dataset_file" in celery_app.tasks


def test_health_check_task_registered():
    """Test health_check task is registered."""
    assert "app.workers.tasks.health_check" in celery_app.tasks


def test_task_routing_configured():
    """Test task routing is configured."""
    routes = celery_app.conf.task_routes
    assert "app.workers.tasks.train_mmm_model" in routes
    assert routes["app.workers.tasks.train_mmm_model"]["queue"] == "model_training"


def test_train_mmm_model_task_is_bound():
    """Test train_mmm_model task is bound (has access to self)."""
    assert hasattr(train_mmm_model, "request")


def test_settings_redis_url():
    """Test Redis URL is configured in settings."""
    assert settings.REDIS_URL.startswith("redis://")


def test_settings_celery_urls():
    """Test Celery URLs are configured in settings."""
    assert settings.CELERY_BROKER_URL.startswith("redis://")
    assert settings.CELERY_RESULT_BACKEND.startswith("redis://")
