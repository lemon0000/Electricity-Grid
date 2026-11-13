"""Minimum flexibility fraction as a function of three-stage misalignment.

DRAFT_NONAUTHORITATIVE. A feasibility probe, not a result.

Design rules (fixed before the run)
-----------------------------------
Window 30 h. Workload steps from `before` to `after` at hour R; supply steps from
`before` to `after` at hour S. Clean budget is set to `alpha * reference` every hour, so
the clean request is identically zero and the problem is isolated to the grid side.

Misalignment means R < S: the business has ramped but the grid expansion has not landed,
which opens a collision window [R, S). When R >= S the grid is ready first and there is
no window.

Why the earlier probe was wrong
-------------------------------
`min_flexibility_probe_v1` and `three_stage_flexibility_probe_v1` both ran on the D
fixture, which has exactly one hour of grid shortfall (h1's temporary limit). That hour
is a fixed constant unrelated to how the three lines stagger, so every stagger returned
the same threshold. The single fixed hour masked the misalignment effect entirely.

`flexible_fraction` enters the model only through
`room = min(capacity, workload * f, ...)` in `advance()`. Therefore the depth needed has a
closed form,

    f_min = max over hours of  shortfall_h / (slope * workload_h)

and this probe reports both that analytic value and the verdict scan, so the two can be
checked against each other.

What is scanned
---------------
For each stagger, `f` runs 0 -> 1 in 1/32 steps and every method's verdict is recorded.
That exposes not only the smallest `f` that passes but also whether any method has an
UPPER limit (deferring more creates debt it cannot repay within the envelope).
"""
from __future__ import annotations

import dataclasses
import hashlib
import json
import sys
from fractions import Fraction as Q
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.staged_deliverability_d_grid_v2 import load_grid_case  # noqa: E402
from src.staged_deliverability_development_v1 import (  # noqa: E402
    assessment, execute, power_mapping, ZERO,
)

OUT = ROOT / "results/tables/min_fraction_misalignment_v1_non_authoritative"
METHODS = ("instantaneous", "fixed_headroom", "full_temporal")
STEPS = 32
HOURS = 30

BASE = {
    "status": "DRAFT_NONAUTHORITATIVE",
    "source_class": "mechanism_assumption",
    "first_hour": 0,
    "last_hour": HOURS - 1,
    "deadline_lag": 3,
    "flexible_fraction": "2/5",
    "prehistory_clean": "3/5",
    "parameters": {
        "capacity": "1/5", "alpha": "4/5", "eta": "1", "beta": "1",
        "facility_factor": "5/4", "auxiliary_mw": "1/40", "fixed_headroom": "1/5",
        "max_recovery": "1/5", "max_debt": "2/5", "max_call_energy": "2/5",
        "call_ramp": "1/5", "max_events": 12, "max_duration": 6, "minimum_rest": 0,
    },
    "business_paths": {
        "baseline": {"before": "1/2", "after": "7/10", "change_hour": 8},
        "fast": {"before": "1/2", "after": "7/10", "change_hour": 8},
        "slow": {"before": "1/2", "after": "7/10", "change_hour": 8},
    },
    "equipment": [
        {"id": "first_batch", "capacity": "4/5", "idle_mw": "2/25",
         "start": 0, "lead": 0, "delay": 0},
        {"id": "second_batch", "capacity": "2/5", "idle_mw": "1/25",
         "start": 0, "lead": 0, "delay": 0},
    ],
    "grid": {"start": 0, "lead": 0, "delays": {"on_time": 0, "delayed": 0},
             "before": "4/5", "after": "13/10",
             "temporary_hour": -999, "temporary_limit": "99"},
    "clean_paths": {"early": [], "late": []},
}

FF = Q(5, 4)
AUX = Q(1, 40)
IDLE = Q(2, 25) + Q(1, 25)


def reference_of(workload):
    return FF * (IDLE + workload) + AUX


