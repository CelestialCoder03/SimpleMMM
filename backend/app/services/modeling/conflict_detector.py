"""Constraint conflict detection service."""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.constraints import (
    CoefficientConstraint,
    ContributionConstraint,
    GroupContributionConstraint,
)


class ConstraintConflict(BaseModel):
    """Represents a detected constraint conflict."""

    type: Literal["error", "warning", "info"] = Field(..., description="Severity of the conflict")
    code: str = Field(..., description="Machine-readable conflict code")
    message: str = Field(..., description="Human-readable description")
    affected_variables: list[str] = Field(default_factory=list)
    affected_groups: list[str] = Field(default_factory=list)
    suggestion: str | None = Field(None, description="Suggested resolution")


class ConflictDetectionResult(BaseModel):
    """Result of constraint conflict detection."""

    valid: bool = Field(..., description="True if no blocking errors found")
    conflicts: list[ConstraintConflict] = Field(default_factory=list)
    warnings_count: int = 0
    errors_count: int = 0


class ConstraintConflictDetector:
    """
    Detects conflicts between various types of constraints.

    Conflict types detected:
    - Impossible contribution constraints (sum of mins > 100% or sum of maxes < 100%)
    - Group vs individual constraint conflicts
    - Overlapping variable assignments in groups
    - Sign constraint vs bound constraint conflicts
    """

    def __init__(
        self,
        coefficient_constraints: list[CoefficientConstraint] | None = None,
        contribution_constraints: list[ContributionConstraint] | None = None,
        group_constraints: list[GroupContributionConstraint] | None = None,
    ):
        self.coefficient_constraints = coefficient_constraints or []
        self.contribution_constraints = contribution_constraints or []
        self.group_constraints = group_constraints or []
        self.conflicts: list[ConstraintConflict] = []

    def detect_all(self) -> ConflictDetectionResult:
        """Run all conflict detection checks."""
        self.conflicts = []

        self._check_contribution_feasibility()
        self._check_coefficient_bound_conflicts()
        self._check_group_variable_overlaps()
        self._check_group_vs_individual_conflicts()
        self._check_sign_vs_bound_conflicts()

        errors = [c for c in self.conflicts if c.type == "error"]
        warnings = [c for c in self.conflicts if c.type == "warning"]

        return ConflictDetectionResult(
            valid=len(errors) == 0,
            conflicts=self.conflicts,
            warnings_count=len(warnings),
            errors_count=len(errors),
        )

    def _check_contribution_feasibility(self) -> None:
        """Check if contribution constraints are mathematically feasible."""
        # Check individual contributions
        total_min = 0.0
        total_max = 0.0

        for c in self.contribution_constraints:
            if c.min_contribution_pct is not None:
                total_min += c.min_contribution_pct
            if c.max_contribution_pct is not None:
                total_max += c.max_contribution_pct
            else:
                total_max += 100.0  # No max means up to 100%

        if total_min > 100:
            self.conflicts.append(
                ConstraintConflict(
                    type="error",
                    code="CONTRIBUTION_MIN_EXCEEDS_100",
                    message=f"Sum of minimum contributions ({total_min:.1f}%) exceeds 100%",
                    affected_variables=[c.variable for c in self.contribution_constraints if c.min_contribution_pct],
                    suggestion="Reduce minimum contribution percentages so their sum is ≤ 100%",
                )
            )

        if total_max < 100 and len(self.contribution_constraints) > 0:
            # Only warn if we have constraints for all variables
            self.conflicts.append(
                ConstraintConflict(
                    type="warning",
                    code="CONTRIBUTION_MAX_BELOW_100",
                    message=f"Sum of maximum contributions ({total_max:.1f}%) is below 100%",
                    affected_variables=[c.variable for c in self.contribution_constraints if c.max_contribution_pct],
                    suggestion="This may be intentional if not all variables are constrained",
                )
            )

        # Check individual constraint validity
        for c in self.contribution_constraints:
            if (
                c.min_contribution_pct is not None
                and c.max_contribution_pct is not None
                and c.min_contribution_pct > c.max_contribution_pct
            ):
                self.conflicts.append(
                    ConstraintConflict(
                        type="error",
                        code="CONTRIBUTION_MIN_EXCEEDS_MAX",
                        message=(
                            f"Variable '{c.variable}': min ({c.min_contribution_pct}%)"
                            f" > max ({c.max_contribution_pct}%)"
                        ),
                        affected_variables=[c.variable],
                        suggestion="Ensure minimum is less than or equal to maximum",
                    )
                )

    def _check_coefficient_bound_conflicts(self) -> None:
        """Check if coefficient min/max bounds are valid."""
        for c in self.coefficient_constraints:
            if c.min is not None and c.max is not None and c.min > c.max:
                self.conflicts.append(
                    ConstraintConflict(
                        type="error",
                        code="COEFFICIENT_MIN_EXCEEDS_MAX",
                        message=f"Variable '{c.variable}': coefficient min ({c.min}) > max ({c.max})",
                        affected_variables=[c.variable],
                        suggestion="Ensure minimum bound is less than or equal to maximum bound",
                    )
                )

    def _check_group_variable_overlaps(self) -> None:
        """Check if variables appear in multiple groups."""
        variable_groups: dict[str, list[str]] = {}

        for g in self.group_constraints:
            for var in g.variables:
                if var not in variable_groups:
                    variable_groups[var] = []
                variable_groups[var].append(g.name)

        for var, groups in variable_groups.items():
            if len(groups) > 1:
                self.conflicts.append(
                    ConstraintConflict(
                        type="warning",
                        code="VARIABLE_IN_MULTIPLE_GROUPS",
                        message=f"Variable '{var}' appears in multiple groups: {', '.join(groups)}",
                        affected_variables=[var],
                        affected_groups=groups,
                        suggestion="Consider removing the variable from one of the groups",
                    )
                )

    def _check_group_vs_individual_conflicts(self) -> None:
        """Check for conflicts between group and individual contribution constraints."""
        # Build map of individual constraints
        individual_map: dict[str, ContributionConstraint] = {c.variable: c for c in self.contribution_constraints}

        for g in self.group_constraints:
            # Calculate sum of individual mins/maxes for group members
            sum_individual_min = 0.0
            sum_individual_max = 0.0

            for var in g.variables:
                if var in individual_map:
                    ic = individual_map[var]
                    if ic.min_contribution_pct is not None:
                        sum_individual_min += ic.min_contribution_pct
                    if ic.max_contribution_pct is not None:
                        sum_individual_max += ic.max_contribution_pct
                    else:
                        sum_individual_max += 100.0

            # Check if group max < sum of individual mins
            if g.max_contribution_pct is not None and g.max_contribution_pct < sum_individual_min:
                self.conflicts.append(
                    ConstraintConflict(
                        type="error",
                        code="GROUP_MAX_BELOW_INDIVIDUAL_MINS",
                        message=(
                            f"Group '{g.name}' max ({g.max_contribution_pct}%)"
                            f" < sum of member mins ({sum_individual_min}%)"
                        ),
                        affected_variables=g.variables,
                        affected_groups=[g.name],
                        suggestion="Increase group max or reduce individual minimum constraints",
                    )
                )

            # Check if group min > sum of individual maxes
            if (
                g.min_contribution_pct is not None
                and sum_individual_max > 0
                and g.min_contribution_pct > sum_individual_max
            ):
                self.conflicts.append(
                    ConstraintConflict(
                        type="error",
                        code="GROUP_MIN_ABOVE_INDIVIDUAL_MAXES",
                        message=(
                            f"Group '{g.name}' min ({g.min_contribution_pct}%)"
                            f" > sum of member maxes ({sum_individual_max}%)"
                        ),
                        affected_variables=g.variables,
                        affected_groups=[g.name],
                        suggestion="Reduce group min or increase individual maximum constraints",
                    )
                )

    def _check_sign_vs_bound_conflicts(self) -> None:
        """Check for conflicts between sign and bound constraints."""
        for c in self.coefficient_constraints:
            if c.sign == "positive":
                if c.max is not None and c.max < 0:
                    self.conflicts.append(
                        ConstraintConflict(
                            type="error",
                            code="POSITIVE_SIGN_WITH_NEGATIVE_MAX",
                            message=(
                                f"Variable '{c.variable}': positive sign constraint but max bound is negative ({c.max})"
                            ),
                            affected_variables=[c.variable],
                            suggestion="Remove the sign constraint or set a positive max bound",
                        )
                    )
                if c.min is not None and c.min < 0:
                    self.conflicts.append(
                        ConstraintConflict(
                            type="info",
                            code="POSITIVE_SIGN_OVERRIDES_NEGATIVE_MIN",
                            message=(
                                f"Variable '{c.variable}': positive sign constraint"
                                f" will override negative min bound ({c.min})"
                            ),
                            affected_variables=[c.variable],
                            suggestion="Consider setting min to 0 or removing the min bound",
                        )
                    )

            elif c.sign == "negative":
                if c.min is not None and c.min > 0:
                    self.conflicts.append(
                        ConstraintConflict(
                            type="error",
                            code="NEGATIVE_SIGN_WITH_POSITIVE_MIN",
                            message=(
                                f"Variable '{c.variable}': negative sign constraint but min bound is positive ({c.min})"
                            ),
                            affected_variables=[c.variable],
                            suggestion="Remove the sign constraint or set a negative min bound",
                        )
                    )
                if c.max is not None and c.max > 0:
                    self.conflicts.append(
                        ConstraintConflict(
                            type="info",
                            code="NEGATIVE_SIGN_OVERRIDES_POSITIVE_MAX",
                            message=(
                                f"Variable '{c.variable}': negative sign constraint"
                                f" will override positive max bound ({c.max})"
                            ),
                            affected_variables=[c.variable],
                            suggestion="Consider setting max to 0 or removing the max bound",
                        )
                    )


def validate_constraints(
    coefficient_constraints: list[dict] | None = None,
    contribution_constraints: list[dict] | None = None,
    group_constraints: list[dict] | None = None,
) -> ConflictDetectionResult:
    """
    Validate a set of constraints and return any detected conflicts.

    This is a convenience function for API usage.
    """
    coef_list = [CoefficientConstraint(**c) for c in (coefficient_constraints or [])]
    contrib_list = [ContributionConstraint(**c) for c in (contribution_constraints or [])]
    group_list = [GroupContributionConstraint(**g) for g in (group_constraints or [])]

    detector = ConstraintConflictDetector(
        coefficient_constraints=coef_list,
        contribution_constraints=contrib_list,
        group_constraints=group_list,
    )

    return detector.detect_all()
