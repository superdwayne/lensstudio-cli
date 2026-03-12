"""Live dashboard server for LS-CLI — see changes as they happen."""

import json
import os
import sys
import tempfile
import time
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

# Add parent to path so we can import the CLI package
sys.path.insert(0, str(Path(__file__).parent.parent))

from cli_anything.lens_studio.core import project as proj_core
from cli_anything.lens_studio.core import scene as scene_core
from cli_anything.lens_studio.core import asset as asset_core
from cli_anything.lens_studio.core import script as script_core
from cli_anything.lens_studio.core import material as mat_core
from cli_anything.lens_studio.core import component as comp_core
from cli_anything.lens_studio.core import lens as lens_core
from cli_anything.lens_studio.core import template as tmpl_core
from cli_anything.lens_studio.utils.config import COMPONENT_TYPES, MATERIAL_TYPES, TEMPLATES

app = Flask(__name__, static_folder="static")
CORS(app)

# In-memory state
STATE = {
    "project_path": None,
    "project_dir": None,
    "project_data": None,
    "log": [],
}


def log_event(action: str, detail: str, data: dict = None):
    """Add an event to the live log."""
    entry = {
        "time": time.strftime("%H:%M:%S"),
        "action": action,
        "detail": detail,
        "data": data or {},
    }
    STATE["log"].append(entry)
    # Keep last 100 entries
    if len(STATE["log"]) > 100:
        STATE["log"] = STATE["log"][-100:]
    return entry


def get_scene_tree(node):
    """Convert scene to nested tree for the frontend."""
    result = {
        "id": node.get("id", ""),
        "name": node.get("name", "unnamed"),
        "enabled": node.get("enabled", True),
        "components": [c.get("type", "") for c in node.get("components", [])],
        "transform": node.get("transform", {}),
        "children": [],
    }
    for child in node.get("children", []):
        result["children"].append(get_scene_tree(child))
    return result


# ── Static files ──────────────────────────────────────────────────────

@app.route("/")
def index():
    return send_from_directory("static", "index.html")


@app.route("/static/<path:path>")
def static_files(path):
    return send_from_directory("static", path)


# ── API: State ────────────────────────────────────────────────────────

@app.route("/api/state")
def api_state():
    """Get full current state."""
    data = STATE["project_data"]
    if not data:
        return jsonify({"project": None, "log": STATE["log"]})

    root = data.get("scene", {}).get("root", {})
    return jsonify({
        "project": {
            "name": data["project"]["name"],
            "id": data["project"]["id"],
            "template": data["project"].get("template", "blank"),
            "created": data["project"]["created"],
            "modified": data["project"]["modified"],
            "path": STATE["project_path"],
        },
        "scene": get_scene_tree(root),
        "assets": data.get("assets", []),
        "scripts": data.get("scripts", []),
        "materials": data.get("materials", []),
        "settings": data.get("settings", {}),
        "stats": {
            "objects": lens_core._count_objects(root),
            "components": lens_core._count_components(root),
            "assets": len(data.get("assets", [])),
            "scripts": len(data.get("scripts", [])),
            "materials": len(data.get("materials", [])),
        },
        "log": STATE["log"],
    })


@app.route("/api/log")
def api_log():
    """Get only the event log (for polling)."""
    return jsonify({"log": STATE["log"]})


# ── API: Templates ────────────────────────────────────────────────────

@app.route("/api/templates")
def api_templates():
    return jsonify({"templates": tmpl_core.list_templates()})


@app.route("/api/templates/<name>")
def api_template_info(name):
    try:
        return jsonify(tmpl_core.template_info(name))
    except ValueError as e:
        return jsonify({"error": str(e)}), 400


# ── API: Project ──────────────────────────────────────────────────────

