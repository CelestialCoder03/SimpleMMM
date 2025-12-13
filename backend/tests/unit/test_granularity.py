"""Tests for multi-granularity modeling services."""

import numpy as np
import pandas as pd
import pytest


class TestDimension:
    """Tests for Dimension and DimensionLevel."""

    def test_dimension_level_creation(self):
        """Test creating a dimension level."""
        from app.services.granularity.dimensions import DimensionLevel

        level = DimensionLevel(
            name="province",
            column="province",
            display_name="Province",
            order=2,
        )

        assert level.name == "province"
        assert level.column == "province"
        assert level.order == 2

    def test_dimension_creation(self):
        """Test creating a dimension with levels."""
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        dim = Dimension(
            name="geography",
            display_name="Geography",
            levels=[
                DimensionLevel("national", None, "National", 0),
                DimensionLevel("province", "province", "Province", 1),
                DimensionLevel("city", "city", "City", 2),
            ],
        )

        assert dim.name == "geography"
        assert len(dim.levels) == 3

    def test_get_level(self):
        """Test getting a level by name."""
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        dim = Dimension(
            name="geography",
            display_name="Geography",
            levels=[
                DimensionLevel("national", None, "National", 0),
                DimensionLevel("province", "province", "Province", 1),
            ],
        )

        level = dim.get_level("province")
        assert level is not None
        assert level.column == "province"

        assert dim.get_level("unknown") is None

    def test_get_parent_child_level(self):
        """Test getting parent and child levels."""
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        dim = Dimension(
            name="geography",
            display_name="Geography",
            levels=[
                DimensionLevel("national", None, "National", 0),
                DimensionLevel("province", "province", "Province", 1),
                DimensionLevel("city", "city", "City", 2),
            ],
        )

        parent = dim.get_parent_level("province")
        assert parent.name == "national"

        child = dim.get_child_level("province")
        assert child.name == "city"

        assert dim.get_parent_level("national") is None
        assert dim.get_child_level("city") is None

    def test_is_ancestor(self):
        """Test ancestor relationship check."""
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        dim = Dimension(
            name="geography",
            display_name="Geography",
            levels=[
                DimensionLevel("national", None, "National", 0),
                DimensionLevel("province", "province", "Province", 1),
                DimensionLevel("city", "city", "City", 2),
            ],
        )

        assert dim.is_ancestor("national", "city") is True
        assert dim.is_ancestor("city", "national") is False
        assert dim.is_ancestor("province", "province") is False

    def test_to_dict_from_dict(self):
        """Test serialization roundtrip."""
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        dim = Dimension(
            name="geography",
            display_name="Geography",
            levels=[
                DimensionLevel("national", None, "National", 0),
                DimensionLevel("province", "province", "Province", 1),
            ],
        )

        data = dim.to_dict()
        restored = Dimension.from_dict(data)

        assert restored.name == dim.name
        assert len(restored.levels) == len(dim.levels)


class TestDimensionRegistry:
    """Tests for DimensionRegistry."""

    def test_default_dimensions(self):
        """Test default dimension configurations."""
        from app.services.granularity.dimensions import DimensionRegistry

        registry = DimensionRegistry()

        # Check default dimensions exist
        time_dim = registry.get("time")
        assert time_dim is not None
        assert time_dim.get_level("month") is not None

        geo_dim = registry.get("geography")
        assert geo_dim is not None
        assert geo_dim.get_level("province") is not None

        channel_dim = registry.get("channel")
        assert channel_dim is not None

    def test_create_custom_dimension(self):
        """Test creating a custom dimension."""
        from app.services.granularity.dimensions import DimensionRegistry

        registry = DimensionRegistry()

        dim = registry.create_custom(
            name="product",
            display_name="Product",
            levels=[
                {"name": "all", "column": None},
                {"name": "category", "column": "category"},
                {"name": "sku", "column": "sku"},
            ],
        )

        assert dim.name == "product"
        assert len(dim.levels) == 3
        assert registry.get("product") is not None

    def test_auto_detect_dimensions(self):
        """Test auto-detection of dimensions from dataset."""
        from app.services.granularity.dimensions import DimensionRegistry

        registry = DimensionRegistry()

        df = pd.DataFrame(
            {
                "month": ["2023-01", "2023-02"],
                "province": ["Beijing", "Shanghai"],
                "channel": ["Online", "Offline"],
                "sales": [100, 200],
            }
        )

        suggestions = registry.auto_detect_dimensions(df)

        # Should detect time, geography, and channel
        dim_names = [s["dimension"] for s in suggestions]
        assert "time" in dim_names
        assert "geography" in dim_names
        assert "channel" in dim_names


