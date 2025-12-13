"""Scenario calculation service."""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ScenarioResult:
    """Result of scenario calculation."""

    dates: list[str]
    baseline: list[float]
    scenario: list[float]
    baseline_contributions: dict[str, list[float]]
    scenario_contributions: dict[str, list[float]]
    baseline_total: float
    scenario_total: float
    lift_percentage: float
    lift_absolute: float
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "dates": self.dates,
            "baseline": self.baseline,
            "scenario": self.scenario,
            "baseline_contributions": self.baseline_contributions,
            "scenario_contributions": self.scenario_contributions,
            "baseline_total": self.baseline_total,
            "scenario_total": self.scenario_total,
            "lift_percentage": self.lift_percentage,
            "lift_absolute": self.lift_absolute,
            "summary": self.summary,
        }


class ScenarioCalculator:
    """
    Calculator for what-if scenario analysis.

    Takes a trained model's results and applies hypothetical adjustments
    to marketing variables to forecast outcomes.
    """

    def __init__(
        self,
        model_result: dict,
        coefficients: dict[str, float],
        contributions: dict[str, list[float]],
        dates: list[str],
        actuals: list[float],
        fitted: list[float],
    ):
        """
        Initialize scenario calculator.

        Args:
            model_result: Full model result dictionary.
            coefficients: Variable coefficients from the model.
            contributions: Contribution decomposition by variable.
            dates: Date strings for the time series.
            actuals: Actual target values.
            fitted: Fitted/predicted values.
        """
        self.model_result = model_result
        self.coefficients = coefficients
        self.contributions = contributions
        self.dates = dates
        self.actuals = actuals
        self.fitted = fitted

    def calculate(
        self,
        adjustments: dict[str, dict],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> ScenarioResult:
        """
        Calculate scenario outcomes based on adjustments.

        Args:
            adjustments: Dict of variable adjustments.
                Format: {"variable": {"type": "percentage|absolute|multiplier", "value": X}}
            start_date: Optional start date filter.
            end_date: Optional end date filter.

        Returns:
            ScenarioResult with baseline and scenario predictions.
        """
        # Filter dates if specified
        dates = self.dates
        start_idx = 0
        end_idx = len(dates)

        if start_date:
            for i, d in enumerate(dates):
                if d >= start_date:
                    start_idx = i
                    break

        if end_date:
            for i, d in enumerate(dates):
                if d > end_date:
                    end_idx = i
                    break

        filtered_dates = dates[start_idx:end_idx]

        # Calculate baseline contributions (from model)
        baseline_contributions = {var: contrib[start_idx:end_idx] for var, contrib in self.contributions.items()}

        # Calculate scenario contributions with adjustments
        scenario_contributions = {}
        for var, contrib in self.contributions.items():
            filtered_contrib = contrib[start_idx:end_idx]

            if var in adjustments:
                adj = adjustments[var]
                adj_type = adj.get("type", "percentage")
                adj_value = adj.get("value", 0)

                if adj_type == "percentage":
                    # Percentage change: 10 means +10%
                    multiplier = 1 + (adj_value / 100)
                    adjusted = [c * multiplier for c in filtered_contrib]
                elif adj_type == "multiplier":
                    # Direct multiplier: 1.1 means +10%
                    adjusted = [c * adj_value for c in filtered_contrib]
                elif adj_type == "absolute":
                    # Absolute change distributed proportionally
                    total_contrib = sum(filtered_contrib) if sum(filtered_contrib) != 0 else 1
                    adjusted = [c + (adj_value * c / total_contrib) for c in filtered_contrib]
                else:
                    adjusted = filtered_contrib

                scenario_contributions[var] = adjusted
            else:
                scenario_contributions[var] = filtered_contrib

        # Calculate totals
        baseline = [
            sum(baseline_contributions[var][i] for var in baseline_contributions) for i in range(len(filtered_dates))
        ]

        scenario = [
            sum(scenario_contributions[var][i] for var in scenario_contributions) for i in range(len(filtered_dates))
        ]

        baseline_total = sum(baseline)
        scenario_total = sum(scenario)
        lift_absolute = scenario_total - baseline_total
        lift_percentage = (lift_absolute / baseline_total * 100) if baseline_total != 0 else 0

        # Build summary
        summary = self._build_summary(
            adjustments=adjustments,
            baseline_contributions=baseline_contributions,
            scenario_contributions=scenario_contributions,
            baseline_total=baseline_total,
            scenario_total=scenario_total,
        )

        return ScenarioResult(
            dates=filtered_dates,
            baseline=baseline,
            scenario=scenario,
            baseline_contributions=baseline_contributions,
            scenario_contributions=scenario_contributions,
            baseline_total=baseline_total,
            scenario_total=scenario_total,
            lift_percentage=round(lift_percentage, 2),
            lift_absolute=round(lift_absolute, 2),
            summary=summary,
        )

    def _build_summary(
        self,
        adjustments: dict[str, dict],
        baseline_contributions: dict[str, list[float]],
        scenario_contributions: dict[str, list[float]],
        baseline_total: float,
        scenario_total: float,
    ) -> dict[str, Any]:
        """Build summary statistics for the scenario."""
        summary = {
            "adjustments_applied": len(adjustments),
            "variables_adjusted": list(adjustments.keys()),
            "period_count": len(next(iter(baseline_contributions.values()), [])),
            "baseline_total": round(baseline_total, 2),
            "scenario_total": round(scenario_total, 2),
            "lift_absolute": round(scenario_total - baseline_total, 2),
            "lift_percentage": round(
                (scenario_total - baseline_total) / baseline_total * 100 if baseline_total != 0 else 0,
                2,
            ),
            "variable_impacts": {},
        }

        # Calculate per-variable impact
        for var in baseline_contributions:
            base_sum = sum(baseline_contributions[var])
            scen_sum = sum(scenario_contributions.get(var, baseline_contributions[var]))
            impact = scen_sum - base_sum
            impact_pct = (impact / base_sum * 100) if base_sum != 0 else 0

            summary["variable_impacts"][var] = {
                "baseline": round(base_sum, 2),
                "scenario": round(scen_sum, 2),
                "impact_absolute": round(impact, 2),
                "impact_percentage": round(impact_pct, 2),
            }

        return summary

    def compare_scenarios(
        self,
        scenarios: list[tuple[str, dict[str, dict]]],
    ) -> dict[str, Any]:
        """
        Compare multiple scenarios.

        Args:
            scenarios: List of (name, adjustments) tuples.

        Returns:
            Comparison results.
        """
        results = {}

        for name, adjustments in scenarios:
            result = self.calculate(adjustments)
            results[name] = {
                "total": result.scenario_total,
                "lift_percentage": result.lift_percentage,
                "lift_absolute": result.lift_absolute,
            }

        # Rank scenarios
        ranked = sorted(
            results.items(),
            key=lambda x: x[1]["total"],
            reverse=True,
        )

        return {
            "scenarios": results,
            "ranking": [name for name, _ in ranked],
            "best_scenario": ranked[0][0] if ranked else None,
            "baseline_total": self.calculate({}).baseline_total,
        }


def calculate_scenario(
    model_result: dict,
    adjustments: dict[str, dict],
    start_date: str | None = None,
    end_date: str | None = None,
) -> ScenarioResult:
    """
    Convenience function to calculate a scenario.

    Args:
        model_result: Full model result with contributions.
        adjustments: Variable adjustments to apply.
        start_date: Optional start date filter.
        end_date: Optional end date filter.

    Returns:
        ScenarioResult with baseline and scenario predictions.
    """
    # Extract required data from model result
    coefficients = model_result.get("coefficients", {})
    contributions = model_result.get("contributions", {})
    dates = model_result.get("dates", [])
    actuals = model_result.get("actuals", [])
    fitted = model_result.get("fitted", [])

    calculator = ScenarioCalculator(
        model_result=model_result,
        coefficients=coefficients,
        contributions=contributions,
        dates=dates,
        actuals=actuals,
        fitted=fitted,
    )

    return calculator.calculate(
        adjustments=adjustments,
        start_date=start_date,
        end_date=end_date,
    )
