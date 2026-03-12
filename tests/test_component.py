"""Tests for component management (flat sceneObjects format)."""

import pytest

from cli_anything.lens_studio.core.component import (
    add_component,
    configure_component,
    list_component_types,
    list_components,
    remove_component,
)
from cli_anything.lens_studio.core.scene import add_object, find_object_by_name


class TestAddComponent:
    def test_add_mesh_visual(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "MeshObj")
        comp = add_component(data, obj["id"], "MeshVisual")
        assert comp["type"] == "MeshVisual"
        assert "id" in comp
        assert "properties" in comp

    def test_add_with_properties(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "TextObj")
        comp = add_component(data, obj["id"], "Text", {"text": "Hello", "size": 64})
        assert comp["properties"]["text"] == "Hello"
        assert comp["properties"]["size"] == 64

    def test_invalid_type_raises(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Bad")
        with pytest.raises(ValueError, match="Unknown component type"):
            add_component(data, obj["id"], "FakeComponent")

    def test_duplicate_singleton_raises(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "DupeCam")
        add_component(data, obj["id"], "Camera")
        with pytest.raises(ValueError, match="only one allowed"):
            add_component(data, obj["id"], "Camera")


class TestRemoveComponent:
    def test_remove(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Removable")
        add_component(data, obj["id"], "MeshVisual")
        remove_component(data, obj["id"], "MeshVisual")
        comps = [c for c in obj["components"] if c["type"] == "MeshVisual"]
        assert len(comps) == 0

    def test_remove_nonexistent_raises(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Empty")
        with pytest.raises(ValueError, match="No MeshVisual component"):
            remove_component(data, obj["id"], "MeshVisual")


class TestListComponents:
    def test_list(self, sample_project):
        data, _, _ = sample_project
        camera = find_object_by_name(data, "Camera")
        comps = list_components(data, camera["id"])
        assert len(comps) >= 1
        assert comps[0]["type"] == "Camera"


class TestConfigureComponent:
    def test_configure(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "Configurable")
        add_component(data, obj["id"], "Text")
        result = configure_component(data, obj["id"], "Text", {"text": "Updated", "size": 72})
        assert result["properties"]["text"] == "Updated"
        assert result["properties"]["size"] == 72


class TestListComponentTypes:
    def test_returns_types(self):
        types = list_component_types()
        assert len(types) > 20
        type_names = [t["type"] for t in types]
        assert "Camera" in type_names
        assert "MeshVisual" in type_names
        assert "ScriptComponent" in type_names
