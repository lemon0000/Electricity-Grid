from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.audit import (
    ARM_IDS,
    audit_raw_training_support,
    cfe_recovery_lower_bounds,
    minimum_event_count_lower_bound,
    terminal_inactivity_conflict,
)
from src.rq2_joint_deliverability_boundary_v1.boundary import (
    BoundaryAnchor,
    ContinuationHour,
    TemporalCarryState,
    advance_continuous_state,
    assess_observed_continuation,
    carry_state_across_boundary,
)
from src.rq2_joint_deliverability_v2.scenarios import expand_registered_cells

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_joint_deliverability_boundary_successor_v1.DRAFT.yaml"


def _config() -> dict[str, object]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def raw_audit() -> dict[str, object]:
    return audit_raw_training_support(CONFIG)


def _state() -> TemporalCarryState:
    return TemporalCarryState(
        arm_id="joint_correct_shared",
        track_id="shared",
        previous_call=0.25,
        event_active=True,
        active_duration_hours=2.0,
        interevent_rest_hours=None,
        event_count=1,
        cumulative_call_energy=0.35,
        recovery_debt=0.12,
        has_prior_event=True,
        accounting_period_id="period-0001",
    )


def _inactive_state() -> TemporalCarryState:
    return replace(
        _state(),
        previous_call=0.0,
        event_active=False,
        active_duration_hours=0.0,
        interevent_rest_hours=1.0,
    )


def _anchor() -> BoundaryAnchor:
    return BoundaryAnchor(
        arm_id="joint_correct_shared",
        track_id="shared",
        split="training",
        power_source_hour=23,
        workload_source_hour=23,
        power_trajectory_id="outage-seed-20260822",
        workload_trace_id="alibaba-source-a53041f4",
        workload_normalization_sha256="4" * 64,
        power_outage_seed=20260822,
        power_provenance_sha256="1" * 64,
        workload_provenance_sha256="2" * 64,
    )


def _continuation_hour(offset: int) -> ContinuationHour:
    return ContinuationHour(
        arm_id="joint_correct_shared",
        track_id="shared",
        split="training",
        power_source_hour=24 + offset,
        workload_source_hour=24 + offset,
        power_trajectory_id="outage-seed-20260822",
        workload_trace_id="alibaba-source-a53041f4",
        workload_normalization_sha256="4" * 64,
        power_outage_seed=20260822,
        grid_request=0.1,
        cfe_request=0.2,
        workload_occupancy=0.3,
        power_provenance_sha256="1" * 64,
        workload_provenance_sha256="2" * 64,
    )


def test_v5_terminal_inactivity_conflicts_with_positive_final_request() -> None:
    assert terminal_inactivity_conflict((0.0,) * 23 + (0.2,), 1.0e-6)
    assert not terminal_inactivity_conflict((0.0,) * 24, 1.0e-6)


def test_raw_training_audit_reproduces_frozen_counts_without_solver(
    raw_audit: dict[str, object],
) -> None:
    summary = raw_audit["summary"]

    assert summary["training_power_block_count"] == 541
    assert summary["training_workload_block_count"] == 34
    assert summary["raw_candidate_pair_count_per_cell"] == 541 * 34
    assert summary["registered_cell_count"] == 46
    assert summary["registered_arm_count"] == 4
    assert summary["registered_arm_ids"] == list(ARM_IDS)
    assert summary["terminal_positive_cfe_block_count_by_alpha"] == {
        "0.5": 358,
        "0.7": 478,
        "0.85": 541,
        "1.0": 541,
    }
    assert summary["solver_calls"] == 0
    assert summary["formal_result"] is False
    assert summary["full_physical_training_support_audited"] is False
    assert summary["absence_of_necessary_condition_means_feasible"] is False


