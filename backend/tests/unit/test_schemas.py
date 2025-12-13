"""Tests for Pydantic schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.constraints import (
    CoefficientConstraint,
    ContributionConstraint,
    GroupContributionConstraint,
    SignConstraint,
)
from app.schemas.dataset import ColumnType, DatasetStatus
from app.schemas.model_config import (
    AdstockConfig,
    FeatureConfig,
    GranularityConfig,
    HierarchyType,
    ModelType,
)
from app.schemas.priors import PriorConfig, PriorDistribution
from app.schemas.project import ProjectCreate, ProjectUpdate
from app.schemas.responses import CoefficientResult, ModelMetrics
from app.schemas.user import UserCreate


# User schemas
def test_user_create_valid():
    """Test valid user creation."""
    user = UserCreate(
        email="test@example.com",
        full_name="Test User",
        password="password123",
    )
    assert user.email == "test@example.com"
    assert user.full_name == "Test User"


def test_user_create_invalid_email():
    """Test user creation with invalid email."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="invalid-email",
            full_name="Test User",
            password="password123",
        )


def test_user_create_short_password():
    """Test user creation with short password."""
    with pytest.raises(ValidationError):
        UserCreate(
            email="test@example.com",
            full_name="Test User",
            password="short",
        )


# Project schemas
def test_project_create_valid():
    """Test valid project creation."""
    project = ProjectCreate(
        name="Test Project",
        description="A test project",
    )
    assert project.name == "Test Project"


def test_project_update_partial():
    """Test partial project update."""
    update = ProjectUpdate(name="New Name")
    assert update.name == "New Name"
    assert update.description is None


# Model config schemas
def test_model_type_enum():
    """Test ModelType enum values."""
    assert ModelType.OLS.value == "ols"
    assert ModelType.RIDGE.value == "ridge"
    assert ModelType.BAYESIAN.value == "bayesian"


def test_feature_config():
    """Test feature configuration."""
    feature = FeatureConfig(
        column="tv_spend",
        transformations=None,
        enabled=True,
    )
    assert feature.column == "tv_spend"


def test_adstock_config_valid():
    """Test valid adstock configuration."""
    adstock = AdstockConfig(decay=0.7, max_lag=8)
    assert adstock.decay == 0.7


def test_adstock_config_auto():
    """Test adstock with auto decay."""
    adstock = AdstockConfig(decay="auto")
    assert adstock.decay == "auto"


def test_adstock_config_invalid_decay():
    """Test adstock with invalid decay value."""
    with pytest.raises(ValidationError):
        AdstockConfig(decay=1.5)  # > 1


def test_granularity_config():
    """Test granularity configuration."""
    config = GranularityConfig(
        level="regional",
        hierarchy_type=HierarchyType.PARTIAL_POOLING,
    )
    assert config.level == "regional"


# Constraint schemas
def test_coefficient_constraint_sign():
    """Test coefficient constraint with sign."""
    constraint = CoefficientConstraint(
        variable="tv_spend",
        sign=SignConstraint.POSITIVE,
    )
    assert constraint.sign == SignConstraint.POSITIVE


def test_coefficient_constraint_bounds():
    """Test coefficient constraint with bounds."""
    constraint = CoefficientConstraint(
        variable="price",
        min=-1.0,
        max=0.0,
    )
    assert constraint.min == -1.0
    assert constraint.max == 0.0


def test_coefficient_constraint_invalid_bounds():
    """Test coefficient constraint with invalid bounds."""
    with pytest.raises(ValidationError):
        CoefficientConstraint(
            variable="test",
            min=1.0,
            max=0.5,  # min > max
        )


def test_contribution_constraint():
    """Test contribution constraint."""
    constraint = ContributionConstraint(
        variable="instagram_impressions",
        max_contribution_pct=1.5,
    )
    assert constraint.max_contribution_pct == 1.5


def test_group_contribution_constraint():
    """Test group contribution constraint."""
    constraint = GroupContributionConstraint(
        name="media_atl",
        variables=["tv_spend", "radio_spend", "print_spend"],
        max_contribution_pct=10.0,
        min_contribution_pct=2.0,
    )
    assert len(constraint.variables) == 3
    assert constraint.max_contribution_pct == 10.0


# Prior schemas
def test_prior_config_normal():
    """Test normal prior configuration."""
    prior = PriorConfig(
        variable="tv_spend",
        distribution=PriorDistribution.NORMAL,
        params={"mu": 0.3, "sigma": 0.1},
    )
    assert prior.distribution == PriorDistribution.NORMAL


def test_prior_config_truncated():
    """Test truncated normal prior."""
    prior = PriorConfig(
        variable="beta",
        distribution=PriorDistribution.TRUNCATED_NORMAL,
        params={"mu": 0.5, "sigma": 0.2, "lower": 0, "upper": 1},
    )
    assert prior.params["lower"] == 0


# Response schemas
def test_model_metrics():
    """Test model metrics schema."""
    metrics = ModelMetrics(
        r_squared=0.89,
        adjusted_r_squared=0.87,
        rmse=25000,
        mape=5.2,
    )
    assert metrics.r_squared == 0.89


def test_coefficient_result():
    """Test coefficient result schema."""
    result = CoefficientResult(
        variable="tv_spend",
        estimate=0.32,
        std_error=0.05,
        ci_lower=0.22,
        ci_upper=0.42,
        p_value=0.001,
        is_significant=True,
    )
    assert result.estimate == 0.32
    assert result.is_significant is True


def test_dataset_status_enum():
    """Test DatasetStatus enum."""
    assert DatasetStatus.PENDING.value == "pending"
    assert DatasetStatus.READY.value == "ready"


def test_column_type_enum():
    """Test ColumnType enum."""
    assert ColumnType.NUMERIC.value == "numeric"
    assert ColumnType.DATETIME.value == "datetime"
