"""Lens Studio application controller — launch, locate, and interact with the running app."""

import platform
import subprocess
import time
from typing import Any, Optional

from ..exceptions import GUIAutomationError, LensStudioNotFoundError
from ..utils.config import find_lens_studio
from ..utils.logging import get_logger
from .accessibility import AXElement
from .selectors import AX_ROLES, MENU_PATHS

logger = get_logger(__name__)


class LensStudioApp:
    """Controller for the Lens Studio macOS application."""

    BUNDLE_ID = "com.snap.lens-studio"
    APP_NAME = "Lens Studio"

    def __init__(self):
        self._pid: Optional[int] = None
        self._app_element: Optional[AXElement] = None

    @property
    def pid(self) -> Optional[int]:
        """Get the PID of the running Lens Studio process."""
        if self._pid and self._is_pid_alive(self._pid):
            return self._pid
        self._pid = self._find_pid()
        return self._pid

    @property
    def is_running(self) -> bool:
        return self.pid is not None

    @property
    def app_element(self) -> AXElement:
        """Get the AXUIElement for the Lens Studio application."""
        pid = self.pid
        if not pid:
            raise GUIAutomationError("Lens Studio is not running")
        if not self._app_element or self._pid != pid:
            self._app_element = AXElement.from_pid(pid)
        return self._app_element

    def launch(self, project_path: Optional[str] = None, wait: float = 10.0) -> bool:
        """Launch Lens Studio, optionally opening a project.

        Args:
            project_path: Optional path to .esproj/.lsproj to open
            wait: Seconds to wait for launch

        Returns:
            True if successfully launched
        """
        if platform.system() != "Darwin":
            raise GUIAutomationError("Launch is only supported on macOS")

        if self.is_running:
            logger.info("Lens Studio already running (PID %s)", self._pid)
            if project_path:
                self._open_via_subprocess(project_path)
            return True

        exe = find_lens_studio()
        if not exe:
            raise LensStudioNotFoundError("Lens Studio executable not found")

        args = ["open", "-a", "Lens Studio"]
        if project_path:
            args.extend(["--args", project_path])

        subprocess.Popen(args, start_new_session=True)  # noqa: S603

        # Wait for launch
        deadline = time.time() + wait
        while time.time() < deadline:
            if self.is_running:
                logger.info("Lens Studio launched (PID %s)", self._pid)
                # Give UI time to render
                time.sleep(2.0)
                return True
            time.sleep(0.5)

        raise GUIAutomationError(f"Lens Studio did not start within {wait}s")

    def activate(self):
        """Bring Lens Studio to the foreground."""
        if not self.is_running:
            raise GUIAutomationError("Lens Studio is not running")
        subprocess.run(  # noqa: S603, S607
            ["osascript", "-e", 'tell application "Lens Studio" to activate'],
            capture_output=True,
        )

    def click_menu(self, menu_key: str):
        """Click a menu item by its key from MENU_PATHS.

        Args:
            menu_key: Key in selectors.MENU_PATHS (e.g., 'file_open', 'build')
        """
        path = MENU_PATHS.get(menu_key)
        if not path:
            raise GUIAutomationError(f"Unknown menu key: {menu_key}")

        app = self.app_element
        menu_bar = app.find(role=AX_ROLES["menu_bar"])
        if not menu_bar:
            raise GUIAutomationError("Could not find menu bar")

        current = menu_bar
        for item_title in path:
            elem = current.find(title=item_title)
            if not elem:
                raise GUIAutomationError(f"Menu item not found: {item_title}")
            elem.press()
            # Wait briefly for submenu to appear
            time.sleep(0.3)
            current = elem

    def get_main_window(self) -> AXElement:
        """Get the main Lens Studio window."""
        windows = self.app_element.windows
        if not windows:
            raise GUIAutomationError("No Lens Studio windows found")
        return windows[0]

    def wait_for_window(self, title_contains: str, timeout: float = 15.0) -> AXElement:
        """Wait for a window or dialog with a title containing the given string."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            for w in self.app_element.windows:
                t = w.title
                if t and title_contains.lower() in t.lower():
                    return w
            time.sleep(0.5)

        raise GUIAutomationError(f"Window containing '{title_contains}' not found within {timeout}s")

    def _find_pid(self) -> Optional[int]:
        """Find Lens Studio PID using pgrep."""
        try:
            result = subprocess.run(  # noqa: S603, S607
                ["pgrep", "-f", "Lens Studio"],
                capture_output=True,
                text=True,
            )
            if result.returncode == 0:
                pids = result.stdout.strip().split("\n")
                if pids and pids[0]:
                    return int(pids[0])
        except (subprocess.SubprocessError, ValueError):
            pass
        return None

    def _is_pid_alive(self, pid: int) -> bool:
        """Check if a process is still running."""
        try:
            import signal

            os_kill = __import__("os").kill
            os_kill(pid, signal.SIG_DFL)
            return True
        except (OSError, ProcessLookupError):
            return False

    def _open_via_subprocess(self, project_path: str):
        """Open a project in an already-running Lens Studio."""
        exe = find_lens_studio()
        if exe:
            subprocess.Popen(  # noqa: S603
                [exe, project_path],
                start_new_session=True,
            )

    def get_status(self) -> dict[str, Any]:
        """Get the current status of Lens Studio."""
        return {
            "running": self.is_running,
            "pid": self.pid,
            "platform": platform.system(),
        }
