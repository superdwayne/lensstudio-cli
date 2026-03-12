"""Template management for Lens Studio CLI.

Lists and applies built-in project templates.
"""

from typing import Any, Dict, List, Optional

from ..utils.config import TEMPLATES
from .project import create_project


def list_templates() -> List[Dict[str, str]]:
    """List all available templates."""
    return [
        {"name": name, "description": desc}
        for name, desc in TEMPLATES.items()
    ]


def get_template(name: str) -> Optional[Dict[str, str]]:
    """Get a specific template by name."""
    desc = TEMPLATES.get(name)
    if desc is None:
        return None
    return {"name": name, "description": desc}


def apply_template(
    project_name: str,
    template_name: str,
    directory: Optional[str] = None,
) -> Dict[str, Any]:
    """Create a new project from a template."""
    if template_name not in TEMPLATES:
        raise ValueError(
            f"Unknown template '{template_name}'. "
            f"Available: {', '.join(TEMPLATES.keys())}"
        )

    return create_project(
        name=project_name,
        directory=directory,
        template=template_name,
    )


def template_info(template_name: str) -> Dict[str, Any]:
    """Get detailed info about a template."""
    if template_name not in TEMPLATES:
        raise ValueError(f"Unknown template: {template_name}")

    # Detailed template descriptions
    details = {
        "blank": {
            "components": ["Camera"],
            "features": ["Basic scene setup"],
            "difficulty": "Beginner",
            "use_cases": ["Custom projects", "Learning"],
        },
        "face-effects": {
            "components": ["Camera", "Head", "FaceMask"],
            "features": ["Face tracking", "Face mesh", "Face effects pipeline"],
            "difficulty": "Beginner",
            "use_cases": ["Face filters", "Face masks", "Beauty effects"],
        },
        "world-ar": {
            "components": ["Camera", "DeviceTracking"],
            "features": ["World tracking", "Ground plane detection", "6DoF"],
            "difficulty": "Intermediate",
            "use_cases": ["AR objects", "Ground plane placement", "World effects"],
        },
        "marker-tracking": {
            "components": ["Camera", "MarkerTracking"],
            "features": ["Image marker detection", "Marker-anchored content"],
            "difficulty": "Intermediate",
            "use_cases": ["Product packaging AR", "Print media AR", "Museum guides"],
        },
        "hand-tracking": {
            "components": ["Camera", "HandTracking", "MeshVisual"],
            "features": ["Hand detection", "Hand mesh", "Gesture recognition"],
            "difficulty": "Intermediate",
            "use_cases": ["Hand effects", "Gesture interactions", "Virtual try-on"],
        },
        "body-tracking": {
            "components": ["Camera", "BodyTracking"],
            "features": ["Full body pose estimation", "Body segmentation"],
            "difficulty": "Advanced",
            "use_cases": ["Full body effects", "Virtual clothing", "Dance effects"],
        },
        "segmentation": {
            "components": ["Camera", "SegmentationTextureProvider", "Image"],
            "features": ["Background segmentation", "Person segmentation"],
            "difficulty": "Beginner",
            "use_cases": ["Background replacement", "Portrait effects"],
        },
        "landmarker": {
            "components": ["Camera", "DeviceTracking", "LocationService"],
            "features": ["Location anchoring", "GPS-based AR"],
            "difficulty": "Advanced",
            "use_cases": ["Location-based experiences", "City tours", "Geo-AR"],
        },
        "connected-lens": {
            "components": ["Camera", "ScriptComponent"],
            "features": ["Multiplayer sync", "Connected Lenses API"],
            "difficulty": "Advanced",
            "use_cases": ["Multiplayer games", "Shared experiences"],
        },
        "interactive": {
            "components": ["Camera", "TouchComponent", "Interactable"],
            "features": ["Touch input", "Gesture handling", "Manipulation"],
            "difficulty": "Beginner",
            "use_cases": ["Interactive objects", "Games", "UI experiences"],
        },
        "face-landmark": {
            "components": ["Camera", "Head"],
            "features": ["Face landmark points", "Feature detection"],
            "difficulty": "Intermediate",
            "use_cases": ["Precise face effects", "Makeup", "Accessories"],
        },
        "3d-object": {
            "components": ["Camera", "MeshVisual", "DeviceTracking"],
            "features": ["3D object rendering", "World placement"],
            "difficulty": "Beginner",
            "use_cases": ["Product visualization", "3D models in AR"],
        },
        "particle-system": {
            "components": ["Camera", "ParticlesVisual"],
            "features": ["Particle emitters", "VFX"],
            "difficulty": "Intermediate",
            "use_cases": ["Special effects", "Fireworks", "Magic effects"],
        },
        "audio-reactive": {
            "components": ["Camera", "AudioComponent", "ScriptComponent"],
            "features": ["Audio analysis", "Beat detection", "Visualization"],
            "difficulty": "Advanced",
            "use_cases": ["Music visualizers", "Audio-reactive filters"],
        },
        "ml-template": {
            "components": ["Camera", "MLComponent"],
            "features": ["ML model loading", "Inference pipeline"],
            "difficulty": "Advanced",
            "use_cases": ["Custom ML models", "Object detection", "Style transfer"],
        },
        "snap-spectacles": {
            "components": ["Camera", "DeviceTracking"],
            "features": ["Spectacles display", "Stereo rendering"],
            "difficulty": "Advanced",
            "use_cases": ["Spectacles AR glasses experiences"],
        },
    }

    base_info = {
        "name": template_name,
        "description": TEMPLATES[template_name],
    }
    extra = details.get(template_name, {})
    base_info.update(extra)
    return base_info
