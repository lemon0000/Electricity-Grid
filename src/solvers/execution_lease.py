"""Cross-process execution leases with fail-closed stale takeover."""

from __future__ import annotations

import ctypes
import json
import os
import re
import shutil
import socket
import tempfile
import threading
import uuid
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_LEASE_SCHEMA = "execution_lease_v1"
_TERMINAL_SCHEMA = "execution_lease_terminal_v1"
_LEASE_FIELDS = {
    "schema",
    "lease_id",
    "hostname",
    "pid",
    "stage",
    "attempt_id",
    "started_utc",
}

ProcessProbe = Callable[[int], bool | None]
Clock = Callable[[], datetime]


class ExecutionLeaseError(RuntimeError):
    """Base error for execution-lease operations."""


class ExecutionLeaseUnavailable(ExecutionLeaseError):
    """Raised when an existing lease cannot be taken over safely."""

    def __init__(
        self,
        message: str,
        *,
        active_payload: Mapping[str, object] | None = None,
    ) -> None:
        super().__init__(message)
        self.active_payload = (
            dict(active_payload) if active_payload is not None else None
        )


class ExecutionLeaseOwnershipError(ExecutionLeaseError):
    """Raised when a lease holder no longer owns the active lease."""


def probe_process(pid: int) -> bool | None:
    """Return whether ``pid`` is alive, or ``None`` when it is unknowable."""

    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("pid must be a positive integer")
    if os.name == "nt":
        return _probe_windows_process(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return None
    except OSError:
        return None
    return True


def _probe_windows_process(pid: int) -> bool | None:
    from ctypes import wintypes

    process_query_limited_information = 0x1000
    error_access_denied = 5
    error_invalid_parameter = 87
    still_active = 259
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    open_process = kernel32.OpenProcess
    open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
    open_process.restype = wintypes.HANDLE
    get_exit_code = kernel32.GetExitCodeProcess
    get_exit_code.argtypes = (wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD))
    get_exit_code.restype = wintypes.BOOL
    close_handle = kernel32.CloseHandle
    close_handle.argtypes = (wintypes.HANDLE,)
    close_handle.restype = wintypes.BOOL

    handle = open_process(process_query_limited_information, False, pid)
    if not handle:
        error = ctypes.get_last_error()
        if error == error_invalid_parameter:
            return False
        if error == error_access_denied:
            return None
        return None
    try:
        exit_code = wintypes.DWORD()
        if not get_exit_code(handle, ctypes.byref(exit_code)):
            return None
        return exit_code.value == still_active
    finally:
        close_handle(handle)


class ParentProcessWatchdog:
    """Terminate an isolated worker when its registered parent disappears."""

    def __init__(
        self,
        parent_pid: int,
        *,
        interval_seconds: float,
        process_probe: ProcessProbe = probe_process,
        exit_process: Callable[[int], object] = os._exit,
    ) -> None:
        if isinstance(parent_pid, bool) or not isinstance(parent_pid, int) or parent_pid <= 0:
            raise ValueError("parent_pid must be a positive integer")
        if not isinstance(interval_seconds, (int, float)) or float(interval_seconds) <= 0:
            raise ValueError("watchdog interval must be positive")
        self._parent_pid = parent_pid
        self._interval_seconds = float(interval_seconds)
        self._process_probe = process_probe
        self._exit_process = exit_process
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def __enter__(self) -> ParentProcessWatchdog:
        try:
            initial_state = self._process_probe(self._parent_pid)
        except Exception as error:
            raise RuntimeError("Parent process liveness cannot be determined") from error
        if initial_state is not True:
            raise RuntimeError("Registered parent process is not confirmed alive")

        def watch() -> None:
            while not self._stop.wait(self._interval_seconds):
                try:
                    state = self._process_probe(self._parent_pid)
                except Exception:
                    state = None
                if state is not True:
                    self._exit_process(70 if state is False else 71)
                    return

        self._thread = threading.Thread(
            target=watch,
            name=f"parent-watchdog-{self._parent_pid}",
            daemon=True,
        )
        self._thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds + 1.0)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _timestamp(clock: Clock) -> str:
    observed = clock()
    if observed.tzinfo is None or observed.utcoffset() is None:
        raise ValueError("execution lease timestamps must be timezone-aware")
    return observed.astimezone(timezone.utc).isoformat()