def test_raw_training_audit_matches_independent_capacity_oracle(
    raw_audit: dict[str, object],
) -> None:
    primary = {
        (
            cell["parameters"]["hourly_cfe_target"],
            cell["parameters"]["flexible_fraction"],
            cell["parameters"]["normalized_recovery_headroom"],
        ): cell
        for cell in raw_audit["cells"]
        if cell["family"] == "primary_factorial"
    }
    expected = {
        (0.5, 0.05): 17503,
        (0.5, 0.2): 16987,
        (0.5, 0.5): 15367,
        (0.7, 0.05): 18394,
        (0.7, 0.2): 18292,
        (0.7, 0.5): 17452,
        (0.85, 0.05): 18394,
        (0.85, 0.2): 18394,
        (0.85, 0.5): 18136,
        (1.0, 0.05): 18394,
        (1.0, 0.2): 18394,
        (1.0, 0.5): 18385,
    }
    for (alpha, flexible), pair_count in expected.items():
        for headroom in (0.0, 0.1, 0.3):
            observed = primary[(alpha, flexible, headroom)]["cfe_projection"][
                "available_flexibility_violation_pair_count"
            ]
            assert observed == pair_count


def test_every_cell_and_projection_carries_legacy_terminal_scope(
    raw_audit: dict[str, object],
) -> None:
    for cell in raw_audit["cells"]:
        assert cell["model_scope"] == "legacy_sealed_v5_single_24h_completed_period"
        assert cell["terminal_conditions_apply_to_selected_continuous_draft"] is False
        projection = cell["cfe_projection"]
        assert projection["model_scope"] == cell["model_scope"]
        assert (
            projection["terminal_conditions_apply_to_selected_continuous_draft"]
            is False
        )


def test_new_cell_inventory_matches_sealed_v2_builder(
    raw_audit: dict[str, object],
) -> None:
    v5 = yaml.safe_load(
        (ROOT / "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml")
        .read_text(encoding="utf-8")
    )
    expected = [
        {
            "cell_id": cell.cell_id,
            "family": cell.family,
            "parameters": {
                "hourly_cfe_target": cell.hourly_cfe_target,
                "flexible_fraction": cell.flexible_fraction,
                "normalized_recovery_headroom": cell.normalized_recovery_headroom,
                "recovery_efficiency": cell.recovery_efficiency,
                "maximum_event_duration_hours": cell.maximum_event_duration_hours,
                "maximum_event_count": cell.maximum_event_count,
                "normalized_energy_budget": cell.normalized_energy_budget,
                "normalized_debt_limit": cell.normalized_debt_limit,
            },
        }
        for cell in expand_registered_cells(v5)
    ]
    observed = [
        {
            "cell_id": cell["cell_id"],
            "family": cell["family"],
            "parameters": cell["parameters"],
        }
        for cell in raw_audit["cells"]
    ]
    assert observed == expected


def test_alpha_one_has_no_cfe_compatible_recovery(
    raw_audit: dict[str, object],
) -> None:
    alpha_one = [
        cell
        for cell in raw_audit["cells"]
        if cell["parameters"]["hourly_cfe_target"] == 1.0
    ]
    assert alpha_one
    assert all(
        cell["cfe_projection"]["maximum_cfe_compatible_headroom"] == 0.0
        for cell in alpha_one
    )
    assert all(
        cell["cfe_projection"]["causal_terminal_debt_violation_pair_count"]
        == 541 * 34
        for cell in alpha_one
    )


def test_audit_covers_registered_necessary_condition_classes(
    raw_audit: dict[str, object],
) -> None:
    expected = {
        "terminal_inactivity",
        "available_flexibility",
        "energy_budget",
        "maximum_event_duration",
        "maximum_event_count_lower_bound",
        "total_recovery_energy_lower_bound",
        "causal_debt_limit",
        "causal_terminal_debt",
    }
    assert set(raw_audit["summary"]["necessary_condition_classes"]) == expected
    for cell in raw_audit["cells"]:
        projection = cell["cfe_projection"]
        assert set(projection["witnesses"]) == expected
        assert cell["arm_assessments"]["network_only_shared"]["status"] == (
            "unknown_grid_need_and_E0"
        )
        for arm_id in ARM_IDS[1:]:
            assert cell["arm_assessments"][arm_id]["status"] == (
                "conditional_on_finite_grid_support"
            )


