"""Focused fail-closed tests for execution-controller successor v3."""

from __future__ import annotations

import importlib
import inspect
import json
import os
import subprocess
from pathlib import Path

import pytest

from tests import test_rq2_public_grid_two_block_pilot_candidate_v4 as v4_fixtures

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3.json"
REAL_0008 = ROOT / (
    "results/checkpoints/rts_gmlc_public_grid_need_dispatch_v4_gurobi/"
    "holdout_s20260822_0008.json"
)


@pytest.fixture(scope="module")
def contract():
    return importlib.import_module(
        "experiments.rq2_public_grid_execution_runtime_contract_v3"
    )


@pytest.fixture(scope="module")
def controller():
    return importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
    )


@pytest.fixture(scope="module")
def worker():
    return importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
    )


def _config() -> dict:
    return json.loads(CONFIG.read_bytes())


def _real_0008() -> dict:
    return json.loads(REAL_0008.read_bytes())


def _accounting_payload(*, active: int, e0: int = 0) -> dict:
    if not 0 <= e0 <= active <= 24:
        raise ValueError("invalid synthetic accounting inventory")
    outcomes = []
    for index in range(24):
        if index < e0:
            outcomes.append(
                {
                    "state": "exogenous_grid_infeasibility",
                    "primary": {
                        "event_id": f"event-{index}",
                        "termination_condition": "infeasible",
                        "solver_status": "warning",
                    },
                    "primary_certificate": {"model_variables": 1},
                    "zero_dc_confirmation": {
                        "event_id": f"event-{index}",
                        "termination_condition": "infeasible",
                        "solver_status": "warning",
                    },
                    "zero_dc_confirmation_certificate": {"model_variables": 1},
                }
            )
        elif index < active:
            outcomes.append(
                {
                    "state": "finite_grid_need",
                    "primary": {
                        "event_id": f"event-{index}",
                        "termination_condition": "optimal",
                        "solver_status": "ok",
                    },
                    "primary_certificate": {"model_variables": 1},
                    "zero_dc_confirmation": None,
                    "zero_dc_confirmation_certificate": None,
                }
            )
        else:
            outcomes.append(
                {
                    "state": "finite_grid_need",
                    "primary": {
                        "event_id": None,
                        "termination_condition": "not_applicable_no_active_outage",
                        "solver_status": "not_applicable",
                    },
                    "primary_certificate": {"model_variables": 0},
                    "zero_dc_confirmation": None,
                    "zero_dc_confirmation_certificate": None,
                }
            )
    return {
        "baseline_audit": (
            {
                "accepted": True,
                "termination_condition": "optimal",
                "solver_status": "ok",
            }
            if active
            else {
                "accepted": True,
                "termination_condition": "not_applicable_no_active_outage",
            }
        ),
        "outcomes": outcomes,
    }


def test_v2_escalate_receipt_binds_exact_outer() -> None:
    receipt = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_escalate_v2.json"
        ).read_bytes()
    )
    assert receipt["verdict"] == "ESCALATE"
    assert receipt["reviewed_outer"]["sha256"] == (
        "9c2822fef43e34743e12f79fb4fd3545812a2cb797bb74d50ed132be15bf44c0"
    )
    assert len(receipt["findings"]) == 3
    assert receipt["effect"]["v2_execution_authorized"] is False


def test_full_recursive_live_closure_and_named_function_sources(contract) -> None:
    trace: list[tuple[str, str]] = []
    observed = contract.verify_full_live_closure(
        ROOT, _config(), trace=lambda path, digest: trace.append((path, digest))
    )
    traced = {path for path, _digest in trace}
    assert set(observed) == traced
    for path in (
        "experiments/run_rq2_public_grid_two_block_pilot_activation_transport_v5.py",
        "experiments/worker_rq2_public_grid_two_block_pilot_activation_transport_v5.py",
        "experiments/run_rq2_public_grid_two_block_pilot_candidate_v7.py",
        "experiments/run_rq2_public_grid_two_block_pilot_candidate_v4.py",
        "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1.py",
    ):
        assert path in traced


