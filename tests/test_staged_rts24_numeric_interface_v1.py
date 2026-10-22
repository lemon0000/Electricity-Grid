"""Pure algebra/import checks. Expected points and multipliers are hand specified."""
from dataclasses import replace
from fractions import Fraction as Q

import pytest
from pyomo.environ import Constraint, Var, value

from experiments.staged_rts24_causal_examples_v1 import (
    analytic_fixture, analytic_hour, analytic_economic, analytic_point,
)
from experiments.staged_rts24_analytic_examples_v1 import example
from src import staged_rts24_development_v1 as c
from src.staged_rts24_causal_v1 import PointEvidence, initialize_execution
from src.staged_rts24_numeric_interface_v1 import (
    NumericSnapshot, UnresolvedNumeric, compile_problem, import_snapshot, hessian_columns,
)


@pytest.fixture(autouse=True)
def no_numeric_backend(monkeypatch):
    import pyomo.environ as pyo

    def denied(*a, **kw): pytest.fail("numeric backend requested by pure interface test")
    monkeypatch.setattr(pyo, "SolverFactory", denied)


def test_interface_has_no_numeric_execution_entrypoint():
    import ast
    from pathlib import Path
    import src.staged_rts24_numeric_interface_v1 as interface
    tree = ast.parse(Path(interface.__file__).read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            assert "highspy" not in ast.unparse(node)
        if isinstance(node, ast.Call):
            name = node.func.id if isinstance(node.func, ast.Name) else node.func.attr if isinstance(node.func, ast.Attribute) else ""
            assert name not in ("Highs", "SolverFactory", "solve", "run")


def frame(hour=0):
    f = analytic_fixture()
    state = initialize_execution(f, "on_time", "early", "full_temporal")
    state = replace(state, ledger=replace(state.ledger, last_hour=hour+state.hour_offset-1))
    return analytic_hour(f, state)


def point_values(point):
    return {"meter": point.meter_load_mw, "curtailment": point.curtailment_mw,
        **{f"generation[{i}]": v for i, v in point.generation_mw},
        **{f"angle[{i}]": v for i, v in point.angles_rad}, **{f"flow[{i}]": v for i, v in point.flows_mw}}


def raw_snapshot(item):
    """Raw min-form shadow prices derived from the independently given multipliers."""
    problem, point = compile_problem(item.query), item.point
    vals = point_values(point)
    cert = item.economic or item.child_lp
    row_duals, col_duals = {}, {}
    if cert is not None:
        row_duals.update({f"power_balance[{i}]": -v for i, v in cert.balance_duals})
        row_duals.update({f"branch_flow[{i}]": -v for i, v in cert.flow_equation_duals})
        for name, lo, hi in (("generation", cert.generation_lower_duals, cert.generation_upper_duals),
                             ("flow", cert.flow_lower_duals, cert.flow_upper_duals)):
            col_duals.update({f"{name}[{i}]": v-dict(hi)[i] for i, v in lo})
        if item.child_lp:
            col_duals.update(meter=cert.meter_lower_dual-cert.meter_upper_dual,
                             curtailment=cert.curtailment_lower_dual-cert.curtailment_upper_dual)
            row_duals.update(connection=-cert.connection_dual, curtailment_bound=-cert.curtailment_le_meter_dual)
    q = item.query.request
    if q.objective == "economic":
        objective = sum((g.cost_quadratic+1e-8)*dict(point.generation_mw)[g.index]**2 +
            g.cost_linear*dict(point.generation_mw)[g.index]+g.cost_constant for g in q.data.generators
            if g.in_service and g.index not in q.outages.generators)
    else:
        objective = point.curtailment_mw if q.objective == "min_curtailment" else point.meter_load_mw*(
            -1. if q.objective == "max_meter" else 1.)
    snap = NumericSnapshot(problem.identity, "kOptimal", True, cert is not None,
        tuple(vals[name] for name in problem.columns),
        tuple(sum(a*vals[problem.columns[i]] for i, a in r.terms) for r in problem.rows),
        tuple(col_duals.get(name, 0.) for name in problem.columns) if cert is not None else (),
        tuple(row_duals.get(r.name, 0.) for r in problem.rows) if cert is not None else (), objective)
    return problem, snap


@pytest.mark.parametrize("hour,role", [(0, "reference"), (0, "lower"), (0, "upper"),
                                      (1, "reference"), (1, "raw"), (1, "lower"), (1, "upper")])
def test_independent_analytic_primal_and_duals_import(hour, role):
    item = getattr(frame(hour), role)
    problem, raw = raw_snapshot(item)
    assert import_snapshot(item.query, problem, raw) == item
    assert not any(name == "angle[1]" for name in problem.columns)
    assert not problem.quadratic or item.economic is not None


@pytest.mark.parametrize("transformer", [False, True])
def test_shift_tap_and_constant_terms_match_original_pyomo_expressions(transformer):
    ex = example(transformer)
    item = PointEvidence(ex["base_query"], ex["base_point"], economic=ex["base_economic"])
    problem, raw = raw_snapshot(item)
    assert import_snapshot(item.query, problem, raw) == item
    model = c.build_point_model(item.query)
    vals = point_values(item.point)
    for v in model.component_data_objects(Var): v.set_value(vals[v.name])
    row_map = {r.name: r for r in problem.rows}
    for row in model.component_data_objects(Constraint, active=True):
        if row.name in row_map:
            reduced = row_map[row.name]
            activity = sum(a*vals[problem.columns[j]] for j, a in reduced.terms)
            # Equality RHS after substitution is checked against the original expression.
            if row.equality:
                assert activity-reduced.lower == pytest.approx(reduced.original_scale*(value(row.body)-value(row.lower)), abs=1e-12)
    assert raw.objective == pytest.approx(value(model.objective), abs=1e-12)


def test_public_normal_export_is_deterministic_complete_and_no_solve():
    f = c.load_fixture()
    for hour in (0, 2):
        request = c.hour_requests(f, "on_time", "early", "full_temporal", hour)["requests"][0]
        query = c.bind(request)
        problem = compile_problem(query)
        assert problem == compile_problem(query)
        assert (len(problem.columns), len(problem.rows)) == (93, 62)
        assert len(problem.quadratic) == 32
        assert dict(problem.fixed)["generation[14]"] == 0.
        assert problem.query_sha == query.identity


def test_zero_output_fixed_economic_generator_has_valid_reconstructed_box_dual():
    item = frame().reference
    data = replace(item.query.request.data, generators=(replace(item.query.request.data.generators[0], p_min_mw=100., p_max_mw=100.),))
    query = c.bind(replace(item.query.request, data=data))
    point = replace(item.point, query_sha=query.identity)
    independent = PointEvidence(query, point, economic=analytic_economic(query, point))
    problem, raw = raw_snapshot(independent)
    assert "generation[0]" not in problem.columns
    assert import_snapshot(query, problem, raw) == independent


def test_offline_economic_generator_stationarity_reconstruction():
    item = frame().reference
    active = item.query.request.data.generators[0]
    inactive = replace(active, index=1, in_service=False)
    data = replace(item.query.request.data, generators=(active, inactive))
    query = c.bind(replace(item.query.request, data=data))
    point = replace(item.point, query_sha=query.identity, generation_mw=item.point.generation_mw+((1, 0.),))
    economic = analytic_economic(query, point)
    economic = replace(economic, generation_lower_duals=((0, 0.), (1, 0.)), generation_upper_duals=((0, 0.), (1, 1.)))
    independent = PointEvidence(query, point, economic=economic)
    problem, raw = raw_snapshot(independent)
    assert import_snapshot(query, problem, raw) == independent


def test_actual_primal_only_import_does_not_fabricate_optimality():
    ex = example(True)
    item = PointEvidence(ex["actual_query"], ex["actual_point"])
    problem, raw = raw_snapshot(item)
    result = import_snapshot(item.query, problem, raw)
    assert result == item and result.economic is result.child_lp is None


@pytest.mark.parametrize("status", ["kTimeLimit", "kInfeasible", "kUnknown", "kUnboundedOrInfeasible", "optimal"])
def test_nonoptimal_native_status_remains_unresolved(status):
    item = frame().reference
    problem, raw = raw_snapshot(item)
    with pytest.raises(UnresolvedNumeric, match="infeasibility not inferred"):
        import_snapshot(item.query, problem, replace(raw, model_status=status))


@pytest.mark.parametrize("name", ["primal_valid", "dual_valid"])
def test_missing_validity_is_unresolved(name):
    item = frame(1).raw
    problem, raw = raw_snapshot(item)
    with pytest.raises(UnresolvedNumeric): import_snapshot(item.query, problem, replace(raw, **{name: False}))


@pytest.mark.parametrize("array", ["column_value", "row_value", "column_dual", "row_dual"])
@pytest.mark.parametrize("change", ["short", "nan", "bool"])
def test_malformed_raw_arrays_rejected(array, change):
    item = frame(1).raw
    problem, raw = raw_snapshot(item)
    old = getattr(raw, array)
    changed = old[:-1] if change == "short" else ((float("nan") if change == "nan" else True), *old[1:])
    with pytest.raises(ValueError): import_snapshot(item.query, problem, replace(raw, **{array: changed}))


@pytest.mark.parametrize("field", ["constant", "lower", "rows", "fixed", "query_sha"])
def test_query_label_alone_cannot_bless_changed_transport(field):
    item = frame().reference
    problem, raw = raw_snapshot(item)
    changes = dict(constant=problem.constant+1., lower=problem.lower[:-1], rows=problem.rows[:-1],
                   fixed=problem.fixed[:-1], query_sha="0"*64)
    changed = replace(problem, **{field: changes[field]})
    with pytest.raises(ValueError, match="problem binding"):
        import_snapshot(item.query, changed, replace(raw, problem_sha=changed.identity))


def test_wrong_native_dual_sign_rejected_by_independent_audit():
    item = frame(1).raw
    problem, raw = raw_snapshot(item)
    with pytest.raises(ValueError, match="reduced-cost|child LP audit"):
        import_snapshot(item.query, problem, replace(raw, row_dual=tuple(-v for v in raw.row_dual)))


@pytest.mark.parametrize("field", ["row_value", "objective", "problem_sha"])
def test_false_native_echo_rejected(field):
    item = frame().reference
    problem, raw = raw_snapshot(item)
    changed = dict(row_value=(raw.row_value[0]+.1, *raw.row_value[1:]), objective=raw.objective+.1, problem_sha="0"*64)
    with pytest.raises(ValueError): import_snapshot(item.query, problem, replace(raw, **{field: changed[field]}))


@pytest.mark.parametrize("hour", [0, 2])
def test_public_export_algebra_at_non_solution_values(hour):
    f = c.load_fixture()
    query = c.bind(c.hour_requests(f, "on_time", "early", "full_temporal", hour)["requests"][0])
    problem = compile_problem(query)
    model = c.build_point_model(query)
    vals = dict(problem.fixed)
    vals.update((name, (i+1)*.013) for i, name in enumerate(problem.columns))
    for v in model.component_data_objects(Var): v.set_value(vals[v.name], skip_validation=True)
    original = {row.name: row for row in model.component_data_objects(Constraint, active=True)}
    for row in problem.rows:
        activity = sum(a*vals[problem.columns[j]] for j, a in row.terms)
        old = original[row.name]
        if row.lower is not None:
            assert activity-row.lower == pytest.approx(row.original_scale*(value(old.body)-value(old.lower)), abs=1e-10)
        if row.upper is not None:
            assert row.upper-activity == pytest.approx(row.original_scale*(value(old.upper)-value(old.body)), abs=1e-10)
    objective = problem.constant + sum(a*vals[name] for name, a in zip(problem.columns, problem.linear)) + sum(
        a*vals[problem.columns[i]]*vals[problem.columns[j]] for i, j, a in problem.quadratic)
    assert objective == pytest.approx(value(model.objective), abs=1e-10)


def test_eliminated_child_generator_and_meter_lower_multiplier():
    root = frame().reference
    request = replace(frame().lower.query.request, outages=c.Outage("gen0", (), (0,)))
    query = c.bind(request, root.query, root.point, root.economic)
    point = analytic_point(query, 0)
    from src.staged_rts24_child_optimality_v1 import ChildLpEvidence, reduction
    zero_bus = tuple((i, 0.) for i in (1, 2, 3))
    zero_branch = tuple((i, 0.) for i in (0, 1, 2))
    cert = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), zero_bus, zero_branch,
        ((0, 0.),), ((0, 0.),), zero_branch, zero_branch, meter_lower_dual=1.)
    item = PointEvidence(query, point, child_lp=cert)
    problem, raw = raw_snapshot(item)
    assert import_snapshot(query, problem, raw) == item


