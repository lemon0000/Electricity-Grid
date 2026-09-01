"""Closed activation-transport v4 candidate.

This module is reviewable infrastructure only.  Its production entry points are
irreversibly closed.  A future executable route must be a new versioned
controller/worker successor reviewed against this candidate's sealed outer.
"""

from __future__ import annotations

import ctypes
import dataclasses
import hashlib
import inspect
import json
import os
import secrets
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v4.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_activation_transport_v4.OUTER.SHA256SUMS.json"
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v4"
WORKER_MODULE = "experiments.worker_rq2_public_grid_two_block_pilot_activation_transport_v4"
BLOCK = "holdout_s20260822_0008"
GIB = 1024**3
PRODUCTION_CLOSED = True


class TransportV4Rejected(RuntimeError):
    """A closed gate or fail-closed transport/resource check rejected an action."""


class ProductionClosed(TransportV4Rejected):
    """The candidate has no production execution authority."""


class ScientificBridgeRejected(TransportV4Rejected):
    """A non-executing scientific-bridge audit failed closed."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _load_config() -> dict[str, Any]:
    try:
        value = json.loads(CONFIG.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise TransportV4Rejected("v4 config unreadable") from exc
    if not isinstance(value, dict):
        raise TransportV4Rejected("v4 config malformed")
    gates = value.get("gates")
    if not isinstance(gates, dict) or any(
        gates.get(name) is not False
        for name in (
            "activation_v4_independent_review_passed",
            "execution_wrapper_present",
            "wrapper_independent_review_passed",
            "dispatch_authorization_present",
            "production_dispatch_permitted",
            "pilot_executed",
            "formal_execution_ready",
            "claim",
            "security_certified",
        )
    ):
        raise TransportV4Rejected("v4 closed gates drifted")
    return value


def _process_creation_time_ns(pid: int) -> int:
    if os.name != "nt":
        try:
            return int((Path("/proc") / str(pid)).stat().st_ctime_ns)
        except OSError as exc:
            raise TransportV4Rejected("process creation time unavailable") from exc
    process_query_limited_information = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(
        process_query_limited_information, False, int(pid)
    )
    if not handle:
        raise TransportV4Rejected("process creation time unavailable")
    try:
        creation = ctypes.c_ulonglong()
        exit_time = ctypes.c_ulonglong()
        kernel = ctypes.c_ulonglong()
        user = ctypes.c_ulonglong()
        if not ctypes.windll.kernel32.GetProcessTimes(
            handle,
            ctypes.byref(creation),
            ctypes.byref(exit_time),
            ctypes.byref(kernel),
            ctypes.byref(user),
        ):
            raise TransportV4Rejected("process creation time unavailable")
        return int(creation.value) * 100
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def available_commit_bytes() -> int:
    """Return available host commit; any inability to observe is a hard reject."""
    if os.name == "nt":
        value = _MemoryStatusEx()
        value.dwLength = ctypes.sizeof(value)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(value)):
            raise TransportV4Rejected("available commit observation failed")
        return int(value.ullAvailPageFile)
    try:
        fields: dict[str, int] = {}
        for line in Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
            name, raw = line.split(":", 1)
            fields[name] = int(raw.strip().split()[0]) * 1024
        return fields["CommitLimit"] - fields["Committed_AS"]
    except (OSError, KeyError, ValueError) as exc:
        raise TransportV4Rejected("available commit observation failed") from exc


def preflight_available_commit(
    *,
    observe: Callable[[], int] = available_commit_bytes,
    child_limit_bytes: int = 8 * GIB,
    reserve_bytes: int = 2 * GIB,
) -> int:
    try:
        observed = observe()
    except Exception as exc:
        raise TransportV4Rejected("available commit observation failed") from exc
    if type(observed) is not int or observed < 0:
        raise TransportV4Rejected("available commit observation malformed")
    if observed < child_limit_bytes + reserve_bytes:
        raise TransportV4Rejected("available commit below child cap plus reserve")
    return observed


class _ProcessMemoryCountersEx(ctypes.Structure):
    _fields_ = [
        ("cb", ctypes.c_ulong),
        ("PageFaultCount", ctypes.c_ulong),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


def sample_child_private_commit_bytes(pid: int, create_time_ns: int) -> int:
    if _process_creation_time_ns(pid) != create_time_ns:
        raise TransportV4Rejected("private-commit sample observed PID reuse")
    if os.name != "nt":
        try:
            for line in (Path("/proc") / str(pid) / "status").read_text().splitlines():
                if line.startswith("VmData:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError) as exc:
            raise TransportV4Rejected("private-commit sample failed") from exc
        raise TransportV4Rejected("private-commit sample missing")
    query = 0x1000
    handle = ctypes.windll.kernel32.OpenProcess(query, False, int(pid))
    if not handle:
        raise TransportV4Rejected("private-commit sample failed")
    try:
        counters = _ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        if not ctypes.windll.psapi.GetProcessMemoryInfo(
            handle, ctypes.byref(counters), counters.cb
        ):
            raise TransportV4Rejected("private-commit sample failed")
        return int(counters.PrivateUsage)
    finally:
        ctypes.windll.kernel32.CloseHandle(handle)


def terminate_exact_owned_child(
    process: subprocess.Popen[Any], *, expected_pid: int, expected_create_time_ns: int
) -> None:
    if process.pid != expected_pid:
        raise TransportV4Rejected("refusing to terminate non-owned PID")
    if process.poll() is not None:
        return
    if _process_creation_time_ns(process.pid) != expected_create_time_ns:
        raise TransportV4Rejected("refusing to terminate PID-reused child")
    process.terminate()
    try:
        process.wait(timeout=1.0)
    except subprocess.TimeoutExpired:
        process.kill()
        try:
            process.wait(timeout=1.0)
        except subprocess.TimeoutExpired as exc:
            raise TransportV4Rejected("owned child survived terminate/kill") from exc


@dataclasses.dataclass(frozen=True, slots=True)
class ResourceOutcome:
    status: str
    honest_incomplete: bool
    mathematical_infeasibility_inferred: bool
    maximum_private_commit_bytes: int
    samples: int


def monitor_owned_child_resources(
    process: subprocess.Popen[Any],
    *,
    expected_pid: int,
    expected_create_time_ns: int,
    sample: Callable[[int, int], int] = sample_child_private_commit_bytes,
    clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    sample_interval_seconds: float = 5.0,
    private_commit_limit_bytes: int = 8 * GIB,
    deadline: float | None = None,
) -> ResourceOutcome:
    if sample_interval_seconds <= 0 or private_commit_limit_bytes <= 0:
        raise TransportV4Rejected("resource monitor contract malformed")
    maximum = 0
    samples = 0
    while process.poll() is None:
        if deadline is not None and clock() >= deadline:
            terminate_exact_owned_child(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome("timeout", True, False, maximum, samples)
        try:
            observed = sample(expected_pid, expected_create_time_ns)
        except Exception:  # noqa: BLE001 - every sampler failure must fail closed
            terminate_exact_owned_child(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome("sampling_error", True, False, maximum, samples)
        if type(observed) is not int or observed < 0:
            terminate_exact_owned_child(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome("sampling_error", True, False, maximum, samples)
        samples += 1
        maximum = max(maximum, observed)
        if observed > private_commit_limit_bytes:
            terminate_exact_owned_child(
                process,
                expected_pid=expected_pid,
                expected_create_time_ns=expected_create_time_ns,
            )
            return ResourceOutcome("resource_stop", True, False, maximum, samples)
        sleep(sample_interval_seconds)
    return ResourceOutcome("child_exited", False, False, maximum, samples)


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewOutcome:
    status: str
    accepted: bool
    execution_index: int
    block_id: str
    mathematical_infeasibility_inferred: bool
    counters: Mapping[str, int]


def _run_review_transport(timeout_seconds: float) -> ReviewOutcome:
    """Use the sealed v3 review-only child; it cannot append accepted evidence."""
    from experiments import (
        run_rq2_public_grid_two_block_pilot_activation_transport_v3 as v3,
    )

    outcome = v3.ControllerSession().run_review_preloader_boundary(
        timeout_seconds=timeout_seconds
    )
    if outcome.accepted or outcome.status != "NON_ACCEPTED_PRELOADER_BOUNDARY":
        raise TransportV4Rejected("review-only predecessor returned accepting evidence")
    return ReviewOutcome(
        status=outcome.status,
        accepted=False,
        execution_index=1,
        block_id=BLOCK,
        mathematical_infeasibility_inferred=False,
        counters=MappingProxyType(dict(outcome.counters)),
    )


class ControllerSession:
    """Closed candidate controller with atomic review-attempt consumption."""

    __slots__ = ("_active_index", "_attempted", "_lock")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempted: set[int] = set()
        self._active_index: int | None = None

    @property
    def attempted_indices(self) -> frozenset[int]:
        with self._lock:
            return frozenset(self._attempted)

    def run_review_preloader_boundary(
        self, *, timeout_seconds: float = 10.0
    ) -> ReviewOutcome:
        config = _load_config()
        resources = config["resource_contract"]
        preflight_available_commit(
            child_limit_bytes=int(float(resources["child_private_commit_limit_gib"]) * GIB),
            reserve_bytes=int(float(resources["minimum_host_commit_reserve_gib"]) * GIB),
        )
        with self._lock:
            if self._active_index is not None:
                raise TransportV4Rejected("single-active-attempt contract violated")
            if 1 in self._attempted:
                raise TransportV4Rejected("attempt index was already consumed; retry forbidden")
            self._attempted.add(1)
            self._active_index = 1
        try:
            return _run_review_transport(timeout_seconds)
        except TransportV4Rejected:
            raise
        except Exception as exc:
            raise TransportV4Rejected("review attempt failed honestly") from exc
        finally:
            with self._lock:
                self._active_index = None

    def run_two_block_pilot(self, *_args: object, **_kwargs: object) -> None:
        """Permanent closed gate; rejects before config, pipe, Popen or imports."""
        raise ProductionClosed(
            "v4 candidate cannot execute; a new reviewed wrapper successor is required"
        )

    def run_production_block(self, *_args: object, **_kwargs: object) -> None:
        """Permanent closed gate; rejects before config, pipe, Popen or imports."""
        raise ProductionClosed(
            "v4 candidate cannot execute; a new reviewed wrapper successor is required"
        )


def _verify_manifest(path: Path, expected_sha256: str) -> None:
    if _sha256(path) != expected_sha256:
        raise ScientificBridgeRejected("scientific dependency manifest drifted")
    try:
        manifest = json.loads(path.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise ScientificBridgeRejected("scientific dependency manifest malformed") from exc
    files = manifest.get("files", manifest)
    if not isinstance(files, dict) or not files:
        raise ScientificBridgeRejected("scientific dependency manifest inventory missing")
    for relative, digest in files.items():
        member = ROOT / str(relative)
        if not isinstance(digest, str) or _sha256(member) != digest:
            raise ScientificBridgeRejected("scientific dependency member drifted")


def _verify_provenance_members(path: Path) -> None:
    """Verify every path/sha256 pair in the frozen provenance YAML without PyYAML."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise ScientificBridgeRejected("provenance contract unreadable") from exc
    observed = 0
    pending_path: str | None = None
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("path:"):
            pending_path = stripped.split(":", 1)[1].strip().strip("\"'")
        elif stripped.startswith("sha256:") and pending_path is not None:
            digest = stripped.split(":", 1)[1].strip().strip("\"'")
            if _sha256(ROOT / pending_path) != digest:
                raise ScientificBridgeRejected("transitive scientific dependency drifted")
            observed += 1
            pending_path = None
    if observed < 2 or pending_path is not None:
        raise ScientificBridgeRejected("provenance contract did not yield a closed inventory")