@app.route("/api/project/new", methods=["POST"])
def api_project_new():
    body = request.json
    name = body.get("name", "Untitled")
    template = body.get("template", "blank")
    directory = body.get("directory") or tempfile.mkdtemp(prefix="ls_cli_live_")

    try:
        result = proj_core.create_project(name, directory, template)
        STATE["project_path"] = result["path"]
        STATE["project_dir"] = result["directory"]
        STATE["project_data"] = proj_core.load_project(result["path"])
        entry = log_event("project.new", f"Created '{name}' from template '{template}'", result)
        return jsonify({"ok": True, "result": result, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/project/info")
def api_project_info():
    if not STATE["project_path"]:
        return jsonify({"error": "No project loaded"}), 400
    info = proj_core.project_info(STATE["project_path"])
    return jsonify(info)


# ── API: Scene ────────────────────────────────────────────────────────

@app.route("/api/scene")
def api_scene():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400
    root = STATE["project_data"]["scene"]["root"]
    return jsonify({"scene": get_scene_tree(root)})


@app.route("/api/scene/add", methods=["POST"])
def api_scene_add():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    name = body.get("name", "New Object")
    parent_id = body.get("parentId")
    root = STATE["project_data"]["scene"]["root"]

    try:
        obj = scene_core.add_object(root, name, parent_id=parent_id)
        _save()
        entry = log_event("scene.add", f"Added '{name}'", {"id": obj["id"], "name": name})
        return jsonify({"ok": True, "object": obj, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/scene/remove", methods=["POST"])
def api_scene_remove():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("id")
    root = STATE["project_data"]["scene"]["root"]

    try:
        obj = scene_core.find_object(root, obj_id)
        obj_name = obj["name"] if obj else obj_id
        scene_core.remove_object(root, obj_id)
        _save()
        entry = log_event("scene.remove", f"Removed '{obj_name}'")
        return jsonify({"ok": True, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/scene/transform", methods=["POST"])
def api_scene_transform():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("id")
    root = STATE["project_data"]["scene"]["root"]

    try:
        obj = scene_core.set_transform(
            root, obj_id,
            position=body.get("position"),
            rotation=body.get("rotation"),
            scale=body.get("scale"),
        )
        _save()
        entry = log_event("scene.transform", f"Transformed '{obj['name']}'", obj.get("transform"))
        return jsonify({"ok": True, "transform": obj.get("transform"), "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/scene/rename", methods=["POST"])
def api_scene_rename():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("id")
    new_name = body.get("name")
    root = STATE["project_data"]["scene"]["root"]

    try:
        scene_core.rename_object(root, obj_id, new_name)
        _save()
        entry = log_event("scene.rename", f"Renamed to '{new_name}'")
        return jsonify({"ok": True, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/scene/duplicate", methods=["POST"])
def api_scene_duplicate():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("id")
    root = STATE["project_data"]["scene"]["root"]

    try:
        clone = scene_core.duplicate_object(root, obj_id)
        _save()
        entry = log_event("scene.duplicate", f"Duplicated → '{clone['name']}'", {"id": clone["id"]})
        return jsonify({"ok": True, "object": {"id": clone["id"], "name": clone["name"]}, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/scene/toggle", methods=["POST"])
def api_scene_toggle():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("id")
    enabled = body.get("enabled", True)
    root = STATE["project_data"]["scene"]["root"]

    try:
        scene_core.set_enabled(root, obj_id, enabled)
        _save()
        state = "Enabled" if enabled else "Disabled"
        entry = log_event("scene.toggle", f"{state} object")
        return jsonify({"ok": True, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ── API: Components ───────────────────────────────────────────────────

@app.route("/api/component/types")
def api_component_types():
    return jsonify({"types": comp_core.list_component_types()})


@app.route("/api/component/add", methods=["POST"])
def api_component_add():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("objectId")
    comp_type = body.get("type")
    props = body.get("properties")
    root = STATE["project_data"]["scene"]["root"]

    try:
        comp = comp_core.add_component(root, obj_id, comp_type, props)
        _save()
        entry = log_event("component.add", f"Added {comp_type}", {"objectId": obj_id})
        return jsonify({"ok": True, "component": comp, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/component/remove", methods=["POST"])
def api_component_remove():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    obj_id = body.get("objectId")
    comp_type = body.get("type")
    root = STATE["project_data"]["scene"]["root"]

    try:
        comp_core.remove_component(root, obj_id, comp_type)
        _save()
        entry = log_event("component.remove", f"Removed {comp_type}")
        return jsonify({"ok": True, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ── API: Scripts ──────────────────────────────────────────────────────

@app.route("/api/script/create", methods=["POST"])
def api_script_create():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    name = body.get("name", "NewScript")
    template = body.get("template", "blank")
    language = body.get("language", "javascript")

    try:
        result = script_core.create_script(
            STATE["project_data"], STATE["project_dir"],
            name, template, language=language,
        )
        _save()
        entry = log_event("script.create", f"Created '{name}' ({language})", result)
        return jsonify({"ok": True, "script": result, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


@app.route("/api/script/templates")
def api_script_templates():
    return jsonify({"templates": list(script_core.SCRIPT_TEMPLATES.keys())})


# ── API: Materials ────────────────────────────────────────────────────

@app.route("/api/material/types")
def api_material_types():
    return jsonify({"types": MATERIAL_TYPES})


@app.route("/api/material/create", methods=["POST"])
def api_material_create():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    body = request.json
    name = body.get("name", "New Material")
    mat_type = body.get("type", "Default")
    props = body.get("properties")

    try:
        result = mat_core.create_material(STATE["project_data"], name, mat_type, props)
        _save()
        entry = log_event("material.create", f"Created {mat_type} material '{name}'", result)
        return jsonify({"ok": True, "material": result, "event": entry})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 400


# ── API: Lens ─────────────────────────────────────────────────────────

@app.route("/api/lens/validate", methods=["POST"])
def api_lens_validate():
    if not STATE["project_data"]:
        return jsonify({"error": "No project loaded"}), 400

    result = lens_core.validate_project(STATE["project_data"])
    entry = log_event(
        "lens.validate",
        "Valid" if result["valid"] else f"{len(result['errors'])} errors",
        result,
    )
    return jsonify({"ok": True, "validation": result, "event": entry})


@app.route("/api/lens/build", methods=["POST"])
def api_lens_build():
    if not STATE["project_data"] or not STATE["project_path"]:
        return jsonify({"error": "No project loaded"}), 400

    output_dir = Path(STATE["project_dir"]) / "builds"
    output_dir.mkdir(exist_ok=True)
    output_path = str(output_dir / "lens_build.json")

    result = lens_core.build_lens(STATE["project_path"], output_path)
    entry = log_event("lens.build", "Built" if result.get("success") else "Failed", result)
    return jsonify({"ok": result.get("success", False), "build": result, "event": entry})


# ── Helpers ───────────────────────────────────────────────────────────

def _save():
    """Persist current project data to disk."""
    if STATE["project_path"] and STATE["project_data"]:
        proj_core.save_project(STATE["project_path"], STATE["project_data"])


if __name__ == "__main__":
    print("\n  🔮 LS-CLI Live Dashboard")
    print("  http://localhost:5199\n")
    app.run(host="0.0.0.0", port=5199, debug=False)
