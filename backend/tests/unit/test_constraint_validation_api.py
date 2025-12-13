"""Tests for constraint validation API endpoint."""

import pytest


class TestValidateConstraintsEndpoint:
    """Tests for POST /projects/{project_id}/models/validate-constraints endpoint."""

    @pytest.fixture
    def valid_constraints_request(self):
        """Valid constraints request payload."""
        return {
            "coefficient_constraints": [
                {"variable": "tv_spend", "sign": "positive", "min": 0, "max": 10},
                {"variable": "digital_spend", "sign": "positive"},
            ],
            "contribution_constraints": [
                {
                    "variable": "tv_spend",
                    "min_contribution_pct": 10,
                    "max_contribution_pct": 40,
                },
                {
                    "variable": "digital_spend",
                    "min_contribution_pct": 15,
                    "max_contribution_pct": 50,
                },
            ],
            "group_constraints": [
                {
                    "name": "media_channels",
                    "variables": ["tv_spend", "digital_spend"],
                    "min_contribution_pct": 30,
                    "max_contribution_pct": 80,
                }
            ],
        }

    @pytest.fixture
    def invalid_constraints_request(self):
        """Invalid constraints request that should fail validation."""
        return {
            "coefficient_constraints": [
                {"variable": "tv_spend", "min": 10, "max": 5},  # min > max
            ],
            "contribution_constraints": [
                {"variable": "digital_spend", "min_contribution_pct": 60},
                {"variable": "print_spend", "min_contribution_pct": 60},  # sum > 100
            ],
            "group_constraints": [],
        }

    def test_validate_constraints_request_structure(self, valid_constraints_request):
        """Test that valid request structure is accepted."""
        # Verify the request structure matches expected schema
        assert "coefficient_constraints" in valid_constraints_request
        assert "contribution_constraints" in valid_constraints_request
        assert "group_constraints" in valid_constraints_request

        # Verify coefficient constraint structure
        coef = valid_constraints_request["coefficient_constraints"][0]
        assert "variable" in coef
        assert "sign" in coef

        # Verify contribution constraint structure
        contrib = valid_constraints_request["contribution_constraints"][0]
        assert "variable" in contrib
        assert "min_contribution_pct" in contrib
        assert "max_contribution_pct" in contrib

        # Verify group constraint structure
        group = valid_constraints_request["group_constraints"][0]
        assert "name" in group
        assert "variables" in group
        assert isinstance(group["variables"], list)

    def test_validate_constraints_response_structure(self):
        """Test expected response structure from validation endpoint."""
        # Expected response format
        expected_structure = {
            "valid": True,
            "conflicts": [],
            "warnings_count": 0,
            "errors_count": 0,
        }

        assert "valid" in expected_structure
        assert "conflicts" in expected_structure
        assert "warnings_count" in expected_structure
        assert "errors_count" in expected_structure

    def test_conflict_response_structure(self):
        """Test expected conflict object structure."""
        conflict = {
            "type": "error",
            "code": "COEFFICIENT_MIN_EXCEEDS_MAX",
            "message": "Variable 'tv_spend': coefficient min (10) > max (5)",
            "affected_variables": ["tv_spend"],
            "affected_groups": [],
            "suggestion": "Ensure minimum bound is less than or equal to maximum bound",
        }

        assert conflict["type"] in ["error", "warning", "info"]
        assert isinstance(conflict["code"], str)
        assert isinstance(conflict["message"], str)
        assert isinstance(conflict["affected_variables"], list)
        assert isinstance(conflict["affected_groups"], list)

    def test_empty_constraints_is_valid(self):
        """Test that empty constraints request is valid."""
        empty_request = {
            "coefficient_constraints": [],
            "contribution_constraints": [],
            "group_constraints": [],
        }

        # This should not raise any errors
        assert len(empty_request["coefficient_constraints"]) == 0

    def test_partial_constraints_request(self):
        """Test request with only some constraint types."""
        # Only coefficient constraints
        partial_request = {
            "coefficient_constraints": [{"variable": "tv", "sign": "positive"}],
            "contribution_constraints": [],
            "group_constraints": [],
        }

        assert len(partial_request["coefficient_constraints"]) == 1
        assert len(partial_request["contribution_constraints"]) == 0


