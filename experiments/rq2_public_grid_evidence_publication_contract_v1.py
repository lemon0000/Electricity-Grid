"""Closed Vnext evidence, ledger, closure, and zero-solver fixture contract."""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import hmac
import json
import os
import secrets
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Self

from experiments import rq2_public_grid_execution_runtime_contract_v3 as v3_contract

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v1.json"
INNER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v1.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_grid_evidence_publication_successor_v1.OUTER.SHA256SUMS.json"
BLOCKS = ("holdout_s20260822_0008", "holdout_s20260822_0009")
STAGES = v3_contract.STAGES
PROTOCOL = "rq2_public_grid_accepted_evidence_vnext_v1"
_FACTORY_TOKEN = object()


class ContractRejected(RuntimeError):
    """A frozen authority, evidence, ledger, or publication binding failed."""


class LiveClosureDrift(ContractRejected):
    """A required full-closure verification failed at a named boundary."""


def exact_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_stable(path: Path) -> bytes:
    try:
        before = path.lstat()
        first = path.read_bytes()
        middle = path.lstat()
        second = path.read_bytes()
        after = path.lstat()
    except OSError as exc:
        raise ContractRejected(f"authority unreadable: {path}") from exc
    if not path.is_file() or path.is_symlink() or first != second:
        raise ContractRejected(f"authority is not one stable ordinary file: {path}")
    identity = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if identity(before) != identity(middle) or identity(middle) != identity(after):
        raise ContractRejected(f"authority changed while read: {path}")
    return first


def process_create_time_ns(pid: int) -> int:
    """Return an OS identity timestamp used only to bind one live attempt."""
    if pid <= 0:
        raise ContractRejected("invalid process identity")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        open_process = kernel32.OpenProcess
        open_process.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        open_process.restype = wintypes.HANDLE
        get_times = kernel32.GetProcessTimes
        get_times.argtypes = (
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
            ctypes.POINTER(wintypes.FILETIME),
        )
        get_times.restype = wintypes.BOOL
        close = kernel32.CloseHandle
        close.argtypes = (wintypes.HANDLE,)
        handle = open_process(0x1000, False, pid)
        if not handle:
            raise ContractRejected("process identity is inaccessible")
        created = wintypes.FILETIME()
        exited = wintypes.FILETIME()
        kernel = wintypes.FILETIME()
        user = wintypes.FILETIME()
        try:
            if not get_times(handle, created, exited, kernel, user):
                raise ContractRejected("process creation time unavailable")
        finally:
            close(handle)
        ticks = (created.dwHighDateTime << 32) | created.dwLowDateTime
        return ticks * 100
    proc = Path(f"/proc/{pid}")
    try:
        return proc.stat().st_ctime_ns
    except OSError as exc:
        if pid == os.getpid():
            return int(time.time_ns() - time.monotonic_ns())
        raise ContractRejected("process creation time unavailable") from exc


def exact_worker_command(read_review_fixture: bool = True) -> tuple[str, ...]:
    config = load_config()
    command = (
        config["runtime"]["locked_python_executable"],
        "-B",
        "-m",
        config["runtime"]["worker_module"],
    )
    if read_review_fixture:
        command = (*command, "--internal-review-fixture-worker")
    return command


def load_config() -> dict[str, Any]:
    try:
        value = json.loads(read_stable(CONFIG))
    except json.JSONDecodeError as exc:
        raise ContractRejected("Vnext config malformed") from exc
    if not isinstance(value, dict) or value.get("status") != (
        "evidence_publication_successor_v1_review_closed"
    ):
        raise ContractRejected("Vnext config identity drifted")
    if tuple(value.get("blocks", ())) != BLOCKS:
        raise ContractRejected("Vnext block order drifted")
    gates = value.get("gates")
    if not isinstance(gates, dict) or any(gates.values()):
        raise ContractRejected("Vnext review/execution gates are not closed")
    return value


