from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from experiments import (
    bootstrap_rq2_public_grid_highs_formal_activation_successor_v2 as bootstrap,
)
from experiments import rq2_public_grid_highs_formal_activation_contract_v2 as contract
from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_formal_v3 as controller,
)


def _sleeping_child() -> subprocess.Popen[str]:
    return subprocess.Popen(
        [sys.executable, "-B", "-c", "import time; time.sleep(30)"],
        cwd=contract.ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )


def _binding_files(tmp_path: Path) -> dict[str, dict[str, str]]:
    bindings: dict[str, dict[str, str]] = {}
    for name in (
        "formal_config",
        "controller",
        "outer",
        "dynamic_authority",
        "preflight",
        "activation_receipt",
        "consumed_authority",
    ):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps({"name": name}) + "\n", encoding="utf-8")
        bindings[name] = {"path": str(path), "sha256": contract.sha256_file(path)}
    return bindings


def _handshake(
    tmp_path: Path,
    *,
    process_identity: dict[str, int],
    bootstrap_identity: dict[str, int],
) -> tuple[dict[str, object], dict[str, dict[str, str]], list[str], dict[str, str]]:
    bindings = _binding_files(tmp_path)
    command = ["python", "-B", "-m", "formal_controller"]
    environment = {"PYTHONHASHSEED": "0"}
    value = contract.build_startup_handshake(
        controller_identity=process_identity,
        bootstrap_identity=bootstrap_identity,
        bindings=bindings,
        command=command,
        cwd=str(contract.ROOT),
        environment=environment,
    )
    return value, bindings, command, environment


def test_v1_is_sealed_rework_and_v2_remains_closed() -> None:
    report = contract.validate_static_authority(require_activation_review=False)
    assert report["validation_passed"] is True
    assert report["v1_review_verdict"] == "REWORK"
    assert report["formal_activation_review_receipt_present"] is False
    assert report["formal_execution_authorized"] is False
    assert report["solver_calls"] == 0
    assert report["formal_root_writes"] == 0


def test_exact_process_pair_rejects_create_time_mismatch() -> None:
    child = _sleeping_child()
    identity = bootstrap._observe_process_identity(child)
    try:
        bootstrap._assert_process_identity(child, identity)
        wrong = {**identity, "create_time_ns": identity["create_time_ns"] + 100}
        with pytest.raises(contract.FormalActivationRejected, match="create-time"):
            bootstrap._assert_process_identity(child, wrong)
    finally:
        bootstrap._terminate_owned(child, identity)


def test_normal_startup_handshake_and_ack_use_live_exact_pair(tmp_path: Path) -> None:
    child = _sleeping_child()
    child_identity = bootstrap._observe_process_identity(child)
    bootstrap_identity = bootstrap._current_process_identity()
    handshake, bindings, command, environment = _handshake(
        tmp_path,
        process_identity=child_identity,
        bootstrap_identity=bootstrap_identity,
    )
    handshake_path = tmp_path / "startup_handshake.json"
    try:
        contract.persist_json_stable(handshake_path, handshake)
        observed = bootstrap._wait_for_controller_handshake(
            child,
            controller_identity=child_identity,
            bootstrap_identity=bootstrap_identity,
            handshake_path=handshake_path,
            bindings=bindings,
            command=command,
            cwd=str(contract.ROOT),
            environment=environment,
            timeout_seconds=1.0,
        )
        ack_path = tmp_path / "startup_ack.json"
        ack = bootstrap._publish_startup_ack(
            ack_path,
            handshake=observed,
            controller_identity=child_identity,
            bootstrap_identity=bootstrap_identity,
        )
        validated = controller._validate_startup_ack(
            ack_path,
            handshake=observed,
            controller_identity=child_identity,
            bootstrap_identity=bootstrap_identity,
        )
        assert validated == ack
        assert child.poll() is None
        assert all(not path.exists() for path in contract.formal_roots().values())
    finally:
        bootstrap._terminate_owned(child, child_identity)


