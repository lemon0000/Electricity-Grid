from __future__ import annotations

import csv
import gzip
import hashlib
import json
import math
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import yaml
from pyomo.environ import value

from experiments import run_rq2_joint_deliverability_implementation_v2 as runner
from experiments import (
    validate_rq2_joint_deliverability_implementation_v2 as implementation_validator,
)
from src.rq2_joint_deliverability_v2 import evaluation
from src.rq2_joint_deliverability_v2.model import (
    CFE_ONLY_SHARED,
    FOUR_ARM_IDS,
    JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    JOINT_CORRECT_SHARED,
    NETWORK_ONLY_SHARED,
    JointDeliverabilityPlanningInputs,
    JointDeliverabilityScenario,
    audit_fixed_service_trajectory,
    build_arm_planning_model,
    effective_request,
    solve_arm_minimum_capacity,
)
from src.rq2_joint_deliverability_v2.scenarios import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    PowerBlock,
    RegisteredCell,
    WorkloadBlock,
    build_pair_scenario,
    condition_finite_power,
    expand_registered_cells,
    load_power_blocks,
    network_capacity_key,
    raw_cfe_request,
    scenario_track_requirements,
    select_representatives,
    structural_recovery_witness,
)
from src.rq2_joint_deliverability_v2.solver_adapter import (
    Rq2SolverSpec,
    solver_options,
    solver_spec,
)

ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
)
IMPLEMENTATION = (
    ROOT / "configs/rq2_joint_deliverability_implementation_successor_v2.yaml"
)


def _design() -> dict:
    return yaml.safe_load(PREREGISTRATION.read_text(encoding="utf-8"))


def _registered_solver_spec() -> Rq2SolverSpec:
    return solver_spec(_design()["solver_contract"])


def _expected_cells() -> list[dict[str, object]]:
    return [asdict(cell) for cell in expand_registered_cells(_design())]


def _cell(**overrides: object) -> RegisteredCell:
    values = {
        "cell_id": "synthetic",
        "family": "synthetic_oracle",
        "hourly_cfe_target": 1.0,
        "flexible_fraction": 1.0,
        "normalized_recovery_headroom": 1.0,
        "recovery_efficiency": 1.0,
        "maximum_event_duration_hours": 4.0,
        "maximum_event_count": 2,
        "normalized_energy_budget": 2.0,
        "normalized_debt_limit": 1.0,
    }
    values.update(overrides)
    return RegisteredCell(**values)


def _power(
    block_id: str,
    probability: float = 1.0,
    *,
    state: str = FINITE_GRID_NEED,
    grid: tuple[float, ...] | None = None,
    cfe_at_one: tuple[float, ...] | None = None,
) -> PowerBlock:
    grid = grid or (0.0,) * 24
    cfe_at_one = cfe_at_one or (0.0,) * 24
    return PowerBlock(
        block_id=block_id,
        split="training",
        probability=probability,
        source_hours=tuple(range(24)),
        cfe_call_fraction_at_alpha_1=cfe_at_one,
        grid_need=((None,) * 24 if state == EXOGENOUS_GRID_INFEASIBILITY else grid),
        state=state,
    )


def _workload(
    block_id: str,
    probability: float = 1.0,
    *,
    values: tuple[float, ...] | None = None,
) -> WorkloadBlock:
    return WorkloadBlock(
        block_id=block_id,
        split="training",
        probability=probability,
        source_relative_hours=tuple(range(24)),
        raw_workload_fraction=values or (1.0,) * 24,
    )


def _planning_scenario(
    *,
    grid: tuple[float, ...],
    cfe: tuple[float, ...],
    business_headroom: tuple[float, ...],
    cfe_headroom: tuple[float, ...],
) -> JointDeliverabilityScenario:
    length = len(grid)
    return JointDeliverabilityScenario(
        name="synthetic",
        power_block_id="p",
        workload_block_id="w",
        probability=1.0,
        raw_grid_request=grid,
        raw_cfe_request=cfe,
        effective_grid_request=grid,
        effective_cfe_request=cfe,
        available_flexibility=(1.0,) * length,
        connected_demand=(1.0,) * length,
        business_recovery_headroom=business_headroom,
        cfe_service_recovery_headroom=cfe_headroom,
    )


def _planning_inputs(
    scenario: JointDeliverabilityScenario,
) -> JointDeliverabilityPlanningInputs:
    return JointDeliverabilityPlanningInputs(
        scenarios=(scenario,),
        time_step_hours=1.0,
        maximum_flexibility_budget=1.0,
        minimum_event_power=1.0e-6,
        response_time_hours=1.0,
        curtailment_ramp_per_hour=1.0,
        minimum_recovery_hours=1.0,
        recovery_efficiency=1.0,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_recovery_headroom=1.0,
        normalized_energy_budget=2.0,
        normalized_debt_limit=1.0,
        terminal_recovery_debt_limit=0.0,
        service_shortfall_tolerance=1.0e-6,
    )


def _candidate(
    arm_id: str,
    *,
    lower: float,
    incumbent: float,
    status: str = "candidate_resolved",
) -> dict[str, object]:
    specification = _registered_solver_spec()
    absolute_gap = incumbent - lower
    return {
        "arm_id": arm_id,
        "status": status,
        "incumbent_capacity": incumbent,
        "objective_lower_bound": lower,
        "objective_upper_bound": incumbent,
        "absolute_gap": absolute_gap,
        "incumbent_relative_gap": absolute_gap / max(abs(incumbent), 1.0e-12),
        "maximum_constraint_residual": 0.0,
        "termination_condition": "optimal",
        "solver_status": "ok",
        "model_variables": 1,
        "model_constraints": 1,
        "solver_name": specification.name,
        "solver_version": specification.expected_package_version,
        "solver_options": solver_options(specification),
    }


def test_exact_46_cell_inventory_and_network_alpha_cache_key() -> None:
    cells = expand_registered_cells(_design())

    assert len(cells) == 46
    assert sum(cell.family == "primary_factorial" for cell in cells) == 36
    assert sum(cell.family == "secondary_oat" for cell in cells) == 10
    assert len({cell.cell_id for cell in cells}) == 46
    groups: dict[tuple[object, ...], list[RegisteredCell]] = {}
    for cell in cells:
        groups.setdefault(network_capacity_key(cell), []).append(cell)
    assert any(len(group) == 4 for group in groups.values())
    assert all(
        len({network_capacity_key(cell) for cell in group}) == 1
        for group in groups.values()
    )


def test_target_specific_cfe_request_is_not_truncated_to_flexibility() -> None:
    assert raw_cfe_request(0.4, 0.5) == 0.0
    assert raw_cfe_request(0.8, 0.5) == pytest.approx(0.6)
    power = _power(
        "p",
        grid=(0.0,) * 24,
        cfe_at_one=(0.8,) + (0.0,) * 23,
    )
    workload = _workload(
        "w",
        values=(0.1,) + (1.0,) * 23,
    )
    scenario = build_pair_scenario(
        power,
        workload,
        _cell(hourly_cfe_target=0.5, flexible_fraction=0.2),
        service_shortfall_tolerance=1.0e-6,
    )

    assert scenario.raw_cfe_request[0] == pytest.approx(0.6)
    assert scenario.effective_cfe_request[0] == pytest.approx(0.6)
    assert scenario.available_flexibility[0] == pytest.approx(0.02)
    assert scenario.raw_cfe_request[0] > scenario.available_flexibility[0]


def test_recovery_builder_is_track_specific_and_cfe_compatible() -> None:
    power = _power(
        "p",
        cfe_at_one=(0.8, 0.0) + (0.0,) * 22,
    )
    workload = _workload(
        "w",
        values=(1.0, 0.0) + (1.0,) * 22,
    )
    scenario = build_pair_scenario(
        power,
        workload,
        _cell(
            hourly_cfe_target=1.0,
            normalized_recovery_headroom=0.5,
        ),
        service_shortfall_tolerance=1.0e-6,
    )

    assert scenario.business_recovery_headroom[1] == pytest.approx(0.5)
    assert scenario.cfe_service_recovery_headroom[1] == pytest.approx(0.0)
    b6_tracks = scenario_track_requirements(
        scenario,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    )
    assert b6_tracks[0][0] == "grid"
    assert b6_tracks[0][2] is scenario.business_recovery_headroom
    assert b6_tracks[1][0] == "cfe"
    assert b6_tracks[1][2] is scenario.cfe_service_recovery_headroom


