"""Dimension hierarchy definitions and management."""

from dataclasses import dataclass, field
from typing import Any

import pandas as pd


@dataclass
class DimensionLevel:
    """
    A single level in a dimension hierarchy.

    Attributes:
        name: Unique identifier for this level (e.g., "province")
        column: Column name in dataset (None if aggregated level)
        display_name: Human-readable name for UI
        order: Position in hierarchy (0=coarsest/most aggregated)
    """

    name: str
    column: str | None
    display_name: str
    order: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "column": self.column,
            "display_name": self.display_name,
            "order": self.order,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DimensionLevel":
        return cls(
            name=data["name"],
            column=data.get("column"),
            display_name=data.get("display_name", data["name"]),
            order=data.get("order", 0),
        )


@dataclass
class Dimension:
    """
    A hierarchical dimension with multiple levels.

    Examples:
        Geography: national → region → province → city
        Time: year → quarter → month → week → day
        Channel: all_channels → channel_group → channel

    Attributes:
        name: Dimension identifier (e.g., "geography")
        display_name: Human-readable name
        levels: Ordered list of levels from coarsest to finest
    """

    name: str
    display_name: str
    levels: list[DimensionLevel] = field(default_factory=list)

    def __post_init__(self):
        # Ensure levels are sorted by order
        self.levels = sorted(self.levels, key=lambda x: x.order)

    def get_level(self, name: str) -> DimensionLevel | None:
        """Get a level by name."""
        for level in self.levels:
            if level.name == name:
                return level
        return None

    def get_level_by_column(self, column: str) -> DimensionLevel | None:
        """Get a level by column name."""
        for level in self.levels:
            if level.column == column:
                return level
        return None

    def get_parent_level(self, name: str) -> DimensionLevel | None:
        """Get the parent (coarser) level of a given level."""
        level = self.get_level(name)
        if level is None:
            return None

        for l in reversed(self.levels):
            if l.order < level.order:
                return l
        return None

    def get_child_level(self, name: str) -> DimensionLevel | None:
        """Get the child (finer) level of a given level."""
        level = self.get_level(name)
        if level is None:
            return None

        for l in self.levels:
            if l.order > level.order:
                return l
        return None

    def get_finest_level(self) -> DimensionLevel | None:
        """Get the finest (most granular) level."""
        return self.levels[-1] if self.levels else None

    def get_coarsest_level(self) -> DimensionLevel | None:
        """Get the coarsest (most aggregated) level."""
        return self.levels[0] if self.levels else None

    def is_ancestor(self, ancestor: str, descendant: str) -> bool:
        """Check if one level is an ancestor (coarser) of another."""
        ancestor_level = self.get_level(ancestor)
        descendant_level = self.get_level(descendant)

        if ancestor_level is None or descendant_level is None:
            return False

        return ancestor_level.order < descendant_level.order

    def get_levels_between(
        self,
        coarse: str,
        fine: str,
        inclusive: bool = True,
    ) -> list[DimensionLevel]:
        """Get all levels between two levels."""
        coarse_level = self.get_level(coarse)
        fine_level = self.get_level(fine)

        if coarse_level is None or fine_level is None:
            return []

        result = []
        for level in self.levels:
            if inclusive:
                if coarse_level.order <= level.order <= fine_level.order:
                    result.append(level)
            else:
                if coarse_level.order < level.order < fine_level.order:
                    result.append(level)

        return result

    def validate_dataset(self, df: pd.DataFrame) -> dict[str, Any]:
        """
        Validate that dataset contains required columns for this dimension.

        Returns validation result with missing columns and warnings.
        """
        result = {
            "valid": True,
            "missing_columns": [],
            "warnings": [],
        }

        for level in self.levels:
            if level.column is not None:
                if level.column not in df.columns:
                    result["missing_columns"].append(level.column)
                    result["valid"] = False

        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "display_name": self.display_name,
            "levels": [level.to_dict() for level in self.levels],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Dimension":
        levels = [DimensionLevel.from_dict(l) for l in data.get("levels", [])]
        return cls(
            name=data["name"],
            display_name=data.get("display_name", data["name"]),
            levels=levels,
        )


