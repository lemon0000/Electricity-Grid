from __future__ import annotations

import dataclasses
import json
import subprocess
import threading
from pathlib import Path

import pytest

from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v1 as publisher,
)
from experiments import rq2_public_grid_evidence_publication_contract_v1 as contract
from experiments import (
    run_rq2_public_grid_evidence_publication_successor_v1 as controller,
)


def test_bundle_is_closed_and_validate_only_is_zero_effect(capsys: pytest.CaptureFixture[str]) -> None:
    assert controller.main(["--validate-only"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["worker_processes_started"] == 0
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["result_writes"] == 0
    with pytest.raises(contract.ContractRejected):
        controller.main(["--execute"])


def test_evidence_has_no_public_constructor_or_accept_api() -> None:
    with pytest.raises(TypeError):
        contract.AcceptedEvidenceVnext()  # type: ignore[call-arg]
    assert not hasattr(contract.ControllerLedgerVnext, "accept")
    assert not hasattr(contract.ControllerLedgerVnext, "append")
    assert not hasattr(controller.ReviewController, "accept_evidence")


def test_real_two_child_review_fixture_commits_with_vnext_only(tmp_path: Path) -> None:
    outcome = controller.run_review_fixture_e2e(tmp_path)
    assert outcome["classification"] == "committed_success"
    assert outcome["published"] is True
    assert outcome["review_fixture"] is True
    assert outcome["nonformal"] is True
    assert outcome["claim"] is False
    assert outcome["worker_processes_started"] == 2
    assert outcome["scientific_loader_calls"] == 0
    assert outcome["solver_calls"] == 0
    assert outcome["ledger_record_count"] == 2
    assert outcome["worker_pids"][0] != outcome["worker_pids"][1]
    assert publisher.reconcile_publication(outcome["paths"])["classification"] == (
        "committed_success"
    )


def test_vnext_ledger_rejects_cross_protocol_and_manual_dataclass(tmp_path: Path) -> None:
    session = controller.ReviewController(tmp_path / "session")
    with pytest.raises(contract.ContractRejected):
        session._ledger._append_controller(object(), token=object())
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as old

    assert old.AcceptedEvidence is not contract.AcceptedEvidenceVnext


def test_deep_frozen_evidence_and_replay_reorder_are_rejected(tmp_path: Path) -> None:
    result = controller.run_review_fixture_e2e(tmp_path)
    records = result["ledger"].records
    with pytest.raises((dataclasses.FrozenInstanceError, AttributeError)):
        records[0].block_id = "holdout_s20260822_0009"  # type: ignore[misc]
    with pytest.raises(contract.ContractRejected):
        contract.verify_frozen_ledger((records[1], records[0]), result["receipt"])
    with pytest.raises(contract.ContractRejected):
        contract.verify_frozen_ledger((records[0], records[0]), result["receipt"])


def test_publisher_rejects_co_tamper_before_commit(tmp_path: Path) -> None:
    session = controller.ReviewController(tmp_path / "session")
    session.dispatch_next_review_fixture()
    session.dispatch_next_review_fixture()
    receipt = session.seal_receipt()
    evidence = session.ledger.records[0]
    source = Path(evidence.result_path)
    value = json.loads(source.read_text(encoding="utf-8"))
    value["scientific_payload"]["all_hours_resolved"] = False
    source.write_bytes(contract.exact_json_bytes(value))
    receipt_path = Path(evidence.attempt_receipt_path)
    receipt = json.loads(receipt_path.read_bytes())
    receipt["result_sha256"] = contract.sha256_bytes(source.read_bytes())
    receipt_path.write_bytes(contract.exact_json_bytes(receipt))
    paths = publisher.publication_paths(tmp_path / "published")
    with pytest.raises(contract.ContractRejected):
        publisher.publish_review_fixture(session.ledger, receipt, paths)
    assert not paths.result.exists()
    assert not paths.success.exists()


@pytest.mark.parametrize(
    "fault_stage, expected",
    [
        ("controller_post_block2_pre_publish", "target_absent"),
        ("controller_post_publish", "commit_indeterminate"),
    ],
)
def test_closure_drift_is_fail_closed_at_publication_boundaries(
    tmp_path: Path, fault_stage: str, expected: str
) -> None:
    verifier = contract.StageAwareClosureVerifier(fault_stage=fault_stage)
    session = controller.ReviewController(tmp_path / "session", verifier=verifier)
    session.dispatch_next_review_fixture()
    session.dispatch_next_review_fixture()
    paths = publisher.publication_paths(tmp_path / "published")
    if expected == "target_absent":
        with pytest.raises(contract.LiveClosureDrift):
            session.publish(paths)
        assert not paths.result.exists()
    else:
        outcome = session.publish(paths)
        assert outcome["classification"] == "commit_indeterminate"
        assert outcome["published"] is False
        assert paths.result.exists()
        assert not paths.terminal.exists()


def test_fixture_hashes_are_exact_and_recovery_validated() -> None:
    config = contract.load_config()
    for block_id in contract.BLOCKS:
        payload = contract.build_review_fixture_payload(block_id)
        raw = contract.exact_json_bytes(payload)
        assert contract.sha256_bytes(raw) == config["fixture"]["payload_sha256"][block_id]
        assert contract.validate_scientific_payload(payload, block_id)["all_hours_resolved"] is True


def test_attempt_is_atomically_consumed_and_concurrent_retry_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    session = controller.ReviewController(tmp_path / "session")
    entered = threading.Barrier(2)
    release = threading.Event()
    calls: list[int] = []

    def stopped(index: int) -> contract.AcceptedEvidenceVnext:
        calls.append(index)
        entered.wait(timeout=5)
        release.wait(timeout=5)
        raise controller.ControllerRejected("registered synthetic attempt failure")

    monkeypatch.setattr(session, "_spawn_and_accept", stopped)
    failures: list[BaseException] = []

    def invoke() -> None:
        try:
            session.dispatch_next_review_fixture()
        except BaseException as exc:  # noqa: BLE001 - assert both fail closed
            failures.append(exc)

    first = threading.Thread(target=invoke)
    first.start()
    entered.wait(timeout=5)
    second = threading.Thread(target=invoke)
    second.start()
    second.join(timeout=5)
    release.set()
    first.join(timeout=5)
    assert calls == [1]
    assert len(failures) == 2
    with pytest.raises(contract.ContractRejected):
        session.dispatch_next_review_fixture()
    assert calls == [1]


@pytest.mark.parametrize(
    ("field", "replacement"),
    [
        ("protocol", "old-v4-protocol"),
        ("session_id", "cross-session"),
        ("block_id", "holdout_s20260822_0009"),
        ("nonce", "replayed"),
        ("worker_pid", 1),
        ("command", ("python", "sleep.py")),
        ("ack_bytes", b"{}\n"),
        ("scientific_bytes", b"{}\n"),
    ],
)
def test_every_authority_family_tamper_rejected(
    tmp_path: Path, field: str, replacement: object
) -> None:
    session = controller.ReviewController(tmp_path / "session")
    evidence = session.dispatch_next_review_fixture()
    corrupt = object.__new__(contract.AcceptedEvidenceVnext)
    for name in contract.AcceptedEvidenceVnext.__dataclass_fields__:
        object.__setattr__(corrupt, name, getattr(evidence, name))
    object.__setattr__(corrupt, field, replacement)
    with pytest.raises(contract.ContractRejected):
        contract.validate_evidence(corrupt, session_key=session._ledger._session_key)


def test_preexisting_result_and_terminal_appearance_fail_closed(tmp_path: Path) -> None:
    session = controller.ReviewController(tmp_path / "session")
    session.dispatch_next_review_fixture()
    session.dispatch_next_review_fixture()
    receipt = session.seal_receipt()
    paths = publisher.publication_paths(tmp_path / "published")
    paths.result.mkdir()
    with pytest.raises(contract.ContractRejected):
        publisher.publish_review_fixture(session.ledger, receipt, paths)
    assert paths.result.exists()
    assert not paths.success.exists()
    paths.result.rmdir()
    paths.terminal.write_text("appeared", encoding="utf-8")
    with pytest.raises(contract.ContractRejected):
        publisher.publish_review_fixture(session.ledger, receipt, paths)
    assert paths.terminal.exists()


def test_post_rename_race_is_indeterminate_and_never_cleaned(tmp_path: Path) -> None:
    session = controller.ReviewController(tmp_path / "session")
    session.dispatch_next_review_fixture()
    session.dispatch_next_review_fixture()
    receipt = session.seal_receipt()
    paths = publisher.publication_paths(tmp_path / "published")
    with pytest.raises(contract.ContractRejected):
        publisher.publish_review_fixture(
            session.ledger,
            receipt,
            paths,
            registered_test_hook="extra_after_result_rename",
        )
    assert paths.result.exists()
    assert publisher.reconcile_publication(paths)["classification"] == "commit_indeterminate"
    assert not paths.success.exists()
    assert not paths.terminal.exists()


def test_bootstrap_direct_validate_and_worker_production_entry_closed() -> None:
    python = contract.load_config()["runtime"]["locked_python_executable"]
    validate = subprocess.run(
        [python, "-B", "-m", "experiments.bootstrap_rq2_public_grid_evidence_publication_successor_v1", "--validate-only"],
        cwd=contract.ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert validate.returncode == 0
    report = json.loads(validate.stdout)
    assert report["worker_processes_started"] == 0
    assert report["solver_calls"] == 0
    worker = subprocess.run(
        [python, "-B", "-m", "experiments.worker_rq2_public_grid_evidence_publication_successor_v1"],
        cwd=contract.ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert worker.returncode != 0
    assert "review closed" in worker.stderr
