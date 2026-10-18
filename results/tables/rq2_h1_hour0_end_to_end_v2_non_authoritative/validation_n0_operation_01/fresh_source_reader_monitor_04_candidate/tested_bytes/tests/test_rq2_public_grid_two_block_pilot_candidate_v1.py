from __future__ import annotations

import copy
import os
import time
from pathlib import Path

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v1 as runner
from experiments import (
    validate_rq2_public_grid_two_block_pilot_candidate_v1 as validator,
)


def _highs_0008() -> dict[str, object]:
    payload = copy.deepcopy(runner._extract_gurobi_payload())
    config = runner._load_yaml(runner.BASE_CONFIG, "base config")
    solver_name = runner.recovery.solver_spec(config["solver"]).name
    options = runner.recovery.solver_options(
        runner.recovery.solver_spec(config["solver"])
    )
    baseline = payload["baseline_audit"]
    baseline["solver_name"] = solver_name
    baseline["solver_options"] = options
    baseline["solver_threads"] = config["solver"]["threads"]
    for outcome, row in zip(payload["outcomes"], payload["rows"], strict=True):
        outcome["solver_name"] = solver_name
        outcome["solver_options"] = options if row["active_event_id"] else {}
    return payload


def _shift_active_hour(payload: dict[str, object], shift: float) -> None:
    index = next(
        index
        for index, row in enumerate(payload["rows"])
        if row["active_event_id"]
    )
    outcome = payload["outcomes"][index]
    row = payload["rows"][index]
    outcome["primary"]["grid_need_mw"] = shift
    certificate = outcome["primary_certificate"]
    for key in ("objective_incumbent_mw", "lower_bound_mw", "upper_bound_mw"):
        certificate[key] = shift
    certificate["absolute_gap_mw"] = 0.0
    certificate["relative_gap"] = 0.0
    certificate["gap_tolerance_mw"] = 1.0e-6
    row["grid_need_mw"] = shift
    row["grid_need_fraction"] = shift / 250.0
    row["dispatch_objective_incumbent_mw"] = shift
    row["dispatch_lower_bound_mw"] = shift
    row["dispatch_upper_bound_mw"] = shift
    row["dispatch_absolute_gap_mw"] = 0.0
    row["dispatch_relative_gap"] = 0.0
    row["dispatch_gap_tolerance_mw"] = 1.0e-6


def _closed_request() -> dict[str, object]:
    return {
        "schema": runner.REQUEST_SCHEMA,
        "block_id": runner.BLOCKS[0],
        "execution_index": 1,
        "block_input_sha256": "a" * 64,
        "config_sha256": "a" * 64,
        "activation_sha256": "a" * 64,
        "pass_receipt_sha256": "a" * 64,
        "bundle_sha256": "a" * 64,
        "outer_sha256": "a" * 64,
        "scientific_config_path": str(runner.BASE_CONFIG.resolve()),
        "scientific_config_sha256": "a" * 64,
        "stage": runner.recovery.STAGE,
        "stage_base_provenance_sha256": "a" * 64,
        "parent_pid": os.getppid(),
        "parent_dispatch_started_ns": time.time_ns(),
        "controller_nonce": "a" * 64,
        "controller_receipt_sha256": "a" * 64,
        "nonce": "b" * 64,
        "python_executable": str(Path(os.sys.executable).resolve()),
        "python_executable_sha256": "a" * 64,
        "execution_host": {},
        "implementation": {},
        "solver": {},
        "worker_result_path": "unused",
    }


def test_validate_only_is_zero_solver_zero_result_and_zero_formal_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    roots = runner._pilot_roots(config)
    assert all(not path.exists() for path in roots.values())
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("solver/worker dispatch"),
    )
    report = runner.run(validate_only=True)
    assert report["validation_passed"] is True
    assert report["implementation_pass_receipt_valid"] is True
    assert report["pilot_implementation_ready"] is True
    assert report["execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0
    assert all(not path.exists() for path in roots.values())


def test_controller_and_hidden_worker_are_closed_before_scientific_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_stage_context",
        lambda: pytest.fail("scientific preflight reached"),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("worker dispatch reached"),
    )
    with pytest.raises(RuntimeError, match="authority is closed"):
        runner.run(validate_only=False)
    request_path = tmp_path / "request.json"
    with pytest.raises(RuntimeError, match="authority is closed"):
        runner._validate_request(_closed_request(), request_path)


def test_candidate_two_layer_gate_is_non_circular_and_closed() -> None:
    config, activation = runner._load_authority()
    successor = config["future_execution_successor"]
    assert successor["current_candidate_execution_gate_remains_closed"] is True
    assert successor["pass_receipt_must_bind_candidate_outer_sha256"] is True
    assert successor["separate_versioned_execution_successor_required"] is True
    assert activation["candidate_authority"]["pre_run_review_receipt_path"] is None
    status = runner._execution_authority_status(config, activation)
    assert status["independent_pre_run_review_passed"] is False
    assert status["execution_successor_present"] is False
    assert status["two_block_pilot_execution_ready"] is False


