"""Linear (OLS) regression model for Marketing Mix Modeling."""

import time
from typing import Any

import numpy as np
import statsmodels.api as sm
from numpy.typing import NDArray
from scipy import stats
from scipy.optimize import minimize

from app.services.modeling.base import BaseModel, ModelResult


class LinearModel(BaseModel):
    """
    Ordinary Least Squares (OLS) regression model with optional constraint support.

    OLS finds coefficients that minimize the sum of squared residuals:
        min_β ||y - Xβ||²

    This implementation also supports constrained optimization for
    enforcing sign constraints and coefficient bounds, which is critical
    for Marketing Mix Models where coefficients should typically be positive.

    Advantages:
        - Simple and interpretable
        - Closed-form solution (fast) when unconstrained
        - Standard statistical inference available
        - Supports coefficient constraints via optimization

    Limitations:
        - No regularization (can overfit with many features)
        - Sensitive to multicollinearity
        - Constrained optimization may be slower

    Usage:
        model = LinearModel()
        model.fit(X, y, feature_names=['tv', 'radio', 'print'])
        predictions = model.predict(X_new)
        result = model.get_result()

        # With constraints
        constraints = {'tv': {'sign': 'positive'}, 'radio': {'min': 0, 'max': 1}}
        model = LinearModel(constraints=constraints)
    """

    def __init__(
        self,
        fit_intercept: bool = True,
        constraints: dict[str, dict[str, Any]] | None = None,
        linear_constraints: list[dict[str, Any]] | None = None,
        bootstrap_n: int = 100,
        **kwargs,
    ):
        """
        Initialize Linear model.

        Args:
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
            bootstrap_n: Number of bootstrap samples for standard errors when constrained.
            **kwargs: Additional configuration.
        """
        super().__init__(**kwargs)
        self.model_type = "ols"
        self.fit_intercept = fit_intercept
        self.constraints = constraints or {}
        self.linear_constraints = linear_constraints or []
        self.bootstrap_n = bootstrap_n
        self._sm_result = None
        self._result: ModelResult | None = None

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

    def _fit_constrained(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
    ) -> tuple[NDArray[np.float64], float]:
        """
        Fit OLS with coefficient constraints using optimization.

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
            """OLS objective (sum of squared residuals)."""
            if self.fit_intercept:
                intercept = params[0]
                coef = params[1:]
            else:
                intercept = 0.0
                coef = params

            # Predictions
            y_pred = X @ coef + intercept

            # Sum of squared residuals
            return np.sum((y - y_pred) ** 2)

        def gradient(params: NDArray[np.float64]) -> NDArray[np.float64]:
            """Gradient of the OLS objective."""
            if self.fit_intercept:
                intercept = params[0]
                coef = params[1:]
            else:
                intercept = 0.0
                coef = params

            # Residuals
            residuals = y - (X @ coef + intercept)

            # Gradient
            grad_coef = -2 * X.T @ residuals

            if self.fit_intercept:
                grad_intercept = -2 * np.sum(residuals)
                return np.concatenate([[grad_intercept], grad_coef])
            else:
                return grad_coef

        # Initial guess from unconstrained OLS
        if self.fit_intercept:
            X_with_const = sm.add_constant(X, has_constant="add")
            ols_result = sm.OLS(y, X_with_const).fit()
            x0 = ols_result.params.copy()
        else:
            ols_result = sm.OLS(y, X).fit()
            x0 = ols_result.params.copy()

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
                options={"maxiter": 1000, "ftol": 1e-10},
            )
        else:
            result = minimize(
                objective,
                x0,
                method="L-BFGS-B",
                jac=gradient,
                bounds=bounds,
                options={"maxiter": 1000, "ftol": 1e-10},
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
            coef, _ = self._fit_constrained(X_boot, y_boot)
            coef_samples[i] = coef

        # Standard deviation of bootstrap estimates
        std_errors = np.std(coef_samples, axis=0)

        return {name: float(std_errors[i]) for i, name in enumerate(self.feature_names)}

    def fit(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        feature_names: list[str] | None = None,
    ) -> "LinearModel":
        """
        Fit OLS regression model.

        Uses statsmodels OLS for fitting with full statistical inference.

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

        # Set feature names
        if feature_names is not None:
            self.feature_names = list(feature_names)
        else:
            self.feature_names = [f"x{i}" for i in range(n_features)]

        if len(self.feature_names) != n_features:
            raise ValueError(
                f"Number of feature names ({len(self.feature_names)}) must match number of features ({n_features})"
            )

        # Check if we have active constraints
        use_constrained = self._has_active_constraints()

        if use_constrained:
            # Use constrained optimization
            coef, intercept = self._fit_constrained(X, y)
            self.coefficients_ = {name: float(coef[i]) for i, name in enumerate(self.feature_names)}
            self.intercept_ = float(intercept)

            # Calculate predictions and residuals
            y_pred = X @ coef + intercept
            residuals = y - y_pred

            # Calculate metrics
            metrics = self._calculate_metrics(y, y_pred, n_features)

            # Bootstrap standard errors for constrained case
            std_errors = self._bootstrap_standard_errors(X, y, self.bootstrap_n)

            # Approximate p-values and confidence intervals
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
        else:
            # Use standard OLS with statsmodels
            # Add constant for intercept if requested
            if self.fit_intercept:
                X_with_const = sm.add_constant(X, has_constant="add")
            else:
                X_with_const = X

            # Fit OLS model
            model = sm.OLS(y, X_with_const)
            self._sm_result = model.fit()

            # Extract coefficients
            params = self._sm_result.params
            if self.fit_intercept:
                self.intercept_ = float(params[0])
                self.coefficients_ = {name: float(params[i + 1]) for i, name in enumerate(self.feature_names)}
            else:
                self.intercept_ = 0.0
                self.coefficients_ = {name: float(params[i]) for i, name in enumerate(self.feature_names)}

            # Calculate predictions and residuals
            y_pred = self._sm_result.fittedvalues
            residuals = self._sm_result.resid

            # Calculate metrics
            metrics = self._calculate_metrics(y, y_pred, n_features)

            # Extract standard errors
            bse = self._sm_result.bse
            if self.fit_intercept:
                std_errors = {name: float(bse[i + 1]) for i, name in enumerate(self.feature_names)}
            else:
                std_errors = {name: float(bse[i]) for i, name in enumerate(self.feature_names)}

            # Extract p-values
            pvalues = self._sm_result.pvalues
            if self.fit_intercept:
                p_values = {name: float(pvalues[i + 1]) for i, name in enumerate(self.feature_names)}
            else:
                p_values = {name: float(pvalues[i]) for i, name in enumerate(self.feature_names)}

            # Calculate confidence intervals (95%)
            conf_int = self._sm_result.conf_int(alpha=0.05)
            if self.fit_intercept:
                ci_lower = {name: float(conf_int[i + 1, 0]) for i, name in enumerate(self.feature_names)}
                ci_upper = {name: float(conf_int[i + 1, 1]) for i, name in enumerate(self.feature_names)}
            else:
                ci_lower = {name: float(conf_int[i, 0]) for i, name in enumerate(self.feature_names)}
                ci_upper = {name: float(conf_int[i, 1]) for i, name in enumerate(self.feature_names)}

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

        self.is_fitted = True
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

        # For constrained case, use stored coefficients directly
        if self._sm_result is None:
            coef = np.array([self.coefficients_[name] for name in self.feature_names])
            return X @ coef + self.intercept_

        # For unconstrained case, use statsmodels
        if self.fit_intercept:
            X_with_const = sm.add_constant(X, has_constant="add")
        else:
            X_with_const = X

        return self._sm_result.predict(X_with_const)

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

    def get_summary(self) -> str:
        """
        Get text summary of regression results.

        Returns:
            Formatted summary string from statsmodels.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return str(self._sm_result.summary())

    def get_residual_diagnostics(self) -> dict[str, float]:
        """
        Get detailed residual diagnostics.

        Returns:
            Dictionary with diagnostic statistics.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        residuals = self._result.residuals

        # Shapiro-Wilk test for normality (for small samples)
        if len(residuals) <= 5000:
            _, shapiro_p = stats.shapiro(residuals)
        else:
            shapiro_p = None

        # Skewness and kurtosis
        skewness = float(stats.skew(residuals))
        kurtosis = float(stats.kurtosis(residuals))

        return {
            "durbin_watson": self._result.durbin_watson,
            "jarque_bera_pvalue": self._result.jarque_bera_pvalue,
            "shapiro_wilk_pvalue": shapiro_p,
            "skewness": skewness,
            "kurtosis": kurtosis,
            "residual_mean": float(np.mean(residuals)),
            "residual_std": float(np.std(residuals)),
        }
