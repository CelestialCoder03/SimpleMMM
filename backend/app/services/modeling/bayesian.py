"""Bayesian regression model using PyMC for Marketing Mix Modeling."""

import time
from typing import Any

import numpy as np
from numpy.typing import NDArray
from sklearn.preprocessing import StandardScaler

from app.services.modeling.base import BaseModel, ModelResult

# PyMC imports - handle gracefully if not installed
try:
    import arviz as az
    import pymc as pm

    PYMC_AVAILABLE = True
except ImportError:
    PYMC_AVAILABLE = False
    pm = None
    az = None


class BayesianModel(BaseModel):
    """
    Bayesian Linear Regression using PyMC for full MCMC inference.

    This implementation uses PyMC's NUTS (No-U-Turn Sampler) for efficient
    Hamiltonian Monte Carlo sampling, providing:

    - True posterior distributions for all coefficients
    - Meaningful convergence diagnostics (R-hat, ESS)
    - Bayesian model comparison metrics (LOO-CV, WAIC)
    - Credible intervals with proper probabilistic interpretation

    Model specification:
        y ~ Normal(X @ beta + intercept, sigma)
        beta[i] ~ UserPrior[i] or Normal(0, 2)
        intercept ~ Normal(y_mean, y_std * 10)
        sigma ~ HalfNormal(y_std)

    Supported prior distributions:
        - normal: Normal(mu, sigma)
        - half_normal: HalfNormal(sigma) - for positive coefficients
        - truncated_normal: TruncatedNormal(mu, sigma, lower, upper)
        - uniform: Uniform(lower, upper)
        - exponential: Exponential(lam)
        - gamma: Gamma(alpha, beta)
        - beta: Beta(alpha, beta)

    Usage:
        priors = {
            'tv': {'distribution': 'normal', 'params': {'mu': 0.5, 'sigma': 0.2}},
            'radio': {'distribution': 'half_normal', 'params': {'sigma': 0.3}},
        }
        model = BayesianModel(priors=priors, n_samples=2000, n_chains=4)
        model.fit(X, y, feature_names=['tv', 'radio', 'print'])
    """

    def __init__(
        self,
        priors: dict[str, dict[str, Any]] | None = None,
        n_samples: int = 2000,
        n_warmup: int = 1000,
        n_chains: int = 4,
        target_accept: float = 0.9,
        fit_intercept: bool = True,
        scale_features: bool = True,
        seed: int | None = None,
        compute_loo: bool = True,
        compute_waic: bool = True,
        **kwargs,
    ):
        """
        Initialize Bayesian model with PyMC.

        Args:
            priors: Dictionary of prior specifications per variable:
                {
                    'feature_name': {
                        'distribution': 'normal', 'half_normal', 'truncated_normal',
                                       'uniform', 'exponential', 'gamma', 'beta'
                        'params': distribution parameters
                    }
                }
            n_samples: Number of posterior samples to draw per chain.
            n_warmup: Number of warmup/tuning samples to discard.
            n_chains: Number of independent MCMC chains (for convergence diagnostics).
            target_accept: Target acceptance probability for NUTS (0.8-0.95 recommended).
            fit_intercept: Whether to fit an intercept term.
            scale_features: Whether to standardize features before fitting.
            seed: Random seed for reproducibility.
            compute_loo: Whether to compute LOO-CV for model comparison.
            compute_waic: Whether to compute WAIC for model comparison.
            **kwargs: Additional configuration.
        """
        super().__init__(**kwargs)

        if not PYMC_AVAILABLE:
            raise ImportError("PyMC is required for BayesianModel. Install with: pip install pymc arviz")

        self.model_type = "bayesian"
        self.priors = priors or {}
        self.n_samples = n_samples
        self.n_warmup = n_warmup
        self.n_chains = n_chains
        self.target_accept = target_accept
        self.fit_intercept = fit_intercept
        self.scale_features = scale_features
        self.seed = seed
        self.compute_loo = compute_loo
        self.compute_waic = compute_waic

        self._scaler: StandardScaler | None = None
        self._pymc_model: pm.Model | None = None
        self._trace: az.InferenceData | None = None
        self._result: ModelResult | None = None
        self._posterior_samples: dict[str, NDArray[np.float64]] = {}

        # Data scaling params for coefficient transformation
        self._y_mean: float = 0.0
        self._y_std: float = 1.0

    def _create_pymc_prior(
        self,
        name: str,
        prior_spec: dict[str, Any],
    ) -> pm.Distribution:
        """
        Create PyMC distribution from prior specification.

        Args:
            name: Name for the PyMC variable.
            prior_spec: Prior specification dictionary with 'distribution' and 'params'.

        Returns:
            PyMC distribution object.
        """
        dist = prior_spec.get("distribution", "normal")
        params = prior_spec.get("params", {})

        if dist == "normal":
            return pm.Normal(name, mu=params.get("mu", 0), sigma=params.get("sigma", 1))
        elif dist == "half_normal":
            return pm.HalfNormal(name, sigma=params.get("sigma", 1))
        elif dist == "truncated_normal":
            return pm.TruncatedNormal(
                name,
                mu=params.get("mu", 0),
                sigma=params.get("sigma", 1),
                lower=params.get("lower"),
                upper=params.get("upper"),
            )
        elif dist == "uniform":
            return pm.Uniform(
                name,
                lower=params.get("lower", 0),
                upper=params.get("upper", 1),
            )
        elif dist == "exponential":
            return pm.Exponential(name, lam=params.get("lam", 1))
        elif dist == "gamma":
            return pm.Gamma(
                name,
                alpha=params.get("alpha", 2),
                beta=params.get("beta", 1),
            )
        elif dist == "beta":
            return pm.Beta(
                name,
                alpha=params.get("alpha", 2),
                beta=params.get("beta", 2),
            )
        else:
            # Default to weakly informative normal
            return pm.Normal(name, mu=0, sigma=2)

    def _build_model(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
    ) -> pm.Model:
        """
        Build PyMC model with specified priors.

        Args:
            X: Feature matrix (potentially scaled).
            y: Target vector.

        Returns:
            PyMC Model object.
        """
        X.shape[1]

        # Scale y for numerical stability
        self._y_mean = float(np.mean(y))
        self._y_std = float(np.std(y)) or 1.0
        y_scaled = (y - self._y_mean) / self._y_std

        with pm.Model() as model:
            # Create coefficient priors
            betas = []
            for i, name in enumerate(self.feature_names):
                prior_spec = self.priors.get(name, {"distribution": "normal", "params": {"mu": 0, "sigma": 2}})
                beta_i = self._create_pymc_prior(f"beta_{name}", prior_spec)
                betas.append(beta_i)

            # Stack into vector
            beta = pm.math.stack(betas)

            # Intercept prior (weakly informative on scaled data)
            if self.fit_intercept:
                intercept = pm.Normal("intercept", mu=0, sigma=10)
            else:
                intercept = 0.0

            # Noise prior (on scaled data, so sigma ~ 1 is reasonable)
            sigma = pm.HalfNormal("sigma", sigma=1)

            # Linear model
            mu = pm.math.dot(X, beta) + intercept

            # Likelihood
            pm.Normal("y_obs", mu=mu, sigma=sigma, observed=y_scaled)

        return model

    def fit(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        feature_names: list[str] | None = None,
    ) -> "BayesianModel":
        """
        Fit Bayesian model using MCMC sampling.

        Uses PyMC's NUTS sampler for efficient Hamiltonian Monte Carlo.

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
        n_samples_data, n_features = X.shape

        # Set feature names
        if feature_names is not None:
            self.feature_names = list(feature_names)
        else:
            self.feature_names = [f"x{i}" for i in range(n_features)]

        if len(self.feature_names) != n_features:
            raise ValueError(
                f"Number of feature names ({len(self.feature_names)}) must match number of features ({n_features})"
            )

        # Scale features
        if self.scale_features:
            self._scaler = StandardScaler()
            X_scaled = self._scaler.fit_transform(X)
        else:
            X_scaled = X

        # Build PyMC model
        self._pymc_model = self._build_model(X_scaled, y)

        # Sample from posterior
        with self._pymc_model:
            self._trace = pm.sample(
                draws=self.n_samples,
                tune=self.n_warmup,
                chains=self.n_chains,
                target_accept=self.target_accept,
                random_seed=self.seed,
                return_inferencedata=True,
                progressbar=True,
                cores=1,  # Must be 1 when running inside Celery (daemonic process)
            )

        # Mark as fitted before extracting results (predict is called in _extract_results)
        self.is_fitted = True

        # Extract results
        self._extract_results(X, y, n_features)

        training_time = time.time() - start_time
        self._result.training_time_seconds = training_time

        return self

    def _extract_results(
        self,
        X: NDArray[np.float64],
        y: NDArray[np.float64],
        n_features: int,
    ) -> None:
        """
        Extract results from MCMC trace.

        Transforms coefficients back to original scale and computes diagnostics.

        Args:
            X: Original feature matrix.
            y: Original target vector.
            n_features: Number of features.
        """
        n_samples_data = len(y)

        # Get posterior samples and transform back to original scale
        coef_means = {}
        std_errors = {}
        ci_lower = {}
        ci_upper = {}
        r_hat = {}
        ess = {}

        for i, name in enumerate(self.feature_names):
            var_name = f"beta_{name}"
            samples = self._trace.posterior[var_name].values.flatten()

            # Transform back to original scale
            if self.scale_features and self._scaler is not None:
                samples = samples * self._y_std / self._scaler.scale_[i]
            else:
                samples = samples * self._y_std

            self._posterior_samples[name] = samples
            coef_means[name] = float(np.mean(samples))
            std_errors[name] = float(np.std(samples))
            ci_lower[name] = float(np.percentile(samples, 2.5))
            ci_upper[name] = float(np.percentile(samples, 97.5))

            # Real diagnostics from ArviZ
            summary = az.summary(self._trace, var_names=[var_name])
            r_hat[name] = float(summary["r_hat"].values[0])
            ess[name] = float(summary["ess_bulk"].values[0])

        # Intercept handling
        if self.fit_intercept:
            intercept_samples = self._trace.posterior["intercept"].values.flatten()
            # Transform intercept back to original scale
            intercept_samples = intercept_samples * self._y_std + self._y_mean

            if self.scale_features and self._scaler is not None:
                # Adjust for feature scaling: intercept_adj = intercept - sum(coef * mean / scale * y_std)
                coef_array = np.array([coef_means[n] for n in self.feature_names])
                intercept_samples = intercept_samples - np.dot(coef_array, self._scaler.mean_)

            self._posterior_samples["intercept"] = intercept_samples
            self.intercept_ = float(np.mean(intercept_samples))

            summary = az.summary(self._trace, var_names=["intercept"])
            r_hat["intercept"] = float(summary["r_hat"].values[0])
            ess["intercept"] = float(summary["ess_bulk"].values[0])
        else:
            self.intercept_ = 0.0

        self.coefficients_ = coef_means

        # Calculate predictions and metrics
        y_pred = self.predict(X)
        residuals = y - y_pred
        metrics = self._calculate_metrics(y, y_pred, n_features)

        # Calculate VIF and diagnostics
        vif = self._calculate_vif(X)
        dw = self._calculate_durbin_watson(residuals)
        jb_pvalue = self._calculate_jarque_bera(residuals)

        # Bayesian model comparison metrics
        loo_val = None
        loo_se_val = None
        waic_val = None
        waic_se_val = None

        if self.compute_loo:
            try:
                loo_result = az.loo(self._trace)
                loo_val = float(loo_result.elpd_loo)
                loo_se_val = float(loo_result.se)
            except Exception:
                pass  # LOO computation can fail in some edge cases

        if self.compute_waic:
            try:
                waic_result = az.waic(self._trace)
                waic_val = float(waic_result.elpd_waic)
                waic_se_val = float(waic_result.se)
            except Exception:
                pass  # WAIC computation can fail in some edge cases

        self._result = ModelResult(
            model_type=self.model_type,
            coefficients=self.coefficients_,
            intercept=self.intercept_,
            std_errors=std_errors,
            ci_lower=ci_lower,
            ci_upper=ci_upper,
            p_values={},  # Not applicable for Bayesian
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
            r_hat=r_hat,
            ess=ess,
            posterior_samples=self._posterior_samples,
            loo=loo_val,
            loo_se=loo_se_val,
            waic=waic_val,
            waic_se=waic_se_val,
            n_observations=n_samples_data,
            n_features=n_features,
            training_time_seconds=0.0,  # Set by caller
        )

    def predict(self, X: NDArray[np.float64]) -> NDArray[np.float64]:
        """
        Generate predictions using posterior mean coefficients.

        Args:
            X: Feature matrix of shape (n_samples, n_features).

        Returns:
            Predicted values of shape (n_samples,).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predicting")

        X, _ = self._validate_input(X)
        coef = np.array([self.coefficients_[name] for name in self.feature_names])
        return X @ coef + self.intercept_

    def predict_samples(
        self,
        X: NDArray[np.float64],
        n_samples: int | None = None,
    ) -> NDArray[np.float64]:
        """
        Generate predictions with uncertainty using posterior samples.

        Each column represents predictions from one posterior sample,
        allowing for uncertainty quantification in predictions.

        Args:
            X: Feature matrix of shape (n_data_points, n_features).
            n_samples: Number of posterior samples to use (None = all).

        Returns:
            Prediction samples of shape (n_data_points, n_posterior_samples).
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predicting")

        X, _ = self._validate_input(X)
        n_data = X.shape[0]

        # Get posterior samples
        available_samples = len(self._posterior_samples[self.feature_names[0]])
        if n_samples is None:
            n_samples = available_samples
        else:
            n_samples = min(n_samples, available_samples)

        predictions = np.zeros((n_data, n_samples))

        for s in range(n_samples):
            coef = np.array([self._posterior_samples[name][s] for name in self.feature_names])

            if self.fit_intercept and "intercept" in self._posterior_samples:
                intercept = self._posterior_samples["intercept"][s]
            else:
                intercept = 0.0

            predictions[:, s] = X @ coef + intercept

        return predictions

    def get_coefficients(self) -> dict[str, float]:
        """Get posterior mean coefficients."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return self.coefficients_.copy()

    def get_standard_errors(self) -> dict[str, float]:
        """Get posterior standard deviations of coefficients."""
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return self._result.std_errors.copy()

    def get_credible_intervals(
        self,
        alpha: float = 0.05,
    ) -> dict[str, tuple[float, float]]:
        """
        Get credible intervals for coefficients.

        These are true Bayesian credible intervals computed from
        posterior samples, with proper probabilistic interpretation.

        Args:
            alpha: Significance level (default 0.05 for 95% intervals).

        Returns:
            Dictionary mapping feature names to (lower, upper) tuples.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        lower_pct = alpha / 2 * 100
        upper_pct = (1 - alpha / 2) * 100

        intervals = {}
        for name in self.feature_names:
            samples = self._posterior_samples[name]
            intervals[name] = (
                float(np.percentile(samples, lower_pct)),
                float(np.percentile(samples, upper_pct)),
            )

        return intervals

    def get_posterior_samples(self) -> dict[str, NDArray[np.float64]]:
        """
        Get raw posterior samples for all coefficients.

        These are actual MCMC samples from the posterior distribution,
        not synthetic samples from an approximation.

        Returns:
            Dictionary mapping parameter names to sample arrays.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return {k: v.copy() for k, v in self._posterior_samples.items()}

    def get_convergence_diagnostics(self) -> dict[str, dict[str, float]]:
        """
        Get detailed convergence diagnostics.

        Returns:
            Dictionary with R-hat, ESS, and other diagnostics per parameter.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")

        return {
            "r_hat": self._result.r_hat.copy(),
            "ess": self._result.ess.copy(),
        }

    def get_trace(self) -> "az.InferenceData":
        """
        Get the full ArviZ InferenceData object.

        Useful for advanced diagnostics, plotting, and model comparison.

        Returns:
            ArviZ InferenceData containing posterior samples and metadata.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted first")
        return self._trace
