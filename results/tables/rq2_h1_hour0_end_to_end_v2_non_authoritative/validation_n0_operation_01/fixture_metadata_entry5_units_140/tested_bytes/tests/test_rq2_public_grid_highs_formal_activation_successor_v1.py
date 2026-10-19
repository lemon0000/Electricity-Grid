from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments import (
    bootstrap_rq2_public_grid_highs_formal_activation_successor_v1 as bootstrap,
)
from experiments import rq2_public_grid_highs_formal_activation_contract_v1 as contract
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v2 as controller,
)


def test_static_authority_binds_v8_result_and_keeps_formal_closed() -> None:
    report = contract.validate_static_authority(require_activation_review=False)
    assert report["validation_passed"] is True
    assert report["v8_post_result_independent_review_passed"] is True
    assert report["formal_activation_review_receipt_present"] is False
    assert report["formal_execution_authorized"] is False
    assert report["formal_result_exists"] is False
    assert report["claim"] is False
    assert report["security_certified"] is False
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0


def test_import_and_validate_only_make_zero_solver_or_formal_writes() -> None:
    roots = contract.formal_roots()
    assert all(not path.exists() for path in roots.values())
    report = bootstrap.validate_only()
    assert report["status"] == "READY_FOR_INDEPENDENT_FORMAL_ACTIVATION_REVIEW"
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0
    assert report["formal_controller_spawned"] is False
    assert all(not path.exists() for path in roots.values())


