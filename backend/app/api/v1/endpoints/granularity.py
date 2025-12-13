"""Multi-granularity modeling API endpoints."""

from pathlib import Path
from typing import Any
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.repositories.dataset import DatasetRepository
from app.repositories.project import ProjectRepository
from app.services.granularity.aggregation import (
    AggregationRule,
    GranularityManager,
    GranularitySpec,
    MetricDefinition,
)
from app.services.granularity.dimensions import (
    Dimension,
    DimensionLevel,
    DimensionRegistry,
)
from app.services.granularity.reports import ReportGenerator, ReportSpec

router = APIRouter(prefix="/projects/{project_id}", tags=["Granularity"])


# --- Pydantic Models ---


class DimensionLevelSchema(BaseModel):
    """Schema for dimension level."""

    name: str
    column: str | None = None
    display_name: str
    order: int = 0


class DimensionSchema(BaseModel):
    """Schema for dimension."""

    name: str
    display_name: str
    levels: list[DimensionLevelSchema]


class MetricSchema(BaseModel):
    """Schema for metric definition."""

    name: str
    column: str
    metric_type: str = "additive"
    aggregation_method: str = "sum"
    weight_column: str | None = None
    derived_formula: str | None = None


class GranularitySpecSchema(BaseModel):
    """Schema for granularity specification."""

    name: str
    dimensions: dict[str, str]
    filters: dict[str, list[Any]] = Field(default_factory=dict)


class ReportSpecSchema(BaseModel):
    """Schema for report specification."""

    name: str
    granularity: GranularitySpecSchema
    model_type: str = "ridge"
    group_by: str | None = None
    features: list[str]
    target: str
    constraints: dict[str, Any] | None = None
    priors: dict[str, Any] | None = None
    hyperparameters: dict[str, Any] = Field(default_factory=dict)
    parent_report: str | None = None
    inherit_constraints: bool = False
    inherit_priors: bool = False
    prior_strength: float = 0.5
    override_constraints: dict[str, Any] | None = None


class AggregationPreviewRequest(BaseModel):
    """Request for aggregation preview."""

    granularity: GranularitySpecSchema
    dimensions: list[DimensionSchema]
    metrics: list[MetricSchema]
    sample_size: int = 20


# --- Helper Functions ---


