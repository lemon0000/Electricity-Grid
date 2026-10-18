"""Focused tests for activation/transport successor v2."""

from __future__ import annotations

import ast
import base64
import dataclasses
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from experiments import (
    bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v2 as bootstrap,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v2 as transport,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / bootstrap.CONFIG_REL).read_text(encoding="utf-8"))


def _runtime() -> dict[str, object]:
    contract = CONFIG["bootstrap_contract"]
    return {
        "executable": contract["locked_python_executable"],
        "executable_sha256": contract["locked_python_sha256"],
        "version": contract["locked_python_version"],
        "orig_argv": [
            contract["locked_python_executable"],
            *contract["validate_only_argv_suffix"],
        ],
        "cwd": contract["exact_cwd"],
        "hostname": contract["host"]["hostname"],
        "system": contract["host"]["system"],
        "release": contract["host"]["release"],
        "machine": contract["host"]["machine"],
        "environment": contract["exact_environment"],
        "process_age_seconds": 1.0,
        "processes": [(os.getpid(), "python.exe")],
        "available_virtual_bytes": 10 * 1024**3,
    }


def _root_map() -> dict[str, bool]:
    paths = [
        *CONFIG["fresh_roots"],
        *CONFIG["formal_invariants"]["protected_roots_clean_absent"],
    ]
    return dict.fromkeys(paths, False)


