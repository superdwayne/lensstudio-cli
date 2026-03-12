"""Tests for CLI subcommand interface (subprocess-style)."""

import json
import os
import tempfile

import pytest
from click.testing import CliRunner

from cli_anything.lens_studio.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def project_with_runner(runner, tmp_dir):
    """Create a project and return (runner, project_path, tmp_dir)."""
    result = runner.invoke(cli, [
        "project", "new", "-n", "CLITest", "-d", tmp_dir,
    ], obj={})
    assert result.exit_code == 0
    project_path = os.path.join(tmp_dir, "CLITest", "CLITest.lsproj")
    return runner, project_path, tmp_dir


class TestVersion:
    def test_version_flag(self, runner):
        result = runner.invoke(cli, ["--version"], obj={})
        assert result.exit_code == 0
        assert "cli-anything-lens-studio" in result.output

    def test_version_json(self, runner):
        result = runner.invoke(cli, ["--version", "--json"], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "version" in data


class TestProjectCommands:
    def test_project_new(self, runner, tmp_dir):
        result = runner.invoke(cli, [
            "project", "new", "-n", "TestProj", "-d", tmp_dir,
        ], obj={})
        assert result.exit_code == 0
        assert "Created" in result.output

    def test_project_new_json(self, runner, tmp_dir):
        result = runner.invoke(cli, [
            "project", "new", "-n", "JSONProj", "-d", tmp_dir, "--json",
        ], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert "data" in data

    def test_project_info(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "project", "info",
        ], obj={})
        assert result.exit_code == 0

    def test_project_info_json(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "project", "info", "--json",
        ], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        # render_detail outputs display field keys
        assert "ID" in data or "name" in data or "Name" in data

    def test_project_list(self, project_with_runner):
        runner, _, tmp_dir = project_with_runner
        result = runner.invoke(cli, [
            "project", "list", "-d", tmp_dir,
        ], obj={})
        assert result.exit_code == 0


class TestSceneCommands:
    def test_scene_list(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "scene", "list",
        ], obj={})
        assert result.exit_code == 0

    def test_scene_add(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "scene", "add", "-n", "Cube",
        ], obj={})
        assert result.exit_code == 0
        assert "Added" in result.output

    def test_scene_add_json(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "scene", "add", "-n", "Sphere", "--json",
        ], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "success"
        assert "id" in data["data"]

    def test_scene_tree(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "scene", "tree",
        ], obj={})
        assert result.exit_code == 0


class TestTemplateCommands:
    def test_template_list(self, runner):
        result = runner.invoke(cli, ["template", "list"], obj={})
        assert result.exit_code == 0
        assert "face-effects" in result.output

    def test_template_list_json(self, runner):
        result = runner.invoke(cli, ["template", "list", "--json"], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "templates" in data
        names = [t["name"] for t in data["templates"]]
        assert "blank" in names

    def test_template_info(self, runner):
        result = runner.invoke(cli, ["template", "info", "face-effects"], obj={})
        assert result.exit_code == 0

    def test_template_apply(self, runner, tmp_dir):
        result = runner.invoke(cli, [
            "template", "apply", "-n", "FaceLens", "-t", "face-effects", "-d", tmp_dir,
        ], obj={})
        assert result.exit_code == 0
        assert "Created" in result.output


class TestLensCommands:
    def test_lens_validate(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "lens", "validate",
        ], obj={})
        assert result.exit_code == 0

    def test_lens_validate_json(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path, "lens", "validate", "--json",
        ], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "valid" in data

    def test_lens_build(self, project_with_runner):
        runner, project_path, tmp_dir = project_with_runner
        output = os.path.join(tmp_dir, "output.lens")
        result = runner.invoke(cli, [
            "--project", project_path, "lens", "build", "-o", output,
        ], obj={})
        assert result.exit_code == 0
        assert os.path.exists(output)

    def test_lens_backend_info(self, runner):
        result = runner.invoke(cli, ["lens", "backend-info"], obj={})
        assert result.exit_code == 0


class TestComponentCommands:
    def test_component_list_types(self, runner):
        result = runner.invoke(cli, ["component", "list-types"], obj={})
        assert result.exit_code == 0
        assert "Camera" in result.output

    def test_component_list_types_json(self, runner):
        result = runner.invoke(cli, ["component", "list-types", "--json"], obj={})
        assert result.exit_code == 0
        data = json.loads(result.output)
        types = [t["type"] for t in data["types"]]
        assert "Camera" in types


class TestMaterialCommands:
    def test_material_types(self, runner):
        result = runner.invoke(cli, ["material", "types"], obj={})
        assert result.exit_code == 0
        assert "PBR" in result.output

    def test_material_create(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path,
            "material", "create", "-n", "RedMat", "-t", "PBR",
            "--color", "1", "0", "0", "1",
        ], obj={})
        assert result.exit_code == 0
        assert "Created" in result.output


class TestScriptCommands:
    def test_script_create(self, project_with_runner):
        runner, project_path, _ = project_with_runner
        result = runner.invoke(cli, [
            "--project", project_path,
            "script", "create", "-n", "MainScript",
        ], obj={})
        assert result.exit_code == 0
        assert "Created" in result.output

    def test_script_templates(self, runner):
        result = runner.invoke(cli, ["script", "templates"], obj={})
        assert result.exit_code == 0
