"""Stage 2 cost probe, part 2: the same SCUC on the real hourly load shape.

DRAFT_NONAUTHORITATIVE. Successor to
`staged_deliverability_grid_scuc_cost_v1.py`, which measured the flat-load
structure only. This file adds the one thing v1 deliberately held out: the
observed chronology.

Why a successor rather than an edit
-----------------------------------
v1's arms are a record of what was measured and are not rewritten. v1 also
fixed a caveat in advance -- "flat load keeps the probe a pure cost
measurement" -- so the moment the real shape enters, the arms, the declared
block and the reading all change. That is a new version, not a patched one.

The load profile
----------------
`data/processed/model_inputs/rq2_joint_data_v1/hourly_bus_load.csv.gz`, summed
over buses per source hour, window [0, 168) -- the exact series and window
stage 1 used. The bridge is stage 1's declared rule, unchanged:

    case_load_h = case_reference_load * (observed_h / observed_mean)

so the shape is measured and the level stays at the case's own reference. Each
bus keeps its own share of the case's demand.

Feasibility, and why it is not the stage-1 floor
------------------------------------------------
Stage 1 marked 5 of 168 hours non-evaluable for being *above* the fleet's
3405 MW ceiling. Under unit commitment that verdict stands and strengthens:
no on/off pattern can serve load above total pmax, so those hours are
structurally infeasible for SCUC too, and they are reported as such.

Stage 1's *other* exclusion -- the 1036 MW pmin floor -- is an artifact of
measuring capacity with every unit held at its minimum. Unit commitment can
turn units off, so total pmin is not a floor on the load a committed fleet can
serve. This window never falls below it anyway (minimum case load 2388 MW), so
the question does not bite here; it is recorded because the reason matters for
how the stage-1 table is read, not because it changes a number.

Arms (fixed before running)
---------------------------
The window start is not chosen by hand. A structural screen runs first, before
any cost is read: an hour whose case load exceeds the fleet's total pmax
cannot be served by any commitment, so every window containing one is
infeasible. The probe measures the *earliest* window whose hours are all
servable -- a mechanical rule, fixed in advance, that a later hour's cost
cannot influence. The screen's own findings are reported alongside the timings,
because they decide what stage 2 can even be run on.

| arm | hours | states | ramp/min-up | question                              |
|-----|-------|--------|-------------|---------------------------------------|
| B0  | 24    | 1      | -           | real shape, the v1 A3 comparison point|
| B1  | 24    | 5      | -           | real shape with security, ~v1 A7      |
| B2  | 24    | 1      | yes         | does declared stiffness bind now?     |
| B3  | 168   | 1      | -           | a full stage window, unscaled         |
| B4  | 168   | 5      | -           | candidate stage-2 shape at full width |

B3 and B4 run only if the 168 h screen passes. If it does not, they are
reported as structurally infeasible -- not skipped, not timed out, and not
rescaled into looking feasible.

Budget and stopping are identical to v1: 300 s per solve, 1800 s cumulative,
MIP gap 0.0, a capped arm blocks every later arm with a larger
`hours x states` product, and the arm reports `hit_time_limit` rather than a
number the solver never reached.
"""
from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pyomo.environ as pyo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import importlib.util

_SPEC = importlib.util.spec_from_file_location(
    "_scuc_cost_v1", ROOT / "experiments/staged_deliverability_grid_scuc_cost_v1.py"
)
_v1 = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_v1)

from src.grid.rts24 import load_rts24  # noqa: E402  (path bootstrap above)

OUT_ROOT = (
    ROOT
    / "results/tables/staged_deliverability_grid_scuc_cost_v2_non_authoritative"
)
JOINT = ROOT / "data/processed/model_inputs/rq2_joint_data_v1"

PER_SOLVE_SECONDS = 300.0
TOTAL_BUDGET_SECONDS = 1800.0
WINDOW_START = 0
WINDOW_HOURS = 168
PEAK_LIMIT_MW = 3405.0      # case24 total pmax; above this no commitment serves load

DECLARED = {
    "purpose": "bounded solve-cost diagnostic including the observed hourly load "
               "shape; successor to staged_deliverability_grid_scuc_cost_v1",
    "load_rule": "case_load_h = case_reference * (observed_h / observed_mean); "
                 "stage 1's declared mapping, unchanged",
    "load_source": "data/processed/model_inputs/rq2_joint_data_v1/"
                   "hourly_bus_load.csv.gz, source hours [0,168)",
    "infeasible_hours_rule": f"hours with case_load > {PEAK_LIMIT_MW} cannot be served "
                             f"by any commitment; reported, never dropped",
    "inherited_from_v1": "model, solver settings, state selection, startup cost, "
                         "declared ramp and minimum up/down, budget and stop rules",
    "solver": "gurobi",
    "mip_gap": 0.0,
    "per_solve_time_limit_s": PER_SOLVE_SECONDS,
    "total_budget_s": TOTAL_BUDGET_SECONDS,
}

