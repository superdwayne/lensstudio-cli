"""CLI commands for scene graph operations."""

import json as json_lib

import click

from ..core import project as proj_core
from ..core import scene as scene_core
from ..utils.formatter import success, error, render_table, render_tree


def _load_scene(ctx):
    """Load project and return (project_data, scene_root, project_path)."""
    path = ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project <path>.")
    data = proj_core.load_project(path)
    root = data.get("scene", {}).get("root", {})
    return data, root, path


@click.group("scene")
def scene_group():
    """Scene graph operations."""
    pass


@scene_group.command("list")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_list(ctx, json_mode):
    """List all scene objects."""
    try:
        data, root, path = _load_scene(ctx)
        items = scene_core.flatten_scene(root)
        rows = []
        for item in items:
            indent = "  " * item["depth"]
            name = f"{indent}{item['name']}"
            comps = ", ".join(item["components"]) if item["components"] else "-"
            enabled = "Yes" if item["enabled"] else "No"
            rows.append([name, item["id"][:8], comps, enabled])

        render_table(
            "Scene Objects",
            ["Name", "ID", "Components", "Enabled"],
            rows,
            json_mode=json_mode,
            json_key="objects",
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("tree")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_tree(ctx, json_mode):
    """Show scene hierarchy as a tree."""
    try:
        data, root, path = _load_scene(ctx)
        tree_data = scene_core.scene_to_tree(root)
        render_tree("Scene Hierarchy", [tree_data], json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("add")
@click.option("-n", "--name", required=True, help="Object name")
@click.option("-p", "--parent", default=None, help="Parent object ID or name")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_add(ctx, name, parent, json_mode):
    """Add a new scene object."""
    try:
        data, root, path = _load_scene(ctx)

        parent_id = None
        if parent:
            obj = scene_core.find_object(root, parent)
            if not obj:
                obj = scene_core.find_object_by_name(root, parent)
            if obj:
                parent_id = obj["id"]
            else:
                error(f"Parent not found: {parent}", json_mode=json_mode)

        new_obj = scene_core.add_object(root, name, parent_id=parent_id)
        proj_core.save_project(path, data)
        success(
            f"Added scene object: {name}",
            json_mode=json_mode,
            data={"id": new_obj["id"], "name": name, "parent": parent_id},
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("remove")
@click.argument("object_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_remove(ctx, object_id, json_mode):
    """Remove a scene object by ID."""
    try:
        data, root, path = _load_scene(ctx)
        obj = scene_core.find_object(root, object_id)
        if not obj:
            obj = scene_core.find_object_by_name(root, object_id)
            if obj:
                object_id = obj["id"]
        scene_core.remove_object(root, object_id)
        proj_core.save_project(path, data)
        success(f"Removed scene object: {object_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("rename")
@click.argument("object_id")
@click.option("-n", "--name", required=True, help="New name")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_rename(ctx, object_id, name, json_mode):
    """Rename a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        scene_core.rename_object(root, object_id, name)
        proj_core.save_project(path, data)
        success(f"Renamed to: {name}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("transform")
@click.argument("object_id")
@click.option("--position", "-pos", nargs=3, type=float, default=None, help="Position x y z")
@click.option("--rotation", "-rot", nargs=3, type=float, default=None, help="Rotation x y z (degrees)")
@click.option("--scale", "-s", nargs=3, type=float, default=None, help="Scale x y z")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_transform(ctx, object_id, position, rotation, scale, json_mode):
    """Set transform on a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        pos = list(position) if position else None
        rot = list(rotation) if rotation else None
        scl = list(scale) if scale else None
        obj = scene_core.set_transform(root, object_id, position=pos, rotation=rot, scale=scl)
        proj_core.save_project(path, data)
        success(
            f"Updated transform on: {obj['name']}",
            json_mode=json_mode,
            data=obj.get("transform"),
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("enable")
@click.argument("object_id")
@click.option("--off", is_flag=True, help="Disable instead of enable")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_enable(ctx, object_id, off, json_mode):
    """Enable or disable a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        enabled = not off
        scene_core.set_enabled(root, object_id, enabled)
        proj_core.save_project(path, data)
        state = "Disabled" if off else "Enabled"
        success(f"{state} object: {object_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("reparent")
@click.argument("object_id")
@click.option("--to", "new_parent", required=True, help="New parent object ID")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_reparent(ctx, object_id, new_parent, json_mode):
    """Move a scene object to a new parent."""
    try:
        data, root, path = _load_scene(ctx)
        scene_core.reparent(root, object_id, new_parent)
        proj_core.save_project(path, data)
        success(f"Reparented {object_id} → {new_parent}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@scene_group.command("duplicate")
@click.argument("object_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def scene_duplicate(ctx, object_id, json_mode):
    """Duplicate a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        clone = scene_core.duplicate_object(root, object_id)
        proj_core.save_project(path, data)
        success(
            f"Duplicated: {clone['name']}",
            json_mode=json_mode,
            data={"id": clone["id"], "name": clone["name"]},
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)
