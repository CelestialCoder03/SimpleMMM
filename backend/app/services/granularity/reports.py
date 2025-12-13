"""Multi-report generation and orchestration."""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

import numpy as np
import pandas as pd

from app.services.granularity.aggregation import GranularityManager, GranularitySpec


@dataclass
class ReportSpec:
    """
    Specification for a report at a certain granularity.

    Attributes:
        name: Report identifier
        granularity: Target data granularity
        model_type: Type of model to use
        group_by: Column to split into sub-models (one model per group value)
        features: Feature columns for modeling
        target: Target column
        constraints: Model constraints

        # Inheritance settings
        parent_report: Reference to parent report (for hierarchical models)
        inherit_constraints: Whether to inherit parent constraints
        inherit_priors: Whether to use parent posteriors as priors
        prior_strength: Weight for parent priors (0=ignore, 1=strong)
        override_constraints: Child-specific constraint overrides
    """

    name: str
    granularity: GranularitySpec
    model_type: str = "ridge"
    group_by: str | None = None
    features: list[str] = field(default_factory=list)
    target: str = "sales"
    constraints: dict[str, Any] | None = None
    priors: dict[str, Any] | None = None
    hyperparameters: dict[str, Any] = field(default_factory=dict)

    # Inheritance settings
    parent_report: str | None = None
    inherit_constraints: bool = False
    inherit_priors: bool = False
    prior_strength: float = 0.5
    override_constraints: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "granularity": self.granularity.to_dict(),
            "model_type": self.model_type,
            "group_by": self.group_by,
            "features": self.features,
            "target": self.target,
            "constraints": self.constraints,
            "priors": self.priors,
            "hyperparameters": self.hyperparameters,
            "parent_report": self.parent_report,
            "inherit_constraints": self.inherit_constraints,
            "inherit_priors": self.inherit_priors,
            "prior_strength": self.prior_strength,
            "override_constraints": self.override_constraints,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReportSpec":
        return cls(
            name=data["name"],
            granularity=GranularitySpec.from_dict(data["granularity"]),
            model_type=data.get("model_type", "ridge"),
            group_by=data.get("group_by"),
            features=data.get("features", []),
            target=data.get("target", "sales"),
            constraints=data.get("constraints"),
            priors=data.get("priors"),
            hyperparameters=data.get("hyperparameters", {}),
            parent_report=data.get("parent_report"),
            inherit_constraints=data.get("inherit_constraints", False),
            inherit_priors=data.get("inherit_priors", False),
            prior_strength=data.get("prior_strength", 0.5),
            override_constraints=data.get("override_constraints"),
        )


@dataclass
class ModelConfig:
    """Configuration for a single model within a report."""

    id: UUID
    report_name: str
    group_value: str | None
    model_type: str
    features: list[str]
    target: str
    constraints: dict[str, Any] | None
    priors: dict[str, Any] | None
    hyperparameters: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "report_name": self.report_name,
            "group_value": self.group_value,
            "model_type": self.model_type,
            "features": self.features,
            "target": self.target,
            "constraints": self.constraints,
            "priors": self.priors,
            "hyperparameters": self.hyperparameters,
        }


