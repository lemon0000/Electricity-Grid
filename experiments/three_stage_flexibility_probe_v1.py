"""Three-stage misalignment probe: minimum flexibility pool under staggered ramp-up.

DRAFT_NONAUTHORITATIVE. A feasibility probe, not a result.

Why this exists
---------------
The earlier `min_flexibility_probe_v1` ran on the D fixture, whose 10-hour window cannot
hold three misaligned stages. It found no gap in the depth dimension (flexible_fraction)
because every method saw the same single hour of shortfall.

This probe lengthens the window and staggers the three progress lines independently:

  business ramp  -- when the IT load steps up
  equipment      -- when the second compute batch is commissioned
  grid expansion -- when the interconnection limit steps up

so that there are hours where the load has ramped but the grid has not, and the
equipment that could absorb recovery work is not yet online. Those "collision windows"
are what the simplified methods are supposed to miss.

Decision variable
-----------------
`flexible_fraction`: the share of each hour's workload the operator commits to defer.
`capacity` is held above `workload * flexible_fraction` so the fraction is the binding
term in `advance()`'s min().

Method
------
For each of several staggers, bisect on `flexible_fraction` per method and record the
smallest value at which that method judges the plan deliverable. A method that never
passes across [0,1] is recorded as None -- that is the strongest disagreement, not a
missing value.
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
from src.staged_deliverability_development_v1 import assessment, execute, ZERO  # noqa: E402

OUT = ROOT / "results/tables/three_stage_flexibility_probe_v1_non_authoritative"
METHODS = ("instantaneous", "fixed_headroom", "full_temporal")
TOL = Q(1, 100)

BASE = {
    "status": "DRAFT_NONAUTHORITATIVE",
    "source_class": "mechanism_assumption",
    "first_hour": -2,
    "last_hour": 21,
    "deadline_lag": 3,
    "flexible_fraction": "2/5",
    "prehistory_clean": "3/5",
    "parameters": {
        "capacity": "1/5", "alpha": "4/5", "eta": "1", "beta": "1",
        "facility_factor": "5/4", "auxiliary_mw": "1/40", "fixed_headroom": "1/5",
        "max_recovery": "1/5", "max_debt": "2/5", "max_call_energy": "2/5",
        "call_ramp": "1/5", "max_events": 8, "max_duration": 4, "minimum_rest": 0,
    },
    "business_paths": {
        "baseline": {"before": "1/2", "after": "7/10", "change_hour": 3},
        "fast": {"before": "1/2", "after": "7/10", "change_hour": 2},
        "slow": {"before": "1/2", "after": "7/10", "change_hour": 5},
    },
    "grid": {"start": 0, "lead": 2, "delays": {"on_time": 0, "delayed": 2},
             "before": "4/5", "after": "13/10",
             "temporary_hour": 1, "temporary_limit": "5/8"},
    "clean_paths": {
        "early": [".60", ".50"] + [".84"] * 20,
        "late": [".60", ".50"] + [".84"] * 20,
    },
}


def make_fixture(target: Path, *, ramp_hour, equip_start, equip_lead, grid_lead,
                 grid_delay, clean_high_hours):
    """Stagger the three lines independently and write the fixture."""
    cfg = json.loads(json.dumps(BASE))          # deep copy
    for path in cfg["business_paths"].values():
        path["change_hour"] = ramp_hour
    cfg["equipment"] = [
        {"id": "first_batch", "capacity": "4/5", "idle_mw": "2/25",
         "start": -2, "lead": 0, "delay": 0},
        {"id": "second_batch", "capacity": "2/5", "idle_mw": "1/25",
         "start": equip_start, "lead": equip_lead, "delay": 0},
    ]
    cfg["grid"]["lead"] = grid_lead
    cfg["grid"]["delays"] = {"on_time": grid_delay, "delayed": grid_delay}
    # The single high-clean hour is the only source of recovery headroom.
    for name in cfg["clean_paths"]:
        path = [".60", ".50"] + [".84"] * 20
        for h in clean_high_hours:
            path[h] = "1.04"
        cfg["clean_paths"][name] = path
    target.write_text(yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
                      encoding="utf-8")
    return cfg


def verdict(path, business, fraction, method, registration_end, expected_last_hour):
    params, observations = load_grid_case(path, business, "on_time", "early")
    obs = tuple(dataclasses.replace(o, flexible_fraction=fraction) for o in observations)
    peak = max(o.workload for o in observations) * fraction
    p = dataclasses.replace(params, capacity=max(params.capacity, peak * Q(2)))
    state = execute(p, obs, method, "probe")
    return assessment(state, registration_end, expected_last_hour)["method_conditions_satisfied"]


def min_fraction(path, business, method, registration_end, expected_last_hour):
    lo, hi = ZERO, Q(1)
    if verdict(path, business, hi, method, registration_end, expected_last_hour) is not True:
        return None
    if verdict(path, business, lo, method, registration_end, expected_last_hour) is True:
        return lo
    while hi - lo > TOL:
        mid = (lo + hi) / 2
        v = verdict(path, business, mid, method, registration_end, expected_last_hour)
        if v is True:
            hi = mid
        elif v is False:
            lo = mid
        else:
            return None
    return hi


def main(argv=None) -> int:
    attempt = (argv or sys.argv[1:] or ["attempt_01"])[0]
    target = OUT / attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)
    fixtures = target / "fixtures"
    fixtures.mkdir()

    # Staggers: business ramp, equipment commissioning, grid expansion, clean peak hour.
    # Each row is a different way the three lines can be out of step.
    staggers = [
        dict(name="aligned", ramp_hour=3, equip_start=0, equip_lead=2,
             grid_lead=2, grid_delay=0, clean_high_hours=[6]),
        dict(name="grid_late", ramp_hour=3, equip_start=0, equip_lead=2,
             grid_lead=6, grid_delay=0, clean_high_hours=[6]),
        dict(name="equip_late", ramp_hour=3, equip_start=4, equip_lead=4,
             grid_lead=2, grid_delay=0, clean_high_hours=[6]),
        dict(name="both_late", ramp_hour=2, equip_start=6, equip_lead=4,
             grid_lead=6, grid_delay=2, clean_high_hours=[14]),
        dict(name="clean_early_only", ramp_hour=2, equip_start=3, equip_lead=3,
             grid_lead=4, grid_delay=1, clean_high_hours=[2]),
        dict(name="clean_late_only", ramp_hour=2, equip_start=3, equip_lead=3,
             grid_lead=4, grid_delay=1, clean_high_hours=[16]),
    ]

    out = {"authority": "DRAFT_NONAUTHORITATIVE",
           "scope": "three_stage_flexibility_probe_v1",
           "decision_variable": "flexible_fraction",
           "tolerance": str(TOL),
           "formal_result": False, "resource_admission": False,
           "window": {"first_hour": BASE["first_hour"], "last_hour": BASE["last_hour"],
                      "deadline_lag": BASE["deadline_lag"]},
           "registration_end": 8, "expected_last_hour": 21,
           "staggers": []}

    for stagger in staggers:
        name = stagger.pop("name")
        path = fixtures / f"{name}.yaml"
        make_fixture(path, **stagger)
        row = {"stagger": name, **stagger, "min_fraction": {}}
        for method in METHODS:
            row["min_fraction"][method] = str(
                min_fraction(path, "fast", method, 8, 21))
        vals = [row["min_fraction"][m] for m in METHODS]
        numeric = sorted({Q(v) for v in vals if v != "None"})
        if "None" in vals and numeric:
            row["class"] = "no_fraction_suffices"
        elif len(numeric) > 1:
            row["class"] = "continuous_gap"
        elif numeric:
            row["class"] = "same_threshold"
        else:
            row["class"] = "no_method_passes"
        out["staggers"].append(row)
        print(f"{name:18s} inst={vals[0]:>7s} fixed={vals[1]:>7s} "
              f"full={vals[2]:>7s}  {row['class']}")

    classes = sorted({r["class"] for r in out["staggers"]})
    out["verdict"] = classes
    print("\nverdict classes:", classes)

    (target / "report.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        hashlib.sha256((target / "report.json").read_bytes()).hexdigest() + "\n",
        encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