def test_execute_absent_review_receipt_rejects_before_preflight_consume_or_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_capture_preflight",
        lambda: events.append("preflight"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_consume_one_shot_authority",
        lambda _authority: events.append("consume"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_spawn_controller",
        lambda *_args, **_kwargs: events.append("spawn"),
    )
    with pytest.raises(contract.FormalActivationRejected, match="review PASS receipt"):
        bootstrap.execute()
    assert events == []


def test_preflight_persist_readback_precedes_consume_and_spawn(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    events: list[str] = []
    preflight_path = tmp_path / "preflight.json"
    authority_path = tmp_path / "authority.json"
    receipt_path = tmp_path / "activation_receipt.json"
    preflight = {
        "threshold_passed": True,
        "persisted_path": str(preflight_path),
        "persisted_sha256": "a" * 64,
        "stable_readback_verified": True,
    }
    dynamic = {
        "authority_path": str(authority_path),
        "authority_sha256": "b" * 64,
        "activation_receipt_path": str(receipt_path),
        "activation_receipt_sha256": "c" * 64,
    }
    monkeypatch.setattr(
        bootstrap,
        "_require_activation_review",
        lambda: events.append("review") or {"verdict": "PASS"},
    )
    monkeypatch.setattr(
        bootstrap,
        "_require_clean_start",
        lambda: events.append("clean_start"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_capture_preflight",
        lambda: events.append("persist_readback") or preflight,
    )
    monkeypatch.setattr(
        bootstrap,
        "_publish_dynamic_authority",
        lambda _preflight: events.append("dynamic_authority") or dynamic,
    )
    monkeypatch.setattr(
        bootstrap,
        "_consume_one_shot_authority",
        lambda _authority: events.append("consume") or {"state": "consumed"},
    )
    monkeypatch.setattr(
        bootstrap,
        "_spawn_controller",
        lambda *_args, **_kwargs: events.append("spawn")
        or {"pid": 1234, "returncode": None},
    )
    report = bootstrap.execute()
    assert events == [
        "review",
        "clean_start",
        "persist_readback",
        "dynamic_authority",
        "clean_start",
        "consume",
        "spawn",
    ]
    assert report["formal_controller_spawned"] is True
    assert report["formal_result_exists"] is False
    assert report["claim"] is False
    assert report["security_certified"] is False


def test_threshold_failure_persists_evidence_without_consume_spawn_or_formal_roots(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_require_activation_review",
        lambda: events.append("review") or {"verdict": "PASS"},
    )
    monkeypatch.setattr(
        bootstrap,
        "_require_clean_start",
        lambda: events.append("clean_start"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_capture_preflight",
        lambda: events.append("persist_readback")
        or {
            "threshold_passed": False,
            "persisted_path": "preflight.json",
            "persisted_sha256": "a" * 64,
            "stable_readback_verified": True,
        },
    )
    monkeypatch.setattr(
        bootstrap,
        "_publish_dynamic_authority",
        lambda _preflight: events.append("dynamic_authority"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_consume_one_shot_authority",
        lambda _authority: events.append("consume"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_spawn_controller",
        lambda *_args, **_kwargs: events.append("spawn"),
    )
    with pytest.raises(contract.FormalActivationRejected, match="10 GiB"):
        bootstrap.execute()
    assert events == ["review", "clean_start", "persist_readback"]
    assert all(not path.exists() for path in contract.formal_roots().values())


def test_preexisting_formal_root_rejects_before_preflight_or_consume(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "checkpoint"
    root.mkdir()
    monkeypatch.setattr(contract, "formal_roots", lambda: {"checkpoint": root})
    events: list[str] = []
    monkeypatch.setattr(
        bootstrap,
        "_require_activation_review",
        lambda: {"verdict": "PASS"},
    )
    monkeypatch.setattr(
        bootstrap,
        "_capture_preflight",
        lambda: events.append("preflight"),
    )
    monkeypatch.setattr(
        bootstrap,
        "_consume_one_shot_authority",
        lambda _authority: events.append("consume"),
    )
    with pytest.raises(contract.FormalActivationRejected, match="must not preexist"):
        bootstrap.execute()
    assert events == []


def test_formal_config_starts_at_block_zero_and_forbids_all_resume() -> None:
    report = controller.validate_only()
    assert report["power_system_block_count"] == 1071
    assert report["starts_from_block_zero"] is True
    assert report["resume_allowed"] is False
    assert report["predecessor_gurobi_checkpoint_reuse_allowed"] is False
    assert report["predecessor_highs_checkpoint_reuse_allowed"] is False
    assert report["solver_name"] == "highs"
    assert report["highspy_version"] == "1.15.1"
    assert report["threads"] == 4
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0


def test_preflight_machine_evidence_is_atomic_and_complete(tmp_path: Path) -> None:
    mapping = {"configs/example.json": "d" * 64}
    observed = 11 * 1024**3
    report = contract.capture_preflight_evidence(
        tmp_path / "attempt",
        authority_mapping=mapping,
        observed_available_commit_bytes=lambda: observed,
        wall_time_ns=lambda: 100,
        monotonic_ns=lambda: 200,
    )
    path = Path(report["persisted_path"])
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["wall_time_ns"] == 100
    assert stored["monotonic_ns"] == 200
    assert stored["observed_available_commit_bytes"] == observed
    assert stored["preflight_threshold_bytes"] == 10 * 1024**3
    assert stored["child_private_commit_stop_bytes"] == 8 * 1024**3
    assert stored["system_commit_available_stop_bytes"] == 2 * 1024**3
    assert stored["comparison"] == "observed_available_commit_bytes >= preflight_threshold_bytes"
    assert stored["threshold_passed"] is True
    assert stored["authority_mapping"] == mapping
    assert len(stored["authority_mapping_sha256"]) == 64
    assert report["stable_readback_verified"] is True


def test_static_binding_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text("{}\n", encoding="utf-8")
    expected = contract.sha256_file(artifact)
    contract.verify_file_binding(artifact, expected, label="test artifact")
    artifact.write_text('{"drift":true}\n', encoding="utf-8")
    with pytest.raises(contract.FormalActivationRejected, match="drifted"):
        contract.verify_file_binding(artifact, expected, label="test artifact")


def test_checkpoint_binds_complete_resource_journal() -> None:
    journal = {"schema": "example", "status": "child_exited", "samples": [1]}
    envelope = controller.attach_resource_journal_for_test(
        {"schema": "checkpoint", "execution_receipt": {"schema": "receipt"}},
        journal,
        persisted_path="results/logs/example/resource_journal.json",
    )
    assert envelope["resource_journal"] == journal
    assert len(envelope["resource_journal_sha256"]) == 64
    assert envelope["execution_receipt"]["resource_journal"] == journal
    assert envelope["execution_receipt"]["resource_journal_sha256"] == envelope[
        "resource_journal_sha256"
    ]
    assert len(envelope["execution_receipt_sha256"]) == 64


def test_formal_persist_callback_matches_sealed_v8_outcome_schema(
    tmp_path: Path,
) -> None:
    journal = controller.resource_contract.synthetic_resource_journal_for_test(
        pid=1234,
        create_time_ns=5678,
        private_values=(1024,),
        available_values=(12 * 1024**3,),
    )
    path = tmp_path / "resource_journal.json"
    persisted = controller._persist_resource_journal(path, journal)
    validated = controller.resource_contract.validate_resource_monitor_outcome(
        persisted,
        expected_path=str(path),
    )
    assert validated["readback_verified"] is True
    assert validated["resource_journal"]["status"] == "child_exited"
