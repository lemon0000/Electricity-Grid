from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from typing import Any

import pytest

from experiments import (
    bootstrap_rq2_public_grid_highs_formal_activation_successor_v3 as bootstrap,
)
from experiments import rq2_public_grid_highs_formal_activation_contract_v3 as contract
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v4 as controller,
)


def _binding_files(tmp_path: Path) -> dict[str, dict[str, str]]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    bindings: dict[str, dict[str, str]] = {}
    for name in sorted(contract.STARTUP_BINDING_NAMES):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({"name": name}) + "\n", encoding="utf-8")
        bindings[name] = {"path": str(path), "sha256": contract.sha256_file(path)}
    return bindings


def _wait_for_file(path: Path, timeout: float = 5.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout
    while not path.is_file():
        if time.monotonic() >= deadline:
            raise AssertionError(f"timed out waiting for {path}")
        time.sleep(0.01)
    value = json.loads(contract._read_stable(path))
    assert isinstance(value, dict)
    return value


def _startup_probe(spec_path: Path) -> int:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    controller_identity = bootstrap._current_process_identity()
    bootstrap_identity = contract._process_identity(
        spec["bootstrap_identity"], "bootstrap identity"
    )
    bindings = {
        name: dict(value) for name, value in spec["bindings"].items()
    }
    command = [str(item) for item in spec["command"]]
    attempt = Path(spec["attempt_root"])
    handshake = contract.build_startup_handshake(
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        bindings=bindings,
        command=command,
        cwd=str(contract.ROOT),
        environment={"PYTHONHASHSEED": "0"},
    )
    contract.persist_json_stable(attempt / "startup_handshake.json", handshake)
    ack = _wait_for_file(attempt / "startup_ack.json")
    contract.validate_startup_ack(
        ack,
        handshake=handshake,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    closure = contract.verify_execution_closure()
    ready = contract.build_startup_ready(
        handshake=handshake,
        ack=ack,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        authority_mapping_sha256="a" * 64,
        execution_closure_sha256=str(closure["members_sha256"]),
    )
    if spec.get("tamper_ready") is True:
        ready["execution_closure_sha256"] = "0" * 64
    contract.persist_json_stable(attempt / "startup_ready.json", ready)
    release = _wait_for_file(attempt / "science_release.json")
    contract.validate_science_release(
        release,
        ready=ready,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
    )
    root = spec.get("create_root_after_release")
    if root:
        created = Path(str(root))
        created.mkdir(parents=True, exist_ok=False)
        (created / "observed.json").write_text("{}\n", encoding="utf-8")
    if spec.get("exit_after_release") is True:
        return 7
    accepted = contract.build_science_release_acceptance(
        release=release,
        controller_identity=controller_identity,
        bootstrap_identity=bootstrap_identity,
        execution_closure_sha256=str(closure["members_sha256"]),
    )
    contract.persist_json_stable(
        attempt / "science_release_accepted.json", accepted
    )
    time.sleep(1.0)
    return 0


def _spawn_probe(
    tmp_path: Path,
    *,
    tamper_ready: bool = False,
    exit_after_release: bool = False,
    create_root_after_release: Path | None = None,
) -> tuple[Any, dict[str, int], dict[str, int], dict[str, Any]]:
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    bindings = _binding_files(tmp_path / "bindings")
    spec_path = tmp_path / "probe.json"
    command = [
        sys.executable,
        "-B",
        str(Path(__file__).resolve()),
        "--startup-probe",
        str(spec_path),
    ]
    bootstrap_identity = bootstrap._current_process_identity()
    spec = {
        "attempt_root": str(attempt),
        "bootstrap_identity": bootstrap_identity,
        "bindings": bindings,
        "command": command,
        "tamper_ready": tamper_ready,
        "exit_after_release": exit_after_release,
        "create_root_after_release": (
            str(create_root_after_release)
            if create_root_after_release is not None
            else None
        ),
    }
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    process = bootstrap.subprocess.Popen(
        command,
        cwd=contract.ROOT,
        stdin=bootstrap.subprocess.DEVNULL,
        stdout=bootstrap.subprocess.DEVNULL,
        stderr=bootstrap.subprocess.DEVNULL,
        env={**os.environ, "PYTHONPATH": str(contract.ROOT)},
    )
    identity = bootstrap._observe_process_identity(process)
    observed = bootstrap._wait_for_controller_handshake(
        process,
        controller_identity=identity,
        bootstrap_identity=bootstrap_identity,
        handshake_path=attempt / "startup_handshake.json",
        bindings=bindings,
        command=command,
        cwd=str(contract.ROOT),
        environment={"PYTHONHASHSEED": "0"},
        timeout_seconds=5.0,
    )
    return process, identity, bootstrap_identity, observed


def _publish_ack_and_wait_ready(
    tmp_path: Path,
    process: Any,
    identity: dict[str, int],
    bootstrap_identity: dict[str, int],
    handshake: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any]]:
    attempt = tmp_path / "attempt"
    ack = bootstrap._publish_startup_ack(
        attempt / "startup_ack.json",
        handshake=handshake,
        controller_identity=identity,
        bootstrap_identity=bootstrap_identity,
    )
    ready = _wait_for_file(attempt / "startup_ready.json")
    bootstrap._assert_process_identity(process, identity)
    return ack, ready


def test_v3_successor_imports_and_closure_are_exact() -> None:
    assert bootstrap.contract is contract
    assert controller.authority is contract
    closure = contract.verify_execution_closure()
    assert closure["member_count"] == 50
    manifest = json.loads(contract.CLOSURE.read_bytes())
    required = {
        "experiments/rq2_public_grid_two_block_pilot_vnext_execution_contract_v8.py",
        "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v4.py",
        "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v5.py",
        "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1.py",
        "experiments/run_rts_gmlc_public_grid_need_dispatch_v4.py",
        "src/evaluation/execution_machine.py",
        "src/evaluation/flexibility_envelope.py",
        "src/evaluation/rq2_provenance_v3.py",
        "src/grid/chronological_dispatch.py",
        "src/grid/rts_gmlc.py",
        "src/grid/rts_gmlc_grid_need.py",
        "src/grid/rts_gmlc_grid_need_successor.py",
        "src/grid/rts_gmlc_scuc.py",
        "src/grid/rts_gmlc_scuc_solver_successor.py",
        "src/scenarios/rts_gmlc_n1_chronology.py",
        "src/solvers/rq2_solver_adapter.py",
    }
    assert required <= set(manifest["members"])


def test_closure_drift_rejects_expected_hash_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    original = contract.sha256_file
    target = (
        contract.ROOT
        / "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v5.py"
    )

    def drifted(path: Path) -> str:
        return "0" * 64 if path.resolve() == target.resolve() else original(path)

    monkeypatch.setattr(contract, "sha256_file", drifted)
    with pytest.raises(contract.FormalActivationRejected, match="closure"):
        contract.verify_execution_closure()


def test_review_pass_does_not_authorize_execution() -> None:
    source = Path(contract.__file__).read_text(encoding="utf-8")
    review_body = source[
        source.index("def require_activation_review_pass(") : source.index(
            "def require_user_formal_run_authority("
        )
    ]
    assert '"formal_execution_authorized": False' in review_body
    assert not contract.ACTIVATION_REVIEW_PASS.exists()
    assert not contract.USER_FORMAL_RUN_AUTHORITY.exists()


def test_negative_execute_rejects_user_authority_before_any_mutation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"clean": 0, "preflight": 0, "spawn": 0, "consume": 0}
    monkeypatch.setattr(
        bootstrap,
        "_require_clean_start",
        lambda: calls.__setitem__("clean", calls["clean"] + 1),
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
    monkeypatch.setattr(
        bootstrap,
        "_consume_one_shot_authority",
        lambda value: calls.__setitem__("consume", calls["consume"] + 1),
    )
    with pytest.raises(contract.FormalActivationRejected, match="user formal-run"):
        bootstrap.execute()
    assert calls == {"clean": 0, "preflight": 0, "spawn": 0, "consume": 0}
    assert not contract.activation_audit_root().exists()
    assert all(not path.exists() for path in contract.formal_roots().values())


def test_real_four_stage_startup_e2e_has_exact_pid_create_time(tmp_path: Path) -> None:
    process, identity, bootstrap_identity, handshake = _spawn_probe(tmp_path)
    try:
        ack, ready = _publish_ack_and_wait_ready(
            tmp_path, process, identity, bootstrap_identity, handshake
        )
        closure = contract.verify_execution_closure()
        validated_ready = contract.validate_startup_ready(
            ready,
            handshake=handshake,
            ack=ack,
            controller_identity=identity,
            bootstrap_identity=bootstrap_identity,
            authority_mapping_sha256="a" * 64,
            execution_closure_sha256=str(closure["members_sha256"]),
        )
        release = contract.build_science_release(
            ready=validated_ready,
            controller_identity=identity,
            bootstrap_identity=bootstrap_identity,
        )
        attempt = tmp_path / "attempt"
        contract.persist_json_stable(attempt / "science_release.json", release)
        accepted = bootstrap._wait_for_release_acceptance(
            process,
            controller_identity=identity,
            bootstrap_identity=bootstrap_identity,
            path=attempt / "science_release_accepted.json",
            release=release,
            timeout_seconds=5.0,
        )
        assert accepted["release_accepted"] is True
        assert accepted["controller_identity"] == identity
        assert identity["create_time_ns"] > 0
    finally:
        process.wait(timeout=5)


def test_ack_tamper_is_rejected_before_ready(tmp_path: Path) -> None:
    process, identity, bootstrap_identity, handshake = _spawn_probe(tmp_path)
    try:
        ack = contract.build_startup_ack(
            handshake=handshake,
            controller_identity=identity,
            bootstrap_identity=bootstrap_identity,
        )
        ack["startup_authority_accepted"] = False
        with pytest.raises(contract.FormalActivationRejected, match="ack"):
            contract.validate_startup_ack(
                ack,
                handshake=handshake,
                controller_identity=identity,
                bootstrap_identity=bootstrap_identity,
            )
        contract.persist_json_stable(tmp_path / "attempt/startup_ack.json", ack)
        process.wait(timeout=5)
        assert process.returncode != 0
        assert not (tmp_path / "attempt/startup_ready.json").exists()
    finally:
        if process.poll() is None:
            bootstrap._terminate_owned(process, identity)


def test_ready_tamper_is_rejected_before_science_release(tmp_path: Path) -> None:
    process, identity, bootstrap_identity, handshake = _spawn_probe(
        tmp_path, tamper_ready=True
    )
    try:
        ack, ready = _publish_ack_and_wait_ready(
            tmp_path, process, identity, bootstrap_identity, handshake
        )
        closure = contract.verify_execution_closure()
        with pytest.raises(contract.FormalActivationRejected, match="ready"):
            contract.validate_startup_ready(
                ready,
                handshake=handshake,
                ack=ack,
                controller_identity=identity,
                bootstrap_identity=bootstrap_identity,
                authority_mapping_sha256="a" * 64,
                execution_closure_sha256=str(closure["members_sha256"]),
            )
        assert not (tmp_path / "attempt/science_release.json").exists()
    finally:
        bootstrap._terminate_owned(process, identity)


def test_release_immediate_exit_is_post_release_unresolved(tmp_path: Path) -> None:
    process, identity, bootstrap_identity, handshake = _spawn_probe(
        tmp_path, exit_after_release=True
    )
    ack, ready = _publish_ack_and_wait_ready(
        tmp_path, process, identity, bootstrap_identity, handshake
    )
    closure = contract.verify_execution_closure()
    ready = contract.validate_startup_ready(
        ready,
        handshake=handshake,
        ack=ack,
        controller_identity=identity,
        bootstrap_identity=bootstrap_identity,
        authority_mapping_sha256="a" * 64,
        execution_closure_sha256=str(closure["members_sha256"]),
    )
    release = contract.build_science_release(
        ready=ready,
        controller_identity=identity,
        bootstrap_identity=bootstrap_identity,
    )
    attempt = tmp_path / "attempt"
    release_path = attempt / "science_release.json"
    contract.persist_json_stable(release_path, release)
    process.wait(timeout=5)
    with pytest.raises(contract.FormalActivationRejected, match="exited"):
        bootstrap._wait_for_release_acceptance(
            process,
            controller_identity=identity,
            bootstrap_identity=bootstrap_identity,
            path=attempt / "science_release_accepted.json",
            release=release,
            timeout_seconds=0.1,
        )
    roots = {name: tmp_path / name for name in contract.formal_roots()}
    outcome = bootstrap._record_post_release_unresolved(
        attempt,
        reason="controller_exit_after_release",
        controller_identity=identity,
        returncode=process.returncode,
        termination={"attempted": False, "reason": "already_exited"},
        release_path=release_path,
        release_acceptance=None,
        formal_roots_override=roots,
    )
    assert outcome["release_persisted"] is True
    assert outcome["release_acceptance_proven"] is False
    assert outcome["formal_started"] is None
    assert outcome["formal_start_status"] == "unresolved_after_science_release"
    assert outcome["mathematical_infeasibility_inferred"] is False
    assert not (attempt / "launch_incomplete.json").exists()


def test_post_release_root_creation_is_observed_without_false_start_claim(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "checkpoint"
    process, identity, bootstrap_identity, handshake = _spawn_probe(
        tmp_path,
        exit_after_release=True,
        create_root_after_release=checkpoint,
    )
    ack, ready = _publish_ack_and_wait_ready(
        tmp_path, process, identity, bootstrap_identity, handshake
    )
    closure = contract.verify_execution_closure()
    ready = contract.validate_startup_ready(
        ready,
        handshake=handshake,
        ack=ack,
        controller_identity=identity,
        bootstrap_identity=bootstrap_identity,
        authority_mapping_sha256="a" * 64,
        execution_closure_sha256=str(closure["members_sha256"]),
    )
    release = contract.build_science_release(
        ready=ready,
        controller_identity=identity,
        bootstrap_identity=bootstrap_identity,
    )
    attempt = tmp_path / "attempt"
    release_path = attempt / "science_release.json"
    contract.persist_json_stable(release_path, release)
    process.wait(timeout=5)
    roots = {
        "checkpoint": checkpoint,
        "worker": tmp_path / "worker",
        "log": tmp_path / "log",
        "output": tmp_path / "output",
    }
    outcome = bootstrap._record_post_release_unresolved(
        attempt,
        reason="root_observed_after_release",
        controller_identity=identity,
        returncode=process.returncode,
        termination={"attempted": False, "reason": "already_exited"},
        release_path=release_path,
        release_acceptance=None,
        formal_roots_override=roots,
    )
    assert outcome["checkpoint_observation"]["exists"] is True
    assert outcome["checkpoint_observation"]["ordinary_file_count"] == 1
    assert outcome["formal_controller_spawned"] is True
    assert outcome["formal_started"] is None


def test_launch_incomplete_is_forbidden_after_release(tmp_path: Path) -> None:
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    (attempt / "science_release.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(contract.FormalActivationRejected, match="forbidden"):
        bootstrap._record_launch_incomplete(
            attempt,
            phase="post_release",
            reason="must_not_reclassify",
            controller_identity=None,
            returncode=None,
            termination={"attempted": False},
        )


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--startup-probe":
        raise SystemExit(2)
    raise SystemExit(_startup_probe(Path(sys.argv[2])))
