"""Tests for constraint conflict detection."""

import pytest

from app.schemas.constraints import (
    CoefficientConstraint,
    ContributionConstraint,
    GroupContributionConstraint,
)
from app.services.modeling.conflict_detector import (
    ConflictDetectionResult,
    ConstraintConflictDetector,
    validate_constraints,
)


class TestConstraintConflictDetector:
    """Tests for ConstraintConflictDetector."""

    def test_no_conflicts_empty_constraints(self):
        """Test that empty constraints return valid result."""
        detector = ConstraintConflictDetector()
        result = detector.detect_all()

        assert result.valid is True
        assert len(result.conflicts) == 0
        assert result.errors_count == 0
        assert result.warnings_count == 0

    def test_valid_contribution_constraints(self):
        """Test valid contribution constraints pass validation."""
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", min_contribution_pct=10, max_contribution_pct=40),
                ContributionConstraint(variable="digital", min_contribution_pct=20, max_contribution_pct=50),
                ContributionConstraint(variable="print", min_contribution_pct=5, max_contribution_pct=30),
            ]
        )
        result = detector.detect_all()

        assert result.valid is True
        assert result.errors_count == 0

    def test_contribution_min_exceeds_100(self):
        """Test error when sum of min contributions exceeds 100%."""
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", min_contribution_pct=50),
                ContributionConstraint(variable="digital", min_contribution_pct=40),
                ContributionConstraint(variable="print", min_contribution_pct=20),
            ]
        )
        result = detector.detect_all()

        assert result.valid is False
        assert result.errors_count >= 1

        error_codes = [c.code for c in result.conflicts if c.type == "error"]
        assert "CONTRIBUTION_MIN_EXCEEDS_100" in error_codes

    def test_contribution_min_exceeds_max(self):
        """Test error when individual min > max - Pydantic validates this at schema level."""
        # Pydantic schema validates min <= max at creation time
        with pytest.raises(Exception):  # ValidationError from Pydantic
            ContributionConstraint(variable="tv", min_contribution_pct=50, max_contribution_pct=30)

    def test_coefficient_min_exceeds_max(self):
        """Test error when coefficient min > max - Pydantic validates this at schema level."""
        # Pydantic schema validates min <= max at creation time
        with pytest.raises(Exception):  # ValidationError from Pydantic
            CoefficientConstraint(variable="tv", min=10, max=5)

    def test_positive_sign_with_negative_max(self):
        """Test error when positive sign constraint but max is negative - Pydantic validates this."""
        # Pydantic schema validates sign/bound consistency at creation time
        with pytest.raises(Exception):  # ValidationError from Pydantic
            CoefficientConstraint(variable="tv", sign="positive", max=-5)

    def test_negative_sign_with_positive_min(self):
        """Test error when negative sign constraint but min is positive - Pydantic validates this."""
        # Pydantic schema validates sign/bound consistency at creation time
        with pytest.raises(Exception):  # ValidationError from Pydantic
            CoefficientConstraint(variable="tv", sign="negative", min=5)

    def test_positive_sign_overrides_negative_min_info(self):
        """Test info message when positive sign will override negative min."""
        detector = ConstraintConflictDetector(
            coefficient_constraints=[
                CoefficientConstraint(variable="tv", sign="positive", min=-5),
            ]
        )
        result = detector.detect_all()

        # Should be valid but with info message
        assert result.valid is True
        info_codes = [c.code for c in result.conflicts if c.type == "info"]
        assert "POSITIVE_SIGN_OVERRIDES_NEGATIVE_MIN" in info_codes

    def test_variable_in_multiple_groups_warning(self):
        """Test warning when variable appears in multiple groups."""
        detector = ConstraintConflictDetector(
            group_constraints=[
                GroupContributionConstraint(name="offline", variables=["tv", "radio"]),
                GroupContributionConstraint(name="traditional", variables=["tv", "print"]),
            ]
        )
        result = detector.detect_all()

        # Should be valid but with warning
        assert result.valid is True
        assert result.warnings_count >= 1

        warning_codes = [c.code for c in result.conflicts if c.type == "warning"]
        assert "VARIABLE_IN_MULTIPLE_GROUPS" in warning_codes

        # Check that tv is listed as affected
        overlap_conflict = next(c for c in result.conflicts if c.code == "VARIABLE_IN_MULTIPLE_GROUPS")
        assert "tv" in overlap_conflict.affected_variables

    def test_group_max_below_individual_mins(self):
        """Test error when group max < sum of individual mins."""
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", min_contribution_pct=30),
                ContributionConstraint(variable="radio", min_contribution_pct=25),
            ],
            group_constraints=[
                GroupContributionConstraint(
                    name="offline",
                    variables=["tv", "radio"],
                    max_contribution_pct=40,  # Less than 30+25=55
                ),
            ],
        )
        result = detector.detect_all()

        assert result.valid is False
        error_codes = [c.code for c in result.conflicts if c.type == "error"]
        assert "GROUP_MAX_BELOW_INDIVIDUAL_MINS" in error_codes

    def test_group_min_above_individual_maxes(self):
        """Test error when group min > sum of individual maxes."""
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", max_contribution_pct=20),
                ContributionConstraint(variable="radio", max_contribution_pct=15),
            ],
            group_constraints=[
                GroupContributionConstraint(
                    name="offline",
                    variables=["tv", "radio"],
                    min_contribution_pct=50,  # More than 20+15=35
                ),
            ],
        )
        result = detector.detect_all()

        assert result.valid is False
        error_codes = [c.code for c in result.conflicts if c.type == "error"]
        assert "GROUP_MIN_ABOVE_INDIVIDUAL_MAXES" in error_codes

    def test_valid_group_constraints(self):
        """Test valid group constraints pass validation."""
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", min_contribution_pct=10, max_contribution_pct=30),
                ContributionConstraint(variable="radio", min_contribution_pct=5, max_contribution_pct=20),
            ],
            group_constraints=[
                GroupContributionConstraint(
                    name="offline",
                    variables=["tv", "radio"],
                    min_contribution_pct=20,  # >= 10+5=15
                    max_contribution_pct=45,  # <= 30+20=50
                ),
            ],
        )
        result = detector.detect_all()

        assert result.valid is True
        assert result.errors_count == 0

    def test_conflict_has_suggestion(self):
        """Test that conflicts include suggestions."""
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", min_contribution_pct=60),
                ContributionConstraint(variable="digital", min_contribution_pct=60),
            ]
        )
        result = detector.detect_all()

        assert len(result.conflicts) > 0
        conflict = result.conflicts[0]
        assert conflict.suggestion is not None
        assert len(conflict.suggestion) > 0

    def test_multiple_contribution_errors(self):
        """Test detecting multiple contribution errors at once."""
        # Test that multiple contribution constraints with sum > 100% are detected
        detector = ConstraintConflictDetector(
            contribution_constraints=[
                ContributionConstraint(variable="tv", min_contribution_pct=50),
                ContributionConstraint(variable="digital", min_contribution_pct=40),
                ContributionConstraint(variable="print", min_contribution_pct=30),  # Sum = 120% > 100%
            ]
        )
        result = detector.detect_all()

        assert result.valid is False
        assert result.errors_count >= 1
        error_codes = [c.code for c in result.conflicts if c.type == "error"]
        assert "CONTRIBUTION_MIN_EXCEEDS_100" in error_codes


class TestValidateConstraintsFunction:
    """Tests for the validate_constraints convenience function."""

    def test_validate_empty_constraints(self):
        """Test validating empty constraints."""
        result = validate_constraints()

        assert isinstance(result, ConflictDetectionResult)
        assert result.valid is True

    def test_validate_with_dict_inputs(self):
        """Test validation with dict inputs (as would come from API)."""
        result = validate_constraints(
            coefficient_constraints=[{"variable": "tv", "sign": "positive", "min": 0, "max": 10}],
            contribution_constraints=[
                {
                    "variable": "tv",
                    "min_contribution_pct": 10,
                    "max_contribution_pct": 50,
                }
            ],
            group_constraints=[
                {
                    "name": "media",
                    "variables": ["tv", "digital"],
                    "min_contribution_pct": 20,
                }
            ],
        )

        assert isinstance(result, ConflictDetectionResult)
        assert result.valid is True

    def test_validate_catches_errors(self):
        """Test that validation catches errors from dict inputs."""
        result = validate_constraints(
            contribution_constraints=[
                {"variable": "tv", "min_contribution_pct": 80},
                {"variable": "digital", "min_contribution_pct": 80},
            ]
        )

        assert result.valid is False
        assert result.errors_count >= 1
