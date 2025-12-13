"""Modeling services package."""

from app.services.modeling.base import BaseModel, ModelResult
from app.services.modeling.bayesian import BayesianModel
from app.services.modeling.comparison import (
    ModelComparer,
    ModelComparison,
    compare_models,
)
from app.services.modeling.constraints import ConstraintHandler
from app.services.modeling.contributions import ContributionCalculator
from app.services.modeling.elasticnet import ElasticNetModel
from app.services.modeling.hyperparameter_tuning import (
    CVResult,
    HyperparameterTuner,
    TuningResult,
    tune_elasticnet,
    tune_ridge_alpha,
)
from app.services.modeling.linear import LinearModel
from app.services.modeling.ridge import RidgeModel
from app.services.modeling.trainer import ModelTrainer
from app.services.modeling.transformations import (
    AdstockTransform,
    FeatureTransformer,
    SaturationTransform,
)

__all__ = [
    "BaseModel",
    "ModelResult",
    "AdstockTransform",
    "SaturationTransform",
    "FeatureTransformer",
    "LinearModel",
    "RidgeModel",
    "ElasticNetModel",
    "BayesianModel",
    "ConstraintHandler",
    "ContributionCalculator",
    "ModelTrainer",
    "HyperparameterTuner",
    "TuningResult",
    "CVResult",
    "tune_ridge_alpha",
    "tune_elasticnet",
    "ModelComparer",
    "ModelComparison",
    "compare_models",
]