def _production_evidence(
    ledger: transport.ControllerLedger,
    index: int,
    *,
    pid: int | None = None,
    create_ns: int | None = None,
    nonce: str | None = None,
    block_id: str | None = None,
    predecessor: str | None | object = ...,
    envelope_extra: MappingForTest | None = None,
) -> transport.AcceptedEvidence:
    block = block_id or transport.BLOCKS[index - 1]
    previous = (
        ledger.predecessor_for(index)
        if predecessor is ...
        else predecessor
    )
    process_id = pid if pid is not None else 20_000 + index
    process_create = create_ns if create_ns is not None else 30_000 + index
    attempt_nonce = nonce or ("a" if index == 1 else "b") * 64
    scientific = ("c" if index == 1 else "d") * 64
    envelope: dict[str, Any] = {
        "schema": transport.ENVELOPE_SCHEMA,
        "mode": "production_accepted",
        "block_id": block,
        "execution_index": index,
        "nonce": attempt_nonce,
        "issued_ns": 40_000 + index,
        "controller_session_id": ledger.session_id,
        "predecessor_accepted_evidence_digest": previous,
        "ledger_digest_before": ledger.digest,
        "parent_pid": 10_000,
        "parent_create_time_ns": 11_000,
        "worker_pid": process_id,
        "worker_create_time_ns": process_create,
        "worker_command": ["python", "-B", "-m", transport.MODULE],
        "read_handle": 7,
        "ack_handle": 8,
        "working_directory": str(ROOT),
        "sanitized_environment": CONFIG["bootstrap_contract"]["exact_environment"],
        "transport_module_path": str(ROOT / bootstrap.RUNNER_REL),
        "transport_module_sha256": CONFIG["transport_contract"]["runner_sha256"],
        "config_path": str(ROOT / bootstrap.CONFIG_REL),
        "config_sha256": hashlib.sha256(
            (ROOT / bootstrap.CONFIG_REL).read_bytes()
        ).hexdigest(),
        "activation_v1_outer_path": str(
            ROOT / CONFIG["predecessor_authority"]["activation_v1_outer_path"]
        ),
        "activation_v1_outer_sha256": CONFIG["predecessor_authority"][
            "activation_v1_outer_sha256"
        ],
        "activation_v1_rework_path": str(
            ROOT / CONFIG["predecessor_authority"]["activation_v1_rework_path"]
        ),
        "activation_v1_rework_sha256": CONFIG["predecessor_authority"][
            "activation_v1_rework_sha256"
        ],
        "production_dispatch_permitted": True,
    }
    if envelope_extra:
        envelope.update(envelope_extra)
    envelope_bytes = transport._canonical_bytes(envelope)
    envelope_hash = hashlib.sha256(envelope_bytes).hexdigest()
    source = {
        "schema": transport.SOURCE_SCHEMA,
        "evidence_kind": "production_accepted",
        "block_id": block,
        "execution_index": index,
        "nonce": attempt_nonce,
        "envelope_sha256": envelope_hash,
        "scientific_payload_sha256": scientific,
        "preloader_cut": False,
        "all_hours_resolved": True,
        "mathematical_infeasibility_inferred": False,
    }
    source_bytes = transport._canonical_bytes(source)
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    receipt = {
        "schema": transport.ATTEMPT_SCHEMA,
        "evidence_kind": "production_accepted",
        "block_id": block,
        "execution_index": index,
        "nonce": attempt_nonce,
        "envelope_sha256": envelope_hash,
        "source_payload_sha256": source_hash,
        "scientific_payload_sha256": scientific,
        "controller_validation_passed": False,
        "published": False,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
        "mathematical_infeasibility_inferred": False,
    }
    receipt_bytes = transport._canonical_bytes(receipt)
    receipt_hash = hashlib.sha256(receipt_bytes).hexdigest()
    ack = {
        "schema": transport.ACK_SCHEMA,
        "mode": "production_accepted",
        "block_id": block,
        "execution_index": index,
        "nonce": attempt_nonce,
        "envelope_sha256": envelope_hash,
        "worker_pid": process_id,
        "worker_create_time_ns": process_create,
        "bounded_eof_verified_before_ack": True,
        "accepted_once": True,
        "source_payload_base64": base64.b64encode(source_bytes).decode("ascii"),
        "source_payload_sha256": source_hash,
        "source_attempt_receipt_base64": base64.b64encode(receipt_bytes).decode(
            "ascii"
        ),
        "source_attempt_receipt_sha256": receipt_hash,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }
    ack_bytes = transport._canonical_bytes(ack)
    provisional = transport.AcceptedEvidence(
        schema=transport.EVIDENCE_SCHEMA,
        evidence_kind="production_accepted",
        block_id=block,
        execution_index=index,
        nonce=attempt_nonce,
        envelope_bytes=envelope_bytes,
        envelope_sha256=envelope_hash,
        ack_bytes=ack_bytes,
        ack_sha256=hashlib.sha256(ack_bytes).hexdigest(),
        popen_pid=process_id,
        worker_create_time_ns=process_create,
        source_payload_bytes=source_bytes,
        source_payload_sha256=source_hash,
        source_attempt_receipt_bytes=receipt_bytes,
        source_attempt_receipt_sha256=receipt_hash,
        scientific_payload_sha256=scientific,
        predecessor_accepted_evidence_digest=(
            previous if isinstance(previous, str) else None
        ),
        controller_session_id=ledger.session_id,
        controller_acceptance_mac=None,
        accepted_evidence_digest="",
    )
    return dataclasses.replace(
        provisional,
        accepted_evidence_digest=transport._canonical_sha256(
            transport._evidence_digest_payload(provisional)
        ),
    )


MappingForTest = dict[str, Any]


def _unit_capability(
    ledger: transport.ControllerLedger,
    evidence: transport.AcceptedEvidence,
) -> transport.AttemptCapability:
    """Register a deterministic unit seam after evidence construction.

    Production code can create this capability only from an exact live ``Popen``;
    the separate live-child test exercises that boundary.
    """
    capability = transport.AttemptCapability(
        controller_session_id=ledger.session_id,
        token_id=hashlib.sha256(
            f"{evidence.execution_index}:{evidence.nonce}".encode("ascii")
        ).hexdigest(),
        block_id=evidence.block_id,
        execution_index=evidence.execution_index,
        nonce=evidence.nonce,
        child_pid=evidence.popen_pid,
        child_create_time_ns=evidence.worker_create_time_ns,
    )
    ledger._active_attempts[capability.token_id] = capability
    return capability


