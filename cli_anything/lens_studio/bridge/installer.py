"""Bridge plugin installer — copies JS plugin into Lens Studio plugins directory."""

import os
import platform
import shutil
from pathlib import Path
from typing import Any, Optional

from ..utils.logging import get_logger

logger = get_logger(__name__)

# Known plugin directories by platform
_PLUGIN_DIRS = {
    "Darwin": [
        Path.home() / "Library" / "Application Support" / "Snap" / "Lens Studio" / "Plugins",
        Path.home() / "Library" / "Application Support" / "Lens Studio" / "Plugins",
    ],
    "Windows": [
        Path(os.path.expandvars(r"%APPDATA%\Snap\Lens Studio\Plugins")),
        Path(os.path.expandvars(r"%LOCALAPPDATA%\Snap\Lens Studio\Plugins")),
    ],
}

PLUGIN_NAME = "ls-cli-bridge"


def get_plugin_source_dir() -> Path:
    """Get the path to the bundled plugin source."""
    # Plugin source is at repo root / ls_bridge_plugin
    here = Path(__file__).resolve().parent
    # Navigate up: bridge -> lens_studio -> cli_anything -> repo root
    repo_root = here.parent.parent.parent
    plugin_dir = repo_root / "ls_bridge_plugin"
    if plugin_dir.is_dir():
        return plugin_dir
    # Fallback: check installed package data
    import importlib.resources as pkg_resources

    try:
        ref = pkg_resources.files("ls_bridge_plugin")
        return Path(str(ref))
    except (ModuleNotFoundError, TypeError):
        pass
    return plugin_dir  # Return expected path even if missing


def find_plugins_dir() -> Optional[Path]:
    """Find the Lens Studio plugins directory for the current platform."""
    system = platform.system()

    # Check environment variable first
    env_path = os.environ.get("LS_PLUGINS_DIR")
    if env_path:
        return Path(env_path)

    for p in _PLUGIN_DIRS.get(system, []):
        if p.parent.is_dir():  # Parent (Lens Studio dir) should exist
            return p

    return None


def install_plugin(target_dir: Optional[str] = None) -> dict[str, Any]:
    """Install the bridge plugin into Lens Studio's plugins directory.

    Args:
        target_dir: Override target directory (for testing)

    Returns:
        Dict with success status and installation details
    """
    source = get_plugin_source_dir()
    if not source.is_dir():
        return {
            "success": False,
            "error": f"Plugin source not found at {source}",
        }

    if target_dir:
        dest = Path(target_dir) / PLUGIN_NAME
    else:
        plugins_dir = find_plugins_dir()
        if not plugins_dir:
            return {
                "success": False,
                "error": "Could not find Lens Studio plugins directory. "
                "Set LS_PLUGINS_DIR environment variable.",
            }
        dest = plugins_dir / PLUGIN_NAME

    try:
        # Ensure parent exists
        dest.parent.mkdir(parents=True, exist_ok=True)

        # Remove existing installation
        if dest.exists():
            shutil.rmtree(dest)

        # Copy plugin
        shutil.copytree(source, dest)
        logger.info("Installed bridge plugin to %s", dest)

        # Write config.json with absolute paths so the plugin doesn't
        # need to resolve ~ (which doesn't work in LS JS runtime)
        import json as _json

        from ..utils.config import get_bridge_dir

        config_path = dest / "config.json"
        bridge_dir = get_bridge_dir()
        bridge_dir.mkdir(parents=True, exist_ok=True)
        config_data = {
            "bridge_dir": str(bridge_dir),
            "commands_dir": str(bridge_dir / "commands"),
            "responses_dir": str(bridge_dir / "responses"),
            "heartbeat_path": str(bridge_dir / "heartbeat.json"),
        }
        with open(config_path, "w") as cf:
            _json.dump(config_data, cf, indent=2)
        logger.info("Wrote plugin config with bridge_dir=%s", bridge_dir)

        # Post-install validation
        warnings: list[str] = []
        module_json = dest / "module.json"
        if module_json.is_file():
            import json

            try:
                with open(module_json) as f:
                    manifest = json.load(f)
                required_fields = {"name", "main", "permissions"}
                missing = required_fields - set(manifest.keys())
                if missing:
                    warnings.append(f"module.json missing fields: {missing}")
                main_file = dest / manifest.get("main", "bridge.js")
                if not main_file.is_file():
                    warnings.append(f"Main file '{manifest.get('main')}' not found in plugin")
            except (json.JSONDecodeError, OSError) as e:
                warnings.append(f"module.json is invalid: {e}")
        else:
            warnings.append("module.json not found in installed plugin")

        result: dict[str, Any] = {
            "success": True,
            "source": str(source),
            "destination": str(dest),
            "files": [str(f.relative_to(dest)) for f in dest.rglob("*") if f.is_file()],
            "note": "Restart Lens Studio for changes to take effect",
        }
        if warnings:
            result["warnings"] = warnings
        return result
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
        }


def uninstall_plugin(target_dir: Optional[str] = None) -> dict[str, Any]:
    """Remove the bridge plugin from Lens Studio's plugins directory."""
    if target_dir:
        dest = Path(target_dir) / PLUGIN_NAME
    else:
        plugins_dir = find_plugins_dir()
        if not plugins_dir:
            return {"success": False, "error": "Could not find Lens Studio plugins directory."}
        dest = plugins_dir / PLUGIN_NAME

    if not dest.exists():
        return {"success": True, "note": "Plugin was not installed."}

    try:
        shutil.rmtree(dest)
        return {"success": True, "removed": str(dest)}
    except Exception as e:
        return {"success": False, "error": str(e)}


def is_installed(target_dir: Optional[str] = None) -> bool:
    """Check if the bridge plugin is currently installed."""
    if target_dir:
        dest = Path(target_dir) / PLUGIN_NAME
    else:
        plugins_dir = find_plugins_dir()
        if not plugins_dir:
            return False
        dest = plugins_dir / PLUGIN_NAME

    return dest.is_dir() and (dest / "module.json").is_file()