def test_shifted_child_maximum_objective_and_nonzero_equality_duals():
    f = analytic_fixture()
    data = replace(f.before, branches=tuple(replace(b, phase_shift_rad=.01) if b.index == 0 else b for b in f.before.branches))
    f = replace(f, before=data, after=data, rights_before=(Q(20), Q(230)), rights_after=(Q(20), Q(230)), source_identity="analytic_shift_C250")
    requests = c.hour_requests(f, "on_time", "early", "full_temporal", 0)["requests"]
    root = c.bind(next(r for r in requests if r.role == "reference_base_P0"))

    def shifted(query, meter):
        return c.PointWitness(query.identity, float(meter), 0., ((0, float(meter)),),
            tuple(zip((1, 2, 3), (0., -meter/3000.-2*.01/3, -meter/1500.-.01/3))),
            tuple(zip((0, 1, 2), (meter/3.-10./3, meter/3.-10./3, 2*meter/3.+10./3))))
    parent = shifted(root, 100)
    query = c.bind(next(r for r in requests if r.role == "recovery_max_meter"), root, parent, analytic_economic(root, parent))
    point = shifted(query, 190)
    from src.staged_rts24_child_optimality_v1 import ChildLpEvidence, reduction
    cert = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), ((1, 0.), (2, 1.), (3, -1.)),
        ((0, -1.), (1, -1.), (2, 1.)), ((0, 0.),), ((0, 0.),), ((0, 0.), (1, 0.), (2, 0.)), ((0, 0.), (1, 3.), (2, 0.)))
    item = PointEvidence(query, point, child_lp=cert)
    problem, raw = raw_snapshot(item)
    assert raw.objective == -190.
    assert import_snapshot(query, problem, raw) == item


