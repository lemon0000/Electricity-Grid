from __future__ import annotations

import os
import shutil
import stat
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4
from experiments import run_rq2_public_grid_two_block_pilot_candidate_v5 as v5
from experiments import run_rq2_public_grid_two_block_pilot_candidate_v6 as runner
from tests import test_rq2_public_grid_two_block_pilot_candidate_v4 as v4_fixtures


def test_v6_candidate_is_closed() -> None:
    config = runner._load_config()
    assert config["status"] == "presence_recovery_candidate_v6_execution_closed"
    assert config["external_execution_trust_root"]["reviewed_outer_sha256"] is None
    assert config["gates"]["two_block_pilot_execution_ready"] is False
    assert config["gates"]["user_formal_run_authorized"] is False


def _publication_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[v4.ControllerLedger, dict[str, object], dict[str, object], Path, Path, Path]:
    ledger = v4_fixtures._complete_ledger(tmp_path, monkeypatch)
    config = v5._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    return (
        ledger,
        config,
        controller,
        tmp_path / "result",
        tmp_path / "success",
        tmp_path / "terminal",
    )


def _directory_link(link: Path, target: Path) -> None:
    if os.name == "nt":
        completed = subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(link), str(target)],
            capture_output=True,
            check=False,
            text=True,
        )
        if completed.returncode != 0:
            pytest.fail(f"native junction creation failed: {completed.stderr}")
    else:
        os.symlink(target, link, target_is_directory=True)


