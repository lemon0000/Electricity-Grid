"""Closed activation-transport v5 resource-monitor remediation.

All v4 execution gates remain literally closed.  This successor changes only
the reviewable resource-monitor primitive so that each 5-second sample enforces
both frozen recovery-v2 limits: child private commit and host commit reserve.
"""

from __future__ import annotations

import dataclasses
import json
import subprocess
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from types import MappingProxyType
from typing import Any

from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v4 as predecessor,
)

PRODUCTION_CLOSED = True
GIB = 1024**3
PRIVATE_COMMIT_LIMIT_BYTES = 8 * GIB
SYSTEM_COMMIT_RESERVE_BYTES = 2 * GIB
PREFLIGHT_AVAILABLE_COMMIT_BYTES = 10 * GIB
RESOURCE_SAMPLE_INTERVAL_SECONDS = 5.0

ProductionClosed = predecessor.ProductionClosed
ScientificBridgeRejected = predecessor.ScientificBridgeRejected
TransportV5Rejected = predecessor.TransportV4Rejected
RegisteredZeroSolverSeam = predecessor.RegisteredZeroSolverSeam
ScientificBridgeAudit = predecessor.ScientificBridgeAudit
register_zero_solver_seam = predecessor.register_zero_solver_seam
audit_registered_zero_solver_seam = predecessor.audit_registered_zero_solver_seam
verify_scientific_dependency_closure = predecessor.verify_scientific_dependency_closure
preflight_available_commit = predecessor.preflight_available_commit
available_commit_bytes = predecessor.available_commit_bytes
sample_child_private_commit_bytes = predecessor.sample_child_private_commit_bytes
terminate_exact_owned_child = predecessor.terminate_exact_owned_child


@dataclasses.dataclass(frozen=True, slots=True)
class ResourceSample:
    child_private_commit_bytes: int
    system_commit_available_bytes: int


@dataclasses.dataclass(frozen=True, slots=True)
class ResourceOutcome:
    status: str
    reason: str | None
    honest_incomplete: bool
    mathematical_infeasibility_inferred: bool
    maximum_private_commit_bytes: int
    minimum_system_commit_available_bytes: int | None
    samples: int


class ResourceOwnershipIndeterminate(TransportV5Rejected):
    honest_incomplete = True
    mathematical_infeasibility_inferred = False


def sample_resource_pair(pid: int, create_time_ns: int) -> ResourceSample:
    """Take both observations in one monitor iteration for the same live child."""
    private = sample_child_private_commit_bytes(pid, create_time_ns)
    available = available_commit_bytes()
    if type(private) is not int or private < 0:
        raise TransportV5Rejected("private-commit observation malformed")
    if type(available) is not int or available < 0:
        raise TransportV5Rejected("system-commit observation malformed")
    return ResourceSample(private, available)


def _stop_reason(sample: ResourceSample) -> str | None:
    private_reached = sample.child_private_commit_bytes >= PRIVATE_COMMIT_LIMIT_BYTES
    reserve_reached = sample.system_commit_available_bytes <= SYSTEM_COMMIT_RESERVE_BYTES
    if private_reached and reserve_reached:
        return "private_and_system_commit_limits_reached"
    if private_reached:
        return "private_commit_limit_reached"
    if reserve_reached:
        return "system_commit_reserve_reached"
    return None


def _terminate_or_indeterminate(
    process: subprocess.Popen[Any], *, expected_pid: int, expected_create_time_ns: int
) -> None:
    try:
        terminate_exact_owned_child(
            process,
            expected_pid=expected_pid,
            expected_create_time_ns=expected_create_time_ns,
        )
    except Exception as exc:
        raise ResourceOwnershipIndeterminate(
            "owned-child identity drifted; termination was not attempted or accepted"
        ) from exc


