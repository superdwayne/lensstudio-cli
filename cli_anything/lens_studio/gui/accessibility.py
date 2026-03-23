"""macOS Accessibility API wrapper using PyObjC.

Provides AXElement for traversing and interacting with native app UIs.
Only available on macOS — imports are guarded.
"""

import platform
import time
from typing import Any, Optional

from ..exceptions import GUIAutomationError, GUIElementNotFoundError
from ..utils.logging import get_logger

logger = get_logger(__name__)

_MACOS = platform.system() == "Darwin"


def _require_macos():
    if not _MACOS:
        raise GUIAutomationError("GUI automation requires macOS")


def _get_ax_modules():
    """Lazily import PyObjC accessibility modules."""
    _require_macos()
    try:
        import ApplicationServices  # noqa: F811
        import Cocoa  # noqa: F811
        import Quartz  # noqa: F811

        return ApplicationServices, Cocoa, Quartz
    except ImportError as e:
        raise GUIAutomationError(
            "PyObjC not installed. Run: pip install 'cli-anything-lens-studio[gui]'"
        ) from e


class AXElement:
    """Wrapper around an AXUIElement for accessible UI interaction."""

    def __init__(self, ref):
        """Initialize with a raw AXUIElementRef."""
        self._ref = ref

    @classmethod
    def from_pid(cls, pid: int) -> "AXElement":
        """Create an AXElement for an application by PID."""
        ApplicationServices, _, _ = _get_ax_modules()
        ref = ApplicationServices.AXUIElementCreateApplication(pid)
        return cls(ref)

    @classmethod
    def system_wide(cls) -> "AXElement":
        """Create the system-wide AXUIElement."""
        ApplicationServices, _, _ = _get_ax_modules()
        ref = ApplicationServices.AXUIElementCreateSystemWide()
        return cls(ref)

    def attribute(self, name: str) -> Any:
        """Get a single AX attribute value."""
        ApplicationServices, _, _ = _get_ax_modules()
        err, value = ApplicationServices.AXUIElementCopyAttributeValue(
            self._ref, name, None
        )
        if err != 0:
            return None
        return value

    @property
    def role(self) -> Optional[str]:
        return self.attribute("AXRole")

    @property
    def title(self) -> Optional[str]:
        return self.attribute("AXTitle")

    @property
    def value(self) -> Any:
        return self.attribute("AXValue")

    @property
    def enabled(self) -> bool:
        val = self.attribute("AXEnabled")
        return bool(val) if val is not None else False

    @property
    def children(self) -> list["AXElement"]:
        kids = self.attribute("AXChildren")
        if not kids:
            return []
        return [AXElement(k) for k in kids]

    @property
    def windows(self) -> list["AXElement"]:
        wins = self.attribute("AXWindows")
        if not wins:
            return []
        return [AXElement(w) for w in wins]

    def find(self, role: Optional[str] = None, title: Optional[str] = None, depth: int = 5) -> Optional["AXElement"]:
        """Find the first descendant matching role and/or title."""
        return self._search(role, title, depth, find_all=False)

    def find_all(self, role: Optional[str] = None, title: Optional[str] = None, depth: int = 5) -> list["AXElement"]:
        """Find all descendants matching role and/or title."""
        results: list[AXElement] = []
        self._search(role, title, depth, find_all=True, results=results)
        return results

    def _search(self, role, title, depth, find_all=False, results=None):
        if depth <= 0:
            return None

        for child in self.children:
            match = True
            if role and child.role != role:
                match = False
            if title and child.title != title:
                match = False

            if match:
                if find_all:
                    results.append(child)
                else:
                    return child

            # Recurse
            result = child._search(role, title, depth - 1, find_all, results)
            if result and not find_all:
                return result

        return None

    def press(self):
        """Perform AXPress action (click a button or menu item)."""
        ApplicationServices, _, _ = _get_ax_modules()
        err = ApplicationServices.AXUIElementPerformAction(self._ref, "AXPress")
        if err != 0:
            raise GUIAutomationError(f"AXPress failed with error code {err}")

    def set_value(self, value: Any):
        """Set the AXValue attribute."""
        ApplicationServices, _, _ = _get_ax_modules()
        err = ApplicationServices.AXUIElementSetAttributeValue(
            self._ref, "AXValue", value
        )
        if err != 0:
            raise GUIAutomationError(f"Failed to set value, error code {err}")

    def wait_for(
        self,
        role: Optional[str] = None,
        title: Optional[str] = None,
        timeout: float = 10.0,
        poll: float = 0.5,
    ) -> "AXElement":
        """Wait for a descendant element to appear."""
        deadline = time.time() + timeout
        while time.time() < deadline:
            elem = self.find(role=role, title=title)
            if elem:
                return elem
            time.sleep(poll)

        raise GUIElementNotFoundError(
            f"Element (role={role}, title={title}) not found within {timeout}s"
        )

    def __repr__(self):
        return f"AXElement(role={self.role!r}, title={self.title!r})"
