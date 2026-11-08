"""B2 feasibility probe: does cross-hour task shifting create real scheduling slack?

DRAFT_NONAUTHORITATIVE. One greedy pass, one MILP, on a real capacity profile.

The question this answers (and nothing more)
--------------------------------------------
The scalar model deferred work but never moved it to a chosen hour: a task's shortfall
was set by its own hour's capacity. Under that model greedy and optimal give the same
deliverability verdict, because whether a deadline is missed is a physical property of
the recovery window, not a policy choice (verified 39/39 last session).

B2 proposes a different model: a task has an arrival, a deadline, and an energy, and the
scheduler chooses WHICH hours inside [arrival, deadline] execute it, subject to each
hour's N-1 capacity. If that freedom lets an optimal schedule meet a deadline the greedy
rule misses, B2 has value. If not, the "physical, not policy" result stands and B2 is
not worth building.

Setup
-----
- Hourly capacity: real RTS-24 N-1 at POI 15 (stage 1), which swings 6-728 MW.
- A base load occupies most capacity; tasks compete for the residual.
- Greedy: earliest-deadline-first, run each task as early as capacity allows.
- Optimal: MILP placing each task's energy across its window to minimise missed energy.
- Compare missed energy. A single case where greedy misses and optimal does not is a
  positive result.

Scope: a probe, not a result. No AC, no commitment integers beyond task placement.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

import pyomo.environ as pyo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

CAP = (ROOT / "results/tables"
       / "staged_deliverability_grid_capacity_hourly_v1_non_authoritative"
       / "attempt_03/report.json")


def capacity_profile(poi=15, hours=24):
    data = json.loads(CAP.read_text(encoding="utf-8"))
    cap = {r["hour"]: r["n1_min_mw"] for r in data["rows"]
           if r["poi"] == poi and r["n1_min_mw"] is not None}
    chosen = sorted(cap)[:hours]
    return list(range(len(chosen))), [cap[h] for h in chosen]


def residual_capacity(cap, base_load):
    """Capacity left for shiftable tasks after a flat base load."""
    return [max(c - base_load, 0.0) for c in cap]


def greedy_schedule(residual, tasks):
    """Earliest-deadline-first; each task runs as early as residual capacity allows."""
    remaining = list(residual)
    missed = 0.0
    for arrival, deadline, energy in sorted(tasks, key=lambda t: t[1]):
        need = energy
        for h in range(arrival, deadline + 1):
            if need <= 0:
                break
            take = min(need, remaining[h])
            remaining[h] -= take
            need -= take
        missed += max(need, 0.0)
    return missed


def optimal_schedule(residual, tasks):
    """MILP: place each task's energy across its window to minimise missed energy."""
    m = pyo.ConcreteModel()
    T = range(len(tasks))
    H = range(len(residual))
    m.x = pyo.Var(((i, h) for i in T for h in H
                   if tasks[i][0] <= h <= tasks[i][1]), within=pyo.NonNegativeReals)
    m.miss = pyo.Var(T, within=pyo.NonNegativeReals)

    def served(i):
        return sum(m.x[i, h] for h in range(tasks[i][0], tasks[i][1] + 1))
    m.meet = pyo.Constraint(T, rule=lambda m, i: served(i) + m.miss[i] >= tasks[i][2])
    def cap_rule(m, h):
        terms = [m.x[i, h] for i in T if tasks[i][0] <= h <= tasks[i][1]]
        if not terms:
            return pyo.Constraint.Skip
        return sum(terms) <= residual[h]
    m.cap = pyo.Constraint(H, rule=cap_rule)
    m.obj = pyo.Objective(expr=sum(m.miss[i] for i in T), sense=pyo.minimize)
    pyo.SolverFactory("highs").solve(m)
    return pyo.value(m.obj)


def main():
    hours, cap = capacity_profile()
    results = []
    # Scan base-load levels: the tighter the residual, the more scheduling matters.
    for base in (200.0, 300.0, 400.0, 500.0):
        residual = residual_capacity(cap, base)
        # Tasks whose windows straddle the capacity valley (h4-h8) and the peaks around it.
        tasks = [
            (0, 8, 300.0),    # can run in early peak or wait through the valley
            (2, 10, 250.0),
            (4, 12, 280.0),   # arrives in the valley, deadline past it
            (5, 9, 180.0),    # entirely inside the valley unless shifted
            (6, 14, 220.0),
        ]
        g = greedy_schedule(residual, tasks)
        o = optimal_schedule(residual, tasks)
        results.append(dict(base_load=base,
                            residual_min=round(min(residual), 1),
                            residual_max=round(max(residual), 1),
                            greedy_missed=round(g, 2),
                            optimal_missed=round(o, 2),
                            gap=round(g - o, 2)))
    print(json.dumps({"poi": 15, "profile_min": round(min(cap), 1),
                      "profile_max": round(max(cap), 1), "results": results}, indent=1))
    positive = [r for r in results if r["gap"] > 1e-6]
    print()
    print("VERDICT:", "cross-hour shifting creates slack (B2 has value)" if positive
          else "no gap: optimal == greedy, shifting adds nothing")


if __name__ == "__main__":
    main()
