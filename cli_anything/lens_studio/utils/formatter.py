"""Output formatting utilities for Lens Studio CLI."""

import json
import sys
from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.tree import Tree

console = Console()
error_console = Console(stderr=True)


def success(message: str, json_mode: bool = False, data: Optional[Dict] = None):
    """Print a success message or JSON output."""
    if json_mode:
        output = {"status": "success", "message": message}
        if data:
            output["data"] = data
        click_echo_json(output)
    else:
        console.print(f"[green]✓[/green] {message}")


def error(message: str, json_mode: bool = False, data: Optional[Dict] = None):
    """Print an error message or JSON output."""
    if json_mode:
        output = {"status": "error", "message": message}
        if data:
            output["data"] = data
        click_echo_json(output)
        sys.exit(1)
    else:
        error_console.print(f"[red]✗[/red] {message}")
        sys.exit(1)


def warning(message: str, json_mode: bool = False):
    """Print a warning message."""
    if json_mode:
        return  # Warnings are suppressed in JSON mode
    console.print(f"[yellow]⚠[/yellow] {message}")


def info(message: str, json_mode: bool = False):
    """Print an info message."""
    if json_mode:
        return  # Info messages are suppressed in JSON mode
    console.print(f"[blue]ℹ[/blue] {message}")


def click_echo_json(data: Any):
    """Output JSON to stdout."""
    print(json.dumps(data, indent=2, default=str))


def render_table(
    title: str,
    columns: List[str],
    rows: List[List[str]],
    json_mode: bool = False,
    json_key: str = "items",
):
    """Render a table or JSON array."""
    if json_mode:
        items = []
        for row in rows:
            item = {}
            for i, col in enumerate(columns):
                key = col.lower().replace(" ", "_")
                item[key] = row[i] if i < len(row) else ""
            items.append(item)
        click_echo_json({json_key: items, "count": len(items)})
    else:
        table = Table(title=title, show_lines=False)
        for col in columns:
            table.add_column(col, style="cyan")
        for row in rows:
            table.add_row(*row)
        console.print(table)


def render_tree(title: str, items: List[Dict], json_mode: bool = False):
    """Render a tree structure or JSON."""
    if json_mode:
        click_echo_json({"tree": items})
        return

    tree = Tree(f"[bold]{title}[/bold]")
    _build_tree(tree, items)
    console.print(tree)


def _build_tree(parent: Tree, items: List[Dict]):
    """Recursively build a Rich tree."""
    for item in items:
        label = item.get("name", "unnamed")
        node_type = item.get("type", "")
        if node_type:
            label = f"{label} [dim]({node_type})[/dim]"
        branch = parent.add(label)
        children = item.get("children", [])
        if children:
            _build_tree(branch, children)


def render_detail(title: str, fields: Dict[str, Any], json_mode: bool = False):
    """Render a detail panel or JSON object."""
    if json_mode:
        click_echo_json(fields)
        return

    lines = []
    for key, value in fields.items():
        lines.append(f"[bold]{key}:[/bold] {value}")
    panel = Panel("\n".join(lines), title=title, border_style="blue")
    console.print(panel)
