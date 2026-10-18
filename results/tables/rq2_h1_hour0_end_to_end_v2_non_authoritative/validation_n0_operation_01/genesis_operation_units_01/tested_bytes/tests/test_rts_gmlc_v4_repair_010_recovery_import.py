from __future__ import annotations

import csv
import json
import os
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal as formal,
)
from src.scenarios.common_input_signature import common_input_signature_sha256
from src.solvers.joint_ac_phase_contract import (
    DurablePhaseJournal,
    PhaseContractError,
    expression_fingerprint_sha256,
    load_verified_phase_events,
    solver_input_fingerprint_sha256,
)


def _hash(character: str) -> str:
    return character * 64


def _write_complete_manifest(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    manifest = root / "SHA256SUMS"
    paths = sorted(
        path for path in root.rglob("*") if path.is_file() and path != manifest
    )
    manifest.write_text(
        "".join(
            f"{formal._sha256(path)}  {path.relative_to(root).as_posix()}\n"
            for path in paths
        ),
        encoding="ascii",
    )


def _binding() -> dict[str, object]:
    return formal.build_worker_binding(
        preregistration_id="repair010",
        input_contract_sha256=_hash("1"),
        frontier_manifest_sha256=_hash("2"),
        call_manifest_sha256=_hash("3"),
        candidate_id="candidate_00",
        commitment_sha256=_hash("4"),
        dispatch_sha256=_hash("5"),
        initial_strategy="source",
        prepared_inputs_sha256=_hash("a"),
        ipopt_options_sha256=_hash("b"),
        software_identity={"test": "synthetic"},
    )


def _emit_complete_journal(path: Path, binding: Mapping[str, object]) -> None:
    journal = DurablePhaseJournal(path, binding=binding)
    for event in (
        "worker_started",
        "context_load_started",
        "context_load_completed",
        "prepared_cases_completed",
    ):
        journal.emit(event)
    build = {
        "schema": "rts_gmlc_ac_aware_nlp_expression_fingerprint_v1",
        "variable_count": 2,
        "constraint_count": 1,
        "variable_order_sha256": _hash("c"),
        "objective_expression_sha256": _hash("d"),
        "constraint_order_and_expression_sha256": _hash("e"),
        "prepared_inputs_sha256": binding["prepared_inputs_sha256"],
        "ipopt_options_sha256": binding["ipopt_options_sha256"],
    }
    build["expression_fingerprint_sha256"] = expression_fingerprint_sha256(build)
    journal.emit(
        "nlp_build_started",
        {
            "prepared_inputs_sha256": binding["prepared_inputs_sha256"],
            "ipopt_options_sha256": binding["ipopt_options_sha256"],
        },
    )
    journal.emit("nlp_build_completed", build)
    solve = {
        **build,
        "initial_point_sha256": _hash("f"),
        "variable_lower_sha256": _hash("0"),
        "variable_upper_sha256": _hash("1"),
        "constraint_lower_sha256": _hash("2"),
        "constraint_upper_sha256": _hash("3"),
    }
    solve["solver_input_fingerprint_sha256"] = solver_input_fingerprint_sha256(solve)
    journal.emit("solver_started", solve)
    journal.emit("solver_finished", {**solve, "termination": "returned"})


def _phase_bundle(tmp_path: Path, *, complete: bool) -> dict[str, object]:
    binding = _binding()
    registration = tmp_path / "phase_registration"
    spawn = tmp_path / "phase_spawn"
    completion = tmp_path / "phase_completion"
    journal = tmp_path / "phase.jsonl"
    worker_result = tmp_path / "worker_result"
    native_log = tmp_path / "ipopt.log"
    registration_manifest = formal.register_phase_worker_call(
        registration,
        binding=binding,
        phase_journal=journal,
        worker_result=worker_result,
        native_solver_log=native_log,
        worker_process_log=tmp_path / "worker.log",
        parent_pid=os.getpid(),
    )
    formal.register_phase_worker_spawn(
        spawn,
        phase_registration_directory=registration,
        binding=binding,
        worker_pid=os.getpid(),
    )
    _emit_complete_journal(journal, binding)
    v4._publish_immutable_payload(
        worker_result,
        lambda staging: (staging / "result.txt").write_text("ok", encoding="ascii"),
    )
    native_log.write_text("tiny synthetic IPOPT log\n", encoding="ascii")
    if complete:
        formal.register_phase_completion(
            completion,
            binding=binding,
            phase_registration_manifest_sha256=registration_manifest,
            phase_journal=journal,
            worker_pid=os.getpid(),
            worker_result=worker_result,
            worker_result_manifest_sha256=formal._sha256(worker_result / "SHA256SUMS"),
            native_solver_log=native_log,
        )
    return {
        "registration": registration,
        "spawn": spawn,
        "completion": completion,
        "journal": journal,
        "worker_result": worker_result,
        "native_log": native_log,
        "binding": binding,
    }


def _phase_finalization_evidence(
    tmp_path: Path, *, completion: bool, terminal: bool
) -> formal.PhaseRecoveryEvidence:
    bundle = _phase_bundle(tmp_path, complete=False)
    intent = tmp_path / "phase_finalization_intent"
    terminal_incomplete = tmp_path / "phase_terminal_incomplete"
    success = tmp_path / "phase_finalization_success"
    checkpoint = tmp_path / "joint_call_checkpoint"
    formal.register_phase_finalization_intent(
        intent,
        phase_registration_directory=bundle["registration"],
        phase_spawn_directory=bundle["spawn"],
        binding=bundle["binding"],
        phase_journal=bundle["journal"],
    )
    if completion:
        formal.register_phase_completion(
            bundle["completion"],
            binding=bundle["binding"],
            phase_registration_manifest_sha256=formal._sha256(
                bundle["registration"] / "SHA256SUMS"
            ),
            phase_journal=bundle["journal"],
            worker_pid=os.getpid(),
            worker_result=bundle["worker_result"],
            worker_result_manifest_sha256=formal._sha256(
                bundle["worker_result"] / "SHA256SUMS"
            ),
            native_solver_log=bundle["native_log"],
        )
    if terminal:
        formal.register_phase_terminal_incomplete(
            terminal_incomplete,
            phase_finalization_intent_directory=intent,
            phase_completion_directory=bundle["completion"],
            binding=bundle["binding"],
            reason="synthetic_post_completion_revalidation_failure",
        )
    return formal.PhaseRecoveryEvidence(
        call_manifest_sha256=str(bundle["binding"]["call_manifest_sha256"]),
        call_registration={"parent_pid": os.getpid()},
        worker_result=bundle["worker_result"],
        native_solver_log=bundle["native_log"],
        phase_journal=bundle["journal"],
        phase_registration=bundle["registration"],
        phase_spawn=bundle["spawn"],
        phase_completion=bundle["completion"],
        phase_finalization_intent=intent,
        phase_terminal_incomplete=terminal_incomplete,
        phase_finalization_success=success,
        checkpoint=checkpoint,
        expected_binding=bundle["binding"],
    )


def _exercise_recovery_branch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    evidence: formal.PhaseRecoveryEvidence,
    branch: str,
    *,
    accepted_expected: bool,
) -> None:
    accepted: list[str] = []
    monkeypatch.setattr(formal, "_phase_recovery_evidence", lambda *_args: evidence)
    candidate = SimpleNamespace(candidate_id="candidate_00")
    context = SimpleNamespace(config={"joint_ac": {"initial_strategies": ["source"]}})
    prepared = {"candidate_00": (object(),)}
    chronology = {"candidate_00": object()}
    if branch == "checkpoint":
        monkeypatch.setattr(
            v4, "_joint_checkpoint_path", lambda *_args: evidence.checkpoint
        )
        monkeypatch.setattr(
            v4,
            "_load_joint_checkpoint",
            lambda *_args: accepted.append(branch) or "checkpoint",
        )

        def call() -> object:
            return formal._load_phase_aware_checkpoint(
                context,
                tmp_path,
                candidate,
                "source",
                _hash("f"),
                prepared["candidate_00"],
                chronology["candidate_00"],
            )

        expected_error = PhaseContractError
    elif branch == "worker_result":
        monkeypatch.setattr(
            v4, "_validate_joint_call_registration", lambda *_args: _hash("3")
        )
        real_load_json = v4._load_json

        def load_json(root: Path, name: str) -> dict[str, object]:
            if name == "call.json":
                return {"schema": "synthetic_call"}
            return real_load_json(root, name)

        monkeypatch.setattr(v4, "_load_json", load_json)
        monkeypatch.setattr(
            v4,
            "_registered_joint_worker_paths",
            lambda *_args: (
                evidence.worker_result,
                evidence.native_solver_log,
                tmp_path / "worker.log",
            ),
        )
        monkeypatch.setattr(
            v4,
            "_load_joint_worker_result",
            lambda *_args: (accepted.append(branch) or "rows", _hash("9")),
        )

        def call() -> object:
            return formal._load_phase_aware_worker_result(
                context,
                tmp_path,
                candidate,
                "source",
                _hash("f"),
                prepared["candidate_00"],
                chronology["candidate_00"],
            )

        expected_error = PhaseContractError
    elif branch == "load_all":
        monkeypatch.setattr(
            v4,
            "_load_all_joint_checkpoints",
            lambda *_args: accepted.append(branch) or "all_checkpoints",
        )

        def call() -> object:
            return formal._load_phase_aware_all_checkpoints(
                context,
                tmp_path,
                [candidate],
                _hash("f"),
                prepared,
                chronology,
            )

        expected_error = formal.IsolatedWorkerIncompleteError
    else:
        monkeypatch.setattr(
            v4,
            "_load_joint_results",
            lambda *_args: accepted.append(branch) or {"loaded": True},
        )

        def call() -> object:
            return formal._load_phase_aware_joint_results(
                context,
                tmp_path / "joint_ac",
                {},
                [candidate],
                _hash("f"),
                prepared,
                chronology,
            )

        expected_error = formal.IsolatedWorkerIncompleteError
    if accepted_expected:
        call()
        assert accepted == [branch]
    else:
        with pytest.raises(expected_error) as caught:
            call()
        if isinstance(caught.value, formal.IsolatedWorkerIncompleteError):
            assert caught.value.outcome.solver_call_count == 1
            assert not caught.value.outcome.is_infeasibility_evidence
            assert not caught.value.outcome.resume_allowed
        assert accepted == []


