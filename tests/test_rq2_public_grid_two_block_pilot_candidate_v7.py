"""Focused publication-presence snapshot tests for closed candidate v7."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4
from experiments import run_rq2_public_grid_two_block_pilot_candidate_v6 as v6
from experiments import run_rq2_public_grid_two_block_pilot_candidate_v7 as runner
from tests import test_rq2_public_grid_two_block_pilot_candidate_v4 as v4_fixtures


def test_v7_snapshot_type_is_deeply_immutable() -> None:
    assert runner.PublicationPresenceSnapshot.__dataclass_params__.frozen is True
    assert runner.FrozenPathPresence.__dataclass_params__.frozen is True
    assert runner.PathSegmentPresence.__dataclass_params__.frozen is True


def _publication_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[v4.ControllerLedger, dict[str, object], dict[str, object], Path, Path, Path]:
    ledger = v4_fixtures._complete_ledger(tmp_path, monkeypatch)
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    return (
        ledger,
        config,
        controller,
        tmp_path / "v7-result",
        tmp_path / "v7-success",
        tmp_path / "v7-terminal",
    )


def _zero_science(monkeypatch: pytest.MonkeyPatch) -> None:
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


def _publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    post_hook=None,
    pre_hook=None,
):
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    _zero_science(monkeypatch)
    outcome = runner._publish_result(
        tmp_path / "v7-staging",
        target,
        success,
        terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        pre_rename_test_hook=pre_hook,
        post_commit_test_hook=post_hook,
    )
    return outcome, target, success, terminal, ledger, config, controller


def test_v7_exact_commit_and_recovery_use_final_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome, target, success, terminal, ledger, config, controller = _publish(
        tmp_path, monkeypatch
    )
    assert outcome["classification"] == "committed_success"
    assert outcome["published"] is True
    calls: list[str] = []
    real_probe = runner._probe_one_path

    def counted(path: Path, *, label: str):
        calls.append(str(path))
        return real_probe(path, label=label)

    monkeypatch.setattr(runner, "_probe_one_path", counted)
    payload = runner.load_verified_success_commit(
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    assert payload["schema"] == runner.SUCCESS_PAYLOAD_SCHEMA
    assert calls == [str(target), str(success), str(terminal)] * 2
    assert not os.path.lexists(terminal)


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
    assert not (
        outcome["published"] and outcome["terminal_state_exists"]
    ), "success and terminal must never be accepted together"
    return outcome


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


def _decision(
    *,
    target: Path,
    success: Path,
    terminal: Path,
    config: dict[str, object],
    controller: dict[str, object],
    ledger: v4.ControllerLedger,
):
    snapshot = runner._capture_publication_presence_snapshot(
        target=target, success_directory=success, terminal_directory=terminal
    )
    return runner._reconcile_publication(
        snapshot=snapshot,
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=None,
        original_error=None,
    )


@pytest.mark.parametrize("result_state", ["absent", "ordinary_unsealed_directory"])
def test_v7_honest_incomplete_truth_table_at_production_and_recovery_entries(
    result_state: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Recovery entry.
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path / "recovery", monkeypatch
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    if result_state == "ordinary_unsealed_directory":
        target.mkdir()
    decision = _decision(
        target=target,
        success=success,
        terminal=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
    )
    assert decision.outcome["classification"] == "honest_incomplete"
    assert decision.outcome["published"] is False
    with pytest.raises(ValueError, match="recovery forbidden"):
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )

    # Production entry reaches the same table without publishing success.
    production = tmp_path / "production"
    if result_state == "absent":
        def fail_before_rename(_staging: Path) -> None:
            raise RuntimeError("synthetic precommit stop")

        outcome, ptarget, psuccess, pterminal, *_ = _publish(
            production, monkeypatch, pre_hook=fail_before_rename
        )
        assert not os.path.lexists(ptarget)
    else:
        def remove_seal_after_commit(
            committed: Path, _expectation: runner.SuccessCommitExpectation
        ) -> None:
            committed.rename(committed.with_name("withdrawn-test-seal"))

        outcome, ptarget, psuccess, pterminal, *_ = _publish(
            production, monkeypatch, post_hook=remove_seal_after_commit
        )
        assert ptarget.is_dir()
    assert outcome["classification"] == "honest_incomplete"
    assert outcome["published"] is False
    assert not os.path.lexists(psuccess)
    assert not os.path.lexists(pterminal)


def _mutate_publication(
    case: str, *, target: Path, success: Path, terminal: Path, base: Path
) -> None:
    if case == "terminal_file":
        terminal.write_text("terminal", encoding="ascii")
    elif case == "terminal_directory":
        terminal.mkdir()
    elif case == "success_corrupt":
        (success / "success.json").write_bytes(b"{}\n")
    elif case == "success_manifest_mismatch":
        (success / "SHA256SUMS.json").write_bytes(b"{}\n")
    elif case == "result_binding_mismatch":
        (target / "summary.json").write_bytes(b"{}\n")
    elif case == "success_broken_link":
        backing = base / "removed-success-backing"
        success.rename(backing)
        _directory_link(success, backing)
        shutil.rmtree(backing)
    elif case == "result_broken_link":
        backing = base / "removed-result-backing"
        target.rename(backing)
        _directory_link(target, backing)
        shutil.rmtree(backing)
    elif case == "terminal_broken_link":
        backing = base / "removed-terminal-backing"
        backing.mkdir()
        _directory_link(terminal, backing)
        shutil.rmtree(backing)
    elif case == "exact_success":
        return
    else:  # pragma: no cover - protects the table itself
        raise AssertionError(case)


_MUTATION_CASES = [
    "terminal_file",
    "terminal_directory",
    "success_corrupt",
    "success_manifest_mismatch",
    "result_binding_mismatch",
    "success_broken_link",
    "result_broken_link",
    "terminal_broken_link",
]


@pytest.mark.parametrize("case", _MUTATION_CASES)
def test_v7_indeterminate_truth_table_at_production_postcommit_boundary(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def mutate(
        _success: Path, _expectation: runner.SuccessCommitExpectation
    ) -> None:
        _mutate_publication(
            case,
            target=tmp_path / "v7-result",
            success=tmp_path / "v7-success",
            terminal=tmp_path / "v7-terminal",
            base=tmp_path,
        )

    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        _publish(tmp_path, monkeypatch, post_hook=mutate)
    outcome = _assert_indeterminate(caught)
    assert outcome["publication_presence_snapshot_sha256"]
    assert outcome["publication_presence_snapshot"][
        "snapshot_sha256"
    ] == outcome["publication_presence_snapshot_sha256"]


@pytest.mark.parametrize("case", _MUTATION_CASES + ["exact_success"])
def test_v7_truth_table_at_recovery_entry(
    case: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome, target, success, terminal, ledger, config, controller = _publish(
        tmp_path, monkeypatch
    )
    assert outcome["classification"] == "committed_success"
    _mutate_publication(
        case, target=target, success=success, terminal=terminal, base=tmp_path
    )
    if case == "exact_success":
        payload = runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
        assert payload["published"] is True
        return
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    _assert_indeterminate(caught)


@pytest.mark.parametrize("leaf", ["result", "success", "terminal"])
def test_v7_ordinary_file_leaf_is_indeterminate_before_content_reads(
    leaf: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    paths = {"result": target, "success": success, "terminal": terminal}
    paths[leaf].write_text("appearance", encoding="ascii")
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        _decision(
            target=target,
            success=success,
            terminal=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    outcome = _assert_indeterminate(caught)
    assert outcome[f"{'target' if leaf == 'result' else leaf + '_commit' if leaf == 'success' else 'terminal_state'}_exists"] is True
    assert paths[leaf].read_text(encoding="ascii") == "appearance"


def test_v7_native_broken_terminal_ancestor_is_indeterminate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outcome, target, success, _terminal, ledger, config, controller = _publish(
        tmp_path, monkeypatch
    )
    assert outcome["classification"] == "committed_success"
    terminal_parent = tmp_path / "terminal-parent"
    terminal_parent.mkdir()
    terminal = terminal_parent / "terminal"
    backing = tmp_path / "removed-terminal-parent"
    terminal_parent.rename(backing)
    _directory_link(terminal_parent, backing)
    shutil.rmtree(backing)
    assert os.path.lexists(terminal_parent)
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    observed = _assert_indeterminate(caught)
    assert observed["terminal_state_presence"]["classification"] == "link_or_reparse"
    assert observed["terminal_state_presence"]["first_issue_path"] == str(terminal_parent)


def _publish_separate_parents(
    base: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    post_hook=None,
):
    ledger = v4_fixtures._complete_ledger(base, monkeypatch)
    config = runner._publication_config()
    controller = v4._build_controller_receipt(config, ledger)
    target = base / "result-parent" / "result"
    success = base / "success-parent" / "success"
    terminal = base / "terminal-parent" / "terminal"
    for parent in (target.parent, success.parent, terminal.parent):
        parent.mkdir(exist_ok=True)
    _zero_science(monkeypatch)
    outcome = runner._publish_result(
        base / "staging",
        target,
        success,
        terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        post_commit_test_hook=post_hook,
    )
    return outcome, target, success, terminal, ledger, config, controller


@pytest.mark.parametrize("entry", ["production", "recovery"])
@pytest.mark.parametrize("victim", ["result", "success", "terminal"])
def test_v7_native_broken_ancestor_matrix_at_both_entries(
    entry: str, victim: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    paths: dict[str, Path] = {}

    def break_ancestor() -> None:
        selected = paths[victim]
        parent = selected.parent
        backing = tmp_path / f"removed-{victim}-parent"
        parent.rename(backing)
        _directory_link(parent, backing)
        shutil.rmtree(backing)
        assert os.path.lexists(parent)

    if entry == "production":
        def hook(success: Path, expectation: runner.SuccessCommitExpectation) -> None:
            paths.update(
                {
                    "result": tmp_path / "result-parent" / "result",
                    "success": success,
                    "terminal": tmp_path / "terminal-parent" / "terminal",
                }
            )
            break_ancestor()

        with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
            _publish_separate_parents(tmp_path, monkeypatch, post_hook=hook)
    else:
        (
            outcome,
            target,
            success,
            terminal,
            ledger,
            config,
            controller,
        ) = _publish_separate_parents(tmp_path, monkeypatch)
        assert outcome["classification"] == "committed_success"
        paths.update({"result": target, "success": success, "terminal": terminal})
        break_ancestor()
        with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
            runner.load_verified_success_commit(
                target=target,
                success_directory=success,
                terminal_directory=terminal,
                config=config,
                controller=controller,
                ledger=ledger,
            )
    observed = _assert_indeterminate(caught)
    key = {
        "result": "target_presence",
        "success": "success_commit_presence",
        "terminal": "terminal_state_presence",
    }[victim]
    assert observed[key]["classification"] == "link_or_reparse"
    assert observed[key]["first_issue_path"] == str(paths[victim].parent)


def test_v7_posix_symlink_or_deterministic_windows_reparse_recovery_gate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    target.mkdir()
    if os.name != "nt":
        target.rmdir()
        os.symlink(tmp_path / "missing-result", target, target_is_directory=True)
    else:
        real_lstat = v6._lstat_for_presence

        def reparse_lstat(path: Path):
            observed = real_lstat(path)
            if Path(path) != target:
                return observed
            return SimpleNamespace(
                st_mode=observed.st_mode,
                st_file_attributes=int(getattr(observed, "st_file_attributes", 0))
                | 0x400,
            )

        monkeypatch.setattr(v6, "_lstat_for_presence", reparse_lstat)
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        _decision(
            target=target,
            success=success,
            terminal=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    observed = _assert_indeterminate(caught)
    assert observed["target_presence"]["classification"] == "link_or_reparse"


@pytest.mark.parametrize("seam", ["mount", "inaccessible"])
def test_v7_mount_and_inaccessible_ancestor_seams_fail_closed(
    seam: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    ancestor = tmp_path / "guarded"
    ancestor.mkdir()
    target = ancestor / "result"
    if seam == "mount":
        real_ismount = v6._ismount_for_presence
        monkeypatch.setattr(
            v6,
            "_ismount_for_presence",
            lambda path: True if Path(path) == ancestor else real_ismount(path),
        )
    else:
        real_lstat = v6._lstat_for_presence

        def inaccessible(path: Path):
            if Path(path) == ancestor:
                raise PermissionError("synthetic inaccessible ancestor")
            return real_lstat(path)

        monkeypatch.setattr(v6, "_lstat_for_presence", inaccessible)
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        _decision(
            target=target,
            success=success,
            terminal=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    observed = _assert_indeterminate(caught)
    assert observed["target_presence"]["classification"] in {
        "mount_alias",
        "inaccessible",
    }


def test_v7_unreadable_exact_success_is_indeterminate_without_deletion(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _outcome, target, success, terminal, ledger, config, controller = _publish(
        tmp_path, monkeypatch
    )
    success_hash = runner._sha256(success / "success.json")
    monkeypatch.setattr(
        runner,
        "_read_success_member",
        lambda _path: (_ for _ in ()).throw(PermissionError("synthetic unreadable")),
    )
    with pytest.raises(runner.SuccessCommitIndeterminateError) as caught:
        runner.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )
    _assert_indeterminate(caught)
    assert runner._sha256(success / "success.json") == success_hash
    assert success.is_dir()
    assert not os.path.lexists(terminal)


def test_v7_outcome_and_honest_reconcile_do_not_reprobe_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ledger, config, controller, target, success, terminal = _publication_case(
        tmp_path, monkeypatch
    )
    calls = 0
    real_probe = runner._probe_one_path

    def counted(path: Path, *, label: str):
        nonlocal calls
        calls += 1
        return real_probe(path, label=label)

    monkeypatch.setattr(runner, "_probe_one_path", counted)
    snapshot = runner._capture_publication_presence_snapshot(
        target=target, success_directory=success, terminal_directory=terminal
    )
    assert calls == 3
    decision = runner._reconcile_publication(
        snapshot=snapshot,
        target=target,
        success_directory=success,
        terminal_directory=terminal,
        config=config,
        controller=controller,
        ledger=ledger,
        expectation=None,
        original_error=None,
    )
    assert decision.outcome["classification"] == "honest_incomplete"
    assert calls == 3


@pytest.mark.parametrize("final_change", ["content_tamper", "terminal_appearance"])
def test_v7_final_snapshot_boundary_revalidates_before_acceptance(
    final_change: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _outcome, target, success, terminal, ledger, config, controller = _publish(
        tmp_path, monkeypatch
    )
    real_capture = runner._capture_publication_presence_snapshot
    captures = 0

    def capture(**kwargs):
        nonlocal captures
        captures += 1
        if captures == 2 and final_change == "terminal_appearance":
            terminal.write_text("appeared at final boundary", encoding="ascii")
        observed = real_capture(**kwargs)
        if captures == 2 and final_change == "content_tamper":
            (success / "success.json").write_bytes(b"{}\n")
        return observed

    monkeypatch.setattr(runner, "_capture_publication_presence_snapshot", capture)
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
    assert captures == 2
    assert outcome["published"] is False


def test_v7_candidate_closed_and_validate_only_uses_one_publication_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runner._load_config()
    assert config["status"] == "publication_presence_snapshot_candidate_v7_execution_closed"
    assert config["external_execution_trust_root"]["reviewed_outer_sha256"] is None
    assert config["gates"]["two_block_pilot_execution_ready"] is False
    assert config["gates"]["user_formal_run_authorized"] is False
    observed_paths: list[str] = []
    real_probe = runner._probe_one_path

    def counted(path: Path, *, label: str):
        observed_paths.append(str(path))
        return real_probe(path, label=label)

    monkeypatch.setattr(runner, "_probe_one_path", counted)
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
    roots = runner._pilot_roots(config)
    assert observed_paths[:3] == [
        str(roots["result"]),
        str(roots["success_commit"]),
        str(roots["forbidden_terminal"]),
    ]
    assert len(observed_paths) == 5
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["worker_processes_started"] == 0
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0
    assert report["mathematical_infeasibility_inferred"] is False


def test_v7_external_execution_chain_requires_reviewed_outer() -> None:
    inspected = runner._inspect_v7_chain()
    assert inspected["outer_sha256"]
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v7_execution_chain(None)
    with pytest.raises(ValueError, match="external trust root"):
        runner._verify_v7_execution_chain("0" * 64)
