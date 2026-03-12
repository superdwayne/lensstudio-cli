"""Tests for scene graph operations."""

import pytest

from cli_anything.lens_studio.core.scene import (
    add_object,
    duplicate_object,
    find_object,
    find_object_by_name,
    find_parent,
    flatten_scene,
    remove_object,
    rename_object,
    reparent,
    scene_to_tree,
    set_enabled,
    set_transform,
)


@pytest.fixture
def scene_root(sample_project):
    data, _, _ = sample_project
    return data["scene"]["root"]


class TestFindObject:
    def test_find_root(self, scene_root):
        result = find_object(scene_root, scene_root["id"])
        assert result is scene_root

    def test_find_camera(self, scene_root):
        camera = find_object_by_name(scene_root, "Camera")
        assert camera is not None
        assert camera["name"] == "Camera"

    def test_find_nonexistent(self, scene_root):
        result = find_object(scene_root, "nonexistent-id")
        assert result is None


class TestAddObject:
    def test_add_to_root(self, scene_root):
        obj = add_object(scene_root, "NewObject")
        assert obj["name"] == "NewObject"
        assert obj["id"] is not None
        assert obj in scene_root["children"]

    def test_add_to_parent(self, scene_root):
        camera = find_object_by_name(scene_root, "Camera")
        child = add_object(scene_root, "CameraChild", parent_id=camera["id"])
        assert child in camera["children"]

    def test_add_with_transform(self, scene_root):
        transform = {"position": [1, 2, 3], "rotation": [0, 90, 0], "scale": [2, 2, 2]}
        obj = add_object(scene_root, "Positioned", transform=transform)
        assert obj["transform"]["position"] == [1, 2, 3]

    def test_add_to_nonexistent_parent(self, scene_root):
        with pytest.raises(ValueError, match="Parent object not found"):
            add_object(scene_root, "Orphan", parent_id="bad-id")


class TestRemoveObject:
    def test_remove_object(self, scene_root):
        obj = add_object(scene_root, "ToRemove")
        remove_object(scene_root, obj["id"])
        assert find_object(scene_root, obj["id"]) is None

    def test_cannot_remove_root(self, scene_root):
        with pytest.raises(ValueError, match="Cannot remove the root"):
            remove_object(scene_root, scene_root["id"])


class TestRename:
    def test_rename_object(self, scene_root):
        obj = add_object(scene_root, "OldName")
        rename_object(scene_root, obj["id"], "NewName")
        assert obj["name"] == "NewName"


class TestTransform:
    def test_set_position(self, scene_root):
        camera = find_object_by_name(scene_root, "Camera")
        set_transform(scene_root, camera["id"], position=[5, 10, 15])
        assert camera["transform"]["position"] == [5, 10, 15]

    def test_set_rotation_and_scale(self, scene_root):
        camera = find_object_by_name(scene_root, "Camera")
        set_transform(scene_root, camera["id"], rotation=[0, 45, 0], scale=[2, 2, 2])
        assert camera["transform"]["rotation"] == [0, 45, 0]
        assert camera["transform"]["scale"] == [2, 2, 2]


class TestEnable:
    def test_disable_object(self, scene_root):
        obj = add_object(scene_root, "Toggle")
        set_enabled(scene_root, obj["id"], False)
        assert obj["enabled"] is False

    def test_enable_object(self, scene_root):
        obj = add_object(scene_root, "Toggle2")
        set_enabled(scene_root, obj["id"], False)
        set_enabled(scene_root, obj["id"], True)
        assert obj["enabled"] is True


class TestReparent:
    def test_reparent(self, scene_root):
        a = add_object(scene_root, "A")
        b = add_object(scene_root, "B")
        reparent(scene_root, b["id"], a["id"])
        assert b in a["children"]
        assert b not in scene_root["children"]

    def test_circular_reparent_raises(self, scene_root):
        a = add_object(scene_root, "Parent")
        b = add_object(scene_root, "Child", parent_id=a["id"])
        with pytest.raises(ValueError, match="Cannot reparent to a descendant"):
            reparent(scene_root, a["id"], b["id"])


class TestDuplicate:
    def test_duplicate(self, scene_root):
        obj = add_object(scene_root, "Original")
        clone = duplicate_object(scene_root, obj["id"])
        assert clone["name"] == "Original (Copy)"
        assert clone["id"] != obj["id"]


class TestFlatten:
    def test_flatten_scene(self, scene_root):
        items = flatten_scene(scene_root)
        assert len(items) >= 2  # root + camera at minimum
        assert items[0]["name"] == "Scene"


class TestSceneToTree:
    def test_tree_structure(self, scene_root):
        tree = scene_to_tree(scene_root)
        assert tree["name"] == "Scene"
        assert "children" in tree