@pytest.mark.parametrize("mutation", ["bad_rc", "suboptimal", "primal_thermal", "nonfinite_objective"])
def test_optimal_label_cannot_replace_numeric_evidence(mutation):
    item = frame(1).raw
    problem, raw = raw_snapshot(item)
    if mutation == "bad_rc":
        raw = replace(raw, column_dual=tuple(v+1. for v in raw.column_dual))
    elif mutation == "nonfinite_objective":
        raw = replace(raw, objective=float("inf"))
    else:
        # Rebuild all echoes for a new feasible but nonoptimal / thermally invalid point.
        point = analytic_point(item.query, 100, 50 if mutation == "suboptimal" else 30)
        item = replace(item, point=point)
        problem, raw = raw_snapshot(item)
    with pytest.raises(ValueError): import_snapshot(item.query, problem, raw)


def test_hessian_transport_has_half_quadratic_factor_and_original_columns():
    problem = compile_problem(frame().reference.query)
    start, index, values = hessian_columns(problem)
    assert len(start) == len(problem.columns)+1
    assert index == (problem.columns.index("generation[0]"),)
    assert values == (2e-8,)
    assert start[-1] == 1
    lp = compile_problem(frame(1).raw.query)
    assert hessian_columns(lp) == ((0,)*(len(lp.columns)+1), (), ())