def test_causal_debt_oracle_distinguishes_total_from_time_order() -> None:
    recover_after = cfe_recovery_lower_bounds(
        (0.2, 0.0),
        (0.0, 0.25),
        recovery_efficiency=0.8,
    )
    assert recover_after["total_terminal_debt_lower_bound"] == pytest.approx(0.0)
    assert recover_after["causal_debt_lower_bound_by_hour"] == pytest.approx([0.2, 0.0])
    premature_recovery = cfe_recovery_lower_bounds(
        (0.0, 0.2),
        (0.25, 0.0),
        recovery_efficiency=0.8,
    )
    assert premature_recovery["total_terminal_debt_lower_bound"] == pytest.approx(0.0)
    assert premature_recovery["causal_terminal_debt_lower_bound"] == pytest.approx(0.2)
    no_recovery = cfe_recovery_lower_bounds(
        (0.1, 0.2),
        (0.0, 0.0),
        recovery_efficiency=1.0,
    )
    assert no_recovery["total_call_energy"] == pytest.approx(0.3)
    assert no_recovery["causal_peak_debt_lower_bound"] == pytest.approx(0.3)


def test_joint_event_lower_bound_allows_zero_hour_bridging() -> None:
    assert minimum_event_count_lower_bound((0.2, 0.0, 0.2), 3, 1.0e-6) == 1


def test_continuous_boundary_carries_every_registered_state_without_reset() -> None:
    state = _state()
    carried = carry_state_across_boundary(
        state,
        anchor=_anchor(),
        next_hour=_continuation_hour(0),
    )
    assert carried == state


def test_first_continuation_step_uses_carried_debt_and_not_boundary_recovery() -> None:
    active = replace(
        _state(),
        previous_call=0.2,
        recovery_debt=0.2,
        active_duration_hours=1.0,
        cumulative_call_energy=0.2,
    )
    carried = carry_state_across_boundary(
        active,
        anchor=_anchor(),
        next_hour=_continuation_hour(0),
    )
    next_active = advance_continuous_state(
        carried,
        call=0.1,
        call_limit=0.5,
        recovery=0.0,
        recovery_headroom=0.1,
        maximum_recovery_power=0.2,
        recovery_efficiency=0.8,
        time_step_hours=1.0,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
        minimum_recovery_hours=1.0,
    )
    assert next_active.recovery_debt == pytest.approx(0.3)
    next_inactive = advance_continuous_state(
        carried,
        call=0.0,
        call_limit=0.5,
        recovery=0.1,
        recovery_headroom=0.1,
        maximum_recovery_power=0.2,
        recovery_efficiency=0.8,
        time_step_hours=1.0,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
        minimum_recovery_hours=1.0,
    )
    assert next_inactive.recovery_debt == pytest.approx(0.12)


def test_cross_boundary_duration_and_energy_budgets_do_not_reset() -> None:
    duration_state = replace(
        _state(),
        previous_call=0.2,
        event_active=True,
        active_duration_hours=2.0,
        cumulative_call_energy=0.2,
    )
    with pytest.raises(ValueError, match="duration"):
        advance_continuous_state(
            duration_state,
            call=0.1,
            call_limit=0.5,
            recovery=0.0,
            recovery_headroom=0.1,
            maximum_recovery_power=0.2,
            recovery_efficiency=0.8,
            time_step_hours=1.0,
            maximum_event_duration_hours=2.0,
            maximum_event_count=2,
            normalized_energy_budget=1.0,
            normalized_debt_limit=1.0,
            minimum_recovery_hours=1.0,
        )
    energy_state = replace(
        _state(),
        previous_call=0.25,
        event_active=True,
        active_duration_hours=1.0,
        cumulative_call_energy=0.25,
        recovery_debt=0.25,
    )
    with pytest.raises(ValueError, match="energy"):
        advance_continuous_state(
            energy_state,
            call=0.25,
            call_limit=0.5,
            recovery=0.0,
            recovery_headroom=0.1,
            maximum_recovery_power=0.2,
            recovery_efficiency=0.8,
            time_step_hours=1.0,
            maximum_event_duration_hours=4.0,
            maximum_event_count=2,
            normalized_energy_budget=0.4,
            normalized_debt_limit=1.0,
            minimum_recovery_hours=1.0,
        )


