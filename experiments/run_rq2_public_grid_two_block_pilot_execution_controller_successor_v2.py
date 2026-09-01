"""Review-closed execution controller successor v2 with live dependency closure."""

from __future__ import annotations

import dataclasses
import hashlib
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

from experiments import rq2_public_grid_execution_dependency_closure_v2 as closure

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.json"
INNER = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.OUTER.SHA256SUMS.json"
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v2.json"
MODULE = "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
WORKER_MODULE = "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")
MAX_FRAME = 256 * 1024 * 1024


class SuccessorV2Rejected(RuntimeError):
    """A fail-closed successor-v2 rejection."""


@dataclasses.dataclass(frozen=True, slots=True)
class ReviewOutcome:
    status: str
    accepted: bool
    child_pid: int
    counters: Mapping[str, int]
    mathematical_infeasibility_inferred: bool


def _canonical_bytes(value: object) -> bytes:
    return closure.canonical_bytes(value)


def _canonical_sha256(value: object) -> str:
    return closure.canonical_sha256(value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_config() -> dict[str, Any]:
    try:
        value = json.loads(closure.read_stable_bytes(CONFIG))
    except (closure.ClosureRejected, json.JSONDecodeError) as exc:
        raise SuccessorV2Rejected("successor-v2 config is unavailable") from exc
    if (
        not isinstance(value, dict)
        or value.get("status") != "execution_controller_successor_v2_review_closed"
    ):
        raise SuccessorV2Rejected("successor-v2 config identity drifted")
    return value


def verify_live_closure() -> tuple[str, ...]:
    return closure.verify_dependency_closure(ROOT, _load_config())


def _resource_authority() -> Any:
    from experiments import (
        run_rq2_public_grid_two_block_pilot_activation_transport_v5 as authority,
    )

    return authority


def _load_execution_authority() -> Mapping[str, Any]:
    config = _load_config()
    try:
        receipt, receipt_sha256 = closure.load_and_validate_review_receipt(
            REVIEW, config=config, outer_path=OUTER, root=ROOT
        )
    except closure.ClosureRejected as exc:
        raise SuccessorV2Rejected("fixed execution review receipt rejected") from exc
    return MappingProxyType(
        {
            "receipt": receipt,
            "receipt_sha256": receipt_sha256,
            "outer_sha256": _sha256(OUTER),
        }
    )


def validate_review_receipt_for_entry(
    receipt: object, *, outer_sha256: str
) -> None:
    """Controller-entry receipt seam using the exact common receipt contract."""
    config = _load_config()
    closure.validate_review_receipt_object(
        receipt,
        config=config,
        outer_relative=OUTER.relative_to(ROOT).as_posix(),
        outer_sha256=outer_sha256,
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
        raise SuccessorV2Rejected("exact reviewed successor-v2 bootstrap is required")


def solver_call_accounting(payload: Mapping[str, Any]) -> dict[str, int]:
    """Mechanically count actual calls represented by the validated payload."""
    baseline = payload.get("baseline_audit")
    outcomes = payload.get("outcomes")
    if not isinstance(baseline, dict) or not isinstance(outcomes, list) or len(outcomes) != 24:
        raise SuccessorV2Rejected("solver accounting payload inventory is malformed")
    termination = baseline.get("termination_condition")
    if not isinstance(termination, str) or not termination:
        raise SuccessorV2Rejected("baseline termination evidence is missing")
    baseline_calls = int(termination != "not_applicable_no_active_outage")
    primary_calls = 0
    confirmation_calls = 0
    for outcome in outcomes:
        if not isinstance(outcome, dict):
            raise SuccessorV2Rejected("hourly accounting outcome is malformed")
        primary = outcome.get("primary")
        certificate = outcome.get("primary_certificate")
        if not isinstance(primary, dict) or not isinstance(certificate, dict) or not certificate:
            raise SuccessorV2Rejected("primary solver/certificate evidence is incomplete")
        primary_termination = primary.get("termination_condition")
        if not isinstance(primary_termination, str) or not primary_termination:
            raise SuccessorV2Rejected("primary termination evidence is missing")
        primary_calls += int(
            primary_termination != "not_applicable_no_active_outage"
        )
        zero = outcome.get("zero_dc_confirmation")
        zero_certificate = outcome.get("zero_dc_confirmation_certificate")
        if (zero is None) != (zero_certificate is None):
            raise SuccessorV2Rejected("zero-DC solve/certificate pair is inconsistent")
        if zero is not None:
            if (
                not isinstance(zero, dict)
                or not isinstance(zero_certificate, dict)
                or not zero_certificate
                or not isinstance(zero.get("termination_condition"), str)
                or not zero["termination_condition"]
            ):
                raise SuccessorV2Rejected("zero-DC confirmation evidence is malformed")
            confirmation_calls += 1
    total = baseline_calls + primary_calls + confirmation_calls
    return {
        "baseline_solver_calls": baseline_calls,
        "primary_solver_calls": primary_calls,
        "zero_dc_confirmation_solver_calls": confirmation_calls,
        "solver_calls": total,
    }


def _read_exact(descriptor: int, count: int) -> bytes:
    chunks: list[bytes] = []
    while count:
        chunk = os.read(descriptor, count)
        if not chunk:
            raise SuccessorV2Rejected("capability pipe closed early")
        chunks.append(chunk)
        count -= len(chunk)
    return b"".join(chunks)


def _write_frame(descriptor: int, value: object) -> bytes:
    payload = _canonical_bytes(value)
    if len(payload) > MAX_FRAME:
        raise SuccessorV2Rejected("capability frame is too large")
    frame = len(payload).to_bytes(8, "big") + payload
    offset = 0
    while offset < len(frame):
        offset += os.write(descriptor, frame[offset:])
    return payload


def _read_frame(descriptor: int) -> tuple[bytes, dict[str, Any]]:
    size = int.from_bytes(_read_exact(descriptor, 8), "big")
    if size <= 0 or size > MAX_FRAME:
        raise SuccessorV2Rejected("capability frame length is invalid")
    raw = _read_exact(descriptor, size)
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SuccessorV2Rejected("capability frame JSON is invalid") from exc
    if not isinstance(value, dict):
        raise SuccessorV2Rejected("capability frame is not an object")
    return raw, value


def _worker_command(config: Mapping[str, Any], read_handle: int, ack_handle: int) -> list[str]:
    return [
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        WORKER_MODULE,
        "--internal-successor-v2-worker",
        "--read-handle",
        str(read_handle),
        "--ack-handle",
        str(ack_handle),
    ]


def _spawn_exact(
    config: Mapping[str, Any], read_handle: int, ack_handle: int
) -> subprocess.Popen[Any]:
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
        return subprocess.Popen(_worker_command(config, read_handle, ack_handle), **kwargs)
    finally:
        for descriptor in (read_handle, ack_handle):
            if os.name == "nt":
                os.set_handle_inheritable(descriptor, False)
            else:
                os.set_inheritable(descriptor, False)


def _output_paths(config: Mapping[str, Any], block_id: str, nonce: str) -> tuple[Path, Path]:
    root = ROOT / config["paths"]["worker_root"] / block_id / nonce
    return root / "payload.json", root / "attempt_receipt.json"


def _build_envelope(
    *,
    config: Mapping[str, Any],
    process: subprocess.Popen[Any],
    created: int,
    execution_index: int,
    mode: str,
    ledger: Any | None,
    authority: Mapping[str, Any] | None,
    read_handle: int,
    ack_handle: int,
) -> dict[str, Any]:
    resource = _resource_authority()
    nonce = secrets.token_hex(32)
    block_id = BLOCKS[execution_index - 1]
    payload_path, receipt_path = _output_paths(config, block_id, nonce)
    parent = {
        "pid": os.getpid(),
        "create_time_ns": resource.predecessor._process_creation_time_ns(os.getpid()),
        "executable_path": config["runtime"]["locked_python_executable"],
        "executable_sha256": config["runtime"]["locked_python_sha256"],
        "command": list(sys.orig_argv),
    }
    worker = {
        "pid": process.pid,
        "create_time_ns": created,
        "executable_path": config["runtime"]["locked_python_executable"],
        "executable_sha256": config["runtime"]["locked_python_sha256"],
        "command": _worker_command(config, read_handle, ack_handle),
    }
    return {
        "schema": "rq2_execution_controller_successor_capability_v2",
        "authority": closure.closure_binding(config),
        "mode": mode,
        "nonce": nonce,
        "issued_ns": time.time_ns(),
        "block_id": block_id,
        "execution_index": execution_index,
        "predecessor_accepted_evidence": (
            None if ledger is None else ledger.predecessor_for(execution_index)
        ),
        "ledger_digest_before": _canonical_sha256([]) if ledger is None else ledger.digest,
        "parent_process_identity": parent,
        "worker_process_identity": worker,
        "worker_command": worker["command"],
        "working_directory": str(ROOT),
        "sanitized_environment": config["runtime"]["sanitized_environment"],
        "controller_sha256": config["successor_identity"]["controller_sha256"],
        "worker_sha256": config["successor_identity"]["worker_sha256"],
        "closure_sha256": config["successor_identity"]["closure_sha256"],
        "config_sha256": _sha256(CONFIG),
        "worker_payload_path": str(payload_path),
        "attempt_receipt_path": str(receipt_path),
        "execution_authority": None if authority is None else dict(authority),
    }


def _cleanup(process: subprocess.Popen[Any], created: int) -> None:
    if process.poll() is None:
        _resource_authority().terminate_exact_owned_child(
            process, expected_pid=process.pid, expected_create_time_ns=created
        )


def _dispatch(
    *,
    execution_index: int,
    mode: str,
    ledger: Any | None,
    authority: Mapping[str, Any] | None,
    timeout_seconds: float,
) -> tuple[ReviewOutcome | Any, dict[str, Any]]:
    verify_live_closure()
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
        created = _resource_authority().predecessor._process_creation_time_ns(process.pid)
        if (
            hello.get("schema") != "rq2_execution_controller_successor_worker_hello_v2"
            or hello.get("pid") != process.pid
            or hello.get("ppid") != os.getpid()
            or hello.get("create_time_ns") != created
            or hello.get("worker_sha256") != config["successor_identity"]["worker_sha256"]
            or hello.get("closure_sha256") != config["successor_identity"]["closure_sha256"]
            or hello.get("config_sha256") != _sha256(CONFIG)
        ):
            raise SuccessorV2Rejected("worker HELLO authority drifted")
        envelope = _build_envelope(
            config=config,
            process=process,
            created=created,
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
            _ack_bytes, ack = _read_frame(controller_read)
            try:
                exit_code = process.wait(timeout=timeout_seconds)
            except subprocess.TimeoutExpired:
                _cleanup(process, created)
                raise SuccessorV2Rejected("review worker watchdog reached") from None
            expected_counters = {
                "loader_calls": 0,
                "solver_calls": 0,
                "result_writes": 0,
                "formal_writes": 0,
            }
            if (
                exit_code != 4
                or ack.get("status") != "NON_ACCEPTED_PRELOADER_BOUNDARY"
                or ack.get("accepted") is not False
                or ack.get("envelope_sha256")
                != hashlib.sha256(envelope_bytes).hexdigest()
                or ack.get("counters") != expected_counters
                or ack.get("dependency_closure_verified") is not True
            ):
                raise SuccessorV2Rejected("review-only evidence drifted")
            return (
                ReviewOutcome(
                    ack["status"],
                    False,
                    process.pid,
                    MappingProxyType(expected_counters),
                    False,
                ),
                envelope,
            )
        ack_box: dict[str, object] = {}

        def read_ack() -> None:
            try:
                ack_box["value"] = _read_frame(controller_read)
            except BaseException as exc:  # noqa: BLE001
                ack_box["error"] = exc

        reader = threading.Thread(target=read_ack, daemon=True)
        reader.start()
        resource = _resource_authority().monitor_owned_child_resources(
            process,
            expected_pid=process.pid,
            expected_create_time_ns=created,
            sample_interval_seconds=float(config["resources"]["sample_interval_seconds"]),
            watchdog_deadline=time.monotonic() + timeout_seconds,
        )
        reader.join(timeout=1.0)
        if reader.is_alive():
            _cleanup(process, created)
            raise SuccessorV2Rejected("worker ACK reader did not terminate")
        if resource.status != "child_exited" or "error" in ack_box:
            raise SuccessorV2Rejected("worker stopped honestly incomplete, not infeasible")
        ack_bytes, ack = ack_box["value"]  # type: ignore[misc]
        if process.returncode != 0:
            raise SuccessorV2Rejected("worker nonzero is honest incomplete, not infeasible")
        from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

        payload_path = Path(envelope["worker_payload_path"])
        receipt_path = Path(envelope["attempt_receipt_path"])
        scientific = v4._validate_worker_result(payload_path, receipt_path, envelope=envelope)
        result = json.loads(payload_path.read_bytes())
        accounting = solver_call_accounting(scientific)
        if result.get("solver_call_accounting") != accounting:
            raise SuccessorV2Rejected("worker solver-call accounting mismatch")
        expected_ack = v4._build_ack(envelope)
        if ack != expected_ack:
            raise SuccessorV2Rejected("worker ACK differs from sealed v4 adapter")
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
            if not created:
                created = _resource_authority().predecessor._process_creation_time_ns(
                    process.pid
                )
            _cleanup(process, created)


def review_preloader_closure_gate() -> tuple[str, ...]:
    """Review seam proving closure precedes pipe creation."""
    return verify_live_closure()


class ControllerSession:
    __slots__ = ("_active", "_attempted", "_lock")

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempted: set[int] = set()
        self._active: int | None = None

    def _consume(self, index: int) -> None:
        with self._lock:
            if self._active is not None or index in self._attempted:
                raise SuccessorV2Rejected("single-active/no-retry gate rejected")
            self._attempted.add(index)
            self._active = index

    def _finish(self) -> None:
        with self._lock:
            self._active = None

    def run_review_preloader_boundary(self, timeout_seconds: float = 10.0) -> ReviewOutcome:
        self._consume(1)
        try:
            outcome, _envelope = _dispatch(
                execution_index=1,
                mode="review_only_preloader_stop",
                ledger=None,
                authority=None,
                timeout_seconds=timeout_seconds,
            )
            if not isinstance(outcome, ReviewOutcome):
                raise SuccessorV2Rejected("review worker returned production evidence")
            return outcome
        finally:
            self._finish()

    def run_two_block_pilot(self) -> Mapping[str, Any]:
        authority = _load_execution_authority()
        verify_live_closure()
        config = _load_config()
        _require_bootstrap_runtime(config)
        resource = _resource_authority()
        resource.preflight_available_commit(
            child_limit_bytes=8 * resource.GIB, reserve_bytes=2 * resource.GIB
        )
        from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4
        from experiments import run_rq2_public_grid_two_block_pilot_candidate_v7 as v7

        ledger = v4.ControllerLedger()
        for index in (1, 2):
            self._consume(index)
            try:
                _dispatch(
                    execution_index=index,
                    mode="production",
                    ledger=ledger,
                    authority=authority,
                    timeout_seconds=float(config["resources"]["watchdog_seconds"]),
                )
            finally:
                self._finish()
        publication_config = v7._publication_config()
        controller = v4._build_controller_receipt(publication_config, ledger)
        roots = config["paths"]
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
            raise SuccessorV2Rejected("v7 publication did not commit exact success")
        return outcome


@dataclasses.dataclass(frozen=True, slots=True)
class RegisteredLiveOrchestrationSeam:
    payloads: Callable[[], tuple[Mapping[str, Any], Mapping[str, Any]]]
    validate_payload: Callable[[Mapping[str, Any], str], Mapping[str, Any]]
    publish: Callable[[tuple[dict[str, Any], ...]], Mapping[str, Any]]
    nonce: str


_REGISTERED_SEAMS: set[str] = set()


def register_zero_solver_live_orchestration_seam(
    *,
    payloads: Callable[[], tuple[Mapping[str, Any], Mapping[str, Any]]],
    validate_payload: Callable[[Mapping[str, Any], str], Mapping[str, Any]],
    publish: Callable[[tuple[dict[str, Any], ...]], Mapping[str, Any]],
) -> RegisteredLiveOrchestrationSeam:
    nonce = secrets.token_hex(32)
    _REGISTERED_SEAMS.add(nonce)
    return RegisteredLiveOrchestrationSeam(payloads, validate_payload, publish, nonce)


def audit_zero_solver_live_orchestration(
    seam: RegisteredLiveOrchestrationSeam,
) -> Mapping[str, Any]:
    if type(seam) is not RegisteredLiveOrchestrationSeam or seam.nonce not in _REGISTERED_SEAMS:
        raise SuccessorV2Rejected("live orchestration seam is unregistered or replayed")
    _REGISTERED_SEAMS.remove(seam.nonce)
    verify_live_closure()
    payloads = seam.payloads()
    if not isinstance(payloads, tuple) or len(payloads) != 2:
        raise SuccessorV2Rejected("live seam requires exact two payloads")
    records: list[dict[str, Any]] = []
    accounted: list[int] = []
    predecessor: str | None = None
    for index, (block_id, payload) in enumerate(zip(BLOCKS, payloads, strict=True), start=1):
        validated = seam.validate_payload(payload, block_id)
        if not isinstance(validated, Mapping):
            raise SuccessorV2Rejected("registered scientific validator returned malformed payload")
        accounting = solver_call_accounting(validated)
        record = {
            "block_id": block_id,
            "execution_index": index,
            "predecessor_digest": predecessor,
            "solver_call_accounting": accounting,
            "all_hours_resolved": validated.get("all_hours_resolved") is True,
            "accepted": validated.get("all_hours_resolved") is True,
            "mathematical_infeasibility_inferred": False,
        }
        if not record["accepted"]:
            raise SuccessorV2Rejected("unresolved seam payload cannot be accepted")
        predecessor = _canonical_sha256(record)
        accounted.append(accounting["solver_calls"])
        records.append(record)
    publication = dict(seam.publish(tuple(records)))
    if publication != {"publisher": "sealed_v7", "writes": 0}:
        raise SuccessorV2Rejected("registered v7 publication seam drifted")
    return MappingProxyType(
        {
            "closure_verified": True,
            "solver_calls_executed": 0,
            "accounted_solver_calls": accounted,
            "publication_calls": 1,
            "writes": 0,
            "accepted_for_execution": False,
        }
    )


def main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments == ["--validate-only"]:
        verify_live_closure()
        print(
            json.dumps(
                {
                    "validation_passed": True,
                    "execution_review_present": REVIEW.exists(),
                    "execution_ready": False,
                    "dependency_closure_verified": True,
                    "workers": 0,
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
        print(
            json.dumps(
                {
                    "status": outcome.status,
                    "accepted": outcome.accepted,
                    "child_pid": outcome.child_pid,
                    "counters": dict(outcome.counters),
                    "mathematical_infeasibility_inferred": (
                        outcome.mathematical_infeasibility_inferred
                    ),
                },
                sort_keys=True,
            )
        )
        return 0
    if arguments == ["--execute"]:
        ControllerSession().run_two_block_pilot()
        return 0
    raise SuccessorV2Rejected("successor-v2 argv is not registered")


if __name__ == "__main__":
    raise SystemExit(main())