@pytest.mark.parametrize("quadratic", [((0, 1, 1.),), ((0, 0, -1.),), ((0, 0, 1.), (0, 0, 1.))])
def test_unsupported_hessian_cannot_be_transported(quadratic):
    problem = compile_problem(frame().reference.query)
    with pytest.raises(ValueError): hessian_columns(replace(problem, quadratic=quadratic))


def test_wrong_snapshot_dual_convention_rejected():
    item = frame().reference
    problem, raw = raw_snapshot(item)
    with pytest.raises(ValueError, match="snapshot binding"):
        import_snapshot(item.query, problem, replace(raw, schema="unspecified_backend"))


def test_free_angle_raw_reduced_cost_is_checked():
    item = frame(1).raw
    problem, raw = raw_snapshot(item)
    i = problem.columns.index("angle[2]")
    changed = list(raw.column_dual)
    changed[i] = 1.
    with pytest.raises(ValueError, match="reduced-cost echo"):
        import_snapshot(item.query, problem, replace(raw, column_dual=tuple(changed)))


def test_elimination_map_retains_original_bounds_and_rows():
    problem = compile_problem(frame(1).raw.query)
    eliminated = {v.name: v for v in problem.eliminated_variables}
    assert eliminated["angle[1]"].reason == "original_fixed"
    assert eliminated["meter"].lower == eliminated["meter"].upper == 100.
    assert eliminated["flow[2]"].reason == "inactive_branch_zero"
    assert (eliminated["flow[2]"].lower, eliminated["flow[2]"].upper) == (-200., 200.)
    assert {r.name for r in problem.eliminated_rows} == {"branch_flow[2]"}
    normal = compile_problem(frame().reference.query)
    rows = {r.name: r for r in normal.eliminated_rows}
    assert rows["curtailment_bound"].constant == -100.
    assert rows["curtailment_bound"].upper == 0.


