"""Constraint handler for Marketing Mix Model coefficients."""

from typing import Any

import numpy as np


class ConstraintHandler:
    """
    Handler for applying and validating coefficient constraints.

    Constraints in MMM are critical for ensuring economically meaningful results:
    - **Sign constraints**: Marketing spend should typically have positive effect on sales
    - **Bound constraints**: Coefficients should fall within reasonable ranges
    - **Contribution constraints**: Channels shouldn't contribute implausibly high/low
    - **Relationship constraints**: E.g., TV coefficient > Print coefficient

    The handler converts high-level constraint specifications into formats
    suitable for optimization solvers (bounds, linear constraints).

    Usage:
        handler = ConstraintHandler(feature_names=['tv', 'radio', 'print'])
        handler.add_sign_constraint('tv', 'positive')
        handler.add_bound_constraint('radio', min_val=0, max_val=2)
        bounds = handler.get_bounds()
    """

    def __init__(self, feature_names: list[str]):
        """
        Initialize constraint handler.

        Args:
            feature_names: List of feature/variable names.
        """
        self.feature_names = feature_names
        self.n_features = len(feature_names)

        # Initialize with no constraints (unbounded)
        self._bounds: dict[str, tuple[float, float]] = {name: (-np.inf, np.inf) for name in feature_names}

        # Contribution constraints (min%, max%)
        self._contribution_constraints: dict[str, tuple[float | None, float | None]] = {}

        # Group contribution constraints
        self._group_constraints: dict[str, dict[str, Any]] = {}

        # Relationship constraints (feature1 >= multiplier * feature2)
        self._relationship_constraints: list[dict[str, Any]] = []

    def add_sign_constraint(self, feature: str, sign: str) -> None:
        """
        Add sign constraint for a feature.

        Args:
            feature: Feature name.
            sign: 'positive' or 'negative'.
        """
        if feature not in self.feature_names:
            raise ValueError(f"Unknown feature: {feature}")

        current_lower, current_upper = self._bounds[feature]

        if sign == "positive":
            self._bounds[feature] = (max(current_lower, 0), current_upper)
        elif sign == "negative":
            self._bounds[feature] = (current_lower, min(current_upper, 0))
        else:
            raise ValueError(f"Invalid sign: {sign}. Must be 'positive' or 'negative'")

    def add_bound_constraint(
        self,
        feature: str,
        min_val: float | None = None,
        max_val: float | None = None,
    ) -> None:
        """
        Add bound constraints for a feature.

        Args:
            feature: Feature name.
            min_val: Minimum coefficient value.
            max_val: Maximum coefficient value.
        """
        if feature not in self.feature_names:
            raise ValueError(f"Unknown feature: {feature}")

        current_lower, current_upper = self._bounds[feature]

        if min_val is not None:
            current_lower = max(current_lower, min_val)
        if max_val is not None:
            current_upper = min(current_upper, max_val)

        if current_lower > current_upper:
            raise ValueError(f"Invalid bounds for {feature}: min={current_lower} > max={current_upper}")

        self._bounds[feature] = (current_lower, current_upper)

    def add_contribution_constraint(
        self,
        feature: str,
        min_pct: float | None = None,
        max_pct: float | None = None,
    ) -> None:
        """
        Add contribution percentage constraint.

        Note: Contribution constraints are soft constraints that are
        checked after model fitting. They may require iterative adjustment
        of coefficient bounds to satisfy.

        Args:
            feature: Feature name.
            min_pct: Minimum contribution percentage (0-100).
            max_pct: Maximum contribution percentage (0-100).
        """
        if feature not in self.feature_names:
            raise ValueError(f"Unknown feature: {feature}")

        if min_pct is not None and (min_pct < 0 or min_pct > 100):
            raise ValueError("min_pct must be between 0 and 100")
        if max_pct is not None and (max_pct < 0 or max_pct > 100):
            raise ValueError("max_pct must be between 0 and 100")
        if min_pct is not None and max_pct is not None and min_pct > max_pct:
            raise ValueError("min_pct must be <= max_pct")

        self._contribution_constraints[feature] = (min_pct, max_pct)

    def add_group_contribution_constraint(
        self,
        name: str,
        features: list[str],
        min_pct: float | None = None,
        max_pct: float | None = None,
    ) -> None:
        """
        Add contribution constraint for a group of features.

        Args:
            name: Group name.
            features: List of features in the group.
            min_pct: Minimum combined contribution percentage.
            max_pct: Maximum combined contribution percentage.
        """
        for f in features:
            if f not in self.feature_names:
                raise ValueError(f"Unknown feature: {f}")

        self._group_constraints[name] = {
            "features": features,
            "min_pct": min_pct,
            "max_pct": max_pct,
        }

    def add_relationship_constraint(
        self,
        constraint_type: str,
        left: str,
        right: str,
        multiplier: float = 1.0,
    ) -> None:
        """
        Add relationship constraint between coefficients.

        Examples:
            - 'greater_than': coef[left] >= multiplier * coef[right]
            - 'less_than': coef[left] <= multiplier * coef[right]
            - 'equal': coef[left] == multiplier * coef[right]

        Args:
            constraint_type: 'greater_than', 'less_than', or 'equal'.
            left: Left feature name.
            right: Right feature name.
            multiplier: Multiplier for right coefficient.
        """
        if left not in self.feature_names:
            raise ValueError(f"Unknown feature: {left}")
        if right not in self.feature_names:
            raise ValueError(f"Unknown feature: {right}")
        if constraint_type not in ["greater_than", "less_than", "equal"]:
            raise ValueError(f"Invalid constraint type: {constraint_type}")

        self._relationship_constraints.append(
            {
                "type": constraint_type,
                "left": left,
                "right": right,
                "multiplier": multiplier,
            }
        )

    def get_bounds(self) -> list[tuple[float, float]]:
        """
        Get bounds in scipy format.

        Returns:
            List of (lower, upper) tuples for each feature.
        """
        return [self._bounds[name] for name in self.feature_names]

    def get_bounds_dict(self) -> dict[str, tuple[float, float]]:
        """
        Get bounds as dictionary.

        Returns:
            Dictionary mapping feature names to (lower, upper) bounds.
        """
        return self._bounds.copy()

    def get_linear_constraints(self) -> list[dict[str, Any]]:
        """
        Convert relationship constraints to linear constraint format.

        Returns:
            List of constraint dictionaries suitable for scipy.optimize.
        """
        constraints = []

        for rel in self._relationship_constraints:
            left_idx = self.feature_names.index(rel["left"])
            right_idx = self.feature_names.index(rel["right"])

            # Build coefficient vector: [0, ..., 1, ..., -multiplier, ..., 0]
            # For constraint: coef[left] - multiplier * coef[right] >= 0
            A = np.zeros(self.n_features)
            A[left_idx] = 1
            A[right_idx] = -rel["multiplier"]

            if rel["type"] == "greater_than":
                # left >= multiplier * right  =>  left - multiplier * right >= 0
                constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda x, A=A: A @ x,
                    }
                )
            elif rel["type"] == "less_than":
                # left <= multiplier * right  =>  multiplier * right - left >= 0
                constraints.append(
                    {
                        "type": "ineq",
                        "fun": lambda x, A=-A: A @ x,
                    }
                )
            elif rel["type"] == "equal":
                # left == multiplier * right  =>  left - multiplier * right == 0
                constraints.append(
                    {
                        "type": "eq",
                        "fun": lambda x, A=A: A @ x,
                    }
                )

        return constraints

    def validate_coefficients(
        self,
        coefficients: dict[str, float],
    ) -> dict[str, list[str]]:
        """
        Validate coefficients against all constraints.

        Args:
            coefficients: Dictionary of fitted coefficients.

        Returns:
            Dictionary with 'passed' and 'violations' lists.
        """
        violations = []
        passed = []

        # Check bound constraints
        for name, coef in coefficients.items():
            if name not in self._bounds:
                continue

            lower, upper = self._bounds[name]
            if coef < lower - 1e-6:
                violations.append(f"{name}: {coef:.4f} < min({lower:.4f})")
            elif coef > upper + 1e-6:
                violations.append(f"{name}: {coef:.4f} > max({upper:.4f})")
            else:
                passed.append(f"{name}: within bounds")

        # Check relationship constraints
        for rel in self._relationship_constraints:
            left_val = coefficients.get(rel["left"], 0)
            right_val = coefficients.get(rel["right"], 0)
            threshold = rel["multiplier"] * right_val

            if rel["type"] == "greater_than":
                if left_val < threshold - 1e-6:
                    violations.append(
                        f"{rel['left']}({left_val:.4f}) < {rel['multiplier']} * {rel['right']}({right_val:.4f})"
                    )
                else:
                    passed.append(f"{rel['left']} >= {rel['multiplier']} * {rel['right']}")
            elif rel["type"] == "less_than":
                if left_val > threshold + 1e-6:
                    violations.append(
                        f"{rel['left']}({left_val:.4f}) > {rel['multiplier']} * {rel['right']}({right_val:.4f})"
                    )
                else:
                    passed.append(f"{rel['left']} <= {rel['multiplier']} * {rel['right']}")
            elif rel["type"] == "equal":
                if abs(left_val - threshold) > 1e-6:
                    violations.append(
                        f"{rel['left']}({left_val:.4f}) != {rel['multiplier']} * {rel['right']}({right_val:.4f})"
                    )
                else:
                    passed.append(f"{rel['left']} == {rel['multiplier']} * {rel['right']}")

        return {"passed": passed, "violations": violations}

    def validate_contributions(
        self,
        contributions: dict[str, float],
        total: float,
    ) -> dict[str, list[str]]:
        """
        Validate contributions against constraints.

        Args:
            contributions: Dictionary of feature contributions.
            total: Total contribution (sum of all features).

        Returns:
            Dictionary with 'passed' and 'violations' lists.
        """
        violations = []
        passed = []

        if total == 0:
            return {"passed": passed, "violations": ["Total contribution is zero"]}

        # Check individual contribution constraints
        for name, (min_pct, max_pct) in self._contribution_constraints.items():
            contrib = contributions.get(name, 0)
            pct = contrib / total * 100 if total != 0 else 0

            if min_pct is not None and pct < min_pct - 0.01:
                violations.append(f"{name}: {pct:.1f}% < min({min_pct:.1f}%)")
            elif max_pct is not None and pct > max_pct + 0.01:
                violations.append(f"{name}: {pct:.1f}% > max({max_pct:.1f}%)")
            else:
                passed.append(f"{name}: {pct:.1f}% within constraints")

        # Check group contribution constraints
        for group_name, group in self._group_constraints.items():
            group_contrib = sum(contributions.get(f, 0) for f in group["features"])
            pct = group_contrib / total * 100 if total != 0 else 0

            if group["min_pct"] is not None and pct < group["min_pct"] - 0.01:
                violations.append(f"Group {group_name}: {pct:.1f}% < min({group['min_pct']:.1f}%)")
            elif group["max_pct"] is not None and pct > group["max_pct"] + 0.01:
                violations.append(f"Group {group_name}: {pct:.1f}% > max({group['max_pct']:.1f}%)")
            else:
                passed.append(f"Group {group_name}: {pct:.1f}% within constraints")

        return {"passed": passed, "violations": violations}

    @classmethod
    def from_config(
        cls,
        feature_names: list[str],
        config: dict[str, Any] | None,
    ) -> "ConstraintHandler":
        """
        Create handler from configuration dictionary.

        Args:
            feature_names: List of feature names.
            config: Constraint configuration with keys:
                - coefficients: List of {variable, sign, min, max}
                - contributions: List of {variable, min_contribution_pct, max_contribution_pct}
                - group_contributions: List of {name, variables, min_contribution_pct, max_contribution_pct}
                - relationships: List of {type, left, right, multiplier}

        Returns:
            Configured ConstraintHandler instance.
        """
        handler = cls(feature_names)

        if config is None:
            return handler

        # Process coefficient constraints
        for c in config.get("coefficients", []):
            if "sign" in c:
                handler.add_sign_constraint(c["variable"], c["sign"])
            if "min" in c or "max" in c:
                handler.add_bound_constraint(
                    c["variable"],
                    min_val=c.get("min"),
                    max_val=c.get("max"),
                )

        # Process contribution constraints
        for c in config.get("contributions", []):
            handler.add_contribution_constraint(
                c["variable"],
                min_pct=c.get("min_contribution_pct"),
                max_pct=c.get("max_contribution_pct"),
            )

        # Process group contribution constraints
        for c in config.get("group_contributions", []):
            handler.add_group_contribution_constraint(
                c["name"],
                c["variables"],
                min_pct=c.get("min_contribution_pct"),
                max_pct=c.get("max_contribution_pct"),
            )

        # Process relationship constraints
        for c in config.get("relationships", []):
            handler.add_relationship_constraint(
                c["type"],
                c["left"],
                c["right"],
                c.get("multiplier", 1.0),
            )

        return handler
