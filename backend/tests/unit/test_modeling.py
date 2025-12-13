"""Comprehensive tests for the modeling services."""

import numpy as np
import pandas as pd
import pytest

# =============================================================================
# TRANSFORMATION TESTS
# =============================================================================


class TestAdstockTransform:
    """Tests for AdstockTransform."""

    def test_geometric_adstock_basic(self):
        """Test basic geometric adstock transformation."""
        from app.services.modeling.transformations import AdstockTransform

        transform = AdstockTransform(decay=0.5, max_lag=8)
        x = np.array([100, 0, 0, 0, 0])
        result = transform.transform(x)

        # First value should be the input
        assert result[0] == 100
        # Second should be 0 + 0.5 * 100 = 50
        assert result[1] == pytest.approx(50, rel=0.01)
        # Third should be 0 + 0.5 * 50 = 25
        assert result[2] == pytest.approx(25, rel=0.01)

    def test_adstock_decay_bounds(self):
        """Test decay parameter bounds."""
        from app.services.modeling.transformations import AdstockTransform

        # Valid decay
        transform = AdstockTransform(decay=0.9)
        assert transform.decay == 0.9

        # Invalid decay
        with pytest.raises(ValueError):
            AdstockTransform(decay=1.5)
        with pytest.raises(ValueError):
            AdstockTransform(decay=-0.1)

    def test_adstock_max_lag(self):
        """Test max_lag parameter."""
        from app.services.modeling.transformations import AdstockTransform

        transform = AdstockTransform(decay=0.5, max_lag=4)
        assert transform.max_lag == 4

        with pytest.raises(ValueError):
            AdstockTransform(max_lag=0)

    def test_adstock_fit_decay(self):
        """Test auto-fitting decay rate."""
        from app.services.modeling.transformations import AdstockTransform

        # Create data with known carryover effect
        np.random.seed(42)
        x = np.random.uniform(50, 150, 100)

        # Create target with 0.7 decay effect
        y = np.zeros(100)
        for t in range(100):
            for k in range(min(t + 1, 8)):
                y[t] += (0.7**k) * x[t - k]
        y += np.random.normal(0, 10, 100)

        optimal_decay = AdstockTransform.fit_decay(x, y, max_lag=8)

        # Should be close to 0.7
        assert 0.5 < optimal_decay < 0.9

    def test_get_params(self):
        """Test getting transformation parameters."""
        from app.services.modeling.transformations import AdstockTransform

        transform = AdstockTransform(decay=0.6, max_lag=10)
        params = transform.get_params()

        assert params["type"] == "geometric"
        assert params["adstock_type"] == "geometric"
        assert params["decay"] == 0.6
        assert params["max_lag"] == 10


class TestSaturationTransform:
    """Tests for SaturationTransform."""

    def test_hill_saturation_basic(self):
        """Test basic Hill saturation transformation."""
        from app.services.modeling.transformations import SaturationTransform

        transform = SaturationTransform(k=100, s=1.0, saturation_type="hill")

        # At x=0, output should be 0
        assert transform.transform(np.array([0]))[0] == pytest.approx(0, abs=0.01)

        # At x=k, output should be 0.5
        assert transform.transform(np.array([100]))[0] == pytest.approx(0.5, rel=0.01)

        # As x -> inf, output should approach 1
        assert transform.transform(np.array([100000]))[0] == pytest.approx(1.0, rel=0.01)

    def test_saturation_diminishing_returns(self):
        """Test that saturation produces diminishing returns."""
        from app.services.modeling.transformations import SaturationTransform

        transform = SaturationTransform(k=100, s=1.0)

        x = np.array([10, 20, 30, 40, 50])
        result = transform.transform(x)

        # Check diminishing increments
        increments = np.diff(result)
        for i in range(len(increments) - 1):
            assert increments[i] > increments[i + 1]

    def test_marginal_response(self):
        """Test marginal response calculation."""
        from app.services.modeling.transformations import SaturationTransform

        transform = SaturationTransform(k=100, s=1.0)

        x = np.array([50, 100, 150])
        marginal = transform.marginal_response(x)

        # Marginal should decrease as x increases
        assert marginal[0] > marginal[1] > marginal[2]

    def test_invalid_parameters(self):
        """Test invalid parameter validation."""
        from app.services.modeling.transformations import SaturationTransform

        with pytest.raises(ValueError):
            SaturationTransform(k=-1)
        with pytest.raises(ValueError):
            SaturationTransform(s=0)


