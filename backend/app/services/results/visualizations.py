"""Visualization data generators for MMM results."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

import numpy as np


@dataclass
class ChartConfig:
    """Base configuration for charts."""

    title: str = ""
    subtitle: str = ""
    width: int = 800
    height: int = 500
    theme: str = "light"
    show_legend: bool = True
    show_tooltip: bool = True
    animation: bool = True
    responsive: bool = True

    # Export options
    exportable: bool = True
    export_formats: list[str] = field(default_factory=lambda: ["png", "svg", "pdf"])


class ChartGenerator(ABC):
    """Abstract base class for chart generators."""

    def __init__(self, config: ChartConfig | None = None):
        self.config = config or ChartConfig()

    @abstractmethod
    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate chart specification from data."""
        pass

    def _base_spec(self) -> dict[str, Any]:
        """Get base chart specification."""
        return {
            "title": {"text": self.config.title, "subtext": self.config.subtitle},
            "tooltip": {"show": self.config.show_tooltip},
            "legend": {"show": self.config.show_legend},
            "animation": self.config.animation,
            "responsive": self.config.responsive,
            "width": self.config.width,
            "height": self.config.height,
        }


class DecompositionChart(ChartGenerator):
    """
    Generates stacked area chart showing time series decomposition.

    Shows how each marketing channel contributes to total sales over time,
    with base/intercept as the bottom layer and channels stacked on top.
    """

    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate decomposition chart spec.

        Args:
            data: Dictionary with keys:
                - dates: List of date strings
                - base: List of base values
                - contributions: Dict of {channel: [values]}
                - actual: List of actual values
                - predicted: List of predicted values
        """
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Sales Decomposition"

        dates = data.get("dates", [])
        base = data.get("base", [])
        contributions = data.get("contributions", {})
        actual = data.get("actual", [])
        predicted = data.get("predicted", [])

        # Build series
        series = []

        # Base layer
        if base:
            series.append(
                {
                    "name": "Base",
                    "type": "area",
                    "stack": "total",
                    "areaStyle": {"opacity": 0.7},
                    "emphasis": {"focus": "series"},
                    "data": base,
                    "color": "#808080",
                }
            )

        # Channel contributions
        colors = self._get_channel_colors(len(contributions))
        for i, (channel, values) in enumerate(contributions.items()):
            series.append(
                {
                    "name": channel,
                    "type": "area",
                    "stack": "total",
                    "areaStyle": {"opacity": 0.7},
                    "emphasis": {"focus": "series"},
                    "data": values,
                    "color": colors[i],
                }
            )

        # Actual values (line overlay)
        if actual:
            series.append(
                {
                    "name": "Actual",
                    "type": "line",
                    "data": actual,
                    "color": "#000000",
                    "lineStyle": {"width": 2},
                    "symbol": "circle",
                    "symbolSize": 4,
                }
            )

        # Predicted values (dashed line)
        if predicted:
            series.append(
                {
                    "name": "Predicted",
                    "type": "line",
                    "data": predicted,
                    "color": "#FF0000",
                    "lineStyle": {"width": 2, "type": "dashed"},
                    "symbol": "none",
                }
            )

        spec["xAxis"] = {
            "type": "category",
            "data": dates,
            "boundaryGap": False,
        }
        spec["yAxis"] = {
            "type": "value",
            "name": "Sales",
        }
        spec["series"] = series
        spec["dataZoom"] = [
            {"type": "inside", "start": 0, "end": 100},
            {"type": "slider", "start": 0, "end": 100},
        ]

        return spec

    def _get_channel_colors(self, n: int) -> list[str]:
        """Get distinct colors for channels."""
        colors = [
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
        return colors[:n] if n <= len(colors) else colors * (n // len(colors) + 1)


class ContributionChart(ChartGenerator):
    """
    Generates contribution charts (pie, bar, or treemap).

    Shows the percentage contribution of each marketing channel
    to total predicted sales.
    """

    def __init__(
        self,
        config: ChartConfig | None = None,
        chart_style: str = "pie",
    ):
        super().__init__(config)
        self.chart_style = chart_style  # 'pie', 'donut', 'bar', 'treemap'

    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate contribution chart spec.

        Args:
            data: Dictionary with keys:
                - contributions: List of {variable, contribution_pct, total_contribution}
        """
        contributions = data.get("contributions", [])

        if self.chart_style == "pie":
            return self._generate_pie(contributions)
        elif self.chart_style == "donut":
            return self._generate_donut(contributions)
        elif self.chart_style == "bar":
            return self._generate_bar(contributions)
        elif self.chart_style == "treemap":
            return self._generate_treemap(contributions)
        else:
            return self._generate_pie(contributions)

    def _generate_pie(self, contributions: list[dict]) -> dict[str, Any]:
        """Generate pie chart specification."""
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Channel Contributions"

        spec["series"] = [
            {
                "name": "Contributions",
                "type": "pie",
                "radius": "70%",
                "center": ["50%", "55%"],
                "data": [
                    {
                        "name": c["variable"],
                        "value": round(c["contribution_pct"], 1),
                    }
                    for c in contributions
                ],
                "label": {
                    "formatter": "{b}: {d}%",
                },
                "emphasis": {
                    "itemStyle": {
                        "shadowBlur": 10,
                        "shadowOffsetX": 0,
                        "shadowColor": "rgba(0, 0, 0, 0.5)",
                    }
                },
            }
        ]

        return spec

    def _generate_donut(self, contributions: list[dict]) -> dict[str, Any]:
        """Generate donut chart specification."""
        spec = self._generate_pie(contributions)
        spec["series"][0]["radius"] = ["40%", "70%"]

        # Add center label with total
        total = sum(c.get("total_contribution", 0) for c in contributions)
        spec["series"][0]["label"] = {
            "show": True,
            "position": "outside",
            "formatter": "{b}: {d}%",
        }
        spec["graphic"] = {
            "type": "text",
            "left": "center",
            "top": "center",
            "style": {
                "text": f"Total\n{total:,.0f}",
                "textAlign": "center",
                "fontSize": 18,
            },
        }

        return spec

    def _generate_bar(self, contributions: list[dict]) -> dict[str, Any]:
        """Generate horizontal bar chart specification."""
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Channel Contributions"

        # Sort by contribution
        sorted_contribs = sorted(
            contributions,
            key=lambda x: x.get("contribution_pct", 0),
        )

        spec["xAxis"] = {"type": "value", "name": "Contribution %"}
        spec["yAxis"] = {
            "type": "category",
            "data": [c["variable"] for c in sorted_contribs],
        }
        spec["series"] = [
            {
                "type": "bar",
                "data": [round(c["contribution_pct"], 1) for c in sorted_contribs],
                "label": {
                    "show": True,
                    "position": "right",
                    "formatter": "{c}%",
                },
                "itemStyle": {"color": "#4E79A7"},
            }
        ]
        spec["grid"] = {"left": "15%", "right": "10%"}

        return spec

    def _generate_treemap(self, contributions: list[dict]) -> dict[str, Any]:
        """Generate treemap specification."""
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Channel Contributions"

        spec["series"] = [
            {
                "type": "treemap",
                "data": [
                    {
                        "name": c["variable"],
                        "value": c.get("total_contribution", 0),
                    }
                    for c in contributions
                ],
                "label": {
                    "formatter": "{b}\n{c}",
                },
                "levels": [
                    {
                        "itemStyle": {
                            "borderWidth": 2,
                            "borderColor": "#fff",
                            "gapWidth": 2,
                        },
                    },
                ],
            }
        ]

        return spec


