"""Data aggregation across granularity levels."""

from dataclasses import dataclass, field
from typing import Any, Callable, Literal

import numpy as np
import pandas as pd

from app.services.granularity.dimensions import Dimension


@dataclass
class AggregationRule:
    """
    Defines how to aggregate a column when rolling up.

    Attributes:
        column: Column name to aggregate
        method: Aggregation method
        weight_column: Column to use for weighted aggregations
        custom_func: Custom aggregation function
    """

    column: str
    method: Literal["sum", "mean", "weighted_mean", "first", "last", "min", "max", "count", "custom"]
    weight_column: str | None = None
    custom_func: Callable | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "column": self.column,
            "method": self.method,
            "weight_column": self.weight_column,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AggregationRule":
        return cls(
            column=data["column"],
            method=data.get("method", "sum"),
            weight_column=data.get("weight_column"),
        )


@dataclass
class MetricDefinition:
    """
    Definition of a metric and how it should be aggregated.

    Attributes:
        name: Metric identifier
        column: Column name in dataset
        metric_type: Type of metric (affects aggregation)
        aggregation: How to aggregate this metric
        derived_formula: Formula for derived metrics
    """

    name: str
    column: str
    metric_type: Literal["additive", "semi_additive", "non_additive", "derived"]
    aggregation: AggregationRule
    derived_formula: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "column": self.column,
            "metric_type": self.metric_type,
            "aggregation": self.aggregation.to_dict(),
            "derived_formula": self.derived_formula,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MetricDefinition":
        return cls(
            name=data["name"],
            column=data["column"],
            metric_type=data.get("metric_type", "additive"),
            aggregation=AggregationRule.from_dict(data.get("aggregation", {"column": data["column"], "method": "sum"})),
            derived_formula=data.get("derived_formula"),
        )


@dataclass
class GranularitySpec:
    """
    Specification of target granularity for aggregation.

    Attributes:
        name: Identifier for this granularity
        dimensions: {dimension_name: level_name} mapping
        filters: Optional filters {column: [values]}
    """

    name: str
    dimensions: dict[str, str]
    filters: dict[str, list[Any]] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "dimensions": self.dimensions,
            "filters": self.filters,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "GranularitySpec":
        return cls(
            name=data["name"],
            dimensions=data["dimensions"],
            filters=data.get("filters", {}),
        )