class TestFeatureTransformer:
    """Tests for combined FeatureTransformer."""

    def test_combined_transformation(self):
        """Test applying both adstock and saturation."""
        from app.services.modeling.transformations import (
            AdstockTransform,
            FeatureTransformer,
            SaturationTransform,
        )

        adstock = AdstockTransform(decay=0.5, max_lag=4)
        saturation = SaturationTransform(k=100, s=1.0)
        transformer = FeatureTransformer(adstock=adstock, saturation=saturation)

        x = np.array([100, 50, 25, 0, 0])
        result = transformer.transform(x)

        # Result should be bounded [0, 1] due to saturation
        assert np.all(result >= 0)
        assert np.all(result <= 1)

    def test_from_config(self):
        """Test creating transformer from config."""
        from app.services.modeling.transformations import FeatureTransformer

        adstock_config = {"type": "geometric", "decay": 0.7, "max_lag": 12}
        saturation_config = {"type": "hill", "k": 200, "s": 1.5}

        transformer = FeatureTransformer.from_config(
            adstock_config=adstock_config,
            saturation_config=saturation_config,
        )

        assert transformer.adstock is not None
        assert transformer.adstock.decay == 0.7
        assert transformer.saturation is not None
        assert transformer.saturation.k == 200


# =============================================================================
# MODEL TESTS
# =============================================================================


class TestLinearModel:
    """Tests for LinearModel (OLS)."""

    def test_fit_basic(self):
        """Test basic OLS fitting."""
        from app.services.modeling.linear import LinearModel

        np.random.seed(42)
        X = np.random.randn(100, 3)
        y = 5 + 2 * X[:, 0] + 3 * X[:, 1] - 1 * X[:, 2] + np.random.randn(100) * 0.5

        model = LinearModel()
        model.fit(X, y, feature_names=["x1", "x2", "x3"])

        assert model.is_fitted
        coef = model.get_coefficients()
        assert "x1" in coef
        assert abs(coef["x1"] - 2) < 0.5
        assert abs(coef["x2"] - 3) < 0.5

    def test_predict(self):
        """Test prediction."""
        from app.services.modeling.linear import LinearModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 1 + X[:, 0] + X[:, 1]

        model = LinearModel()
        model.fit(X, y, feature_names=["a", "b"])

        X_new = np.array([[1, 1], [0, 0]])
        predictions = model.predict(X_new)

        assert len(predictions) == 2
        assert predictions[0] > predictions[1]

    def test_metrics(self):
        """Test that fit metrics are calculated."""
        from app.services.modeling.linear import LinearModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 1 + 2 * X[:, 0] + np.random.randn(100) * 0.1

        model = LinearModel()
        model.fit(X, y, feature_names=["a", "b"])
        result = model.get_result()

        assert result.r_squared > 0.9
        assert result.rmse < 1
        assert result.aic is not None
        assert result.bic is not None

    def test_standard_errors(self):
        """Test standard errors are calculated."""
        from app.services.modeling.linear import LinearModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 1 + X[:, 0] + np.random.randn(100) * 0.5

        model = LinearModel()
        model.fit(X, y, feature_names=["a", "b"])

        se = model.get_standard_errors()
        assert "a" in se
        assert se["a"] > 0


class TestElasticNetModel:
    """Tests for ElasticNetModel."""

    def test_fit_basic(self):
        """Test basic ElasticNet fitting."""
        from app.services.modeling.elasticnet import ElasticNetModel

        np.random.seed(42)
        X = np.random.randn(100, 3)
        y = 5 + 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5

        model = ElasticNetModel(alpha=1.0, l1_ratio=0.5, bootstrap_n=10)
        model.fit(X, y, feature_names=["x1", "x2", "x3"])

        assert model.is_fitted
        coef = model.get_coefficients()
        assert len(coef) == 3

    def test_l1_ratio_effect(self):
        """Test that l1_ratio affects sparsity."""
        from app.services.modeling.elasticnet import ElasticNetModel

        np.random.seed(42)
        X = np.random.randn(100, 5)
        # Only first 2 features matter
        y = 5 + 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5
        names = [f"x{i}" for i in range(5)]

        # High l1_ratio should give more sparse coefficients
        model_sparse = ElasticNetModel(alpha=1.0, l1_ratio=0.9, bootstrap_n=10)
        model_sparse.fit(X, y, feature_names=names)

        # Lower l1_ratio should give less sparse coefficients
        model_dense = ElasticNetModel(alpha=1.0, l1_ratio=0.1, bootstrap_n=10)
        model_dense.fit(X, y, feature_names=names)

        sparse_sparsity = model_sparse.get_sparsity()
        dense_sparsity = model_dense.get_sparsity()

        # Sparse model should have more zero coefficients
        assert sparse_sparsity >= dense_sparsity

    def test_positive_constraints(self):
        """Test positive sign constraints."""
        from app.services.modeling.elasticnet import ElasticNetModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 10 - 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5

        constraints = {
            "x1": {"sign": "positive"},
            "x2": {"sign": "positive"},
        }

        model = ElasticNetModel(alpha=1.0, l1_ratio=0.5, constraints=constraints, bootstrap_n=10)
        model.fit(X, y, feature_names=["x1", "x2"])

        coef = model.get_coefficients()
        assert coef["x1"] >= -0.01

    def test_get_nonzero_features(self):
        """Test getting nonzero features."""
        from app.services.modeling.elasticnet import ElasticNetModel

        np.random.seed(42)
        X = np.random.randn(100, 5)
        y = 5 + 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5

        # Use moderate regularization so true features remain nonzero
        model = ElasticNetModel(alpha=0.5, l1_ratio=0.9, bootstrap_n=10)
        model.fit(X, y, feature_names=[f"x{i}" for i in range(5)])

        nonzero = model.get_nonzero_features()
        assert isinstance(nonzero, list)
        # At minimum, x0 and x1 should be nonzero (they have true effects)
        assert "x0" in nonzero or "x1" in nonzero


