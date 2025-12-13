"""Data exploration and analysis service."""

from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class ColumnStats:
    """Statistics for a single column."""

    name: str
    dtype: str
    count: int
    missing: int
    missing_pct: float
    unique: int

    # Numeric stats (None for non-numeric)
    mean: float | None = None
    std: float | None = None
    min: float | None = None
    q25: float | None = None
    median: float | None = None
    q75: float | None = None
    max: float | None = None
    skewness: float | None = None
    kurtosis: float | None = None

    # Categorical stats (None for numeric)
    top_values: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class DistributionResult:
    """Distribution analysis result."""

    column: str
    dtype: str

    # For numeric columns
    histogram: dict[str, list] | None = None  # {bins, counts, bin_edges}
    kde: dict[str, list] | None = None  # {x, y} for kernel density
    normality_test: dict[str, float] | None = None  # {statistic, p_value}
    outliers: dict[str, Any] | None = None  # {count, pct, lower_bound, upper_bound, values}

    # For categorical columns
    value_counts: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class TimeSeriesResult:
    """Time series analysis result."""

    date_column: str
    value_column: str
    frequency: str  # 'daily', 'weekly', 'monthly', etc.
    n_periods: int
    date_range: tuple[str, str]

    # Time series data
    dates: list[str] = field(default_factory=list)
    values: list[float] = field(default_factory=list)

    # Trend analysis
    trend: list[float] | None = None
    seasonality: dict[str, float] | None = None  # {period: strength}

    # Statistics
    mean: float = 0.0
    std: float = 0.0
    cv: float = 0.0  # Coefficient of variation
    autocorrelation: list[float] | None = None  # ACF values

    def to_dict(self) -> dict[str, Any]:
        return {
            "date_column": self.date_column,
            "value_column": self.value_column,
            "frequency": self.frequency,
            "n_periods": self.n_periods,
            "date_range": self.date_range,
            "dates": self.dates,
            "values": self.values,
            "trend": self.trend,
            "seasonality": self.seasonality,
            "mean": self.mean,
            "std": self.std,
            "cv": self.cv,
            "autocorrelation": self.autocorrelation,
        }


@dataclass
class MissingValueResult:
    """Missing value analysis result."""

    total_rows: int
    total_cells: int
    total_missing: int
    total_missing_pct: float
    complete_rows: int
    complete_rows_pct: float

    # Per-column missing
    columns: list[dict[str, Any]] = field(default_factory=list)

    # Missing patterns
    patterns: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


@dataclass
class CorrelationResult:
    """Correlation analysis result."""

    method: str  # 'pearson', 'spearman', 'kendall'
    columns: list[str]
    matrix: list[list[float]]

    # Significant correlations
    significant_pairs: list[dict[str, Any]] | None = None

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__


