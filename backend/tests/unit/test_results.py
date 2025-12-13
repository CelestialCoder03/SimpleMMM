"""Tests for results processing and visualization services."""

from uuid import uuid4

import pytest


class TestResultProcessor:
    """Tests for ResultProcessor."""

    @pytest.fixture
    def sample_raw_result(self):
        """Create sample raw training result."""
        return {
            "status": "completed",
            "model_result": {
                "r_squared": 0.85,
                "adjusted_r_squared": 0.82,
                "rmse": 1500.0,
                "mape": 8.5,
                "aic": 1200.0,
                "bic": 1220.0,
                "n_observations": 52,
                "n_features": 3,
                "coefficients": {
                    "tv_spend": 0.45,
                    "radio_spend": 0.25,
                    "digital_spend": 0.35,
                },
                "intercept": 10000.0,
                "std_errors": {
                    "tv_spend": 0.05,
                    "radio_spend": 0.08,
                    "digital_spend": 0.06,
                },
                "p_values": {
                    "tv_spend": 0.001,
                    "radio_spend": 0.02,
                    "digital_spend": 0.005,
                },
                "confidence_intervals": {
                    "tv_spend": [0.35, 0.55],
                    "radio_spend": [0.09, 0.41],
                    "digital_spend": [0.23, 0.47],
                },
                "vif": {
                    "tv_spend": 2.1,
                    "radio_spend": 1.5,
                    "digital_spend": 1.8,
                },
                "durbin_watson": 1.95,
                "jarque_bera_pvalue": 0.15,
            },
            "contributions": {
                "contributions": [
                    {
                        "variable": "base",
                        "total_contribution": 520000,
                        "contribution_pct": 40.0,
                        "avg_contribution": 10000,
                    },
                    {
                        "variable": "tv_spend",
                        "total_contribution": 390000,
                        "contribution_pct": 30.0,
                        "avg_contribution": 7500,
                        "roi": 3.5,
                    },
                    {
                        "variable": "radio_spend",
                        "total_contribution": 195000,
                        "contribution_pct": 15.0,
                        "avg_contribution": 3750,
                        "roi": 2.8,
                    },
                    {
                        "variable": "digital_spend",
                        "total_contribution": 195000,
                        "contribution_pct": 15.0,
                        "avg_contribution": 3750,
                        "roi": 4.2,
                    },
                ],
                "total_actual": 1300000,
            },
            "decomposition": {
                "dates": ["2024-01-01", "2024-01-08", "2024-01-15"],
                "actual": [25000, 26000, 24500],
                "predicted": [24800, 25900, 24600],
                "base": [10000, 10000, 10000],
                "contributions": {
                    "tv_spend": [8000, 8500, 7500],
                    "radio_spend": [3500, 3800, 3600],
                    "digital_spend": [3300, 3600, 3500],
                },
            },
            "response_curves": {
                "tv_spend": {
                    "spend_levels": [0, 1000, 2000, 3000],
                    "response_values": [0, 400, 700, 900],
                    "marginal_response": [0.45, 0.35, 0.25, 0.15],
                    "roi_values": [0, 0.4, 0.35, 0.3],
                },
            },
            "validation": {
                "coefficient_constraints": {"violations": []},
            },
            "transformations": {
                "tv_spend": {"adstock": {"decay": 0.7, "max_lag": 4}},
            },
            "metadata": {
                "model_type": "ridge",
                "training_time_seconds": 2.5,
                "n_features": 3,
                "n_observations": 52,
            },
        }

    def test_process_basic(self, sample_raw_result):
        """Test basic result processing."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()
        result = processor.process(sample_raw_result)

        assert result.model_type == "ridge"
        assert result.metrics["r_squared"] == 0.85
        assert len(result.coefficients) == 4  # 3 features + intercept
        assert len(result.contributions) == 4

    def test_process_coefficients(self, sample_raw_result):
        """Test coefficient processing with statistics."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()
        result = processor.process(sample_raw_result)

        tv_coef = next(c for c in result.coefficients if c["variable"] == "tv_spend")

        assert tv_coef["estimate"] == 0.45
        assert tv_coef["std_error"] == 0.05
        assert tv_coef["p_value"] == 0.001
        assert tv_coef["is_significant"] is True
        assert tv_coef["ci_lower"] == 0.35
        assert tv_coef["ci_upper"] == 0.55

    def test_get_summary(self, sample_raw_result):
        """Test summary generation."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()
        result = processor.process(sample_raw_result)
        summary = processor.get_summary(result)

        assert summary["model_type"] == "ridge"
        assert summary["fit_quality"] == "good"
        assert len(summary["top_contributors"]) == 3
        assert summary["n_significant"] == 3
        assert summary["has_issues"] is False

    def test_get_chart_data_contributions(self, sample_raw_result):
        """Test contribution chart data generation."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()
        result = processor.process(sample_raw_result)
        chart_data = processor.get_chart_data(result, "contributions")

        assert chart_data["chart_type"] == "contribution"
        assert len(chart_data["labels"]) == 4
        assert len(chart_data["values"]) == 4
        assert sum(chart_data["values"]) == pytest.approx(100, rel=0.1)

    def test_get_chart_data_decomposition(self, sample_raw_result):
        """Test decomposition chart data generation."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()
        result = processor.process(sample_raw_result)
        chart_data = processor.get_chart_data(result, "decomposition")

        assert chart_data["chart_type"] == "decomposition"
        assert "series" in chart_data
        assert len(chart_data["x_axis"]["data"]) == 3

    def test_assess_fit_quality(self, sample_raw_result):
        """Test fit quality assessment."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()

        # Excellent fit
        assert processor._assess_fit_quality({"r_squared": 0.95, "mape": 3}) == "excellent"

        # Good fit
        assert processor._assess_fit_quality({"r_squared": 0.85, "mape": 8}) == "good"

        # Moderate fit
        assert processor._assess_fit_quality({"r_squared": 0.65, "mape": 15}) == "moderate"

        # Fair fit
        assert processor._assess_fit_quality({"r_squared": 0.45, "mape": 25}) == "fair"

        # Poor fit
        assert processor._assess_fit_quality({"r_squared": 0.25, "mape": 35}) == "poor"

    def test_process_failed_result(self):
        """Test handling of failed result."""
        from app.services.results.processor import ResultProcessor

        processor = ResultProcessor()

        with pytest.raises(ValueError, match="Cannot process incomplete result"):
            processor.process({"status": "failed", "error": "Test error"})