def _required_text(value: object, *, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    encoded = (
        json.dumps(
            dict(payload),
            allow_nan=False,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    with path.open("xb") as output:
        output.write(encoded)
        output.flush()
        os.fsync(output.fileno())


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Execution lease artifact is not an object: {path}")
    return payload


def _validate_lease(payload: Mapping[str, object]) -> dict[str, object]:
    if set(payload) != _LEASE_FIELDS or payload.get("schema") != _LEASE_SCHEMA:
        raise ValueError("Execution lease schema drifted")
    lease_id = _required_text(payload.get("lease_id"), label="lease_id")
    if re.fullmatch(r"[0-9a-f]{32}", lease_id) is None:
        raise ValueError("Execution lease ID drifted")
    hostname = _required_text(payload.get("hostname"), label="hostname")
    stage = _required_text(payload.get("stage"), label="stage")
    attempt_id = _required_text(payload.get("attempt_id"), label="attempt_id")
    pid = payload.get("pid")
    if isinstance(pid, bool) or not isinstance(pid, int) or pid <= 0:
        raise ValueError("Execution lease PID drifted")
    started_utc = _required_text(payload.get("started_utc"), label="started_utc")
    parsed = datetime.fromisoformat(started_utc)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("Execution lease start timestamp drifted")
    return {
        "schema": _LEASE_SCHEMA,
        "lease_id": lease_id,
        "hostname": hostname,
        "pid": pid,
        "stage": stage,
        "attempt_id": attempt_id,
        "started_utc": started_utc,
    }


def _read_active(active_path: Path) -> dict[str, object]:
    if not active_path.is_dir() or active_path.is_symlink():
        raise ExecutionLeaseUnavailable(
            f"Active execution lease cannot be identified safely: {active_path}"
        )
    try:
        if {path.name for path in active_path.iterdir()} != {"lease.json"}:
            raise ValueError("Active execution lease inventory drifted")
        return _validate_lease(_load_json(active_path / "lease.json"))
    except (OSError, ValueError, json.JSONDecodeError) as error:
        raise ExecutionLeaseUnavailable(
            f"Active execution lease cannot be identified safely: {active_path}"
        ) from error


def _history_terminal(
    lease_payload: Mapping[str, object],
    *,
    status: str,
    ended_utc: str,
    error: BaseException | None = None,
    detected_by: Mapping[str, object] | None = None,
) -> dict[str, object]:
    terminal: dict[str, object] = {
        "schema": _TERMINAL_SCHEMA,
        "lease_id": lease_payload["lease_id"],
        "status": status,
        "ended_utc": ended_utc,
        "error_type": None,
        "error_message": None,
    }
    if error is not None:
        terminal["error_type"] = type(error).__name__
        terminal["error_message"] = str(error) or repr(error)
    if detected_by is not None:
        terminal.update(
            {
                "liveness": "not_running",
                "detected_by_lease_id": detected_by["lease_id"],
                "detected_by_hostname": detected_by["hostname"],
                "detected_by_pid": detected_by["pid"],
                "detected_by_stage": detected_by["stage"],
                "detected_by_attempt_id": detected_by["attempt_id"],
            }
        )
    return terminal


def _archive_stale_lease(
    root: Path,
    observed: Mapping[str, object],
    successor: Mapping[str, object],
    *,
    clock: Clock,
) -> Path:
    history_root = root / "history"
    history_root.mkdir(parents=True, exist_ok=True)
    destination = history_root / f"{observed['lease_id']}.stale_takeover"
    if destination.exists():
        raise ExecutionLeaseUnavailable(
            "Stale takeover evidence already exists; prior takeover is unresolved",
            active_payload=observed,
        )
    staging = Path(tempfile.mkdtemp(dir=history_root, prefix=".stale-processing-"))
    try:
        _write_json(staging / "lease.json", observed)
        _write_json(
            staging / "terminal.json",
            _history_terminal(
                observed,
                status="stale_takeover",
                ended_utc=_timestamp(clock),
                detected_by=successor,
            ),
        )
        try:
            staging.rename(destination)
        except OSError as error:
            if destination.exists():
                raise ExecutionLeaseUnavailable(
                    "Another process already recorded this stale takeover",
                    active_payload=observed,
                ) from error
            raise
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return destination


def _retire_stale_active(
    root: Path,
    observed: Mapping[str, object],
) -> None:
    active_path = root / "active"
    retired = root / f".retired-{observed['lease_id']}-{uuid.uuid4().hex}"
    try:
        active_path.rename(retired)
    except OSError as error:
        raise ExecutionLeaseUnavailable(
            "Active execution lease changed during stale takeover",
            active_payload=observed,
        ) from error
    try:
        retired_payload = _validate_lease(_load_json(retired / "lease.json"))
        if retired_payload != dict(observed):
            if not active_path.exists():
                retired.rename(active_path)
            raise ExecutionLeaseUnavailable(
                "Active execution lease changed during stale takeover",
                active_payload=retired_payload,
            )
    except (OSError, ValueError, json.JSONDecodeError) as error:
        if retired.exists() and not active_path.exists():
            retired.rename(active_path)
        raise ExecutionLeaseUnavailable(
            "Retired execution lease could not be verified",
            active_payload=observed,
        ) from error
    shutil.rmtree(retired)


class ExecutionLease:
    """One owned execution lease rooted at ``root/active``."""

    def __init__(
        self,
        root: Path,
        payload: Mapping[str, object],
        *,
        clock: Clock,
    ) -> None:
        self.root = root
        self._payload = dict(payload)
        self._clock = clock
        self._released = False
        self._history_path: Path | None = None

    @property
    def active_path(self) -> Path:
        return self.root / "active"

    @property
    def active_payload(self) -> dict[str, object]:
        return dict(self._payload)

    @property
    def history_path(self) -> Path | None:
        return self._history_path

    @classmethod
    def acquire(
        cls,
        root: Path,
        *,
        stage: str,
        attempt_id: str,
        pid: int | None = None,
        hostname: str | None = None,
        process_probe: ProcessProbe | None = None,
        now: Clock | None = None,
    ) -> ExecutionLease:
        lease_root = Path(root)
        lease_root.mkdir(parents=True, exist_ok=True)
        (lease_root / "history").mkdir(parents=True, exist_ok=True)
        owner_pid = os.getpid() if pid is None else pid
        if (
            isinstance(owner_pid, bool)
            or not isinstance(owner_pid, int)
            or owner_pid <= 0
        ):
            raise ValueError("pid must be a positive integer")
        owner_hostname = _required_text(
            socket.gethostname() if hostname is None else hostname,
            label="hostname",
        )
        owner_stage = _required_text(stage, label="stage")
        owner_attempt = _required_text(attempt_id, label="attempt_id")
        clock = _utc_now if now is None else now
        probe = probe_process if process_probe is None else process_probe
        payload: dict[str, object] = {
            "schema": _LEASE_SCHEMA,
            "lease_id": uuid.uuid4().hex,
            "hostname": owner_hostname,
            "pid": owner_pid,
            "stage": owner_stage,
            "attempt_id": owner_attempt,
            "started_utc": _timestamp(clock),
        }
        active_path = lease_root / "active"
        while True:
            try:
                active_path.mkdir()
            except FileExistsError:
                observed = _read_active(active_path)
                if str(observed["hostname"]).casefold() != owner_hostname.casefold():
                    raise ExecutionLeaseUnavailable(
                        "Active execution lease belongs to another host",
                        active_payload=observed,
                    )
                try:
                    state = probe(int(observed["pid"]))
                except Exception as error:
                    raise ExecutionLeaseUnavailable(
                        "Active execution lease liveness cannot be determined",
                        active_payload=observed,
                    ) from error
                if state is True:
                    raise ExecutionLeaseUnavailable(
                        "Active execution lease owner is still running",
                        active_payload=observed,
                    )
                if state is not False:
                    raise ExecutionLeaseUnavailable(
                        "Active execution lease liveness cannot be determined",
                        active_payload=observed,
                    )
                _archive_stale_lease(lease_root, observed, payload, clock=clock)
                _retire_stale_active(lease_root, observed)
                continue
            try:
                _write_json(active_path / "lease.json", payload)
            except BaseException:
                if active_path.exists():
                    shutil.rmtree(active_path)
                raise
            return cls(lease_root, payload, clock=clock)

    def release(self, error: BaseException | None = None) -> Path:
        if self._released:
            if self._history_path is None:
                raise ExecutionLeaseOwnershipError(
                    "Released lease lost its history path"
                )
            return self._history_path
        try:
            observed = _validate_lease(_load_json(self.active_path / "lease.json"))
        except (OSError, ValueError, json.JSONDecodeError) as cause:
            raise ExecutionLeaseOwnershipError(
                "Active execution lease cannot be verified during release"
            ) from cause
        if observed != self._payload:
            raise ExecutionLeaseOwnershipError(
                "Active execution lease ownership drifted before release"
            )
        status = "released" if error is None else "failed"
        terminal = _history_terminal(
            self._payload,
            status=status,
            ended_utc=_timestamp(self._clock),
            error=error,
        )
        terminal_path = self.active_path / "terminal.json"
        if terminal_path.exists():
            if _load_json(terminal_path) != terminal:
                raise ExecutionLeaseOwnershipError(
                    "Execution lease terminal record drifted"
                )
        else:
            _write_json(terminal_path, terminal)
        destination = self.root / "history" / f"{self._payload['lease_id']}.{status}"
        if destination.exists():
            raise ExecutionLeaseOwnershipError(
                "Execution lease history destination already exists"
            )
        try:
            self.active_path.rename(destination)
        except OSError as cause:
            raise ExecutionLeaseOwnershipError(
                "Execution lease could not be archived during release"
            ) from cause
        self._released = True
        self._history_path = destination
        return destination

    def __enter__(self) -> ExecutionLease:
        return self

    def __exit__(
        self,
        _error_type: type[BaseException] | None,
        error: BaseException | None,
        _traceback: object,
    ) -> None:
        self.release(error)


__all__ = [
    "ExecutionLease",
    "ExecutionLeaseError",
    "ExecutionLeaseOwnershipError",
    "ExecutionLeaseUnavailable",
    "ParentProcessWatchdog",
    "probe_process",
]
