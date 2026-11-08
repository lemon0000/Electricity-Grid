"""Minimum business-flexibility pool: do the three evaluation methods disagree?

DRAFT_NONAUTHORITATIVE. A feasibility probe, not a result.

The question
------------
Under the three-stage-misalignment setup, ask of each evaluation method: what is the
smallest business-flexibility pool (the share of deferrable compute) under which this
plan is judged deliverable? If the three methods return different minimums, the gap is
the decision consequence -- a planner screening with a simplified check under-provisions
flexibility and defaults after ramp-up.

This is NOT DC02's defer/shift scheduling problem (they optimise how work is moved) and
NOT DC22's grid-side capacity sizing (they optimise POI import plus onsite PV/BESS).
The decision variable here is the data centre's own flexibility pool.

Decision variable
-----------------
`flexible_fraction`: the share of each hour's workload the operator commits to defer.
To keep it binding, `capacity` (the absolute deferral cap) is raised above
`workload * flexible_fraction` for the whole search, so the min() in `advance()` is set
by the fraction rather than by the absolute cap.

Method
------
Bisection on `flexible_fraction` in [0, 1] for each method, using its own verdict rule.
Tolerance 1/200 -- the quantity is a planning share, not a physical measurement.
"""
from __future__ import annotations

import dataclasses
import json
import sys
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.staged_deliverability_d_grid_v2 import load_grid_case  # noqa: E402
from src.staged_deliverability_development_v1 import (  # noqa: E402
    assessment, execute, ZERO,
)

CFG = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"
METHODS = ("instantaneous", "fixed_headroom", "full_temporal")
CELLS = [("fast", "on_time", "early"), ("fast", "on_time", "late"),
         ("slow", "on_time", "early"), ("slow", "delayed", "early")]
TOL = Q(1, 200)


def verdict(params, observations, method, fraction):
    """Evaluate one cell with a given flexibility fraction; keep capacity non-binding."""
    obs = tuple(dataclasses.replace(o, flexible_fraction=fraction) for o in observations)
    # Raise the absolute deferral cap well above the fractional bound so that the min()
    # in advance() is decided by flexible_fraction, not by p.capacity.
    peak = max(o.workload for o in observations) * fraction
    p = dataclasses.replace(params, capacity=max(params.capacity, peak * Q(2)))
    state = execute(p, obs, method, "probe")
    return assessment(state)["method_conditions_satisfied"]


def min_fraction(params, observations, method):
    """Smallest flexible_fraction at which the method judges the plan deliverable."""
    lo, hi = ZERO, Q(1)
    if verdict(params, observations, method, hi) is not True:
        return None                      # not deliverable even at full flexibility
    if verdict(params, observations, method, lo) is True:
        return lo                        # deliverable with no flexibility at all
    while hi - lo > TOL:
        mid = (lo + hi) / 2
        v = verdict(params, observations, method, mid)
        if v is True:
            hi = mid
        elif v is False:
            lo = mid
        else:
            return None                  # undetermined: right-censored coverage
    return hi


def main():
    out = {"authority": "DRAFT_NONAUTHORITATIVE",
           "scope": "min_business_flexibility_probe_v1",
           "decision_variable": "flexible_fraction",
           "tolerance": str(TOL),
           "formal_result": False, "resource_admission": False,
           "cells": []}
    for business, plan, clean in CELLS:
        params, observations = load_grid_case(CFG, business, plan, clean)
        row = {"cell": f"{business}/{plan}/{clean}", "min_fraction": {}}
        for method in METHODS:
            row["min_fraction"][method] = str(min_fraction(params, observations, method))
        vals = [row["min_fraction"][m] for m in METHODS]
        # "None" means no fraction in [0, 1] makes the method pass. It is not a missing
        # value: a numeric minimum next to None is the strongest possible disagreement.
        numeric = sorted({Q(v) for v in vals if v != "None"})
        if "None" in vals and numeric:
            row["class"] = "no_fraction_suffices_for_stricter_method"
        elif len(numeric) > 1:
            row["class"] = "continuous_gap"
        elif numeric:
            row["class"] = "same_threshold"
        else:
            row["class"] = "no_method_passes"
        out["cells"].append(row)
        print(f"{row['cell']:26s} instantaneous={vals[0]:>8s} "
              f"fixed={vals[1]:>8s} full={vals[2]:>8s} class={row['class']}")

    classes = {c["class"] for c in out["cells"]}
    out["verdict"] = sorted(classes)
    print()
    print("VERDICT classes:", sorted(classes))

    attempt = sys.argv[1] if len(sys.argv) > 1 else "attempt_02"
    target = ROOT / "results/tables/min_flexibility_probe_v1_non_authoritative" / attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)
    (target / "report.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    import hashlib
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")


if __name__ == "__main__":
    main()
