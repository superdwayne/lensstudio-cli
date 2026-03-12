"""Asset management for Lens Studio CLI.

Handles importing, listing, removing, and inspecting assets (textures, meshes, audio, etc.).
"""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..utils.config import ASSET_TYPES


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


def detect_asset_type(file_path: str) -> str:
    """Detect asset type from file extension."""
    ext = Path(file_path).suffix.lower()
    for asset_type, extensions in ASSET_TYPES.items():
        if ext in extensions:
            return asset_type
    return "unknown"


def import_asset(
    project_data: Dict,
    project_dir: str,
    source_path: str,
    name: Optional[str] = None,
    asset_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Import an asset file into the project."""
    src = Path(source_path)
    if not src.exists():
        raise FileNotFoundError(f"Source file not found: {source_path}")

    detected_type = asset_type or detect_asset_type(source_path)
    asset_name = name or src.stem

    # Determine destination subdirectory
    type_to_dir = {
        "texture": "Textures",
        "mesh": "Meshes",
        "audio": "Audio",
        "video": "Audio",
        "font": "Fonts",
        "script": "Scripts",
        "material": "Materials",
        "prefab": "Prefabs",
    }
    sub_dir = type_to_dir.get(detected_type, "Resources")
    dest_dir = Path(project_dir) / sub_dir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / src.name

    # Copy file
    shutil.copy2(str(src), str(dest_path))

    # Register in project data
    asset_id = _new_uuid()
    asset_entry = {
        "id": asset_id,
        "name": asset_name,
        "type": detected_type,
        "fileName": src.name,
        "relativePath": f"{sub_dir}/{src.name}",
        "fileSize": os.path.getsize(str(dest_path)),
        "imported": _timestamp(),
    }

    # Add type-specific metadata
    if detected_type == "texture":
        asset_entry["textureSettings"] = {
            "wrapMode": "repeat",
            "filterMode": "bilinear",
            "compression": "auto",
        }
    elif detected_type == "mesh":
        asset_entry["meshSettings"] = {
            "importScale": 1.0,
            "importAnimations": True,
            "importMaterials": True,
        }
    elif detected_type == "audio":
        asset_entry["audioSettings"] = {
            "loadType": "decompressOnLoad",
            "sampleRate": 44100,
        }

    project_data.setdefault("assets", []).append(asset_entry)

    return asset_entry


def list_assets(
    project_data: Dict,
    asset_type: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """List assets in the project, optionally filtered by type."""
    assets = project_data.get("assets", [])
    if asset_type:
        assets = [a for a in assets if a.get("type") == asset_type]
    return assets


def get_asset(project_data: Dict, asset_id: str) -> Optional[Dict[str, Any]]:
    """Get asset details by ID."""
    for asset in project_data.get("assets", []):
        if asset.get("id") == asset_id:
            return asset
    return None


def get_asset_by_name(project_data: Dict, name: str) -> Optional[Dict[str, Any]]:
    """Get asset details by name."""
    for asset in project_data.get("assets", []):
        if asset.get("name") == name:
            return asset
    return None


def remove_asset(
    project_data: Dict,
    project_dir: str,
    asset_id: str,
    delete_file: bool = True,
) -> bool:
    """Remove an asset from the project."""
    asset = get_asset(project_data, asset_id)
    if not asset:
        raise ValueError(f"Asset not found: {asset_id}")

    # Remove file if requested
    if delete_file:
        rel_path = asset.get("relativePath", "")
        if rel_path:
            file_path = Path(project_dir) / rel_path
            if file_path.exists():
                file_path.unlink()

    # Remove from project data
    project_data["assets"] = [
        a for a in project_data.get("assets", []) if a.get("id") != asset_id
    ]
    return True


def update_asset(
    project_data: Dict,
    asset_id: str,
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """Update asset properties."""
    asset = get_asset(project_data, asset_id)
    if not asset:
        raise ValueError(f"Asset not found: {asset_id}")

    # Only allow updating certain fields
    allowed = {"name", "textureSettings", "meshSettings", "audioSettings"}
    for key, value in updates.items():
        if key in allowed:
            asset[key] = value

    return asset
