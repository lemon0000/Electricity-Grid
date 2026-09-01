from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments import (
    bootstrap_rq2_public_grid_evidence_publication_successor_v2 as bootstrap,
)
from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v2 as publisher,
)
from experiments import rq2_public_grid_evidence_publication_contract_v2 as contract
from experiments import (
    run_rq2_public_grid_evidence_publication_successor_v2 as controller,
)
from experiments import (
    worker_rq2_public_grid_evidence_publication_successor_v2 as worker,
)


def test_validate_only_is_closed_and_zero_effect(capsys: pytest.CaptureFixture[str]) -> None:
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


def test_ordinary_import_exposes_no_composable_acceptance_authority() -> None:
    forbidden = (
        "factory",
        "session_key",
        "secret_key",
        "sign_record",
        "append_record",
        "seal_receipt",
        "accept_evidence",
        "publish_authority",
    )
    for module in (bootstrap, contract, controller, publisher, worker):
        names = tuple(name.lower() for name in dir(module))
        assert not any(term in name for term in forbidden for name in names)
    assert not hasattr(controller, "ReviewController")
    assert not hasattr(contract, "ControllerLedger")
    assert not hasattr(contract, "AcceptedEvidence")


def test_zero_worker_complete_forgery_cannot_publish(tmp_path: Path) -> None:
    outcome = controller.run_review_fixture_e2e(
        tmp_path / "forged", registered_test_case="zero_worker_complete_forgery"
    )
    assert outcome.classification == "rejected_before_result"
    assert outcome.worker_processes_started == 0
    assert outcome.published is False
    assert not Path(outcome.result_path).exists()
    assert not Path(outcome.success_path).exists()


def test_real_two_child_review_fixture_commits_without_returning_authority(
    tmp_path: Path,
) -> None:
    outcome = controller.run_review_fixture_e2e(tmp_path / "positive")
    assert outcome.classification == "committed_success"
    assert outcome.published is True
    assert outcome.review_fixture is True
    assert outcome.nonformal is True
    assert outcome.claim is False
    assert outcome.worker_processes_started == 2
    assert outcome.scientific_loader_calls == 0
    assert outcome.solver_calls == 0
    assert len(outcome.worker_pids) == 2
    assert outcome.worker_pids[0] != outcome.worker_pids[1]
    assert len(outcome.pipe_authority_digests) == 2
    assert not hasattr(outcome, "ledger")
    assert not hasattr(outcome, "evidence")
    assert not hasattr(outcome, "session_key")


def test_full_closure_is_complete_canonical_mapping() -> None:
    mapping = contract.verify_full_live_closure()
    config = contract.load_config()
    assert isinstance(mapping, dict)
    assert config["predecessor"]["outer_path"] in mapping
    assert set(config["bundle"]["members"].values()).issubset(mapping)
    assert contract.closure_mapping_sha256(mapping) == contract.closure_mapping_sha256(
        dict(reversed(tuple(mapping.items())))
    )
    assert len(mapping) >= 19


