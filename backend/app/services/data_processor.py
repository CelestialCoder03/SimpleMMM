"""Data processor service for analyzing uploaded datasets."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


class DataProcessorService:
    """Service for processing and analyzing uploaded data files."""

    DTYPE_MAPPING = {
        "int64": "numeric",
        "int32": "numeric",
        "float64": "numeric",
        "float32": "numeric",
        "object": "text",
        "string": "text",
        "bool": "boolean",
        "boolean": "boolean",
        "datetime64[ns]": "datetime",
        "datetime64": "datetime",
        "category": "categorical",
    }

    def read_file(self, file_path: str) -> pd.DataFrame:
        """Read file into DataFrame based on extension."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext == ".csv":
            return pd.read_csv(file_path, parse_dates=True)
        elif ext in [".xlsx", ".xls"]:
            return pd.read_excel(file_path, parse_dates=True)
        else:
            raise ValueError(f"Unsupported file type: {ext}")

    def _looks_like_date(self, series: pd.Series) -> bool:
        """Check if a text column contains date-like values."""
        if series.dtype != "object" or len(series) == 0:
            return False

        # Sample some values to check
        sample = series.dropna().head(20)
        if len(sample) == 0:
            return False

        # Common date patterns
        date_patterns = [
            r"^\d{4}-\d{2}-\d{2}$",  # 2018-04-02
            r"^\d{2}/\d{2}/\d{4}$",  # 04/02/2018
            r"^\d{2}-\d{2}-\d{4}$",  # 04-02-2018
            r"^\d{4}/\d{2}/\d{2}$",  # 2018/04/02
            r"^\d{8}$",  # 20180402
        ]

        import re

        for val in sample:
            val_str = str(val).strip()
            if any(re.match(pattern, val_str) for pattern in date_patterns):
                # Try to parse it
                try:
                    pd.to_datetime(val_str)
                    return True
                except (ValueError, TypeError):
                    pass

        # Also try pandas inference on a sample
        try:
            pd.to_datetime(sample, errors="raise")
            return True
        except (ValueError, TypeError):
            return False

    def get_column_type(self, series: pd.Series) -> str:
        """Determine column type for a series."""
        dtype_str = str(series.dtype)

        # Check for datetime
        if pd.api.types.is_datetime64_any_dtype(series):
            return "datetime"

        # Check for boolean
        if pd.api.types.is_bool_dtype(series):
            return "boolean"

        # Check for numeric
        if pd.api.types.is_numeric_dtype(series):
            return "numeric"

        # Check for categorical (few unique values relative to total)
        if series.dtype == "object":
            # First check if it looks like a date column
            if self._looks_like_date(series):
                return "datetime"

            unique_ratio = series.nunique() / len(series) if len(series) > 0 else 0
            if unique_ratio < 0.05 and series.nunique() < 50:
                return "categorical"
            return "text"

        return self.DTYPE_MAPPING.get(dtype_str, "text")

    def compute_column_stats(self, series: pd.Series, column_type: str) -> dict[str, Any]:
        """Compute statistics for a column."""
        stats = {
            "name": series.name,
            "dtype": str(series.dtype),
            "column_type": column_type,
            "non_null_count": int(series.notna().sum()),
            "null_count": int(series.isna().sum()),
            "unique_count": int(series.nunique()),
        }

        if column_type == "numeric":
            stats.update(
                {
                    "min": float(series.min()) if pd.notna(series.min()) else None,
                    "max": float(series.max()) if pd.notna(series.max()) else None,
                    "mean": float(series.mean()) if pd.notna(series.mean()) else None,
                    "std": float(series.std()) if pd.notna(series.std()) else None,
                    "median": float(series.median()) if pd.notna(series.median()) else None,
                }
            )
        elif column_type in ["categorical", "text"]:
            value_counts = series.value_counts().head(10)
            stats["top_values"] = (
                [{"value": str(idx), "count": int(cnt)} for idx, cnt in value_counts.items()]
                if len(value_counts) > 0
                else None
            )

        return stats

    def analyze_dataframe(self, df: pd.DataFrame) -> dict[str, Any]:
        """Analyze DataFrame and return metadata."""
        columns_metadata = []

        for col in df.columns:
            col_type = self.get_column_type(df[col])
            col_stats = self.compute_column_stats(df[col], col_type)
            columns_metadata.append(col_stats)

        # Detect date column
        date_columns = [col for col in df.columns if pd.api.types.is_datetime64_any_dtype(df[col])]

        # Compute memory usage
        memory_bytes = int(df.memory_usage(deep=True).sum())

        return {
            "row_count": len(df),
            "column_count": len(df.columns),
            "columns": columns_metadata,
            "memory_usage_bytes": memory_bytes,
            "date_columns": date_columns,
        }

    def get_preview(self, df: pd.DataFrame, rows: int = 100) -> dict[str, Any]:
        """Get preview of DataFrame."""
        preview_df = df.head(rows)

        # Convert to JSON-serializable format
        data = preview_df.replace({np.nan: None}).to_dict("records")

        return {
            "columns": list(df.columns),
            "data": data,
            "total_rows": len(df),
            "preview_rows": len(preview_df),
        }

    def compute_correlation_matrix(
        self,
        df: pd.DataFrame,
        numeric_only: bool = True,
    ) -> dict[str, dict[str, float]]:
        """Compute correlation matrix for numeric columns."""
        if numeric_only:
            numeric_df = df.select_dtypes(include=[np.number])
        else:
            numeric_df = df

        if numeric_df.empty or len(numeric_df.columns) < 2:
            return {}

        corr = numeric_df.corr()
        return corr.to_dict()