class TestGranularityManager:
    """Tests for GranularityManager."""

    @pytest.fixture
    def sample_data(self):
        """Create sample hierarchical data."""
        np.random.seed(42)

        provinces = ["Beijing", "Shanghai", "Guangdong"]
        cities = {
            "Beijing": ["Chaoyang", "Haidian"],
            "Shanghai": ["Pudong", "Huangpu"],
            "Guangdong": ["Guangzhou", "Shenzhen"],
        }
        channels = ["Online", "Offline"]
        months = pd.date_range("2023-01", periods=12, freq="ME").strftime("%Y-%m").tolist()

        rows = []
        for month in months:
            for province in provinces:
                for city in cities[province]:
                    for channel in channels:
                        rows.append(
                            {
                                "month": month,
                                "province": province,
                                "city": city,
                                "channel": channel,
                                "sales": np.random.uniform(1000, 5000),
                                "spend": np.random.uniform(100, 500),
                                "units": np.random.randint(10, 100),
                            }
                        )

        return pd.DataFrame(rows)

    @pytest.fixture
    def dimensions(self):
        """Create dimension configurations."""
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        return [
            Dimension(
                name="time",
                display_name="Time",
                levels=[
                    DimensionLevel("all_time", None, "All Time", 0),
                    DimensionLevel("month", "month", "Month", 1),
                ],
            ),
            Dimension(
                name="geography",
                display_name="Geography",
                levels=[
                    DimensionLevel("national", None, "National", 0),
                    DimensionLevel("province", "province", "Province", 1),
                    DimensionLevel("city", "city", "City", 2),
                ],
            ),
            Dimension(
                name="channel",
                display_name="Channel",
                levels=[
                    DimensionLevel("all_channels", None, "All Channels", 0),
                    DimensionLevel("channel", "channel", "Channel", 1),
                ],
            ),
        ]

    @pytest.fixture
    def metrics(self):
        """Create metric definitions."""
        from app.services.granularity.aggregation import (
            AggregationRule,
            MetricDefinition,
        )

        return [
            MetricDefinition(
                name="sales",
                column="sales",
                metric_type="additive",
                aggregation=AggregationRule("sales", "sum"),
            ),
            MetricDefinition(
                name="spend",
                column="spend",
                metric_type="additive",
                aggregation=AggregationRule("spend", "sum"),
            ),
            MetricDefinition(
                name="units",
                column="units",
                metric_type="additive",
                aggregation=AggregationRule("units", "sum"),
            ),
        ]

    def test_aggregate_to_province(self, sample_data, dimensions, metrics):
        """Test aggregation to province level."""
        from app.services.granularity.aggregation import (
            GranularityManager,
            GranularitySpec,
        )

        manager = GranularityManager(sample_data, dimensions, metrics)

        spec = GranularitySpec(
            name="province_monthly",
            dimensions={
                "time": "month",
                "geography": "province",
                "channel": "all_channels",
            },
        )

        result = manager.aggregate(spec)

        # Should have 12 months * 3 provinces = 36 rows
        assert len(result) == 36
        assert "province" in result.columns
        assert "month" in result.columns
        assert "sales" in result.columns

    def test_aggregate_to_national(self, sample_data, dimensions, metrics):
        """Test aggregation to national (fully aggregated) level."""
        from app.services.granularity.aggregation import (
            GranularityManager,
            GranularitySpec,
        )

        manager = GranularityManager(sample_data, dimensions, metrics)

        spec = GranularitySpec(
            name="national_monthly",
            dimensions={
                "time": "month",
                "geography": "national",
                "channel": "all_channels",
            },
        )

        result = manager.aggregate(spec)

        # Should have 12 months
        assert len(result) == 12
        assert "month" in result.columns

    def test_aggregate_with_filter(self, sample_data, dimensions, metrics):
        """Test aggregation with filters."""
        from app.services.granularity.aggregation import (
            GranularityManager,
            GranularitySpec,
        )

        manager = GranularityManager(sample_data, dimensions, metrics)

        spec = GranularitySpec(
            name="beijing_monthly",
            dimensions={
                "time": "month",
                "geography": "city",
                "channel": "channel",
            },
            filters={"province": ["Beijing"]},
        )

        result = manager.aggregate(spec)

        # Should only have Beijing cities
        assert set(result["city"].unique()) == {"Chaoyang", "Haidian"}

    def test_validate_granularity(self, sample_data, dimensions, metrics):
        """Test granularity validation."""
        from app.services.granularity.aggregation import (
            GranularityManager,
            GranularitySpec,
        )

        manager = GranularityManager(sample_data, dimensions, metrics)

        # Valid spec
        valid_spec = GranularitySpec(
            name="valid",
            dimensions={"time": "month", "geography": "province"},
        )

        validation = manager.validate_granularity(valid_spec)
        assert validation["valid"] is True
        assert validation["estimated_rows"] == 36

    def test_preview_aggregation(self, sample_data, dimensions, metrics):
        """Test aggregation preview."""
        from app.services.granularity.aggregation import (
            GranularityManager,
            GranularitySpec,
        )

        manager = GranularityManager(sample_data, dimensions, metrics)

        spec = GranularitySpec(
            name="preview_test",
            dimensions={"time": "month", "geography": "province"},
        )

        preview = manager.preview_aggregation(spec, sample_size=5)

        assert preview["valid"] is True
        assert preview["total_rows"] == 36
        assert len(preview["sample"]) == 5


