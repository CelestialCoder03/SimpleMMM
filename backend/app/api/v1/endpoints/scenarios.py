"""Scenario planning endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status

from app.core.deps import CurrentUser, DbSession
from app.models.scenario import ScenarioStatus
from app.repositories.model_config import ModelConfigRepository
from app.repositories.project import ProjectRepository
from app.repositories.scenario import ScenarioRepository
from app.schemas.base import PaginatedResponse
from app.schemas.scenario import (
    ScenarioComparison,
    ScenarioCreate,
    ScenarioRead,
    ScenarioResults,
    ScenarioUpdate,
)
from app.services.scenarios import calculate_scenario

router = APIRouter(prefix="/projects/{project_id}/scenarios", tags=["Scenarios"])


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


@router.get("", response_model=PaginatedResponse)
async def list_scenarios(
    project_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
) -> PaginatedResponse:
    """List all scenarios for a project."""
    await verify_project_access(project_id, current_user, db)

    scenario_repo = ScenarioRepository(db)
    skip = (page - 1) * limit

    scenarios = await scenario_repo.get_project_scenarios(
        project_id=project_id,
        skip=skip,
        limit=limit,
    )
    total = await scenario_repo.count_project_scenarios(project_id)

    items = [ScenarioRead.model_validate(s) for s in scenarios]
    return PaginatedResponse.create(items=items, total=total, page=page, limit=limit)


@router.post("", response_model=ScenarioRead, status_code=status.HTTP_201_CREATED)
async def create_scenario(
    project_id: UUID,
    scenario_in: ScenarioCreate,
    current_user: CurrentUser,
    db: DbSession,
) -> ScenarioRead:
    """Create a new scenario."""
    await verify_project_access(project_id, current_user, db)

    # Verify model exists and belongs to project
    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_by_id(scenario_in.model_id)

    if model is None or model.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Model not found in this project",
        )

    if model.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model must be trained before creating scenarios",
        )

    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.create_scenario(scenario_in, project_id)

    return ScenarioRead.model_validate(scenario)


@router.get("/{scenario_id}", response_model=ScenarioRead)
async def get_scenario(
    project_id: UUID,
    scenario_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ScenarioRead:
    """Get a specific scenario."""
    await verify_project_access(project_id, current_user, db)

    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)

    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    return ScenarioRead.model_validate(scenario)


@router.patch("/{scenario_id}", response_model=ScenarioRead)
async def update_scenario(
    project_id: UUID,
    scenario_id: UUID,
    scenario_in: ScenarioUpdate,
    current_user: CurrentUser,
    db: DbSession,
) -> ScenarioRead:
    """Update a scenario."""
    await verify_project_access(project_id, current_user, db)

    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)

    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    scenario = await scenario_repo.update_scenario(scenario, scenario_in)

    # Reset status if adjustments changed
    if scenario_in.adjustments is not None:
        await scenario_repo.update_status(scenario, ScenarioStatus.DRAFT)

    return ScenarioRead.model_validate(scenario)


@router.delete("/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_scenario(
    project_id: UUID,
    scenario_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> None:
    """Delete a scenario."""
    await verify_project_access(project_id, current_user, db)

    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)

    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    await scenario_repo.delete(scenario_id)


@router.post("/{scenario_id}/calculate", response_model=ScenarioResults)
async def calculate_scenario_results(
    project_id: UUID,
    scenario_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ScenarioResults:
    """Calculate scenario results."""
    await verify_project_access(project_id, current_user, db)

    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)

    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    # Get model results
    model_repo = ModelConfigRepository(db)
    model = await model_repo.get_by_id(scenario.model_id)

    if model is None or model.result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Model results not available",
        )

    # Update status to calculating
    await scenario_repo.update_status(scenario, ScenarioStatus.CALCULATING)

    try:
        # Get model result data
        model_result = {
            "coefficients": model.result.coefficients or {},
            "contributions": model.result.contributions or {},
            "dates": model.result.dates or [],
            "actuals": model.result.actuals or [],
            "fitted": model.result.fitted or [],
        }

        # Calculate scenario
        result = calculate_scenario(
            model_result=model_result,
            adjustments=scenario.adjustments,
            start_date=scenario.start_date,
            end_date=scenario.end_date,
        )

        # Save results
        await scenario_repo.save_results(
            scenario=scenario,
            results=result.to_dict(),
            baseline_total=result.baseline_total,
            scenario_total=result.scenario_total,
            lift_percentage=result.lift_percentage,
        )

        return ScenarioResults(
            scenario_id=scenario_id,
            dates=result.dates,
            baseline=result.baseline,
            scenario=result.scenario,
            baseline_contributions=result.baseline_contributions,
            scenario_contributions=result.scenario_contributions,
            summary=result.summary,
        )

    except Exception as e:
        await scenario_repo.update_status(scenario, ScenarioStatus.FAILED)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Scenario calculation failed: {str(e)}",
        )


@router.get("/{scenario_id}/results", response_model=ScenarioResults)
async def get_scenario_results(
    project_id: UUID,
    scenario_id: UUID,
    current_user: CurrentUser,
    db: DbSession,
) -> ScenarioResults:
    """Get calculated scenario results."""
    await verify_project_access(project_id, current_user, db)

    scenario_repo = ScenarioRepository(db)
    scenario = await scenario_repo.get_by_id(scenario_id)

    if scenario is None or scenario.project_id != project_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Scenario not found",
        )

    if scenario.status != ScenarioStatus.READY.value or scenario.results is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Scenario results not available. Run calculate first.",
        )

    results = scenario.results

    return ScenarioResults(
        scenario_id=scenario_id,
        dates=results.get("dates", []),
        baseline=results.get("baseline", []),
        scenario=results.get("scenario", []),
        baseline_contributions=results.get("baseline_contributions", {}),
        scenario_contributions=results.get("scenario_contributions", {}),
        summary=results.get("summary", {}),
    )


@router.post("/compare", response_model=ScenarioComparison)
async def compare_scenarios(
    project_id: UUID,
    scenario_ids: list[UUID],
    current_user: CurrentUser,
    db: DbSession,
) -> ScenarioComparison:
    """Compare multiple scenarios."""
    await verify_project_access(project_id, current_user, db)

    if len(scenario_ids) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least 2 scenarios required for comparison",
        )

    scenario_repo = ScenarioRepository(db)
    scenarios = []

    for sid in scenario_ids:
        scenario = await scenario_repo.get_by_id(sid)
        if scenario is None or scenario.project_id != project_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Scenario {sid} not found",
            )
        if scenario.status != ScenarioStatus.READY.value:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Scenario {scenario.name} has not been calculated",
            )
        scenarios.append(scenario)

    # Build comparison
    comparison = {
        "totals": {s.name: s.scenario_total for s in scenarios},
        "lifts": {s.name: s.lift_percentage for s in scenarios},
        "ranking": sorted(
            [(s.name, s.scenario_total) for s in scenarios],
            key=lambda x: x[1] or 0,
            reverse=True,
        ),
    }

    return ScenarioComparison(
        scenarios=[ScenarioRead.model_validate(s) for s in scenarios],
        comparison=comparison,
    )