def _accept(
    ledger: transport.ControllerLedger,
    evidence: transport.AcceptedEvidence,
) -> transport.AcceptedEvidence:
    return ledger.accept_verified_transport(
        evidence,
        _unit_capability(ledger, evidence),
    )


def test_v2_modules_are_standard_library_only_and_production_closed() -> None:
    assert bootstrap.PROJECT_IMPORTS_PERMITTED is False
    assert transport.PRODUCTION_DISPATCH_PERMITTED is False
    for relative in (bootstrap.SELF_REL, bootstrap.RUNNER_REL):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported.intersection({"src", "experiments", "pyomo", "pandas"})
    runner_source = (ROOT / bootstrap.RUNNER_REL).read_text(encoding="utf-8")
    assert "_dispatch_one(" not in runner_source
    assert "_worker_from_capability(" not in runner_source
    assert CONFIG["transport_contract"]["production_dispatch_permitted"] is False
    assert CONFIG["gates"]["production_dispatch_permitted"] is False


def test_static_authority_and_rework_receipt_are_live() -> None:
    config, _helper = bootstrap._verify_static_authority()
    assert config["gates"]["activation_v1_rework_recorded"] is True
    assert config["gates"]["activation_v2_independent_review_passed"] is False


def test_preimport_fails_before_static_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def forbidden() -> tuple[dict[str, Any], Any]:
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr(bootstrap, "_verify_static_authority", forbidden)
    with pytest.raises(bootstrap.BootstrapRejected, match="preimport"):
        bootstrap.validate(preimport_modules=["src.attack"])
    assert called is False


def test_validate_only_is_closed_and_zero_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    helper = type(
        "Helper",
        (),
        {
            "_verify_runtime": staticmethod(lambda _config, _runtime: None),
            "_verify_roots": staticmethod(lambda _config, _roots: None),
        },
    )
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: (CONFIG, helper))
    report = bootstrap.validate(
        preimport_modules=[], runtime=_runtime(), root_appearances=_root_map()
    )
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["activation_review_present"] is False
    assert report["execution_wrapper_present"] is False
    assert report["dispatch_authorization_present"] is False
    assert report["production_dispatch_permitted"] is False
    for key in (
        "production_workers_started",
        "scientific_loader_calls",
        "solver_calls",
        "result_files_written",
        "formal_writes",
    ):
        assert report[key] == 0


def test_review_pass_only_authorizes_wrapper_creation() -> None:
    outer = "e" * 64
    payload = {
        "schema": "rq2_public_grid_two_block_pilot_activation_transport_review_pass_v2",
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "reviewed_outer": {"path": bootstrap.OUTER_REL, "sha256": outer},
        "findings": {"blocker": [], "major": [], "minor": []},
        "effect": CONFIG["future_activation_review"]["expected_effect"],
    }
    bootstrap._verify_review_effect(payload, outer)
    overauthorized = json.loads(json.dumps(payload))
    overauthorized["effect"]["activation_execution_authorized"] = True
    with pytest.raises(bootstrap.BootstrapRejected, match="overauthorizes"):
        bootstrap._verify_review_effect(overauthorized, outer)
    overauthorized = json.loads(json.dumps(payload))
    overauthorized["effect"]["two_block_pilot_execution_authorized"] = True
    with pytest.raises(bootstrap.BootstrapRejected, match="overauthorizes"):
        bootstrap._verify_review_effect(overauthorized, outer)


def test_caller_supplied_history_constructor_is_impossible() -> None:
    with pytest.raises(TypeError):
        transport.ControllerLedger([object()])  # type: ignore[call-arg]