class TestReportSpec:
    """Tests for ReportSpec."""

    def test_report_spec_creation(self):
        """Test creating a report specification."""
        from app.services.granularity.aggregation import GranularitySpec
        from app.services.granularity.reports import ReportSpec

        spec = ReportSpec(
            name="national_report",
            granularity=GranularitySpec(
                name="national_monthly",
                dimensions={"time": "month", "geography": "national"},
            ),
            model_type="ridge",
            features=["spend"],
            target="sales",
        )

        assert spec.name == "national_report"
        assert spec.model_type == "ridge"
        assert spec.inherit_constraints is False

    def test_report_spec_with_inheritance(self):
        """Test report specification with inheritance enabled."""
        from app.services.granularity.aggregation import GranularitySpec
        from app.services.granularity.reports import ReportSpec

        spec = ReportSpec(
            name="province_report",
            granularity=GranularitySpec(
                name="province_monthly",
                dimensions={"time": "month", "geography": "province"},
            ),
            model_type="ridge",
            features=["spend"],
            target="sales",
            parent_report="national_report",
            inherit_constraints=True,
            inherit_priors=True,
            prior_strength=0.7,
        )

        assert spec.parent_report == "national_report"
        assert spec.inherit_constraints is True
        assert spec.inherit_priors is True
        assert spec.prior_strength == 0.7


class TestConstraintInheritance:
    """Tests for ConstraintInheritance."""

    def test_merge_constraints_basic(self):
        """Test basic constraint merging."""
        from app.services.granularity.reports import ConstraintInheritance

        parent = {"spend": {"sign": "positive"}}
        child = {"price": {"min": 0}}

        merged = ConstraintInheritance.merge_constraints(parent, child, None)

        assert "spend" in merged
        assert "price" in merged
        assert merged["spend"]["sign"] == "positive"

    def test_merge_constraints_override(self):
        """Test constraint override."""
        from app.services.granularity.reports import ConstraintInheritance

        parent = {"spend": {"sign": "positive", "max": 100}}
        child = {"spend": {"max": 50}}
        override = {"spend": {"max": 75}}

        merged = ConstraintInheritance.merge_constraints(parent, child, override)

        assert merged["spend"]["sign"] == "positive"  # From parent
        assert merged["spend"]["max"] == 75  # From override


class TestPriorInheritance:
    """Tests for PriorInheritance."""

    def test_create_child_priors(self):
        """Test creating child priors from parent result."""
        from app.services.granularity.reports import PriorInheritance

        parent_result = {
            "model_result": {
                "coefficients": {"spend": 0.5, "price": -0.1},
                "std_errors": {"spend": 0.1, "price": 0.05},
            }
        }

        priors = PriorInheritance.create_child_priors(
            parent_result,
            prior_strength=0.5,
        )

        assert "spend" in priors
        assert "price" in priors
        assert priors["spend"]["mean"] == 0.5
        assert priors["spend"]["distribution"] == "normal"

    def test_prior_strength_effect(self):
        """Test that prior strength affects variance."""
        from app.services.granularity.reports import PriorInheritance

        parent_result = {
            "model_result": {
                "coefficients": {"spend": 0.5},
                "std_errors": {"spend": 0.1},
            }
        }

        strong_priors = PriorInheritance.create_child_priors(parent_result, prior_strength=1.0)
        weak_priors = PriorInheritance.create_child_priors(parent_result, prior_strength=0.1)

        # Weaker prior strength = larger std (less influence)
        assert weak_priors["spend"]["std"] > strong_priors["spend"]["std"]


