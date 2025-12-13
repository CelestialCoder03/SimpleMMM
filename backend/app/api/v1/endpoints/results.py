"""Model results and visualization endpoints."""

import io
import logging
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select

from app.core.deps import CurrentUser, DbSession
from app.models.model_config import ModelStatus
from app.repositories.model_config import ModelConfigRepository
from app.repositories.project import ProjectRepository
from app.services.results.exporter import ResultExporter
from app.services.results.processor import ProcessedResult, ResultProcessor
from app.services.results.visualizations import (
    ChartConfig,
    ContributionChart,
    DecompositionChart,
    DiagnosticsChart,
    ResponseCurveChart,
    WaterfallChart,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects/{project_id}/models/{model_id}/results", tags=["Results"])


async def get_processed_result(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ProcessedResult:
    """Get processed model result with authorization check."""
    # Verify project access
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

    # Get model config with result relationship
    model_repo = ModelConfigRepository(db)
    model_config = await model_repo.get_with_result(model_id)

    if model_config is None or model_config.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found",
        )

    if model_config.status != ModelStatus.COMPLETED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Model not completed. Status: {model_config.status}",
        )

    processor = ResultProcessor()

    # Try to get result from Celery first
    if model_config.task_id:
        from celery.result import AsyncResult

        from app.workers.celery_app import celery_app

        result = AsyncResult(model_config.task_id, app=celery_app)

        if result.successful():
            raw_result = result.result
            # Validate that result is not None (can happen if Redis TTL expired)
            if raw_result is not None and isinstance(raw_result, dict):
                logger.debug(f"Returning model result from Celery for {model_id}")
                return processor.process(
                    raw_result,
                    model_id=model_id,
                    model_name=model_config.name,
                )
            else:
                logger.warning(
                    f"Celery task {model_config.task_id} successful but result is None/invalid for model {model_id}"
                )

    # Fallback to DB-stored result if Celery result expired
    if model_config.result:
        logger.debug(f"Returning model result from database for {model_id}")
        # Reconstruct ProcessedResult from stored DB result
        return ProcessedResult(
            model_id=model_id,
            model_name=model_config.name,
            model_type=model_config.model_type or "",
            metrics=model_config.result.metrics or {},
            coefficients=model_config.result.coefficients or [],
            contributions=model_config.result.contributions or [],
            decomposition=model_config.result.decomposition or {},
            response_curves=model_config.result.response_curves or {},
            diagnostics=model_config.result.diagnostics or {},
        )

    # Generate placeholder results from model config if no results exist
    logger.warning(f"No results found for model {model_id} in Celery or database - returning placeholder data")
    # This allows viewing the page while model is being retrained
    features = model_config.features or []
    placeholder_coefficients = [
        {
            "variable": f.get("column", f"feature_{i}"),
            "estimate": 0.0,
            "std_error": None,
            "t_statistic": None,
            "p_value": None,
            "ci_lower": None,
            "ci_upper": None,
            "is_significant": None,
        }
        for i, f in enumerate(features)
    ]
    placeholder_contributions = [
        {
            "variable": f.get("column", f"feature_{i}"),
            "total_contribution": 0.0,
            "contribution_pct": 0.0,
            "avg_contribution": 0.0,
            "roi": None,
        }
        for i, f in enumerate(features)
    ]

    return ProcessedResult(
        model_id=model_id,
        model_name=model_config.name,
        model_type=model_config.model_type or "",
        metrics={"r_squared": 0.0, "adj_r_squared": 0.0, "rmse": 0.0, "mape": 0.0},
        coefficients=placeholder_coefficients,
        contributions=placeholder_contributions,
        decomposition={"dates": [], "actual": [], "predicted": [], "base": []},
        response_curves={},
        diagnostics={},
    )