def _verify_hash(relative: str, expected: str) -> str:
    raw = read_stable(ROOT / relative)
    observed = sha256_bytes(raw)
    if observed != expected:
        raise ContractRejected(f"dependency drifted: {relative}")
    return observed


def verify_full_live_closure(*, trace: list[str] | None = None) -> tuple[str, ...]:
    """Verify predecessor recursive closure, dependencies, and exact own bundle."""
    config = load_config()
    observed: list[str] = []

    def check(relative: str, expected: str) -> None:
        _verify_hash(relative, expected)
        observed.append(relative)

    predecessor = config["predecessor"]
    check(predecessor["outer_path"], predecessor["outer_sha256"])
    check(predecessor["inner_path"], predecessor["inner_sha256"])
    check(predecessor["escalate_path"], predecessor["escalate_sha256"])
    try:
        v3_config = v3_contract._load_config()
        v3_contract.verify_full_live_closure(ROOT, v3_config)
    except Exception as exc:
        raise ContractRejected("predecessor recursive closure rejected") from exc
    for key, expected in config["dependencies"].items():
        if key.endswith("_path"):
            check(expected, config["dependencies"][key.removesuffix("_path") + "_sha256"])

    try:
        inner_raw = read_stable(INNER)
        outer_raw = read_stable(OUTER)
        inner = json.loads(inner_raw)
        outer = json.loads(outer_raw)
    except (OSError, json.JSONDecodeError, ContractRejected) as exc:
        raise ContractRejected("Vnext manifests unavailable") from exc
    inner_relative = INNER.relative_to(ROOT).as_posix()
    if outer != {
        "schema": "rq2_public_grid_evidence_publication_successor_outer_v1",
        "files": {inner_relative: sha256_bytes(inner_raw)},
    }:
        raise ContractRejected("Vnext outer manifest drifted")
    files = inner.get("files") if isinstance(inner, dict) else None
    expected_members = set(config["bundle"]["members"].values())
    if (
        inner.get("schema") != "rq2_public_grid_evidence_publication_successor_bundle_v1"
        or not isinstance(files, dict)
        or set(files) != expected_members
        or len(files) != config["bundle"]["exact_member_count"]
    ):
        raise ContractRejected("Vnext inner manifest inventory drifted")
    for relative, expected in files.items():
        check(relative, expected)
    observed.extend([inner_relative, OUTER.relative_to(ROOT).as_posix()])
    if trace is not None:
        trace.extend(observed)
    return tuple(sorted(set(observed)))


class StageAwareClosureVerifier:
    def __init__(self, fault_stage: str | None = None) -> None:
        if fault_stage is not None and fault_stage not in STAGES:
            raise ContractRejected("unregistered closure stage")
        self.fault_stage = fault_stage
        self.stages: list[str] = []

    def verify(self, stage: str) -> tuple[str, ...]:
        if stage not in STAGES:
            raise ContractRejected("unregistered closure stage")
        inventory = verify_full_live_closure()
        self.stages.append(stage)
        if stage == self.fault_stage:
            raise LiveClosureDrift(f"injected full-closure drift at {stage}")
        return inventory