@pytest.mark.parametrize("branch", ("checkpoint", "worker_result", "load_all", "final"))
def test_terminal_incomplete_permanently_blocks_every_recovery_acceptance_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str
) -> None:
    evidence = _phase_finalization_evidence(tmp_path, completion=True, terminal=True)
    evidence.checkpoint.mkdir()
    accepted: list[str] = []
    monkeypatch.setattr(formal, "_phase_recovery_evidence", lambda *_args: evidence)
    candidate = SimpleNamespace(candidate_id="candidate_00")
    context = SimpleNamespace(config={"joint_ac": {"initial_strategies": ["source"]}})
    prepared = {"candidate_00": (object(),)}
    chronology = {"candidate_00": object()}

    if branch == "checkpoint":
        monkeypatch.setattr(
            v4,
            "_joint_checkpoint_path",
            lambda *_args: evidence.checkpoint,
        )
        monkeypatch.setattr(
            v4,
            "_load_joint_checkpoint",
            lambda *_args: accepted.append(branch),
        )

        def call() -> object:
            return formal._load_phase_aware_checkpoint(
                context,
                tmp_path,
                candidate,
                "source",
                _hash("f"),
                prepared["candidate_00"],
                chronology["candidate_00"],
            )

        expected_error = PhaseContractError
    elif branch == "worker_result":
        monkeypatch.setattr(
            v4,
            "_load_joint_worker_result",
            lambda *_args: accepted.append(branch),
        )

        def call() -> object:
            return formal._load_phase_aware_worker_result(
                context,
                tmp_path,
                candidate,
                "source",
                _hash("f"),
                prepared["candidate_00"],
                chronology["candidate_00"],
            )

        expected_error = PhaseContractError
    elif branch == "load_all":
        monkeypatch.setattr(
            v4,
            "_load_all_joint_checkpoints",
            lambda *_args: accepted.append(branch),
        )

        def call() -> object:
            return formal._load_phase_aware_all_checkpoints(
                context,
                tmp_path,
                [candidate],
                _hash("f"),
                prepared,
                chronology,
            )

        expected_error = formal.IsolatedWorkerIncompleteError
    else:
        monkeypatch.setattr(
            v4,
            "_load_joint_results",
            lambda *_args: accepted.append(branch),
        )

        def call() -> object:
            return formal._load_phase_aware_joint_results(
                context,
                tmp_path / "joint_ac",
                {},
                [candidate],
                _hash("f"),
                prepared,
                chronology,
            )

        expected_error = formal.IsolatedWorkerIncompleteError

    with pytest.raises(expected_error) as caught:
        call()
    if isinstance(caught.value, formal.IsolatedWorkerIncompleteError):
        assert caught.value.outcome.solver_call_count == 1
        assert not caught.value.outcome.is_infeasibility_evidence
        assert not caught.value.outcome.resume_allowed
    assert accepted == []


