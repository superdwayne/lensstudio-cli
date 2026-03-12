"""Unified REPL interface for Lens Studio CLI — consistent interactive experience."""

import os
import sys
import shlex
from typing import Callable, Optional

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import HTML
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from cli_anything.lens_studio import __version__, __app_name__

console = Console()

BANNER = f"""\
[bold cyan]╔══════════════════════════════════════════════╗[/bold cyan]
[bold cyan]║[/bold cyan]  [bold white]cli-anything-lens-studio v{__version__}[/bold white]          [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]  [dim]Lens Studio CLI for AI Agents[/dim]              [bold cyan]║[/bold cyan]
[bold cyan]║[/bold cyan]  [dim]Type 'help' for commands, 'exit' to quit[/dim]  [bold cyan]║[/bold cyan]
[bold cyan]╚══════════════════════════════════════════════╝[/bold cyan]\
"""

GOODBYE = "[bold cyan]Goodbye![/bold cyan] 👋"

HELP_TEXT = """\
[bold]Available Commands:[/bold]
  [cyan]project[/cyan]    Manage Lens Studio projects (new, open, info, list)
  [cyan]scene[/cyan]      Scene graph operations (list, add, remove, transform)
  [cyan]asset[/cyan]      Asset management (import, list, remove, info)
  [cyan]script[/cyan]     Script management (add, remove, list, edit)
  [cyan]material[/cyan]   Material operations (create, list, edit, assign)
  [cyan]component[/cyan]  Component management (add, remove, list, configure)
  [cyan]lens[/cyan]       Build, export, and preview lenses
  [cyan]template[/cyan]   List and apply project templates

[bold]Global Options:[/bold]
  [cyan]--json[/cyan]     Output structured JSON for agent consumption
  [cyan]--project[/cyan]  Specify project file path

[bold]Session:[/bold]
  [cyan]help[/cyan]       Show this help message
  [cyan]status[/cyan]     Show current session status
  [cyan]undo[/cyan]       Undo last action
  [cyan]redo[/cyan]       Redo last undone action
  [cyan]exit[/cyan]       Exit REPL
"""


class ReplSession:
    """Interactive REPL session for Lens Studio CLI."""

    def __init__(
        self,
        invoke_command: Callable,
        project_path: Optional[str] = None,
    ):
        self._invoke = invoke_command
        self._project_path = project_path
        self._project_name: Optional[str] = None
        self._modified = False
        self._history_file = os.path.expanduser("~/.ls_cli_history")
        self._undo_stack: list = []
        self._redo_stack: list = []

    @property
    def prompt_text(self) -> str:
        """Build the prompt string."""
        base = "lens-studio"
        if self._project_name:
            mod = "*" if self._modified else ""
            return f"{base}[{self._project_name}]{mod}> "
        return f"{base}> "

    def set_project(self, name: str, path: str):
        """Set the active project."""
        self._project_name = name
        self._project_path = path
        self._modified = False

    def mark_modified(self):
        """Mark the current project as modified."""
        self._modified = True

    def run(self):
        """Start the REPL loop."""
        console.print(BANNER)

        session = PromptSession(
            history=FileHistory(self._history_file),
            auto_suggest=AutoSuggestFromHistory(),
        )

        while True:
            try:
                user_input = session.prompt(
                    HTML(f"<ansigreen>{self.prompt_text}</ansigreen>")
                )
            except (EOFError, KeyboardInterrupt):
                console.print(GOODBYE)
                break

            line = user_input.strip()
            if not line:
                continue

            if line.lower() in ("exit", "quit", "q"):
                console.print(GOODBYE)
                break

            if line.lower() == "help":
                console.print(HELP_TEXT)
                continue

            if line.lower() == "status":
                self._show_status()
                continue

            if line.lower() == "undo":
                self._undo()
                continue

            if line.lower() == "redo":
                self._redo()
                continue

            # Parse and invoke command
            try:
                args = shlex.split(line)
                if self._project_path and "--project" not in args:
                    args = ["--project", self._project_path] + args
                self._invoke(args)
            except SystemExit:
                pass  # Click raises SystemExit on errors; absorb in REPL
            except Exception as e:
                console.print(f"[red]Error:[/red] {e}")

    def _show_status(self):
        """Show current session status."""
        fields = {
            "Project": self._project_name or "(none)",
            "Path": self._project_path or "(none)",
            "Modified": "Yes" if self._modified else "No",
            "Undo Stack": str(len(self._undo_stack)),
        }
        lines = [f"[bold]{k}:[/bold] {v}" for k, v in fields.items()]
        console.print(Panel("\n".join(lines), title="Session Status", border_style="blue"))

    def _undo(self):
        """Undo last action."""
        if not self._undo_stack:
            console.print("[yellow]Nothing to undo[/yellow]")
            return
        action = self._undo_stack.pop()
        self._redo_stack.append(action)
        console.print(f"[green]↩[/green]  Undid: {action.get('description', 'action')}")

    def _redo(self):
        """Redo last undone action."""
        if not self._redo_stack:
            console.print("[yellow]Nothing to redo[/yellow]")
            return
        action = self._redo_stack.pop()
        self._undo_stack.append(action)
        console.print(f"[green]↪[/green]  Redid: {action.get('description', 'action')}")

    def push_undo(self, description: str, data: dict = None):
        """Push an action to the undo stack."""
        self._undo_stack.append({"description": description, "data": data or {}})
        self._redo_stack.clear()
        self.mark_modified()