def test_effective_request_threshold_is_closed() -> None:
    tolerance = 1.0e-6
    assert effective_request(tolerance, tolerance) == 0.0
    assert effective_request(math.nextafter(tolerance, math.inf), tolerance) > 0.0


def test_structural_recovery_witness_contains_auditable_identity() -> None:
    witness = structural_recovery_witness(
        cell_id="cell",
        arm_id=JOINT_CORRECT_SHARED,
        track_id="shared",
        power_block_id="p",
        workload_block_id="w",
        required_call=(0.2, 0.0),
        recovery_headroom=(0.0, 0.0),
        maximum_recovery_power=0.5,
        recovery_efficiency=0.85,
        initial_recovery_debt=0.0,
        terminal_recovery_debt_limit=0.0,
        time_step_hours=1.0,
        service_tolerance=1.0e-6,
        tolerance=1.0e-12,
    )

    assert witness is not None
    assert witness["terminal_debt_lower_bound"] == pytest.approx(0.2)
    assert witness["power_block_id"] == "p"
    assert witness["workload_block_id"] == "w"
    assert (
        structural_recovery_witness(
            cell_id="cell",
            arm_id=JOINT_CORRECT_SHARED,
            track_id="shared",
            power_block_id="p",
            workload_block_id="w",
            required_call=(1.0e-6, 0.0),
            recovery_headroom=(0.0, 0.0),
            maximum_recovery_power=0.5,
            recovery_efficiency=0.85,
            initial_recovery_debt=0.0,
            terminal_recovery_debt_limit=0.0,
            time_step_hours=1.0,
            service_tolerance=1.0e-6,
            tolerance=1.0e-12,
        )
        is None
    )


def test_structural_witness_validation_recomputes_debt_identity() -> None:
    cell = _cell(
        cell_id="cell",
        normalized_recovery_headroom=0.5,
        recovery_efficiency=0.85,
    )
    witness = structural_recovery_witness(
        cell_id=cell.cell_id,
        arm_id=JOINT_CORRECT_SHARED,
        track_id="shared",
        power_block_id="p",
        workload_block_id="w",
        required_call=(0.2,) + (0.0,) * 23,
        recovery_headroom=(0.0,) * 24,
        maximum_recovery_power=cell.normalized_recovery_headroom,
        recovery_efficiency=cell.recovery_efficiency,
        initial_recovery_debt=0.0,
        terminal_recovery_debt_limit=0.0,
        time_step_hours=1.0,
        service_tolerance=1.0e-6,
        tolerance=1.0e-12,
    )
    assert witness is not None
    evaluation._validate_structural_witness(
        witness,
        cell=asdict(cell),
        arm_id=JOINT_CORRECT_SHARED,
    )
    forged = {**witness, "terminal_debt_lower_bound": 0.1}
    with pytest.raises(ValueError, match="arithmetic"):
        evaluation._validate_structural_witness(
            forged,
            cell=asdict(cell),
            arm_id=JOINT_CORRECT_SHARED,
        )


def test_analytic_oracle_recovers_four_arm_capacity_difference() -> None:
    grid = (0.3,) + (0.0,) * 23
    cfe = (0.2,) + (0.0,) * 23
    headroom = (0.0, 0.5) + (0.0,) * 22
    inputs = _planning_inputs(
        _planning_scenario(
            grid=grid,
            cfe=cfe,
            business_headroom=headroom,
            cfe_headroom=headroom,
        )
    )

    capacities = {
        arm_id: audit_fixed_service_trajectory(inputs, arm_id).required_capacity
        for arm_id in FOUR_ARM_IDS
    }
    assert capacities == pytest.approx(
        {
            NETWORK_ONLY_SHARED: 0.3,
            CFE_ONLY_SHARED: 0.2,
            JOINT_CORRECT_SHARED: 0.5,
            JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION: 0.3,
        }
    )
    assert all(
        audit_fixed_service_trajectory(inputs, arm_id).feasible
        for arm_id in FOUR_ARM_IDS
    )


def test_analytic_oracle_exposes_wrong_recovery_headroom_reuse() -> None:
    grid = (0.0,) * 24
    cfe = (0.2,) + (0.0,) * 23
    business = (0.0, 0.5) + (0.0,) * 22
    cfe_headroom = (0.0,) * 24
    inputs = _planning_inputs(
        _planning_scenario(
            grid=grid,
            cfe=cfe,
            business_headroom=business,
            cfe_headroom=cfe_headroom,
        )
    )

    cfe_audit = audit_fixed_service_trajectory(inputs, CFE_ONLY_SHARED)
    network_audit = audit_fixed_service_trajectory(inputs, NETWORK_ONLY_SHARED)
    assert not cfe_audit.feasible
    assert "synthetic:shared:terminal_debt" in cfe_audit.violations
    assert network_audit.feasible


def test_pyomo_builder_uses_two_b6_tracks_and_one_shared_track() -> None:
    zeros = (0.0,) * 24
    inputs = _planning_inputs(
        _planning_scenario(
            grid=zeros,
            cfe=zeros,
            business_headroom=zeros,
            cfe_headroom=zeros,
        )
    )
    correct = build_arm_planning_model(inputs, JOINT_CORRECT_SHARED)
    b6 = build_arm_planning_model(
        inputs,
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    )

    assert tuple(correct.tracks) == ("shared",)
    assert tuple(b6.tracks) == ("grid", "cfe")
    assert len(b6.tracked_points) == 2 * len(correct.tracked_points)
    assert value(correct.minimum_capacity.expr, exception=False) is None


def test_capacity_intervals_and_signed_decomposition_are_fail_closed() -> None:
    values = {
        NETWORK_ONLY_SHARED: (0.1, 0.2),
        CFE_ONLY_SHARED: (0.3, 0.4),
        JOINT_CORRECT_SHARED: (0.5, 0.6),
        JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION: (0.45, 0.55),
    }
    arms = {
        arm_id: evaluation.CellArmCapacity(
            arm_id=arm_id,
            status=evaluation.RESOLVED,
            interval=evaluation.CapacityInterval(*interval),
            reported_point=interval[1],
            solver_certificate={"synthetic_interval_oracle": True},
            structural_witness=None,
            training_support_failures=(),
        )
        for arm_id, interval in values.items()
    }
    result = evaluation.capacity_attribution(arms)

    assert result["resolved"] is True
    assert result["contrasts"]["I_joint"] == pytest.approx({"lower": 0.1, "upper": 0.3})
    assert result["contrasts"]["I_sep"] == pytest.approx({"lower": 0.05, "upper": 0.25})
    assert result["contrasts"]["A_B6"] == pytest.approx({"lower": -0.05, "upper": 0.15})
    assert result["decomposition_residual"] == pytest.approx(0.0)
    assert result["interval_labels"]["I_joint"] == "robust_positive"
    assert result["interval_labels"]["A_B6"] == "numerically_indeterminate"
    assert result["labels"]["joint_extra_requirement"] is True
    assert result["labels"]["b6_capacity_indeterminate"] is True


def test_undefined_arm_suppresses_all_signed_capacity_labels() -> None:
    arms = {
        arm_id: evaluation.finalize_capacity_certificate(
            arm_id=arm_id,
            candidate=(
                None
                if arm_id == JOINT_CORRECT_SHARED
                else _candidate(arm_id, lower=0.1, incumbent=0.1)
            ),
        )
        for arm_id in FOUR_ARM_IDS
    }

    result = evaluation.capacity_attribution(arms)

    assert result["resolved"] is False
    assert result["contrasts"] is None
    assert result["interval_labels"] is None
    assert all(value == "not_evaluable" for value in result["labels"].values())