def test_full_history_accepts_exact_0008_then_0009() -> None:
    ledger = transport.ControllerLedger()
    first = _accept(ledger, _production_evidence(ledger, 1))
    second = _accept(ledger, _production_evidence(ledger, 2))
    assert tuple(record.block_id for record in ledger.records) == transport.BLOCKS
    assert second.predecessor_accepted_evidence_digest == first.accepted_evidence_digest
    assert first.controller_acceptance_mac is not None
    assert second.controller_acceptance_mac is not None


@pytest.mark.parametrize(
    "case",
    ["0009-first", "block-swap", "wrong-predecessor", "extra-envelope-key"],
)
def test_forged_truncated_reordered_or_block_swapped_history_rejected(case: str) -> None:
    ledger = transport.ControllerLedger()
    if case == "0009-first":
        evidence = _production_evidence(
            ledger, 2, predecessor="f" * 64
        )
    elif case == "block-swap":
        evidence = _production_evidence(
            ledger, 1, block_id=transport.BLOCKS[1]
        )
    elif case == "wrong-predecessor":
        evidence = _production_evidence(
            ledger, 1, predecessor="f" * 64
        )
    else:
        evidence = _production_evidence(
            ledger, 1, envelope_extra={"forged": True}
        )
    with pytest.raises(transport.TransportRejected):
        _accept(ledger, evidence)


def test_mutated_stored_history_cannot_unlock_0009() -> None:
    ledger = transport.ControllerLedger()
    first = _accept(ledger, _production_evidence(ledger, 1))
    forged = dataclasses.replace(first, ack_sha256="0" * 64)
    ledger._records = (forged,)
    with pytest.raises(transport.TransportRejected):
        ledger.predecessor_for(2)


def test_cross_session_history_and_truncated_history_rejected() -> None:
    first_ledger = transport.ControllerLedger()
    first = _accept(first_ledger, _production_evidence(first_ledger, 1))
    second_ledger = transport.ControllerLedger()
    second_ledger._records = (first,)
    with pytest.raises(transport.TransportRejected, match="session"):
        second_ledger.predecessor_for(2)
    with pytest.raises(transport.TransportRejected):
        _accept(
            second_ledger,
            _production_evidence(second_ledger, 2, predecessor=first.accepted_evidence_digest)
        )


@pytest.mark.parametrize("identity", ["process", "nonce"])
def test_replayed_identity_rejected(identity: str) -> None:
    ledger = transport.ControllerLedger()
    first = _accept(ledger, _production_evidence(ledger, 1))
    kwargs: dict[str, Any] = {}
    if identity == "process":
        kwargs.update(pid=first.popen_pid, create_ns=first.worker_create_time_ns)
    else:
        kwargs.update(nonce=first.nonce)
    with pytest.raises(transport.TransportRejected, match="replay"):
        _accept(ledger, _production_evidence(ledger, 2, **kwargs))


@pytest.mark.parametrize(
    "field",
    [
        "envelope_bytes",
        "ack_bytes",
        "source_payload_bytes",
        "source_attempt_receipt_bytes",
        "accepted_evidence_digest",
    ],
)
def test_corrupt_bytes_or_digest_rejected(field: str) -> None:
    ledger = transport.ControllerLedger()
    evidence = _production_evidence(ledger, 1)
    value: object = b"{}" if field.endswith("bytes") else "0" * 64
    with pytest.raises(transport.TransportRejected):
        _accept(ledger, dataclasses.replace(evidence, **{field: value}))


def test_evidence_is_frozen_and_ledger_records_are_immutable() -> None:
    ledger = transport.ControllerLedger()
    evidence = _accept(ledger, _production_evidence(ledger, 1))
    with pytest.raises(dataclasses.FrozenInstanceError):
        evidence.block_id = "forged"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        ledger.records.append(evidence)  # type: ignore[attr-defined]


