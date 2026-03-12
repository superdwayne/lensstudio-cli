"""Project management for Lens Studio CLI.

Handles creation, loading, inspection, and manipulation of .lsproj project files.
Matches the real Lens Studio file format so projects open natively in the app.
"""

import json
import os
import shutil
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.config import (
    PROJECT_EXT,
    TEMPLATES,
    ensure_dir,
    get_projects_dir,
)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _vec3(x=0, y=0, z=0) -> Dict[str, float]:
    """Create a Lens Studio {x, y, z} vector."""
    return {"x": x, "y": y, "z": z}


def _default_transform() -> Dict[str, Dict]:
    return {
        "position": _vec3(),
        "rotation": _vec3(),
        "scale": _vec3(1, 1, 1),
    }


def _make_component(comp_type: str, properties: Optional[Dict] = None) -> Dict:
    """Create a component entry matching real LS format."""
    return {
        "type": comp_type,
        "id": _new_uuid(),
        "properties": properties or {},
    }


def _make_scene_object(
    name: str,
    components: Optional[List[Dict]] = None,
    parent_id: Optional[str] = None,
    transform: Optional[Dict] = None,
) -> Dict:
    """Create a SceneObject matching real LS format."""
    return {
        "id": _new_uuid(),
        "name": name,
        "enabled": True,
        "parentId": parent_id,
        "transform": transform or _default_transform(),
        "components": components or [],
    }


# ---------------------------------------------------------------------------
# Project file schema — matches real Lens Studio .lsproj format
# ---------------------------------------------------------------------------

def blank_project(name: str, template: str = "blank") -> Dict[str, Any]:
    """Generate a Lens Studio project in the real .lsproj format."""
    scene_objects = _template_scene_objects(template)

    return {
        "id": _new_uuid(),
        "name": name,
        "version": "5.0",
        "sceneObjects": scene_objects,
        "resources": [],
        "settings": {
            "targetDevice": "mobile",
            "orientation": "portrait",
        },
    }


def _template_scene_objects(template: str) -> List[Dict]:
    """Build the initial sceneObjects list based on template."""
    objects = []

    # Every project gets a perspective camera
    objects.append(_make_scene_object("Camera", [
        _make_component("Camera", {
            "cameraType": "Perspective",
            "fov": 60,
            "near": 1,
            "far": 1000,
            "renderOrder": 0,
            "deviceCameraTexture": True,
        }),
    ]))

    # Orthographic camera for 2D overlays
    objects.append(_make_scene_object("Orthographic Camera", [
        _make_component("Camera", {
            "cameraType": "Orthographic",
            "renderOrder": 1,
        }),
    ]))

    if template == "face-effects":
        objects.append(_make_scene_object("Face Effects", [
            _make_component("Head", {"attachmentPoint": "center"}),
            _make_component("FaceMask", {"texture": None}),
        ]))
    elif template == "world-ar":
        objects.append(_make_scene_object("Device Tracking", [
            _make_component("DeviceTracking", {"trackingMode": "world"}),
        ]))
    elif template == "hand-tracking":
        objects.append(_make_scene_object("Hand Tracking", [
            _make_component("HandTracking", {"hand": "right"}),
            _make_component("MeshVisual", {"mesh": "handMesh"}),
        ]))
    elif template == "body-tracking":
        objects.append(_make_scene_object("Body Tracking", [
            _make_component("BodyTracking", {}),
        ]))
    elif template == "marker-tracking":
        objects.append(_make_scene_object("Marker Tracker", [
            _make_component("MarkerTracking", {"markerAsset": None}),
        ]))
    elif template == "segmentation":
        objects.append(_make_scene_object("Segmentation", [
            _make_component("SegmentationTextureProvider", {"segmentationType": "background"}),
            _make_component("Image", {"texture": None}),
        ]))

    return objects


# ---------------------------------------------------------------------------
# CRUD operations
# ---------------------------------------------------------------------------

def create_project(
    name: str,
    directory: Optional[str] = None,
    template: str = "blank",
) -> Dict[str, Any]:
    """Create a new Lens Studio project."""
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Available: {', '.join(TEMPLATES)}")

    base_dir = Path(directory) if directory else get_projects_dir()
    project_dir = ensure_dir(base_dir / name)
    project_file = project_dir / f"{name}{PROJECT_EXT}"

    if project_file.exists():
        raise FileExistsError(f"Project already exists: {project_file}")

    data = blank_project(name, template)

    # Real LS projects use a Public/ subdirectory for assets
    ensure_dir(project_dir / "Public")

    # Write project file
    with open(project_file, "w") as f:
        json.dump(data, f, indent=2)

    return {
        "name": name,
        "path": str(project_file),
        "directory": str(project_dir),
        "template": template,
        "id": data["id"],
    }


def load_project(path: str) -> Dict[str, Any]:
    """Load a project from a .lsproj file."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Project file not found: {path}")
    if p.suffix != PROJECT_EXT:
        raise ValueError(f"Not a Lens Studio project file: {path}")

    with open(p, "r") as f:
        return json.load(f)


def save_project(path: str, data: Dict[str, Any]):
    """Save project data to a .lsproj file."""
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def project_info(path: str) -> Dict[str, Any]:
    """Get summary info about a project."""
    data = load_project(path)
    scene_objects = data.get("sceneObjects", [])
    resources = data.get("resources", [])
    settings = data.get("settings", {})

    return {
        "name": data.get("name", "unknown"),
        "id": data.get("id", "unknown"),
        "version": data.get("version", "unknown"),
        "sceneObjects": len(scene_objects),
        "resources": len(resources),
        "targetDevice": settings.get("targetDevice", "mobile"),
        "orientation": settings.get("orientation", "portrait"),
    }


def list_projects(directory: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all projects in a directory."""
    base_dir = Path(directory) if directory else get_projects_dir()
    if not base_dir.exists():
        return []

    projects = []
    for item in sorted(base_dir.iterdir()):
        if item.is_dir():
            proj_file = item / f"{item.name}{PROJECT_EXT}"
            if proj_file.exists():
                try:
                    info = project_info(str(proj_file))
                    info["path"] = str(proj_file)
                    projects.append(info)
                except Exception:
                    projects.append({"name": item.name, "path": str(proj_file), "error": True})
    return projects


def delete_project(path: str, force: bool = False) -> bool:
    """Delete a project directory."""
    p = Path(path)
    if p.is_file():
        project_dir = p.parent
    else:
        project_dir = p

    if not project_dir.exists():
        raise FileNotFoundError(f"Project not found: {path}")

    shutil.rmtree(project_dir)
    return True