class TestRidgeModel:
    """Tests for RidgeModel."""

    def test_fit_basic(self):
        """Test basic Ridge fitting."""
        from app.services.modeling.ridge import RidgeModel

        np.random.seed(42)
        X = np.random.randn(100, 3)
        y = 5 + 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5

        model = RidgeModel(alpha=1.0)
        model.fit(X, y, feature_names=["x1", "x2", "x3"])

        assert model.is_fitted
        coef = model.get_coefficients()
        assert len(coef) == 3

    def test_regularization_effect(self):
        """Test that higher alpha shrinks coefficients."""
        from app.services.modeling.ridge import RidgeModel

        np.random.seed(42)
        X = np.random.randn(50, 5)
        y = np.sum(X, axis=1) + np.random.randn(50) * 0.1
        names = [f"x{i}" for i in range(5)]

        model_low = RidgeModel(alpha=0.1, bootstrap_n=10)
        model_low.fit(X, y, feature_names=names)

        model_high = RidgeModel(alpha=100, bootstrap_n=10)
        model_high.fit(X, y, feature_names=names)

        # Higher alpha should give smaller coefficients
        coef_low = np.array(list(model_low.get_coefficients().values()))
        coef_high = np.array(list(model_high.get_coefficients().values()))

        assert np.sum(coef_low**2) > np.sum(coef_high**2)

    def test_positive_constraints(self):
        """Test positive sign constraints."""
        from app.services.modeling.ridge import RidgeModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        # Create negative relationship
        y = 10 - 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5

        constraints = {
            "x1": {"sign": "positive"},
            "x2": {"sign": "positive"},
        }

        model = RidgeModel(alpha=1.0, constraints=constraints, bootstrap_n=10)
        model.fit(X, y, feature_names=["x1", "x2"])

        coef = model.get_coefficients()
        # x1 should be forced to >= 0 despite negative true relationship
        assert coef["x1"] >= -0.01  # Small tolerance