@pytest.mark.parametrize(
    ("result_kind", "success_kind", "terminal_kind", "result_exact", "success_exact", "expected"),
    [
        ("absent", "absent", "absent", False, False, "honest_incomplete"),
        ("directory", "absent", "absent", False, False, "commit_indeterminate"),
        ("absent", "directory", "absent", False, False, "commit_indeterminate"),
        ("directory", "directory", "absent", True, True, "committed_success"),
        ("directory", "directory", "file", True, True, "commit_indeterminate"),
        ("file", "absent", "absent", False, False, "commit_indeterminate"),
        ("absent", "absent", "directory", False, False, "commit_indeterminate"),
        ("alias", "absent", "absent", False, False, "commit_indeterminate"),
        ("absent", "alias", "absent", False, False, "commit_indeterminate"),
        ("absent", "absent", "alias", False, False, "commit_indeterminate"),
    ],
)
def test_machine_truth_table(
    tmp_path: Path,
    result_kind: str,
    success_kind: str,
    terminal_kind: str,
    result_exact: bool,
    success_exact: bool,
    expected: str,
) -> None:
    paths = publisher.publication_paths(tmp_path / "result")
    try:
        publisher.materialize_presence_for_test(
            paths,
            result_kind=result_kind,
            success_kind=success_kind,
            terminal_kind=terminal_kind,
        )
        snapshot = publisher.capture_presence(paths)
    except OSError as exc:
        # Windows without SeCreateSymbolicLinkPrivilege still exercises the exact
        # independent V2 classification branch through a deterministic reparse
        # snapshot; real aliases remain covered whenever the OS permits creation.
        if "alias" not in (result_kind, success_kind, terminal_kind) or getattr(
            exc, "winerror", None
        ) != 1314:
            raise
        classifications = {
            "absent": ("clean_absent", True, False),
            "directory": ("ordinary_directory", False, True),
            "file": ("ordinary_file", False, False),
            "alias": ("windows_reparse_point", False, False),
        }
        result_class, result_absent, result_dir = classifications[result_kind]
        success_class, success_absent, success_dir = classifications[success_kind]
        terminal_class, terminal_absent, terminal_dir = classifications[terminal_kind]
        snapshot = publisher.PresenceSnapshot(
            result_classification=result_class,
            success_classification=success_class,
            terminal_classification=terminal_class,
            result_clean_absent=result_absent,
            success_clean_absent=success_absent,
            terminal_clean_absent=terminal_absent,
            result_ordinary_directory=result_dir,
            success_ordinary_directory=success_dir,
            terminal_ordinary_directory=terminal_dir,
        )
    assert publisher.classify_publication(
        snapshot, result_exact=result_exact, success_exact=success_exact
    ) == expected


@pytest.mark.parametrize(
    "case",
    [
        "tamper_hello",
        "tamper_envelope",
        "tamper_ack",
        "tamper_result",
        "tamper_attempt_receipt",
        "tamper_closure_mapping",
        "cross_session",
        "replay_0008",
        "swap_blocks",
        "co_tamper_sources",
        "cross_protocol_v1",
    ],
)
def test_transport_or_evidence_tamper_rejected_before_result(
    tmp_path: Path, case: str
) -> None:
    outcome = controller.run_review_fixture_e2e(
        tmp_path / case, registered_test_case=case
    )
    assert outcome.classification == "rejected_before_result"
    assert outcome.published is False
    assert not Path(outcome.result_path).exists()
    assert not Path(outcome.success_path).exists()


@pytest.mark.parametrize(
    ("case", "expected", "result_exists", "success_exists"),
    [
        ("closure_pre_result", "rejected_before_result", False, False),
        ("extra_before_result_rename", "rejected_before_result", False, False),
        ("closure_post_result", "commit_indeterminate", True, False),
        ("extra_post_result", "commit_indeterminate", True, False),
        ("closure_post_success", "commit_indeterminate", True, True),
        ("corrupt_post_success", "commit_indeterminate", True, True),
    ],
)
def test_publication_boundaries_are_fail_closed(
    tmp_path: Path,
    case: str,
    expected: str,
    result_exists: bool,
    success_exists: bool,
) -> None:
    outcome = controller.run_review_fixture_e2e(
        tmp_path / case, registered_test_case=case
    )
    assert outcome.classification == expected
    assert outcome.published is False
    assert Path(outcome.result_path).exists() is result_exists
    assert Path(outcome.success_path).exists() is success_exists
    assert not Path(outcome.terminal_path).exists()


def test_pipe_authority_binds_roles_types_directions_and_parent(tmp_path: Path) -> None:
    outcome = controller.run_review_fixture_e2e(tmp_path / "pipe")
    assert outcome.classification == "committed_success"
    assert outcome.pipe_authority_verified is True
    assert outcome.parent_identity_verified is True
    assert outcome.raw_handle_roles_verified is True
