from __future__ import annotations

import copy
import dataclasses
import json
import os
import subprocess
import threading
from pathlib import Path

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as runner


def _identity(pid: int, command: list[str]) -> dict[str, object]:
    python = Path(os.sys.executable).resolve()
    return {
        "pid": pid,
        "creation_time": 880000 + pid,
        "executable_path": str(python),
        "executable_sha256": runner._sha256(python),
        "command": command,
    }


def _highs_payload(block_id: str) -> dict[str, object]:
    payload = copy.deepcopy(runner.predecessor._extract_gurobi_payload())
    context = runner._stage_context()
    expected = context["blocks"][block_id]
    config = context["config"]
    spec = runner.recovery.solver_spec(config["solver"])
    options = runner.recovery.solver_options(spec)
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
    no_event = next(
        (copy.deepcopy(outcome), copy.deepcopy(row))
        for outcome, row in zip(payload["outcomes"], payload["rows"], strict=True)
        if not row["active_event_id"]
    )
    active = next(
        (copy.deepcopy(outcome), copy.deepcopy(row))
        for outcome, row in zip(payload["outcomes"], payload["rows"], strict=True)
        if row["active_event_id"]
    )
    rows: list[dict[str, object]] = []
    outcomes: list[dict[str, object]] = []
    for input_row in expected:
        outcome, row = copy.deepcopy(active if input_row["active_event_id"] else no_event)
        for key in runner.recovery.v4._BLOCK_FIELDS:
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
    return payload


def _test_roots(tmp_path: Path) -> dict[str, Path]:
    return {
        "result": tmp_path / "published",
        "worker": tmp_path / "worker",
        "log": tmp_path / "logs",
        "success_seal": tmp_path / "published.PUBLISHED.json",
    }


def _patch_roots(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> dict[str, Path]:
    roots = _test_roots(tmp_path)
    monkeypatch.setattr(runner, "_pilot_roots", lambda _config: roots)
    return roots


def _envelope(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    ledger: runner.ControllerLedger,
    block_id: str,
    execution_index: int,
    nonce: str,
) -> dict[str, object]:
    roots = _patch_roots(monkeypatch, tmp_path)
    config = runner._load_config()
    python = Path(os.sys.executable).resolve()
    parent = _identity(72001, runner._expected_controller_command(python))
    worker = _identity(
        72002,
        runner._expected_worker_command(python, read_handle=41, ack_handle=42),
    )
    attempt = roots["worker"] / block_id / nonce
    return runner._build_capability_envelope(
        config,
        ledger=ledger,
        block_id=block_id,
        execution_index=execution_index,
        parent_identity=parent,
        worker_identity=worker,
        payload_path=attempt / "payload.json",
        attempt_receipt_path=attempt / "attempt_receipt.json",
        read_handle=41,
        ack_handle=42,
        environment={},
        nonce=nonce,
    )


def _source_attempt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    ledger: runner.ControllerLedger,
    block_id: str,
    execution_index: int,
    nonce: str,
) -> runner.AcceptedEvidence:
    envelope = _envelope(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=block_id,
        execution_index=execution_index,
        nonce=nonce,
    )
    payload_path = Path(str(envelope["worker_payload_path"]))
    receipt_path = Path(str(envelope["attempt_receipt_path"]))
    payload_path.parent.mkdir(parents=True, exist_ok=False)
    scientific = _highs_payload(block_id)
    runner.recovery._atomic_json(
        payload_path, runner._build_worker_result(envelope, scientific)
    )
    runner.recovery._atomic_json(
        receipt_path, runner._build_attempt_receipt(envelope, payload_path)
    )
    ack = runner._build_ack(envelope)
    accepted = runner._accept_worker_attempt(
        envelope=envelope,
        ack=ack,
        payload_path=payload_path,
        attempt_receipt_path=receipt_path,
        popen_identity=envelope["worker_process_identity"],
        ledger=ledger,
    )
    ledger.accept(accepted)
    return accepted


