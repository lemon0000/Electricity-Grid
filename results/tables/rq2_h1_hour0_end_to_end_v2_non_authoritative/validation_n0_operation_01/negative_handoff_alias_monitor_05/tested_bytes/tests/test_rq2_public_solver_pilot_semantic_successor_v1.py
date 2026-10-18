from __future__ import annotations

import copy
import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml

from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    CONFIG,
    EXPECTED_GATES,
    _certificate_interval,
    _close,
    _verify_transfer_archive,
    evaluate_runs,
    validate,
)

ROOT = Path(__file__).resolve().parents[1]
RUNS = ROOT / "results/tables/rq2_public_solver_pilot_v1/runs.json"


def _config() -> dict[str, object]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def _runs() -> list[dict[str, object]]:
    return json.loads(RUNS.read_text(encoding="utf-8"))


def _hour(
    runs: list[dict[str, object]],
    run_id: str,
    block_id: str,
    source_hour: int,
) -> dict[str, object]:
    run = next(item for item in runs if item["run_id"] == run_id)
    block = next(item for item in run["blocks"] if item["block_id"] == block_id)
    return next(item for item in block["hours"] if item["source_hour"] == source_hour)


def test_legal_minimization_interval_uses_own_gap_not_cross_solver_bound_equality():
    interval = _certificate_interval(
        {
            "incumbent": 10.0,
            "lower": 8.0,
            "upper": 10.0,
            "absolute": 2.0,
            "relative": 0.2,
            "tolerance": 2.5,
        },
        prefix="analytic",
        configured_relative_gap=0.25,
        model_tolerance=1.0e-6,
        numeric_tolerance=1.0e-12,
        incumbent_key="incumbent",
        lower_key="lower",
        upper_key="upper",
        absolute_gap_key="absolute",
        relative_gap_key="relative",
        gap_tolerance_key="tolerance",
    )
    assert interval == (10.0, 8.0, 10.0)


def test_own_gap_above_configured_limit_fails_closed():
    with pytest.raises(ValueError, match="own gap tolerance is inconsistent"):
        _certificate_interval(
            {
                "incumbent": 10.0,
                "lower": 8.0,
                "upper": 10.0,
                "absolute": 2.0,
                "relative": 0.2,
                "tolerance": 2.5,
            },
            prefix="analytic",
            configured_relative_gap=0.1,
            model_tolerance=1.0e-6,
            numeric_tolerance=1.0e-12,
            incumbent_key="incumbent",
            lower_key="lower",
            upper_key="upper",
            absolute_gap_key="absolute",
            relative_gap_key="relative",
            gap_tolerance_key="tolerance",
        )


def test_materially_reversed_interval_fails_closed():
    with pytest.raises(ValueError, match="invalid minimization interval"):
        _certificate_interval(
            {
                "incumbent": 10.0,
                "lower": 10.00005,
                "upper": 10.0,
                "absolute": 0.0,
                "relative": 0.0,
                "tolerance": 1.0e-5,
            },
            prefix="analytic",
            configured_relative_gap=1.0e-6,
            model_tolerance=1.0e-6,
            numeric_tolerance=1.0e-12,
            incumbent_key="incumbent",
            lower_key="lower",
            upper_key="upper",
            absolute_gap_key="absolute",
            relative_gap_key="relative",
            gap_tolerance_key="tolerance",
        )


def test_observed_v1_is_only_a_semantic_diagnostic_and_preserves_raw_statuses():
    report = evaluate_runs(_config(), _runs())
    assert report["diagnostic_semantic_consistency_observed"] is True
    assert report["v1_eligibility_changed"] is False
    assert report["confirmatory_pilot_required"] is True
    assert report["cross_solver_confirmation_completed"] is False
    assert report["run_count"] == 4
    assert report["block_run_count"] == 16
    assert report["hour_run_count"] == 384
    assert report["raw_status_inventory"] == [
        {
            "solver": "gurobi",
            "termination_condition": "infeasible",
            "solver_status": "warning",
            "count": 8,
        },
        {
            "solver": "gurobi",
            "termination_condition": "not_applicable_no_active_outage",
            "solver_status": "not_applicable",
            "count": 54,
        },
        {
            "solver": "gurobi",
            "termination_condition": "optimal",
            "solver_status": "ok",
            "count": 130,
        },
        {
            "solver": "highs",
            "termination_condition": "infeasible",
            "solver_status": "error",
            "count": 8,
        },
        {
            "solver": "highs",
            "termination_condition": "not_applicable_no_active_outage",
            "solver_status": "not_applicable",
            "count": 54,
        },
        {
            "solver": "highs",
            "termination_condition": "optimal",
            "solver_status": "ok",
            "count": 130,
        },
    ]