@pytest.mark.parametrize("mutation", ["negative_qp", "lower_row", "bad_constant"])
def test_unsupported_original_problem_fails_before_transport(monkeypatch, mutation):
    build = c.build_point_model

    def changed(query):
        model = build(query)
        if mutation == "negative_qp": model.objective.set_value(-model.generation[0]**2)
        elif mutation == "lower_row": model.extra = Constraint(expr=model.generation[0] >= 1.)
        else: model.extra = Constraint(expr=model.meter <= 0.)
        return model
    monkeypatch.setattr(c, "build_point_model", changed)
    with pytest.raises(ValueError): compile_problem(frame().reference.query)


@pytest.mark.parametrize("flag,column,row", [(True, (), ()), (False, (float("nan"),), ()),
    (True, (float("nan"),), (float("nan"),)), (None, (), ()), (False, [], [])])
def test_actual_dual_validity_and_payload_are_consistent(flag, column, row):
    ex = example()
    item = PointEvidence(ex["actual_query"], ex["actual_point"])
    problem, raw = raw_snapshot(item)
    with pytest.raises(ValueError):
        import_snapshot(item.query, problem, replace(raw, dual_valid=flag, column_dual=column, row_dual=row))


def test_python_numeric_equality_cannot_replace_canonical_problem_identity():
    item = frame().reference
    problem, raw = raw_snapshot(item)
    changed = replace(problem, constant=int(problem.constant))
    assert changed == problem and changed.identity != problem.identity
    with pytest.raises(ValueError, match="problem binding"):
        import_snapshot(item.query, changed, replace(raw, problem_sha=changed.identity))