def monitor_owned_child_resources(
    process: subprocess.Popen[Any],
    *,
    expected_pid: int,
    expected_create_time_ns: int,
    sample: Callable[[int, int], ResourceSample] = sample_resource_pair,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    sample_interval_seconds: float = RESOURCE_SAMPLE_INTERVAL_SECONDS,
    watchdog_deadline: float | None = None,
) -> ResourceOutcome:
    """Monitor the exact owned child; no stop outcome implies infeasibility."""
    if sample_interval_seconds <= 0:
        raise TransportV5Rejected("resource sample interval must be positive")
    if process.pid != expected_pid:
        raise ResourceOwnershipIndeterminate("monitor target is not the expected PID")
    samples = 0
    maximum_private = 0
    minimum_available: int | None = None
    while process.poll() is None:
        if watchdog_deadline is not None and clock() >= watchdog_deadline:
            _terminate_or_indeterminate(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome(
                "timeout",
                "external_watchdog_reached",
                True,
                False,
                maximum_private,
                minimum_available,
                samples,
            )
        try:
            observed = sample(expected_pid, expected_create_time_ns)
        except Exception:  # noqa: BLE001 - any sampling failure is fail closed
            _terminate_or_indeterminate(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome(
                "sampling_error",
                "resource_sample_failed",
                True,
                False,
                maximum_private,
                minimum_available,
                samples,
            )
        if type(observed) is not ResourceSample:
            _terminate_or_indeterminate(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome(
                "sampling_error",
                "resource_sample_malformed",
                True,
                False,
                maximum_private,
                minimum_available,
                samples,
            )
        private = observed.child_private_commit_bytes
        available = observed.system_commit_available_bytes
        if (
            type(private) is not int
            or private < 0
            or type(available) is not int
            or available < 0
        ):
            _terminate_or_indeterminate(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome(
                "sampling_error",
                "resource_sample_malformed",
                True,
                False,
                maximum_private,
                minimum_available,
                samples,
            )
        samples += 1
        maximum_private = max(maximum_private, private)
        minimum_available = (
            available if minimum_available is None else min(minimum_available, available)
        )
        reason = _stop_reason(observed)
        if reason is not None:
            _terminate_or_indeterminate(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome(
                "resource_stop",
                reason,
                True,
                False,
                maximum_private,
                minimum_available,
                samples,
            )
        sleep(sample_interval_seconds)
    return ResourceOutcome(
        "child_exited",
        None,
        False,
        False,
        maximum_private,
        minimum_available,
        samples,
    )


class ControllerSession(predecessor.ControllerSession):
    """v4 hard-close/RLock controller plus the frozen v5 resource primitive."""

    resource_monitor = staticmethod(monitor_owned_child_resources)


def future_wrapper_contract() -> Mapping[str, Any]:
    contract = dict(predecessor.future_wrapper_contract())
    contract.update(
        {
            "must_use_resource_monitor_v5": True,
            "resource_sample_interval_seconds": RESOURCE_SAMPLE_INTERVAL_SECONDS,
            "child_private_commit_stop_is_greater_equal_8_gib": True,
            "system_commit_available_stop_is_less_equal_2_gib": True,
            "each_sample_observes_private_and_system_commit": True,
            "preflight_10_gib_does_not_replace_runtime_reserve": True,
            "must_preserve_atomic_no_retry_v4": True,
            "must_preserve_scientific_dependency_closure_v4": True,
            "all_resource_timeout_sampling_and_science_failures_are_honest_incomplete": True,
            "mathematical_infeasibility_inferred_from_failure": False,
            "successor_tests_and_independent_review_must_cover_every_field": True,
        }
    )
    return MappingProxyType(contract)


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["--validate-only"]:
        raise ProductionClosed(
            "v5 candidate is closed; a new independently reviewed successor is required"
        )
    print(
        json.dumps(
            {
                "validation_passed": True,
                "status": "activation_transport_v5_closed_candidate_pending_independent_review",
                "production_closed": True,
                "execution_ready": False,
                "production_workers": 0,
                "loader_calls": 0,
                "solver_calls": 0,
                "result_writes": 0,
                "formal_writes": 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
