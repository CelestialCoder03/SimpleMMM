"""Model comparison framework for Marketing Mix Models."""

from dataclasses import dataclass
from typing import Any

from app.services.modeling.base import ModelResult


@dataclass
class ModelComparison:
    """
    Comparison results between multiple models.

    Provides metrics comparison, coefficient comparison, and
    contribution comparison for side-by-side model evaluation.
    """

    model_ids: list[str]
    model_names: list[str]
    metrics_comparison: dict[str, dict[str, float]]
    coefficients_comparison: dict[str, dict[str, float]]
    contributions_comparison: dict[str, dict[str, float]]
    rankings: dict[str, list[str]]  # metric -> [model_id in ranked order]
    summary: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "model_ids": self.model_ids,
            "model_names": self.model_names,
            "metrics_comparison": self.metrics_comparison,
            "coefficients_comparison": self.coefficients_comparison,
            "contributions_comparison": self.contributions_comparison,
            "rankings": self.rankings,
            "summary": self.summary,
        }


class ModelComparer:
    """
    Compare multiple Marketing Mix Models.

    Provides:
    - Side-by-side metrics comparison
    - Coefficient comparison across models
    - Contribution comparison
    - Model ranking by various criteria
    - Statistical tests for model differences

    Usage:
        comparer = ModelComparer()
        comparison = comparer.compare(
            models=[
                {"id": "model_1", "name": "Ridge α=1.0", "result": result1, "contributions": contrib1},
                {"id": "model_2", "name": "Ridge α=10.0", "result": result2, "contributions": contrib2},
            ]
        )
    """

    # Metrics where higher is better
    HIGHER_IS_BETTER = {"r_squared", "adjusted_r_squared"}

    # Metrics where lower is better
    LOWER_IS_BETTER = {"rmse", "mae", "mape", "aic", "bic"}

    def __init__(self):
        self._models: list[dict[str, Any]] = []

    def compare(
        self,
        models: list[dict[str, Any]],
    ) -> ModelComparison:
        """
        Compare multiple models.

        Args:
            models: List of model dictionaries, each containing:
                - id: Unique identifier for the model
                - name: Display name
                - result: ModelResult or dict from model.get_result().to_dict()
                - contributions: Contribution data (optional)

        Returns:
            ModelComparison with all comparison data.
        """
        if len(models) < 2:
            raise ValueError("Need at least 2 models to compare")

        self._models = models

        model_ids = [m["id"] for m in models]
        model_names = [m.get("name", m["id"]) for m in models]

        # Compare metrics
        metrics_comparison = self._compare_metrics()

        # Compare coefficients
        coefficients_comparison = self._compare_coefficients()

        # Compare contributions
        contributions_comparison = self._compare_contributions()

        # Rank models
        rankings = self._rank_models(metrics_comparison)

        # Generate summary
        summary = self._generate_summary(metrics_comparison, rankings)

        return ModelComparison(
            model_ids=model_ids,
            model_names=model_names,
            metrics_comparison=metrics_comparison,
            coefficients_comparison=coefficients_comparison,
            contributions_comparison=contributions_comparison,
            rankings=rankings,
            summary=summary,
        )

    def _get_result(self, model: dict) -> dict[str, Any]:
        """Extract result dict from model."""
        result = model.get("result", {})
        if isinstance(result, ModelResult):
            return result.to_dict()
        return result

    def _compare_metrics(self) -> dict[str, dict[str, float]]:
        """
        Compare metrics across all models.

        Returns:
            Dict mapping metric name to {model_id: value}.
        """
        metrics = [
            "r_squared",
            "adjusted_r_squared",
            "rmse",
            "mae",
            "mape",
            "aic",
            "bic",
            "durbin_watson",
        ]

        comparison = {}

        for metric in metrics:
            comparison[metric] = {}
            for model in self._models:
                result = self._get_result(model)
                value = result.get(metric)
                if value is not None:
                    comparison[metric][model["id"]] = float(value)

        # Add training time comparison
        comparison["training_time_seconds"] = {}
        for model in self._models:
            result = self._get_result(model)
            value = result.get("training_time_seconds")
            if value is not None:
                comparison["training_time_seconds"][model["id"]] = float(value)

        return comparison

    def _compare_coefficients(self) -> dict[str, dict[str, float]]:
        """
        Compare coefficients across all models.

        Returns:
            Dict mapping variable name to {model_id: coefficient}.
        """
        # Collect all variable names
        all_variables = set()
        for model in self._models:
            result = self._get_result(model)
            coefficients = result.get("coefficients", {})
            all_variables.update(coefficients.keys())

        comparison = {}

        for var in sorted(all_variables):
            comparison[var] = {}
            for model in self._models:
                result = self._get_result(model)
                coefficients = result.get("coefficients", {})
                if var in coefficients:
                    comparison[var][model["id"]] = float(coefficients[var])

        # Add intercept comparison
        comparison["_intercept"] = {}
        for model in self._models:
            result = self._get_result(model)
            intercept = result.get("intercept")
            if intercept is not None:
                comparison["_intercept"][model["id"]] = float(intercept)

        return comparison

    def _compare_contributions(self) -> dict[str, dict[str, float]]:
        """
        Compare contributions across all models.

        Returns:
            Dict mapping variable name to {model_id: contribution_pct}.
        """
        # Collect all variable names from contributions
        all_variables = set()
        for model in self._models:
            contributions = model.get("contributions", {})
            if isinstance(contributions, dict):
                for item in contributions.get("contributions", []):
                    all_variables.add(item.get("variable", ""))

        comparison = {}

        for var in sorted(all_variables):
            if not var:
                continue
            comparison[var] = {}
            for model in self._models:
                contributions = model.get("contributions", {})
                if isinstance(contributions, dict):
                    for item in contributions.get("contributions", []):
                        if item.get("variable") == var:
                            comparison[var][model["id"]] = float(item.get("contribution_pct", 0))
                            break

        return comparison

    def _rank_models(
        self,
        metrics_comparison: dict[str, dict[str, float]],
    ) -> dict[str, list[str]]:
        """
        Rank models by each metric.

        Returns:
            Dict mapping metric name to list of model_ids in ranked order (best first).
        """
        rankings = {}

        for metric, values in metrics_comparison.items():
            if not values:
                continue

            # Determine sort order
            reverse = metric in self.HIGHER_IS_BETTER

            # Sort models by metric value
            sorted_models = sorted(
                values.items(),
                key=lambda x: x[1],
                reverse=reverse,
            )

            rankings[metric] = [model_id for model_id, _ in sorted_models]

        return rankings

    def _generate_summary(
        self,
        metrics_comparison: dict[str, dict[str, float]],
        rankings: dict[str, list[str]],
    ) -> dict[str, Any]:
        """
        Generate comparison summary.

        Returns:
            Summary dict with best model recommendations.
        """
        # Count how many times each model ranks first
        first_place_counts = {}
        for model in self._models:
            first_place_counts[model["id"]] = 0

        key_metrics = ["r_squared", "adjusted_r_squared", "rmse", "mape", "aic"]

        for metric in key_metrics:
            if metric in rankings and rankings[metric]:
                first_place_counts[rankings[metric][0]] += 1

        # Find overall best model
        best_model_id = max(first_place_counts.items(), key=lambda x: x[1])[0]
        best_model = next(m for m in self._models if m["id"] == best_model_id)

        # Calculate metric improvements
        improvements = {}
        if len(self._models) >= 2:
            for metric in key_metrics:
                if metric in metrics_comparison:
                    values = list(metrics_comparison[metric].values())
                    if len(values) >= 2:
                        if metric in self.HIGHER_IS_BETTER:
                            improvements[metric] = {
                                "best": max(values),
                                "worst": min(values),
                                "improvement_pct": (
                                    (max(values) - min(values)) / abs(min(values)) * 100 if min(values) != 0 else 0
                                ),
                            }
                        else:
                            improvements[metric] = {
                                "best": min(values),
                                "worst": max(values),
                                "improvement_pct": (
                                    (max(values) - min(values)) / abs(max(values)) * 100 if max(values) != 0 else 0
                                ),
                            }

        return {
            "best_model_id": best_model_id,
            "best_model_name": best_model.get("name", best_model_id),
            "first_place_counts": first_place_counts,
            "improvements": improvements,
            "recommendation": self._generate_recommendation(best_model, metrics_comparison, rankings),
        }

    def _generate_recommendation(
        self,
        best_model: dict,
        metrics_comparison: dict[str, dict[str, float]],
        rankings: dict[str, list[str]],
    ) -> str:
        """Generate a text recommendation."""
        model_name = best_model.get("name", best_model["id"])
        result = self._get_result(best_model)

        r2 = result.get("r_squared", 0)
        mape = result.get("mape", 0)

        recommendation = f"Based on the comparison, '{model_name}' performs best overall. "
        recommendation += f"It achieves R² of {r2:.4f} "

        if mape:
            recommendation += f"and MAPE of {mape:.2f}%. "

        # Check for potential issues
        dw = result.get("durbin_watson")
        if dw is not None and (dw < 1.5 or dw > 2.5):
            recommendation += "Note: Durbin-Watson statistic suggests potential autocorrelation. "

        return recommendation


def compare_models(
    models: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convenience function to compare models.

    Args:
        models: List of model dicts with id, name, result, and contributions.

    Returns:
        Comparison results as a dictionary.
    """
    comparer = ModelComparer()
    comparison = comparer.compare(models)
    return comparison.to_dict()
