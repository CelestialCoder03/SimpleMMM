"""Tests for variable group features."""

from uuid import uuid4

import pytest

from app.schemas.variable_group import (
    VariableGroupCreate,
    VariableGroupList,
    VariableGroupRead,
    VariableGroupUpdate,
)


class TestVariableGroupSchemas:
    """Tests for VariableGroup Pydantic schemas."""

    def test_variable_group_create_valid(self):
        """Test creating a valid VariableGroupCreate schema."""
        data = VariableGroupCreate(
            name="Offline Media",
            description="Traditional media channels",
            variables=["tv_spend", "radio_spend", "ooh_spend"],
            color="#3B82F6",
        )

        assert data.name == "Offline Media"
        assert data.description == "Traditional media channels"
        assert len(data.variables) == 3
        assert data.color == "#3B82F6"

    def test_variable_group_create_minimal(self):
        """Test creating VariableGroupCreate with minimal required fields."""
        data = VariableGroupCreate(
            name="Media",
            variables=["tv"],
        )

        assert data.name == "Media"
        assert data.variables == ["tv"]
        assert data.description is None
        assert data.color is None

    def test_variable_group_create_empty_name_fails(self):
        """Test that empty name fails validation."""
        with pytest.raises(ValueError):
            VariableGroupCreate(
                name="",
                variables=["tv"],
            )

    def test_variable_group_create_empty_variables_fails(self):
        """Test that empty variables list fails validation."""
        with pytest.raises(ValueError):
            VariableGroupCreate(
                name="Media",
                variables=[],
            )

    def test_variable_group_create_invalid_color_fails(self):
        """Test that invalid color format fails validation."""
        with pytest.raises(ValueError):
            VariableGroupCreate(
                name="Media",
                variables=["tv"],
                color="red",  # Not a valid hex color
            )

    def test_variable_group_create_valid_color_formats(self):
        """Test various valid hex color formats."""
        # Uppercase
        data1 = VariableGroupCreate(name="A", variables=["x"], color="#FFFFFF")
        assert data1.color == "#FFFFFF"

        # Lowercase
        data2 = VariableGroupCreate(name="B", variables=["y"], color="#aabbcc")
        assert data2.color == "#aabbcc"

        # Mixed case
        data3 = VariableGroupCreate(name="C", variables=["z"], color="#AaBbCc")
        assert data3.color == "#AaBbCc"

    def test_variable_group_update_partial(self):
        """Test VariableGroupUpdate with partial data."""
        # Only update name
        update1 = VariableGroupUpdate(name="New Name")
        assert update1.name == "New Name"
        assert update1.variables is None

        # Only update variables
        update2 = VariableGroupUpdate(variables=["a", "b"])
        assert update2.name is None
        assert update2.variables == ["a", "b"]

    def test_variable_group_read_from_dict(self):
        """Test VariableGroupRead model validation from dict."""
        data = {
            "id": str(uuid4()),
            "name": "Test Group",
            "description": "Test description",
            "variables": ["var1", "var2"],
            "color": "#FF0000",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
        }

        group = VariableGroupRead.model_validate(data)

        assert group.name == "Test Group"
        assert len(group.variables) == 2

    def test_variable_group_list(self):
        """Test VariableGroupList schema."""
        items = [
            VariableGroupRead(
                id=uuid4(),
                name=f"Group {i}",
                description=None,
                variables=[f"var_{i}"],
                color=None,
                created_at="2024-01-01T00:00:00Z",
                updated_at="2024-01-01T00:00:00Z",
            )
            for i in range(3)
        ]

        group_list = VariableGroupList(items=items, total=3)

        assert len(group_list.items) == 3
        assert group_list.total == 3


class TestVariableGroupValidation:
    """Tests for variable group business logic validation."""

    def test_group_with_single_variable(self):
        """Test that a group can have a single variable."""
        data = VariableGroupCreate(
            name="Single",
            variables=["only_one"],
        )
        assert len(data.variables) == 1

    def test_group_with_many_variables(self):
        """Test group with many variables."""
        variables = [f"var_{i}" for i in range(20)]
        data = VariableGroupCreate(
            name="Large Group",
            variables=variables,
        )
        assert len(data.variables) == 20

    def test_group_name_max_length(self):
        """Test group name respects max length."""
        long_name = "A" * 255  # Max allowed
        data = VariableGroupCreate(
            name=long_name,
            variables=["var"],
        )
        assert len(data.name) == 255

    def test_group_description_can_be_long(self):
        """Test group description can handle long text."""
        long_desc = "This is a detailed description. " * 30
        data = VariableGroupCreate(
            name="Test",
            description=long_desc,
            variables=["var"],
        )
        assert len(data.description) > 500


class TestVariableGroupOverlapDetection:
    """Tests for overlap detection logic (tested via API in integration tests)."""

    def test_detect_overlap_logic(self):
        """Test the overlap detection algorithm."""
        groups = [
            {"name": "Group A", "variables": ["tv", "radio", "print"]},
            {
                "name": "Group B",
                "variables": ["digital", "social", "tv"],
            },  # tv overlaps
            {"name": "Group C", "variables": ["search", "display"]},
        ]

        # Build variable -> groups mapping
        variable_groups = {}
        for group in groups:
            for var in group["variables"]:
                if var not in variable_groups:
                    variable_groups[var] = []
                variable_groups[var].append(group["name"])

        # Find overlapping variables
        overlaps = {var: group_names for var, group_names in variable_groups.items() if len(group_names) > 1}

        assert "tv" in overlaps
        assert set(overlaps["tv"]) == {"Group A", "Group B"}
        assert "radio" not in overlaps
        assert "digital" not in overlaps

    def test_no_overlaps(self):
        """Test when there are no overlaps."""
        groups = [
            {"name": "Offline", "variables": ["tv", "radio"]},
            {"name": "Online", "variables": ["digital", "social"]},
        ]

        variable_groups = {}
        for group in groups:
            for var in group["variables"]:
                if var not in variable_groups:
                    variable_groups[var] = []
                variable_groups[var].append(group["name"])

        overlaps = {var: group_names for var, group_names in variable_groups.items() if len(group_names) > 1}

        assert len(overlaps) == 0

    def test_multiple_overlaps(self):
        """Test detecting multiple overlapping variables."""
        groups = [
            {"name": "A", "variables": ["x", "y", "z"]},
            {"name": "B", "variables": ["x", "y", "w"]},
            {"name": "C", "variables": ["x", "v"]},
        ]

        variable_groups = {}
        for group in groups:
            for var in group["variables"]:
                if var not in variable_groups:
                    variable_groups[var] = []
                variable_groups[var].append(group["name"])

        overlaps = {var: group_names for var, group_names in variable_groups.items() if len(group_names) > 1}

        assert "x" in overlaps
        assert len(overlaps["x"]) == 3  # In all 3 groups
        assert "y" in overlaps
        assert len(overlaps["y"]) == 2
        assert "z" not in overlaps
