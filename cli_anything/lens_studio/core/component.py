"""Component management for Lens Studio CLI.

Handles adding, removing, listing, and configuring components on SceneObjects.
"""

from typing import Any, Dict, List, Optional

from ..utils.config import COMPONENT_TYPES
from .scene import find_object
from .project import _new_uuid


# ---------------------------------------------------------------------------
# Component defaults
# ---------------------------------------------------------------------------

_COMPONENT_DEFAULTS = {
    "Camera": {"renderOrder": 0, "renderLayer": "default", "clearColor": [0, 0, 0, 0]},
    "MeshVisual": {"mesh": None, "materialId": None, "renderOrder": 0},
    "Image": {"texture": None, "materialId": None, "stretchMode": "fill"},
    "Text": {"text": "Text", "font": "default", "size": 48, "color": [1, 1, 1, 1], "alignment": "center"},
    "Text3D": {"text": "3D Text", "font": "default", "size": 1.0, "color": [1, 1, 1, 1]},
    "ScreenTransform": {"anchors": {"left": 0, "right": 1, "top": 1, "bottom": 0}, "offsets": {"left": 0, "right": 0, "top": 0, "bottom": 0}},
    "ScriptComponent": {"scriptId": None, "inputs": {}},
    "AudioComponent": {"audioTrack": None, "playOnStart": False, "loop": False, "volume": 1.0},
    "AnimationPlayer": {"clip": None, "playOnStart": True, "loop": True},
    "AnimationMixer": {"clips": [], "autoPlay": True},
    "DeviceTracking": {"trackingMode": "world"},
    "Head": {"attachmentPoint": "center"},
    "ObjectTracking": {"targetObject": None},
    "MarkerTracking": {"markerAsset": None},
    "HandTracking": {"hand": "right"},
    "BodyTracking": {},
    "LightSource": {"lightType": "directional", "color": [1, 1, 1], "intensity": 1.0, "castShadows": False},
    "PostEffectVisual": {"effect": None, "materialId": None},
    "RetouchVisual": {"eyeEnlarge": 0, "faceShrink": 0, "skinSmoothing": 0},
    "LiquifyVisual": {},
    "FaceStretch": {"feature": "nose", "intensity": 0.0},
    "FaceMask": {"texture": None},
    "FaceInset": {"faceRegion": "mouth"},
    "EyeColorVisual": {"color": [0.5, 0.3, 0.1, 1.0]},
    "HairVisual": {"color": [0.2, 0.1, 0.05, 1.0]},
    "SegmentationTextureProvider": {"segmentationType": "background"},
    "PersistentStorageSystem": {},
    "LocationService": {},
    "PinToMesh": {"targetMesh": None, "triangleIndex": 0},
    "Interactable": {},
    "TouchComponent": {},
    "ManipulateComponent": {"allowTranslation": True, "allowRotation": True, "allowScale": True},
    "ParticlesVisual": {"maxParticles": 100, "emissionRate": 10, "lifetime": 2.0},
    "VFXComponent": {"asset": None},
    "MLComponent": {"model": None},
}


# ---------------------------------------------------------------------------
# Component operations
# ---------------------------------------------------------------------------

