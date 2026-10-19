from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from pyomo.environ import (
    Binary,
    ConcreteModel,
    Constraint,
    ConstraintList,
    Expression,
    Objective,
    Set,
    Var,
    maximize,
    minimize,
)
from pyomo.opt import TerminationCondition

from experiments import pilot_rts_gmlc_zero_dc_ac_aware_formulations as pilot
from src.grid.rts_gmlc_exact_cg import (
    apply_shared_snapshot,
    assert_conditionally_independent_recourse,
    extract_shared_snapshot,
    final_max_certificate,
    final_min_certificate,
    orient_bound_interval,
    promotions,
    relax_fixed_integer_variables,
    screen_plan,
    shared_snapshot_violation,
)
from src.solvers.mip_progress import JsonlProgressWriter

CONFIG = Path("configs/rts_gmlc_zero_dc_ac_aware_formulation_pilot.yaml")


def _synthetic_model(*, cross_contingency: bool = False) -> ConcreteModel:
    model = ConcreteModel()
    model.STATE = Set(initialize=("normal", "s1", "s2"), ordered=True)
    model.TIME = Set(initialize=(0,), ordered=True)
    model.GEN = Set(initialize=("g1",), ordered=True)
    model.BUS = Set(initialize=(1,), ordered=True)
    model.BRANCH = Set(initialize=("b1",), ordered=True)
    model.DC_BRANCH = Set(initialize=("dc1",), ordered=True)
    model.SEGMENT = Set(initialize=(("g1", 0),), dimen=2, ordered=True)

    model.commitment = Var(model.TIME, model.GEN, domain=Binary)
    model.startup = Var(model.TIME, model.GEN)
    model.shutdown = Var(model.TIME, model.GEN)
    model.generation = Var(model.STATE, model.TIME, model.GEN)
    model.angle_degrees = Var(model.STATE, model.TIME, model.BUS)
    model.branch_flow = Var(model.STATE, model.TIME, model.BRANCH)
    model.dc_flow = Var(model.STATE, model.TIME, model.DC_BRANCH)
    model.reserve_up = Var(model.TIME, model.GEN)
    model.segment_power = Var(model.TIME, model.SEGMENT)
    model.reactive_proxy = Var(bounds=(0.0, 1.0))
    model.operating_cost = Expression(expr=model.segment_power[0, "g1", 0])
    model.state_balance = ConstraintList()
    for state in model.STATE:
        model.state_balance.add(
            model.generation[state, 0, "g1"] == model.branch_flow[state, 0, "b1"]
        )
        model.state_balance.add(
            model.dc_flow[state, 0, "dc1"] == model.angle_degrees[state, 0, 1]
        )
    model.response = Constraint(
        expr=model.generation["s1", 0, "g1"] == model.generation["normal", 0, "g1"]
    )
    if cross_contingency:
        model.cross = Constraint(
            expr=model.generation["s1", 0, "g1"] + model.generation["s2", 0, "g1"]
            == 0.0
        )
    model.objective = Objective(expr=model.reactive_proxy, sense=maximize)

    model.commitment[0, "g1"].set_value(1.0)
    model.startup[0, "g1"].set_value(1.0)
    model.shutdown[0, "g1"].set_value(0.0)
    model.reserve_up[0, "g1"].set_value(2.0)
    model.segment_power[0, "g1", 0].set_value(3.0)
    model.reactive_proxy.set_value(0.4)
    for state in model.STATE:
        model.generation[state, 0, "g1"].set_value(5.0)
        model.branch_flow[state, 0, "b1"].set_value(5.0)
        model.angle_degrees[state, 0, 1].set_value(1.0)
        model.dc_flow[state, 0, "dc1"].set_value(1.0)
    return model


def test_config_freezes_independent_two_formulation_comparison() -> None:
    config = pilot._read_config(CONFIG)

    assert config["formulations"]["included"] == [
        "full_state_monolith",
        "exact_selected_state_constraint_generation",
    ]
    assert config["solver"]["threads"] == 4
    assert config["solver"]["repetitions"] == 2
    assert config["solver"]["target_mip_relative_gap"] == 1.0e-4
    assert config["pilot"]["horizon_hours"] == 6
    assert config["pilot"]["relative_cost_budget_delta"] == 0.0075
    assert not config["selection"]["objective_value_used"]


