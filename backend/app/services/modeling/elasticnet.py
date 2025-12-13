"""Elastic Net regression model with constraint support for Marketing Mix Modeling."""

import time
from typing import Any

import numpy as np
from numpy.typing import NDArray
from scipy import stats
from scipy.optimize import minimize
from sklearn.linear_model import ElasticNet
from sklearn.preprocessing import StandardScaler

from app.services.modeling.base import BaseModel, ModelResult


class ElasticNetModel(BaseModel):
    """
    Elastic Net regression model with optional coefficient constraints.

    Elastic Net combines L1 (Lasso) and L2 (Ridge) regularization:
        min_β ||y - Xβ||² + α * (ρ||β||₁ + (1-ρ)/2||β||²)

    Where:
        - α (alpha) controls overall regularization strength
        - ρ (l1_ratio) controls the mix: ρ=1 is Lasso, ρ=0 is Ridge

    This combines the benefits of both regularization methods:
        - L1 (Lasso) promotes sparsity (feature selection)
        - L2 (Ridge) handles correlated features better

    Particularly useful for MMM when:
        - You want automatic feature selection
        - Features are moderately correlated
        - You need a balance between Ridge stability and Lasso sparsity

    Advantages:
        - Automatic variable selection (unlike Ridge)
        - Handles correlated features better than pure Lasso
        - Can enforce coefficient constraints (sign, bounds)
        - Good for high-dimensional problems

    Limitations:
        - Two hyperparameters to tune (alpha and l1_ratio)
        - Standard errors require bootstrap
        - May set some coefficients to exactly zero

    Usage:
        model = ElasticNetModel(alpha=1.0, l1_ratio=0.5)
        model.fit(X, y, feature_names=['tv', 'radio', 'print'])

        # With constraints
        constraints = {'tv': {'sign': 'positive'}, 'radio': {'min': 0, 'max': 1}}
        model = ElasticNetModel(alpha=1.0, l1_ratio=0.5, constraints=constraints)
        model.fit(X, y, feature_names=['tv', 'radio', 'print'])
    """

    def __init__(
        self,
        alpha: float = 1.0,
        l1_ratio: float = 0.5,
        fit_intercept: bool = True,
        constraints: dict[str, dict[str, Any]] | None = None,
        linear_constraints: list[dict[str, Any]] | None = None,
        scale_features: bool = True,
        bootstrap_n: int = 100,
        max_iter: int = 1000,
        tol: float = 1e-4,
        **kwargs,
    ):
        """
        Initialize Elastic Net model.

        Args:
            alpha: Regularization strength (higher = more regularization).
            l1_ratio: Mix between L1 and L2 regularization (0-1).
                - l1_ratio=1: Pure Lasso (L1 only)
                - l1_ratio=0: Pure Ridge (L2 only)
                - l1_ratio=0.5: Equal mix (default)
            fit_intercept: Whether to fit an intercept term.
            constraints: Dictionary of constraints per variable:
                {
                    'feature_name': {
                        'sign': 'positive' or 'negative',
                        'min': float,
                        'max': float
                    }
                }
            linear_constraints: List of scipy-format linear constraints for relationships:
                [{'type': 'ineq', 'fun': callable}, ...]
            scale_features: Whether to standardize features before fitting.
            bootstrap_n: Number of bootstrap samples for standard errors.
            max_iter: Maximum iterations for optimization.
            tol: Tolerance for optimization convergence.
            **kwargs: Additional configuration.
        """
        super().__init__(**kwargs)
        self.model_type = "elasticnet"
        self.alpha = alpha
        self.l1_ratio = l1_ratio
        self.fit_intercept = fit_intercept
        self.constraints = constraints or {}
        self.linear_constraints = linear_constraints or []
        self.scale_features = scale_features
        self.bootstrap_n = bootstrap_n
        self.max_iter = max_iter
        self.tol = tol

        self._scaler: StandardScaler | None = None
        self._elasticnet_model: ElasticNet | None = None
        self._result: ModelResult | None = None
        self._X_scaled: NDArray[np.float64] | None = None
        self._y: NDArray[np.float64] | None = None

    def _get_bounds(self, feature_names: list[str]) -> list[tuple[float, float]]:
        """
        Convert constraints to scipy bounds format.

        Args:
            feature_names: List of feature names.

        Returns:
            List of (lower, upper) tuples for each feature.
        """
        bounds = []
        for name in feature_names:
            constraint = self.constraints.get(name, {})

            # Default bounds
            lower = -np.inf
            upper = np.inf

            # Apply sign constraint
            sign = constraint.get("sign")
            if sign == "positive":
                lower = max(lower, 0)
            elif sign == "negative":
                upper = min(upper, 0)

            # Apply explicit bounds
            if "min" in constraint:
                lower = max(lower, constraint["min"])
            if "max" in constraint:
                upper = min(upper, constraint["max"])

            bounds.append((lower, upper))

        return bounds

    def _has_active_constraints(self) -> bool:
        """Check if any constraints are active."""
        # Check linear (relationship) constraints
        if self.linear_constraints:
            return True

        if not self.constraints:
            return False

        for name in self.feature_names:
            constraint = self.constraints.get(name, {})
            if constraint.get("sign") or "min" in constraint or "max" in constraint:
                return True
        return False

    def _fit_unconstrained(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], float]:
        """
        Fit standard Elastic Net regression without constraints.

        Args:
            X: Feature matrix.
            y: Target vector.

        Returns:
            Tuple of (coefficients, intercept).
        """
        self._elasticnet_model = ElasticNet(
            alpha=self.alpha,
            l1_ratio=self.l1_ratio,
            fit_intercept=self.fit_intercept,
            max_iter=self.max_iter,
            tol=self.tol,
        )
        self._elasticnet_model.fit(X, y)
        return self._elasticnet_model.coef_, self._elasticnet_model.intercept_

    def _fit_constrained(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], float]:
        """
        Fit Elastic Net regression with coefficient constraints using optimization.

        Uses scipy.optimize.minimize with L-BFGS-B for constrained optimization.

        Args:
            X: Feature matrix.
            y: Target vector.

        Returns:
            Tuple of (coefficients, intercept).
        """
        n_samples, n_features = X.shape
        bounds = self._get_bounds(self.feature_names)

        # Add intercept bound if fitting intercept
        if self.fit_intercept:
            bounds = [(-np.inf, np.inf)] + bounds  # Unconstrained intercept
            n_features + 1
        else:
            pass

        def objective(params: NDArray[np.float64]) -> float:
            """Elastic Net objective with L1 and L2 penalties."""
            if self.fit_intercept:
                intercept = params[0]
                coef = params[1:]
            else:
                intercept = 0.0
                coef = params

            # Predictions
            y_pred = X @ coef + intercept

            # Elastic Net objective: RSS + alpha * (l1_ratio * ||coef||₁ + (1-l1_ratio)/2 * ||coef||²)
            rss = np.sum((y - y_pred) ** 2) / (2 * n_samples)
            l1_penalty = self.l1_ratio * np.sum(np.abs(coef))
            l2_penalty = (1 - self.l1_ratio) / 2 * np.sum(coef**2)
            penalty = self.alpha * (l1_penalty + l2_penalty)

            return rss + penalty

        def gradient(params: NDArray[np.float64]) -> NDArray[np.float64]:
            """Gradient of the Elastic Net objective (using subgradient for L1)."""
            if self.fit_intercept:
                intercept = params[0]
                coef = params[1:]
            else:
                intercept = 0.0
                coef = params

            # Residuals
            residuals = y - (X @ coef + intercept)

            # Gradient of RSS
            grad_coef = -X.T @ residuals / n_samples

            # Gradient of L2 penalty
            grad_coef += self.alpha * (1 - self.l1_ratio) * coef

            # Subgradient of L1 penalty
            grad_coef += self.alpha * self.l1_ratio * np.sign(coef)

            if self.fit_intercept:
                grad_intercept = -np.sum(residuals) / n_samples
                return np.concatenate([[grad_intercept], grad_coef])
            else:
                return grad_coef

        # Initial guess from unconstrained Elastic Net
        unconstrained_coef, unconstrained_intercept = self._fit_unconstrained(X, y)

        if self.fit_intercept:
            x0 = np.concatenate([[unconstrained_intercept], unconstrained_coef])
        else:
            x0 = unconstrained_coef.copy()

        # Project initial guess to feasible region
        for i, (lower, upper) in enumerate(bounds):
            x0[i] = np.clip(x0[i], lower, upper)

        # Build scipy constraints for relationship constraints
        # Need to adjust for intercept offset in params vector
        scipy_constraints = []
        if self.linear_constraints:
            for lc in self.linear_constraints:
                if self.fit_intercept:
                    # Original constraint is over coefficients only
                    # But params = [intercept, coef1, coef2, ...]
                    # So we need to skip intercept: apply fun to params[1:]
                    scipy_constraints.append(
                        {
                            "type": lc["type"],
                            "fun": lambda x, f=lc["fun"]: f(x[1:]),
                        }
                    )
                else:
                    scipy_constraints.append(lc)

        # Choose optimizer: SLSQP for linear constraints, L-BFGS-B for bounds only
        if scipy_constraints:
            result = minimize(
                objective,
                x0,
                method="SLSQP",
                jac=gradient,
                bounds=bounds,
                constraints=scipy_constraints,
                options={"maxiter": self.max_iter, "ftol": self.tol},
            )
        else:
            result = minimize(
                objective,
                x0,
                method="L-BFGS-B",
                jac=gradient,
                bounds=bounds,
                options={"maxiter": self.max_iter, "ftol": self.tol},
            )

        if self.fit_intercept:
            return result.x[1:], result.x[0]
        else:
            return result.x, 0.0

    def _bootstrap_standard_errors(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        n_bootstrap: int = 100,
    ) -> dict[str, float]:
        """
        Estimate standard errors using bootstrap.

        Args:
            X: Feature matrix.
            y: Target vector.
            n_bootstrap: Number of bootstrap samples.

        Returns:
            Dictionary mapping feature names to standard errors.
        """
        n_samples = len(y)
        n_features = X.shape[1]
        coef_samples = np.zeros((n_bootstrap, n_features))

        for i in range(n_bootstrap):
            # Bootstrap sample
            indices = np.random.choice(n_samples, size=n_samples, replace=True)
            X_boot = X[indices]
            y_boot = y[indices]

            # Fit on bootstrap sample
            if self._has_active_constraints():
                coef, _ = self._fit_constrained(X_boot, y_boot)
            else:
                model = ElasticNet(
                    alpha=self.alpha,
                    l1_ratio=self.l1_ratio,
                    fit_intercept=self.fit_intercept,
                    max_iter=self.max_iter,
                    tol=self.tol,
                )
                model.fit(X_boot, y_boot)
                coef = model.coef_

            coef_samples[i] = coef

        # Standard deviation of bootstrap estimates
        std_errors = np.std(coef_samples, axis=0)

        return {name: float(std_errors[i]) for i, name in enumerate(self.feature_names)}

    def fit(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        feature_names: list[str] | None = None,
    ) -> "ElasticNetModel":
        """
        Fit Elastic Net regression model.

        Args:
            X: Feature matrix of shape (n_samples, n_features).
            y: Target vector of shape (n_samples,).
            feature_names: Optional names for features.

        Returns:
            Self (fitted model instance).
        """
        start_time = time.time()

        # Validate input
        X, y = self._validate_input(X, y)
        n_samples, n_features = X.shape

        # Store original data for predictions
        self._y = y

        # Set feature names
        if feature_names is not None:
            self.feature_names = list(feature_names)
        else:
            self.feature_names = [f"x{i}" for i in range(n_features)]

        if len(self.feature_names) != n_features:
            raise ValueError(
                f"Number of feature names ({len(self.feature_names)}) must match number of features ({n_features})"
            )

        # Optionally scale features
        if self.scale_features:
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)
        else:
            X_scaled = X
        self._X_scaled = X_scaled

        # Fit model (constrained or unconstrained)
        if self._has_active_constraints():
            coef, intercept = self._fit_constrained(X_scaled, y)
        else:
            coef, intercept = self._fit_unconstrained(X_scaled, y)

        # Store scaled coefficients
        coef.copy()

        # Transform coefficients back to original scale
        if self.scale_features and self._scaler is not None:
            # Adjust coefficients for scaling
            coef = coef / self._scaler.scale_
            if self.fit_intercept:
                intercept = intercept - np.dot(coef, self._scaler.mean_)

        self.coefficients_ = {name: float(coef[i]) for i, name in enumerate(self.feature_names)}
        self.intercept_ = float(intercept)

        # Mark as fitted so we can predict
        self.is_fitted = True

        # Calculate predictions and residuals
        y_pred = self.predict(X)
        residuals = y - y_pred

        # Calculate metrics
        metrics = self._calculate_metrics(y, y_pred, n_features)

        # Bootstrap standard errors
        std_errors = self._bootstrap_standard_errors(X_scaled, y, self.bootstrap_n)

        # Scale standard errors back
        if self.scale_features and self._scaler is not None:
            std_errors = {name: se / self._scaler.scale_[i] for i, (name, se) in enumerate(std_errors.items())}

        # Calculate approximate p-values and confidence intervals
        # Using t-distribution approximation
        dof = n_samples - n_features - 1
        p_values = {}
        ci_lower = {}
        ci_upper = {}

        for name in self.feature_names:
            coef_val = self.coefficients_[name]
            se = std_errors[name]

            if se > 0:
                t_stat = coef_val / se
                p_values[name] = float(2 * (1 - stats.t.cdf(abs(t_stat), dof)))
                t_crit = stats.t.ppf(0.975, dof)
                ci_lower[name] = coef_val - t_crit * se
                ci_upper[name] = coef_val + t_crit * se
            else:
                p_values[name] = 0.0
                ci_lower[name] = coef_val
                ci_upper[name] = coef_val

        # Calculate VIF
        vif = self._calculate_vif(X)

        # Calculate diagnostics
        dw = self._calculate_durbin_watson(residuals)
        jb_pvalue = self._calculate_jarque_bera(residuals)

        training_time = time.time() - start_time

        # Create result object
        self._result = ModelResult(
            model_type=self.model_type,
            coefficients=self.coefficients_,
            intercept=self.intercept_,
            std_errors=std_errors,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_values=p_values,
            r_squared=metrics["r_squared"],
            adjusted_r_squared=metrics["adjusted_r_squared"],
            rmse=metrics["rmse"],
            mape=metrics["mape"],
            mae=metrics["mae"],
            aic=metrics["aic"],
            bic=metrics["bic"],
            fitted_values=y_pred,
            residuals=residuals,
            vif=vif,
            durbin_watson=dw,
            jarque_bera_pvalue=jb_pvalue,
            n_observations=n_samples,
            n_features=n_features,
            training_time_seconds=training_time,
        )

        return self

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Generate predictions.

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            Predicted values of shape (n_samples,).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predicting")

        X, _ = self._validate_input(X)

        # Apply coefficients
        coef = np.array([self.coefficients_[name] for name in self.feature_names])
        return X @ coef + self.intercept_

    def get_coefficients(self) -> dict[str, float]:
        """Get fitted coefficients."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return self.coefficients_.copy()

    def get_standard_errors(self) -> dict[str, float]:
        """Get standard errors of coefficients."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return self._result.std_errors.copy()

    def get_nonzero_features(self) -> list[str]:
        """
        Get list of features with non-zero coefficients.

        Elastic Net can set coefficients to exactly zero,
        effectively performing feature selection.

        Returns:
            List of feature names with non-zero coefficients.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        return [name for name, coef in self.coefficients_.items() if abs(coef) > 1e-10]

    def get_sparsity(self) -> float:
        """
        Get the sparsity ratio (fraction of zero coefficients).

        Returns:
            Sparsity ratio between 0 and 1.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        n_zero = sum(1 for coef in self.coefficients_.values() if abs(coef) < 1e-10)
        return n_zero / len(self.coefficients_)

    def get_regularization_path(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        alphas: list[float] | None = None,
        l1_ratios: list[float] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate coefficients for different alpha and l1_ratio values.

        Useful for visualizing the effect of regularization and
        selecting optimal hyperparameters.

        Args:
            X: Feature matrix.
            y: Target vector.
            alphas: List of alpha values to test.
            l1_ratios: List of l1_ratio values to test.

        Returns:
            Dictionary with regularization path data.
        """
        if alphas is None:
            alphas = np.logspace(-3, 3, 50).tolist()
        if l1_ratios is None:
            l1_ratios = [self.l1_ratio]

        X, y = self._validate_input(X, y)

        if self.scale_features:
            scaler = StandardScaler()
            X = scaler.fit_transform(X)

        results = []

        for l1_ratio in l1_ratios:
            paths = {name: [] for name in self.feature_names}

            for alpha in alphas:
                model = ElasticNet(
                    alpha=alpha,
                    l1_ratio=l1_ratio,
                    fit_intercept=self.fit_intercept,
                    max_iter=self.max_iter,
                )
                model.fit(X, y)

                for i, name in enumerate(self.feature_names):
                    paths[name].append(float(model.coef_[i]))

            results.append(
                {
                    "l1_ratio": l1_ratio,
                    "alphas": alphas,
                    "coefficients": paths,
                }
            )

        return {"paths": results}
