"""Data exploration API endpoints."""

from pathlib import Path
from typing import Literal
from uuid import UUID

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, status

from app.core.config import settings
from app.core.deps import CurrentUser, DbSession
from app.repositories.dataset import DatasetRepository
from app.repositories.project import ProjectRepository
from app.services.exploration.analyzer import DataExplorer

router = APIRouter(prefix="/projects/{project_id}/datasets/{dataset_id}/explore", tags=["Exploration"])


async def verify_project_access(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Verify user has access to project."""
    project_repo = ProjectRepository(db)
    project = await project_repo.get_by_id(project_id)

    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    if not await project_repo.is_owner(project, current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this project",
        )


async def get_dataset_df(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> pd.DataFrame:
    """Load dataset as DataFrame with authorization check."""
    await verify_project_access(project_id, current_user, db)

    # Get dataset
    dataset_repo = DatasetRepository(db)
    dataset = await dataset_repo.get_by_id(dataset_id)

    if dataset is None or dataset.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset not found",
        )

    # Load file - handle both absolute and relative paths
    stored_path = Path(dataset.file_path)
    if stored_path.is_absolute():
        file_path = stored_path
    else:
        file_path = Path(settings.UPLOAD_DIR) / dataset.file_path

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dataset file not found",
        )

    # Read based on extension
    if file_path.suffix.lower() == ".csv":
        df = pd.read_csv(file_path)
    elif file_path.suffix.lower() in [".xlsx", ".xls"]:
        df = pd.read_excel(file_path)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format: {file_path.suffix}",
        )

    return df


@router.get("/summary")
async def get_summary(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get comprehensive summary statistics for the dataset.

    Returns:
        - Overall dataset stats (rows, columns, memory)
        - Per-column statistics (type-specific)
        - Missing value summary
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)
    explorer = DataExplorer(df)
    return explorer.get_summary()


@router.get("/distribution/{column}")
async def get_distribution(
    project_id: UUID,
    dataset_id: UUID,
    column: str,
    current_user: CurrentUser,
    db: DbSession,
    n_bins: int = Query(30, ge=5, le=100, description="Number of histogram bins"),
    include_kde: bool = Query(True, description="Include kernel density estimation"),
) -> dict:
    """
    Get distribution analysis for a specific column.

    For numeric columns:
        - Histogram
        - KDE (optional)
        - Normality test
        - Outlier detection

    For categorical columns:
        - Value counts
        - Frequency percentages
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    if column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column not found: {column}",
        )

    explorer = DataExplorer(df)
    result = explorer.analyze_distribution(column, n_bins=n_bins, include_kde=include_kde)
    return result.to_dict()


@router.get("/time-series")
async def get_time_series(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    date_column: str = Query(..., description="Name of date column"),
    value_column: str = Query(..., description="Name of value column"),
    freq: str | None = Query(None, description="Frequency hint (D, W, M, Q, Y)"),
    include_trend: bool = Query(True, description="Include trend line"),
    acf_lags: int = Query(20, ge=1, le=52, description="Number of ACF lags"),
) -> dict:
    """
    Get time series analysis for a date-value pair.

    Returns:
        - Time series data (dates, values)
        - Frequency detection
        - Trend line (optional)
        - Autocorrelation function
        - Seasonality detection
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    if date_column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Date column not found: {date_column}",
        )

    if value_column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Value column not found: {value_column}",
        )

    explorer = DataExplorer(df)
    result = explorer.analyze_time_series(
        date_column=date_column,
        value_column=value_column,
        freq=freq,
        include_trend=include_trend,
        acf_lags=acf_lags,
    )
    return result.to_dict()


@router.get("/correlations")
async def get_correlations(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    columns: str | None = Query(None, description="Comma-separated column names"),
    method: Literal["pearson", "spearman", "kendall"] = Query("pearson"),
    threshold: float = Query(0.5, ge=0, le=1, description="Significance threshold"),
) -> dict:
    """
    Get correlation matrix for numeric columns.

    Returns:
        - Correlation matrix
        - Significant pairs above threshold
        - Correlation strength classification
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)
    explorer = DataExplorer(df)

    column_list = None
    if columns:
        column_list = [c.strip() for c in columns.split(",")]

        # Validate columns
        invalid_cols = [c for c in column_list if c not in df.columns]
        if invalid_cols:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Columns not found: {invalid_cols}",
            )

    try:
        result = explorer.get_correlations(
            columns=column_list,
            method=method,
            threshold=threshold,
        )
        return result.to_dict()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/missing")
async def get_missing_analysis(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get missing value analysis.

    Returns:
        - Overall missing stats
        - Per-column missing counts
        - Missing patterns (which columns tend to be missing together)
        - Complete row count
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)
    explorer = DataExplorer(df)
    result = explorer.analyze_missing()
    return result.to_dict()


