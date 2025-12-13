"""Pydantic schemas for API request/response validation."""

from app.schemas.constraints import (
    CoefficientConstraint,
    ConstraintsConfig,
    ContributionConstraint,
    GroupContributionConstraint,
)
from app.schemas.dataset import (
    ColumnInfo,
    DatasetCreate,
    DatasetPreview,
    DatasetRead,
    DatasetStatus,
)
from app.schemas.model_config import (
    FeatureConfig,
    GranularityConfig,
    ModelConfigCreate,
    ModelConfigRead,
    ModelType,
    TransformationConfig,
)
from app.schemas.priors import PriorConfig, PriorDistribution
from app.schemas.project import ProjectCreate, ProjectList, ProjectRead, ProjectUpdate
from app.schemas.project_member import (
    ProjectMemberCreate,
    ProjectMemberListResponse,
    ProjectMemberResponse,
    ProjectMemberUpdate,
)
from app.schemas.responses import (
    CoefficientResult,
    ContributionResult,
    ModelMetrics,
    ModelResultRead,
)
from app.schemas.user import Token, UserCreate, UserLogin, UserRead, UserUpdate
from app.schemas.variable_group import (
    VariableGroupCreate,
    VariableGroupList,
    VariableGroupRead,
    VariableGroupUpdate,
)

__all__ = [
    # User
    "UserCreate",
    "UserRead",
    "UserUpdate",
    "UserLogin",
    "Token",
    # Project
    "ProjectCreate",
    "ProjectRead",
    "ProjectUpdate",
    "ProjectList",
    # Dataset
    "DatasetCreate",
    "DatasetRead",
    "DatasetPreview",
    "ColumnInfo",
    "DatasetStatus",
    # Model Config
    "ModelType",
    "ModelConfigCreate",
    "ModelConfigRead",
    "FeatureConfig",
    "TransformationConfig",
    "GranularityConfig",
    # Constraints
    "CoefficientConstraint",
    "ContributionConstraint",
    "GroupContributionConstraint",
    "ConstraintsConfig",
    # Priors
    "PriorConfig",
    "PriorDistribution",
    # Responses
    "ModelResultRead",
    "ContributionResult",
    "CoefficientResult",
    "ModelMetrics",
    # Project Members
    "ProjectMemberCreate",
    "ProjectMemberUpdate",
    "ProjectMemberResponse",
    "ProjectMemberListResponse",
    # Variable Groups
    "VariableGroupCreate",
    "VariableGroupRead",
    "VariableGroupUpdate",
    "VariableGroupList",
]
