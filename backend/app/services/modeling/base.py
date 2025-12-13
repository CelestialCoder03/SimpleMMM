"""Base model interface for Marketing Mix Models."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from numpy.typing import NDArray


@dataclass
class ModelResult:
    """
    Container for model training results.

    Stores all outputs from model fitting including coefficients,
    fit metrics, and diagnostic information.
    """

    # Model identification
    model_type: str

    # Coefficients
    coefficients: dict[str, float] = field(default_factory=dict)
    intercept: float = 0.0

    # Standard errors and confidence intervals
    std_errors: dict[str, float] = field(default_factory=dict)
    ci_lower: dict[str, float] = field(default_factory=dict)
    ci_upper: dict[str, float] = field(default_factory=dict)
    p_values: dict[str, float] = field(default_factory=dict)

    # Fit metrics
    r_squared: float = 0.0
    adjusted_r_squared: float = 0.0
    rmse: float = 0.0
    mape: float = 0.0
    mae: float = 0.0
    aic: float | None = None
    bic: float | None = None

    # Predictions
    fitted_values: NDArray[np.float64] | None = None
    residuals: NDArray[np.float64] | None = None

    # Diagnostics
    vif: dict[str, float] = field(default_factory=dict)
    durbin_watson: float | None = None
    jarque_bera_pvalue: float | None = None

    # Bayesian specific
    r_hat: dict[str, float] = field(default_factory=dict)
    ess: dict[str, float] = field(default_factory=dict)
    posterior_samples: dict[str, NDArray[np.float64]] | None = None

    # Bayesian model comparison metrics
    loo: float | None = None
    loo_se: float | None = None
    waic: float | None = None
    waic_se: float | None = None

    # Feature transformations used
    transformations: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Training metadata
    n_observations: int = 0
    n_features: int = 0
    training_time_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert result to dictionary for serialization."""
        result = {
            "model_type": self.model_type,
            "coefficients": self.coefficients,
            "intercept": self.intercept,
            "std_errors": self.std_errors,
            "ci_lower": self.ci_lower,
            "ci_upper": self.ci_upper,
            "p_values": self.p_values,
            "r_squared": self.r_squared,
            "adjusted_r_squared": self.adjusted_r_squared,
            "rmse": self.rmse,
            "mape": self.mape,
            "mae": self.mae,
            "aic": self.aic,
            "bic": self.bic,
            "vif": self.vif,
            "durbin_watson": self.durbin_watson,
            "jarque_bera_pvalue": self.jarque_bera_pvalue,
            "n_observations": self.n_observations,
            "n_features": self.n_features,
            "training_time_seconds": self.training_time_seconds,
            "transformations": self.transformations,
        }

        # Add Bayesian diagnostics if present
        if self.r_hat:
            result["r_hat"] = self.r_hat
        if self.ess:
            result["ess"] = self.ess

        # Add Bayesian model comparison metrics if present
        if self.loo is not None:
            result["loo"] = self.loo
            result["loo_se"] = self.loo_se
        if self.waic is not None:
            result["waic"] = self.waic
            result["waic_se"] = self.waic_se

        # Convert numpy arrays to lists for JSON serialization
        if self.fitted_values is not None:
            result["fitted_values"] = self.fitted_values.tolist()
        if self.residuals is not None:
            result["residuals"] = self.residuals.tolist()

        return result


