"""Tests for material operations (flat sceneObjects format)."""

import pytest

from cli_anything.lens_studio.core.material import (
    assign_material,
    create_material,
    get_material,
    get_material_by_name,
    list_materials,
    remove_material,
    update_material,
)
from cli_anything.lens_studio.core.scene import add_object
from cli_anything.lens_studio.core.component import add_component


class TestCreateMaterial:
    def test_create_default(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "TestMat")
        assert mat["name"] == "TestMat"
        assert mat["type"] == "Default"
        assert mat["id"] is not None

    def test_create_pbr(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "PBRMat", material_type="PBR")
        assert mat["type"] == "PBR"
        assert "metallic" in mat["properties"]
        assert "roughness" in mat["properties"]

    def test_create_with_custom_props(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "Custom", properties={"baseColor": [1, 0, 0, 1]})
        assert mat["properties"]["baseColor"] == [1, 0, 0, 1]

    def test_invalid_type_raises(self, sample_project):
        data, _, _ = sample_project
        with pytest.raises(ValueError, match="Unknown material type"):
            create_material(data, "Bad", material_type="Nonexistent")


class TestListMaterials:
    def test_list_empty(self, sample_project):
        data, _, _ = sample_project
        assert list_materials(data) == []

    def test_list_with_filter(self, sample_project):
        data, _, _ = sample_project
        create_material(data, "A", "PBR")
        create_material(data, "B", "Unlit")
        assert len(list_materials(data, "PBR")) == 1
        assert len(list_materials(data)) == 2


class TestGetMaterial:
    def test_get_by_id(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "Find")
        found = get_material(data, mat["id"])
        assert found["name"] == "Find"

    def test_get_by_name(self, sample_project):
        data, _, _ = sample_project
        create_material(data, "ByName")
        found = get_material_by_name(data, "ByName")
        assert found is not None


class TestUpdateMaterial:
    def test_update_name(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "Old")
        updated = update_material(data, mat["id"], {"name": "New"})
        assert updated["name"] == "New"

    def test_update_properties(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "PBR", "PBR")
        updated = update_material(data, mat["id"], {"properties": {"metallic": 1.0}})
        assert updated["properties"]["metallic"] == 1.0


class TestRemoveMaterial:
    def test_remove(self, sample_project):
        data, _, _ = sample_project
        mat = create_material(data, "ToRemove")
        remove_material(data, mat["id"])
        assert len(data["materials"]) == 0

    def test_remove_nonexistent_raises(self, sample_project):
        data, _, _ = sample_project
        with pytest.raises(ValueError):
            remove_material(data, "bad-id")


class TestAssignMaterial:
    def test_assign_to_mesh_visual(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "MeshObj")
        add_component(data, obj["id"], "MeshVisual")
        mat = create_material(data, "Assigned")

        result = assign_material(data, obj["id"], mat["id"])
        assert result["properties"]["materialId"] == mat["id"]

    def test_assign_no_visual_raises(self, sample_project):
        data, _, _ = sample_project
        obj = add_object(data, "EmptyObj")
        mat = create_material(data, "NoTarget")

        with pytest.raises(ValueError, match="no visual component"):
            assign_material(data, obj["id"], mat["id"])
