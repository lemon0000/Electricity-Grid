"""Read-only status monitor for AC-aware commitment attempts."""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import os
import re
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_SCHEMA = "rts_gmlc_zero_dc_ac_aware_commitment_monitor_v1"
_COMPLETED_EVENTS = {"attempt_completed", "run_completed"}
_FAILED_EVENTS = {
    "attempt_failed",
    "run_failed",
    "candidate_failed",
    "joint_call_failed",
}
_CANDIDATE_END_EVENTS = {"candidate_completed", "candidate_failed"}
_WORK_END_EVENTS = {
    "joint_call_completed",
    "joint_call_failed",
    "joint_checkpoint_loaded",
}
_SOLVE_START_EVENTS = {
    "solve_started",
    "exact_cg_call_started",
    "joint_call_started",
}
_SOLVE_END_EVENTS = {
    "solve_completed",
    "solve_failed",
    "exact_cg_master_completed",
    "exact_cg_screen_completed",
    "exact_cg_full_state_audit_completed",
    "joint_call_completed",
    "joint_call_failed",
}
_STAGE_END_EVENTS = {
    "exact_cg_stage_completed",
    "joint_preparation_completed",
}
_NUMBER = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?|[-+]?inf"
_REPORT_PATTERNS = {
    "incumbent": re.compile(rf"^\s*Primal bound\s+({_NUMBER})\b", re.IGNORECASE),
    "best_bound": re.compile(rf"^\s*Dual bound\s+({_NUMBER})\b", re.IGNORECASE),
    "gap": re.compile(rf"^\s*Gap\s+({_NUMBER})%?\b", re.IGNORECASE),
    "nodes": re.compile(r"^\s*Nodes\s+(\d+)\b", re.IGNORECASE),
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_timestamp(value: object) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip()
    if candidate.endswith("Z"):
        candidate = candidate[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _finite_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _nonnegative_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed >= 0 else None


def _age_seconds(now: datetime, timestamp: datetime | None) -> float | None:
    if timestamp is None:
        return None
    return max(0.0, (now - timestamp).total_seconds())


def _read_progress(path: Path) -> tuple[list[dict[str, Any]], int, list[str]]:
    warnings: list[str] = []
    try:
        raw = path.read_bytes()
    except OSError as exc:
        return [], 1, [f"progress log could not be read: {exc}"]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        text = raw.decode("utf-8", errors="replace")
        warnings.append("progress log is not valid UTF-8")

    records: list[dict[str, Any]] = []
    malformed = 0
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            malformed += 1
            warnings.append(f"progress line {line_number} is blank")
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            malformed += 1
            warnings.append(f"progress line {line_number} is not complete JSON")
            continue
        if (
            not isinstance(record, dict)
            or not isinstance(record.get("event"), str)
            or not record["event"].strip()
        ):
            malformed += 1
            warnings.append(f"progress line {line_number} is not an event object")
            continue
        records.append(record)
    return records, malformed, warnings


def _integrity_warnings(records: Sequence[Mapping[str, object]]) -> list[str]:
    warnings: list[str] = []
    for key in ("schema", "run_id", "preregistration_id", "pid"):
        values = {str(row[key]) for row in records if row.get(key) is not None}
        if len(values) > 1:
            warnings.append(f"progress events contain inconsistent {key} values")
    invalid_timestamps = sum(
        1 for row in records if _parse_timestamp(row.get("timestamp_utc")) is None
    )
    if invalid_timestamps:
        warnings.append(
            f"{invalid_timestamps} progress event(s) have invalid UTC timestamps"
        )
    return warnings


def _find_progress_logs(log_root: Path) -> tuple[list[Path], list[str]]:
    if log_root.is_file():
        return ([log_root] if log_root.name == "progress.jsonl" else []), []
    if not log_root.is_dir():
        return [], ["log root does not exist or is not a directory"]
    try:
        paths = [path for path in log_root.rglob("progress.jsonl") if path.is_file()]
    except OSError as exc:
        return [], [f"log root could not be scanned: {exc}"]
    return paths, []


def _latest_progress_log(paths: Sequence[Path]) -> Path:
    def sort_key(path: Path) -> tuple[int, str]:
        try:
            modified = path.stat().st_mtime_ns
        except OSError:
            modified = -1
        return modified, str(path)

    return max(paths, key=sort_key)


def _candidate_id(record: Mapping[str, object]) -> object | None:
    for key in ("candidate_id", "requested_candidate_id", "candidate"):
        value = record.get(key)
        if value is not None:
            return value
    return None


def _solve_label(record: Mapping[str, object]) -> str | None:
    for key in ("solve_label", "call_id"):
        value = record.get(key)
        if value is not None:
            return str(value)
    for key in ("solve", "callback_record"):
        nested = record.get(key)
        if isinstance(nested, Mapping):
            label = _solve_label(nested)
            if label is not None:
                return label
    return None


def _nested_values(record: Mapping[str, object]) -> list[Mapping[str, object]]:
    values = [record]
    for key in ("solve", "callback_record", "certificate"):
        nested = record.get(key)
        if isinstance(nested, Mapping):
            values.extend(_nested_values(nested))
    return values


def _first_value(record: Mapping[str, object], keys: Sequence[str]) -> object | None:
    for candidate in _nested_values(record):
        for key in keys:
            if candidate.get(key) is not None:
                return candidate[key]
    return None


def _event_state(records: Sequence[Mapping[str, object]]) -> dict[str, object]:
    current_candidate: object | None = None
    current_stage: str | None = None
    current_iteration: int | None = None
    current_solve: str | None = None
    current_initial_strategy: str | None = None
    completed_ids: set[str] = set()
    anonymous_completed_events = 0
    explicit_completed = 0
    requested_budget_candidate_count = 0
    parent_baseline_completed = False
    completed_joint_call_count = 0
    expected_joint_call_count = 0

    for record in records:
        event = str(record["event"])
        candidate = _candidate_id(record)
        requested = _nonnegative_int(record.get("candidate_count"))
        if requested is not None:
            requested_budget_candidate_count = max(
                requested_budget_candidate_count, requested
            )
        explicit = _nonnegative_int(record.get("completed_candidate_count"))
        if explicit is not None:
            explicit_completed = max(explicit_completed, explicit)
        completed_joint = _nonnegative_int(record.get("completed_joint_call_count"))
        if completed_joint is not None:
            completed_joint_call_count = max(
                completed_joint_call_count, completed_joint
            )
        expected_joint = _nonnegative_int(record.get("expected_joint_call_count"))
        if expected_joint is not None:
            expected_joint_call_count = max(expected_joint_call_count, expected_joint)

        if event == "candidate_started":
            current_candidate = candidate
        elif event in _CANDIDATE_END_EVENTS:
            if event == "candidate_completed":
                if (
                    record.get("source") == "frozen_parent_zero_dc_dispatch"
                    or _nonnegative_int(record.get("candidate_ordinal")) == 0
                ):
                    parent_baseline_completed = True
                if candidate is not None:
                    completed_ids.add(str(candidate))
                else:
                    anonymous_completed_events += 1
            current_candidate = None
        elif event in _WORK_END_EVENTS:
            current_candidate = None
            current_initial_strategy = None
        elif candidate is not None:
            current_candidate = candidate
        if record.get("initial_strategy") is not None:
            current_initial_strategy = str(record["initial_strategy"])

        stage = record.get("stage")
        if stage is not None:
            current_stage = str(stage)
        iteration = _nonnegative_int(
            record.get("cg_iteration", record.get("iteration"))
        )
        if iteration is not None:
            current_iteration = iteration

        label = _solve_label(record)
        if event in _SOLVE_START_EVENTS:
            current_solve = label
        elif event in _SOLVE_END_EVENTS and (label is None or label == current_solve):
            current_solve = None
            current_initial_strategy = None
        elif event == "heartbeat" and label is not None:
            current_solve = label

        if event in _CANDIDATE_END_EVENTS | _WORK_END_EVENTS:
            current_stage = None
            current_iteration = None
            current_solve = None
            current_initial_strategy = None
        elif event in _STAGE_END_EVENTS:
            current_stage = None
            current_iteration = None
            current_solve = None
            current_initial_strategy = None
        if event in _COMPLETED_EVENTS | _FAILED_EVENTS:
            current_candidate = None
            current_stage = None
            current_iteration = None
            current_solve = None
            current_initial_strategy = None

    completed_candidate_count = max(
        explicit_completed,
        len(completed_ids) + anonymous_completed_events,
    )
    return {
        "current_candidate": current_candidate,
        "current_stage": current_stage,
        "current_cg_iteration": current_iteration,
        "current_solve_label": current_solve,
        "current_initial_strategy": current_initial_strategy,
        "completed_candidate_count": completed_candidate_count,
        "completed_budget_candidate_count": max(
            0, completed_candidate_count - int(parent_baseline_completed)
        ),
        "requested_budget_candidate_count": requested_budget_candidate_count,
        "parent_baseline_completed": parent_baseline_completed,
        "completed_joint_call_count": completed_joint_call_count,
        "expected_joint_call_count": expected_joint_call_count,
    }


def _event_solver_metrics(
    records: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    metrics: dict[str, object] = {
        "incumbent": None,
        "lower_bound": None,
        "upper_bound": None,
        "absolute_gap": None,
        "gap": None,
        "nodes": None,
        "sense": None,
    }
    key_sets = {
        "incumbent": ("incumbent_objective", "primal_bound", "best_solution"),
        "lower_bound": ("certified_lower_bound", "lower_bound", "raw_lower_bound"),
        "upper_bound": ("certified_upper_bound", "upper_bound", "raw_upper_bound"),
        "absolute_gap": ("absolute_gap",),
        "gap": (
            "relative_gap_to_feasible_incumbent",
            "relative_gap",
            "relative_gap_to_incumbent",
            "mip_gap",
        ),
        "nodes": ("nodes", "node_count", "mip_node_count"),
        "sense": ("sense",),
    }
    for record in records:
        for output_key, input_keys in key_sets.items():
            value = _first_value(record, input_keys)
            if value is None:
                continue
            if output_key in {
                "incumbent",
                "lower_bound",
                "upper_bound",
                "absolute_gap",
                "gap",
            }:
                parsed: object | None = _finite_float(value)
            elif output_key == "nodes":
                parsed = _nonnegative_int(value)
            else:
                parsed = str(value)
            if parsed is not None:
                metrics[output_key] = parsed
    return metrics


def _latest_solve_scope(
    records: Sequence[Mapping[str, object]],
) -> Sequence[Mapping[str, object]]:
    for index in range(len(records) - 1, -1, -1):
        if records[index].get("event") in _SOLVE_START_EVENTS:
            return records[index:]
    return records


def _parse_highs_number(value: str) -> float | None:
    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if math.isfinite(parsed) else None


def _parse_highs_progress(text: str, *, sense: str | None) -> dict[str, object]:
    incumbent: float | None = None
    best_bound: float | None = None
    gap: float | None = None
    nodes: int | None = None

    for line in text.splitlines():
        stripped = line.strip()
        tokens = stripped.split()
        offset = 1 if tokens and len(tokens[0]) == 1 and tokens[0].isalpha() else 0
        if len(tokens) >= offset + 12 and tokens[offset + 3].endswith("%"):
            parsed_nodes = _nonnegative_int(tokens[offset])
            row_bound = _parse_highs_number(tokens[offset + 4])
            row_incumbent = _parse_highs_number(tokens[offset + 5])
            row_gap = tokens[offset + 6].rstrip("%")
            if parsed_nodes is not None:
                nodes = parsed_nodes
                best_bound = row_bound
                incumbent = row_incumbent
                parsed_gap = _parse_highs_number(row_gap)
                gap = parsed_gap / 100.0 if parsed_gap is not None else None

        for key, pattern in _REPORT_PATTERNS.items():
            match = pattern.match(line)
            if match is None:
                continue
            if key == "nodes":
                nodes = int(match.group(1))
            elif key == "gap":
                parsed_gap = _parse_highs_number(match.group(1))
                gap = parsed_gap / 100.0 if parsed_gap is not None else None
            elif key == "incumbent":
                incumbent = _parse_highs_number(match.group(1))
            else:
                best_bound = _parse_highs_number(match.group(1))

    lower_bound: float | None = None
    upper_bound: float | None = None
    if incumbent is not None and best_bound is not None:
        lower_bound, upper_bound = sorted((incumbent, best_bound))
    elif sense == "maximize":
        lower_bound, upper_bound = incumbent, best_bound
    elif sense == "minimize":
        lower_bound, upper_bound = best_bound, incumbent

    return {
        "incumbent": incumbent,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "gap": gap,
        "nodes": nodes,
    }


def _native_log_path(
    records: Sequence[Mapping[str, object]],
    *,
    progress_path: Path,
    log_root: Path,
    now: datetime,
    missing_grace_seconds: float = 30.0,
) -> tuple[Path | None, list[str]]:
    native_log: object | None = None
    native_log_timestamp: datetime | None = None
    for record in records:
        value = _first_value(record, ("native_log", "native_log_path"))
        if value is not None:
            native_log = value
            native_log_timestamp = _parse_timestamp(record.get("timestamp_utc"))
    if not isinstance(native_log, (str, os.PathLike)):
        return None, []

    candidate = Path(native_log)
    if not candidate.is_absolute():
        candidate = progress_path.parent / candidate
        if not candidate.is_file():
            matches = [
                path for path in log_root.rglob(Path(native_log).name) if path.is_file()
            ]
            if matches:
                candidate = max(
                    matches,
                    key=lambda path: (path.stat().st_mtime_ns, path.as_posix()),
                )
    try:
        resolved = candidate.resolve()
        allowed_root = (
            log_root.resolve() if log_root.is_dir() else log_root.parent.resolve()
        )
        resolved.relative_to(allowed_root)
    except (OSError, ValueError):
        return None, ["native solver log resolves outside the explicit log root"]
    if not resolved.is_file():
        age = _age_seconds(now, native_log_timestamp)
        if age is not None and age <= missing_grace_seconds:
            return None, []
        return None, [f"native solver log is missing: {resolved}"]
    return resolved, []


def _deadline_state(
    records: Sequence[Mapping[str, object]],
    *,
    now: datetime,
    monotonic_now: float,
) -> dict[str, object]:
    deadline_utc: datetime | None = None
    deadline_monotonic: float | None = None
    remaining: float | None = None
    remaining_timestamp: datetime | None = None
    for record in records:
        utc_value = _first_value(
            record, ("hard_deadline_utc", "candidate_deadline_utc", "deadline_utc")
        )
        parsed_utc = _parse_timestamp(utc_value)
        if parsed_utc is not None:
            deadline_utc = parsed_utc
        monotonic_value = _first_value(
            record,
            (
                "hard_deadline_monotonic",
                "candidate_deadline_monotonic",
                "deadline_monotonic",
            ),
        )
        parsed_monotonic = _finite_float(monotonic_value)
        if parsed_monotonic is not None:
            deadline_monotonic = parsed_monotonic
        remaining_value = _first_value(
            record,
            (
                "hard_deadline_remaining_seconds",
                "candidate_remaining_seconds",
                "remaining_seconds",
            ),
        )
        parsed_remaining = _finite_float(remaining_value)
        if parsed_remaining is not None:
            remaining = parsed_remaining
            remaining_timestamp = _parse_timestamp(record.get("timestamp_utc"))

    if deadline_utc is not None:
        remaining = (deadline_utc - now).total_seconds()
    elif deadline_monotonic is not None:
        remaining = deadline_monotonic - monotonic_now
    elif remaining is not None and remaining_timestamp is not None:
        remaining -= max(0.0, (now - remaining_timestamp).total_seconds())

    return {
        "hard_deadline_utc": (
            deadline_utc.isoformat() if deadline_utc is not None else None
        ),
        "hard_deadline_monotonic": deadline_monotonic,
        "remaining_seconds": remaining,
    }


def _process_is_running(pid: int) -> bool | None:
    """Probe a PID without sending it a signal."""

    if pid <= 0:
        return False
    if os.name == "nt":
        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        handle = kernel32.OpenProcess(
            process_query_limited_information, False, int(pid)
        )
        if not handle:
            error = ctypes.get_last_error()
            return None if error == 5 else False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return None
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)

    proc_stat = Path(f"/proc/{pid}/stat")
    try:
        stat_text = proc_stat.read_text(encoding="ascii")
    except FileNotFoundError:
        return False
    except (OSError, UnicodeError):
        return None
    closing_paren = stat_text.rfind(")")
    if closing_paren < 0 or len(stat_text) <= closing_paren + 2:
        return None
    return stat_text[closing_paren + 2] != "Z"


def _empty_status(
    log_root: Path, now: datetime, warnings: list[str]
) -> dict[str, object]:
    return {
        "schema": _SCHEMA,
        "observed_at_utc": now.isoformat(),
        "log_root": str(log_root.resolve()),
        "progress_path": None,
        "attempt": None,
        "run_id": None,
        "status": "missing",
        "alive": None,
        "pid": None,
        "current_candidate": None,
        "current_stage": None,
        "current_cg_iteration": None,
        "current_solve_label": None,
        "current_initial_strategy": None,
        "elapsed_seconds": None,
        "last_event_age_seconds": None,
        "last_heartbeat_age_seconds": None,
        "latest_incumbent": None,
        "latest_lower_bound": None,
        "latest_upper_bound": None,
        "latest_absolute_gap": None,
        "latest_gap": None,
        "latest_nodes": None,
        "completed_candidate_count": 0,
        "completed_budget_candidate_count": 0,
        "requested_budget_candidate_count": 0,
        "parent_baseline_completed": False,
        "completed_joint_call_count": 0,
        "expected_joint_call_count": 0,
        "hard_deadline_utc": None,
        "hard_deadline_monotonic": None,
        "remaining_seconds": None,
        "native_log_path": None,
        "last_event": None,
        "malformed_line_count": 0,
        "warnings": warnings,
    }


def build_status(
    log_root: Path,
    *,
    now: datetime | None = None,
    monotonic_now: float | None = None,
    stale_after_seconds: float = 120.0,
    process_probe: Callable[[int], bool | None] = _process_is_running,
) -> dict[str, object]:
    """Build a status snapshot without changing any run artifact."""

    observed_at = (now or _utc_now()).astimezone(timezone.utc)
    if not math.isfinite(stale_after_seconds) or stale_after_seconds <= 0.0:
        raise ValueError("stale_after_seconds must be finite and positive")
    root = Path(log_root)
    progress_logs, warnings = _find_progress_logs(root)
    if not progress_logs:
        return _empty_status(root, observed_at, warnings or ["no progress.jsonl found"])

    progress_path = _latest_progress_log(progress_logs)
    records, malformed_lines, read_warnings = _read_progress(progress_path)
    warnings.extend(read_warnings)
    integrity = _integrity_warnings(records) if records else []
    warnings.extend(integrity)
    if not records:
        status = _empty_status(root, observed_at, warnings or ["progress log is empty"])
        status.update(
            {
                "progress_path": str(progress_path.resolve()),
                "attempt": progress_path.parent.name,
                "status": "malformed" if malformed_lines else "unknown",
                "malformed_line_count": malformed_lines,
            }
        )
        return status

    last_record = records[-1]
    last_timestamp = _parse_timestamp(last_record.get("timestamp_utc"))
    heartbeat_records = [row for row in records if row.get("event") == "heartbeat"]
    heartbeat_timestamp = (
        _parse_timestamp(heartbeat_records[-1].get("timestamp_utc"))
        if heartbeat_records
        else None
    )
    last_event_age = _age_seconds(observed_at, last_timestamp)
    heartbeat_age = _age_seconds(observed_at, heartbeat_timestamp)
    elapsed_values = [
        value
        for row in records
        if (value := _finite_float(row.get("monotonic_elapsed_seconds"))) is not None
    ]
    elapsed = max(elapsed_values) if elapsed_values else None

    pid_values = [
        value
        for row in records
        if (value := _nonnegative_int(row.get("pid"))) is not None
    ]
    pid = pid_values[-1] if pid_values else None
    try:
        process_alive = process_probe(pid) if pid is not None else None
    except Exception as exc:  # pragma: no cover - platform probes are external.
        process_alive = None
        warnings.append(f"PID liveness probe failed: {exc}")
    last_event = str(last_record["event"])

    corrupt = bool(malformed_lines or integrity or read_warnings)
    if corrupt:
        status_name = "malformed"
        alive: bool | None = None
    elif last_event in _COMPLETED_EVENTS:
        status_name = "completed"
        alive = False
    elif last_event in _FAILED_EVENTS:
        status_name = "failed"
        alive = False
    else:
        fresh = last_event_age is not None and last_event_age <= stale_after_seconds
        if process_alive is True and fresh:
            status_name = "running"
            alive = True
        elif process_alive is None and fresh:
            status_name = "unknown"
            alive = None
            warnings.append("PID liveness could not be confirmed")
        else:
            status_name = "stale"
            alive = False
            if process_alive is False:
                warnings.append("recorded PID is not running")
            if last_event_age is None or not fresh:
                warnings.append("latest progress event is stale")

    state = _event_state(records)
    solve_records = _latest_solve_scope(records)
    event_metrics = _event_solver_metrics(solve_records)
    native_path, native_warnings = _native_log_path(
        solve_records,
        progress_path=progress_path,
        log_root=root,
        now=observed_at,
    )
    warnings.extend(native_warnings)
    if native_path is not None:
        try:
            native_text = native_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            warnings.append(f"native solver log could not be read: {exc}")
        else:
            native_metrics = _parse_highs_progress(
                native_text,
                sense=(
                    str(event_metrics["sense"])
                    if event_metrics["sense"] is not None
                    else None
                ),
            )
            for key, value in native_metrics.items():
                if value is not None and event_metrics[key] is None:
                    event_metrics[key] = value
    lower_bound = _finite_float(event_metrics["lower_bound"])
    upper_bound = _finite_float(event_metrics["upper_bound"])
    if (
        lower_bound is not None
        and upper_bound is not None
        and lower_bound <= upper_bound
    ):
        event_metrics["absolute_gap"] = upper_bound - lower_bound

    deadline = _deadline_state(
        records,
        now=observed_at,
        monotonic_now=(time.monotonic() if monotonic_now is None else monotonic_now),
    )
    return {
        "schema": _SCHEMA,
        "observed_at_utc": observed_at.isoformat(),
        "log_root": str(root.resolve()),
        "progress_path": str(progress_path.resolve()),
        "attempt": progress_path.parent.name,
        "run_id": last_record.get("run_id"),
        "status": status_name,
        "alive": alive,
        "pid": pid,
        **state,
        "elapsed_seconds": elapsed,
        "last_event_age_seconds": last_event_age,
        "last_heartbeat_age_seconds": heartbeat_age,
        "latest_incumbent": event_metrics["incumbent"],
        "latest_lower_bound": event_metrics["lower_bound"],
        "latest_upper_bound": event_metrics["upper_bound"],
        "latest_absolute_gap": event_metrics["absolute_gap"],
        "latest_gap": event_metrics["gap"],
        "latest_nodes": event_metrics["nodes"],
        **deadline,
        "native_log_path": str(native_path) if native_path is not None else None,
        "last_event": last_event,
        "malformed_line_count": malformed_lines,
        "warnings": warnings,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--log-root",
        type=Path,
        required=True,
        help="Explicit attempt log directory to inspect recursively.",
    )
    parser.add_argument(
        "--stale-after-seconds",
        type=float,
        default=120.0,
        help="Maximum last-event age that can be considered live.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        status = build_status(
            args.log_root,
            stale_after_seconds=args.stale_after_seconds,
        )
    except ValueError as exc:
        _parser().error(str(exc))
    print(json.dumps(status, allow_nan=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