def test_structural_single_service_label_survives_other_unresolved_arms() -> None:
    arms = {
        arm_id: evaluation.finalize_capacity_certificate(
            arm_id=arm_id,
            structural_witness={"witness": True}
            if arm_id == NETWORK_ONLY_SHARED
            else None,
            candidate=None,
        )
        for arm_id in FOUR_ARM_IDS
    }

    result = evaluation.capacity_attribution(arms)

    assert result["labels"]["network_single_service_binding"] is True
    assert result["labels"]["cfe_single_service_binding"] == "not_evaluable"


def test_operational_quantifier_rejects_crossing_zero_and_uses_strict_bounds() -> None:
    crossing = {metric: (-0.2, 0.3) for metric in evaluation.OPERATIONAL_METRICS}
    assert evaluation.operational_labels(crossing) == {
        "b6_operational_penalty": False,
        "b6_operational_relief": False,
    }
    crossing[evaluation.OPERATIONAL_METRICS[0]] = (
        math.nextafter(1.0e-6, math.inf),
        0.2,
    )
    crossing[evaluation.OPERATIONAL_METRICS[1]] = (
        -0.2,
        math.nextafter(-1.0e-6, -math.inf),
    )
    assert evaluation.operational_labels(crossing) == {
        "b6_operational_penalty": True,
        "b6_operational_relief": True,
    }


def test_holdout_golden_trajectory_matches_sealed_v5_probe() -> None:
    design = _design()
    probe = design["holdout_policy"]["deterministic_probe"]
    temporal = design["temporal_envelope"]
    result = evaluation.execute_holdout_policy(
        committed_capacity=probe["committed_capacity"],
        grid_request=probe["grid_request"],
        cfe_request=probe["cfe_request"],
        available_flexibility=probe["available_flexibility"],
        connected_demand=probe["connected_demand"],
        current_recovery_headroom=probe["current_recovery_headroom"],
        maximum_recovery_power=probe["maximum_recovery_power"],
        recovery_efficiency=probe["recovery_efficiency"],
        maximum_event_duration_hours=probe["maximum_event_duration_hours"],
        maximum_event_count=probe["maximum_event_count"],
        minimum_recovery_hours=probe["minimum_recovery_hours"],
        normalized_energy_budget=probe["normalized_energy_budget"],
        normalized_debt_limit=probe["normalized_debt_limit"],
        terminal_recovery_debt_limit=temporal["terminal_recovery_debt_limit"],
        time_step_hours=design["data_contract"]["time_step_hours"],
        minimum_event_power=temporal["minimum_event_power"],
        curtailment_ramp_per_hour=temporal["curtailment_ramp_per_hour"],
        response_time_hours=temporal["response_time_hours"],
        service_shortfall_tolerance=temporal["service_shortfall_tolerance"],
    )

    assert [row["grid_served"] for row in result["trajectory"]] == pytest.approx(
        [0.3, 0.0, 0.2, 0.0, 0.0]
    )
    assert [row["cfe_served"] for row in result["trajectory"]] == pytest.approx(
        [0.2, 0.0, 0.3, 0.0, 0.0]
    )
    assert result["metrics"]["total_service_shortfall"] == pytest.approx(0.1)
    assert result["metrics"]["joint_service_failure"] is True
    projection = evaluation.sealed_holdout_probe_projection(result)
    assert (
        evaluation.canonical_certificate_sha256(projection)
        == (probe["canonical_trajectory_payload_sha256"])
    )


def test_holdout_runner_preserves_raw_requests_until_policy_preprocessing() -> None:
    tolerance = _design()["temporal_envelope"]["service_shortfall_tolerance"]
    scenario = replace(
        _planning_scenario(
            grid=(0.0,) * 24,
            cfe=(0.0,) * 24,
            business_headroom=(0.0,) * 24,
            cfe_headroom=(0.0,) * 24,
        ),
        raw_grid_request=(tolerance,) + (0.0,) * 23,
        raw_cfe_request=(tolerance / 2.0,) + (0.0,) * 23,
        effective_grid_request=(0.0,) * 24,
        effective_cfe_request=(0.0,) * 24,
    )

    grid, cfe, _ = runner._arm_holdout_arguments(
        scenario,
        JOINT_CORRECT_SHARED,
    )
    assert grid[0] == tolerance
    assert cfe[0] == tolerance / 2.0

    outcome = evaluation.execute_holdout_policy(
        committed_capacity=1.0,
        grid_request=grid,
        cfe_request=cfe,
        available_flexibility=(1.0,) * 24,
        connected_demand=(1.0,) * 24,
        current_recovery_headroom=(0.0,) * 24,
        maximum_recovery_power=0.0,
        recovery_efficiency=1.0,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        minimum_recovery_hours=1.0,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
        terminal_recovery_debt_limit=0.0,
        time_step_hours=1.0,
        minimum_event_power=tolerance,
        curtailment_ramp_per_hour=1.0,
        response_time_hours=1.0,
        service_shortfall_tolerance=tolerance,
    )
    assert outcome["trajectory"][0]["raw_grid_request"] == tolerance
    assert outcome["trajectory"][0]["raw_cfe_request"] == tolerance / 2.0
    assert outcome["trajectory"][0]["effective_grid_request"] == 0.0
    assert outcome["trajectory"][0]["effective_cfe_request"] == 0.0


def test_planning_input_hash_binds_raw_requests_by_arm() -> None:
    zeros = (0.0,) * 24
    base = _planning_scenario(
        grid=zeros,
        cfe=zeros,
        business_headroom=zeros,
        cfe_headroom=zeros,
    )
    raw_grid_changed = replace(
        base,
        raw_grid_request=(1.0e-6,) + zeros[1:],
    )
    raw_cfe_changed = replace(
        base,
        raw_cfe_request=(1.0e-6,) + zeros[1:],
    )
    specification = _registered_solver_spec()

    base_network = runner._planning_input_sha256(
        _planning_inputs(base),
        NETWORK_ONLY_SHARED,
        specification,
    )
    assert base_network != runner._planning_input_sha256(
        _planning_inputs(raw_grid_changed),
        NETWORK_ONLY_SHARED,
        specification,
    )
    assert base_network == runner._planning_input_sha256(
        _planning_inputs(raw_cfe_changed),
        NETWORK_ONLY_SHARED,
        specification,
    )
    assert runner._planning_input_sha256(
        _planning_inputs(base),
        JOINT_CORRECT_SHARED,
        specification,
    ) != runner._planning_input_sha256(
        _planning_inputs(raw_cfe_changed),
        JOINT_CORRECT_SHARED,
        specification,
    )


def test_all_e0_has_no_finite_denominator_or_transport_call() -> None:
    result = evaluation.finite_conditioning(
        ["p0", "p1"],
        [0.25, 0.75],
        {
            "p0": EXOGENOUS_GRID_INFEASIBILITY,
            "p1": EXOGENOUS_GRID_INFEASIBILITY,
        },
    )

    assert result["status"] == "finite_service_identification_unresolved"
    assert result["E0_mass"] == pytest.approx(1.0)
    assert result["transport_solver_called"] is False


def test_scalar_transport_certificate_checks_analytic_primal_and_dual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lower = SimpleNamespace(
        success=True,
        status=0,
        x=np.asarray([0.4, 0.0, 0.1, 0.5]),
        eqlin=SimpleNamespace(marginals=np.asarray([-2.0, 0.0, 2.0])),
        message="Optimal",
    )
    upper = SimpleNamespace(
        success=True,
        status=0,
        x=np.asarray([0.0, 0.4, 0.5, 0.1]),
        eqlin=SimpleNamespace(marginals=np.asarray([-1.0, 0.0, -2.0])),
        message="Optimal",
    )
    calls = iter((lower, upper))
    monkeypatch.setattr(evaluation, "linprog", lambda *args, **kwargs: next(calls))
    certificate = evaluation.certify_scalar_transport(
        [0.4, 0.6],
        [0.5, 0.5],
        [[0.0, 1.0], [2.0, 0.0]],
        metric_name="probe",
        require_registered_environment=False,
    )

    assert certificate.resolved
    assert certificate.lower is not None
    assert certificate.upper is not None
    assert certificate.lower.value == pytest.approx(0.2)
    assert certificate.upper.value == pytest.approx(1.4)
    assert certificate.lower.primal_dual_gap <= 1.0e-8
    assert certificate.upper.dual_feasibility_residual <= 1.0e-8