@pytest.mark.parametrize("drift", ("manifest", "binding"))
def test_terminal_incomplete_drift_fails_closed(tmp_path: Path, drift: str) -> None:
    evidence = _phase_finalization_evidence(tmp_path, completion=True, terminal=True)
    payload_path = evidence.phase_terminal_incomplete / "terminal_incomplete.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["reason"] = "tampered" if drift == "manifest" else payload["reason"]
    if drift == "binding":
        payload["binding"]["candidate_id"] = "candidate_drift"
        payload["binding_sha256"] = formal.canonical_sha256(payload["binding"])
    formal.v4._write_exact_json(payload_path, payload)
    if drift == "binding":
        _write_complete_manifest(evidence.phase_terminal_incomplete)

    with pytest.raises(PhaseContractError):
        formal._validate_phase_finalization_for_recovery(evidence)


def test_terminal_publish_failure_leaves_completion_unacceptable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    evidence = _phase_finalization_evidence(tmp_path, completion=True, terminal=False)
    outcome = formal.classify_phase_contract_failure(
        solver_started_was_verified=True,
        reason="synthetic_parent_finalization_failure",
    )

    def fail_publish(_outcome: object) -> None:
        raise OSError("synthetic terminal persistence failure")

    with pytest.raises(formal.TerminalIncompletePersistenceError) as caught:
        formal._persist_terminal_incomplete_or_raise(
            RuntimeError("synthetic parent finalization failure"),
            outcome=outcome,
            persist_terminal=fail_publish,
            on_incomplete=lambda _outcome: None,
        )

    assert caught.value.outcome == outcome
    assert evidence.phase_completion.is_dir()
    assert not evidence.phase_terminal_incomplete.exists()
    assert not evidence.phase_finalization_success.exists()
    with pytest.raises(PhaseContractError, match="success seal is missing"):
        formal._validate_phase_finalization_for_recovery(evidence)


