"""Double-commitment narrow band: can the model distinguish R2 from R3?

DRAFT_NONAUTHORITATIVE. A feasibility probe, not a result.

Why this exists
---------------
The frozen 70-cell phase map reported `R1=0, R2=0, R3=69, mixed=1`: every cell was
"common insufficiency" (the resources were not enough for both services together in a
way that no allocation fixes) and none was "double-commitment risk" (each service alone
would have been servable, but both at once compete for the same flexibility pool).

That leaves an open question the paper can turn into its contribution: under what
conditions is R2 reachable at all? R2 requires a narrow band -- the flexibility pool
must cover either service alone, but not both together. This probe builds that band by
hand and asks whether the existing MILP (src/models/rq2_joint_deliverability.py)
actually reports it.

If the model detects the hand-built band, the criterion is sound and the open problem
is data (finding real parameters inside the band). If it does not, the classifier or the
model is wrong and must be fixed before any paper claim.

Arms
----
- network_only_shared : serves the grid request alone
- cfe_only_shared     : serves the CFE request alone
- joint_correct_shared: serves both against one shared pool

The band, in one hour, with a single shared flexibility pool of size P:

    grid_request  <= P          (network alone fits)
    cfe_request   <= P          (CFE alone fits)
    grid + cfe    >  P          (together do not fit)

That is exactly the definition of double-commitment risk.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pyomo.environ as pyo

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.models.rq2_joint_deliverability import (  # noqa: E402
    CFE_ONLY_SHARED, JOINT_CORRECT_SHARED, NETWORK_ONLY_SHARED,
    JointDeliverabilityPlanningInputs, JointDeliverabilityScenario,
    build_arm_planning_model,
)

HOURS = 4
POOL = 1.0                      # shared flexibility pool per hour


def scenario(grid, cfe, headroom):
    return JointDeliverabilityScenario(
        name="band",
        power_block_id="p", workload_block_id="w", probability=1.0,
        raw_grid_request=grid, raw_cfe_request=cfe,
        effective_grid_request=grid, effective_cfe_request=cfe,
        available_flexibility=(POOL,) * HOURS,
        connected_demand=(POOL,) * HOURS,
        business_recovery_headroom=headroom,
        cfe_service_recovery_headroom=headroom,
    )


def inputs(scn):
    return JointDeliverabilityPlanningInputs(
        scenarios=(scn,), time_step_hours=1.0,
        maximum_flexibility_budget=POOL,
        minimum_event_power=1.0e-6, response_time_hours=1.0,
        curtailment_ramp_per_hour=10.0, minimum_recovery_hours=1.0,
        recovery_efficiency=1.0, maximum_event_duration_hours=float(HOURS),
        maximum_event_count=10,
        normalized_recovery_headroom=10.0, normalized_energy_budget=10.0,
        normalized_debt_limit=10.0, terminal_recovery_debt_limit=10.0,
        service_shortfall_tolerance=1.0e-6,
    )


def solve(arm, scn):
    model = build_arm_planning_model(inputs(scn), arm)
    try:
        res = pyo.SolverFactory("highs").solve(model)
    except Exception as exc:                      # no feasible solution
        return "infeasible", None, str(exc)[:60]
    status = str(res.solver.termination_condition)
    if status != "optimal":
        return status, None, None
    return status, pyo.value(model.capacity), None


def classify(grid, cfe):
    """R1 no conflict / R2 double commitment / R3 common insufficiency.

    The final hour carries no request: the model requires the event to be inactive at
    `horizon - 1` (terminal_event_inactive), so a positive last-hour request is
    structurally infeasible regardless of the pool. The band is therefore built on
    hours 0..HOURS-2.
    """
    g = tuple(float(grid) for _ in range(HOURS - 1)) + (0.0,)
    c = tuple(float(cfe) for _ in range(HOURS - 1)) + (0.0,)
    net = solve(NETWORK_ONLY_SHARED, scenario(g, c, (POOL,) * HOURS))
    cfe_only = solve(CFE_ONLY_SHARED, scenario(g, c, (POOL,) * HOURS))
    joint = solve(JOINT_CORRECT_SHARED, scenario(g, c, (POOL,) * HOURS))
    return net, cfe_only, joint


def main():
    print(f"shared pool P = {POOL} per hour, {HOURS} hours")
    print()
    print(f"{'case':28s} {'grid':>6s} {'cfe':>6s}  network  cfe-only  joint   verdict")
    print("-" * 88)
    cases = [
        ("R2 band: each alone fits", 0.9, 0.9),
        ("R2 band, asymmetric", 0.8, 0.5),
        ("R1: nothing needed", 0.0, 0.0),
        ("R3: grid alone too big", 1.6, 0.1),
        ("R3: cfe alone too big", 0.1, 1.6),
        ("R3: both far too big", 1.2, 1.2),
        ("edge: grid exactly P", 1.0, 0.1),
        ("edge: sum exactly P", 0.6, 0.4),
    ]
    rows = []
    for name, g, c in cases:
        net, cfe_only, joint = classify(g, c)
        ok = lambda r: "opt" if r[0] == "optimal" else r[0][:8]
        net_ok = net[0] == "optimal"
        cfe_ok = cfe_only[0] == "optimal"
        joint_ok = joint[0] == "optimal"
        if net_ok and cfe_ok and not joint_ok:
            verdict = "R2 (double commitment)"
        elif not net_ok or not cfe_ok:
            verdict = "R3 (common insufficiency)"
        elif joint_ok:
            verdict = "R1 (no conflict)"
        else:
            verdict = "?"
        rows.append((name, g, c, net, cfe_only, joint, verdict))
        print(f"{name:28s} {g:6.2f} {c:6.2f}  {ok(net):>7s}  {ok(cfe_only):>7s}  "
              f"{ok(joint):>6s}  {verdict}")
    print()
    r2 = [r for r in rows if r[6].startswith("R2")]
    print(f"cases classified R2: {len(r2)} / {len(rows)}")
    if r2:
        print("VERDICT: the model does detect the double-commitment band.")
        print("The frozen R2=0 count is therefore a property of the 70-cell data,")
        print("not of the classifier: no cell fell inside the band.")
    else:
        print("VERDICT: the model failed to detect a hand-built R2 band -- fix before use.")


if __name__ == "__main__":
    main()
