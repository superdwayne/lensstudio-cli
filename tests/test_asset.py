"""Tests for asset management."""

import os
from pathlib import Path

import pytest

from cli_anything.lens_studio.core.asset import (
    detect_asset_type,
    get_asset,
    get_asset_by_name,
    import_asset,
    list_assets,
    remove_asset,
    update_asset,
)
from cli_anything.lens_studio.core.project import save_project


class TestDetectAssetType:
    def test_texture_types(self):
        assert detect_asset_type("photo.png") == "texture"
        assert detect_asset_type("photo.jpg") == "texture"
        assert detect_asset_type("photo.jpeg") == "texture"

    def test_mesh_types(self):
        assert detect_asset_type("model.fbx") == "mesh"
        assert detect_asset_type("model.glb") == "mesh"
        assert detect_asset_type("model.gltf") == "mesh"

    def test_audio_types(self):
        assert detect_asset_type("sound.mp3") == "audio"
        assert detect_asset_type("sound.wav") == "audio"

    def test_script_types(self):
        assert detect_asset_type("main.js") == "script"
        assert detect_asset_type("main.ts") == "script"

    def test_unknown_type(self):
        assert detect_asset_type("data.xyz") == "unknown"


class TestImportAsset:
    def test_import_texture(self, sample_project, sample_texture):
        data, path, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture)
        assert result["type"] == "texture"
        assert result["name"] == "test_texture"
        assert result["id"] is not None
        assert "textureSettings" in result

        # File was copied
        dest = Path(project_dir) / result["relativePath"]
        assert dest.exists()

    def test_import_with_custom_name(self, sample_project, sample_texture):
        data, path, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture, name="MyTexture")
        assert result["name"] == "MyTexture"

    def test_import_nonexistent_file(self, sample_project):
        data, path, project_dir = sample_project
        with pytest.raises(FileNotFoundError):
            import_asset(data, project_dir, "/nonexistent/file.png")

    def test_import_registers_in_project(self, sample_project, sample_texture):
        data, path, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture)
        assert len(data["assets"]) == 1
        assert data["assets"][0]["id"] == result["id"]


class TestListAssets:
    def test_list_empty(self, sample_project):
        data, _, _ = sample_project
        assets = list_assets(data)
        assert assets == []

    def test_list_with_filter(self, sample_project, sample_texture):
        data, _, project_dir = sample_project
        import_asset(data, project_dir, sample_texture)
        assert len(list_assets(data, "texture")) == 1
        assert len(list_assets(data, "mesh")) == 0


class TestGetAsset:
    def test_get_by_id(self, sample_project, sample_texture):
        data, _, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture)
        asset = get_asset(data, result["id"])
        assert asset is not None
        assert asset["name"] == "test_texture"

    def test_get_by_name(self, sample_project, sample_texture):
        data, _, project_dir = sample_project
        import_asset(data, project_dir, sample_texture)
        asset = get_asset_by_name(data, "test_texture")
        assert asset is not None


class TestRemoveAsset:
    def test_remove_asset(self, sample_project, sample_texture):
        data, _, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture)
        dest = Path(project_dir) / result["relativePath"]
        assert dest.exists()

        remove_asset(data, project_dir, result["id"])
        assert len(data["assets"]) == 0
        assert not dest.exists()

    def test_remove_keep_file(self, sample_project, sample_texture):
        data, _, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture)
        dest = Path(project_dir) / result["relativePath"]

        remove_asset(data, project_dir, result["id"], delete_file=False)
        assert len(data["assets"]) == 0
        assert dest.exists()


class TestUpdateAsset:
    def test_update_name(self, sample_project, sample_texture):
        data, _, project_dir = sample_project
        result = import_asset(data, project_dir, sample_texture)
        updated = update_asset(data, result["id"], {"name": "Renamed"})
        assert updated["name"] == "Renamed"