def build_fixture(target: Path, *, ramp_hour, expand_hour):
    """Workload steps at `ramp_hour`, supply at `expand_hour`, clean pinned to zero request."""
    cfg = json.loads(json.dumps(BASE))
    for path in cfg["business_paths"].values():
        path["change_hour"] = ramp_hour
    cfg["grid"]["lead"] = 0
    # A single supply step at `expand_hour` is expressed by making the grid commission
    # then: start + lead + delay = expand_hour.
    cfg["grid"]["start"] = expand_hour

    path = []
    for hour in range(HOURS):
        workload = Q(1, 2) if hour < ramp_hour else Q(7, 10)
        path.append(str(reference_of(workload) * Q(4, 5)))
    for name in cfg["clean_paths"]:
        cfg["clean_paths"][name] = path

    target.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
                      encoding="utf-8")
    return cfg


def analytic_min_f(params, observations):
    """Closed form: max over hours of shortfall / (slope * workload)."""
    best = ZERO
    for o in observations:
        _, _, ref = power_mapping(params, o)
        grid = max(ref - o.supply_mw, ZERO)
        green = max(ref - o.clean_mwh / params.alpha, ZERO) if params.alpha else ZERO
        need = (grid + green) / params.slope
        if o.workload:
            best = max(best, need / o.workload)
    return best


def scan_verdicts(path, fraction):
    """Per-method verdict at one flexibility fraction."""
    out = {}
    params, observations = load_grid_case(path, "fast", "on_time", "early")
    obs = tuple(dataclasses.replace(o, flexible_fraction=fraction) for o in observations)
    peak = max(o.workload for o in observations) * fraction
    p = dataclasses.replace(params, capacity=max(params.capacity, peak * Q(2)))
    for method in METHODS:
        state = execute(p, obs, method, "probe")
        verdict = assessment(state)["method_conditions_satisfied"]
        out[method] = verdict
    return out


def main(argv=None) -> int:
    attempt = (argv or sys.argv[1:] or ["attempt_01"])[0]
    target = OUT / attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)
    fixtures = target / "fixtures"
    fixtures.mkdir()

    # (label, ramp_hour, expand_hour): expansion before ramp is "aligned"; after is "misaligned"
    staggers = [
        ("aligned_grid_first", 8, 4),
        ("aligned_same_hour", 8, 8),
        ("gap_2h", 8, 10),
        ("gap_4h", 8, 12),
        ("gap_8h", 8, 16),
        ("gap_16h", 8, 24),
        ("ramp_late", 16, 24),
    ]

    report = {"authority": "DRAFT_NONAUTHORITATIVE",
              "scope": "min_fraction_misalignment_v1",
              "decision_variable": "flexible_fraction",
              "scan_steps": STEPS, "hours": HOURS,
              "formal_result": False, "resource_admission": False,
              "clean_isolated": True,
              "rows": []}

    for label, ramp, expand in staggers:
        path = fixtures / f"{label}.yaml"
        build_fixture(path, ramp_hour=ramp, expand_hour=expand)
        params, observations = load_grid_case(path, "fast", "on_time", "early")
        f_analytic = analytic_min_f(params, observations)

        verdicts = {}
        for step in range(STEPS + 1):
            f = Q(step, STEPS)
            verdicts[str(f)] = scan_verdicts(path, f)

        row = {"label": label, "ramp_hour": ramp, "expand_hour": expand,
               "gap_hours": max(expand - ramp, 0),
               "analytic_min_f": str(f_analytic), "verdicts": verdicts}
        for method in METHODS:
            passing = [Q(f) for f, v in verdicts.items() if v[method] is True]
            row[f"{method}_min"] = str(min(passing)) if passing else None
            row[f"{method}_max"] = str(max(passing)) if passing else None
            row[f"{method}_count"] = len(passing)
        report["rows"].append(row)

        print(f"{label:22s} gap={max(expand-ramp,0):3d}h  analytic_f={float(f_analytic):.3f}  "
              f"inst={row['instantaneous_min'] or '-':>6s}  "
              f"fixed={row['fixed_headroom_min'] or '-':>6s}  "
              f"full={row['full_temporal_min'] or '-':>6s}")

    (target / "report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
