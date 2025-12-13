"""Variable metadata endpoints."""

from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.core.deps import CurrentUser, DbSession
from app.models import Dataset, Project, VariableMetadata, VariableType
from app.schemas.variable_metadata import (
    VariableMetadataBulkUpdate,
    VariableMetadataCreate,
    VariableMetadataRead,
    VariableMetadataUpdate,
    VariableSummary,
    VariableTypeOption,
)

router = APIRouter(prefix="/projects/{project_id}/variables", tags=["Variable Metadata"])


VARIABLE_TYPE_OPTIONS = [
    VariableTypeOption(
        value=VariableType.TARGET.value,
        label="目标变量",
        description="销售额、收入等需要预测的目标",
    ),
    VariableTypeOption(
        value=VariableType.SPENDING.value,
        label="花费/投资",
        description="媒体投放花费、广告支出等",
    ),
    VariableTypeOption(
        value=VariableType.SUPPORT.value,
        label="支持指标",
        description="GRP、曝光次数、点击量等非花费类指标",
    ),
    VariableTypeOption(
        value=VariableType.DIMENSION.value,
        label="维度",
        description="地区、渠道、日期等分类字段",
    ),
    VariableTypeOption(
        value=VariableType.CONTROL.value,
        label="控制变量",
        description="价格、铺货率、季节性等控制因素",
    ),
    VariableTypeOption(value=VariableType.OTHER.value, label="其他", description="未分类的变量"),
]


async def get_project_or_404(project_id: UUID, db: DbSession, current_user: CurrentUser) -> Project:
    """Get project or raise 404."""
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/types", response_model=list[VariableTypeOption])
async def get_variable_types():
    """Get available variable type options."""
    return VARIABLE_TYPE_OPTIONS


@router.get("", response_model=list[VariableSummary])
async def list_variables(
    project_id: UUID,
    dataset_id: UUID | None = None,
    db: DbSession = None,
    current_user: CurrentUser = None,
):
    """
    List all variables in a project with their metadata.

    If dataset_id is provided, returns variables for that specific dataset.
    Otherwise returns all variables across all datasets in the project.
    """
    import pandas as pd

    from app.services.file_storage import FileStorageService

    await get_project_or_404(project_id, db, current_user)

    # Get datasets
    if dataset_id:
        result = await db.execute(
            select(Dataset).where(
                Dataset.id == dataset_id,
                Dataset.project_id == project_id,
            )
        )
        datasets = [result.scalar_one_or_none()]
        if not datasets[0]:
            raise HTTPException(status_code=404, detail="Dataset not found")
    else:
        result = await db.execute(select(Dataset).where(Dataset.project_id == project_id))
        datasets = result.scalars().all()

    # Get all variable metadata for this project
    result = await db.execute(
        select(VariableMetadata)
        .where(VariableMetadata.project_id == project_id)
        .options(selectinload(VariableMetadata.group))
    )
    metadata_list = result.scalars().all()
    metadata_map = {m.variable_name: m for m in metadata_list}

    # Get all variable groups for this project and build variable->group map
    from app.models.variable_group import VariableGroup

    result = await db.execute(select(VariableGroup).where(VariableGroup.project_id == project_id))
    groups = result.scalars().all()
    variable_to_group = {}
    for group in groups:
        for var_name in group.variables:
            variable_to_group[var_name] = {"name": group.name, "color": group.color}

    # Collect all unique variables from datasets
    storage = FileStorageService()
    variables = {}

    for ds in datasets:
        if not ds or not ds.file_path:
            continue
        try:
            file_path = storage.base_dir / ds.file_path
            df = pd.read_csv(file_path, nrows=1)
            for col in df.columns:
                if col not in variables:
                    dtype = str(df[col].dtype)
                    variables[col] = {"name": col, "dtype": dtype}
        except Exception:
            continue

    # Build response with metadata
    summaries = []
    for var_name, var_info in variables.items():
        meta = metadata_map.get(var_name)
        # Get group info from variable_to_group map (VariableGroup.variables array)
        group_info = variable_to_group.get(var_name, {})
        summaries.append(
            VariableSummary(
                name=var_name,
                dtype=var_info.get("dtype"),
                metadata=VariableMetadataRead.model_validate(meta) if meta else None,
                group_name=group_info.get("name"),
                group_color=group_info.get("color"),
            )
        )

    # Sort: variables with metadata first, then alphabetically
    summaries.sort(key=lambda x: (x.metadata is None, x.name))

    return summaries


