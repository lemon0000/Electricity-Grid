from dataclasses import replace
from fractions import Fraction as Q
import json

import pytest
import yaml

from experiments.staged_rts24_analytic_examples_v1 import example, economic_evidence
import src.staged_rts24_development_v1 as c
from src.staged_rts24_audit_v1 import audit_point, audit_legal_x, audit_economic_base


@pytest.fixture(autouse=True)
def deny_solver_calls(monkeypatch):
    import pyomo.environ as pyo
    import src.grid.dc_opf as dc
    import src.grid.network_grid_need as need
    import src.grid.scopf as security
    def denied(*args, **kwargs): pytest.fail("solver requested during build-only tests")
    for module in (pyo, dc, need, security): monkeypatch.setattr(module, "SolverFactory", denied)


@pytest.fixture
def fixture():
    return c.load_fixture()


def test_public_source_selection_project_and_immutable_before(fixture):
    f = fixture
    assert (len(f.before.buses), len(f.before.generators), len(f.before.branches)) == (24, 33, 38)
    assert f.before.total_demand_mw == pytest.approx(2280.)
    assert sum(bool(s.branches) for s in f.selected) == 37
    assert sum(bool(s.generators) for s in f.selected) == 32
    assert not any(s.branches == (10,) or s.generators == (14,) for s in f.selected)
    assert f.selected[0] == c.Outage("branch_0", (0,))
    for before, after in zip(f.before.branches, f.after.branches):
        if before.index in (11, 12):
            assert after.rate_a_mw == before.rate_a_mw+100
            assert after.rate_c_mw == before.rate_c_mw+100
            assert replace(after, rate_a_mw=before.rate_a_mw, rate_c_mw=before.rate_c_mw) == before
        else:
            assert after == before
    assert f.before is not f.after


def test_scaled_units_and_unclipped_followup_deadlines(fixture):
    f = fixture
    assert f.parameters.capacity == 40 and f.parameters.slope == Q(5, 4)
    assert f.parameters.auxiliary_mw == 5 and f.parameters.max_debt == 80
    assert f.parameters.alpha == Q(4, 5) and f.parameters.eta == 1
    assert f.rights_before == (120, 40) and f.rights_after == (160, 100)
    assert json.loads(f.x_envelope_json)["max_call_mw"] == "100"
    assert json.loads(f.x_envelope_json)["response_model"] == "static_hourly_declared_branch_or_generator_outage_same_hour_redispatch"
    assert json.loads(f.x_envelope_json)["source_response_model"] == "preventive_hourly_declared_line_outage"
    assert [c.hour_requests(f, "on_time", "early", "full_temporal", h)["reference_mw"] for h in (0, 2, 3)] == [150, 160, 210]
    assert c.observe(f, "on_time", "early", 6).due == 8
    assert c.observe(f, "on_time", "early", 7).due == 9
    assert c.observe(f, "on_time", "early", 2).clean_mwh == 168
    assert c.observe(f, "on_time", "late", 2).clean_mwh == 128
    assert not hasattr(c.observe(f, "on_time", "early", 2), "supply_mw")


def test_project_timing_rights_and_reference_refusal_remain_separate(fixture):
    assert not c.observe(fixture, "on_time", "early", 1).commissioned
    assert c.observe(fixture, "on_time", "early", 2).commissioned
    assert not c.observe(fixture, "delayed", "early", 3).commissioned
    assert c.observe(fixture, "delayed", "early", 4).commissioned
    h = c.hour_requests(fixture, "delayed", "early", "full_temporal", 3)
    assert h["reference_connection_shortfall_mw"] == 50
    assert h["observation"].workload == 140  # No reduction of exogenous arrivals.
    assert h["reference_mw"] == 210 and h["firm"]+h["conditional"] == 160


