from dataclasses import replace
from fractions import Fraction as Q

import pytest

from experiments.staged_rts24_causal_examples_v1 import (
    analytic_fixture, analytic_hour, analytic_point, analytic_economic, analytic_child,
)
from src import staged_rts24_development_v1 as c
from src.staged_rts24_causal_v1 import initialize_execution
from src.staged_rts24_child_optimality_v1 import audit_child_lp, reduction, ChildLpEvidence


@pytest.fixture(autouse=True)
def no_solver(monkeypatch):
    import pyomo.environ as pyo
    import src.grid.dc_opf as dc
    import src.grid.network_grid_need as need
    import src.grid.scopf as security

    def denied(*args, **kwargs): pytest.fail("solver requested by ordinary child-LP test")
    for module in (pyo, dc, need, security): monkeypatch.setattr(module, "SolverFactory", denied)


def sample(hour=0):
    fixture = analytic_fixture()
    state = initialize_execution(fixture, "on_time", "early", "full_temporal")
    # This helper only selects an independent current-hour analytic frame, not a simulated prefix.
    state = replace(state, ledger=replace(state.ledger, last_hour=hour+state.hour_offset-1))
    return analytic_hour(fixture, state)


@pytest.mark.parametrize("hour,role,objective", [(1, "raw", 40.), (0, "lower", 40.), (0, "upper", -150.), (1, "upper", -60.)])
def test_exact_analytic_minima_and_maxima(hour, role, objective):
    item = getattr(sample(hour), role)
    observed = audit_child_lp(item.query, item.point, item.child_lp)
    assert observed["lp_optimality_conditions_satisfied"]
    assert observed["primal_objective"] == observed["numeric_dual_constant"] == objective
    assert observed["absolute_primal_dual_gap"] == 0.
    assert not observed["rigorous_bound_certified"]
    assert not observed["primal_audit"]["minimum_established"]


@pytest.mark.parametrize("hour,role,meter,curtail", [(1, "raw", 100, 50), (0, "lower", 50, 0), (0, "upper", 140, 0)])
def test_feasible_nonoptimal_points_cannot_supply_decision_endpoints(hour, role, meter, curtail):
    item = getattr(sample(hour), role)
    point = analytic_point(item.query, meter, curtail)
    evidence = replace(item.child_lp, point_sha=c.digest(point))
    result = audit_child_lp(item.query, point, evidence)
    assert result["primal_audit"]["point_constraints_satisfied"]
    assert not result["lp_optimality_conditions_satisfied"]
    assert result["absolute_primal_dual_gap"] == 10.


@pytest.mark.parametrize("name", ["query_sha", "point_sha", "reduction_sha"])
def test_child_evidence_binds_query_point_and_reduction(name):
    item = sample(1).raw
    with pytest.raises(ValueError, match="binding"):
        audit_child_lp(item.query, item.point, replace(item.child_lp, **{name: "0"*64}))


@pytest.mark.parametrize("name", ["balance_duals", "flow_equation_duals", "generation_lower_duals", "generation_upper_duals", "flow_lower_duals", "flow_upper_duals"])
@pytest.mark.parametrize("mutation", ["missing", "duplicate", "nan"])
def test_complete_finite_dual_arrays(name, mutation):
    item = sample().lower
    rows = getattr(item.child_lp, name)
    changed = rows[:-1] if mutation == "missing" else rows+(rows[0],) if mutation == "duplicate" else ((rows[0][0], float("nan")), *rows[1:])
    with pytest.raises(ValueError): audit_child_lp(item.query, item.point, replace(item.child_lp, **{name: changed}))


@pytest.mark.parametrize("name", ["meter_lower_dual", "meter_upper_dual", "curtailment_lower_dual", "curtailment_upper_dual", "connection_dual", "curtailment_le_meter_dual"])
def test_nonfinite_scalar_duals_rejected(name):
    item = sample().upper
    with pytest.raises(ValueError): audit_child_lp(item.query, item.point, replace(item.child_lp, **{name: float("inf")}))


def test_reference_raw_connection_is_absent_and_inactive_flow_is_eliminated():
    item = sample(1).raw
    assert item.query.request.role == "reference_raw_need"
    with pytest.raises(ValueError, match="connection"):
        audit_child_lp(item.query, item.point, replace(item.child_lp, connection_dual=1.))
    with pytest.raises(ValueError, match="eliminated branch"):
        audit_child_lp(item.query, item.point, replace(item.child_lp, flow_equation_duals=((0, 0.), (1, 0.), (2, 1.))))
    with pytest.raises(ValueError, match="eliminated meter"):
        audit_child_lp(item.query, item.point, replace(item.child_lp, meter_lower_dual=1.))


def test_valid_redundant_upper_bound_dual_distributions_are_accepted():
    item = sample().upper
    for fraction in (0., .25, 1.):
        evidence = replace(item.child_lp, connection_dual=fraction, meter_upper_dual=1.-fraction)
        assert audit_child_lp(item.query, item.point, evidence)["lp_optimality_conditions_satisfied"]


