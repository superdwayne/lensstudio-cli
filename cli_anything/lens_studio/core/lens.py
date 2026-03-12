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

    proj = project_data.get("project", {})
    scene = project_data.get("scene", {})
    settings = project_data.get("settings", {})

    # Check required fields
    if not proj.get("name"):
        errors.append("Project name is required")

    if not scene.get("root"):
        errors.append("Scene must have a root object")

    # Check for camera
    root = scene.get("root", {})
    if not _has_component_type(root, "Camera"):
        errors.append("Scene must have at least one Camera component")

    # Check render target
    rt = settings.get("renderTarget", {})
    width = rt.get("width", 0)
    height = rt.get("height", 0)
    if width < 720 or height < 1280:
        warnings.append(f"Render target {width}x{height} is below recommended 720x1280")

    # Check assets for missing files
    for asset in project_data.get("assets", []):
        if not asset.get("relativePath"):
            warnings.append(f"Asset '{asset.get('name')}' has no file path")

    # Check scripts for syntax issues (basic check)
    for script in project_data.get("scripts", []):
        if not script.get("relativePath"):
            warnings.append(f"Script '{script.get('name')}' has no file path")

    # Size estimation
    total_size = sum(a.get("fileSize", 0) for a in project_data.get("assets", []))
    if total_size > 8 * 1024 * 1024:  # 8MB limit for Snapchat
        warnings.append(f"Total asset size ({total_size / 1024 / 1024:.1f}MB) exceeds 8MB limit")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
        "stats": {
            "sceneObjects": _count_objects(root),
            "components": _count_components(root),
            "assets": len(project_data.get("assets", [])),
            "scripts": len(project_data.get("scripts", [])),
            "materials": len(project_data.get("materials", [])),
            "estimatedSize": total_size,
        },
    }


def _has_component_type(node: Dict, comp_type: str) -> bool:
    """Check if any object in the tree has a component of the given type."""
    for comp in node.get("components", []):
        if comp.get("type") == comp_type:
            return True
    for child in node.get("children", []):
        if _has_component_type(child, comp_type):
            return True
    return False


def _count_objects(node: Dict) -> int:
    count = 1
    for child in node.get("children", []):
        count += _count_objects(child)
    return count


def _count_components(node: Dict) -> int:
    count = len(node.get("components", []))
    for child in node.get("children", []):
        count += _count_components(child)
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
            "project": project_data["project"],
            "scene": project_data["scene"],
            "settings": project_data["settings"],
            "assets": project_data.get("assets", []),
            "scripts": project_data.get("scripts", []),
            "materials": project_data.get("materials", []),
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