def test_hour_dag_roles_actual_outage_and_count_bounds(fixture):
    normal = c.hour_requests(fixture, "on_time", "early", "full_temporal", 0)
    fault = c.hour_requests(fixture, "on_time", "early", "full_temporal", 1)
    instant = c.hour_requests(fixture, "on_time", "early", "instantaneous", 1)
    assert normal["solver_node_upper_bound_including_actual"] == 143
    assert fault["solver_node_upper_bound_including_actual"] == 144
    assert instant["solver_node_upper_bound_including_actual"] == 142
    assert fault["actual_outage"].branches == (0,)
    assert sum(r.role == "fault_firm_F" for r in fault["requests"]) == 69
    assert sum(r.role == "fault_raw_need" for r in fault["requests"]) == 69
    assert not any(r.role == "actual_P" for r in fault["requests"])
    raw = next(r for r in fault["requests"] if r.role == "fault_raw_need")
    assert raw.curtailment_max == 160  # Keep the complete request; legal X is 40 separately.
    with pytest.raises(ValueError, match="anchor"):
        c.bind(raw)


def test_query_identity_covers_frame_network_role_power_and_parent(fixture):
    base = next(r for r in c.hour_requests(fixture, "on_time", "early", "full_temporal", 0)["requests"]
                if r.role == "reference_base_P0")
    variants = [replace(base, hour=1), replace(base, method="fixed_headroom"), replace(base, data=fixture.after), replace(base, clean_path="late"),
                replace(base, meter_min=Q(149), meter_max=Q(149)), replace(base, role="normal_contract_C", meter_min=Q(160), meter_max=Q(160))]
    assert len({base.identity, *(r.identity for r in variants)}) == 7
    late = next(r for r in c.hour_requests(fixture, "on_time", "late", "full_temporal", 0)["requests"]
                if r.role == "reference_base_P0")
    assert late == replace(base, clean_path="late")
    actual = c.actual_request(fixture, "on_time", "early", "full_temporal", 1, Q(145))
    assert actual.role == "actual_P" and actual.curtailment_max == 0 and actual.outages.branches == (0,)
    with pytest.raises(ValueError): c.actual_request(fixture, "on_time", "early", "full_temporal", 1, 145.)


def test_parent_clean_path_must_match_in_binding_and_independent_audit():
    e = example()
    raw = replace(e["raw_query"].request, clean_path="different")
    with pytest.raises(ValueError, match="frame"):
        c.bind(raw, e["base_query"], e["base_point"], e["base_economic"])
    invalid = replace(e["raw_query"], request=raw)
    with pytest.raises(ValueError, match="frame"):
        audit_point(invalid, replace(e["raw_point"], query_sha=invalid.identity))


def test_source_and_config_drift_rejected(tmp_path):
    raw = yaml.safe_load(c.CONFIG.read_text(encoding="utf-8"))
    raw["business"]["sha256"] = "0"*64
    path = tmp_path/"fixture.yaml"
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="source SHA"): c.load_fixture(path)
    raw = yaml.safe_load(c.CONFIG.read_text(encoding="utf-8"))
    raw["contingencies"]["expected_excluded_branches"] = []
    path.write_text(yaml.safe_dump(raw), encoding="utf-8")
    with pytest.raises(ValueError, match="excluded"): c.load_fixture(path)


def test_public_models_build_without_a_solver_or_fabricated_parent(fixture, monkeypatch):
    import pyomo.environ as pyo
    monkeypatch.setattr(pyo, "SolverFactory", lambda *a, **k: pytest.fail("solver requested during build"))
    for hour in (0, 2):
        request = c.hour_requests(fixture, "on_time", "early", "full_temporal", hour)["requests"][0]
        bound = c.bind(request)
        model = c.build_point_model(bound)
        assert (len(model.BUS), len(model.GEN), len(model.BRANCH)) == (24, 33, 38)
        assert len(list(model.component_data_objects(pyo.Var))) == 97
        assert len(list(model.component_data_objects(pyo.Constraint))) == 64
        with pytest.raises(ValueError, match="unresolved"): c.point_from_model(bound, model)
    fault = next(r for r in c.hour_requests(fixture, "on_time", "early", "full_temporal", 1)["requests"] if r.role == "fault_firm_F")
    with pytest.raises(ValueError): c.build_point_model(c.BoundQuery(fault))


