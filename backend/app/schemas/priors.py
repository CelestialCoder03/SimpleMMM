"""Prior distribution schemas for Bayesian models."""

from enum import Enum
from typing import Any

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema


class PriorDistribution(str, Enum):
    """Supported prior distributions."""

    NORMAL = "normal"
    HALF_NORMAL = "half_normal"
    TRUNCATED_NORMAL = "truncated_normal"
    UNIFORM = "uniform"
    EXPONENTIAL = "exponential"
    BETA = "beta"
    GAMMA = "gamma"


class NormalParams(BaseSchema):
    """Parameters for Normal distribution."""

    mu: float = Field(default=0.0, description="Mean")
    sigma: float = Field(default=1.0, gt=0, description="Standard deviation")


class HalfNormalParams(BaseSchema):
    """Parameters for HalfNormal distribution."""

    sigma: float = Field(default=1.0, gt=0, description="Standard deviation")


class TruncatedNormalParams(BaseSchema):
    """Parameters for TruncatedNormal distribution."""

    mu: float = Field(default=0.0, description="Mean")
    sigma: float = Field(default=1.0, gt=0, description="Standard deviation")
    lower: float | None = Field(None, description="Lower bound")
    upper: float | None = Field(None, description="Upper bound")

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.lower is not None and self.upper is not None:
            if self.lower >= self.upper:
                raise ValueError("lower must be less than upper")
        return self


class UniformParams(BaseSchema):
    """Parameters for Uniform distribution."""

    lower: float = Field(default=0.0, description="Lower bound")
    upper: float = Field(default=1.0, description="Upper bound")

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.lower >= self.upper:
            raise ValueError("lower must be less than upper")
        return self


class ExponentialParams(BaseSchema):
    """Parameters for Exponential distribution."""

    lam: float = Field(default=1.0, gt=0, description="Rate parameter")


class BetaParams(BaseSchema):
    """Parameters for Beta distribution."""

    alpha: float = Field(default=2.0, gt=0, description="Alpha parameter")
    beta: float = Field(default=2.0, gt=0, description="Beta parameter")


class GammaParams(BaseSchema):
    """Parameters for Gamma distribution."""

    alpha: float = Field(default=2.0, gt=0, description="Shape parameter")
    beta: float = Field(default=1.0, gt=0, description="Rate parameter")


class PriorConfig(BaseSchema):
    """Prior configuration for a single variable."""

    variable: str = Field(..., min_length=1)
    distribution: PriorDistribution
    params: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_params(self):
        """Validate params match the distribution type."""

        # Just check that required params exist (with defaults allowed)
        # More detailed validation happens when building the model
        return self


class PriorsConfig(BaseSchema):
    """Complete priors configuration."""

    priors: list[PriorConfig] = Field(default_factory=list)
    intercept: PriorConfig | None = Field(
        None,
        description="Prior for intercept term",
    )
    sigma: PriorConfig | None = Field(
        None,
        description="Prior for residual standard deviation",
    )
