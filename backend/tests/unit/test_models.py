"""Tests for SQLAlchemy models."""

from app.db.base import Base, TimestampMixin, UUIDMixin
from app.models import Dataset, ModelConfig, ModelResult
from app.models.project import Project
from app.models.user import User


def test_user_model_table_name():
    """Test User model has correct table name."""
    assert User.__tablename__ == "users"


def test_user_model_inherits_base():
    """Test User model inherits from Base."""
    assert issubclass(User, Base)


def test_user_model_has_mixins():
    """Test User model has UUID and Timestamp mixins."""
    assert issubclass(User, UUIDMixin)
    assert issubclass(User, TimestampMixin)


def test_user_model_columns():
    """Test User model has expected columns."""
    columns = [c.name for c in User.__table__.columns]
    assert "id" in columns
    assert "email" in columns
    assert "hashed_password" in columns
    assert "full_name" in columns
    assert "is_active" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_project_model_table_name():
    """Test Project model has correct table name."""
    assert Project.__tablename__ == "projects"


def test_project_model_columns():
    """Test Project model has expected columns."""
    columns = [c.name for c in Project.__table__.columns]
    assert "id" in columns
    assert "name" in columns
    assert "description" in columns
    assert "owner_id" in columns
    assert "created_at" in columns
    assert "updated_at" in columns


def test_project_has_foreign_key():
    """Test Project model has foreign key to User."""
    fk_columns = [fk.column.table.name for fk in Project.__table__.foreign_keys]
    assert "users" in fk_columns


def test_uuid_mixin_default():
    """Test UUIDMixin provides valid UUID default."""
    # Check that the column has a default
    id_col = User.__table__.columns["id"]
    assert id_col.default is not None


# Dataset model tests
def test_dataset_model_table_name():
    """Test Dataset model has correct table name."""
    assert Dataset.__tablename__ == "datasets"


def test_dataset_model_columns():
    """Test Dataset model has expected columns."""
    columns = [c.name for c in Dataset.__table__.columns]
    assert "id" in columns
    assert "name" in columns
    assert "description" in columns
    assert "project_id" in columns
    assert "status" in columns
    assert "file_name" in columns
    assert "file_size" in columns
    assert "row_count" in columns
    assert "columns_metadata" in columns


def test_dataset_has_foreign_key():
    """Test Dataset model has foreign key to Project."""
    fk_columns = [fk.column.table.name for fk in Dataset.__table__.foreign_keys]
    assert "projects" in fk_columns


# ModelConfig model tests
def test_model_config_table_name():
    """Test ModelConfig model has correct table name."""
    assert ModelConfig.__tablename__ == "model_configs"


def test_model_config_columns():
    """Test ModelConfig model has expected columns."""
    columns = [c.name for c in ModelConfig.__table__.columns]
    assert "id" in columns
    assert "name" in columns
    assert "project_id" in columns
    assert "dataset_id" in columns
    assert "model_type" in columns
    assert "status" in columns
    assert "target_variable" in columns
    assert "date_column" in columns
    assert "features" in columns
    assert "constraints" in columns
    assert "priors" in columns


def test_model_config_has_foreign_keys():
    """Test ModelConfig model has foreign keys."""
    fk_tables = [fk.column.table.name for fk in ModelConfig.__table__.foreign_keys]
    assert "projects" in fk_tables
    assert "datasets" in fk_tables


# ModelResult model tests
def test_model_result_table_name():
    """Test ModelResult model has correct table name."""
    assert ModelResult.__tablename__ == "model_results"


def test_model_result_columns():
    """Test ModelResult model has expected columns."""
    columns = [c.name for c in ModelResult.__table__.columns]
    assert "id" in columns
    assert "model_config_id" in columns
    assert "training_duration_seconds" in columns
    assert "metrics" in columns
    assert "coefficients" in columns
    assert "contributions" in columns
    assert "decomposition" in columns
    assert "response_curves" in columns
    assert "diagnostics" in columns


def test_model_result_has_foreign_key():
    """Test ModelResult model has foreign key to ModelConfig."""
    fk_columns = [fk.column.table.name for fk in ModelResult.__table__.foreign_keys]
    assert "model_configs" in fk_columns
