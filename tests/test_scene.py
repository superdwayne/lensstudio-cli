"""Tests for scene graph operations (flat sceneObjects format)."""

import pytest

from cli_anything.lens_studio.core.scene import (
    add_object,
    duplicate_object,
    find_object,
    find_object_by_name,
    flatten_scene,
    get_children,
    get_roots,
    remove_object,
    rename_object,
    reparent,
    scene_to_tree,
    set_enabled,
    set_transform,
)


class TestFindObject:
    def test_find_camera(self, sample_project):
        data, _, _ = sample_project
        camera = find_object_by_name(data, "Camera")
        assert camera is not None
        assert camera["name"] == "Camera"

    def test_find_by_id(self, sample_project):
        data, _, _ = sample_project
        camera = find_object_by_name(data, "Camera")
        found = find_object(data, camera["id"])
        assert found is camera

    def test_find_nonexistent(self, sample_project):
        data, _, _ = sample_project
        result = find_object(data, "nonexistent-id")
        assert result is None


class TestAddObject:
    def test_add_object(self, sample_project):
        data, _, _ = sample_project
        before = len(data["sceneObjects"])
        obj = add_object(data, "NewObject")
        assert obj["name"] == "NewObject"
        assert obj["id"] is not None
        assert len(data["sceneObjects"]) == before + 1

    def test_add_to_parent(self, sample_project):
        data, _, _ = sample_project
        camera = find_object_by_name(data, "Camera")
        child = add_object(data, "CameraChild", parent_id=camera["id"])
        assert child["parentId"] == camera["id"]
        children = get_children(data, camera["id"])
        assert child in children

    def test_add_to_nonexistent_parent(self, sample_project):
        data, _, _ = sample_project
        with pytest.raises(ValueError, match="Parent object not found"):
            add_object(data, "Orphan", parent_id="bad-id")


class TestRemoveObject:
    def test_remove_object(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "ToRemove")
        remove_object(data, obj["id"])
        assert find_object(data, obj["id"]) is None

    def test_remove_nonexistent(self, sample_project):
        data, _, _ = sample_project
        with pytest.raises(ValueError, match="Object not found"):
            remove_object(data, "bad-id")


class TestRename:
    def test_rename_object(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "OldName")
        rename_object(data, obj["id"], "NewName")
        assert obj["name"] == "NewName"


class TestTransform:
    def test_set_position(self, sample_project):
        data, _, _ = sample_project
        camera = find_object_by_name(data, "Camera")
        set_transform(data, camera["id"], position=[5, 10, 15])
        assert camera["transform"]["position"] == {"x": 5, "y": 10, "z": 15}

    def test_set_rotation_and_scale(self, sample_project):
        data, _, _ = sample_project
        camera = find_object_by_name(data, "Camera")
        set_transform(data, camera["id"], rotation=[0, 45, 0], scale=[2, 2, 2])
        assert camera["transform"]["rotation"] == {"x": 0, "y": 45, "z": 0}
        assert camera["transform"]["scale"] == {"x": 2, "y": 2, "z": 2}


class TestEnable:
    def test_disable_object(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Toggle")
        set_enabled(data, obj["id"], False)
        assert obj["enabled"] is False

    def test_enable_object(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Toggle2")
        set_enabled(data, obj["id"], False)
        set_enabled(data, obj["id"], True)
        assert obj["enabled"] is True


class TestReparent:
    def test_reparent(self, sample_project):
        data, _, _ = sample_project
        a = add_object(data, "A")
        b = add_object(data, "B")
        reparent(data, b["id"], a["id"])
        assert b["parentId"] == a["id"]

    def test_circular_reparent_raises(self, sample_project):
        data, _, _ = sample_project
        a = add_object(data, "Parent")
        b = add_object(data, "Child", parent_id=a["id"])
        with pytest.raises(ValueError, match="Cannot reparent to a descendant"):
            reparent(data, a["id"], b["id"])


class TestDuplicate:
    def test_duplicate(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Original")
        before = len(data["sceneObjects"])
        clone = duplicate_object(data, obj["id"])
        assert clone["name"] == "Original (Copy)"
        assert clone["id"] != obj["id"]
        assert len(data["sceneObjects"]) == before + 1


class TestFlatten:
    def test_flatten_scene(self, sample_project):
        data, _, _ = sample_project
        items = flatten_scene(data)
        assert len(items) >= 2  # Camera + Ortho Camera
        names = [i["name"] for i in items]
        assert "Camera" in names


class TestSceneToTree:
    def test_tree_structure(self, sample_project):
        data, _, _ = sample_project
        trees = scene_to_tree(data)
        assert len(trees) >= 2
        names = [t["name"] for t in trees]
        assert "Camera" in names
