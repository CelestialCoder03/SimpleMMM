"""Tests for data exploration service."""

import numpy as np
import pandas as pd
import pytest


class TestDataExplorer:
    """Tests for DataExplorer."""

    @pytest.fixture
    def sample_df(self):
        """Create sample dataframe for testing."""
        np.random.seed(42)
        n = 100

        return pd.DataFrame(
            {
                "date": pd.date_range("2023-01-01", periods=n, freq="W"),
                "sales": np.random.normal(10000, 2000, n),
                "tv_spend": np.random.uniform(1000, 5000, n),
                "radio_spend": np.random.uniform(500, 2000, n),
                "province": np.random.choice(["Beijing", "Shanghai", "Guangdong"], n),
                "channel": np.random.choice(["Online", "Offline"], n),
                "price": np.random.uniform(10, 50, n),
            }
        )

    def test_get_summary(self, sample_df):
        """Test summary statistics."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        summary = explorer.get_summary()

        assert summary["n_rows"] == 100
        assert summary["n_columns"] == 7
        assert len(summary["columns"]) == 7
        assert "sales" in summary["numeric_columns"]
        assert "province" in summary["categorical_columns"]

    def test_column_stats_numeric(self, sample_df):
        """Test numeric column statistics."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        stats = explorer._get_column_stats("sales")

        assert stats.name == "sales"
        assert stats.count == 100
        assert stats.missing == 0
        assert stats.mean is not None
        assert stats.std is not None
        assert stats.min is not None
        assert stats.max is not None

    def test_column_stats_categorical(self, sample_df):
        """Test categorical column statistics."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        stats = explorer._get_column_stats("province")

        assert stats.name == "province"
        assert stats.unique == 3
        assert stats.top_values is not None
        assert len(stats.top_values) <= 10

    def test_analyze_distribution_numeric(self, sample_df):
        """Test numeric distribution analysis."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        dist = explorer.analyze_distribution("sales", n_bins=20)

        assert dist.column == "sales"
        assert dist.histogram is not None
        assert len(dist.histogram["counts"]) == 20
        assert dist.normality_test is not None
        assert dist.outliers is not None

    def test_analyze_distribution_categorical(self, sample_df):
        """Test categorical distribution analysis."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        dist = explorer.analyze_distribution("province")

        assert dist.column == "province"
        assert dist.value_counts is not None
        assert len(dist.value_counts) == 3

    def test_analyze_time_series(self, sample_df):
        """Test time series analysis."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        ts = explorer.analyze_time_series("date", "sales")

        assert ts.date_column == "date"
        assert ts.value_column == "sales"
        assert ts.n_periods == 100
        assert len(ts.dates) == 100
        assert len(ts.values) == 100
        assert ts.trend is not None
        assert ts.autocorrelation is not None

    def test_analyze_missing(self, sample_df):
        """Test missing value analysis."""
        from app.services.exploration.analyzer import DataExplorer

        # Add some missing values
        df = sample_df.copy()
        df.loc[0:5, "sales"] = np.nan
        df.loc[3:8, "tv_spend"] = np.nan

        explorer = DataExplorer(df)
        missing = explorer.analyze_missing()

        assert missing.total_rows == 100
        assert missing.total_missing > 0
        assert len(missing.columns) == 7
        assert missing.complete_rows < 100

    def test_get_correlations(self, sample_df):
        """Test correlation analysis."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        corr = explorer.get_correlations(
            columns=["sales", "tv_spend", "radio_spend"],
            threshold=0.1,
        )

        assert corr.method == "pearson"
        assert len(corr.columns) == 3
        assert len(corr.matrix) == 3
        assert len(corr.matrix[0]) == 3

    def test_get_aggregated_preview(self, sample_df):
        """Test aggregated preview."""
        from app.services.exploration.analyzer import DataExplorer

        explorer = DataExplorer(sample_df)
        preview = explorer.get_aggregated_preview(
            group_by=["province"],
            agg_columns={"sales": "sum", "tv_spend": "sum"},
            limit=10,
        )

        assert preview["n_groups"] == 3
        assert len(preview["data"]) == 3
        assert "province" in preview["columns"]


class TestDistributionResult:
    """Tests for DistributionResult."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from app.services.exploration.analyzer import DistributionResult

        result = DistributionResult(
            column="test",
            dtype="float64",
            histogram={"counts": [1, 2, 3], "bins": [0, 1, 2]},
        )

        data = result.to_dict()

        assert data["column"] == "test"
        assert data["histogram"] is not None


class TestTimeSeriesResult:
    """Tests for TimeSeriesResult."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from app.services.exploration.analyzer import TimeSeriesResult

        result = TimeSeriesResult(
            date_column="date",
            value_column="sales",
            frequency="weekly",
            n_periods=10,
            date_range=("2023-01-01", "2023-03-01"),
            dates=["2023-01-01"],
            values=[100.0],
        )

        data = result.to_dict()

        assert data["date_column"] == "date"
        assert data["frequency"] == "weekly"
        assert data["n_periods"] == 10