def test_solver_specific_e0_raw_status_mapping_rejects_unregistered_status():
    runs = _runs()
    target = _hour(runs, "highs_r1", "holdout_s20260822_0089", 6598)
    target["primary"]["solver_status"] = "warning"
    with pytest.raises(ValueError, match="not registered as infeasible"):
        evaluate_runs(_config(), runs)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("termination_condition", "maxTimeLimit", "unregistered raw status"),
        ("solver_status", "aborted", "unregistered raw status"),
    ],
)
def test_timeout_or_unknown_raw_status_cannot_confirm_finite_hour(
    field: str,
    value: str,
    message: str,
):
    runs = _runs()
    target = _hour(runs, "gurobi_r1", "holdout_s20260822_0091", 6624)
    target["primary"][field] = value
    with pytest.raises(ValueError, match=message):
        evaluate_runs(_config(), runs)


def test_unresolved_hour_cannot_confirm_semantics():
    runs = _runs()
    target = _hour(runs, "gurobi_r1", "holdout_s20260822_0091", 6624)
    target["resolved_for_pipeline"] = False
    with pytest.raises(ValueError, match="unresolved hour"):
        evaluate_runs(_config(), runs)


def test_incomplete_e0_certificate_cannot_confirm_semantics():
    runs = _runs()
    target = _hour(runs, "gurobi_r1", "holdout_s20260822_0150", 8057)
    target["zero_dc_confirmation_certificate"]["lower_bound_mw"] = 0.0
    with pytest.raises(ValueError, match="must be null for infeasibility"):
        evaluate_runs(_config(), runs)


def test_e0_primary_and_zero_dc_metadata_must_match():
    runs = _runs()
    target = _hour(runs, "highs_r2", "holdout_s20260822_0089", 6598)
    target["zero_dc_confirmation"]["source_hour"] = 6599
    with pytest.raises(ValueError, match="metadata differ"):
        evaluate_runs(_config(), runs)


def test_solver_option_drift_cannot_confirm_semantics():
    runs = _runs()
    target = next(item for item in runs if item["run_id"] == "gurobi_r1")
    target["blocks"][0]["baseline_audit"]["solver_options"]["Threads"] = 8
    with pytest.raises(ValueError, match="solver options drifted"):
        evaluate_runs(_config(), runs)


def test_cross_solver_incumbent_drift_fails_closed():
    runs = _runs()
    target = next(item for item in runs if item["run_id"] == "gurobi_r1")
    block = next(
        item
        for item in target["blocks"]
        if item["block_id"] == "holdout_s20260822_0013"
    )
    audit = block["baseline_audit"]
    audit["objective_usd"] += 1.0e-3
    audit["upper_bound_usd"] += 1.0e-3
    audit["lower_bound_usd"] += 1.0e-3
    audit["gap_tolerance_usd"] += 1.0e-9
    with pytest.raises(ValueError, match="baseline incumbents differ"):
        evaluate_runs(_config(), runs)


def test_cross_solver_disjoint_intervals_cannot_use_incumbent_tolerance():
    runs = _runs()
    for run_id in ("gurobi_r1", "gurobi_r2"):
        run = next(item for item in runs if item["run_id"] == run_id)
        block = next(
            item
            for item in run["blocks"]
            if item["block_id"] == "holdout_s20260822_0013"
        )
        audit = block["baseline_audit"]
        for field in ("objective_usd", "lower_bound_usd", "upper_bound_usd"):
            audit[field] += 5.0e-5
        audit["gap_tolerance_usd"] = max(
            1.0e-6,
            1.0e-6 * abs(audit["upper_bound_usd"]),
        )
    with pytest.raises(ValueError, match="baseline MIP intervals are disjoint"):
        evaluate_runs(_config(), runs)


