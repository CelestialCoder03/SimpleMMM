"""Scenario repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Scenario
from app.models.scenario import ScenarioStatus
from app.repositories.base import BaseRepository
from app.schemas.scenario import ScenarioCreate, ScenarioUpdate


class ScenarioRepository(BaseRepository[Scenario]):
    """Repository for Scenario operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Scenario)

    async def get_project_scenarios(
        self,
        project_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Scenario]:
        """Get all scenarios for a project."""
        result = await self.db.execute(
            select(Scenario)
            .where(Scenario.project_id == project_id)
            .offset(skip)
            .limit(limit)
            .order_by(Scenario.updated_at.desc())
        )
        return list(result.scalars().all())

    async def count_project_scenarios(self, project_id: UUID) -> int:
        """Count scenarios for a project."""
        result = await self.db.execute(
            select(func.count()).select_from(Scenario).where(Scenario.project_id == project_id)
        )
        return result.scalar_one()

    async def get_model_scenarios(
        self,
        model_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Scenario]:
        """Get all scenarios for a specific model."""
        result = await self.db.execute(
            select(Scenario)
            .where(Scenario.model_id == model_id)
            .offset(skip)
            .limit(limit)
            .order_by(Scenario.updated_at.desc())
        )
        return list(result.scalars().all())

    async def create_scenario(
        self,
        scenario_in: ScenarioCreate,
        project_id: UUID,
    ) -> Scenario:
        """Create a new scenario."""
        # Convert adjustments list to dict format
        adjustments_dict = {
            adj.variable: {"type": adj.type.value, "value": adj.value} for adj in scenario_in.adjustments
        }

        db_obj = Scenario(
            name=scenario_in.name,
            description=scenario_in.description,
            project_id=project_id,
            model_id=scenario_in.model_id,
            adjustments=adjustments_dict,
            start_date=scenario_in.start_date,
            end_date=scenario_in.end_date,
            status=ScenarioStatus.DRAFT.value,
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_scenario(
        self,
        scenario: Scenario,
        scenario_in: ScenarioUpdate,
    ) -> Scenario:
        """Update a scenario."""
        update_data = scenario_in.model_dump(exclude_unset=True)

        # Handle adjustments conversion
        if "adjustments" in update_data and update_data["adjustments"] is not None:
            adjustments_dict = {
                adj.variable: {"type": adj.type.value, "value": adj.value} for adj in scenario_in.adjustments
            }
            update_data["adjustments"] = adjustments_dict

        for key, value in update_data.items():
            setattr(scenario, key, value)

        await self.db.commit()
        await self.db.refresh(scenario)
        return scenario

    async def update_status(
        self,
        scenario: Scenario,
        status: ScenarioStatus,
    ) -> Scenario:
        """Update scenario status."""
        scenario.status = status.value
        await self.db.commit()
        await self.db.refresh(scenario)
        return scenario

    async def save_results(
        self,
        scenario: Scenario,
        results: dict,
        baseline_total: float,
        scenario_total: float,
        lift_percentage: float,
    ) -> Scenario:
        """Save scenario calculation results."""
        scenario.results = results
        scenario.baseline_total = baseline_total
        scenario.scenario_total = scenario_total
        scenario.lift_percentage = lift_percentage
        scenario.status = ScenarioStatus.READY.value

        await self.db.commit()
        await self.db.refresh(scenario)
        return scenario