def add_component(
    project_data: Dict,
    object_id: str,
    component_type: str,
    properties: Optional[Dict] = None,
) -> Dict[str, Any]:
    """Add a component to a scene object."""
    if component_type not in COMPONENT_TYPES:
        raise ValueError(
            f"Unknown component type '{component_type}'. "
            f"Use 'component list-types' to see available types."
        )

    obj = find_object(project_data, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")

    # Check for duplicate components (some types only allow one)
    single_instance = {
        "Camera", "ScreenTransform", "DeviceTracking", "Head",
        "HandTracking", "BodyTracking", "SegmentationTextureProvider",
    }
    if component_type in single_instance:
        existing = [c for c in obj.get("components", []) if c.get("type") == component_type]
        if existing:
            raise ValueError(
                f"Object already has a {component_type} component (only one allowed)"
            )

    # Build component in real LS format: {type, id, properties}
    defaults = _COMPONENT_DEFAULTS.get(component_type, {}).copy()
    if properties:
        defaults.update(properties)

    component = {"type": component_type, "id": _new_uuid(), "properties": defaults}
    obj.setdefault("components", []).append(component)

    return component


def remove_component(
    project_data: Dict,
    object_id: str,
    component_type: str,
    index: int = 0,
) -> bool:
    """Remove a component from a scene object by type and optional index."""
    obj = find_object(project_data, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")

    components = obj.get("components", [])
    matches = [(i, c) for i, c in enumerate(components) if c.get("type") == component_type]

    if not matches:
        raise ValueError(f"No {component_type} component found on object")

    if index >= len(matches):
        raise ValueError(f"Component index {index} out of range (found {len(matches)})")

    real_index = matches[index][0]
    components.pop(real_index)
    return True


def list_components(project_data: Dict, object_id: str) -> List[Dict[str, Any]]:
    """List all components on a scene object."""
    obj = find_object(project_data, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")
    return obj.get("components", [])


def configure_component(
    project_data: Dict,
    object_id: str,
    component_type: str,
    properties: Dict[str, Any],
    index: int = 0,
) -> Dict[str, Any]:
    """Configure properties on an existing component."""
    obj = find_object(project_data, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")

    components = obj.get("components", [])
    matches = [(i, c) for i, c in enumerate(components) if c.get("type") == component_type]

    if not matches:
        raise ValueError(f"No {component_type} component found on object")

    if index >= len(matches):
        raise ValueError(f"Component index {index} out of range (found {len(matches)})")

    component = matches[index][1]
    component.setdefault("properties", {}).update(properties)
    return component


def list_component_types() -> List[Dict[str, str]]:
    """List all available component types with descriptions."""
    descriptions = {
        "Camera": "Renders the scene from a viewpoint",
        "MeshVisual": "Displays a 3D mesh with material",
        "Image": "Displays a 2D texture/image",
        "Text": "Renders 2D text overlay",
        "Text3D": "Renders 3D text in world space",
        "ScreenTransform": "2D screen-space positioning",
        "ScriptComponent": "Attaches a JavaScript/TypeScript script",
        "AudioComponent": "Plays audio tracks",
        "AnimationPlayer": "Plays animation clips",
        "AnimationMixer": "Blends multiple animations",
        "DeviceTracking": "Tracks device position/orientation",
        "Head": "Tracks head position for face effects",
        "ObjectTracking": "Tracks 3D objects in the scene",
        "MarkerTracking": "Tracks image markers",
        "HandTracking": "Tracks hand gestures and positions",
        "BodyTracking": "Tracks full body pose",
        "LightSource": "Adds lighting to the scene",
        "PostEffectVisual": "Applies post-processing effects",
        "RetouchVisual": "Beauty/retouch face effects",
        "LiquifyVisual": "Face liquify deformation",
        "FaceStretch": "Stretches facial features",
        "FaceMask": "Applies texture mask to face",
        "FaceInset": "Insets region of face",
        "EyeColorVisual": "Changes eye color",
        "HairVisual": "Changes hair color",
        "SegmentationTextureProvider": "Provides segmentation masks",
        "PersistentStorageSystem": "Persistent data storage",
        "LocationService": "GPS location access",
        "PinToMesh": "Pins object to mesh surface",
        "Interactable": "Makes object interactable",
        "TouchComponent": "Handles touch input",
        "ManipulateComponent": "Allows translate/rotate/scale gestures",
        "ParticlesVisual": "Particle system emitter",
        "VFXComponent": "Visual effects component",
        "MLComponent": "Machine learning model inference",
    }
    return [
        {"type": t, "description": descriptions.get(t, "")}
        for t in COMPONENT_TYPES
    ]