@router.get("/summary")
async def get_results_summary(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get full model results including metrics, coefficients, contributions, and decomposition.

    This endpoint returns all the data needed by the frontend results page.
    """
    processed = await get_processed_result(project_id, model_id, current_user, db)

    # Format metrics to match frontend expectations
    metrics = {
        "r_squared": processed.metrics.get("r_squared", 0),
        "adj_r_squared": processed.metrics.get("adjusted_r_squared", processed.metrics.get("adj_r_squared", 0)),
        "rmse": processed.metrics.get("rmse", 0),
        "mape": processed.metrics.get("mape", 0),
        "aic": processed.metrics.get("aic"),
        "bic": processed.metrics.get("bic"),
        "durbin_watson": processed.diagnostics.get("durbin_watson"),
    }

    # Format coefficients to match frontend expectations
    coefficients = [
        {
            "variable": c.get("variable", ""),
            "coefficient": c.get("estimate", 0),
            "std_error": c.get("std_error", 0),
            "t_statistic": c.get("t_statistic", 0),
            "p_value": c.get("p_value", 0),
            "significant": c.get("is_significant", False),
            "ci_lower": c.get("ci_lower", 0),
            "ci_upper": c.get("ci_upper", 0),
        }
        for c in processed.coefficients
    ]

    # Format contributions to match frontend expectations
    contributions = [
        {
            "variable": c.get("variable", ""),
            "contribution": c.get("total_contribution", 0),
            "contribution_pct": c.get("contribution_pct", 0),
            "roi": c.get("roi"),
        }
        for c in processed.contributions
    ]

    # Format decomposition to match frontend expectations (array of objects)
    dates = processed.decomposition.get("dates", [])
    actual = processed.decomposition.get("actual", [])
    predicted = processed.decomposition.get("predicted", [])
    base = processed.decomposition.get("base", [])

    # Channel contributions can be either under "contributions" key or at top level
    contrib_data = processed.decomposition.get("contributions", {})

    # Also check for channel contributions at top level (feature names directly in decomposition)
    exclude_keys = {
        "dates",
        "actual",
        "predicted",
        "base",
        "residuals",
        "contributions",
    }
    for key, values in processed.decomposition.items():
        if key not in exclude_keys and isinstance(values, list):
            contrib_data[key] = values

    decomposition = []
    for i, date in enumerate(dates):
        point = {
            "date": str(date) if date is not None else f"t{i}",
            "actual": float(actual[i]) if i < len(actual) else 0,
            "predicted": float(predicted[i]) if i < len(predicted) else 0,
            "base": float(base[i]) if i < len(base) else 0,
        }
        for channel, values in contrib_data.items():
            point[channel] = float(values[i]) if i < len(values) else 0
        decomposition.append(point)

    return {
        "model_id": str(model_id),
        "metrics": metrics,
        "coefficients": coefficients,
        "contributions": contributions,
        "decomposition": decomposition,
        "response_curves": processed.response_curves,
    }


@router.get("/executive-summary")
async def get_executive_summary(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """
    Get executive summary of model results.

    Returns key metrics, top contributors, and any issues detected.
    """
    processed = await get_processed_result(project_id, model_id, current_user, db)
    processor = ResultProcessor()
    return processor.get_summary(processed)


@router.get("/metrics")
async def get_model_metrics(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get model fit metrics."""
    processed = await get_processed_result(project_id, model_id, current_user, db)
    return {
        "metrics": processed.metrics,
        "model_type": processed.model_type,
        "training_duration_seconds": processed.training_duration_seconds,
    }


@router.get("/coefficients")
async def get_coefficients(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    significant_only: bool = Query(False, description="Return only significant coefficients"),
) -> dict:
    """Get coefficient estimates with statistics."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    coefficients = processed.coefficients
    if significant_only:
        coefficients = [c for c in coefficients if c.get("is_significant")]

    return {
        "coefficients": coefficients,
        "n_total": len(processed.coefficients),
        "n_significant": len([c for c in processed.coefficients if c.get("is_significant")]),
    }


@router.get("/contributions")
async def get_contributions(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get channel contribution analysis."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    return {
        "contributions": processed.contributions,
        "total_predicted": processed.total_predicted,
        "total_actual": processed.total_actual,
    }


@router.get("/decomposition")
async def get_decomposition(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    start_date: str | None = Query(None, description="Filter start date (YYYY-MM-DD)"),
    end_date: str | None = Query(None, description="Filter end date (YYYY-MM-DD)"),
) -> dict:
    """Get time series decomposition data."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    decomposition = processed.decomposition

    # Apply date filtering if specified
    if start_date or end_date:
        dates = decomposition.get("dates", [])
        indices = []

        for i, date in enumerate(dates):
            if start_date and date < start_date:
                continue
            if end_date and date > end_date:
                continue
            indices.append(i)

        if indices:
            filtered = {
                "dates": [dates[i] for i in indices],
                "actual": [decomposition.get("actual", [])[i] for i in indices] if decomposition.get("actual") else [],
                "predicted": [decomposition.get("predicted", [])[i] for i in indices]
                if decomposition.get("predicted")
                else [],
                "base": [decomposition.get("base", [])[i] for i in indices] if decomposition.get("base") else [],
                "contributions": {
                    k: [v[i] for i in indices] for k, v in decomposition.get("contributions", {}).items()
                },
            }
            return filtered

    return decomposition


@router.get("/response-curves")
async def get_response_curves(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    channel: str | None = Query(None, description="Filter to specific channel"),
) -> dict:
    """Get response curve data."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    curves = processed.response_curves

    if channel:
        if channel not in curves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel}",
            )
        return {"channel": channel, **curves[channel]}

    return {"channels": list(curves.keys()), "curves": curves}


@router.get("/diagnostics")
async def get_diagnostics(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Get model diagnostics."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    return {
        "diagnostics": processed.diagnostics,
        "validation": processed.validation,
    }


# =============================================================================
# CHART ENDPOINTS
# =============================================================================


@router.get("/charts/decomposition")
async def get_decomposition_chart(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    title: str = Query("Sales Decomposition", description="Chart title"),
) -> dict:
    """Get decomposition chart specification."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    config = ChartConfig(title=title)
    chart = DecompositionChart(config)

    return chart.generate(processed.decomposition)


@router.get("/charts/contributions")
async def get_contributions_chart(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    style: Literal["pie", "donut", "bar", "treemap"] = Query("pie"),
    title: str = Query("Channel Contributions", description="Chart title"),
) -> dict:
    """Get contribution chart specification."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    config = ChartConfig(title=title)
    chart = ContributionChart(config, chart_style=style)

    return chart.generate({"contributions": processed.contributions})


@router.get("/charts/response-curves")
async def get_response_curves_chart(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    channel: str | None = Query(None, description="Specific channel or all"),
    show_marginal: bool = Query(True),
    title: str = Query("Response Curves", description="Chart title"),
) -> dict:
    """Get response curve chart specification."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    config = ChartConfig(title=title)
    chart = ResponseCurveChart(config, show_marginal=show_marginal)

    if channel:
        if channel not in processed.response_curves:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Channel not found: {channel}",
            )
        data = {"variable": channel, **processed.response_curves[channel]}
    else:
        data = {"curves": processed.response_curves}

    return chart.generate(data)