def build_review_fixture_payload(block_id: str) -> dict[str, object]:
    """Derive the frozen nonformal payload without loading data or invoking a solver."""
    if block_id not in BLOCKS:
        raise ContractRejected("fixture block is unregistered")
    from experiments import (
        run_rq2_public_grid_two_block_pilot_candidate_v4 as candidate,
    )

    payload = copy.deepcopy(candidate.predecessor._extract_gurobi_payload())
    context = candidate._stage_context()
    expected = context["blocks"][block_id]
    config = context["config"]
    spec = candidate.recovery.solver_spec(config["solver"])
    options = candidate.recovery.solver_options(spec)
    baseline = payload["baseline_audit"]
    baseline.update(
        {
            "solver_name": spec.name,
            "solver_options": options,
            "solver_threads": config["solver"]["threads"],
            "termination_condition": "optimal",
            "solver_status": "ok",
        }
    )
    pairs = list(zip(payload["outcomes"], payload["rows"], strict=True))
    no_event = next((copy.deepcopy(o), copy.deepcopy(r)) for o, r in pairs if not r["active_event_id"])
    active = next((copy.deepcopy(o), copy.deepcopy(r)) for o, r in pairs if r["active_event_id"])
    rows: list[dict[str, object]] = []
    outcomes: list[dict[str, object]] = []
    for input_row in expected:
        outcome, row = copy.deepcopy(active if input_row["active_event_id"] else no_event)
        for key in candidate.recovery.v4._BLOCK_FIELDS:
            row[key] = input_row[key]
        primary = outcome["primary"]
        primary.update(
            {
                "source_hour": int(input_row["source_hour"]),
                "event_id": input_row["active_event_id"] or None,
                "component_type": input_row["active_component_type"] or None,
                "component_uid": input_row["active_component_uid"] or None,
            }
        )
        outcome["solver_name"] = spec.name
        if input_row["active_event_id"]:
            outcome["solver_options"] = options
            primary["termination_condition"] = "optimal"
            primary["solver_status"] = "ok"
        else:
            outcome["solver_options"] = {}
            primary["termination_condition"] = "not_applicable_no_active_outage"
            primary["solver_status"] = "not_applicable"
        row["dispatch_termination_condition"] = primary["termination_condition"]
        row["dispatch_solver_status"] = primary["solver_status"]
        rows.append(row)
        outcomes.append(outcome)
    payload.update(
        {
            "block_id": block_id,
            "split": expected[0]["split"],
            "rows": rows,
            "outcomes": outcomes,
            "all_hours_resolved": True,
            "exogenous_grid_infeasibility_hour_count": 0,
        }
    )
    raw = exact_json_bytes(payload)
    if sha256_bytes(raw) != load_config()["fixture"]["payload_sha256"][block_id]:
        raise ContractRejected("frozen review fixture payload drifted")
    validate_scientific_payload(payload, block_id)
    return payload


def validate_scientific_payload(
    payload: Mapping[str, Any], block_id: str
) -> dict[str, Any]:
    if block_id not in BLOCKS:
        raise ContractRejected("scientific block is unregistered")
    from experiments import (
        run_rq2_public_grid_two_block_pilot_candidate_v4 as candidate,
    )

    context = candidate._stage_context()
    return candidate.recovery._validate_scientific_payload(
        payload,
        block_id=block_id,
        expected_block=context["blocks"][block_id],
        config=context["config"],
    )


def _evidence_body(fields: Mapping[str, object]) -> dict[str, object]:
    return {key: fields[key] for key in AcceptedEvidenceVnext.__dataclass_fields__ if key != "auth_tag"}


@dataclasses.dataclass(frozen=True, slots=True, init=False)
class AcceptedEvidenceVnext:
    protocol: str
    session_id: str
    execution_index: int
    block_id: str
    predecessor_digest: str | None
    nonce: str
    parent_pid: int
    parent_create_time_ns: int
    worker_pid: int
    worker_ppid: int
    worker_create_time_ns: int
    command: tuple[str, ...]
    cwd: str
    environment_sha256: str
    config_sha256: str
    chain_sha256: str
    worker_source_sha256: str
    hello_bytes: bytes
    hello_sha256: str
    envelope_bytes: bytes
    envelope_sha256: str
    ack_bytes: bytes
    ack_sha256: str
    result_path: str
    result_bytes: bytes
    result_sha256: str
    attempt_receipt_path: str
    attempt_receipt_bytes: bytes
    attempt_receipt_sha256: str
    scientific_bytes: bytes
    scientific_sha256: str
    review_fixture: bool
    nonformal: bool
    claim: bool
    scientific_loader_calls: int
    solver_calls: int
    auth_tag: str

    def __new__(cls) -> Self:
        raise TypeError("AcceptedEvidenceVnext is controller-factory-only")

    @classmethod
    def _from_controller(
        cls, *, token: object, session_key: bytes, fields: Mapping[str, object]
    ) -> AcceptedEvidenceVnext:
        if token is not _FACTORY_TOKEN:
            raise ContractRejected("evidence factory authority rejected")
        instance = object.__new__(cls)
        for name in cls.__dataclass_fields__:
            if name == "auth_tag":
                continue
            object.__setattr__(instance, name, fields[name])
        tag = hmac.new(session_key, exact_json_bytes(_json_safe(_evidence_body(fields))), hashlib.sha256).hexdigest()
        object.__setattr__(instance, "auth_tag", tag)
        validate_evidence(instance, session_key=session_key)
        return instance

    def as_object(self) -> dict[str, object]:
        return _json_safe({name: getattr(self, name) for name in self.__dataclass_fields__})


