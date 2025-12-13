"""Constraint schemas for model configuration."""

from enum import Enum

from pydantic import Field, model_validator

from app.schemas.base import BaseSchema


class SignConstraint(str, Enum):
    """Sign constraint types."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class CoefficientConstraint(BaseSchema):
    """Coefficient constraint for a single variable."""

    variable: str = Field(..., min_length=1)
    sign: SignConstraint | None = None
    min: float | None = Field(None, description="Minimum coefficient value")
    max: float | None = Field(None, description="Maximum coefficient value")

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.min is not None and self.max is not None:
            if self.min > self.max:
                raise ValueError("min must be less than or equal to max")
        if self.sign == SignConstraint.POSITIVE and self.max is not None and self.max < 0:
            raise ValueError("max must be >= 0 for positive constraint")
        if self.sign == SignConstraint.NEGATIVE and self.min is not None and self.min > 0:
            raise ValueError("min must be <= 0 for negative constraint")
        return self


class ContributionConstraint(BaseSchema):
    """Contribution constraint for a single variable."""

    variable: str = Field(..., min_length=1)
    min_contribution_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Minimum contribution percentage",
    )
    max_contribution_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Maximum contribution percentage",
    )

    @model_validator(mode="after")
    def validate_contribution_bounds(self):
        if self.min_contribution_pct is not None and self.max_contribution_pct is not None:
            if self.min_contribution_pct > self.max_contribution_pct:
                raise ValueError("min_contribution_pct must be less than or equal to max_contribution_pct")
        return self


class GroupContributionConstraint(BaseSchema):
    """Contribution constraint for a group of variables."""

    name: str = Field(..., min_length=1, description="Group name, e.g., 'media_atl'")
    variables: list[str] = Field(..., min_length=1)
    min_contribution_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Minimum combined contribution percentage",
    )
    max_contribution_pct: float | None = Field(
        None,
        ge=0,
        le=100,
        description="Maximum combined contribution percentage",
    )

    @model_validator(mode="after")
    def validate_group_bounds(self):
        if self.min_contribution_pct is not None and self.max_contribution_pct is not None:
            if self.min_contribution_pct > self.max_contribution_pct:
                raise ValueError("min_contribution_pct must be less than or equal to max_contribution_pct")
        return self


class RelationshipConstraint(BaseSchema):
    """Relationship constraint between coefficients."""

    type: str = Field(
        ...,
        description="Constraint type: 'greater_than', 'less_than', 'equal'",
    )
    left: str = Field(..., description="Left variable name")
    right: str = Field(..., description="Right variable name")
    multiplier: float = Field(
        default=1.0,
        description="Multiplier for comparison, e.g., left >= multiplier * right",
    )


class ConstraintsConfig(BaseSchema):
    """Complete constraints configuration."""

    coefficients: list[CoefficientConstraint] = Field(default_factory=list)
    contributions: list[ContributionConstraint] = Field(default_factory=list)
    group_contributions: list[GroupContributionConstraint] = Field(default_factory=list)
    relationships: list[RelationshipConstraint] = Field(default_factory=list)
