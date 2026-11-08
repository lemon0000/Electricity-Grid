"""Minimum capacity probe: do the three evaluation methods imply different capacity?

DRAFT_NONAUTHORITATIVE. A feasibility probe, not a result.

The question
------------
Under the three-stage-misalignment setup, if we ask "what is the minimum接入容量that
makes this plan deliverable under method X?", do the three methods give different
answers? If they do, the gap is the decision consequence: using a simplified check
underspecifies capacity and leads the planner to underprovision.

This is NOT the defer/shift scheduling problem (DC02 territory). It is the inverse
deliverability problem: given plan and policy, find the minimum capacity/投运时点/
recovery budget.

Setup
-----
Take one D grid cell (fast/on_time/early). The frozen base config sets capacity and
other parameters. We binary-search for the minimum scale factor `s` such that
method(s × capacity) judges the plan deliverable.

- instantaneous: ignores recovery, should need low capacity
- fixed_headroom: uses constant recovery, should need medium
- full_temporal: uses complete temporal recovery, should need high

If all three methods return the same minimum capacity, this angle has zero value.

Scope: a single cell, a single decision dimension (capacity scaling), no求解器.
"""
from __future__ import annotations

import sys
from fractions import Fraction as Q
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.staged_deliverability_d_grid_v2 import load_grid_case  # noqa: E402
from src.staged_deliverability_development_v1 import (  # noqa: E402
    execute, assessment, Parameters,
)
import dataclasses  # noqa: E402


def with_capacity_scale(params: Parameters, scale: Q):
    """Scale deferral capacity and related envelopes."""
    return dataclasses.replace(
        params,
        capacity=params.capacity * scale,
        max_recovery=params.max_recovery * scale,
        max_debt=params.max_debt * scale,
        max_call_energy=params.max_call_energy * scale,
    )


def binary_search_min_scale(params, observations, method, target=True, lo=Q(1, 10),
                             hi=Q(10), tol=Q(1, 100)):
    """Find minimum scale `s` such that method(s × params) achieves `target` verdict."""
    # Check bounds.
    p_lo = with_capacity_scale(params, lo)
    st_lo = execute(p_lo, observations, method, "probe")
    verdict_lo = assessment(st_lo)["method_conditions_satisfied"]
    if verdict_lo == target:
        return lo  # already satisfied at lo

    p_hi = with_capacity_scale(params, hi)
    st_hi = execute(p_hi, observations, method, "probe")
    verdict_hi = assessment(st_hi)["method_conditions_satisfied"]
    if verdict_hi != target:
        return None  # not satisfied even at hi

    # Binary search.
    while hi - lo > tol:
        mid = (lo + hi) / 2
        p_mid = with_capacity_scale(params, mid)
        st = execute(p_mid, observations, method, "probe")
        verdict = assessment(st)["method_conditions_satisfied"]
        if verdict == target:
            hi = mid
        else:
            lo = mid
    return hi


def main():
    cfg = "configs/staged_deliverability_d_v1.DRAFT.yaml"
    params, obs = load_grid_case(cfg, "fast", "on_time", "early")
    print("Base capacity:", params.capacity, "max_recovery:", params.max_recovery)
    print()
    results = {}
    for method in ("instantaneous", "fixed_headroom", "full_temporal"):
        scale = binary_search_min_scale(params, obs, method)
        results[method] = scale
        print(f"{method:20s} min_scale = {scale}")
    print()
    if results["instantaneous"] == results["fixed_headroom"] == results["full_temporal"]:
        print("VERDICT: all three give the same minimum capacity → zero gap, no value")
    else:
        vals = sorted((float(v) if v else float("inf")) for v in results.values())
        gap = vals[-1] - vals[0] if len(vals) >= 2 else 0.0
        print(f"VERDICT: methods differ, max gap = {gap:.2f}× base capacity")
        print("This means simplified checks underprovision接入容量.")


if __name__ == "__main__":
    main()