@router.get("/charts/waterfall")
async def get_waterfall_chart(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    title: str = Query("Contribution Waterfall", description="Chart title"),
) -> dict:
    """Get waterfall chart specification."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    config = ChartConfig(title=title)
    chart = WaterfallChart(config)

    # Build waterfall items
    items = []
    base_contrib = next((c for c in processed.contributions if c["variable"] == "base"), None)

    if base_contrib:
        items.append(
            {
                "name": "Base",
                "value": base_contrib["total_contribution"],
                "type": "base",
            }
        )

    for contrib in processed.contributions:
        if contrib["variable"] != "base":
            items.append(
                {
                    "name": contrib["variable"],
                    "value": contrib["total_contribution"],
                    "type": "positive" if contrib["total_contribution"] >= 0 else "negative",
                }
            )

    items.append(
        {
            "name": "Total",
            "value": sum(c["total_contribution"] for c in processed.contributions),
            "type": "total",
        }
    )

    return chart.generate({"items": items})


@router.get("/charts/diagnostics")
async def get_diagnostics_chart(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    title: str = Query("Model Diagnostics", description="Chart title"),
) -> dict:
    """Get diagnostics chart specification."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    config = ChartConfig(title=title)
    chart = DiagnosticsChart(config)

    data = {
        "actual": processed.decomposition.get("actual", []),
        "predicted": processed.decomposition.get("predicted", []),
        "residuals": processed.decomposition.get("residuals", []),
        "vif": processed.diagnostics.get("vif", {}),
    }

    return chart.generate(data)


# =============================================================================
# EXPORT ENDPOINTS
# =============================================================================