@pytest.mark.parametrize("transformer", [False, True])
def test_analytic_triangle_point_and_model_equations_agree_without_optimization(transformer):
    import pyomo.environ as pyo
    e = example(transformer)
    for role in ("base", "raw", "actual"):
        query, point = e[role+"_query"], e[role+"_point"]
        observed = audit_point(query, point)
        assert observed["point_constraints_satisfied"] and observed["minimum_established"] is False
        model = c.build_point_model(query)
        model.meter.value, model.curtailment.value = point.meter_load_mw, point.curtailment_mw
        for name, pairs in (("generation", point.generation_mw), ("angle", point.angles_rad), ("flow", point.flows_mw)):
            for i, value in pairs: getattr(model, name)[i].value = value
        for con in model.component_data_objects(pyo.Constraint):
            body = pyo.value(con.body)
            assert con.lower is None or body >= pyo.value(con.lower)-1e-9
            assert con.upper is None or body <= pyo.value(con.upper)+1e-9
        if role == "base":
            first = 160. if transformer else 120.
            expected_cost = point.meter_load_mw-1e-8*(first**2+30.**2)
            assert pyo.value(model.objective) == pytest.approx(expected_cost, abs=1e-9)
        if role == "raw": assert pyo.value(model.objective) == point.curtailment_mw
        assert c.point_from_model(query, model) == point


def test_parent_point_must_be_complete_physical_and_same_frame():
    e = example()
    raw = e["raw_query"].request
    with pytest.raises(ValueError):
        c.bind(raw, e["base_query"], replace(e["base_point"], meter_load_mw=1000.), e["base_economic"])
    with pytest.raises(ValueError, match="anchor"):
        c.bind(replace(raw, hour=1), e["base_query"], e["base_point"])
    with pytest.raises(ValueError, match="identity"):
        audit_point(e["raw_query"], replace(e["raw_point"], query_sha=e["actual_query"].identity))


@pytest.mark.parametrize("change", ["balance", "angle", "outage_flow", "generation", "redispatch", "nan", "indices", "curtailment"])
def test_point_auditor_rejects_independent_corruption(change):
    e = example()
    point, query = e["raw_point"], e["raw_query"]
    if change == "balance": point = replace(point, meter_load_mw=point.meter_load_mw-1.)
    if change == "angle": point = replace(point, angles_rad=((1, 0.), (2, -.03), (3, -.08)))
    if change == "outage_flow": point = replace(point, flows_mw=((0, 30.), (1, 60.), (2, 1.)))
    if change == "generation": point = replace(point, generation_mw=((0, -1.), (1, 30.), (2, 0.)))
    if change == "redispatch": point = replace(point, generation_mw=((0, 399.), (1, 30.), (2, 0.)))
    if change == "nan": point = replace(point, flows_mw=((0, float("nan")), (1, 60.), (2, 0.)))
    if change == "indices": point = replace(point, generation_mw=((0, 30.), (0, 30.), (2, 0.)))
    if change == "curtailment": point = replace(point, curtailment_mw=point.meter_load_mw+1.)
    if change in ("nan", "indices"):
        with pytest.raises(ValueError): audit_point(query, point)
    else:
        assert not audit_point(query, point)["point_constraints_satisfied"]


def test_raw_point_is_not_a_legal_x_or_minimum_certificate():
    e = example()
    assert audit_legal_x(e["raw_query"], e["raw_point"], Q(50), Q(100))["point_legal_under_X"]
    with pytest.raises(ValueError, match="rights"):
        audit_legal_x(e["raw_query"], e["raw_point"], Q(120), Q(30))
    other = example(firm=120)
    result = audit_legal_x(other["raw_query"], other["raw_point"], Q(120), Q(30))
    assert not result["point_legal_under_X"] and result["minimum_established"] is False
    assert result["independent_firm_point_still_required"]
    with pytest.raises(ValueError): audit_legal_x(e["actual_query"], e["actual_point"], Q(50), Q(100))


