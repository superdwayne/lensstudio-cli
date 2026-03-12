"""Material operations for Lens Studio CLI.

Handles creating, editing, listing, and assigning materials to scene objects.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..utils.config import MATERIAL_TYPES
from .scene import find_object


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Material defaults by type
# ---------------------------------------------------------------------------

_MATERIAL_DEFAULTS = {
    "Default": {
        "shader": "default",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {
            "baseColor": [1.0, 1.0, 1.0, 1.0],
            "baseTexture": None,
        },
    },
    "Unlit": {
        "shader": "unlit",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {
            "baseColor": [1.0, 1.0, 1.0, 1.0],
            "baseTexture": None,
            "opacity": 1.0,
        },
    },
    "PBR": {
        "shader": "pbr",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {
            "baseColor": [1.0, 1.0, 1.0, 1.0],
            "baseTexture": None,
            "metallic": 0.0,
            "roughness": 0.5,
            "normalMap": None,
            "normalStrength": 1.0,
            "emissiveColor": [0.0, 0.0, 0.0],
            "emissiveStrength": 0.0,
            "aoMap": None,
            "aoStrength": 1.0,
        },
    },
    "FacePaint": {
        "shader": "facePaint",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {
            "baseColor": [1.0, 1.0, 1.0, 1.0],
            "baseTexture": None,
            "opacity": 1.0,
        },
    },
    "FaceMesh": {
        "shader": "faceMesh",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": True,
        "properties": {
            "baseColor": [1.0, 1.0, 1.0, 1.0],
            "baseTexture": None,
        },
    },
    "Occluder": {
        "shader": "occluder",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {},
    },
    "Flat": {
        "shader": "flat",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {
            "baseColor": [1.0, 1.0, 1.0, 1.0],
        },
    },
    "Graph": {
        "shader": "graph",
        "blendMode": "normal",
        "depthTest": True,
        "depthWrite": True,
        "twoSided": False,
        "properties": {},
    },
}


# ---------------------------------------------------------------------------
# Material CRUD
# ---------------------------------------------------------------------------

def create_material(
    project_data: Dict,
    name: str,
    material_type: str = "Default",
    properties: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Create a new material."""
    if material_type not in MATERIAL_TYPES:
        raise ValueError(
            f"Unknown material type '{material_type}'. "
            f"Available: {', '.join(MATERIAL_TYPES)}"
        )

    mat_id = _new_uuid()
    defaults = _MATERIAL_DEFAULTS.get(material_type, _MATERIAL_DEFAULTS["Default"]).copy()

    if properties:
        defaults.setdefault("properties", {}).update(properties)

    material = {
        "id": mat_id,
        "name": name,
        "type": material_type,
        "created": _timestamp(),
        **defaults,
    }

    project_data.setdefault("materials", []).append(material)
    return material


def list_materials(
    project_data: Dict,
    material_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List all materials, optionally filtered by type."""
    materials = project_data.get("materials", [])
    if material_type:
        materials = [m for m in materials if m.get("type") == material_type]
    return materials


def get_material(project_data: Dict, mat_id: str) -> Optional[Dict[str, Any]]:
    """Get material by ID."""
    for m in project_data.get("materials", []):
        if m.get("id") == mat_id:
            return m
    return None


def get_material_by_name(project_data: Dict, name: str) -> Optional[Dict[str, Any]]:
    """Get material by name."""
    for m in project_data.get("materials", []):
        if m.get("name") == name:
            return m
    return None


def update_material(
    project_data: Dict,
    mat_id: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update material properties."""
    material = get_material(project_data, mat_id)
    if not material:
        raise ValueError(f"Material not found: {mat_id}")

    # Update top-level fields
    allowed_top = {"name", "blendMode", "depthTest", "depthWrite", "twoSided"}
    for key in allowed_top:
        if key in updates:
            material[key] = updates[key]

    # Update nested properties
    if "properties" in updates:
        material.setdefault("properties", {}).update(updates["properties"])

    return material


def remove_material(project_data: Dict, mat_id: str) -> bool:
    """Remove a material from the project."""
    material = get_material(project_data, mat_id)
    if not material:
        raise ValueError(f"Material not found: {mat_id}")

    project_data["materials"] = [
        m for m in project_data.get("materials", []) if m.get("id") != mat_id
    ]
    return True


def assign_material(
    project_data: Dict,
    object_id: str,
    mat_id: str,
) -> Dict:
    """Assign a material to a scene object's MeshVisual or Image component."""
    material = get_material(project_data, mat_id)
    if not material:
        raise ValueError(f"Material not found: {mat_id}")

    obj = find_object(project_data, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")

    # Find a visual component to assign to
    for comp in obj.get("components", []):
        if comp.get("type") in ("MeshVisual", "Image", "PostEffectVisual", "Text"):
            comp.setdefault("properties", {})["materialId"] = mat_id
            comp["properties"]["materialName"] = material["name"]
            return comp

    raise ValueError(
        f"Object '{obj.get('name')}' has no visual component to assign material to"
    )
