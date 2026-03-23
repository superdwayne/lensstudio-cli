"""High-level GUI actions for Lens Studio automation.

These functions orchestrate multi-step GUI interactions like building,
exporting, and opening projects through the macOS Accessibility API.
"""

import time
from typing import Any, Optional

from ..exceptions import GUIAutomationError
from ..utils.logging import get_logger
from .lens_studio_app import LensStudioApp
from .selectors import AX_ROLES, DIALOG_BUTTONS

logger = get_logger(__name__)

# Module-level app instance
_app: Optional[LensStudioApp] = None


def _get_app() -> LensStudioApp:
    global _app  # noqa: PLW0603
    if _app is None:
        _app = LensStudioApp()
    return _app


def open_project_gui(project_path: str) -> dict[str, Any]:
    """Open a project in Lens Studio via GUI.

    Launches Lens Studio if not running, then opens the project.
    """
    app = _get_app()
    try:
        app.launch(project_path=project_path)
        return {
            "success": True,
            "project": project_path,
            "pid": app.pid,
            "method": "gui",
        }
    except Exception as e:
        return {"success": False, "error": str(e), "method": "gui"}


def build_lens_gui(output_path: Optional[str] = None, target: str = "snapchat") -> dict[str, Any]:
    """Build a lens using the GUI Build menu.

    Steps:
    1. Ensure Lens Studio is running and activated
    2. Click File > Build Lens (or the build menu item)
    3. Wait for build dialog
    4. Set output path if provided
    5. Click Build button
    6. Wait for completion
    """
    app = _get_app()
    if not app.is_running:
        return {"success": False, "error": "Lens Studio is not running", "method": "gui"}

    try:
        app.activate()
        time.sleep(0.5)

        # Trigger build via menu
        app.click_menu("build")

        # Wait for build dialog/sheet
        time.sleep(1.0)
        window = app.get_main_window()

        # Look for the build sheet/dialog
        dialog = window.find(role=AX_ROLES["sheet"]) or window.find(role=AX_ROLES["dialog"])

        if dialog and output_path:
            # Try to set output path in text field
            text_field = dialog.find(role=AX_ROLES["text_field"])
            if text_field:
                text_field.set_value(output_path)

        # Click the build/export button
        if dialog:
            build_btn = dialog.find(role=AX_ROLES["button"], title=DIALOG_BUTTONS["build"])
            if not build_btn:
                build_btn = dialog.find(role=AX_ROLES["button"], title=DIALOG_BUTTONS["export"])
            if build_btn:
                build_btn.press()
            else:
                logger.warning("Could not find Build button in dialog")
        else:
            logger.warning("No build dialog appeared after menu click")

        # Wait for build to complete (look for success indicator or dialog close)
        time.sleep(3.0)

        return {
            "success": True,
            "output": output_path,
            "target": target,
            "method": "gui",
            "note": "Build triggered via GUI — verify output manually",
        }
    except GUIAutomationError as e:
        return {"success": False, "error": str(e), "method": "gui"}


def export_lens_gui(output_path: Optional[str] = None) -> dict[str, Any]:
    """Export a lens using File > Export Lens... menu."""
    app = _get_app()
    if not app.is_running:
        return {"success": False, "error": "Lens Studio is not running", "method": "gui"}

    try:
        app.activate()
        time.sleep(0.5)

        app.click_menu("file_export")
        time.sleep(1.0)

        window = app.get_main_window()
        dialog = window.find(role=AX_ROLES["sheet"]) or window.find(role=AX_ROLES["dialog"])

        if dialog and output_path:
            text_field = dialog.find(role=AX_ROLES["text_field"])
            if text_field:
                text_field.set_value(output_path)

        if dialog:
            export_btn = dialog.find(role=AX_ROLES["button"], title=DIALOG_BUTTONS["export"])
            if not export_btn:
                export_btn = dialog.find(role=AX_ROLES["button"], title=DIALOG_BUTTONS["save"])
            if export_btn:
                export_btn.press()

        time.sleep(2.0)

        return {
            "success": True,
            "output": output_path,
            "method": "gui",
        }
    except GUIAutomationError as e:
        return {"success": False, "error": str(e), "method": "gui"}


def start_preview_gui(device: str = "simulator") -> dict[str, Any]:
    """Start preview via Preview menu."""
    app = _get_app()
    if not app.is_running:
        return {"success": False, "error": "Lens Studio is not running", "method": "gui"}

    try:
        app.activate()
        time.sleep(0.3)
        app.click_menu("preview_start")

        return {"success": True, "device": device, "method": "gui"}
    except GUIAutomationError as e:
        return {"success": False, "error": str(e), "method": "gui"}


def get_gui_status() -> dict[str, Any]:
    """Check GUI automation availability and Lens Studio status."""
    app = _get_app()
    import platform

    is_macos = platform.system() == "Darwin"

    pyobjc_available = False
    if is_macos:
        try:
            import ApplicationServices  # noqa: F401

            pyobjc_available = True
        except ImportError:
            pass

    return {
        "macos": is_macos,
        "pyobjc_installed": pyobjc_available,
        "lens_studio_running": app.is_running if is_macos else False,
        "lens_studio_pid": app.pid if is_macos and app.is_running else None,
    }
