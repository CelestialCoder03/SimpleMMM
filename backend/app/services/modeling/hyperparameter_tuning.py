"""Hyperparameter tuning with cross-validation for Marketing Mix Models."""

from dataclasses import dataclass
from typing import Any, Callable

import numpy as np
from numpy.typing import NDArray
from sklearn.model_selection import KFold, TimeSeriesSplit

from app.services.modeling.base import BaseModel
from app.services.modeling.elasticnet import ElasticNetModel
from app.services.modeling.ridge import RidgeModel


@dataclass
class CVResult:
    """Cross-validation result for a single hyperparameter configuration."""

    params: dict[str, Any]
    mean_score: float
    std_score: float
    scores: list[float]
    mean_train_score: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "params": self.params,
            "mean_score": self.mean_score,
            "std_score": self.std_score,
            "scores": self.scores,
            "mean_train_score": self.mean_train_score,
        }


@dataclass
class TuningResult:
    """Complete hyperparameter tuning result."""

    best_params: dict[str, Any]
    best_score: float
    cv_results: list[CVResult]
    best_model: BaseModel | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "best_params": self.best_params,
            "best_score": self.best_score,
            "cv_results": [r.to_dict() for r in self.cv_results],
        }


class HyperparameterTuner:
    """
    Hyperparameter tuning with cross-validation for MMM models.

    Supports:
    - Time series cross-validation (recommended for MMM)
    - Standard k-fold cross-validation
    - Grid search over hyperparameter space
    - Multiple scoring metrics

    For time series data, TimeSeriesSplit is used by default to maintain
    temporal order and avoid data leakage.

    Usage:
        tuner = HyperparameterTuner(
            model_type="ridge",
            param_grid={"alpha": [0.1, 1.0, 10.0]},
            cv=5,
            scoring="r_squared",
        )
        result = tuner.fit(X, y, feature_names)
        best_model = result.best_model
    """

    SUPPORTED_MODELS = ["ridge", "elasticnet"]

    SCORING_FUNCTIONS = {
        "r_squared": lambda y_true, y_pred: 1
        - np.sum((y_true - y_pred) ** 2) / np.sum((y_true - np.mean(y_true)) ** 2),
        "neg_rmse": lambda y_true, y_pred: -np.sqrt(np.mean((y_true - y_pred) ** 2)),
        "neg_mae": lambda y_true, y_pred: -np.mean(np.abs(y_true - y_pred)),
        "neg_mape": lambda y_true, y_pred: -np.mean(np.abs((y_true - y_pred) / np.where(y_true != 0, y_true, 1))) * 100,
    }

    def __init__(
        self,
        model_type: str = "ridge",
        param_grid: dict[str, list[Any]] | None = None,
        cv: int = 5,
        scoring: str = "r_squared",
        use_time_series_cv: bool = True,
        constraints: dict[str, dict[str, Any]] | None = None,
        progress_callback: Callable[[int, str], None] | None = None,
    ):
        """
        Initialize hyperparameter tuner.

        Args:
            model_type: Type of model ("ridge" or "elasticnet").
            param_grid: Dictionary of parameter names to lists of values to try.
                For Ridge: {"alpha": [0.1, 1.0, 10.0]}
                For ElasticNet: {"alpha": [0.1, 1.0], "l1_ratio": [0.2, 0.5, 0.8]}
            cv: Number of cross-validation folds.
            scoring: Scoring metric ("r_squared", "neg_rmse", "neg_mae", "neg_mape").
            use_time_series_cv: Whether to use time series split (recommended for MMM).
            constraints: Coefficient constraints to apply to all models.
            progress_callback: Optional callback for progress updates.
        """
        if model_type not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model type must be one of {self.SUPPORTED_MODELS}")

        if scoring not in self.SCORING_FUNCTIONS:
            raise ValueError(f"Scoring must be one of {list(self.SCORING_FUNCTIONS.keys())}")

        self.model_type = model_type
        self.param_grid = param_grid or self._get_default_param_grid()
        self.cv = cv
        self.scoring = scoring
        self.use_time_series_cv = use_time_series_cv
        self.constraints = constraints
        self.progress_callback = progress_callback

        self._best_model: BaseModel | None = None

    def _get_default_param_grid(self) -> dict[str, list[Any]]:
        """Get default parameter grid for the model type."""
        if self.model_type == "ridge":
            return {
                "alpha": [0.001, 0.01, 0.1, 1.0, 10.0, 100.0],
            }
        elif self.model_type == "elasticnet":
            return {
                "alpha": [0.001, 0.01, 0.1, 1.0, 10.0],
                "l1_ratio": [0.1, 0.3, 0.5, 0.7, 0.9],
            }
        return {}

    def _update_progress(self, pct: int, message: str) -> None:
        """Update progress if callback is set."""
        if self.progress_callback:
            self.progress_callback(pct, message)

    def _create_model(self, params: dict[str, Any]) -> BaseModel:
        """Create a model instance with given parameters."""
        if self.model_type == "ridge":
            return RidgeModel(
                alpha=params.get("alpha", 1.0),
                constraints=self.constraints,
                bootstrap_n=20,  # Reduced for speed during CV
            )
        elif self.model_type == "elasticnet":
            return ElasticNetModel(
                alpha=params.get("alpha", 1.0),
                l1_ratio=params.get("l1_ratio", 0.5),
                constraints=self.constraints,
                bootstrap_n=20,  # Reduced for speed during CV
            )
        raise ValueError(f"Unknown model type: {self.model_type}")

    def _get_cv_splitter(self, n_samples: int):
        """Get cross-validation splitter."""
        if self.use_time_series_cv:
            return TimeSeriesSplit(n_splits=self.cv)
        else:
            return KFold(n_splits=self.cv, shuffle=True, random_state=42)

    def _generate_param_combinations(self) -> list[dict[str, Any]]:
        """Generate all combinations of parameters from the grid."""
        from itertools import product

        keys = list(self.param_grid.keys())
        values = list(self.param_grid.values())

        combinations = []
        for combo in product(*values):
            combinations.append(dict(zip(keys, combo)))

        return combinations

    def _score(
        self,
        y_true: NDArray[np.float64],
        y_pred: NDArray[np.float64],
    ) -> float:
        """Calculate score using the configured scoring function."""
        score_fn = self.SCORING_FUNCTIONS[self.scoring]
        return float(score_fn(y_true, y_pred))

    def _cross_validate(
        self,
        model: BaseModel,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        feature_names: list[str],
    ) -> tuple[list[float], list[float]]:
        """
        Perform cross-validation for a single model.

        Returns:
            Tuple of (test_scores, train_scores).
        """
        cv_splitter = self._get_cv_splitter(len(y))
        test_scores = []
        train_scores = []

        for train_idx, test_idx in cv_splitter.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]

            # Clone model parameters for fresh fit
            model_clone = self._create_model(
                {k: getattr(model, k) for k in self.param_grid.keys() if hasattr(model, k)}
            )

            # Fit and score
            try:
                model_clone.fit(X_train, y_train, feature_names=feature_names)

                y_pred_test = model_clone.predict(X_test)
                y_pred_train = model_clone.predict(X_train)

                test_scores.append(self._score(y_test, y_pred_test))
                train_scores.append(self._score(y_train, y_pred_train))
            except Exception:
                # If fitting fails, append NaN
                test_scores.append(np.nan)
                train_scores.append(np.nan)

        return test_scores, train_scores

    def fit(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        feature_names: list[str] | None = None,
    ) -> TuningResult:
        """
        Perform hyperparameter tuning with cross-validation.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Target vector of shape (n_samples,).
            feature_names: Optional names for features.

        Returns:
            TuningResult with best parameters and all CV results.
        """
        X = np.asarray(X, dtype=np.float64)
        y = np.asarray(y, dtype=np.float64)

        if feature_names is None:
            feature_names = [f"x{i}" for i in range(X.shape[1])]

        param_combinations = self._generate_param_combinations()
        n_combinations = len(param_combinations)

        self._update_progress(0, f"Starting hyperparameter search with {n_combinations} combinations...")

        cv_results = []
        best_score = -np.inf
        best_params = param_combinations[0]

        for i, params in enumerate(param_combinations):
            self._update_progress(
                int(100 * i / n_combinations),
                f"Evaluating params: {params}",
            )

            model = self._create_model(params)
            test_scores, train_scores = self._cross_validate(model, X, y, feature_names)

            # Filter out NaN scores
            valid_scores = [s for s in test_scores if not np.isnan(s)]

            if valid_scores:
                mean_score = np.mean(valid_scores)
                std_score = np.std(valid_scores)
                mean_train = np.mean([s for s in train_scores if not np.isnan(s)])
            else:
                mean_score = -np.inf
                std_score = 0.0
                mean_train = None

            cv_result = CVResult(
                params=params,
                mean_score=float(mean_score),
                std_score=float(std_score),
                scores=test_scores,
                mean_train_score=float(mean_train) if mean_train is not None else None,
            )
            cv_results.append(cv_result)

            if mean_score > best_score:
                best_score = mean_score
                best_params = params

        self._update_progress(95, "Training final model with best parameters...")

        # Train final model with best parameters on all data
        best_model = self._create_model(best_params)
        # Use more bootstrap samples for final model
        if hasattr(best_model, "bootstrap_n"):
            best_model.bootstrap_n = 100
        best_model.fit(X, y, feature_names=feature_names)
        self._best_model = best_model

        self._update_progress(100, "Hyperparameter tuning complete!")

        return TuningResult(
            best_params=best_params,
            best_score=float(best_score),
            cv_results=cv_results,
            best_model=best_model,
        )

    def get_best_model(self) -> BaseModel:
        """Get the best model after tuning."""
        if self._best_model is None:
            raise RuntimeError("Must call fit() before getting best model")
        return self._best_model