def test_success_seal_requires_and_binds_completion_and_checkpoint(
    tmp_path: Path,
) -> None:
    evidence = _phase_finalization_evidence(tmp_path, completion=True, terminal=False)
    v4._publish_immutable_payload(
        evidence.checkpoint,
        lambda staging: (staging / "checkpoint.txt").write_text(
            "synthetic checkpoint", encoding="ascii"
        ),
    )
    formal.register_phase_finalization_success(
        evidence.phase_finalization_success,
        phase_finalization_intent_directory=evidence.phase_finalization_intent,
        phase_completion_directory=evidence.phase_completion,
        checkpoint_directory=evidence.checkpoint,
        terminal_directory=evidence.phase_terminal_incomplete,
        binding=evidence.expected_binding,
    )

    success = formal._validate_phase_finalization_for_recovery(evidence)

    assert success["successfully_finalized"] is True
    assert success["checkpoint_manifest_sha256"] == formal._sha256(
        evidence.checkpoint / "SHA256SUMS"
    )


@pytest.mark.parametrize("branch", ("checkpoint", "worker_result", "load_all", "final"))
def test_success_seal_post_commit_exception_is_success_for_recovery_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str
) -> None:
    evidence = _phase_finalization_evidence(tmp_path, completion=True, terminal=False)
    v4._publish_immutable_payload(
        evidence.checkpoint,
        lambda staging: (staging / "checkpoint.txt").write_text(
            "synthetic checkpoint", encoding="ascii"
        ),
    )
    real_publish = v4._publish_immutable_payload
    terminal_calls: list[str] = []

    def publish_then_fail(target: Path, *args: object, **kwargs: object) -> None:
        real_publish(target, *args, **kwargs)
        if target == evidence.phase_finalization_success:
            raise RuntimeError("synthetic post-rename verification failure")

    def fail_if_terminal_is_called(*_args: object, **_kwargs: object) -> str:
        terminal_calls.append("called")
        raise OSError("terminal publisher must not run after committed success")

    monkeypatch.setattr(v4, "_publish_immutable_payload", publish_then_fail)
    monkeypatch.setattr(
        formal, "register_phase_terminal_incomplete", fail_if_terminal_is_called
    )

    formal._seal_phase_finalization_or_raise(
        evidence,
        on_incomplete=lambda _outcome: pytest.fail(
            "committed success was reported honest-incomplete"
        ),
    )

    assert terminal_calls == []
    assert formal._validate_phase_finalization_for_recovery(evidence)[
        "successfully_finalized"
    ]
    _exercise_recovery_branch(
        monkeypatch,
        tmp_path,
        evidence,
        branch,
        accepted_expected=True,
    )


@pytest.mark.parametrize("branch", ("checkpoint", "worker_result", "load_all", "final"))
def test_success_seal_pre_commit_failure_is_terminal_for_recovery_branch(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, branch: str
) -> None:
    evidence = _phase_finalization_evidence(tmp_path, completion=True, terminal=False)
    v4._publish_immutable_payload(
        evidence.checkpoint,
        lambda staging: (staging / "checkpoint.txt").write_text(
            "synthetic checkpoint", encoding="ascii"
        ),
    )
    real_publish = v4._publish_immutable_payload

    def fail_before_commit(target: Path, *args: object, **kwargs: object) -> None:
        if target == evidence.phase_finalization_success:
            raise RuntimeError("synthetic pre-rename success failure")
        real_publish(target, *args, **kwargs)

    monkeypatch.setattr(v4, "_publish_immutable_payload", fail_before_commit)
    outcomes: list[object] = []

    with pytest.raises(formal.IsolatedWorkerIncompleteError) as caught:
        formal._seal_phase_finalization_or_raise(
            evidence,
            on_incomplete=outcomes.append,
        )

    assert outcomes == [caught.value.outcome]
    assert caught.value.outcome.solver_call_count == 1
    assert not caught.value.outcome.is_infeasibility_evidence
    assert not caught.value.outcome.resume_allowed
    assert not evidence.phase_finalization_success.exists()
    assert evidence.phase_terminal_incomplete.is_dir()
    _exercise_recovery_branch(
        monkeypatch,
        tmp_path,
        evidence,
        branch,
        accepted_expected=False,
    )


