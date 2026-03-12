"""CLI commands for component management."""

import json as json_lib

import click

from ..core import project as proj_core
from ..core import component as comp_core
from ..utils.formatter import success, error, render_table, render_detail


def _load_scene(ctx):
    path = ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project <path>.")
    data = proj_core.load_project(path)
    root = data.get("scene", {}).get("root", {})
    return data, root, path


@click.group("component")
def component_group():
    """Component management on scene objects."""
    pass


@component_group.command("add")
@click.option("--to", "object_id", required=True, help="Scene object ID")
@click.option("-t", "--type", "comp_type", required=True, help="Component type (e.g. MeshVisual, Image, Text)")
@click.option("-p", "--properties", default=None, help="JSON properties string")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def component_add(ctx, object_id, comp_type, properties, json_mode):
    """Add a component to a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        props = json_lib.loads(properties) if properties else None
        result = comp_core.add_component(root, object_id, comp_type, props)
        proj_core.save_project(path, data)
        success(
            f"Added {comp_type} to {object_id}",
            json_mode=json_mode,
            data=result,
        )
    except json_lib.JSONDecodeError:
        error("Invalid JSON in --properties", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@component_group.command("remove")
@click.option("--from", "object_id", required=True, help="Scene object ID")
@click.option("-t", "--type", "comp_type", required=True, help="Component type to remove")
@click.option("-i", "--index", default=0, type=int, help="Component index (if multiple of same type)")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def component_remove(ctx, object_id, comp_type, index, json_mode):
    """Remove a component from a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        comp_core.remove_component(root, object_id, comp_type, index)
        proj_core.save_project(path, data)
        success(f"Removed {comp_type} from {object_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@component_group.command("list")
@click.argument("object_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def component_list(ctx, object_id, json_mode):
    """List all components on a scene object."""
    try:
        data, root, path = _load_scene(ctx)
        components = comp_core.list_components(root, object_id)

        if not components:
            success("No components found", json_mode=json_mode, data={"components": []})
            return

        rows = []
        for i, c in enumerate(components):
            comp_type = c.get("type", "?")
            # Summarize key properties
            props = {k: v for k, v in c.items() if k != "type"}
            props_str = ", ".join(f"{k}={v}" for k, v in list(props.items())[:3])
            rows.append([str(i), comp_type, props_str or "-"])

        render_table(
            "Components",
            ["#", "Type", "Properties"],
            rows,
            json_mode=json_mode,
            json_key="components",
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@component_group.command("configure")
@click.option("--on", "object_id", required=True, help="Scene object ID")
@click.option("-t", "--type", "comp_type", required=True, help="Component type")
@click.option("-p", "--properties", required=True, help="JSON properties to set")
@click.option("-i", "--index", default=0, type=int, help="Component index")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def component_configure(ctx, object_id, comp_type, properties, index, json_mode):
    """Configure properties on an existing component."""
    try:
        data, root, path = _load_scene(ctx)
        props = json_lib.loads(properties)
        result = comp_core.configure_component(root, object_id, comp_type, props, index)
        proj_core.save_project(path, data)
        success(
            f"Configured {comp_type} on {object_id}",
            json_mode=json_mode,
            data=result,
        )
    except json_lib.JSONDecodeError:
        error("Invalid JSON in --properties", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@component_group.command("list-types")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def component_list_types(json_mode):
    """List all available component types."""
    types = comp_core.list_component_types()
    rows = [[t["type"], t["description"]] for t in types]
    render_table(
        "Component Types",
        ["Type", "Description"],
        rows,
        json_mode=json_mode,
        json_key="types",
    )
