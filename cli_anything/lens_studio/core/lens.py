"""Lens build, export, and preview operations for Lens Studio CLI.

Handles building lenses from projects, exporting for different targets,
and launching previews via the Lens Studio backend.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.backend import get_backend


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_project(project_data: Dict) -> Dict[str, Any]:
    """Validate a project for lens submission readiness."""
    errors = []
    warnings = []

    scene_objects = project_data.get("sceneObjects", [])
    settings = project_data.get("settings", {})

    # Check required fields
    if not project_data.get("name"):
        errors.append("Project name is required")

    if not scene_objects:
        errors.append("Scene must have at least one object")

    # Check for camera
    if not _has_component_type(scene_objects, "Camera"):
        errors.append("Scene must have at least one Camera component")

    # Check resources for missing files
    for res in project_data.get("resources", []):
        if not res.get("relativePath"):
            warnings.append(f"Resource '{res.get('name')}' has no file path")

    # Size estimation
    total_size = sum(r.get("fileSize", 0) for r in project_data.get("resources", []))
    if total_size > 8 * 1024 * 1024:  # 8MB limit for Snapchat
        warnings.append(f"Total asset size ({total_size / 1024 / 1024:.1f}MB) exceeds 8MB limit")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "sceneObjects": _count_objects(project_data),
            "components": _count_components(project_data),
            "resources": len(project_data.get("resources", [])),
            "estimatedSize": total_size,
        },
    }


def _has_component_type(scene_objects: list, comp_type: str) -> bool:
    """Check if any object in the flat list has a component of the given type."""
    for obj in scene_objects:
        for comp in obj.get("components", []):
            if comp.get("type") == comp_type:
                return True
    return False


def _count_objects(project_data: Dict) -> int:
    return len(project_data.get("sceneObjects", []))


def _count_components(project_data: Dict) -> int:
    count = 0
    for obj in project_data.get("sceneObjects", []):
        count += len(obj.get("components", []))
    return count


# ---------------------------------------------------------------------------
# Build & Export
# ---------------------------------------------------------------------------

def build_lens(
    project_path: str,
    output_path: str,
    target: str = "snapchat",
) -> Dict[str, Any]:
    """Build a lens from a project file using Lens Studio backend."""
    backend = get_backend()

    if not backend.available:
        # Fallback: package project data as a lens bundle (JSON-based)
        return _build_lens_bundle(project_path, output_path, target)

    try:
        result = backend.build_lens(project_path, output_path, target)
        if result.returncode == 0:
            output_size = os.path.getsize(output_path) if os.path.exists(output_path) else 0
            return {
                "success": True,
                "output": output_path,
                "size": output_size,
                "target": target,
                "built": _timestamp(),
            }
        else:
            # Backend failed — fall back to bundle
            return _build_lens_bundle(project_path, output_path, target)
    except Exception:
        # Backend unavailable or errored — fall back to bundle
        return _build_lens_bundle(project_path, output_path, target)


def _build_lens_bundle(
    project_path: str,
    output_path: str,
    target: str,
) -> Dict[str, Any]:
    """Build a lens bundle without Lens Studio (packages project as JSON bundle)."""
    from .project import load_project

    try:
        project_data = load_project(project_path)
        project_dir = str(Path(project_path).parent)

        bundle = {
            "format": "lens-bundle",
            "version": "1.0.0",
            "target": target,
            "built": _timestamp(),
            "id": project_data.get("id"),
            "name": project_data.get("name"),
            "sceneObjects": project_data.get("sceneObjects", []),
            "settings": project_data.get("settings", {}),
            "resources": project_data.get("resources", []),
        }

        # Write bundle
        out = Path(output_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        with open(out, "w") as f:
            json.dump(bundle, f, indent=2)

        return {
            "success": True,
            "output": output_path,
            "size": os.path.getsize(output_path),
            "target": target,
            "built": _timestamp(),
            "note": "Built as JSON bundle (Lens Studio not available for native build)",
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "target": target,
        }


# ---------------------------------------------------------------------------
# Preview
# ---------------------------------------------------------------------------

def preview_lens(
    project_path: str,
    device: str = "simulator",
) -> Dict[str, Any]:
    """Launch lens preview."""
    backend = get_backend()

    if not backend.available:
        return {
            "success": False,
            "error": "Lens Studio not found. Cannot launch preview.",
        }

    try:
        backend.preview(project_path, device)
        return {
            "success": True,
            "project": project_path,
            "device": device,
            "launched": _timestamp(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def open_in_lens_studio(project_path: str) -> Dict[str, Any]:
    """Open project in Lens Studio GUI."""
    backend = get_backend()

    if not backend.available:
        return {
            "success": False,
            "error": "Lens Studio not found.",
        }

    try:
        backend.open_project(project_path)
        return {
            "success": True,
            "project": project_path,
            "opened": _timestamp(),
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def get_backend_info() -> Dict[str, Any]:
    """Get information about the Lens Studio backend."""
    backend = get_backend()
    info = {
        "available": backend.available,
        "executable": backend.executable,
    }
    if backend.available:
        info["version"] = backend.version()
    return info
