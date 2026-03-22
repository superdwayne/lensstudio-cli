"""Tests for cli_anything.lens_studio.utils.validation module."""

import pytest
from pathlib import Path

from cli_anything.lens_studio.utils.validation import (
    sanitize_project_name,
    validate_project_path,
)
from cli_anything.lens_studio.exceptions import InvalidProjectNameError, ValidationError


# ---------------------------------------------------------------------------
# sanitize_project_name
# ---------------------------------------------------------------------------

class TestSanitizeProjectName:
    def test_valid_simple_name(self):
        assert sanitize_project_name("MyProject") == "MyProject"

    def test_valid_name_with_hyphens(self):
        assert sanitize_project_name("my-project") == "my-project"

    def test_valid_name_with_underscores(self):
        assert sanitize_project_name("my_project") == "my_project"

    def test_valid_name_with_spaces(self):
        assert sanitize_project_name("My Project") == "My Project"

    def test_valid_name_with_numbers(self):
        assert sanitize_project_name("Project123") == "Project123"

    def test_strips_whitespace(self):
        assert sanitize_project_name("  MyProject  ") == "MyProject"

    def test_empty_string_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("")

    def test_whitespace_only_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("   ")

    def test_none_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name(None)

    def test_path_traversal_dots_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("../etc/passwd")

    def test_tilde_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("~root")

    def test_null_byte_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("bad\x00name")

    def test_special_characters_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("my@project!")

    def test_too_long_name_raises(self):
        with pytest.raises(InvalidProjectNameError):
            sanitize_project_name("a" * 65)

    def test_max_length_name_ok(self):
        name = "a" * 64
        assert sanitize_project_name(name) == name


# ---------------------------------------------------------------------------
# validate_project_path
# ---------------------------------------------------------------------------

class TestValidateProjectPath:
    def test_resolves_path(self, tmp_path):
        p = tmp_path / "project"
        p.mkdir()
        result = validate_project_path(str(p))
        assert result == p.resolve()

    def test_within_projects_dir(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        target = projects / "my-lens"
        target.mkdir()
        result = validate_project_path(str(target), projects_dir=projects)
        assert result == target.resolve()

    def test_outside_projects_dir_raises(self, tmp_path):
        projects = tmp_path / "projects"
        projects.mkdir()
        outside = tmp_path / "other"
        outside.mkdir()
        with pytest.raises(ValidationError):
            validate_project_path(str(outside), projects_dir=projects)

    def test_no_projects_dir_always_passes(self, tmp_path):
        result = validate_project_path(str(tmp_path))
        assert result == tmp_path.resolve()
