from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as runner
from src.scenarios.common_input_signature import common_input_signature_sha256

_HOURS = 2
_STATES = ("normal", "branch_b1")
_PROXY_LOWER = 0.8
_PROXY_UPPER = 0.80005
_COST_LOWER = 100.0
_COST_UPPER = 100.005


def _residual() -> dict[str, object]:
    return {
        "commitment_feasible_by_step": [True] * _HOURS,
        "contingency_secure_by_step": [True] * _HOURS,
        "maximum_balance_residual_mw": 0.0,
        "maximum_branch_flow_equation_residual_mw": 0.0,
        "maximum_branch_rating_violation_mw": 0.0,
        "maximum_commitment_logic_violation": 0.0,
        "maximum_dc_flow_bound_violation_mw": 0.0,
        "maximum_generation_bound_violation_mw": 0.0,
        "maximum_minimum_time_violation": 0.0,
        "maximum_online_ramp_violation_mw": 0.0,
        "maximum_outage_flow_mw": 0.0,
        "maximum_reserve_bound_violation_mw": 0.0,
        "maximum_reserve_shortfall_mw": 0.0,
        "maximum_security_response_violation_mw": 0.0,
        "normal_secure_by_step": [True] * _HOURS,
        "passed": True,
        "ramp_feasible_by_step": [True] * _HOURS,
        "reserve_feasible_by_step": [True] * _HOURS,
    }


def _stage_record(
    stage: str,
    lower: float,
    upper: float,
    *,
    residual: dict[str, object],
    candidate_proxy: float,
    candidate_cost: float,
) -> dict[str, object]:
    sense = "maximize" if stage == "proxy_maximization" else "minimize"
    target = 1.0e-4
    maximum_relative = 1.0e-3
    maximum_absolute = 1.0e-3 if sense == "maximize" else None
    absolute_gap = upper - lower
    feasible = lower if sense == "maximize" else upper
    relative_to_feasible = absolute_gap / max(abs(feasible), 1.0e-12)
    generic_relative = absolute_gap / max(abs(lower), abs(upper), 1.0)
    target_attained = relative_to_feasible <= target
    relative_passed = relative_to_feasible <= maximum_relative
    absolute_passed = maximum_absolute is None or absolute_gap <= maximum_absolute
    maximum_passed = relative_passed and absolute_passed
    snapshot_sha256 = ("a" if sense == "maximize" else "b") * 64
    callback = {
        "actual_operating_cost_usd": candidate_cost,
        "actual_proxy_fraction": _PROXY_LOWER - 1.0e-7,
        "commitment_capability_proxy_fraction": candidate_proxy,
        "cost_consistent": True,
        "maximum_shared_value_violation": 0.0,
        "passed": True,
        "proxy_consistent": True,
        "residual_audit": deepcopy(residual),
        "snapshot_proxy_consistent": True,
    }
    record: dict[str, object] = {
        "schema": "rts_gmlc_exact_cg_stage_record_v1",
        "stage": stage,
        "sense": sense,
        "eligible": maximum_passed,
        "eligibility_status": (
            "target_attained" if target_attained else "eligible_within_maximum"
        ),
        "failure_reason": None,
        "target_relative_gap": target,
        "target_attained": target_attained,
        "certificate": {
            "valid": True,
            "lower_bound": lower,
            "upper_bound": upper,
            "absolute_gap": absolute_gap,
            "relative_gap": generic_relative,
            "relative_gap_to_feasible_incumbent": relative_to_feasible,
            "target_gap_attained": generic_relative <= target,
        },
        "maximum_acceptance": {
            "target_relative_gap_to_feasible_incumbent": target,
            "target_attained": target_attained,
            "maximum_accepted_relative_gap_to_feasible_incumbent": (maximum_relative),
            "maximum_accepted_absolute_gap": maximum_absolute,
            "relative_acceptance_passed": relative_passed,
            "absolute_acceptance_passed": absolute_passed,
            "maximum_acceptance_passed": maximum_passed,
        },
        "master_records": [{"dual_bound": upper if sense == "maximize" else lower}],
        "final_shared_snapshot_sha256": snapshot_sha256,
        "final_full_state_audit": {
            "additional_audits_passed": True,
            "audited_state_ids": list(_STATES),
            "callback_record": callback,
            "full_feasible_objective": feasible,
            "integer_variables_relaxed": True,
            "passed": True,
            "reported_shared_snapshot_sha256": snapshot_sha256,
            "residual_audit_passed": True,
            "shared_snapshot_fixed": True,
            "shared_snapshot_sha256": snapshot_sha256,
            "solution_usable": True,
        },
    }
    if stage == "cost_normalization":
        record["proxy_floor"] = _PROXY_LOWER - 1.0e-7
    return record


