"""Bridge protocol definitions for CLI <-> Lens Studio IPC.

Communication uses JSON files in ~/.ls-cli/bridge/:
  - commands/cmd-{uuid}.json  (CLI writes, plugin reads)
  - responses/resp-{uuid}.json (plugin writes, CLI reads)
  - heartbeat.json (plugin writes every 2s)
"""

import enum
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional


class CommandDomain(str, enum.Enum):
    """Domains grouping related bridge commands."""

    SCENE = "scene"
    ASSET = "asset"
    COMPONENT = "component"
    SCRIPT = "script"
    MATERIAL = "material"
    QUERY = "query"
    PREFAB = "prefab"


@dataclass
class BridgeCommand:
    """A command sent from CLI to the Lens Studio bridge plugin."""

    domain: str
    action: str
    params: dict = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BridgeCommand":
        return cls(
            domain=data["domain"],
            action=data["action"],
            params=data.get("params", {}),
            id=data.get("id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class BridgeResponse:
    """A response from the Lens Studio bridge plugin."""

    command_id: str
    success: bool
    data: Optional[dict] = None
    error: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "BridgeResponse":
        return cls(
            command_id=data["command_id"],
            success=data["success"],
            data=data.get("data"),
            error=data.get("error"),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        )
