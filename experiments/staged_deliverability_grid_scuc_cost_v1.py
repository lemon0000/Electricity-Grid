"""Stage 2 cost probe: DC SCUC solve cost on the RTS-24 case used by stages 0/1.

DRAFT_NONAUTHORITATIVE. This is a bounded performance diagnostic under
`agent.md` section 9, not a scientific result, not an admission, and not a
deliverable-capacity measurement. It exists to answer one gated question:

    can a 24 h SCUC window be solved at a cost that fits the paper's budget?

Stage 0 measured a DC OPF / N-1 LP at ~25 ms per solve. That number cannot be
extrapolated to SCUC: unit commitment adds binary variables and intertemporal
state (transition indicators, startup cost, ramp, minimum up/down), and the
N-1 security formulation multiplies the network constraints by the number of
contingency states. `results/logs/` holds 20 unfinished SCUC attempts from an
earlier, much larger formulation; the history says the cost must be measured,
not assumed.

Everything that could be tuned after seeing a timing is fixed here, in the
docstring and in `DECLARED`, before the first solve:

Model
-----
DC, one slack (the case reference bus, 13). Per hour and per security state:
nodal balance, `f_l = (base/x_l)(theta_from - theta_to)`, `|f_l| <= rate_a`.
Unit commitment on the base state; contingency states carry the same
commitment with per-state recourse dispatch (preventive security reading: the
commitment must be feasible in every state, dispatch may differ).

    pmin_g * u[t,g] <= p[s,t,g] <= pmax_g * u[t,g]
    su[t,g] - sd[t,g] = u[t,g] - u[t,g-1]        u[t<0,g] := 0
    su[t,g] + sd[t,g] <= 1

Operating cost is charged on the base state only; contingency states add
constraints, not cost. Objective is the case24 quadratic fuel cost
(`c2 p^2 + c1 p`) plus no-load `c0 u` plus startup `STARTUP su`, exactly as the
case's own gencost rows carry them. Since the objective is quadratic and the
commitment is binary, this is an MIQP; it is not the repo's production SCUC
formulation (piecewise-linear segments, reserve envelopes, RTS-GMLC 158-unit
data), so the timings bound the combinatorial cost of the horizon/state shape,
not the production model's cost. That distinction is recorded, not papered over.

Deliberately excluded from the probe (each is a continuous variable per
(state, hour) at most, i.e. it cannot change the combinatorial cost this probe
measures):

- the POI injection variable that turns capacity into an output (`delta`);
- spinning-reserve envelope and the RTS-GMLC DC branches;
- renewable profiles and any chronology. Load is the case reference demand
  (2850 MW) held flat, because flat load removes the stage-1 feasibility-floor
  trap and keeps the probe a pure cost measurement.

Parameters and their provenance
-------------------------------
From the pinned case (public static benchmark, PYPOWER 5.1.19 `case24_ieee_rts`):

- pmin/pmax, rate_a, reactance, quadratic fuel cost, no-load cost, startup.

`STARTUP` in this case is 1500 $/start for every unit -- a single generic RTS
value, not per-technology. It is used as-is and is not presented as calibrated.

Absent from the case, therefore **declared**, uncalibrated, and flagged as
`mechanism_assumption` in the report:

- ramp rate. case24's RAMP_10/RAMP_30 columns are all zero, so
  `src/grid/rts24.py` returns `ramp=None` for every unit. The ramp arm uses
  `0.5 * pmax per hour` (a unit can traverse its full range in two hours).
- minimum up/down time. Also absent from the case; the stiff arm uses 4 h.

The base arms use neither, so the horizon ladder measures the cost of binary
commitment and startup/transition state alone; the ramp arm measures what the
declared intertemporal stiffness adds on top.

Security states
---------------
State 0 is the intact network. Contingency states outage one branch each, in
case order, restricted to branches whose loss leaves the network connected
(computed at run time by union-find over in-service branches; this is the same
`all_non_islanding` convention the frozen RTS-24 config declares). Which
specific branch each state outages is irrelevant to a cost measurement, so the
selection is mechanical (case order) rather than chosen.

Ladder (fixed before running, eight solves)
-------------------------------------------
| arm | T  | states        | ramp      | min up/down | question                   |
|-----|----|---------------|-----------|-------------|----------------------------|
| A0  | 1  | 1             | -         | -           | LP anchor (~stage 0)       |
| A1  | 1  | 1             | -         | -           | binary overhead at 1 h     |
| A2  | 4  | 1             | -         | -           | intertemporal state at 4 h |
| A3  | 24 | 1             | -         | -           | horizon cost at 24 h       |
| A4  | 4  | 5             | -         | -           | security multiplier, small |
| A5  | 4  | all connected | -         | -           | security multiplier, full  |
| A6  | 4  | 1             | 0.5*pmax  | 4 h         | declared stiffness         |
| A7  | 24 | 5             | -         | -           | candidate stage-2 shape    |

Budget and stop conditions
--------------------------
- per solve: TimeLimit 300 s, MIP gap 0.0 (a certified solve is what the paper
  would need; the achieved gap is recorded when the cap bites);
- whole probe: 1800 s cumulative wall clock, checked before each arm; the
  remaining budget caps the next arm's own TimeLimit;
- directional stop: if an arm hits its cap, every later arm with a larger
  `T x states` product is skipped and reported as skipped, not as timed out;
- no solver process is left running: every solve carries its own TimeLimit.

Output is create-only: the attempt directory must not exist.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pypower.api as pp
import pyomo.environ as pyo
from pypower.idx_cost import STARTUP
from pypower.idx_gen import PMAX, PMIN

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.grid.rts24 import load_rts24  # noqa: E402  (path bootstrap above)

OUT_ROOT = (
    ROOT
    / "results/tables/staged_deliverability_grid_scuc_cost_v1_non_authoritative"
)

PER_SOLVE_SECONDS = 300.0
TOTAL_BUDGET_SECONDS = 1800.0
LOAD_MW = 2850.0                    # case reference demand, held flat
RAMP_FRACTION = 0.5                 # declared, uncalibrated
MIN_UP_HOURS = 4                    # declared, uncalibrated
MIN_DOWN_HOURS = 4                  # declared, uncalibrated
# Angle bound in radians. Case24's stiffest line carries 175 MW at a
# susceptance of base/x = 2000 MW/rad, i.e. a 0.088 rad angle difference, so
# +/-1 rad cannot bind in the intact case and is generous under contingency.
# A looser bound would only make the probe easier than the production model.
ANGLE_BOUND_RAD = 1.0

DECLARED = {
    "purpose": "bounded solve-cost diagnostic for the stage-2 SCUC gate",
    "solver": "gurobi",
    "mip_gap": 0.0,
    "per_solve_time_limit_s": PER_SOLVE_SECONDS,
    "total_budget_s": TOTAL_BUDGET_SECONDS,
    "load_mw": LOAD_MW,
    "load_rule": "case reference demand held flat for every hour",
    "cost_charged_on": "base state only; contingency states add constraints",
    "state_selection": "one branch outaged per state, case order, non-islanding "
                       "only (union-find over in-service branches)",
    "ramp_declared_fraction_of_pmax_per_hour": RAMP_FRACTION,
    "ramp_source": "mechanism_assumption: case24 RAMP_10/RAMP_30 are zero",
    "min_up_declared_hours": MIN_UP_HOURS,
    "min_down_declared_hours": MIN_DOWN_HOURS,
    "min_up_down_source": "mechanism_assumption: absent from case24",
    "startup_cost_source": "case24 gencost STARTUP = 1500 for every unit; "
                           "generic RTS value, not per-technology, not calibrated",
    "excluded": [
        "POI injection (delta) variable",
        "spinning reserve envelope and RTS-GMLC DC branches",
        "renewable profiles and any chronology",
        "piecewise-linear cost segments (production SCUC formulation)",
    ],
    "direction_of_bias": "the probe is expected to be cheaper per solve than "
                         "the production formulation because it omits reserve "
                         "envelopes and the RTS-GMLC unit set; if the probe "
                         "already exceeds the budget, the production model "
                         "does too. The reverse inference is not made.",
}

LADDER = (
    dict(arm="A0", hours=1, states=1, integer=False, ramp=False, min_up=False,
         question="LP anchor at one hour (compare stage 0/1 ~25 ms)"),
    dict(arm="A1", hours=1, states=1, integer=True, ramp=False, min_up=False,
         question="binary commitment overhead at one hour"),
    dict(arm="A2", hours=4, states=1, integer=True, ramp=False, min_up=False,
         question="intertemporal state at four hours"),
    dict(arm="A3", hours=24, states=1, integer=True, ramp=False, min_up=False,
         question="horizon cost at twenty-four hours"),
    dict(arm="A4", hours=4, states=5, integer=True, ramp=False, min_up=False,
         question="security multiplier, five states"),
    dict(arm="A5", hours=4, states="all", integer=True, ramp=False, min_up=False,
         question="security multiplier, every non-islanding state"),
    dict(arm="A6", hours=4, states=1, integer=True, ramp=True, min_up=True,
         question="declared ramp and minimum up/down stiffness"),
    dict(arm="A7", hours=24, states=5, integer=True, ramp=False, min_up=False,
         question="candidate stage-2 shape: 24 h with five states"),
)


def _components(nodes, edges):
    parent = {node: node for node in nodes}

    def find(node):
        while parent[node] != node:
            parent[node] = parent[parent[node]]
            node = parent[node]
        return node

    for left, right in edges:
        ra, rb = find(left), find(right)
        if ra != rb:
            parent[ra] = rb
    return len({find(node) for node in nodes})


def non_islanding_branches(data) -> tuple[int, ...]:
    """Branch indices whose individual loss leaves the network connected."""

    nodes = [bus.index for bus in data.buses]
    keep = []
    for branch in data.branches:
        edges = [
            (other.from_bus, other.to_bus)
            for other in data.branches
            if other.in_service and other.index != branch.index
        ]
        if _components(nodes, edges) == 1:
            keep.append(branch.index)
    return tuple(keep)


def _build(data, *, hours, outaged_branches, integer, ramp, min_up, startup):
    """Build the DC SCUC model. `outaged_branches[0]` must be the empty set."""

    buses = tuple(bus.index for bus in data.buses)
    gens = tuple(
        index
        for index, generator in enumerate(data.generators)
        if generator.in_service and generator.p_max_mw > 0.0
    )
    branches = tuple(branch.index for branch in data.branches)
    bus_by_index = {bus.index: bus for bus in data.buses}
    gen_by_index = {index: generator for index, generator in enumerate(data.generators)}
    branch_by_index = {branch.index: branch for branch in data.branches}
    states = tuple(range(len(outaged_branches)))

    gens_at_bus = {bus: [] for bus in buses}
    out_at_bus = {bus: [] for bus in buses}
    in_at_bus = {bus: [] for bus in buses}
    for index in gens:
        gens_at_bus[gen_by_index[index].bus].append(index)
    for index in branches:
        out_at_bus[branch_by_index[index].from_bus].append(index)
        in_at_bus[branch_by_index[index].to_bus].append(index)

    load_scale = LOAD_MW / data.total_demand_mw

    model = pyo.ConcreteModel()
    model.TIME = pyo.RangeSet(0, hours - 1)
    model.STATE = pyo.Set(initialize=states, ordered=True)
    model.GEN = pyo.Set(initialize=gens, ordered=True)
    model.BUS = pyo.Set(initialize=buses, ordered=True)
    model.BRANCH = pyo.Set(initialize=branches, ordered=True)

    model.commitment = pyo.Var(
        model.TIME, model.GEN, domain=pyo.Binary if integer else pyo.NonNegativeReals,
        bounds=(0.0, 1.0) if not integer else None,
    )
    if not integer:
        # LP anchor: commitment forced on, so the arm measures the same network
        # and cost without the combinatorial part.
        for time_index in range(hours):
            for gen in gens:
                model.commitment[time_index, gen].fix(1.0)

    def generation_bounds(_model, _state, _time, gen):
        generator = gen_by_index[gen]
        return 0.0, generator.p_max_mw

    model.generation = pyo.Var(
        model.STATE, model.TIME, model.GEN, domain=pyo.NonNegativeReals,
        bounds=generation_bounds,
    )
    model.angle = pyo.Var(
        model.STATE, model.TIME, model.BUS,
        bounds=(-ANGLE_BOUND_RAD, ANGLE_BOUND_RAD),
    )
    model.flow = pyo.Var(model.STATE, model.TIME, model.BRANCH)

    if integer:
        model.startup = pyo.Var(model.TIME, model.GEN, bounds=(0.0, 1.0))
        model.shutdown = pyo.Var(model.TIME, model.GEN, bounds=(0.0, 1.0))

    def committed(_model, time_index, gen):
        if integer:
            return model.commitment[time_index, gen]
        return 1.0

    model.on_min = pyo.Constraint(
        model.STATE, model.TIME, model.GEN,
        rule=lambda m, state, t, g: (
            m.generation[state, t, g] >= gen_by_index[g].p_min_mw * committed(m, t, g)
        ),
    )
    model.on_max = pyo.Constraint(
        model.STATE, model.TIME, model.GEN,
        rule=lambda m, state, t, g: (
            m.generation[state, t, g] <= gen_by_index[g].p_max_mw * committed(m, t, g)
        ),
    )

    def balance_rule(model_, state, t, bus):
        demand = bus_by_index[bus].demand_mw * load_scale
        return (
            sum(model_.generation[state, t, g] for g in gens_at_bus[bus])
            - sum(model_.flow[state, t, l] for l in out_at_bus[bus])
            + sum(model_.flow[state, t, l] for l in in_at_bus[bus])
            - demand
            == 0
        )

    model.balance = pyo.Constraint(model.STATE, model.TIME, model.BUS, rule=balance_rule)

    dead = {state: outaged_branches[state] for state in states}

    def flow_rule(model_, state, t, line):
        if line in dead[state]:
            return model_.flow[state, t, line] == 0.0
        branch = branch_by_index[line]
        susceptance = data.base_mva / (branch.reactance_pu * branch.tap_ratio)
        angle_from = model_.angle[state, t, branch.from_bus]
        angle_to = model_.angle[state, t, branch.to_bus]
        return model_.flow[state, t, line] == susceptance * (angle_from - angle_to)

    model.dc_flow = pyo.Constraint(model.STATE, model.TIME, model.BRANCH, rule=flow_rule)
    model.rating = pyo.Constraint(
        model.STATE, model.TIME, model.BRANCH,
        rule=lambda m, state, t, l: (
            (-branch_by_index[l].rate_a_mw, m.flow[state, t, l],
             branch_by_index[l].rate_a_mw)
        ),
    )
    for state in states:
        model.angle[state, :, data.reference_bus].fix(0.0)

    if integer:
        # Two separate components on purpose: a two-element tuple returned from
        # one rule is read as (lower, upper) bounds, not as two constraints.
        def startup_rule(model_, t, g):
            previous = model_.commitment[t - 1, g] if t > 0 else 0.0
            return (
                model_.startup[t, g] - model_.shutdown[t, g]
                == model_.commitment[t, g] - previous
            )

        model.startup_link = pyo.Constraint(model.TIME, model.GEN, rule=startup_rule)
        model.transition_exclusive = pyo.Constraint(
            model.TIME, model.GEN,
            rule=lambda m_, t, g: m_.startup[t, g] + m_.shutdown[t, g] <= 1,
        )

    if ramp:
        def ramp_rule(model_, state, t, g):
            if t == 0:
                return pyo.Constraint.Skip
            limit = RAMP_FRACTION * gen_by_index[g].p_max_mw
            return (
                -limit,
                model_.generation[state, t, g] - model_.generation[state, t - 1, g],
                limit,
            )

        model.ramp = pyo.Constraint(model.STATE, model.TIME, model.GEN, rule=ramp_rule)

    if min_up:
        def up_rule(model_, t, g):
            if t < MIN_UP_HOURS - 1:
                return pyo.Constraint.Skip
            return sum(model_.commitment[k, g] for k in range(t - MIN_UP_HOURS + 1, t + 1)) \
                >= MIN_UP_HOURS * model_.startup[t, g]

        def down_rule(model_, t, g):
            if t < MIN_DOWN_HOURS - 1:
                return pyo.Constraint.Skip
            return sum(1.0 - model_.commitment[k, g]
                       for k in range(t - MIN_DOWN_HOURS + 1, t + 1)) \
                >= MIN_DOWN_HOURS * model_.shutdown[t, g]

        model.min_up = pyo.Constraint(model.TIME, model.GEN, rule=up_rule)
        model.min_down = pyo.Constraint(model.TIME, model.GEN, rule=down_rule)

    base = 0
    fuel_and_noload = sum(
        gen_by_index[g].cost_quadratic * model.generation[base, t, g] ** 2
        + gen_by_index[g].cost_linear * model.generation[base, t, g]
        + gen_by_index[g].cost_constant * committed(model, t, g)
        for t in range(hours)
        for g in gens
    )
    if integer:
        start_cost = sum(startup[g] * model.startup[t, g]
                         for t in range(hours) for g in gens)
    else:
        start_cost = 0.0
    model.total_cost = pyo.Objective(expr=fuel_and_noload + start_cost, sense=pyo.minimize)
    return model


def _count(model) -> dict:
    variables = 0
    binaries = 0
    integers = 0
    for variable in model.component_data_objects(pyo.Var, active=True):
        variables += 1
        if variable.is_binary():
            binaries += 1
        elif variable.is_integer():
            integers += 1
    constraints = sum(
        1 for _ in model.component_data_objects(pyo.Constraint, active=True)
    )
    return {
        "vars": variables,
        "binaries": binaries,
        "integers": integers,
        "constraints": constraints,
    }


def _case_sha() -> str:
    import pypower

    path = Path(pypower.__file__).parent / "case24_ieee_rts.py"
    return hashlib.sha256(path.read_bytes()).hexdigest()


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

    data = load_rts24()
    case = pp.case24_ieee_rts()
    gens = [index for index, g in enumerate(data.generators) if g.in_service]
    for index in gens:
        row = case["gen"][index]
        if abs(float(row[PMAX]) - data.generators[index].p_max_mw) > 1.0e-9:
            raise ValueError(f"generator {index} pmax misaligned with case rows")
        if abs(float(row[PMIN]) - data.generators[index].p_min_mw) > 1.0e-9:
            raise ValueError(f"generator {index} pmin misaligned with case rows")
    startup = {
        index: float(case["gencost"][index, STARTUP]) for index in range(len(data.generators))
    }

    connected = non_islanding_branches(data)
    if len(connected) == 0:
        raise ValueError("no non-islanding branch found; state rule invalid")
    excluded = sorted(set(branch.index for branch in data.branches) - set(connected))

    ladder = list(LADDER)
    if args.ladder:
        wanted = {name.strip() for name in args.ladder.split(",") if name.strip()}
        ladder = [arm for arm in ladder if arm["arm"] in wanted]

    target.mkdir(parents=True)
    started = datetime.now(timezone.utc)
    clock = time.perf_counter()

    arms = []
    capped_product = None
    for arm in ladder:
        state_count = len(connected) if arm["states"] == "all" else int(arm["states"])
        product = arm["hours"] * state_count
        elapsed = time.perf_counter() - clock
        remaining = args.budget - elapsed
        record = {
            "arm": arm["arm"], "hours": arm["hours"], "states": state_count,
            "integer": arm["integer"], "ramp": arm["ramp"], "min_up": arm["min_up"],
            "question": arm["question"],
        }
        if capped_product is not None and product > capped_product:
            record["status"] = "skipped_after_cap"
            arms.append(record)
            continue
        if remaining <= 5.0:
            record["status"] = "skipped_budget_exhausted"
            arms.append(record)
            continue

        limit = min(args.per_solve, remaining)
        outages = [frozenset()] + [frozenset([line]) for line in connected[: state_count - 1]]
        if len(outages) != state_count:
            raise ValueError(f"state construction mismatch for {arm['arm']}")

        build_start = time.perf_counter()
        model = _build(
            data, hours=arm["hours"], outaged_branches=outages,
            integer=arm["integer"], ramp=arm["ramp"], min_up=arm["min_up"],
            startup=startup,
        )
        record["build_seconds"] = round(time.perf_counter() - build_start, 3)
        record.update(_count(model))

        solve_start = time.perf_counter()
        results = pyo.SolverFactory("gurobi").solve(
            model,
            load_solutions=False,
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
            dispatched = {
                index: float(pyo.value(model.generation[0, 0, index]))
                for index in model.GEN
            }
            record["base_hour0_total_mw"] = round(sum(dispatched.values()), 3)
            record["base_hour0_committed"] = int(
                sum(1 for index in model.GEN if pyo.value(model.commitment[0, index]) > 0.5)
            )
        else:
            record["status"] = "not_optimal"
            record["objective"] = None
            if float(record["solve_seconds"]) >= limit - 1.0:
                record["status"] = "hit_time_limit"
                capped_product = product
        arms.append(record)
        print(json.dumps({"arm": record["arm"], "status": record["status"],
                          "solve_s": record["solve_seconds"],
                          "build_s": record["build_seconds"],
                          "vars": record.get("vars"),
                          "bins": record.get("binaries")}, separators=(",", ":")))

    total = time.perf_counter() - clock
    timed = [arm for arm in arms if arm.get("solve_seconds") is not None]
    scaling = {}
    by_name = {arm["arm"]: arm for arm in arms}
    for left, right, label in (
        ("A0", "A1", "binary_overhead_1h"),
        ("A1", "A2", "intertemporal_1h_to_4h"),
        ("A2", "A3", "horizon_4h_to_24h"),
        ("A2", "A4", "states_1_to_5_at_4h"),
        ("A4", "A5", "states_5_to_all_at_4h"),
        ("A2", "A6", "declared_stiffness_at_4h"),
    ):
        low, high = by_name.get(left), by_name.get(right)
        if (low and high and low.get("solve_seconds") and high.get("solve_seconds")
                and low["status"] == "optimal" and high["status"] == "optimal"):
            scaling[label] = {
                "from": left, "to": right,
                "seconds_ratio": round(high["solve_seconds"] / max(low["solve_seconds"], 1.0e-9), 2),
            }

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_grid_scuc_cost_v1",
        "created_utc": started.isoformat(),
        "formal_result": False,
        "resource_admission": False,
        "security_certified": False,
        "ac_certified": False,
        "aggregate_contract_release": False,
        "model_note": (
            "DC SCUC on PYPOWER case24_ieee_rts: binary commitment, transition "
            "indicators, startup cost, quadratic fuel cost; per-state recourse "
            "dispatch under one branch outage. Cost probe only -- no POI "
            "capacity output, no reserve envelope, no chronology."
        ),
        "declared": DECLARED,
        "environment": {
            "python": sys.version.split()[0],
            "pyomo": _pyomo_version(),
            "gurobi": _gurobi_version(),
            "case_module_sha256": _case_sha(),
            "case_source": "PYPOWER case24_ieee_rts",
        },
        "data": {
            "base_mva": data.base_mva,
            "buses": len(data.buses),
            "branches": len(data.branches),
            "generators_in_service": len(gens),
            # One case24 unit has pmax = 0 (a synchronous condenser). It is in
            # service but cannot be dispatched, so the model excludes it; the
            # two counts are reported separately rather than conflated.
            "generators_modelled": sum(
                1 for index in gens if data.generators[index].p_max_mw > 0.0
            ),
            "pmin_total_mw": round(sum(g.p_min_mw for g in data.generators if g.in_service), 3),
            "pmax_total_mw": round(sum(g.p_max_mw for g in data.generators if g.in_service), 3),
            "load_mw": LOAD_MW,
            "non_islanding_branches": list(connected),
            "islanding_excluded": excluded,
            "startup_cost_usd": sorted({round(value, 3) for value in startup.values()}),
        },
        "arms": arms,
        "scaling_measured": scaling,
        "solves_attempted": len(timed),
        "solves_optimal": sum(1 for arm in timed if arm["status"] == "optimal"),
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
                      "scaling": scaling}, indent=1))
    return 0


def _pyomo_version() -> str | None:
    try:
        import pyomo.version

        return str(pyomo.version.version)
    except Exception:  # pragma: no cover - diagnostics only
        return None


def _gurobi_version() -> str | None:
    try:
        import gurobipy

        return ".".join(str(part) for part in gurobipy.gurobi.version())
    except Exception:  # pragma: no cover - diagnostics only
        return None


if __name__ == "__main__":
    raise SystemExit(main())