@pytest.mark.parametrize("state", ("missing", "bad", "valid"))
def test_phase_completion_evidence_missing_bad_or_valid(
    tmp_path: Path, state: str
) -> None:
    bundle = _phase_bundle(tmp_path, complete=state != "missing")
    if state == "bad":
        bundle["journal"].write_text("{}\n", encoding="ascii")

    def load() -> dict[str, object]:
        return formal.load_verified_phase_completion(
            phase_registration_directory=bundle["registration"],
            phase_completion_directory=bundle["completion"],
            expected_binding=bundle["binding"],
            expected_phase_journal=bundle["journal"],
            expected_worker_result=bundle["worker_result"],
            expected_native_solver_log=bundle["native_log"],
        )

    if state == "valid":
        assert load()["worker_pid"] == os.getpid()
    else:
        with pytest.raises(PhaseContractError):
            load()


@pytest.mark.parametrize(
    ("state", "expected_solver_call_count"),
    (
        ("solver_started", 1),
        ("corrupt_completion", 1),
        ("pre_solver", 0),
        ("bad_journal", 0),
    ),
)
def test_recovery_completion_failure_counts_only_verified_solver_started(
    tmp_path: Path, state: str, expected_solver_call_count: int
) -> None:
    bundle = _phase_bundle(tmp_path, complete=state == "corrupt_completion")
    journal = bundle["journal"]
    if state == "corrupt_completion":
        (bundle["completion"] / "phase_completion.json").write_text(
            "{}\n", encoding="ascii"
        )
    elif state == "pre_solver":
        lines = journal.read_text(encoding="utf-8").splitlines()
        journal.write_text("\n".join(lines[:4]) + "\n", encoding="utf-8")
    elif state == "bad_journal":
        journal.write_text("{}\n", encoding="ascii")

    outcome = formal._classify_phase_journal_evidence(
        phase_registration=bundle["registration"],
        phase_spawn=bundle["spawn"],
        phase_journal=journal,
        expected_binding=bundle["binding"],
        reason="recovery_phase_completion_missing",
    )

    assert bundle["completion"].exists() is (state == "corrupt_completion")
    assert bundle["worker_result"].is_dir()
    assert outcome.solver_call_count == expected_solver_call_count
    assert not outcome.is_infeasibility_evidence
    assert not outcome.resume_allowed


@pytest.mark.parametrize("failure_stage", ("register", "revalidate"))
def test_post_solver_completion_failure_is_one_call_honest_incomplete(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, failure_stage: str
) -> None:
    bundle = _phase_bundle(tmp_path, complete=False)
    intent = tmp_path / "phase_finalization_intent"
    terminal = tmp_path / "phase_terminal_incomplete"
    formal.register_phase_finalization_intent(
        intent,
        phase_registration_directory=bundle["registration"],
        phase_spawn_directory=bundle["spawn"],
        binding=bundle["binding"],
        phase_journal=bundle["journal"],
    )
    outcomes: list[object] = []
    events = load_verified_phase_events(
        bundle["journal"],
        expected_binding=bundle["binding"],
        expected_worker_pid=os.getpid(),
    )
    assert events[-1]["event"] == "solver_finished"
    if failure_stage == "register":

        def fail_registration(*_args: object, **_kwargs: object) -> str:
            raise RuntimeError("synthetic completion publication failure")

        monkeypatch.setattr(formal, "register_phase_completion", fail_registration)

    def revalidate() -> None:
        if failure_stage == "revalidate":
            raise PhaseContractError("synthetic post-completion revalidation failure")

    def persist_terminal(outcome: object) -> None:
        formal.register_phase_terminal_incomplete(
            terminal,
            phase_finalization_intent_directory=intent,
            phase_completion_directory=bundle["completion"],
            binding=bundle["binding"],
            reason=outcome.reason,
        )

    with pytest.raises(formal.IsolatedWorkerIncompleteError) as caught:
        formal._publish_verified_phase_completion(
            completion_directory=bundle["completion"],
            binding=bundle["binding"],
            phase_registration_manifest_sha256=formal._sha256(
                bundle["registration"] / "SHA256SUMS"
            ),
            phase_journal=bundle["journal"],
            worker_pid=os.getpid(),
            worker_result=bundle["worker_result"],
            worker_result_manifest_sha256=formal._sha256(
                bundle["worker_result"] / "SHA256SUMS"
            ),
            native_solver_log=bundle["native_log"],
            post_completion_validator=revalidate,
            persist_terminal=persist_terminal,
            on_incomplete=outcomes.append,
        )

    outcome = caught.value.outcome
    assert outcomes == [outcome]
    assert outcome.solver_call_count == 1
    assert not outcome.is_infeasibility_evidence
    assert not outcome.resume_allowed
    terminal_payload = formal.load_verified_phase_terminal_incomplete(
        terminal_directory=terminal,
        finalization_intent_directory=intent,
        expected_binding=bundle["binding"],
        expected_phase_registration=bundle["registration"],
        expected_phase_spawn=bundle["spawn"],
        expected_phase_journal=bundle["journal"],
        expected_phase_completion=bundle["completion"],
    )
    assert terminal_payload["solver_call_count"] == 1
    if failure_stage == "register":
        assert terminal_payload["completion_manifest_observed_sha256"] is None
    else:
        assert len(terminal_payload["completion_manifest_observed_sha256"]) == 64
    assert not (tmp_path / "joint_call_checkpoints").exists()