def _json_safe(value: object) -> Any:
    if isinstance(value, bytes):
        return {"encoding": "hex", "value": value.hex()}
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return value


def validate_evidence(evidence: AcceptedEvidenceVnext, *, session_key: bytes) -> None:
    if type(evidence) is not AcceptedEvidenceVnext or evidence.protocol != PROTOCOL:
        raise ContractRejected("cross-protocol evidence rejected")
    if evidence.execution_index not in (1, 2) or evidence.block_id != BLOCKS[evidence.execution_index - 1]:
        raise ContractRejected("evidence block/index drifted")
    if evidence.execution_index == 1 and evidence.predecessor_digest is not None:
        raise ContractRejected("first evidence has predecessor")
    byte_pairs = (
        (evidence.hello_bytes, evidence.hello_sha256),
        (evidence.envelope_bytes, evidence.envelope_sha256),
        (evidence.ack_bytes, evidence.ack_sha256),
        (evidence.result_bytes, evidence.result_sha256),
        (evidence.attempt_receipt_bytes, evidence.attempt_receipt_sha256),
        (evidence.scientific_bytes, evidence.scientific_sha256),
    )
    if any(sha256_bytes(raw) != digest for raw, digest in byte_pairs):
        raise ContractRejected("evidence byte/hash binding drifted")
    if not evidence.review_fixture or not evidence.nonformal or evidence.claim:
        raise ContractRejected("review fixture claim boundary drifted")
    if evidence.scientific_loader_calls != 0 or evidence.solver_calls != 0:
        raise ContractRejected("review fixture call counters drifted")
    body = {name: getattr(evidence, name) for name in evidence.__dataclass_fields__ if name != "auth_tag"}
    expected = hmac.new(session_key, exact_json_bytes(_json_safe(body)), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, evidence.auth_tag):
        raise ContractRejected("controller evidence authentication drifted")


def evidence_digest(evidence: AcceptedEvidenceVnext) -> str:
    return sha256_bytes(exact_json_bytes(evidence.as_object()))


@dataclasses.dataclass(frozen=True, slots=True)
class ControllerReceiptVnext:
    schema: str
    session_id: str
    purpose: str
    record_digests: tuple[str, str]
    ledger_sha256: str
    closure_inventory_sha256: str
    review_fixture: bool
    nonformal: bool
    claim: bool

    def as_object(self) -> dict[str, object]:
        return _json_safe(dataclasses.asdict(self))