class GranularityManager:
    """
    Manages data aggregation across granularity levels.

    This class handles:
    - Aggregating data to specified granularity
    - Validating granularity specifications
    - Computing derived metrics after aggregation

    Usage:
        manager = GranularityManager(df, dimensions, metrics)

        # Aggregate to province-month level
        agg_df = manager.aggregate(GranularitySpec(
            name="province_monthly",
            dimensions={"geography": "province", "time": "month"},
        ))
    """

    def __init__(
        self,
        df: pd.DataFrame,
        dimensions: list[Dimension],
        metrics: list[MetricDefinition],
    ):
        """
        Initialize manager.

        Args:
            df: Raw dataset at finest granularity
            dimensions: List of dimension configurations
            metrics: List of metric definitions
        """
        self.df = df
        self.dimensions = {d.name: d for d in dimensions}
        self.metrics = {m.name: m for m in metrics}
        self._metrics_list = metrics

    def aggregate(
        self,
        granularity: GranularitySpec,
        include_count: bool = True,
    ) -> pd.DataFrame:
        """
        Aggregate data to specified granularity.

        Args:
            granularity: Target granularity specification
            include_count: Whether to include row count per group

        Returns:
            Aggregated DataFrame
        """
        # Build groupby columns
        groupby_cols = self._get_groupby_columns(granularity)

        if not groupby_cols:
            # No groupby columns = full aggregation
            return self._aggregate_all(granularity, include_count)

        # Apply filters first
        df = self._apply_filters(self.df, granularity.filters)

        # Separate metrics by aggregation type
        sum_cols = []
        mean_cols = []
        weighted_cols = []  # (col, weight_col)
        first_cols = []
        derived_metrics = []

        for metric in self._metrics_list:
            if metric.metric_type == "derived":
                derived_metrics.append(metric)
                continue

            rule = metric.aggregation
            if rule.method == "sum":
                sum_cols.append(metric.column)
            elif rule.method == "mean":
                mean_cols.append(metric.column)
            elif rule.method == "weighted_mean":
                weighted_cols.append((metric.column, rule.weight_column))
            elif rule.method == "first":
                first_cols.append(metric.column)

        # Build aggregation dict
        agg_dict = {}
        for col in sum_cols:
            if col in df.columns:
                agg_dict[col] = "sum"
        for col in mean_cols:
            if col in df.columns:
                agg_dict[col] = "mean"
        for col in first_cols:
            if col in df.columns:
                agg_dict[col] = "first"

        # Handle weighted means separately
        weighted_results = {}
        for col, weight_col in weighted_cols:
            if col in df.columns and weight_col in df.columns:
                # Create weighted column
                weighted_col_name = f"_weighted_{col}"
                df[weighted_col_name] = df[col] * df[weight_col]
                agg_dict[weighted_col_name] = "sum"
                agg_dict[weight_col] = "sum"
                weighted_results[col] = (weighted_col_name, weight_col)

        if include_count:
            agg_dict["_row_count"] = (df.columns[0], "count")

        # Perform aggregation
        if agg_dict:
            # Handle the special case of count
            if include_count:
                agg_dict.pop("_row_count")
                result = df.groupby(groupby_cols, as_index=False).agg(agg_dict)
                result["_row_count"] = df.groupby(groupby_cols).size().values
            else:
                result = df.groupby(groupby_cols, as_index=False).agg(agg_dict)
        else:
            result = df[groupby_cols].drop_duplicates().reset_index(drop=True)
            if include_count:
                result["_row_count"] = df.groupby(groupby_cols).size().values

        # Compute weighted means
        for col, (weighted_col, weight_col) in weighted_results.items():
            result[col] = result[weighted_col] / result[weight_col]
            result = result.drop(columns=[weighted_col])

        # Calculate derived metrics
        for metric in derived_metrics:
            if metric.derived_formula:
                try:
                    result[metric.column] = eval(
                        metric.derived_formula,
                        {"__builtins__": {}},
                        {"df": result, "np": np},
                    )
                except Exception:
                    # Log warning but continue
                    result[metric.column] = np.nan

        return result

    def _get_groupby_columns(self, granularity: GranularitySpec) -> list[str]:
        """Get column names for groupby based on granularity spec."""
        groupby_cols = []

        for dim_name, level_name in granularity.dimensions.items():
            dim = self.dimensions.get(dim_name)
            if dim is None:
                continue

            level = dim.get_level(level_name)
            if level is None:
                continue

            # Aggregated levels (column=None) don't add groupby columns
            if level.column is not None and level.column in self.df.columns:
                groupby_cols.append(level.column)

        return groupby_cols

    def _apply_filters(
        self,
        df: pd.DataFrame,
        filters: dict[str, list[Any]],
    ) -> pd.DataFrame:
        """Apply filters to dataframe."""
        result = df

        for col, values in filters.items():
            if col in result.columns:
                result = result[result[col].isin(values)]

        return result

    def _aggregate_all(
        self,
        granularity: GranularitySpec,
        include_count: bool,
    ) -> pd.DataFrame:
        """Aggregate all rows to a single row."""
        df = self._apply_filters(self.df, granularity.filters)

        result = {}

        for metric in self._metrics_list:
            if metric.metric_type == "derived":
                continue

            col = metric.column
            if col not in df.columns:
                continue

            rule = metric.aggregation
            if rule.method == "sum":
                result[col] = df[col].sum()
            elif rule.method == "mean":
                result[col] = df[col].mean()
            elif rule.method == "weighted_mean" and rule.weight_column in df.columns:
                result[col] = np.average(df[col], weights=df[rule.weight_column])
            elif rule.method == "first":
                result[col] = df[col].iloc[0] if len(df) > 0 else None

        if include_count:
            result["_row_count"] = len(df)

        result_df = pd.DataFrame([result])

        # Calculate derived metrics
        for metric in self._metrics_list:
            if metric.metric_type == "derived" and metric.derived_formula:
                try:
                    result_df[metric.column] = eval(
                        metric.derived_formula,
                        {"__builtins__": {}},
                        {"df": result_df, "np": np},
                    )
                except Exception:
                    result_df[metric.column] = np.nan

        return result_df

    def validate_granularity(
        self,
        granularity: GranularitySpec,
    ) -> dict[str, Any]:
        """
        Validate that granularity spec is achievable with current dataset.

        Returns:
            Validation result with issues and warnings
        """
        result = {
            "valid": True,
            "issues": [],
            "warnings": [],
            "estimated_rows": None,
        }

        missing_dims = []
        missing_cols = []

        for dim_name, level_name in granularity.dimensions.items():
            dim = self.dimensions.get(dim_name)
            if dim is None:
                missing_dims.append(dim_name)
                continue

            level = dim.get_level(level_name)
            if level is None:
                result["issues"].append(f"Level '{level_name}' not found in dimension '{dim_name}'")
                result["valid"] = False
                continue

            if level.column is not None and level.column not in self.df.columns:
                missing_cols.append(level.column)

        if missing_dims:
            result["issues"].append(f"Dimensions not configured: {missing_dims}")
            result["valid"] = False

        if missing_cols:
            result["issues"].append(f"Columns not found in dataset: {missing_cols}")
            result["valid"] = False

        # Check filters
        for col, values in granularity.filters.items():
            if col not in self.df.columns:
                result["warnings"].append(f"Filter column '{col}' not found, will be ignored")
            else:
                actual_values = set(self.df[col].unique())
                missing_values = set(values) - actual_values
                if missing_values:
                    result["warnings"].append(f"Filter values not found in '{col}': {list(missing_values)[:5]}")

        # Estimate result rows
        if result["valid"]:
            groupby_cols = self._get_groupby_columns(granularity)
            if groupby_cols:
                filtered_df = self._apply_filters(self.df, granularity.filters)
                result["estimated_rows"] = filtered_df.groupby(groupby_cols).ngroups
            else:
                result["estimated_rows"] = 1

        return result

    def preview_aggregation(
        self,
        granularity: GranularitySpec,
        sample_size: int = 10,
    ) -> dict[str, Any]:
        """
        Preview aggregation result.

        Args:
            granularity: Target granularity
            sample_size: Number of rows to show

        Returns:
            Preview with sample data and statistics
        """
        validation = self.validate_granularity(granularity)

        if not validation["valid"]:
            return {
                "valid": False,
                "issues": validation["issues"],
            }

        result_df = self.aggregate(granularity)

        return {
            "valid": True,
            "total_rows": len(result_df),
            "columns": result_df.columns.tolist(),
            "sample": result_df.head(sample_size).to_dict(orient="records"),
            "groupby_columns": self._get_groupby_columns(granularity),
        }

    def get_available_granularities(self) -> list[dict[str, Any]]:
        """
        Get all possible granularity combinations.

        Returns:
            List of possible granularity specs with estimated row counts
        """
        granularities = []

        # Generate combinations for each dimension
        for dim_name, dim in self.dimensions.items():
            for level in dim.levels:
                if level.column is None:
                    continue  # Skip aggregated levels for now

                if level.column in self.df.columns:
                    unique_count = self.df[level.column].nunique()
                    granularities.append(
                        {
                            "dimension": dim_name,
                            "level": level.name,
                            "column": level.column,
                            "unique_values": unique_count,
                        }
                    )

        return granularities
