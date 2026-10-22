"""Independent full-point DC arithmetic; no model-builder or solver import."""
from fractions import Fraction as Q
from math import isfinite
from dataclasses import asdict, is_dataclass
import hashlib
import json

TOL_MW = 1e-6
TOL_RAD = 1e-9
TOL_KKT = 1e-6


def point_sha(value):
    def plain(v):
        if is_dataclass(v): return plain(asdict(v))
        if isinstance(v, dict): return {str(k): plain(x) for k, x in v.items()}
        if isinstance(v, (tuple, list)): return [plain(x) for x in v]
        return v
    return hashlib.sha256(json.dumps(plain(value), sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()


def check(value, message):
    if not value: raise ValueError(message)


def indexed(values, expected):
    check(type(values) is tuple and all(type(i) is int and type(v) in (int, float) and isfinite(v) for i, v in values),
          "nonfinite or malformed point")
    result = dict(values)
    check(len(values) == len(result) and set(result) == expected, "incomplete or duplicate point indices")
    return result


def audit_point(query, witness):
    q, data = query.request, query.request.data
    check(type(q.rights) is tuple and len(q.rights) == 2 and all(isinstance(v, Q) and v >= 0 for v in q.rights)
          and sum(q.rights) == q.connection_capacity, "audit F/X decomposition differs")
    check(q.economic_regularization_quadratic == Q(1, 100000000), "audit objective policy differs")
    if q.role == "normal_contract_C": check(q.meter_min == q.meter_max == q.connection_capacity, "audit full C differs")
    if q.role == "fault_firm_F": check(q.meter_min == q.meter_max == q.rights[0], "audit firm F differs")
    if q.role == "fault_raw_need": check(q.meter_min == q.meter_max == q.curtailment_max == q.connection_capacity, "audit full raw load differs")
    if q.role in ("recovery_min_meter", "recovery_max_meter"):
        check(q.meter_min == 0 and q.meter_max == q.connection_capacity and q.curtailment_max == 0, "audit recovery domain differs")
    buses, gens, branches = ({v.index: v for v in values} for values in (data.buses, data.generators, data.branches))
    check(len(buses) == len(data.buses) and len(gens) == len(data.generators) and len(branches) == len(data.branches)
          and q.poi_bus in buses and data.reference_bus in buses, "invalid audit network indices")
    check(isfinite(data.base_mva) and data.base_mva > 0
          and all(isfinite(b.demand_mw) and b.demand_mw >= 0 for b in data.buses), "invalid audit network quantities")
    check(set(q.outages.branches) <= set(branches) and set(q.outages.generators) <= set(gens)
          and len(q.outages.branches)+len(q.outages.generators) <= 1, "invalid audit outage")
    adjacency = {i: set() for i in buses}
    for b in data.branches:
        check(b.from_bus in buses and b.to_bus in buses and b.from_bus != b.to_bus
              and all(isfinite(v) for v in (b.reactance_pu, b.tap_ratio, b.phase_shift_rad, b.rate_a_mw))
              and b.reactance_pu > 0 and b.tap_ratio > 0 and b.rate_a_mw > 0, "invalid audit branch")
        if b.in_service and b.index not in q.outages.branches:
            adjacency[b.from_bus].add(b.to_bus); adjacency[b.to_bus].add(b.from_bus)
    unseen, reached = [data.reference_bus], set()
    while unseen:
        current = unseen.pop()
        if current not in reached:
            reached.add(current); unseen.extend(adjacency[current]-reached)
    check(reached == set(buses), "islanded point rejected")
    check(all(g.bus in buses and isfinite(g.p_min_mw) and isfinite(g.p_max_mw)
              and 0 <= g.p_min_mw <= g.p_max_mw for g in data.generators), "invalid audit generator")
    check(all(isinstance(v, Q) and v >= 0 for v in (q.meter_min, q.meter_max, q.curtailment_max,
              q.connection_capacity, q.redispatch_fraction)) and q.meter_min <= q.meter_max
              and q.curtailment_max <= q.meter_max and q.redispatch_fraction <= 1, "invalid audit query bounds")
    if q.anchor_id is None:
        check(query.base_query is None and query.base_point is None and query.base_economic is None and q.role in ("normal_contract_C", "reference_base_P0")
              and not q.outages.branches and not q.outages.generators, "invalid audit economic base")
    else:
        parent, point = query.base_query, query.base_point
        check(parent is not None and point is not None and parent.request.anchor_id is None
              and parent.request.identity == q.anchor_id, "invalid audit parent identity")
        p = parent.request
        check((p.fixture_identity, p.plan, p.clean_path, p.hour, p.method, p.data, p.connection_capacity, p.rights) ==
              (q.fixture_identity, q.plan, q.clean_path, q.hour, q.method, q.data, q.connection_capacity, q.rights), "audit parent frame differs")
        check(p.role == ("normal_contract_C" if q.role.startswith("fault_") else "reference_base_P0"), "audit parent role differs")
        if q.role == "reference_raw_need":
            check(q.meter_min == q.meter_max == q.curtailment_max == p.meter_min == p.meter_max, "audit raw reference differs from P0")
        check(query.base_economic is not None and audit_economic_base(parent, point, query.base_economic)["economic_kkt_satisfied"], "audit economic parent invalid")
    check(witness.query_sha == query.identity, "point/query identity differs")
    generation = indexed(witness.generation_mw, {g.index for g in data.generators})
    theta = indexed(witness.angles_rad, {b.index for b in data.buses})
    flows = indexed(witness.flows_mw, {b.index for b in data.branches})
    meter, curtail = witness.meter_load_mw, witness.curtailment_mw
    check(type(meter) in (int, float) and type(curtail) in (int, float) and isfinite(meter) and isfinite(curtail), "nonfinite meter")
    check((q.anchor_id is None) == (query.anchor_sha is None), "missing corrective binding")
    anchor = dict(query.anchor_generation)
    check(not anchor or len(anchor) == len(query.anchor_generation) == len(data.generators)
          and set(anchor) == set(generation) and all(isfinite(v) for v in anchor.values()), "invalid audit anchor")
    check(q.anchor_id is None or bool(anchor), "missing corrective generation")
    residual = dict(balance_mw=0., flow_equation_mw=0., thermal_mw=0., generation_mw=0.,
                    redispatch_mw=0., outage_generation_mw=0., outage_flow_mw=0.,
                    meter_bounds_mw=max(float(q.meter_min)-meter, meter-float(q.meter_max), 0.),
                    curtailment_bounds_mw=max(-curtail, curtail-float(q.curtailment_max), curtail-meter, 0.),
                    connection_mw=0., reference_angle_rad=abs(theta[data.reference_bus]))
    if q.role not in ("reference_base_P0", "reference_raw_need"):
        residual["connection_mw"] = max(meter-curtail-float(q.connection_capacity), 0.)
    for bus in data.buses:
        balance = sum(generation[g.index] for g in data.generators if g.bus == bus.index) - bus.demand_mw
        if bus.index == q.poi_bus: balance -= meter-curtail
        balance -= sum(flows[b.index] for b in data.branches if b.from_bus == bus.index)
        balance += sum(flows[b.index] for b in data.branches if b.to_bus == bus.index)
        residual["balance_mw"] = max(residual["balance_mw"], abs(balance))
    for branch in data.branches:
        flow = flows[branch.index]
        online = branch.in_service and branch.index not in q.outages.branches
        expected = data.base_mva/(branch.reactance_pu*branch.tap_ratio) * (theta[branch.from_bus]-theta[branch.to_bus]-branch.phase_shift_rad) if online else 0.
        residual["flow_equation_mw"] = max(residual["flow_equation_mw"], abs(flow-expected))
        residual["thermal_mw"] = max(residual["thermal_mw"], abs(flow)-branch.rate_a_mw, 0.)
        if not online: residual["outage_flow_mw"] = max(residual["outage_flow_mw"], abs(flow))
    for generator in data.generators:
        output = generation[generator.index]
        available = generator.in_service and generator.index not in q.outages.generators
        if not available:
            residual["outage_generation_mw"] = max(residual["outage_generation_mw"], abs(output))
            residual["generation_mw"] = max(residual["generation_mw"], abs(output))
        else:
            residual["generation_mw"] = max(residual["generation_mw"], generator.p_min_mw-output, output-generator.p_max_mw, 0.)
            if anchor:
                residual["redispatch_mw"] = max(residual["redispatch_mw"], abs(output-anchor[generator.index])-float(q.redispatch_fraction)*generator.p_max_mw, 0.)
    passed = all(v <= (TOL_RAD if k == "reference_angle_rad" else TOL_MW) for k, v in residual.items())
    return dict(point_constraints_satisfied=passed, residuals=residual, minimum_established=False,
                scope="declared_static_dc_point_only")


def audit_economic_base(query, witness, evidence):
    """KKT sufficiency for the convex fixed-load economic DC base, independently.

    Fixed meter/curtailment/reference-angle variables are eliminated. Balance
    multipliers use G-Pd-Pnet-out+in=0; flow multipliers use f-B*dtheta=0.
    Box multipliers are nonnegative for lower-x and x-upper respectively.
    """
    q, d = query.request, query.request.data
    check(q.anchor_id is None and q.objective == "economic" and q.meter_min == q.meter_max
          and q.curtailment_max == 0 and q.economic_regularization_quadratic == Q(1, 100000000), "economic fixed-load base required")
    primal = audit_point(query, witness)
    check(evidence.query_sha == query.identity and evidence.point_sha == point_sha(witness), "economic evidence binding differs")
    check(all(isfinite(g.cost_quadratic) and g.cost_quadratic >= 0 and isfinite(g.cost_linear) for g in d.generators), "nonconvex or nonfinite economic objective")
    bus_ids, gen_ids, branch_ids = ({v.index for v in values} for values in (d.buses, d.generators, d.branches))
    lam = indexed(evidence.balance_duals, bus_ids)
    mu = indexed(evidence.flow_equation_duals, branch_ids)
    gl = indexed(evidence.generation_lower_duals, gen_ids)
    gu = indexed(evidence.generation_upper_duals, gen_ids)
    fl = indexed(evidence.flow_lower_duals, branch_ids)
    fu = indexed(evidence.flow_upper_duals, branch_ids)
    generation, flows = dict(witness.generation_mw), dict(witness.flows_mw)
    residual = dict(dual_sign=0., generation_stationarity=0., flow_stationarity=0., angle_stationarity=0., complementarity=0.)
    residual["dual_sign"] = max([0.] + [-v for m in (gl, gu, fl, fu) for v in m.values()])
    for g in d.generators:
        low, high = (g.p_min_mw, g.p_max_mw) if g.in_service else (0., 0.)
        output = generation[g.index]
        gradient = 2*(g.cost_quadratic+float(q.economic_regularization_quadratic))*output+g.cost_linear if g.in_service else 0.
        residual["generation_stationarity"] = max(residual["generation_stationarity"], abs(gradient+lam[g.bus]-gl[g.index]+gu[g.index]))
        residual["complementarity"] = max(residual["complementarity"], abs(gl[g.index]*(output-low)), abs(gu[g.index]*(high-output)))
    angle_gradient = {i: 0. for i in bus_ids}
    for b in d.branches:
        i, flow = b.index, flows[b.index]
        residual["flow_stationarity"] = max(residual["flow_stationarity"], abs(-lam[b.from_bus]+lam[b.to_bus]+mu[i]-fl[i]+fu[i]))
        residual["complementarity"] = max(residual["complementarity"], abs(fl[i]*(flow+b.rate_a_mw)), abs(fu[i]*(b.rate_a_mw-flow)))
        if b.in_service:
            term = d.base_mva/(b.reactance_pu*b.tap_ratio)*mu[i]
            angle_gradient[b.from_bus] -= term; angle_gradient[b.to_bus] += term
    residual["angle_stationarity"] = max([0.] + [abs(v) for i, v in angle_gradient.items() if i != d.reference_bus])
    return dict(economic_kkt_satisfied=primal["point_constraints_satisfied"] and all(v <= TOL_KKT for v in residual.values()),
                primal_audit=primal, kkt_residuals=residual, tolerance=TOL_KKT,
                objective_policy="fixed_regularized_economic_base",
                scope="convex_regularized_fixed_load_economic_dc_KKT_with_declared_numeric_tolerances")


def audit_legal_x(query, witness, firm, conditional):
    """Raw counterfactual point stays raw; no relabelling or optimality claim."""
    check(isinstance(firm, Q) and isinstance(conditional, Q) and firm >= 0 and conditional >= 0, "exact nonnegative rights required")
    check(query.request.rights == (firm, conditional) and query.request.role == "fault_raw_need"
          and query.request.meter_min == query.request.meter_max == firm+conditional,
          "wrong raw contract role/rights")
    audited = audit_point(query, witness)
    legal = (audited["point_constraints_satisfied"] and witness.curtailment_mw <= float(conditional)+TOL_MW
             and witness.meter_load_mw-witness.curtailment_mw >= float(firm)-TOL_MW)
    return dict(point_legal_under_X=legal, minimum_established=False, independent_firm_point_still_required=True,
                temporal_backing="not_established")