def test_immediate_exit_is_launch_incomplete_not_spawned(tmp_path: Path) -> None:
    child = subprocess.Popen(
        [sys.executable, "-B", "-c", "pass"],
        cwd=contract.ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    child.wait(timeout=10)
    identity = {"pid": child.pid, "create_time_ns": 1}
    with pytest.raises(contract.FormalActivationRejected, match="exited"):
        bootstrap._wait_for_controller_handshake(
            child,
            controller_identity=identity,
            bootstrap_identity=bootstrap._current_process_identity(),
            handshake_path=tmp_path / "absent.json",
            bindings={},
            command=[],
            cwd=str(contract.ROOT),
            environment={},
            timeout_seconds=0.1,
        )
    outcome = bootstrap._record_launch_incomplete(
        tmp_path,
        phase="startup_handshake",
        reason="controller_exited_before_handshake",
        controller_identity=identity,
        returncode=child.returncode,
        termination={"attempted": False, "reason": "already_exited"},
    )
    assert outcome["formal_controller_spawned"] is False
    assert outcome["formal_started"] is False
    assert outcome["mathematical_infeasibility_inferred"] is False


def test_handshake_timeout_terminates_exact_owned_child_and_persists(
    tmp_path: Path,
) -> None:
    child = _sleeping_child()
    identity = bootstrap._observe_process_identity(child)
    try:
        with pytest.raises(contract.FormalActivationRejected, match="timed out"):
            bootstrap._wait_for_controller_handshake(
                child,
                controller_identity=identity,
                bootstrap_identity=bootstrap._current_process_identity(),
                handshake_path=tmp_path / "absent.json",
                bindings={},
                command=[],
                cwd=str(contract.ROOT),
                environment={},
                timeout_seconds=0.05,
            )
    finally:
        termination = bootstrap._terminate_owned(child, identity)
    outcome = bootstrap._record_launch_incomplete(
        tmp_path,
        phase="startup_handshake",
        reason="startup_handshake_timeout",
        controller_identity=identity,
        returncode=child.returncode,
        termination=termination,
    )
    assert child.poll() is not None
    assert outcome["one_shot_authority_remains_consumed"] is True
    assert outcome["retry_allowed"] is False
    assert outcome["resume_allowed"] is False


def test_handshake_tamper_rejects_before_ack_or_formal_roots(tmp_path: Path) -> None:
    child = _sleeping_child()
    identity = bootstrap._observe_process_identity(child)
    bootstrap_identity = bootstrap._current_process_identity()
    handshake, bindings, command, environment = _handshake(
        tmp_path,
        process_identity=identity,
        bootstrap_identity=bootstrap_identity,
    )
    handshake["bindings"]["outer"]["sha256"] = "0" * 64
    path = tmp_path / "startup_handshake.json"
    try:
        contract.persist_json_stable(path, handshake)
        with pytest.raises(contract.FormalActivationRejected, match="binding"):
            bootstrap._wait_for_controller_handshake(
                child,
                controller_identity=identity,
                bootstrap_identity=bootstrap_identity,
                handshake_path=path,
                bindings=bindings,
                command=command,
                cwd=str(contract.ROOT),
                environment=environment,
                timeout_seconds=1.0,
            )
        assert all(not root.exists() for root in contract.formal_roots().values())
    finally:
        bootstrap._terminate_owned(child, identity)


def test_controller_startup_gate_precedes_science_and_root_creation() -> None:
    source = Path(controller.__file__).read_text(encoding="utf-8")
    run_body = source[source.index("def run(") : source.index("def main(")]
    assert run_body.index("_complete_startup_handshake(") < run_body.index(
        "predecessor._stage_context("
    )
    assert run_body.index("_complete_startup_handshake(") < run_body.index(
        ".mkdir("
    )