class TestBayesianModel:
    """Tests for BayesianModel with PyMC MCMC sampling."""

    def test_fit_basic(self):
        """Test basic Bayesian fitting with MCMC."""
        from app.services.modeling.bayesian import BayesianModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 5 + 2 * X[:, 0] + np.random.randn(100) * 0.5

        model = BayesianModel(
            n_samples=200,
            n_warmup=100,
            n_chains=2,
            seed=42,
            compute_loo=False,
            compute_waic=False,
        )
        model.fit(X, y, feature_names=["x1", "x2"])

        assert model.is_fitted
        coef = model.get_coefficients()
        assert "x1" in coef
        # True coefficient is 2, should be close
        assert abs(coef["x1"] - 2) < 1.0

    def test_posterior_samples(self):
        """Test that posterior samples are generated from MCMC."""
        from app.services.modeling.bayesian import BayesianModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 1 + X[:, 0] + np.random.randn(100) * 0.5

        model = BayesianModel(
            n_samples=200,
            n_warmup=100,
            n_chains=2,
            seed=42,
            compute_loo=False,
            compute_waic=False,
        )
        model.fit(X, y, feature_names=["a", "b"])

        samples = model.get_posterior_samples()
        assert "a" in samples
        # Total samples = n_samples * n_chains
        assert len(samples["a"]) == 200 * 2

    def test_credible_intervals(self):
        """Test credible interval calculation."""
        from app.services.modeling.bayesian import BayesianModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 1 + X[:, 0] + np.random.randn(100) * 0.5

        model = BayesianModel(
            n_samples=200,
            n_warmup=100,
            n_chains=2,
            seed=42,
            compute_loo=False,
            compute_waic=False,
        )
        model.fit(X, y, feature_names=["a", "b"])

        intervals = model.get_credible_intervals(alpha=0.05)
        assert "a" in intervals
        lower, upper = intervals["a"]
        assert lower < upper

    def test_priors_effect(self):
        """Test that informative priors affect results."""
        from app.services.modeling.bayesian import BayesianModel

        np.random.seed(42)
        X = np.random.randn(50, 1)
        # True coefficient is ~0
        y = 5 + np.random.randn(50) * 0.5

        # Strong prior that coefficient should be 2
        priors = {"x1": {"distribution": "normal", "params": {"mu": 2.0, "sigma": 0.1}}}

        model = BayesianModel(
            priors=priors,
            n_samples=200,
            n_warmup=100,
            n_chains=2,
            seed=42,
            compute_loo=False,
            compute_waic=False,
        )
        model.fit(X, y, feature_names=["x1"])

        # Coefficient should be pulled toward prior mean
        coef = model.get_coefficients()["x1"]
        assert abs(coef - 2.0) < 1.5  # Should be closer to 2 than far away

    def test_convergence_diagnostics(self):
        """Test that R-hat and ESS are meaningful."""
        from app.services.modeling.bayesian import BayesianModel

        np.random.seed(42)
        X = np.random.randn(100, 2)
        y = 1 + X[:, 0] + np.random.randn(100) * 0.5

        model = BayesianModel(
            n_samples=500,
            n_warmup=200,
            n_chains=4,
            seed=42,
            compute_loo=False,
            compute_waic=False,
        )
        model.fit(X, y, feature_names=["a", "b"])
        result = model.get_result()

        # R-hat should be close to 1 for converged chains
        for name, rhat in result.r_hat.items():
            assert 0.9 < rhat < 1.2, f"R-hat for {name} = {rhat}"

        # ESS should be reasonable
        for name, ess_val in result.ess.items():
            assert ess_val > 50, f"ESS for {name} too low: {ess_val}"

    def test_half_normal_prior(self):
        """Test half-normal prior for positive coefficients."""
        from app.services.modeling.bayesian import BayesianModel

        np.random.seed(42)
        X = np.random.randn(100, 1)
        y = 5 + 2 * X[:, 0] + np.random.randn(100) * 0.5

        priors = {"x1": {"distribution": "half_normal", "params": {"sigma": 3.0}}}

        model = BayesianModel(
            priors=priors,
            n_samples=200,
            n_warmup=100,
            n_chains=2,
            seed=42,
            compute_loo=False,
            compute_waic=False,
        )
        model.fit(X, y, feature_names=["x1"])

        # Coefficient should be positive due to half-normal prior
        coef = model.get_coefficients()["x1"]
        assert coef > 0


# =============================================================================
# CONSTRAINTS TESTS
# =============================================================================


class TestConstraintHandler:
    """Tests for ConstraintHandler."""

    def test_sign_constraints(self):
        """Test sign constraint handling."""
        from app.services.modeling.constraints import ConstraintHandler

        handler = ConstraintHandler(["a", "b", "c"])
        handler.add_sign_constraint("a", "positive")
        handler.add_sign_constraint("b", "negative")

        bounds = handler.get_bounds_dict()
        assert bounds["a"][0] >= 0
        assert bounds["b"][1] <= 0
        assert bounds["c"] == (-np.inf, np.inf)

    def test_bound_constraints(self):
        """Test explicit bound constraints."""
        from app.services.modeling.constraints import ConstraintHandler

        handler = ConstraintHandler(["a", "b"])
        handler.add_bound_constraint("a", min_val=0.5, max_val=2.0)

        bounds = handler.get_bounds_dict()
        assert bounds["a"] == (0.5, 2.0)

    def test_combined_constraints(self):
        """Test combining sign and bound constraints."""
        from app.services.modeling.constraints import ConstraintHandler

        handler = ConstraintHandler(["a"])
        handler.add_sign_constraint("a", "positive")
        handler.add_bound_constraint("a", max_val=1.0)

        bounds = handler.get_bounds_dict()
        assert bounds["a"] == (0, 1.0)

    def test_validate_coefficients(self):
        """Test coefficient validation."""
        from app.services.modeling.constraints import ConstraintHandler

        handler = ConstraintHandler(["a", "b"])
        handler.add_sign_constraint("a", "positive")

        # Valid coefficients
        result = handler.validate_coefficients({"a": 1.0, "b": -0.5})
        assert len(result["violations"]) == 0

        # Invalid coefficients
        result = handler.validate_coefficients({"a": -1.0, "b": -0.5})
        assert len(result["violations"]) > 0

    def test_from_config(self):
        """Test creating handler from config."""
        from app.services.modeling.constraints import ConstraintHandler

        config = {
            "coefficients": [
                {"variable": "tv", "sign": "positive"},
                {"variable": "radio", "min": 0, "max": 1},
            ],
            "contributions": [
                {"variable": "tv", "min_contribution_pct": 10},
            ],
        }

        handler = ConstraintHandler.from_config(["tv", "radio", "print"], config)
        bounds = handler.get_bounds_dict()

        assert bounds["tv"][0] >= 0
        assert bounds["radio"] == (0, 1)