def tune_ridge_alpha(
    X: NDArray[np.float64],
    y: NDArray[np.float64],
    feature_names: list[str] | None = None,
    alphas: list[float] | None = None,
    cv: int = 5,
    constraints: dict[str, dict[str, Any]] | None = None,
) -> TuningResult:
    """
    Convenience function to tune Ridge alpha parameter.

    Args:
        X: Feature matrix.
        y: Target vector.
        feature_names: Optional feature names.
        alphas: List of alpha values to try.
        cv: Number of CV folds.
        constraints: Coefficient constraints.

    Returns:
        TuningResult with best alpha and CV scores.
    """
    if alphas is None:
        alphas = [0.001, 0.01, 0.1, 1.0, 10.0, 100.0, 1000.0]

    tuner = HyperparameterTuner(
        model_type="ridge",
        param_grid={"alpha": alphas},
        cv=cv,
        constraints=constraints,
    )

    return tuner.fit(X, y, feature_names)


def tune_elasticnet(
    X: NDArray[np.float64],
    y: NDArray[np.float64],
    feature_names: list[str] | None = None,
    alphas: list[float] | None = None,
    l1_ratios: list[float] | None = None,
    cv: int = 5,
    constraints: dict[str, dict[str, Any]] | None = None,
) -> TuningResult:
    """
    Convenience function to tune ElasticNet parameters.

    Args:
        X: Feature matrix.
        y: Target vector.
        feature_names: Optional feature names.
        alphas: List of alpha values to try.
        l1_ratios: List of l1_ratio values to try.
        cv: Number of CV folds.
        constraints: Coefficient constraints.

    Returns:
        TuningResult with best parameters and CV scores.
    """
    if alphas is None:
        alphas = [0.001, 0.01, 0.1, 1.0, 10.0]
    if l1_ratios is None:
        l1_ratios = [0.1, 0.3, 0.5, 0.7, 0.9]

    tuner = HyperparameterTuner(
        model_type="elasticnet",
        param_grid={"alpha": alphas, "l1_ratio": l1_ratios},
        cv=cv,
        constraints=constraints,
    )

    return tuner.fit(X, y, feature_names)
