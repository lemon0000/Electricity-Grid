"""Canonical repository-relative paths for cross-platform manifests."""

from __future__ import annotations

import os
from pathlib import PurePosixPath, PureWindowsPath
from typing import Any


def canonical_repository_relative_path(raw: Any) -> str:
    """Return a validated POSIX path for a repository manifest key."""

    value = os.fspath(raw)
    if not isinstance(value, str) or not value:
        raise ValueError("repository path must be a nonempty string")
    windows_path = PureWindowsPath(value)
    normalized = value.replace("\\", "/")
    path = PurePosixPath(normalized)
    if windows_path.drive or path.is_absolute():
        raise ValueError("repository path must be relative")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError("repository path must not contain traversal")
    return path.as_posix()
