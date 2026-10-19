from __future__ import annotations

from dataclasses import asdict
from importlib.metadata import version
from types import SimpleNamespace

import pytest

from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.evaluation.rq2_joint_identification import (
    R1,
    R2,
    bootstrap_transport_interval,
    joint_region_compatibility,
)
from src.grid.rts_gmlc_grid_need_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    assess_hourly_rts_gmlc_grid_need,
)
from src.grid.rts_gmlc_scuc_solver_successor import (
    RtsGmlcSuccessorSolverAudit,
    _relative_gap,
)
from src.models.temporal_flexibility_capacity_successor import (
    plan_minimum_flexibility_pair_with_spec,
)
from src.scenarios.rq2_public_replay import ParameterCell, TemporalBlock
from src.scenarios.rq2_public_replay_successor import (
    audit_training_support,
    condition_on_grid_evaluable,
)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
from src.solvers.rq2_solver_adapter import (
    Rq2SolverSpec,
    solver_options,
)


def _solver_spec() -> Rq2SolverSpec:
    return Rq2SolverSpec(
        name="highs",
        expected_package_version=version("highspy"),
        threads=1,
        mip_relative_gap=0.0,
        feasibility_tolerance=1.0e-7,
        optimality_tolerance=1.0e-7,
        integer_feasibility_tolerance=1.0e-7,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )


def _generator(uid: str, maximum: float):
    return SimpleNamespace(
        uid=uid,
        bus=1,
        enabled=True,
        dispatch_mode="committable",
        ramp_mw_per_hour=100.0,
        p_max_mw=maximum,
    )


def _branch(uid: str):
    return SimpleNamespace(
        uid=uid,
        from_bus=1,
        to_bus=2,
        reactance_pu=0.1,
        tap_ratio=1.0,
        continuous_rating_mw=40.0,
    )


def _data(generators):
    return SimpleNamespace(
        base_mva=100.0,
        reference_bus=1,
        buses=(SimpleNamespace(uid=1), SimpleNamespace(uid=2)),
        generators=tuple(generators),
        branches=(_branch("L1"), _branch("L2")),
        dc_branches=(),
    )


def _point(generators, *, native_bus_2_load: float = 0.0):
    return SimpleNamespace(
        demand_by_bus_mw={1: 0.0, 2: native_bus_2_load},
        generator_min_mw={generator.uid: 0.0 for generator in generators},
        generator_max_mw={
            generator.uid: generator.p_max_mw for generator in generators
        },
    )


def _block(
    block_id: str,
    probability: float,
    *,
    grid: tuple[float, ...] = (),
    cfe: tuple[float, ...] = (),
    workload: tuple[float, ...] = (),
) -> TemporalBlock:
    return TemporalBlock(
        block_id=block_id,
        split="training",
        probability=probability,
        first_source_hour=0,
        grid_need=grid,
        cfe_call=cfe,
        workload=workload,
    )


def _cell() -> ParameterCell:
    return ParameterCell(
        cell_id="base",
        varied_dimension="base",
        flexible_fraction=1.0,
        recovery_efficiency=1.0,
        normalized_recovery_headroom=1.0,
        maximum_event_duration_hours=1.0,
        maximum_event_count=1,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
    )


def _fixed_policy() -> dict[str, object]:
    return {
        "minimum_recovery_hours": 0.0,
        "minimum_event_power": 1.0e-8,
        "response_time_hours": 1.0,
        "curtailment_ramp_per_hour": 1.0,
    }


def test_solver_options_are_explicit_and_solver_specific():
    highs = solver_options(_solver_spec())
    gurobi = solver_options(
        Rq2SolverSpec(
            **{
                **_solver_spec().__dict__,
                "name": "gurobi",
                "expected_package_version": "13.0.2",
                "time_limit_seconds": 300.0,
            }
        )
    )

    assert highs["threads"] == 1
    assert highs["mip_rel_gap"] == 0.0
    assert gurobi["Threads"] == 1
    assert gurobi["MIPGap"] == 0.0
    assert gurobi["TimeLimit"] == 300.0


def test_successor_scuc_audit_records_incumbent_relative_gap():
    relative_gap = _relative_gap(9.0, 10.0)
    audit = RtsGmlcSuccessorSolverAudit(
        accepted=True,
        termination_condition="optimal",
        solver_status="ok",
        solver_message="",
        objective_usd=10.0,
        lower_bound_usd=9.0,
        upper_bound_usd=10.0,
        absolute_gap_usd=1.0,
        gap_tolerance_usd=1.0,
        maximum_constraint_violation=0.0,
        maximum_integrality_violation=0.0,
        solver_threads=1,
        configured_mip_relative_gap=0.1,
        relative_gap=relative_gap,
    )

    assert relative_gap == pytest.approx(0.1)
    assert asdict(audit)["relative_gap"] == pytest.approx(0.1)
    assert _relative_gap(None, 10.0) is None


def test_full_dc_curtailment_infeasibility_becomes_exogenous_state():
    generators = (_generator("G1", 100.0),)
    assessment = assess_hourly_rts_gmlc_grid_need(
        _data(generators),
        _point(generators, native_bus_2_load=10.0),
        {"G1": 90.0},
        {"G1": True},
        N1OutageEvent(1, "generator", "generator", "G1", 0, 1),
        source_hour=0,
        dc_bus=2,
        dc_demand_mw=80.0,
        solver_specification=_solver_spec(),
    )

    assert assessment.state == EXOGENOUS_GRID_INFEASIBILITY
    assert assessment.resolved_for_pipeline
    assert assessment.primary.proven_infeasible
    assert assessment.zero_dc_confirmation is not None
    assert assessment.zero_dc_confirmation.proven_infeasible
    assert assessment.primary.grid_need_mw is None
    assert assessment.primary_certificate.model_variables > 0
    assert assessment.primary_certificate.model_constraints > 0
    assert assessment.zero_dc_confirmation_certificate is not None


