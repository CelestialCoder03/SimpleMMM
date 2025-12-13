"""Marketing Mix Model transformations: Adstock and Saturation."""

from abc import ABC, abstractmethod
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy.optimize import minimize_scalar


class BaseTransform(ABC):
    """Base class for feature transformations."""

    @abstractmethod
    def transform(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """Apply transformation to input array."""
        pass

    @abstractmethod
    def get_params(self) -> dict[str, Any]:
        """Get transformation parameters."""
        pass


class AdstockTransform(BaseTransform):
    """
    Adstock transformation to model carryover effects.

    Adstock captures the lingering effect of advertising spend over time.
    The geometric adstock assumes exponential decay of advertising effect.

    Mathematical formulation (Geometric):
        A[t] = X[t] + decay * A[t-1]

    Where:
        - X[t] is the original spend at time t
        - A[t] is the adstocked spend at time t
        - decay is the carryover rate (0 < decay < 1)

    Weibull adstock provides more flexible decay patterns:
        weight[k] = 1 - CDF(k; shape, scale)
        A[t] = sum(weight[k] * X[t-k] for k in range(max_lag))
    """

    def __init__(
        self,
        decay: float = 0.5,
        max_lag: int = 8,
        adstock_type: str = "geometric",
        shape: float = 1.0,  # For Weibull
        scale: float = 1.0,  # For Weibull
    ):
        """
        Initialize adstock transformation.

        Args:
            decay: Decay rate for geometric adstock (0 < decay < 1).
                   Higher values mean longer carryover.
            max_lag: Maximum number of periods for carryover effect.
            adstock_type: Type of adstock ('geometric' or 'weibull').
            shape: Shape parameter for Weibull distribution.
            scale: Scale parameter for Weibull distribution.
        """
        if not 0 <= decay <= 1:
            raise ValueError("decay must be between 0 and 1")
        if max_lag < 1:
            raise ValueError("max_lag must be at least 1")

        self.decay = decay
        self.max_lag = max_lag
        self.adstock_type = adstock_type
        self.shape = shape
        self.scale = scale

        # Precompute weights for vectorized operations
        self._weights = self._compute_weights()

    def _compute_weights(self) -> NDArray[np.float64]:
        """Compute decay weights based on adstock type."""
        if self.adstock_type == "geometric":
            # Geometric decay: weight[k] = decay^k
            return np.array([self.decay**k for k in range(self.max_lag)])
        elif self.adstock_type == "weibull":
            # Weibull survival function: 1 - CDF
            from scipy.stats import weibull_min

            k = np.arange(self.max_lag)
            weights = weibull_min.sf(k, self.shape, scale=self.scale)
            return weights / weights.sum()  # Normalize
        else:
            raise ValueError(f"Unknown adstock type: {self.adstock_type}")

    def transform(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Apply adstock transformation.

        Args:
            x: Input array of spend/impressions over time.

        Returns:
            Adstocked array with carryover effects.
        """
        x = np.asarray(x, dtype=np.float64)
        n = len(x)
        result = np.zeros(n)

        if self.adstock_type == "geometric":
            # Efficient recursive implementation
            result[0] = x[0]
            for t in range(1, n):
                result[t] = x[t] + self.decay * result[t - 1]
        else:
            # Convolution-based implementation for Weibull
            for t in range(n):
                for k in range(min(t + 1, self.max_lag)):
                    result[t] += self._weights[k] * x[t - k]

        return result

    def get_params(self) -> dict[str, Any]:
        """Get transformation parameters."""
        return {
            "type": self.adstock_type,
            "adstock_type": self.adstock_type,
            "decay": self.decay,
            "max_lag": self.max_lag,
            "shape": self.shape,
            "scale": self.scale,
        }

    @staticmethod
    def fit_decay(
        x: NDArray[np.float64],
        y: NDArray[np.float64],
        max_lag: int = 8,
    ) -> float:
        """
        Fit optimal decay rate by maximizing correlation with target.

        Args:
            x: Input spend array.
            y: Target variable (e.g., sales).
            max_lag: Maximum lag for adstock.

        Returns:
            Optimal decay rate.
        """

        def neg_correlation(decay: float) -> float:
            transform = AdstockTransform(decay=decay, max_lag=max_lag)
            x_transformed = transform.transform(x)
            corr = np.corrcoef(x_transformed, y)[0, 1]
            return -abs(corr) if not np.isnan(corr) else 0

        result = minimize_scalar(
            neg_correlation,
            bounds=(0.01, 0.99),
            method="bounded",
        )
        return result.x


class SaturationTransform(BaseTransform):
    """
    Saturation transformation to model diminishing returns.

    Captures the economic principle that incremental advertising spending
    yields decreasing marginal returns as spend increases.

    Hill function (recommended):
        S(x) = x^s / (k^s + x^s)

    Where:
        - k is the half-saturation point (spend at 50% response)
        - s is the shape/slope parameter (steepness)

    Logistic function:
        S(x) = L / (1 + exp(-k * (x - x0)))

    Properties:
        - Output is bounded [0, 1] (or [0, L] for logistic)
        - Monotonically increasing
        - Concave (diminishing returns)
    """

    def __init__(
        self,
        k: float = 1.0,
        s: float = 1.0,
        saturation_type: str = "hill",
        l: float = 1.0,  # Max value for logistic
        x0: float = 0.0,  # Inflection point for logistic
    ):
        """
        Initialize saturation transformation.

        Args:
            k: Half-saturation point (Hill) or steepness (Logistic).
            s: Shape parameter for Hill function.
            saturation_type: Type of saturation ('hill' or 'logistic').
            l: Maximum value for logistic function.
            x0: Inflection point for logistic function.
        """
        if k <= 0:
            raise ValueError("k must be positive")
        if s <= 0:
            raise ValueError("s must be positive")

        self.k = k
        self.s = s
        self.saturation_type = saturation_type
        self.l = l
        self.x0 = x0

    def transform(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Apply saturation transformation.

        Args:
            x: Input array (typically adstocked spend).

        Returns:
            Saturated array with diminishing returns applied.
        """
        x = np.asarray(x, dtype=np.float64)
        # Ensure non-negative
        x = np.maximum(x, 0)

        if self.saturation_type == "hill":
            # Hill function: x^s / (k^s + x^s)
            x_s = np.power(x, self.s)
            k_s = np.power(self.k, self.s)
            return x_s / (k_s + x_s + 1e-10)  # Add small epsilon to avoid div by 0
        elif self.saturation_type == "logistic":
            # Logistic function: L / (1 + exp(-k * (x - x0)))
            return self.l / (1 + np.exp(-self.k * (x - self.x0)))
        else:
            raise ValueError(f"Unknown saturation type: {self.saturation_type}")

    def get_params(self) -> dict[str, Any]:
        """Get transformation parameters."""
        return {
            "type": self.saturation_type,
            "saturation_type": self.saturation_type,
            "k": self.k,
            "s": self.s,
            "l": self.l,
            "x0": self.x0,
        }

    def marginal_response(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Calculate marginal response (derivative) at each point.

        This represents the incremental response from additional spend.

        Args:
            x: Input array.

        Returns:
            Array of marginal responses (derivatives).
        """
        x = np.asarray(x, dtype=np.float64)
        x = np.maximum(x, 1e-10)

        if self.saturation_type == "hill":
            # Derivative of Hill: s * k^s * x^(s-1) / (k^s + x^s)^2
            x_s = np.power(x, self.s)
            k_s = np.power(self.k, self.s)
            numerator = self.s * k_s * np.power(x, self.s - 1)
            denominator = np.power(k_s + x_s, 2) + 1e-10
            return numerator / denominator
        elif self.saturation_type == "logistic":
            # Derivative of logistic
            exp_term = np.exp(-self.k * (x - self.x0))
            return self.l * self.k * exp_term / np.power(1 + exp_term, 2)
        else:
            raise ValueError(f"Unknown saturation type: {self.saturation_type}")

    @staticmethod
    def fit_hill_params(
        x: NDArray[np.float64],
        y: NDArray[np.float64],
        s_bounds: tuple[float, float] = (0.5, 3.0),
    ) -> tuple[float, float]:
        """
        Fit Hill function parameters by maximizing correlation.

        Args:
            x: Input spend array.
            y: Target variable.
            s_bounds: Bounds for shape parameter s.

        Returns:
            Tuple of (k, s) optimal parameters.
        """
        from scipy.optimize import minimize

        # Use median as initial guess for k
        k_init = np.median(x[x > 0]) if np.any(x > 0) else 1.0
        s_init = 1.0

        def neg_correlation(params: NDArray[np.float64]) -> float:
            k, s = params
            if k <= 0 or s <= 0:
                return 1e10
            transform = SaturationTransform(k=k, s=s)
            x_transformed = transform.transform(x)
            corr = np.corrcoef(x_transformed, y)[0, 1]
            return -abs(corr) if not np.isnan(corr) else 0

        result = minimize(
            neg_correlation,
            x0=[k_init, s_init],
            method="L-BFGS-B",
            bounds=[(1e-6, np.max(x) * 2), s_bounds],
        )
        return result.x[0], result.x[1]


class FeatureTransformer:
    """
    Combined transformer that applies adstock and saturation sequentially.

    The standard MMM transformation pipeline is:
    1. Apply adstock (carryover effects)
    2. Apply saturation (diminishing returns)

    Mathematical formulation:
        transformed = Saturation(Adstock(x))
    """

    def __init__(
        self,
        adstock: AdstockTransform | None = None,
        saturation: SaturationTransform | None = None,
    ):
        """
        Initialize feature transformer.

        Args:
            adstock: Optional adstock transformation.
            saturation: Optional saturation transformation.
        """
        self.adstock = adstock
        self.saturation = saturation

    def transform(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Apply transformations in sequence.

        Args:
            x: Input array.

        Returns:
            Transformed array.
        """
        result = np.asarray(x, dtype=np.float64)

        if self.adstock is not None:
            result = self.adstock.transform(result)

        if self.saturation is not None:
            result = self.saturation.transform(result)

        return result

    def get_params(self) -> dict[str, Any]:
        """Get all transformation parameters."""
        params = {}
        if self.adstock is not None:
            params["adstock"] = self.adstock.get_params()
        if self.saturation is not None:
            params["saturation"] = self.saturation.get_params()
        return params

    @classmethod
    def from_config(
        cls,
        adstock_config: dict[str, Any] | None = None,
        saturation_config: dict[str, Any] | None = None,
    ) -> "FeatureTransformer":
        """
        Create transformer from configuration dictionaries.

        Args:
            adstock_config: Adstock configuration with keys:
                - type: 'geometric' or 'weibull'
                - decay: float or 'auto'
                - max_lag: int
            saturation_config: Saturation configuration with keys:
                - type: 'hill' or 'logistic'
                - k: float or 'auto'
                - s: float or 'auto'

        Returns:
            Configured FeatureTransformer instance.
        """
        adstock = None
        saturation = None

        if adstock_config is not None:
            decay = adstock_config.get("decay", 0.5)
            if decay == "auto":
                decay = 0.5  # Will be fit later
            adstock = AdstockTransform(
                decay=decay,
                max_lag=adstock_config.get("max_lag", 8),
                adstock_type=adstock_config.get("type", "geometric"),
            )

        if saturation_config is not None:
            k = saturation_config.get("k", 1.0)
            s = saturation_config.get("s", 1.0)
            if k == "auto":
                k = 1.0  # Will be fit later
            if s == "auto":
                s = 1.0  # Will be fit later
            saturation = SaturationTransform(
                k=k,
                s=s,
                saturation_type=saturation_config.get("type", "hill"),
            )

        return cls(adstock=adstock, saturation=saturation)
