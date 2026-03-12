"""Script management for Lens Studio CLI.

Handles creating, listing, removing, and attaching scripts to SceneObjects.
Lens Studio scripts are JavaScript/TypeScript files with a specific API.
"""

import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .scene import find_object


def _new_uuid() -> str:
    return str(uuid.uuid4())


def _timestamp() -> str:
    return datetime.utcnow().isoformat() + "Z"


# ---------------------------------------------------------------------------
# Script templates
# ---------------------------------------------------------------------------

SCRIPT_TEMPLATES = {
    "blank": """\
// @input

// @ui {"widget":"separator"}

script.createEvent("OnStartEvent").bind(function () {
    // Initialization code here
});
""",
    "update": """\
// @input

script.createEvent("UpdateEvent").bind(function (eventData) {
    // Runs every frame
    var deltaTime = eventData.getDeltaTime();
});
""",
    "tap": """\
// @input
// @input Component.ScriptComponent targetObject

script.createEvent("TapEvent").bind(function (eventData) {
    // Handle tap interaction
    print("Tapped!");
});
""",
    "tween": """\
// @input SceneObject targetObject
// @input float duration = 1.0
// @input float delay = 0.0

var startTime = 0;
var isPlaying = false;

script.createEvent("OnStartEvent").bind(function () {
    startTime = getTime() + script.delay;
    isPlaying = true;
});

script.createEvent("UpdateEvent").bind(function () {
    if (!isPlaying) return;
    var elapsed = getTime() - startTime;
    if (elapsed < 0) return;
    var t = Math.min(elapsed / script.duration, 1.0);
    // Apply tween logic here
    if (t >= 1.0) isPlaying = false;
});
""",
    "behavior": """\
// @input string triggerType = "onStart" {"widget":"combobox","values":[{"label":"On Start","value":"onStart"},{"label":"On Tap","value":"onTap"},{"label":"On Update","value":"onUpdate"}]}
// @input string responseType = "print" {"widget":"combobox","values":[{"label":"Print","value":"print"},{"label":"Enable","value":"enable"},{"label":"Disable","value":"disable"}]}

function onTrigger() {
    switch (script.responseType) {
        case "print":
            print("Behavior triggered!");
            break;
        case "enable":
            script.getSceneObject().enabled = true;
            break;
        case "disable":
            script.getSceneObject().enabled = false;
            break;
    }
}

switch (script.triggerType) {
    case "onStart":
        script.createEvent("OnStartEvent").bind(onTrigger);
        break;
    case "onTap":
        script.createEvent("TapEvent").bind(onTrigger);
        break;
    case "onUpdate":
        script.createEvent("UpdateEvent").bind(onTrigger);
        break;
}
""",
    "typescript": """\
@component
export class NewScript extends BaseScriptComponent {

    @input
    myProperty: string = "Hello";

    onAwake(): void {
        // Initialization
    }

    onStart(): void {
        print(this.myProperty);
    }

    onUpdate(): void {
        // Runs every frame
    }
}
""",
}


# ---------------------------------------------------------------------------
# Script CRUD
# ---------------------------------------------------------------------------

def create_script(
    project_data: Dict,
    project_dir: str,
    name: str,
    template: str = "blank",
    content: Optional[str] = None,
    language: str = "javascript",
) -> Dict[str, Any]:
    """Create a new script file and register it in the project."""
    ext = ".ts" if language == "typescript" else ".js"
    filename = f"{name}{ext}"
    scripts_dir = Path(project_dir) / "Scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    script_path = scripts_dir / filename

    if script_path.exists():
        raise FileExistsError(f"Script already exists: {script_path}")

    # Write script content
    if content is None:
        if template == "typescript" or language == "typescript":
            content = SCRIPT_TEMPLATES.get("typescript", SCRIPT_TEMPLATES["blank"])
        else:
            content = SCRIPT_TEMPLATES.get(template, SCRIPT_TEMPLATES["blank"])

    with open(script_path, "w") as f:
        f.write(content)

    # Register in project
    script_id = _new_uuid()
    script_entry = {
        "id": script_id,
        "name": name,
        "fileName": filename,
        "relativePath": f"Scripts/{filename}",
        "language": language,
        "template": template,
        "created": _timestamp(),
    }
    project_data.setdefault("scripts", []).append(script_entry)

    return script_entry