def test_hourly_numeric_envelope_is_derived_and_below_scientific_thresholds():
    config = _config()
    acceptance = config["semantic_acceptance"]
    provenance = acceptance["threshold_provenance"][
        "hourly_solver_report_absolute_tolerance"
    ]
    absolute = acceptance["hourly_solver_report_absolute_tolerance_mw"]
    relative = acceptance["numeric_serialization_consistency_tolerance"]
    assert absolute == pytest.approx(
        provenance["frozen_model_tolerance_mw"]
        * provenance["fraction_of_frozen_model_tolerance"],
        rel=0.0,
        abs=1.0e-25,
    )
    assert absolute == pytest.approx(
        acceptance["hourly"]["maximum_finite_grid_need_difference_mw"]
        * provenance["fraction_of_cross_solver_finite_grid_threshold"],
        rel=0.0,
        abs=1.0e-25,
    )
    assert provenance["introduced_after_v1_observation"] is True
    assert provenance["diagnostic_only_until_fresh_confirmatory_pilot"] is True
    assert _close(
        12.319343744854965,
        12.31934374488517,
        relative,
        absolute_tolerance=absolute,
    )
    assert _close(
        199.25100100007356,
        199.25100100000148,
        relative,
        absolute_tolerance=absolute,
    )
    assert not _close(
        12.319343744854965,
        12.319348744854965,
        relative,
        absolute_tolerance=absolute,
    )


def test_same_wrong_hourly_grid_need_in_all_runs_fails_own_certificate_gate():
    runs = _runs()
    for run_id in ("highs_r1", "gurobi_r1", "gurobi_r2", "highs_r2"):
        target = _hour(runs, run_id, "holdout_s20260822_0091", 6624)
        target["primary"]["grid_need_mw"] += 9.0e-6
    with pytest.raises(ValueError, match="grid need and incumbent differ"):
        evaluate_runs(_config(), runs)


def test_hourly_point_certificate_rejects_fake_absolute_gap_inside_envelope():
    runs = _runs()
    target = _hour(runs, "gurobi_r1", "holdout_s20260822_0091", 6624)
    certificate = target["primary_certificate"]
    assert certificate["lower_bound_mw"] == certificate["upper_bound_mw"]
    certificate["absolute_gap_mw"] = 5.0e-11
    with pytest.raises(ValueError, match="absolute gap is inconsistent with bounds"):
        evaluate_runs(_config(), runs)


def test_analytic_certificate_rejects_reverse_interval_inside_envelope():
    with pytest.raises(ValueError, match="invalid minimization interval"):
        _certificate_interval(
            {
                "incumbent": 10.0,
                "lower": 10.0 + 5.0e-11,
                "upper": 10.0,
                "absolute": 0.0,
                "relative": 0.0,
                "tolerance": 1.0e-5,
            },
            prefix="analytic",
            configured_relative_gap=1.0e-6,
            model_tolerance=1.0e-6,
            numeric_tolerance=1.0e-12,
            incumbent_key="incumbent",
            lower_key="lower",
            upper_key="upper",
            absolute_gap_key="absolute",
            relative_gap_key="relative",
            gap_tolerance_key="tolerance",
        )


def test_hourly_pairwise_disjoint_intervals_fail_numeric_overlap_gate():
    runs = _runs()
    shift = 5.0e-6
    for run_id in ("gurobi_r1", "gurobi_r2"):
        target = _hour(runs, run_id, "holdout_s20260822_0091", 6624)
        target["primary"]["grid_need_mw"] += shift
        certificate = target["primary_certificate"]
        for field in (
            "objective_incumbent_mw",
            "lower_bound_mw",
            "upper_bound_mw",
        ):
            certificate[field] += shift
        certificate["gap_tolerance_mw"] = max(
            1.0e-6,
            1.0e-6 * abs(certificate["upper_bound_mw"]),
        )
    with pytest.raises(ValueError, match="hourly MIP intervals are disjoint"):
        evaluate_runs(_config(), runs)


def test_same_wrong_source_hour_in_all_runs_fails_frozen_inventory():
    runs = _runs()
    for run_id in ("highs_r1", "gurobi_r1", "gurobi_r2", "highs_r2"):
        target = _hour(runs, run_id, "holdout_s20260822_0091", 6624)
        target["source_hour"] = 999999
        target["primary"]["source_hour"] = 999999
    with pytest.raises(ValueError, match="frozen source-hour inventory"):
        evaluate_runs(_config(), runs)


def test_same_wrong_event_metadata_in_all_runs_fails_frozen_inventory():
    runs = _runs()
    for run_id in ("highs_r1", "gurobi_r1", "gurobi_r2", "highs_r2"):
        target = _hour(runs, run_id, "holdout_s20260822_0091", 6624)
        target["active_event_id"] = "fabricated_event"
        target["primary"]["event_id"] = "fabricated_event"
        target["primary"]["component_uid"] = "fabricated_component"
    with pytest.raises(ValueError, match="frozen hour inventory"):
        evaluate_runs(_config(), runs)