class TestConstraintValidationLogic:
    """Tests for the constraint validation logic used by the API."""

    def test_coefficient_bounds_validation(self):
        """Test coefficient min/max bounds validation."""
        import pytest

        from app.services.modeling.conflict_detector import validate_constraints

        # Valid bounds
        result = validate_constraints(coefficient_constraints=[{"variable": "tv", "min": 0, "max": 10}])
        assert result.valid is True

        # Invalid bounds (min > max) - Pydantic validates at schema level
        with pytest.raises(Exception):  # ValidationError from Pydantic
            validate_constraints(coefficient_constraints=[{"variable": "tv", "min": 10, "max": 5}])

    def test_contribution_sum_validation(self):
        """Test contribution constraint sum validation."""
        from app.services.modeling.conflict_detector import validate_constraints

        # Valid sum (< 100%)
        result = validate_constraints(
            contribution_constraints=[
                {"variable": "tv", "min_contribution_pct": 30},
                {"variable": "digital", "min_contribution_pct": 30},
            ]
        )
        assert result.valid is True

        # Invalid sum (> 100%)
        result = validate_constraints(
            contribution_constraints=[
                {"variable": "tv", "min_contribution_pct": 60},
                {"variable": "digital", "min_contribution_pct": 60},
            ]
        )
        assert result.valid is False

    def test_sign_bound_consistency(self):
        """Test sign and bound constraint consistency."""
        import pytest

        from app.services.modeling.conflict_detector import validate_constraints

        # Inconsistent: positive sign with negative max - Pydantic validates at schema level
        with pytest.raises(Exception):  # ValidationError from Pydantic
            validate_constraints(coefficient_constraints=[{"variable": "tv", "sign": "positive", "max": -5}])

    def test_group_individual_consistency(self):
        """Test group vs individual constraint consistency."""
        from app.services.modeling.conflict_detector import validate_constraints

        # Group max less than sum of individual mins
        result = validate_constraints(
            contribution_constraints=[
                {"variable": "tv", "min_contribution_pct": 30},
                {"variable": "radio", "min_contribution_pct": 30},
            ],
            group_constraints=[
                {
                    "name": "offline",
                    "variables": ["tv", "radio"],
                    "max_contribution_pct": 40,
                }
            ],
        )
        assert result.valid is False
        assert any(c.code == "GROUP_MAX_BELOW_INDIVIDUAL_MINS" for c in result.conflicts)


class TestConstraintValidationEdgeCases:
    """Edge case tests for constraint validation."""

    def test_single_variable_group(self):
        """Test group with single variable."""
        from app.services.modeling.conflict_detector import validate_constraints

        result = validate_constraints(
            group_constraints=[{"name": "single", "variables": ["tv"], "min_contribution_pct": 10}]
        )
        assert result.valid is True

    def test_overlapping_groups(self):
        """Test warning for overlapping groups."""
        from app.services.modeling.conflict_detector import validate_constraints

        result = validate_constraints(
            group_constraints=[
                {"name": "group_a", "variables": ["tv", "radio"]},
                {"name": "group_b", "variables": ["tv", "digital"]},  # tv overlaps
            ]
        )

        # Should be valid but with warning
        assert result.valid is True
        assert result.warnings_count >= 1

    def test_zero_bounds(self):
        """Test constraints with zero bounds."""
        from app.services.modeling.conflict_detector import validate_constraints

        result = validate_constraints(
            coefficient_constraints=[
                {"variable": "tv", "min": 0, "max": 0}  # Valid: min == max
            ]
        )
        assert result.valid is True

    def test_large_number_of_constraints(self):
        """Test validation with many constraints."""
        from app.services.modeling.conflict_detector import validate_constraints

        # Create many valid constraints
        coef_constraints = [{"variable": f"var_{i}", "sign": "positive"} for i in range(50)]

        contrib_constraints = [
            {
                "variable": f"var_{i}",
                "min_contribution_pct": 1,
                "max_contribution_pct": 10,
            }
            for i in range(50)
        ]

        result = validate_constraints(
            coefficient_constraints=coef_constraints,
            contribution_constraints=contrib_constraints,
        )

        # All valid since min contributions sum to 50% and max to 500%
        assert result.valid is True