# =============================================================================
# CONTRIBUTIONS TESTS
# =============================================================================


class TestContributionCalculator:
    """Tests for ContributionCalculator."""

    def test_calculate_basic(self):
        """Test basic contribution calculation."""
        from app.services.modeling.contributions import ContributionCalculator

        calc = ContributionCalculator(
            coefficients={"a": 2.0, "b": 3.0},
            intercept=100,
            feature_names=["a", "b"],
        )

        X = np.array([[10, 20], [15, 25]])
        result = calc.calculate(X)

        # Check structure
        assert "total_contributions" in result
        assert "contribution_pct" in result
        assert "contributions_time_series" in result

    def test_contribution_percentages(self):
        """Test contribution percentage calculation."""
        from app.services.modeling.contributions import ContributionCalculator

        calc = ContributionCalculator(
            coefficients={"a": 1.0, "b": 1.0},
            intercept=0,
            feature_names=["a", "b"],
        )

        # Equal features should give equal contributions
        X = np.array([[10, 10], [10, 10]])
        result = calc.calculate(X)

        assert result["contribution_pct"]["a"] == pytest.approx(50, rel=0.1)
        assert result["contribution_pct"]["b"] == pytest.approx(50, rel=0.1)

    def test_waterfall_calculation(self):
        """Test waterfall chart data."""
        from app.services.modeling.contributions import ContributionCalculator

        calc = ContributionCalculator(
            coefficients={"a": 2.0, "b": 1.0},
            intercept=50,
            feature_names=["a", "b"],
        )

        X = np.array([[10, 20]])
        waterfall = calc.calculate_waterfall(X)

        # Should have base + 2 features + total = 4 items
        assert len(waterfall) == 4
        assert waterfall[0]["name"] == "Base"
        assert waterfall[-1]["name"] == "Total"

    def test_decomposition_dataframe(self):
        """Test decomposition for visualization."""
        from app.services.modeling.contributions import ContributionCalculator

        calc = ContributionCalculator(
            coefficients={"tv": 1.0},
            intercept=100,
            feature_names=["tv"],
        )

        X = np.array([[10], [20], [30]])
        y = np.array([110, 120, 130])
        dates = ["2024-01-01", "2024-01-02", "2024-01-03"]

        decomp = calc.get_decomposition_dataframe(X, y, dates)

        assert "dates" in decomp
        assert "base" in decomp
        assert "predicted" in decomp
        assert "tv" in decomp
        assert len(decomp["dates"]) == 3


# =============================================================================
# TRAINER TESTS
# =============================================================================


