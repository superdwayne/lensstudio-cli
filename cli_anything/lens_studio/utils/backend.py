"""Lens Studio backend wrapper — delegates to real Lens Studio application."""

import json
import os
import platform
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .config import find_lens_studio


class LensStudioBackend:
    """Wrapper around the Lens Studio application for headless operations."""

    def __init__(self, executable: Optional[str] = None):
        self._executable = executable or find_lens_studio()
        self._version: Optional[str] = None

    @property
    def executable(self) -> Optional[str]:
        return self._executable

    @property
    def available(self) -> bool:
        return self._executable is not None and os.path.exists(self._executable)

    def require(self):
        """Raise if Lens Studio is not available."""
        if not self.available:
            raise RuntimeError(
                "Lens Studio not found. Install from https://lensstudio.snapchat.com/ "
                "or set LENS_STUDIO_PATH environment variable."
            )

    def version(self) -> str:
        """Get Lens Studio version string."""
        if self._version:
            return self._version
        self.require()
        try:
            result = self._run(["--version"], timeout=10)
            self._version = result.stdout.strip()
            return self._version
        except Exception:
            return "unknown"

    def open_project(self, project_path: str) -> subprocess.CompletedProcess:
        """Open a project in Lens Studio GUI."""
        self.require()
        return self._run([project_path], timeout=5, detach=True)

    def build_lens(
        self,
        project_path: str,
        output_path: str,
        target: str = "snapchat",
    ) -> subprocess.CompletedProcess:
        """Build/export a lens from a project file."""
        self.require()
        args = [
            "-p", project_path,
            "--build",
            "-o", output_path,
        ]
        if target:
            args.extend(["--target", target])
        return self._run(args, timeout=120)

    def preview(self, project_path: str, device: str = "simulator") -> subprocess.CompletedProcess:
        """Launch preview for a project."""
        self.require()
        args = ["-p", project_path, "--preview"]
        if device != "simulator":
            args.extend(["--device", device])
        return self._run(args, timeout=30, detach=True)

    def validate_project(self, project_path: str) -> Dict[str, Any]:
        """Validate a project for submission readiness."""
        self.require()
        try:
            result = self._run(
                ["-p", project_path, "--validate", "--json"],
                timeout=60,
            )
            return json.loads(result.stdout)
        except (json.JSONDecodeError, subprocess.CalledProcessError):
            return {"valid": False, "errors": ["Validation failed"]}

    def _run(
        self,
        args: List[str],
        timeout: Optional[int] = None,
        detach: bool = False,
    ) -> subprocess.CompletedProcess:
        """Run Lens Studio with given arguments."""
        cmd = [self._executable] + args

        if detach:
            if platform.system() == "Darwin":
                subprocess.Popen(cmd, start_new_session=True)
            else:
                subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            return subprocess.CompletedProcess(cmd, 0, "", "")

        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )


# Singleton backend instance
_backend: Optional[LensStudioBackend] = None


def get_backend() -> LensStudioBackend:
    """Get the global Lens Studio backend instance."""
    global _backend
    if _backend is None:
        _backend = LensStudioBackend()
    return _backend