@pytest.mark.parametrize("branch", ("checkpoint", "worker_result", "load_all", "final"))
@pytest.mark.parametrize("state", ("missing", "bad", "valid"))
def test_every_recovery_acceptance_branch_requires_phase_evidence(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    branch: str,
    state: str,
) -> None:
    accepted: list[str] = []

    def phase_guard(*_args: object, **_kwargs: object) -> dict[str, object]:
        if state != "valid":
            raise PhaseContractError(f"synthetic_{state}_phase_journal")
        return {"worker_pid": os.getpid()}

    monkeypatch.setattr(formal, "_validate_completed_phase_evidence", phase_guard)
    candidate = SimpleNamespace(candidate_id="candidate_00")
    context = SimpleNamespace(config={"joint_ac": {"initial_strategies": ["source"]}})
    prepared = {"candidate_00": (object(),)}
    chronology = {"candidate_00": object()}

    if branch == "checkpoint":
        v4._joint_checkpoint_path(tmp_path, "candidate_00", "source").mkdir(
            parents=True
        )

        def base_checkpoint(*_args: object, **_kwargs: object) -> str:
            accepted.append(branch)
            return "checkpoint"

        monkeypatch.setattr(v4, "_load_joint_checkpoint", base_checkpoint)

        def call() -> object:
            return formal._load_phase_aware_checkpoint(
                context,
                tmp_path,
                candidate,
                "source",
                _hash("f"),
                prepared["candidate_00"],
                chronology["candidate_00"],
            )

    elif branch == "worker_result":
        monkeypatch.setattr(
            v4, "_validate_joint_call_registration", lambda *_args: _hash("c")
        )
        monkeypatch.setattr(
            v4, "_load_json", lambda *_args: {"schema": "synthetic_call"}
        )
        monkeypatch.setattr(
            v4,
            "_registered_joint_worker_paths",
            lambda *_args: (
                tmp_path / "worker_result",
                tmp_path / "ipopt.log",
                tmp_path / "worker.log",
            ),
        )

        def base_worker(*_args: object, **_kwargs: object) -> tuple[str, str]:
            accepted.append(branch)
            return "rows", _hash("w")

        monkeypatch.setattr(v4, "_load_joint_worker_result", base_worker)

        def call() -> object:
            return formal._load_phase_aware_worker_result(
                context,
                tmp_path,
                candidate,
                "source",
                _hash("f"),
                prepared["candidate_00"],
                chronology["candidate_00"],
            )

    elif branch == "load_all":

        def base_load_all(*_args: object, **_kwargs: object) -> str:
            accepted.append(branch)
            return "all_checkpoints"

        monkeypatch.setattr(v4, "_load_all_joint_checkpoints", base_load_all)

        def call() -> object:
            return formal._load_phase_aware_all_checkpoints(
                context,
                tmp_path,
                [candidate],
                _hash("f"),
                prepared,
                chronology,
            )

    else:

        def base_final(*_args: object, **_kwargs: object) -> dict[str, bool]:
            accepted.append(branch)
            return {"loaded": True}

        monkeypatch.setattr(v4, "_load_joint_results", base_final)

        def call() -> object:
            return formal._load_phase_aware_joint_results(
                context,
                tmp_path / "joint_ac",
                {},
                [candidate],
                _hash("f"),
                prepared,
                chronology,
            )

    if state == "valid":
        call()
        assert accepted == [branch]
    elif branch in {"load_all", "final"}:
        with pytest.raises(formal.IsolatedWorkerIncompleteError) as caught:
            call()
        assert caught.value.outcome.solver_call_count == 0
        assert accepted == []
    else:
        with pytest.raises(PhaseContractError, match=f"synthetic_{state}"):
            call()
        assert accepted == []