def verify_scientific_dependency_closure() -> dict[str, str]:
    config = _load_config()
    closure = config["scientific_bridge"]["dependency_closure"]
    for binding in closure["manifests"]:
        _verify_manifest(ROOT / binding["path"], binding["sha256"])
    provenance = ROOT / closure["provenance_contract"]["path"]
    if _sha256(provenance) != closure["provenance_contract"]["sha256"]:
        raise ScientificBridgeRejected("provenance contract drifted")
    _verify_provenance_members(provenance)
    from experiments import (
        run_rq2_public_grid_two_block_pilot_candidate_v4 as candidate,
    )

    signatures = {
        "stage": str(inspect.signature(candidate._stage_context)),
        "load": str(inspect.signature(candidate._load_worker_data)),
        "process": str(inspect.signature(candidate.recovery.v4._process_block)),
        "validate": str(inspect.signature(candidate.recovery._validate_scientific_payload)),
    }
    if signatures != closure["expected_signatures"]:
        raise ScientificBridgeRejected("sealed scientific function signature drifted")
    return signatures


@dataclasses.dataclass(frozen=True, slots=True)
class RegisteredZeroSolverSeam:
    stage_context: Callable[[], Mapping[str, Any]]
    load_worker_data: Callable[[Mapping[str, Any]], Any]
    process_block: Callable[..., Mapping[str, Any]]
    validate_payload: Callable[..., Mapping[str, Any]]
    certificate_inventory: Mapping[str, Any]
    registration_nonce: str


