"""Independent numeric KKT audit of staged child LPs; never solves a model."""
from dataclasses import dataclass
from math import isfinite

from src.staged_rts24_development_v1 import digest
from src.staged_rts24_audit_v1 import audit_point, indexed, point_sha, check, TOL_KKT

SCHEMA = "staged_child_lp_fixed_variable_elimination_v1"


@dataclass(frozen=True)
class ChildLpEvidence:
    query_sha: str
    point_sha: str
    reduction_sha: str
    balance_duals: tuple[tuple[int, float], ...]
    flow_equation_duals: tuple[tuple[int, float], ...]
    generation_lower_duals: tuple[tuple[int, float], ...]
    generation_upper_duals: tuple[tuple[int, float], ...]
    flow_lower_duals: tuple[tuple[int, float], ...]
    flow_upper_duals: tuple[tuple[int, float], ...]
    meter_lower_dual: float = 0.
    meter_upper_dual: float = 0.
    curtailment_lower_dual: float = 0.
    curtailment_upper_dual: float = 0.
    connection_dual: float = 0.
    curtailment_le_meter_dual: float = 0.


def reduction(query):
    """Recompute the reduced child problem without reading Pyomo or its bounds."""
    q, d = query.request, query.request.data
    check(q.anchor_id is not None and query.base_point is not None
          and q.objective in ("min_curtailment", "min_meter", "max_meter"), "anchored child LP required")
    anchor = dict(query.base_point.generation_mw)
    for b in d.branches:
        if not b.in_service or b.index in q.outages.branches: continue
        denominator = b.reactance_pu*b.tap_ratio
        check(isfinite(denominator) and denominator > 0, "nonfinite reduced branch denominator")
        coefficient = d.base_mva/denominator
        check(isfinite(coefficient) and coefficient > 0, "nonfinite reduced branch coefficient")
    bounds = {}
    for g in d.generators:
        if not g.in_service or g.index in q.outages.generators:
            bounds[g.index] = (0., 0.)
        else:
            step = float(q.redispatch_fraction)*g.p_max_mw
            bounds[g.index] = (max(g.p_min_mw, anchor[g.index]-step), min(g.p_max_mw, anchor[g.index]+step))
        check(bounds[g.index][0] <= bounds[g.index][1], "empty child generation box")
    return dict(schema=SCHEMA, generation_bounds=bounds,
        active_branches=tuple(b.index for b in d.branches if b.in_service and b.index not in q.outages.branches),
        fixed_meter=q.meter_min == q.meter_max, fixed_curtailment=q.curtailment_max == 0,
        reference_bus=d.reference_bus,
        connection_present=q.role not in ("reference_base_P0", "reference_raw_need"))