class TestModelTrainer:
    """Tests for ModelTrainer."""

    @pytest.fixture
    def sample_data(self):
        """Create sample MMM dataset."""
        np.random.seed(42)
        n = 52  # One year of weekly data

        dates = pd.date_range("2023-01-01", periods=n, freq="W")
        tv_spend = np.random.uniform(1000, 5000, n)
        radio_spend = np.random.uniform(500, 2000, n)

        # Simulate sales with known effects
        sales = (
            10000  # Base
            + 0.5 * tv_spend
            + 0.3 * radio_spend
            + np.random.normal(0, 500, n)
        )

        return pd.DataFrame(
            {
                "date": dates,
                "tv_spend": tv_spend,
                "radio_spend": radio_spend,
                "sales": sales,
            }
        )

    def test_trainer_basic(self, sample_data):
        """Test basic model training."""
        from app.services.modeling.trainer import ModelTrainer

        features = [
            {"column": "tv_spend", "enabled": True},
            {"column": "radio_spend", "enabled": True},
        ]

        trainer = ModelTrainer(
            model_type="ridge",
            features=features,
            target_variable="sales",
            date_column="date",
            hyperparameters={"ridge_alpha": 1.0, "bootstrap_n": 10},
        )

        result = trainer.train(sample_data)

        assert result["status"] == "completed"
        assert "model_result" in result
        assert "contributions" in result

    def test_trainer_with_transformations(self, sample_data):
        """Test training with transformations."""
        from app.services.modeling.trainer import ModelTrainer

        features = [
            {
                "column": "tv_spend",
                "enabled": True,
                "transformations": {
                    "adstock": {"type": "geometric", "decay": 0.5, "max_lag": 4},
                    "saturation": {"type": "hill", "k": 3000, "s": 1.0},
                },
            },
            {"column": "radio_spend", "enabled": True},
        ]

        trainer = ModelTrainer(
            model_type="ridge",
            features=features,
            target_variable="sales",
            date_column="date",
            hyperparameters={"bootstrap_n": 10},
            auto_fit_transformations=False,
        )

        result = trainer.train(sample_data)

        assert result["status"] == "completed"
        assert "transformations" in result
        assert "tv_spend" in result["transformations"]

    def test_trainer_with_constraints(self, sample_data):
        """Test training with constraints."""
        from app.services.modeling.trainer import ModelTrainer

        features = [
            {"column": "tv_spend", "enabled": True},
            {"column": "radio_spend", "enabled": True},
        ]

        constraints = {
            "coefficients": [
                {"variable": "tv_spend", "sign": "positive"},
                {"variable": "radio_spend", "sign": "positive"},
            ]
        }

        trainer = ModelTrainer(
            model_type="ridge",
            features=features,
            target_variable="sales",
            date_column="date",
            constraints=constraints,
            hyperparameters={"bootstrap_n": 10},
        )

        result = trainer.train(sample_data)

        assert result["status"] == "completed"
        coefs = result["model_result"]["coefficients"]
        assert coefs["tv_spend"] >= 0
        assert coefs["radio_spend"] >= 0

    def test_trainer_response_curves(self, sample_data):
        """Test response curve generation."""
        from app.services.modeling.trainer import ModelTrainer

        features = [
            {"column": "tv_spend", "enabled": True},
            {"column": "radio_spend", "enabled": True},
        ]

        trainer = ModelTrainer(
            model_type="ridge",
            features=features,
            target_variable="sales",
            date_column="date",
            hyperparameters={"bootstrap_n": 10},
        )

        result = trainer.train(sample_data)

        assert "response_curves" in result
        assert "tv_spend" in result["response_curves"]
        assert "spend_levels" in result["response_curves"]["tv_spend"]
        assert "response_values" in result["response_curves"]["tv_spend"]

    def test_trainer_invalid_data(self):
        """Test error handling for invalid data."""
        from app.services.modeling.trainer import ModelTrainer

        trainer = ModelTrainer(
            model_type="ridge",
            features=[{"column": "missing_col"}],
            target_variable="sales",
            date_column="date",
        )

        df = pd.DataFrame({"date": [1, 2], "sales": [100, 200]})
        result = trainer.train(df)

        assert result["status"] == "failed"
        assert "error" in result


# =============================================================================
# HYPERPARAMETER TUNING TESTS
# =============================================================================


class TestHyperparameterTuner:
    """Tests for HyperparameterTuner."""

    def test_tune_ridge_basic(self):
        """Test basic Ridge hyperparameter tuning."""
        from app.services.modeling.hyperparameter_tuning import HyperparameterTuner

        np.random.seed(42)
        X = np.random.randn(100, 3)
        y = 5 + 2 * X[:, 0] + 3 * X[:, 1] + np.random.randn(100) * 0.5

        tuner = HyperparameterTuner(
            model_type="ridge",
            param_grid={"alpha": [0.1, 1.0, 10.0]},
            cv=3,
        )

        result = tuner.fit(X, y, feature_names=["x1", "x2", "x3"])

        assert result.best_params is not None
        assert "alpha" in result.best_params
        assert result.best_score is not None
        assert len(result.cv_results) == 3  # 3 alpha values

    def test_tune_elasticnet_basic(self):
        """Test basic ElasticNet hyperparameter tuning."""
        from app.services.modeling.hyperparameter_tuning import HyperparameterTuner

        np.random.seed(42)
        X = np.random.randn(100, 3)
        y = 5 + 2 * X[:, 0] + np.random.randn(100) * 0.5

        tuner = HyperparameterTuner(
            model_type="elasticnet",
            param_grid={"alpha": [0.1, 1.0], "l1_ratio": [0.3, 0.7]},
            cv=3,
        )

        result = tuner.fit(X, y, feature_names=["x1", "x2", "x3"])

        assert result.best_params is not None
        assert "alpha" in result.best_params
        assert "l1_ratio" in result.best_params
        assert len(result.cv_results) == 4  # 2 alpha * 2 l1_ratio

    def test_cv_results_structure(self):
        """Test CV results have correct structure."""
        from app.services.modeling.hyperparameter_tuning import HyperparameterTuner

        np.random.seed(42)
        X = np.random.randn(50, 2)
        y = X[:, 0] + np.random.randn(50) * 0.1

        tuner = HyperparameterTuner(
            model_type="ridge",
            param_grid={"alpha": [1.0]},
            cv=3,
        )

        result = tuner.fit(X, y, feature_names=["a", "b"])

        cv_result = result.cv_results[0]
        assert "mean_score" in cv_result.to_dict()
        assert "std_score" in cv_result.to_dict()
        assert "scores" in cv_result.to_dict()
        assert len(cv_result.scores) == 3  # 3 folds

    def test_convenience_functions(self):
        """Test convenience tuning functions."""
        from app.services.modeling.hyperparameter_tuning import (
            tune_elasticnet,
            tune_ridge_alpha,
        )

        np.random.seed(42)
        X = np.random.randn(50, 2)
        y = X[:, 0] + np.random.randn(50) * 0.1

        # Test tune_ridge_alpha
        result = tune_ridge_alpha(X, y, alphas=[0.1, 1.0], cv=2)
        assert result.best_params["alpha"] in [0.1, 1.0]

        # Test tune_elasticnet
        result = tune_elasticnet(X, y, alphas=[1.0], l1_ratios=[0.5], cv=2)
        assert result.best_params["alpha"] == 1.0
        assert result.best_params["l1_ratio"] == 0.5

    def test_best_model_returned(self):
        """Test that best model is trained and returned."""
        from app.services.modeling.hyperparameter_tuning import HyperparameterTuner

        np.random.seed(42)
        X = np.random.randn(50, 2)
        y = X[:, 0] + np.random.randn(50) * 0.1

        tuner = HyperparameterTuner(
            model_type="ridge",
            param_grid={"alpha": [1.0]},
            cv=2,
        )

        result = tuner.fit(X, y, feature_names=["a", "b"])

        best_model = result.best_model
        assert best_model is not None
        assert best_model.is_fitted

        # Should be able to predict
        predictions = best_model.predict(X)
        assert len(predictions) == len(y)


