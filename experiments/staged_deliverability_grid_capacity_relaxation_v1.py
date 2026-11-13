"""Equivalence probe: does continuous-commitment relaxation change measured capacity?

DRAFT_NONAUTHORITATIVE. Bounded development diagnostic, not a result.

Why this exists
---------------
Stages 0/1 bound every generator at `pmin <= p <= pmax` and maximise injection at
the POI. Under the corrected (identity) load mapping, 16.1% of the year sits below
the fleet's total minimum output (1036 MW), where that formulation has no feasible
point at all: the LP can only "serve" such an hour by *raising* the load, which is
the measurement error recorded in stage 0.

The proposed successor relaxes commitment to a continuous `u in [0,1]`:

    pmin_g * u_g <= p_g <= pmax_g * u_g

That is a strict superset of the current feasible set, so relaxed capacity can only
be >= current capacity. The claim that has to hold before adopting it is stronger
and must be tested, not argued:

    at every hour the current formulation can evaluate, the relaxation returns
    the SAME capacity, so existing numbers are not invalidated and the relaxation
    only adds hours that were previously unmeasurable.

If that fails anywhere, the relaxation changes the measurement and cannot be
adopted as a coverage extension alone.

Design
------
Hours are picked by rule, not by interest: the coldest (lowest load), the median,
and the warmest (highest load) hour of the stage-1 window [0,168) under the
identity mapping. Both formulations are solved on each, for all five POIs and the
full N-1 set, and compared per row.

Budget: 3 hours x 5 POIs x 39 solves x 2 formulations = 1170 LPs at ~25 ms.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyomo.environ as pyo
import pypower.api as pp

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JOINT = ROOT / "data/processed/model_inputs/rq2_joint_data_v1"
OUT_ROOT = (
    ROOT / "results/tables/staged_deliverability_grid_capacity_relaxation_v1"
    / "non_authoritative"
)

POIS = (3, 7, 15, 19, 23)
WINDOW_START = 0
WINDOW_HOURS = 168
PMIN_FLOOR_MW = 1036.0
PEAK_LIMIT_MW = 3405.0


def observed_load(start: int, hours: int) -> list[float]:
    import csv
    import gzip

    by_hour: dict[int, float] = {}
    with gzip.open(JOINT / "hourly_bus_load.csv.gz", "rt", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            hour = int(row[0])
            if start <= hour < start + hours:
                by_hour[hour] = by_hour.get(hour, 0.0) + float(row[4])
    return [by_hour[h] for h in range(start, start + hours)]


def max_injection(poi, load_mw, outaged=None, cap_mw=3000.0, relaxed=False):
    """Largest extra load at `poi`. `load_mw` is the total case load."""

    case = pp.case24_ieee_rts()
    base = float(case["baseMVA"])
    bus, gen, branch = case["bus"], case["gen"], case["branch"]
    nb, ng, nl = bus.shape[0], gen.shape[0], branch.shape[0]
    f = branch[:, 0].astype(int) - 1
    t = branch[:, 1].astype(int) - 1
    x = branch[:, 3] / base
    rate = branch[:, 5] / base
    scale = load_mw / float(bus[:, 2].sum())
    pd = bus[:, 2] / base * scale
    genbus = gen[:, 0].astype(int) - 1
    pmax = gen[:, 8] / base
    pmin = gen[:, 9] / base
    ref = [i for i in range(nb) if bus[i, 1] == 3][0]
    active = [g for g in range(ng) if pmax[g] > 1e-9]

    model = pyo.ConcreteModel()
    model.G = pyo.Set(initialize=active)
    model.B = pyo.Set(initialize=range(nb))
    live = [l for l in range(nl) if l != outaged]
    model.L = pyo.Set(initialize=live)
    model.theta = pyo.Var(model.B, bounds=(-20, 20))
    model.flow = pyo.Var(model.L)
    model.delta = pyo.Var(bounds=(0.0, cap_mw / base))

    if relaxed:
        model.u = pyo.Var(model.G, bounds=(0.0, 1.0))
        model.pg = pyo.Var(model.G, bounds=lambda m, g: (0.0, pmax[g]))
        model.lo = pyo.Constraint(
            model.G, rule=lambda m, g: m.pg[g] >= pmin[g] * m.u[g]
        )
        model.hi = pyo.Constraint(
            model.G, rule=lambda m, g: m.pg[g] <= pmax[g] * m.u[g]
        )
    else:
        model.pg = pyo.Var(model.G, bounds=lambda m, g: (pmin[g], pmax[g]))

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

    import pyomo.contrib.solver.common.util as util

    try:
        pyo.SolverFactory("highs").solve(model)
        return pyo.value(model.delta) * base
    except util.NoFeasibleSolutionError:
        return None


def pick_hours(observed: list[float]) -> list[dict]:
    """Coldest, median and warmest hour of the window, picked by rule."""

    order = sorted(range(len(observed)), key=lambda index: observed[index])
    picks = [
        ("coldest", order[0]),
        ("median", order[len(order) // 2]),
        ("warmest", order[-1]),
    ]
    return [dict(label=label, offset=offset, load_mw=observed[offset])
            for label, offset in picks]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt_01")
    args = parser.parse_args(argv)

    target = OUT_ROOT / args.attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")

    observed = observed_load(WINDOW_START, WINDOW_HOURS)
    picks = pick_hours(observed)
    nl = pp.case24_ieee_rts()["branch"].shape[0]

    target.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    clock = time.perf_counter()

    rows = []
    for pick in picks:
        load = pick["load_mw"]
        evaluable = PMIN_FLOOR_MW <= load <= PEAK_LIMIT_MW
        for poi in POIS:
            current_base = max_injection(poi, load, relaxed=False)
            relaxed_base = max_injection(poi, load, relaxed=True)
            current_n1, relaxed_n1, agree_n1, valid_n1 = [], [], 0, 0
            for line in range(nl):
                cur = max_injection(poi, load, outaged=line, relaxed=False)
                rel = max_injection(poi, load, outaged=line, relaxed=True)
                current_n1.append(cur)
                relaxed_n1.append(rel)
                if cur is not None:
                    valid_n1 += 1
                    if rel is not None and abs(rel - cur) < 1e-6:
                        agree_n1 += 1
            cur_valid = [v for v in current_n1 if v is not None]
            rel_valid = [v for v in relaxed_n1 if v is not None]
            row = dict(
                label=pick["label"], hour=WINDOW_START + pick["offset"],
                case_load_mw=round(load, 1),
                current_formulation_evaluable=evaluable,
                poi=poi,
                current_base_mw=None if current_base is None else round(current_base, 3),
                relaxed_base_mw=None if relaxed_base is None else round(relaxed_base, 3),
                base_agrees=(current_base is not None and relaxed_base is not None
                             and abs(current_base - relaxed_base) < 1e-6),
                current_n1_min_mw=round(min(cur_valid), 3) if cur_valid else None,
                relaxed_n1_min_mw=round(min(rel_valid), 3) if rel_valid else None,
                current_contingencies_ok=valid_n1,
                relaxed_contingencies_ok=len(rel_valid),
                contingencies_agree=agree_n1,
            )
            rows.append(row)
            print(json.dumps({k: row[k] for k in (
                "label", "poi", "case_load_mw", "current_base_mw",
                "relaxed_base_mw", "base_agrees", "current_n1_min_mw",
                "relaxed_n1_min_mw", "relaxed_contingencies_ok")},
                separators=(",", ":")))

    total = time.perf_counter() - clock
    # The equivalence claim, evaluated over every row the current formulation can
    # actually measure (base case and per-contingency).
    comparable = [r for r in rows if r["current_base_mw"] is not None]
    base_mismatch = [r for r in comparable if not r["base_agrees"]]
    n1_mismatch = [r for r in rows
                   if r["current_contingencies_ok"] > 0
                   and r["contingencies_agree"] != r["current_contingencies_ok"]]
    gained = [r for r in rows if r["current_base_mw"] is None
              and r["relaxed_base_mw"] is not None]

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_grid_capacity_relaxation_v1",
        "created_utc": started.isoformat(),
        "formal_result": False,
        "purpose": "test whether continuous-commitment relaxation changes capacity at "
                   "hours the current formulation can already measure",
        "claim": "relaxation returns identical capacity wherever the current "
                 "formulation is feasible, and adds only previously infeasible hours",
        "mapping": "identity: case_load_h = observed_h (see the v2 spec); the "
                   "detected data identity is observed(h,b) = s_h * case24_PD(b) "
                   "with max(s_h) = 1.0",
        "environment": {"python": sys.version.split()[0], "solver": "highs"},
        "window": {"start": WINDOW_START, "hours": WINDOW_HOURS},
        "hour_selection": "coldest, median, warmest of the window by total load; "
                          "fixed by rule, not chosen against any capacity value",
        "pois": list(POIS),
        "rows": rows,
        "summary": {
            "rows_total": len(rows),
            "rows_current_feasible": len(comparable),
            "base_case_mismatches": len(base_mismatch),
            "n1_mismatch_rows": len(n1_mismatch),
            "rows_gained_by_relaxation": len(gained),
            "equivalence_holds": not base_mismatch and not n1_mismatch,
        },
        "total_seconds": round(total, 2),
    }
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")
    print(json.dumps(report["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
