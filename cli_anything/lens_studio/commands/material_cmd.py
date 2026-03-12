"""CLI commands for material operations."""

import click

from ..core import project as proj_core
from ..core import material as mat_core
from ..utils.config import MATERIAL_TYPES
from ..utils.formatter import success, error, render_table, render_detail


def _load_project(ctx):
    path = ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project <path>.")
    data = proj_core.load_project(path)
    return data, path


@click.group("material")
def material_group():
    """Material operations (create, edit, assign)."""
    pass


@material_group.command("create")
@click.option("-n", "--name", required=True, help="Material name")
@click.option("-t", "--type", "material_type", default="Default", help="Material type (Default, Unlit, PBR, FacePaint, etc.)")
@click.option("--color", nargs=4, type=float, default=None, help="Base color RGBA (0-1)")
@click.option("--metallic", type=float, default=None, help="Metallic value (PBR)")
@click.option("--roughness", type=float, default=None, help="Roughness value (PBR)")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def material_create(ctx, name, material_type, color, metallic, roughness, json_mode):
    """Create a new material."""
    try:
        data, path = _load_project(ctx)
        props = {}
        if color:
            props["baseColor"] = list(color)
        if metallic is not None:
            props["metallic"] = metallic
        if roughness is not None:
            props["roughness"] = roughness

        result = mat_core.create_material(data, name, material_type, props or None)
        proj_core.save_project(path, data)
        success(
            f"Created {material_type} material: {name}",
            json_mode=json_mode,
            data=result,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@material_group.command("list")
@click.option("-t", "--type", "material_type", default=None, help="Filter by material type")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def material_list(ctx, material_type, json_mode):
    """List all materials in the project."""
    try:
        data, path = _load_project(ctx)
        materials = mat_core.list_materials(data, material_type)

        if not materials:
            success("No materials found", json_mode=json_mode, data={"materials": []})
            return

        rows = []
        for m in materials:
            color = m.get("properties", {}).get("baseColor", [])
            color_str = f"({', '.join(f'{c:.1f}' for c in color)})" if color else "-"
            rows.append([
                m.get("name", "?"),
                m.get("type", "?"),
                m.get("blendMode", "?"),
                color_str,
                m.get("id", "?")[:8],
            ])

        render_table(
            "Project Materials",
            ["Name", "Type", "Blend", "Color", "ID"],
            rows,
            json_mode=json_mode,
            json_key="materials",
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@material_group.command("info")
@click.argument("mat_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def material_info(ctx, mat_id, json_mode):
    """Show detailed material information."""
    try:
        data, path = _load_project(ctx)
        mat = mat_core.get_material(data, mat_id)
        if not mat:
            mat = mat_core.get_material_by_name(data, mat_id)
        if not mat:
            error(f"Material not found: {mat_id}", json_mode=json_mode)
        render_detail(f"Material: {mat['name']}", mat, json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@material_group.command("edit")
@click.argument("mat_id")
@click.option("--name", default=None, help="New name")
@click.option("--color", nargs=4, type=float, default=None, help="Base color RGBA")
@click.option("--metallic", type=float, default=None, help="Metallic value")
@click.option("--roughness", type=float, default=None, help="Roughness value")
@click.option("--blend-mode", default=None, help="Blend mode")
@click.option("--two-sided/--one-sided", default=None, help="Two-sided rendering")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def material_edit(ctx, mat_id, name, color, metallic, roughness, blend_mode, two_sided, json_mode):
    """Edit material properties."""
    try:
        data, path = _load_project(ctx)
        updates = {}
        if name:
            updates["name"] = name
        if blend_mode:
            updates["blendMode"] = blend_mode
        if two_sided is not None:
            updates["twoSided"] = two_sided

        props = {}
        if color:
            props["baseColor"] = list(color)
        if metallic is not None:
            props["metallic"] = metallic
        if roughness is not None:
            props["roughness"] = roughness
        if props:
            updates["properties"] = props

        result = mat_core.update_material(data, mat_id, updates)
        proj_core.save_project(path, data)
        success(f"Updated material: {result['name']}", json_mode=json_mode, data=result)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@material_group.command("remove")
@click.argument("mat_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def material_remove(ctx, mat_id, json_mode):
    """Remove a material."""
    try:
        data, path = _load_project(ctx)
        mat_core.remove_material(data, mat_id)
        proj_core.save_project(path, data)
        success(f"Removed material: {mat_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@material_group.command("assign")
@click.option("--material", "mat_id", required=True, help="Material ID or name")
@click.option("--to", "object_id", required=True, help="Scene object ID")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def material_assign(ctx, mat_id, object_id, json_mode):
    """Assign a material to a scene object."""
    try:
        data, path = _load_project(ctx)

        # Resolve by name
        mat = mat_core.get_material(data, mat_id)
        if not mat:
            mat = mat_core.get_material_by_name(data, mat_id)
        if not mat:
            error(f"Material not found: {mat_id}", json_mode=json_mode)

        result = mat_core.assign_material(data, object_id, mat["id"])
        proj_core.save_project(path, data)
        success(
            f"Assigned {mat['name']} → {object_id}",
            json_mode=json_mode,
            data=result,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@material_group.command("types")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def material_types(json_mode):
    """List available material types."""
    rows = [[t] for t in MATERIAL_TYPES]
    render_table(
        "Material Types",
        ["Type"],
        rows,
        json_mode=json_mode,
        json_key="types",
    )