@router.post("", response_model=VariableMetadataRead, status_code=status.HTTP_201_CREATED)
async def create_variable_metadata(
    project_id: UUID,
    data: VariableMetadataCreate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Create or update metadata for a variable."""
    await get_project_or_404(project_id, db, current_user)

    # Check if metadata already exists
    result = await db.execute(
        select(VariableMetadata).where(
            VariableMetadata.project_id == project_id,
            VariableMetadata.variable_name == data.variable_name,
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        # Update existing
        for key, value in data.model_dump(exclude_unset=True, exclude={"variable_name"}).items():
            setattr(existing, key, value)
        await db.commit()
        await db.refresh(existing)
        return existing

    # Create new
    metadata = VariableMetadata(
        project_id=project_id,
        **data.model_dump(),
    )
    db.add(metadata)
    await db.commit()
    await db.refresh(metadata)

    return metadata


@router.put("/{variable_name}", response_model=VariableMetadataRead)
async def update_variable_metadata(
    project_id: UUID,
    variable_name: str,
    data: VariableMetadataUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Update metadata for a variable."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(VariableMetadata).where(
            VariableMetadata.project_id == project_id,
            VariableMetadata.variable_name == variable_name,
        )
    )
    metadata = result.scalar_one_or_none()

    if not metadata:
        # Create new if doesn't exist
        metadata = VariableMetadata(
            project_id=project_id,
            variable_name=variable_name,
            **data.model_dump(exclude_unset=True),
        )
        db.add(metadata)
    else:
        # Update existing
        for key, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(metadata, key, value)

    await db.commit()
    await db.refresh(metadata)

    return metadata


@router.post("/bulk", response_model=list[VariableMetadataRead])
async def bulk_update_variables(
    project_id: UUID,
    data: VariableMetadataBulkUpdate,
    db: DbSession,
    current_user: CurrentUser,
):
    """Bulk create or update variable metadata."""
    await get_project_or_404(project_id, db, current_user)

    results = []
    for var_data in data.variables:
        result = await db.execute(
            select(VariableMetadata).where(
                VariableMetadata.project_id == project_id,
                VariableMetadata.variable_name == var_data.variable_name,
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            for key, value in var_data.model_dump(exclude_unset=True, exclude={"variable_name"}).items():
                if value is not None:
                    setattr(existing, key, value)
            results.append(existing)
        else:
            metadata = VariableMetadata(
                project_id=project_id,
                **var_data.model_dump(),
            )
            db.add(metadata)
            results.append(metadata)

    await db.commit()

    for r in results:
        await db.refresh(r)

    return results


@router.delete("/{variable_name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_variable_metadata(
    project_id: UUID,
    variable_name: str,
    db: DbSession,
    current_user: CurrentUser,
):
    """Delete metadata for a variable."""
    await get_project_or_404(project_id, db, current_user)

    await db.execute(
        delete(VariableMetadata).where(
            VariableMetadata.project_id == project_id,
            VariableMetadata.variable_name == variable_name,
        )
    )
    await db.commit()


@router.get("/spending-options", response_model=list[str])
async def get_spending_options(
    project_id: UUID,
    db: DbSession,
    current_user: CurrentUser,
):
    """Get list of spending variables for ROI mapping."""
    await get_project_or_404(project_id, db, current_user)

    result = await db.execute(
        select(VariableMetadata.variable_name).where(
            VariableMetadata.project_id == project_id,
            VariableMetadata.variable_type == VariableType.SPENDING.value,
        )
    )
    return [r[0] for r in result.all()]
