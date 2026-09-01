from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4
from experiments import run_rq2_public_grid_two_block_pilot_candidate_v5 as runner
from tests import test_rq2_public_grid_two_block_pilot_candidate_v4 as v4_fixtures


def test_v5_candidate_is_closed_and_has_no_external_trust_root() -> None:
    config = runner._load_config()
    assert config["status"] == "postcommit_remediation_candidate_v5_execution_closed"
    assert config["external_execution_trust_root"]["reviewed_outer_sha256"] is None
    assert config["gates"]["two_block_pilot_execution_ready"] is False
    assert config["gates"]["user_formal_run_authorized"] is False


def _publication_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[
    v4.ControllerLedger,
    dict[str, object],
    dict[str, object],
    Path,
    Path,
    Path,
]:
    ledger = v4_fixtures._complete_ledger(tmp_path, monkeypatch)
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    return (
        ledger,
        config,
        controller,
        tmp_path / "v5-result",
        tmp_path / "v5-success",
        tmp_path / "v5-terminal-forbidden",
    )


def _publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    pre_hook=None,
    post_hook=None,
) -> tuple[dict[str, object], Path, Path, Path, v4.ControllerLedger]:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    outcome = runner._publish_result(
        tmp_path / "v5-staging",
        target,
        success,
        terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        pre_rename_test_hook=pre_hook,
        post_commit_test_hook=post_hook,
    )
    return outcome, target, success, terminal, ledger


def test_v4_reproduces_postcommit_success_plus_reported_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    roots = v4_fixtures._patch_roots(monkeypatch, tmp_path)
    ledger = v4_fixtures._complete_ledger(tmp_path, monkeypatch)
    config = v4._load_config()
    controller = v4._build_controller_receipt(config, ledger)
    real_atomic_json = v4.recovery._atomic_json

    def commit_then_raise(path: Path, payload: object) -> None:
        real_atomic_json(path, payload)
        if path == roots["success_seal"]:
            raise RuntimeError("review reproduction: exception after seal commit")

    monkeypatch.setattr(v4.recovery, "_atomic_json", commit_then_raise)
    with pytest.raises(RuntimeError, match="after seal commit"):
        v4._publish_result(
            tmp_path / "staging",
            roots["result"],
            roots["success_seal"],
            config=config,
            controller=controller,
            ledger=ledger,
        )

    seal = json.loads(roots["success_seal"].read_text(encoding="utf-8"))
    assert roots["result"].is_dir()
    assert seal["published"] is True


