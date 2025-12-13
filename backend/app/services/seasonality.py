"""Seasonality feature generation service."""

from enum import Enum
from typing import Any

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field


class SeasonalityMethod(str, Enum):
    """Seasonality generation method."""

    CALENDAR = "calendar"
    FOURIER = "fourier"
    BOTH = "both"


class CalendarFeatureConfig(BaseModel):
    """Configuration for calendar-based seasonality features."""

    include_weekend: bool = Field(default=True, description="Add is_weekend binary feature")
    include_month: bool = Field(default=True, description="Add month dummy variables (12)")
    include_quarter: bool = Field(default=False, description="Add quarter dummy variables (4)")
    include_day_of_week: bool = Field(default=False, description="Add day of week dummy variables (7)")
    include_year: bool = Field(default=False, description="Add year dummy variables")


class FourierFeatureConfig(BaseModel):
    """Configuration for Fourier-based seasonality features."""

    periods: list[int] = Field(default=[7, 30, 365], description="Periods to model (days)")
    n_terms: int = Field(default=3, ge=1, le=10, description="Number of Fourier terms per period")


class SeasonalityConfig(BaseModel):
    """Complete seasonality configuration."""

    enabled: bool = Field(default=False)
    method: SeasonalityMethod = Field(default=SeasonalityMethod.CALENDAR)
    calendar: CalendarFeatureConfig = Field(default_factory=CalendarFeatureConfig)
    fourier: FourierFeatureConfig = Field(default_factory=FourierFeatureConfig)


class SeasonalityService:
    """Service for generating seasonality features."""

    def __init__(self, config: SeasonalityConfig):
        self.config = config

    def generate_features(
        self,
        df: pd.DataFrame,
        date_column: str,
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """
        Generate seasonality features based on configuration.

        Args:
            df: Input DataFrame
            date_column: Name of the date column

        Returns:
            Tuple of (DataFrame with new features, list of feature metadata)
        """
        if not self.config.enabled:
            return df, []

        result_df = df.copy()
        feature_metadata = []

        # Parse dates
        dates = pd.to_datetime(result_df[date_column])

        if self.config.method in [SeasonalityMethod.CALENDAR, SeasonalityMethod.BOTH]:
            result_df, calendar_meta = self._generate_calendar_features(result_df, dates)
            feature_metadata.extend(calendar_meta)

        if self.config.method in [SeasonalityMethod.FOURIER, SeasonalityMethod.BOTH]:
            result_df, fourier_meta = self._generate_fourier_features(result_df, dates)
            feature_metadata.extend(fourier_meta)

        return result_df, feature_metadata

    def _generate_calendar_features(
        self,
        df: pd.DataFrame,
        dates: pd.Series,
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """Generate calendar-based seasonality features."""
        result_df = df.copy()
        feature_metadata = []
        cal_config = self.config.calendar

        if cal_config.include_weekend:
            col_name = "is_weekend"
            result_df[col_name] = (dates.dt.dayofweek >= 5).astype(int)
            feature_metadata.append(
                {
                    "name": col_name,
                    "type": "seasonality",
                    "subtype": "calendar",
                    "description": "Weekend indicator (Sat=1, Sun=1)",
                }
            )

        if cal_config.include_month:
            # One-hot encode months (drop first to avoid multicollinearity)
            for month in range(2, 13):  # Skip month 1 (reference)
                col_name = f"month_{month}"
                result_df[col_name] = (dates.dt.month == month).astype(int)
                feature_metadata.append(
                    {
                        "name": col_name,
                        "type": "seasonality",
                        "subtype": "calendar",
                        "description": f"Month {month} indicator",
                    }
                )

        if cal_config.include_quarter:
            for quarter in range(2, 5):  # Skip Q1 (reference)
                col_name = f"quarter_{quarter}"
                result_df[col_name] = (dates.dt.quarter == quarter).astype(int)
                feature_metadata.append(
                    {
                        "name": col_name,
                        "type": "seasonality",
                        "subtype": "calendar",
                        "description": f"Quarter {quarter} indicator",
                    }
                )

        if cal_config.include_day_of_week:
            for dow in range(1, 7):  # Skip Monday (reference)
                col_name = f"dow_{dow}"
                result_df[col_name] = (dates.dt.dayofweek == dow).astype(int)
                feature_metadata.append(
                    {
                        "name": col_name,
                        "type": "seasonality",
                        "subtype": "calendar",
                        "description": f"Day of week {dow} indicator (0=Mon, 6=Sun)",
                    }
                )

        if cal_config.include_year:
            years = dates.dt.year.unique()
            reference_year = years.min()
            for year in years:
                if year == reference_year:
                    continue
                col_name = f"year_{year}"
                result_df[col_name] = (dates.dt.year == year).astype(int)
                feature_metadata.append(
                    {
                        "name": col_name,
                        "type": "seasonality",
                        "subtype": "calendar",
                        "description": f"Year {year} indicator",
                    }
                )

        return result_df, feature_metadata

    def _generate_fourier_features(
        self,
        df: pd.DataFrame,
        dates: pd.Series,
        target_column: str | None = None,
    ) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
        """Generate Fourier-based seasonality features.

        Fourier features are scaled to have meaningful magnitude relative to the data.
        This prevents extremely large coefficients in the regression.
        """
        result_df = df.copy()
        feature_metadata = []
        fourier_config = self.config.fourier

        # Calculate time index based on data frequency
        # Use row index as time unit (works for any frequency)
        n_obs = len(dates)
        time_index = np.arange(n_obs)

        for period in fourier_config.periods:
            # Adjust period based on data length
            # If period > n_obs, it won't complete a cycle, so use a fraction
            effective_period = min(period, n_obs)

            for i in range(1, fourier_config.n_terms + 1):
                # Sin term - values in [-1, 1]
                sin_col = f"sin_{period}_{i}"
                result_df[sin_col] = np.sin(2 * np.pi * i * time_index / effective_period)
                feature_metadata.append(
                    {
                        "name": sin_col,
                        "type": "seasonality",
                        "subtype": "fourier",
                        "description": f"Fourier sin term (period={period}, order={i})",
                    }
                )

                # Cos term - values in [-1, 1]
                cos_col = f"cos_{period}_{i}"
                result_df[cos_col] = np.cos(2 * np.pi * i * time_index / effective_period)
                feature_metadata.append(
                    {
                        "name": cos_col,
                        "type": "seasonality",
                        "subtype": "fourier",
                        "description": f"Fourier cos term (period={period}, order={i})",
                    }
                )

        return result_df, feature_metadata

    def get_feature_names(self) -> list[str]:
        """Get list of feature names that would be generated."""
        if not self.config.enabled:
            return []

        names = []
        cal_config = self.config.calendar
        fourier_config = self.config.fourier

        if self.config.method in [SeasonalityMethod.CALENDAR, SeasonalityMethod.BOTH]:
            if cal_config.include_weekend:
                names.append("is_weekend")
            if cal_config.include_month:
                names.extend([f"month_{m}" for m in range(2, 13)])
            if cal_config.include_quarter:
                names.extend([f"quarter_{q}" for q in range(2, 5)])
            if cal_config.include_day_of_week:
                names.extend([f"dow_{d}" for d in range(1, 7)])

        if self.config.method in [SeasonalityMethod.FOURIER, SeasonalityMethod.BOTH]:
            for period in fourier_config.periods:
                for i in range(1, fourier_config.n_terms + 1):
                    names.append(f"sin_{period}_{i}")
                    names.append(f"cos_{period}_{i}")

        return names