class DimensionRegistry:
    """
    Registry for managing dimension configurations.

    Provides pre-defined common dimensions and allows custom dimensions.
    """

    def __init__(self):
        self._dimensions: dict[str, Dimension] = {}
        self._load_defaults()

    def _load_defaults(self):
        """Load default dimension configurations."""
        # Time dimension
        self.register(
            Dimension(
                name="time",
                display_name="Time",
                levels=[
                    DimensionLevel("all_time", None, "All Time", 0),
                    DimensionLevel("year", "year", "Year", 1),
                    DimensionLevel("quarter", "quarter", "Quarter", 2),
                    DimensionLevel("month", "month", "Month", 3),
                    DimensionLevel("week", "week", "Week", 4),
                    DimensionLevel("day", "date", "Day", 5),
                ],
            )
        )

        # Geography dimension
        self.register(
            Dimension(
                name="geography",
                display_name="Geography",
                levels=[
                    DimensionLevel("global", None, "Global", 0),
                    DimensionLevel("region", "region", "Region", 1),
                    DimensionLevel("country", "country", "Country", 2),
                    DimensionLevel("province", "province", "Province/State", 3),
                    DimensionLevel("city", "city", "City", 4),
                    DimensionLevel("district", "district", "District", 5),
                ],
            )
        )

        # Channel dimension
        self.register(
            Dimension(
                name="channel",
                display_name="Channel",
                levels=[
                    DimensionLevel("all_channels", None, "All Channels", 0),
                    DimensionLevel("channel_group", "channel_group", "Channel Group", 1),
                    DimensionLevel("channel", "channel", "Channel", 2),
                    DimensionLevel("sub_channel", "sub_channel", "Sub-Channel", 3),
                ],
            )
        )

    def register(self, dimension: Dimension) -> None:
        """Register a dimension."""
        self._dimensions[dimension.name] = dimension

    def get(self, name: str) -> Dimension | None:
        """Get a dimension by name."""
        return self._dimensions.get(name)

    def list_all(self) -> list[Dimension]:
        """List all registered dimensions."""
        return list(self._dimensions.values())

    def create_custom(
        self,
        name: str,
        display_name: str,
        levels: list[dict[str, Any]],
    ) -> Dimension:
        """Create and register a custom dimension."""
        dim_levels = [
            DimensionLevel(
                name=l["name"],
                column=l.get("column"),
                display_name=l.get("display_name", l["name"]),
                order=i,
            )
            for i, l in enumerate(levels)
        ]

        dimension = Dimension(
            name=name,
            display_name=display_name,
            levels=dim_levels,
        )

        self.register(dimension)
        return dimension

    def auto_detect_dimensions(
        self,
        df: pd.DataFrame,
        column_hints: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Auto-detect dimension mappings from dataset columns.

        Args:
            df: Dataset to analyze
            column_hints: Optional hints {column_name: dimension_level}

        Returns:
            List of suggested dimension configurations
        """
        suggestions = []
        column_hints = column_hints or {}

        for dim in self._dimensions.values():
            matched_levels = []

            for level in dim.levels:
                if level.column is None:
                    continue

                # Check if column exists directly
                if level.column in df.columns:
                    matched_levels.append(
                        {
                            "level": level.name,
                            "column": level.column,
                            "confidence": "high",
                        }
                    )
                # Check hints
                elif level.name in column_hints.values():
                    for col, hint_level in column_hints.items():
                        if hint_level == level.name and col in df.columns:
                            matched_levels.append(
                                {
                                    "level": level.name,
                                    "column": col,
                                    "confidence": "user_specified",
                                }
                            )
                # Check for similar column names
                else:
                    for col in df.columns:
                        col_lower = col.lower()
                        if level.column.lower() in col_lower or level.name.lower() in col_lower:
                            matched_levels.append(
                                {
                                    "level": level.name,
                                    "column": col,
                                    "confidence": "medium",
                                }
                            )
                            break

            if matched_levels:
                suggestions.append(
                    {
                        "dimension": dim.name,
                        "display_name": dim.display_name,
                        "matched_levels": matched_levels,
                        "unmatched_levels": [
                            l.name
                            for l in dim.levels
                            if l.column and l.name not in [m["level"] for m in matched_levels]
                        ],
                    }
                )

        return suggestions

    def get_unique_values_at_level(
        self,
        df: pd.DataFrame,
        dimension: str,
        level: str,
        parent_filter: dict[str, Any] | None = None,
    ) -> list[Any]:
        """
        Get unique values at a dimension level, optionally filtered by parent.

        Args:
            df: Dataset
            dimension: Dimension name
            level: Level name
            parent_filter: Optional filter {column: value} to restrict by parent

        Returns:
            List of unique values
        """
        dim = self.get(dimension)
        if dim is None:
            raise ValueError(f"Dimension not found: {dimension}")

        level_obj = dim.get_level(level)
        if level_obj is None:
            raise ValueError(f"Level not found: {level}")

        if level_obj.column is None:
            return []  # Aggregated level has no values

        result_df = df

        # Apply parent filter
        if parent_filter:
            for col, value in parent_filter.items():
                if col in result_df.columns:
                    result_df = result_df[result_df[col] == value]

        if level_obj.column not in result_df.columns:
            return []

        return result_df[level_obj.column].dropna().unique().tolist()