def _formal_context() -> SimpleNamespace:
    generators = (
        SimpleNamespace(
            uid="g_provider",
            enabled=True,
            dispatch_mode="committable",
            category="Coal",
        ),
        SimpleNamespace(
            uid="g_nonprovider",
            enabled=True,
            dispatch_mode="fixed",
            category="Nuclear",
        ),
    )
    return SimpleNamespace(
        config={
            "preregistration": {"id": "formal-v4"},
            "candidate_frontier": {
                "relative_cost_budget_deltas": [0.1],
                "expected_hours": _HOURS,
                "cost_cap_absolute_tolerance_usd": 1.0e-4,
            },
            "parent_zero_control": {"baseline_full_state_cost_usd": 100.0},
            "formal_solver": {
                "stages": {
                    "proxy_maximization": {
                        "target_relative_gap": 1.0e-4,
                        "maximum_accepted_absolute_gap": 1.0e-3,
                        "maximum_accepted_relative_gap_to_feasible_incumbent": (1.0e-3),
                    },
                    "cost_normalization": {
                        "target_relative_gap": 1.0e-4,
                        "maximum_accepted_absolute_gap": None,
                        "maximum_accepted_relative_gap_to_feasible_incumbent": (1.0e-3),
                        "proxy_floor_absolute_tolerance": 1.0e-7,
                    },
                },
                "primary_regret": {
                    "proxy_floor_tolerance": 1.0e-7,
                    "numerical_audit_allowance": 1.0e-6,
                    "hard_maximum": 0.0010011,
                },
                "solver": {"feasibility_tolerance": 1.0e-6},
                "final_audit": {"selected_state_count": len(_STATES)},
            },
        },
        zero=SimpleNamespace(
            scan=SimpleNamespace(
                data=SimpleNamespace(
                    generators=generators,
                    branches=(SimpleNamespace(uid="b1"),),
                    dc_branches=(SimpleNamespace(uid="dc1"),),
                )
            )
        ),
        initial_state=SimpleNamespace(
            commitment={"g_provider": False, "g_nonprovider": True}
        ),
        selection=SimpleNamespace(
            states=tuple(SimpleNamespace(state_id=state_id) for state_id in _STATES)
        ),
        input_contract_sha256="c" * 64,
    )


def _formal_candidate() -> runner._Candidate:
    commitment = tuple(
        {"g_provider": True, "g_nonprovider": True} for _ in range(_HOURS)
    )
    startup, shutdown = runner._boolean_transitions(
        commitment,
        {"g_provider": False, "g_nonprovider": True},
    )
    generation = tuple(
        {"g_provider": 10.0 + hour, "g_nonprovider": 5.0} for hour in range(_HOURS)
    )
    branch_flows = tuple({"b1": float(hour)} for hour in range(_HOURS))
    dc_flows = tuple({"dc1": 0.0} for _ in range(_HOURS))
    reserve = tuple({"g_provider": 1.0, "g_nonprovider": 0.0} for _ in range(_HOURS))
    residual = _residual()
    proxy_record = _stage_record(
        "proxy_maximization",
        _PROXY_LOWER,
        _PROXY_UPPER,
        residual=residual,
        candidate_proxy=_PROXY_LOWER,
        candidate_cost=_COST_UPPER,
    )
    cost_record = _stage_record(
        "cost_normalization",
        _COST_LOWER,
        _COST_UPPER,
        residual=residual,
        candidate_proxy=_PROXY_LOWER,
        candidate_cost=_COST_UPPER,
    )
    observed_regret = _PROXY_UPPER - _PROXY_LOWER
    derived_allowed = observed_regret + 1.0e-7 + 1.0e-6
    return runner._Candidate(
        requested_candidate_id=runner._requested_candidate_id(0.1),
        source="q_proxy_exact_selected_state_constraint_generation",
        relative_cost_budget_delta=0.1,
        cost_budget_usd=100.0 * 1.1,
        operating_cost_usd=_COST_UPPER,
        reactive_proxy_fraction=_PROXY_LOWER,
        commitment_sha256=runner._commitment_sha256(commitment),
        dispatch_sha256=runner._dispatch_sha256(
            generation,
            branch_flows,
            dc_flows,
        ),
        commitment=commitment,
        startup=startup,
        shutdown=shutdown,
        generation_mw=generation,
        branch_flows_mw=branch_flows,
        dc_flows_mw=dc_flows,
        reserve_up_mw=reserve,
        stage_audits={
            "proxy_maximization": proxy_record,
            "cost_normalization": cost_record,
            "primary_proxy_regret": {
                "schema": "rts_gmlc_primary_proxy_regret_certificate_v1",
                "stage_one_certified_upper_bound": _PROXY_UPPER,
                "final_commitment_capability_proxy_fraction": _PROXY_LOWER,
                "observed_regret_upper_bound": observed_regret,
                "stage_one_actual_absolute_gap": observed_regret,
                "proxy_floor_tolerance": 1.0e-7,
                "numerical_audit_allowance": 1.0e-6,
                "derived_allowed_regret": derived_allowed,
                "hard_maximum": 0.0010011,
                "passed": True,
            },
        },
        residual_audit=residual,
    )


