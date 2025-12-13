"""Result processor for formatting and storing model outputs."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID


@dataclass
class ProcessedResult:
    """Container for processed model results ready for storage/display."""

    # Identification
    model_id: UUID | None = None
    model_name: str = ""
    model_type: str = ""

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    training_duration_seconds: float = 0.0

    # Fit metrics
    metrics: dict[str, float] = field(default_factory=dict)

    # Coefficients with statistics
    coefficients: list[dict[str, Any]] = field(default_factory=list)

    # Contributions
    contributions: list[dict[str, Any]] = field(default_factory=list)
    total_predicted: float = 0.0
    total_actual: float = 0.0

    # Time series decomposition
    decomposition: dict[str, list[Any]] = field(default_factory=dict)

    # Response curves
    response_curves: dict[str, dict[str, list[float]]] = field(default_factory=dict)

    # Diagnostics
    diagnostics: dict[str, Any] = field(default_factory=dict)

    # Validation
    validation: dict[str, Any] = field(default_factory=dict)

    # Transformations applied
    transformations: dict[str, dict[str, Any]] = field(default_factory=dict)

    # Metadata
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "model_id": str(self.model_id) if self.model_id else None,
            "model_name": self.model_name,
            "model_type": self.model_type,
            "created_at": self.created_at.isoformat(),
            "training_duration_seconds": self.training_duration_seconds,
            "metrics": self.metrics,
            "coefficients": self.coefficients,
            "contributions": self.contributions,
            "total_predicted": self.total_predicted,
            "total_actual": self.total_actual,
            "decomposition": self.decomposition,
            "response_curves": self.response_curves,
            "diagnostics": self.diagnostics,
            "validation": self.validation,
            "transformations": self.transformations,
            "metadata": self.metadata,
        }


class ResultProcessor:
    """
    Processes raw model training results into structured formats
    suitable for storage, display, and visualization.

    This class transforms the raw output from ModelTrainer into
    clean, well-organized data structures for:
    - Database storage
    - API responses
    - Chart generation
    - Report export

    Usage:
        processor = ResultProcessor()
        processed = processor.process(raw_training_result)

        # Get formatted for storage
        db_record = processed.to_dict()

        # Get specific views
        summary = processor.get_summary(processed)
        chart_data = processor.get_chart_data(processed, 'contributions')
    """

    def __init__(self, significance_level: float = 0.05):
        """
        Initialize processor.

        Args:
            significance_level: P-value threshold for significance testing.
        """
        self.significance_level = significance_level

    def process(
        self,
        raw_result: dict[str, Any],
        model_id: UUID | None = None,
        model_name: str = "",
    ) -> ProcessedResult:
        """
        Process raw training results into structured format.

        Args:
            raw_result: Raw result dictionary from ModelTrainer.train()
            model_id: Optional model configuration ID
            model_name: Optional model name

        Returns:
            ProcessedResult with all data organized
        """
        if raw_result.get("status") != "completed":
            raise ValueError(f"Cannot process incomplete result: {raw_result.get('status')}")

        model_result = raw_result.get("model_result", {})

        # Process metrics
        metrics = self._process_metrics(model_result)

        # Process coefficients
        coefficients = self._process_coefficients(model_result)

        # Process contributions
        contributions_data = raw_result.get("contributions", {})
        contributions = self._process_contributions(contributions_data)

        # Process decomposition
        decomposition = self._process_decomposition(raw_result.get("decomposition", {}))

        # Process response curves
        response_curves = self._process_response_curves(raw_result.get("response_curves", {}))

        # Process diagnostics
        diagnostics = self._process_diagnostics(model_result)

        # Get totals
        total_predicted = sum(c.get("total_contribution", 0) for c in contributions)
        total_actual = (
            contributions_data.get("total_actual", total_predicted)
            if isinstance(contributions_data, dict)
            else total_predicted
        )

        return ProcessedResult(
            model_id=model_id,
            model_name=model_name,
            model_type=raw_result.get("metadata", {}).get("model_type", ""),
            training_duration_seconds=raw_result.get("metadata", {}).get("training_time_seconds", 0),
            metrics=metrics,
            coefficients=coefficients,
            contributions=contributions,
            total_predicted=total_predicted,
            total_actual=total_actual,
            decomposition=decomposition,
            response_curves=response_curves,
            diagnostics=diagnostics,
            validation=raw_result.get("validation", {}),
            transformations=raw_result.get("transformations", {}),
            metadata=raw_result.get("metadata", {}),
        )

    def _process_metrics(self, model_result: dict[str, Any]) -> dict[str, float]:
        """Extract and format fit metrics."""
        return {
            "r_squared": model_result.get("r_squared", 0),
            "adjusted_r_squared": model_result.get("adjusted_r_squared", 0),
            "rmse": model_result.get("rmse", 0),
            "mape": model_result.get("mape", 0),
            "aic": model_result.get("aic"),
            "bic": model_result.get("bic"),
            "n_observations": model_result.get("n_observations", 0),
            "n_features": model_result.get("n_features", 0),
        }

    def _process_coefficients(self, model_result: dict[str, Any]) -> list[dict[str, Any]]:
        """Process coefficient estimates with statistics."""
        coefficients = model_result.get("coefficients", {})
        std_errors = model_result.get("std_errors", {})
        p_values = model_result.get("p_values", {})
        conf_intervals = model_result.get("confidence_intervals", {})

        processed = []

        for var_name, estimate in coefficients.items():
            se = std_errors.get(var_name)
            p_val = p_values.get(var_name)
            ci = conf_intervals.get(var_name, [None, None])

            processed.append(
                {
                    "variable": var_name,
                    "estimate": float(estimate),
                    "std_error": float(se) if se is not None else None,
                    "t_statistic": float(estimate / se) if se and se > 0 else None,
                    "p_value": float(p_val) if p_val is not None else None,
                    "ci_lower": float(ci[0]) if ci[0] is not None else None,
                    "ci_upper": float(ci[1]) if ci[1] is not None else None,
                    "is_significant": p_val < self.significance_level if p_val is not None else None,
                }
            )

        # Add intercept
        intercept = model_result.get("intercept")
        if intercept is not None:
            processed.append(
                {
                    "variable": "intercept",
                    "estimate": float(intercept),
                    "std_error": None,
                    "t_statistic": None,
                    "p_value": None,
                    "ci_lower": None,
                    "ci_upper": None,
                    "is_significant": None,
                }
            )

        return processed

    def _process_contributions(self, contributions_data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Process contribution results.

        Handles both formats:
        - List of contribution dicts directly
        - Dict with "contributions" key containing the list
        """
        # Handle both list and dict formats
        if isinstance(contributions_data, list):
            contributions_list = contributions_data
        else:
            contributions_list = contributions_data.get("contributions", [])

        processed = []
        for item in contributions_list:
            processed.append(
                {
                    "variable": item.get("variable", ""),
                    "total_contribution": item.get("total_contribution", 0),
                    "contribution_pct": item.get("contribution_pct", 0),
                    "avg_contribution": item.get("avg_contribution", 0),
                    "roi": item.get("roi"),
                    "marginal_roi": item.get("marginal_roi"),
                }
            )

        return processed

    def _process_decomposition(self, decomposition: dict[str, Any]) -> dict[str, list[Any]]:
        """Process time series decomposition."""
        result = {
            "dates": decomposition.get("dates", []),
            "actual": decomposition.get("actual", []),
            "predicted": decomposition.get("predicted", []),
            "residuals": decomposition.get("residuals", []),
            "base": decomposition.get("base", []),
            "contributions": decomposition.get("contributions", {}),
        }

        # Preserve channel contributions that are stored at top level (feature names)
        exclude_keys = {
            "dates",
            "actual",
            "predicted",
            "residuals",
            "base",
            "contributions",
        }
        for key, values in decomposition.items():
            if key not in exclude_keys and isinstance(values, list):
                result[key] = values

        return result

    def _process_response_curves(
        self,
        response_curves: dict[str, dict[str, list[float]]],
    ) -> dict[str, dict[str, list[float]]]:
        """Process response curve data."""
        processed = {}

        for var_name, curve_data in response_curves.items():
            processed[var_name] = {
                "spend_levels": curve_data.get("spend_levels", []),
                "response_values": curve_data.get("response_values", []),
                "marginal_response": curve_data.get("marginal_response", []),
                "roi_values": curve_data.get("roi_values", []),
            }

        return processed

    def _process_diagnostics(self, model_result: dict[str, Any]) -> dict[str, Any]:
        """Process model diagnostics."""
        return {
            "vif": model_result.get("vif", {}),
            "durbin_watson": model_result.get("durbin_watson"),
            "jarque_bera_pvalue": model_result.get("jarque_bera_pvalue"),
            "shapiro_pvalue": model_result.get("shapiro_pvalue"),
            "skewness": model_result.get("skewness"),
            "kurtosis": model_result.get("kurtosis"),
            "r_hat": model_result.get("r_hat", {}),
            "ess": model_result.get("ess", {}),
        }

    def get_summary(self, result: ProcessedResult) -> dict[str, Any]:
        """
        Generate executive summary of model results.

        Args:
            result: Processed model result

        Returns:
            Summary dictionary with key insights
        """
        # Find top contributors
        sorted_contribs = sorted(
            result.contributions,
            key=lambda x: x.get("contribution_pct", 0),
            reverse=True,
        )
        top_contributors = sorted_contribs[:3]

        # Find significant coefficients
        significant_coefs = [c for c in result.coefficients if c.get("is_significant") and c["variable"] != "intercept"]

        # Check for issues
        issues = []

        # High VIF (multicollinearity)
        high_vif = {k: v for k, v in result.diagnostics.get("vif", {}).items() if v and v > 10}
        if high_vif:
            issues.append(
                {
                    "type": "multicollinearity",
                    "severity": "warning",
                    "message": f"High VIF detected for: {', '.join(high_vif.keys())}",
                    "variables": list(high_vif.keys()),
                }
            )

        # Autocorrelation
        dw = result.diagnostics.get("durbin_watson")
        if dw and (dw < 1.5 or dw > 2.5):
            issues.append(
                {
                    "type": "autocorrelation",
                    "severity": "warning",
                    "message": f"Durbin-Watson statistic ({dw:.2f}) indicates potential autocorrelation",
                }
            )

        # Non-normality
        jb_pval = result.diagnostics.get("jarque_bera_pvalue")
        if jb_pval and jb_pval < 0.05:
            issues.append(
                {
                    "type": "non_normality",
                    "severity": "info",
                    "message": "Residuals may not be normally distributed",
                }
            )

        # Constraint violations
        violations = result.validation.get("coefficient_constraints", {}).get("violations", [])
        if violations:
            issues.append(
                {
                    "type": "constraint_violation",
                    "severity": "error",
                    "message": f"{len(violations)} constraint violation(s) detected",
                    "details": violations,
                }
            )

        return {
            "model_type": result.model_type,
            "fit_quality": self._assess_fit_quality(result.metrics),
            "metrics": {
                "r_squared": result.metrics.get("r_squared"),
                "mape": result.metrics.get("mape"),
                "rmse": result.metrics.get("rmse"),
            },
            "top_contributors": [
                {
                    "variable": c["variable"],
                    "contribution_pct": c["contribution_pct"],
                }
                for c in top_contributors
            ],
            "significant_variables": [c["variable"] for c in significant_coefs],
            "n_significant": len(significant_coefs),
            "n_total_variables": len([c for c in result.coefficients if c["variable"] != "intercept"]),
            "issues": issues,
            "has_issues": len(issues) > 0,
            "training_duration": result.training_duration_seconds,
        }

    def _assess_fit_quality(self, metrics: dict[str, float]) -> str:
        """Assess overall model fit quality."""
        r2 = metrics.get("r_squared", 0)
        mape = metrics.get("mape", 100)

        if r2 >= 0.9 and mape <= 5:
            return "excellent"
        elif r2 >= 0.8 and mape <= 10:
            return "good"
        elif r2 >= 0.6 and mape <= 20:
            return "moderate"
        elif r2 >= 0.4:
            return "fair"
        else:
            return "poor"

    def get_chart_data(
        self,
        result: ProcessedResult,
        chart_type: str,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Get formatted data for specific chart type.

        Args:
            result: Processed model result
            chart_type: Type of chart ('contributions', 'decomposition',
                       'response_curves', 'waterfall', 'coefficients', 'diagnostics')
            **kwargs: Additional chart-specific options

        Returns:
            Chart-ready data dictionary
        """
        if chart_type == "contributions":
            return self._get_contribution_chart_data(result, **kwargs)
        elif chart_type == "decomposition":
            return self._get_decomposition_chart_data(result, **kwargs)
        elif chart_type == "response_curves":
            return self._get_response_curve_chart_data(result, **kwargs)
        elif chart_type == "waterfall":
            return self._get_waterfall_chart_data(result, **kwargs)
        elif chart_type == "coefficients":
            return self._get_coefficient_chart_data(result, **kwargs)
        elif chart_type == "diagnostics":
            return self._get_diagnostics_chart_data(result, **kwargs)
        else:
            raise ValueError(f"Unknown chart type: {chart_type}")

    def _get_contribution_chart_data(
        self,
        result: ProcessedResult,
        **kwargs,
    ) -> dict[str, Any]:
        """Format data for contribution pie/bar chart."""
        # Sort by contribution
        sorted_contribs = sorted(
            result.contributions,
            key=lambda x: x.get("contribution_pct", 0),
            reverse=True,
        )

        return {
            "chart_type": "contribution",
            "title": "Channel Contributions",
            "labels": [c["variable"] for c in sorted_contribs],
            "values": [c["contribution_pct"] for c in sorted_contribs],
            "total_contributions": [c["total_contribution"] for c in sorted_contribs],
            "colors": self._generate_colors(len(sorted_contribs)),
        }

    def _get_decomposition_chart_data(
        self,
        result: ProcessedResult,
        **kwargs,
    ) -> dict[str, Any]:
        """Format data for time series decomposition chart."""
        decomp = result.decomposition

        # Build series for stacked area chart
        series = [
            {
                "name": "Base",
                "data": decomp.get("base", []),
                "type": "area",
                "stack": "contributions",
            }
        ]

        # Add each channel contribution
        contributions = decomp.get("contributions", {})
        colors = self._generate_colors(len(contributions) + 1)

        for i, (var_name, values) in enumerate(contributions.items()):
            series.append(
                {
                    "name": var_name,
                    "data": values,
                    "type": "area",
                    "stack": "contributions",
                    "color": colors[i + 1],
                }
            )

        # Add actual line
        series.append(
            {
                "name": "Actual",
                "data": decomp.get("actual", []),
                "type": "line",
                "color": "#000000",
            }
        )

        return {
            "chart_type": "decomposition",
            "title": "Sales Decomposition Over Time",
            "x_axis": {
                "type": "category",
                "data": decomp.get("dates", []),
            },
            "y_axis": {
                "type": "value",
                "name": "Sales",
            },
            "series": series,
            "legend": ["Base"] + list(contributions.keys()) + ["Actual"],
        }

    def _get_response_curve_chart_data(
        self,
        result: ProcessedResult,
        variable: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """Format data for response curve chart."""
        curves = result.response_curves

        if variable:
            # Single variable
            if variable not in curves:
                raise ValueError(f"Variable not found: {variable}")
            curve = curves[variable]
            return {
                "chart_type": "response_curve",
                "title": f"Response Curve: {variable}",
                "x_axis": {"name": "Spend", "data": curve["spend_levels"]},
                "y_axis": {"name": "Response"},
                "series": [
                    {
                        "name": "Response",
                        "data": curve["response_values"],
                        "type": "line",
                    },
                    {
                        "name": "Marginal Response",
                        "data": curve["marginal_response"],
                        "type": "line",
                        "y_axis_index": 1,
                    },
                ],
            }
        else:
            # All variables
            series = []
            colors = self._generate_colors(len(curves))

            for i, (var_name, curve) in enumerate(curves.items()):
                series.append(
                    {
                        "name": var_name,
                        "data": list(zip(curve["spend_levels"], curve["response_values"])),
                        "type": "line",
                        "color": colors[i],
                    }
                )

            return {
                "chart_type": "response_curves",
                "title": "Response Curves by Channel",
                "x_axis": {"name": "Spend"},
                "y_axis": {"name": "Response"},
                "series": series,
            }

    def _get_waterfall_chart_data(
        self,
        result: ProcessedResult,
        **kwargs,
    ) -> dict[str, Any]:
        """Format data for waterfall chart."""
        # Build waterfall from contributions
        items = []
        running_total = 0

        # Find base contribution
        base_contrib = next((c for c in result.contributions if c["variable"] == "base"), None)

        if base_contrib:
            items.append(
                {
                    "name": "Base",
                    "value": base_contrib["total_contribution"],
                    "type": "base",
                }
            )
            running_total = base_contrib["total_contribution"]

        # Add channel contributions
        channel_contribs = [c for c in result.contributions if c["variable"] != "base"]
        sorted_contribs = sorted(
            channel_contribs,
            key=lambda x: x["total_contribution"],
            reverse=True,
        )

        for contrib in sorted_contribs:
            items.append(
                {
                    "name": contrib["variable"],
                    "value": contrib["total_contribution"],
                    "type": "positive" if contrib["total_contribution"] >= 0 else "negative",
                    "start": running_total,
                }
            )
            running_total += contrib["total_contribution"]

        # Add total
        items.append(
            {
                "name": "Total",
                "value": running_total,
                "type": "total",
            }
        )

        return {
            "chart_type": "waterfall",
            "title": "Contribution Waterfall",
            "items": items,
            "total": running_total,
        }

    def _get_coefficient_chart_data(
        self,
        result: ProcessedResult,
        **kwargs,
    ) -> dict[str, Any]:
        """Format data for coefficient chart with error bars."""
        coefs = [c for c in result.coefficients if c["variable"] != "intercept"]
        sorted_coefs = sorted(coefs, key=lambda x: abs(x["estimate"]), reverse=True)

        return {
            "chart_type": "coefficients",
            "title": "Coefficient Estimates",
            "categories": [c["variable"] for c in sorted_coefs],
            "series": [
                {
                    "name": "Estimate",
                    "data": [c["estimate"] for c in sorted_coefs],
                    "type": "bar",
                },
            ],
            "error_bars": [
                {
                    "variable": c["variable"],
                    "lower": c["ci_lower"],
                    "upper": c["ci_upper"],
                }
                for c in sorted_coefs
                if c["ci_lower"] is not None
            ],
            "significance": {c["variable"]: c["is_significant"] for c in sorted_coefs},
        }

    def _get_diagnostics_chart_data(
        self,
        result: ProcessedResult,
        **kwargs,
    ) -> dict[str, Any]:
        """Format data for diagnostics charts."""
        decomp = result.decomposition

        # Residuals data
        residuals = decomp.get("residuals", [])
        predicted = decomp.get("predicted", [])
        actual = decomp.get("actual", [])

        return {
            "chart_type": "diagnostics",
            "panels": [
                {
                    "title": "Actual vs Predicted",
                    "type": "scatter",
                    "data": list(zip(predicted, actual)) if predicted and actual else [],
                    "x_label": "Predicted",
                    "y_label": "Actual",
                },
                {
                    "title": "Residuals vs Predicted",
                    "type": "scatter",
                    "data": list(zip(predicted, residuals)) if predicted and residuals else [],
                    "x_label": "Predicted",
                    "y_label": "Residuals",
                },
                {
                    "title": "Residual Distribution",
                    "type": "histogram",
                    "data": residuals,
                    "bins": 20,
                },
                {
                    "title": "VIF by Variable",
                    "type": "bar",
                    "categories": list(result.diagnostics.get("vif", {}).keys()),
                    "data": list(result.diagnostics.get("vif", {}).values()),
                    "threshold": 10,
                },
            ],
            "statistics": {
                "durbin_watson": result.diagnostics.get("durbin_watson"),
                "jarque_bera_pvalue": result.diagnostics.get("jarque_bera_pvalue"),
                "skewness": result.diagnostics.get("skewness"),
                "kurtosis": result.diagnostics.get("kurtosis"),
            },
        }

    def _generate_colors(self, n: int) -> list[str]:
        """Generate distinct colors for charts."""
        base_colors = [
            "#4E79A7",
            "#F28E2B",
            "#E15759",
            "#76B7B2",
            "#59A14F",
            "#EDC948",
            "#B07AA1",
            "#FF9DA7",
            "#9C755F",
            "#BAB0AC",
        ]

        if n <= len(base_colors):
            return base_colors[:n]

        # Generate additional colors if needed
        colors = base_colors.copy()
        for i in range(n - len(base_colors)):
            # Create variations
            base = base_colors[i % len(base_colors)]
            colors.append(base)

        return colors
