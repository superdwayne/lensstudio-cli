"""Bridge client — sends commands to Lens Studio plugin via file-based IPC.

Protocol:
  1. CLI writes cmd-{uuid}.json atomically (write to .tmp, then rename)
  2. CLI polls for resp-{uuid}.json with exponential backoff
  3. Plugin heartbeat checked via heartbeat.json age
"""

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from ..exceptions import BridgeNotRunningError, BridgeTimeoutError
from ..utils.logging import get_logger
from .protocol import BridgeCommand, BridgeResponse

logger = get_logger(__name__)

# Singleton instance
_client: Optional["BridgeClient"] = None


def get_bridge_client() -> "BridgeClient":
    """Get or create the singleton BridgeClient."""
    global _client  # noqa: PLW0603
    if _client is None:
        _client = BridgeClient()
    return _client


class BridgeClient:
    """File-based IPC client for the Lens Studio bridge plugin."""

    HEARTBEAT_MAX_AGE = 5.0  # seconds before heartbeat is stale
    DEFAULT_TIMEOUT = 10.0  # default command timeout
    POLL_INITIAL = 0.1  # initial poll interval
    POLL_MAX = 1.0  # max poll interval
    POLL_MULTIPLIER = 1.5  # exponential backoff factor

    def __init__(self, bridge_dir: Optional[str] = None):
        from ..utils.config import get_bridge_dir

        self._bridge_dir = Path(bridge_dir) if bridge_dir else get_bridge_dir()
        self._commands_dir = self._bridge_dir / "commands"
        self._responses_dir = self._bridge_dir / "responses"
        self._heartbeat_path = self._bridge_dir / "heartbeat.json"
        self._ensure_dirs()

    def _ensure_dirs(self):
        self._commands_dir.mkdir(parents=True, exist_ok=True)
        self._responses_dir.mkdir(parents=True, exist_ok=True)

    @property
    def bridge_dir(self) -> Path:
        return self._bridge_dir

    def is_alive(self) -> bool:
        """Check if the bridge plugin is running via heartbeat age."""
        if not self._heartbeat_path.exists():
            return False
        try:
            age = time.time() - self._heartbeat_path.stat().st_mtime
            return age < self.HEARTBEAT_MAX_AGE
        except OSError:
            return False

    def get_heartbeat(self) -> Optional[dict]:
        """Read the heartbeat data (includes plugin version, capabilities)."""
        if not self._heartbeat_path.exists():
            return None
        try:
            with open(self._heartbeat_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    def get_capabilities(self) -> dict:
        """Read plugin capabilities from heartbeat."""
        heartbeat = self.get_heartbeat()
        if not heartbeat:
            return {}
        return heartbeat.get("capabilities", {})

    def has_capability(self, name: str) -> bool:
        """Check if the plugin reports a specific capability.

        Args:
            name: Capability name (e.g. 'fs.writeFile', 'Editor.Model.IModel')
        """
        return self.get_capabilities().get(name, False)

    def send(
        self,
        domain: str,
        action: str,
        params: Optional[dict] = None,
        timeout: Optional[float] = None,
    ) -> BridgeResponse:
        """Send a command and wait for the response.

        Args:
            domain: Command domain (scene, asset, component, etc.)
            action: Action name within the domain
            params: Optional parameters dict
            timeout: Max seconds to wait for response

        Returns:
            BridgeResponse from the plugin

        Raises:
            BridgeNotRunningError: If the plugin heartbeat is stale
            BridgeTimeoutError: If no response within timeout
        """
        if not self.is_alive():
            raise BridgeNotRunningError(
                "Bridge plugin is not running. Open Lens Studio or run 'ls-cli bridge install'."
            )

        timeout = timeout or self.DEFAULT_TIMEOUT
        cmd = BridgeCommand(
            domain=domain,
            action=action,
            params=params or {},
        )

        self._write_command(cmd)
        return self._poll_response(cmd.id, timeout)

    def send_command(self, cmd: BridgeCommand, timeout: Optional[float] = None) -> BridgeResponse:
        """Send a pre-built BridgeCommand and wait for response."""
        if not self.is_alive():
            raise BridgeNotRunningError(
                "Bridge plugin is not running. Open Lens Studio or run 'ls-cli bridge install'."
            )
        timeout = timeout or self.DEFAULT_TIMEOUT
        self._write_command(cmd)
        return self._poll_response(cmd.id, timeout)

    def _write_command(self, cmd: BridgeCommand):
        """Atomically write a command file and update the pending manifest.

        The LS plugin cannot list directories, so we write a pending.json
        manifest that tells it which command IDs to process.
        """
        target = self._commands_dir / f"cmd-{cmd.id}.json"
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._commands_dir),
            prefix=".cmd-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(cmd.to_dict(), f, indent=2)
            os.rename(tmp_path, str(target))
            logger.debug("Wrote command %s -> %s", cmd.id, target)
        except Exception:
            # Clean up tmp on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        # Update pending.json manifest so the plugin knows about this command
        self._update_pending_manifest(cmd.id)

    def _update_pending_manifest(self, command_id: str):
        """Append a command ID to pending.json (the plugin reads this instead of listing the directory)."""
        manifest_path = self._commands_dir / "pending.json"
        pending: list[str] = []

        # Read existing manifest if present
        if manifest_path.exists():
            try:
                with open(manifest_path) as f:
                    pending = json.load(f)
                if not isinstance(pending, list):
                    pending = []
            except (json.JSONDecodeError, OSError):
                pending = []

        pending.append(command_id)

        # Write atomically
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._commands_dir),
            prefix=".pending-",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(pending, f)
            os.rename(tmp_path, str(manifest_path))
            logger.debug("Updated pending manifest with %s (%d total)", command_id, len(pending))
        except Exception:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

    def _poll_response(self, command_id: str, timeout: float) -> BridgeResponse:
        """Poll for a response file with exponential backoff."""
        resp_path = self._responses_dir / f"resp-{command_id}.json"
        deadline = time.time() + timeout
        interval = self.POLL_INITIAL

        while time.time() < deadline:
            if resp_path.exists():
                try:
                    with open(resp_path) as f:
                        data = json.load(f)
                    # Clean up response file
                    try:
                        resp_path.unlink()
                    except OSError:
                        pass
                    logger.debug("Got response for %s", command_id)
                    return BridgeResponse.from_dict(data)
                except (json.JSONDecodeError, KeyError) as e:
                    logger.warning("Malformed response for %s: %s", command_id, e)

            time.sleep(interval)
            interval = min(interval * self.POLL_MULTIPLIER, self.POLL_MAX)

        raise BridgeTimeoutError(
            f"No response from bridge plugin within {timeout}s for command {command_id}"
        )

    def cleanup_stale(self, max_age: float = 300.0) -> dict[str, Any]:
        """Remove command/response files older than max_age seconds."""
        removed = {"commands": 0, "responses": 0}
        now = time.time()

        for d, key in [(self._commands_dir, "commands"), (self._responses_dir, "responses")]:
            if not d.exists():
                continue
            for f in d.iterdir():
                if f.suffix == ".json" and (now - f.stat().st_mtime) > max_age:
                    try:
                        f.unlink()
                        removed[key] += 1
                    except OSError:
                        pass

        return removed
