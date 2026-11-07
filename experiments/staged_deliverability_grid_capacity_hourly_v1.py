"""Stage 1: hourly N-1 deliverable capacity at candidate POIs over real RTS-GMLC load.

DRAFT_NONAUTHORITATIVE. Zero external downloads; reads the pinned joint data only.

Why this exists
---------------
Stage 0 measured capacity at five synthetic load levels. That is enough to price the
compute, not enough to use: the D/E evaluation chain needs a capacity *per hour*, driven
by the observed load chronology rather than by a declared constant.

Declared mapping (fixed before any hour is evaluated)
-----------------------------------------------------
The RTS-GMLC case has its own reference load (2850 MW over 24 buses); the observed
chronology has a different scale. The bridge is a shape-preserving rescale:

    case_load_h = case_reference_load * (observed_load_h / observed_load_mean)

so the *hour-to-hour shape* is measured and the *level* stays at the case's own
reference. No fitting, no per-hour adjustment after seeing a result.

Feasibility floor
-----------------
RTS-24's total minimum output is 1036 MW. Any hour whose rescaled load falls below that
is marked `evaluable=false` and reported, never silently dropped: the same distortion
that corrupted stage 0's 0.35 row would otherwise reappear as a fake capacity.

Output
------
One row per (hour, POI): base-case capacity, N-1 minimum, the binding branch, and the
hour's load level. Downstream, `supply_mw` becomes this table instead of a constant.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import time
from datetime import datetime, timezone
from fractions import Fraction as Q
from pathlib import Path
import sys

import pyomo.environ as pyo
import pypower.api as pp
import pyomo.contrib.solver.common.util as _pyo_util

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

JOINT = ROOT / "data/processed/model_inputs/rq2_joint_data_v1"
ROOT_OUT = ROOT / "results/tables/staged_deliverability_grid_capacity_hourly_v1_non_authoritative"

POIS = (3, 7, 15, 19, 23)
WINDOW_START = 0
WINDOW_HOURS = 168            # one week: covers a stage switch in the D/E framing
PMIN_FLOOR_MW = 1036.0        # RTS-24 total minimum output
PEAK_LIMIT_MW = 3405.0        # RTS-24 total maximum output


def observed_load(start: int, hours: int):
    """Total system load per hour from the pinned chronology."""
    by_hour: dict[int, float] = {}
    with gzip.open(JOINT / "hourly_bus_load.csv.gz", "rt", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        next(reader)
        for row in reader:
            hour = int(row[0])
            if start <= hour < start + hours:
                by_hour[hour] = by_hour.get(hour, 0.0) + float(row[4])
    missing = [h for h in range(start, start + hours) if h not in by_hour]
    if missing:
        raise ValueError(f"load series missing hours {missing[:5]}")
    return [by_hour[h] for h in range(start, start + hours)]


def _case():
    case = pp.case24_ieee_rts()
    return case, float(case["baseMVA"])


def max_injection(poi, load_scale, outaged=None, cap_mw=3000.0):
    """Largest extra load at `poi` with `outaged` removed, case load scaled."""
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


def scan(start=WINDOW_START, hours=WINDOW_HOURS, pois=POIS):
    case, _ = _case()
    nl = case["branch"].shape[0]
    case_reference = float(case["bus"][:, 2].sum())
    total_pmax = float(case["gen"][:, 8].sum())
    observed = observed_load(start, hours)
    mean = sum(observed) / len(observed)

    rows, hour_meta = [], []
    for offset, load in enumerate(observed):
        scale = load / mean                     # shape only; mean maps to case reference
        case_load = case_reference * scale
        evaluable = PMIN_FLOOR_MW <= case_load <= PEAK_LIMIT_MW
        hour_rows = []
        if not evaluable:
            for poi in pois:
                hour_rows.append(dict(hour=start + offset, poi=poi, evaluable=False,
                                      base_mw=None, n1_min_mw=None,
                                      binding_branch=None, contingencies_ok=0,
                                      limited_by=None))
        else:
            for poi in pois:
                base_mw = max_injection(poi, scale)
                n1 = [max_injection(poi, scale, outaged=l) for l in range(nl)]
                valid = [c for c in n1 if c is not None]
                binding = (int(min(range(nl),
                                   key=lambda l: (n1[l] if n1[l] is not None else 1e9)))
                           if valid else None)
                hour_rows.append(dict(
                    hour=start + offset, poi=poi, evaluable=True,
                    base_mw=None if base_mw is None else round(base_mw, 1),
                    n1_min_mw=None if not valid else round(min(valid), 1),
                    binding_branch=binding,
                    contingencies_ok=len(valid),
                    limited_by=None,
                ))

        # Generation vs network, decided PER ROW, not per hour.
        #
        # A row is generation-limited when its base-case capacity equals the fleet
        # headroom `total_pmax - load`: in that regime the binding resource is how much
        # the generators can still produce, and the POI's position in the network does
        # not matter. Such rows cannot support a claim about siting.
        #
        # The per-hour version of this test was wrong. At a high-load hour the several
        # POIs can return *different* capacities (H19: 208.4 vs 217.3) while every one
        # of them sits at the fleet headroom, because the outage case binds first at
        # different buses. A per-hour "all POIs identical" test therefore missed 66 of
        # the 81 affected hours.
        if evaluable:
            headroom = total_pmax - case_load
            for row in hour_rows:
                if row["base_mw"] is None:
                    row["limited_by"] = None
                elif abs(row["base_mw"] - headroom) < 0.5:
                    row["limited_by"] = "generation"
                else:
                    row["limited_by"] = "network"

        classes = {r["limited_by"] for r in hour_rows if r["limited_by"] is not None}
        hour_meta.append(dict(
            hour=start + offset,
            observed_load_mw=round(load, 1),
            scale=round(scale, 4),
            case_load_mw=round(case_load, 1),
            evaluable=evaluable,
            hour_class=("mixed" if len(classes) > 1
                        else (classes.pop() if classes else None)),
            reason=None if evaluable else (
                "below pmin floor" if case_load < PMIN_FLOOR_MW else "above pmax"),
        ))
        rows.extend(hour_rows)
    return rows, hour_meta


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
    rows, hour_meta = scan()
    elapsed = time.perf_counter() - t0

    case, _ = _case()
    nl = case["branch"].shape[0]
    evaluable = [h for h in hour_meta if h["evaluable"]]
    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_grid_capacity_hourly_v1",
        "created_utc": started.isoformat(),
        "formal_result": False, "resource_admission": False,
        "security_certified": False, "ac_certified": False, "aggregate_contract_release": False,
        "solver": "highs",
        "solver_calls": len(evaluable) * len(POIS) * (nl + 1),
        "model_note": ("DC OPF, single slack, POI as one extra load variable; N-1 = each "
                       "branch outaged once. MW at the POI bus."),
        "mapping": ("case_load_h = case_reference * (observed_load_h / observed_mean); "
                    "shape measured, level held at the case reference"),
        "feasibility_rule": (f"an hour is evaluable iff {PMIN_FLOOR_MW} <= case_load <= "
                             f"{PEAK_LIMIT_MW}; other hours are reported with "
                             f"evaluable=false, never dropped"),
        "window": {"start": WINDOW_START, "hours": WINDOW_HOURS},
        "pois": list(POIS),
        "hours_evaluable": len(evaluable),
        "hours_total": len(hour_meta),
        "total_seconds": round(elapsed, 2),
        "hours": hour_meta,
        "rows": rows,
    }
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")

    print(json.dumps({"hours": len(hour_meta), "evaluable": len(evaluable),
                      "rows": len(rows), "solver_calls": report["solver_calls"],
                      "seconds": report["total_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
