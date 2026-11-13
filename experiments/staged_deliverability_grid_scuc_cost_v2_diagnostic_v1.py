"""Diagnostic: why does adding constraints make the 24 h SCUC solve faster?

DRAFT_NONAUTHORITATIVE. Bounded diagnostic, not a result. It exists because
`staged_deliverability_grid_scuc_cost_v2` produced an ordering that cannot be
reported without an explanation:

    B0  24 h, 1 state, no ramp, no min up/down   -> 290.5 s, optimal
    B2  24 h, 1 state, ramp + 4 h min up/down    ->   0.5 s, optimal

"More constraints, 550x faster" is not a property of the paper's model; it is
a property of this MIP as formulated. Three explanations are separable, and
each is tested here on the identical window, load series, cost and budget:

1. Ramp alone prunes the feasible commitment/dispatch space.
2. Minimum up/down alone prunes the commitment space.
3. Neither; the original formulation is simply highly symmetric (case24 holds
   six identical 50 MW units at bus 22, five identical 12 MW units at bus 15,
   three identical 197 MW units at bus 13), and Gurobi's default symmetry
   handling is leaving that on the table. E3 forces aggressive symmetry
   detection on the unchanged B0 model.

E1 and E2 change the model; E3 changes only the solver's symmetry setting. If
E3 recovers most of the speed-up, the inversion is a solver-symmetry artifact
and the B0/B2 comparison in v2 must be read as "the timings are not monotone in
constraint count", not as "the stiff model is cheaper to solve". If E1 or E2
alone accounts for it, the pruning explanation stands and E3 adds nothing.

Budget: 3 arms x 120 s cap, 360 s total. Same stop rule as v2.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyomo.environ as pyo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pypower.api as pp  # noqa: E402

from src.grid.rts24 import load_rts24  # noqa: E402


def _load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_v2 = _load("_scuc_cost_v2", "experiments/staged_deliverability_grid_scuc_cost_v2.py")
_v1 = _v2._v1

OUT_ROOT = (
    ROOT
    / "results/tables/staged_deliverability_grid_scuc_cost_v2_diagnostic_v1"
    / "non_authoritative"
)

PER_SOLVE_SECONDS = 120.0
TOTAL_BUDGET_SECONDS = 360.0

ARMS = (
    dict(arm="E1", ramp=True, min_up=False, symmetry=None,
         question="ramp alone (4 h min up/down off)"),
    dict(arm="E2", ramp=False, min_up=True, symmetry=None,
         question="minimum up/down alone (ramp off)"),
    dict(arm="E3", ramp=False, min_up=False, symmetry=2,
         question="unchanged B0 model, aggressive solver symmetry detection"),
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt_01")
    parser.add_argument("--per-solve", type=float, default=PER_SOLVE_SECONDS)
    parser.add_argument("--budget", type=float, default=TOTAL_BUDGET_SECONDS)
    args = parser.parse_args(argv)

    target = OUT_ROOT / args.attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")

    data = load_rts24()
    case = pp.case24_ieee_rts()
    startup = {i: float(case["gencost"][i, 1]) for i in range(len(data.generators))}
    connected = _v1.non_islanding_branches(data)

    observed = _v2.observed_load(_v2.WINDOW_START, _v2.WINDOW_HOURS)
    mean = sum(observed) / len(observed)
    scale_by_hour = [value / mean for value in observed]
    case_load = [data.total_demand_mw * scale for scale in scale_by_hour]
    unservable = {
        _v2.WINDOW_START + offset
        for offset, value in enumerate(case_load)
        if value > _v2.PEAK_LIMIT_MW + 1.0e-9
    }
    starts = [
        start for start in range(_v2.WINDOW_HOURS - 24 + 1)
        if not any(_v2.WINDOW_START + h in unservable for h in range(start, start + 24))
    ]
    if not starts:
        raise SystemExit("no servable 24 h window")
    offset = starts[0]
    load_by_hour = scale_by_hour[offset:offset + 24]

    target.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    clock = time.perf_counter()
    records = []
    for arm in ARMS:
        elapsed = time.perf_counter() - clock
        remaining = args.budget - elapsed
        record = {
            "arm": arm["arm"], "ramp": arm["ramp"], "min_up": arm["min_up"],
            "symmetry": arm["symmetry"], "question": arm["question"],
            "window_start_hour": _v2.WINDOW_START + offset,
        }
        if remaining <= 5.0:
            record["status"] = "skipped_budget_exhausted"
            records.append(record)
            continue
        limit = min(args.per_solve, remaining)

        model = _v2.build_with_load(
            data, hours=24, outaged_branches=[frozenset()], integer=True,
            ramp=arm["ramp"], min_up=arm["min_up"], startup=startup,
            load_by_hour=load_by_hour,
        )
        record.update(_v1._count(model))
        options = {"OutputFlag": 0, "MipGap": 0.0, "TimeLimit": float(limit),
                   "Seed": 0, "Threads": 1}
        if arm["symmetry"] is not None:
            options["Symmetry"] = int(arm["symmetry"])
        solve_start = time.perf_counter()
        results = pyo.SolverFactory("gurobi").solve(
            model, load_solutions=False, options=options
        )
        record["solve_seconds"] = round(time.perf_counter() - solve_start, 3)
        record["termination"] = str(results.solver.termination_condition)
        problem = getattr(results, "problem", None)
        for key in ("upper_bound", "lower_bound"):
            value = getattr(problem, key, None) if problem is not None else None
            record[key] = None if value is None else float(value)
        if record["termination"] in {"optimal", "locallyOptimal", "globallyOptimal"}:
            model.solutions.load_from(results)
            record["status"] = "optimal"
            record["objective"] = float(pyo.value(model.total_cost))
        else:
            record["status"] = "hit_time_limit"
            record["objective"] = None
        records.append(record)
        print(json.dumps({"arm": record["arm"], "status": record["status"],
                          "solve_s": record["solve_seconds"],
                          "obj": record.get("objective"),
                          "ub": record.get("upper_bound"),
                          "lb": record.get("lower_bound")}, separators=(",", ":")))

    total = time.perf_counter() - clock
    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_grid_scuc_cost_v2_diagnostic_v1",
        "created_utc": started.isoformat(),
        "formal_result": False,
        "purpose": "explain the B0(290.5 s) / B2(0.5 s) ordering inversion before "
                   "either timing is cited",
        "model_note": "identical model, window, load, cost and budget to v2; only "
                      "the listed constraint family or solver symmetry setting differs",
        "declared": {
            "per_solve_time_limit_s": PER_SOLVE_SECONDS,
            "total_budget_s": TOTAL_BUDGET_SECONDS,
            "interpretation_rule": "E1/E2 change the model; E3 changes only the solver "
                                  "setting. A speed-up under E3 alone is a solver-symmetry "
                                  "artifact and must not be reported as a property of the "
                                  "stiff formulation.",
        },
        "environment": {"python": sys.version.split()[0],
                        "pyomo": _v1._pyomo_version(),
                        "gurobi": _v1._gurobi_version()},
        "window": {"start": _v2.WINDOW_START + offset, "hours": 24,
                   "rule": "earliest servable window, same as v2"},
        "reference": {"B0_seconds": 290.503, "B0_objective": 1380391.1621663827,
                      "B2_seconds": 0.526, "B2_objective": 1468306.8946349584,
                      "source": "v2 attempt_01"},
        "arms": records,
        "total_seconds": round(total, 2),
    }
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"total_seconds": report["total_seconds"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
