"""Model trainer service that orchestrates the complete MMM training pipeline."""

import time
from typing import Any, Callable

import numpy as np
import pandas as pd
from numpy.typing import NDArray

from app.services.modeling.base import BaseModel, ModelResult
from app.services.modeling.bayesian import BayesianModel
from app.services.modeling.constraints import ConstraintHandler
from app.services.modeling.contributions import ContributionCalculator
from app.services.modeling.elasticnet import ElasticNetModel
from app.services.modeling.linear import LinearModel
from app.services.modeling.ridge import RidgeModel
from app.services.modeling.transformations import (
    AdstockTransform,
    FeatureTransformer,
    SaturationTransform,
)


class ModelTrainer:
    """
    Orchestrator for the complete Marketing Mix Model training pipeline.

    The training pipeline consists of:
    1. Data preparation and validation
    2. Feature transformation (adstock, saturation)
    3. Constraint setup
    4. Model fitting
    5. Contribution calculation
    6. Response curve generation
    7. Diagnostics and validation

    This class coordinates all components and provides a unified interface
    for training MMM models with various configurations.

    Usage:
        trainer = ModelTrainer(
            model_type='ridge',
            features=[
                {'column': 'tv_spend', 'transformations': {'adstock': {...}, 'saturation': {...}}},
                {'column': 'radio_spend', 'transformations': {...}},
            ],
            target_variable='sales',
            date_column='date',
            constraints={...},
            hyperparameters={'ridge_alpha': 1.0},
        )

        result = trainer.train(df)
    """

    MODEL_CLASSES = {
        "ols": LinearModel,
        "linear": LinearModel,
        "ridge": RidgeModel,
        "elasticnet": ElasticNetModel,
        "bayesian": BayesianModel,
    }

    def __init__(
        self,
        model_type: str = "ridge",
        features: list[dict[str, Any]] | None = None,
        target_variable: str = "sales",
        date_column: str = "date",
        constraints: dict[str, Any] | None = None,
        priors: dict[str, Any] | None = None,
        hyperparameters: dict[str, Any] | None = None,
        seasonality: dict[str, Any] | None = None,
        auto_fit_transformations: bool = True,
        progress_callback: Callable[[int, str], None] | None = None,
    ):
        """
        Initialize the model trainer.

        Args:
            model_type: Type of model ('ols', 'ridge', 'bayesian').
            features: List of feature configurations:
                [
                    {
                        'column': 'tv_spend',
                        'enabled': True,
                        'transformations': {
                            'adstock': {'type': 'geometric', 'decay': 0.5, 'max_lag': 8},
                            'saturation': {'type': 'hill', 'k': 'auto', 's': 'auto'}
                        }
                    },
                    ...
                ]
            target_variable: Name of target column.
            date_column: Name of date column.
            constraints: Constraint configuration (see ConstraintHandler).
            priors: Prior configuration for Bayesian model.
            hyperparameters: Model hyperparameters:
                - ridge_alpha: Regularization for Ridge
                - mcmc_samples, mcmc_chains, etc. for Bayesian
            auto_fit_transformations: Whether to auto-fit transformation params.
            progress_callback: Optional callback for progress updates (pct, message).
        """
        self.model_type = model_type.lower()
        self.features = features or []
        self.target_variable = target_variable
        self.date_column = date_column
        self.constraints = constraints
        self.priors = priors
        self.hyperparameters = hyperparameters or {}
        self.seasonality = seasonality
        self.auto_fit_transformations = auto_fit_transformations
        self.progress_callback = progress_callback

        # State
        self._model: BaseModel | None = None
        self._transformers: dict[str, FeatureTransformer] = {}
        self._constraint_handler: ConstraintHandler | None = None
        self._contribution_calculator: ContributionCalculator | None = None
        self._feature_names: list[str] = []
        self._X_original: NDArray[np.float64] | None = None
        self._X_transformed: NDArray[np.float64] | None = None
        self._y: NDArray[np.float64] | None = None
        self._dates: list[str] | None = None

        # Validate model type
        if self.model_type not in self.MODEL_CLASSES:
            raise ValueError(f"Unknown model type: {self.model_type}. Supported: {list(self.MODEL_CLASSES.keys())}")

    def _update_progress(self, pct: int, message: str) -> None:
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(pct, message)

    def _prepare_data(
        self,
        df: pd.DataFrame,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64], list[str]]:
        """
        Prepare and validate input data.

        Args:
            df: Input DataFrame with features, target, and date columns.

        Returns:
            Tuple of (X, y, dates).
        """
        self._update_progress(5, "Validating input data...")

        # Validate required columns
        if self.target_variable not in df.columns:
            raise ValueError(f"Target variable '{self.target_variable}' not in DataFrame")
        if self.date_column not in df.columns:
            raise ValueError(f"Date column '{self.date_column}' not in DataFrame")

        # Get enabled features
        self._feature_names = []
        for feature_config in self.features:
            if feature_config.get("enabled", True):
                col = feature_config["column"]
                if col not in df.columns:
                    raise ValueError(f"Feature column '{col}' not in DataFrame")
                self._feature_names.append(col)

        if not self._feature_names:
            raise ValueError("No enabled features specified")

        # Sort by date
        df = df.sort_values(self.date_column).reset_index(drop=True)

        # Generate seasonality features if configured
        self._seasonality_features: list[str] = []
        if self.seasonality and self.seasonality.get("enabled"):
            from app.services.seasonality import SeasonalityConfig, SeasonalityService

            try:
                seasonality_config = SeasonalityConfig(**self.seasonality)
                seasonality_service = SeasonalityService(seasonality_config)
                df, feature_metadata = seasonality_service.generate_features(df, self.date_column)
                self._seasonality_features = [f["name"] for f in feature_metadata]
                self._update_progress(
                    8,
                    f"Generated {len(self._seasonality_features)} seasonality features",
                )
            except Exception as e:
                # Log but don't fail if seasonality generation fails
                self._update_progress(8, f"Seasonality generation failed: {e}")

        # Combine user features with seasonality features
        all_features = self._feature_names + self._seasonality_features

        # Extract arrays
        X = df[all_features].values.astype(np.float64)
        y = df[self.target_variable].values.astype(np.float64)

        # Update feature names to include seasonality
        self._all_feature_names = all_features

        # Handle dates
        dates = df[self.date_column].astype(str).tolist()

        # Check for missing values
        if np.any(np.isnan(X)):
            raise ValueError("Feature matrix contains missing values")
        if np.any(np.isnan(y)):
            raise ValueError("Target variable contains missing values")

        self._X_original = X
        self._y = y
        self._dates = dates

        return X, y, dates

    def _fit_transformations(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
    ) -> None:
        """
        Fit and apply transformations to features.

        Args:
            X: Original feature matrix.
            y: Target variable.
        """
        self._update_progress(15, "Fitting transformations...")

        n_user_features = len(self._feature_names)
        n_seasonality_features = len(getattr(self, "_seasonality_features", []))
        n_total_features = n_user_features + n_seasonality_features
        X_transformed = np.zeros((X.shape[0], n_total_features), dtype=np.float64)

        for i, name in enumerate(self._feature_names):
            # Find feature config
            feature_config = next(
                (f for f in self.features if f["column"] == name),
                {},
            )

            transform_config = feature_config.get("transformations", {})
            adstock_config = transform_config.get("adstock")
            saturation_config = transform_config.get("saturation")

            x_col = X[:, i]

            # Check if adstock is enabled
            adstock_enabled = adstock_config.get("enabled", False) if adstock_config else False

            # Auto-fit adstock if requested and enabled
            if (
                self.auto_fit_transformations
                and adstock_config
                and adstock_enabled
                and adstock_config.get("decay") == "auto"
            ):
                optimal_decay = AdstockTransform.fit_decay(x_col, y, max_lag=adstock_config.get("max_lag", 8))
                adstock_config = {**adstock_config, "decay": optimal_decay}

            # Apply adstock only if enabled
            if adstock_config and adstock_enabled:
                # Support both 'type' and 'adstock_type' keys
                adstock_type = adstock_config.get("adstock_type") or adstock_config.get("type", "geometric")
                adstock = AdstockTransform(
                    decay=adstock_config.get("decay", 0.5),
                    max_lag=adstock_config.get("max_lag", 8),
                    adstock_type=adstock_type,
                )
                x_col = adstock.transform(x_col)
            else:
                adstock = None

            # Check if saturation is enabled
            saturation_enabled = saturation_config.get("enabled", False) if saturation_config else False

            # Auto-fit saturation if requested and enabled
            if (
                self.auto_fit_transformations
                and saturation_config
                and saturation_enabled
                and (saturation_config.get("k") == "auto" or saturation_config.get("s") == "auto")
            ):
                k, s = SaturationTransform.fit_hill_params(x_col, y)
                saturation_config = {
                    **saturation_config,
                    "k": k if saturation_config.get("k") == "auto" else saturation_config.get("k", k),
                    "s": s if saturation_config.get("s") == "auto" else saturation_config.get("s", s),
                }

            # Apply saturation only if enabled
            if saturation_config and saturation_enabled:
                # Support both 'type' and 'saturation_type' keys
                saturation_type = saturation_config.get("saturation_type") or saturation_config.get("type", "hill")
                saturation = SaturationTransform(
                    k=saturation_config.get("k", 1.0),
                    s=saturation_config.get("s", 1.0),
                    saturation_type=saturation_type,
                )
                x_col = saturation.transform(x_col)
            else:
                saturation = None

            X_transformed[:, i] = x_col

            # Store transformer
            self._transformers[name] = FeatureTransformer(
                adstock=adstock,
                saturation=saturation,
            )

            self._update_progress(
                15 + int(20 * (i + 1) / n_user_features),
                f"Transformed feature: {name}",
            )

        # Copy seasonality features (no transformation needed)
        seasonality_features = getattr(self, "_seasonality_features", [])
        for j, name in enumerate(seasonality_features):
            X_transformed[:, n_user_features + j] = X[:, n_user_features + j]
            # Store empty transformer for seasonality features
            self._transformers[name] = FeatureTransformer(adstock=None, saturation=None)

        self._X_transformed = X_transformed

    def _setup_constraints(
        self,
    ) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
        """
        Setup constraint handler and get bounds for model.

        Converts contribution constraints to coefficient bounds using the formula:
            contribution = coef * sum(X_transformed)
            contribution_pct = contribution / total_y * 100

        So: coef_max = max_pct / 100 * total_y / sum(X_transformed)
            coef_min = min_pct / 100 * total_y / sum(X_transformed)

        Returns:
            Tuple of (constraint bounds dict, linear constraints list).
        """
        self._update_progress(40, "Setting up constraints...")

        # Use all feature names including seasonality
        all_feature_names = getattr(self, "_all_feature_names", self._feature_names)
        self._constraint_handler = ConstraintHandler.from_config(
            all_feature_names,
            self.constraints,
        )

        # Convert contribution constraints to coefficient bounds
        if self.constraints and self._X_transformed is not None:
            total_y = np.sum(np.abs(self._y))  # Use absolute sum for robustness

            # Handle individual contribution constraints
            for contrib in self.constraints.get("contributions", []):
                var_name = contrib.get("variable")
                min_pct = contrib.get("min_contribution_pct")
                max_pct = contrib.get("max_contribution_pct")

                if var_name in self._feature_names:
                    idx = self._feature_names.index(var_name)
                    x_sum = np.sum(np.abs(self._X_transformed[:, idx]))

                    if x_sum > 0 and total_y > 0:
                        # Convert contribution % to coefficient bounds
                        if max_pct is not None:
                            coef_max = (max_pct / 100.0) * total_y / x_sum
                            self._constraint_handler.add_bound_constraint(var_name, max_val=coef_max)
                        if min_pct is not None:
                            coef_min = (min_pct / 100.0) * total_y / x_sum
                            self._constraint_handler.add_bound_constraint(var_name, min_val=coef_min)

            # Handle group contribution constraints
            for group in self.constraints.get("group_contributions", []):
                group.get("name")
                variables = group.get("variables", [])
                min_pct = group.get("min_contribution_pct")
                max_pct = group.get("max_contribution_pct")

                if not variables:
                    continue

                # Calculate total X sum for the group
                group_x_sum = 0.0
                valid_vars = []
                for var_name in variables:
                    if var_name in self._feature_names:
                        idx = self._feature_names.index(var_name)
                        group_x_sum += np.sum(np.abs(self._X_transformed[:, idx]))
                        valid_vars.append(var_name)

                if group_x_sum > 0 and total_y > 0 and valid_vars:
                    # Distribute the constraint proportionally across group members
                    # Each variable gets a share based on its X magnitude
                    for var_name in valid_vars:
                        idx = self._feature_names.index(var_name)
                        var_x_sum = np.sum(np.abs(self._X_transformed[:, idx]))
                        share = var_x_sum / group_x_sum  # This variable's share of group

                        if max_pct is not None:
                            # Scale max constraint by variable's share of group
                            var_max_pct = max_pct * share
                            coef_max = (var_max_pct / 100.0) * total_y / var_x_sum
                            self._constraint_handler.add_bound_constraint(var_name, max_val=coef_max)
                        if min_pct is not None:
                            # Scale min constraint by variable's share of group
                            # This is stricter than necessary (forces each to contribute)
                            # but guarantees group min is satisfied
                            var_min_pct = min_pct * share
                            coef_min = (var_min_pct / 100.0) * total_y / var_x_sum
                            self._constraint_handler.add_bound_constraint(var_name, min_val=coef_min)

        # Convert bounds to constraint dict format expected by model
        bounds = self._constraint_handler.get_bounds_dict()
        constraints_dict = {}
        for name, (lower, upper) in bounds.items():
            constraint = {}
            if lower > -np.inf:
                constraint["min"] = lower
            if upper < np.inf:
                constraint["max"] = upper
            if lower >= 0:
                constraint["sign"] = "positive"
            elif upper <= 0:
                constraint["sign"] = "negative"
            if constraint:
                constraints_dict[name] = constraint

        # Get linear (relationship) constraints from handler
        linear_constraints = self._constraint_handler.get_linear_constraints()

        return constraints_dict, linear_constraints

    def _create_model(
        self,
        constraints_dict: dict[str, dict[str, Any]],
        linear_constraints: list[dict[str, Any]] | None = None,
    ) -> BaseModel:
        """
        Create the appropriate model instance.

        Args:
            constraints_dict: Constraint bounds per feature.
            linear_constraints: Linear constraints for relationships (e.g., TV >= 1.5 * Radio).

        Returns:
            Configured model instance.
        """
        self._update_progress(45, f"Creating {self.model_type} model...")

        model_class = self.MODEL_CLASSES[self.model_type]

        if self.model_type in ["ols", "linear"]:
            return model_class(
                fit_intercept=True,
                constraints=constraints_dict,
                linear_constraints=linear_constraints,
                bootstrap_n=self.hyperparameters.get("bootstrap_n", 100),
            )

        elif self.model_type == "ridge":
            return model_class(
                alpha=self.hyperparameters.get("ridge_alpha", 1.0),
                fit_intercept=True,
                constraints=constraints_dict,
                linear_constraints=linear_constraints,
                bootstrap_n=self.hyperparameters.get("bootstrap_n", 100),
            )

        elif self.model_type == "elasticnet":
            return model_class(
                alpha=self.hyperparameters.get("elasticnet_alpha", 1.0),
                l1_ratio=self.hyperparameters.get("elasticnet_l1_ratio", 0.5),
                fit_intercept=True,
                constraints=constraints_dict,
                linear_constraints=linear_constraints,
                bootstrap_n=self.hyperparameters.get("bootstrap_n", 100),
            )

        elif self.model_type == "bayesian":
            # Convert priors config to model format
            priors_dict = {}
            if self.priors:
                for prior in self.priors.get("priors", []):
                    priors_dict[prior["variable"]] = {
                        "distribution": prior["distribution"],
                        "params": prior.get("params", {}),
                    }

            return model_class(
                priors=priors_dict,
                n_samples=self.hyperparameters.get("mcmc_samples", 2000),
                n_warmup=self.hyperparameters.get("mcmc_tune", 1000),
                n_chains=self.hyperparameters.get("mcmc_chains", 4),
                target_accept=self.hyperparameters.get("mcmc_target_accept", 0.9),
                fit_intercept=True,
                scale_features=True,
                compute_loo=self.hyperparameters.get("compute_loo", True),
                compute_waic=self.hyperparameters.get("compute_waic", True),
            )

        else:
            raise ValueError(f"Unknown model type: {self.model_type}")

    def _fit_model(self, model: BaseModel) -> ModelResult:
        """
        Fit the model to transformed data.

        Args:
            model: Model instance to fit.

        Returns:
            Model result.
        """
        self._update_progress(50, "Fitting model...")

        # Use all feature names including seasonality
        all_names = getattr(self, "_all_feature_names", self._feature_names)
        model.fit(
            self._X_transformed,
            self._y,
            feature_names=all_names,
        )

        self._model = model
        return model.get_result()

    def _calculate_contributions(self) -> dict[str, Any]:
        """
        Calculate channel contributions.

        Returns:
            Contribution results dictionary.
        """
        self._update_progress(75, "Calculating contributions...")

        # Use all feature names including seasonality
        all_names = getattr(self, "_all_feature_names", self._feature_names)
        seasonality_features = getattr(self, "_seasonality_features", [])

        self._contribution_calculator = ContributionCalculator(
            coefficients=self._model.get_coefficients(),
            intercept=self._model.get_intercept(),
            feature_names=all_names,
        )

        raw_result = self._contribution_calculator.to_summary_dict(
            self._X_transformed,
            self._y,
        )

        # Aggregate seasonality features in contributions
        if seasonality_features:
            aggregated_contributions = []
            seasonality_total = 0.0
            seasonality_pct = 0.0

            for contrib in raw_result["contributions"]:
                var_name = contrib["variable"]
                if var_name in seasonality_features:
                    # Aggregate seasonality contributions
                    seasonality_total += contrib["total_contribution"]
                    seasonality_pct += contrib["contribution_pct"]
                else:
                    # Keep non-seasonality contributions as-is
                    aggregated_contributions.append(contrib)

            # Add aggregated seasonality contribution
            if seasonality_total != 0 or seasonality_pct != 0:
                aggregated_contributions.append(
                    {
                        "variable": "seasonality",
                        "total_contribution": seasonality_total,
                        "contribution_pct": seasonality_pct,
                        "avg_contribution": seasonality_total / len(self._y) if len(self._y) > 0 else 0,
                        "min_contribution": 0,  # Simplified
                        "max_contribution": 0,  # Simplified
                    }
                )

            # Sort by contribution
            aggregated_contributions.sort(key=lambda x: x["total_contribution"], reverse=True)
            raw_result["contributions"] = aggregated_contributions

        return raw_result

    def _calculate_response_curves(self) -> dict[str, dict[str, Any]]:
        """
        Calculate response curves for each feature.

        Returns:
            Response curve data per feature.
        """
        self._update_progress(85, "Generating response curves...")

        # Get transformer configs - only for user features, not seasonality
        transformer_configs = {}
        for name in self._feature_names:
            transformer = self._transformers.get(name)
            if transformer:
                transformer_configs[name] = transformer.get_params()

        # Only calculate response curves for user features (not seasonality)
        # Need to filter X_original to only user features
        n_user_features = len(self._feature_names)
        X_user_only = self._X_original[:, :n_user_features] if self._X_original is not None else None

        if X_user_only is None:
            return {}

        # Create a temporary calculator with only user features
        user_coefficients = {name: self._model.get_coefficients().get(name, 0) for name in self._feature_names}
        temp_calculator = ContributionCalculator(
            coefficients=user_coefficients,
            intercept=self._model.get_intercept(),
            feature_names=self._feature_names,
        )

        return temp_calculator.calculate_response_curves(
            X_user_only,
            transformer_configs,
        )

    def _get_decomposition(self) -> dict[str, Any]:
        """
        Get time series decomposition.

        Returns:
            Decomposition data for visualization.
        """
        self._update_progress(90, "Creating decomposition...")

        raw_decomp = self._contribution_calculator.get_decomposition_dataframe(
            self._X_transformed,
            self._y,
            self._dates,
        )

        # Restructure decomposition to separate contributions from other fields
        decomp = {
            "dates": raw_decomp.get("dates", []),
            "actual": raw_decomp.get("actual", []),
            "predicted": raw_decomp.get("predicted", []),
            "base": raw_decomp.get("base", []),
            "contributions": {},
            "support_values": {},
            "transformed_values": {},
        }

        # Get all feature names and seasonality features
        all_names = getattr(self, "_all_feature_names", self._feature_names)
        seasonality_features = getattr(self, "_seasonality_features", [])

        # Extract feature contributions - aggregate seasonality features together
        seasonality_contrib = None
        for name in all_names:
            if name in raw_decomp:
                if name in seasonality_features:
                    # Aggregate seasonality contributions
                    if seasonality_contrib is None:
                        seasonality_contrib = [0.0] * len(raw_decomp[name])
                    seasonality_contrib = [a + b for a, b in zip(seasonality_contrib, raw_decomp[name])]
                else:
                    # Regular feature contribution
                    decomp["contributions"][name] = raw_decomp[name]

        # Add aggregated seasonality contribution if present
        if seasonality_contrib is not None:
            decomp["contributions"]["seasonality"] = seasonality_contrib

        # Add original (support) values for each user feature only
        if self._X_original is not None:
            for i, name in enumerate(self._feature_names):
                decomp["support_values"][name] = self._X_original[:, i].tolist()

            # Add transformed values for user features only
            for i, name in enumerate(self._feature_names):
                decomp["transformed_values"][name] = self._X_transformed[:, i].tolist()

        return decomp

    def _validate_results(self, result: ModelResult) -> dict[str, Any]:
        """
        Validate model results against constraints.

        Args:
            result: Model fitting result.

        Returns:
            Validation report.
        """
        self._update_progress(95, "Validating results...")

        validation = {
            "coefficient_constraints": {},
            "contribution_constraints": {},
            "diagnostics": {},
        }

        # Validate coefficient constraints
        if self._constraint_handler:
            validation["coefficient_constraints"] = self._constraint_handler.validate_coefficients(result.coefficients)

        # Check diagnostics
        diagnostics = {}

        # VIF check (multicollinearity)
        high_vif = {k: v for k, v in result.vif.items() if v > 10}
        diagnostics["high_vif_features"] = high_vif
        diagnostics["vif_warning"] = len(high_vif) > 0

        # Durbin-Watson (autocorrelation)
        if result.durbin_watson is not None:
            diagnostics["durbin_watson"] = result.durbin_watson
            diagnostics["autocorrelation_warning"] = result.durbin_watson < 1.5 or result.durbin_watson > 2.5

        # Jarque-Bera (normality)
        if result.jarque_bera_pvalue is not None:
            diagnostics["jarque_bera_pvalue"] = result.jarque_bera_pvalue
            diagnostics["normality_warning"] = result.jarque_bera_pvalue < 0.05

        # Bayesian diagnostics
        if result.r_hat:
            non_converged = {k: v for k, v in result.r_hat.items() if v > 1.1}
            diagnostics["non_converged_params"] = non_converged
            diagnostics["convergence_warning"] = len(non_converged) > 0

        validation["diagnostics"] = diagnostics

        return validation

    def train(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Execute the complete training pipeline.

        Args:
            df: Input DataFrame with all required columns.

        Returns:
            Complete training results dictionary containing:
                - model_result: Fitted model results
                - contributions: Channel contribution analysis
                - decomposition: Time series decomposition
                - response_curves: Response curves per channel
                - validation: Constraint validation results
                - transformations: Applied transformation parameters
                - metadata: Training metadata
        """
        start_time = time.time()

        try:
            # Step 1: Prepare data
            X, y, dates = self._prepare_data(df)

            # Step 2: Fit and apply transformations
            self._fit_transformations(X, y)

            # Step 3: Setup constraints
            constraints_dict, linear_constraints = self._setup_constraints()

            # Step 4: Create model
            model = self._create_model(constraints_dict, linear_constraints)

            # Step 5: Fit model
            model_result = self._fit_model(model)

            # Step 6: Calculate contributions
            contributions = self._calculate_contributions()

            # Step 7: Calculate response curves
            response_curves = self._calculate_response_curves()

            # Step 8: Get decomposition
            decomposition = self._get_decomposition()

            # Step 9: Validate results
            validation = self._validate_results(model_result)

            # Collect transformation parameters
            transformations = {}
            for name, transformer in self._transformers.items():
                transformations[name] = transformer.get_params()

            training_time = time.time() - start_time

            self._update_progress(100, "Training complete!")

            return {
                "status": "completed",
                "model_result": model_result.to_dict(),
                "contributions": contributions,
                "decomposition": decomposition,
                "response_curves": response_curves,
                "validation": validation,
                "transformations": transformations,
                "metadata": {
                    "model_type": self.model_type,
                    "n_features": len(self._feature_names),
                    "n_seasonality_features": len(getattr(self, "_seasonality_features", [])),
                    "n_observations": len(y),
                    "feature_names": self._feature_names,
                    "seasonality_features": getattr(self, "_seasonality_features", []),
                    "training_time_seconds": training_time,
                    "target_variable": self.target_variable,
                    "date_range": {
                        "start": dates[0] if dates else None,
                        "end": dates[-1] if dates else None,
                    },
                },
            }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    def predict(
        self,
        df: pd.DataFrame,
        include_contributions: bool = True,
    ) -> dict[str, Any]:
        """
        Generate predictions for new data.

        Args:
            df: New data with same feature columns.
            include_contributions: Whether to include contribution breakdown.

        Returns:
            Prediction results.
        """
        if self._model is None:
            raise RuntimeError("Model must be trained before prediction")

        # Prepare features
        X = df[self._feature_names].values.astype(np.float64)

        # Apply transformations
        X_transformed = np.zeros_like(X)
        for i, name in enumerate(self._feature_names):
            transformer = self._transformers.get(name, FeatureTransformer())
            X_transformed[:, i] = transformer.transform(X[:, i])

        # Get predictions
        predictions = self._model.predict(X_transformed)

        result = {
            "predictions": predictions.tolist(),
        }

        # Optionally include contributions
        if include_contributions and self._contribution_calculator:
            contrib_result = self._contribution_calculator.calculate(X_transformed)
            result["contributions_time_series"] = {
                name: contrib_result["contributions_time_series"][name].tolist() for name in self._feature_names
            }
            result["base"] = contrib_result["base_time_series"].tolist()

        return result

    def get_model(self) -> BaseModel:
        """Get the fitted model instance."""
        if self._model is None:
            raise RuntimeError("Model must be trained first")
        return self._model

    def get_feature_importance(self) -> dict[str, float]:
        """
        Get feature importance based on contribution percentages.

        Returns:
            Dictionary of feature importance scores.
        """
        if self._contribution_calculator is None:
            raise RuntimeError("Model must be trained first")

        result = self._contribution_calculator.calculate(self._X_transformed)
        return result["contribution_pct"]

    def get_summary(self) -> str:
        """
        Get text summary of model results.

        Returns:
            Formatted summary string.
        """
        if self._model is None:
            raise RuntimeError("Model must be trained first")

        result = self._model.get_result()
        contrib = self._contribution_calculator.to_summary_dict(self._X_transformed, self._y)

        lines = [
            "=" * 60,
            "MARKETING MIX MODEL SUMMARY",
            "=" * 60,
            f"Model Type: {self.model_type.upper()}",
            f"Observations: {result.n_observations}",
            f"Features: {result.n_features}",
            "",
            "FIT METRICS",
            "-" * 40,
            f"R-squared:          {result.r_squared:.4f}",
            f"Adjusted R-squared: {result.adjusted_r_squared:.4f}",
            f"RMSE:               {result.rmse:.2f}",
            f"MAPE:               {result.mape:.2f}%",
            "",
            "COEFFICIENTS",
            "-" * 40,
        ]

        for name in self._feature_names:
            coef = result.coefficients[name]
            se = result.std_errors.get(name, 0)
            lines.append(f"{name:20s}  {coef:10.4f}  (SE: {se:.4f})")

        lines.append(f"{'Intercept':20s}  {result.intercept:10.4f}")

        lines.extend(
            [
                "",
                "CONTRIBUTIONS",
                "-" * 40,
            ]
        )

        for item in contrib["contributions"]:
            lines.append(f"{item['variable']:20s}  {item['contribution_pct']:6.1f}%")

        lines.append("=" * 60)

        return "\n".join(lines)
