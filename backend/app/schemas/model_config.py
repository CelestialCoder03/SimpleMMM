"""Model configuration schemas."""

from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import Field, field_validator

from app.schemas.base import BaseSchema, TimestampSchema, UUIDSchema


class ModelType(str, Enum):
    """Supported model types."""

    OLS = "ols"
    RIDGE = "ridge"
    ELASTICNET = "elasticnet"
    BAYESIAN = "bayesian"


class ModelStatus(str, Enum):
    """Model training status."""

    PENDING = "pending"
    TRAINING = "training"
    COMPLETED = "completed"
    FAILED = "failed"


class AdstockType(str, Enum):
    """Adstock transformation types."""

    GEOMETRIC = "geometric"
    WEIBULL = "weibull"


class SaturationType(str, Enum):
    """Saturation transformation types."""

    HILL = "hill"
    LOGISTIC = "logistic"


class HierarchyType(str, Enum):
    """Hierarchical modeling types."""

    NO_POOLING = "no_pooling"
    COMPLETE_POOLING = "complete_pooling"
    PARTIAL_POOLING = "partial_pooling"


class AdstockConfig(BaseSchema):
    """Adstock transformation configuration."""

    type: AdstockType = AdstockType.GEOMETRIC
    decay: float | str = Field(
        default=0.5,
        description="Decay rate (0-1) or 'auto' to fit from data",
    )
    max_lag: int = Field(default=8, ge=1, le=52)
    enabled: bool = Field(default=False, description="Whether adstock is enabled")

    @field_validator("decay")
    @classmethod
    def validate_decay(cls, v):
        if isinstance(v, str) and v != "auto":
            raise ValueError("decay must be a float or 'auto'")
        if isinstance(v, (int, float)) and not 0 <= v <= 1:
            raise ValueError("decay must be between 0 and 1")
        return v


class SaturationConfig(BaseSchema):
    """Saturation transformation configuration."""

    type: SaturationType = SaturationType.HILL
    k: float | str = Field(
        default="auto",
        description="Half-saturation point or 'auto'",
    )
    s: float | str = Field(
        default="auto",
        description="Slope parameter or 'auto'",
    )
    enabled: bool = Field(default=False, description="Whether saturation is enabled")


class TransformationConfig(BaseSchema):
    """Feature transformation configuration."""

    adstock: AdstockConfig | None = None
    saturation: SaturationConfig | None = None


class FeatureConfig(BaseSchema):
    """Single feature configuration."""

    column: str = Field(..., min_length=1)
    transformations: TransformationConfig | None = None
    enabled: bool = True


class GranularityDimension(BaseSchema):
    """Granularity dimension configuration."""

    column: str
    type: str = "categorical"


class VaryingCoefficients(BaseSchema):
    """Varying coefficients by dimension."""

    by_region: list[str] = Field(default_factory=list)
    by_channel: list[str] = Field(default_factory=list)
    fixed: list[str] = Field(default_factory=list)


class GranularityConfig(BaseSchema):
    """Multi-granularity configuration."""

    level: str = Field(
        default="national",
        description="Granularity level: national, regional, city, channel",
    )
    dimensions: list[GranularityDimension] = Field(default_factory=list)
    hierarchy_type: HierarchyType = HierarchyType.PARTIAL_POOLING
    varying_coefficients: VaryingCoefficients | None = None


class HyperparametersConfig(BaseSchema):
    """Model hyperparameters."""

    # Ridge/ElasticNet
    ridge_alpha: float = Field(default=1.0, ge=0)
    elasticnet_alpha: float = Field(default=1.0, ge=0)
    elasticnet_l1_ratio: float = Field(default=0.5, ge=0, le=1)

    # Bayesian MCMC
    mcmc_samples: int = Field(default=2000, ge=100)
    mcmc_chains: int = Field(default=4, ge=1)
    mcmc_tune: int = Field(default=1000, ge=100)
    mcmc_target_accept: float = Field(default=0.9, ge=0.5, le=0.99)


class SeasonalityMethod(str, Enum):
    """Seasonality generation method."""

    CALENDAR = "calendar"
    FOURIER = "fourier"
    BOTH = "both"


class CalendarFeaturesConfig(BaseSchema):
    """Calendar-based seasonality features configuration."""

    include_weekend: bool = Field(default=True, description="Add is_weekend binary feature")
    include_month: bool = Field(default=True, description="Add month dummy variables")
    include_quarter: bool = Field(default=False, description="Add quarter dummy variables")
    include_day_of_week: bool = Field(default=False, description="Add day of week dummy variables")


class FourierFeaturesConfig(BaseSchema):
    """Fourier-based seasonality features configuration."""

    periods: list[int] = Field(default=[7, 30, 365], description="Periods to model (days)")
    n_terms: int = Field(default=3, ge=1, le=10, description="Number of Fourier terms per period")


class SeasonalityConfig(BaseSchema):
    """Seasonality configuration for automatic feature generation."""

    enabled: bool = Field(default=False, description="Enable seasonality features")
    method: SeasonalityMethod = Field(default=SeasonalityMethod.CALENDAR)
    calendar: CalendarFeaturesConfig = Field(default_factory=CalendarFeaturesConfig)
    fourier: FourierFeaturesConfig = Field(default_factory=FourierFeaturesConfig)


class ModelConfigCreate(BaseSchema):
    """Schema for creating a model configuration."""

    name: str = Field(..., min_length=1, max_length=255)
    dataset_id: UUID
    model_type: ModelType = ModelType.RIDGE

    # Target and date
    target_variable: str
    date_column: str

    # Features
    features: list[FeatureConfig]

    # Granularity
    granularity: GranularityConfig | None = None

    # Constraints (imported separately)
    constraints: dict[str, Any] | None = None

    # Priors (for Bayesian)
    priors: dict[str, Any] | None = None

    # Hyperparameters
    hyperparameters: HyperparametersConfig | None = None

    # Seasonality (auto-generated features)
    seasonality: SeasonalityConfig | None = None


class ModelConfigUpdate(BaseSchema):
    """Schema for updating a model configuration (partial update)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    model_type: ModelType | None = None
    target_variable: str | None = None
    date_column: str | None = None
    features: list[FeatureConfig] | None = None
    granularity: GranularityConfig | None = None
    constraints: dict[str, Any] | None = None
    priors: dict[str, Any] | None = None
    hyperparameters: HyperparametersConfig | None = None
    seasonality: SeasonalityConfig | None = None


class ModelConfigRead(UUIDSchema, TimestampSchema):
    """Schema for reading a model configuration."""

    name: str
    project_id: UUID
    dataset_id: UUID
    model_type: ModelType
    status: ModelStatus
    target_variable: str
    date_column: str
    features: list[FeatureConfig]
    granularity: GranularityConfig | None
    constraints: dict[str, Any] | None
    priors: dict[str, Any] | None
    hyperparameters: HyperparametersConfig | None
    seasonality: SeasonalityConfig | None = None
    task_id: str | None = None
    error_message: str | None = None
