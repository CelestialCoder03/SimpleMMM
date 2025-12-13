"""Celery tasks for async processing."""

import logging
import os
from typing import Any

from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

# Configure PyTensor for Celery workers (used by PyMC)
# This ensures stable operation in multi-process environments
os.environ.setdefault("PYTENSOR_FLAGS", "device=cpu,floatX=float64")


@celery_app.task(name="app.workers.tasks.health_check")
def health_check() -> dict[str, str]:
    """Simple health check task for testing Celery connectivity."""
    return {"status": "ok", "worker": "healthy"}


@celery_app.task(bind=True, name="app.workers.tasks.train_mmm_model")
def train_mmm_model(
    self,
    model_config_id: str,
    dataset_path: str,
    config: dict[str, Any],
) -> dict[str, Any]:
    """
    Train a Marketing Mix Model asynchronously.

    Args:
        model_config_id: ID of the ModelConfig record.
        dataset_path: Path to the dataset file.
        config: Model configuration dictionary containing:
            - model_type: 'ols', 'ridge', or 'bayesian'
            - features: List of feature configurations
            - target_variable: Name of target column
            - date_column: Name of date column
            - constraints: Optional constraint configuration
            - priors: Optional prior configuration
            - hyperparameters: Optional hyperparameter configuration

    Returns:
        Dictionary with training results.
    """
    from app.services.modeling.trainer import ModelTrainer
    from app.workers.db import save_model_training_result

    task_id = self.request.id

    def progress_callback(pct: int, message: str) -> None:
        self.update_state(
            state="PROGRESS",
            meta={"progress": pct, "status": message},
        )

    try:
        self.update_state(
            state="PROGRESS",
            meta={"progress": 0, "status": "Loading dataset..."},
        )

        # Load dataset
        # Keep file handling consistent with the rest of the app (supports csv/xls/xlsx)
        from app.services.data_processor import DataProcessorService

        df = DataProcessorService().read_file(dataset_path)

        self.update_state(
            state="PROGRESS",
            meta={"progress": 5, "status": "Initializing trainer..."},
        )

        # Create trainer
        trainer = ModelTrainer(
            model_type=config.get("model_type", "ridge"),
            features=config.get("features", []),
            target_variable=config.get("target_variable", "sales"),
            date_column=config.get("date_column", "date"),
            constraints=config.get("constraints"),
            priors=config.get("priors"),
            hyperparameters=config.get("hyperparameters", {}),
            seasonality=config.get("seasonality"),
            auto_fit_transformations=config.get("auto_fit_transformations", True),
            progress_callback=progress_callback,
        )

        # Train model
        result = trainer.train(df)

        # Persist model artifact (pickle) so it can be reloaded for prediction
        artifact_path = None
        try:
            import pickle
            from pathlib import Path

            from app.core.config import settings

            artifacts_dir = Path(settings.UPLOAD_DIR) / "artifacts"
            artifacts_dir.mkdir(parents=True, exist_ok=True)
            artifact_path = str(artifacts_dir / f"model_{model_config_id}.pkl")
            with open(artifact_path, "wb") as f:
                pickle.dump(trainer, f)
            logger.info(f"Saved model artifact to {artifact_path}")
        except Exception as e:
            logger.warning(f"Failed to save model artifact for {model_config_id}: {e}")

        payload = {
            "task_id": task_id,
            "model_config_id": model_config_id,
            **result,
        }

        # Persist training outcome (status + model_results) for TTL-safe retrieval
        try:
            save_model_training_result(
                model_config_id=model_config_id,
                raw_result=result,
                artifact_path=artifact_path,
            )
            logger.info(f"Successfully persisted model result for config {model_config_id}")
        except Exception as e:
            # Log the error but don't fail the Celery task
            logger.error(
                f"Failed to persist model result for config {model_config_id}: {e}",
                exc_info=True,
            )

        return payload

    except Exception as e:
        fail_payload = {
            "task_id": task_id,
            "model_config_id": model_config_id,
            "status": "failed",
            "error": str(e),
            "error_type": type(e).__name__,
        }

        try:
            save_model_training_result(model_config_id=model_config_id, raw_result=fail_payload)
            logger.info(f"Persisted failure status for config {model_config_id}")
        except Exception as persist_err:
            logger.error(
                f"Failed to persist failure status for config {model_config_id}: {persist_err}",
                exc_info=True,
            )

        return fail_payload


