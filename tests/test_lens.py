"""Tests for lens build, validate, and export."""

import json
import os
from pathlib import Path

import pytest

from cli_anything.lens_studio.core.lens import (
    validate_project,
    _build_lens_bundle,
    _count_components,
    _count_objects,
    _has_component_type,
    get_backend_info,
)


class TestValidateProject:
    def test_valid_blank_project(self, sample_project):
        data, _, _ = sample_project
        result = validate_project(data)
        assert result["valid"] is True
        assert result["errors"] == []

    def test_missing_name(self, sample_project):
        data, _, _ = sample_project
        data["name"] = ""
        result = validate_project(data)
        assert result["valid"] is False
        assert any("name" in e.lower() for e in result["errors"])

    def test_missing_camera(self, sample_project):
        data, _, _ = sample_project
        data["sceneObjects"] = []
        result = validate_project(data)
        assert any("Camera" in e for e in result["errors"])

    def test_stats_included(self, sample_project):
        data, _, _ = sample_project
        result = validate_project(data)
        stats = result["stats"]
        assert "sceneObjects" in stats
        assert "resources" in stats


class TestBuildLensBundle:
    def test_build_bundle(self, sample_project, tmp_dir):
        _, path, _ = sample_project
        output = os.path.join(tmp_dir, "output.lens")
        result = _build_lens_bundle(path, output, "snapchat")
        assert result["success"] is True
        assert os.path.exists(output)

        with open(output) as f:
            bundle = json.load(f)
        assert bundle["format"] == "lens-bundle"
        assert bundle["target"] == "snapchat"


class TestHasComponentType:
    def test_finds_camera(self, sample_project):
        data, _, _ = sample_project
        assert _has_component_type(data["sceneObjects"], "Camera") is True

    def test_missing_type(self, sample_project):
        data, _, _ = sample_project
        assert _has_component_type(data["sceneObjects"], "HandTracking") is False


class TestCounting:
    def test_count_objects(self, sample_project):
        data, _, _ = sample_project
        count = _count_objects(data)
        assert count >= 2  # Camera + Ortho Camera

    def test_count_components(self, sample_project):
        data, _, _ = sample_project
        count = _count_components(data)
        assert count >= 1  # at least the Camera component


class TestBackendInfo:
    def test_backend_info(self):
        info = get_backend_info()
        assert "available" in info
        assert "executable" in info
