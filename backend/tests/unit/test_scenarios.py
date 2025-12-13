"""Tests for scenario planning features."""

import pytest

from app.services.scenarios.calculator import (
    ScenarioCalculator,
    ScenarioResult,
    calculate_scenario,
)


class TestScenarioCalculator:
    """Tests for ScenarioCalculator."""

    @pytest.fixture
    def sample_model_result(self):
        """Sample model result for testing."""
        return {
            "coefficients": {
                "intercept": 1000,
                "tv_spend": 0.5,
                "digital_spend": 0.8,
                "print_spend": 0.3,
            },
            "contributions": {
                "base": [1000, 1000, 1000, 1000],
                "tv_spend": [500, 600, 550, 580],
                "digital_spend": [800, 850, 900, 820],
                "print_spend": [300, 280, 310, 290],
            },
            "dates": ["2024-01-01", "2024-01-08", "2024-01-15", "2024-01-22"],
            "actuals": [2600, 2730, 2760, 2690],
            "fitted": [2600, 2730, 2760, 2690],
        }

    @pytest.fixture
    def calculator(self, sample_model_result):
        """Create calculator instance."""
        return ScenarioCalculator(
            model_result=sample_model_result,
            coefficients=sample_model_result["coefficients"],
            contributions=sample_model_result["contributions"],
            dates=sample_model_result["dates"],
            actuals=sample_model_result["actuals"],
            fitted=sample_model_result["fitted"],
        )

    def test_calculate_no_adjustments(self, calculator):
        """Test scenario with no adjustments returns baseline."""
        result = calculator.calculate(adjustments={})

        assert isinstance(result, ScenarioResult)
        assert result.baseline_total == result.scenario_total
        assert result.lift_percentage == 0
        assert result.lift_absolute == 0

    def test_calculate_percentage_increase(self, calculator):
        """Test scenario with percentage increase."""
        adjustments = {"tv_spend": {"type": "percentage", "value": 10}}

        result = calculator.calculate(adjustments=adjustments)

        assert result.scenario_total > result.baseline_total
        assert result.lift_percentage > 0
        # TV spend contribution should increase by 10%
        baseline_tv = sum(result.baseline_contributions["tv_spend"])
        scenario_tv = sum(result.scenario_contributions["tv_spend"])
        assert scenario_tv == pytest.approx(baseline_tv * 1.1, rel=0.01)

    def test_calculate_percentage_decrease(self, calculator):
        """Test scenario with percentage decrease."""
        adjustments = {"digital_spend": {"type": "percentage", "value": -20}}

        result = calculator.calculate(adjustments=adjustments)

        assert result.scenario_total < result.baseline_total
        assert result.lift_percentage < 0

    def test_calculate_multiplier(self, calculator):
        """Test scenario with multiplier adjustment."""
        adjustments = {"print_spend": {"type": "multiplier", "value": 1.5}}

        result = calculator.calculate(adjustments=adjustments)

        baseline_print = sum(result.baseline_contributions["print_spend"])
        scenario_print = sum(result.scenario_contributions["print_spend"])
        assert scenario_print == pytest.approx(baseline_print * 1.5, rel=0.01)

    def test_calculate_multiple_adjustments(self, calculator):
        """Test scenario with multiple variable adjustments."""
        adjustments = {
            "tv_spend": {"type": "percentage", "value": 20},
            "digital_spend": {"type": "percentage", "value": -10},
        }

        result = calculator.calculate(adjustments=adjustments)

        assert len(result.summary["variables_adjusted"]) == 2
        assert "tv_spend" in result.summary["variables_adjusted"]
        assert "digital_spend" in result.summary["variables_adjusted"]

    def test_calculate_with_date_filter(self, calculator):
        """Test scenario with date range filter."""
        result = calculator.calculate(
            adjustments={},
            start_date="2024-01-08",
            end_date="2024-01-15",
        )

        # Should only have 2 periods
        assert len(result.dates) == 2
        assert result.dates[0] == "2024-01-08"
        assert result.dates[-1] == "2024-01-15"

    def test_summary_contains_variable_impacts(self, calculator):
        """Test that summary contains per-variable impacts."""
        adjustments = {"tv_spend": {"type": "percentage", "value": 10}}

        result = calculator.calculate(adjustments=adjustments)

        assert "variable_impacts" in result.summary
        assert "tv_spend" in result.summary["variable_impacts"]
        impact = result.summary["variable_impacts"]["tv_spend"]
        assert "baseline" in impact
        assert "scenario" in impact
        assert "impact_absolute" in impact
        assert "impact_percentage" in impact

    def test_compare_scenarios(self, calculator):
        """Test comparing multiple scenarios."""
        scenarios = [
            ("High TV", {"tv_spend": {"type": "percentage", "value": 50}}),
            ("High Digital", {"digital_spend": {"type": "percentage", "value": 50}}),
            (
                "Balanced",
                {
                    "tv_spend": {"type": "percentage", "value": 25},
                    "digital_spend": {"type": "percentage", "value": 25},
                },
            ),
        ]

        comparison = calculator.compare_scenarios(scenarios)

        assert "scenarios" in comparison
        assert "ranking" in comparison
        assert "best_scenario" in comparison
        assert len(comparison["scenarios"]) == 3
        assert len(comparison["ranking"]) == 3

    def test_result_to_dict(self, calculator):
        """Test ScenarioResult to_dict method."""
        result = calculator.calculate(adjustments={})

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "dates" in result_dict
        assert "baseline" in result_dict
        assert "scenario" in result_dict
        assert "baseline_total" in result_dict
        assert "scenario_total" in result_dict


class TestCalculateScenarioFunction:
    """Tests for the convenience function."""

    def test_calculate_scenario_convenience(self):
        """Test calculate_scenario convenience function."""
        model_result = {
            "coefficients": {"channel_a": 0.5},
            "contributions": {"channel_a": [100, 200, 150]},
            "dates": ["2024-01-01", "2024-01-08", "2024-01-15"],
            "actuals": [100, 200, 150],
            "fitted": [100, 200, 150],
        }

        result = calculate_scenario(
            model_result=model_result,
            adjustments={"channel_a": {"type": "percentage", "value": 10}},
        )

        assert isinstance(result, ScenarioResult)
        assert result.scenario_total > result.baseline_total