def test_v5_normal_publication_has_one_exact_irreversible_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome, target, success, terminal, ledger = _publish(tmp_path, monkeypatch)
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    payload = runner.load_verified_success_commit(
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    manifest = json.loads((success / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert outcome["classification"] == "committed_success"
    assert outcome["published"] is True
    assert outcome["terminal_state_created"] is False
    assert outcome["resume_allowed"] is False
    assert payload["published"] is True
    assert payload["unique_irreversible_commit_point"] is True
    assert manifest["files"] == {
        "success.json": runner._sha256(success / "success.json")
    }
    assert (success / "success.json").read_bytes() == runner._exact_json_bytes(payload)
    assert target.is_dir()
    assert not terminal.exists()


def test_v5_precommit_failure_is_honest_incomplete_without_published_state(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_before_result_rename(_staging: Path) -> None:
        raise RuntimeError("synthetic pre-commit failure")

    outcome, target, success, terminal, _ledger = _publish(
        tmp_path, monkeypatch, pre_hook=fail_before_result_rename
    )
    assert outcome["classification"] == "honest_incomplete"
    assert outcome["published"] is False
    assert outcome["success_commit_accepted"] is False
    assert outcome["terminal_state_created"] is False
    assert outcome["resume_allowed"] is False
    assert not target.exists()
    assert not success.exists()
    assert not terminal.exists()


def test_v5_seal_precommit_failure_retains_unsealed_target_as_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_publish_success_directory",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("synthetic seal pre-rename failure")
        ),
    )
    outcome, target, success, terminal, _ledger = _publish(tmp_path, monkeypatch)
    assert outcome["classification"] == "honest_incomplete"
    assert outcome["target_exists"] is True
    assert outcome["published"] is False
    assert outcome["terminal_state_created"] is False
    assert target.is_dir()
    assert not success.exists()
    assert not terminal.exists()


def test_v5_postcommit_exact_seal_plus_exception_is_committed_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_after_commit(
        _success: Path, _expectation: runner.SuccessCommitExpectation
    ) -> None:
        raise RuntimeError("synthetic exception after exact commit")

    outcome, target, success, terminal, ledger = _publish(
        tmp_path, monkeypatch, post_hook=fail_after_commit
    )
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    assert outcome["classification"] == "committed_success"
    assert outcome["original_error_type"] == "RuntimeError"
    assert outcome["success_and_terminal_dual_state"] is False
    assert outcome["published"] is True
    assert not terminal.exists()
    assert runner.load_verified_success_commit(
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )["published"] is True


@pytest.mark.parametrize("mutation", ["corrupt", "target_mismatch", "unreadable"])
def test_v5_postcommit_unprovable_state_is_indeterminate_without_terminal(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate_after_commit(
        success: Path, _expectation: runner.SuccessCommitExpectation
    ) -> None:
        if mutation == "corrupt":
            (success / "success.json").write_text("{}\n", encoding="utf-8")
        elif mutation == "target_mismatch":
            target = tmp_path / "v5-result" / "summary.json"
            target.write_text("{}\n", encoding="utf-8")
        else:
            monkeypatch.setattr(
                runner,
                "_read_success_member",
                lambda _path: (_ for _ in ()).throw(
                    PermissionError("synthetic unreadable commit")
                ),
            )

    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        _publish(tmp_path, monkeypatch, post_hook=mutate_after_commit)
    outcome = caught.value.outcome
    assert outcome["classification"] == "commit_indeterminate"
    assert outcome["published"] is False
    assert outcome["success_commit_accepted"] is False
    assert outcome["terminal_state_created"] is False
    assert outcome["resume_allowed"] is False
    assert outcome["mathematical_infeasibility_inferred"] is False
    assert (tmp_path / "v5-result").exists()
    assert (tmp_path / "v5-success").exists()
    assert not (tmp_path / "v5-terminal-forbidden").exists()


def test_v5_exact_success_plus_terminal_dual_state_is_never_accepted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome, target, success, terminal, ledger = _publish(tmp_path, monkeypatch)
    assert outcome["classification"] == "committed_success"
    terminal.mkdir()
    (terminal / "injected.txt").write_text("forbidden", encoding="ascii")
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    assert caught.value.outcome["success_and_terminal_dual_state"] is True
    assert caught.value.outcome["published"] is False
    assert caught.value.outcome["terminal_state_created"] is False
    assert caught.value.resume_allowed is False


def test_v5_recovery_rejects_file_shape_and_missing_seal(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    with pytest.raises(ValueError, match="missing"):
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    success.write_text("appearance only", encoding="ascii")
    with pytest.raises(runner.SuccessCommitIndeterminateError):
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )


@pytest.mark.parametrize(
    "victim",
    [
        "configs/rq2_public_grid_two_block_pilot_candidate_v4.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v4.OUTER.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_pre_run_review_escalation_v4.yaml",
        "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal.py",
        "tests/test_rts_gmlc_v4_repair_010_recovery_import.py",
        "tests/test_rts_gmlc_v4_repair_010_startup_calibration.py",
    ],
)
def test_v5_predecessor_and_repair010_authority_drift_fails_closed(
    victim: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = runner.ROOT / victim
    original_v5 = runner._sha256
    original_v4 = runner.predecessor._sha256

    def replacement(path: Path) -> str:
        return "0" * 64 if Path(path) == target else original_v5(Path(path))

    monkeypatch.setattr(
        runner,
        "_sha256",
        replacement,
    )
    monkeypatch.setattr(
        runner.predecessor,
        "_sha256",
        lambda path: (
            "0" * 64 if Path(path) == target else original_v4(Path(path))
        ),
    )
    with pytest.raises(ValueError, match="authority|drift|hash|chain"):
        runner._verify_predecessor_authority()


def test_v5_external_execution_chain_requires_reviewed_outer() -> None:
    inspected = runner._inspect_v5_chain()
    assert inspected["outer_sha256"]
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v5_execution_chain(None)
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v5_execution_chain("0" * 64)


def test_v5_validate_only_is_zero_process_solver_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.predecessor.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("worker or solver process started"),
    )
    monkeypatch.setattr(
        runner.recovery,
        "_atomic_json",
        lambda *_args, **_kwargs: pytest.fail("result/formal write attempted"),
    )
    report = runner.run(validate_only=True)
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["worker_processes_started"] == 0
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0
    assert report["mathematical_infeasibility_inferred"] is False
    assert not any(path.exists() for path in runner._pilot_roots(runner._load_config()).values())


def test_v5_publication_tests_never_call_solver_or_formal_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner.predecessor.recovery.v4,
        "_process_block",
        lambda *_args, **_kwargs: pytest.fail("solver path reached"),
    )
    outcome, _target, _success, _terminal, _ledger = _publish(
        tmp_path, monkeypatch
    )
    assert outcome["classification"] == "committed_success"
    assert outcome["formal_execution_ready"] is False
    assert outcome["mathematical_infeasibility_inferred"] is False
    assert os.getpid() > 0
