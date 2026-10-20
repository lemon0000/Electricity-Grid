"""Fail-closed separation between development and formal execution hosts."""

from __future__ import annotations

import os
import socket
from collections.abc import Mapping


def execution_host_status(
    execution: Mapping[str, object],
) -> dict[str, object]:
    """Return machine-role evidence without authorizing a run."""

    hostname = socket.gethostname()
    forbidden = execution.get("forbidden_hostnames")
    if (
        not isinstance(forbidden, list)
        or any(not isinstance(item, str) or not item for item in forbidden)
    ):
        raise ValueError("execution.forbidden_hostnames must be a string list")
    required_value = execution.get("required_environment_value")
    if not isinstance(required_value, str) or not required_value:
        raise ValueError("execution.required_environment_value must be explicit")
    observed_value = os.environ.get("RQ2_EXECUTION_MACHINE")
    return {
        "hostname": hostname,
        "hostname_allowed": hostname not in forbidden,
        "required_environment_variable": "RQ2_EXECUTION_MACHINE",
        "required_environment_value": required_value,
        "observed_environment_value": observed_value,
        "environment_authorized": observed_value == required_value,
    }


def require_execution_host(execution: Mapping[str, object]) -> None:
    """Reject formal execution on a development host or without opt-in."""

    status = execution_host_status(execution)
    if not status["hostname_allowed"]:
        raise RuntimeError(
            f"formal execution is forbidden on development host "
            f"{status['hostname']}"
        )
    if not status["environment_authorized"]:
        raise RuntimeError(
            "formal execution requires RQ2_EXECUTION_MACHINE="
            f"{status['required_environment_value']}"
        )
