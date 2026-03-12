"""Tests for project management."""

import json
import os
from pathlib import Path

import pytest

from cli_anything.lens_studio.core.project import (
    blank_project,
    create_project,
    delete_project,
    list_projects,
    load_project,
    project_info,
    save_project,
)


class TestBlankProject:
    def test_structure(self):
        data = blank_project("Test")
        assert data["name"] == "Test"
        assert data["version"] == "5.0"
        assert "sceneObjects" in data
        assert "resources" in data
        assert "settings" in data

    def test_has_cameras(self):
        data = blank_project("Test")
        names = [o["name"] for o in data["sceneObjects"]]
        assert "Camera" in names
        assert "Orthographic Camera" in names

    def test_template_applied(self):
        data = blank_project("FaceTest", template="face-effects")
        names = [o["name"] for o in data["sceneObjects"]]
        assert "Face Effects" in names

    def test_world_ar_template(self):
        data = blank_project("WorldTest", template="world-ar")
        names = [o["name"] for o in data["sceneObjects"]]
        assert "Device Tracking" in names


class TestCreateProject:
    def test_creates_directory_and_file(self, tmp_dir):
        result = create_project("MyLens", directory=tmp_dir)
        assert os.path.isdir(result["directory"])
        assert os.path.isfile(result["path"])
        assert result["name"] == "MyLens"
        assert result["template"] == "blank"

    def test_creates_assets_directory(self, tmp_dir):
        result = create_project("MyLens", directory=tmp_dir)
        project_dir = Path(result["directory"])
        assert (project_dir / "Assets").is_dir()

    def test_duplicate_project_raises(self, tmp_dir):
        create_project("Dupe", directory=tmp_dir)
        with pytest.raises(FileExistsError):
            create_project("Dupe", directory=tmp_dir)

    def test_invalid_template_raises(self, tmp_dir):
        with pytest.raises(ValueError, match="Unknown template"):
            create_project("Bad", directory=tmp_dir, template="nonexistent")


class TestLoadSaveProject:
    def test_round_trip(self, sample_project):
        data, path, _ = sample_project
        assert data["name"] == "TestProject"

        data["name"] = "Updated"
        save_project(path, data)

        reloaded = load_project(path)
        assert reloaded["name"] == "Updated"

    def test_load_missing_file(self):
        with pytest.raises(FileNotFoundError):
            load_project("/nonexistent/path.lsproj")

    def test_load_wrong_extension(self, tmp_dir):
        bad_file = Path(tmp_dir) / "test.txt"
        bad_file.write_text("{}")
        with pytest.raises(ValueError, match="Not a Lens Studio project"):
            load_project(str(bad_file))


class TestProjectInfo:
    def test_returns_correct_info(self, sample_project):
        _, path, _ = sample_project
        info = project_info(path)
        assert info["name"] == "TestProject"
        assert info["sceneObjects"] >= 2  # Camera + Ortho Camera
        assert "id" in info


class TestListProjects:
    def test_lists_projects(self, tmp_dir):
        create_project("A", directory=tmp_dir)
        create_project("B", directory=tmp_dir)
        projects = list_projects(tmp_dir)
        names = [p["name"] for p in projects]
        assert "A" in names
        assert "B" in names

    def test_empty_directory(self, tmp_dir):
        projects = list_projects(tmp_dir)
        assert projects == []


class TestDeleteProject:
    def test_deletes_project(self, tmp_dir):
        result = create_project("ToDelete", directory=tmp_dir)
        assert os.path.exists(result["directory"])
        delete_project(result["path"])
        assert not os.path.exists(result["directory"])