@pytest.mark.parametrize(
    "stage",
    [
        "bootstrap_pre_controller_import",
        "worker_pre_loader",
        "worker_post_solve_pre_validator",
        "worker_post_validator_pre_write",
        "worker_post_write_pre_ack",
        "controller_post_child_pre_accept",
        "controller_post_block2_pre_publish",
        "controller_post_publish",
    ],
)
def test_stage_fault_runs_full_inventory_then_fails_exact_stage(contract, stage: str) -> None:
    verifier = contract.register_test_stage_fault(stage)
    with pytest.raises(contract.LiveClosureDrift, match=stage):
        verifier.verify(stage)
    assert verifier.audit["full_verifications"] == 1
    assert verifier.audit["last_inventory_count"] == len(
        contract.full_inventory_paths(ROOT, _config())
    )
    with pytest.raises(contract.LiveClosureDrift, match="replayed"):
        verifier.verify(stage)


@pytest.mark.parametrize(
    ("active", "e0", "expected"),
    [
        (0, 0, (0, 0, 0, 0)),
        (1, 0, (1, 1, 0, 2)),
        (1, 1, (1, 1, 1, 3)),
        (3, 3, (1, 3, 3, 7)),
    ],
)
def test_status_pair_accounting_exact(contract, active: int, e0: int, expected) -> None:
    observed = contract.solver_call_accounting(
        _accounting_payload(active=active, e0=e0)
    )
    assert tuple(observed.values()) == expected


def test_real_gurobi_0008_payload_validates_and_counts_three(contract) -> None:
    verifier = contract.StageAwareClosureVerifier.production()
    integration = contract.load_sealed_actual_integration(verifier)
    validated = integration.validate_scientific_payload(
        _real_0008(), "holdout_s20260822_0008"
    )
    assert validated["all_hours_resolved"] is True
    assert contract.solver_call_accounting(validated)["solver_calls"] == 3


@pytest.mark.parametrize(
    ("target", "field", "value"),
    [
        ("baseline", "solver_status", "warning"),
        ("primary", "solver_status", "unknown"),
        ("primary", "solver_status", "ok"),
        ("primary", "solver_status", None),
        ("primary", "termination_condition", "unknown"),
        ("zero", "solver_status", "ok"),
        ("zero", "termination_condition", "optimal"),
    ],
)
def test_status_pair_and_applicability_forgery_rejected(
    contract, target: str, field: str, value: object
) -> None:
    payload = _accounting_payload(active=1, e0=1)
    if target == "baseline":
        payload["baseline_audit"][field] = value
    elif target == "primary":
        payload["outcomes"][0]["primary"][field] = value
    else:
        payload["outcomes"][0]["zero_dc_confirmation"][field] = value
    with pytest.raises(contract.RuntimeContractRejected):
        contract.solver_call_accounting(payload)


def test_no_event_status_field_and_active_not_applicable_are_rejected(contract) -> None:
    no_event = _accounting_payload(active=0)
    no_event["baseline_audit"]["solver_status"] = "not_applicable"
    with pytest.raises(contract.RuntimeContractRejected):
        contract.solver_call_accounting(no_event)
    active = _accounting_payload(active=1)
    active["outcomes"][0]["primary"].update(
        {
            "termination_condition": "not_applicable_no_active_outage",
            "solver_status": "not_applicable",
        }
    )
    with pytest.raises(contract.RuntimeContractRejected):
        contract.solver_call_accounting(active)


def test_sealed_integration_uses_exact_functions_and_no_caller_lambdas(
    contract, controller
) -> None:
    integration = contract.load_sealed_actual_integration(
        contract.StageAwareClosureVerifier.production()
    )
    assert integration.verify_function_identities()["verified"] is True
    assert "register_zero_solver_live_orchestration_seam" not in vars(controller)
    assert "validate_payload" not in inspect.signature(
        controller.publish_with_stage_gates
    ).parameters
    assert "publisher" not in inspect.signature(
        controller.publish_with_stage_gates
    ).parameters


