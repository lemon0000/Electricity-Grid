"""Greedy versus optimal deferral scheduling under real N-1 capacity.

DRAFT_NONAUTHORITATIVE. Zero solver for the greedy arm; one LP for the optimal arm.

Why this exists
---------------
`advance()` in the frozen B1 module is a *rule*: serve the grid request first, then the
clean request, and recover debt only in hours that issue no request at all. Nothing in
the protocol says that rule is optimal, but the paper's central claim ("the plan is not
deliverable") has so far been evaluated only under it. A reviewer can answer that with
"your policy is bad, not the plan".

This module compares the rule against a multi-period optimum on the same exogenous path:

  greedy  : B1 `advance()`, unchanged
  optimal : LP over the whole horizon, choosing q_h and r_h jointly

If the two agree, the greedy rule is not costing anything and the claim stands on the
policy too. If they disagree, the gap is itself the result: the causal rule forfeits
deliverability that a planner could have achieved.

What the optimum is over
------------------------
Decision variables per hour: deferral `q_h`, recovery `r_h`, and the induced debt.
Constraints: power/capacity (`q_h - r_h` must cover the hour's shortfall), CFE target,
deferral cap, debt cap, call-energy cap, and every task's deadline. Objective: minimise
total missed work at deadlines. This is an LP, so the event-envelope integer rules
(max_events, max_duration) are NOT modelled; that limitation is reported.

Scope
-----
One POI, one window, declared workload. Not an AC study, not a market model.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction as Q
import hashlib
import json
from pathlib import Path
import sys

import pyomo.environ as pyo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.staged_deliverability_development_v1 import (  # noqa: E402
    ZERO, HourInput, Parameters, advance, initialize, power_mapping,
)

CAPACITY_RESULTS = (ROOT / "results/tables"
                    / "staged_deliverability_grid_capacity_hourly_v1_non_authoritative"
                    / "attempt_03/report.json")
ROOT_OUT = ROOT / "results/tables/staged_deliverability_greedy_vs_optimal_v1_non_authoritative"

POI = 15
DEADLINE_LAG = 3
IT_LOAD_FRACTION = Q(9, 10)     # declared: DC draws near the POI's own capacity
FLEXIBLE_FRACTION = Q(2, 5)
ALPHA = Q(4, 5)
PUE = Q(5, 4)
IDLE_FRACTION = Q(1, 25)
AUX_FRACTION = Q(1, 40)


def load_capacity(poi=POI):
    """N-1 capacity per hour from the stage 1 table; None where non-evaluable."""
    data = json.loads(CAPACITY_RESULTS.read_text(encoding="utf-8"))
    out = {}
    for row in data["rows"]:
        if row["poi"] == poi:
            out[row["hour"]] = row["n1_min_mw"]
    return out


def build_case(poi=POI):
    """Declared case: one DC at `poi`, capacity-driven supply, tasks every hour."""
    cap = load_capacity(poi)
    hours = sorted(h for h, v in cap.items() if v is not None)
    # Convert to exact rationals at the boundary: the capacity table is JSON floats, but
    # every quantity the model consumes must be a Fraction or Parameters rejects it.
    peak = Q(str(max(round(cap[h], 6) for h in hours)))
    it = peak * IT_LOAD_FRACTION
    params = Parameters(
        capacity=it * Q(1, 5),
        alpha=ALPHA, eta=Q(1), beta=Q(1),
        facility_factor=PUE,
        auxiliary_mw=peak * AUX_FRACTION,
        fixed_headroom=peak * Q(1, 5),
        max_recovery=peak * Q(1, 5),
        max_debt=peak * Q(2, 5),
        max_call_energy=peak * Q(2, 5),
        call_ramp=peak,
        max_events=10**6, max_duration=10**6, minimum_rest=0,
    )
    observations = []
    for h in hours:
        observations.append(HourInput(
            hour=h, due=h + DEADLINE_LAG,
            workload=it,
            flexible_fraction=FLEXIBLE_FRACTION,
            compute_capacity=peak,
            idle_mw=peak * IDLE_FRACTION,
            clean_mwh=Q(str(round(cap[h], 6))) * ALPHA * PUE,
            supply_mw=Q(str(round(cap[h], 6))),
            equipment_online=("dc",), grid_online=True,
        ))
    return params, observations, hours, cap


def shortfall_of(params, o):
    """Load that the hour's power and CFE limits force off the site, before deferral.

    Power: metered load must not exceed the POI's deliverable capacity.
    CFE:   attributed clean must not fall below alpha * metered load.
    Both reduce to a minimum amount of deferred work; the binding one wins.
    """
    pue = float(params.facility_factor)
    beta = float(params.beta)
    aux = float(params.auxiliary_mw)
    idle = float(o.idle_mw)
    alpha = float(params.alpha)
    supply = float(o.supply_mw)
    clean = float(o.clean_mwh)
    workload = float(o.workload)

    # power-limited: pue*(idle + beta*activity) + aux <= supply
    act_power = (supply - aux) / pue / beta - idle / beta if pue and beta else workload
    # clean-limited: alpha * (pue*(idle + beta*activity) + aux) <= clean
    act_clean = (clean / alpha - aux) / pue / beta - idle / beta if alpha else workload
    allowed = min(act_power, act_clean)
    return max(workload - allowed, 0.0)


def greedy_run(params, observations):
    """B1's own rule, plus the unmet service it leaves in each hour."""
    state = initialize(params, "full_temporal", "greedy", observations[0].hour)
    unmet = 0.0
    hours_run = 0
    for o in observations:
        if state.stopped:
            break
        need = shortfall_of(params, o)
        state = advance(params, state, o)
        q = float(state.records[-1].deferred)
        unmet += max(need - q, 0.0)
        hours_run += 1
    missed = sum(float(c.missed_at_deadline or ZERO) for c in state.ledger.cohorts)
    return dict(unmet_mwh=round(unmet, 2), missed_mwh=round(missed, 2),
                total=round(unmet + missed, 2),
                stopped=state.stopped, hours_run=hours_run)