async def get_dataset_df(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> pd.DataFrame:
    """Load dataset as DataFrame with authorization check."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)

    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not await project_repo.is_owner(project, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset not found")

    file_path = Path(settings.UPLOAD_DIR) / dataset.file_path
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Dataset file not found")

    if file_path.suffix.lower() == ".csv":
        return pd.read_csv(file_path)
    elif file_path.suffix.lower() in [".xlsx", ".xls"]:
        return pd.read_excel(file_path)
    else:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported format")


def schema_to_dimensions(schemas: list[DimensionSchema]) -> list[Dimension]:
    """Convert schema to Dimension objects."""
    dimensions = []
    for schema in schemas:
        levels = [
            DimensionLevel(
                name=l.name,
                column=l.column,
                display_name=l.display_name,
                order=l.order,
            )
            for l in schema.levels
        ]
        dimensions.append(
            Dimension(
                name=schema.name,
                display_name=schema.display_name,
                levels=levels,
            )
        )
    return dimensions


def schema_to_metrics(schemas: list[MetricSchema]) -> list[MetricDefinition]:
    """Convert schema to MetricDefinition objects."""
    return [
        MetricDefinition(
            name=s.name,
            column=s.column,
            metric_type=s.metric_type,
            aggregation=AggregationRule(
                column=s.column,
                method=s.aggregation_method,
                weight_column=s.weight_column,
            ),
            derived_formula=s.derived_formula,
        )
        for s in schemas
    ]


# --- Endpoints ---


@router.get("/dimensions/defaults")
async def get_default_dimensions(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get default dimension configurations.

    Returns pre-configured dimensions for time, geography, and channel.
    """
    # Verify project access
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)

    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    if not await project_repo.is_owner(project, current_user.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    registry = DimensionRegistry()

    return {"dimensions": [dim.to_dict() for dim in registry.list_all()]}


@router.get("/datasets/{dataset_id}/dimensions/detect")
async def detect_dimensions(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Auto-detect dimension mappings from dataset columns.

    Analyzes column names to suggest dimension configurations.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    registry = DimensionRegistry()
    suggestions = registry.auto_detect_dimensions(df)

    return {
        "columns": df.columns.tolist(),
        "suggestions": suggestions,
    }


@router.post("/datasets/{dataset_id}/granularity/validate")
async def validate_granularity(
    project_id: UUID,
    dataset_id: UUID,
    request: AggregationPreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Validate if a granularity specification is achievable.

    Checks that required columns exist and estimates result size.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    dimensions = schema_to_dimensions(request.dimensions)
    metrics = schema_to_metrics(request.metrics)

    manager = GranularityManager(df, dimensions, metrics)

    granularity = GranularitySpec(
        name=request.granularity.name,
        dimensions=request.granularity.dimensions,
        filters=request.granularity.filters,
    )

    return manager.validate_granularity(granularity)


@router.post("/datasets/{dataset_id}/granularity/preview")
async def preview_aggregation(
    project_id: UUID,
    dataset_id: UUID,
    request: AggregationPreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Preview data aggregated to specified granularity.

    Returns sample rows at the target aggregation level.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    dimensions = schema_to_dimensions(request.dimensions)
    metrics = schema_to_metrics(request.metrics)

    manager = GranularityManager(df, dimensions, metrics)

    granularity = GranularitySpec(
        name=request.granularity.name,
        dimensions=request.granularity.dimensions,
        filters=request.granularity.filters,
    )

    return manager.preview_aggregation(granularity, sample_size=request.sample_size)


@router.post("/datasets/{dataset_id}/granularity/aggregate")
async def aggregate_data(
    project_id: UUID,
    dataset_id: UUID,
    request: AggregationPreviewRequest,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Fully aggregate data to specified granularity.

    Returns all aggregated rows (limited to 10000).
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    dimensions = schema_to_dimensions(request.dimensions)
    metrics = schema_to_metrics(request.metrics)

    manager = GranularityManager(df, dimensions, metrics)

    granularity = GranularitySpec(
        name=request.granularity.name,
        dimensions=request.granularity.dimensions,
        filters=request.granularity.filters,
    )

    result_df = manager.aggregate(granularity)

    # Limit output
    if len(result_df) > 10000:
        return {
            "warning": f"Result truncated from {len(result_df)} to 10000 rows",
            "total_rows": len(result_df),
            "columns": result_df.columns.tolist(),
            "data": result_df.head(10000).to_dict(orient="records"),
        }

    return {
        "total_rows": len(result_df),
        "columns": result_df.columns.tolist(),
        "data": result_df.to_dict(orient="records"),
    }


@router.get("/datasets/{dataset_id}/dimensions/{dimension}/values")
async def get_dimension_values(
    project_id: UUID,
    dataset_id: UUID,
    dimension: str,
    current_user: CurrentUser,
    db: DbSession,
    level: str = Query(..., description="Level name within dimension"),
    parent_column: str | None = Query(None, description="Parent column for filtering"),
    parent_value: str | None = Query(None, description="Parent value to filter by"),
) -> dict:
    """
    Get unique values for a dimension level.

    Optionally filter by parent dimension value for hierarchical navigation.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    registry = DimensionRegistry()
    dim = registry.get(dimension)

    if dim is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Dimension not found: {dimension}",
        )

    parent_filter = None
    if parent_column and parent_value:
        parent_filter = {parent_column: parent_value}

    try:
        values = registry.get_unique_values_at_level(df, dimension, level, parent_filter)
        return {
            "dimension": dimension,
            "level": level,
            "values": sorted([str(v) for v in values]),
            "count": len(values),
        }
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.post("/reports/generate-configs")
async def generate_report_configs(
    project_id: UUID,
    dataset_id: UUID,
    report: ReportSpecSchema,
    dimensions: list[DimensionSchema],
    metrics: list[MetricSchema],
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Generate model configurations for a report specification.

    If group_by is specified, returns one config per group value.
    This endpoint helps preview what models will be created.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    dim_objs = schema_to_dimensions(dimensions)
    metric_objs = schema_to_metrics(metrics)

    manager = GranularityManager(df, dim_objs, metric_objs)

    report_spec = ReportSpec(
        name=report.name,
        granularity=GranularitySpec(
            name=report.granularity.name,
            dimensions=report.granularity.dimensions,
            filters=report.granularity.filters,
        ),
        model_type=report.model_type,
        group_by=report.group_by,
        features=report.features,
        target=report.target,
        constraints=report.constraints,
        priors=report.priors,
        hyperparameters=report.hyperparameters,
        parent_report=report.parent_report,
        inherit_constraints=report.inherit_constraints,
        inherit_priors=report.inherit_priors,
        prior_strength=report.prior_strength,
        override_constraints=report.override_constraints,
    )

    generator = ReportGenerator(manager, {report.name: report_spec})
    configs = generator.generate_model_configs(report.name)

    return {
        "report_name": report.name,
        "n_models": len(configs),
        "group_by": report.group_by,
        "configs": [
            {
                "id": str(config.id),
                "group_value": config.group_value,
                "model_type": config.model_type,
                "features": config.features,
                "target": config.target,
                "n_rows": len(data),
                "constraints": config.constraints,
                "priors": config.priors,
            }
            for config, data in configs
        ],
    }


@router.get("/granularity/options")
async def get_granularity_options(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get available granularity levels based on dataset columns.

    Shows which dimension levels are available and their unique value counts.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    registry = DimensionRegistry()

    options = []
    for dim in registry.list_all():
        dim_options = {
            "dimension": dim.name,
            "display_name": dim.display_name,
            "levels": [],
        }

        for level in dim.levels:
            level_info = {
                "name": level.name,
                "display_name": level.display_name,
                "column": level.column,
                "available": level.column is None or level.column in df.columns,
            }

            if level.column and level.column in df.columns:
                level_info["unique_values"] = int(df[level.column].nunique())

            dim_options["levels"].append(level_info)

        options.append(dim_options)

    return {"options": options}
