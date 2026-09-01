"""Closed, reviewable execution controller/worker successor v1.

The fixed execution-review receipt is intentionally absent.  Therefore the
production route rejects before pipe creation, Popen, or scientific imports.
Only the exact non-accepting pre-loader transport may run during review.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import secrets
import stat
import subprocess
import sys
import threading
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import MappingProxyType
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v1.OUTER.SHA256SUMS.json"
EXECUTION_REVIEW_RECEIPT = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v1.json"
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
WORKER_MODULE = "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v1"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")
EXECUTION_REVIEW_REQUIRED = True
MAX_FRAME = 256 * 1024 * 1024


class SuccessorRejected(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewOutcome:
    status: str
    accepted: bool
    child_pid: int
    counters: Mapping[str, int]
    mathematical_infeasibility_inferred: bool


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _resource_authority() -> Any:
    """Import the sealed v5 resource authority only after the execution gate."""
    from experiments import (
        run_rq2_public_grid_two_block_pilot_activation_transport_v5 as authority,
    )

    return authority


def _load_config() -> dict[str, Any]:
    try:
        value = json.loads(CONFIG.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        raise SuccessorRejected("successor config unreadable") from exc
    if not isinstance(value, dict) or value.get("status") != "execution_controller_successor_v1_review_closed":
        raise SuccessorRejected("successor config identity drifted")
    return value


def _strict_file_bytes(path: Path, label: str) -> bytes:
    if not path.is_absolute() or any(part in {".", ".."} for part in path.parts):
        raise SuccessorRejected(f"{label} path is not canonical absolute")
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            metadata = os.lstat(current)
        except OSError as exc:
            raise SuccessorRejected(f"{label} path unavailable") from exc
        attributes = int(getattr(metadata, "st_file_attributes", 0))
        if stat.S_ISLNK(metadata.st_mode) or attributes & 0x400:
            raise SuccessorRejected(f"{label} alias/reparse rejected")
    if not stat.S_ISREG(os.lstat(path).st_mode):
        raise SuccessorRejected(f"{label} is not an ordinary file")
    first = path.read_bytes()
    second = path.read_bytes()
    if first != second:
        raise SuccessorRejected(f"{label} changed during double-read")
    return first


def _load_execution_authority() -> Mapping[str, Any]:
    """Load only the fixed receipt; no caller path/hash is accepted."""
    config = _load_config()
    raw = _strict_file_bytes(EXECUTION_REVIEW_RECEIPT, "execution review receipt")
    try:
        receipt = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SuccessorRejected("execution review receipt malformed") from exc
    expected = config["fixed_execution_review"]
    if (
        not isinstance(receipt, dict)
        or receipt.get("schema") != expected["schema"]
        or receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_outer")
        != {
            "path": OUTER.relative_to(ROOT).as_posix(),
            "sha256": _sha256(OUTER),
        }
        or receipt.get("bound_chain") != config["chain_authority"]
        or receipt.get("effect")
        != {
            "successor_execution_review_passed": True,
            "two_block_nonformal_pilot_execution_authorized": True,
            "formal_execution_authorized": False,
            "claim": False,
            "security_certified": False,
        }
    ):
        raise SuccessorRejected("fixed execution review receipt is absent or inexact")
    return MappingProxyType(
        {
            "receipt": receipt,
            "receipt_sha256": hashlib.sha256(raw).hexdigest(),
            "successor_outer_sha256": _sha256(OUTER),
        }
    )


def _require_bootstrap_runtime(config: Mapping[str, Any]) -> None:
    runtime = config["runtime"]
    expected = [
        runtime["locked_python_executable"],
        "-B",
        "-m",
        config["successor_identity"]["bootstrap_module"],
        "--execute",
    ]
    if (
        list(sys.orig_argv) != expected
        or sys.executable != runtime["locked_python_executable"]
        or str(Path.cwd()) != runtime["exact_cwd"]
        or dict(os.environ) != runtime["sanitized_environment"]
    ):
        raise SuccessorRejected("exact reviewed bootstrap runtime is required")


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    remaining = count
    while remaining:
        chunk = os.read(descriptor, remaining)
        if not chunk:
            raise SuccessorRejected("capability pipe closed early")
        chunks.append(chunk)
        remaining -= len(chunk)
    return b"".join(chunks)


def _write_frame(descriptor: int, value: object) -> bytes:
    payload = _canonical_bytes(value)
    if len(payload) > MAX_FRAME:
        raise SuccessorRejected("capability frame too large")
    frame = len(payload).to_bytes(8, "big") + payload
    offset = 0
    while offset < len(frame):
        offset += os.write(descriptor, frame[offset:])
    return payload


def _read_frame(descriptor: int) -> tuple[bytes, dict[str, Any]]:
    size = int.from_bytes(_read_exact(descriptor, 8), "big")
    if size <= 0 or size > MAX_FRAME:
        raise SuccessorRejected("capability frame length invalid")
    payload = _read_exact(descriptor, size)
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SuccessorRejected("capability frame JSON invalid") from exc
    if not isinstance(value, dict):
        raise SuccessorRejected("capability frame is not an object")
    return payload, value


def _worker_command(config: Mapping[str, Any], read_handle: int, ack_handle: int) -> list[str]:
    return [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        WORKER_MODULE,
        "--internal-successor-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _spawn_exact(config: Mapping[str, Any], read_handle: int, ack_handle: int) -> subprocess.Popen[Any]:
    command = _worker_command(config, read_handle, ack_handle)
    kwargs: dict[str, Any] = {
        "cwd": config["runtime"]["exact_cwd"],
        "env": dict(config["runtime"]["sanitized_environment"]),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        for handle in (read_handle, ack_handle):
            os.set_handle_inheritable(handle, True)
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": [read_handle, ack_handle]}
        kwargs["startupinfo"] = startup
    else:
        for descriptor in (read_handle, ack_handle):
            os.set_inheritable(descriptor, True)
        kwargs["pass_fds"] = (read_handle, ack_handle)
    try:
        return subprocess.Popen(command, **kwargs)
    finally:
        if os.name == "nt":
            for handle in (read_handle, ack_handle):
                os.set_handle_inheritable(handle, False)
        else:
            for descriptor in (read_handle, ack_handle):
                os.set_inheritable(descriptor, False)


def _validate_hello(hello: Mapping[str, Any], process: subprocess.Popen[Any], config: Mapping[str, Any]) -> int:
    authority = _resource_authority()
    created = authority.predecessor._process_creation_time_ns(process.pid)
    identity = config["successor_identity"]
    if (
        hello.get("schema") != "rq2_execution_successor_worker_hello_v1"
        or hello.get("pid") != process.pid
        or hello.get("ppid") != os.getpid()
        or hello.get("create_time_ns") != created
        or hello.get("worker_module") != WORKER_MODULE
        or hello.get("worker_sha256") != identity["worker_sha256"]
        or hello.get("config_sha256") != _sha256(CONFIG)
    ):
        raise SuccessorRejected("successor worker HELLO authority drifted")
    return created


def _output_paths(config: Mapping[str, Any], block_id: str, nonce: str) -> tuple[Path, Path]:
    root = ROOT / config["paths"]["worker_root"] / block_id / nonce
    return root / "payload.json", root / "attempt_receipt.json"


def _build_envelope(
    *,
    config: Mapping[str, Any],
    process: subprocess.Popen[Any],
    child_create_ns: int,
    execution_index: int,
    mode: str,
    ledger: Any | None,
    authority: Mapping[str, Any] | None,
    read_handle: int,
    ack_handle: int,
) -> dict[str, Any]:
    resource_authority = _resource_authority()
    nonce = secrets.token_hex(32)
    block_id = BLOCKS[execution_index - 1]
    payload_path, receipt_path = _output_paths(config, block_id, nonce)
    predecessor_binding = None if ledger is None else ledger.predecessor_for(execution_index)
    ledger_digest = _canonical_sha256([]) if ledger is None else ledger.digest
    parent_identity = {
        "pid": os.getpid(),
        "create_time_ns": resource_authority.predecessor._process_creation_time_ns(
            os.getpid()
        ),
        "executable_path": config["runtime"]["locked_python_executable"],
        "executable_sha256": config["runtime"]["locked_python_sha256"],
        "command": list(sys.orig_argv),
    }
    worker_identity = {
        "pid": process.pid,
        "create_time_ns": child_create_ns,
        "executable_path": config["runtime"]["locked_python_executable"],
        "executable_sha256": config["runtime"]["locked_python_sha256"],
        "command": _worker_command(config, read_handle, ack_handle),
    }
    return {
        "schema": "rq2_execution_successor_capability_v1",
        "authority": config["chain_authority"],
        "mode": mode,
        "nonce": nonce,
        "issued_ns": time.time_ns(),
        "block_id": block_id,
        "execution_index": execution_index,
        "predecessor_accepted_evidence": predecessor_binding,
        "ledger_digest_before": ledger_digest,
        "parent_pid": parent_identity["pid"],
        "parent_create_time_ns": parent_identity["create_time_ns"],
        "parent_process_identity": parent_identity,
        "worker_pid": process.pid,
        "worker_create_time_ns": child_create_ns,
        "worker_process_identity": worker_identity,
        "worker_command": _worker_command(config, read_handle, ack_handle),
        "working_directory": str(ROOT),
        "sanitized_environment": config["runtime"]["sanitized_environment"],
        "controller_sha256": config["successor_identity"]["controller_sha256"],
        "worker_sha256": config["successor_identity"]["worker_sha256"],
        "config_sha256": _sha256(CONFIG),
        "worker_payload_path": str(payload_path),
        "attempt_receipt_path": str(receipt_path),
        "execution_authority": None if authority is None else dict(authority),
    }


def _cleanup_child(process: subprocess.Popen[Any], created: int) -> None:
    if process.poll() is None:
        resource_authority = _resource_authority()
        resource_authority.terminate_exact_owned_child(
            process, expected_pid=process.pid, expected_create_time_ns=created
        )


def _dispatch_transport(
    *,
    execution_index: int,
    mode: str,
    ledger: Any | None,
    authority: Mapping[str, Any] | None,
    timeout_seconds: float,
) -> tuple[ReviewOutcome | Any, dict[str, Any]]:
    config = _load_config()
    controller_read, worker_write = os.pipe()
    worker_read, controller_write = os.pipe()
    process: subprocess.Popen[Any] | None = None
    created = 0
    worker_read_authority = worker_read
    worker_write_authority = worker_write
    if os.name == "nt":
        import msvcrt

        worker_read_authority = msvcrt.get_osfhandle(worker_read)
        worker_write_authority = msvcrt.get_osfhandle(worker_write)
    try:
        process = _spawn_exact(config, worker_read_authority, worker_write_authority)
        os.close(worker_read)
        worker_read = -1
        os.close(worker_write)
        worker_write = -1
        _hello_bytes, hello = _read_frame(controller_read)
        created = _validate_hello(hello, process, config)
        envelope = _build_envelope(
            config=config,
            process=process,
            child_create_ns=created,
            execution_index=execution_index,
            mode=mode,
            ledger=ledger,
            authority=authority,
            read_handle=worker_read_authority,
            ack_handle=worker_write_authority,
        )
        envelope_bytes = _write_frame(controller_write, envelope)
        os.close(controller_write)
        controller_write = -1
        if mode == "review_only_preloader_stop":
            ack_bytes, ack = _read_frame(controller_read)
            try:
                exit_code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _cleanup_child(process, created)
                raise SuccessorRejected("successor worker watchdog reached") from None
        else:
            resource_authority = _resource_authority()
            ack_box: dict[str, object] = {}

            def read_ack() -> None:
                try:
                    ack_box["value"] = _read_frame(controller_read)
                except BaseException as exc:  # noqa: BLE001 - delivered to controller
                    ack_box["error"] = exc

            reader = threading.Thread(target=read_ack, daemon=True)
            reader.start()
            resource = resource_authority.monitor_owned_child_resources(
                process,
                expected_pid=process.pid,
                expected_create_time_ns=created,
                sample_interval_seconds=float(
                    config["resources"]["sample_interval_seconds"]
                ),
                watchdog_deadline=time.monotonic() + timeout_seconds,
            )
            reader.join(timeout=1.0)
            if reader.is_alive():
                _cleanup_child(process, created)
                raise SuccessorRejected("worker ACK reader did not terminate")
            if resource.status in {"resource_stop", "sampling_error", "timeout"}:
                raise SuccessorRejected(
                    f"worker {resource.status} is honest incomplete, not infeasible"
                )
            if "error" in ack_box:
                raise SuccessorRejected("worker ACK failed honestly") from ack_box["error"]
            ack_bytes, ack = ack_box["value"]  # type: ignore[misc]
            exit_code = process.returncode
        if mode == "review_only_preloader_stop":
            if (
                exit_code != 4
                or ack.get("status") != "NON_ACCEPTED_PRELOADER_BOUNDARY"
                or ack.get("accepted") is not False
                or ack.get("envelope_sha256") != hashlib.sha256(envelope_bytes).hexdigest()
                or ack.get("counters")
                != {"loader_calls": 0, "solver_calls": 0, "result_writes": 0, "formal_writes": 0}
            ):
                raise SuccessorRejected("review-only boundary evidence drifted")
            return (
                ReviewOutcome(
                    ack["status"],
                    False,
                    process.pid,
                    MappingProxyType(dict(ack["counters"])),
                    False,
                ),
                envelope,
            )
        if exit_code != 0:
            raise SuccessorRejected("production worker failed honestly; unresolved not infeasible")
        from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

        payload_path = Path(envelope["worker_payload_path"])
        receipt_path = Path(envelope["attempt_receipt_path"])
        scientific = v4._validate_worker_result(payload_path, receipt_path, envelope=envelope)
        expected_ack = v4._build_ack(envelope)
        if ack != expected_ack:
            raise SuccessorRejected("production ACK differs from sealed v4 adapter")
        identity = dict(envelope["worker_process_identity"])
        provisional = v4.AcceptedEvidence(
            block_id=envelope["block_id"],
            execution_index=execution_index,
            nonce=envelope["nonce"],
            envelope_bytes=_canonical_bytes(envelope),
            envelope_sha256=_canonical_sha256(envelope),
            ack_bytes=ack_bytes,
            ack_sha256=hashlib.sha256(ack_bytes).hexdigest(),
            popen_pid=process.pid,
            worker_creation_identity_bytes=_canonical_bytes(identity),
            source_payload_path=payload_path,
            source_payload_sha256=_sha256(payload_path),
            source_attempt_receipt_path=receipt_path,
            source_attempt_receipt_sha256=_sha256(receipt_path),
            scientific_payload_sha256=_canonical_sha256(scientific),
            predecessor_accepted_evidence_digest=(
                None if execution_index == 1 else ledger.records[0].accepted_evidence_digest
            ),
            accepted_evidence_digest="",
        )
        evidence = dataclasses.replace(
            provisional,
            accepted_evidence_digest=v4._expected_accepted_digest(provisional),
        )
        ledger.accept(evidence)
        return evidence, envelope
    finally:
        for descriptor in (controller_read, worker_write, worker_read, controller_write):
            if descriptor >= 0:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
        if process is not None and process.poll() is None:
            resource_authority = _resource_authority()
            if not created:
                created = resource_authority.predecessor._process_creation_time_ns(process.pid)
            _cleanup_child(process, created)


class ControllerSession:
    """Fixed-order, single-active, no-retry two-block controller."""

    __slots__ = ("_active", "_attempted", "_lock")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempted: set[int] = set()
        self._active: int | None = None

    @property
    def attempted_indices(self) -> frozenset[int]:
        with self._lock:
            return frozenset(self._attempted)

    def _consume(self, index: int) -> None:
        with self._lock:
            if self._active is not None or index in self._attempted:
                raise SuccessorRejected("single-active/no-retry attempt gate rejected")
            self._attempted.add(index)
            self._active = index

    def _finish(self) -> None:
        with self._lock:
            self._active = None

    def run_review_preloader_boundary(self, *, timeout_seconds: float = 10.0) -> ReviewOutcome:
        self._consume(1)
        try:
            outcome, _envelope = _dispatch_transport(
                execution_index=1,
                mode="review_only_preloader_stop",
                ledger=None,
                authority=None,
                timeout_seconds=timeout_seconds,
            )
            if not isinstance(outcome, ReviewOutcome):
                raise SuccessorRejected("review boundary returned production evidence")
            return outcome
        finally:
            self._finish()

    def run_two_block_pilot(self) -> dict[str, object]:
        authority = _load_execution_authority()
        config = _load_config()
        _require_bootstrap_runtime(config)
        resource_authority = _resource_authority()
        resource_authority.preflight_available_commit(
            child_limit_bytes=8 * resource_authority.GIB,
            reserve_bytes=2 * resource_authority.GIB,
        )
        from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4
        from experiments import run_rq2_public_grid_two_block_pilot_candidate_v7 as v7

        ledger = v4.ControllerLedger()
        for index in (1, 2):
            self._consume(index)
            try:
                _dispatch_transport(
                    execution_index=index,
                    mode="production",
                    ledger=ledger,
                    authority=authority,
                    timeout_seconds=float(config["resources"]["watchdog_seconds"]),
                )
            finally:
                self._finish()
        if len(ledger.records) != 2:
            raise SuccessorRejected("publication requires exact accepted 0008 and 0009")
        roots = config["paths"]
        publication_config = v7._publication_config()
        controller = v4._build_controller_receipt(publication_config, ledger)
        outcome = v7._publish_result(
            ROOT / roots["publication_staging"],
            ROOT / roots["result_root"],
            ROOT / roots["success_root"],
            ROOT / roots["terminal_root"],
            config=publication_config,
            controller=controller,
            ledger=ledger,
        )
        if outcome.get("classification") != "committed_success":
            raise SuccessorRejected("sealed v7 publication did not commit exact success")
        return outcome


@dataclasses.dataclass(frozen=True, slots=True)
class RegisteredOrchestrationSeam:
    dispatch: Callable[[str, int, str | None], Mapping[str, Any]]
    publish_v7: Callable[[tuple[Mapping[str, Any], ...]], Mapping[str, Any]]
    nonce: str


_SEAMS: set[str] = set()


def register_zero_solver_orchestration_seam(
    *,
    dispatch: Callable[[str, int, str | None], Mapping[str, Any]],
    publish_v7: Callable[[tuple[Mapping[str, Any], ...]], Mapping[str, Any]],
) -> RegisteredOrchestrationSeam:
    nonce = secrets.token_hex(32)
    _SEAMS.add(nonce)
    return RegisteredOrchestrationSeam(dispatch, publish_v7, nonce)


def audit_zero_solver_orchestration(seam: RegisteredOrchestrationSeam) -> Mapping[str, Any]:
    if type(seam) is not RegisteredOrchestrationSeam or seam.nonce not in _SEAMS:
        raise SuccessorRejected("orchestration seam is unregistered or replayed")
    _SEAMS.remove(seam.nonce)
    records: list[Mapping[str, Any]] = []
    predecessor: str | None = None
    for index, block_id in enumerate(BLOCKS, start=1):
        record = dict(seam.dispatch(block_id, index, predecessor))
        if (
            record.get("block_id") != block_id
            or record.get("execution_index") != index
            or record.get("predecessor_digest") != predecessor
            or record.get("accepted") is not True
            or record.get("all_hours_resolved") is not True
            or record.get("certificate_valid") is not True
            or record.get("mathematical_infeasibility_inferred") is not False
        ):
            raise SuccessorRejected("zero-solver orchestration evidence unresolved")
        predecessor = _canonical_sha256(record)
        records.append(MappingProxyType(record))
    publication = dict(seam.publish_v7(tuple(records)))
    if publication != {
        "publisher": "sealed_v7_unified_snapshot_atomic_publication",
        "classification": "committed_success_shape_only",
        "writes": 0,
    }:
        raise SuccessorRejected("zero-solver publication invocation shape drifted")
    return MappingProxyType(
        {
            "blocks": BLOCKS,
            "dispatch_calls": 2,
            "publication_calls": 1,
            "solver_calls": 0,
            "writes": 0,
            "accepted_for_execution": False,
            "mathematical_infeasibility_inferred": False,
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--validate-only"]:
        print(
            json.dumps(
                {
                    "validation_passed": True,
                    "execution_review_present": EXECUTION_REVIEW_RECEIPT.exists(),
                    "execution_ready": False,
                    "project_science_imports": 0,
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
    if arguments == ["--review-preloader"]:
        outcome = ControllerSession().run_review_preloader_boundary()
        print(json.dumps(dataclasses.asdict(outcome), sort_keys=True))
        return 0
    if arguments == ["--execute"]:
        ControllerSession().run_two_block_pilot()
        return 0
    raise SuccessorRejected("successor argv is not registered")


if __name__ == "__main__":
    raise SystemExit(main())
