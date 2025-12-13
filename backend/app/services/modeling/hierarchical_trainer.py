"""Hierarchical model trainer for multi-dimensional MMM."""

import time

import pandas as pd

from app.models import HierarchicalModelConfig, SubModelConfig, SubModelStatus


class HierarchicalTrainer:
    """
    Trainer for hierarchical marketing mix models.

    Handles:
    - Data splitting by dimension columns
    - Constraint/prior generation from parent model
    - Parallel sub-model training orchestration
    """

    def __init__(
        self,
        config: HierarchicalModelConfig,
        dataset: pd.DataFrame,
    ):
        """
        Initialize hierarchical trainer.

        Args:
            config: Hierarchical model configuration.
            dataset: Full dataset for training.
        """
        self.config = config
        self.dataset = dataset
        self.dimension_columns = config.dimension_columns

    def get_dimension_combinations(self) -> list[dict]:
        """
        Get all unique dimension value combinations.

        Returns:
            List of dimension value dictionaries.
        """
        if len(self.dimension_columns) == 1:
            col = self.dimension_columns[0]
            return [{col: v} for v in self.dataset[col].unique()]
        else:
            # Multi-dimension cross product
            combinations = self.dataset[self.dimension_columns].drop_duplicates()
            return combinations.to_dict("records")

    def get_subset_data(self, dimension_values: dict) -> pd.DataFrame:
        """
        Get data subset for specific dimension values.

        Args:
            dimension_values: Dictionary of dimension column -> value.

        Returns:
            Filtered DataFrame.
        """
        mask = pd.Series(True, index=self.dataset.index)
        for col, val in dimension_values.items():
            mask &= self.dataset[col] == val
        return self.dataset[mask].copy()

    def generate_constraints_from_parent(
        self,
        parent_result: dict,
        relaxation: float = 0.2,
    ) -> dict:
        """
        Generate constraints from parent model coefficients.

        Uses parent model's confidence intervals, relaxed by the
        specified factor, as bounds for sub-model coefficients.

        Args:
            parent_result: Parent model result dictionary.
            relaxation: Relaxation factor (0-1) to widen constraints.

        Returns:
            Constraints configuration for sub-models.
        """
        constraints = {"coefficients": []}

        coefficients = parent_result.get("coefficients", {})
        ci_lower = parent_result.get("ci_lower", {})
        ci_upper = parent_result.get("ci_upper", {})

        for var, estimate in coefficients.items():
            if var == "intercept":
                continue

            lower = ci_lower.get(var, estimate * 0.5)
            upper = ci_upper.get(var, estimate * 1.5)

            # Relax the constraints
            range_width = upper - lower
            relaxed_lower = lower - range_width * relaxation
            relaxed_upper = upper + range_width * relaxation

            # Ensure positive constraint if parent coefficient is positive
            if estimate > 0:
                relaxed_lower = max(0, relaxed_lower)

            constraints["coefficients"].append(
                {
                    "variable": var,
                    "min": float(relaxed_lower),
                    "max": float(relaxed_upper),
                }
            )

        return constraints

    def generate_priors_from_parent(
        self,
        parent_result: dict,
        weight: float = 0.5,
    ) -> dict:
        """
        Generate Bayesian priors from parent model coefficients.

        Uses parent model's coefficient estimates as prior means,
        with standard errors adjusted by the weight parameter.

        Args:
            parent_result: Parent model result dictionary.
            weight: Prior weight (0-1). Higher = tighter priors.

        Returns:
            Priors configuration for Bayesian sub-models.
        """
        priors = {"priors": []}

        coefficients = parent_result.get("coefficients", {})
        std_errors = parent_result.get("std_errors", {})

        for var, estimate in coefficients.items():
            if var == "intercept":
                continue

            std_error = std_errors.get(var, abs(estimate) * 0.5)

            # Adjust sigma based on weight
            # Higher weight = smaller sigma = tighter prior
            adjusted_sigma = std_error / weight if weight > 0 else std_error * 2

            if estimate > 0:
                # Positive coefficient: use truncated normal
                priors["priors"].append(
                    {
                        "variable": var,
                        "distribution": "truncated_normal",
                        "params": {
                            "mu": float(estimate),
                            "sigma": float(adjusted_sigma),
                            "lower": 0,
                        },
                    }
                )
            else:
                # Negative or zero: use normal
                priors["priors"].append(
                    {
                        "variable": var,
                        "distribution": "normal",
                        "params": {
                            "mu": float(estimate),
                            "sigma": float(adjusted_sigma),
                        },
                    }
                )

        return priors

    def get_dimension_key(self, dimension_values: dict) -> str:
        """
        Get a string key for dimension values.

        Args:
            dimension_values: Dictionary of dimension values.

        Returns:
            String key like "华东" or "华东_线上".
        """
        return "_".join(str(v) for v in dimension_values.values())