def test_transport_certificate_fails_closed_on_invalid_dual(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = SimpleNamespace(
        success=True,
        status=0,
        x=np.asarray([0.4, 0.0, 0.1, 0.5]),
        eqlin=SimpleNamespace(marginals=np.asarray([100.0, 0.0, 0.0])),
        message="Optimal",
    )
    monkeypatch.setattr(evaluation, "linprog", lambda *args, **kwargs: invalid)
    certificate = evaluation.certify_scalar_transport(
        [0.4, 0.6],
        [0.5, 0.5],
        [[0.0, 1.0], [2.0, 0.0]],
        metric_name="probe",
        require_registered_environment=False,
    )

    assert not certificate.resolved
    assert certificate.lower is None
    assert certificate.unresolved_reason is not None


def test_transport_attempts_both_endpoints_after_lower_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = 0

    def fail(*args: object, **kwargs: object) -> object:
        nonlocal calls
        del args, kwargs
        calls += 1
        raise RuntimeError("synthetic endpoint failure")

    monkeypatch.setattr(evaluation, "linprog", fail)
    certificate = evaluation.certify_scalar_transport(
        [0.4, 0.6],
        [0.5, 0.5],
        [[0.0, 1.0], [2.0, 0.0]],
        metric_name="probe",
        require_registered_environment=False,
    )

    assert calls == 2
    assert certificate.resolved is False
    assert certificate.unresolved_reason is not None
    assert "lower:" in certificate.unresolved_reason
    assert "upper:" in certificate.unresolved_reason


def test_representative_selection_is_finite_only_and_uses_utf8_ties() -> None:
    finite, e0_mass = condition_finite_power(
        (
            _power("z", 0.2, state=EXOGENOUS_GRID_INFEASIBILITY),
            _power("b", 0.4),
            _power("a", 0.4),
        )
    )
    selected = select_representatives(
        finite,
        role="power",
        quantile_targets=(0.25, 0.75),
    )

    assert e0_mass == pytest.approx(0.2)
    assert [block.block_id for block in selected] == ["a", "b"]
    assert sum(block.probability for block in selected) == pytest.approx(1.0)


@pytest.mark.parametrize("invalid_side", ("power", "workload"))
def test_capacity_representatives_reject_nontraining_input_before_conditioning(
    invalid_side: str,
) -> None:
    power = (
        replace(
            _power(
                "e0",
                0.2,
                state=EXOGENOUS_GRID_INFEASIBILITY,
            ),
            split="holdout" if invalid_side == "power" else "training",
        ),
        *tuple(_power(f"p{index}", 0.1) for index in range(8)),
    )
    workload = tuple(
        replace(
            _workload(f"w{index}", 0.125),
            split=(
                "holdout" if invalid_side == "workload" and index == 0 else "training"
            ),
        )
        for index in range(8)
    )

    with pytest.raises(ValueError, match="non-training"):
        runner._representatives(_design(), power, workload)


def test_bootstrap_probe_uses_registered_rng_and_draw_order() -> None:
    design = _design()["bootstrap_contract"]
    probe = design["deterministic_probe"]
    raw = evaluation.bootstrap_raw_draw_stream(
        probe["power_IDs"],
        probe["power_probabilities"],
        probe["workload_IDs"],
        probe["workload_probabilities"],
        power_draw_count=probe["power_draw_count"],
        workload_draw_count=probe["workload_draw_count"],
        replicates=probe["replicates"],
        seed=design["pseudorandom_generator"]["seed"],
    )
    digest = hashlib.sha256(
        (
            json.dumps(
                raw,
                allow_nan=False,
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
            + "\n"
        ).encode()
    ).hexdigest()

    assert digest == probe["canonical_draw_payload_sha256"]


def test_canonical_certificate_serialization_uses_float_hex() -> None:
    payload = evaluation.canonical_certificate_payload(
        {"interval": evaluation.CapacityInterval(0.1, 0.2)}
    )
    decoded = json.loads(payload)

    assert decoded["interval"] == {
        "lower": (0.1).hex(),
        "upper": (0.2).hex(),
    }


def test_implementation_candidate_validates_without_solver_or_writes() -> None:
    config = implementation_validator._load_yaml(IMPLEMENTATION)
    require_sealed = (
        config["lifecycle"]["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    )
    report = implementation_validator.validate(config, require_sealed=require_sealed)
    runtime_report = runner.run(validate_only=True)

    assert report["valid"] is True
    assert report["unique_solver_task_count"] == 157
    assert report["solver_calls"] == 0
    assert runtime_report["formal_execution_ready"] is False
    assert runtime_report["result_files_written"] == 0
    with pytest.raises(RuntimeError, match="not authorized"):
        runner.run(validate_only=False)


def test_v2_dependency_inventory_is_explicit_and_local() -> None:
    config = implementation_validator._load_yaml(IMPLEMENTATION)
    assert config["local_dependencies"] == {
        "experiments_package_initializer": {
            "path": "experiments/__init__.py",
        },
        "implementation_package_initializer": {
            "path": "src/rq2_joint_deliverability_v2/__init__.py",
        },
        "src_package_initializer": {
            "path": "src/__init__.py",
        },
        "solver_adapter": {
            "path": "src/rq2_joint_deliverability_v2/solver_adapter.py",
        },
    }
    model_imports = implementation_validator._imports(
        ROOT / implementation_validator.MODEL_RELATIVE
    )
    assert "src.models.economic_temporal_stochastic" not in model_imports
    assert "solver_adapter" in model_imports
    implementation_validator._validate_predecessor_authority(config)


def test_v2_fresh_process_import_closure_is_manifest_bound() -> None:
    script = """
import json
import sys
from pathlib import Path

root = Path.cwd().resolve()
import experiments.run_rq2_joint_deliverability_implementation_v2  # noqa: F401

observed = set()
for module in sys.modules.values():
    raw = getattr(module, "__file__", None)
    if raw is None:
        continue
    path = Path(raw).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        continue
    if relative.suffix == ".py":
        observed.add(relative.as_posix())
print(json.dumps(sorted(observed)))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    observed = set(json.loads(completed.stdout))

    assert observed == implementation_validator.EXPECTED_RUNTIME_MODULES
    assert observed <= implementation_validator.EXPECTED_MEMBERS


def test_validator_rejects_closed_gate_and_contract_mutations() -> None:
    original = implementation_validator._load_yaml(IMPLEMENTATION)
    require_sealed = (
        original["lifecycle"]["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    )
    mutations = (
        ("scope", "formal_execution", True),
        ("solver_contract", "timeout_is_infeasible", True),
        ("output_contract", "required_schemas", []),
        ("validation_contract", "analytic_oracles", []),
        (
            "validation_contract",
            "validator_imports_or_calls_optimization_solver",
            True,
        ),
    )
    for section, key, replacement in mutations:
        candidate = deepcopy(original)
        candidate[section][key] = replacement
        with pytest.raises(ValueError):
            implementation_validator.validate(
                candidate,
                require_sealed=require_sealed,
            )


def test_validator_rejects_live_v5_member_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    relative_paths = {
        implementation_validator.V5_OUTER_RELATIVE,
        implementation_validator.V5_INNER_RELATIVE,
        implementation_validator.V5_REVIEW_RELATIVE,
        *implementation_validator.V5_MEMBERS,
    }
    for relative in relative_paths:
        source = ROOT / relative
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    scientific = tmp_path / (
        "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
    )
    scientific.write_bytes(scientific.read_bytes() + b"\n")
    monkeypatch.setattr(implementation_validator, "ROOT", tmp_path)

    with pytest.raises(ValueError, match="scientific member SHA-256"):
        implementation_validator._validate_authority(
            implementation_validator._load_yaml(IMPLEMENTATION)
        )


def test_capacity_stage_reuses_exact_network_only_tasks() -> None:
    probability = 1.0 / 8.0
    training_power = tuple(_power(f"p{index}", probability) for index in range(8))
    training_workload = tuple(_workload(f"w{index}", probability) for index in range(8))
    calls: list[tuple[str, float]] = []

    def analytic_solver(
        inputs: JointDeliverabilityPlanningInputs,
        arm_id: str,
        specification: Rq2SolverSpec,
    ) -> dict[str, object]:
        del specification
        audit = audit_fixed_service_trajectory(inputs, arm_id)
        calls.append((arm_id, audit.required_capacity))
        return _candidate(
            arm_id,
            lower=audit.required_capacity,
            incumbent=audit.required_capacity,
        )

    result = runner.execute_capacity_stage(
        _design(),
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=_registered_solver_spec(),
        solve_callback=analytic_solver,
    )

    assert result["cell_count"] == 46
    assert result["arm_output_count"] == 184
    assert result["representative_solver_calls"] == 157
    assert result["full_support_fallback_solver_calls"] == 0
    assert result["total_solver_calls"] == 157
    assert len(calls) == 157
    assert sum(arm_id == NETWORK_ONLY_SHARED for arm_id, _ in calls) == 19
    assert (
        len(
            {
                cell["arms"][NETWORK_ONLY_SHARED]["planning_input_sha256"]
                for cell in result["cells"]
            }
        )
        == 19
    )
    assert len(result["frontier_summary"]["primary_strata"]) == 9
    assert all(
        cell["capacity_attribution"]["resolved"] is True for cell in result["cells"]
    )


def test_capacity_stage_rejects_fallback_batch_size_drift() -> None:
    with pytest.raises(ValueError, match="batch size drifted"):
        runner.execute_capacity_stage(
            _design(),
            training_power_blocks=(),
            training_workload_blocks=(),
            solver_specification=_registered_solver_spec(),
            full_support_batch_size=255,
        )


def test_full_support_capacity_exceedance_invalidates_representative_candidate() -> (
    None
):
    low_probability = 0.99 / 8.0
    training_power = tuple(
        _power(f"p{index}", low_probability) for index in range(8)
    ) + (
        _power(
            "z-high",
            0.01,
            grid=(0.04,) + (0.0,) * 23,
        ),
    )
    workload_shape = (1.0, 0.0) + (1.0,) * 22
    training_workload = tuple(
        _workload(
            f"w{index}",
            1.0 / 8.0,
            values=workload_shape,
        )
        for index in range(8)
    )

    def zero_candidate(
        inputs: JointDeliverabilityPlanningInputs,
        arm_id: str,
        specification: Rq2SolverSpec,
    ) -> dict[str, object]:
        del inputs, specification
        return _candidate(arm_id, lower=0.0, incumbent=0.0)

    result = runner.execute_capacity_stage(
        _design(),
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=_registered_solver_spec(),
        solve_callback=zero_candidate,
    )
    target = next(
        cell for cell in result["cells"] if cell["cell_id"] == "primary_a050_f050_h010"
    )

    assert target["arms"][NETWORK_ONLY_SHARED]["status"] == (
        "training_support_failure_estimand_undefined"
    )
    assert target["capacity_attribution"]["resolved"] is False


def test_full_support_grid_excess_bridge_uses_exact_fallback() -> None:
    zeros = (0.0,) * 24
    grid = (0.1, 0.0, 0.1) + (0.0,) * 21
    scenario = JointDeliverabilityScenario(
        name="p__w",
        power_block_id="p",
        workload_block_id="w",
        probability=1.0,
        raw_grid_request=grid,
        raw_cfe_request=zeros,
        effective_grid_request=grid,
        effective_cfe_request=zeros,
        available_flexibility=(1.0,) * 24,
        connected_demand=(1.0,) * 24,
        business_recovery_headroom=(1.0,) * 24,
        cfe_service_recovery_headroom=(1.0,) * 24,
    )
    inputs = replace(
        _planning_inputs(scenario),
        maximum_event_count=1,
        normalized_energy_budget=1.0,
    )
    fixed = audit_fixed_service_trajectory(inputs, NETWORK_ONLY_SHARED)
    specification = Rq2SolverSpec(
        name="highs",
        expected_package_version="1.15.1",
        threads=1,
        mip_relative_gap=1.0e-9,
        feasibility_tolerance=1.0e-8,
        optimality_tolerance=1.0e-8,
        integer_feasibility_tolerance=1.0e-8,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )

    result = runner._audit_full_support_candidate(
        inputs,
        NETWORK_ONLY_SHARED,
        incumbent_capacity=0.1,
        solver_specification=specification,
        solve=lambda value, arm, spec: solve_arm_minimum_capacity(
            value,
            arm,
            solver_specification=spec,
        ),
        batch_size=256,
    )

    assert fixed.feasible is False
    assert fixed.violations == ("p__w:shared:event_count",)
    assert result["status"] == "passed"
    assert result["fallback_scenario_count"] == 1
    assert result["fallback_solver_calls"] == 1


def test_incomplete_solver_certificate_cannot_resolve_capacity() -> None:
    with pytest.raises(ValueError, match="field inventory"):
        evaluation.finalize_capacity_certificate(
            arm_id=NETWORK_ONLY_SHARED,
            candidate={
                "arm_id": NETWORK_ONLY_SHARED,
                "status": "candidate_resolved",
                "incumbent_capacity": 0.1,
                "objective_lower_bound": 0.1,
            },
        )


def test_resolved_solver_certificate_rejects_status_and_gap_drift() -> None:
    warning = _candidate(NETWORK_ONLY_SHARED, lower=0.1, incumbent=0.1)
    warning["solver_status"] = "warning"
    with pytest.raises(ValueError, match="inconsistent"):
        evaluation.finalize_capacity_certificate(
            arm_id=NETWORK_ONLY_SHARED,
            candidate=warning,
        )

    excessive_gap = _candidate(NETWORK_ONLY_SHARED, lower=0.5, incumbent=1.0)
    with pytest.raises(ValueError, match="inconsistent"):
        evaluation.finalize_capacity_certificate(
            arm_id=NETWORK_ONLY_SHARED,
            candidate=excessive_gap,
        )


def test_proven_infeasible_certificate_rejects_invalid_status_pair() -> None:
    certificate = _candidate(
        NETWORK_ONLY_SHARED,
        lower=0.0,
        incumbent=0.0,
        status=evaluation.PROVEN_INFEASIBLE,
    )
    certificate.update(
        {
            "incumbent_capacity": None,
            "objective_lower_bound": None,
            "objective_upper_bound": None,
            "absolute_gap": None,
            "incumbent_relative_gap": None,
            "maximum_constraint_residual": None,
            "termination_condition": "infeasible",
            "solver_status": "error",
        }
    )

    with pytest.raises(ValueError, match="inconsistent"):
        evaluation.finalize_capacity_certificate(
            arm_id=NETWORK_ONLY_SHARED,
            candidate=certificate,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("objective_lower_bound", 0.0),
        ("objective_upper_bound", 1.0),
        ("absolute_gap", 1.0),
        ("incumbent_relative_gap", 1.0),
        ("maximum_constraint_residual", 0.0),
    ),
)
def test_proven_infeasible_certificate_rejects_stale_numeric_fields(
    field: str,
    value: float,
) -> None:
    certificate = _candidate(
        NETWORK_ONLY_SHARED,
        lower=0.0,
        incumbent=0.0,
        status=evaluation.PROVEN_INFEASIBLE,
    )
    certificate.update(
        {
            "incumbent_capacity": None,
            "objective_lower_bound": None,
            "objective_upper_bound": None,
            "absolute_gap": None,
            "incumbent_relative_gap": None,
            "maximum_constraint_residual": None,
            "termination_condition": "infeasible",
            "solver_status": "ok",
            field: value,
        }
    )

    with pytest.raises(ValueError, match="inconsistent"):
        evaluation.finalize_capacity_certificate(
            arm_id=NETWORK_ONLY_SHARED,
            candidate=certificate,
        )


def _zero_capacity_frontier() -> dict[str, object]:
    task_hashes = {
        (str(task["cell_id"]), str(task["arm_id"])): str(task["solve_key"])
        for task in runner.planning_task_inventory(_design())
    }
    rows = []
    for cell in expand_registered_cells(_design()):
        typed_arms = {
            arm_id: evaluation.finalize_capacity_certificate(
                arm_id=arm_id,
                candidate=_candidate(arm_id, lower=0.0, incumbent=0.0),
            )
            for arm_id in FOUR_ARM_IDS
        }
        arms = {
            arm_id: {
                **asdict(typed_arms[arm_id]),
                "planning_input_sha256": task_hashes[(cell.cell_id, arm_id)],
                "full_support_audit": {
                    "status": "passed",
                    "failures": [],
                    "fallback_scenario_count": 0,
                    "fallback_solver_calls": 0,
                    "fallback_certificates": [],
                },
            }
            for arm_id in FOUR_ARM_IDS
        }
        rows.append(
            {
                "cell_id": cell.cell_id,
                "family": cell.family,
                "parameters": asdict(cell),
                "arms": arms,
                "capacity_attribution": evaluation.capacity_attribution(typed_arms),
            }
        )
    frontier = {
        "schema": "rq2_joint_deliverability_capacity_frontier_v3",
        "cell_count": 46,
        "arm_output_count": 184,
        "representative_solver_calls": 157,
        "full_support_fallback_solver_calls": 0,
        "total_solver_calls": 157,
        "network_alpha_reuse_count": 27,
        "training_E0_mass": 0.0,
        "representative_power_ids": [f"p{index}" for index in range(8)],
        "representative_workload_ids": [f"w{index}" for index in range(8)],
        "cells": rows,
    }
    frontier["frontier_summary"] = runner._frontier_summary(rows)
    return frontier


def _zero_transport_certificate(
    rows: object,
    columns: object,
    matrix: object,
    *,
    metric_name: str,
) -> evaluation.ScalarTransportCertificate:
    del rows, columns, matrix
    endpoint = evaluation.TransportEndpoint(
        extremum="lower",
        value=0.0,
        coupling_row_major=(1.0,),
        dual_equality_variables=(0.0,),
        primal_objective_min_form=0.0,
        dual_objective_min_form=0.0,
        primal_dual_gap=0.0,
        marginal_residual=0.0,
        dual_feasibility_residual=0.0,
        solver_status="analytic",
    )
    return evaluation.ScalarTransportCertificate(
        schema="rq2_joint_deliverability_transport_certificate_v3",
        metric=metric_name,
        resolved=True,
        sharp=True,
        lower=endpoint,
        upper=replace(endpoint, extremum="upper"),
        unresolved_reason=None,
    )


def test_transport_output_validation_recomputes_the_primal_objective() -> None:
    certificate = json.loads(
        evaluation.canonical_certificate_payload(
            _zero_transport_certificate(
                [1.0],
                [1.0],
                [[0.0]],
                metric_name="probe",
            )
        )
    )

    with pytest.raises(ValueError, match="certificate is inconsistent"):
        evaluation._validate_transport_certificate(
            certificate,
            "probe",
            row_probabilities=[1.0],
            column_probabilities=[1.0],
            metric_matrix=[[1.0]],
        )


def test_bootstrap_recomputes_every_registered_endpoint() -> None:
    metric_matrices = {
        "cell": {metric: {("p", "w"): 0.0} for metric in evaluation.REGISTERED_METRICS}
    }
    draws = [
        {
            "replicate": replicate,
            "power": {"p": 1.0},
            "workload": {"w": 1.0},
        }
        for replicate in range(2)
    ]

    result = evaluation.bootstrap_transport_intervals(
        draws=draws,
        state_by_power_id={"p": FINITE_GRID_NEED},
        metric_matrices=metric_matrices,
        endpoint_solver=_zero_transport_certificate,
    )

    assert result["status"] == "resolved"
    assert result["replicates"] == 2
    assert result["endpoint_solver_calls"] == 2 * 2 * 23
    assert result["intervals"]["cell"]["B6_minus_correct_joint_service_failure"] == {
        "lower": [0.0, 0.0],
        "upper": [0.0, 0.0],
    }


def test_holdout_and_identification_stages_preserve_scalar_quantifier() -> None:
    holdout = runner.execute_holdout_stage(
        _design(),
        capacity_frontier=_zero_capacity_frontier(),
        holdout_power_blocks=(replace(_power("p"), split="holdout"),),
        holdout_workload_blocks=(replace(_workload("w"), split="holdout"),),
        retain_trajectories=False,
    )
    identified = runner.execute_identification_stage(
        _design(),
        capacity_frontier=_zero_capacity_frontier(),
        holdout=holdout,
        transport_solver=_zero_transport_certificate,
        execute_bootstrap=False,
    )

    assert holdout["schema"] == "rq2_joint_deliverability_holdout_v3"
    assert holdout["trajectories_retained"] is False
    assert holdout["trajectory_hash_count"] == 184
    assert identified["status"] == "resolved"
    assert identified["transport_solver_calls"] == 2 * 46 * 23
    assert identified["bootstrap"]["status"] == "not_executed"
    assert [row["cell_id"] for row in identified["cells"]] == [
        row["cell_id"] for row in holdout["cells"]
    ]
    assert identified["cells"][0]["operational_labels"] == {
        "b6_operational_penalty": False,
        "b6_operational_relief": False,
    }
    assert (
        identified["cells"][0]["capacity_attribution"]["labels"][
            "network_single_service_binding"
        ]
        is False
    )
    assert isinstance(
        identified["cells"][0]["transport_certificates"][
            "network_only_joint_service_failure"
        ]["lower"]["value"],
        str,
    )


def test_holdout_rejects_resolved_arm_without_full_support_pass() -> None:
    frontier = _zero_capacity_frontier()
    frontier["cells"][0]["arms"][NETWORK_ONLY_SHARED]["full_support_audit"][
        "status"
    ] = "unresolved"

    with pytest.raises(ValueError, match="full-support audit"):
        runner.execute_holdout_stage(
            _design(),
            capacity_frontier=frontier,
            holdout_power_blocks=(replace(_power("p"), split="holdout"),),
            holdout_workload_blocks=(replace(_workload("w"), split="holdout"),),
        )


def test_all_e0_holdout_skips_transport_stage() -> None:
    holdout = runner.execute_holdout_stage(
        _design(),
        capacity_frontier=_zero_capacity_frontier(),
        holdout_power_blocks=(
            replace(
                _power(
                    "p",
                    state=EXOGENOUS_GRID_INFEASIBILITY,
                ),
                split="holdout",
            ),
        ),
        holdout_workload_blocks=(replace(_workload("w"), split="holdout"),),
        retain_trajectories=False,
    )
    identified = runner.execute_identification_stage(
        _design(),
        capacity_frontier=_zero_capacity_frontier(),
        holdout=holdout,
        transport_solver=lambda *args, **kwargs: pytest.fail(
            "transport must not run for all-E0"
        ),
    )

    assert holdout["E0_mass"] == pytest.approx(1.0)
    assert identified["status"] == "finite_service_identification_unresolved"
    assert identified["transport_solver_calls"] == 0
    assert len(identified["cells"]) == 46


def _output_payloads(
    root: Path,
) -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    digest = "a" * 64
    code = root / "module.py"
    source = root / "input.json"
    code.write_text("pass\n", encoding="utf-8")
    source.write_text("{}\n", encoding="utf-8")
    provenance = {
        "schema": "rq2_joint_deliverability_provenance_v1",
        "scientific_outer_sha256": digest,
        "scientific_review_sha256": digest,
        "implementation_outer_sha256": digest,
        "code_sha256": {"module.py": hashlib.sha256(code.read_bytes()).hexdigest()},
        "input_manifest_sha256": {
            "input.json": hashlib.sha256(source.read_bytes()).hexdigest()
        },
        "software": {"python": "3.11.15"},
    }
    capacity = _zero_capacity_frontier()
    holdout = {
        "schema": "rq2_joint_deliverability_holdout_v3",
        "E0_mass": 1.0,
        "E0_power_block_ids": ["p"],
        "finite_power_block_ids": [],
        "workload_block_ids": ["w"],
        "power_marginal": [
            {
                "block_id": "p",
                "probability": 1.0,
                "state": EXOGENOUS_GRID_INFEASIBILITY,
            }
        ],
        "workload_marginal": [{"block_id": "w", "probability": 1.0}],
        "trajectories_retained": False,
        "trajectory_hash_count": 0,
        "trajectory_hash_stream_sha256": hashlib.sha256().hexdigest(),
        "cells": [
            {
                "cell_id": row["cell_id"],
                "status": "finite_service_identification_unresolved",
                "pairs": [],
            }
            for row in capacity["cells"]
        ],
    }
    identification = {
        "schema": "rq2_joint_deliverability_identification_v3",
        "status": "finite_service_identification_unresolved",
        "E0_mass": 1.0,
        "transport_solver_calls": 0,
        "bootstrap": {
            "status": "unresolved",
            "reason": "empty_finite_support",
            "endpoint_solver_calls": 0,
            "intervals": None,
        },
        "cells": [
            {
                "cell_id": row["cell_id"],
                "status": "finite_service_identification_unresolved",
                "capacity_attribution": row["capacity_attribution"],
                "transport_certificates": None,
                "operational_labels": None,
            }
            for row in capacity["cells"]
        ],
    }
    report = runner.build_report(
        capacity_frontier=capacity,
        holdout=holdout,
        identification=identification,
        provenance=provenance,
    )
    payloads = {
        "capacity_frontier.json": capacity,
        "holdout.json": holdout,
        "identification.json": identification,
        "report.json": report,
        "provenance.json": provenance,
    }
    return payloads, {
        key: value for key, value in provenance.items() if key != "schema"
    }


def test_finite_runner_outputs_pass_nested_output_validation(tmp_path: Path) -> None:
    template, expected = _output_payloads(tmp_path)
    capacity = _zero_capacity_frontier()
    holdout = runner.execute_holdout_stage(
        _design(),
        capacity_frontier=capacity,
        holdout_power_blocks=(replace(_power("p"), split="holdout"),),
        holdout_workload_blocks=(replace(_workload("w"), split="holdout"),),
    )
    identification = runner.execute_identification_stage(
        _design(),
        capacity_frontier=capacity,
        holdout=holdout,
        transport_solver=_zero_transport_certificate,
        execute_bootstrap=False,
    )
    evaluated = sorted(
        (str(row["cell_id"]) for row in identification["cells"]),
        key=lambda item: item.encode("utf-8"),
    )
    identification["bootstrap"] = {
        "status": "resolved",
        "replicates": 200,
        "endpoint_solver_calls": 200 * 46 * len(evaluation.REGISTERED_METRICS) * 2,
        "intervals": {
            cell_id: {
                metric: {"lower": [0.0, 0.0], "upper": [0.0, 0.0]}
                for metric in evaluation.REGISTERED_METRICS
            }
            for cell_id in evaluated
        },
        "evaluated_cell_ids": evaluated,
        "not_evaluable_cell_ids": [],
    }
    payloads = {
        "capacity_frontier.json": capacity,
        "holdout.json": holdout,
        "identification.json": identification,
        "provenance.json": template["provenance.json"],
    }
    payloads["report.json"] = runner.build_report(
        capacity_frontier=capacity,
        holdout=holdout,
        identification=identification,
        provenance=payloads["provenance.json"],
    )

    evaluation.validate_output_payloads(
        payloads,
        expected_provenance=expected,
        provenance_root=tmp_path,
        expected_cells=_expected_cells(),
        expected_solver_specification=_registered_solver_spec(),
    )


def test_atomic_output_publication_has_exact_recursive_manifest(
    tmp_path: Path,
) -> None:
    target = tmp_path / "published"
    payloads, expected = _output_payloads(tmp_path)
    manifest = evaluation.publish_output_bundle(
        target,
        payloads,
        expected_provenance=expected,
        provenance_root=tmp_path,
        expected_cells=_expected_cells(),
        expected_solver_specification=_registered_solver_spec(),
    )

    assert set(manifest["files"]) == set(evaluation.OUTPUT_SCHEMAS)
    assert evaluation.recursive_manifest(target) == manifest
    assert (tmp_path / "published.PUBLISHED" / "success.json").is_file()
    with pytest.raises(FileExistsError):
        evaluation.publish_output_bundle(
            target,
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )


def test_output_validation_rejects_unexecuted_bootstrap(tmp_path: Path) -> None:
    payloads, expected = _output_payloads(tmp_path)
    payloads["identification.json"]["bootstrap"]["status"] = "not_executed"
    payloads["report.json"] = runner.build_report(
        capacity_frontier=payloads["capacity_frontier.json"],
        holdout=payloads["holdout.json"],
        identification=payloads["identification.json"],
        provenance=payloads["provenance.json"],
    )

    with pytest.raises(ValueError, match="bootstrap"):
        evaluation.publish_output_bundle(
            tmp_path / "rejected-bootstrap",
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )


@pytest.mark.parametrize("fallback_status", ("capacity_exceeds", "infeasible"))
def test_output_validation_rejects_forged_passed_fallback(
    tmp_path: Path,
    fallback_status: str,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    capacity = payloads["capacity_frontier.json"]
    arm = capacity["cells"][0]["arms"][NETWORK_ONLY_SHARED]
    if fallback_status == "capacity_exceeds":
        fallback = _candidate(
            NETWORK_ONLY_SHARED,
            lower=0.5,
            incumbent=0.5,
        )
    else:
        fallback = _candidate(
            NETWORK_ONLY_SHARED,
            lower=0.0,
            incumbent=0.0,
        )
        fallback.update(
            {
                "status": evaluation.PROVEN_INFEASIBLE,
                "incumbent_capacity": None,
                "objective_lower_bound": None,
                "objective_upper_bound": None,
                "absolute_gap": None,
                "incumbent_relative_gap": None,
                "maximum_constraint_residual": None,
                "termination_condition": "infeasible",
            }
        )
    arm["full_support_audit"].update(
        {
            "fallback_scenario_count": 1,
            "fallback_solver_calls": 1,
            "fallback_certificates": [fallback],
        }
    )
    capacity["full_support_fallback_solver_calls"] = 1
    capacity["total_solver_calls"] = 158

    with pytest.raises(
        ValueError,
        match="fallback certificates and failure inventory disagree",
    ):
        evaluation.validate_output_payloads(
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )


def test_output_validation_rejects_network_alpha_certificate_drift(
    tmp_path: Path,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    capacity = payloads["capacity_frontier.json"]
    groups: dict[str, list[dict[str, object]]] = {}
    for cell in capacity["cells"]:
        arm = cell["arms"][NETWORK_ONLY_SHARED]
        groups.setdefault(str(arm["planning_input_sha256"]), []).append(cell)
    target = next(group[1] for group in groups.values() if len(group) > 1)
    target_arm = target["arms"][NETWORK_ONLY_SHARED]
    replacement = evaluation.finalize_capacity_certificate(
        arm_id=NETWORK_ONLY_SHARED,
        candidate=_candidate(
            NETWORK_ONLY_SHARED,
            lower=0.1,
            incumbent=0.1,
        ),
    )
    target_arm.update(asdict(replacement))
    typed_arms = {
        arm_id: evaluation.finalize_capacity_certificate(
            arm_id=arm_id,
            candidate=arm["solver_certificate"],
        )
        for arm_id, arm in target["arms"].items()
    }
    target["capacity_attribution"] = evaluation.capacity_attribution(typed_arms)

    with pytest.raises(ValueError, match="network-only alpha reuse"):
        evaluation.validate_output_payloads(
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )


@pytest.mark.parametrize(
    ("mutate", "message"),
    (
        (
            lambda payloads: payloads["capacity_frontier.json"]["cells"][0][
                "capacity_attribution"
            ]["labels"].update({"joint_extra_requirement": True}),
            "capacity attribution",
        ),
        (
            lambda payloads: payloads["capacity_frontier.json"]["cells"][0]["arms"][
                NETWORK_ONLY_SHARED
            ]["solver_certificate"]["solver_options"].update({"MIPGap": 1.0}),
            "solver certificate binding",
        ),
        (
            lambda payloads: payloads["capacity_frontier.json"].update(
                {"representative_solver_calls": 156}
            ),
            "capacity output counts",
        ),
        (
            lambda payloads: payloads["capacity_frontier.json"][
                "frontier_summary"
            ].update({"interpolation_used": True}),
            "frontier summary",
        ),
        (
            lambda payloads: payloads["holdout.json"].update({"E0_mass": 0.0}),
            "holdout E0",
        ),
        (
            lambda payloads: payloads["identification.json"]["cells"][0].update(
                {
                    "status": "resolved",
                    "transport_certificates": None,
                    "operational_labels": {
                        "b6_operational_penalty": True,
                        "b6_operational_relief": True,
                    },
                }
            ),
            "all-E0 identification",
        ),
        (
            lambda payloads: payloads["identification.json"]["bootstrap"].update(
                {"status": "invented"}
            ),
            "bootstrap",
        ),
        (
            lambda payloads: payloads["identification.json"]["bootstrap"].update(
                {"unexpected": True}
            ),
            "all-E0 bootstrap",
        ),
        (
            lambda payloads: payloads["identification.json"]["bootstrap"].update(
                {"reason": "invented"}
            ),
            "all-E0 bootstrap",
        ),
    ),
)
def test_output_validation_rejects_nested_semantic_drift(
    tmp_path: Path,
    mutate: object,
    message: str,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    mutate(payloads)
    payloads["report.json"] = runner.build_report(
        capacity_frontier=payloads["capacity_frontier.json"],
        holdout=payloads["holdout.json"],
        identification=payloads["identification.json"],
        provenance=payloads["provenance.json"],
    )

    with pytest.raises(ValueError, match=message):
        evaluation.publish_output_bundle(
            tmp_path / "rejected-nested",
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )


def test_recursive_manifest_rejects_extra_empty_directory(tmp_path: Path) -> None:
    payloads, expected = _output_payloads(tmp_path)
    target = tmp_path / "published"
    evaluation.publish_output_bundle(
        target,
        payloads,
        expected_provenance=expected,
        provenance_root=tmp_path,
        expected_cells=_expected_cells(),
        expected_solver_specification=_registered_solver_spec(),
    )
    (target / "unexpected").mkdir()

    with pytest.raises(ValueError, match="typed-tree"):
        evaluation.recursive_manifest(target)


def test_publication_marks_post_result_failure_indeterminate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    target = tmp_path / "published"
    original = evaluation.recursive_manifest

    def fail_target_readback(path: Path) -> dict[str, object]:
        if path == target:
            raise RuntimeError("injected readback failure")
        return original(path)

    monkeypatch.setattr(evaluation, "recursive_manifest", fail_target_readback)
    with pytest.raises(RuntimeError, match="commit_indeterminate"):
        evaluation.publish_output_bundle(
            target,
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )

    assert target.is_dir()
    assert not (tmp_path / "published.PUBLISHED").exists()
    assert (tmp_path / ".published.publish.lock").is_file()


def test_publication_cleans_up_failure_before_result_rename(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    target = tmp_path / "published"
    original_rename = evaluation.os.rename

    def fail_result_rename(source: object, destination: object) -> None:
        if Path(destination) == target:
            raise OSError("injected result rename failure")
        original_rename(source, destination)

    monkeypatch.setattr(evaluation.os, "rename", fail_result_rename)
    with pytest.raises(OSError, match="result rename"):
        evaluation.publish_output_bundle(
            target,
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )

    assert not target.exists()
    assert not (tmp_path / "published.PUBLISHED").exists()
    assert not (tmp_path / ".published.publish.lock").exists()
    assert not list(tmp_path.glob(".published.staging-*"))


def test_publication_reconciles_transient_post_success_readback_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    target = tmp_path / "published"
    original = evaluation._validate_committed_output
    calls = 0

    def fail_once(result: Path, success: Path) -> dict[str, object]:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise OSError("injected transient final readback failure")
        return original(result, success)

    monkeypatch.setattr(evaluation, "_validate_committed_output", fail_once)
    manifest = evaluation.publish_output_bundle(
        target,
        payloads,
        expected_provenance=expected,
        provenance_root=tmp_path,
        expected_cells=_expected_cells(),
        expected_solver_specification=_registered_solver_spec(),
    )

    assert calls == 2
    assert evaluation.recursive_manifest(target) == manifest
    assert (tmp_path / "published.PUBLISHED" / "success.json").is_file()
    assert not (tmp_path / ".published.publish.lock").exists()


def test_publication_keeps_success_parent_fsync_failure_indeterminate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads, expected = _output_payloads(tmp_path)
    target = tmp_path / "published"
    success = tmp_path / "published.PUBLISHED"
    original = evaluation._fsync_directory

    def fail_success_parent(path: Path) -> None:
        if path == target.parent and success.exists():
            raise OSError("injected success parent fsync failure")
        original(path)

    monkeypatch.setattr(evaluation, "_fsync_directory", fail_success_parent)
    with pytest.raises(RuntimeError, match="commit_indeterminate"):
        evaluation.publish_output_bundle(
            target,
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )

    assert target.is_dir()
    assert success.is_dir()
    assert (tmp_path / ".published.publish.lock").is_file()


def test_output_publication_rejects_symlink_ancestor(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    link.symlink_to(real, target_is_directory=True)
    payloads, expected = _output_payloads(tmp_path)

    with pytest.raises(ValueError, match="symlink"):
        evaluation.publish_output_bundle(
            link / "published",
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )


def _write_gzip_rows(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_power_loader_uses_hour_offset_not_csv_row_order(tmp_path: Path) -> None:
    _write_gzip_rows(
        tmp_path / "training_marginal.csv.gz",
        ["id", "probability"],
        [{"id": "p", "probability": 1.0}],
    )
    fields = [
        "block_id",
        "split",
        "hour_offset",
        "source_hour",
        "cfe_call_fraction",
        "grid_need_fraction",
        "dispatch_state",
    ]
    rows = [
        {
            "block_id": "p",
            "split": "training",
            "hour_offset": hour,
            "source_hour": 100 + hour,
            "cfe_call_fraction": hour / 100.0,
            "grid_need_fraction": hour / 100.0,
            "dispatch_state": FINITE_GRID_NEED,
        }
        for hour in reversed(range(24))
    ]
    _write_gzip_rows(
        tmp_path / "dispatched_power_system_blocks.csv.gz",
        fields,
        rows,
    )

    block = load_power_blocks(tmp_path, "training")[0]

    assert block.source_hours == tuple(range(100, 124))
    assert block.grid_need == pytest.approx(tuple(hour / 100.0 for hour in range(24)))


def test_power_loader_rejects_unknown_split_even_when_unreferenced(
    tmp_path: Path,
) -> None:
    _write_gzip_rows(
        tmp_path / "training_marginal.csv.gz",
        ["id", "probability"],
        [{"id": "p", "probability": 1.0}],
    )
    fields = [
        "block_id",
        "split",
        "hour_offset",
        "source_hour",
        "cfe_call_fraction",
        "grid_need_fraction",
        "dispatch_state",
    ]
    rows = [
        {
            "block_id": block_id,
            "split": split,
            "hour_offset": hour,
            "source_hour": hour,
            "cfe_call_fraction": 0.0,
            "grid_need_fraction": 0.0,
            "dispatch_state": FINITE_GRID_NEED,
        }
        for block_id, split in (("p", "training"), ("ignored", "invalid"))
        for hour in range(24)
    ]
    _write_gzip_rows(
        tmp_path / "dispatched_power_system_blocks.csv.gz",
        fields,
        rows,
    )

    with pytest.raises(ValueError, match="invalid split"):
        load_power_blocks(tmp_path, "training")


def test_publication_rejects_provenance_drift_before_writing(tmp_path: Path) -> None:
    payloads, expected = _output_payloads(tmp_path)
    expected["software"] = {"python": "0.0.0"}
    target = tmp_path / "rejected"

    with pytest.raises(ValueError, match="expected authority"):
        evaluation.publish_output_bundle(
            target,
            payloads,
            expected_provenance=expected,
            provenance_root=tmp_path,
            expected_cells=_expected_cells(),
            expected_solver_specification=_registered_solver_spec(),
        )

    assert not target.exists()