class TestVisualizationCharts:
    """Tests for visualization chart generators."""

    def test_decomposition_chart(self):
        """Test decomposition chart generation."""
        from app.services.results.visualizations import ChartConfig, DecompositionChart

        config = ChartConfig(title="Test Decomposition")
        chart = DecompositionChart(config)

        data = {
            "dates": ["2024-01-01", "2024-01-08"],
            "base": [1000, 1000],
            "contributions": {"tv": [500, 600], "radio": [300, 350]},
            "actual": [1800, 1950],
        }

        spec = chart.generate(data)

        assert spec["title"]["text"] == "Test Decomposition"
        assert len(spec["series"]) == 4  # base + 2 channels + actual
        assert spec["series"][0]["name"] == "Base"

    def test_contribution_chart_pie(self):
        """Test pie chart generation."""
        from app.services.results.visualizations import ChartConfig, ContributionChart

        config = ChartConfig(title="Contributions")
        chart = ContributionChart(config, chart_style="pie")

        data = {
            "contributions": [
                {"variable": "tv", "contribution_pct": 50, "total_contribution": 5000},
                {
                    "variable": "radio",
                    "contribution_pct": 30,
                    "total_contribution": 3000,
                },
                {
                    "variable": "digital",
                    "contribution_pct": 20,
                    "total_contribution": 2000,
                },
            ]
        }

        spec = chart.generate(data)

        assert spec["series"][0]["type"] == "pie"
        assert len(spec["series"][0]["data"]) == 3

    def test_contribution_chart_bar(self):
        """Test bar chart generation."""
        from app.services.results.visualizations import ChartConfig, ContributionChart

        config = ChartConfig(title="Contributions")
        chart = ContributionChart(config, chart_style="bar")

        data = {
            "contributions": [
                {"variable": "tv", "contribution_pct": 50},
                {"variable": "radio", "contribution_pct": 30},
            ]
        }

        spec = chart.generate(data)

        assert spec["series"][0]["type"] == "bar"

    def test_response_curve_chart_single(self):
        """Test single channel response curve."""
        from app.services.results.visualizations import ChartConfig, ResponseCurveChart

        config = ChartConfig(title="TV Response")
        chart = ResponseCurveChart(config, show_marginal=True)

        data = {
            "variable": "tv_spend",
            "spend_levels": [0, 100, 200, 300],
            "response_values": [0, 80, 140, 180],
            "marginal_response": [1.0, 0.7, 0.5, 0.3],
        }

        spec = chart.generate(data)

        assert "TV Response" in spec["title"]["text"]
        assert len(spec["series"]) == 2  # response + marginal

    def test_response_curve_chart_multi(self):
        """Test multi-channel response curves."""
        from app.services.results.visualizations import ChartConfig, ResponseCurveChart

        config = ChartConfig(title="All Response Curves")
        chart = ResponseCurveChart(config)

        data = {
            "curves": {
                "tv": {"spend_levels": [0, 100], "response_values": [0, 80]},
                "radio": {"spend_levels": [0, 100], "response_values": [0, 60]},
            }
        }

        spec = chart.generate(data)

        assert len(spec["series"]) == 2

    def test_waterfall_chart(self):
        """Test waterfall chart generation."""
        from app.services.results.visualizations import ChartConfig, WaterfallChart

        config = ChartConfig(title="Waterfall")
        chart = WaterfallChart(config)

        data = {
            "items": [
                {"name": "Base", "value": 1000, "type": "base"},
                {"name": "TV", "value": 500, "type": "positive"},
                {"name": "Radio", "value": 300, "type": "positive"},
                {"name": "Total", "value": 1800, "type": "total"},
            ]
        }

        spec = chart.generate(data)

        assert len(spec["series"]) == 3  # placeholder, increase, decrease
        assert len(spec["xAxis"]["data"]) == 4

    def test_diagnostics_chart(self):
        """Test diagnostics chart generation."""
        from app.services.results.visualizations import ChartConfig, DiagnosticsChart

        config = ChartConfig(title="Diagnostics")
        chart = DiagnosticsChart(config)

        data = {
            "actual": [100, 110, 105],
            "predicted": [102, 108, 106],
            "residuals": [-2, 2, -1],
            "vif": {"tv": 2.5, "radio": 1.8},
        }

        spec = chart.generate(data)

        assert "panels" in spec
        assert len(spec["panels"]) >= 3


