"""Budget optimization service using scipy optimization."""

import logging
from dataclasses import dataclass, field
from enum import Enum

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, minimize

logger = logging.getLogger(__name__)


class OptimizationObjective(str, Enum):
    """Optimization objectives."""

    MAXIMIZE_RESPONSE = "maximize_response"
    MAXIMIZE_ROI = "maximize_roi"
    MINIMIZE_COST = "minimize_cost"


@dataclass
class ChannelConstraint:
    """Constraint for a single channel."""

    channel: str
    min_budget: float | None = None
    max_budget: float | None = None
    min_share: float | None = None  # As percentage (0-100)
    max_share: float | None = None  # As percentage (0-100)


@dataclass
class OptimizationResult:
    """Result of budget optimization."""

    success: bool
    message: str
    objective: str
    total_budget: float

    # Current allocation
    current_allocation: dict[str, float] = field(default_factory=dict)
    current_response: float = 0.0
    current_roi: float = 0.0

    # Optimized allocation
    optimized_allocation: dict[str, float] = field(default_factory=dict)
    optimized_response: float = 0.0
    optimized_roi: float = 0.0

    # Improvements
    response_lift: float = 0.0
    response_lift_pct: float = 0.0
    roi_improvement: float = 0.0

    # Per-channel changes
    channel_changes: dict[str, dict[str, float]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "message": self.message,
            "objective": self.objective,
            "total_budget": self.total_budget,
            "current_allocation": self.current_allocation,
            "current_response": self.current_response,
            "current_roi": self.current_roi,
            "optimized_allocation": self.optimized_allocation,
            "optimized_response": self.optimized_response,
            "optimized_roi": self.optimized_roi,
            "response_lift": self.response_lift,
            "response_lift_pct": self.response_lift_pct,
            "roi_improvement": self.roi_improvement,
            "channel_changes": self.channel_changes,
        }