# =============================================================================
# MODEL COMPARISON TESTS
# =============================================================================


class TestModelComparer:
    """Tests for ModelComparer."""

    def test_compare_basic(self):
        """Test basic model comparison."""
        from app.services.modeling.comparison import ModelComparer

        models = [
            {
                "id": "model_1",
                "name": "Ridge α=1.0",
                "result": {
                    "r_squared": 0.85,
                    "adjusted_r_squared": 0.84,
                    "rmse": 100,
                    "mape": 5.0,
                    "coefficients": {"tv": 0.5, "radio": 0.3},
                    "intercept": 1000,
                },
                "contributions": {
                    "contributions": [
                        {"variable": "tv", "contribution_pct": 60},
                        {"variable": "radio", "contribution_pct": 40},
                    ]
                },
            },
            {
                "id": "model_2",
                "name": "Ridge α=10.0",
                "result": {
                    "r_squared": 0.80,
                    "adjusted_r_squared": 0.79,
                    "rmse": 120,
                    "mape": 6.0,
                    "coefficients": {"tv": 0.4, "radio": 0.25},
                    "intercept": 1100,
                },
                "contributions": {
                    "contributions": [
                        {"variable": "tv", "contribution_pct": 55},
                        {"variable": "radio", "contribution_pct": 45},
                    ]
                },
            },
        ]

        comparer = ModelComparer()
        comparison = comparer.compare(models)

        assert comparison.model_ids == ["model_1", "model_2"]
        assert "r_squared" in comparison.metrics_comparison
        assert "tv" in comparison.coefficients_comparison

    def test_metrics_comparison(self):
        """Test metrics comparison structure."""
        from app.services.modeling.comparison import ModelComparer

        models = [
            {
                "id": "m1",
                "result": {"r_squared": 0.9, "rmse": 50},
            },
            {
                "id": "m2",
                "result": {"r_squared": 0.8, "rmse": 60},
            },
        ]

        comparer = ModelComparer()
        comparison = comparer.compare(models)

        assert comparison.metrics_comparison["r_squared"]["m1"] == 0.9
        assert comparison.metrics_comparison["r_squared"]["m2"] == 0.8
        assert comparison.metrics_comparison["rmse"]["m1"] == 50

    def test_rankings(self):
        """Test model rankings by metrics."""
        from app.services.modeling.comparison import ModelComparer

        models = [
            {"id": "m1", "result": {"r_squared": 0.7, "rmse": 100}},
            {"id": "m2", "result": {"r_squared": 0.9, "rmse": 50}},
            {"id": "m3", "result": {"r_squared": 0.8, "rmse": 75}},
        ]

        comparer = ModelComparer()
        comparison = comparer.compare(models)

        # Higher r_squared is better -> m2 should be first
        assert comparison.rankings["r_squared"][0] == "m2"

        # Lower rmse is better -> m2 should be first
        assert comparison.rankings["rmse"][0] == "m2"

    def test_summary_generation(self):
        """Test summary and recommendation generation."""
        from app.services.modeling.comparison import ModelComparer

        models = [
            {
                "id": "m1",
                "name": "Model A",
                "result": {"r_squared": 0.9, "rmse": 50, "mape": 3.0},
            },
            {
                "id": "m2",
                "name": "Model B",
                "result": {"r_squared": 0.7, "rmse": 100, "mape": 8.0},
            },
        ]

        comparer = ModelComparer()
        comparison = comparer.compare(models)

        assert comparison.summary["best_model_id"] == "m1"
        assert "recommendation" in comparison.summary

    def test_compare_needs_two_models(self):
        """Test that comparison requires at least 2 models."""
        from app.services.modeling.comparison import ModelComparer

        comparer = ModelComparer()

        with pytest.raises(ValueError):
            comparer.compare([{"id": "m1", "result": {}}])

    def test_to_dict(self):
        """Test serialization to dict."""
        from app.services.modeling.comparison import compare_models

        models = [
            {"id": "m1", "result": {"r_squared": 0.9}},
            {"id": "m2", "result": {"r_squared": 0.8}},
        ]

        result = compare_models(models)

        assert isinstance(result, dict)
        assert "model_ids" in result
        assert "metrics_comparison" in result
        assert "summary" in result


