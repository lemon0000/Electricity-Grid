"""Measure N-1 secure deliverable capacity at candidate POI buses on RTS-24.

DRAFT_NONAUTHORITATIVE. This is a bounded development probe, not a formal result and not
an AC certification.

Why this exists
---------------
Every D/E cell to date takes `supply_mw` as a declared constant. That makes the whole
comparison rest on a number nobody computed. Here the number is computed instead: for a
given host bus and system load level, how much extra power can actually be delivered
there while every branch stays inside rating, in the base case and with each branch
outaged in turn?

What this measures and what it does not
---------------------------------------
Measured: a DC OPF maximum-injection LP per (POI, load level, contingency). The POI is
modelled as one extra load variable at its bus; maximising it gives the transfer
capability.
Not measured: AC feasibility (`ac_certified=false`), voltage/reactive limits, dynamic
stability, or any market/dispatch policy. `security_certified=false` throughout.

Note: N-1 here means "each branch outaged once, generation re-dispatched". It is not a
joint multi-contingency study.
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import sys

import numpy as np
import pyomo.environ as pyo
import pypower.api as pp
import pyomo.contrib.solver.common.util as _pyo_util

ROOT = Path(__file__).resolve().parents[1]
ROOT_OUT = ROOT / "results/tables/staged_deliverability_grid_capacity_v1_non_authoritative"

POIS = (3, 7, 15, 19, 23)
# RTS-24 total pmin is 1036 MW = 0.3635 of the 2850 MW base load. Any load scale below
# that leaves the unit commitment infeasible regardless of the POI, and the maximum-
# injection LP would then report "how much load must be added to become feasible"
# rather than a transfer capability. The grid starts above that floor.
LOAD_SCALES = (0.40, 0.55, 0.70, 0.85, 1.00)


def _case():
    case = pp.case24_ieee_rts()
    return case, float(case["baseMVA"])


def max_injection(poi, load_scale, outaged=None, cap_mw=3000.0):
    """Largest extra load at `poi` with branch `outaged` removed, base load scaled."""
    case, base = _case()
    bus, gen, branch = case["bus"], case["gen"], case["branch"]
    nb, ng, nl = bus.shape[0], gen.shape[0], branch.shape[0]
    f = branch[:, 0].astype(int) - 1
    t = branch[:, 1].astype(int) - 1
    x = branch[:, 3] / base
    rate = branch[:, 5] / base
    pd = bus[:, 2] / base * load_scale
    genbus = gen[:, 0].astype(int) - 1
    pmax = gen[:, 8] / base
    pmin = gen[:, 9] / base
    ref = [i for i in range(nb) if bus[i, 1] == 3][0]

    model = pyo.ConcreteModel()
    model.G = pyo.Set(initialize=range(ng))
    model.B = pyo.Set(initialize=range(nb))
    live = [l for l in range(nl) if l != outaged]
    model.L = pyo.Set(initialize=live)
    model.pg = pyo.Var(model.G, bounds=lambda m, g: (pmin[g], pmax[g]))
    model.theta = pyo.Var(model.B, bounds=(-20, 20))
    model.flow = pyo.Var(model.L)
    model.delta = pyo.Var(bounds=(0.0, cap_mw / base))
    model.obj = pyo.Objective(expr=model.delta, sense=pyo.maximize)
    model.balance = pyo.Constraint(model.B, rule=lambda m, b: (
        sum(m.pg[g] for g in m.G if genbus[g] == b)
        - sum(m.flow[l] for l in m.L if f[l] == b)
        + sum(m.flow[l] for l in m.L if t[l] == b)
        - pd[b]
        - (m.delta if b == poi else 0.0)) == 0)
    model.dc = pyo.Constraint(model.L, rule=lambda m, l: (
        m.flow[l] * x[l] - (m.theta[f[l]] - m.theta[t[l]]) == 0))
    model.lim = pyo.Constraint(model.L, rule=lambda m, l: (-rate[l], m.flow[l], rate[l]))
    model.ref = pyo.Constraint(expr=model.theta[ref] == 0)

    try:
        pyo.SolverFactory("highs").solve(model)
        return pyo.value(model.delta) * base
    except _pyo_util.NoFeasibleSolutionError:
        return None


def probe(pois=POIS, scales=LOAD_SCALES):
    case, _ = _case()
    nl = case["branch"].shape[0]
    demand = float(case["bus"][:, 2].sum())
    rows = []
    for poi in pois:
        for scale in scales:
            base_mw = max_injection(poi, scale)
            n1 = [max_injection(poi, scale, outaged=l) for l in range(nl)]
            valid = [c for c in n1 if c is not None]
            binding = (int(min(range(nl),
                               key=lambda l: (n1[l] if n1[l] is not None else 1e9)))
                       if valid else None)
            rows.append(dict(
                poi=poi, load_scale=scale,
                demand_mw=round(demand * scale, 1),
                base_mw=None if base_mw is None else round(base_mw, 1),
                n1_min_mw=None if not valid else round(min(valid), 1),
                n1_loss_mw=None if (base_mw is None or not valid)
                else round(base_mw - min(valid), 1),
                binding_branch=binding,
                contingencies_ok=len(valid),
                contingencies_total=nl,
            ))
    return rows


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt_01")
    args = parser.parse_args(argv)

    target = ROOT_OUT / args.attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)

    started = datetime.now(timezone.utc)
    t0 = time.perf_counter()
    rows = probe()
    elapsed = time.perf_counter() - t0

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_grid_capacity_v1",
        "created_utc": started.isoformat(),
        "formal_result": False, "resource_admission": False,
        "security_certified": False, "ac_certified": False, "aggregate_contract_release": False,
        "solver": "highs",
        "solver_calls": len(rows) * (len(_case()[0]["branch"]) + 1),
        "model_note": ("DC OPF with a single slack bus; the POI is one extra load variable "
                       "whose maximum is optimised. N-1 = each branch outaged once with "
                       "generation re-dispatched. MW measured at the POI bus."),
        "feasibility_floor": ("RTS-24 total pmin 1036 MW equals 0.3635 of the 2850 MW base "
                              "load; below that the commitment is infeasible regardless of "
                              "POI, so the probe starts at 0.40."),
        "total_seconds": round(elapsed, 2),
        "pois": list(POIS),
        "load_scales": list(LOAD_SCALES),
        "rows": rows,
    }
    (target / "report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    import hashlib
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")

    print(json.dumps({"rows": len(rows), "solver_calls": report["solver_calls"],
                      "seconds": report["total_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
