"""Input validation and sanitization for Lens Studio CLI."""

import re
from pathlib import Path
from typing import Optional

from ..exceptions import InvalidProjectNameError, ValidationError

_MAX_PROJECT_NAME_LENGTH = 64
_ALLOWED_NAME_RE = re.compile(r"^[A-Za-z0-9 _-]+$")
_DANGEROUS_PATTERNS = ("..", "~", "\x00")


def sanitize_project_name(name: str) -> str:
    """Validate and sanitize a project name.

    Rejects empty strings, path traversal characters (../ ..\\ ~ and null
    bytes), and names exceeding 64 characters.  Only alphanumeric characters,
    hyphens, underscores, and spaces are allowed.

    Returns the stripped name on success.

    Raises:
        InvalidProjectNameError: If the name is invalid.
    """
    if not isinstance(name, str) or not name.strip():
        raise InvalidProjectNameError("Project name must be a non-empty string.")

    name = name.strip()

    # Reject path traversal / dangerous characters
    for pattern in _DANGEROUS_PATTERNS:
        if pattern in name:
            raise InvalidProjectNameError(
                f"Project name contains forbidden characters: {pattern!r}"
            )

    if len(name) > _MAX_PROJECT_NAME_LENGTH:
        raise InvalidProjectNameError(
            f"Project name exceeds {_MAX_PROJECT_NAME_LENGTH} characters."
        )

    if not _ALLOWED_NAME_RE.match(name):
        raise InvalidProjectNameError(
            "Project name may only contain alphanumeric characters, "
            "hyphens, underscores, and spaces."
        )

    return name


def validate_project_path(path: str, projects_dir: Optional[Path] = None) -> Path:
    """Resolve a project path and guard against directory traversal.

    Resolves symlinks and ``..`` segments, then verifies the result lives
    inside *projects_dir* (when provided).

    Returns the resolved ``Path``.

    Raises:
        ValidationError: If the path escapes the allowed directory.
    """
    resolved = Path(path).resolve()

    if projects_dir is not None:
        projects_resolved = projects_dir.resolve()
        try:
            resolved.relative_to(projects_resolved)
        except ValueError:
            raise ValidationError(
                f"Path '{path}' resolves outside the projects directory."
            ) from None

    return resolved


def validate_object_name(name: str) -> str:
    """Sanitize a scene-object name.

    Strips leading/trailing whitespace, rejects empty names, null bytes,
    and path traversal sequences.

    Returns the cleaned name.

    Raises:
        ValidationError: If the name is invalid.
    """
    if not isinstance(name, str) or not name.strip():
        raise ValidationError("Object name must be a non-empty string.")

    name = name.strip()

    if "\x00" in name:
        raise ValidationError("Object name must not contain null bytes.")

    for pattern in ("..", "~"):
        if pattern in name:
            raise ValidationError(
                f"Object name contains forbidden sequence: {pattern!r}"
            )

    if len(name) > 128:
        raise ValidationError("Object name exceeds 128 characters.")

    return name