class BudgetOptimizer:
    """
    Budget optimizer for marketing mix models.

    Uses model coefficients and response curves to find optimal
    budget allocation across channels.
    """

    def __init__(
        self,
        channels: list[str],
        coefficients: dict[str, float],
        current_spend: dict[str, float],
        saturation_params: dict[str, dict] | None = None,
    ):
        """
        Initialize budget optimizer.

        Args:
            channels: List of channel names (marketing variables).
            coefficients: Model coefficients per channel.
            current_spend: Current spend per channel.
            saturation_params: Optional saturation curve parameters per channel.
        """
        self.channels = channels
        self.coefficients = coefficients
        self.current_spend = current_spend
        self.saturation_params = saturation_params or {}

        # Ensure all channels have coefficients
        for ch in channels:
            if ch not in self.coefficients:
                self.coefficients[ch] = 0.0

    def _response_function(
        self,
        spend: float,
        channel: str,
    ) -> float:
        """
        Calculate response for a given spend level.

        Uses Hill saturation curve if parameters available,
        otherwise uses linear response.
        """
        coef = self.coefficients.get(channel, 0.0)

        if channel in self.saturation_params:
            params = self.saturation_params[channel]
            half_sat = params.get("half_saturation", spend * 2)
            slope = params.get("slope", 1.0)

            # Hill function: coef * (spend^slope) / (half_sat^slope + spend^slope)
            if spend <= 0:
                return 0.0
            numerator = spend**slope
            denominator = half_sat**slope + spend**slope
            return coef * numerator / denominator if denominator > 0 else 0.0
        else:
            # Linear response
            return coef * spend

    def _total_response(self, allocation: np.ndarray) -> float:
        """Calculate total response for an allocation."""
        total = 0.0
        for i, channel in enumerate(self.channels):
            total += self._response_function(allocation[i], channel)
        return total

    def _objective_maximize_response(self, allocation: np.ndarray) -> float:
        """Objective: maximize total response (negative for minimization)."""
        return -self._total_response(allocation)

    def _objective_maximize_roi(self, allocation: np.ndarray) -> float:
        """Objective: maximize ROI (negative for minimization)."""
        total_response = self._total_response(allocation)
        total_spend = np.sum(allocation)
        if total_spend <= 0:
            return 0.0
        return -(total_response / total_spend)

    def optimize(
        self,
        total_budget: float,
        objective: OptimizationObjective = OptimizationObjective.MAXIMIZE_RESPONSE,
        constraints: list[ChannelConstraint] | None = None,
        min_channel_budget: float = 0.0,
    ) -> OptimizationResult:
        """
        Optimize budget allocation.

        Args:
            total_budget: Total budget to allocate.
            objective: Optimization objective.
            constraints: Optional channel-specific constraints.
            min_channel_budget: Minimum budget per channel (default 0).

        Returns:
            OptimizationResult with optimal allocation.
        """
        n_channels = len(self.channels)
        constraints = constraints or []

        # Build constraint lookup
        channel_constraints = {c.channel: c for c in constraints}

        # Initial allocation (proportional to current spend)
        total_current = sum(self.current_spend.values())
        if total_current > 0:
            x0 = np.array([self.current_spend.get(ch, 0) / total_current * total_budget for ch in self.channels])
        else:
            x0 = np.full(n_channels, total_budget / n_channels)

        # Build bounds for each channel
        lower_bounds = []
        upper_bounds = []

        for ch in self.channels:
            lb = min_channel_budget
            ub = total_budget

            if ch in channel_constraints:
                cc = channel_constraints[ch]
                if cc.min_budget is not None:
                    lb = max(lb, cc.min_budget)
                if cc.max_budget is not None:
                    ub = min(ub, cc.max_budget)
                if cc.min_share is not None:
                    lb = max(lb, total_budget * cc.min_share / 100)
                if cc.max_share is not None:
                    ub = min(ub, total_budget * cc.max_share / 100)

            lower_bounds.append(lb)
            upper_bounds.append(ub)

        bounds = Bounds(lower_bounds, upper_bounds)

        # Budget constraint: sum of allocations = total_budget
        LinearConstraint(
            np.ones(n_channels),
            lb=total_budget,
            ub=total_budget,
        )

        # Select objective function
        if objective == OptimizationObjective.MAXIMIZE_RESPONSE:
            obj_func = self._objective_maximize_response
        elif objective == OptimizationObjective.MAXIMIZE_ROI:
            obj_func = self._objective_maximize_roi
        else:
            obj_func = self._objective_maximize_response

        # Run optimization
        try:
            result = minimize(
                obj_func,
                x0,
                method="SLSQP",
                bounds=bounds,
                constraints=[{"type": "eq", "fun": lambda x: np.sum(x) - total_budget}],
                options={"maxiter": 1000, "ftol": 1e-9},
            )

            success = result.success
            message = result.message if hasattr(result, "message") else "Optimization completed"
            optimized = result.x

        except Exception as e:
            logger.error(f"Optimization failed: {e}")
            return OptimizationResult(
                success=False,
                message=str(e),
                objective=objective.value,
                total_budget=total_budget,
            )

        # Calculate results
        current_allocation = {ch: self.current_spend.get(ch, 0) for ch in self.channels}
        optimized_allocation = {ch: float(optimized[i]) for i, ch in enumerate(self.channels)}

        current_response = sum(self._response_function(current_allocation[ch], ch) for ch in self.channels)
        optimized_response = self._total_response(optimized)

        current_total_spend = sum(current_allocation.values())
        current_roi = current_response / current_total_spend if current_total_spend > 0 else 0
        optimized_roi = optimized_response / total_budget if total_budget > 0 else 0

        response_lift = optimized_response - current_response
        response_lift_pct = (response_lift / current_response * 100) if current_response > 0 else 0
        roi_improvement = optimized_roi - current_roi

        # Per-channel changes
        channel_changes = {}
        for ch in self.channels:
            current = current_allocation[ch]
            optimized_val = optimized_allocation[ch]
            change = optimized_val - current
            change_pct = (change / current * 100) if current > 0 else 0

            channel_changes[ch] = {
                "current": round(current, 2),
                "optimized": round(optimized_val, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
            }

        return OptimizationResult(
            success=success,
            message=message,
            objective=objective.value,
            total_budget=total_budget,
            current_allocation=current_allocation,
            current_response=round(current_response, 2),
            current_roi=round(current_roi, 4),
            optimized_allocation=optimized_allocation,
            optimized_response=round(optimized_response, 2),
            optimized_roi=round(optimized_roi, 4),
            response_lift=round(response_lift, 2),
            response_lift_pct=round(response_lift_pct, 2),
            roi_improvement=round(roi_improvement, 4),
            channel_changes=channel_changes,
        )


def optimize_budget(
    channels: list[str],
    coefficients: dict[str, float],
    current_spend: dict[str, float],
    total_budget: float,
    objective: str = "maximize_response",
    constraints: list[dict] | None = None,
    saturation_params: dict[str, dict] | None = None,
) -> OptimizationResult:
    """
    Convenience function for budget optimization.

    Args:
        channels: List of channel names.
        coefficients: Model coefficients per channel.
        current_spend: Current spend per channel.
        total_budget: Total budget to allocate.
        objective: Optimization objective string.
        constraints: Optional list of constraint dicts.
        saturation_params: Optional saturation parameters.

    Returns:
        OptimizationResult with optimal allocation.
    """
    optimizer = BudgetOptimizer(
        channels=channels,
        coefficients=coefficients,
        current_spend=current_spend,
        saturation_params=saturation_params,
    )

    # Convert objective string to enum
    obj_enum = OptimizationObjective(objective)

    # Convert constraint dicts to ChannelConstraint objects
    channel_constraints = None
    if constraints:
        channel_constraints = [
            ChannelConstraint(
                channel=c["channel"],
                min_budget=c.get("min_budget"),
                max_budget=c.get("max_budget"),
                min_share=c.get("min_share"),
                max_share=c.get("max_share"),
            )
            for c in constraints
        ]

    return optimizer.optimize(
        total_budget=total_budget,
        objective=obj_enum,
        constraints=channel_constraints,
    )