def test_v5_broken_success_link_is_misreported_as_clean_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    outcome = v5._publish_result(
        tmp_path / "staging",
        target,
        success,
        terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    assert outcome["classification"] == "committed_success"
    backing = tmp_path / "removed-success-backing"
    success.rename(backing)
    _directory_link(success, backing)
    shutil.rmtree(backing)
    assert os.path.lexists(success)

    reproduced = v5._reconcile_publication(
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=None,
        original_error=None,
    )
    assert reproduced["classification"] == "honest_incomplete"
    assert reproduced["success_commit_exists"] is False


def _v6_publication_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[v4.ControllerLedger, dict[str, object], dict[str, object], Path, Path, Path]:
    ledger = v4_fixtures._complete_ledger(tmp_path, monkeypatch)
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    return (
        ledger,
        config,
        controller,
        tmp_path / "v6-result",
        tmp_path / "v6-success",
        tmp_path / "v6-terminal",
    )


def _publish_v6(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    post_hook=None,
    pre_hook=None,
) -> tuple[dict[str, object], Path, Path, Path, v4.ControllerLedger]:
    ledger, config, controller, target, success, terminal = _v6_publication_case(
        tmp_path, monkeypatch
    )
    monkeypatch.setattr(
        runner.v4.recovery.v4,
        "_process_block",
        lambda *_args, **_kwargs: pytest.fail("solver path reached"),
    )
    monkeypatch.setattr(
        runner.v4.recovery.v4,
        "load_rts_gmlc_chronological_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    monkeypatch.setattr(
        runner.v4.recovery.v4,
        "_write_checkpoint",
        lambda *_args, **_kwargs: pytest.fail("formal checkpoint write reached"),
    )
    monkeypatch.setattr(
        runner.v4.recovery.v4,
        "_write_gzip_csv",
        lambda *_args, **_kwargs: pytest.fail("formal result write reached"),
    )
    outcome = runner._publish_result(
        tmp_path / "v6-staging",
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


def _assert_indeterminate(
    caught: pytest.ExceptionInfo[runner.SuccessCommitIndeterminateError],
) -> dict[str, object]:
    outcome = caught.value.outcome
    assert outcome["classification"] == "commit_indeterminate"
    assert outcome["published"] is False
    assert outcome["success_commit_accepted"] is False
    assert outcome["terminal_state_created"] is False
    assert outcome["resume_allowed"] is False
    assert outcome["mathematical_infeasibility_inferred"] is False
    return outcome


def test_v6_normal_commit_and_clean_absent_recovery_states(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    absent_target = tmp_path / "absent-result"
    absent_success = tmp_path / "absent-success"
    absent_terminal = tmp_path / "absent-terminal"
    ledger, config, controller, _target, _success, _terminal = _v6_publication_case(
        tmp_path, monkeypatch
    )
    incomplete = runner._reconcile_publication(
        target=absent_target,
        success_directory=absent_success,
        terminal_directory=absent_terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=None,
        original_error=None,
    )
    assert incomplete["classification"] == "honest_incomplete"
    assert incomplete["success_commit_presence"]["clean_absent"] is True
    assert incomplete["terminal_state_presence"]["clean_absent"] is True

    outcome, target, success, terminal, ledger = _publish_v6(
        tmp_path / "published", monkeypatch
    )
    controller = v4._build_controller_receipt(config, ledger)
    payload = runner.load_verified_success_commit(
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    assert outcome["classification"] == "committed_success"
    assert outcome["success_commit_presence"]["classification"] == "ordinary_directory"
    assert outcome["terminal_state_presence"]["clean_absent"] is True
    assert payload["schema"] == runner.SUCCESS_PAYLOAD_SCHEMA
    assert payload["published"] is True
    assert not os.path.lexists(terminal)


def test_v6_precommit_failure_remains_honest_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_before_result_rename(_staging: Path) -> None:
        raise RuntimeError("synthetic precommit failure")

    outcome, target, success, terminal, _ledger = _publish_v6(
        tmp_path, monkeypatch, pre_hook=fail_before_result_rename
    )
    assert outcome["classification"] == "honest_incomplete"
    assert outcome["published"] is False
    assert not os.path.lexists(target)
    assert not os.path.lexists(success)
    assert not os.path.lexists(terminal)


def test_v6_postcommit_broken_native_junction_is_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def break_success(
        success: Path, _expectation: runner.SuccessCommitExpectation
    ) -> None:
        backing = tmp_path / "removed-v6-success-backing"
        success.rename(backing)
        _directory_link(success, backing)
        shutil.rmtree(backing)
        assert os.path.lexists(success)

    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        _publish_v6(tmp_path, monkeypatch, post_hook=break_success)
    outcome = _assert_indeterminate(caught)
    success = tmp_path / "v6-success"
    terminal = tmp_path / "v6-terminal"
    assert outcome["success_commit_exists"] is True
    assert outcome["success_commit_presence"]["classification"] == "link_or_reparse"
    assert os.path.lexists(success)
    assert not os.path.lexists(terminal)


@pytest.mark.parametrize("terminal_kind", ["file", "directory"])
def test_v6_exact_success_rejects_ordinary_terminal_file_or_directory(
    terminal_kind: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _outcome, target, success, terminal, ledger = _publish_v6(tmp_path, monkeypatch)
    success_hash = runner._sha256(success / "success.json")
    if terminal_kind == "file":
        terminal.write_text("terminal sentinel", encoding="ascii")
    else:
        terminal.mkdir()
        (terminal / "sentinel.txt").write_text("terminal sentinel", encoding="ascii")
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
    outcome = _assert_indeterminate(caught)
    assert outcome["terminal_state_exists"] is True
    assert outcome["terminal_state_presence"]["classification"] == f"ordinary_{terminal_kind}"
    assert runner._sha256(success / "success.json") == success_hash
    assert os.path.lexists(terminal)


def test_v6_exact_success_rejects_broken_terminal_junction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _outcome, target, success, terminal, ledger = _publish_v6(tmp_path, monkeypatch)
    backing = tmp_path / "removed-terminal-backing"
    backing.mkdir()
    _directory_link(terminal, backing)
    shutil.rmtree(backing)
    assert os.path.lexists(terminal)
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
    outcome = _assert_indeterminate(caught)
    assert outcome["terminal_state_exists"] is True
    assert outcome["terminal_state_presence"]["classification"] == "link_or_reparse"
    assert os.path.lexists(terminal)
    assert success.is_dir()


def test_v6_rejects_success_ordinary_file_without_overwrite(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _v6_publication_case(
        tmp_path, monkeypatch
    )
    success.write_text("appearance only", encoding="ascii")
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        runner._reconcile_publication(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
            expectation=None,
            original_error=None,
        )
    outcome = _assert_indeterminate(caught)
    assert outcome["success_commit_exists"] is True
    assert outcome["success_commit_presence"]["classification"] == "ordinary_file"
    assert success.read_text(encoding="ascii") == "appearance only"


def test_v6_rejects_alias_in_success_ancestor_before_resolve(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, _success, terminal = _v6_publication_case(
        tmp_path, monkeypatch
    )
    success_parent = tmp_path / "success-parent"
    success = success_parent / "commit"
    outcome = runner._publish_result(
        tmp_path / "v6-staging",
        target,
        success,
        terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    assert outcome["classification"] == "committed_success"
    original_parent = success_parent
    backing_parent = original_parent.with_name(f"{original_parent.name}-backing")
    original_parent.rename(backing_parent)
    _directory_link(original_parent, backing_parent)
    aliased_success = original_parent / success.name
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        runner.load_verified_success_commit(
            target=target,
            success_directory=aliased_success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    observed = _assert_indeterminate(caught)
    assert observed["success_commit_exists"] is True
    assert observed["success_commit_presence"]["classification"] == "link_or_reparse"
    assert observed["success_commit_presence"]["first_issue_path"] == str(original_parent)
    assert os.path.lexists(original_parent)


def test_v6_posix_broken_symlink_or_windows_deterministic_symlink_seam(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "broken-symlink"
    if os.name != "nt":
        os.symlink(tmp_path / "missing-target", path, target_is_directory=True)
    else:
        real_lexists = runner._lexists_for_presence
        real_lstat = runner._lstat_for_presence
        monkeypatch.setattr(
            runner,
            "_lexists_for_presence",
            lambda candidate: True if Path(candidate) == path else real_lexists(candidate),
        )
        monkeypatch.setattr(
            runner,
            "_lstat_for_presence",
            lambda candidate: (
                SimpleNamespace(st_mode=stat.S_IFLNK, st_file_attributes=0)
                if Path(candidate) == path
                else real_lstat(candidate)
            ),
        )
    presence = runner._probe_path(path, label="broken POSIX symlink")
    assert presence.classification == "link_or_reparse"
    assert presence.path_appearance is True
    assert presence.clean_absent is False


@pytest.mark.parametrize("alias_location", ["leaf", "ancestor"])
def test_v6_deterministic_windows_reparse_seam_rejects_leaf_and_ancestor(
    alias_location: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ancestor = tmp_path / "reparse-parent"
    ancestor.mkdir()
    leaf = ancestor / "reparse-leaf"
    leaf.mkdir()
    marked = leaf if alias_location == "leaf" else ancestor
    real_lstat = runner._lstat_for_presence

    def marked_lstat(path: Path):
        observed = real_lstat(path)
        if Path(path) != marked:
            return observed
        return SimpleNamespace(
            st_mode=observed.st_mode,
            st_file_attributes=int(getattr(observed, "st_file_attributes", 0)) | 0x400,
        )

    monkeypatch.setattr(runner, "_lstat_for_presence", marked_lstat)
    presence = runner._probe_path(leaf, label="deterministic reparse seam")
    assert presence.classification == "link_or_reparse"
    assert presence.first_issue_path == str(marked)
    assert presence.path_appearance is True
    assert presence.clean_absent is False


def test_v6_deterministic_mount_ancestor_is_not_clean_absent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ancestor = tmp_path / "mount-parent"
    ancestor.mkdir()
    leaf = ancestor / "absent-leaf"
    real_ismount = runner._ismount_for_presence
    monkeypatch.setattr(
        runner,
        "_ismount_for_presence",
        lambda path: True if Path(path) == ancestor else real_ismount(path),
    )
    presence = runner._probe_path(leaf, label="mount ancestor")
    assert presence.classification == "mount_alias"
    assert presence.first_issue_path == str(ancestor)
    assert presence.path_appearance is True


@pytest.mark.parametrize(
    "victim",
    [
        "configs/rq2_public_grid_two_block_pilot_candidate_v5.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_candidate_v5.OUTER.SHA256SUMS.json",
        "configs/rq2_public_grid_two_block_pilot_pre_run_review_rework_v5.yaml",
        "experiments/run_rq2_public_grid_two_block_pilot_candidate_v5.py",
    ],
)
def test_v6_predecessor_authority_drift_fails_closed(
    victim: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = runner.ROOT / victim
    original_v6 = runner._sha256
    original_v5 = runner.predecessor._sha256
    original_v4 = runner.v4._sha256
    monkeypatch.setattr(
        runner,
        "_sha256",
        lambda path: "0" * 64 if Path(path) == target else original_v6(Path(path)),
    )
    monkeypatch.setattr(
        runner.predecessor,
        "_sha256",
        lambda path: "0" * 64 if Path(path) == target else original_v5(Path(path)),
    )
    monkeypatch.setattr(
        runner.v4,
        "_sha256",
        lambda path: "0" * 64 if Path(path) == target else original_v4(Path(path)),
    )
    if target == runner.V5_RUNNER:
        monkeypatch.setattr(
            runner,
            "V5_SOURCE_HASHES",
            {**runner.V5_SOURCE_HASHES, "_publish_result": "0" * 64},
        )
    with pytest.raises(ValueError, match="authority|drift|hash|chain"):
        runner._verify_predecessor_authority()


def test_v6_external_execution_chain_requires_reviewed_outer() -> None:
    inspected = runner._inspect_v6_chain()
    assert inspected["outer_sha256"]
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v6_execution_chain(None)
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v6_execution_chain("0" * 64)


def test_v6_validate_only_is_zero_worker_solver_and_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.v4.subprocess,
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
