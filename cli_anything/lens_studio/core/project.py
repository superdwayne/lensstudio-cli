"""Project management for Lens Studio CLI.

Handles creation, loading, inspection, and manipulation of .esproj project files.
Uses the real Lens Studio 5.x YAML format so projects open natively in the app.
"""

import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

from ..utils.config import (
    LS_TEMPLATE_DIR,
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
    obj = {
        "id": _new_uuid(),
        "name": name,
        "enabled": True,
        "transform": transform or _default_transform(),
        "components": components or [],
    }
    if parent_id:
        obj["parentId"] = parent_id
    return obj


# ---------------------------------------------------------------------------
# .esproj YAML helpers
# ---------------------------------------------------------------------------

def _blank_esproj(name: str) -> Dict[str, Any]:
    """Generate the .esproj YAML content matching LS 5.x format."""
    return {
        "studioVersion": {
            "major": 5,
            "minor": 18,
            "patch": 0,
            "build": 26021107,
            "type": "Public",
        },
        "coreVersion": 348,
        "clientVersion": 13.78,
        "updateCheckpoint": 87,
        "sceneId": _new_uuid(),
        "metaInfo": {
            "hints": [],
            "tags": [],
            "lensName": name,
            "lensDescriptors": [],
            "lensApplicableContext": ["live_camera", "reply_camera", "video_chat"],
            "lensApplicability": ["Front", "Back"],
            "lensClientCompatibilities": ["Mobile", "Web"],
            "platformBundlesEnabled": False,
            "iconHash": "",
            "videoPreviewHash": "",
            "fromTemplateName": "Empty Project",
            "fromTemplateUrl": "Lens Studio 5.18.0.26021107",
            "activationCamera": "Front",
            "sourceMapEnabled": False,
            "shaderCacheInvalidationEnabled": False,
            "usingMinClientVersions": False,
            "androidMinClientVersion": {"major": 0, "minor": 0, "patch": 0, "build": 0},
            "iOSMinClientVersion": {"major": 0, "minor": 0, "patch": 0, "build": 0},
            "documentId": _new_uuid(),
            "originalDocumentId": _new_uuid(),
            "packageId": "",
            "packageVersion": "",
            "gluboEnabled": False,
        },
    }


# ---------------------------------------------------------------------------
# Internal scene data (stored as companion .scene.json alongside .esproj)
# ---------------------------------------------------------------------------

def blank_project(name: str, template: str = "blank") -> Dict[str, Any]:
    """Generate a Lens Studio project scene data."""
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
    """Create a new Lens Studio project by copying the real LS template."""
    if template not in TEMPLATES:
        raise ValueError(f"Unknown template '{template}'. Available: {', '.join(TEMPLATES)}")

    base_dir = Path(directory) if directory else get_projects_dir()
    project_dir = base_dir / name

    if project_dir.exists():
        raise FileExistsError(f"Project already exists: {project_dir}")

    # Copy the real LS template if available
    ls_template = Path(LS_TEMPLATE_DIR)
    if ls_template.exists():
        shutil.copytree(str(ls_template), str(project_dir))
        # Rename Project.esproj to <name>.esproj
        template_esproj = project_dir / "Project.esproj"
        project_file = project_dir / f"{name}{PROJECT_EXT}"
        if template_esproj.exists():
            # Read, update name, write
            with open(template_esproj) as f:
                esproj_data = yaml.safe_load(f)
            esproj_data["metaInfo"]["lensName"] = name
            esproj_data["metaInfo"]["documentId"] = _new_uuid()
            esproj_data["metaInfo"]["originalDocumentId"] = _new_uuid()
            esproj_data["sceneId"] = _new_uuid()
            with open(project_file, "w") as f:
                yaml.dump(esproj_data, f, default_flow_style=False, sort_keys=False)
            template_esproj.unlink()
        else:
            # No template .esproj — generate one
            esproj_data = _blank_esproj(name)
            with open(project_file, "w") as f:
                yaml.dump(esproj_data, f, default_flow_style=False, sort_keys=False)
    else:
        # No LS installation — create minimal project structure
        ensure_dir(project_dir)
        ensure_dir(project_dir / "Assets")
        ensure_dir(project_dir / "Cache")
        ensure_dir(project_dir / "Packages")
        project_file = project_dir / f"{name}{PROJECT_EXT}"
        esproj_data = _blank_esproj(name)
        with open(project_file, "w") as f:
            yaml.dump(esproj_data, f, default_flow_style=False, sort_keys=False)

    # Also write scene data as companion JSON (for CLI operations)
    scene_data = blank_project(name, template)
    scene_file = project_dir / f"{name}.scene.json"
    with open(scene_file, "w") as f:
        json.dump(scene_data, f, indent=2)

    return {
        "name": name,
        "path": str(project_file),
        "directory": str(project_dir),
        "template": template,
        "id": esproj_data.get("sceneId", scene_data["id"]),
    }


def load_project(path: str) -> Dict[str, Any]:
    """Load a project's scene data. Accepts .esproj or .scene.json path."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Project file not found: {path}")

    # If given .esproj, look for companion .scene.json
    if p.suffix == PROJECT_EXT:
        scene_file = p.parent / f"{p.stem}.scene.json"
        if scene_file.exists():
            with open(scene_file) as f:
                return json.load(f)
        # No scene file — return minimal data from esproj
        with open(p) as f:
            esproj = yaml.safe_load(f)
        return {
            "id": esproj.get("sceneId", ""),
            "name": esproj.get("metaInfo", {}).get("lensName", p.stem),
            "version": "5.0",
            "sceneObjects": [],
            "resources": [],
            "settings": {"targetDevice": "mobile", "orientation": "portrait"},
        }
    elif p.suffix == ".json":
        with open(p) as f:
            return json.load(f)
    else:
        raise ValueError(f"Not a Lens Studio project file: {path}")


def save_project(path: str, data: Dict[str, Any]):
    """Save project scene data. Writes companion .scene.json next to .esproj."""
    p = Path(path)
    if p.suffix == PROJECT_EXT:
        scene_file = p.parent / f"{p.stem}.scene.json"
    else:
        scene_file = p

    with open(scene_file, "w") as f:
        json.dump(data, f, indent=2)


def project_info(path: str) -> Dict[str, Any]:
    """Get summary info about a project."""
    p = Path(path)

    # Read .esproj YAML for studio metadata
    esproj_meta = {}
    if p.suffix == PROJECT_EXT and p.exists():
        with open(p) as f:
            esproj = yaml.safe_load(f) or {}
        meta = esproj.get("metaInfo", {})
        sv = esproj.get("studioVersion", {})
        esproj_meta = {
            "lensName": meta.get("lensName", p.stem),
            "studioVersion": f"{sv.get('major', '?')}.{sv.get('minor', '?')}.{sv.get('patch', '?')}",
            "documentId": meta.get("documentId", ""),
        }

    # Read scene data
    data = load_project(path)
    scene_objects = data.get("sceneObjects", [])

    return {
        "name": esproj_meta.get("lensName", data.get("name", "unknown")),
        "id": esproj_meta.get("documentId", data.get("id", "unknown")),
        "version": esproj_meta.get("studioVersion", data.get("version", "unknown")),
        "sceneObjects": len(scene_objects),
        "resources": len(data.get("resources", [])),
        "targetDevice": data.get("settings", {}).get("targetDevice", "mobile"),
        "orientation": data.get("settings", {}).get("orientation", "portrait"),
    }


def list_projects(directory: Optional[str] = None) -> List[Dict[str, Any]]:
    """List all projects in a directory."""
    base_dir = Path(directory) if directory else get_projects_dir()
    if not base_dir.exists():
        return []

    projects = []
    for item in sorted(base_dir.iterdir()):
        if item.is_dir():
            # Check for .esproj files
            for f in item.iterdir():
                if f.suffix == PROJECT_EXT:
                    try:
                        info = project_info(str(f))
                        info["path"] = str(f)
                        projects.append(info)
                    except Exception:
                        projects.append({"name": item.name, "path": str(f), "error": True})
                    break
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