ARMS = (
    dict(arm="B0", hours=24, states=1, ramp=False, min_up=False,
         question="real shape at 24 h (v1 A3 comparison point)"),
    dict(arm="B1", hours=24, states=5, ramp=False, min_up=False,
         question="real shape at 24 h with five security states (v1 A7 point)"),
    dict(arm="B2", hours=24, states=1, ramp=True, min_up=True,
         question="does the declared stiffness bind under a real shape?"),
    dict(arm="B3", hours=168, states=1, ramp=False, min_up=False,
         question="one full stage window at 168 h"),
    dict(arm="B4", hours=168, states=5, ramp=False, min_up=False,
         question="candidate stage-2 shape: 168 h with five states"),
)


def observed_load(start: int, hours: int) -> list[float]:
    """Total system load per source hour, summed over buses."""

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


def build_with_load(data, *, hours, outaged_branches, integer, ramp, min_up,
                    startup, load_by_hour):
    """v1's model, with per-hour load scaling.

    The only change from `_v1._build` is that the demand term varies by hour
    instead of being one flat scale. The structure, bounds, cost and state
    handling are v1's, so the arms are comparable.
    """

    model = _v1._build(
        data, hours=hours, outaged_branches=outaged_branches, integer=integer,
        ramp=ramp, min_up=min_up, startup=startup,
    )
    # Rebuild the balance constraints with the hourly scale. Deleting and
    # re-adding is safer than mutating, and keeps a single code path.
    model.del_component("balance")
    buses = tuple(bus.index for bus in data.buses)
    bus_by_index = {bus.index: bus for bus in data.buses}
    gen_by_index = {index: g for index, g in enumerate(data.generators)}
    gens = tuple(model.GEN)
    branches = tuple(model.BRANCH)
    branch_by_index = {branch.index: branch for branch in data.branches}
    gens_at_bus = {bus: [] for bus in buses}
    out_at_bus = {bus: [] for bus in buses}
    in_at_bus = {bus: [] for bus in buses}
    for index in gens:
        gens_at_bus[gen_by_index[index].bus].append(index)
    for index in branches:
        out_at_bus[branch_by_index[index].from_bus].append(index)
        in_at_bus[branch_by_index[index].to_bus].append(index)

    def balance_rule(model_, state, t, bus):
        demand = bus_by_index[bus].demand_mw * load_by_hour[t]
        return (
            sum(model_.generation[state, t, g] for g in gens_at_bus[bus])
            - sum(model_.flow[state, t, l] for l in out_at_bus[bus])
            + sum(model_.flow[state, t, l] for l in in_at_bus[bus])
            - demand
            == 0
        )

    model.balance = pyo.Constraint(
        model.STATE, model.TIME, model.BUS, rule=balance_rule
    )
    return model


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt_01")
    parser.add_argument("--budget", type=float, default=TOTAL_BUDGET_SECONDS)
    parser.add_argument("--per-solve", type=float, default=PER_SOLVE_SECONDS)
    parser.add_argument("--ladder", default="")
    args = parser.parse_args(argv)

    target = OUT_ROOT / args.attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")

    import pypower.api as pp

    data = load_rts24()
    case = pp.case24_ieee_rts()
    startup = {
        index: float(case["gencost"][index, 1])
        for index in range(len(data.generators))
    }

    observed = observed_load(WINDOW_START, WINDOW_HOURS)
    mean = sum(observed) / len(observed)
    scale_by_hour = [value / mean for value in observed]
    case_load = [data.total_demand_mw * scale for scale in scale_by_hour]
    infeasible_hours = [
        WINDOW_START + offset
        for offset, value in enumerate(case_load)
        if value > PEAK_LIMIT_MW + 1.0e-9
    ]
    unservable = set(infeasible_hours)

    # Structural screen, run before any cost is read. The earliest window whose
    # every hour is servable; mechanical, so no later result can steer it.
    feasible_24h_starts = [
        start
        for start in range(WINDOW_HOURS - 24 + 1)
        if not any((WINDOW_START + h) in unservable for h in range(start, start + 24))
    ]
    window_24h_start = (
        WINDOW_START + feasible_24h_starts[0] if feasible_24h_starts else None
    )
    window_168h_feasible = not infeasible_hours

    connected = _v1.non_islanding_branches(data)

    arms = list(ARMS)
    if args.ladder:
        wanted = {name.strip() for name in args.ladder.split(",") if name.strip()}
        arms = [arm for arm in arms if arm["arm"] in wanted]

    target.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    clock = time.perf_counter()

    records = []
    capped_product = None
    for arm in arms:
        horizon = arm["hours"]
        state_count = int(arm["states"])
        product = horizon * state_count
        elapsed = time.perf_counter() - clock
        remaining = args.budget - elapsed
        record = {
            "arm": arm["arm"], "hours": horizon, "states": state_count,
            "integer": True, "ramp": arm["ramp"], "min_up": arm["min_up"],
            "question": arm["question"],
        }
        if capped_product is not None and product > capped_product:
            record["status"] = "skipped_after_cap"
            records.append(record)
            continue
        if remaining <= 5.0:
            record["status"] = "skipped_budget_exhausted"
            records.append(record)
            continue

        limit = min(args.per_solve, remaining)
        outages = [frozenset()] + [
            frozenset([line]) for line in connected[: state_count - 1]
        ]

        # Window start comes from the screen, not from the arm definition:
        # a 24 h arm uses the earliest servable window, a 168 h arm the whole
        # window it screened. An arm whose window is structurally infeasible is
        # recorded as such and never solved, because an infeasible MIP returns
        # no timing that means anything.
        if horizon == WINDOW_HOURS:
            if not window_168h_feasible:
                record["status"] = "structurally_infeasible"
                record["reason"] = (
                    f"{len(infeasible_hours)} hour(s) in the 168 h window exceed the "
                    f"fleet ceiling {PEAK_LIMIT_MW} MW; no commitment can serve them"
                )
                records.append(record)
                continue
            start_offset = 0
        else:
            if window_24h_start is None:
                record["status"] = "structurally_infeasible"
                record["reason"] = "no servable 24 h window in the screened span"
                records.append(record)
                continue
            start_offset = window_24h_start - WINDOW_START
        record["window_start_hour"] = WINDOW_START + start_offset
        load_by_hour = scale_by_hour[start_offset:start_offset + horizon]

        build_start = time.perf_counter()
        model = build_with_load(
            data, hours=horizon, outaged_branches=outages, integer=True,
            ramp=arm["ramp"], min_up=arm["min_up"], startup=startup,
            load_by_hour=load_by_hour,
        )
        record["build_seconds"] = round(time.perf_counter() - build_start, 3)
        record.update(_v1._count(model))

        solve_start = time.perf_counter()
        results = pyo.SolverFactory("gurobi").solve(
            model, load_solutions=False,
            options={"OutputFlag": 0, "MipGap": 0.0, "TimeLimit": float(limit),
                     "Seed": 0, "Threads": 1},
        )
        record["solve_seconds"] = round(time.perf_counter() - solve_start, 3)
        record["time_limit_s"] = round(limit, 1)
        termination = str(results.solver.termination_condition)
        record["termination"] = termination
        problem = getattr(results, "problem", None)
        for key in ("upper_bound", "lower_bound", "gap"):
            value = getattr(problem, key, None) if problem is not None else None
            record[key] = None if value is None else float(value)

        if termination in {"optimal", "locallyOptimal", "globallyOptimal"}:
            model.solutions.load_from(results)
            record["status"] = "optimal"
            record["objective"] = float(pyo.value(model.total_cost))
            committed = [
                sum(1 for g in model.GEN if pyo.value(model.commitment[t, g]) > 0.5)
                for t in range(horizon)
            ]
            record["units_committed_min"] = min(committed)
            record["units_committed_max"] = max(committed)
            record["starts"] = int(round(sum(
                pyo.value(model.startup[t, g])
                for t in range(horizon) for g in model.GEN
            )))
            # Sanity: served energy equals demand energy on the base state.
            served = sum(
                pyo.value(model.generation[0, t, g])
                for t in range(horizon) for g in model.GEN
            )
            demanded = sum(
                data.total_demand_mw * load_by_hour[t] for t in range(horizon)
            )
            record["served_mwh"] = round(served, 3)
            record["demanded_mwh"] = round(demanded, 3)
            record["balance_error_mwh"] = round(served - demanded, 6)
        else:
            record["status"] = "not_optimal"
            record["objective"] = None
            if float(record["solve_seconds"]) >= limit - 1.0:
                record["status"] = "hit_time_limit"
                capped_product = product
        records.append(record)
        print(json.dumps({
            "arm": record["arm"], "status": record["status"],
            "solve_s": record["solve_seconds"], "build_s": record["build_seconds"],
            "vars": record.get("vars"), "bins": record.get("binaries"),
            "obj": record.get("objective"), "starts": record.get("starts"),
        }, separators=(",", ":")))

    total = time.perf_counter() - clock
    by_name = {record["arm"]: record for record in records}
    comparisons = {}
    for left, right, label in (
        ("B0", "B1", "security_1_to_5_states_at_24h"),
        ("B0", "B2", "declared_stiffness_at_24h"),
        ("B0", "B3", "horizon_24h_to_168h"),
        ("B1", "B4", "horizon_24h_to_168h_at_5_states"),
    ):
        low, high = by_name.get(left), by_name.get(right)
        if (low and high and low.get("objective") is not None
                and high.get("objective") is not None):
            comparisons[label] = {
                "from": left, "to": right,
                "objective_delta_usd": round(high["objective"] - low["objective"], 1),
                "seconds_ratio": round(
                    high["solve_seconds"] / max(low["solve_seconds"], 1.0e-9), 2
                ),
            }

    # v1's flat-load arms, restated so the two probes can be read side by side.
    v1_reference = {
        "A3_24h_flat_1state_seconds": 4.425,
        "A7_24h_flat_5states_seconds": 58.159,
        "note": "measured in v1 attempt_01; flat 2850 MW load; same model, "
                "same budget, same solver settings",
    }

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_grid_scuc_cost_v2",
        "successor_of": "staged_deliverability_grid_scuc_cost_v1",
        "created_utc": started.isoformat(),
        "formal_result": False,
        "resource_admission": False,
        "security_certified": False,
        "ac_certified": False,
        "aggregate_contract_release": False,
        "model_note": (
            "v1's DC SCUC (binary commitment, transition, startup, quadratic "
            "fuel cost, per-state recourse) on the observed hourly load shape. "
            "Cost probe only."
        ),
        "declared": DECLARED,
        "inherited_model": _v1.DECLARED,
        "environment": {
            "python": sys.version.split()[0],
            "pyomo": _v1._pyomo_version(),
            "gurobi": _v1._gurobi_version(),
            "case_module_sha256": _v1._case_sha(),
            "load_series_sha256": hashlib.sha256(
                (JOINT / "hourly_bus_load.csv.gz").read_bytes()
            ).hexdigest(),
        },
        "load_window": {
            "start": WINDOW_START,
            "hours": WINDOW_HOURS,
            "observed_mean_mw": round(mean, 3),
            "case_load_min_mw": round(min(case_load), 1),
            "case_load_max_mw": round(max(case_load), 1),
            "case_load_mean_mw": round(sum(case_load) / len(case_load), 1),
            "infeasible_hours": infeasible_hours,
            "infeasible_reason": f"case load above the fleet ceiling {PEAK_LIMIT_MW} MW",
            "evaluable_hours": WINDOW_HOURS - len(infeasible_hours),
        },
        "structural_screen": {
            "rule": f"an hour is servable iff case_load <= {PEAK_LIMIT_MW} MW "
                    f"(fleet total pmax); a window is feasible iff every hour is",
            "run_before": "any solve; no cost was read when this ran",
            "hours_window_168_feasible": window_168h_feasible,
            "feasible_24h_window_count": len(feasible_24h_starts),
            "feasible_24h_starts_first_last": (
                [feasible_24h_starts[0], feasible_24h_starts[-1]]
                if feasible_24h_starts else None
            ),
            "window_24h_start_used": window_24h_start,
            "window_choice_rule": "earliest servable window; fixed, not selected "
                                  "against any cost or objective",
            "peak_shortfall_mw": round(max(case_load) - PEAK_LIMIT_MW, 1),
        },
        "arms": records,
        "comparisons": comparisons,
        "v1_reference": v1_reference,
        "solves_attempted": sum(1 for r in records if r.get("solve_seconds") is not None),
        "solves_optimal": sum(1 for r in records if r.get("status") == "optimal"),
        "total_seconds": round(total, 2),
        "budget_seconds": args.budget,
    }
    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"total_seconds": report["total_seconds"],
                      "optimal": report["solves_optimal"],
                      "attempted": report["solves_attempted"],
                      "comparisons": comparisons}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