class ResponseCurveChart(ChartGenerator):
    """
    Generates response curve charts showing diminishing returns.

    Shows how incremental spend translates to incremental response
    for each marketing channel.
    """

    def __init__(
        self,
        config: ChartConfig | None = None,
        show_marginal: bool = True,
        show_roi: bool = False,
    ):
        super().__init__(config)
        self.show_marginal = show_marginal
        self.show_roi = show_roi

    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate response curve chart spec.

        Args:
            data: Dictionary with keys:
                - variable: Channel name (optional, for single channel)
                - spend_levels: List of spend values
                - response_values: List of response values
                - marginal_response: List of marginal response values
                - roi_values: List of ROI values
                OR
                - curves: Dict of {channel: {spend_levels, response_values, ...}}
        """
        if "curves" in data:
            return self._generate_multi_channel(data["curves"])
        else:
            return self._generate_single_channel(data)

    def _generate_single_channel(self, data: dict[str, Any]) -> dict[str, Any]:
        """Generate chart for single channel."""
        spec = self._base_spec()
        variable = data.get("variable", "Channel")
        spec["title"]["text"] = self.config.title or f"Response Curve: {variable}"

        spend = data.get("spend_levels", [])
        response = data.get("response_values", [])
        marginal = data.get("marginal_response", [])
        roi = data.get("roi_values", [])

        spec["xAxis"] = {"type": "value", "name": "Spend"}

        # Primary y-axis for response
        y_axes = [{"type": "value", "name": "Response", "position": "left"}]

        series = [
            {
                "name": "Response",
                "type": "line",
                "data": list(zip(spend, response)),
                "smooth": True,
                "color": "#4E79A7",
                "yAxisIndex": 0,
            }
        ]

        # Secondary y-axis for marginal/ROI
        if self.show_marginal and marginal:
            y_axes.append(
                {
                    "type": "value",
                    "name": "Marginal Response",
                    "position": "right",
                }
            )
            series.append(
                {
                    "name": "Marginal Response",
                    "type": "line",
                    "data": list(zip(spend, marginal)),
                    "smooth": True,
                    "color": "#E15759",
                    "lineStyle": {"type": "dashed"},
                    "yAxisIndex": 1,
                }
            )

        if self.show_roi and roi:
            if len(y_axes) == 1:
                y_axes.append(
                    {
                        "type": "value",
                        "name": "ROI",
                        "position": "right",
                    }
                )
            series.append(
                {
                    "name": "ROI",
                    "type": "line",
                    "data": list(zip(spend, roi)),
                    "smooth": True,
                    "color": "#59A14F",
                    "lineStyle": {"type": "dotted"},
                    "yAxisIndex": 1 if len(y_axes) > 1 else 0,
                }
            )

        spec["yAxis"] = y_axes
        spec["series"] = series

        return spec

    def _generate_multi_channel(self, curves: dict[str, dict]) -> dict[str, Any]:
        """Generate chart comparing multiple channels."""
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Response Curves by Channel"

        spec["xAxis"] = {"type": "value", "name": "Spend"}
        spec["yAxis"] = {"type": "value", "name": "Response"}

        colors = self._get_channel_colors(len(curves))
        series = []

        for i, (channel, curve_data) in enumerate(curves.items()):
            spend = curve_data.get("spend_levels", [])
            response = curve_data.get("response_values", [])

            series.append(
                {
                    "name": channel,
                    "type": "line",
                    "data": list(zip(spend, response)),
                    "smooth": True,
                    "color": colors[i],
                }
            )

        spec["series"] = series

        return spec

    def _get_channel_colors(self, n: int) -> list[str]:
        colors = [
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
        return colors[:n]


class WaterfallChart(ChartGenerator):
    """
    Generates waterfall chart showing contribution buildup.

    Shows how total sales is built up from base + channel contributions.
    """

    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate waterfall chart spec.

        Args:
            data: Dictionary with keys:
                - items: List of {name, value, type} where type is
                  'base', 'positive', 'negative', or 'total'
        """
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Contribution Waterfall"

        items = data.get("items", [])

        categories = [item["name"] for item in items]

        # Calculate cumulative values for waterfall effect
        placeholder_data = []
        increase_data = []
        decrease_data = []

        running_total = 0

        for item in items:
            item_type = item.get("type", "positive")
            value = item.get("value", 0)

            if item_type == "base":
                placeholder_data.append(0)
                increase_data.append(value)
                decrease_data.append(0)
                running_total = value
            elif item_type == "total":
                placeholder_data.append(0)
                increase_data.append(running_total)
                decrease_data.append(0)
            elif value >= 0:
                placeholder_data.append(running_total)
                increase_data.append(value)
                decrease_data.append(0)
                running_total += value
            else:
                running_total += value
                placeholder_data.append(running_total)
                increase_data.append(0)
                decrease_data.append(abs(value))

        spec["xAxis"] = {"type": "category", "data": categories}
        spec["yAxis"] = {"type": "value", "name": "Value"}

        spec["series"] = [
            {
                "name": "Placeholder",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": "transparent"},
                "data": placeholder_data,
            },
            {
                "name": "Increase",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": "#59A14F"},
                "label": {
                    "show": True,
                    "position": "top",
                    "formatter": lambda x: f"+{x['value']:,.0f}" if x["value"] > 0 else "",
                },
                "data": increase_data,
            },
            {
                "name": "Decrease",
                "type": "bar",
                "stack": "total",
                "itemStyle": {"color": "#E15759"},
                "label": {
                    "show": True,
                    "position": "bottom",
                    "formatter": lambda x: f"-{x['value']:,.0f}" if x["value"] > 0 else "",
                },
                "data": decrease_data,
            },
        ]

        # Convert lambda to string formatter for JSON serialization
        for s in spec["series"]:
            if "label" in s and callable(s["label"].get("formatter")):
                s["label"]["formatter"] = "{c}"

        return spec


