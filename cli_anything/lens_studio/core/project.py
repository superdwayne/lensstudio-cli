"""Project management for Lens Studio CLI.

Handles creation, loading, inspection, and manipulation of .lsproj project files.
Lens Studio projects are JSON-based with a scene graph, asset references, and metadata.
"""

import json
import os
import shutil
import time
import uuid
from datetime import datetime
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


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Project file schema helpers
# ---------------------------------------------------------------------------

def blank_project(name: str, template: str = "blank") -> Dict[str, Any]:
    """Generate a blank Lens Studio project structure."""
    project_id = _new_uuid()
    now = _timestamp()

    scene = _template_scene(template)

    return {
        "meta": {
            "version": "5.4.0",
            "format": "lsproj",
            "generator": "cli-anything-lens-studio",
        },
        "project": {
            "id": project_id,
            "name": name,
            "description": "",
            "template": template,
            "created": now,
            "modified": now,
            "lensStudioVersion": "5.4.0",
        },
        "settings": {
            "targetPlatform": "snapchat",
            "renderTarget": {
                "width": 1080,
                "height": 1920,
            },
            "physics": {"enabled": False},
            "touchInput": {"enabled": True},
        },
        "scene": scene,
        "assets": [],
        "scripts": [],
        "materials": [],
        "resources": [],
    }


def _template_scene(template: str) -> Dict[str, Any]:
    """Build the initial scene graph based on template."""
    root_id = _new_uuid()
    camera_id = _new_uuid()

    base_scene = {
        "root": {
            "id": root_id,
            "name": "Scene",
            "type": "SceneObject",
            "enabled": True,
            "children": [
                {
                    "id": camera_id,
                    "name": "Camera",
                    "type": "SceneObject",
                    "enabled": True,
                    "components": [
                        {"type": "Camera", "renderOrder": 0},
                    ],
                    "transform": {
                        "position": [0, 0, 0],
                        "rotation": [0, 0, 0],
                        "scale": [1, 1, 1],
                    },
                    "children": [],
                }
            ],
        }
    }

    if template == "face-effects":
        face_id = _new_uuid()
        base_scene["root"]["children"].append({
            "id": face_id,
            "name": "Face Effects",
            "type": "SceneObject",
            "enabled": True,
            "components": [
                {"type": "Head", "attachmentPoint": "center"},
                {"type": "FaceMask", "texture": None},
            ],
            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [],
        })
    elif template == "world-ar":
        tracker_id = _new_uuid()
        base_scene["root"]["children"].append({
            "id": tracker_id,
            "name": "Device Tracking",
            "type": "SceneObject",
            "enabled": True,
            "components": [
                {"type": "DeviceTracking", "trackingMode": "world"},
            ],
            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [],
        })
    elif template == "hand-tracking":
        hand_id = _new_uuid()
        base_scene["root"]["children"].append({
            "id": hand_id,
            "name": "Hand Tracking",
            "type": "SceneObject",
            "enabled": True,
            "components": [
                {"type": "HandTracking", "hand": "right"},
                {"type": "MeshVisual", "mesh": "handMesh"},
            ],
            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [],
        })
    elif template == "body-tracking":
        body_id = _new_uuid()
        base_scene["root"]["children"].append({
            "id": body_id,
            "name": "Body Tracking",
            "type": "SceneObject",
            "enabled": True,
            "components": [
                {"type": "BodyTracking"},
            ],
            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [],
        })
    elif template == "marker-tracking":
        marker_id = _new_uuid()
        base_scene["root"]["children"].append({
            "id": marker_id,
            "name": "Marker Tracker",
            "type": "SceneObject",
            "enabled": True,
            "components": [
                {"type": "MarkerTracking", "markerAsset": None},
            ],
            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [],
        })
    elif template == "segmentation":
        seg_id = _new_uuid()
        base_scene["root"]["children"].append({
            "id": seg_id,
            "name": "Segmentation",
            "type": "SceneObject",
            "enabled": True,
            "components": [
                {"type": "SegmentationTextureProvider", "segmentationType": "background"},
                {"type": "Image", "texture": None},
            ],
            "transform": {"position": [0, 0, 0], "rotation": [0, 0, 0], "scale": [1, 1, 1]},
            "children": [],
        })

    return base_scene


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

    # Create standard subdirectories
    for sub in ["Scripts", "Textures", "Materials", "Meshes", "Audio", "Prefabs"]:
        ensure_dir(project_dir / sub)

    # Write project file
    with open(project_file, "w") as f:
        json.dump(data, f, indent=2)

    return {
        "name": name,
        "path": str(project_file),
        "directory": str(project_dir),
        "template": template,
        "id": data["project"]["id"],
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
    data["project"]["modified"] = _timestamp()
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def project_info(path: str) -> Dict[str, Any]:
    """Get summary info about a project."""
    data = load_project(path)
    proj = data["project"]
    scene_root = data.get("scene", {}).get("root", {})

    def count_objects(node):
        c = 1
        for child in node.get("children", []):
            c += count_objects(child)
        return c

    obj_count = count_objects(scene_root) if scene_root else 0

    return {
        "name": proj["name"],
        "id": proj["id"],
        "template": proj.get("template", "unknown"),
        "created": proj["created"],
        "modified": proj["modified"],
        "lensStudioVersion": proj.get("lensStudioVersion", "unknown"),
        "sceneObjects": obj_count,
        "assets": len(data.get("assets", [])),
        "scripts": len(data.get("scripts", [])),
        "materials": len(data.get("materials", [])),
        "targetPlatform": data.get("settings", {}).get("targetPlatform", "snapchat"),
        "resolution": data.get("settings", {}).get("renderTarget", {}),
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