def test_bound_roles_follow_objective_direction() -> None:
    maximization = orient_bound_interval(
        sense="maximize",
        raw_lower_bound=0.28,
        raw_upper_bound=0.30,
        incumbent_objective=0.28,
        consistency_tolerance=1.0e-9,
    )
    minimization = orient_bound_interval(
        sense="minimize",
        raw_lower_bound=100.0,
        raw_upper_bound=101.0,
        incumbent_objective=101.0,
        consistency_tolerance=1.0e-9,
    )

    assert maximization["dual_bound"] == 0.30
    assert maximization["certified_lower_bound"] == 0.28
    assert maximization["certified_upper_bound"] == 0.30
    assert minimization["dual_bound"] == 100.0
    assert minimization["certified_lower_bound"] == 100.0
    assert minimization["certified_upper_bound"] == 101.0


def test_bound_roles_reject_a_raw_primal_that_is_not_loaded_incumbent() -> None:
    observed = orient_bound_interval(
        sense="maximize",
        raw_lower_bound=0.29,
        raw_upper_bound=0.30,
        incumbent_objective=0.28,
        consistency_tolerance=1.0e-6,
    )

    assert not observed["bound_valid"]
    assert not observed["raw_primal_bound_consistent"]


def test_time_limit_incumbent_is_usable_for_screening_only_when_audited() -> None:
    accepted = pilot._incumbent_is_usable(
        termination_condition=TerminationCondition.maxTimeLimit,
        solution_loaded=True,
        incumbent_objective=0.28,
        maximum_constraint_violation=1.0e-7,
        maximum_integrality_violation=0.0,
        variables_finite=True,
        feasibility_tolerance=1.0e-6,
    )
    missing = pilot._incumbent_is_usable(
        termination_condition=TerminationCondition.maxTimeLimit,
        solution_loaded=False,
        incumbent_objective=None,
        maximum_constraint_violation=None,
        maximum_integrality_violation=None,
        variables_finite=False,
        feasibility_tolerance=1.0e-6,
    )

    assert accepted
    assert not missing


@pytest.mark.parametrize(
    "stage",
    (
        "proxy_maximization",
        "cost_normalization",
        "level_set_cost_minimization",
        "level_set_budget_feasibility",
    ),
)
def test_every_stage_rescreens_every_currently_inactive_state(stage: str) -> None:
    all_states = ("normal", "s1", "s2", "s3")

    first = screen_plan(
        stage=stage,
        all_state_ids=all_states,
        active_state_ids=("normal", "s1"),
    )
    second = screen_plan(
        stage=stage,
        all_state_ids=all_states,
        active_state_ids=("normal", "s1", "s3"),
    )

    assert first == ("s2", "s3")
    assert second == ("s2",)


def test_unresolved_is_promoted_without_an_infeasibility_claim() -> None:
    observed = promotions(
        (
            {"state_id": "s1", "status": "feasible"},
            {"state_id": "s2", "status": "certified_infeasible"},
            {"state_id": "s3", "status": "unresolved"},
        ),
        ("normal", "s1", "s2", "s3"),
    )

    assert observed == (
        {"state_id": "s2", "reason": "certified_infeasible"},
        {"state_id": "s3", "reason": "unresolved_promoted"},
    )


def test_shared_snapshot_fixes_every_shared_and_normal_component() -> None:
    source = _synthetic_model()
    target = _synthetic_model()
    snapshot = extract_shared_snapshot(source)

    apply_shared_snapshot(target, snapshot)

    assert shared_snapshot_violation(target, snapshot) == 0.0
    assert target.commitment[0, "g1"].fixed
    assert target.startup[0, "g1"].fixed
    assert target.shutdown[0, "g1"].fixed
    assert target.generation["normal", 0, "g1"].fixed
    assert target.dc_flow["normal", 0, "dc1"].fixed
    assert target.angle_degrees["normal", 0, 1].fixed
    assert target.branch_flow["normal", 0, "b1"].fixed
    assert target.segment_power[0, "g1", 0].fixed
    assert target.reserve_up[0, "g1"].fixed
    assert target.reactive_proxy.fixed
    assert not target.generation["s1", 0, "g1"].fixed
    relax_fixed_integer_variables(target)


