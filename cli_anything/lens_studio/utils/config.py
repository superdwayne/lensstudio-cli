"""Configuration and path utilities for Lens Studio CLI."""

import os
import platform
import shutil
from pathlib import Path
from typing import Optional


# Lens Studio application paths by platform
_LS_PATHS = {
    "Darwin": [
        "/Applications/Lens Studio.app/Contents/MacOS/Lens Studio",
        os.path.expanduser("~/Applications/Lens Studio.app/Contents/MacOS/Lens Studio"),
    ],
    "Windows": [
        r"C:\Program Files\Snap Inc\Lens Studio\Lens Studio.exe",
        r"C:\Program Files (x86)\Snap Inc\Lens Studio\Lens Studio.exe",
        os.path.expandvars(r"%LOCALAPPDATA%\Snap\Lens Studio\Lens Studio.exe"),
    ],
    "Linux": [
        "/usr/bin/lens-studio",
        "/opt/snap/lens-studio/lens-studio",
        os.path.expanduser("~/.local/bin/lens-studio"),
    ],
}

# Default project directory
DEFAULT_PROJECTS_DIR = os.path.expanduser("~/LensStudio/Projects")

# Lens Studio project file extension (LS 5.x uses .esproj YAML format)
PROJECT_EXT = ".esproj"

# Path to the default project template inside the LS app bundle
LS_TEMPLATE_DIR = "/Applications/Lens Studio.app/Contents/Resources/ModelResources.bundle/ProjectTemplates/Default"

# Supported asset types
ASSET_TYPES = {
    "texture": [".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp", ".exr", ".hdr"],
    "mesh": [".fbx", ".obj", ".gltf", ".glb"],
    "audio": [".mp3", ".wav", ".ogg", ".aac", ".m4a"],
    "video": [".mp4", ".mov", ".webm"],
    "font": [".ttf", ".otf", ".woff", ".woff2"],
    "script": [".js", ".ts"],
    "material": [".material"],
    "prefab": [".prefab"],
}

# Built-in component types in Lens Studio
COMPONENT_TYPES = [
    "Camera",
    "MeshVisual",
    "Image",
    "Text",
    "Text3D",
    "ScreenTransform",
    "Physics.BodyComponent",
    "Physics.ColliderComponent",
    "ScriptComponent",
    "AudioComponent",
    "AnimationPlayer",
    "AnimationMixer",
    "DeviceTracking",
    "Head",
    "ObjectTracking",
    "MarkerTracking",
    "HandTracking",
    "BodyTracking",
    "LightSource",
    "PostEffectVisual",
    "RetouchVisual",
    "LiquifyVisual",
    "FaceStretch",
    "FaceMask",
    "FaceInset",
    "EyeColorVisual",
    "HairVisual",
    "SegmentationTextureProvider",
    "PersistentStorageSystem",
    "LocationService",
    "SnapcodeMarkerProvider",
    "PinToMesh",
    "Interactable",
    "TouchComponent",
    "ManipulateComponent",
    "ParticlesVisual",
    "VFXComponent",
    "MLComponent",
]

# Built-in material types
MATERIAL_TYPES = [
    "Default",
    "Unlit",
    "PBR",
    "FacePaint",
    "FaceMesh",
    "Occluder",
    "DepthOnly",
    "Flat",
    "BlinnPhong",
    "UberUnlit",
    "Graph",
]

# Lens Studio templates
TEMPLATES = {
    "blank": "Empty project with a single camera",
    "face-effects": "Face tracking with face mesh and effects",
    "world-ar": "World tracking with ground plane detection",
    "marker-tracking": "Image marker tracking template",
    "hand-tracking": "Hand tracking with hand mesh",
    "body-tracking": "Full body tracking template",
    "segmentation": "Background segmentation template",
    "landmarker": "Location-based AR experience",
    "connected-lens": "Multiplayer connected lens",
    "interactive": "Touch and gesture interaction template",
    "face-landmark": "Face landmark detection template",
    "3d-object": "3D object placement template",
    "particle-system": "Particle effects template",
    "audio-reactive": "Audio-reactive visual effects",
    "ml-template": "Machine learning integration template",
    "snap-spectacles": "Spectacles AR glasses template",
}


def find_lens_studio() -> Optional[str]:
    """Find the Lens Studio executable on the system."""
    system = platform.system()

    # Check PATH first
    which_result = shutil.which("lens-studio") or shutil.which("Lens Studio")
    if which_result:
        return which_result

    # Check known paths
    for path in _LS_PATHS.get(system, []):
        if os.path.isfile(path):
            return path

    # Check environment variable
    env_path = os.environ.get("LENS_STUDIO_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path

    return None


def get_projects_dir() -> Path:
    """Get the default projects directory."""
    env_dir = os.environ.get("LS_PROJECTS_DIR")
    if env_dir:
        return Path(env_dir)
    return Path(DEFAULT_PROJECTS_DIR)


def ensure_dir(path: Path) -> Path:
    """Ensure a directory exists, creating it if necessary."""
    path.mkdir(parents=True, exist_ok=True)
    return path