def test_islanding_and_outaged_generator_cannot_hide_in_a_feasible_flag(fixture):
    e = example()
    original = e["base_query"].request.data
    data = replace(original, branches=tuple(replace(b, in_service=False) if b.index == 2 else b for b in original.branches),
        generators=tuple(replace(g, cost_linear=1.-2e-8*30.) if g.index in (0, 1) else g for g in original.generators))
    base = replace(e["base_query"].request, data=data, meter_min=Q(60), meter_max=Q(60), connection_capacity=Q(60), rights=(Q(30), Q(30)))
    base_bound = c.bind(base)
    base_point = replace(e["raw_point"], query_sha=base_bound.identity, meter_load_mw=60., curtailment_mw=0.)
    assert audit_point(base_bound, base_point)["point_constraints_satisfied"]
    request = replace(base, role="fault_raw_need", objective="min_curtailment", curtailment_max=Q(60),
                      anchor_id=base.identity, outages=c.Outage("generator_2", (), (2,)))
    evidence = economic_evidence(base_bound, base_point)
    bound = c.bind(request, base_bound, base_point, evidence)
    point = replace(base_point, query_sha=bound.identity, generation_mw=((0, 30.), (1, 30.), (2, 1.)))
    assert audit_point(bound, point)["residuals"]["outage_generation_mw"] == 1.
    assert not c.connected(fixture.before, (10,))
    island = replace(request, outages=c.Outage("branch_1", (1,)))
    island_bound = c.bind(island, base_bound, base_point, evidence)
    with pytest.raises(ValueError, match="islanded"): c.build_point_model(island_bound)
    with pytest.raises(ValueError, match="islanded"): audit_point(island_bound, replace(base_point, query_sha=island_bound.identity))


def test_physical_parent_without_economic_evidence_is_rejected():
    e = example()
    with pytest.raises(ValueError, match="optimality evidence"):
        c.bind(e["raw_query"].request, e["base_query"], e["base_point"])
    assert audit_economic_base(e["base_query"], e["base_point"], e["base_economic"])["economic_kkt_satisfied"]
    data = replace(e["base_query"].request.data, generators=tuple(
        replace(g, cost_linear=2.) if g.index == 0 else g for g in e["base_query"].request.data.generators))
    base = c.bind(replace(e["base_query"].request, data=data))
    point = replace(e["base_point"], query_sha=base.identity)
    evidence = economic_evidence(base, point)
    assert audit_point(base, point)["point_constraints_satisfied"]
    assert not audit_economic_base(base, point, evidence)["economic_kkt_satisfied"]
    with pytest.raises(ValueError, match="economic base"):
        c.bind(replace(e["raw_query"].request, data=data, anchor_id=base.request.identity), base, point, evidence)
    with pytest.raises(ValueError, match="binding"):
        audit_economic_base(e["base_query"], e["base_point"], replace(e["base_economic"], point_sha="0"*64))


@pytest.mark.parametrize("component", ["balance_duals", "flow_equation_duals", "generation_lower_duals", "generation_upper_duals", "flow_lower_duals", "flow_upper_duals"])
def test_economic_kkt_evidence_rejects_each_dual_corruption(component):
    e = example()
    certificate = e["base_economic"]
    original = getattr(certificate, component)
    corrupt = ((original[0][0], -2. if "lower" in component or "upper" in component else 2.), *original[1:])
    observed = audit_economic_base(e["base_query"], e["base_point"], replace(certificate, **{component: corrupt}))
    assert not observed["economic_kkt_satisfied"]


def test_thermal_reference_meter_and_connection_residuals_are_independent():
    e = example()
    q, point = e["base_query"], e["base_point"]
    thermal_data = replace(q.request.data, branches=tuple(replace(b, rate_a_mw=59.) if b.index == 1 else b for b in q.request.data.branches))
    thermal = c.bind(replace(q.request, data=thermal_data))
    assert audit_point(thermal, replace(point, query_sha=thermal.identity))["residuals"]["thermal_mw"] == 1.
    shifted = replace(point, angles_rad=tuple((i, v+.1) for i, v in point.angles_rad))
    assert audit_point(q, shifted)["residuals"]["reference_angle_rad"] == .1
    assert audit_point(q, replace(point, meter_load_mw=151.))["residuals"]["meter_bounds_mw"] == 1.
    source = e["actual_query"]
    actual = c.bind(replace(source.request, meter_min=Q(160), meter_max=Q(160)), source.base_query, source.base_point, source.base_economic)
    candidate = c.PointWitness(actual.identity, 160., 0., ((0, 80.), (1, 80.), (2, 0.)),
        ((1, 0.), (2, -.08), (3, -.24)), ((0, 80.), (1, 160.), (2, 0.)))
    residuals = audit_point(actual, candidate)["residuals"]
    assert residuals["connection_mw"] == 10.
    assert all(v <= 1e-6 for k, v in residuals.items() if k != "connection_mw")


