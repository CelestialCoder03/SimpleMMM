"""Tests for service classes."""

import tempfile
from pathlib import Path

import pandas as pd
import pytest


def test_file_storage_service_exists():
    """Test FileStorageService can be imported."""
    from app.services.file_storage import FileStorageService

    assert FileStorageService is not None


def test_data_processor_service_exists():
    """Test DataProcessorService can be imported."""
    from app.services.data_processor import DataProcessorService

    assert DataProcessorService is not None


def test_file_storage_validate_extension():
    """Test file extension validation."""
    from app.services.file_storage import FileStorageService

    storage = FileStorageService()

    assert storage.validate_extension("data.csv") is True
    assert storage.validate_extension("data.xlsx") is True
    assert storage.validate_extension("data.xls") is True
    assert storage.validate_extension("data.txt") is False
    assert storage.validate_extension("data.pdf") is False


def test_file_storage_validate_size():
    """Test file size validation."""
    from app.services.file_storage import FileStorageService

    storage = FileStorageService()

    assert storage.validate_size(1024) is True  # 1KB
    assert storage.validate_size(50 * 1024 * 1024) is True  # 50MB
    assert storage.validate_size(200 * 1024 * 1024) is False  # 200MB


def test_file_storage_generate_filename():
    """Test unique filename generation."""
    from app.services.file_storage import FileStorageService

    storage = FileStorageService()

    filename = storage.generate_filename("test_data.csv")
    assert filename.endswith(".csv")
    assert "test_data" in filename

    # Should be unique each time
    filename2 = storage.generate_filename("test_data.csv")
    assert filename != filename2


def test_data_processor_read_csv():
    """Test reading CSV files."""
    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()

    # Create temp CSV
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        f.write("date,sales,spend\n")
        f.write("2024-01-01,1000,100\n")
        f.write("2024-01-02,1200,120\n")
        temp_path = f.name

    try:
        df = processor.read_file(temp_path)
        assert len(df) == 2
        assert "sales" in df.columns
        assert "spend" in df.columns
    finally:
        Path(temp_path).unlink()


def test_data_processor_get_column_type():
    """Test column type detection."""
    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()

    # Numeric
    series = pd.Series([1, 2, 3, 4, 5])
    assert processor.get_column_type(series) == "numeric"

    # Boolean
    series = pd.Series([True, False, True])
    assert processor.get_column_type(series) == "boolean"

    # Datetime
    series = pd.to_datetime(["2024-01-01", "2024-01-02"])
    assert processor.get_column_type(series) == "datetime"


def test_data_processor_analyze_dataframe():
    """Test DataFrame analysis."""
    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()

    df = pd.DataFrame(
        {
            "date": pd.to_datetime(["2024-01-01", "2024-01-02", "2024-01-03"]),
            "sales": [1000, 1200, 1100],
            "region": ["A", "A", "B"],
        }
    )

    metadata = processor.analyze_dataframe(df)

    assert metadata["row_count"] == 3
    assert metadata["column_count"] == 3
    assert len(metadata["columns"]) == 3


def test_data_processor_get_preview():
    """Test DataFrame preview."""
    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()

    df = pd.DataFrame(
        {
            "a": range(200),
            "b": range(200),
        }
    )

    preview = processor.get_preview(df, rows=50)

    assert preview["total_rows"] == 200
    assert preview["preview_rows"] == 50
    assert len(preview["data"]) == 50


def test_data_processor_correlation():
    """Test correlation matrix computation."""
    from app.services.data_processor import DataProcessorService

    processor = DataProcessorService()

    df = pd.DataFrame(
        {
            "a": [1, 2, 3, 4, 5],
            "b": [2, 4, 6, 8, 10],  # Perfectly correlated
            "c": [5, 4, 3, 2, 1],  # Negatively correlated
        }
    )

    corr = processor.compute_correlation_matrix(df)

    assert "a" in corr
    assert corr["a"]["b"] == pytest.approx(1.0)
    assert corr["a"]["c"] == pytest.approx(-1.0)