def _document(
    context: SimpleNamespace, candidate: runner._Candidate
) -> dict[str, object]:
    return runner._exact_json_payload(runner._checkpoint_payload(context, 1, candidate))


def _validate(context: SimpleNamespace, candidate: runner._Candidate) -> None:
    runner._validate_checkpoint_document(
        _document(context, candidate),
        context,
        1,
        candidate.requested_candidate_id,
    )


def test_complete_minimal_formal_candidate_is_accepted() -> None:
    context = _formal_context()
    candidate = _formal_candidate()

    loaded = runner._validate_checkpoint_document(
        _document(context, candidate),
        context,
        1,
        candidate.requested_candidate_id,
    )

    assert loaded == candidate


def test_gross_absolute_gap_is_rejected() -> None:
    context = _formal_context()
    candidate = _formal_candidate()
    audits = deepcopy(candidate.stage_audits)
    audits["proxy_maximization"]["certificate"]["absolute_gap"] = 999.0

    with pytest.raises(RuntimeError, match="bound interval drifted"):
        _validate(context, replace(candidate, stage_audits=audits))


def test_forged_acceptance_flags_are_rejected() -> None:
    context = _formal_context()
    candidate = _formal_candidate()
    audits = deepcopy(candidate.stage_audits)
    record = audits["proxy_maximization"]
    record["certificate"].update(
        {
            "upper_bound": 1.8,
            "absolute_gap": 1.0,
            "relative_gap": 1.0 / 1.8,
            "relative_gap_to_feasible_incumbent": 1.0 / _PROXY_LOWER,
            "target_gap_attained": False,
        }
    )
    record["master_records"] = [{"dual_bound": 1.8}]

    with pytest.raises(RuntimeError, match="acceptance drifted"):
        _validate(context, replace(candidate, stage_audits=audits))


def test_one_hour_candidate_is_rejected() -> None:
    context = _formal_context()
    candidate = _formal_candidate()
    one_hour = replace(
        candidate,
        commitment=candidate.commitment[:1],
        startup=candidate.startup[:1],
        shutdown=candidate.shutdown[:1],
        generation_mw=candidate.generation_mw[:1],
        branch_flows_mw=candidate.branch_flows_mw[:1],
        dc_flows_mw=candidate.dc_flows_mw[:1],
        reserve_up_mw=candidate.reserve_up_mw[:1],
        commitment_sha256=runner._commitment_sha256(candidate.commitment[:1]),
        dispatch_sha256=runner._dispatch_sha256(
            candidate.generation_mw[:1],
            candidate.branch_flows_mw[:1],
            candidate.dc_flows_mw[:1],
        ),
    )

    with pytest.raises(RuntimeError, match="formal candidate contract drifted"):
        _validate(context, one_hour)


def test_missing_generator_uid_is_rejected() -> None:
    context = _formal_context()
    candidate = _formal_candidate()
    generation = tuple(
        {"g_provider": row["g_provider"]} for row in candidate.generation_mw
    )
    missing_uid = replace(
        candidate,
        generation_mw=generation,
        dispatch_sha256=runner._dispatch_sha256(
            generation,
            candidate.branch_flows_mw,
            candidate.dc_flows_mw,
        ),
    )

    with pytest.raises(RuntimeError, match="formal candidate contract drifted"):
        _validate(context, missing_uid)


def test_non_provider_reserve_must_be_zero() -> None:
    context = _formal_context()
    candidate = _formal_candidate()
    reserve = tuple({**row, "g_nonprovider": 0.5} for row in candidate.reserve_up_mw)

    with pytest.raises(RuntimeError, match="non-provider reserve drifted"):
        _validate(context, replace(candidate, reserve_up_mw=reserve))