def test_recovery_projection_can_have_a_positive_lower_bound():
    e = example()
    source = e["actual_query"]
    data = replace(source.request.data, generators=tuple(replace(g, p_min_mw=30.) if g.index in (0, 1) else g for g in source.request.data.generators))
    base = c.bind(replace(source.base_query.request, data=data))
    point = replace(source.base_point, query_sha=base.identity)
    request = replace(source.request, data=data, role="recovery_min_meter", meter_min=Q(0), meter_max=Q(150),
                      objective="min_meter", anchor_id=base.request.identity)
    bound = c.bind(request, base, point, economic_evidence(base, point))
    valid = replace(e["actual_point"], query_sha=bound.identity)
    assert audit_point(bound, valid)["point_constraints_satisfied"]
    assert not audit_point(bound, valid)["minimum_established"]
    assert not audit_point(bound, replace(valid, meter_load_mw=0.))["point_constraints_satisfied"]
    model = c.build_point_model(bound)
    assert model.generation[0].lb+model.generation[1].lb == 60.


def test_reference_raw_and_recovery_domains_cannot_be_silently_narrowed():
    e = example()
    source = e["actual_query"]
    raw = replace(source.request, role="reference_raw_need", meter_min=Q(149), meter_max=Q(149),
                  curtailment_max=Q(149), objective="min_curtailment")
    with pytest.raises(ValueError, match="P0"):
        c.bind(raw, source.base_query, source.base_point, source.base_economic)
    with pytest.raises(ValueError, match="projection domain"):
        replace(source.request, role="recovery_min_meter", objective="min_meter", meter_min=Q(60), meter_max=Q(150))


def test_diagnostic_output_is_exclusive(tmp_path, monkeypatch):
    import experiments.staged_rts24_build_diagnostic_v1 as diagnostic
    output = tmp_path/"build_01"
    output.mkdir()
    marker = output/"existing.json"
    marker.write_bytes(b"preserve")
    monkeypatch.setattr(diagnostic, "OUTPUT", output)
    with pytest.raises(FileExistsError): diagnostic.run(output)
    assert marker.read_bytes() == b"preserve"
    assert list(output.iterdir()) == [marker]


def test_build_completion_rejects_mutation_extra_directory_and_failure(tmp_path):
    import experiments.staged_rts24_build_diagnostic_v1 as diagnostic
    for name in diagnostic.ROLES: diagnostic.write(tmp_path/name, {})
    diagnostic.write(tmp_path/"completion.json", dict(status="build_only_diagnostic_completed",
        authority="DRAFT_NONAUTHORITATIVE", inventory=diagnostic.inventory(tmp_path)))
    diagnostic.verify_completion(tmp_path)
    foreign = tmp_path/"foreign"
    foreign.mkdir()
    with pytest.raises(ValueError, match="nonregular"): diagnostic.verify_completion(tmp_path)
    foreign.rmdir()
    (tmp_path/"events.jsonl").write_bytes(b"tampered")
    with pytest.raises(ValueError, match="inventory"): diagnostic.verify_completion(tmp_path)
    diagnostic.write(tmp_path/"failure.json", {})
    with pytest.raises(ValueError, match="inventory"): diagnostic.verify_completion(tmp_path)


@pytest.mark.parametrize("target", ["prior", "external"])
def test_diagnostic_preserved_bookend_rejects_root_and_external_drift(monkeypatch, target):
    import experiments.staged_rts24_build_diagnostic_v1 as diagnostic
    original = diagnostic.stamp

    def corrupt_selected(path):
        actual = original(path)
        corrupt = path == diagnostic.PRIOR if target == "prior" else path.suffix == ".pyd"
        return {**actual, "sha256": "0"*64} if corrupt else actual

    monkeypatch.setattr(diagnostic, "stamp", corrupt_selected)
    with pytest.raises(ValueError, match="prior audit SHA" if target == "prior" else "external bytes"):
        diagnostic.preserved()