def optimal_run(params, observations):
    """Multi-period LP: minimise unmet service plus missed work at deadlines.

    A pure feasibility LP is infeasible whenever a single hour cannot be served even
    with maximum deferral, which is exactly the case this comparison is about. The
    shortfall is therefore carried by an explicit `shed` variable and priced into the
    objective, so the optimum always exists and the amount that cannot be served is a
    reported quantity rather than a solver failure.
    """
    hours = [o.hour for o in observations]
    idx = {h: i for i, h in enumerate(hours)}
    capd = float(params.capacity)
    max_rec = float(params.max_recovery)
    max_debt = float(params.max_debt)
    max_energy = float(params.max_call_energy)
    flex = float(observations[0].flexible_fraction)
    workload = {o.hour: float(o.workload) for o in observations}
    need = {o.hour: shortfall_of(params, o) for o in observations}

    m = pyo.ConcreteModel()
    m.H = pyo.Set(initialize=hours)
    m.q = pyo.Var(m.H, within=pyo.NonNegativeReals)
    m.r = pyo.Var(m.H, within=pyo.NonNegativeReals)
    m.debt = pyo.Var(m.H, within=pyo.NonNegativeReals)
    m.energy = pyo.Var(m.H, within=pyo.NonNegativeReals)
    m.miss = pyo.Var(m.H, within=pyo.NonNegativeReals)
    m.shed = pyo.Var(m.H, within=pyo.NonNegativeReals)

    # Serve the hour's forced-off load, or declare it unserved.
    m.serve = pyo.Constraint(m.H, rule=lambda m, h: (
        m.q[h] - m.r[h] + m.shed[h] >= need[h]))
    m.capq = pyo.Constraint(m.H, rule=lambda m, h: (
        m.q[h] <= min(capd, workload[h] * flex, workload[h])))
    m.capr = pyo.Constraint(m.H, rule=lambda m, h: m.r[h] <= max_rec)

    def debt_rule(m, h):
        prior = 0.0 if h == hours[0] else m.debt[m.H.prev(h)]
        return m.debt[h] >= prior + m.q[h] - m.r[h]
    m.debtt = pyo.Constraint(m.H, rule=debt_rule)
    m.debtcap = pyo.Constraint(m.H, rule=lambda m, h: m.debt[h] <= max_debt)

    def energy_rule(m, h):
        prior = 0.0 if h == hours[0] else m.energy[m.H.prev(h)]
        return m.energy[h] >= prior + m.q[h]
    m.energyt = pyo.Constraint(m.H, rule=energy_rule)
    m.energycap = pyo.Constraint(m.H, rule=lambda m, h: m.energy[h] <= max_energy)

    # Work deferred at hour a must be recovered inside [a, a + lag].
    def deadline_rule(m, h):
        due = idx.get(h + DEADLINE_LAG)
        if due is None:
            return pyo.Constraint.Skip
        recovered = sum(m.r[hours[j]] for j in range(idx[h], due + 1))
        return m.miss[h] >= m.q[h] - recovered
    m.deadline = pyo.Constraint(m.H, rule=deadline_rule)

    m.obj = pyo.Objective(
        expr=sum(m.miss[h] for h in m.H) + sum(m.shed[h] for h in m.H),
        sense=pyo.minimize)

    solver = pyo.SolverFactory("highs")
    res = solver.solve(m)
    status = str(res.solver.termination_condition)
    if status != "optimal":
        return dict(error=status)
    shed = sum(pyo.value(m.shed[h]) for h in hours)
    missed = sum(pyo.value(m.miss[h]) for h in hours)
    return dict(unmet_mwh=round(shed, 2), missed_mwh=round(missed, 2),
                total=round(shed + missed, 2), hours_run=len(hours), status=status)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt_01")
    args = parser.parse_args(argv)

    target = ROOT_OUT / args.attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)

    params, observations, hours, cap = build_case()
    g = greedy_run(params, observations)
    o = optimal_run(params, observations)

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_greedy_vs_optimal_v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "formal_result": False, "resource_admission": False,
        "security_certified": False, "ac_certified": False,
        "poi": POI, "window_hours": len(hours),
        "deadline_lag": DEADLINE_LAG,
        "it_load_mw": round(float(observations[0].workload), 1),
        "note": ("greedy = frozen B1 advance(); optimal = multi-period LP minimising "
                 "missed work. Event-envelope integers are not modelled in the LP."),
        "greedy": g, "optimal": o,
        "gap_missed_mw_h": round(g["missed"] - o["missed"], 4),
    }
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("poi", "window_hours", "greedy", "optimal",
                                             "gap_missed_mw_h")}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