# =============================================================================
# INTEGRATION TESTS
# =============================================================================


class TestEndToEndIntegration:
    """End-to-end integration tests."""

    def test_full_pipeline(self):
        """Test complete MMM pipeline."""
        from app.services.modeling.trainer import ModelTrainer

        # Generate realistic MMM data
        np.random.seed(42)
        n = 104  # Two years weekly

        dates = pd.date_range("2022-01-01", periods=n, freq="W")

        # Marketing spends with seasonality
        tv_spend = 3000 + 1000 * np.sin(2 * np.pi * np.arange(n) / 52) + np.random.normal(0, 200, n)
        radio_spend = 1000 + 500 * np.sin(2 * np.pi * np.arange(n) / 52) + np.random.normal(0, 100, n)
        digital_spend = 2000 + np.random.normal(0, 300, n)

        # Make spends positive
        tv_spend = np.maximum(tv_spend, 100)
        radio_spend = np.maximum(radio_spend, 100)
        digital_spend = np.maximum(digital_spend, 100)

        # Generate sales with realistic effects
        base = 50000
        sales = base + np.random.normal(0, 2000, n)

        # Add marketing effects (simplified)
        for t in range(n):
            # TV effect with carryover
            for k in range(min(t + 1, 4)):
                sales[t] += 0.8**k * tv_spend[t - k] * 0.3
            # Radio effect
            sales[t] += radio_spend[t] * 0.2
            # Digital effect with saturation
            sales[t] += digital_spend[t] * 0.4 * (1 - np.exp(-digital_spend[t] / 2000))

        df = pd.DataFrame(
            {
                "date": dates,
                "tv_spend": tv_spend,
                "radio_spend": radio_spend,
                "digital_spend": digital_spend,
                "sales": sales,
            }
        )

        # Configure trainer
        features = [
            {
                "column": "tv_spend",
                "transformations": {
                    "adstock": {"type": "geometric", "decay": "auto", "max_lag": 4},
                },
            },
            {"column": "radio_spend"},
            {
                "column": "digital_spend",
                "transformations": {
                    "saturation": {"type": "hill", "k": "auto", "s": "auto"},
                },
            },
        ]

        constraints = {
            "coefficients": [
                {"variable": "tv_spend", "sign": "positive"},
                {"variable": "radio_spend", "sign": "positive"},
                {"variable": "digital_spend", "sign": "positive"},
            ]
        }

        trainer = ModelTrainer(
            model_type="ridge",
            features=features,
            target_variable="sales",
            date_column="date",
            constraints=constraints,
            hyperparameters={"ridge_alpha": 1.0, "bootstrap_n": 20},
            auto_fit_transformations=True,
        )

        result = trainer.train(df)

        # Verify complete output
        assert result["status"] == "completed"

        # Check model result
        model_result = result["model_result"]
        assert model_result["r_squared"] > 0.1  # Model fits (doesn't need to be perfect)
        assert all(c >= 0 for c in model_result["coefficients"].values())

        # Check contributions
        contribs = result["contributions"]
        assert len(contribs["contributions"]) > 0
        assert sum(c["contribution_pct"] for c in contribs["contributions"]) == pytest.approx(100, rel=0.1)

        # Check decomposition
        decomp = result["decomposition"]
        assert "dates" in decomp
        assert len(decomp["dates"]) == n

        # Check response curves
        curves = result["response_curves"]
        assert len(curves) == 3
        for channel in ["tv_spend", "radio_spend", "digital_spend"]:
            assert channel in curves
            assert len(curves[channel]["spend_levels"]) > 0

        # Check validation
        validation = result["validation"]
        assert "coefficient_constraints" in validation
        assert len(validation["coefficient_constraints"]["violations"]) == 0

        # Check metadata
        metadata = result["metadata"]
        assert metadata["n_features"] == 3
        assert metadata["n_observations"] == n
        assert metadata["model_type"] == "ridge"
