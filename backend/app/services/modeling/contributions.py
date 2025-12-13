"""Contribution calculator for Marketing Mix Models."""

from typing import Any

import numpy as np
from numpy.typing import NDArray


class ContributionCalculator:
    """
    Calculate marketing channel contributions from fitted MMM.

    Contributions decompose the target variable (e.g., sales) into
    components attributable to each marketing channel and baseline.

    Key outputs:
    - **Total contribution**: Sum of contribution across all time periods
    - **Contribution percentage**: Share of total contribution
    - **Time series decomposition**: Contribution at each time point
    - **ROI calculation**: Return on investment per channel

    Mathematical formulation:
        y_hat = intercept + Σ(coef[i] * X[i])

        contribution[i] = coef[i] * X[i]  (time series)
        total_contribution[i] = Σ(contribution[i])  (sum across time)
        contribution_pct[i] = total_contribution[i] / Σ(total_contribution)

    Usage:
        calculator = ContributionCalculator(
            coefficients={'tv': 0.5, 'radio': 0.3},
            intercept=1000,
            feature_names=['tv', 'radio'],
        )
        contributions = calculator.calculate(X_transformed)
    """

    def __init__(
        self,
        coefficients: dict[str, float],
        intercept: float,
        feature_names: list[str],
    ):
        """
        Initialize contribution calculator.

        Args:
            coefficients: Dictionary mapping feature names to coefficients.
            intercept: Model intercept (base sales).
            feature_names: Ordered list of feature names matching X columns.
        """
        self.coefficients = coefficients
        self.intercept = intercept
        self.feature_names = feature_names

        # Validate
        for name in feature_names:
            if name not in coefficients:
                raise ValueError(f"Missing coefficient for feature: {name}")

    def calculate(
        self,
        X: NDArray[np.float64],
        y_actual: NDArray[np.float64] | None = None,
        spend: NDArray[np.float64] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate contributions for all features.

        Args:
            X: Transformed feature matrix of shape (n_samples, n_features).
               Should already have transformations applied.
            y_actual: Optional actual target values for decomposition.
            spend: Optional original spend values for ROI calculation.
               Shape (n_samples, n_features).

        Returns:
            Dictionary with contribution results.
        """
        X = np.asarray(X, dtype=np.float64)
        n_samples, n_features = X.shape

        if n_features != len(self.feature_names):
            raise ValueError(f"X has {n_features} columns but {len(self.feature_names)} features expected")

        # Calculate contribution time series for each feature
        contributions_ts: dict[str, NDArray[np.float64]] = {}
        for i, name in enumerate(self.feature_names):
            contributions_ts[name] = self.coefficients[name] * X[:, i]

        # Base contribution (intercept)
        base = np.full(n_samples, self.intercept, dtype=np.float64)

        # Predicted values
        predicted = base.copy()
        for name in self.feature_names:
            predicted = predicted + contributions_ts[name]

        # Total contributions (sum across time)
        total_contributions = {name: float(np.sum(contributions_ts[name])) for name in self.feature_names}
        total_contributions["base"] = float(np.sum(base))

        # Calculate contribution percentages
        # Only consider positive contributions for percentage calculation
        total_positive = sum(max(0, contrib) for contrib in total_contributions.values())

        if total_positive > 0:
            contribution_pct = {
                name: max(0, total_contributions[name]) / total_positive * 100 for name in total_contributions
            }
        else:
            contribution_pct = {name: 0.0 for name in total_contributions}

        # Summary statistics per feature
        feature_stats = {}
        for name in self.feature_names:
            ts = contributions_ts[name]
            feature_stats[name] = {
                "total": float(np.sum(ts)),
                "mean": float(np.mean(ts)),
                "std": float(np.std(ts)),
                "min": float(np.min(ts)),
                "max": float(np.max(ts)),
                "contribution_pct": contribution_pct[name],
            }

        # Base stats
        feature_stats["base"] = {
            "total": float(np.sum(base)),
            "mean": float(np.mean(base)),
            "std": 0.0,
            "min": float(self.intercept),
            "max": float(self.intercept),
            "contribution_pct": contribution_pct["base"],
        }

        # Calculate ROI if spend data provided
        roi = None
        if spend is not None:
            spend = np.asarray(spend, dtype=np.float64)
            if spend.shape[1] == n_features:
                roi = {}
                for i, name in enumerate(self.feature_names):
                    total_spend = np.sum(spend[:, i])
                    total_contrib = total_contributions[name]

                    if total_spend > 0:
                        # ROI = (contribution - cost) / cost
                        # But commonly in MMM: ROI = contribution / spend
                        roi[name] = total_contrib / total_spend
                    else:
                        roi[name] = 0.0

        result = {
            "contributions_time_series": contributions_ts,
            "base_time_series": base,
            "predicted": predicted,
            "total_contributions": total_contributions,
            "contribution_pct": contribution_pct,
            "feature_stats": feature_stats,
            "n_samples": n_samples,
        }

        if roi is not None:
            result["roi"] = roi

        if y_actual is not None:
            y_actual = np.asarray(y_actual, dtype=np.float64)
            result["actual"] = y_actual
            result["residuals"] = y_actual - predicted

        return result

    def calculate_marginal_contribution(
        self,
        X: NDArray[np.float64],
        feature_idx: int,
        spend_levels: NDArray[np.float64] | None = None,
    ) -> dict[str, Any]:
        """
        Calculate marginal contribution curve for a feature.

        Shows how contribution changes with different spend levels.

        Args:
            X: Feature matrix.
            feature_idx: Index of feature to analyze.
            spend_levels: Optional custom spend levels to evaluate.

        Returns:
            Dictionary with marginal contribution data.
        """
        X = np.asarray(X, dtype=np.float64)
        feature_name = self.feature_names[feature_idx]

        # Get the feature values
        feature_values = X[:, feature_idx]

        if spend_levels is None:
            # Create range from 0 to 2x max
            max_val = np.max(feature_values)
            spend_levels = np.linspace(0, max_val * 2, 100)

        # Calculate contribution at each spend level
        contributions = self.coefficients[feature_name] * spend_levels

        # Marginal contribution (derivative) - for transformed features
        # This is a simplified version; actual marginal depends on transformation
        marginal = np.gradient(contributions, spend_levels)

        return {
            "feature": feature_name,
            "spend_levels": spend_levels.tolist(),
            "contributions": contributions.tolist(),
            "marginal_contributions": marginal.tolist(),
        }

    def get_decomposition_dataframe(
        self,
        X: NDArray[np.float64],
        y_actual: NDArray[np.float64] | None = None,
        dates: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Get decomposition data suitable for visualization.

        Args:
            X: Transformed feature matrix.
            y_actual: Optional actual values.
            dates: Optional date labels.

        Returns:
            Dictionary with decomposition data for charts.
        """
        result = self.calculate(X, y_actual)
        n = result["n_samples"]

        decomposition = {
            "base": result["base_time_series"].tolist(),
            "predicted": result["predicted"].tolist(),
        }

        for name in self.feature_names:
            decomposition[name] = result["contributions_time_series"][name].tolist()

        if y_actual is not None:
            decomposition["actual"] = result["actual"].tolist()

        if dates is not None:
            decomposition["dates"] = dates
        else:
            decomposition["dates"] = list(range(n))

        return decomposition

    def calculate_waterfall(
        self,
        X: NDArray[np.float64],
    ) -> list[dict[str, Any]]:
        """
        Calculate waterfall chart data.

        Shows how each component contributes to the total.

        Args:
            X: Transformed feature matrix.

        Returns:
            List of waterfall segments.
        """
        result = self.calculate(X)
        total_contribs = result["total_contributions"]

        # Sort features by contribution
        sorted_features = sorted(
            self.feature_names,
            key=lambda x: total_contribs[x],
            reverse=True,
        )

        waterfall = []
        running_total = 0

        # Start with base
        waterfall.append(
            {
                "name": "Base",
                "value": total_contribs["base"],
                "start": 0,
                "end": total_contribs["base"],
                "type": "base",
            }
        )
        running_total = total_contribs["base"]

        # Add features
        for name in sorted_features:
            contrib = total_contribs[name]
            waterfall.append(
                {
                    "name": name,
                    "value": contrib,
                    "start": running_total,
                    "end": running_total + contrib,
                    "type": "increase" if contrib >= 0 else "decrease",
                }
            )
            running_total += contrib

        # Add total
        waterfall.append(
            {
                "name": "Total",
                "value": running_total,
                "start": 0,
                "end": running_total,
                "type": "total",
            }
        )

        return waterfall

    def calculate_response_curves(
        self,
        X_original: NDArray[np.float64],
        transformer_configs: dict[str, Any] | None = None,
        n_points: int = 100,
    ) -> dict[str, dict[str, Any]]:
        """
        Calculate response curves for each feature.

        Response curves show the relationship between spend and
        expected contribution, accounting for transformations.

        Args:
            X_original: Original (untransformed) feature values.
            transformer_configs: Transformation configurations per feature.
            n_points: Number of points for the curve.

        Returns:
            Dictionary of response curve data per feature.
        """
        from app.services.modeling.transformations import FeatureTransformer

        X = np.asarray(X_original, dtype=np.float64)
        response_curves = {}

        for i, name in enumerate(self.feature_names):
            feature_values = X[:, i]
            max_val = np.max(feature_values) * 1.5
            min_val = 0

            # Generate spend levels
            spend_levels = np.linspace(min_val, max_val, n_points)

            # Get transformer for this feature
            if transformer_configs and name in transformer_configs:
                config = transformer_configs[name]
                transformer = FeatureTransformer.from_config(
                    adstock_config=config.get("adstock"),
                    saturation_config=config.get("saturation"),
                )
            else:
                transformer = FeatureTransformer()

            # Calculate response at each spend level
            # For simplicity, use steady-state (constant spend)
            response_values = []
            for spend in spend_levels:
                # Assume constant spend for n periods
                x_const = np.full(52, spend)  # 52 weeks
                x_transformed = transformer.transform(x_const)
                # Take last value (steady state)
                response = self.coefficients[name] * x_transformed[-1]
                response_values.append(response)

            response_values = np.array(response_values)

            # Marginal response
            marginal = np.gradient(response_values, spend_levels)

            # ROI at each level
            roi_values = np.where(
                spend_levels > 0,
                response_values / spend_levels,
                0,
            )

            response_curves[name] = {
                "spend_levels": spend_levels.tolist(),
                "response_values": response_values.tolist(),
                "marginal_response": marginal.tolist(),
                "roi_values": roi_values.tolist(),
            }

        return response_curves

    def to_summary_dict(
        self,
        X: NDArray[np.float64],
        y_actual: NDArray[np.float64] | None = None,
    ) -> dict[str, Any]:
        """
        Generate summary dictionary for storage/serialization.

        Args:
            X: Transformed feature matrix.
            y_actual: Optional actual values.

        Returns:
            Serializable dictionary with all contribution data.
        """
        result = self.calculate(X, y_actual)

        # Prepare contribution results for each feature
        contributions_list = []
        for name in self.feature_names:
            stats = result["feature_stats"][name]
            contributions_list.append(
                {
                    "variable": name,
                    "total_contribution": stats["total"],
                    "contribution_pct": stats["contribution_pct"],
                    "avg_contribution": stats["mean"],
                    "min_contribution": stats["min"],
                    "max_contribution": stats["max"],
                }
            )

        # Add base
        base_stats = result["feature_stats"]["base"]
        contributions_list.append(
            {
                "variable": "base",
                "total_contribution": base_stats["total"],
                "contribution_pct": base_stats["contribution_pct"],
                "avg_contribution": base_stats["mean"],
                "min_contribution": base_stats["min"],
                "max_contribution": base_stats["max"],
            }
        )

        # Sort by contribution
        contributions_list.sort(key=lambda x: x["total_contribution"], reverse=True)

        return {
            "contributions": contributions_list,
            "total_predicted": float(np.sum(result["predicted"])),
            "n_samples": result["n_samples"],
            "roi": result.get("roi"),
        }