def test_cross_contingency_recoursing_constraint_is_rejected() -> None:
    with pytest.raises(RuntimeError, match="Cross-contingency"):
        assert_conditionally_independent_recourse(
            _synthetic_model(cross_contingency=True)
        )


def test_final_proxy_certificate_uses_minimum_master_dual_upper_bound() -> None:
    certificate = final_max_certificate(
        full_feasible_objective=0.28570,
        master_dual_upper_bounds=(0.30, 0.29, 0.28572),
        target_relative_gap=1.0e-4,
    )

    assert certificate["valid"]
    assert certificate["upper_bound"] == 0.28572
    assert certificate["target_gap_attained"]
    assert certificate["proxy_percentage_point_width"] == pytest.approx(0.002)


def test_final_cost_certificate_uses_maximum_master_dual_lower_bound() -> None:
    certificate = final_min_certificate(
        full_feasible_objective=1_000_050.0,
        master_dual_lower_bounds=(999_000.0, 1_000_000.0, 999_500.0),
        target_relative_gap=1.0e-4,
    )

    assert certificate["valid"]
    assert certificate["lower_bound"] == 1_000_000.0
    assert certificate["upper_bound"] == 1_000_050.0
    assert certificate["target_gap_attained"]


def _record(
    formulation: str,
    repetition: int,
    seconds: float,
    eligible: bool,
    objective: float,
) -> dict[str, object]:
    return {
        "formulation": formulation,
        "repetition": repetition,
        "total_elapsed_seconds": seconds,
        "eligible": eligible,
        "objective_forbidden_to_selection": objective,
    }


def test_selection_uses_runtime_and_never_reads_objective() -> None:
    records = (
        _record("full_state_monolith", 1, 12.0, True, 0.99),
        _record("full_state_monolith", 2, 14.0, True, 0.99),
        _record("exact_selected_state_constraint_generation", 1, 8.0, True, 0.10),
        _record("exact_selected_state_constraint_generation", 2, 10.0, True, 0.10),
    )

    selected = pilot._select_formulation(
        records,
        (
            "full_state_monolith",
            "exact_selected_state_constraint_generation",
        ),
        2,
    )

    assert selected["selected_formulation"] == (
        "exact_selected_state_constraint_generation"
    )
    assert not selected["objective_value_used"]


def test_tiny_highs_wrapper_smoke_does_not_build_the_rts_pilot(
    tmp_path: Path,
) -> None:
    model = _synthetic_model()
    handle = pilot._ModelHandle(
        model=model,
        scuc_context=None,
        state_ids=("normal", "s1", "s2"),
        stage="proxy_maximization",
        sense="maximize",
        base_variables=0,
        base_constraints=0,
        formulation_variables=0,
        formulation_constraints=0,
    )
    config = pilot._read_config(CONFIG)
    progress = JsonlProgressWriter(
        tmp_path / "progress.jsonl",
        run_id="tiny-smoke",
        preregistration_id="synthetic-only",
        input_contract_sha256="a" * 64,
    )

    solved = pilot._solve_handle(
        handle,
        config,
        native_log=tmp_path / "highs.log",
        progress=progress,
        solve_label="tiny_synthetic",
    )

    assert solved["incumbent_usable"]
    assert solved["bound_valid"]
    assert solved["incumbent_objective"] == pytest.approx(1.0)