def test_continuous_state_rejects_unregistered_period_reset() -> None:
    with pytest.raises(ValueError, match="accounting period"):
        advance_continuous_state(
            _state(),
            call=0.0,
            call_limit=0.5,
            recovery=0.1,
            recovery_headroom=0.1,
            maximum_recovery_power=0.2,
            recovery_efficiency=0.8,
            time_step_hours=1.0,
            maximum_event_duration_hours=4.0,
            maximum_event_count=2,
            normalized_energy_budget=1.0,
            normalized_debt_limit=1.0,
            minimum_recovery_hours=1.0,
            accounting_period_id="period-0002",
        )


@pytest.mark.parametrize("fault", ["call_limit", "recovery_headroom", "recovery_power"])
def test_continuous_step_rejects_unavailable_call_or_recovery(fault: str) -> None:
    arguments = {
        "call": 0.0,
        "call_limit": 0.5,
        "recovery": 0.1,
        "recovery_headroom": 0.1,
        "maximum_recovery_power": 0.2,
        "recovery_efficiency": 0.8,
        "time_step_hours": 1.0,
        "maximum_event_duration_hours": 4.0,
        "maximum_event_count": 2,
        "normalized_energy_budget": 1.0,
        "normalized_debt_limit": 1.0,
        "minimum_recovery_hours": 1.0,
    }
    state = _inactive_state()
    if fault == "call_limit":
        arguments.update(call=0.2, call_limit=0.1, recovery=0.0)
    elif fault == "recovery_headroom":
        arguments["recovery_headroom"] = 0.05
    else:
        arguments["maximum_recovery_power"] = 0.05
    with pytest.raises(ValueError, match=fault.replace("_", " ")):
        advance_continuous_state(state, **arguments)


def test_tolerance_sized_call_does_not_create_ghost_energy_or_debt() -> None:
    state = _inactive_state()
    advanced = advance_continuous_state(
        state,
        call=1.0e-6,
        call_limit=0.0,
        recovery=0.0,
        recovery_headroom=0.0,
        maximum_recovery_power=0.0,
        recovery_efficiency=0.8,
        time_step_hours=1.0,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
        minimum_recovery_hours=1.0,
    )
    assert advanced.previous_call == 0.0
    assert advanced.cumulative_call_energy == state.cumulative_call_energy
    assert advanced.recovery_debt == state.recovery_debt


def test_carry_rejects_arm_track_mismatch() -> None:
    state = replace(
        _state(),
        arm_id="joint_b6_separate_planning_shared_execution",
        track_id="cfe",
    )
    with pytest.raises(ValueError, match="arm-track"):
        carry_state_across_boundary(
            state,
            anchor=_anchor(),
            next_hour=_continuation_hour(0),
        )


def test_unknown_continuation_is_blocked_and_right_censored() -> None:
    state = replace(_state(), observed_violations=("energy_budget",))
    assessment = assess_observed_continuation(
        anchor=_anchor(),
        continuation=None,
        registered_completion_deadline_hours=4,
        state=state,
    )
    assert assessment.status == "blocked_right_censored_unknown_continuation"
    assert not assessment.completion_can_be_evaluated
    assert assessment.observed_violations == ("energy_budget",)