@router.get("/aggregated")
async def get_aggregated_preview(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    group_by: str = Query(..., description="Comma-separated columns to group by"),
    sum_columns: str | None = Query(None, description="Comma-separated columns to sum"),
    mean_columns: str | None = Query(None, description="Comma-separated columns to average"),
    sort_by: str | None = Query(None, description="Column to sort by"),
    limit: int = Query(100, ge=1, le=1000, description="Max rows to return"),
) -> dict:
    """
    Preview data aggregated by specified columns.

    Useful for previewing data at different granularity levels.

    Returns:
        - Aggregated data
        - Number of groups
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    # Parse group_by columns
    group_by_cols = [c.strip() for c in group_by.split(",")]

    # Build aggregation dict
    agg_columns = {}

    if sum_columns:
        for col in sum_columns.split(","):
            col = col.strip()
            agg_columns[col] = "sum"

    if mean_columns:
        for col in mean_columns.split(","):
            col = col.strip()
            agg_columns[col] = "mean"

    if not agg_columns:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify at least one of sum_columns or mean_columns",
        )

    explorer = DataExplorer(df)

    try:
        return explorer.get_aggregated_preview(
            group_by=group_by_cols,
            agg_columns=agg_columns,
            sort_by=sort_by,
            limit=limit,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/columns")
async def list_columns(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    List all columns with their types.

    Useful for building UI dropdowns and validating inputs.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    columns = []
    for col in df.columns:
        dtype = str(df[col].dtype)

        if dtype.startswith(("int", "float")):
            col_type = "numeric"
        elif dtype == "object":
            col_type = "categorical"
        elif dtype.startswith("datetime"):
            col_type = "datetime"
        elif dtype == "bool":
            col_type = "boolean"
        else:
            col_type = "other"

        columns.append(
            {
                "name": col,
                "dtype": dtype,
                "type": col_type,
                "unique_count": int(df[col].nunique()),
                "missing_count": int(df[col].isna().sum()),
            }
        )

    return {
        "columns": columns,
        "n_rows": len(df),
        "n_columns": len(df.columns),
    }


@router.get("/unique-values/{column}")
async def get_unique_values(
    project_id: UUID,
    dataset_id: UUID,
    column: str,
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(100, ge=1, le=1000),
) -> dict:
    """
    Get unique values for a column.

    Useful for building filter dropdowns.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    if column not in df.columns:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Column not found: {column}",
        )

    unique_values = df[column].dropna().unique()

    # Sort and limit
    try:
        unique_values = sorted(unique_values)
    except TypeError:
        pass  # Can't sort mixed types

    unique_values = unique_values[:limit]

    return {
        "column": column,
        "values": [str(v) if not isinstance(v, (int, float)) else v for v in unique_values],
        "total_unique": int(df[column].nunique()),
        "shown": len(unique_values),
    }


@router.post("/chart-data")
async def get_chart_data(
    project_id: UUID,
    dataset_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    x_column: str = Query(..., description="X-axis column"),
    y_columns: str = Query(..., description="Comma-separated Y-axis columns"),
    group_by: str = Query(None, description="Column to group by for legend"),
    aggregation: str = Query("sum", description="Aggregation method: sum, mean, count, min, max"),
) -> dict:
    """
    Get aggregated chart data for visualization.

    Supports multiple Y columns, grouping, and aggregation.
    """
    df = await get_dataset_df(project_id, dataset_id, current_user, db)

    # Parse y_columns
    y_cols = [c.strip() for c in y_columns.split(",") if c.strip()]

    # Validate columns
    if x_column not in df.columns:
        raise HTTPException(status_code=404, detail=f"X column not found: {x_column}")

    for col in y_cols:
        if col not in df.columns:
            raise HTTPException(status_code=404, detail=f"Y column not found: {col}")

    if group_by and group_by not in df.columns:
        raise HTTPException(status_code=404, detail=f"Group column not found: {group_by}")

    # Aggregation function
    agg_funcs = {
        "sum": "sum",
        "mean": "mean",
        "count": "count",
        "min": "min",
        "max": "max",
    }
    agg_func = agg_funcs.get(aggregation, "sum")

    try:
        if group_by:
            # Group by both x_column and group_by
            grouped = df.groupby([x_column, group_by])[y_cols].agg(agg_func).reset_index()

            # Get unique x values and groups
            x_values = sorted(grouped[x_column].unique(), key=lambda x: str(x))
            groups = sorted(grouped[group_by].unique(), key=lambda x: str(x))

            # Build series data for each group and y column
            series = []
            for y_col in y_cols:
                for grp in groups:
                    grp_data = grouped[grouped[group_by] == grp]
                    # Create a mapping for quick lookup
                    value_map = dict(zip(grp_data[x_column], grp_data[y_col]))
                    data = [float(value_map.get(x, 0)) if pd.notna(value_map.get(x, 0)) else 0 for x in x_values]
                    series.append(
                        {
                            "name": f"{y_col} - {grp}" if len(y_cols) > 1 else str(grp),
                            "data": data,
                        }
                    )
        else:
            # Simple aggregation by x_column only
            grouped = df.groupby(x_column)[y_cols].agg(agg_func).reset_index()
            x_values = grouped[x_column].tolist()

            series = []
            for y_col in y_cols:
                series.append(
                    {
                        "name": y_col,
                        "data": [float(v) if pd.notna(v) else 0 for v in grouped[y_col].tolist()],
                    }
                )

        return {
            "x_axis": [str(v) for v in x_values],
            "series": series,
            "aggregation": aggregation,
            "x_column": x_column,
            "y_columns": y_cols,
            "group_by": group_by,
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Aggregation error: {str(e)}")