def test_finite_grid_need_remains_a_finite_state():
    generators = (_generator("G1", 100.0),)
    assessment = assess_hourly_rts_gmlc_grid_need(
        _data(generators),
        _point(generators),
        {"G1": 80.0},
        {"G1": True},
        N1OutageEvent(1, "line", "branch", "L1", 0, 1),
        source_hour=0,
        dc_bus=2,
        dc_demand_mw=80.0,
        solver_specification=_solver_spec(),
    )

    assert assessment.state == FINITE_GRID_NEED
    assert assessment.primary.grid_need_mw == pytest.approx(40.0)
    assert assessment.zero_dc_confirmation is None
    assert assessment.primary_certificate.lower_bound_mw == pytest.approx(40.0)
    assert assessment.primary_certificate.upper_bound_mw == pytest.approx(40.0)
    assert assessment.primary_certificate.absolute_gap_mw == pytest.approx(0.0)


def test_conditioning_preserves_exogenous_probability_mass():
    blocks = (
        _block("p0", 0.25, grid=(0.0,), cfe=(0.0,)),
        _block("p1", 0.75, grid=(0.0,), cfe=(0.0,)),
    )
    result = condition_on_grid_evaluable(
        blocks,
        {
            "p0": FINITE_GRID_NEED,
            "p1": EXOGENOUS_GRID_INFEASIBILITY,
        },
    )

    assert result.exogenous_probability_mass == pytest.approx(0.75)
    assert result.conditioning_probability_mass == pytest.approx(0.25)
    assert result.exogenous_block_ids == ("p1",)
    assert result.evaluable_blocks[0].probability == pytest.approx(1.0)


def test_full_training_support_audit_detects_omitted_stress_pair():
    power = (
        _block("p0", 0.5, grid=(0.0, 0.0), cfe=(0.05, 0.0)),
        _block("p1", 0.5, grid=(0.1, 0.0), cfe=(0.1, 0.0)),
    )
    workload = (_block("w0", 1.0, workload=(1.0, 0.0)),)

    correct, b6 = audit_training_support(
        power,
        workload,
        _cell(),
        correct_capacity=0.1,
        b6_capacity=0.1,
        fixed_policy=_fixed_policy(),
    )

    assert not correct.passed
    assert correct.failed_pair_ids == ("p1__w0",)
    assert b6.passed


def test_joint_region_uses_one_coupling_for_all_metrics():
    zeros = ((0.0, 0.0), (0.0, 0.0))
    result = joint_region_compatibility(
        (0.5, 0.5),
        (0.5, 0.5),
        {
            "delta_failure_probability": ((0.0, 1.0), (1.0, 0.0)),
            "delta_expected_shortfall": ((1.0, 0.0), (0.0, 1.0)),
            "flexibility_underprovisioning": zeros,
            "delta_peak_recovery_debt": zeros,
            "delta_terminal_recovery_debt": zeros,
            "correct_failure_probability": zeros,
            "correct_expected_shortfall": zeros,
        },
    )

    assert R1 not in result.compatible_regions
    assert R2 in result.compatible_regions


def test_bootstrap_transport_interval_is_reproducible():
    first = bootstrap_transport_interval(
        (0.5, 0.5),
        (0.5, 0.5),
        ((0.0, 1.0), (1.0, 0.0)),
        replicates=20,
        seed=17,
        confidence_level=0.9,
    )
    second = bootstrap_transport_interval(
        (0.5, 0.5),
        (0.5, 0.5),
        ((0.0, 1.0), (1.0, 0.0)),
        replicates=20,
        seed=17,
        confidence_level=0.9,
    )

    assert first == second
    assert first.lower_endpoint_interval[0] <= first.lower_endpoint_interval[1]
    assert first.upper_endpoint_interval[0] <= first.upper_endpoint_interval[1]


def test_execution_host_requires_both_hostname_and_environment(monkeypatch):
    execution = {
        "forbidden_hostnames": ["development-host"],
        "required_environment_value": "EXECUTION_MACHINE_CONFIRMED",
    }
    monkeypatch.setattr("socket.gethostname", lambda: "development-host")
    monkeypatch.setenv("RQ2_EXECUTION_MACHINE", "EXECUTION_MACHINE_CONFIRMED")

    status = execution_host_status(execution)
    assert not status["hostname_allowed"]
    assert status["environment_authorized"]
    with pytest.raises(RuntimeError, match="forbidden on development host"):
        require_execution_host(execution)


def test_successor_capacity_solve_reports_bound_gap_and_model_scale():
    from tests.test_temporal_flexibility_capacity import _inputs

    result = plan_minimum_flexibility_pair_with_spec(
        _inputs(80.0),
        solver_specification=_solver_spec(),
    )

    assert result.correct.feasible
    assert result.correct.minimum_capacity == pytest.approx(80.0)
    assert result.correct.lower_bound == pytest.approx(80.0)
    assert result.correct.upper_bound == pytest.approx(80.0)
    assert result.correct.absolute_gap == pytest.approx(0.0)
    assert result.correct.model_variables > 0
    assert result.correct.model_constraints > 0