class ControllerLedgerVnext:
    """Controller-owned append-only ledger. No public evidence-accept method exists."""

    __slots__ = ("_records", "_sealed", "_session_id", "_session_key")

    def __init__(self, session_id: str | None = None) -> None:
        self._session_id = session_id or secrets.token_hex(32)
        self._session_key = secrets.token_bytes(32)
        self._records: tuple[AcceptedEvidenceVnext, ...] = ()
        self._sealed = False

    @property
    def session_id(self) -> str:
        return self._session_id

    @property
    def records(self) -> tuple[AcceptedEvidenceVnext, ...]:
        return self._records

    def _append_controller(self, evidence: object, *, token: object) -> None:
        if token is not _FACTORY_TOKEN or type(evidence) is not AcceptedEvidenceVnext:
            raise ContractRejected("external/cross-protocol ledger append rejected")
        if self._sealed or len(self._records) >= 2:
            raise ContractRejected("sealed/full ledger rejected append")
        validate_evidence(evidence, session_key=self._session_key)
        index = len(self._records) + 1
        predecessor = None if index == 1 else evidence_digest(self._records[-1])
        if evidence.session_id != self._session_id or evidence.execution_index != index:
            raise ContractRejected("ledger session/order drifted")
        if evidence.predecessor_digest != predecessor:
            raise ContractRejected("ledger predecessor drifted")
        if any(record.nonce == evidence.nonce or record.worker_pid == evidence.worker_pid for record in self._records):
            raise ContractRejected("ledger replay/PID reuse within session rejected")
        self._records = (*self._records, evidence)

    def _new_evidence(self, fields: Mapping[str, object]) -> AcceptedEvidenceVnext:
        return AcceptedEvidenceVnext._from_controller(
            token=_FACTORY_TOKEN, session_key=self._session_key, fields=fields
        )

    def _seal_controller(self, closure_inventory: tuple[str, ...]) -> ControllerReceiptVnext:
        if len(self._records) != 2:
            raise ContractRejected("controller receipt requires exact two-block ledger")
        self._sealed = True
        digests = tuple(evidence_digest(record) for record in self._records)
        ledger_sha = sha256_bytes(exact_json_bytes([record.as_object() for record in self._records]))
        return ControllerReceiptVnext(
            schema="rq2_public_grid_controller_receipt_vnext_v1",
            session_id=self._session_id,
            purpose="review_fixture_zero_solver",
            record_digests=(digests[0], digests[1]),
            ledger_sha256=ledger_sha,
            closure_inventory_sha256=sha256_bytes(exact_json_bytes(list(closure_inventory))),
            review_fixture=True,
            nonformal=True,
            claim=False,
        )

    def _verify_controller_receipt(self, receipt: ControllerReceiptVnext) -> None:
        if type(receipt) is not ControllerReceiptVnext or receipt.session_id != self._session_id:
            raise ContractRejected("controller receipt type/session drifted")
        for record in self._records:
            validate_evidence(record, session_key=self._session_key)
        if tuple(evidence_digest(item) for item in self._records) != receipt.record_digests:
            raise ContractRejected("controller receipt record digest drifted")
        expected_ledger = sha256_bytes(exact_json_bytes([item.as_object() for item in self._records]))
        if expected_ledger != receipt.ledger_sha256:
            raise ContractRejected("controller receipt ledger digest drifted")
        expected_closure = sha256_bytes(
            exact_json_bytes(list(verify_full_live_closure()))
        )
        if (
            receipt.schema != "rq2_public_grid_controller_receipt_vnext_v1"
            or receipt.purpose != "review_fixture_zero_solver"
            or receipt.closure_inventory_sha256 != expected_closure
            or receipt.review_fixture is not True
            or receipt.nonformal is not True
            or receipt.claim is not False
        ):
            raise ContractRejected("controller receipt authority/claim drifted")


def verify_frozen_ledger(
    records: tuple[AcceptedEvidenceVnext, ...], receipt: ControllerReceiptVnext
) -> None:
    if len(records) != 2 or type(receipt) is not ControllerReceiptVnext:
        raise ContractRejected("frozen ledger inventory malformed")
    if tuple(evidence_digest(item) for item in records) != receipt.record_digests:
        raise ContractRejected("frozen ledger replay/reorder rejected")
    if records[0].execution_index != 1 or records[1].execution_index != 2:
        raise ContractRejected("frozen ledger order rejected")
    if records[1].predecessor_digest != evidence_digest(records[0]):
        raise ContractRejected("frozen ledger predecessor rejected")
    if records[0].session_id != receipt.session_id or records[1].session_id != receipt.session_id:
        raise ContractRejected("frozen ledger cross-session rejected")
