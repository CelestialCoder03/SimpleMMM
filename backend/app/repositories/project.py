"""Project repository."""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Project
from app.repositories.base import BaseRepository
from app.schemas.project import ProjectCreate, ProjectUpdate


class ProjectRepository(BaseRepository[Project]):
    """Repository for Project operations."""

    def __init__(self, db: AsyncSession):
        super().__init__(db, Project)

    async def get_by_id_with_counts(self, id: UUID) -> Project | None:
        """Get project by ID with related counts."""
        result = await self.db.execute(
            select(Project)
            .options(
                selectinload(Project.datasets),
                selectinload(Project.model_configs),
            )
            .where(Project.id == id)
        )
        return result.scalar_one_or_none()

    async def get_user_projects(
        self,
        owner_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Project]:
        """Get all projects for a user."""
        result = await self.db.execute(
            select(Project)
            .where(Project.owner_id == owner_id)
            .offset(skip)
            .limit(limit)
            .order_by(Project.updated_at.desc())
        )
        return list(result.scalars().all())

    async def count_user_projects(self, owner_id: UUID) -> int:
        """Count projects for a user."""
        result = await self.db.execute(select(func.count()).select_from(Project).where(Project.owner_id == owner_id))
        return result.scalar_one()

    async def create_project(
        self,
        project_in: ProjectCreate,
        owner_id: UUID,
    ) -> Project:
        """Create a new project."""
        db_obj = Project(
            name=project_in.name,
            description=project_in.description,
            owner_id=owner_id,
        )
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj

    async def update_project(
        self,
        project: Project,
        project_in: ProjectUpdate,
    ) -> Project:
        """Update project data."""
        update_data = project_in.model_dump(exclude_unset=True)

        for key, value in update_data.items():
            setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def is_owner(self, project: Project, user_id: UUID) -> bool:
        """Check if user is the project owner."""
        return project.owner_id == user_id