def test_science_resources_solver_and_block_order_are_exactly_inherited() -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    base = runner._load_yaml(runner.BASE_CONFIG, "base")
    assert config["scientific_authority"]["solver"] == base["solver"]
    assert config["pilot"]["blocks"] == runner.BLOCKS
    assert config["pilot"]["execution_order"] == runner.BLOCKS
    assert config["pilot"]["external_watchdog_seconds"] == 21600
    assert config["pilot"]["resource_sample_interval_seconds"] == 5.0
    assert config["pilot"]["private_commit_limit_gib"] == 8.0
    assert config["pilot"]["minimum_system_commit_available_gib"] == 2.0
    assert base["solver"]["name"] == "highs"
    assert base["solver"]["expected_package_version"] == "1.15.1"
    assert base["solver"]["threads"] == 4
    assert base["solver"]["random_seed"] == 0
    assert base["solver"]["time_limit_seconds"] is None


def test_pilot_roots_are_fresh_pairwise_isolated_and_formal_snapshot_is_exact() -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    roots = runner._pilot_roots(config)
    assert len({path.resolve() for path in roots.values()}) == len(roots)
    assert all(not path.exists() for path in roots.values())
    snapshot = runner._formal_snapshot(config)
    checkpoint = snapshot["formal_roots"]["gurobi_checkpoint_directory"]
    assert checkpoint["exists"] is True
    assert len(checkpoint["inventory"]) == 9
    assert snapshot["formal_roots"]["gurobi_output_directory"]["exists"] is False
    assert snapshot["formal_roots"]["recovery_checkpoint_directory"]["exists"] is False
    assert snapshot["formal_roots"]["recovery_output_directory"]["exists"] is False


def test_named_outage_comparator_passes_valid_payloads_without_raw_status_equality() -> None:
    highs = _highs_0008()
    active_index = next(
        index
        for index, item in enumerate(highs["outcomes"])
        if item["primary"]["event_id"]
    )
    active = highs["outcomes"][active_index]
    active["primary"]["termination_condition"] = "globallyOptimal"
    highs["rows"][active_index]["dispatch_termination_condition"] = "globallyOptimal"
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is True
    assert report["raw_status_equality_required"] is False
    assert report["mathematical_infeasibility_inferred"] is False


def test_named_outage_hourly_interval_uses_frozen_semantic_numeric_envelope() -> None:
    highs = _highs_0008()
    _shift_active_hour(highs, 5.0e-11)
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is True
    assert report["mathematical_infeasibility_inferred"] is False


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("grid_need", "finite grid need differs"),
        ("disjoint_interval", "certified intervals are disjoint"),
        ("baseline", "baseline incumbents differ"),
        ("missing_certificate", "fields drifted"),
        ("unresolved", "state, or resolution authority drifted"),
    ],
)
def test_named_outage_comparator_fails_closed_without_infeasibility_inference(
    mutation: str, message: str
) -> None:
    highs = _highs_0008()
    if mutation == "grid_need":
        _shift_active_hour(highs, 2.0e-5)
    elif mutation == "disjoint_interval":
        _shift_active_hour(highs, 5.0e-6)
    elif mutation == "baseline":
        baseline = highs["baseline_audit"]
        for key in ("objective_usd", "lower_bound_usd", "upper_bound_usd"):
            baseline[key] += 2.0e-4
        baseline["gap_tolerance_usd"] = max(
            1.0e-6, 1.0e-6 * max(abs(baseline["lower_bound_usd"]), abs(baseline["upper_bound_usd"]), 1.0)
        )
    elif mutation == "missing_certificate":
        highs["outcomes"][0]["primary_certificate"].pop("lower_bound_mw")
    else:
        highs["outcomes"][0]["resolved_for_pipeline"] = False
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is False
    assert message in report["reason"]
    assert report["mathematical_infeasibility_inferred"] is False


def test_0009_requires_complete_payload_but_has_no_cross_solver_comparison() -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    comparison = config["named_outage_comparison"]
    publication = config["publication"]
    assert comparison["block_0009_cross_solver_comparison_required"] is False
    assert publication["success_requires_both_complete_valid_payloads"] is True
    assert publication["success_requires_named_outage_comparison_passed"] is True


def test_incomplete_payload_or_failed_comparison_cannot_publish_success(
    tmp_path: Path,
) -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    controller = {"formal_snapshot_before": runner._formal_snapshot(config)}
    with pytest.raises(RuntimeError, match="complete ordered payloads"):
        runner._publish_result(
            tmp_path,
            config=config,
            controller=controller,
            payloads={runner.BLOCKS[0]: _highs_0008()},
            comparison={"comparison_passed": False},
            formal_after=controller["formal_snapshot_before"],
        )
    assert not (tmp_path / "summary.json").exists()


def test_bundle_outer_and_pass_receipt_bind_exact_live_bytes() -> None:
    files = runner._verify_bundle_chain()
    assert set(files) == runner.BUNDLE_INVENTORY
    receipt = validator._validate_pass_receipt()
    assert receipt["verdict"] == "PASS"
    assert receipt["effect"]["two_block_pilot_execution_authorized"] is False
    assert receipt["effect"]["formal_execution_ready"] is False