_SEAM_REGISTRY: set[str] = set()


def register_zero_solver_seam(
    *,
    stage_context: Callable[[], Mapping[str, Any]],
    load_worker_data: Callable[[Mapping[str, Any]], Any],
    process_block: Callable[..., Mapping[str, Any]],
    validate_payload: Callable[..., Mapping[str, Any]],
    certificate_inventory: Mapping[str, Any],
) -> RegisteredZeroSolverSeam:
    nonce = secrets.token_hex(32)
    _SEAM_REGISTRY.add(nonce)
    return RegisteredZeroSolverSeam(
        stage_context,
        load_worker_data,
        process_block,
        validate_payload,
        MappingProxyType(dict(certificate_inventory)),
        nonce,
    )


@dataclasses.dataclass(frozen=True, slots=True)
class ScientificBridgeAudit:
    status: str
    accepted: bool
    counters: Mapping[str, int]
    mathematical_infeasibility_inferred: bool


def _certificate_inventory(payload: Mapping[str, Any]) -> dict[str, Any]:
    outcomes = payload.get("outcomes")
    if not isinstance(outcomes, list):
        raise ScientificBridgeRejected("scientific outcomes missing")
    rows: list[dict[str, Any]] = []
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            raise ScientificBridgeRejected("scientific outcome malformed")
        rows.append(
            {
                "primary_certificate": outcome.get("primary_certificate"),
                "zero_dc_confirmation_certificate": outcome.get(
                    "zero_dc_confirmation_certificate"
                ),
            }
        )
    return {"baseline_audit": payload.get("baseline_audit"), "hourly": rows}