def _synthetic_frontier_source(
    root: Path,
) -> tuple[dict[str, object], dict[str, object]]:
    source_id = "synthetic_repair_009"
    source_input = {"schema": "synthetic_input_v1", "hours": 1}
    source_input_sha = common_input_signature_sha256(source_input)
    candidate_ids = ("candidate_00", "candidate_01", "candidate_02")
    requested_ids = ("source", "delta_1", "delta_2")

    def preregistration_writer(staging: Path) -> None:
        v4._write_exact_json(
            staging / "registration.json",
            {
                "preregistration_id": source_id,
                "input_contract": source_input,
                "input_contract_sha256": source_input_sha,
            },
        )

    v4._publish_immutable_payload(root / "preregistration", preregistration_writer)
    checkpoint_manifests: dict[str, str] = {}
    for index, requested_id in enumerate(requested_ids[1:], start=1):
        checkpoint = root / "candidate_checkpoints" / f"{index:02d}_{requested_id}"
        v4._write_exact_json(
            checkpoint / "candidate.json",
            {"candidate": {"requested_candidate_id": requested_id}},
        )
        round_root = checkpoint / "round_00"
        v4._write_exact_json(round_root / "round.json", {"round": 0})
        _write_complete_manifest(round_root)
        _write_complete_manifest(checkpoint)
        checkpoint_manifests[requested_id] = formal._sha256(checkpoint / "SHA256SUMS")

    frontier_input_sha = _hash("9")

    def frontier_writer(staging: Path) -> None:
        v4._write_exact_json(
            staging / "summary.json",
            {
                "preregistration_id": source_id,
                "input_contract_sha256": frontier_input_sha,
                "candidate_ids": list(candidate_ids),
                "requested_candidate_count": len(candidate_ids),
                "unique_candidate_count": len(candidate_ids),
                "joint_ac_solver_call_count": 0,
                "candidate_checkpoint_manifest_sha256s": checkpoint_manifests,
            },
        )
        with (staging / "candidates.csv").open(
            "w", encoding="utf-8", newline=""
        ) as stream:
            writer = csv.DictWriter(stream, fieldnames=("candidate_id",))
            writer.writeheader()
            for candidate_id in candidate_ids:
                writer.writerow({"candidate_id": candidate_id})

    v4._publish_immutable_payload(root / "candidate_frontier", frontier_writer)
    predecessor_contract = {
        "root": str(root),
        "preregistration_manifest_sha256": formal._sha256(
            root / "preregistration" / "SHA256SUMS"
        ),
        "candidate_frontier_manifest_sha256": formal._sha256(
            root / "candidate_frontier" / "SHA256SUMS"
        ),
    }
    import_contract = {
        "schema": "rts_gmlc_v4_repair_010_frontier_import_v1",
        "mode": "audited_immutable_copy",
        "source_preregistration_id": source_id,
        "source_preregistration_input_contract_sha256": source_input_sha,
        "source_frontier_input_contract_sha256": frontier_input_sha,
        "source_candidate_ids": list(candidate_ids),
        "source_budget_checkpoint_count": 2,
        "source_nested_round_manifest_count": 2,
        "destination_relative_directory": "predecessor_frontier_import",
        "authority_loader": "repair_009_load_candidate_frontier",
        "source_outcomes_observed": True,
        "scientific_values_unchanged": True,
        "solver_calls_allowed": False,
        "direct_source_use_as_solver_input_allowed": False,
        "hard_links_allowed": False,
        "atomic_immutable_publication_required": True,
    }
    return predecessor_contract, import_contract


def _synthetic_authority_loader(
    calls: list[Path],
) -> Callable[[Path], tuple[Sequence[object], str]]:
    def load(root: Path) -> tuple[Sequence[object], str]:
        calls.append(root.resolve())
        summary = v4._load_json(root / "candidate_frontier", "summary.json")
        candidates = [
            SimpleNamespace(candidate_id=candidate_id)
            for candidate_id in summary["candidate_ids"]
        ]
        return candidates, formal._sha256(root / "candidate_frontier" / "SHA256SUMS")

    return load


def _synthetic_successor_context(
    source: Path,
    predecessor: Mapping[str, object],
    import_contract: Mapping[str, object],
) -> SimpleNamespace:
    return SimpleNamespace(
        config={"preregistration": {"id": "synthetic_repair_010"}},
        input_contract={
            "frontier_import": dict(import_contract),
            "predecessor_ifocus4": {**predecessor, "root": str(source)},
        },
        input_contract_sha256=_hash("8"),
    )


