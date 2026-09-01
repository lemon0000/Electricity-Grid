"""Isolate Gurobi behaviour on one RQ2 grid-need normal-SCUC block.

This entry point is diagnostic only.  It imports the activated v4 runner's
normal-baseline path, writes to dedicated diagnostic roots, and verifies that
the formal checkpoint and output trees are byte-for-byte unchanged.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path

from experiments import run_rts_gmlc_public_grid_need_dispatch_v4 as v4
from src.grid import rts_gmlc_scuc_solver_successor as successor_solver
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_CONFIG = Path(
    "results/execution_configs/rq2_public_successor_v2/grid.yaml"
)
_DEFAULT_TABLE_ROOT = Path(
    "results/tables/rq2_grid_need_gurobi_0009_diagnostic_v1"
)
_DEFAULT_LOG_ROOT = Path(
    "results/logs/rq2_grid_need_gurobi_0009_diagnostic_v1"
)
_DEFAULT_BLOCKS = (
    "holdout_s20260822_0008",
    "holdout_s20260822_0009",
)
_GUROBI_PROBE_PROFILES: dict[str, dict[str, int]] = {
    "formal_default": {},
    "symmetry_aggressive": {"Symmetry": 2},
    "incumbent_focus": {"MIPFocus": 1},
    "bound_focus": {"MIPFocus": 3},
    "highs_route": {},
}
_PROGRESS_RE = re.compile(
    r"^\s*(?:[H*]\s*)?(?P<explored>\d+)\s+"
    r"(?P<unexplored>\d+)\s+.*?\s+"
    r"(?P<seconds>\d+(?:\.\d+)?)s\s*$"
)
_FINAL_NODES_RE = re.compile(
    r"Explored\s+(?P<nodes>\d+)\s+nodes\s+"
    r"\((?P<iterations>\d+)\s+simplex iterations\)\s+in\s+"
    r"(?P<seconds>\d+(?:\.\d+)?)\s+seconds"
)
_FINAL_CERTIFICATE_RE = re.compile(
    r"Best objective\s+(?P<objective>[-+0-9.eE]+),\s+"
    r"best bound\s+(?P<bound>[-+0-9.eE]+),\s+"
    r"gap\s+(?P<gap>[-+0-9.eE]+)%"
)
_HIGHS_PROGRESS_RE = re.compile(
    r"^\s*(?:[A-Za-z]\s+)?(?P<explored>\d+)\s+"
    r"(?P<unexplored>\d+)\s+.*?\s+"
    r"(?P<seconds>\d+(?:\.\d+)?)s\s*$"
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _atomic_write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _resolve(path: Path) -> Path:
    path = path if path.is_absolute() else _ROOT / path
    return path.resolve()


def _display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        displayed = resolved.relative_to(_ROOT)
    except ValueError:
        displayed = resolved
    return displayed.as_posix()


def _is_same_or_descendant(candidate: Path, parent: Path) -> bool:
    candidate = candidate.resolve()
    parent = parent.resolve()
    try:
        candidate.relative_to(parent)
    except ValueError:
        return False
    return True


def _ensure_diagnostic_roots_are_isolated(
    *,
    table_root: Path,
    log_root: Path,
    formal_checkpoint_root: Path,
    formal_output_root: Path,
) -> None:
    """Reject every diagnostic/formal directory containment relationship."""

    diagnostic_roots = (table_root.resolve(), log_root.resolve())
    formal_roots = (formal_checkpoint_root.resolve(), formal_output_root.resolve())
    for diagnostic in diagnostic_roots:
        for formal in formal_roots:
            if _is_same_or_descendant(diagnostic, formal) or _is_same_or_descendant(
                formal, diagnostic
            ):
                raise ValueError(
                    "diagnostic root overlaps a formal artifact directory"
                )
    if any(
        _is_same_or_descendant(left, right)
        for left, right in (
            (diagnostic_roots[0], diagnostic_roots[1]),
            (diagnostic_roots[1], diagnostic_roots[0]),
        )
    ):
        raise ValueError("diagnostic table and log roots must be disjoint")


def _ensure_worker_result_is_isolated(
    *,
    result_path: Path,
    formal_checkpoint_root: Path,
    formal_output_root: Path,
) -> None:
    result_path = result_path.resolve()
    result_parent = result_path.parent
    for formal in (formal_checkpoint_root.resolve(), formal_output_root.resolve()):
        if _is_same_or_descendant(result_path, formal) or _is_same_or_descendant(
            formal, result_parent
        ):
            raise ValueError("worker result path overlaps a formal artifact directory")
    if result_path.exists():
        raise FileExistsError("worker result already exists; refuse overwrite")


def _diagnostic_solver_payload(
    formal_solver: Mapping[str, object],
    *,
    time_limit_seconds: float,
    gurobi_probe_profile: str = "formal_default",
) -> dict[str, object]:
    """Copy the formal solver contract and add only diagnostic observability."""

    if formal_solver.get("name") != "gurobi":
        raise ValueError("this diagnostic requires the activated Gurobi solver")
    if not isinstance(time_limit_seconds, (int, float)) or isinstance(
        time_limit_seconds, bool
    ):
        raise TypeError("diagnostic time limit must be numeric")
    if not 0.0 < float(time_limit_seconds) <= 3600.0:
        raise ValueError("diagnostic time limit must be in (0, 3600] seconds")
    payload = {
        **formal_solver,
        "time_limit_seconds": float(time_limit_seconds),
        "tee": True,
    }
    if gurobi_probe_profile == "highs_route":
        payload.update(
            {
                "name": "highs",
                "expected_package_version": "1.15.1",
            }
        )
    return payload


def _gurobi_probe_options(profile: str) -> dict[str, int]:
    try:
        return dict(_GUROBI_PROBE_PROFILES[profile])
    except KeyError as error:
        raise ValueError(f"unknown Gurobi probe profile: {profile}") from error


def _install_gurobi_probe_profile(profile: str) -> dict[str, int]:
    extra_options = _gurobi_probe_options(profile)
    if not extra_options:
        return extra_options
    original_create_solver = successor_solver.create_solver

    def create_solver_with_probe(specification):
        solver, options = original_create_solver(specification)
        return solver, {**options, **extra_options}

    successor_solver.create_solver = create_solver_with_probe
    return extra_options


def _optional_float(raw: str) -> float | None:
    try:
        return float(raw)
    except ValueError:
        return None


def _parse_gurobi_log(text: str) -> dict[str, object]:
    """Extract progress-tree and final-certificate fields from a native log."""

    maximum_explored = 0
    maximum_unexplored = 0
    last_elapsed: float | None = None
    for line in text.splitlines():
        match = _PROGRESS_RE.match(line)
        if match is None:
            continue
        maximum_explored = max(maximum_explored, int(match.group("explored")))
        maximum_unexplored = max(
            maximum_unexplored,
            int(match.group("unexplored")),
        )
        last_elapsed = float(match.group("seconds"))

    final_nodes = None
    final_iterations = None
    final_elapsed = None
    for match in _FINAL_NODES_RE.finditer(text):
        final_nodes = int(match.group("nodes"))
        final_iterations = int(match.group("iterations"))
        final_elapsed = float(match.group("seconds"))

    final_objective = None
    final_bound = None
    final_gap_percent = None
    for match in _FINAL_CERTIFICATE_RE.finditer(text):
        final_objective = _optional_float(match.group("objective"))
        final_bound = _optional_float(match.group("bound"))
        final_gap_percent = _optional_float(match.group("gap"))

    return {
        "maximum_explored_nodes": maximum_explored,
        "maximum_unexplored_nodes": maximum_unexplored,
        "last_progress_elapsed_seconds": last_elapsed,
        "final_explored_nodes": final_nodes,
        "final_simplex_iterations": final_iterations,
        "final_elapsed_seconds": final_elapsed,
        "final_best_objective": final_objective,
        "final_best_bound": final_bound,
        "final_gap_percent": final_gap_percent,
        "time_limit_reached": "Time limit reached" in text,
        "out_of_memory_reported": "Out of memory" in text,
        "numerical_warning_reported": any(
            marker in text
            for marker in (
                "Numerical trouble encountered",
                "Warning: Model contains large",
                "Warning: switch to quad precision",
            )
        ),
    }


def _last_regex_value(
    text: str,
    label: str,
    pattern: str,
) -> str | None:
    matches = tuple(
        re.finditer(
            rf"^\s*{re.escape(label)}\s+(?P<value>{pattern})\s*$",
            text,
            flags=re.MULTILINE,
        )
    )
    return matches[-1].group("value") if matches else None


def _parse_highs_log(text: str) -> dict[str, object]:
    """Extract progress-tree and final-certificate fields from a HiGHS log."""

    maximum_explored = 0
    maximum_unexplored = 0
    last_elapsed: float | None = None
    for line in text.splitlines():
        match = _HIGHS_PROGRESS_RE.match(line)
        if match is None:
            continue
        maximum_explored = max(maximum_explored, int(match.group("explored")))
        maximum_unexplored = max(
            maximum_unexplored,
            int(match.group("unexplored")),
        )
        last_elapsed = float(match.group("seconds"))

    number = r"[-+0-9.eE]+"
    status = _last_regex_value(text, "Status", r".+")
    objective = _last_regex_value(text, "Primal bound", number)
    bound = _last_regex_value(text, "Dual bound", number)
    gap_match = tuple(
        re.finditer(
            rf"^\s*Gap\s+(?P<value>{number})%.*$",
            text,
            flags=re.MULTILINE,
        )
    )
    elapsed = _last_regex_value(text, "Timing", number)
    nodes = _last_regex_value(text, "Nodes", r"\d+")
    iterations = _last_regex_value(text, "LP iterations", r"\d+")
    final_nodes = int(nodes) if nodes is not None else None
    if final_nodes is not None:
        maximum_explored = max(maximum_explored, final_nodes)
    return {
        "status": status,
        "maximum_explored_nodes": maximum_explored,
        "maximum_unexplored_nodes": maximum_unexplored,
        "last_progress_elapsed_seconds": last_elapsed,
        "final_explored_nodes": final_nodes,
        "final_simplex_iterations": (
            int(iterations) if iterations is not None else None
        ),
        "final_elapsed_seconds": _optional_float(elapsed) if elapsed else None,
        "final_best_objective": (
            _optional_float(objective) if objective else None
        ),
        "final_best_bound": _optional_float(bound) if bound else None,
        "final_gap_percent": (
            _optional_float(gap_match[-1].group("value"))
            if gap_match
            else None
        ),
        "time_limit_reached": status == "Time limit reached",
        "out_of_memory_reported": "Out of memory" in text,
        "numerical_warning_reported": any(
            marker in text
            for marker in (
                "WARNING: Problem has some excessively",
                "Numerical trouble",
            )
        ),
    }


def _classify_memory_growth(
    *,
    memory_samples: Sequence[Mapping[str, object]],
    gurobi_log: Mapping[str, object],
) -> dict[str, object]:
    """Classify evidence without equating unexplained growth with a leak."""

    usable = [
        sample
        for sample in memory_samples
        if isinstance(sample.get("private_bytes"), int)
    ]
    if len(usable) < 2:
        return {
            "classification": "insufficient_memory_samples",
            "private_bytes_delta": None,
            "private_bytes_growth_fraction": None,
        }
    first = int(usable[0]["private_bytes"])
    last = int(usable[-1]["private_bytes"])
    delta = last - first
    fraction = delta / max(first, 1)
    explored = int(gurobi_log.get("maximum_explored_nodes") or 0)
    unexplored = int(gurobi_log.get("maximum_unexplored_nodes") or 0)
    substantial = delta >= 1_000_000_000 and fraction >= 0.25
    if substantial and (explored >= 100 or unexplored >= 100):
        classification = "branch_and_bound_tree_growth_supported"
    elif substantial:
        classification = "native_memory_growth_not_explained_by_nodes"
    else:
        classification = "no_substantial_private_memory_growth_observed"
    return {
        "classification": classification,
        "private_bytes_delta": delta,
        "private_bytes_growth_fraction": fraction,
        "first_private_bytes": first,
        "last_private_bytes": last,
        "maximum_explored_nodes": explored,
        "maximum_unexplored_nodes": unexplored,
    }


def _resource_stop_reason(
    sample: Mapping[str, object],
    *,
    private_commit_limit_bytes: int,
    minimum_system_commit_available_bytes: int,
) -> str | None:
    if sample.get("sampling_available") is not True:
        return None
    private_bytes = sample.get("private_bytes")
    if isinstance(private_bytes, int) and private_bytes >= private_commit_limit_bytes:
        return "private_commit_limit_reached"
    available = sample.get("system_commit_available_bytes")
    if (
        isinstance(available, int)
        and available <= minimum_system_commit_available_bytes
    ):
        return "system_commit_reserve_reached"
    return None


def _tree_snapshot(root: Path) -> dict[str, str] | None:
    if not root.exists():
        return None
    if not root.is_dir():
        raise ValueError(f"artifact root is not a directory: {root}")
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


if os.name == "nt":
    from ctypes import wintypes

    class _ProcessMemoryCountersEx(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("PageFaultCount", wintypes.DWORD),
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

    class _MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", wintypes.DWORD),
            ("dwMemoryLoad", wintypes.DWORD),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]


def _windows_memory_sample(pid: int) -> dict[str, object]:
    if os.name != "nt":
        return {"sampling_available": False, "reason": "windows_only"}
    process_query_information = 0x0400
    process_vm_read = 0x0010
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    handle = kernel32.OpenProcess(
        process_query_information | process_vm_read,
        False,
        pid,
    )
    if not handle:
        return {
            "sampling_available": False,
            "reason": f"OpenProcess failed: {ctypes.get_last_error()}",
        }
    try:
        counters = _ProcessMemoryCountersEx()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(
            handle,
            ctypes.byref(counters),
            counters.cb,
        ):
            return {
                "sampling_available": False,
                "reason": (
                    "GetProcessMemoryInfo failed: "
                    f"{ctypes.get_last_error()}"
                ),
            }
        memory = _MemoryStatusEx()
        memory.dwLength = ctypes.sizeof(memory)
        system_available = bool(kernel32.GlobalMemoryStatusEx(ctypes.byref(memory)))
        sample: dict[str, object] = {
            "sampling_available": True,
            "working_set_bytes": int(counters.WorkingSetSize),
            "peak_working_set_bytes": int(counters.PeakWorkingSetSize),
            "pagefile_usage_bytes": int(counters.PagefileUsage),
            "peak_pagefile_usage_bytes": int(counters.PeakPagefileUsage),
            "private_bytes": int(counters.PrivateUsage),
            "page_fault_count": int(counters.PageFaultCount),
        }
        if system_available:
            sample.update(
                {
                    "system_memory_load_percent": int(memory.dwMemoryLoad),
                    "system_total_physical_bytes": int(memory.ullTotalPhys),
                    "system_available_physical_bytes": int(memory.ullAvailPhys),
                    "system_commit_limit_bytes": int(memory.ullTotalPageFile),
                    "system_commit_available_bytes": int(memory.ullAvailPageFile),
                }
            )
        return sample
    finally:
        kernel32.CloseHandle(handle)


def _worker(
    *,
    config_path: Path,
    block_id: str,
    time_limit_seconds: float,
    gurobi_probe_profile: str,
    result_path: Path,
) -> int:
    preflight = v4._preflight(config_path)
    config, grid_root, blocks, _, _ = preflight
    formal_checkpoint_root = _resolve(
        Path(str(config["execution"]["checkpoint_directory"]))
    )
    formal_output_root = _resolve(Path(str(config["output"]["directory"])))
    _ensure_worker_result_is_isolated(
        result_path=result_path,
        formal_checkpoint_root=formal_checkpoint_root,
        formal_output_root=formal_output_root,
    )
    started_monotonic = time.perf_counter()
    payload: dict[str, object] = {
        "schema": "rq2_grid_need_gurobi_block_worker_v1",
        "block_id": block_id,
        "worker_pid": os.getpid(),
        "worker_started_at_utc": _utc_now(),
        "worker_started_monotonic_seconds": started_monotonic,
        "formal_checkpoint_written": False,
        "formal_output_written": False,
    }
    try:
        if block_id not in blocks:
            raise ValueError(f"unknown diagnostic block: {block_id}")
        solver_payload = _diagnostic_solver_payload(
            config["solver"],
            time_limit_seconds=time_limit_seconds,
            gurobi_probe_profile=gurobi_probe_profile,
        )
        probe_options = _install_gurobi_probe_profile(gurobi_probe_profile)
        payload["gurobi_probe_profile"] = gurobi_probe_profile
        payload["gurobi_probe_options"] = probe_options
        data = load_rts_gmlc_chronological_data(
            grid_root,
            base_mva=float(config["grid_source"]["base_mva"]),
        )
        block = blocks[block_id]
        source_hours = tuple(int(row["source_hour"]) for row in block)
        solver_started_monotonic = time.perf_counter()
        payload["solver_started_monotonic_seconds"] = solver_started_monotonic
        print(
            "DIAGNOSTIC_PHASE solver_started "
            f"block={block_id} monotonic={solver_started_monotonic:.9f}",
            flush=True,
        )
        try:
            _, _, audit = v4._normal_baseline(
                data,
                source_hours,
                dc_bus=int(config["model"]["dc_bus"]),
                dc_demand_mw=float(config["model"]["dc_reference_demand_mw"]),
                solver=solver_payload,
            )
        except RuntimeError as error:
            payload.update(
                {
                    "solver_call_returned": True,
                    "accepted": False,
                    "termination_detail": str(error),
                }
            )
        else:
            payload.update(
                {
                    "solver_call_returned": True,
                    "accepted": True,
                    "baseline_audit": audit,
                }
            )
        payload["solver_finished_monotonic_seconds"] = time.perf_counter()
        payload["worker_completed_at_utc"] = _utc_now()
        payload["worker_elapsed_seconds"] = (
            time.perf_counter() - started_monotonic
        )
        _atomic_write_json(result_path, payload)
        print(
            "DIAGNOSTIC_PHASE solver_finished "
            f"block={block_id} accepted={payload['accepted']}",
            flush=True,
        )
        return 0
    except Exception as error:  # noqa: BLE001 - persist every worker failure
        payload.update(
            {
                "solver_call_returned": False,
                "accepted": False,
                "worker_failed": True,
                "failure_type": type(error).__name__,
                "failure_detail": str(error),
                "worker_completed_at_utc": _utc_now(),
                "worker_elapsed_seconds": time.perf_counter() - started_monotonic,
            }
        )
        _atomic_write_json(result_path, payload)
        print(
            "DIAGNOSTIC_PHASE worker_failed "
            f"block={block_id} type={type(error).__name__} detail={error}",
            flush=True,
        )
        return 2


def _run_child(
    *,
    config_path: Path,
    block_id: str,
    time_limit_seconds: float,
    sample_interval_seconds: float,
    private_commit_limit_bytes: int,
    minimum_system_commit_available_bytes: int,
    gurobi_probe_profile: str,
    table_root: Path,
    log_root: Path,
) -> dict[str, object]:
    result_path = table_root / f"{block_id}.worker.json"
    log_path = log_root / f"{block_id}.native.log"
    memory_path = log_root / f"{block_id}.memory.jsonl"
    command = [
        sys.executable,
        "-u",
        "-B",
        "-m",
        "experiments.diagnose_rq2_grid_need_gurobi_block",
        "--worker",
        "--config",
        str(config_path),
        "--block",
        block_id,
        "--time-limit-seconds",
        str(time_limit_seconds),
        "--gurobi-probe-profile",
        gurobi_probe_profile,
        "--worker-result",
        str(result_path),
    ]
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    started_monotonic = time.perf_counter()
    samples: list[dict[str, object]] = []
    wall_limit_seconds = time_limit_seconds + 300.0
    terminated_by_parent = False
    resource_stop_reason = None
    with (
        log_path.open("w", encoding="utf-8", newline="") as log,
        memory_path.open("w", encoding="utf-8", newline="") as memory_log,
    ):
        process = subprocess.Popen(
            command,
            cwd=_ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        last_console_update = -30.0
        while process.poll() is None:
            now = time.perf_counter()
            elapsed = now - started_monotonic
            sample = {
                "timestamp_utc": _utc_now(),
                "monotonic_seconds": now,
                "elapsed_seconds": elapsed,
                "pid": process.pid,
                **_windows_memory_sample(process.pid),
            }
            samples.append(sample)
            memory_log.write(json.dumps(sample, sort_keys=True) + "\n")
            memory_log.flush()
            if elapsed - last_console_update >= 30.0:
                private_gib = (
                    float(sample.get("private_bytes", 0)) / (1024.0**3)
                    if sample.get("sampling_available")
                    else float("nan")
                )
                print(
                    "DIAGNOSTIC_HEARTBEAT "
                    f"block={block_id} elapsed={elapsed:.1f}s "
                    f"private={private_gib:.3f}GiB",
                    flush=True,
                )
                last_console_update = elapsed
            resource_stop_reason = _resource_stop_reason(
                sample,
                private_commit_limit_bytes=private_commit_limit_bytes,
                minimum_system_commit_available_bytes=(
                    minimum_system_commit_available_bytes
                ),
            )
            if resource_stop_reason is not None:
                terminated_by_parent = True
                process.terminate()
                try:
                    process.wait(timeout=30.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=30.0)
                print(
                    "DIAGNOSTIC_RESOURCE_STOP "
                    f"block={block_id} reason={resource_stop_reason}",
                    flush=True,
                )
                break
            if elapsed > wall_limit_seconds:
                terminated_by_parent = True
                process.terminate()
                try:
                    process.wait(timeout=30.0)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=30.0)
                break
            time.sleep(sample_interval_seconds)
        exit_code = process.wait()

    native_text = log_path.read_text(encoding="utf-8", errors="replace")
    solver_name = "highs" if gurobi_probe_profile == "highs_route" else "gurobi"
    parsed = (
        _parse_highs_log(native_text)
        if solver_name == "highs"
        else _parse_gurobi_log(native_text)
    )
    worker_payload = (
        json.loads(result_path.read_text(encoding="utf-8"))
        if result_path.exists()
        else None
    )
    solver_samples = samples
    if isinstance(worker_payload, dict) and isinstance(
        worker_payload.get("solver_started_monotonic_seconds"),
        (int, float),
    ):
        solver_started = float(
            worker_payload["solver_started_monotonic_seconds"]
        )
        solver_samples = [
            sample
            for sample in samples
            if float(sample["monotonic_seconds"]) >= solver_started
        ]
    classification = _classify_memory_growth(
        memory_samples=solver_samples,
        gurobi_log=parsed,
    )
    return {
        "block_id": block_id,
        "command": command,
        "pid": process.pid,
        "exit_code": exit_code,
        "terminated_by_parent_watchdog": terminated_by_parent,
        "diagnostic_resource_stop": resource_stop_reason is not None,
        "diagnostic_resource_stop_reason": resource_stop_reason,
        "solver_infeasibility_inferred_from_resource_stop": False,
        "wall_elapsed_seconds": time.perf_counter() - started_monotonic,
        "worker_result_path": _display_path(result_path),
        "worker_result_sha256": _sha256(result_path) if result_path.exists() else None,
        "native_log_path": _display_path(log_path),
        "native_log_sha256": _sha256(log_path),
        "memory_log_path": _display_path(memory_path),
        "memory_log_sha256": _sha256(memory_path),
        "memory_sample_count": len(samples),
        "peak_private_bytes": max(
            (
                int(sample["private_bytes"])
                for sample in samples
                if isinstance(sample.get("private_bytes"), int)
            ),
            default=None,
        ),
        "solver_name": solver_name,
        "solver_log": parsed,
        "gurobi_log": parsed if solver_name == "gurobi" else None,
        "highs_log": parsed if solver_name == "highs" else None,
        "memory_growth": classification,
        "worker": worker_payload,
    }


def run_diagnostic(
    *,
    config_path: Path,
    block_ids: Sequence[str],
    time_limit_seconds: float,
    sample_interval_seconds: float,
    private_commit_limit_gib: float,
    minimum_system_commit_available_gib: float,
    gurobi_probe_profile: str,
    table_root: Path,
    log_root: Path,
) -> dict[str, object]:
    config_path = _resolve(config_path)
    table_root = _resolve(table_root)
    log_root = _resolve(log_root)
    config, _, blocks, _, _ = v4._preflight(config_path)
    if tuple(block_ids) != _DEFAULT_BLOCKS:
        raise ValueError(
            "v1 diagnostic is frozen to control 0008 followed by target 0009"
        )
    if any(block_id not in blocks for block_id in block_ids):
        raise ValueError("diagnostic block inventory drifted")
    if not 0.5 <= float(sample_interval_seconds) <= 30.0:
        raise ValueError("sample interval must be in [0.5, 30] seconds")
    if not 1.0 <= float(private_commit_limit_gib) <= 32.0:
        raise ValueError("private commit limit must be in [1, 32] GiB")
    if not 0.5 <= float(minimum_system_commit_available_gib) <= 16.0:
        raise ValueError("system commit reserve must be in [0.5, 16] GiB")
    private_commit_limit_bytes = int(private_commit_limit_gib * 1024**3)
    minimum_system_commit_available_bytes = int(
        minimum_system_commit_available_gib * 1024**3
    )
    diagnostic_solver = _diagnostic_solver_payload(
        config["solver"],
        time_limit_seconds=time_limit_seconds,
        gurobi_probe_profile=gurobi_probe_profile,
    )
    gurobi_probe_options = _gurobi_probe_options(gurobi_probe_profile)
    formal_checkpoint_root = _resolve(
        Path(str(config["execution"]["checkpoint_directory"]))
    )
    formal_output_root = _resolve(Path(str(config["output"]["directory"])))
    _ensure_diagnostic_roots_are_isolated(
        table_root=table_root,
        log_root=log_root,
        formal_checkpoint_root=formal_checkpoint_root,
        formal_output_root=formal_output_root,
    )
    if table_root.exists() or log_root.exists():
        raise FileExistsError("diagnostic roots already exist; refuse overwrite")
    before_formal = {
        "checkpoint": _tree_snapshot(formal_checkpoint_root),
        "output": _tree_snapshot(formal_output_root),
    }
    host_sample = _windows_memory_sample(os.getpid())
    if (
        host_sample.get("sampling_available") is True
        and int(host_sample.get("system_commit_available_bytes", 0))
        <= minimum_system_commit_available_bytes
    ):
        raise RuntimeError(
            "diagnostic start refused: system commit reserve is already below "
            "the fail-safe floor"
        )
    table_root.mkdir(parents=True)
    log_root.mkdir(parents=True)
    block_results = []
    for block_id in block_ids:
        print(f"DIAGNOSTIC_START block={block_id}", flush=True)
        block_result = _run_child(
            config_path=config_path,
            block_id=block_id,
            time_limit_seconds=time_limit_seconds,
            sample_interval_seconds=sample_interval_seconds,
            private_commit_limit_bytes=private_commit_limit_bytes,
            minimum_system_commit_available_bytes=(
                minimum_system_commit_available_bytes
            ),
            gurobi_probe_profile=gurobi_probe_profile,
            table_root=table_root,
            log_root=log_root,
        )
        block_results.append(block_result)
        print(
            "DIAGNOSTIC_DONE "
            f"block={block_id} exit={block_result['exit_code']} "
            f"classification={block_result['memory_growth']['classification']}",
            flush=True,
        )
    after_formal = {
        "checkpoint": _tree_snapshot(formal_checkpoint_root),
        "output": _tree_snapshot(formal_output_root),
    }
    formal_unchanged = after_formal == before_formal
    summary: dict[str, object] = {
        "schema": "rq2_grid_need_gurobi_block_diagnostic_v1",
        "scope": {
            "evidence_level": "development_root_cause_diagnostic",
            "formal_grid_execution": False,
            "formal_checkpoint_reuse": False,
            "formal_checkpoint_write": False,
            "formal_output_write": False,
        },
        "created_at_utc": _utc_now(),
        "config_path": _display_path(config_path),
        "config_sha256": _sha256(config_path),
        "formal_runner_path": v4.__file__.replace("\\", "/"),
        "formal_runner_sha256": _sha256(Path(v4.__file__)),
        "diagnostic_runner_sha256": _sha256(Path(__file__)),
        "block_ids": list(block_ids),
        "control_block_id": block_ids[0],
        "target_block_id": block_ids[1],
        "formal_solver": config["solver"],
        "diagnostic_solver": diagnostic_solver,
        "gurobi_probe_profile": gurobi_probe_profile,
        "gurobi_probe_options": gurobi_probe_options,
        "sample_interval_seconds": float(sample_interval_seconds),
        "private_commit_limit_gib": float(private_commit_limit_gib),
        "minimum_system_commit_available_gib": float(
            minimum_system_commit_available_gib
        ),
        "formal_artifacts_before": before_formal,
        "formal_artifacts_after": after_formal,
        "formal_artifacts_unchanged": formal_unchanged,
        "blocks": block_results,
    }
    _atomic_write_json(table_root / "summary.json", summary)
    manifest = {
        path.relative_to(table_root).as_posix(): _sha256(path)
        for path in sorted(table_root.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS.json"
    }
    _atomic_write_json(table_root / "SHA256SUMS.json", manifest)
    if not formal_unchanged:
        raise RuntimeError("formal artifacts changed during isolated diagnostic")
    return summary


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=_DEFAULT_CONFIG)
    parser.add_argument(
        "--block",
        action="append",
        dest="blocks",
        default=None,
        help="Repeat twice: control 0008 then target 0009.",
    )
    parser.add_argument("--time-limit-seconds", type=float, default=600.0)
    parser.add_argument(
        "--gurobi-probe-profile",
        choices=tuple(_GUROBI_PROBE_PROFILES),
        default="formal_default",
        help=argparse.SUPPRESS,
    )
    parser.add_argument("--sample-interval-seconds", type=float, default=5.0)
    parser.add_argument("--private-commit-limit-gib", type=float, default=8.0)
    parser.add_argument(
        "--minimum-system-commit-available-gib",
        type=float,
        default=2.0,
    )
    parser.add_argument("--table-root", type=Path, default=_DEFAULT_TABLE_ROOT)
    parser.add_argument("--log-root", type=Path, default=_DEFAULT_LOG_ROOT)
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--worker-result", type=Path, help=argparse.SUPPRESS)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    blocks = tuple(args.blocks or _DEFAULT_BLOCKS)
    if args.worker:
        if len(blocks) != 1 or args.worker_result is None:
            raise ValueError("worker mode requires one block and --worker-result")
        return _worker(
            config_path=_resolve(args.config),
            block_id=blocks[0],
            time_limit_seconds=args.time_limit_seconds,
            gurobi_probe_profile=args.gurobi_probe_profile,
            result_path=_resolve(args.worker_result),
        )
    summary = run_diagnostic(
        config_path=args.config,
        block_ids=blocks,
        time_limit_seconds=args.time_limit_seconds,
        sample_interval_seconds=args.sample_interval_seconds,
        private_commit_limit_gib=args.private_commit_limit_gib,
        minimum_system_commit_available_gib=(
            args.minimum_system_commit_available_gib
        ),
        gurobi_probe_profile=args.gurobi_probe_profile,
        table_root=args.table_root,
        log_root=args.log_root,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