def test_budget_decision_builder_preserves_cost_objective_and_target(
    monkeypatch,
) -> None:
    model = _synthetic_model()
    model.objective.set_value(model.operating_cost)
    model.objective.sense = minimize
    model.del_component(model.reactive_proxy)
    states = tuple(
        SimpleNamespace(state_id=state_id) for state_id in ("normal", "s1", "s2")
    )
    problem = SimpleNamespace(
        parent_context=SimpleNamespace(
            zero=SimpleNamespace(scan=SimpleNamespace(data=object())),
            initial_state=object(),
        ),
        request=object(),
        points=(object(),),
        states=states,
        all_state_ids=("normal", "s1", "s2"),
        cost_budget_usd=4.0,
    )
    monkeypatch.setattr(pilot, "_build_scuc_context", lambda *_args: object())
    monkeypatch.setattr(pilot, "_build_model", lambda *_args, **_kwargs: model)
    monkeypatch.setattr(
        pilot.parent,
        "_proxy_components",
        lambda *_args: (
            {"a": (0.0, 0.0)},
            {"a": {"g1": (1.0, 1.0)}},
            ({"a": (1.0, 1.0)},),
        ),
    )
    monkeypatch.setattr(
        pilot, "_assert_conditionally_independent_recourse", lambda *_args: None
    )

    handle = pilot._build_model_handle(
        problem,
        pilot._read_config(CONFIG),
        problem.all_state_ids,
        stage="level_set_budget_feasibility",
        proxy_floor=0.6,
    )

    active_objectives = tuple(
        handle.model.component_data_objects(Objective, active=True)
    )
    assert active_objectives == (model.objective,)
    assert model.objective.sense == minimize
    assert handle.decision_objective_target_usd == pytest.approx(4.0001)
    assert not hasattr(model, "level_set_feasibility_objective")


@pytest.mark.parametrize(
    (
        "proxy_floor",
        "expected_termination",
        "expected_incumbent",
        "expected_global_infeasibility",
    ),
    (
        (0.6, "TerminationCondition.convergenceCriteriaSatisfied", True, False),
        (1.1, "TerminationCondition.provenInfeasible", False, True),
    ),
)
def test_tiny_highs_budget_decision_mip_has_explicit_feasibility_outcomes(
    tmp_path: Path,
    proxy_floor: float,
    expected_termination: str,
    expected_incumbent: bool,
    expected_global_infeasibility: bool,
) -> None:
    model = _synthetic_model()
    model.nonnegative_cost = Constraint(expr=model.segment_power[0, "g1", 0] >= 0.0)
    model.cost_cap = Constraint(expr=model.operating_cost <= 4.0)
    model.reactive_proxy_floor = Constraint(expr=model.reactive_proxy >= proxy_floor)
    model.objective.deactivate()
    model.operating_cost_objective = Objective(expr=model.operating_cost)
    handle = pilot._ModelHandle(
        model=model,
        scuc_context=None,
        state_ids=("normal", "s1", "s2"),
        stage="level_set_budget_feasibility",
        sense="minimize",
        base_variables=0,
        base_constraints=0,
        formulation_variables=0,
        formulation_constraints=0,
        decision_objective_target_usd=4.0,
    )
    config = pilot._read_config(CONFIG)
    progress = JsonlProgressWriter(
        tmp_path / f"progress-{expected_termination}.jsonl",
        run_id=f"tiny-decision-{expected_termination}",
        preregistration_id="synthetic-only",
        input_contract_sha256="a" * 64,
    )

    solved = pilot._solve_handle(
        handle,
        config,
        native_log=tmp_path / f"highs-{expected_termination}.log",
        progress=progress,
        solve_label=f"tiny_decision_{expected_termination}",
    )

    assert solved["solver_api"] == "pyomo.contrib.solver.highs_v2"
    assert solved["solver_status"] is None
    assert solved["termination_condition"] == expected_termination
    assert solved["incumbent_usable"] is expected_incumbent
    assert solved["global_infeasibility_certified"] is expected_global_infeasibility
    assert solved["decision_objective_target_usd"] == pytest.approx(4.0)
    assert model.operating_cost_objective.active
    assert not model.objective.active


def test_objective_limit_is_feasible_only_and_requires_an_audited_incumbent() -> None:
    termination = pilot._legacy_incumbent_termination(
        pilot.V2TerminationCondition.objectiveLimit
    )

    assert termination == TerminationCondition.feasible
    assert termination not in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
    }
    assert not pilot._incumbent_is_usable(
        termination_condition=termination,
        solution_loaded=False,
        incumbent_objective=3.0,
        maximum_constraint_violation=0.0,
        maximum_integrality_violation=0.0,
        variables_finite=True,
        feasibility_tolerance=1.0e-6,
    )
    assert pilot._incumbent_is_usable(
        termination_condition=termination,
        solution_loaded=True,
        incumbent_objective=3.0,
        maximum_constraint_violation=1.0e-7,
        maximum_integrality_violation=0.0,
        variables_finite=True,
        feasibility_tolerance=1.0e-6,
    )


