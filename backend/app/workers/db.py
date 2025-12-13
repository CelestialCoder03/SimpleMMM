"""Sync database utilities for Celery workers.

Celery workers run in a sync context, so we need a sync SQLAlchemy engine
separate from the async engine used by FastAPI.
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import QueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_sync_database_url() -> str:
    """Convert async database URL to sync URL."""
    url = settings.DATABASE_URL
    # Replace asyncpg with psycopg2 for sync operations
    if "+asyncpg" in url:
        return url.replace("+asyncpg", "")
    return url


# Module-level sync engine with connection pooling
# This is created once when the module is imported
_sync_engine = create_engine(
    _get_sync_database_url(),
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=3600,  # Recycle connections after 1 hour
)

_SyncSessionLocal = sessionmaker(
    bind=_sync_engine,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_sync_session() -> Generator[Session, None, None]:
    """Get a sync database session for Celery tasks.

    Usage:
        with get_sync_session() as session:
            session.execute(...)
            session.commit()
    """
    session = _SyncSessionLocal()
    try:
        yield session
    finally:
        session.close()


def update_dataset_status(
    dataset_id: str,
    status: str,
    row_count: int | None = None,
    column_count: int | None = None,
    columns_metadata: list | None = None,
    error_message: str | None = None,
) -> None:
    """Update dataset record in database.

    Args:
        dataset_id: UUID of the dataset
        status: New status ('ready', 'failed', 'processing')
        row_count: Number of rows (for 'ready' status)
        column_count: Number of columns (for 'ready' status)
        columns_metadata: Column metadata list (for 'ready' status)
        error_message: Error message (for 'failed' status)
    """
    import json

    with get_sync_session() as session:
        if status == "ready":
            session.execute(
                text("""
                    UPDATE datasets
                    SET status = :status,
                        row_count = :row_count,
                        column_count = :column_count,
                        columns_metadata = CAST(:columns_metadata AS jsonb),
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": dataset_id,
                    "status": status,
                    "row_count": row_count,
                    "column_count": column_count,
                    "columns_metadata": json.dumps(columns_metadata) if columns_metadata else None,
                },
            )
        else:
            session.execute(
                text("""
                    UPDATE datasets
                    SET status = :status,
                        error_message = :error_message,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": dataset_id,
                    "status": status,
                    "error_message": error_message,
                },
            )
        session.commit()


def save_model_training_result(
    model_config_id: str,
    raw_result: dict,
    artifact_path: str | None = None,
) -> None:
    import json
    import uuid
    from uuid import UUID

    from app.services.results.processor import ResultProcessor

    status = raw_result.get("status")
    error_message = raw_result.get("error") or raw_result.get("message")

    logger.info(f"Saving model training result for {model_config_id}, status={status}")

    with get_sync_session() as session:
        model_row = (
            session.execute(
                text("""
                SELECT name
                FROM model_configs
                WHERE id = :id
            """),
                {"id": model_config_id},
            )
            .mappings()
            .first()
        )

        model_name = model_row["name"] if model_row else ""

        if status == "completed":
            logger.debug(f"Processing completed result for {model_config_id}")
            processor = ResultProcessor()
            processed = processor.process(
                raw_result,
                model_id=UUID(model_config_id),
                model_name=model_name,
            )
            logger.debug(f"Result processed successfully for {model_config_id}")

            session.execute(
                text("""
                    UPDATE model_configs
                    SET status = 'completed',
                        error_message = NULL,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": model_config_id},
            )

            payload = {
                "metrics": processed.metrics,
                "coefficients": processed.coefficients,
                "contributions": processed.contributions,
                "decomposition": processed.decomposition,
                "response_curves": processed.response_curves,
                "diagnostics": processed.diagnostics,
                "fitted_params": processed.transformations,
                "training_duration_seconds": processed.training_duration_seconds,
            }

            session.execute(
                text("""
                    INSERT INTO model_results (
                        id,
                        model_config_id,
                        training_duration_seconds,
                        metrics,
                        coefficients,
                        contributions,
                        decomposition,
                        response_curves,
                        diagnostics,
                        fitted_params,
                        model_artifact_path,
                        updated_at
                    ) VALUES (
                        :id,
                        :model_config_id,
                        :training_duration_seconds,
                        CAST(:metrics AS jsonb),
                        CAST(:coefficients AS jsonb),
                        CAST(:contributions AS jsonb),
                        CAST(:decomposition AS jsonb),
                        CAST(:response_curves AS jsonb),
                        CAST(:diagnostics AS jsonb),
                        CAST(:fitted_params AS jsonb),
                        :model_artifact_path,
                        NOW()
                    )
                    ON CONFLICT (model_config_id) DO UPDATE
                    SET training_duration_seconds = EXCLUDED.training_duration_seconds,
                        metrics = EXCLUDED.metrics,
                        coefficients = EXCLUDED.coefficients,
                        contributions = EXCLUDED.contributions,
                        decomposition = EXCLUDED.decomposition,
                        response_curves = EXCLUDED.response_curves,
                        diagnostics = EXCLUDED.diagnostics,
                        fitted_params = EXCLUDED.fitted_params,
                        model_artifact_path = EXCLUDED.model_artifact_path,
                        updated_at = NOW()
                """),
                {
                    "id": str(uuid.uuid4()),
                    "model_config_id": model_config_id,
                    "training_duration_seconds": payload["training_duration_seconds"],
                    "metrics": json.dumps(payload["metrics"]) if payload["metrics"] is not None else None,
                    "coefficients": json.dumps(payload["coefficients"])
                    if payload["coefficients"] is not None
                    else None,
                    "contributions": json.dumps(payload["contributions"])
                    if payload["contributions"] is not None
                    else None,
                    "decomposition": json.dumps(payload["decomposition"])
                    if payload["decomposition"] is not None
                    else None,
                    "response_curves": json.dumps(payload["response_curves"])
                    if payload["response_curves"] is not None
                    else None,
                    "diagnostics": json.dumps(payload["diagnostics"]) if payload["diagnostics"] is not None else None,
                    "fitted_params": json.dumps(payload["fitted_params"])
                    if payload["fitted_params"] is not None
                    else None,
                    "model_artifact_path": artifact_path,
                },
            )
            logger.debug(f"Inserted/updated model_results for {model_config_id}")

        else:
            session.execute(
                text("""
                    UPDATE model_configs
                    SET status = 'failed',
                        error_message = :error_message,
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {
                    "id": model_config_id,
                    "error_message": error_message,
                },
            )
            logger.debug(f"Updated model_config status to failed for {model_config_id}")

        session.commit()
        logger.info(f"Successfully committed model result to database for {model_config_id}")