class TestReportGenerator:
    """Tests for ReportGenerator."""

    @pytest.fixture
    def sample_setup(self):
        """Create sample setup for report generation."""
        from app.services.granularity.aggregation import (
            AggregationRule,
            GranularityManager,
            MetricDefinition,
        )
        from app.services.granularity.dimensions import Dimension, DimensionLevel

        np.random.seed(42)

        # Create sample data
        provinces = ["Beijing", "Shanghai"]
        months = ["2023-01", "2023-02", "2023-03"]

        rows = []
        for month in months:
            for province in provinces:
                rows.append(
                    {
                        "month": month,
                        "province": province,
                        "sales": np.random.uniform(1000, 5000),
                        "spend": np.random.uniform(100, 500),
                    }
                )

        df = pd.DataFrame(rows)

        dimensions = [
            Dimension(
                "time",
                "Time",
                [
                    DimensionLevel("month", "month", "Month", 0),
                ],
            ),
            Dimension(
                "geography",
                "Geography",
                [
                    DimensionLevel("national", None, "National", 0),
                    DimensionLevel("province", "province", "Province", 1),
                ],
            ),
        ]

        metrics = [
            MetricDefinition("sales", "sales", "additive", AggregationRule("sales", "sum")),
            MetricDefinition("spend", "spend", "additive", AggregationRule("spend", "sum")),
        ]

        manager = GranularityManager(df, dimensions, metrics)

        return manager, df

    def test_generate_model_configs_single(self, sample_setup):
        """Test generating configs for single model report."""
        from app.services.granularity.aggregation import GranularitySpec
        from app.services.granularity.reports import ReportGenerator, ReportSpec

        manager, df = sample_setup

        report = ReportSpec(
            name="national",
            granularity=GranularitySpec(
                name="national_monthly",
                dimensions={"time": "month", "geography": "national"},
            ),
            features=["spend"],
            target="sales",
        )

        generator = ReportGenerator(manager, {"national": report})
        configs = generator.generate_model_configs("national")

        assert len(configs) == 1
        config, data = configs[0]
        assert config.group_value is None
        assert len(data) == 3  # 3 months aggregated nationally

    def test_generate_model_configs_grouped(self, sample_setup):
        """Test generating configs for grouped report."""
        from app.services.granularity.aggregation import GranularitySpec
        from app.services.granularity.reports import ReportGenerator, ReportSpec

        manager, df = sample_setup

        report = ReportSpec(
            name="by_province",
            granularity=GranularitySpec(
                name="province_monthly",
                dimensions={"time": "month", "geography": "province"},
            ),
            group_by="province",
            features=["spend"],
            target="sales",
        )

        generator = ReportGenerator(manager, {"by_province": report})
        configs = generator.generate_model_configs("by_province")

        assert len(configs) == 2  # One per province

        group_values = [c.group_value for c, _ in configs]
        assert "Beijing" in group_values
        assert "Shanghai" in group_values

    def test_get_training_order(self, sample_setup):
        """Test getting correct training order for hierarchical reports."""
        from app.services.granularity.aggregation import GranularitySpec
        from app.services.granularity.reports import ReportGenerator, ReportSpec

        manager, df = sample_setup

        national = ReportSpec(
            name="national",
            granularity=GranularitySpec("national", {"time": "month", "geography": "national"}),
            features=["spend"],
            target="sales",
        )

        province = ReportSpec(
            name="province",
            granularity=GranularitySpec("province", {"time": "month", "geography": "province"}),
            features=["spend"],
            target="sales",
            parent_report="national",
            inherit_priors=True,
        )

        generator = ReportGenerator(manager, {"national": national, "province": province})
        order = generator.get_training_order()

        # National should come before province
        assert order.index("national") < order.index("province")