def test_budget_decision_v2_feasible_solution_matches_legacy_audits(
    tmp_path: Path,
) -> None:
    def decision_model() -> ConcreteModel:
        model = _synthetic_model()
        model.fixed_cost = Constraint(expr=model.segment_power[0, "g1", 0] == 3.0)
        model.cost_cap = Constraint(expr=model.operating_cost <= 4.0)
        model.reactive_proxy_floor = Constraint(expr=model.reactive_proxy == 0.6)
        model.objective.deactivate()
        model.operating_cost_objective = Objective(expr=model.operating_cost)
        return model

    config = pilot._read_config(CONFIG)
    v2_model = decision_model()
    v2_handle = pilot._ModelHandle(
        model=v2_model,
        scuc_context=None,
        state_ids=("normal", "s1", "s2"),
        stage="level_set_budget_feasibility",
        sense="minimize",
        base_variables=0,
        base_constraints=0,
        formulation_variables=0,
        formulation_constraints=0,
        decision_objective_target_usd=4.0,
    )
    progress = JsonlProgressWriter(
        tmp_path / "progress-v2-feasible.jsonl",
        run_id="tiny-decision-v2-feasible",
        preregistration_id="synthetic-only",
        input_contract_sha256="a" * 64,
    )
    v2_solved = pilot._solve_handle(
        v2_handle,
        config,
        native_log=tmp_path / "highs-v2-feasible.log",
        progress=progress,
        solve_label="tiny_decision_v2_feasible",
    )

    legacy_model = decision_model()
    solver_config = config["solver"]
    legacy_options = pilot.highs_runtime_options(
        mip_relative_gap=float(solver_config["target_mip_relative_gap"]),
        threads=int(solver_config["threads"]),
        random_seed=int(solver_config["random_seed"]),
        feasibility_tolerance=float(solver_config["feasibility_tolerance"]),
        time_limit_seconds=float(solver_config["time_limit_seconds_per_call"]),
        log_file=tmp_path / "highs-legacy-feasible.log",
        mip_min_logging_interval_seconds=float(
            solver_config["mip_min_logging_interval_seconds"]
        ),
    )
    pilot.Highs.resetGlobalScheduler(True)
    legacy_results = pilot.SolverFactory("highs").solve(
        legacy_model,
        load_solutions=False,
        tee=False,
        options=legacy_options,
    )
    legacy_model.solutions.load_from(legacy_results)

    assert v2_solved["incumbent_usable"]
    assert v2_solved["termination_condition"] == (
        "TerminationCondition.convergenceCriteriaSatisfied"
    )
    assert str(legacy_results.solver.status) == "ok"
    assert str(legacy_results.solver.termination_condition) == "optimal"
    assert v2_solved["incumbent_objective"] == pytest.approx(
        float(pilot.value(legacy_model.operating_cost))
    )
    assert v2_solved["maximum_constraint_violation"] == pytest.approx(
        pilot._constraint_violation(legacy_model)
    )
    assert v2_solved["maximum_integrality_violation"] == pytest.approx(
        pilot._integrality_violation(legacy_model)
    )


def test_prepare_hash_locks_inputs_without_building_or_running_pilot(
    tmp_path: Path,
) -> None:
    output = tmp_path / "pilot"

    first = pilot.prepare(CONFIG, output_directory=output)
    second = pilot.prepare(CONFIG, output_directory=output)

    assert first == second
    assert first["status"] == "prepared_not_run"
    assert first["provenance"]["selected_threads"] == 4
    assert first["provenance"]["exact_cg_module_sha256"]
    assert (output / "preparation" / "SHA256SUMS").is_file()
    assert not (output / "comparison").exists()


def test_run_refuses_to_build_without_preparation(tmp_path: Path) -> None:
    with pytest.raises(RuntimeError, match="requires a published"):
        pilot.run_pilot(CONFIG, output_directory=tmp_path / "missing")
