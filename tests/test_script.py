"""Tests for script management."""

import os
from pathlib import Path

import pytest

from cli_anything.lens_studio.core.script import (
    SCRIPT_TEMPLATES,
    attach_script,
    create_script,
    detach_script,
    get_script,
    get_script_by_name,
    list_scripts,
    read_script_content,
    remove_script,
    write_script_content,
)
from cli_anything.lens_studio.core.scene import add_object, find_object_by_name


class TestCreateScript:
    def test_create_blank(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "MyScript")
        assert result["name"] == "MyScript"
        assert result["language"] == "javascript"
        assert result["fileName"] == "MyScript.js"

        file_path = Path(project_dir) / result["relativePath"]
        assert file_path.exists()

    def test_create_typescript(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "TSScript", language="typescript")
        assert result["fileName"] == "TSScript.ts"
        assert result["language"] == "typescript"

    def test_create_with_template(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "TapHandler", template="tap")
        content = read_script_content(project_dir, result)
        assert "TapEvent" in content

    def test_duplicate_name_raises(self, sample_project):
        data, path, project_dir = sample_project
        create_script(data, project_dir, "Dupe")
        with pytest.raises(FileExistsError):
            create_script(data, project_dir, "Dupe")


class TestListScripts:
    def test_list_empty(self, sample_project):
        data, _, _ = sample_project
        assert list_scripts(data) == []

    def test_list_after_create(self, sample_project):
        data, path, project_dir = sample_project
        create_script(data, project_dir, "A")
        create_script(data, project_dir, "B")
        scripts = list_scripts(data)
        assert len(scripts) == 2


class TestGetScript:
    def test_get_by_id(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "Find")
        found = get_script(data, result["id"])
        assert found is not None
        assert found["name"] == "Find"

    def test_get_by_name(self, sample_project):
        data, path, project_dir = sample_project
        create_script(data, project_dir, "ByName")
        found = get_script_by_name(data, "ByName")
        assert found is not None


class TestRemoveScript:
    def test_remove_script(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "ToRemove")
        file_path = Path(project_dir) / result["relativePath"]
        assert file_path.exists()

        remove_script(data, project_dir, result["id"])
        assert len(data["scripts"]) == 0
        assert not file_path.exists()


class TestAttachDetach:
    def test_attach_script(self, sample_project):
        data, path, project_dir = sample_project
        scene_root = data["scene"]["root"]

        script = create_script(data, project_dir, "Attached")
        obj = add_object(scene_root, "ScriptHolder")

        comp = attach_script(data, scene_root, obj["id"], script["id"])
        assert comp["type"] == "ScriptComponent"
        assert comp["scriptId"] == script["id"]

    def test_detach_script(self, sample_project):
        data, path, project_dir = sample_project
        scene_root = data["scene"]["root"]

        script = create_script(data, project_dir, "Detachable")
        obj = add_object(scene_root, "Holder")
        attach_script(data, scene_root, obj["id"], script["id"])

        result = detach_script(scene_root, obj["id"], script["id"])
        assert result is True
        script_comps = [c for c in obj["components"] if c.get("type") == "ScriptComponent"]
        assert len(script_comps) == 0


class TestReadWriteContent:
    def test_read_content(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "Readable")
        content = read_script_content(project_dir, result)
        assert "OnStartEvent" in content

    def test_write_content(self, sample_project):
        data, path, project_dir = sample_project
        result = create_script(data, project_dir, "Writable")
        write_script_content(project_dir, result, "// custom content\n")
        content = read_script_content(project_dir, result)
        assert content == "// custom content\n"


class TestScriptTemplates:
    def test_all_templates_exist(self):
        expected = {"blank", "update", "tap", "tween", "behavior", "typescript"}
        assert set(SCRIPT_TEMPLATES.keys()) == expected