def _complete_ledger(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> runner.ControllerLedger:
    ledger = runner.ControllerLedger()
    _source_attempt(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="a" * 64,
    )
    _source_attempt(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[1],
        execution_index=2,
        nonce="b" * 64,
    )
    return ledger


def test_test_first_candidate_v4_is_closed_and_external_trust_root_is_null() -> None:
    config = runner._load_config()
    assert config["status"] == "rework_candidate_v4_execution_closed"
    assert config["external_execution_trust_root"]["reviewed_outer_sha256"] is None
    assert config["gates"]["independent_pre_run_review_passed"] is False
    assert config["gates"]["two_block_pilot_execution_ready"] is False
    assert config["gates"]["user_formal_run_authorized"] is False
    assert config["gates"]["security_certified"] is False


def test_closed_production_consumer_fails_before_pipe_or_science(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_read_frame_with_deadline",
        lambda *_args, **_kwargs: pytest.fail("pipe read reached"),
    )
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    with pytest.raises(RuntimeError, match="execution authority is closed"):
        runner._worker_from_capability(-1, -1)


@pytest.mark.parametrize("tail", [b"x", b"second_frame"])
def test_production_consumer_rejects_trailing_or_replay_before_ack_and_data(
    tail: bytes,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = runner.ControllerLedger()
    envelope = _envelope(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="c" * 64,
    )
    read_fd, write_fd = os.pipe()
    ack_read, ack_write = os.pipe()

    def writer() -> None:
        try:
            runner._write_frame(write_fd, envelope)
            if tail == b"second_frame":
                runner._write_frame(write_fd, envelope)
            else:
                os.write(write_fd, tail)
        except BrokenPipeError:
            pass
        finally:
            os.close(write_fd)

    thread = threading.Thread(target=writer)
    thread.start()
    monkeypatch.setattr(runner, "_require_execution_authority", lambda: runner._load_config())
    monkeypatch.setattr(runner, "_query_process_identity", lambda _pid: envelope["worker_process_identity"])
    monkeypatch.setattr(runner.os, "getppid", lambda: int(envelope["parent_process_identity"]["pid"]))
    monkeypatch.setattr(runner, "_sanitized_environment", lambda source=None: {})
    monkeypatch.setattr(runner, "_pilot_roots", lambda _config: _test_roots(tmp_path))
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    emitted_schemas: list[str] = []
    original_write = runner._write_frame_with_deadline

    def recording_write(descriptor, payload, timeout, label):
        emitted_schemas.append(str(payload.get("schema")))
        return original_write(descriptor, payload, timeout, label)

    monkeypatch.setattr(runner, "_write_frame_with_deadline", recording_write)
    with pytest.raises(ValueError, match="trailing|replay"):
        runner._worker_from_capability(
            read_fd,
            ack_write,
            read_handle=41,
            ack_handle=42,
            ledger=ledger,
            handshake_timeout_seconds=1.0,
        )
    hello = runner._read_frame_with_deadline(ack_read, 1.0, "HELLO")
    assert hello["schema"] == runner.HELLO_SCHEMA
    assert emitted_schemas == [runner.HELLO_SCHEMA]
    thread.join(timeout=2)
    os.close(read_fd)
    os.close(ack_read)
    os.close(ack_write)


def test_production_consumer_requires_eof_before_ack_then_reaches_loader(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.ControllerLedger()
    envelope = _envelope(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="d" * 64,
    )
    read_fd, write_fd = os.pipe()
    ack_read, ack_write = os.pipe()

    def writer() -> None:
        runner._write_frame(write_fd, envelope)
        os.close(write_fd)

    thread = threading.Thread(target=writer)
    thread.start()
    monkeypatch.setattr(runner, "_require_execution_authority", lambda: runner._load_config())
    monkeypatch.setattr(
        runner,
        "_query_process_identity",
        lambda pid: (
            envelope["worker_process_identity"]
            if pid == os.getpid()
            else envelope["parent_process_identity"]
        ),
    )
    monkeypatch.setattr(runner.os, "getppid", lambda: int(envelope["parent_process_identity"]["pid"]))
    monkeypatch.setattr(runner, "_sanitized_environment", lambda source=None: {})
    monkeypatch.setattr(runner, "_pilot_roots", lambda _config: _test_roots(tmp_path))
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(RuntimeError("loader sentinel")),
    )
    with pytest.raises(RuntimeError, match="loader sentinel"):
        runner._worker_from_capability(
            read_fd,
            ack_write,
            read_handle=41,
            ack_handle=42,
            ledger=ledger,
            handshake_timeout_seconds=1.0,
        )
    hello = runner._read_frame_with_deadline(ack_read, 1.0, "HELLO")
    assert hello["schema"] == runner.HELLO_SCHEMA
    ack = runner._read_frame_with_deadline(ack_read, 1.0, "ACK")
    assert ack["schema"] == runner.ACK_SCHEMA
    thread.join(timeout=2)
    os.close(read_fd)
    os.close(ack_read)
    os.close(ack_write)


@pytest.mark.parametrize("case", ["0009_first", "block_swap", "replayed_0008"])
def test_production_consumer_rejects_invalid_execution_order_before_data(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.ControllerLedger()
    envelope = _envelope(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="9" * 64,
    )
    if case == "0009_first":
        envelope["block_id"] = runner.BLOCKS[1]
        envelope["execution_index"] = 2
    elif case == "block_swap":
        envelope["block_id"] = runner.BLOCKS[1]
    else:
        envelope["execution_index"] = 2
    read_fd, write_fd = os.pipe()
    ack_read, ack_write = os.pipe()

    def writer() -> None:
        try:
            runner._write_frame(write_fd, envelope)
        except BrokenPipeError:
            pass
        finally:
            os.close(write_fd)

    thread = threading.Thread(target=writer)
    thread.start()
    monkeypatch.setattr(runner, "_require_execution_authority", lambda: runner._load_config())
    monkeypatch.setattr(
        runner,
        "_query_process_identity",
        lambda pid: (
            envelope["worker_process_identity"]
            if pid == os.getpid()
            else envelope["parent_process_identity"]
        ),
    )
    monkeypatch.setattr(
        runner.os,
        "getppid",
        lambda: int(envelope["parent_process_identity"]["pid"]),
    )
    monkeypatch.setattr(runner, "_sanitized_environment", lambda source=None: {})
    monkeypatch.setattr(runner, "_pilot_roots", lambda _config: _test_roots(tmp_path))
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    with pytest.raises((TypeError, ValueError), match="block|index|predecessor|0008|0009"):
        runner._worker_from_capability(
            read_fd,
            ack_write,
            read_handle=41,
            ack_handle=42,
            ledger=None,
            handshake_timeout_seconds=1.0,
        )
    hello = runner._read_frame_with_deadline(ack_read, 1.0, "HELLO")
    assert hello["schema"] == runner.HELLO_SCHEMA
    thread.join(timeout=2)
    for descriptor in (read_fd, ack_read, ack_write):
        os.close(descriptor)


def test_production_consumer_rejects_ordinary_and_wrong_direction_handles(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(runner, "_require_execution_authority", lambda: runner._load_config())
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    ordinary = os.open(runner.__file__, os.O_RDONLY)
    ack_read, ack_write = os.pipe()
    with pytest.raises(ValueError, match="anonymous pipe"):
        runner._worker_from_capability(ordinary, ack_write)
    os.close(ordinary)
    request_read, request_write = os.pipe()
    with pytest.raises(ValueError, match="writable|direction"):
        runner._worker_from_capability(request_read, ack_read)
    for descriptor in (request_read, request_write, ack_read, ack_write):
        os.close(descriptor)


def test_execution_index_and_immutable_predecessor_ledger_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.ControllerLedger()
    with pytest.raises(ValueError, match="0009|predecessor|index"):
        _envelope(
            tmp_path,
            monkeypatch,
            ledger=ledger,
            block_id=runner.BLOCKS[1],
            execution_index=2,
            nonce="e" * 64,
        )
    with pytest.raises(ValueError, match="block|index"):
        _envelope(
            tmp_path,
            monkeypatch,
            ledger=ledger,
            block_id=runner.BLOCKS[1],
            execution_index=1,
            nonce="f" * 64,
        )
    first = _source_attempt(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="1" * 64,
    )
    replay = dataclasses.replace(first, execution_index=2, block_id=runner.BLOCKS[1])
    with pytest.raises(ValueError, match="digest|predecessor|replay"):
        ledger.accept(replay)
    second_envelope = _envelope(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[1],
        execution_index=2,
        nonce="0" * 64,
    )
    second_envelope["ledger_digest_before"] = "0" * 64
    with pytest.raises(ValueError, match="ledger"):
        runner._accept_worker_attempt(
            envelope=second_envelope,
            ack=runner._build_ack(second_envelope),
            payload_path=Path(str(second_envelope["worker_payload_path"])),
            attempt_receipt_path=Path(
                str(second_envelope["attempt_receipt_path"])
            ),
            popen_identity=second_envelope["worker_process_identity"],
            ledger=ledger,
        )


def test_attempt_receipt_never_claims_validation_or_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.ControllerLedger()
    accepted = _source_attempt(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="2" * 64,
    )
    receipt = json.loads(accepted.source_attempt_receipt_path.read_text(encoding="utf-8"))
    assert receipt["attempt_complete"] is True
    assert receipt["controller_validation_passed"] is False
    assert receipt["published"] is False
    assert "published_by_controller" not in receipt


def test_accepted_evidence_is_frozen_and_contains_ack_process_and_source_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.ControllerLedger()
    accepted = _source_attempt(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="3" * 64,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        accepted.ack_sha256 = "0" * 64  # type: ignore[misc]
    assert accepted.ack_bytes
    assert accepted.ack_sha256 == runner._sha256_bytes(accepted.ack_bytes)
    assert accepted.popen_pid == accepted.worker_creation_identity["pid"]
    assert accepted.source_payload_sha256 == runner._sha256(accepted.source_payload_path)
    assert accepted.source_attempt_receipt_sha256 == runner._sha256(
        accepted.source_attempt_receipt_path
    )
    assert accepted.scientific_payload_sha256


def test_result_and_attempt_receipt_paths_are_exact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = runner.ControllerLedger()
    envelope = _envelope(
        tmp_path,
        monkeypatch,
        ledger=ledger,
        block_id=runner.BLOCKS[0],
        execution_index=1,
        nonce="4" * 64,
    )
    runner._validate_attempt_paths(envelope, runner._load_config())
    for field, suffix in (
        ("worker_payload_path", "other.json"),
        ("attempt_receipt_path", "receipt.json"),
    ):
        mutated = dict(envelope)
        mutated[field] = str(Path(str(envelope[field])).with_name(suffix))
        with pytest.raises(ValueError, match="canonical attempt path"):
            runner._validate_attempt_paths(mutated, runner._load_config())


def test_silent_child_times_out_and_is_reaped_with_exclusive_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    with pytest.raises(runner.DispatchFailure) as captured:
        runner._synthetic_dispatch_probe(tmp_path, mode="silent", timeout_seconds=0.2)
    assert captured.value.child_alive is False
    assert captured.value.mathematical_infeasibility_inferred is False
    assert (tmp_path / "stdout.log").is_file()
    assert (tmp_path / "stderr.log").is_file()


def test_flooding_child_does_not_deadlock_and_logs_are_ordinary_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    report = runner._synthetic_dispatch_probe(
        tmp_path, mode="flood", timeout_seconds=5.0
    )
    assert report["probe_passed"] is True
    assert report["child_alive"] is False
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["formal_writes"] == 0
    assert (tmp_path / "stdout.log").stat().st_size > 65536
    assert (tmp_path / "stderr.log").stat().st_size > 65536


@pytest.mark.parametrize(
    "victim",
    [
        "configs/rq2_public_grid_two_block_pilot_candidate_v1.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v1.OUTER.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v2.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v2.OUTER.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v2.yaml",
        "configs/rq2_public_grid_solver_recovery_v2.SHA256SUMS.json",
        "configs/rq2_public_grid_solver_recovery_preregistration_v2.yaml",
        "configs/rq2_public_grid_solver_recovery_review_rework_v1.yaml",
        "configs/rq2_public_pipeline_provenance_contract_v4_process_isolated_v1.yaml",
        "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml",
        "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1.py",
        "experiments/validate_rq2_public_grid_solver_recovery_v2.py",
        "tests/test_rq2_public_grid_solver_recovery_v2.py",
        "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml",
        "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json",
        "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py",
        "configs/rq2_public_grid_two_block_pilot_candidate_v3.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v3.OUTER.SHA256SUMS.json",
        "experiments/run_rq2_public_grid_two_block_pilot_candidate_v3.py",
        "configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v3.yaml",
    ],
)
def test_every_predecessor_authority_class_drift_fails_closed(
    victim: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runner._sha256
    target = runner.ROOT / victim
    monkeypatch.setattr(
        runner,
        "_sha256",
        lambda path: "0" * 64 if Path(path) == target else original(Path(path)),
    )
    with pytest.raises(ValueError, match="authority|drift|hash"):
        runner._verify_predecessor_authority()


def test_v4_execution_chain_requires_external_reviewed_outer_digest() -> None:
    inspected = runner._inspect_v4_chain()
    assert inspected["outer_sha256"]
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v4_execution_chain(None)
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v4_execution_chain("0" * 64)


@pytest.mark.parametrize(
    "victim",
    [
        *sorted(runner.V4_BUNDLE_INVENTORY),
        "configs/rq2_public_grid_two_block_pilot_candidate_v4.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v4.OUTER.SHA256SUMS.json",
    ],
)
def test_v4_chain_live_byte_drift_fails_closed(
    victim: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    original = runner._sha256
    target = runner.ROOT / victim
    expected_outer = original(runner.OUTER)
    monkeypatch.setattr(
        runner,
        "_sha256",
        lambda path: "0" * 64 if Path(path) == target else original(Path(path)),
    )
    with pytest.raises(ValueError, match="authority|drift|hash|trust root"):
        if target == runner.OUTER:
            runner._verify_v4_execution_chain(expected_outer)
        else:
            runner._inspect_v4_chain()


def test_typed_tree_rejects_nested_manifest_file_dir_swap_and_reparse(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "tree"
    (root / "workers").mkdir(parents=True)
    (root / "workers" / "payload.json").write_text("{}", encoding="utf-8")
    (root / "workers" / "SHA256SUMS.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="nested manifest"):
        runner._typed_tree(root)
    (root / "workers" / "SHA256SUMS.json").unlink()
    expected = runner._typed_tree(root)
    (root / "workers" / "payload.json").unlink()
    (root / "workers" / "payload.json").mkdir()
    assert runner._typed_tree(root) != expected
    original = runner._is_link_or_reparse
    monkeypatch.setattr(
        runner,
        "_is_link_or_reparse",
        lambda path: path.name == "payload.json" or original(path),
    )
    with pytest.raises(ValueError, match="reparse"):
        runner._typed_tree(root)


def test_actual_windows_junction_or_deterministic_reparse_seam_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "tree"
    target = tmp_path / "target"
    root.mkdir()
    target.mkdir()
    junction = root / "junction"
    created = False
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(junction), str(target)],
            capture_output=True,
            check=False,
            text=True,
        )
        created = completed.returncode == 0
    if not created:
        junction.mkdir()
        original = runner._is_link_or_reparse
        monkeypatch.setattr(
            runner,
            "_is_link_or_reparse",
            lambda path: path == junction or original(path),
        )
    with pytest.raises(ValueError, match="reparse"):
        runner._typed_tree(root)


def _publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    ledger: runner.ControllerLedger | None = None,
    hook=None,
) -> tuple[dict[str, object], Path, Path]:
    roots = _patch_roots(monkeypatch, tmp_path)
    complete = ledger or _complete_ledger(tmp_path, monkeypatch)
    config = runner._load_config()
    controller = runner._build_controller_receipt(config, complete)
    summary = runner._publish_result(
        tmp_path / "staging",
        roots["result"],
        roots["success_seal"],
        config=config,
        controller=controller,
        ledger=complete,
        pre_rename_test_hook=hook,
    )
    return summary, roots["result"], roots["success_seal"]


def test_publication_separates_validation_receipt_and_postrename_success_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    summary, target, seal = _publish(tmp_path, monkeypatch)
    assert summary["status"] == "complete_nonformal_pilot"
    for block_id in runner.BLOCKS:
        validation = json.loads(
            (target / "workers" / block_id / "validation_receipt.json").read_text(
                encoding="utf-8"
            )
        )
        assert validation["controller_validation_passed"] is True
        assert validation["published"] is False
    published = json.loads(seal.read_text(encoding="utf-8"))
    assert published["published"] is True
    assert published["after_atomic_rename_readback_passed"] is True


@pytest.mark.parametrize("mutation", ["missing_ack", "wrong_ack", "source_memory"])
def test_publication_rejects_ack_and_source_memory_mismatch(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _complete_ledger(tmp_path, monkeypatch)
    first, second = ledger.records
    if mutation == "missing_ack":
        first = dataclasses.replace(first, ack_bytes=b"")
    elif mutation == "wrong_ack":
        first = dataclasses.replace(first, ack_sha256="0" * 64)
    else:
        first.source_payload_path.write_text("{}", encoding="utf-8")
    bad = runner.ControllerLedger(records=(first, second))
    roots = _test_roots(tmp_path)
    with pytest.raises((TypeError, ValueError)):
        runner._publish_result(
            tmp_path / "staging",
            roots["result"],
            roots["success_seal"],
            config=runner._load_config(),
            controller=runner._build_controller_receipt(runner._load_config(), ledger),
            ledger=bad,
        )
    assert not roots["result"].exists()
    assert not roots["success_seal"].exists()


@pytest.mark.parametrize(
    "mutation", ["co_tamper", "extra_last_boundary", "nested_manifest", "file_dir_swap"]
)
def test_publication_final_boundary_tamper_keeps_target_and_success_seal_absent(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _complete_ledger(tmp_path, monkeypatch)
    roots = _test_roots(tmp_path)

    def tamper(staging: Path) -> None:
        if mutation == "co_tamper":
            base = staging / "workers" / runner.BLOCKS[0]
            payload = json.loads((base / "payload.json").read_text(encoding="utf-8"))
            payload["scientific_payload_sha256"] = "0" * 64
            (base / "payload.json").write_text(json.dumps(payload), encoding="utf-8")
            attempt = json.loads(
                (base / "attempt_receipt.json").read_text(encoding="utf-8")
            )
            attempt["worker_payload_sha256"] = runner._sha256(base / "payload.json")
            (base / "attempt_receipt.json").write_text(
                json.dumps(attempt), encoding="utf-8"
            )
            manifest = staging / "SHA256SUMS.json"
            manifest.unlink()
            runner.recovery._atomic_json(manifest, runner._typed_tree(staging))
        elif mutation == "extra_last_boundary":
            (staging / "extra.txt").write_text("x", encoding="utf-8")
        elif mutation == "nested_manifest":
            (staging / "workers" / "SHA256SUMS.json").write_text(
                "{}", encoding="utf-8"
            )
        else:
            path = staging / "workers" / runner.BLOCKS[0] / "payload.json"
            path.unlink()
            path.mkdir()

    with pytest.raises((TypeError, ValueError)):
        runner._publish_result(
            tmp_path / "staging",
            roots["result"],
            roots["success_seal"],
            config=runner._load_config(),
            controller=runner._build_controller_receipt(runner._load_config(), ledger),
            ledger=ledger,
            pre_rename_test_hook=tamper,
        )
    assert not roots["result"].exists()
    assert not roots["success_seal"].exists()


def test_publication_target_preexist_preserves_user_data_and_no_success_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger = _complete_ledger(tmp_path, monkeypatch)
    roots = _test_roots(tmp_path)
    roots["result"].mkdir()
    marker = roots["result"] / "user.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner._publish_result(
            tmp_path / "staging",
            roots["result"],
            roots["success_seal"],
            config=runner._load_config(),
            controller=runner._build_controller_receipt(runner._load_config(), ledger),
            ledger=ledger,
        )
    assert marker.read_text(encoding="utf-8") == "preserve"
    assert not roots["success_seal"].exists()


def test_validate_only_is_zero_worker_solver_result_and_formal_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("process or solver dispatch"),
    )
    monkeypatch.setattr(
        runner.recovery,
        "_atomic_json",
        lambda *_args, **_kwargs: pytest.fail("write attempted"),
    )
    report = runner.run(validate_only=True)
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["worker_processes_started"] == 0
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0
    assert report["mathematical_infeasibility_inferred"] is False