def train_single_sub_model(
    hierarchical_config_id: str,
    dimension_values: dict,
    inherited_config: dict | None = None,
) -> dict:
    """
    Train a single sub-model for specific dimension values.

    This function is called by Celery workers.

    Args:
        hierarchical_config_id: UUID of hierarchical config.
        dimension_values: Dimension values for this sub-model.
        inherited_config: Constraints or priors from parent model.

    Returns:
        Training result dictionary.
    """
    import asyncio

    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    from app.db.session import async_session_maker
    from app.models import HierarchicalModelConfig, ModelConfig, ModelResult
    from app.services.file_storage import FileStorage
    from app.services.modeling.trainer import ModelTrainer

    async def _train():
        async with async_session_maker() as db:
            # Load config
            result = await db.execute(
                select(HierarchicalModelConfig)
                .where(HierarchicalModelConfig.id == hierarchical_config_id)
                .options(selectinload(HierarchicalModelConfig.dataset))
            )
            config = result.scalar_one_or_none()

            if not config:
                return {"status": "failed", "error": "Config not found"}

            # Find or create sub-model record
            result = await db.execute(
                select(SubModelConfig).where(
                    SubModelConfig.hierarchical_config_id == hierarchical_config_id,
                    SubModelConfig.dimension_values == dimension_values,
                )
            )
            sub_model = result.scalar_one_or_none()

            if not sub_model:
                sub_model = SubModelConfig(
                    hierarchical_config_id=config.id,
                    dimension_values=dimension_values,
                    status=SubModelStatus.TRAINING.value,
                )
                db.add(sub_model)
                await db.commit()
                await db.refresh(sub_model)
            else:
                sub_model.status = SubModelStatus.TRAINING.value
                await db.commit()

            try:
                start_time = time.time()

                # Load dataset
                storage = FileStorage()
                df = pd.read_csv(storage.get_path(config.dataset.file_path))

                # Get subset data
                trainer_helper = HierarchicalTrainer(config, df)
                subset_df = trainer_helper.get_subset_data(dimension_values)

                # Check minimum observations
                if len(subset_df) < config.min_observations:
                    sub_model.status = SubModelStatus.SKIPPED.value
                    sub_model.error_message = (
                        f"Insufficient data: {len(subset_df)} rows (minimum: {config.min_observations})"
                    )
                    sub_model.observation_count = len(subset_df)
                    await db.commit()
                    return {
                        "status": "skipped",
                        "reason": sub_model.error_message,
                        "dimension_values": dimension_values,
                    }

                sub_model.observation_count = len(subset_df)

                # Prepare feature configs
                features = config.features or []

                # Merge inherited config with any custom config
                if config.model_type == "bayesian" and inherited_config:
                    model_kwargs = {"priors": inherited_config.get("priors", {})}
                elif inherited_config:
                    model_kwargs = {"constraints": inherited_config.get("coefficients", [])}
                else:
                    model_kwargs = {}

                # Create model trainer
                trainer = ModelTrainer(
                    model_type=config.model_type,
                    target_variable=config.target_variable,
                    date_column=config.date_column,
                    features=features,
                    **model_kwargs,
                )

                # Train model
                training_result = trainer.train(subset_df)

                training_time = time.time() - start_time

                # Create model config for this sub-model
                dimension_key = trainer_helper.get_dimension_key(dimension_values)
                model_config = ModelConfig(
                    project_id=config.project_id,
                    dataset_id=config.dataset_id,
                    name=f"{config.name} - {dimension_key}",
                    model_type=config.model_type,
                    target_variable=config.target_variable,
                    date_column=config.date_column,
                    features=features,
                    status="completed",
                )
                db.add(model_config)
                await db.commit()
                await db.refresh(model_config)

                # Create model result
                model_result_data = training_result.get("model_result", {})
                model_result = ModelResult(
                    model_config_id=model_config.id,
                    training_duration_seconds=training_time,
                    metrics=model_result_data.get("metrics"),
                    coefficients=model_result_data.get("coefficients"),
                    contributions=model_result_data.get("contributions"),
                    decomposition=model_result_data.get("decomposition"),
                    response_curves=model_result_data.get("response_curves"),
                    diagnostics=model_result_data.get("diagnostics"),
                )
                db.add(model_result)

                # Update sub-model record
                sub_model.model_config_id = model_config.id
                sub_model.status = SubModelStatus.COMPLETED.value
                sub_model.r_squared = model_result_data.get("metrics", {}).get("r_squared")
                sub_model.rmse = model_result_data.get("metrics", {}).get("rmse")
                sub_model.training_duration_seconds = training_time

                await db.commit()

                return {
                    "status": "completed",
                    "dimension_values": dimension_values,
                    "metrics": model_result_data.get("metrics", {}),
                    "training_time": training_time,
                }

            except Exception as e:
                sub_model.status = SubModelStatus.FAILED.value
                sub_model.error_message = str(e)[:1000]
                await db.commit()

                return {
                    "status": "failed",
                    "dimension_values": dimension_values,
                    "error": str(e),
                }

    # Run async function
    return asyncio.run(_train())