@pytest.mark.parametrize(
    "continuation,deadline,expected",
    [
        (None, None, "blocked_missing_registered_completion_deadline"),
        (None, 2, "blocked_right_censored_unknown_continuation"),
        ("short", 2, "blocked_right_censored_incomplete_continuation"),
    ],
)
def test_every_censored_branch_preserves_observed_violations(
    continuation: str | None,
    deadline: int | None,
    expected: str,
) -> None:
    rows = [_continuation_hour(0)] if continuation == "short" else None
    assessment = assess_observed_continuation(
        anchor=_anchor(),
        continuation=rows,
        registered_completion_deadline_hours=deadline,
        state=replace(_state(), observed_violations=("available_flexibility",)),
    )
    assert assessment.status == expected
    assert assessment.observed_violations == ("available_flexibility",)


@pytest.mark.parametrize(
    "fault",
    [
        "cross_split",
        "power_gap",
        "workload_gap",
        "hash",
        "power_trajectory",
        "workload_identity",
        "normalization",
        "first_power_gap",
        "first_workload_gap",
        "first_split",
        "first_seed",
        "first_arm",
    ],
)
def test_continuation_rejects_split_gap_and_provenance_faults(fault: str) -> None:
    rows = [_continuation_hour(0), _continuation_hour(1)]
    if fault == "first_power_gap":
        rows[0] = replace(rows[0], power_source_hour=25)
    elif fault == "first_workload_gap":
        rows[0] = replace(rows[0], workload_source_hour=25)
    elif fault == "first_split":
        rows[0] = replace(rows[0], split="holdout")
    elif fault == "first_seed":
        rows[0] = replace(rows[0], power_outage_seed=20260823)
    elif fault == "first_arm":
        rows[0] = replace(rows[0], arm_id="network_only_shared")
    elif fault == "cross_split":
        rows[1] = replace(rows[1], split="holdout")
    elif fault == "power_gap":
        rows[1] = replace(rows[1], power_source_hour=26)
    elif fault == "workload_gap":
        rows[1] = replace(rows[1], workload_source_hour=26)
    elif fault == "power_trajectory":
        rows[1] = replace(rows[1], power_trajectory_id="outage-seed-20260823")
    elif fault == "workload_identity":
        rows[1] = replace(rows[1], workload_trace_id="other-trace")
    elif fault == "normalization":
        rows[1] = replace(rows[1], workload_normalization_sha256="5" * 64)
    else:
        rows[1] = replace(rows[1], power_provenance_sha256="3" * 64)
    with pytest.raises(ValueError):
        assess_observed_continuation(
            anchor=_anchor(),
            continuation=rows,
            registered_completion_deadline_hours=2,
        )


def test_missing_deadline_still_validates_observed_continuation() -> None:
    bad = replace(_continuation_hour(0), split="holdout")
    with pytest.raises(ValueError, match="cross-split"):
        assess_observed_continuation(
            anchor=_anchor(),
            continuation=[bad],
            registered_completion_deadline_hours=None,
        )


def test_continuation_rejects_state_from_another_arm_track() -> None:
    state = replace(
        _state(),
        arm_id="joint_b6_separate_planning_shared_execution",
        track_id="cfe",
    )
    with pytest.raises(ValueError, match="arm-track"):
        assess_observed_continuation(
            anchor=_anchor(),
            continuation=[_continuation_hour(0)],
            registered_completion_deadline_hours=None,
            state=state,
        )


def test_active_state_requires_prior_event_and_positive_event_count() -> None:
    with pytest.raises(ValueError, match="has_prior_event"):
        replace(_state(), event_count=0)


def test_unregistered_or_incomplete_tail_cannot_pass_completion_gate() -> None:
    missing_deadline = assess_observed_continuation(
        anchor=_anchor(),
        continuation=[_continuation_hour(0)],
        registered_completion_deadline_hours=None,
    )
    assert missing_deadline.status == "blocked_missing_registered_completion_deadline"
    short = assess_observed_continuation(
        anchor=_anchor(),
        continuation=[_continuation_hour(0)],
        registered_completion_deadline_hours=2,
    )
    assert short.status == "blocked_right_censored_incomplete_continuation"
    complete = assess_observed_continuation(
        anchor=_anchor(),
        continuation=[_continuation_hour(0), _continuation_hour(1)],
        registered_completion_deadline_hours=2,
    )
    assert complete.status == "continuation_inputs_complete_not_solved"
    assert not complete.completion_can_be_evaluated


