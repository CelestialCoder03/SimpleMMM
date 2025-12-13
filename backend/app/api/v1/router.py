"""Main API v1 router."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    datasets,
    exploration,
    granularity,
    hierarchical,
    models,
    optimization,
    project_members,
    projects,
    results,
    scenarios,
    training,
    transformations,
    upload,
    users,
    variable_groups,
    variable_metadata,
)

router = APIRouter()

# Include all endpoint routers
router.include_router(auth.router)
router.include_router(users.router)
router.include_router(projects.router)
router.include_router(project_members.router, prefix="/projects", tags=["project-members"])
router.include_router(datasets.router)
router.include_router(models.router)
router.include_router(upload.router)
router.include_router(training.router)
router.include_router(results.router)
router.include_router(exploration.router)
router.include_router(granularity.router)
router.include_router(transformations.router)
router.include_router(scenarios.router)
router.include_router(optimization.router)
router.include_router(variable_groups.router)
router.include_router(hierarchical.router)
router.include_router(variable_metadata.router)


@router.get("/")
async def root():
    """API root endpoint."""
    return {"message": "Marketing Mix Model API v1"}