def test_cost_callback_residual_swap_is_rejected() -> None:
    context = _formal_context()
    candidate = _formal_candidate()
    swapped = deepcopy(candidate.residual_audit)
    swapped["maximum_balance_residual_mw"] = 1.0e-7

    with pytest.raises(RuntimeError, match="cost callback drifted"):
        _validate(context, replace(candidate, residual_audit=swapped))


def test_immutable_staging_validator_failure_does_not_publish(
    tmp_path: Path,
) -> None:
    target = tmp_path / "artifact"

    def writer(staging: Path) -> None:
        (staging / "payload.txt").write_text("payload\n", encoding="utf-8")

    def reject(_staging: Path) -> None:
        raise RuntimeError("semantic validation failed")

    with pytest.raises(RuntimeError, match="semantic validation failed"):
        runner._publish_immutable_payload(target, writer, validator=reject)

    assert not target.exists()
    assert not tuple(tmp_path.glob(".artifact.processing-*"))


def _registration_payload(context: SimpleNamespace) -> dict[str, object]:
    preregistration = context.config["preregistration"]
    return {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "previous_ac_outcomes_observed": True,
        "candidate_frontier_outcomes_observed": False,
        "joint_ac_outcomes_observed": False,
        "parent_first_budget_solver_outcomes_observed": True,
        "parent_invalid_checkpoint_payload_observed": True,
        "parent_candidate_frontier_artifact_published": False,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    (
        ("status", "drifted-status"),
        ("parent_invalid_checkpoint_payload_observed", False),
    ),
)
def test_preregistration_status_or_disclosure_drift_is_rejected(
    tmp_path: Path,
    field: str,
    drifted_value: object,
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("schema: test\n", encoding="utf-8")
    input_contract = {"schema": "formal_contract_test_v1"}
    context = SimpleNamespace(
        config_path=config_path,
        config={
            "preregistration": {
                "schema": "rts_gmlc_zero_dc_ac_aware_commitment_preregistration_v4",
                "id": "formal-v4",
                "status": "frozen-status",
            }
        },
        input_contract=input_contract,
        input_contract_sha256=common_input_signature_sha256(input_contract),
    )
    payload = _registration_payload(context)
    payload[field] = drifted_value
    output_root = tmp_path / "output"
    target = output_root / "preregistration"

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        runner._write_exact_json(staging / "registration.json", payload)

    runner._publish_immutable_payload(target, writer)

    with pytest.raises(RuntimeError, match="registration payload drifted"):
        runner._require_preregistration(context, output_root)


@pytest.mark.parametrize(
    ("field", "drifted_value"),
    (
        ("solver", {"name": "highs", "threads": 8}),
        ("relative_cost_budget_deltas", [0.2]),
        ("formal_candidate_result", True),
    ),
)
def test_frontier_summary_drift_is_rejected_before_detail_loading(
    tmp_path: Path,
    field: str,
    drifted_value: object,
) -> None:
    evidence = {"formal_candidate_result": False}
    context = SimpleNamespace(
        config={
            "preregistration": {"id": "formal-v4"},
            "formal_solver": {
                "algorithm": "exact_selected_state_constraint_generation",
                "solver": {"name": "highs", "threads": 4},
            },
            "candidate_frontier": {"relative_cost_budget_deltas": [0.1]},
            "evidence": evidence,
        },
        input_contract_sha256="d" * 64,
    )
    summary = {
        "schema": "rts_gmlc_zero_dc_ac_aware_candidate_frontier_v4",
        "checkpoint_schema": runner._CHECKPOINT_SCHEMA,
        "float_serialization": runner._CHECKPOINT_FLOAT_SERIALIZATION,
        "preregistration_id": "formal-v4",
        "input_contract_sha256": context.input_contract_sha256,
        "algorithm": "exact_selected_state_constraint_generation",
        "solver": {"name": "highs", "threads": 4},
        "relative_cost_budget_deltas": [0.1],
        "all_budget_candidates_completed_before_deduplication": True,
        "candidate_generation_completed_before_any_joint_ac_solve": True,
        "candidate_generation_uses_ac_outcomes": False,
        "joint_ac_solver_call_count": 0,
        **evidence,
    }
    summary[field] = drifted_value
    root = tmp_path / "candidate_frontier"

    runner._publish_immutable_payload(
        root,
        lambda staging: runner._write_exact_json(staging / "summary.json", summary),
    )

    with pytest.raises(RuntimeError, match="candidate summary drifted"):
        runner._load_candidate_frontier(context, tmp_path)
