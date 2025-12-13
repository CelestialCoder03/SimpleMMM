"""Celery application configuration."""

import sentry_sdk
from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# Initialize Sentry for Celery workers
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        release=settings.VERSION,
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        send_default_pii=False,
    )

celery_app = Celery(
    "mmm_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"],
)

# Celery configuration
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Result settings
    result_expires=3600,  # 1 hour
    # Worker settings
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    # Task routing
    task_routes={
        "app.workers.tasks.train_mmm_model": {"queue": "model_training"},
        "app.workers.tasks.train_sub_model": {"queue": "model_training"},
        "app.workers.tasks.process_dataset_file": {"queue": "data_processing"},
    },
    # Default queue
    task_default_queue="default",
    # Celery Beat schedule for periodic cleanup
    beat_schedule={
        "cleanup-expired-reset-tokens": {
            "task": "app.workers.tasks.cleanup_expired_reset_tokens",
            "schedule": crontab(hour=3, minute=0),  # Daily at 3:00 AM UTC
        },
        "cleanup-stale-uploads": {
            "task": "app.workers.tasks.cleanup_stale_uploads",
            "schedule": crontab(hour=4, minute=0),  # Daily at 4:00 AM UTC
        },
    },
)
