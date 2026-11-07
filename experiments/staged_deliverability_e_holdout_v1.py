"""E independent holdout: run the frozen D comparison on paths D never saw.

DRAFT_NONAUTHORITATIVE. Zero solver calls, zero external downloads.

Why this exists
---------------
D attempt_01 and the sensitivity scan both vary parameters on one fixture skeleton:
same `first_hour`/`last_hour`, same equipment path, same grid lead times, and clean
paths that differ only in where two entries are swapped. A reviewer can fairly ask
whether the false-pass result belongs to that skeleton or to the simplifying
evaluation in general.

E answers one question: on exogenous paths D never saw, do the frozen plan, equipment
and policy still produce the same class of divergence? It adds no method, changes no
criterion and re-selects no parameter.

Holdout levels (fixed before any E result exists, see the contract §2)
----------------------------------------------------------------------
- business ramp at `change_hour` 1 and 4          (D used 2, 3, 5)
- grid delay 1 and 3                               (D used 0 and 2)
- two clean paths matched to *each other* in total and peak, not to D, because the
  window is longer; `holdout_a` puts the single high-clean hour late, `holdout_b`
  early, so the arrival time is genuinely new while the total is held.
- window `last_hour` 9                             (D used 7), `first_hour` -2 and
  `deadline_lag` 2 unchanged.

Everything else -- physical parameters, equipment path, grid lead and start, the three
methods and their criteria -- is copied unchanged from the D fixture.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import sys

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.staged_deliverability_d_grid_v2 import (  # noqa: E402
    load_grid_case, run_matrix, summarize,
)

BASE_FIXTURE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"
ROOT_OUT = ROOT / "results/tables/staged_deliverability_e_holdout_v1_non_authoritative"
# Bytes this runner actually executes, pinned into every report so an E result can be
# traced back to the code that produced it. Without this the report records only the
# fixture, and a later source change would be invisible.
SOURCES = (
    "experiments/staged_deliverability_e_holdout_v1.py",
    "src/staged_deliverability_d_grid_v2.py",
    "src/staged_deliverability_replay_v2.py",
    "src/staged_deliverability_development_v1.py",
)

# Declared holdout set. Each level is absent from D attempt_01 and from the
# sensitivity axes f/K/alpha, which moved parameters rather than exogenous paths.
CHANGE_HOURS = (1, 4)          # D business paths use 2, 3, 5
GRID_DELAYS = (1, 3)           # D grid delays are 0 (on_time) and 2 (delayed)
LAST_HOUR = 9                  # D window ends at 7
FIRST_HOUR = -2
DEADLINE_LAG = 2

# Two clean paths matched to each other: both total 401/50 and peak 26/25, but the
# single high-clean hour sits at h8 in `a` and h2 in `b`. h0/h1 match D so the
# structural low-clean hour that caps alpha at 4/5 is preserved.
#
# Post-ramp hours must stay at or above alpha * reference = 4/5 * 21/20 = 21/25 = .84.
# A lower value makes `hourly_cfe` bind in every post-ramp hour, all three methods fail
# together and the holdout degenerates (attempt_02: 7 of 8 cells all-D4 for exactly this
# reason). D's paths satisfy the bound by construction; E only moves the raised hour.
CLEAN_PATHS = {
    "holdout_a": [".60", ".50", ".84", ".84", ".84", ".84", ".84", ".84", "1.04", ".84"],
    "holdout_b": [".60", ".50", "1.04", ".84", ".84", ".84", ".84", ".84", ".84", ".84"],
}

# Evaluation window for the extended horizon. The D defaults (4/7) would mark every
# E cell right-censored, so they are passed explicitly from here on.
REGISTRATION_END = 5
EXPECTED_LAST_HOUR = LAST_HOUR


def _tag(value):
    return str(value).replace("/", "of")


def variant_name(change_hour, delay, clean):
    return f"c{change_hour}__d{delay}__{clean}"


def patch_config(base, change_hour, delay, clean):
    """Return the holdout fixture: exogenous paths only, physical parameters untouched.

    The loader requires the schema keys `baseline/fast/slow` and `early/late` to exist,
    so the holdout level is written *into* those keys rather than collapsing them. Each
    cell then reads one of them (`fast`, `on_time`, `early`); the duplicates are the same
    level so a mis-selected key cannot silently fall back to a D value.
    """
    cfg = deepcopy(base)
    cfg["first_hour"] = FIRST_HOUR
    cfg["last_hour"] = LAST_HOUR
    cfg["deadline_lag"] = DEADLINE_LAG
    holdout_path = {"before": "1/2", "after": "7/10", "change_hour": change_hour}
    cfg["business_paths"] = {name: dict(holdout_path)
                             for name in ("baseline", "fast", "slow")}
    cfg["grid"]["delays"] = {"on_time": delay, "delayed": delay}
    cfg["clean_paths"] = {name: list(CLEAN_PATHS[clean]) for name in ("early", "late")}
    return cfg


def phase_screen(cfg, params, observations):
    """Hours at which no policy could serve the hour's total request.

    `room` is bounded by the loosest call bound any method uses --
    `min(capacity, workload * flexible_fraction, workload)`; the approximate methods
    only tighten it further. If `grid/slope + green/slope` exceeds that bound, every
    method fails for a structural reason and the cell says nothing about the
    simplifications. Mirrors the `structurally_infeasible` screen of the sensitivity
    scan: it is label-independent, computed before any label is read, and marks cells
    rather than dropping them.

    attempt_03 exposed why this matters: `change_hour = 1` puts the business ramp on
    the grid's temporary-limit hour, where supply is `5/8`, so the request is `3/5`
    against a room of `1/5` and all four such cells were all-D4.
    """
    from src.staged_deliverability_development_v1 import power_mapping, ZERO

    blocked = []
    for observation in observations:
        _, _, reference = power_mapping(params, observation)
        grid = max(reference - observation.supply_mw, ZERO)
        green = (max(reference - observation.clean_mwh / params.alpha, ZERO)
                 if params.alpha else ZERO)
        needed = grid / params.slope + green / params.slope
        room = min(params.capacity, observation.workload * observation.flexible_fraction,
                   observation.workload)
        if needed > room:
            blocked.append(dict(hour=observation.hour, needed=str(needed), room=str(room)))
    return blocked


def pin(path: Path) -> dict:
    data = path.read_bytes()
    try:
        shown = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        shown = path.resolve().as_posix()
    return {"path": shown, "bytes": len(data), "sha256": sha256(data).hexdigest()}


def holdout_checks(cfg, base):
    """E1/E2: the paths are new, and nothing frozen moved."""
    problems = []
    base_map = {p["change_hour"] for p in base["business_paths"].values()}
    for path in cfg["business_paths"].values():
        if path["change_hour"] in base_map:
            problems.append(f"ramp hour {path['change_hour']} already appears in D")
    for delay in cfg["grid"]["delays"].values():
        if delay in set(base["grid"]["delays"].values()):
            problems.append(f"grid delay {delay} already appears in D")
    for name, values in cfg["clean_paths"].items():
        if values in [list(v) for v in base["clean_paths"].values()]:
            problems.append(f"clean path {name} duplicates a D path")
    if cfg["last_hour"] == base["last_hour"]:
        problems.append("window length equals D")
    for key, value in base["parameters"].items():
        if cfg["parameters"][key] != value:
            problems.append(f"parameter {key} moved")
    if cfg["equipment"] != base["equipment"]:
        problems.append("equipment path moved")
    if cfg["grid"]["lead"] != base["grid"]["lead"] or cfg["grid"]["start"] != base["grid"]["start"]:
        problems.append("grid lead/start moved")
    if cfg["deadline_lag"] != base["deadline_lag"]:
        problems.append("deadline lag moved")
    return problems


def clean_path_stats(values):
    path = [Q(v) for v in values]
    return dict(total=str(sum(path)), peak=str(max(path)),
                peak_hours=[i for i, v in enumerate(path) if v == max(path)])


def scan(base_fixture: Path, target: Path) -> tuple[list[dict], list[dict], list[str]]:
    base = yaml.safe_load(base_fixture.read_text(encoding="utf-8"))
    fixtures = target / "fixtures"
    fixtures.mkdir(exist_ok=True)

    cells, all_rows, problems = [], [], []
    for clean in CLEAN_PATHS:
        for change_hour in CHANGE_HOURS:
            for delay in GRID_DELAYS:
                name = variant_name(change_hour, delay, clean)
                path = fixtures / f"{name}.yaml"
                cfg = patch_config(base, change_hour, delay, clean)
                problems.extend(f"{name}: {p}" for p in holdout_checks(cfg, base))
                path.write_text(
                    yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True,
                                   default_flow_style=False),
                    encoding="utf-8")
                # Label-independent screen, computed before any label is read.
                probe_params, probe_obs = load_grid_case(path, "fast", "on_time", "early")
                blocked = phase_screen(cfg, probe_params, probe_obs)
                rows = run_matrix(path, businesses=("fast",), grid_paths=("on_time",),
                                  clean_paths=("early",),
                                  registration_end=REGISTRATION_END,
                                  expected_last_hour=EXPECTED_LAST_HOUR)
                summary = summarize(rows)
                for row in rows:
                    row.update(variant=name, change_hour=change_hour, grid_delay=delay,
                               clean_variant=clean,
                               structurally_infeasible=bool(blocked))
                all_rows.extend(rows)
                cells.append(dict(
                    variant=name, change_hour=change_hour, grid_delay=delay,
                    clean_variant=clean,
                    clean_stats=clean_path_stats(CLEAN_PATHS[clean]),
                    fixture=pin(path),
                    blocked_hours=blocked,
                    structurally_infeasible=bool(blocked),
                    evaluations=summary["total"],
                    replay=summary["counts"],
                    strategy=summary["strategy_counts"],
                    false_pass_any=(summary["counts"]["D1_false_pass"] > 0
                                    or summary["strategy_counts"]["D1_false_pass"] > 0),
                ))
    return cells, all_rows, problems


def aggregate(cells):
    if not cells:
        raise ValueError("nonempty cells required")
    informative = [c for c in cells if not c["structurally_infeasible"]]

    def _sums(subset):
        if not subset:
            return None
        return dict(
            cells=len(subset),
            cells_with_false_pass=sum(1 for c in subset if c["false_pass_any"]),
            replay_D1_total=sum(c["replay"]["D1_false_pass"] for c in subset),
            strategy_D1_total=sum(c["strategy"]["D1_false_pass"] for c in subset),
            replay_D1_max=max(c["replay"]["D1_false_pass"] for c in subset),
            replay_D1_min=min(c["replay"]["D1_false_pass"] for c in subset),
            any_D2=any(c["replay"]["D2_false_reject"] or c["strategy"]["D2_false_reject"]
                       for c in subset),
            any_D5=any(c["replay"]["D5_undetermined"] or c["strategy"]["D5_undetermined"]
                       for c in subset),
        )

    return dict(
        cells=len(cells),
        informative_cells=len(informative),
        structurally_infeasible_cells=len(cells) - len(informative),
        cells_with_false_pass=sum(1 for c in cells if c["false_pass_any"]),
        replay_D1_total=sum(c["replay"]["D1_false_pass"] for c in cells),
        strategy_D1_total=sum(c["strategy"]["D1_false_pass"] for c in cells),
        replay_D1_max=max(c["replay"]["D1_false_pass"] for c in cells),
        replay_D1_min=min(c["replay"]["D1_false_pass"] for c in cells),
        any_D2=any(c["replay"]["D2_false_reject"] or c["strategy"]["D2_false_reject"]
                   for c in cells),
        any_D5=any(c["replay"]["D5_undetermined"] or c["strategy"]["D5_undetermined"]
                   for c in cells),
        informative=_sums(informative),
        by_change_hour={str(h): {k: sum(c["replay"][k] for c in cells if c["change_hour"] == h)
                                 for k in ("D1_false_pass", "D2_false_reject",
                                           "D3_agree_pass", "D4_agree_fail", "D5_undetermined")}
                        for h in CHANGE_HOURS},
        by_grid_delay={str(d): {k: sum(c["replay"][k] for c in cells if c["grid_delay"] == d)
                                for k in ("D1_false_pass", "D2_false_reject",
                                          "D3_agree_pass", "D4_agree_fail", "D5_undetermined")}
                       for d in GRID_DELAYS},
        by_clean={name: {k: sum(c["replay"][k] for c in cells if c["clean_variant"] == name)
                         for k in ("D1_false_pass", "D2_false_reject",
                                   "D3_agree_pass", "D4_agree_fail", "D5_undetermined")}
                  for name in CLEAN_PATHS},
        interpretation=("counts cover the declared holdout only; they are not summed with "
                        "D or the sensitivity scan, and a cell without a false pass is "
                        "reported as such. `informative` excludes cells where the "
                        "label-independent screen found an hour no policy could serve."),
    )


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--attempt", default="attempt_01")
    parser.add_argument("--fixture", type=Path, default=BASE_FIXTURE)
    args = parser.parse_args(argv)

    target = ROOT_OUT / args.attempt
    if target.exists():
        raise SystemExit(f"refusing to overwrite existing attempt: {target}")
    target.mkdir(parents=True)

    started = datetime.now(timezone.utc)
    cells, rows, problems = scan(args.fixture, target)
    summary = aggregate(cells)

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_e_holdout_v1",
        "created_utc": started.isoformat(),
        "formal_result": False, "resource_admission": False,
        "security_certified": False, "aggregate_contract_release": False,
        "solver_calls": 0, "external_downloads": 0,
        "base_fixture": pin(args.fixture),
        "sources": [pin(ROOT / name) for name in SOURCES],
        "holdout_axes": {"change_hour": list(CHANGE_HOURS),
                         "grid_delay": list(GRID_DELAYS),
                         "clean_paths": {k: list(v) for k, v in CLEAN_PATHS.items()},
                         "last_hour": LAST_HOUR,
                         "registration_end": REGISTRATION_END,
                         "expected_last_hour": EXPECTED_LAST_HOUR},
        "holdout_problems": problems,
        "summary": summary,
        "cells": cells,
        "rows": rows,
    }
    (target / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        sha256((target / "report.json").read_bytes()).hexdigest() + "\n", encoding="utf-8")

    print(json.dumps({"cells": summary["cells"],
                      "with_false_pass": summary["cells_with_false_pass"],
                      "replay_D1_range": [summary["replay_D1_min"], summary["replay_D1_max"]],
                      "any_D2": summary["any_D2"], "any_D5": summary["any_D5"],
                      "holdout_problems": problems}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