def test_eliminated_generator_and_active_meter_lower_bound():
    root = sample().reference
    request = replace(sample().lower.query.request, outages=c.Outage("gen0", (), (0,)))
    query = c.bind(request, root.query, root.point, root.economic)
    point = analytic_point(query, 0)
    zero_bus = tuple((i, 0.) for i in (1, 2, 3))
    zero_branch = tuple((i, 0.) for i in (0, 1, 2))
    evidence = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), zero_bus, zero_branch,
        ((0, 0.),), ((0, 0.),), zero_branch, zero_branch, meter_lower_dual=1.)
    assert audit_child_lp(query, point, evidence)["lp_optimality_conditions_satisfied"]
    with pytest.raises(ValueError, match="eliminated generation"):
        audit_child_lp(query, point, replace(evidence, generation_lower_duals=((0, 1.),)))


def test_curtailment_meter_coupling_and_upper_box_can_have_nonzero_duals():
    root = sample().reference
    request = replace(root.query.request, role="reference_raw_need", objective="min_curtailment",
                      curtailment_max=Q(100), outages=c.Outage("gen0", (), (0,)), anchor_id=root.query.request.identity)
    query = c.bind(request, root.query, root.point, root.economic)
    point = analytic_point(query, 100, 100)
    branch = tuple((i, 0.) for i in (0, 1, 2))
    evidence = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), tuple((i, -2.) for i in (1, 2, 3)),
        branch, ((0, 0.),), ((0, 0.),), branch, branch, curtailment_le_meter_dual=1.)
    assert audit_child_lp(query, point, evidence)["lp_optimality_conditions_satisfied"]
    alternate = replace(evidence, curtailment_le_meter_dual=0., curtailment_upper_dual=1.)
    assert audit_child_lp(query, point, alternate)["lp_optimality_conditions_satisfied"]
    assert not audit_child_lp(query, point, replace(evidence, curtailment_le_meter_dual=-1.))["lp_optimality_conditions_satisfied"]


def test_phase_shift_lagrangian_constant_and_maximum_sign():
    fixture = analytic_fixture()
    data = replace(fixture.before, branches=tuple(replace(b, phase_shift_rad=.01) if b.index == 0 else b for b in fixture.before.branches))
    fixture = replace(fixture, before=data, after=data, rights_before=(Q(20), Q(230)), rights_after=(Q(20), Q(230)), source_identity="analytic_shift_C250")
    requests = c.hour_requests(fixture, "on_time", "early", "full_temporal", 0)["requests"]
    root = c.bind(next(r for r in requests if r.role == "reference_base_P0"))

    def shifted(query, meter):
        theta = (0., -meter/3000.-2*.01/3, -meter/1500.-.01/3)
        flow = (meter/3.-10./3, meter/3.-10./3, 2*meter/3.+10./3)
        return c.PointWitness(query.identity, float(meter), 0., ((0, float(meter)),), tuple(zip((1, 2, 3), theta)), tuple(zip((0, 1, 2), flow)))

    parent = shifted(root, 100)
    query = c.bind(next(r for r in requests if r.role == "recovery_max_meter"), root, parent, analytic_economic(root, parent))
    point = shifted(query, 190)
    evidence = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), ((1, 0.), (2, 1.), (3, -1.)),
        ((0, -1.), (1, -1.), (2, 1.)), ((0, 0.),), ((0, 0.),), ((0, 0.), (1, 0.), (2, 0.)), ((0, 0.), (1, 3.), (2, 0.)))
    result = audit_child_lp(query, point, evidence)
    assert result["lp_optimality_conditions_satisfied"]
    assert result["numeric_dual_constant"] == result["primal_objective"] == -190.


def test_maximum_certificate_cannot_be_relabelled_as_a_minimum():
    item = sample().upper
    request = replace(item.query.request, role="recovery_min_meter", objective="min_meter")
    query = c.bind(request, item.query.base_query, item.query.base_point, item.query.base_economic)
    point = replace(item.point, query_sha=query.identity)
    evidence = replace(item.child_lp, query_sha=query.identity, point_sha=c.digest(point), reduction_sha=c.digest(reduction(query)))
    assert not audit_child_lp(query, point, evidence)["lp_optimality_conditions_satisfied"]


@pytest.mark.parametrize("reactance,tap", [(1e-320, 1.), (1e-200, 1e-200), (1e200, 1e200)])
def test_finite_input_numbers_cannot_hide_nonfinite_derived_coefficients(reactance, tap):
    item = sample().upper
    data = replace(item.query.request.data, branches=tuple(replace(b, reactance_pu=reactance, tap_ratio=tap) if b.index == 0 else b
                                                         for b in item.query.request.data.branches))
    query = replace(item.query, request=replace(item.query.request, data=data))
    with pytest.raises(ValueError, match="reduced branch"): reduction(query)


def test_finite_but_overflowing_dual_arithmetic_is_unresolved():
    item = sample().upper
    with pytest.raises(ValueError, match="nonfinite LP"):
        audit_child_lp(item.query, item.point, replace(item.child_lp, flow_equation_duals=((0, 1e308), (1, 0.), (2, 0.))))
