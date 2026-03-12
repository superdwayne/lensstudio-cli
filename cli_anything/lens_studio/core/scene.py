"""Scene graph operations for Lens Studio CLI.

Manages SceneObjects: add, remove, list, transform, reparent within the scene hierarchy.
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ---------------------------------------------------------------------------
# Scene traversal helpers
# ---------------------------------------------------------------------------

def find_object(root: Dict, obj_id: str) -> Optional[Dict]:
    """Find a scene object by ID (DFS)."""
    if root.get("id") == obj_id:
        return root
    for child in root.get("children", []):
        result = find_object(child, obj_id)
        if result:
            return result
    return None


def find_object_by_name(root: Dict, name: str) -> Optional[Dict]:
    """Find the first scene object matching name."""
    if root.get("name") == name:
        return root
    for child in root.get("children", []):
        result = find_object_by_name(child, name)
        if result:
            return result
    return None


def find_parent(root: Dict, obj_id: str) -> Optional[Dict]:
    """Find the parent of a scene object."""
    for child in root.get("children", []):
        if child.get("id") == obj_id:
            return root
        result = find_parent(child, obj_id)
        if result:
            return result
    return None


def flatten_scene(root: Dict, depth: int = 0) -> List[Dict]:
    """Flatten the scene tree into a list with depth info."""
    items = [{
        "id": root.get("id", ""),
        "name": root.get("name", ""),
        "type": root.get("type", ""),
        "enabled": root.get("enabled", True),
        "depth": depth,
        "components": [c.get("type", "") for c in root.get("components", [])],
        "childCount": len(root.get("children", [])),
    }]
    for child in root.get("children", []):
        items.extend(flatten_scene(child, depth + 1))
    return items


def scene_to_tree(root: Dict) -> Dict:
    """Convert scene to tree structure for display."""
    node = {
        "name": root.get("name", "unnamed"),
        "type": root.get("type", ""),
        "id": root.get("id", ""),
    }
    components = root.get("components", [])
    if components:
        node["components"] = [c.get("type", "") for c in components]
    children = root.get("children", [])
    if children:
        node["children"] = [scene_to_tree(c) for c in children]
    return node


# ---------------------------------------------------------------------------
# Scene mutations
# ---------------------------------------------------------------------------

def add_object(
    root: Dict,
    name: str,
    parent_id: Optional[str] = None,
    components: Optional[List[Dict]] = None,
    transform: Optional[Dict] = None,
) -> Dict:
    """Add a new SceneObject to the scene."""
    obj_id = _new_uuid()
    new_obj = {
        "id": obj_id,
        "name": name,
        "type": "SceneObject",
        "enabled": True,
        "components": components or [],
        "transform": transform or {
            "position": [0, 0, 0],
            "rotation": [0, 0, 0],
            "scale": [1, 1, 1],
        },
        "children": [],
    }

    if parent_id:
        parent = find_object(root, parent_id)
        if not parent:
            raise ValueError(f"Parent object not found: {parent_id}")
        parent.setdefault("children", []).append(new_obj)
    else:
        root.setdefault("children", []).append(new_obj)

    return new_obj


def remove_object(root: Dict, obj_id: str) -> bool:
    """Remove a scene object by ID."""
    if root.get("id") == obj_id:
        raise ValueError("Cannot remove the root scene object")

    parent = find_parent(root, obj_id)
    if not parent:
        raise ValueError(f"Object not found: {obj_id}")

    parent["children"] = [c for c in parent["children"] if c.get("id") != obj_id]
    return True


def rename_object(root: Dict, obj_id: str, new_name: str) -> Dict:
    """Rename a scene object."""
    obj = find_object(root, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")
    obj["name"] = new_name
    return obj


def set_transform(
    root: Dict,
    obj_id: str,
    position: Optional[List[float]] = None,
    rotation: Optional[List[float]] = None,
    scale: Optional[List[float]] = None,
) -> Dict:
    """Set transform properties on a scene object."""
    obj = find_object(root, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    transform = obj.setdefault("transform", {
        "position": [0, 0, 0],
        "rotation": [0, 0, 0],
        "scale": [1, 1, 1],
    })

    if position is not None:
        transform["position"] = position
    if rotation is not None:
        transform["rotation"] = rotation
    if scale is not None:
        transform["scale"] = scale

    return obj


def set_enabled(root: Dict, obj_id: str, enabled: bool) -> Dict:
    """Enable or disable a scene object."""
    obj = find_object(root, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")
    obj["enabled"] = enabled
    return obj


def reparent(root: Dict, obj_id: str, new_parent_id: str) -> Dict:
    """Move a scene object to a new parent."""
    obj = find_object(root, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    if obj_id == root.get("id"):
        raise ValueError("Cannot reparent the root object")

    new_parent = find_object(root, new_parent_id)
    if not new_parent:
        raise ValueError(f"New parent not found: {new_parent_id}")

    # Check for circular reparenting
    if find_object(obj, new_parent_id):
        raise ValueError("Cannot reparent to a descendant")

    # Remove from current parent
    old_parent = find_parent(root, obj_id)
    if old_parent:
        old_parent["children"] = [c for c in old_parent["children"] if c.get("id") != obj_id]

    # Add to new parent
    new_parent.setdefault("children", []).append(obj)
    return obj


def duplicate_object(root: Dict, obj_id: str) -> Dict:
    """Duplicate a scene object (deep copy with new IDs)."""
    import copy
    obj = find_object(root, obj_id)
    if not obj:
        raise ValueError(f"Object not found: {obj_id}")

    parent = find_parent(root, obj_id)
    if not parent:
        parent = root

    clone = copy.deepcopy(obj)
    _assign_new_ids(clone)
    clone["name"] = f"{clone['name']} (Copy)"

    parent.setdefault("children", []).append(clone)
    return clone


def _assign_new_ids(node: Dict):
    """Recursively assign new UUIDs to a node tree."""
    node["id"] = _new_uuid()
    for child in node.get("children", []):
        _assign_new_ids(child)
