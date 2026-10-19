from __future__ import annotations

import inspect
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
import threading
import time
from collections.abc import Mapping
from modulefinder import ModuleFinder
from pathlib import Path
from typing import Any

import pytest

from experiments import bootstrap_rq2_joint_deliverability_activation_v3 as anchored_v3
from experiments import (
    bootstrap_rq2_public_grid_highs_formal_activation_successor_v5 as bootstrap,
)
from experiments import rq2_public_grid_highs_formal_activation_contract_v5 as contract
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v6 as controller,
)


def _terminal_contender(
    attempt_root: str,
    terminal_class: str,
    delay_seconds: float,
    start: Any,
    commit_barrier: Any,
    results: Any,
) -> None:
    from experiments import (
        rq2_public_grid_highs_formal_activation_contract_v5 as child_contract,
    )

    root = Path(attempt_root)
    original_persist = child_contract.persist_json_exclusive_stable

    def gated_terminal_claim(
        path: Path, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        if path.resolve() == child_contract.terminal_outcome_path(root).resolve():
            commit_barrier.wait(timeout=300)
            if delay_seconds:
                time.sleep(delay_seconds)
        return original_persist(path, payload)

    child_contract.persist_json_exclusive_stable = gated_terminal_claim
    identity = {"pid": 4242, "create_time_ns": 987654321}
    release_path = root / "science_release.json"
    acceptance = json.loads((root / "science_release_accepted.json").read_text())
    start.wait(timeout=10)
    if terminal_class == "success":
        decision = child_contract.persist_controller_terminal_success(
            root,
            controller_identity=identity,
            release_path=release_path,
            release_acceptance=acceptance,
            result={"completed": True},
            formal_roots_override=_formal_roots_for_attempt(root),
        )
    else:
        decision = child_contract.persist_post_release_unresolved(
            root,
            reason="injected",
            reporter="bootstrap_supervisor",
            controller_identity=identity,
            returncode=None,
            termination={"attempted": False, "reason": "race_fixture"},
            release_path=release_path,
            release_acceptance=acceptance,
            formal_roots_override=_formal_roots_for_attempt(root),
        )
    results.put(decision)


def _one_shot_contender(
    fresh_path: str,
    consumed_path: str,
    expected_sha256: str,
    tombstone: dict[str, Any],
    start: Any,
    results: Any,
) -> None:
    from experiments import (
        rq2_public_grid_highs_formal_activation_contract_v5 as child_contract,
    )

    start.wait(timeout=30)
    try:
        child_contract._consume_reserved_one_shot(
            Path(fresh_path),
            Path(consumed_path),
            expected_sha256=expected_sha256,
            tombstone=tombstone,
        )
    except BaseException as exc:  # noqa: BLE001 - exact contender outcome is evidence
        results.put({"outcome": "rejected", "type": type(exc).__name__})
    else:
        results.put({"outcome": "consumed"})


def _ordinary_binding_files(tmp_path: Path) -> dict[str, dict[str, str]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    bindings: dict[str, dict[str, str]] = {}
    for name in sorted(contract.STARTUP_BINDING_NAMES):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({"name": name}) + "\n", encoding="utf-8")
        bindings[name] = {"path": str(path), "sha256": contract.sha256_file(path)}
    return bindings


def _release_and_acceptance(
    attempt: Path,
    *,
    identity: dict[str, int] | None = None,
) -> tuple[Path, dict[str, Any]]:
    pair = identity or {"pid": 4242, "create_time_ns": 987654321}
    bootstrap_pair = {"pid": 4343, "create_time_ns": 123456789}
    dynamic, _ = contract.prepare_preseal_authority(
        attempt, bootstrap_identity=bootstrap_pair
    )
    authority_path = Path(dynamic["authority_path"])
    bindings = contract.startup_bindings(authority_path)
    command = list(dynamic["exact_command"])
    environment = dict(dynamic["exact_environment"])
    handshake = contract.build_startup_handshake(
        controller_identity=pair,
        bootstrap_identity=bootstrap_pair,
        bindings=bindings,
        command=command,
        cwd=str(contract.ROOT),
        environment=environment,
    )
    contract.persist_json_stable(attempt / "startup_handshake.json", handshake)
    ack = contract.build_startup_ack(
        handshake=handshake,
        controller_identity=pair,
        bootstrap_identity=bootstrap_pair,
    )
    contract.persist_json_stable(attempt / "startup_ack.json", ack)
    closure_sha256 = dynamic["execution_closure"]["members_sha256"]
    ready = contract.build_startup_ready(
        handshake=handshake,
        ack=ack,
        controller_identity=pair,
        bootstrap_identity=bootstrap_pair,
        authority_mapping_sha256=contract.canonical_sha256(
            contract.runtime_authority_mapping(authority_path)
        ),
        execution_closure_sha256=closure_sha256,
    )
    contract.persist_json_stable(attempt / "startup_ready.json", ready)
    release = contract.build_science_release(
        ready=ready,
        controller_identity=pair,
        bootstrap_identity=bootstrap_pair,
    )
    release_path = attempt / "science_release.json"
    contract.persist_json_stable(release_path, release)
    acceptance = contract.build_science_release_acceptance(
        release=release,
        controller_identity=pair,
        bootstrap_identity=bootstrap_pair,
        execution_closure_sha256=closure_sha256,
    )
    contract.persist_json_stable(attempt / "science_release_accepted.json", acceptance)
    return release_path, acceptance


def _formal_roots_for_attempt(attempt: Path) -> dict[str, Path]:
    authority_path = attempt / "authority.json"
    dynamic = {
        **contract.validate_dynamic_authority(authority_path),
        "authority_path": str(authority_path),
        "authority_sha256": contract.sha256_file(authority_path),
    }
    return {name: Path(path) for name, path in dynamic["formal_roots"].items()}


def _persist_valid_spawn_receipt(
    attempt: Path, *, controller_identity: dict[str, int]
) -> dict[str, Any]:
    dynamic_path = attempt / "authority.json"
    dynamic = json.loads(dynamic_path.read_text(encoding="utf-8"))
    paths = {name: Path(path) for name, path in dynamic["startup_paths"].items()}
    receipt = {
        "schema": "rq2_public_grid_highs_formal_activation_spawn_receipt_v5_preseal",
        "version": 5,
        "pid": controller_identity["pid"],
        "create_time_ns": controller_identity["create_time_ns"],
        "bootstrap_identity": dynamic["bootstrap_identity"],
        "returncode": None,
        "dynamic_authority_path": str(dynamic_path.resolve()),
        "dynamic_authority_sha256": contract.sha256_file(dynamic_path),
        "command": dynamic["exact_command"],
        "cwd": dynamic["exact_cwd"],
        "environment_sha256": contract.canonical_sha256(dynamic["exact_environment"]),
        "stdout_path": str((attempt / "controller.stdout.log").resolve()),
        "stderr_path": str((attempt / "controller.stderr.log").resolve()),
        "startup_handshake_path": str(paths["handshake"]),
        "startup_handshake_sha256": contract.sha256_file(paths["handshake"]),
        "startup_ack_path": str(paths["bootstrap_ack"]),
        "startup_ack_sha256": contract.sha256_file(paths["bootstrap_ack"]),
        "startup_ready_path": str(paths["startup_ready"]),
        "startup_ready_sha256": contract.sha256_file(paths["startup_ready"]),
        "science_release_path": str(paths["science_release"]),
        "science_release_sha256": contract.sha256_file(paths["science_release"]),
        "science_release_accepted_path": str(paths["science_release_accepted"]),
        "science_release_accepted_sha256": contract.sha256_file(
            paths["science_release_accepted"]
        ),
        "release_acceptance_proven": True,
        "controller_authority_accepted": True,
        "exact_pid_create_time_verified": True,
        "formal_controller_spawned": True,
        "formal_started_at_controller_ready": False,
        "formal_start_status": "released_and_controller_acceptance_proven",
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    persisted, created = contract.persist_json_exclusive_stable(
        paths["spawn_receipt"], receipt
    )
    assert created is True
    assert persisted == receipt
    return receipt


def test_spawn_receipt_payload_reuses_one_validated_dynamic_snapshot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = tmp_path / "attempt"
    controller_identity = {"pid": 4242, "create_time_ns": 987654321}
    _release_and_acceptance(attempt, identity=controller_identity)
    receipt = _persist_valid_spawn_receipt(
        attempt, controller_identity=controller_identity
    )
    real_validate = contract.validate_dynamic_authority
    validate_calls = 0

    def counted_validate(path: Path) -> dict[str, Any]:
        nonlocal validate_calls
        validate_calls += 1
        return real_validate(path)

    monkeypatch.setattr(contract, "validate_dynamic_authority", counted_validate)
    validated = contract.validate_spawn_receipt_payload(receipt, attempt_root=attempt)

    assert validated["receipt"] == receipt
    assert validate_calls == 1


@pytest.mark.parametrize(
    "winner_class", ["cancelled_before_science", "controller_owned_lifecycle"]
)
def test_lifecycle_decision_is_one_strict_cross_process_authority(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, winner_class: str
) -> None:
    attempt = tmp_path / "attempt"
    controller_identity = {"pid": 4242, "create_time_ns": 987654321}
    _release_and_acceptance(attempt, identity=controller_identity)
    _persist_valid_spawn_receipt(attempt, controller_identity=controller_identity)
    roots = _formal_roots_for_attempt(attempt)
    derived_closure = contract.verify_execution_closure()
    monkeypatch.setattr(
        contract, "verify_execution_closure", lambda *args, **kwargs: derived_closure
    )
    original_persist = contract.persist_json_exclusive_stable
    barrier = threading.Barrier(2, timeout=300)

    def adversarial_persist(
        path: Path, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        if path.resolve() == (attempt / "lifecycle_decision.json").resolve():
            barrier.wait()
            if payload["lifecycle_class"] != winner_class:
                time.sleep(0.05)
        return original_persist(path, payload)

    monkeypatch.setattr(contract, "persist_json_exclusive_stable", adversarial_persist)
    decisions: list[dict[str, Any]] = []
    errors: list[BaseException] = []

    def contend(lifecycle_class: str) -> None:
        try:
            decisions.append(
                contract.claim_lifecycle_decision(
                    attempt,
                    lifecycle_class=lifecycle_class,
                    controller_identity=controller_identity,
                    bootstrap_identity={"pid": 4343, "create_time_ns": 123456789},
                    formal_roots_override=roots,
                )
            )
        except BaseException as exc:  # noqa: BLE001 - test captures contender result
            errors.append(exc)

    contenders = [
        threading.Thread(target=contend, args=(lifecycle_class,))
        for lifecycle_class in (
            "cancelled_before_science",
            "controller_owned_lifecycle",
        )
    ]
    for contender in contenders:
        contender.start()
    for contender in contenders:
        contender.join(timeout=300)

    assert errors == []
    assert all(not contender.is_alive() for contender in contenders)
    assert len(decisions) == 2
    assert {decision["outcome"]["lifecycle_class"] for decision in decisions} == {
        winner_class
    }
    assert sum(decision["created"] for decision in decisions) == 1
    assert sum(decision["accepted_existing_decision"] for decision in decisions) == 1
    validated = contract.validate_lifecycle_decision(
        attempt / "lifecycle_decision.json", formal_roots_override=roots
    )
    assert validated["outcome"]["lifecycle_class"] == winner_class
    assert len(list(attempt.glob("lifecycle_decision.json"))) == 1
    assert all(not root.exists() for root in roots.values())


def test_lifecycle_decision_reconstructs_committed_authority_and_rejects_forgery(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = tmp_path / "attempt"
    controller_identity = {"pid": 4242, "create_time_ns": 987654321}
    bootstrap_identity = {"pid": 4343, "create_time_ns": 123456789}
    _release_and_acceptance(attempt, identity=controller_identity)
    _persist_valid_spawn_receipt(attempt, controller_identity=controller_identity)
    roots = _formal_roots_for_attempt(attempt)
    target = attempt / "lifecycle_decision.json"
    original_persist = contract.persist_json_exclusive_stable

    def commit_then_interrupt(
        path: Path, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        persisted = original_persist(path, payload)
        if path.resolve() == target.resolve() and persisted[1]:
            raise KeyboardInterrupt("injected:lifecycle_after_atomic_commit")
        return persisted

    with monkeypatch.context() as context:
        context.setattr(
            contract, "persist_json_exclusive_stable", commit_then_interrupt
        )
        decision = contract.claim_lifecycle_decision(
            attempt,
            lifecycle_class="controller_owned_lifecycle",
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            formal_roots_override=roots,
        )

    assert decision["outcome"]["lifecycle_class"] == "controller_owned_lifecycle"
    assert decision["commit_interrupted_but_disk_authority_reconstructed"] is True
    assert decision["accepted_existing_decision"] is True
    valid_raw = target.read_bytes()
    mutations: list[tuple[str, Any]] = [
        ("extra key", lambda value: value.update({"forged": True})),
        ("missing key", lambda value: value.pop("release_acceptance_sha256")),
        ("alien class", lambda value: value.update({"lifecycle_class": "alien"})),
        ("requester drift", lambda value: value.update({"requested_by": "bootstrap"})),
        (
            "authority hash drift",
            lambda value: value.update({"dynamic_authority_sha256": "0" * 64}),
        ),
        (
            "spawn receipt drift",
            lambda value: value.update({"spawn_receipt_sha256": "1" * 64}),
        ),
        (
            "controller identity drift",
            lambda value: value["controller_identity"].update(
                {"create_time_ns": 987654322}
            ),
        ),
        (
            "root observation drift",
            lambda value: next(
                iter(value["formal_root_observations_at_decision"].values())
            ).update({"exists": True}),
        ),
    ]
    for _label, mutate in mutations:
        forged = json.loads(valid_raw)
        mutate(forged)
        target.write_bytes(contract.canonical_bytes(forged))
        with pytest.raises(contract.FormalActivationRejected, match="drifted"):
            contract.validate_lifecycle_decision(target, formal_roots_override=roots)
        target.write_bytes(valid_raw)

    replay_root = tmp_path / "other-attempt"
    replay_root.mkdir()
    replay = replay_root / "lifecycle_decision.json"
    replay.write_bytes(valid_raw)
    with pytest.raises(
        contract.FormalActivationRejected, match="common evidence drifted"
    ):
        contract.validate_lifecycle_decision(replay, formal_roots_override=roots)

    linked = tmp_path / "lifecycle-decision-linked.json"
    junction: Path | None = None
    try:
        linked.symlink_to(target)
    except OSError:
        junction = tmp_path / "lifecycle-attempt-junction"
        completed = subprocess.run(
            [
                "cmd.exe",
                "/d",
                "/c",
                "mklink",
                "/J",
                str(junction),
                str(target.parent),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        linked = junction / target.name
    try:
        with pytest.raises(
            contract.FormalActivationRejected,
            match="ordinary|linked|alias|anchored",
        ):
            contract.validate_lifecycle_decision(linked, formal_roots_override=roots)
    finally:
        if junction is not None and junction.exists():
            junction.rmdir()

    backing = tmp_path / "lifecycle-decision-backing.json"
    backing.write_bytes(valid_raw)
    target.unlink()
    os.link(backing, target)
    with pytest.raises(contract.FormalActivationRejected, match="ordinary, non-linked"):
        contract.validate_lifecycle_decision(target, formal_roots_override=roots)


def _spawn_sleeper() -> tuple[subprocess.Popen[Any], dict[str, int]]:
    process = subprocess.Popen(
        [sys.executable, "-B", "-c", "import time;time.sleep(300)"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return process, bootstrap._observe_process_identity(process)


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize(
    ("fault_stage", "acceptance_must_exist"),
    [
        ("release_after_atomic_commit_before_stable_readback", False),
        ("release_after_stable_readback_before_phase_return", False),
        ("acceptance_after_atomic_commit_before_validation", True),
    ],
)
def test_disk_phase_authority_survives_all_baseexception_windows(
    tmp_path: Path,
    exception_type: type[BaseException],
    fault_stage: str,
    acceptance_must_exist: bool,
) -> None:
    attempt = tmp_path / "attempt"
    bystander, _ = _spawn_sleeper()

    try:
        with pytest.raises((exception_type, contract.FormalActivationRejected)):
            bootstrap._execute_preseal_startup_probe(
                attempt,
                fault_phase=fault_stage,
                fault_type=exception_type.__name__,
            )
        assert bystander.poll() is None
        terminal = contract.load_terminal_outcome(attempt)
        assert terminal["terminal_class"] == "unresolved"
        acceptance_exists = (attempt / "science_release_accepted.json").is_file()
        assert terminal["release_acceptance_proven"] is acceptance_exists
        if acceptance_must_exist:
            assert acceptance_exists is True
        expected_termination_reasons = {
            "exact_owned_child_terminated",
            "already_exited",
        }
        if acceptance_must_exist:
            expected_termination_reasons.add(
                "controller_self_report_before_exception_propagation"
            )
        assert terminal["termination"]["reason"] in expected_termination_reasons
        assert not (attempt / "launch_incomplete.json").exists()
        assert not (attempt / "controller_terminal_success.json").exists()
        assert not (attempt / "post_release_unresolved.json").exists()
    finally:
        if bystander.poll() is None:
            bystander.terminate()
            bystander.wait(timeout=5)


@pytest.mark.parametrize(
    ("success_delay", "unresolved_delay", "expected_winner"),
    [(0.0, 0.2, "success"), (0.2, 0.0, "unresolved"), (0.0, 0.0, None)],
)
def test_two_os_processes_share_one_atomic_terminal_decision(
    tmp_path: Path,
    success_delay: float,
    unresolved_delay: float,
    expected_winner: str | None,
) -> None:
    attempt = tmp_path / "attempt"
    _release_and_acceptance(attempt)
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    commit_barrier = context.Barrier(2)
    results = context.Queue()
    contenders = [
        context.Process(
            target=_terminal_contender,
            args=(
                str(attempt),
                "success",
                success_delay,
                start,
                commit_barrier,
                results,
            ),
        ),
        context.Process(
            target=_terminal_contender,
            args=(
                str(attempt),
                "unresolved",
                unresolved_delay,
                start,
                commit_barrier,
                results,
            ),
        ),
    ]
    owned_identities: dict[int, int] = {}
    for contender in contenders:
        contender.start()
        assert contender.pid is not None
        owned_identities[contender.pid] = (
            bootstrap.process_identity._process_creation_time_ns(contender.pid)
        )
    start.set()
    try:
        decisions = [results.get(timeout=300), results.get(timeout=300)]
        for contender in contenders:
            contender.join(timeout=30)
            assert contender.exitcode == 0
    finally:
        for contender in contenders:
            if contender.is_alive():
                assert contender.pid is not None
                assert (
                    bootstrap.process_identity._process_creation_time_ns(contender.pid)
                    == owned_identities[contender.pid]
                )
                contender.terminate()
                contender.join(timeout=10)
    assert sum(bool(item["created"]) for item in decisions) == 1
    assert len({item["winner_sha256"] for item in decisions}) == 1
    assert len({item["outcome"]["terminal_class"] for item in decisions}) == 1
    winner = decisions[0]["outcome"]["terminal_class"]
    if expected_winner is not None:
        assert winner == expected_winner
    assert all(
        item["created"] or item["accepted_existing_decision"] for item in decisions
    )
    assert contract.load_terminal_outcome(attempt)["terminal_class"] == winner
    assert not (attempt / "controller_terminal_success.json").exists()
    assert not (attempt / "post_release_unresolved.json").exists()


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
@pytest.mark.parametrize("terminal_class", ["success", "unresolved"])
def test_terminal_decision_reconstructs_committed_authority_after_baseexception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
    terminal_class: str,
) -> None:
    attempt = tmp_path / "attempt"
    identity = {"pid": 4242, "create_time_ns": 987654321}
    release_path, acceptance = _release_and_acceptance(attempt, identity=identity)
    terminal_path = contract.terminal_outcome_path(attempt)
    original_persist = contract.persist_json_exclusive_stable

    def commit_then_interrupt(
        path: Path, payload: dict[str, Any]
    ) -> tuple[dict[str, Any], bool]:
        persisted = original_persist(path, payload)
        if path.resolve() == terminal_path.resolve() and persisted[1]:
            raise exception_type("injected:terminal_after_atomic_commit")
        return persisted

    with monkeypatch.context() as context:
        context.setattr(
            contract, "persist_json_exclusive_stable", commit_then_interrupt
        )
        if terminal_class == "success":
            decision = contract.persist_controller_terminal_success(
                attempt,
                controller_identity=identity,
                release_path=release_path,
                release_acceptance=acceptance,
                result={"completed": True},
                formal_roots_override=_formal_roots_for_attempt(attempt),
            )
        else:
            decision = contract.persist_post_release_unresolved(
                attempt,
                reason="injected",
                reporter="bootstrap_supervisor",
                controller_identity=identity,
                returncode=None,
                termination={"attempted": False, "reason": "fixture"},
                release_path=release_path,
                release_acceptance=acceptance,
                formal_roots_override=_formal_roots_for_attempt(attempt),
            )

    assert decision["outcome"]["terminal_class"] == terminal_class
    assert decision["created"] is False
    assert decision["accepted_existing_decision"] is True
    assert decision["commit_interrupted_but_disk_authority_reconstructed"] is True
    assert contract.load_terminal_outcome(attempt)["terminal_class"] == terminal_class


@pytest.mark.parametrize("exception_type", [KeyboardInterrupt, SystemExit])
def test_terminal_success_winner_controls_guard_exit_after_baseexception(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    exception_type: type[BaseException],
) -> None:
    attempt = tmp_path / "attempt"
    identity = {"pid": 4242, "create_time_ns": 987654321}
    release_path, acceptance = _release_and_acceptance(attempt, identity=identity)
    expected = {"completed": True}
    original_persist = contract.persist_controller_terminal_success

    def persist_then_interrupt(*args: Any, **kwargs: Any) -> dict[str, Any]:
        decision = original_persist(*args, **kwargs)
        assert decision["outcome"]["terminal_class"] == "success"
        raise exception_type("injected:terminal_success_helper_returned")

    monkeypatch.setattr(
        contract, "persist_controller_terminal_success", persist_then_interrupt
    )
    observed = controller._run_released_lifecycle_with_terminal_guard(
        lambda: expected,
        attempt_root=attempt,
        controller_identity=identity,
        release_path=release_path,
        release_acceptance=acceptance,
        formal_roots_override=_formal_roots_for_attempt(attempt),
    )

    assert observed == expected
    terminal = contract.load_terminal_outcome(attempt)
    assert terminal["terminal_class"] == "success"
    assert len(list(attempt.glob("terminal_outcome.json"))) == 1


def test_normal_four_stage_handshake_and_terminal_success(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt"
    controller_identity = {"pid": 4242, "create_time_ns": 987654321}
    release_path, acceptance = _release_and_acceptance(
        attempt, identity=controller_identity
    )
    decision = contract.persist_controller_terminal_success(
        attempt,
        controller_identity=controller_identity,
        release_path=release_path,
        release_acceptance=acceptance,
        result={"completed": True},
        formal_roots_override=_formal_roots_for_attempt(attempt),
    )
    assert decision["created"] is True
    assert decision["outcome"]["terminal_class"] == "success"
    assert contract.load_terminal_outcome(attempt)["terminal_class"] == "success"


def test_block_zero_exception_self_reports_single_unresolved(
    tmp_path: Path,
) -> None:
    attempt = tmp_path / "attempt"
    identity = {"pid": 4242, "create_time_ns": 987654321}
    release_path, acceptance = _release_and_acceptance(attempt, identity=identity)

    def fail() -> dict[str, object]:
        raise RuntimeError("block-0 injected")

    with pytest.raises(RuntimeError, match="block-0"):
        controller._run_released_lifecycle_with_terminal_guard(
            fail,
            attempt_root=attempt,
            controller_identity=identity,
            release_path=release_path,
            release_acceptance=acceptance,
            formal_roots_override=_formal_roots_for_attempt(attempt),
        )
    terminal = contract.load_terminal_outcome(attempt)
    assert terminal["terminal_class"] == "unresolved"
    assert terminal["mathematical_infeasibility_inferred"] is False


def test_selected_lifecycle_execute_rejects_before_any_runtime_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = contract.load_config()
    sealed = config["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    fresh_path: Path | None = None
    fresh_sha256: str | None = None
    consumed_path: Path | None = None
    if sealed:
        lease = contract._production_one_shot()
        fresh_path = contract._repo_path(lease["fresh_path"], "fresh lease")
        consumed_path = contract._repo_path(lease["consumed_path"], "consumed lease")
        fresh_sha256 = contract.sha256_file(fresh_path)
    calls = {"preflight": 0, "consume": 0, "spawn": 0}
    monkeypatch.setattr(
        bootstrap,
        "_capture_preflight",
        lambda: calls.__setitem__("preflight", calls["preflight"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_consume_one_shot_authority",
        lambda value: calls.__setitem__("consume", calls["consume"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_spawn_controller",
        lambda *args, **kwargs: calls.__setitem__("spawn", calls["spawn"] + 1),
    )
    expected_rejection = (
        "activation review PASS receipt" if sealed else "non-authoritative draft"
    )
    with pytest.raises(contract.FormalActivationRejected, match=expected_rejection):
        bootstrap.execute()
    assert calls == {"preflight": 0, "consume": 0, "spawn": 0}
    if sealed:
        assert contract.production_artifact_paths()
        assert fresh_path is not None
        assert contract.sha256_file(fresh_path) == fresh_sha256
        assert consumed_path is not None
        assert not contract._entry_exists(consumed_path)
    else:
        assert contract.production_artifact_paths() == []
    assert all(not path.exists() for path in contract.formal_roots().values())


def test_mocked_sealed_execute_stops_at_missing_review_before_runtime_effect(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"sealed": 0, "review": 0, "user": 0, "preflight": 0, "spawn": 0}

    def sealed() -> dict[str, Any]:
        calls["sealed"] += 1
        return {}

    def missing_review() -> dict[str, Any]:
        calls["review"] += 1
        raise contract.FormalActivationRejected(
            "activation review PASS receipt is missing"
        )

    monkeypatch.setattr(contract, "require_sealed_for_execution", sealed)
    monkeypatch.setattr(contract, "require_activation_review_pass", missing_review)
    monkeypatch.setattr(
        contract,
        "require_user_formal_run_authority",
        lambda: calls.__setitem__("user", calls["user"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_capture_preflight",
        lambda: calls.__setitem__("preflight", calls["preflight"] + 1),
    )
    monkeypatch.setattr(
        bootstrap,
        "_spawn_controller",
        lambda *args, **kwargs: calls.__setitem__("spawn", calls["spawn"] + 1),
    )
    with pytest.raises(
        contract.FormalActivationRejected, match="activation review PASS receipt"
    ):
        bootstrap.execute()
    assert calls == {
        "sealed": 1,
        "review": 1,
        "user": 0,
        "preflight": 0,
        "spawn": 0,
    }


def test_v4_outer_and_closure_bindings_remain_exact() -> None:
    report = contract.validate_only()
    assert report["status"] == contract.load_config()["status"]
    assert report["predecessor_v4_outer_sha256"] == (
        "6936d06a5bc8d191f5eaf235fe7784c36193ac6343d88d16cbbd3e5bea8d2068"
    )
    assert report["predecessor_v4_closure_member_count"] == 77
    formal = contract.validate_formal_config()
    assert formal["solver"]["threads"] == 4
    assert formal["execution"]["process_isolation"]["expected_block_count"] == 1071
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0


def test_validate_only_reports_follow_selected_sealed_lifecycle(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_controller_validate_only = controller.validate_only
    sealed_status = "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    static = {
        "status": sealed_status,
        "solver_calls": 0,
        "formal_root_writes": 0,
    }
    runtime = {"solver_calls": 0, "formal_root_writes": 0}
    production = {
        "activation_review_receipt": "configs/future-review.json",
        "user_formal_run_authority": "configs/future-user-authority.json",
    }
    monkeypatch.setattr(contract, "validate_only", lambda: static)
    monkeypatch.setattr(controller, "validate_only", lambda: runtime)
    monkeypatch.setattr(
        contract,
        "load_config",
        lambda: {"status": sealed_status, "production_artifacts": production},
    )
    monkeypatch.setattr(contract, "_entry_exists", lambda path: False)
    report = bootstrap.validate_only()
    assert report["schema"].endswith("_sealed")
    assert report["status"] == sealed_status
    assert report["formal_activation_review_receipt_present"] is False
    assert report["user_formal_run_authority_present"] is False

    monkeypatch.setattr(controller, "validate_only", real_controller_validate_only)
    controller_context = {
        "config": {
            "execution": {
                "starts_from_block_zero": True,
                "resume_allowed": False,
                "predecessor_Gurobi_checkpoint_reuse_allowed": False,
                "predecessor_HiGHS_checkpoint_reuse_allowed": False,
                "process_isolation": {"resource_sample_interval_seconds": 5.0},
            },
            "solver": {"name": "highs", "threads": 4},
        },
        "blocks": [None] * 1071,
    }
    monkeypatch.setattr(controller, "_load_science_dependencies", lambda: None)
    monkeypatch.setattr(
        controller.authority,
        "verify_execution_closure",
        lambda: {
            "derived_current_hashes_verified": True,
            "hash_authority": "frozen_expected",
        },
    )
    monkeypatch.setattr(controller.authority, "validate_only", lambda: static)

    class PredecessorFixture:
        @staticmethod
        def _stage_context(path: Path) -> dict[str, Any]:
            return controller_context

    monkeypatch.setattr(controller, "predecessor", PredecessorFixture)
    controller_report = controller.validate_only()
    assert controller_report["schema"].endswith("_sealed")
    assert controller_report["static_authority"] == static


def test_v5_materializes_full_production_wiring_behind_draft_gate() -> None:
    assert callable(bootstrap._execute_preseal_startup_probe)
    assert callable(controller._complete_startup_handshake)
    assert callable(controller._run_released_block_lifecycle)
    assert callable(controller._dispatch_one)
    assert callable(controller._worker)
    assert callable(contract.validate_terminal_outcome)


def test_v5_contract_exposes_complete_production_api() -> None:
    for name in (
        "ensure_no_related_formal_process",
        "capture_preflight_evidence",
        "next_attempt_root",
        "preflight_authority_mapping",
        "publish_dynamic_authority",
        "consume_one_shot_authority",
        "validate_dynamic_authority",
    ):
        assert callable(getattr(contract, name))


def test_unsealed_production_call_graph_reaches_stubbed_spawn_without_effects(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    attempt = tmp_path / "attempt"
    authority_path = attempt / "authority.json"
    preflight = {
        "persisted_path": str(attempt / "preflight.json"),
        "persisted_sha256": "a" * 64,
        "stable_readback_verified": True,
        "threshold_passed": True,
    }
    dynamic = {
        "authority_path": str(authority_path),
        "authority_sha256": "b" * 64,
    }
    monkeypatch.setattr(contract, "require_sealed_for_execution", lambda: None)
    monkeypatch.setattr(
        contract,
        "require_activation_review_pass",
        lambda: calls.append("review") or {"verdict": "PASS"},
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "require_user_formal_run_authority",
        lambda: (
            calls.append("user") or {"effect": {"formal_execution_authorized": True}}
        ),
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "verify_execution_closure",
        lambda: (
            calls.append("closure")
            or {"expected_hashes_verified": True, "members_sha256": "c" * 64}
        ),
    )
    monkeypatch.setattr(
        contract,
        "ensure_formal_roots_absent",
        lambda: calls.append("roots_absent"),
    )
    monkeypatch.setattr(
        contract,
        "ensure_no_related_formal_process",
        lambda: calls.append("process_absent"),
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "next_attempt_root",
        lambda: calls.append("attempt") or attempt,
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "preflight_authority_mapping",
        lambda: calls.append("preflight_mapping") or {"sealed": "d" * 64},
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "capture_preflight_evidence",
        lambda *args, **kwargs: calls.append("preflight") or preflight,
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "publish_dynamic_authority",
        lambda *args, **kwargs: calls.append("publish") or dynamic,
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "validate_dynamic_authority",
        lambda path: calls.append("validate_dynamic") or dynamic,
    )
    monkeypatch.setattr(
        contract,
        "consume_one_shot_authority",
        lambda value: calls.append("consume") or {"state": "consumed"},
        raising=False,
    )
    monkeypatch.setattr(
        contract,
        "exact_controller_command",
        lambda *args, **kwargs: [sys.executable, "-B", "-c", "pass"],
    )
    monkeypatch.setattr(contract, "exact_controller_environment", dict)
    monkeypatch.setattr(
        bootstrap, "_current_process_identity", lambda: {"pid": 1, "create_time_ns": 1}
    )
    monkeypatch.setattr(
        bootstrap,
        "_spawn_controller",
        lambda *args, **kwargs: (
            calls.append("spawn") or {"pid": 2, "create_time_ns": 2}
        ),
    )

    report = bootstrap.execute()

    assert report["formal_controller_spawned"] is True
    for name in (
        "review",
        "user",
        "attempt",
        "preflight_mapping",
        "preflight",
        "publish",
        "validate_dynamic",
        "consume",
        "spawn",
    ):
        assert calls.count(name) == 1
    assert not attempt.exists()


def _run_production_spawn_sandbox(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    lifecycle_winner: str | None = None,
) -> dict[str, Any]:
    canonical_roots = contract.formal_roots()
    activation_root = tmp_path / "activation"
    activation_root.mkdir()
    artifact_root = tmp_path / "sealed-fixtures"
    artifact_root.mkdir()
    artifact_paths = {
        name: artifact_root / f"{name}.json"
        for name in (
            "inner_manifest",
            "outer_manifest",
            "execution_closure",
            "activation_review_receipt",
            "user_formal_run_authority",
        )
    }
    closure_members = contract.derive_execution_closure_members()
    frozen_closure = {
        "schema": "rq2_v5_test_frozen_execution_closure",
        "members": closure_members,
        "members_sha256": contract.canonical_sha256(closure_members),
        "derived_current_hashes_verified": True,
        "expected_hashes_verified": True,
        "hash_authority": "frozen_expected",
    }
    for name, path in artifact_paths.items():
        payload = frozen_closure if name == "execution_closure" else {"name": name}
        contract.persist_json_stable(path, payload)
    artifact_bindings = {
        "formal_config": {
            "path": str(contract.FORMAL_CONFIG),
            "sha256": contract.sha256_file(contract.FORMAL_CONFIG),
        },
        "controller": {
            "path": str(Path(controller.__file__).resolve()),
            "sha256": contract.sha256_file(Path(controller.__file__).resolve()),
        },
        "outer": {
            "path": str(artifact_paths["outer_manifest"]),
            "sha256": contract.sha256_file(artifact_paths["outer_manifest"]),
        },
        "execution_closure": {
            "path": str(artifact_paths["execution_closure"]),
            "sha256": contract.sha256_file(artifact_paths["execution_closure"]),
        },
        "activation_review_pass": {
            "path": str(artifact_paths["activation_review_receipt"]),
            "sha256": contract.sha256_file(artifact_paths["activation_review_receipt"]),
        },
        "user_formal_run_authority": {
            "path": str(artifact_paths["user_formal_run_authority"]),
            "sha256": contract.sha256_file(artifact_paths["user_formal_run_authority"]),
        },
    }
    static_mapping = {
        str(path): contract.sha256_file(path) for path in artifact_paths.values()
    }
    fresh_path = tmp_path / "one-shot.fresh.json"
    consumed_path = tmp_path / "one-shot.consumed.json"
    one_shot = {
        "fresh_path": str(fresh_path),
        "fresh_sha256": "0" * 64,
        "consumed_path": str(consumed_path),
        "authority_id": "1" * 64,
        "one_shot": True,
    }
    fresh = {
        "authority_id": one_shot["authority_id"],
        "state": "fresh",
        "one_shot": True,
    }
    contract.persist_json_stable(fresh_path, fresh)
    one_shot["fresh_sha256"] = contract.sha256_file(fresh_path)
    preflight_mapping = {**static_mapping, str(fresh_path): one_shot["fresh_sha256"]}
    formal_roots = {
        name: tmp_path / "formal-sandbox" / name
        for name in ("checkpoint", "worker", "log", "output")
    }
    review = {"verdict": "PASS"}
    user_authority = {"formal_execution_authorized": True}
    bootstrap_identity = {"pid": 8101, "create_time_ns": 8101001}
    controller_identity = {"pid": 8102, "create_time_ns": 8102001}
    controller._load_science_dependencies()

    monkeypatch.setattr(contract, "activation_audit_root", lambda: activation_root)
    monkeypatch.setattr(contract, "formal_roots", lambda: formal_roots)
    monkeypatch.setattr(
        contract, "_production_artifact_path", lambda name: artifact_paths[name]
    )
    monkeypatch.setattr(
        contract, "_production_artifact_bindings", lambda: artifact_bindings
    )
    monkeypatch.setattr(contract, "_production_one_shot", lambda: one_shot)
    repository_path = contract._repo_path
    monkeypatch.setattr(
        contract,
        "_repo_path",
        lambda raw, label: (
            Path(str(raw)).resolve()
            if Path(str(raw)).is_absolute()
            else repository_path(raw, label)
        ),
    )
    monkeypatch.setattr(
        contract,
        "_expected_preflight_authority_mapping",
        lambda **kwargs: preflight_mapping,
    )
    monkeypatch.setattr(
        contract,
        "production_static_authority_mapping",
        lambda **kwargs: static_mapping,
    )
    monkeypatch.setattr(
        contract,
        "verify_execution_closure",
        lambda *args, **kwargs: frozen_closure,
    )
    monkeypatch.setattr(
        contract,
        "_verify_sealed_bundle",
        lambda **kwargs: {"closure": frozen_closure},
    )
    monkeypatch.setattr(
        contract,
        "_verify_fresh_one_shot_authority",
        lambda: {"binding": one_shot, "payload": fresh},
    )
    monkeypatch.setattr(contract, "require_activation_review_pass", lambda: review)
    monkeypatch.setattr(
        contract,
        "require_user_formal_run_authority",
        lambda **kwargs: user_authority,
    )

    attempt = contract.next_attempt_root()
    preflight = contract.capture_preflight_evidence(
        attempt,
        authority_mapping=preflight_mapping,
        observed_available_commit_bytes=lambda: contract.PREFLIGHT_THRESHOLD_BYTES,
    )
    dynamic = contract.publish_dynamic_authority(
        preflight,
        review_receipt=review,
        user_run_authority=user_authority,
        bootstrap_identity=bootstrap_identity,
    )
    authority_path = Path(dynamic["authority_path"])
    tombstone = contract.consume_one_shot_authority(dynamic)
    assert tombstone["state"] == "consumed"
    assert contract.validate_dynamic_authority(authority_path)["schema"] == (
        "rq2_public_grid_highs_formal_dynamic_activation_authority_v5"
    )

    class OneBlockOrder(list[str]):
        def __len__(self) -> int:
            return 1071

    class ImmediateFuture:
        def __init__(self, value: dict[str, Any]) -> None:
            self.value = value

        def done(self) -> bool:
            return True

        def result(self, timeout: float | None = None) -> dict[str, Any]:
            return self.value

    class ImmediateExecutor:
        def shutdown(self, **kwargs: Any) -> None:
            return None

    class MonitorState:
        def __init__(self) -> None:
            self.ready = threading.Event()
            self.ready.set()
            self.first_sample_success = True

    class WorkerProcess:
        pid = 8103
        returncode = 0

        def poll(self) -> int:
            return 0

        def wait(self, timeout: float | None = None) -> int:
            return 0

    thread_errors: list[BaseException] = []

    class ControllerProcess:
        pid = controller_identity["pid"]

        def __init__(self) -> None:
            self.returncode: int | None = None
            self.thread = threading.Thread(target=self._run, daemon=True)
            self.thread.start()

        def _run(self) -> None:
            paths = {
                name: Path(path) for name, path in dynamic["startup_paths"].items()
            }
            try:
                controller.run(
                    controller.CONFIG,
                    authority_path,
                    bootstrap_identity=bootstrap_identity,
                    handshake_path=paths["handshake"],
                    ack_path=paths["bootstrap_ack"],
                    ready_path=paths["startup_ready"],
                    release_path=paths["science_release"],
                    release_accepted_path=paths["science_release_accepted"],
                    preseal_startup_probe=False,
                )
            except BaseException as exc:  # noqa: BLE001 - propagated through Popen seam
                thread_errors.append(exc)
                self.returncode = 1
            else:
                self.returncode = 0

        def poll(self) -> int | None:
            return None if self.thread.is_alive() else self.returncode

        def wait(self, timeout: float | None = None) -> int:
            self.thread.join(timeout)
            if self.thread.is_alive():
                raise subprocess.TimeoutExpired("sandbox-controller", timeout)
            return int(self.returncode)

    call_order: list[str] = []
    lifecycle_calls = {
        "science_import": 0,
        "stage_context": 0,
        "require_isolated_roots": 0,
        "dispatch_one": 0,
    }
    solver_calls = 0
    config = contract.validate_formal_config()
    context = {
        "config_path": controller.CONFIG,
        "config": config,
        "blocks": {"0000": [{"timestamp": "sandbox"}]},
        "stage_base_sha256": "2" * 64,
    }
    isolated_roots = {
        "checkpoint": formal_roots["checkpoint"],
        "worker": formal_roots["worker"],
        "attempt_log": formal_roots["log"],
        "output": formal_roots["output"],
    }

    def popen_sandbox(command: list[str], **kwargs: Any) -> Any:
        nonlocal solver_calls
        if "--worker-request" not in command:
            return ControllerProcess()
        request_path = Path(command[command.index("--worker-request") + 1])
        request = json.loads(request_path.read_text(encoding="utf-8"))
        controller._atomic_json(Path(request["worker_result_path"]), {})
        controller._atomic_json(Path(request["solver_runtime_evidence_path"]), {})
        solver_calls += 0
        return WorkerProcess()

    def monitor_sandbox(
        process: Any,
        *,
        create_time_ns: int,
        dynamic_authority: Path,
        persistence_path: Path,
    ) -> tuple[Any, Any, Any]:
        controller._atomic_json(persistence_path, {})
        return MonitorState(), ImmediateExecutor(), ImmediateFuture({})

    def validate_worker(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert (attempt / "spawn_receipt.json").is_file()
        call_order.append("block0_dispatch")
        return {"block_id": "0000", "all_hours_resolved": True}

    def finalize(*args: Any, **kwargs: Any) -> dict[str, Any]:
        assert call_order == ["block0_dispatch"]
        call_order.append("finalize")
        return {"all_hours_resolved": True, "block_count": 1071}

    def assert_sandbox_process(process: Any, identity: dict[str, int]) -> None:
        assert identity == controller_identity
        if process.poll() is not None:
            raise AssertionError(f"sandbox controller failed: {thread_errors!r}")

    monkeypatch.setattr(bootstrap.subprocess, "Popen", popen_sandbox)
    monkeypatch.setattr(
        bootstrap, "_observe_process_identity", lambda process: controller_identity
    )
    monkeypatch.setattr(bootstrap, "_assert_process_identity", assert_sandbox_process)
    monkeypatch.setattr(
        controller, "_current_controller_identity", lambda: controller_identity
    )
    monkeypatch.setattr(controller, "_assert_live_pair", lambda *args, **kwargs: None)
    monkeypatch.setattr(controller.os, "getpid", lambda: controller_identity["pid"])
    monkeypatch.setattr(controller.os, "getppid", lambda: bootstrap_identity["pid"])
    monkeypatch.setattr(
        controller,
        "_assert_exact_runtime_environment",
        lambda value: (
            (
                value["schema"]
                == "rq2_public_grid_highs_formal_dynamic_activation_authority_v5"
                and value["formal_roots"]
                == {name: str(path.resolve()) for name, path in formal_roots.items()}
            )
            or (_ for _ in ()).throw(AssertionError("production root binding drifted"))
        ),
    )
    original_science_loader = controller._load_science_dependencies

    def tracked_science_loader() -> None:
        lifecycle_calls["science_import"] += 1
        original_science_loader()

    def stage_context(path: Path) -> dict[str, Any]:
        lifecycle_calls["stage_context"] += 1
        return context

    def require_isolated_roots(value: dict[str, Any]) -> dict[str, Path]:
        lifecycle_calls["require_isolated_roots"] += 1
        return isolated_roots

    monkeypatch.setattr(
        controller, "_load_science_dependencies", tracked_science_loader
    )
    monkeypatch.setattr(controller.predecessor, "_stage_context", stage_context)
    monkeypatch.setattr(
        controller.predecessor, "_require_isolated_roots", require_isolated_roots
    )
    monkeypatch.setattr(
        controller.predecessor, "_python_authority", lambda value: Path(sys.executable)
    )
    monkeypatch.setattr(
        controller, "sorted", lambda value: OneBlockOrder(["0000"]), raising=False
    )
    monkeypatch.setattr(
        controller.resource_identity,
        "_process_creation_time_ns",
        lambda pid: (
            controller_identity["create_time_ns"]
            if pid == controller_identity["pid"]
            else 8103001
        ),
    )
    monkeypatch.setattr(controller, "_start_resource_monitor", monitor_sandbox)
    monkeypatch.setattr(
        controller.resource_contract,
        "validate_resource_monitor_outcome",
        lambda value, expected_path: {"resource_journal": {}},
    )
    journal = {"status": "child_exited", "honest_incomplete": False, "sample_count": 1}
    monkeypatch.setattr(
        controller.resource_contract, "validate_resource_journal", lambda value: journal
    )
    monkeypatch.setattr(
        controller.resource_contract,
        "validate_success_resource_journal",
        lambda value: None,
    )
    monkeypatch.setattr(
        controller,
        "_validate_formal_solver_runtime_evidence",
        lambda *args, **kwargs: {},
    )
    monkeypatch.setattr(
        controller.predecessor, "_validate_worker_result", validate_worker
    )
    monkeypatch.setattr(
        controller.predecessor,
        "_checkpoint_envelope",
        lambda *args, **kwargs: {"schema": "sandbox", "execution_receipt": {}},
    )
    monkeypatch.setattr(
        controller,
        "attach_resource_journal_for_test",
        lambda value, *args, **kwargs: value,
    )
    monkeypatch.setattr(
        controller, "_attach_runtime_evidence", lambda value, *args, **kwargs: value
    )
    monkeypatch.setattr(controller.predecessor, "_finalize", finalize)

    original_dispatch = controller._dispatch_one

    def tracked_dispatch(*args: Any, **kwargs: Any) -> dict[str, Any]:
        lifecycle_calls["dispatch_one"] += 1
        return original_dispatch(*args, **kwargs)

    monkeypatch.setattr(controller, "_dispatch_one", tracked_dispatch)

    if lifecycle_winner is not None:
        barrier = threading.Barrier(2, timeout=300)
        lifecycle_arrivals: list[str] = []
        original_persist = contract.persist_json_exclusive_stable

        def adversarial_lifecycle_commit(
            path: Path, payload: dict[str, Any]
        ) -> tuple[dict[str, Any], bool]:
            if (
                path.resolve()
                == Path(dynamic["startup_paths"]["lifecycle_decision"]).resolve()
            ):
                lifecycle_arrivals.append(str(payload["lifecycle_class"]))
                try:
                    barrier.wait()
                except threading.BrokenBarrierError as exc:
                    raise AssertionError(
                        "lifecycle contender did not reach the barrier; "
                        f"thread_errors={thread_errors!r}"
                    ) from exc
                if payload["lifecycle_class"] != lifecycle_winner:
                    time.sleep(0.25)
            return original_persist(path, payload)

        monkeypatch.setattr(
            contract, "persist_json_exclusive_stable", adversarial_lifecycle_commit
        )

    fault_stages: list[str] = []

    def fault_hook(stage: str) -> None:
        fault_stages.append(stage)
        if (
            lifecycle_winner is not None
            and stage == "spawn_receipt_after_atomic_commit"
        ):
            raise KeyboardInterrupt("injected:spawn_receipt_after_atomic_commit")

    original_spawn = bootstrap._spawn_controller
    original_run = controller.run
    spawn: dict[str, Any] | None = None
    if lifecycle_winner is None:
        spawn = bootstrap._spawn_controller(
            list(dynamic["exact_command"]),
            cwd=contract.ROOT,
            environment=dynamic["exact_environment"],
            dynamic=dynamic,
            bootstrap_identity=bootstrap_identity,
        )
    else:
        with pytest.raises(
            KeyboardInterrupt, match="spawn_receipt_after_atomic_commit"
        ):
            bootstrap._spawn_controller(
                list(dynamic["exact_command"]),
                cwd=contract.ROOT,
                environment=dynamic["exact_environment"],
                dynamic=dynamic,
                bootstrap_identity=bootstrap_identity,
                fault_hook=fault_hook,
            )

    assert bootstrap._spawn_controller is original_spawn
    assert controller.run is original_run
    lifecycle = contract.validate_lifecycle_decision(
        attempt / "lifecycle_decision.json", formal_roots_override=formal_roots
    )["outcome"]
    expected_winner = lifecycle_winner or "controller_owned_lifecycle"
    assert lifecycle["lifecycle_class"] == expected_winner
    if lifecycle_winner is not None:
        assert sorted(lifecycle_arrivals) == [
            "cancelled_before_science",
            "controller_owned_lifecycle",
        ]
        assert fault_stages[-1] == "spawn_receipt_after_atomic_commit"
        assert fault_stages.count("spawn_receipt_after_atomic_commit") == 1
    assert solver_calls == 0
    terminal = contract.validate_terminal_outcome(
        attempt / "terminal_outcome.json", formal_roots_override=formal_roots
    )["outcome"]
    if expected_winner == "cancelled_before_science":
        assert lifecycle_calls == {
            "science_import": 0,
            "stage_context": 0,
            "require_isolated_roots": 0,
            "dispatch_one": 0,
        }
        assert call_order == []
        assert terminal["terminal_class"] == "unresolved"
        assert len(thread_errors) == 1
        assert isinstance(thread_errors[0], controller.LifecycleCancelledBeforeScience)
        cancellation = contract.validate_controller_cancellation(
            attempt / "controller_cancellation.json",
            dynamic_authority=authority_path,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
        )
        acknowledgement = contract.validate_controller_stop_ack(
            attempt / "controller_cancellation_ack.json",
            dynamic_authority=authority_path,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
        )
        assert acknowledgement["cancellation_sha256"] == contract.sha256_file(
            attempt / "controller_cancellation.json"
        )
        assert cancellation["controller_identity"] == controller_identity
        assert not (attempt / "deferred_supervisor_interruption.json").exists()
        assert all(not path.exists() for path in formal_roots.values())
    else:
        assert thread_errors == []
        assert lifecycle_calls == {
            "science_import": 1,
            "stage_context": 1,
            # Once at lifecycle root acquisition and once while building the
            # real block-zero worker request through the predecessor path.
            "require_isolated_roots": 2,
            "dispatch_one": 1,
        }
        assert call_order == ["block0_dispatch", "finalize"]
        assert terminal["terminal_class"] == "success"
        assert not (attempt / "controller_cancellation.json").exists()
        if lifecycle_winner is not None:
            deferred = contract.validate_deferred_supervisor_interruption(
                attempt / "deferred_supervisor_interruption.json",
                formal_roots_override=formal_roots,
            )["interruption"]
            assert deferred["lifecycle_class"] == "controller_owned_lifecycle"
            assert deferred["lifecycle_decision_sha256"] == contract.sha256_file(
                attempt / "lifecycle_decision.json"
            )
        else:
            assert not (attempt / "deferred_supervisor_interruption.json").exists()
        assert spawn is None or spawn["terminal_outcome"]["terminal_class"] == "success"
    assert all(
        Path(dynamic["startup_paths"][name]).is_file()
        for name in (
            "handshake",
            "bootstrap_ack",
            "startup_ready",
            "science_release",
            "science_release_accepted",
            "terminal_outcome",
        )
    )
    assert all(not path.exists() for path in canonical_roots.values())
    return {
        "lifecycle": lifecycle,
        "terminal": terminal,
        "lifecycle_calls": lifecycle_calls,
    }


def test_production_spawn_reaches_real_block_zero_dispatch_and_finalize_in_sandbox(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    started = time.monotonic()
    report = _run_production_spawn_sandbox(tmp_path, monkeypatch)
    elapsed = time.monotonic() - started
    assert report["terminal"]["terminal_class"] == "success"
    assert elapsed < 30.0


@pytest.mark.parametrize(
    "lifecycle_winner", ["cancelled_before_science", "controller_owned_lifecycle"]
)
def test_production_lifecycle_decision_race_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, lifecycle_winner: str
) -> None:
    report = _run_production_spawn_sandbox(
        tmp_path, monkeypatch, lifecycle_winner=lifecycle_winner
    )
    assert report["lifecycle"]["lifecycle_class"] == lifecycle_winner


def _valid_terminal_path(tmp_path: Path) -> Path:
    attempt = tmp_path / "attempt"
    identity = {"pid": 4242, "create_time_ns": 987654321}
    release_path, acceptance = _release_and_acceptance(attempt, identity=identity)
    contract.persist_controller_terminal_success(
        attempt,
        controller_identity=identity,
        release_path=release_path,
        release_acceptance=acceptance,
        result={"completed": True},
        formal_roots_override=_formal_roots_for_attempt(attempt),
    )
    return contract.terminal_outcome_path(attempt)


@pytest.mark.parametrize(
    "mutation",
    ["extra", "missing", "alien_class", "payload_tamper", "partial_json"],
)
def test_strict_terminal_validator_rejects_forged_content(
    tmp_path: Path, mutation: str
) -> None:
    terminal_path = _valid_terminal_path(tmp_path)
    forged = json.loads(terminal_path.read_text(encoding="utf-8"))
    if mutation == "extra":
        forged["forged_extra"] = True
    elif mutation == "missing":
        del forged["release_sha256"]
    elif mutation == "alien_class":
        forged["terminal_class"] = "alien"
    elif mutation == "payload_tamper":
        forged["release_payload_sha256"] = "0" * 64
    else:
        terminal_path.write_bytes(b'{"schema":')
    if mutation != "partial_json":
        terminal_path.write_bytes(contract.canonical_bytes(forged))
    with pytest.raises(contract.FormalActivationRejected, match="terminal"):
        contract.validate_terminal_outcome(
            terminal_path,
            formal_roots_override=_formal_roots_for_attempt(terminal_path.parent),
        )


def test_strict_terminal_validator_rejects_symlink_and_hardlink(
    tmp_path: Path,
) -> None:
    terminal_path = _valid_terminal_path(tmp_path)
    symlink = tmp_path / "terminal.symlink.json"
    junction: Path | None = None
    try:
        symlink.symlink_to(terminal_path)
    except OSError:
        junction = tmp_path / "terminal-parent-junction"
        completed = subprocess.run(
            [
                "cmd.exe",
                "/d",
                "/c",
                "mklink",
                "/J",
                str(junction),
                str(terminal_path.parent),
            ],
            check=False,
            capture_output=True,
            text=True,
        )
        assert completed.returncode == 0, completed.stderr
        symlink = junction / terminal_path.name
    try:
        with pytest.raises(
            contract.FormalActivationRejected, match="ordinary|linked|alias|anchored"
        ):
            contract.validate_terminal_outcome(
                symlink,
                formal_roots_override=_formal_roots_for_attempt(terminal_path.parent),
            )
    finally:
        if junction is not None and junction.exists():
            junction.rmdir()
    hardlink = tmp_path / "terminal.hardlink.json"
    os.link(terminal_path, hardlink)
    with pytest.raises(contract.FormalActivationRejected, match="ordinary|linked"):
        contract.validate_terminal_outcome(
            terminal_path,
            formal_roots_override=_formal_roots_for_attempt(terminal_path.parent),
        )


def test_terminal_loser_rejects_forged_existing_winner(tmp_path: Path) -> None:
    terminal_path = _valid_terminal_path(tmp_path)
    forged = json.loads(terminal_path.read_text(encoding="utf-8"))
    forged["forged_extra"] = True
    terminal_path.write_bytes(contract.canonical_bytes(forged))
    attempt = terminal_path.parent
    release = json.loads((attempt / "science_release.json").read_text(encoding="utf-8"))
    acceptance = json.loads(
        (attempt / "science_release_accepted.json").read_text(encoding="utf-8")
    )
    with pytest.raises(contract.FormalActivationRejected, match="terminal"):
        contract.persist_controller_terminal_success(
            attempt,
            controller_identity=release["controller_identity"],
            release_path=attempt / "science_release.json",
            release_acceptance=acceptance,
            result={"completed": True},
            formal_roots_override=_formal_roots_for_attempt(attempt),
        )


def test_strict_terminal_validator_rejects_in_read_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    terminal_path = _valid_terminal_path(tmp_path)
    replacement = tmp_path / "replacement.json"
    forged = json.loads(terminal_path.read_text(encoding="utf-8"))
    forged["release_payload_sha256"] = "0" * 64
    replacement.write_bytes(contract.canonical_bytes(forged))
    formal_roots = _formal_roots_for_attempt(terminal_path.parent)
    original_read = anchored_v3._read_all_descriptor
    calls = 0

    def replace_after_first_read(descriptor: int) -> bytes:
        nonlocal calls
        raw = original_read(descriptor)
        if calls == 0:
            calls += 1
            os.replace(replacement, terminal_path)
        return raw

    monkeypatch.setattr(anchored_v3, "_read_all_descriptor", replace_after_first_read)
    with pytest.raises(
        contract.FormalActivationRejected, match="identity drifted|read failed"
    ):
        contract.validate_terminal_outcome(
            terminal_path,
            formal_roots_override=formal_roots,
        )
    assert calls == 1


def test_terminal_validator_rejects_forged_ready_with_rehashed_descendants(
    tmp_path: Path,
) -> None:
    terminal_path = _valid_terminal_path(tmp_path)
    attempt = terminal_path.parent
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    ready_path = attempt / "startup_ready.json"
    ready = json.loads(ready_path.read_text(encoding="utf-8"))
    ready["formal_roots_absent"] = False
    ready_path.write_bytes(contract.canonical_bytes(ready))
    release = contract.build_science_release(
        ready=ready,
        controller_identity=terminal["controller_identity"],
        bootstrap_identity=terminal["bootstrap_identity"],
    )
    release_path = attempt / "science_release.json"
    release_path.write_bytes(contract.canonical_bytes(release))
    acceptance = contract.build_science_release_acceptance(
        release=release,
        controller_identity=terminal["controller_identity"],
        bootstrap_identity=terminal["bootstrap_identity"],
        execution_closure_sha256=terminal["execution_closure_sha256"],
    )
    acceptance_path = attempt / "science_release_accepted.json"
    acceptance_path.write_bytes(contract.canonical_bytes(acceptance))
    terminal.update(
        {
            "startup_ready_sha256": contract.sha256_file(ready_path),
            "release_sha256": contract.sha256_file(release_path),
            "release_payload_sha256": contract.canonical_sha256(release),
            "release": release,
            "release_acceptance_sha256": contract.sha256_file(acceptance_path),
            "release_acceptance": acceptance,
        }
    )
    terminal_path.write_bytes(contract.canonical_bytes(terminal))
    with pytest.raises(contract.FormalActivationRejected, match="ready|protocol"):
        contract.validate_terminal_outcome(
            terminal_path,
            formal_roots_override=_formal_roots_for_attempt(attempt),
        )


def test_terminal_validator_rejects_cross_attempt_replay(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    terminal_path = _valid_terminal_path(source)
    replay_attempt = tmp_path / "replay" / "attempt"
    shutil.copytree(terminal_path.parent, replay_attempt)
    replay = replay_attempt / terminal_path.name
    replay_roots = {
        name: (replay_attempt / "formal_roots" / name).resolve()
        for name in ("checkpoint", "worker", "log", "output")
    }
    with pytest.raises(
        contract.FormalActivationRejected, match="attempt|path|authority drifted"
    ):
        contract.validate_terminal_outcome(
            replay,
            formal_roots_override=replay_roots,
        )


def test_real_two_process_preseal_probe_completes_without_solver(
    tmp_path: Path,
) -> None:
    report = bootstrap._execute_preseal_startup_probe(tmp_path / "attempt")
    assert report["preflight_captured"] is True
    assert report["authority_consumed"] is True
    assert report["controller_spawned"] is True
    assert report["release_acceptance_proven"] is True
    assert report["terminal_class"] == "success"
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0
    assert report["power_system_block_count"] == 1071


@pytest.mark.parametrize("fault_type", ["KeyboardInterrupt", "SystemExit"])
def test_real_two_process_success_terminal_winner_keeps_zero_exit(
    tmp_path: Path, fault_type: str
) -> None:
    report = bootstrap._execute_preseal_startup_probe(
        tmp_path / "attempt",
        fault_phase="terminal_success_after_persist_before_return",
        fault_type=fault_type,
    )
    assert report["terminal_class"] == "success"
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0


@pytest.mark.parametrize("fault_type", ["KeyboardInterrupt", "SystemExit"])
def test_acceptance_return_to_protected_lifecycle_exit_is_terminal_unresolved(
    tmp_path: Path, fault_type: str
) -> None:
    attempt = tmp_path / "attempt"
    with pytest.raises(contract.FormalActivationRejected):
        bootstrap._execute_preseal_startup_probe(
            attempt,
            fault_phase="acceptance_after_validation_before_protected_lifecycle",
            fault_type=fault_type,
        )
    terminal = contract.load_terminal_outcome(attempt)
    assert terminal["terminal_class"] == "unresolved"
    assert terminal["mathematical_infeasibility_inferred"] is False
    assert len(list(attempt.glob("terminal_outcome.json"))) == 1
    spawn_path = attempt / "spawn_receipt.json"
    if spawn_path.exists():
        spawn = contract.validate_spawn_receipt(spawn_path)["receipt"]
        assert spawn["returncode"] is None
        lifecycle = contract.validate_lifecycle_decision(
            attempt / "lifecycle_decision.json",
            formal_roots_override=_formal_roots_for_attempt(attempt),
        )["outcome"]
        assert lifecycle["lifecycle_class"] == "cancelled_before_science"


def test_dead_after_acceptance_is_recovered_before_spawn_receipt_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = tmp_path / "attempt"
    controller_identity = {"pid": 4242, "create_time_ns": 987654321}
    bootstrap_identity = {"pid": 4343, "create_time_ns": 123456789}
    _release_and_acceptance(attempt, identity=controller_identity)
    authority_path = attempt / "authority.json"
    dynamic = {
        **contract.validate_dynamic_authority(authority_path),
        "authority_path": str(authority_path),
        "authority_sha256": contract.sha256_file(authority_path),
    }
    process: Any

    class DeadAfterAcceptanceProcess:
        pid = controller_identity["pid"]

        def __init__(self) -> None:
            self.returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

    process = DeadAfterAcceptanceProcess()
    recovery_modes: list[bool] = []
    paths = {name: Path(value) for name, value in dynamic["startup_paths"].items()}

    monkeypatch.setattr(bootstrap.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        bootstrap, "_observe_process_identity", lambda value: controller_identity
    )
    monkeypatch.setattr(
        bootstrap,
        "_wait_for_controller_handshake",
        lambda *args, **kwargs: json.loads(paths["handshake"].read_text()),
    )
    monkeypatch.setattr(
        bootstrap,
        "_publish_startup_ack",
        lambda *args, **kwargs: json.loads(paths["bootstrap_ack"].read_text()),
    )
    monkeypatch.setattr(
        bootstrap,
        "_wait_for_startup_ready",
        lambda *args, **kwargs: json.loads(paths["startup_ready"].read_text()),
    )

    def acceptance_then_exit(*args: Any, **kwargs: Any) -> dict[str, Any]:
        release = json.loads(paths["science_release"].read_text())
        accepted = contract.build_science_release_acceptance(
            release=release,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            execution_closure_sha256=dynamic["execution_closure"]["members_sha256"],
        )
        contract._atomic_write(
            paths["science_release_accepted"], contract.canonical_bytes(accepted)
        )
        process.returncode = 17
        return accepted

    monkeypatch.setattr(bootstrap, "_wait_for_release_acceptance", acceptance_then_exit)
    monkeypatch.setattr(
        bootstrap,
        "_recover_post_release_baseexception",
        lambda *args, **kwargs: (
            recovery_modes.append(bool(kwargs.get("spawn_receipt_committed", False)))
            or {}
        ),
    )

    with pytest.raises(contract.FormalActivationRejected):
        bootstrap._spawn_controller(
            list(dynamic["exact_command"]),
            cwd=contract.ROOT,
            environment=dynamic["exact_environment"],
            dynamic=dynamic,
            bootstrap_identity=bootstrap_identity,
        )

    assert recovery_modes == [False]
    assert not paths["spawn_receipt"].exists()
    assert not paths["lifecycle_decision"].exists()


def test_live_spawn_receipt_payload_is_strictly_validated_before_commit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = tmp_path / "attempt"
    controller_identity = {"pid": 4242, "create_time_ns": 987654321}
    bootstrap_identity = {"pid": 4343, "create_time_ns": 123456789}
    _release_and_acceptance(attempt, identity=controller_identity)
    authority_path = attempt / "authority.json"
    dynamic = {
        **contract.validate_dynamic_authority(authority_path),
        "authority_path": str(authority_path),
        "authority_sha256": contract.sha256_file(authority_path),
    }
    paths = {name: Path(value) for name, value in dynamic["startup_paths"].items()}

    class LiveProcess:
        pid = controller_identity["pid"]
        returncode = None

        def poll(self) -> None:
            return None

    process = LiveProcess()
    validation_calls: list[dict[str, Any]] = []
    receipt_presence_at_validation: list[bool] = []
    original_validate = contract.validate_spawn_receipt_payload

    monkeypatch.setattr(bootstrap.subprocess, "Popen", lambda *args, **kwargs: process)
    monkeypatch.setattr(
        bootstrap, "_observe_process_identity", lambda value: controller_identity
    )
    monkeypatch.setattr(
        bootstrap.process_identity,
        "_process_creation_time_ns",
        lambda pid: controller_identity["create_time_ns"],
    )
    monkeypatch.setattr(
        bootstrap,
        "_wait_for_controller_handshake",
        lambda *args, **kwargs: json.loads(paths["handshake"].read_text()),
    )
    monkeypatch.setattr(
        bootstrap,
        "_publish_startup_ack",
        lambda *args, **kwargs: json.loads(paths["bootstrap_ack"].read_text()),
    )
    monkeypatch.setattr(
        bootstrap,
        "_wait_for_startup_ready",
        lambda *args, **kwargs: json.loads(paths["startup_ready"].read_text()),
    )

    def publish_acceptance(*args: Any, **kwargs: Any) -> dict[str, Any]:
        release = json.loads(paths["science_release"].read_text())
        accepted = contract.build_science_release_acceptance(
            release=release,
            controller_identity=controller_identity,
            bootstrap_identity=bootstrap_identity,
            execution_closure_sha256=dynamic["execution_closure"]["members_sha256"],
        )
        contract._atomic_write(
            paths["science_release_accepted"], contract.canonical_bytes(accepted)
        )
        return accepted

    monkeypatch.setattr(
        bootstrap,
        "_wait_for_release_acceptance",
        publish_acceptance,
    )

    def validate_payload(
        payload: Mapping[str, Any], *, attempt_root: Path
    ) -> dict[str, Any]:
        assert process.poll() is None
        validation_calls.append(dict(payload))
        receipt_presence_at_validation.append(paths["spawn_receipt"].exists())
        return original_validate(payload, attempt_root=attempt_root)

    monkeypatch.setattr(contract, "validate_spawn_receipt_payload", validate_payload)
    monkeypatch.setattr(
        bootstrap,
        "_supervise_controller_after_acceptance",
        lambda *args, **kwargs: {"terminal_class": "success"},
    )

    spawn = bootstrap._spawn_controller(
        list(dynamic["exact_command"]),
        cwd=contract.ROOT,
        environment=dynamic["exact_environment"],
        dynamic=dynamic,
        bootstrap_identity=bootstrap_identity,
    )

    assert len(validation_calls) == 2
    assert receipt_presence_at_validation == [False, True]
    assert all(payload["returncode"] is None for payload in validation_calls)
    assert validation_calls[0] == validation_calls[1]
    assert spawn["returncode"] is None
    assert (
        contract.validate_spawn_receipt(paths["spawn_receipt"])["receipt"]
        == (validation_calls[0])
    )


def test_tmp_v5_closure_matches_independent_modulefinder_exact_set(
    tmp_path: Path,
) -> None:
    root = contract.ROOT
    implementation = set(contract.derive_execution_closure_members())
    entry_points = [
        root
        / "experiments/bootstrap_rq2_public_grid_highs_formal_activation_successor_v5.py"
    ]
    for module_name in sorted(contract.DYNAMIC_EXECUTION_MODULES):
        module_path = contract._module_file(module_name)
        assert module_path is not None
        entry_points.append(module_path)
    oracle: set[str] = set()
    for entry_point in entry_points:
        finder = ModuleFinder(path=[str(root)])
        finder.run_script(str(entry_point))
        oracle.add(entry_point.resolve().relative_to(root).as_posix())
        oracle.update(
            Path(module.__file__).resolve().relative_to(root).as_posix()
            for module in finder.modules.values()
            if getattr(module, "__file__", None)
            and Path(module.__file__).resolve().is_relative_to(root)
        )
    oracle.update(
        {
            contract.CONFIG.relative_to(root).as_posix(),
            contract.FORMAL_CONFIG.relative_to(root).as_posix(),
        }
    )
    assert implementation == oracle
    assert (
        "experiments/bootstrap_rq2_public_grid_highs_formal_activation_successor_v5.py"
        in implementation
    )
    assert (
        "experiments/rq2_public_grid_highs_formal_activation_contract_v5.py"
        in implementation
    )
    assert (
        "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v6.py"
        in implementation
    )
    closure_path = tmp_path / "execution_closure.NONAUTHORITATIVE.json"
    closure = contract.persist_preseal_execution_closure(closure_path)
    assert closure["member_count"] == len(oracle)
    assert closure["members_sha256"] == contract.canonical_sha256(closure["members"])
    assert contract.sha256_file(closure_path) == contract.sha256_file(closure_path)
    production_closure = (
        root
        / "configs/rq2_public_grid_highs_formal_activation_successor_v5.EXECUTION_CLOSURE.SHA256SUMS.json"
    )
    if contract.load_config()["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW":
        assert production_closure.exists()
        assert (
            contract.verify_execution_closure(require_frozen_expected=True)[
                "expected_hashes_verified"
            ]
            is True
        )
    else:
        assert not production_closure.exists()


def test_selected_current_closure_has_matching_authority_state(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("RQ2_V5_PRESEAL_CLOSURE", raising=False)
    closure = contract.verify_execution_closure()
    if contract.load_config()["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW":
        assert closure["expected_hashes_verified"] is True
        assert closure["hash_authority"] == "frozen_expected"
    else:
        assert closure["expected_hashes_verified"] is False
        assert closure["hash_authority"] == "derived_current"


@pytest.mark.parametrize(
    ("mode", "recovery_fault_type", "expected_reason"),
    [
        ("identity_mismatch", None, "FormalActivationRejected"),
        ("termination_failure", None, "RuntimeError"),
        ("secondary_baseexception", "KeyboardInterrupt", "KeyboardInterrupt"),
        ("secondary_baseexception", "SystemExit", "SystemExit"),
    ],
)
def test_real_production_recovery_is_terminal_and_bystander_safe(
    tmp_path: Path,
    mode: str,
    recovery_fault_type: str | None,
    expected_reason: str,
) -> None:
    attempt = tmp_path / "attempt"
    bystander, _ = _spawn_sleeper()
    try:
        with pytest.raises(KeyboardInterrupt):
            bootstrap._execute_preseal_startup_probe(
                attempt,
                fault_phase="release_after_stable_readback_before_phase_return",
                fault_type="KeyboardInterrupt",
                termination_identity_mismatch=mode == "identity_mismatch",
                injected_termination_failure=mode == "termination_failure",
                recovery_fault_type=recovery_fault_type,
            )
        assert bystander.poll() is None
        terminal = contract.load_terminal_outcome(attempt)
        assert terminal["terminal_class"] == "unresolved"
        assert expected_reason in terminal["termination"]["reason"]
        assert terminal["formal_result_exists"] is False
        assert terminal["mathematical_infeasibility_inferred"] is False
        if mode in {"identity_mismatch", "termination_failure"}:
            assert not (attempt / "preseal_recovery_cleanup.json").exists()
            cancellation = json.loads(
                (attempt / "controller_cancellation.json").read_text(encoding="utf-8")
            )
            acknowledgement = json.loads(
                (attempt / "controller_cancellation_ack.json").read_text(
                    encoding="utf-8"
                )
            )
            assert (
                cancellation["controller_identity"] == terminal["controller_identity"]
            )
            assert acknowledgement["cancellation_sha256"] == contract.sha256_file(
                attempt / "controller_cancellation.json"
            )
            assert (
                acknowledgement["controller_identity"]
                == terminal["controller_identity"]
            )
        else:
            assert terminal["termination"]["attempted"] is True
            assert terminal["termination"]["returncode"] is not None
        assert len(list(attempt.glob("terminal_outcome.json"))) == 1
        assert not (attempt / "controller_terminal_success.json").exists()
        assert not (attempt / "post_release_unresolved.json").exists()
    finally:
        if bystander.poll() is None:
            bystander.terminate()
            bystander.wait(timeout=5)


@pytest.mark.parametrize(
    "fault_stage",
    ["post_acceptance_before_spawn_receipt", "spawn_receipt_after_atomic_commit"],
)
def test_real_post_acceptance_and_spawn_receipt_baseexception_is_terminal(
    tmp_path: Path, fault_stage: str
) -> None:
    attempt = tmp_path / "attempt"
    with pytest.raises(KeyboardInterrupt, match="injected"):
        bootstrap._execute_preseal_startup_probe(
            attempt,
            fault_phase=fault_stage,
            fault_type="KeyboardInterrupt",
        )
    terminal = contract.load_terminal_outcome(attempt)
    assert terminal["terminal_class"] in {"success", "unresolved"}
    assert terminal["release_acceptance_proven"] is True
    assert len(list(attempt.glob("terminal_outcome.json"))) == 1
    assert not (attempt / "launch_incomplete.json").exists()
    assert (attempt / "spawn_receipt.json").exists() is (
        fault_stage == "spawn_receipt_after_atomic_commit"
    )


@pytest.mark.parametrize(
    (
        "fault_type",
        "mode",
        "recovery_fault_type",
        "expected_recovery_reason",
        "strict_ack_required",
    ),
    [
        (
            "KeyboardInterrupt",
            "identity_mismatch",
            None,
            "FormalActivationRejected",
            True,
        ),
        ("SystemExit", "termination_failure", None, "RuntimeError", True),
        (
            "KeyboardInterrupt",
            "secondary_baseexception",
            "KeyboardInterrupt",
            "KeyboardInterrupt",
            False,
        ),
        (
            "SystemExit",
            "secondary_baseexception",
            "SystemExit",
            "SystemExit",
            False,
        ),
    ],
)
def test_post_spawn_receipt_baseexception_uses_shared_production_recovery(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    fault_type: str,
    mode: str,
    recovery_fault_type: str | None,
    expected_recovery_reason: str,
    strict_ack_required: bool,
) -> None:
    attempt = tmp_path / "attempt"
    bystander, _ = _spawn_sleeper()
    owned_controllers: list[subprocess.Popen[Any]] = []
    real_popen = bootstrap.subprocess.Popen

    def capture_controller(command: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
        process = real_popen(command, **kwargs)
        if controller.MODULE in command:
            owned_controllers.append(process)
        return process

    monkeypatch.setattr(bootstrap.subprocess, "Popen", capture_controller)
    expected_exception = (
        KeyboardInterrupt if fault_type == "KeyboardInterrupt" else SystemExit
    )
    try:
        with pytest.raises(expected_exception, match="injected"):
            bootstrap._execute_preseal_startup_probe(
                attempt,
                fault_phase="spawn_receipt_after_atomic_commit",
                fault_type=fault_type,
                termination_identity_mismatch=mode == "identity_mismatch",
                injected_termination_failure=mode == "termination_failure",
                recovery_fault_type=recovery_fault_type,
            )

        assert bystander.poll() is None
        assert (attempt / "spawn_receipt.json").is_file()
        terminal = contract.load_terminal_outcome(attempt)
        assert terminal["terminal_class"] == "unresolved"
        assert terminal["release_acceptance_proven"] is True
        assert expected_recovery_reason in terminal["termination"]["reason"]
        assert len(list(attempt.glob("terminal_outcome.json"))) == 1
        assert not (attempt / "launch_incomplete.json").exists()
        assert not (attempt / "controller_terminal_success.json").exists()
        assert not (attempt / "post_release_unresolved.json").exists()

        dynamic_path = attempt / "authority.json"
        dynamic = json.loads(dynamic_path.read_text(encoding="utf-8"))
        cancellation_path = attempt / "controller_cancellation.json"
        cancellation = contract.validate_controller_cancellation(
            cancellation_path,
            dynamic_authority=dynamic_path,
            controller_identity=terminal["controller_identity"],
            bootstrap_identity=dynamic["bootstrap_identity"],
        )
        acknowledgement_path = attempt / "controller_cancellation_ack.json"
        has_strict_ack = acknowledgement_path.is_file()
        if has_strict_ack:
            acknowledgement = contract.validate_controller_stop_ack(
                acknowledgement_path,
                dynamic_authority=dynamic_path,
                controller_identity=terminal["controller_identity"],
                bootstrap_identity=dynamic["bootstrap_identity"],
            )
            assert acknowledgement["cancellation_sha256"] == contract.sha256_file(
                cancellation_path
            )
        else:
            assert strict_ack_required is False
        assert cancellation["controller_identity"] == terminal["controller_identity"]
        assert len(owned_controllers) == 1
        assert has_strict_ack or owned_controllers[0].poll() is not None
        assert all(
            not path.exists() for path in _formal_roots_for_attempt(attempt).values()
        )
        assert all(not path.exists() for path in contract.formal_roots().values())
    finally:
        if bystander.poll() is None:
            bystander.terminate()
            bystander.wait(timeout=5)


def test_post_release_launch_incomplete_is_forbidden(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt"
    _release_and_acceptance(attempt)
    with pytest.raises(contract.FormalActivationRejected, match="forbidden"):
        bootstrap._record_launch_incomplete(
            attempt,
            phase="forged_post_release",
            reason="injected",
            controller_identity={"pid": 4242, "create_time_ns": 987654321},
            returncode=None,
            termination={"attempted": False, "reason": "fixture", "returncode": None},
        )


def test_preseal_authority_cannot_enter_science_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = tmp_path / "attempt"
    bootstrap_identity = {
        "pid": os.getpid(),
        "create_time_ns": bootstrap.process_identity._process_creation_time_ns(
            os.getpid()
        ),
    }
    dynamic, _ = contract.prepare_preseal_authority(
        attempt, bootstrap_identity=bootstrap_identity
    )
    called = False

    def forbidden_handshake(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal called
        called = True
        raise AssertionError("handshake must not run")

    monkeypatch.setattr(controller, "_complete_startup_handshake", forbidden_handshake)
    paths = {key: Path(value) for key, value in dynamic["startup_paths"].items()}
    with pytest.raises(
        contract.FormalActivationRejected, match="cannot enter the science path"
    ):
        controller.run(
            contract.FORMAL_CONFIG,
            Path(dynamic["authority_path"]),
            bootstrap_identity=bootstrap_identity,
            handshake_path=paths["handshake"],
            ack_path=paths["bootstrap_ack"],
            ready_path=paths["startup_ready"],
            release_path=paths["science_release"],
            release_accepted_path=paths["science_release_accepted"],
            preseal_startup_probe=False,
        )
    assert called is False
    assert all(not Path(path).exists() for path in dynamic["formal_roots"].values())


def _source_line(function: Any, exact_text: str) -> int:
    lines, first = inspect.getsourcelines(function)
    matches = [
        first + offset
        for offset, line in enumerate(lines)
        if line.strip() == exact_text
    ]
    assert len(matches) == 1
    return matches[0]


@pytest.mark.parametrize("fault_type", ["KeyboardInterrupt", "SystemExit"])
def test_bootstrap_acceptance_to_spawn_try_line_gap_is_recovered(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, fault_type: str
) -> None:
    """The first executable line after acceptance must share its recovery envelope."""
    attempt = tmp_path / "attempt"
    target_line = _source_line(
        bootstrap._spawn_controller, 'path = paths["spawn_receipt"]'
    )
    exception_type = (
        KeyboardInterrupt if fault_type == "KeyboardInterrupt" else SystemExit
    )
    owned: list[subprocess.Popen[Any]] = []
    real_popen = bootstrap.subprocess.Popen

    def capture_controller(command: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
        process = real_popen(command, **kwargs)
        if controller.MODULE in command:
            owned.append(process)
        return process

    def inject_at_gap(frame: Any, event: str, _arg: Any) -> Any:
        if (
            event == "line"
            and frame.f_code is bootstrap._spawn_controller.__code__
            and frame.f_lineno == target_line
        ):
            raise exception_type("injected:bootstrap_acceptance_to_spawn_try_gap")
        return inject_at_gap

    monkeypatch.setattr(bootstrap.subprocess, "Popen", capture_controller)
    previous_trace = sys.gettrace()
    try:
        sys.settrace(inject_at_gap)
        with pytest.raises(
            exception_type, match="injected:bootstrap_acceptance_to_spawn_try_gap"
        ):
            bootstrap._execute_preseal_startup_probe(attempt)
    finally:
        sys.settrace(previous_trace)
    try:
        assert len(owned) == 1
        terminal = contract.load_terminal_outcome(attempt)
        assert terminal["terminal_class"] in {"success", "unresolved"}
        assert terminal["release_acceptance_proven"] is True
        assert owned[0].poll() is not None
        assert len(list(attempt.glob("terminal_outcome.json"))) == 1
        assert not (attempt / "launch_incomplete.json").exists()
    finally:
        for process in owned:
            if process.poll() is None:
                process.terminate()
                process.wait(timeout=10)


def test_ordinary_stable_bytes_rejects_endpoint_replacement_during_read(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.json"
    replacement = tmp_path / "replacement.json"
    target.write_bytes(b"original")
    replacement.write_bytes(b"alternate")
    real_read = anchored_v3._read_all_descriptor
    calls = 0

    def replace_after_first_descriptor_read(descriptor: int) -> bytes:
        nonlocal calls
        raw = real_read(descriptor)
        calls += 1
        if calls == 1:
            os.replace(replacement, target)
        return raw

    monkeypatch.setattr(
        anchored_v3, "_read_all_descriptor", replace_after_first_descriptor_read
    )
    with pytest.raises(contract.FormalActivationRejected, match="drift|stable|read"):
        contract._ordinary_stable_bytes(target, "endpoint replacement probe")
    assert calls >= 1


def test_ordinary_stable_bytes_never_accepts_ancestor_swap_read_swap_back(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    live_parent = tmp_path / "live"
    alternate_parent = tmp_path / "alternate"
    parked_parent = tmp_path / "parked"
    live_parent.mkdir()
    alternate_parent.mkdir()
    target = live_parent / "target.json"
    target.write_bytes(b"original")
    alternate_target = alternate_parent / target.name
    alternate_target.write_bytes(b"alternate")
    real_open = contract._open_ordinary_anchored
    real_close = contract._close_ordinary_descriptor
    open_calls = 0
    close_calls = 0
    swap_injections = 0
    swap_restorations = 0
    injected_descriptor_identity: tuple[int, ...] | None = None

    def swap_ancestor_around_first_anchored_open(path: Path, label: str) -> int:
        nonlocal open_calls, swap_injections, injected_descriptor_identity
        open_calls += 1
        if path != target or swap_injections:
            return real_open(path, label)
        swap_injections += 1
        os.replace(live_parent, parked_parent)
        os.replace(alternate_parent, live_parent)
        descriptor = real_open(path, label)
        injected_descriptor_identity = contract._ordinary_file_identity(
            os.fstat(descriptor)
        )
        return descriptor

    def restore_ancestor_after_first_descriptor_close(
        descriptor: int, label: str, *, primary_error: BaseException | None
    ) -> None:
        nonlocal close_calls, swap_restorations
        real_close(descriptor, label, primary_error=primary_error)
        close_calls += 1
        if close_calls == 1:
            os.replace(live_parent, alternate_parent)
            os.replace(parked_parent, live_parent)
            swap_restorations += 1

    monkeypatch.setattr(
        contract,
        "_open_ordinary_anchored",
        swap_ancestor_around_first_anchored_open,
    )
    monkeypatch.setattr(
        contract,
        "_close_ordinary_descriptor",
        restore_ancestor_after_first_descriptor_close,
    )
    with pytest.raises(
        contract.FormalActivationRejected, match="stable file identity drifted"
    ):
        contract._ordinary_stable_bytes(target, "ancestor replacement probe")
    assert swap_injections == 1
    assert swap_restorations == 1
    assert open_calls == 2
    assert close_calls == 2
    assert injected_descriptor_identity == contract._ordinary_file_identity(
        alternate_target.stat()
    )
    assert target.read_bytes() == b"original"
    assert alternate_target.read_bytes() == b"alternate"


@pytest.mark.parametrize("link_kind", ["hardlink", "symlink"])
def test_ordinary_stable_bytes_rejects_linked_endpoint(
    tmp_path: Path, link_kind: str
) -> None:
    source = tmp_path / "source.json"
    linked = tmp_path / "linked.json"
    source.write_bytes(b"payload")
    junction: Path | None = None
    if link_kind == "hardlink":
        os.link(source, linked)
    else:
        try:
            linked.symlink_to(source)
        except OSError as exc:
            if os.name != "nt":
                pytest.skip(f"symlink unavailable: {exc}")
            source_parent = tmp_path / "source-parent"
            source_parent.mkdir()
            source = source_parent / "source.json"
            source.write_bytes(b"payload")
            junction = tmp_path / "source-parent-junction"
            completed = subprocess.run(
                [
                    "cmd.exe",
                    "/d",
                    "/c",
                    "mklink",
                    "/J",
                    str(junction),
                    str(source_parent),
                ],
                check=False,
                capture_output=True,
                text=True,
            )
            assert completed.returncode == 0, completed.stderr
            linked = junction / source.name
    try:
        with pytest.raises(
            contract.FormalActivationRejected, match="link|alias|ordinary|anchored"
        ):
            contract._ordinary_stable_bytes(linked, f"{link_kind} endpoint")
    finally:
        if junction is not None and junction.exists():
            junction.rmdir()


def test_ordinary_stable_bytes_closes_descriptor_after_read_callback_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target.json"
    target.write_bytes(b"payload")
    observed_descriptors: list[int] = []

    def fail_read(descriptor: int) -> bytes:
        observed_descriptors.append(descriptor)
        raise RuntimeError("injected descriptor read callback failure")

    monkeypatch.setattr(anchored_v3, "_read_all_descriptor", fail_read)
    with pytest.raises(RuntimeError, match="injected descriptor read callback failure"):
        contract._ordinary_stable_bytes(target, "read callback cleanup probe")
    assert observed_descriptors
    for descriptor in observed_descriptors:
        with pytest.raises(OSError):
            os.fstat(descriptor)


def _windows_short_path(path: Path) -> Path | None:
    if os.name != "nt":
        return None
    import ctypes

    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.GetShortPathNameW.argtypes = (
        ctypes.c_wchar_p,
        ctypes.c_wchar_p,
        ctypes.c_uint,
    )
    kernel32.GetShortPathNameW.restype = ctypes.c_uint
    capacity = 32768
    buffer = ctypes.create_unicode_buffer(capacity)
    length = kernel32.GetShortPathNameW(str(path), buffer, capacity)
    if length == 0 or length >= capacity:
        return None
    short = Path(buffer.value)
    return short if str(short).casefold() != str(path).casefold() else None


def test_preseal_authority_windows_short_alias_self_validates(
    tmp_path: Path,
) -> None:
    short_parent = _windows_short_path(tmp_path)
    if short_parent is None:
        pytest.skip("Windows 8.3 alias is unavailable on this volume")
    alias_attempt = short_parent / "alias_attempt"
    canonical_attempt = (tmp_path / "alias_attempt").resolve()
    bootstrap_identity = {
        "pid": os.getpid(),
        "create_time_ns": bootstrap.process_identity._process_creation_time_ns(
            os.getpid()
        ),
    }
    dynamic, tombstone = contract.prepare_preseal_authority(
        alias_attempt, bootstrap_identity=bootstrap_identity
    )
    authority_path = canonical_attempt / "authority.json"
    assert Path(dynamic["authority_path"]) == authority_path
    assert Path(tombstone["dynamic_authority_path"]) == authority_path
    validated = contract.validate_dynamic_authority(authority_path)
    assert validated == {key: dynamic[key] for key in validated}


def test_preseal_authority_canonical_long_path_is_unchanged(tmp_path: Path) -> None:
    attempt = (tmp_path / "long_path_attempt").resolve()
    bootstrap_identity = {
        "pid": os.getpid(),
        "create_time_ns": bootstrap.process_identity._process_creation_time_ns(
            os.getpid()
        ),
    }
    dynamic, _ = contract.prepare_preseal_authority(
        attempt, bootstrap_identity=bootstrap_identity
    )
    assert Path(dynamic["authority_path"]) == attempt / "authority.json"
    validated = contract.validate_dynamic_authority(attempt / "authority.json")
    assert validated == {key: dynamic[key] for key in validated}


def test_review_gate_precedes_run_authority_and_closure_drift_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempt = tmp_path / "attempt"
    bootstrap_identity = {
        "pid": os.getpid(),
        "create_time_ns": bootstrap.process_identity._process_creation_time_ns(
            os.getpid()
        ),
    }
    dynamic, _ = contract.prepare_preseal_authority(
        attempt, bootstrap_identity=bootstrap_identity
    )
    config = contract.load_config()
    if config["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW":
        assert contract.production_artifact_paths()
        contract.require_sealed_for_execution()
        review_raw = config["production_artifacts"]["activation_review_receipt"]
        review_path = contract._repo_path(review_raw, "activation review receipt")
        if contract._entry_exists(review_path):
            contract.require_activation_review_pass()
        else:
            with pytest.raises(
                contract.FormalActivationRejected,
                match="activation review PASS receipt",
            ):
                contract.require_activation_review_pass()
    else:
        assert contract.production_artifact_paths() == []
        with pytest.raises(
            contract.FormalActivationRejected, match="non-authoritative draft"
        ):
            contract.require_sealed_for_execution()
    closure_path = Path(dynamic["execution_closure"]["path"])
    closure = json.loads(closure_path.read_text(encoding="utf-8"))
    closure["members_sha256"] = "0" * 64
    closure_path.write_bytes(contract.canonical_bytes(closure))
    monkeypatch.setenv("RQ2_V5_PRESEAL_CLOSURE", str(closure_path))
    with pytest.raises(contract.FormalActivationRejected, match="closure drifted"):
        contract.verify_execution_closure()


def test_runtime_authority_binds_real_highspy_files_without_solver_call(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import highspy

    contract.validate_runtime_files()
    controller._load_science_dependencies()
    real_highs = highspy.Highs
    solver_calls = 0

    class RuntimeProbeHighs:
        def __init__(self) -> None:
            self.instance = real_highs()

        def version(self) -> str:
            return self.instance.version()

        def versionMajor(self) -> int:
            return self.instance.versionMajor()

        def versionMinor(self) -> int:
            return self.instance.versionMinor()

        def versionPatch(self) -> int:
            return self.instance.versionPatch()

        def run(self) -> None:
            nonlocal solver_calls
            solver_calls += 1
            raise AssertionError("runtime identity probe must not solve")

    monkeypatch.setattr(highspy, "Highs", RuntimeProbeHighs)
    identity = {"pid": os.getpid(), "create_time_ns": time.time_ns()}
    evidence = controller._collect_formal_solver_runtime_evidence(
        identity, {"config": contract.validate_formal_config()}
    )
    runtime = contract.load_config()["runtime"]
    assert (
        evidence["highspy_package_init_sha256"]
        == runtime["highspy_package_init_sha256"]
    )
    assert (
        evidence["highspy_python_source_sha256"]
        == runtime["highspy_python_source_sha256"]
    )
    assert evidence["highspy_binary_sha256"] == runtime["highspy_binary_sha256"]
    assert evidence["solver_solve_called_by_runtime_probe"] is False
    assert solver_calls == 0


def test_production_artifact_paths_expands_one_shot_mapping(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    production = {
        "inner_manifest": "configs/v5.inner.json",
        "outer_manifest": "configs/v5.outer.json",
        "execution_closure": "configs/v5.closure.json",
        "one_shot_lease": {
            "fresh_path": "results/leases/v5.fresh.json",
            "fresh_sha256": "a" * 64,
            "consumed_path": "results/leases/v5.consumed.json",
            "authority_id": "b" * 64,
            "one_shot": True,
        },
        "activation_review_receipt": "configs/v5.review.json",
        "user_formal_run_authority": "configs/v5.user.json",
    }
    monkeypatch.setattr(
        contract, "load_config", lambda: {"production_artifacts": production}
    )
    paths = contract.production_artifact_paths()
    assert len(paths) == 7
    assert contract.ROOT / "results/leases/v5.fresh.json" in paths
    assert contract.ROOT / "results/leases/v5.consumed.json" in paths


def test_sealed_gate_validates_bundle_without_opening_run_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    closure = {"expected_hashes_verified": True}
    monkeypatch.setattr(
        contract,
        "load_config",
        lambda: {"status": "SEALED_READY_FOR_INDEPENDENT_REVIEW"},
    )
    monkeypatch.setattr(
        contract, "validate_formal_config", lambda: calls.append("formal")
    )
    monkeypatch.setattr(
        contract,
        "verify_execution_closure",
        lambda **kwargs: calls.append("closure") or closure,
    )
    monkeypatch.setattr(
        contract,
        "_verify_sealed_bundle",
        lambda **kwargs: calls.append("bundle") or {"closure": closure},
    )
    monkeypatch.setattr(
        contract,
        "require_activation_review_pass",
        lambda: (_ for _ in ()).throw(AssertionError("review gate must stay closed")),
    )
    assert contract.require_sealed_for_execution() == {"closure": closure}
    assert calls == ["formal", "closure", "bundle"]


def test_fresh_lease_and_review_user_receipts_require_exact_keys(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(contract, "ROOT", tmp_path)
    formal_config = tmp_path / "formal.yaml"
    formal_config.write_text("status: fixture\n", encoding="utf-8")
    monkeypatch.setattr(contract, "FORMAL_CONFIG", formal_config)
    paths = {
        name: tmp_path / f"{name}.json"
        for name in (
            "outer_manifest",
            "execution_closure",
            "activation_review_receipt",
            "user_formal_run_authority",
        )
    }
    for name in ("outer_manifest", "execution_closure"):
        contract.persist_json_stable(paths[name], {"name": name})
    fresh = tmp_path / "fresh.json"
    consumed = tmp_path / "consumed.json"
    fresh_payload = {
        "schema": (
            "rq2_public_grid_highs_formal_activation_successor_v5_one_shot_authority"
        ),
        "version": 5,
        "authority_id": "c" * 64,
        "state": "fresh",
        "one_shot": True,
        "formal_execution_authorized": False,
        "materialized_from_successor_design_authorization": False,
        "security_certified": False,
    }
    contract.persist_json_stable(fresh, fresh_payload)
    lease = {
        "fresh_path": str(fresh),
        "fresh_sha256": contract.sha256_file(fresh),
        "consumed_path": str(consumed),
        "authority_id": fresh_payload["authority_id"],
        "one_shot": True,
    }
    monkeypatch.setattr(
        contract,
        "_repo_path",
        lambda raw, label: (
            Path(str(raw)).resolve()
            if Path(str(raw)).is_absolute()
            else (contract.ROOT / str(raw)).resolve()
        ),
    )
    monkeypatch.setattr(contract, "_production_one_shot", lambda: lease)
    assert contract._verify_fresh_one_shot_authority()["payload"] == fresh_payload
    invalid_fresh = {**fresh_payload, "unexpected": False}
    fresh.write_bytes(contract.canonical_bytes(invalid_fresh))
    lease["fresh_sha256"] = contract.sha256_file(fresh)
    with pytest.raises(contract.FormalActivationRejected, match="fresh one-shot"):
        contract._verify_fresh_one_shot_authority()
    fresh.write_bytes(contract.canonical_bytes(fresh_payload))
    lease["fresh_sha256"] = contract.sha256_file(fresh)
    reservation = contract._one_shot_reservation_path(consumed)
    reservation.mkdir()
    with pytest.raises(contract.FormalActivationRejected, match="already exists"):
        contract._verify_fresh_one_shot_authority()
    reservation.rmdir()

    monkeypatch.setattr(contract, "_production_artifact_path", lambda name: paths[name])
    command_prefix = ["locked", "--activation-authority"]
    monkeypatch.setattr(
        contract,
        "load_config",
        lambda: {"runtime": {"controller_command_prefix": command_prefix}},
    )
    review = {
        "schema": "rq2_public_grid_highs_formal_activation_successor_review_pass_v5",
        "version": 5,
        "reviewed_on": "2026-09-10",
        "reviewer_agent": "/root/fresh_official_reviewer",
        "reviewer_role": "independent_sol_reviewer",
        "reviewer_model": "gpt-5.6-sol",
        "verdict": "PASS",
        "reviewed_outer": {
            "path": paths["outer_manifest"].relative_to(contract.ROOT).as_posix(),
            "sha256": contract.sha256_file(paths["outer_manifest"]),
        },
        "findings": [],
        "materialized_from_independent_review_report": True,
        "cryptographic_reviewer_signature_present": False,
        "effect": {
            "formal_activation_successor_independent_review_passed": True,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        },
    }
    contract.persist_json_stable(paths["activation_review_receipt"], review)
    assert contract.require_activation_review_pass() == review
    paths["activation_review_receipt"].write_bytes(
        contract.canonical_bytes({**review, "unexpected": False})
    )
    with pytest.raises(contract.FormalActivationRejected, match="review PASS"):
        contract.require_activation_review_pass()
    paths["activation_review_receipt"].write_bytes(contract.canonical_bytes(review))
    user = {
        "schema": "rq2_public_grid_highs_formal_run_authority_v5",
        "version": 5,
        "authority_source": "explicit_user_formal_run_authorization",
        "materialized_from_user_instruction": True,
        "cryptographic_user_signature_present": False,
        "review_pass": {
            "path": paths["activation_review_receipt"]
            .relative_to(contract.ROOT)
            .as_posix(),
            "sha256": contract.sha256_file(paths["activation_review_receipt"]),
        },
        "reviewed_outer": review["reviewed_outer"],
        "formal_config": {
            "path": contract.FORMAL_CONFIG.relative_to(contract.ROOT).as_posix(),
            "sha256": contract.sha256_file(contract.FORMAL_CONFIG),
        },
        "execution_closure": {
            "path": paths["execution_closure"].relative_to(contract.ROOT).as_posix(),
            "sha256": contract.sha256_file(paths["execution_closure"]),
        },
        "controller_command_prefix": command_prefix,
        "one_shot_authority": lease,
        "effect": {
            "formal_activation_successor_independent_review_passed": True,
            "user_formal_run_authorized": True,
            "formal_execution_authorized": True,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
        },
    }
    contract.persist_json_stable(paths["user_formal_run_authority"], user)
    assert contract.require_user_formal_run_authority(validated_review=review) == user
    invalid_user = {**user, "unexpected": False}
    paths["user_formal_run_authority"].write_bytes(
        contract.canonical_bytes(invalid_user)
    )
    with pytest.raises(contract.FormalActivationRejected, match="user formal-run"):
        contract.require_user_formal_run_authority(validated_review=review)


def test_one_shot_consume_is_destination_exclusive_across_processes(
    tmp_path: Path,
) -> None:
    fresh = tmp_path / "fresh.json"
    consumed = tmp_path / "consumed.json"
    fresh.write_bytes(contract.canonical_bytes({"state": "fresh"}))
    expected_sha256 = contract.sha256_file(fresh)
    tombstone = {"state": "consumed", "authority_id": "d" * 64}
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    results = context.Queue()
    contenders = [
        context.Process(
            target=_one_shot_contender,
            args=(
                str(fresh),
                str(consumed),
                expected_sha256,
                tombstone,
                start,
                results,
            ),
        )
        for _ in range(2)
    ]
    for contender in contenders:
        contender.start()
    start.set()
    for contender in contenders:
        contender.join(timeout=30)
        assert contender.exitcode == 0
    outcomes = [results.get(timeout=10)["outcome"] for _ in contenders]
    assert sorted(outcomes) == ["consumed", "rejected"]
    assert not contract._entry_exists(fresh)
    assert json.loads(consumed.read_text(encoding="utf-8")) == tombstone


def test_one_shot_preexisting_consumed_is_never_overwritten(tmp_path: Path) -> None:
    fresh = tmp_path / "fresh.json"
    consumed = tmp_path / "consumed.json"
    fresh.write_bytes(b"fresh")
    consumed.write_bytes(b"preexisting")
    with pytest.raises(contract.FormalActivationRejected, match="already reserved"):
        contract._consume_reserved_one_shot(
            fresh,
            consumed,
            expected_sha256=contract.sha256_file(fresh),
            tombstone={"state": "consumed"},
        )
    assert fresh.read_bytes() == b"fresh"
    assert consumed.read_bytes() == b"preexisting"
    assert not contract._entry_exists(contract._one_shot_reservation_path(consumed))


def test_one_shot_interruption_after_atomic_move_makes_fresh_unusable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = tmp_path / "fresh.json"
    consumed = tmp_path / "consumed.json"
    fresh.write_bytes(b"fresh")
    real_rename = os.rename

    def rename_then_interrupt(source: Path, destination: Path) -> None:
        real_rename(source, destination)
        raise KeyboardInterrupt()

    monkeypatch.setattr(contract.os, "rename", rename_then_interrupt)
    with pytest.raises(KeyboardInterrupt):
        contract._consume_reserved_one_shot(
            fresh,
            consumed,
            expected_sha256=contract.sha256_file(fresh),
            tombstone={"state": "consumed"},
        )
    assert not contract._entry_exists(fresh)
    assert consumed.read_bytes() == b"fresh"
    assert contract._one_shot_reservation_path(consumed).is_dir()


def test_one_shot_atomic_move_eliminates_secondary_cleanup_gap(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = tmp_path / "fresh.json"
    consumed = tmp_path / "consumed.json"
    fresh.write_bytes(b"fresh")
    cleanup_checks = 0

    def interrupt_before_move(source: Path, destination: Path) -> None:
        raise KeyboardInterrupt()

    def interrupt_cleanup(path: Path) -> bool:
        nonlocal cleanup_checks
        if path == fresh:
            cleanup_checks += 1
            raise SystemExit("injected secondary cleanup interruption")
        return os.path.lexists(path)

    monkeypatch.setattr(contract.os, "rename", interrupt_before_move)
    monkeypatch.setattr(contract, "_entry_exists", interrupt_cleanup)
    with pytest.raises(KeyboardInterrupt):
        contract._consume_reserved_one_shot(
            fresh,
            consumed,
            expected_sha256=contract.sha256_file(fresh),
            tombstone={"state": "consumed"},
        )
    assert cleanup_checks == 0
    assert os.path.lexists(fresh)
    assert not os.path.lexists(consumed)
    assert contract._one_shot_reservation_path(consumed).is_dir()
    with pytest.raises(contract.FormalActivationRejected, match="already reserved"):
        contract._consume_reserved_one_shot(
            fresh,
            consumed,
            expected_sha256=contract.sha256_file(fresh),
            tombstone={"state": "consumed"},
        )


def test_one_shot_tombstone_failure_after_atomic_move_is_fail_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fresh = tmp_path / "fresh.json"
    consumed = tmp_path / "consumed.json"
    fresh.write_bytes(b"fresh")
    monkeypatch.setattr(
        contract,
        "persist_json_stable",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            RuntimeError("injected tombstone failure")
        ),
    )
    with pytest.raises(RuntimeError, match="injected tombstone failure"):
        contract._consume_reserved_one_shot(
            fresh,
            consumed,
            expected_sha256=contract.sha256_file(fresh),
            tombstone={"state": "consumed"},
        )
    assert not contract._entry_exists(fresh)
    assert consumed.read_bytes() == b"fresh"
    assert contract._one_shot_reservation_path(consumed).is_dir()


def test_production_dynamic_full_closure_is_validated_once_under_timeout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    closure = contract._closure_payload()
    closure.update(
        {
            "schema": "rq2_public_grid_highs_formal_activation_v5_execution_closure",
            "status": "FROZEN_EXPECTED",
            "hash_authority": "frozen_expected",
            "expected_hashes_verified": True,
        }
    )
    closure_path = tmp_path / "closure.json"
    contract.persist_json_stable(closure_path, closure)
    activation_root = tmp_path / "activation"
    activation_root.mkdir()
    attempt = activation_root / "attempt_1"
    static_mapping = {"sealed": "e" * 64}
    lease = {
        "fresh_path": "results/leases/v5.fresh.json",
        "fresh_sha256": "f" * 64,
        "consumed_path": "results/leases/v5.consumed.json",
        "authority_id": "1" * 64,
        "one_shot": True,
    }
    preflight_mapping = {**static_mapping, lease["fresh_path"]: lease["fresh_sha256"]}
    monkeypatch.setattr(contract, "activation_audit_root", lambda: activation_root)
    preflight = contract.capture_preflight_evidence(
        attempt,
        authority_mapping=preflight_mapping,
        observed_available_commit_bytes=lambda: contract.PREFLIGHT_THRESHOLD_BYTES,
    )
    original_verify = contract.verify_execution_closure
    calls = 0

    def tracked_verify(*, require_frozen_expected: bool = False) -> dict[str, Any]:
        nonlocal calls
        calls += 1
        return original_verify(require_frozen_expected=require_frozen_expected)

    monkeypatch.setattr(
        contract,
        "load_config",
        lambda: {"production_artifacts": {"execution_closure": str(closure_path)}},
    )
    original_repo_path = contract._repo_path
    monkeypatch.setattr(
        contract,
        "_repo_path",
        lambda raw, label: (
            Path(str(raw)).resolve()
            if Path(str(raw)).is_absolute()
            else original_repo_path(raw, label)
        ),
    )
    monkeypatch.setattr(contract, "verify_execution_closure", tracked_verify)
    monkeypatch.setattr(
        contract, "_verify_sealed_bundle", lambda **kwargs: {"closure": closure}
    )
    monkeypatch.setattr(
        contract,
        "production_static_authority_mapping",
        lambda **kwargs: static_mapping,
    )
    monkeypatch.setattr(contract, "_production_one_shot", lambda: lease)
    monkeypatch.setattr(
        contract,
        "_expected_preflight_authority_mapping",
        lambda **kwargs: preflight_mapping,
    )
    monkeypatch.setattr(contract, "require_activation_review_pass", dict)
    monkeypatch.setattr(
        contract, "require_user_formal_run_authority", lambda **kwargs: {}
    )
    monkeypatch.setattr(
        contract,
        "_production_artifact_path",
        lambda name: (
            closure_path if name == "execution_closure" else tmp_path / f"{name}.json"
        ),
    )
    monkeypatch.setattr(contract, "_production_artifact_bindings", dict)
    monkeypatch.setattr(contract, "startup_paths", lambda attempt_root: {})
    monkeypatch.setattr(
        contract,
        "exact_controller_command",
        lambda *args, **kwargs: ["locked-controller"],
    )
    monkeypatch.setattr(contract, "exact_controller_environment", lambda *args: {})
    roots = {
        name: tmp_path / "formal" / name
        for name in ("checkpoint", "worker", "log", "output")
    }
    monkeypatch.setattr(contract, "formal_roots", lambda: roots)
    bootstrap_identity = {"pid": 123, "create_time_ns": 456}
    authority_path = attempt / "authority.json"
    dynamic = {
        "schema": "rq2_public_grid_highs_formal_dynamic_activation_authority_v5",
        "version": 5,
        "status": "PRODUCTION_ONE_SHOT_AUTHORITY",
        "preflight": {
            "path": str(attempt / "preflight.json"),
            "sha256": contract.sha256_file(attempt / "preflight.json"),
        },
        "preflight_authority_mapping": preflight_mapping,
        "preflight_authority_mapping_sha256": contract.canonical_sha256(
            preflight_mapping
        ),
        "execution_closure": {
            "path": str(closure_path),
            "sha256": contract.sha256_file(closure_path),
            "members_sha256": closure["members_sha256"],
            "expected_hashes_verified": True,
        },
        "artifact_bindings": {},
        "one_shot": lease,
        "bootstrap_identity": bootstrap_identity,
        "startup_paths": {},
        "exact_command": ["locked-controller"],
        "exact_cwd": str(contract.ROOT),
        "exact_environment": {},
        "exact_environment_sha256": contract.canonical_sha256({}),
        "formal_roots": {name: str(path.resolve()) for name, path in roots.items()},
        "preseal_startup_probe": False,
        "fault_phase": None,
        "fault_type": None,
        "starts_from_block_zero": True,
        "resume_allowed": False,
        "formal_execution_authorized": True,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    contract.persist_json_stable(authority_path, dynamic)
    started = time.monotonic()
    assert contract.validate_dynamic_authority(authority_path) == dynamic
    elapsed = time.monotonic() - started
    assert calls == 1
    assert elapsed < 30.0
    assert preflight["formal_controller_spawned"] is False


def test_selected_preseal_audit_commits_six_nonself_hashes() -> None:
    audit = json.loads(contract.PRE_SEAL_AUDIT.read_text(encoding="utf-8"))
    sealed = contract.load_config()["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    binding_name = (
        "exact_nonself_sealed_sha256" if sealed else "exact_nonself_draft_sha256"
    )
    bindings = audit[binding_name]
    expected = {
        contract.CONFIG.relative_to(contract.ROOT).as_posix(),
        contract.FORMAL_CONFIG.relative_to(contract.ROOT).as_posix(),
        Path(bootstrap.__file__).resolve().relative_to(contract.ROOT).as_posix(),
        Path(contract.__file__).resolve().relative_to(contract.ROOT).as_posix(),
        Path(controller.__file__).resolve().relative_to(contract.ROOT).as_posix(),
        Path(__file__).resolve().relative_to(contract.ROOT).as_posix(),
    }
    assert set(bindings) == expected
    assert all(
        contract.sha256_file(contract.ROOT / path) == digest
        for path, digest in bindings.items()
    )
    assert audit["self_sha256_binding"] == "external_only_non_circular"
