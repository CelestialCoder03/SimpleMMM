"""Tests for budget optimization features."""

import pytest

from app.services.optimization.budget_optimizer import (
    BudgetOptimizer,
    ChannelConstraint,
    OptimizationObjective,
    OptimizationResult,
    optimize_budget,
)


class TestBudgetOptimizer:
    """Tests for BudgetOptimizer."""

    @pytest.fixture
    def channels(self):
        """Sample channels."""
        return ["tv", "digital", "print", "radio"]

    @pytest.fixture
    def coefficients(self):
        """Sample coefficients."""
        return {
            "tv": 0.5,
            "digital": 0.8,
            "print": 0.3,
            "radio": 0.4,
        }

    @pytest.fixture
    def current_spend(self):
        """Sample current spend."""
        return {
            "tv": 30000,
            "digital": 40000,
            "print": 15000,
            "radio": 15000,
        }

    @pytest.fixture
    def optimizer(self, channels, coefficients, current_spend):
        """Create optimizer instance."""
        return BudgetOptimizer(
            channels=channels,
            coefficients=coefficients,
            current_spend=current_spend,
        )

    def test_optimize_maximize_response(self, optimizer):
        """Test optimization with maximize response objective."""
        result = optimizer.optimize(
            total_budget=100000,
            objective=OptimizationObjective.MAXIMIZE_RESPONSE,
        )

        assert isinstance(result, OptimizationResult)
        assert result.success
        assert result.total_budget == 100000
        # Sum of optimized allocation should equal total budget
        assert sum(result.optimized_allocation.values()) == pytest.approx(100000, rel=0.01)

    def test_optimize_maximize_roi(self, optimizer):
        """Test optimization with maximize ROI objective."""
        result = optimizer.optimize(
            total_budget=100000,
            objective=OptimizationObjective.MAXIMIZE_ROI,
        )

        assert result.success
        assert result.optimized_roi >= result.current_roi or result.optimized_roi == pytest.approx(
            result.current_roi, rel=0.1
        )

    def test_optimize_respects_budget_constraint(self, optimizer):
        """Test that optimization respects total budget constraint."""
        result = optimizer.optimize(
            total_budget=50000,
            objective=OptimizationObjective.MAXIMIZE_RESPONSE,
        )

        total_allocated = sum(result.optimized_allocation.values())
        assert total_allocated == pytest.approx(50000, rel=0.01)

    def test_optimize_with_channel_constraints(self, optimizer):
        """Test optimization with channel-specific constraints."""
        constraints = [
            ChannelConstraint(channel="tv", min_budget=10000, max_budget=40000),
            ChannelConstraint(channel="digital", min_share=20, max_share=50),
        ]

        result = optimizer.optimize(
            total_budget=100000,
            objective=OptimizationObjective.MAXIMIZE_RESPONSE,
            constraints=constraints,
        )

        assert result.success
        # TV should be within bounds
        assert result.optimized_allocation["tv"] >= 10000
        assert result.optimized_allocation["tv"] <= 40000
        # Digital should be within share bounds
        digital_share = result.optimized_allocation["digital"] / 100000 * 100
        assert digital_share >= 20
        assert digital_share <= 50

    def test_optimize_with_min_channel_budget(self, optimizer):
        """Test optimization with minimum channel budget."""
        result = optimizer.optimize(
            total_budget=100000,
            objective=OptimizationObjective.MAXIMIZE_RESPONSE,
            min_channel_budget=5000,
        )

        # All channels should have at least 5000
        for channel, allocation in result.optimized_allocation.items():
            assert allocation >= 5000

    def test_response_function_linear(self, optimizer):
        """Test linear response function."""
        response = optimizer._response_function(1000, "tv")
        expected = 0.5 * 1000  # coefficient * spend
        assert response == expected

    def test_response_function_with_saturation(self):
        """Test response function with saturation parameters."""
        optimizer = BudgetOptimizer(
            channels=["channel_a"],
            coefficients={"channel_a": 1.0},
            current_spend={"channel_a": 1000},
            saturation_params={"channel_a": {"half_saturation": 500, "slope": 1.0}},
        )

        # Response should be diminishing
        response_low = optimizer._response_function(500, "channel_a")
        response_high = optimizer._response_function(1000, "channel_a")

        # Doubling spend should not double response with saturation
        assert response_high < response_low * 2

    def test_channel_changes_calculation(self, optimizer):
        """Test that channel changes are calculated correctly."""
        result = optimizer.optimize(
            total_budget=100000,
            objective=OptimizationObjective.MAXIMIZE_RESPONSE,
        )

        for channel in result.channel_changes:
            change = result.channel_changes[channel]
            assert "current" in change
            assert "optimized" in change
            assert "change" in change
            assert "change_pct" in change
            # Verify change calculation
            assert change["change"] == pytest.approx(change["optimized"] - change["current"], rel=0.01)

    def test_result_to_dict(self, optimizer):
        """Test OptimizationResult to_dict method."""
        result = optimizer.optimize(
            total_budget=100000,
            objective=OptimizationObjective.MAXIMIZE_RESPONSE,
        )

        result_dict = result.to_dict()

        assert isinstance(result_dict, dict)
        assert "success" in result_dict
        assert "optimized_allocation" in result_dict
        assert "response_lift" in result_dict
        assert "channel_changes" in result_dict


class TestOptimizeBudgetFunction:
    """Tests for the convenience function."""

    def test_optimize_budget_convenience(self):
        """Test optimize_budget convenience function."""
        result = optimize_budget(
            channels=["a", "b"],
            coefficients={"a": 0.5, "b": 0.8},
            current_spend={"a": 5000, "b": 5000},
            total_budget=10000,
            objective="maximize_response",
        )

        assert isinstance(result, OptimizationResult)
        assert result.success

    def test_optimize_budget_with_constraints(self):
        """Test optimize_budget with constraints as dicts."""
        result = optimize_budget(
            channels=["a", "b"],
            coefficients={"a": 0.5, "b": 0.8},
            current_spend={"a": 5000, "b": 5000},
            total_budget=10000,
            objective="maximize_response",
            constraints=[
                {"channel": "a", "min_share": 30, "max_share": 70},
            ],
        )

        assert result.success
        a_share = result.optimized_allocation["a"] / 10000 * 100
        assert a_share >= 30
        assert a_share <= 70


class TestEdgeCases:
    """Tests for edge cases."""

    def test_zero_current_spend(self):
        """Test with zero current spend."""
        optimizer = BudgetOptimizer(
            channels=["a", "b"],
            coefficients={"a": 0.5, "b": 0.8},
            current_spend={"a": 0, "b": 0},
        )

        result = optimizer.optimize(total_budget=10000)

        assert result.success
        assert sum(result.optimized_allocation.values()) == pytest.approx(10000, rel=0.01)

    def test_single_channel(self):
        """Test with single channel."""
        optimizer = BudgetOptimizer(
            channels=["only_channel"],
            coefficients={"only_channel": 1.0},
            current_spend={"only_channel": 5000},
        )

        result = optimizer.optimize(total_budget=10000)

        assert result.success
        assert result.optimized_allocation["only_channel"] == pytest.approx(10000, rel=0.01)

    def test_missing_coefficient(self):
        """Test with missing coefficient (should default to 0)."""
        optimizer = BudgetOptimizer(
            channels=["a", "b"],
            coefficients={"a": 0.5},  # b is missing
            current_spend={"a": 5000, "b": 5000},
        )

        # Should not raise an error
        result = optimizer.optimize(total_budget=10000)
        assert result.success