class ConstraintInheritance:
    """Handles constraint inheritance from parent to child models."""

    @staticmethod
    def merge_constraints(
        parent_constraints: dict[str, Any] | None,
        child_constraints: dict[str, Any] | None,
        override_constraints: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Merge parent and child constraints.

        Priority: override > child > parent

        Args:
            parent_constraints: Constraints from parent model
            child_constraints: Base constraints for child
            override_constraints: Specific overrides for child

        Returns:
            Merged constraint dictionary
        """
        merged = {}

        # Start with parent
        if parent_constraints:
            for var, constraint in parent_constraints.items():
                merged[var] = constraint.copy() if isinstance(constraint, dict) else constraint

        # Overlay child
        if child_constraints:
            for var, constraint in child_constraints.items():
                if var in merged and isinstance(merged[var], dict) and isinstance(constraint, dict):
                    merged[var] = {**merged[var], **constraint}
                else:
                    merged[var] = constraint

        # Apply overrides
        if override_constraints:
            for var, constraint in override_constraints.items():
                if var in merged and isinstance(merged[var], dict) and isinstance(constraint, dict):
                    merged[var] = {**merged[var], **constraint}
                else:
                    merged[var] = constraint

        return merged if merged else None


class PriorInheritance:
    """Handles prior inheritance for partial pooling in hierarchical models."""

    @staticmethod
    def create_child_priors(
        parent_result: dict[str, Any],
        prior_strength: float = 0.5,
        features: list[str] | None = None,
    ) -> dict[str, Any]:
        """
        Create priors for child model based on parent posteriors.

        Uses parent's coefficient estimates as prior means,
        with variance scaled by prior_strength.

        Args:
            parent_result: Result dictionary from parent model training
            prior_strength: How strongly to weight parent (0=weak, 1=strong)
            features: Optional list of features to create priors for

        Returns:
            Prior configuration dictionary
        """
        model_result = parent_result.get("model_result", {})
        coefficients = model_result.get("coefficients", {})
        std_errors = model_result.get("std_errors", {})

        if not coefficients:
            return {}

        child_priors = {}

        for var, estimate in coefficients.items():
            # Skip if not in feature list
            if features and var not in features:
                continue

            # Get std error (fallback to fraction of estimate)
            std_error = std_errors.get(var)
            if std_error is None or std_error <= 0:
                std_error = abs(estimate) * 0.5 if estimate != 0 else 1.0

            # Adjust std based on prior_strength
            # prior_strength=1.0: tight prior (strong influence from parent)
            # prior_strength=0.1: wide prior (weak influence from parent)
            adjusted_std = std_error / max(prior_strength, 0.01)

            # Create prior specification
            child_priors[var] = {
                "distribution": "normal",
                "mean": float(estimate),
                "std": float(adjusted_std),
            }

        return child_priors

    @staticmethod
    def merge_priors(
        inherited_priors: dict[str, Any],
        explicit_priors: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """
        Merge inherited priors with explicitly specified priors.

        Explicit priors take precedence.
        """
        merged = inherited_priors.copy()

        if explicit_priors:
            for var, prior in explicit_priors.items():
                merged[var] = prior

        return merged


class ReportGenerator:
    """
    Generates and orchestrates multi-granularity reports.

    Handles:
    - Generating model configurations for reports
    - Aggregating data to target granularity
    - Creating multiple sub-models when group_by is specified
    - Inheriting constraints/priors from parent reports
    - Combining results into hierarchical reports
    """

    def __init__(
        self,
        granularity_manager: GranularityManager,
        reports: dict[str, ReportSpec] | None = None,
    ):
        """
        Initialize report generator.

        Args:
            granularity_manager: Manager for data aggregation
            reports: Dictionary of report specifications
        """
        self.gm = granularity_manager
        self.reports = reports or {}
        self._results: dict[str, Any] = {}  # Cache for parent results

    def add_report(self, report: ReportSpec) -> None:
        """Add a report specification."""
        self.reports[report.name] = report

    def generate_model_configs(
        self,
        report_name: str,
        parent_result: dict[str, Any] | None = None,
    ) -> list[tuple[ModelConfig, pd.DataFrame]]:
        """
        Generate model configurations and data for a report.

        If group_by is specified, creates one config per group value.

        Args:
            report_name: Name of report to generate configs for
            parent_result: Optional result from parent model (for inheritance)

        Returns:
            List of (ModelConfig, DataFrame) tuples
        """
        report = self.reports.get(report_name)
        if report is None:
            raise ValueError(f"Report not found: {report_name}")

        # Get parent result if inheritance is enabled and not provided
        if parent_result is None and report.parent_report:
            parent_result = self._results.get(report.parent_report)

        # Aggregate data to target granularity
        df = self.gm.aggregate(report.granularity)

        # Build constraints (with inheritance if enabled)
        constraints = self._build_constraints(report, parent_result)

        # Build priors (with inheritance if enabled)
        priors = self._build_priors(report, parent_result)

        configs = []

        if report.group_by and report.group_by in df.columns:
            # Create one model per group value
            group_values = df[report.group_by].unique()

            for group_value in group_values:
                group_df = df[df[report.group_by] == group_value].copy()

                config = ModelConfig(
                    id=uuid4(),
                    report_name=report_name,
                    group_value=str(group_value),
                    model_type=report.model_type,
                    features=report.features,
                    target=report.target,
                    constraints=constraints,
                    priors=priors,
                    hyperparameters=report.hyperparameters,
                )

                configs.append((config, group_df))
        else:
            # Single model for entire report
            config = ModelConfig(
                id=uuid4(),
                report_name=report_name,
                group_value=None,
                model_type=report.model_type,
                features=report.features,
                target=report.target,
                constraints=constraints,
                priors=priors,
                hyperparameters=report.hyperparameters,
            )

            configs.append((config, df))

        return configs

    def _build_constraints(
        self,
        report: ReportSpec,
        parent_result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Build constraints with optional inheritance."""
        if not report.inherit_constraints or parent_result is None:
            return report.constraints

        # Get parent constraints from config (not result)
        parent_report = self.reports.get(report.parent_report or "")
        parent_constraints = parent_report.constraints if parent_report else None

        return ConstraintInheritance.merge_constraints(
            parent_constraints,
            report.constraints,
            report.override_constraints,
        )

    def _build_priors(
        self,
        report: ReportSpec,
        parent_result: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Build priors with optional inheritance from parent posteriors."""
        if not report.inherit_priors or parent_result is None:
            return report.priors

        # Create priors from parent posteriors
        inherited_priors = PriorInheritance.create_child_priors(
            parent_result,
            prior_strength=report.prior_strength,
            features=report.features,
        )

        # Merge with explicit priors
        return PriorInheritance.merge_priors(inherited_priors, report.priors)

    def store_result(self, report_name: str, result: dict[str, Any]) -> None:
        """Store a result for later inheritance."""
        self._results[report_name] = result

    def get_training_order(self) -> list[str]:
        """
        Get the order in which reports should be trained.

        Parent reports must be trained before children.

        Returns:
            Ordered list of report names
        """
        # Build dependency graph
        dependencies: dict[str, set[str]] = {name: set() for name in self.reports}

        for name, report in self.reports.items():
            if report.parent_report and report.parent_report in self.reports:
                dependencies[name].add(report.parent_report)

        # Topological sort
        order = []
        remaining = set(self.reports.keys())

        while remaining:
            # Find reports with no unprocessed dependencies
            ready = [name for name in remaining if dependencies[name].issubset(set(order))]

            if not ready:
                # Circular dependency
                raise ValueError(f"Circular dependency detected in reports: {remaining}")

            order.extend(sorted(ready))  # Sort for determinism
            remaining -= set(ready)

        return order

    def combine_results(
        self,
        report_name: str,
        sub_results: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Combine multiple sub-model results into a unified report.

        Args:
            report_name: Name of the report
            sub_results: Dictionary of {group_value: model_result}

        Returns:
            Combined report result
        """
        report = self.reports.get(report_name)
        if report is None:
            raise ValueError(f"Report not found: {report_name}")

        combined = {
            "report_name": report_name,
            "granularity": report.granularity.to_dict(),
            "n_models": len(sub_results),
            "group_by": report.group_by,
            "sub_results": {},
            "summary": {},
        }

        # Collect metrics across all sub-models
        all_metrics = []
        all_coefficients = []

        for group_value, result in sub_results.items():
            combined["sub_results"][group_value] = result

            model_result = result.get("model_result", {})
            if model_result:
                all_metrics.append(
                    {
                        "group": group_value,
                        "r_squared": model_result.get("r_squared"),
                        "mape": model_result.get("mape"),
                        "rmse": model_result.get("rmse"),
                    }
                )

                for var, coef in model_result.get("coefficients", {}).items():
                    all_coefficients.append(
                        {
                            "group": group_value,
                            "variable": var,
                            "coefficient": coef,
                        }
                    )

        # Aggregate summary statistics
        if all_metrics:
            r_squared_values = [m["r_squared"] for m in all_metrics if m["r_squared"] is not None]
            mape_values = [m["mape"] for m in all_metrics if m["mape"] is not None]

            combined["summary"] = {
                "avg_r_squared": np.mean(r_squared_values) if r_squared_values else None,
                "min_r_squared": np.min(r_squared_values) if r_squared_values else None,
                "max_r_squared": np.max(r_squared_values) if r_squared_values else None,
                "avg_mape": np.mean(mape_values) if mape_values else None,
                "metrics_by_group": all_metrics,
            }

        # Coefficient comparison across groups
        if all_coefficients:
            coef_df = pd.DataFrame(all_coefficients)
            coef_summary = coef_df.groupby("variable")["coefficient"].agg(["mean", "std", "min", "max"])
            combined["summary"]["coefficient_comparison"] = coef_summary.to_dict(orient="index")

        return combined

    def get_hierarchy(self) -> dict[str, Any]:
        """
        Get the report hierarchy structure.

        Returns:
            Tree structure of reports
        """
        # Find root reports (no parent)
        roots = [name for name, report in self.reports.items() if report.parent_report is None]

        def build_tree(name: str) -> dict[str, Any]:
            report = self.reports[name]
            children = [n for n, r in self.reports.items() if r.parent_report == name]

            return {
                "name": name,
                "granularity": report.granularity.to_dict(),
                "model_type": report.model_type,
                "group_by": report.group_by,
                "children": [build_tree(c) for c in children],
            }

        return {
            "roots": [build_tree(r) for r in roots],
        }