@router.get("/export/csv")
async def export_csv(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    data_type: Literal["all", "coefficients", "contributions", "decomposition", "metrics"] = Query("all"),
) -> StreamingResponse:
    """Export results to CSV."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    exporter = ResultExporter(processed)
    csv_content = exporter.to_csv(data_type)

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=mmm_results_{model_id}_{data_type}.csv"},
    )


@router.get("/export/excel")
async def export_excel(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    language: str = Query("en", description="Language for field names (en/zh)"),
) -> StreamingResponse:
    """
    Export results to Excel workbook.

    Sheets:
    1. Model Metrics - Key performance metrics
    2. Coefficients - Coefficients with p-values, significance, and contribution %
    3. Decomposition - Pivot format with variable name, group, type (support/decomp), value
    """
    processed = await get_processed_result(project_id, model_id, current_user, db)

    # Try to fetch variable groups if the model exists
    variable_groups: dict[str, str] = {}
    try:
        from app.models import VariableGroup

        result = await db.execute(select(VariableGroup).where(VariableGroup.project_id == project_id))
        groups = result.scalars().all()
        for group in groups:
            if group.variables:
                for var in group.variables:
                    variable_groups[var] = group.name
    except Exception:
        # If variable groups table doesn't exist or other error, continue without groups
        pass

    exporter = ResultExporter(processed, language=language, variable_groups=variable_groups)
    excel_bytes = exporter.to_excel()

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=mmm_results_{model_id}.xlsx"},
    )


@router.get("/export/json")
async def export_json(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> dict:
    """Export complete results as JSON."""
    processed = await get_processed_result(project_id, model_id, current_user, db)
    return processed.to_dict()


@router.get("/export/html")
async def export_html_report(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """Export results as HTML report."""
    processed = await get_processed_result(project_id, model_id, current_user, db)

    exporter = ResultExporter(processed)
    html_content = exporter.to_html_report()

    return StreamingResponse(
        io.StringIO(html_content),
        media_type="text/html",
        headers={"Content-Disposition": f"attachment; filename=mmm_report_{model_id}.html"},
    )


# =============================================================================
# MODEL COMPARISON ENDPOINTS
# =============================================================================


@router.post("/compare", tags=["Results"])
async def compare_models_endpoint(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    compare_with: list[UUID] = Query(..., description="Model IDs to compare with"),
) -> dict:
    """
    Compare this model with other models in the same project.

    Returns metrics comparison, coefficient comparison, and contribution comparison.
    """
    from app.services.modeling.comparison import ModelComparer

    # Get all model IDs to compare
    all_model_ids = [model_id] + compare_with

    if len(all_model_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Need at least 2 models to compare",
        )

    # Get results for all models
    models_data = []
    model_repo = ModelConfigRepository(db)

    for mid in all_model_ids:
        try:
            processed = await get_processed_result(project_id, mid, current_user, db)
            model_config = await model_repo.get_by_id(mid)

            models_data.append(
                {
                    "id": str(mid),
                    "name": model_config.name if model_config else str(mid),
                    "result": processed.to_dict(),
                    "contributions": {
                        "contributions": processed.contributions,
                    },
                }
            )
        except HTTPException:
            continue  # Skip models that aren't ready

    if len(models_data) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Not enough completed models to compare",
        )

    # Run comparison
    comparer = ModelComparer()
    comparison = comparer.compare(models_data)

    return comparison.to_dict()


@router.get("/export/pdf", tags=["Results"])
async def export_pdf_report(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """Export results as PDF report."""
    from app.repositories.project import ProjectRepository
    from app.services.reports.pdf_generator import generate_pdf_report

    processed = await get_processed_result(project_id, model_id, current_user, db)

    # Get model and project names
    model_repo = ModelConfigRepository(db)
    project_repo = ProjectRepository(db)

    model_config = await model_repo.get_by_id(model_id)
    project = await project_repo.get_by_id(project_id)

    model_name = model_config.name if model_config else str(model_id)
    project_name = project.name if project else str(project_id)

    # Generate PDF
    pdf_bytes = generate_pdf_report(
        model_name=model_name,
        project_name=project_name,
        model_result=processed.to_dict(),
        contributions=processed.contributions,
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=mmm_report_{model_id}.pdf"},
    )


@router.get("/export/pptx", tags=["Results"])
async def export_pptx_report(
    project_id: UUID,
    model_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> StreamingResponse:
    """Export results as PowerPoint presentation."""
    from app.repositories.project import ProjectRepository
    from app.services.reports.pptx_generator import generate_pptx_report

    processed = await get_processed_result(project_id, model_id, current_user, db)

    # Get model and project names
    model_repo = ModelConfigRepository(db)
    project_repo = ProjectRepository(db)

    model_config = await model_repo.get_by_id(model_id)
    project = await project_repo.get_by_id(project_id)

    model_name = model_config.name if model_config else str(model_id)
    project_name = project.name if project else str(project_id)

    # Generate PPTX
    pptx_bytes = generate_pptx_report(
        model_name=model_name,
        project_name=project_name,
        model_result=processed.to_dict(),
        contributions=processed.contributions,
    )

    return StreamingResponse(
        io.BytesIO(pptx_bytes),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        headers={"Content-Disposition": f"attachment; filename=mmm_report_{model_id}.pptx"},
    )