@pytest.mark.parametrize(
    ("stage", "expect_payload", "expect_receipt", "expect_ack"),
    [
        ("worker_post_solve_pre_validator", False, False, False),
        ("worker_post_validator_pre_write", False, False, False),
        ("worker_post_write_pre_ack", True, True, False),
    ],
)
def test_worker_stage_drift_never_emits_accepted_ack(
    contract,
    worker,
    tmp_path: Path,
    stage: str,
    expect_payload: bool,
    expect_receipt: bool,
    expect_ack: bool,
) -> None:
    verifier = contract.register_test_stage_fault(stage)
    envelope = worker.build_test_envelope(
        block_id="holdout_s20260822_0008",
        output_root=tmp_path,
    )
    with pytest.raises(contract.LiveClosureDrift, match=stage):
        worker.finalize_existing_scientific_payload_for_test(
            envelope=envelope,
            payload=_real_0008(),
            verifier=verifier,
        )
    assert Path(envelope["worker_payload_path"]).exists() is expect_payload
    assert Path(envelope["attempt_receipt_path"]).exists() is expect_receipt
    assert (tmp_path / "accepted_ack.json").exists() is expect_ack


def _actual_publication_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, contract):
    integration = contract.load_sealed_actual_integration(
        contract.StageAwareClosureVerifier.production()
    )
    ledger = v4_fixtures._complete_ledger(tmp_path / "sources", monkeypatch)
    config = integration.publication_config()
    controller_receipt = integration.build_controller_receipt(config, ledger)
    return integration, ledger, config, controller_receipt