@celery_app.task(bind=True, name="app.workers.tasks.process_dataset_file")
def process_dataset_file(
    self,
    dataset_id: str,
    file_path: str,
) -> dict[str, Any]:
    """Process uploaded dataset file asynchronously.

    Args:
        dataset_id: ID of the dataset record
        file_path: Path to the uploaded file

    Returns:
        Dictionary with processing results.
    """
    from app.services.data_processor import DataProcessorService
    from app.workers.db import update_dataset_status

    task_id = self.request.id

    self.update_state(
        state="PROGRESS",
        meta={"progress": 0, "status": "Starting file processing..."},
    )

    try:
        # Initialize processor
        processor = DataProcessorService()

        self.update_state(
            state="PROGRESS",
            meta={"progress": 20, "status": "Reading file..."},
        )

        # Read file
        df = processor.read_file(file_path)

        self.update_state(
            state="PROGRESS",
            meta={"progress": 50, "status": "Analyzing columns..."},
        )

        # Analyze
        metadata = processor.analyze_dataframe(df)

        self.update_state(
            state="PROGRESS",
            meta={"progress": 80, "status": "Saving to database..."},
        )

        # Update dataset in database with READY status
        update_dataset_status(
            dataset_id=dataset_id,
            status="ready",
            row_count=metadata["row_count"],
            column_count=metadata["column_count"],
            columns_metadata=metadata["columns"],
        )

        self.update_state(
            state="PROGRESS",
            meta={"progress": 100, "status": "Processing complete!"},
        )

        return {
            "task_id": task_id,
            "dataset_id": dataset_id,
            "status": "completed",
            "row_count": metadata["row_count"],
            "column_count": metadata["column_count"],
            "columns": metadata["columns"],
            "memory_usage_bytes": metadata["memory_usage_bytes"],
        }

    except Exception as e:
        # Update dataset with FAILED status
        try:
            update_dataset_status(
                dataset_id=dataset_id,
                status="failed",
                error_message=str(e),
            )
        except Exception:
            pass  # Don't fail the task if DB update fails

        return {
            "task_id": task_id,
            "dataset_id": dataset_id,
            "status": "failed",
            "error": str(e),
        }


@celery_app.task(bind=True, name="app.workers.tasks.train_hierarchical_model")
def train_hierarchical_model(self, hierarchical_config_id: str) -> dict:
    """
    Train all sub-models for a hierarchical model.

    This task orchestrates the training of multiple sub-models,
    one for each dimension combination (e.g., each region).

    Args:
        hierarchical_config_id: UUID of the hierarchical model config.

    Returns:
        Dictionary with training results summary.
    """
    import asyncio

    import pandas as pd
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.session import async_session_maker
    from app.models import (
        HierarchicalModelConfig,
        ModelResult,
        SubModelConfig,
        SubModelStatus,
    )
    from app.services.file_storage import FileStorage
    from app.services.modeling.hierarchical_trainer import HierarchicalTrainer

    task_id = self.request.id

    async def _run_training():
        async with async_session_maker() as db:
            # Load config
            result = await db.execute(
                select(HierarchicalModelConfig)
                .where(HierarchicalModelConfig.id == hierarchical_config_id)
                .options(
                    selectinload(HierarchicalModelConfig.dataset),
                    selectinload(HierarchicalModelConfig.parent_model),
                )
            )
            config = result.scalar_one_or_none()

            if not config:
                return {"status": "failed", "error": "Config not found"}

            # Load dataset
            storage = FileStorage()
            df = pd.read_csv(storage.get_path(config.dataset.file_path))

            # Get dimension combinations
            trainer = HierarchicalTrainer(config, df)
            combinations = trainer.get_dimension_combinations()

            # Get parent model result if exists
            inherited_config = None
            if config.parent_model_id:
                result = await db.execute(
                    select(ModelResult).where(ModelResult.model_config_id == config.parent_model_id)
                )
                parent_result = result.scalar_one_or_none()

                if parent_result and parent_result.coefficients:
                    parent_data = {
                        "coefficients": parent_result.coefficients.get("coefficients", {}),
                        "std_errors": parent_result.coefficients.get("std_errors", {}),
                        "ci_lower": parent_result.coefficients.get("ci_lower", {}),
                        "ci_upper": parent_result.coefficients.get("ci_upper", {}),
                    }

                    if config.model_type == "bayesian" and config.inherit_priors:
                        inherited_config = trainer.generate_priors_from_parent(parent_data, config.prior_weight)
                    elif config.inherit_constraints:
                        inherited_config = trainer.generate_constraints_from_parent(
                            parent_data, config.constraint_relaxation
                        )

            # Create sub-model records
            for dim_values in combinations:
                sub_model = SubModelConfig(
                    hierarchical_config_id=config.id,
                    dimension_values=dim_values,
                    status=SubModelStatus.PENDING.value,
                )
                db.add(sub_model)

            await db.commit()

            return {
                "combinations": combinations,
                "inherited_config": inherited_config,
                "total": len(combinations),
            }

    # Get combinations and inherited config
    setup_result = asyncio.run(_run_training())

    if setup_result.get("status") == "failed":
        return setup_result

    combinations = setup_result["combinations"]
    inherited_config = setup_result["inherited_config"]
    total = setup_result["total"]

    self.update_state(
        state="PROGRESS",
        meta={"progress": 0, "status": f"Training {total} sub-models..."},
    )

    # Dispatch sub-models in parallel via Celery group
    from celery import group

    job = group(
        train_sub_model.s(
            hierarchical_config_id=hierarchical_config_id,
            dimension_values=dim_values,
            inherited_config=inherited_config,
        )
        for dim_values in combinations
    )
    group_result = job.apply_async()

    # Poll for completion and report progress
    results = []
    while not group_result.ready():
        import time

        time.sleep(2)
        completed_count = sum(1 for r in group_result.results if r.ready())
        self.update_state(
            state="PROGRESS",
            meta={
                "progress": int(completed_count / total * 100) if total else 0,
                "status": f"Completed {completed_count}/{total} sub-models",
                "completed": completed_count,
                "total": total,
            },
        )

    results = [r.result for r in group_result.results]

    # Update config status
    async def _update_status():
        async with async_session_maker() as db:
            result = await db.execute(
                select(HierarchicalModelConfig).where(HierarchicalModelConfig.id == hierarchical_config_id)
            )
            config = result.scalar_one_or_none()
            if config:
                completed = sum(1 for r in results if r.get("status") == "completed")
                failed = sum(1 for r in results if r.get("status") == "failed")

                if failed == total:
                    config.status = "failed"
                elif completed == total:
                    config.status = "completed"
                else:
                    config.status = "completed"  # Partial success

                await db.commit()

    asyncio.run(_update_status())

    completed = sum(1 for r in results if r.get("status") == "completed")
    failed = sum(1 for r in results if r.get("status") == "failed")
    skipped = sum(1 for r in results if r.get("status") == "skipped")

    return {
        "task_id": task_id,
        "status": "completed",
        "total": total,
        "completed": completed,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }


@celery_app.task(bind=True, name="app.workers.tasks.train_sub_model")
def train_sub_model(
    self,
    hierarchical_config_id: str,
    dimension_values: dict,
    inherited_config: dict | None = None,
) -> dict:
    """
    Train a single sub-model (for parallel execution).

    Args:
        hierarchical_config_id: UUID of hierarchical config.
        dimension_values: Dimension values for this sub-model.
        inherited_config: Constraints or priors from parent model.

    Returns:
        Training result dictionary.
    """
    from app.services.modeling.hierarchical_trainer import train_single_sub_model

    return train_single_sub_model(
        hierarchical_config_id=hierarchical_config_id,
        dimension_values=dimension_values,
        inherited_config=inherited_config,
    )


@celery_app.task(name="app.workers.tasks.cleanup_expired_reset_tokens")
def cleanup_expired_reset_tokens() -> dict[str, Any]:
    """Remove expired password reset tokens from the database."""
    from sqlalchemy import text

    from app.workers.db import get_sync_session

    with get_sync_session() as session:
        result = session.execute(
            text("""
                DELETE FROM password_reset_tokens
                WHERE expires_at < NOW()
            """)
        )
        deleted = result.rowcount
        session.commit()

    logger.info(f"Cleaned up {deleted} expired password reset tokens")
    return {"deleted": deleted}


@celery_app.task(name="app.workers.tasks.cleanup_stale_uploads")
def cleanup_stale_uploads(max_age_hours: int = 72) -> dict[str, Any]:
    """Remove upload files for datasets stuck in 'uploading' status beyond max_age_hours."""
    import os
    from pathlib import Path

    from sqlalchemy import text

    from app.core.config import settings
    from app.workers.db import get_sync_session

    removed_files: list[str] = []

    with get_sync_session() as session:
        rows = (
            session.execute(
                text("""
                SELECT id, file_path FROM datasets
                WHERE status = 'uploading'
                  AND updated_at < NOW() - INTERVAL ':hours hours'
            """),
                {"hours": max_age_hours},
            )
            .mappings()
            .all()
        )

        for row in rows:
            file_path = row.get("file_path")
            if file_path:
                stored_path = Path(file_path)
                full_path = stored_path if stored_path.is_absolute() else Path(settings.UPLOAD_DIR) / file_path
                if full_path.exists():
                    try:
                        os.remove(full_path)
                        removed_files.append(str(full_path))
                    except OSError as e:
                        logger.warning(f"Failed to remove stale upload {full_path}: {e}")

            session.execute(
                text("""
                    UPDATE datasets
                    SET status = 'failed',
                        error_message = 'Upload timed out and was cleaned up',
                        updated_at = NOW()
                    WHERE id = :id
                """),
                {"id": row["id"]},
            )

        session.commit()

    logger.info(f"Cleaned up {len(removed_files)} stale upload files")
    return {"removed_files": len(removed_files), "updated_datasets": len(rows)}
