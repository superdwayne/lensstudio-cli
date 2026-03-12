"""Scene graph operations for Lens Studio CLI.

Operates on a flat sceneObjects array matching the real Lens Studio .lsproj format.
Parent-child relationships use the `parentId` field on each object.

All functions take the project data dict (or its sceneObjects list) as first arg.
"""

import copy
import uuid
from typing import Any, Dict, List, Optional

from .project import _default_transform, _vec3


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Accessors — work on project_data["sceneObjects"] (a flat list)
# ---------------------------------------------------------------------------

def _objects(project_data: Dict) -> List[Dict]:
    """Get the sceneObjects list from project data."""
    return project_data.setdefault("sceneObjects", [])


def find_object(project_data: Dict, obj_id: str) -> Optional[Dict]:
    """Find a scene object by ID."""
    for obj in _objects(project_data):
        if obj.get("id") == obj_id:
            return obj
    return None


def find_object_by_name(project_data: Dict, name: str) -> Optional[Dict]:
    """Find the first scene object matching name."""
    for obj in _objects(project_data):
        if obj.get("name") == name:
            return obj
    return None


def get_children(project_data: Dict, parent_id: str) -> List[Dict]:
    """Get direct children of an object."""
    return [o for o in _objects(project_data) if o.get("parentId") == parent_id]


def get_descendants(project_data: Dict, obj_id: str) -> List[Dict]:
    """Get all descendants of an object (recursive)."""
    children = get_children(project_data, obj_id)
    result = list(children)
    for child in children:
        result.extend(get_descendants(project_data, child["id"]))
    return result


def get_roots(project_data: Dict) -> List[Dict]:
    """Get top-level objects (no parentId)."""
    return [o for o in _objects(project_data) if not o.get("parentId")]


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def flatten_scene(project_data: Dict) -> List[Dict]:
    """Flatten the scene into a display list with depth info."""
    items = []
    roots = get_roots(project_data)
    for root in roots:
        _flatten_recursive(project_data, root, 0, items)
    return items


def _flatten_recursive(project_data: Dict, obj: Dict, depth: int, items: List):
    items.append({
        "id": obj.get("id", ""),
        "name": obj.get("name", ""),
        "enabled": obj.get("enabled", True),
        "depth": depth,
        "components": [c.get("type", "") for c in obj.get("components", [])],
        "childCount": len(get_children(project_data, obj["id"])),
    })
    for child in get_children(project_data, obj["id"]):
        _flatten_recursive(project_data, child, depth + 1, items)


def scene_to_tree(project_data: Dict) -> List[Dict]:
    """Convert flat scene to nested tree structure for display."""
    roots = get_roots(project_data)
    return [_build_tree_node(project_data, r) for r in roots]


def _build_tree_node(project_data: Dict, obj: Dict) -> Dict:
    node = {
        "name": obj.get("name", "unnamed"),
        "id": obj.get("id", ""),
    }
    components = obj.get("components", [])
    if components:
        node["components"] = [c.get("type", "") for c in components]
    children = get_children(project_data, obj["id"])
    if children:
        node["children"] = [_build_tree_node(project_data, c) for c in children]
    return node


# ---------------------------------------------------------------------------
# Scene mutations
# ---------------------------------------------------------------------------

def add_object(
    project_data: Dict,
    name: str,
    parent_id: Optional[str] = None,
    components: Optional[List[Dict]] = None,
    transform: Optional[Dict] = None,
) -> Dict:
    """Add a new SceneObject to the scene."""
    if parent_id:
        parent = find_object(project_data, parent_id)
        if not parent:
            raise ValueError(f"Parent object not found: {parent_id}")

    new_obj = {
        "id": _new_uuid(),
        "name": name,
        "enabled": True,
        "parentId": parent_id,
        "transform": transform or _default_transform(),
        "components": components or [],
    }

    _objects(project_data).append(new_obj)
    return new_obj


def remove_object(project_data: Dict, obj_id: str) -> bool:
    """Remove a scene object and all its descendants."""
    obj = find_object(project_data, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    # Collect IDs to remove (object + all descendants)
    ids_to_remove = {obj_id}
    for desc in get_descendants(project_data, obj_id):
        ids_to_remove.add(desc["id"])

    project_data["sceneObjects"] = [
        o for o in _objects(project_data) if o["id"] not in ids_to_remove
    ]
    return True


def rename_object(project_data: Dict, obj_id: str, new_name: str) -> Dict:
    """Rename a scene object."""
    obj = find_object(project_data, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")
    obj["name"] = new_name
    return obj


def set_transform(
    project_data: Dict,
    obj_id: str,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> Dict:
    """Set transform properties on a scene object using [x,y,z] input."""
    obj = find_object(project_data, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    transform = obj.setdefault("transform", _default_transform())

    if position is not None:
        transform["position"] = _vec3(*position)
    if rotation is not None:
        transform["rotation"] = _vec3(*rotation)
    if scale is not None:
        transform["scale"] = _vec3(*scale)

    return obj


def set_enabled(project_data: Dict, obj_id: str, enabled: bool) -> Dict:
    """Enable or disable a scene object."""
    obj = find_object(project_data, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")
    obj["enabled"] = enabled
    return obj


def reparent(project_data: Dict, obj_id: str, new_parent_id: Optional[str]) -> Dict:
    """Move a scene object to a new parent (None = make root)."""
    obj = find_object(project_data, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    if new_parent_id:
        new_parent = find_object(project_data, new_parent_id)
        if not new_parent:
            raise ValueError(f"New parent not found: {new_parent_id}")

        # Check for circular reparenting
        desc_ids = {d["id"] for d in get_descendants(project_data, obj_id)}
        if new_parent_id in desc_ids:
            raise ValueError("Cannot reparent to a descendant")

    obj["parentId"] = new_parent_id
    return obj


def duplicate_object(project_data: Dict, obj_id: str) -> Dict:
    """Duplicate a scene object (deep copy with new IDs)."""
    obj = find_object(project_data, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    clone = copy.deepcopy(obj)
    clone["id"] = _new_uuid()
    clone["name"] = f"{clone['name']} (Copy)"

    # Assign new IDs to component entries too
    for comp in clone.get("components", []):
        if "id" in comp:
            comp["id"] = _new_uuid()

    _objects(project_data).append(clone)

    # Also duplicate descendants
    for desc in get_descendants(project_data, obj_id):
        desc_clone = copy.deepcopy(desc)
        old_id = desc_clone["id"]
        desc_clone["id"] = _new_uuid()
        # Update parentId if it pointed to the original object
        if desc_clone.get("parentId") == obj_id:
            desc_clone["parentId"] = clone["id"]
        for comp in desc_clone.get("components", []):
            if "id" in comp:
                comp["id"] = _new_uuid()
        _objects(project_data).append(desc_clone)

    return clone