def audit_child_lp(query, point, evidence):
    """Numeric primal/KKT/duality consistency, not a rigorous certified bound."""
    primal = audit_point(query, point)  # Also rechecks the full economic parent.
    r = reduction(query)
    check(isinstance(evidence, ChildLpEvidence) and evidence.query_sha == query.identity
          and evidence.point_sha == point_sha(point) and evidence.reduction_sha == digest(r), "child LP evidence binding differs")
    q, d = query.request, query.request.data
    buses, gens, branches = ({v.index: v for v in vs} for vs in (d.buses, d.generators, d.branches))
    lam = indexed(evidence.balance_duals, set(buses))
    mu = indexed(evidence.flow_equation_duals, set(branches))
    gl = indexed(evidence.generation_lower_duals, set(gens))
    gu = indexed(evidence.generation_upper_duals, set(gens))
    fl = indexed(evidence.flow_lower_duals, set(branches))
    fu = indexed(evidence.flow_upper_duals, set(branches))
    ml, mh, cl, ch, kappa, rho = scalar = tuple(getattr(evidence, name) for name in
        ("meter_lower_dual", "meter_upper_dual", "curtailment_lower_dual", "curtailment_upper_dual", "connection_dual", "curtailment_le_meter_dual"))
    check(all(not isinstance(v, bool) and isinstance(v, (int, float)) and isfinite(v) for v in scalar), "nonfinite child scalar dual")
    active = set(r["active_branches"])
    check(all(gl[i] == gu[i] == 0 for i, (lo, hi) in r["generation_bounds"].items() if lo == hi), "eliminated generation dual must be zero")
    check(all(mu[i] == fl[i] == fu[i] == 0 for i in branches if i not in active), "eliminated branch dual must be zero")
    check(not r["fixed_meter"] or ml == mh == 0, "eliminated meter dual must be zero")
    check(not r["fixed_curtailment"] or cl == ch == 0, "eliminated curtailment dual must be zero")
    both_fixed = r["fixed_meter"] and r["fixed_curtailment"]
    check((r["connection_present"] and not both_fixed) or kappa == 0, "absent or eliminated connection dual must be zero")
    check(not both_fixed or rho == 0, "eliminated curtailment-meter dual must be zero")
    residual = dict(dual_sign=max([0.] + [-v for table in (gl, gu, fl, fu) for v in table.values()] + [-v for v in scalar]),
                    generation_stationarity=0., flow_stationarity=0., angle_stationarity=0.,
                    meter_stationarity=0., curtailment_stationarity=0., complementarity=0.)
    generation, flow = dict(point.generation_mw), dict(point.flows_mw)
    angle_gradient = {i: 0. for i in buses}
    for i, g in gens.items():
        lo, hi = r["generation_bounds"][i]
        if lo != hi:
            residual["generation_stationarity"] = max(residual["generation_stationarity"], abs(lam[g.bus]-gl[i]+gu[i]))
        residual["complementarity"] = max(residual["complementarity"], abs(gl[i]*(generation[i]-lo)), abs(gu[i]*(hi-generation[i])))
    for i in active:
        b = branches[i]
        residual["flow_stationarity"] = max(residual["flow_stationarity"], abs(-lam[b.from_bus]+lam[b.to_bus]+mu[i]-fl[i]+fu[i]))
        residual["complementarity"] = max(residual["complementarity"], abs(fl[i]*(flow[i]+b.rate_a_mw)), abs(fu[i]*(b.rate_a_mw-flow[i])))
        term = d.base_mva/(b.reactance_pu*b.tap_ratio)*mu[i]
        angle_gradient[b.from_bus] -= term
        angle_gradient[b.to_bus] += term
    residual["angle_stationarity"] = max([0.] + [abs(v) for i, v in angle_gradient.items() if i != d.reference_bus])
    dm, dc = {"min_curtailment": (0., 1.), "min_meter": (1., 0.), "max_meter": (-1., 0.)}[q.objective]
    if not r["fixed_meter"]: residual["meter_stationarity"] = abs(dm-lam[q.poi_bus]+kappa-rho-ml+mh)
    if not r["fixed_curtailment"]: residual["curtailment_stationarity"] = abs(dc+lam[q.poi_bus]-kappa+rho-cl+ch)
    m, c = point.meter_load_mw, point.curtailment_mw
    residual["complementarity"] = max(residual["complementarity"], abs(ml*(m-float(q.meter_min))), abs(mh*(float(q.meter_max)-m)),
        abs(cl*c), abs(ch*(float(q.curtailment_max)-c)), abs(kappa*(float(q.connection_capacity)-m+c)), abs(rho*(m-c)))

    # Evaluate the Lagrangian constant at free variables=0 and fixed variables=substituted.
    g0 = {i: lo if lo == hi else 0. for i, (lo, hi) in r["generation_bounds"].items()}
    m0, c0 = (float(q.meter_min) if r["fixed_meter"] else 0.), 0.
    dual = dm*m0+dc*c0
    for i, b in buses.items():
        dual += lam[i]*(sum(g0[g.index] for g in d.generators if g.bus == i)-b.demand_mw-(m0-c0 if i == q.poi_bus else 0.))
    for i, g in gens.items():
        lo, hi = r["generation_bounds"][i]
        dual += gl[i]*(lo-g0[i])+gu[i]*(g0[i]-hi)
    for i in active:
        b = branches[i]
        dual += mu[i]*d.base_mva/(b.reactance_pu*b.tap_ratio)*b.phase_shift_rad-(fl[i]+fu[i])*b.rate_a_mw
    dual += ml*(float(q.meter_min)-m0)+mh*(m0-float(q.meter_max))-cl*c0+ch*(c0-float(q.curtailment_max))
    dual += kappa*(m0-c0-float(q.connection_capacity))+rho*(c0-m0)
    objective = dm*m+dc*c
    gap = abs(objective-dual)
    check(all(isfinite(value) for value in (*residual.values(), objective, dual, gap)), "nonfinite LP audit arithmetic")
    satisfied = primal["point_constraints_satisfied"] and all(v <= TOL_KKT for v in residual.values()) and gap <= TOL_KKT
    return dict(lp_optimality_conditions_satisfied=satisfied, primal_audit=primal, kkt_residuals=residual,
        primal_objective=objective, numeric_dual_constant=dual, absolute_primal_dual_gap=gap, tolerance=TOL_KKT,
        minimum_conditions_satisfied=satisfied and q.objective != "max_meter",
        maximum_conditions_satisfied=satisfied and q.objective == "max_meter", rigorous_bound_certified=False,
        scope="declared_child_LP_numeric_KKT_only", reduction_schema=SCHEMA)