class BaseModel(ABC):
    """
    Abstract base class for Marketing Mix Models.

    Defines the interface that all model implementations must follow.
    Each model type (OLS, Ridge, Bayesian) inherits from this class
    and implements the abstract methods.

    The modeling process follows these steps:
    1. Prepare data (apply transformations, handle constraints)
    2. Fit the model
    3. Calculate fit metrics
    4. Generate predictions
    5. Run diagnostics
    """

    def __init__(self, **kwargs):
        """
        Initialize base model.

        Args:
            **kwargs: Model-specific configuration parameters.
        """
        self.model_type: str = "base"
        self.is_fitted: bool = False
        self.feature_names: list[str] = []
        self.coefficients_: dict[str, float] = {}
        self.intercept_: float = 0.0
        self._kwargs = kwargs

    @abstractmethod
    def fit(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        feature_names: list[str] | None = None,
    ) -> "BaseModel":
        """
        Fit the model to training data.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Target vector of shape (n_samples,).
            feature_names: Optional names for features.

        Returns:
            Self (fitted model instance).
        """
        pass

    @abstractmethod
    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Generate predictions for new data.

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            Predicted values of shape (n_samples,).
        """
        pass

    @abstractmethod
    def get_coefficients(self) -> dict[str, float]:
        """
        Get fitted coefficients.

        Returns:
            Dictionary mapping feature names to coefficient values.
        """
        pass

    @abstractmethod
    def get_standard_errors(self) -> dict[str, float]:
        """
        Get standard errors of coefficients.

        Returns:
            Dictionary mapping feature names to standard errors.
        """
        pass

    def get_intercept(self) -> float:
        """Get the fitted intercept term."""
        return self.intercept_

    def get_result(self) -> ModelResult:
        """
        Get complete model result.

        Returns:
            ModelResult instance with all fitting information.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before getting results")
        return self._result

    def _validate_input(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64] | None = None,
    ) -> tuple[NDArray[np.float64], NDArray[np.float64] | None]:
        """
        Validate and prepare input data.

        Args:
            X: Feature matrix.
            y: Optional target vector.

        Returns:
            Validated (X, y) tuple.

        Raises:
            ValueError: If input shapes are incompatible.
        """
        X = np.asarray(X, dtype=np.float64)

        if X.ndim == 1:
            X = X.reshape(-1, 1)

        if y is not None:
            y = np.asarray(y, dtype=np.float64)
            if len(X) != len(y):
                raise ValueError(f"X and y must have same length. Got X={len(X)}, y={len(y)}")

        # Check for NaN/Inf
        if np.any(~np.isfinite(X)):
            raise ValueError("X contains NaN or infinite values")
        if y is not None and np.any(~np.isfinite(y)):
            raise ValueError("y contains NaN or infinite values")

        return X, y

    def _calculate_metrics(
        self,
        y_true: NDArray[np.float64],
        y_pred: NDArray[np.float64],
        n_features: int,
    ) -> dict[str, float]:
        """
        Calculate fit metrics.

        Args:
            y_true: Actual values.
            y_pred: Predicted values.
            n_features: Number of features in model.

        Returns:
            Dictionary of metrics.
        """
        n = len(y_true)
        residuals = y_true - y_pred

        # Sum of squares
        ss_res = np.sum(residuals**2)
        ss_tot = np.sum((y_true - np.mean(y_true)) ** 2)

        # R-squared
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        # Adjusted R-squared
        if n > n_features + 1:
            adj_r_squared = 1 - (1 - r_squared) * (n - 1) / (n - n_features - 1)
        else:
            adj_r_squared = r_squared

        # RMSE
        rmse = np.sqrt(np.mean(residuals**2))

        # MAE
        mae = np.mean(np.abs(residuals))

        # MAPE (avoid division by zero)
        mask = y_true != 0
        if np.sum(mask) > 0:
            mape = np.mean(np.abs(residuals[mask] / y_true[mask])) * 100
        else:
            mape = 0.0

        # AIC and BIC (assuming Gaussian errors)
        k = n_features + 2  # Including intercept and variance parameter
        log_likelihood = -n / 2 * (1 + np.log(2 * np.pi) + np.log(ss_res / n))
        aic = 2 * k - 2 * log_likelihood
        bic = k * np.log(n) - 2 * log_likelihood

        return {
            "r_squared": float(r_squared),
            "adjusted_r_squared": float(adj_r_squared),
            "rmse": float(rmse),
            "mae": float(mae),
            "mape": float(mape),
            "aic": float(aic),
            "bic": float(bic),
        }

    def _calculate_vif(self, X: NDArray[np.float64]) -> dict[str, float]:
        """
        Calculate Variance Inflation Factor for each feature.

        VIF measures multicollinearity between features.
        VIF > 5 suggests moderate correlation.
        VIF > 10 suggests high correlation that may affect results.

        Args:
            X: Feature matrix.

        Returns:
            Dictionary mapping feature names to VIF values.
        """
        from sklearn.linear_model import LinearRegression

        vif = {}
        n_features = X.shape[1]

        for i in range(n_features):
            # Get other features as predictors
            X_other = np.delete(X, i, axis=1)
            X_i = X[:, i]

            if X_other.shape[1] == 0:
                vif[self.feature_names[i]] = 1.0
                continue

            # Fit regression of feature i on other features
            reg = LinearRegression()
            reg.fit(X_other, X_i)
            r_squared = reg.score(X_other, X_i)

            # VIF = 1 / (1 - R^2)
            if r_squared < 1:
                vif[self.feature_names[i]] = 1 / (1 - r_squared)
            else:
                vif[self.feature_names[i]] = float("inf")

        return vif

    def _calculate_durbin_watson(self, residuals: NDArray[np.float64]) -> float:
        """
        Calculate Durbin-Watson statistic for autocorrelation.

        DW ≈ 2: No autocorrelation
        DW < 2: Positive autocorrelation
        DW > 2: Negative autocorrelation

        Args:
            residuals: Model residuals.

        Returns:
            Durbin-Watson statistic.
        """
        diff = np.diff(residuals)
        dw = np.sum(diff**2) / np.sum(residuals**2)
        return float(dw)

    def _calculate_jarque_bera(self, residuals: NDArray[np.float64]) -> float:
        """
        Calculate Jarque-Bera test p-value for normality of residuals.

        Tests the null hypothesis that residuals are normally distributed.
        p < 0.05 suggests non-normal residuals.

        Args:
            residuals: Model residuals.

        Returns:
            p-value from Jarque-Bera test.
        """
        from scipy import stats

        _, p_value = stats.jarque_bera(residuals)
        return float(p_value)