class TestResultExporter:
    """Tests for ResultExporter."""

    @pytest.fixture
    def processed_result(self):
        """Create sample processed result."""
        from app.services.results.processor import ProcessedResult

        return ProcessedResult(
            model_id=uuid4(),
            model_name="Test Model",
            model_type="ridge",
            training_duration_seconds=2.5,
            metrics={
                "r_squared": 0.85,
                "adjusted_r_squared": 0.82,
                "rmse": 1500.0,
                "mape": 8.5,
                "n_observations": 52,
                "n_features": 3,
            },
            coefficients=[
                {
                    "variable": "tv_spend",
                    "estimate": 0.45,
                    "std_error": 0.05,
                    "p_value": 0.001,
                    "is_significant": True,
                    "ci_lower": 0.35,
                    "ci_upper": 0.55,
                    "t_statistic": 9.0,
                },
                {
                    "variable": "radio_spend",
                    "estimate": 0.25,
                    "std_error": 0.08,
                    "p_value": 0.02,
                    "is_significant": True,
                    "ci_lower": 0.09,
                    "ci_upper": 0.41,
                    "t_statistic": 3.1,
                },
                {
                    "variable": "intercept",
                    "estimate": 10000,
                    "std_error": None,
                    "p_value": None,
                    "is_significant": None,
                    "ci_lower": None,
                    "ci_upper": None,
                    "t_statistic": None,
                },
            ],
            contributions=[
                {
                    "variable": "base",
                    "total_contribution": 520000,
                    "contribution_pct": 40.0,
                    "avg_contribution": 10000,
                    "roi": None,
                    "marginal_roi": None,
                },
                {
                    "variable": "tv_spend",
                    "total_contribution": 390000,
                    "contribution_pct": 30.0,
                    "avg_contribution": 7500,
                    "roi": 3.5,
                    "marginal_roi": 2.1,
                },
                {
                    "variable": "radio_spend",
                    "total_contribution": 195000,
                    "contribution_pct": 15.0,
                    "avg_contribution": 3750,
                    "roi": 2.8,
                    "marginal_roi": 1.5,
                },
            ],
            decomposition={
                "dates": ["2024-01-01", "2024-01-08"],
                "actual": [25000, 26000],
                "predicted": [24800, 25900],
                "base": [10000, 10000],
                "contributions": {
                    "tv_spend": [8000, 8500],
                    "radio_spend": [3500, 3800],
                },
            },
            response_curves={
                "tv_spend": {
                    "spend_levels": [0, 1000, 2000],
                    "response_values": [0, 400, 700],
                    "marginal_response": [0.45, 0.35, 0.25],
                    "roi_values": [0, 0.4, 0.35],
                },
            },
            diagnostics={
                "vif": {"tv_spend": 2.1, "radio_spend": 1.5},
                "durbin_watson": 1.95,
                "jarque_bera_pvalue": 0.15,
            },
        )

    def test_to_csv_coefficients(self, processed_result):
        """Test CSV export for coefficients."""
        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        csv_content = exporter.to_csv("coefficients")

        assert "Variable" in csv_content
        assert "tv_spend" in csv_content
        assert "0.45" in csv_content

    def test_to_csv_contributions(self, processed_result):
        """Test CSV export for contributions."""
        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        csv_content = exporter.to_csv("contributions")

        assert "Contribution %" in csv_content
        assert "390000" in csv_content

    def test_to_csv_decomposition(self, processed_result):
        """Test CSV export for decomposition."""
        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        csv_content = exporter.to_csv("decomposition")

        assert "Date" in csv_content
        assert "2024-01-01" in csv_content

    def test_to_csv_all(self, processed_result):
        """Test CSV export for all data."""
        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        csv_content = exporter.to_csv("all")

        assert "MODEL METRICS" in csv_content
        assert "COEFFICIENTS" in csv_content
        assert "CONTRIBUTIONS" in csv_content

    def test_to_excel(self, processed_result):
        """Test Excel export."""
        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        excel_bytes = exporter.to_excel()

        assert len(excel_bytes) > 0
        # Check it's a valid Excel file (starts with PK for zip)
        assert excel_bytes[:2] == b"PK"

    def test_to_json(self, processed_result):
        """Test JSON export."""
        import json

        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        json_str = exporter.to_json()

        # Verify it's valid JSON
        data = json.loads(json_str)

        assert data["model_type"] == "ridge"
        assert data["metrics"]["r_squared"] == 0.85

    def test_to_html_report(self, processed_result):
        """Test HTML report export."""
        from app.services.results.exporter import ResultExporter

        exporter = ResultExporter(processed_result)
        html_content = exporter.to_html_report()

        assert "<!DOCTYPE html>" in html_content
        assert "Marketing Mix Model Results" in html_content
        assert "85" in html_content  # R-squared percentage
        assert "tv_spend" in html_content


class TestProcessedResult:
    """Tests for ProcessedResult dataclass."""

    def test_to_dict(self):
        """Test conversion to dictionary."""
        from app.services.results.processor import ProcessedResult

        result = ProcessedResult(
            model_name="Test",
            model_type="ridge",
            metrics={"r_squared": 0.85},
        )

        data = result.to_dict()

        assert data["model_name"] == "Test"
        assert data["model_type"] == "ridge"
        assert data["metrics"]["r_squared"] == 0.85
        assert "created_at" in data