def test_same_wrong_block_role_in_all_runs_fails_frozen_inventory():
    runs = _runs()
    for run in runs:
        block = next(
            item
            for item in run["blocks"]
            if item["block_id"] == "holdout_s20260822_0091"
        )
        block["role"] = "ordinary_no_outage"
    with pytest.raises(ValueError, match="role drifted"):
        evaluate_runs(_config(), runs)


@pytest.mark.parametrize("kind", ["baseline", "hourly"])
def test_negative_residual_fails_closed(kind: str):
    runs = _runs()
    if kind == "baseline":
        run = next(item for item in runs if item["run_id"] == "gurobi_r1")
        block = next(
            item
            for item in run["blocks"]
            if item["block_id"] == "holdout_s20260822_0091"
        )
        block["baseline_audit"]["maximum_constraint_violation"] = -100.0
        message = "residual limit failed"
    else:
        target = _hour(runs, "gurobi_r1", "holdout_s20260822_0091", 6624)
        target["primary"]["maximum_constraint_violation"] = -100.0
        message = "finite residual limit failed"
    with pytest.raises(ValueError, match=message):
        evaluate_runs(_config(), runs)


def test_active_finite_hour_requires_positive_model_scale():
    runs = _runs()
    target = _hour(runs, "gurobi_r1", "holdout_s20260822_0091", 6624)
    target["primary_certificate"]["model_variables"] = 0
    target["primary_certificate"]["model_constraints"] = 0
    with pytest.raises(ValueError, match="active finite model scale must be positive"):
        evaluate_runs(_config(), runs)


def test_transfer_archive_rejects_extra_member(tmp_path: Path):
    archive_path = tmp_path / "extra.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for name, payload in (("expected.txt", b"expected"), ("extra.txt", b"extra")):
            info = tarfile.TarInfo(name)
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
    with pytest.raises(ValueError, match="transfer archive inventory"):
        _verify_transfer_archive(
            archive_path,
            {
                "expected.txt": "cea23dd4b87e8b00d78bd9f2e0e8c6047fe308b415bd5f7a36e6f63ed1842f02"
            },
        )


def test_transfer_archive_rejects_link_member(tmp_path: Path):
    archive_path = tmp_path / "link.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        info = tarfile.TarInfo("link.txt")
        info.type = tarfile.SYMTYPE
        info.linkname = "target.txt"
        archive.addfile(info)
    with pytest.raises(ValueError, match="not an ordinary file"):
        _verify_transfer_archive(archive_path, {"link.txt": "0" * 64})


def test_semantic_successor_keeps_every_execution_and_claim_gate_closed():
    config = _config()
    provenance = config["semantic_acceptance"]["threshold_provenance"]
    assert provenance["baseline_incumbent_difference"] == {
        "v1_source_field": "acceptance.maximum_baseline_objective_difference_usd",
        "frozen_value": 1.0e-4,
        "successor_use": "incumbent_objective_only",
    }
    assert provenance["scientific_threshold_values_changed_after_observation"] is False
    assert (
        provenance["hourly_solver_report_absolute_tolerance"][
            "introduced_after_v1_observation"
        ]
        is True
    )
    assert config["gates"] == EXPECTED_GATES
    assert all(value is False for value in config["gates"].values())
    assert config["confirmatory_pilot"]["runner_path"] is None
    assert config["confirmatory_pilot"]["result_directory"] is None
    assert (
        config["confirmatory_pilot"][
            "v1_runs_or_transfer_package_may_satisfy_confirmation"
        ]
        is False
    )


def test_canonical_contract_and_frozen_v1_artifacts_validate_without_solver_calls():
    report = validate()
    assert report["validation_passed"] is True
    assert report["original_v1_failed_check_count"] == 12
    assert report["original_v1_eligible"] is False
    assert report["executor_bundle_v1_member_count"] == 53
    assert report["executor_bundle_v2_member_count"] == 63
    assert report["input_package_member_count"] == 5
    assert report["preflight_member_count"] == 2
    assert report["pilot_result_member_count"] == 4
    assert report["transfer_manifest_member_count"] == 8
    assert report["transfer_archive_member_count"] == 9
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["confirmatory_pilot_executed"] is False
    assert report["cross_solver_confirmation_completed"] is False
    assert report["formal_execution_ready"] is False
    assert report["formal_result_exists"] is False
    assert report["security_certified"] is False


def test_canonical_only_validator_rejects_config_substitution(tmp_path: Path):
    tampered = copy.deepcopy(_config())
    tampered["gates"]["formal_execution_ready"] = True
    path = tmp_path / "tampered.yaml"
    path.write_text(yaml.safe_dump(tampered, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="only canonical"):
        validate(path)