def test_controller_post_child_drift_prevents_ledger_accept(
    contract, controller, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from experiments import run_rq2_public_grid_two_block_pilot_candidate_v4 as v4

    source = v4_fixtures._complete_ledger(tmp_path, monkeypatch).records[0]
    ledger = v4.ControllerLedger()
    verifier = contract.register_test_stage_fault(
        "controller_post_child_pre_accept"
    )
    with pytest.raises(contract.LiveClosureDrift):
        controller.accept_after_child(source, ledger=ledger, verifier=verifier)
    assert ledger.records == ()


def test_actual_validator_ledger_publisher_and_reconcile_tmp_only(
    contract, controller, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    integration, ledger, config, receipt = _actual_publication_case(
        tmp_path, monkeypatch, contract
    )
    outcome = controller.publish_with_stage_gates(
        staging=tmp_path / "staging",
        target=tmp_path / "result",
        success=tmp_path / "success",
        terminal=tmp_path / "terminal",
        publication_config=config,
        controller_receipt=receipt,
        ledger=ledger,
        verifier=contract.StageAwareClosureVerifier.production(),
    )
    assert outcome["classification"] == "committed_success"
    recovered = integration.load_verified_success(
        target=tmp_path / "result",
        success=tmp_path / "success",
        terminal=tmp_path / "terminal",
        config=config,
        controller=receipt,
        ledger=ledger,
    )
    assert recovered["published"] is True
    assert not os.path.lexists(tmp_path / "terminal")


def test_prepublish_closure_drift_never_calls_actual_publisher(
    contract, controller, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _integration, ledger, config, receipt = _actual_publication_case(
        tmp_path, monkeypatch, contract
    )
    verifier = contract.register_test_stage_fault(
        "controller_post_block2_pre_publish"
    )
    with pytest.raises(contract.LiveClosureDrift):
        controller.publish_with_stage_gates(
            staging=tmp_path / "staging",
            target=tmp_path / "result",
            success=tmp_path / "success",
            terminal=tmp_path / "terminal",
            publication_config=config,
            controller_receipt=receipt,
            ledger=ledger,
            verifier=verifier,
        )
    assert not os.path.lexists(tmp_path / "result")
    assert not os.path.lexists(tmp_path / "success")


def test_postpublish_closure_drift_is_indeterminate_without_deletion(
    contract, controller, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _integration, ledger, config, receipt = _actual_publication_case(
        tmp_path, monkeypatch, contract
    )
    outcome = controller.publish_with_stage_gates(
        staging=tmp_path / "staging",
        target=tmp_path / "result",
        success=tmp_path / "success",
        terminal=tmp_path / "terminal",
        publication_config=config,
        controller_receipt=receipt,
        ledger=ledger,
        verifier=contract.register_test_stage_fault("controller_post_publish"),
    )
    assert outcome["classification"] == "commit_indeterminate"
    assert outcome["published"] is False
    assert outcome["claim"] is False
    assert outcome["formal_execution_ready"] is False
    assert outcome["ledger_digest"] == ledger.digest
    assert (tmp_path / "result").is_dir()
    assert (tmp_path / "success").is_dir()
    assert not os.path.lexists(tmp_path / "terminal")


def test_corrupt_actual_evidence_fails_before_publication(
    contract, controller, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _integration, ledger, config, receipt = _actual_publication_case(
        tmp_path, monkeypatch, contract
    )
    ledger.records[0].source_payload_path.write_bytes(b"{}\n")
    with pytest.raises(ValueError):
        controller.publish_with_stage_gates(
            staging=tmp_path / "staging",
            target=tmp_path / "result",
            success=tmp_path / "success",
            terminal=tmp_path / "terminal",
            publication_config=config,
            controller_receipt=receipt,
            ledger=ledger,
            verifier=contract.StageAwareClosureVerifier.production(),
        )
    assert not os.path.lexists(tmp_path / "success")


def test_actual_publisher_race_is_indeterminate(
    contract, controller, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _integration, ledger, config, receipt = _actual_publication_case(
        tmp_path, monkeypatch, contract
    )
    with pytest.raises(Exception) as caught:
        controller.publish_with_stage_gates(
            staging=tmp_path / "staging",
            target=tmp_path / "result",
            success=tmp_path / "success",
            terminal=tmp_path / "terminal",
            publication_config=config,
            controller_receipt=receipt,
            ledger=ledger,
            verifier=contract.StageAwareClosureVerifier.production(),
            registered_test_race="terminal_after_commit",
        )
    assert getattr(caught.value, "outcome", {}).get("classification") == (
        "commit_indeterminate"
    )
    assert getattr(caught.value, "outcome", {}).get("published") is False


def test_v3_review_closed_roots_absent() -> None:
    config = _config()
    assert config["gates"] == {
        "successor_v3_independent_review_passed": False,
        "fixed_execution_review_receipt_present": False,
        "execution_ready": False,
        "pilot_executed": False,
        "formal_execution_ready": False,
        "user_formal_run_authorized": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    for relative in config["paths"].values():
        assert not os.path.lexists(ROOT / relative)


def test_canonical_bootstrap_validate_only_is_zero_import_write_boundary() -> None:
    config = _config()
    completed = subprocess.run(
        [
            config["runtime"]["locked_python_executable"],
            "-B",
            "-m",
            config["successor_identity"]["bootstrap_module"],
            "--validate-only",
        ],
        cwd=ROOT,
        env=config["runtime"]["sanitized_environment"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    outcome = json.loads(completed.stdout)
    assert outcome == {
        "dependency_closure_verified": True,
        "execution_ready": False,
        "execution_review_present": False,
        "formal_writes": 0,
        "loader_calls": 0,
        "result_writes": 0,
        "solver_calls": 0,
        "validation_passed": True,
        "workers": 0,
    }


def test_canonical_bootstrap_execute_missing_review_fails_before_controller() -> None:
    config = _config()
    completed = subprocess.run(
        [
            config["runtime"]["locked_python_executable"],
            "-B",
            "-m",
            config["successor_identity"]["bootstrap_module"],
            "--execute",
        ],
        cwd=ROOT,
        env=config["runtime"]["sanitized_environment"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    assert "absent before controller import" in completed.stderr
    for relative in config["paths"].values():
        assert not os.path.lexists(ROOT / relative)
