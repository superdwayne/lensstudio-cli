"""CLI commands for asset management."""

import click

from ..core import project as proj_core
from ..core import asset as asset_core
from ..utils.config import ASSET_TYPES
from ..utils.formatter import success, error, render_table, render_detail


def _load_project(ctx):
    """Load project data and return (data, project_dir, project_path)."""
    path = ctx.obj.get("project_path")
    if not path:
        error("No project specified. Use --project <path>.")
    from pathlib import Path
    data = proj_core.load_project(path)
    project_dir = str(Path(path).parent)
    return data, project_dir, path


@click.group("asset")
def asset_group():
    """Asset management (textures, meshes, audio, etc.)."""
    pass


@asset_group.command("import")
@click.argument("source_path")
@click.option("-n", "--name", default=None, help="Asset name (default: filename)")
@click.option("-t", "--type", "asset_type", default=None, help="Asset type override")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def asset_import(ctx, source_path, name, asset_type, json_mode):
    """Import an asset file into the project."""
    try:
        data, project_dir, path = _load_project(ctx)
        result = asset_core.import_asset(data, project_dir, source_path, name, asset_type)
        proj_core.save_project(path, data)
        success(
            f"Imported {result['type']}: {result['name']} ({result['fileSize']} bytes)",
            json_mode=json_mode,
            data=result,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@asset_group.command("list")
@click.option("-t", "--type", "asset_type", default=None, help="Filter by asset type")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def asset_list(ctx, asset_type, json_mode):
    """List all assets in the project."""
    try:
        data, project_dir, path = _load_project(ctx)
        assets = asset_core.list_assets(data, asset_type)

        if not assets:
            success("No assets found", json_mode=json_mode, data={"assets": []})
            return

        rows = []
        for a in assets:
            size = a.get("fileSize", 0)
            size_str = f"{size / 1024:.1f}KB" if size > 1024 else f"{size}B"
            rows.append([
                a.get("name", "?"),
                a.get("type", "?"),
                a.get("fileName", "?"),
                size_str,
                a.get("id", "?")[:8],
            ])

        render_table(
            "Project Assets",
            ["Name", "Type", "File", "Size", "ID"],
            rows,
            json_mode=json_mode,
            json_key="assets",
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@asset_group.command("info")
@click.argument("asset_id")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def asset_info(ctx, asset_id, json_mode):
    """Show detailed asset information."""
    try:
        data, project_dir, path = _load_project(ctx)
        asset = asset_core.get_asset(data, asset_id)
        if not asset:
            asset = asset_core.get_asset_by_name(data, asset_id)
        if not asset:
            error(f"Asset not found: {asset_id}", json_mode=json_mode)

        render_detail(
            f"Asset: {asset['name']}",
            asset,
            json_mode=json_mode,
        )
    except Exception as e:
        error(str(e), json_mode=json_mode)


@asset_group.command("remove")
@click.argument("asset_id")
@click.option("--keep-file", is_flag=True, help="Keep the file on disk")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
@click.pass_context
def asset_remove(ctx, asset_id, keep_file, json_mode):
    """Remove an asset from the project."""
    try:
        data, project_dir, path = _load_project(ctx)
        asset_core.remove_asset(data, project_dir, asset_id, delete_file=not keep_file)
        proj_core.save_project(path, data)
        success(f"Removed asset: {asset_id}", json_mode=json_mode)
    except Exception as e:
        error(str(e), json_mode=json_mode)


@asset_group.command("types")
@click.option("--json", "json_mode", is_flag=True, help="Output JSON")
def asset_types(json_mode):
    """List supported asset types and extensions."""
    rows = []
    for type_name, extensions in ASSET_TYPES.items():
        rows.append([type_name, ", ".join(extensions)])

    render_table(
        "Supported Asset Types",
        ["Type", "Extensions"],
        rows,
        json_mode=json_mode,
        json_key="types",
    )