class DiagnosticsChart(ChartGenerator):
    """
    Generates diagnostic charts for model validation.

    Includes residual plots, actual vs predicted, VIF chart, etc.
    """

    def generate(self, data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate diagnostics charts spec.

        Args:
            data: Dictionary with decomposition and diagnostics data
        """
        spec = self._base_spec()
        spec["title"]["text"] = self.config.title or "Model Diagnostics"

        # Generate multiple panels
        panels = []

        # 1. Actual vs Predicted scatter
        actual = data.get("actual", [])
        predicted = data.get("predicted", [])
        if actual and predicted:
            panels.append(self._actual_vs_predicted(actual, predicted))

        # 2. Residuals vs Predicted
        residuals = data.get("residuals", [])
        if residuals and predicted:
            panels.append(self._residuals_vs_predicted(residuals, predicted))

        # 3. Residual histogram
        if residuals:
            panels.append(self._residual_histogram(residuals))

        # 4. VIF bar chart
        vif = data.get("vif", {})
        if vif:
            panels.append(self._vif_chart(vif))

        spec["panels"] = panels

        return spec

    def _actual_vs_predicted(
        self,
        actual: list[float],
        predicted: list[float],
    ) -> dict[str, Any]:
        """Generate actual vs predicted scatter plot."""
        min_val = min(min(actual), min(predicted))
        max_val = max(max(actual), max(predicted))

        return {
            "title": "Actual vs Predicted",
            "type": "scatter",
            "xAxis": {
                "type": "value",
                "name": "Predicted",
                "min": min_val,
                "max": max_val,
            },
            "yAxis": {
                "type": "value",
                "name": "Actual",
                "min": min_val,
                "max": max_val,
            },
            "series": [
                {
                    "type": "scatter",
                    "data": list(zip(predicted, actual)),
                    "symbolSize": 8,
                    "color": "#4E79A7",
                },
                {
                    "type": "line",
                    "data": [[min_val, min_val], [max_val, max_val]],
                    "lineStyle": {"type": "dashed", "color": "#999"},
                    "symbol": "none",
                },
            ],
        }

    def _residuals_vs_predicted(
        self,
        residuals: list[float],
        predicted: list[float],
    ) -> dict[str, Any]:
        """Generate residuals vs predicted scatter plot."""
        return {
            "title": "Residuals vs Predicted",
            "type": "scatter",
            "xAxis": {"type": "value", "name": "Predicted"},
            "yAxis": {"type": "value", "name": "Residuals"},
            "series": [
                {
                    "type": "scatter",
                    "data": list(zip(predicted, residuals)),
                    "symbolSize": 8,
                    "color": "#4E79A7",
                },
                {
                    "type": "line",
                    "data": [
                        [min(predicted), 0],
                        [max(predicted), 0],
                    ],
                    "lineStyle": {"type": "dashed", "color": "#999"},
                    "symbol": "none",
                },
            ],
        }

    def _residual_histogram(self, residuals: list[float]) -> dict[str, Any]:
        """Generate residual histogram."""
        # Create histogram bins
        hist, bin_edges = np.histogram(residuals, bins=20)
        bin_centers = [(bin_edges[i] + bin_edges[i + 1]) / 2 for i in range(len(bin_edges) - 1)]

        return {
            "title": "Residual Distribution",
            "type": "bar",
            "xAxis": {"type": "category", "data": [f"{x:.1f}" for x in bin_centers]},
            "yAxis": {"type": "value", "name": "Frequency"},
            "series": [
                {
                    "type": "bar",
                    "data": hist.tolist(),
                    "color": "#4E79A7",
                }
            ],
        }

    def _vif_chart(self, vif: dict[str, float]) -> dict[str, Any]:
        """Generate VIF bar chart."""
        sorted_vif = sorted(vif.items(), key=lambda x: x[1], reverse=True)

        return {
            "title": "Variance Inflation Factor (VIF)",
            "type": "bar",
            "xAxis": {"type": "category", "data": [v[0] for v in sorted_vif]},
            "yAxis": {"type": "value", "name": "VIF"},
            "series": [
                {
                    "type": "bar",
                    "data": [v[1] for v in sorted_vif],
                    "itemStyle": {
                        "color": lambda params: "#E15759" if params["value"] > 10 else "#4E79A7",
                    },
                    "markLine": {
                        "data": [{"yAxis": 10, "name": "Threshold"}],
                        "lineStyle": {"type": "dashed", "color": "#E15759"},
                    },
                }
            ],
        }