def audit_registered_zero_solver_seam(
    seam: RegisteredZeroSolverSeam, *, block_id: str = BLOCK
) -> ScientificBridgeAudit:
    if type(seam) is not RegisteredZeroSolverSeam or seam.registration_nonce not in _SEAM_REGISTRY:
        raise ScientificBridgeRejected("zero-solver seam is not registered")
    _SEAM_REGISTRY.remove(seam.registration_nonce)
    verify_scientific_dependency_closure()
    counters = {"stage_calls": 0, "loader_calls": 0, "process_calls": 0, "validator_calls": 0, "solver_calls": 0, "writes": 0}
    try:
        context = seam.stage_context()
        counters["stage_calls"] += 1
        block = context["blocks"][block_id]
        data = seam.load_worker_data(context)
        counters["loader_calls"] += 1
        payload = seam.process_block(
            data,
            block,
            dc_bus=int(context["config"]["model"]["dc_bus"]),
            dc_demand_mw=float(context["config"]["model"]["dc_reference_demand_mw"]),
            solver=context["config"]["solver"],
        )
        counters["process_calls"] += 1
        validated = seam.validate_payload(
            payload,
            block_id=block_id,
            expected_block=block,
            config=context["config"],
        )
        counters["validator_calls"] += 1
        if validated.get("all_hours_resolved") is not True:
            raise ScientificBridgeRejected("unresolved scientific payload")
        outcomes = validated.get("outcomes")
        if not isinstance(outcomes, list) or not outcomes or any(
            not isinstance(row, dict) or row.get("resolved_for_pipeline") is not True
            for row in outcomes
        ):
            raise ScientificBridgeRejected("unresolved scientific outcome")
        if _certificate_inventory(validated) != dict(seam.certificate_inventory):
            raise ScientificBridgeRejected("certificate inventory mismatch")
    except ScientificBridgeRejected:
        raise
    except Exception as exc:
        raise ScientificBridgeRejected("scientific bridge exception is honest incomplete") from exc
    return ScientificBridgeAudit(
        "ZERO_SOLVER_SEAM_VALIDATED",
        False,
        MappingProxyType(counters),
        False,
    )


def future_wrapper_contract() -> Mapping[str, Any]:
    """Frozen interface description only; it grants no executable capability."""
    return MappingProxyType(dict(_load_config()["future_wrapper_successor_contract"]))


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments != ["--validate-only"]:
        raise ProductionClosed("v4 runner only supports --validate-only")
    config = _load_config()
    print(
        json.dumps(
            {
                "validation_passed": True,
                "status": config["status"],
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
