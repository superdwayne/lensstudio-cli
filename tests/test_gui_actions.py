"""Tests for GUI automation layer — mocked since AX API requires macOS + Lens Studio."""

from unittest.mock import MagicMock, patch

from cli_anything.lens_studio.gui.selectors import (
    AX_ROLES,
    DIALOG_BUTTONS,
    MENU_PATHS,
    WINDOW_PATTERNS,
)


class TestSelectors:
    def test_menu_paths_has_required_keys(self):
        assert "file_open" in MENU_PATHS
        assert "build" in MENU_PATHS
        assert "preview_start" in MENU_PATHS
        assert "file_export" in MENU_PATHS

    def test_menu_paths_are_lists(self):
        for key, path in MENU_PATHS.items():
            assert isinstance(path, list), f"{key} should be a list"
            assert len(path) >= 2, f"{key} should have at least 2 items"

    def test_dialog_buttons(self):
        assert DIALOG_BUTTONS["ok"] == "OK"
        assert DIALOG_BUTTONS["cancel"] == "Cancel"
        assert DIALOG_BUTTONS["build"] == "Build"
        assert DIALOG_BUTTONS["export"] == "Export"

    def test_ax_roles(self):
        assert AX_ROLES["button"] == "AXButton"
        assert AX_ROLES["menu_bar"] == "AXMenuBar"
        assert AX_ROLES["window"] == "AXWindow"

    def test_window_patterns(self):
        assert "main" in WINDOW_PATTERNS
        assert "preview" in WINDOW_PATTERNS


class TestGUIStatusNoMacOS:
    """Test GUI status on any platform (with mocks)."""

    def test_get_gui_status_returns_dict(self):
        from cli_anything.lens_studio.gui.actions import get_gui_status

        status = get_gui_status()
        assert isinstance(status, dict)
        assert "macos" in status
        assert "pyobjc_installed" in status

    @patch("platform.system", return_value="Linux")
    def test_gui_status_non_macos(self, mock_sys):
        # Re-import to get fresh state
        from cli_anything.lens_studio.gui import actions

        # Reset the cached app instance
        actions._app = None
        status = actions.get_gui_status()
        assert status["lens_studio_running"] is False


class TestLensStudioApp:
    def test_app_init(self):
        from cli_anything.lens_studio.gui.lens_studio_app import LensStudioApp

        app = LensStudioApp()
        assert app._pid is None

    def test_get_status(self):
        from cli_anything.lens_studio.gui.lens_studio_app import LensStudioApp

        app = LensStudioApp()
        status = app.get_status()
        assert "running" in status
        assert "pid" in status
        assert "platform" in status

    @patch("subprocess.run")
    def test_find_pid_not_running(self, mock_run):
        from cli_anything.lens_studio.gui.lens_studio_app import LensStudioApp

        mock_run.return_value = MagicMock(returncode=1, stdout="")
        app = LensStudioApp()
        assert app._find_pid() is None


class TestOpenProjectGUI:
    @patch("cli_anything.lens_studio.gui.actions._get_app")
    def test_open_project_success(self, mock_get_app):
        from cli_anything.lens_studio.gui.actions import open_project_gui

        mock_app = MagicMock()
        mock_app.launch.return_value = True
        mock_app.pid = 12345
        mock_get_app.return_value = mock_app

        result = open_project_gui("/tmp/test.esproj")
        assert result["success"] is True
        assert result["method"] == "gui"
        mock_app.launch.assert_called_once_with(project_path="/tmp/test.esproj")

    @patch("cli_anything.lens_studio.gui.actions._get_app")
    def test_open_project_failure(self, mock_get_app):
        from cli_anything.lens_studio.gui.actions import open_project_gui

        mock_app = MagicMock()
        mock_app.launch.side_effect = Exception("Not found")
        mock_get_app.return_value = mock_app

        result = open_project_gui("/tmp/test.esproj")
        assert result["success"] is False
        assert "Not found" in result["error"]


class TestBuildLensGUI:
    @patch("cli_anything.lens_studio.gui.actions._get_app")
    def test_build_not_running(self, mock_get_app):
        from cli_anything.lens_studio.gui.actions import build_lens_gui

        mock_app = MagicMock()
        mock_app.is_running = False
        mock_get_app.return_value = mock_app

        result = build_lens_gui()
        assert result["success"] is False
        assert "not running" in result["error"]