def test_self_consistent_forged_evidence_lacks_live_attempt_capability() -> None:
    ledger = transport.ControllerLedger()
    evidence = _production_evidence(ledger, 1)
    with pytest.raises(transport.TransportRejected, match="capability is required"):
        ledger.accept_verified_transport(evidence, object())  # type: ignore[arg-type]
    forged = transport.AttemptCapability(
        controller_session_id=ledger.session_id,
        token_id="f" * 64,
        block_id=evidence.block_id,
        execution_index=evidence.execution_index,
        nonce=evidence.nonce,
        child_pid=evidence.popen_pid,
        child_create_time_ns=evidence.worker_create_time_ns,
    )
    with pytest.raises(transport.TransportRejected, match="absent, forged, or replayed"):
        ledger.accept_verified_transport(evidence, forged)
    assert ledger.records == ()


def test_live_popen_attempt_capability_is_exact_and_one_shot() -> None:
    ledger = transport.ControllerLedger()
    process = subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    try:
        nonce = "a" * 64
        capability = ledger.begin_transport_attempt(
            process,
            block_id=transport.BLOCKS[0],
            execution_index=1,
            nonce=nonce,
        )
        evidence = _production_evidence(
            ledger,
            1,
            pid=capability.child_pid,
            create_ns=capability.child_create_time_ns,
            nonce=nonce,
        )
        accepted = ledger.accept_verified_transport(evidence, capability)
        assert accepted.block_id == transport.BLOCKS[0]
        with pytest.raises(
            transport.TransportRejected, match="absent, forged, or replayed"
        ):
            ledger.accept_verified_transport(evidence, capability)
    finally:
        process.terminate()
        process.wait(timeout=5)


def test_real_windows_preloader_probe_uses_new_worker_and_source_bytes() -> None:
    evidence = transport.run_preloader_probe(timeout_seconds=10.0)
    assert evidence.evidence_kind == "preloader_probe"
    assert evidence.block_id == transport.BLOCKS[0]
    assert evidence.popen_pid != os.getpid()
    assert evidence.scientific_payload_sha256 is None
    source = json.loads(evidence.source_payload_bytes)
    receipt = json.loads(evidence.source_attempt_receipt_bytes)
    ack = json.loads(evidence.ack_bytes)
    assert source["preloader_cut"] is True
    assert receipt["scientific_loader_calls"] == 0
    assert receipt["solver_calls"] == 0
    assert receipt["result_writes"] == 0
    assert receipt["formal_writes"] == 0
    assert base64.b64decode(ack["source_payload_base64"]) == evidence.source_payload_bytes
    with pytest.raises(transport.TransportRejected):
        transport._process_creation_time_ns(evidence.popen_pid)


def test_worker_rejects_ordinary_file_handles(tmp_path: Path) -> None:
    path = tmp_path / "ordinary.bin"
    path.write_bytes(b"ordinary")
    read = os.open(path, os.O_RDONLY)
    write = os.open(path, os.O_WRONLY)
    try:
        with pytest.raises(transport.TransportRejected, match="pipe"):
            transport._worker_probe(read, write, read_handle=read, ack_handle=write)
    finally:
        os.close(read)
        os.close(write)


def test_execute_and_public_transport_cli_remain_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "_PREIMPORT_PROJECT_MODULES", ())
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: (CONFIG, object()))
    with pytest.raises(bootstrap.BootstrapRejected, match="authority is absent"):
        bootstrap.main(["--execute"])
    with pytest.raises(SystemExit):
        transport.main([])


def test_failure_semantics_never_infer_infeasibility() -> None:
    semantics = CONFIG["resource_contract"]["failure_semantics"]
    assert semantics["any_failure_is_mathematical_infeasibility_evidence"] is False
    assert set(semantics.values()) <= {
        "honest_incomplete",
        "commit_indeterminate",
        False,
    }
    formal = CONFIG["formal_invariants"]
    assert formal["formal_entrypoints_reachable"] is False
    assert formal["gurobi_entrypoints_reachable"] is False
    assert formal["recovery_activation_entrypoints_reachable"] is False