def test_frontier_import_audits_then_publishes_independent_atomic_copy(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    predecessor, import_contract = _synthetic_frontier_source(source)
    context = _synthetic_successor_context(source, predecessor, import_contract)
    output = tmp_path / "successor"
    calls: list[Path] = []
    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: {})

    record = formal.publish_audited_frontier_import(
        context=context,
        output_root=output,
        source_root=source,
        predecessor_authority_context=None,
        authority_loader=_synthetic_authority_loader(calls),
    )

    imported = output / "predecessor_frontier_import"
    assert record["source_outcomes_observed"] is True
    assert record["solver_call_count"] == 0
    assert record["destination_input_contract_sha256"] == _hash("8")
    assert imported.is_dir()
    assert not any(
        path.name.startswith(".predecessor_frontier_import.processing-")
        for path in output.iterdir()
    )
    assert calls
    source_csv = source / "candidate_frontier" / "candidates.csv"
    imported_csv = imported / "candidate_frontier" / "candidates.csv"
    imported_bytes = imported_csv.read_bytes()
    source_csv.write_text("source changed after import\n", encoding="ascii")
    assert imported_csv.read_bytes() == imported_bytes
    assert (
        formal._validate_frontier_import_payload(
            context,
            imported,
            authority_loader=_synthetic_authority_loader([]),
        )[1]
        == predecessor["candidate_frontier_manifest_sha256"]
    )


def test_frontier_import_default_authority_calls_repair009_loader(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    source = tmp_path / "source"
    predecessor, import_contract = _synthetic_frontier_source(source)
    context = _synthetic_successor_context(source, predecessor, import_contract)
    authority_context = object()
    calls: list[Path] = []
    synthetic_loader = _synthetic_authority_loader(calls)

    def repair009_loader(
        observed_context: object, root: Path
    ) -> tuple[Sequence[object], str]:
        assert observed_context is authority_context
        return synthetic_loader(root)

    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: {})
    monkeypatch.setattr(formal.repair009, "_load_candidate_frontier", repair009_loader)

    formal.publish_audited_frontier_import(
        context=context,
        output_root=tmp_path / "successor",
        source_root=source,
        predecessor_authority_context=authority_context,
    )

    assert calls


@pytest.mark.parametrize("drift", ("source_hash", "candidate_count", "contract"))
def test_frontier_import_rejects_source_or_contract_drift_before_publication(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, drift: str
) -> None:
    source = tmp_path / "source"
    predecessor, import_contract = _synthetic_frontier_source(source)
    if drift == "source_hash":
        (source / "candidate_frontier" / "candidates.csv").write_text(
            "drift\n", encoding="ascii"
        )
    elif drift == "candidate_count":
        summary_path = source / "candidate_frontier" / "summary.json"
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        summary["requested_candidate_count"] = 4
        v4._write_exact_json(summary_path, summary)
        v4._write_manifest(source / "candidate_frontier")
        predecessor["candidate_frontier_manifest_sha256"] = formal._sha256(
            source / "candidate_frontier" / "SHA256SUMS"
        )
    else:
        import_contract["source_frontier_input_contract_sha256"] = _hash("7")
    context = _synthetic_successor_context(source, predecessor, import_contract)
    output = tmp_path / "successor"
    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: {})

    with pytest.raises(RuntimeError, match="drifted"):
        formal.publish_audited_frontier_import(
            context=context,
            output_root=output,
            source_root=source,
            predecessor_authority_context=None,
            authority_loader=_synthetic_authority_loader([]),
        )
    assert not (output / "predecessor_frontier_import").exists()


def test_configured_ifocus4_frontier_tree_passes_read_only_mechanical_audit() -> None:
    config = formal._read_config()

    audit = formal.audit_configured_predecessor_frontier_source(config)

    assert audit.candidate_ids == tuple(f"candidate_{index:02d}" for index in range(7))
    assert len(audit.budget_checkpoint_manifest_sha256s) == 6
    assert audit.nested_round_manifest_count == 22
    assert not Path(config["output"]["directory"]).exists()


def test_run_requires_successor_local_frontier_import_before_lease(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context = SimpleNamespace(
        output_root=tmp_path,
        input_contract={
            "frontier_import": {
                "destination_relative_directory": "predecessor_frontier_import"
            }
        },
    )
    monkeypatch.setattr(formal, "_read_config", lambda *_args: {})
    monkeypatch.setattr(formal, "_assert_successor_ready", lambda *_args: None)
    monkeypatch.setattr(formal, "_build_context", lambda *_args: context)
    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: {})

    with pytest.raises(
        RuntimeError, match="successor-local frontier import is missing"
    ):
        formal.run_joint_ac(output_directory=tmp_path, attempt_id="synthetic")
    assert not (tmp_path / "execution_lease").exists()