class DataExplorer:
    """
    Comprehensive data exploration and analysis service.

    Provides:
    - Summary statistics
    - Distribution analysis
    - Time series preview
    - Correlation analysis
    - Missing value analysis

    Usage:
        explorer = DataExplorer(df)

        # Get full summary
        summary = explorer.get_summary()

        # Analyze specific column distribution
        dist = explorer.analyze_distribution('sales')

        # Get correlation matrix
        corr = explorer.get_correlations(['tv_spend', 'sales'])
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initialize explorer with dataframe.

        Args:
            df: Pandas DataFrame to explore
        """
        self.df = df
        self._numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        self._categorical_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
        self._datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    def get_summary(self) -> dict[str, Any]:
        """
        Get comprehensive summary statistics for all columns.

        Returns:
            Dictionary with overall stats and per-column stats
        """
        n_rows, n_cols = self.df.shape

        # Overall stats
        total_missing = self.df.isna().sum().sum()
        memory_mb = self.df.memory_usage(deep=True).sum() / 1024 / 1024

        # Per-column stats
        columns = []
        for col in self.df.columns:
            columns.append(self._get_column_stats(col).to_dict())

        return {
            "n_rows": n_rows,
            "n_columns": n_cols,
            "memory_mb": round(memory_mb, 2),
            "total_missing": int(total_missing),
            "total_missing_pct": round(total_missing / (n_rows * n_cols) * 100, 2),
            "numeric_columns": self._numeric_cols,
            "categorical_columns": self._categorical_cols,
            "datetime_columns": self._datetime_cols,
            "columns": columns,
        }

    def _get_column_stats(self, column: str) -> ColumnStats:
        """Get statistics for a single column."""
        col = self.df[column]

        base_stats = {
            "name": column,
            "dtype": str(col.dtype),
            "count": int(col.count()),
            "missing": int(col.isna().sum()),
            "missing_pct": round(col.isna().mean() * 100, 2),
            "unique": int(col.nunique()),
        }

        if column in self._numeric_cols:
            # Numeric statistics
            desc = col.describe()
            base_stats.update(
                {
                    "mean": float(desc["mean"]) if pd.notna(desc["mean"]) else None,
                    "std": float(desc["std"]) if pd.notna(desc["std"]) else None,
                    "min": float(desc["min"]) if pd.notna(desc["min"]) else None,
                    "q25": float(desc["25%"]) if pd.notna(desc["25%"]) else None,
                    "median": float(desc["50%"]) if pd.notna(desc["50%"]) else None,
                    "q75": float(desc["75%"]) if pd.notna(desc["75%"]) else None,
                    "max": float(desc["max"]) if pd.notna(desc["max"]) else None,
                    "skewness": float(col.skew()) if col.count() > 2 else None,
                    "kurtosis": float(col.kurtosis()) if col.count() > 3 else None,
                }
            )
        else:
            # Categorical statistics
            value_counts = col.value_counts().head(10)
            top_values = [
                {"value": str(v), "count": int(c), "pct": round(c / len(col) * 100, 2)} for v, c in value_counts.items()
            ]
            base_stats["top_values"] = top_values

        return ColumnStats(**base_stats)

    def analyze_distribution(
        self,
        column: str,
        n_bins: int = 30,
        include_kde: bool = True,
    ) -> DistributionResult:
        """
        Analyze distribution of a column.

        Args:
            column: Column name to analyze
            n_bins: Number of histogram bins for numeric columns
            include_kde: Whether to include kernel density estimation

        Returns:
            DistributionResult with histogram, KDE, normality test, outliers
        """
        col = self.df[column].dropna()
        dtype = str(self.df[column].dtype)

        result = DistributionResult(column=column, dtype=dtype)

        if column in self._numeric_cols:
            # Histogram
            counts, bin_edges = np.histogram(col, bins=n_bins)
            result.histogram = {
                "counts": counts.tolist(),
                "bin_edges": bin_edges.tolist(),
                "bins": [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)],
            }

            # KDE
            if include_kde and len(col) > 10:
                try:
                    kde = stats.gaussian_kde(col)
                    x_range = np.linspace(col.min(), col.max(), 100)
                    result.kde = {
                        "x": x_range.tolist(),
                        "y": kde(x_range).tolist(),
                    }
                except Exception:
                    pass  # KDE can fail for degenerate data

            # Normality test (Shapiro-Wilk for small samples, D'Agostino for large)
            if len(col) >= 20:
                if len(col) <= 5000:
                    stat, p_value = stats.shapiro(col.sample(min(len(col), 5000)))
                    test_name = "shapiro"
                else:
                    stat, p_value = stats.normaltest(col)
                    test_name = "dagostino"

                result.normality_test = {
                    "test": test_name,
                    "statistic": float(stat),
                    "p_value": float(p_value),
                    "is_normal": bool(p_value > 0.05),
                }

            # Outliers (IQR method)
            q1, q3 = col.quantile([0.25, 0.75])
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            outliers = col[(col < lower_bound) | (col > upper_bound)]

            result.outliers = {
                "count": len(outliers),
                "pct": round(len(outliers) / len(col) * 100, 2),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "lower_outliers": int((col < lower_bound).sum()),
                "upper_outliers": int((col > upper_bound).sum()),
            }
        else:
            # Categorical value counts
            value_counts = col.value_counts()
            result.value_counts = [
                {"value": str(v), "count": int(c), "pct": round(c / len(col) * 100, 2)} for v, c in value_counts.items()
            ]

        return result

    def analyze_time_series(
        self,
        date_column: str,
        value_column: str,
        freq: str | None = None,
        include_trend: bool = True,
        acf_lags: int = 20,
    ) -> TimeSeriesResult:
        """
        Analyze time series data.

        Args:
            date_column: Name of date/time column
            value_column: Name of value column
            freq: Frequency hint ('D', 'W', 'M', 'Q', 'Y') or None to auto-detect
            include_trend: Whether to compute trend line
            acf_lags: Number of lags for autocorrelation

        Returns:
            TimeSeriesResult with dates, values, trend, ACF
        """
        # Prepare data
        df = self.df[[date_column, value_column]].dropna().copy()
        df[date_column] = pd.to_datetime(df[date_column])
        df = df.sort_values(date_column)

        # Detect frequency
        if freq is None:
            freq = self._detect_frequency(df[date_column])

        dates = df[date_column].dt.strftime("%Y-%m-%d").tolist()
        values = df[value_column].tolist()

        result = TimeSeriesResult(
            date_column=date_column,
            value_column=value_column,
            frequency=freq,
            n_periods=len(df),
            date_range=(dates[0], dates[-1]),
            dates=dates,
            values=values,
            mean=float(df[value_column].mean()),
            std=float(df[value_column].std()),
            cv=float(df[value_column].std() / df[value_column].mean()) if df[value_column].mean() != 0 else 0,
        )

        # Trend (simple linear)
        if include_trend and len(df) > 2:
            x = np.arange(len(df))
            slope, intercept, _, _, _ = stats.linregress(x, df[value_column])
            result.trend = (slope * x + intercept).tolist()

        # Autocorrelation
        if len(df) > acf_lags + 1:
            acf_values = self._compute_acf(df[value_column].values, acf_lags)
            result.autocorrelation = acf_values

        # Seasonality detection (basic)
        if len(df) >= 12:
            result.seasonality = self._detect_seasonality(df[value_column].values, freq)

        return result

    def _detect_frequency(self, dates: pd.Series) -> str:
        """Auto-detect time series frequency."""
        if len(dates) < 2:
            return "unknown"

        diff = dates.diff().dropna()
        median_diff = diff.median().days

        if median_diff <= 1:
            return "daily"
        elif median_diff <= 7:
            return "weekly"
        elif median_diff <= 31:
            return "monthly"
        elif median_diff <= 92:
            return "quarterly"
        else:
            return "yearly"

    def _compute_acf(self, values: np.ndarray, max_lag: int) -> list[float]:
        """Compute autocorrelation function."""
        n = len(values)
        mean = values.mean()
        var = np.var(values)

        if var == 0:
            return [1.0] + [0.0] * max_lag

        acf = []
        for lag in range(max_lag + 1):
            if lag == 0:
                acf.append(1.0)
            else:
                cov = np.sum((values[lag:] - mean) * (values[:-lag] - mean)) / n
                acf.append(float(cov / var))

        return acf

    def _detect_seasonality(
        self,
        values: np.ndarray,
        freq: str,
    ) -> dict[str, float]:
        """Basic seasonality detection using autocorrelation peaks."""
        seasonality = {}

        # Expected seasonal periods
        periods = {
            "daily": [7, 30, 365],
            "weekly": [4, 12, 52],
            "monthly": [3, 6, 12],
            "quarterly": [4],
            "yearly": [],
        }

        check_periods = periods.get(freq, [])

        if len(values) > max(check_periods, default=0) + 1:
            acf = self._compute_acf(values, max(check_periods, default=10))

            for period in check_periods:
                if period < len(acf):
                    strength = abs(acf[period])
                    if strength > 0.3:  # Significant correlation
                        seasonality[f"period_{period}"] = round(strength, 3)

        return seasonality

    def analyze_missing(self) -> MissingValueResult:
        """
        Analyze missing values in the dataset.

        Returns:
            MissingValueResult with overall and per-column missing stats
        """
        n_rows, n_cols = self.df.shape
        total_cells = n_rows * n_cols

        # Per-column missing
        missing_per_col = self.df.isna().sum()
        columns = []
        for col in self.df.columns:
            missing = int(missing_per_col[col])
            columns.append(
                {
                    "column": col,
                    "missing": missing,
                    "missing_pct": round(missing / n_rows * 100, 2),
                    "dtype": str(self.df[col].dtype),
                }
            )

        # Sort by missing count descending
        columns = sorted(columns, key=lambda x: x["missing"], reverse=True)

        # Complete rows
        complete_mask = self.df.notna().all(axis=1)
        complete_rows = int(complete_mask.sum())

        # Missing patterns (which columns tend to be missing together)
        patterns = self._analyze_missing_patterns()

        return MissingValueResult(
            total_rows=n_rows,
            total_cells=total_cells,
            total_missing=int(missing_per_col.sum()),
            total_missing_pct=round(missing_per_col.sum() / total_cells * 100, 2),
            complete_rows=complete_rows,
            complete_rows_pct=round(complete_rows / n_rows * 100, 2),
            columns=columns,
            patterns=patterns,
        )

    def _analyze_missing_patterns(self, max_patterns: int = 10) -> list[dict[str, Any]]:
        """Identify common missing value patterns."""
        # Create a boolean mask for missing values
        missing_mask = self.df.isna()

        # Group rows by their missing pattern
        pattern_counts = missing_mask.groupby(missing_mask.apply(tuple, axis=1)).size().sort_values(ascending=False)

        patterns = []
        for pattern, count in pattern_counts.head(max_patterns).items():
            missing_cols = [col for col, is_missing in zip(self.df.columns, pattern) if is_missing]
            if missing_cols:  # Only include patterns with at least one missing
                patterns.append(
                    {
                        "missing_columns": missing_cols,
                        "count": int(count),
                        "pct": round(count / len(self.df) * 100, 2),
                    }
                )

        return patterns

    def get_correlations(
        self,
        columns: list[str] | None = None,
        method: Literal["pearson", "spearman", "kendall"] = "pearson",
        threshold: float = 0.5,
    ) -> CorrelationResult:
        """
        Compute correlation matrix.

        Args:
            columns: Columns to include (defaults to all numeric)
            method: Correlation method
            threshold: Threshold for significant correlations

        Returns:
            CorrelationResult with matrix and significant pairs
        """
        if columns is None:
            columns = self._numeric_cols
        else:
            columns = [c for c in columns if c in self._numeric_cols]

        if len(columns) < 2:
            raise ValueError("Need at least 2 numeric columns for correlation")

        # Compute correlation matrix
        corr_df = self.df[columns].corr(method=method)

        # Find significant correlations
        significant_pairs = []
        for i, col1 in enumerate(columns):
            for j, col2 in enumerate(columns):
                if i < j:  # Upper triangle only
                    corr_value = corr_df.loc[col1, col2]
                    if abs(corr_value) >= threshold:
                        significant_pairs.append(
                            {
                                "var1": col1,
                                "var2": col2,
                                "correlation": round(float(corr_value), 3),
                                "strength": self._correlation_strength(abs(corr_value)),
                            }
                        )

        # Sort by absolute correlation
        significant_pairs = sorted(
            significant_pairs,
            key=lambda x: abs(x["correlation"]),
            reverse=True,
        )

        return CorrelationResult(
            method=method,
            columns=columns,
            matrix=corr_df.values.tolist(),
            significant_pairs=significant_pairs,
        )

    def _correlation_strength(self, r: float) -> str:
        """Classify correlation strength."""
        if r >= 0.9:
            return "very_strong"
        elif r >= 0.7:
            return "strong"
        elif r >= 0.5:
            return "moderate"
        elif r >= 0.3:
            return "weak"
        else:
            return "negligible"

    def get_aggregated_preview(
        self,
        group_by: list[str],
        agg_columns: dict[str, str],
        sort_by: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        Preview data aggregated by specified columns.

        Args:
            group_by: Columns to group by
            agg_columns: {column: agg_func} mapping
            sort_by: Column to sort by
            limit: Max rows to return

        Returns:
            Aggregated data preview
        """
        # Validate columns
        for col in group_by:
            if col not in self.df.columns:
                raise ValueError(f"Column not found: {col}")

        for col in agg_columns:
            if col not in self.df.columns:
                raise ValueError(f"Column not found: {col}")

        # Perform aggregation
        result_df = self.df.groupby(group_by, as_index=False).agg(agg_columns)

        # Sort
        if sort_by and sort_by in result_df.columns:
            result_df = result_df.sort_values(sort_by, ascending=False)

        # Limit
        result_df = result_df.head(limit)

        return {
            "columns": result_df.columns.tolist(),
            "data": result_df.values.tolist(),
            "n_groups": len(self.df.groupby(group_by)),
            "n_rows_shown": len(result_df),
        }