def test_draft_protocol_keeps_all_execution_and_claim_gates_closed() -> None:
    config = _config()
    assert config["lifecycle"] == {
        "status": "DRAFT_NONAUTHORITATIVE",
        "pre_seal_audit_complete": False,
        "sealed_ready_for_independent_review": False,
        "independent_review_passed": False,
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }
    assert config["boundary_contract"]["service_hours"] == 24
    assert config["boundary_contract"]["hour_23_service_retained"] is True
    assert config["boundary_contract"]["default_tail_hours"] is None
    assert config["boundary_contract"]["unknown_continuation"] == (
        "blocked_right_censored"
    )
    assert config["service_mapping"]["additive_shared_call"][
        "unique_physical_truth_claimed"
    ] is False


@pytest.mark.parametrize(
    ("section", "key", "bad_value"),
    [
        ("authority", "may_open_any_execution_gate", True),
        ("audit_contract", "full_physical_training_support_audited", True),
        ("audit_contract", "absence_of_necessary_condition_means_feasible", True),
        ("audit_contract", "result_contingent_parameter_change_allowed", True),
        ("boundary_contract", "force_inactive_at_observation_end", True),
        ("boundary_contract", "force_zero_debt_at_observation_end", True),
        ("boundary_contract", "cross_split_continuation_allowed", True),
        ("boundary_contract", "debt_reset_at_boundary_allowed", True),
        ("output", "overwrite_allowed", True),
    ],
)
def test_draft_semantic_gates_fail_closed(
    tmp_path: Path,
    section: str,
    key: str,
    bad_value: object,
) -> None:
    config = deepcopy(_config())
    config[section][key] = bad_value
    path = tmp_path / "mutated.DRAFT.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError):
        audit_raw_training_support(path)


def test_written_diagnostic_is_self_hashing_and_non_authoritative(tmp_path: Path) -> None:
    from experiments.audit_rq2_joint_deliverability_boundary_v1 import write_diagnostic

    output = tmp_path / "diagnostic"
    summary = write_diagnostic(CONFIG, output_override=output)
    assert summary["evidence_level"] == "non_authoritative_zero_solver_diagnostic"
    assert summary["solver_calls"] == 0
    manifest = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"cells.json", "summary.json"}
    for name, expected in manifest.items():
        observed = hashlib.sha256((output / name).read_bytes()).hexdigest()
        assert observed == expected
    with pytest.raises(FileExistsError):
        write_diagnostic(CONFIG, output_override=output)


def test_relevant_sealed_and_input_hashes_remain_unchanged() -> None:
    expected = {
        "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml": (
            "19d61a2913e346090db23d01de587b650d8599999c40a78a291f627915ec2a69"
        ),
        "configs/rq2_joint_deliverability_preregistration_successor_v5.OUTER.SHA256SUMS.json": (
            "92a58498e1de5f84b132067e3d4a4443ae841747846785e9df54cd9afd7efdfd"
        ),
        "src/rq2_joint_deliverability_v2/scenarios.py": (
            "0dcb1879c1864746770b248a1383da0b8588bbae9571f0bb4dc9eab211c597dd"
        ),
        "src/rq2_joint_deliverability_v2/model.py": (
            "f79039fe018e2c581a044852b2418dd6e75d839b7f5d4a6f674cfea9fbdd6ccc"
        ),
        "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4/SHA256SUMS.json": (
            "28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63"
        ),
        "data/processed/model_inputs/alibaba_dimensionless_workload_blocks_v3/SHA256SUMS.json": (
            "62f2ec5eefd0c651d8b970a16fce4fb6336ccb75ab09e3d2c67386cc26edb524"
        ),
    }
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