def list_scripts(project_data: Dict) -> List[Dict[str, Any]]:
    """List all scripts in the project."""
    return project_data.get("scripts", [])


def get_script(project_data: Dict, script_id: str) -> Optional[Dict[str, Any]]:
    """Get script entry by ID."""
    for s in project_data.get("scripts", []):
        if s.get("id") == script_id:
            return s
    return None


def get_script_by_name(project_data: Dict, name: str) -> Optional[Dict[str, Any]]:
    """Get script entry by name."""
    for s in project_data.get("scripts", []):
        if s.get("name") == name:
            return s
    return None


def remove_script(
    project_data: Dict,
    project_dir: str,
    script_id: str,
    delete_file: bool = True,
) -> bool:
    """Remove a script from the project."""
    script = get_script(project_data, script_id)
    if not script:
        raise ValueError(f"Script not found: {script_id}")

    # Remove file
    if delete_file:
        rel_path = script.get("relativePath", "")
        if rel_path:
            file_path = Path(project_dir) / rel_path
            if file_path.exists():
                file_path.unlink()

    # Remove from project data
    project_data["scripts"] = [
        s for s in project_data.get("scripts", []) if s.get("id") != script_id
    ]

    # Remove ScriptComponent references from scene
    _remove_script_refs(project_data.get("scene", {}).get("root", {}), script_id)

    return True


def attach_script(
    project_data: Dict,
    scene_root: Dict,
    object_id: str,
    script_id: str,
) -> Dict:
    """Attach a script to a scene object as a ScriptComponent."""
    script = get_script(project_data, script_id)
    if not script:
        raise ValueError(f"Script not found: {script_id}")

    obj = find_object(scene_root, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")

    component = {
        "type": "ScriptComponent",
        "scriptId": script_id,
        "scriptName": script["name"],
        "inputs": {},
    }
    obj.setdefault("components", []).append(component)
    return component


def detach_script(scene_root: Dict, object_id: str, script_id: str) -> bool:
    """Detach a script from a scene object."""
    obj = find_object(scene_root, object_id)
    if not obj:
        raise ValueError(f"Scene object not found: {object_id}")

    components = obj.get("components", [])
    original_len = len(components)
    obj["components"] = [
        c for c in components
        if not (c.get("type") == "ScriptComponent" and c.get("scriptId") == script_id)
    ]
    return len(obj["components"]) < original_len


def read_script_content(project_dir: str, script_entry: Dict) -> str:
    """Read the content of a script file."""
    rel_path = script_entry.get("relativePath", "")
    if not rel_path:
        raise ValueError("Script has no file path")
    file_path = Path(project_dir) / rel_path
    if not file_path.exists():
        raise FileNotFoundError(f"Script file not found: {file_path}")
    return file_path.read_text()


def write_script_content(project_dir: str, script_entry: Dict, content: str):
    """Write content to a script file."""
    rel_path = script_entry.get("relativePath", "")
    if not rel_path:
        raise ValueError("Script has no file path")
    file_path = Path(project_dir) / rel_path
    file_path.write_text(content)


def _remove_script_refs(node: Dict, script_id: str):
    """Recursively remove ScriptComponent references to a script."""
    components = node.get("components", [])
    node["components"] = [
        c for c in components
        if not (c.get("type") == "ScriptComponent" and c.get("scriptId") == script_id)
    ]
    for child in node.get("children", []):
        _remove_script_refs(child, script_id)
