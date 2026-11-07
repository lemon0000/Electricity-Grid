"""D recovery-timing matching arm: same requests, same total and peak, different arrival hour.

DRAFT_NONAUTHORITATIVE. Zero solver calls, zero external downloads.

Why this exists
---------------
Section 6.2 needs a matched comparison: hold the exogenous requests, the clean
allocation total and its peak fixed, and move only *when* the surplus clean hour
arrives. D's `early`/`late` paths do not satisfy that. They share a total (317/50)
and a peak (26/25), but `late` puts clean at 16/25 in h2 while `early` puts 21/25
there, so the CFE request differs (1/4 vs 0). Any verdict difference between the two
is therefore not attributable to arrival time.

This arm builds three paths that do satisfy the input-layer match:

- h0/h1 identical to D (`.60`, `.50`) so the low-clean structural hour is preserved;
- h2..h7 all at `.84`, the value at which the post-ramp CFE request is exactly zero;
- exactly one hour raised to `1.04`, the only source of recovery headroom, placed at
  h3, h4 or h5.

Total (317/50) and peak (26/25) are identical across the three, and the hourly CFE
and grid requests are identical too: the raised hour still requests zero. What moves
is the *physical headroom*, hence when recovery can happen relative to the deadline.
That is the arrival-time-only comparison 6.2 requires.

What this arm does NOT match
----------------------------
Realized deferral and recovery starting debt are policy outcomes, not inputs. They
cannot be fixed by input design, so the match holds at the exogenous layer only. The
contract records this as the "strengthened matching not done" limitation and C2 must
be stated with it.
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
ROOT_OUT = ROOT / "results/tables/staged_deliverability_d_matching_v1_non_authoritative"

# The three arrival positions for the single high-clean hour.
ARRIVAL_HOURS = (3, 4, 5)
BASE_CLEAN = "21/25"   # 0.84: post-ramp CFE request is exactly zero
HIGH_CLEAN = "26/25"   # 1.04: the only hour with recovery headroom
LOW_CLEAN = ("3/5", "1/2")  # h0/h1, identical to D


def clean_path(arrival_hour, last_hour=7):
    path = [LOW_CLEAN[0], LOW_CLEAN[1]]
    path += [HIGH_CLEAN if hour == arrival_hour else BASE_CLEAN
             for hour in range(2, last_hour + 1)]
    return path


def variant_name(arrival_hour):
    return f"arrival_h{arrival_hour}"


def patch_config(base, arrival_hour):
    """Only the clean path's raised hour moves; everything else is D's."""
    cfg = deepcopy(base)
    path = clean_path(arrival_hour, base["last_hour"])
    cfg["clean_paths"] = {name: list(path) for name in base["clean_paths"]}
    return cfg


def profile(observations, params):
    """Hourly CFE and grid requests, to prove the match rather than assert it."""
    from src.staged_deliverability_development_v1 import power_mapping, ZERO

    rows = []
    for observation in observations:
        _, _, reference = power_mapping(params, observation)
        grid = max(reference - observation.supply_mw, ZERO)
        green = (max(reference - observation.clean_mwh / params.alpha, ZERO)
                 if params.alpha else ZERO)
        rows.append((observation.hour, str(grid), str(green)))
    return rows


def match_checks(cfg, base):
    """P3: totals and peaks match across arms; only the raised hour moves."""
    problems = []
    paths = [list(v) for v in cfg["clean_paths"].values()]
    if len(set(map(tuple, paths))) != 1:
        problems.append("clean paths differ between the fixed keys")
    path = [Q(v) for v in paths[0]] if paths else []
    if sum(path) != Q(317, 50):
        problems.append(f"total {sum(path)} != 317/50")
    if max(path) != Q(26, 25):
        problems.append(f"peak {max(path)} != 26/25")
    if [i for i, v in enumerate(path) if v == max(path)].__len__() != 1:
        problems.append("exactly one high hour required")
    if cfg["parameters"] != base["parameters"]:
        problems.append("parameters moved")
    if cfg["equipment"] != base["equipment"]:
        problems.append("equipment moved")
    if cfg["business_paths"] != base["business_paths"]:
        problems.append("business paths moved")
    if cfg["grid"] != base["grid"]:
        problems.append("grid moved")
    return problems


def pin(path: Path) -> dict:
    data = path.read_bytes()
    try:
        shown = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        shown = path.resolve().as_posix()
    return {"path": shown, "bytes": len(data), "sha256": sha256(data).hexdigest()}


def scan(base_fixture: Path, target: Path):
    base = yaml.safe_load(base_fixture.read_text(encoding="utf-8"))
    fixtures = target / "fixtures"
    fixtures.mkdir(exist_ok=True)

    arms, all_rows, problems = [], [], []
    for arrival in ARRIVAL_HOURS:
        name = variant_name(arrival)
        path = fixtures / f"{name}.yaml"
        cfg = patch_config(base, arrival)
        problems.extend(f"{name}: {p}" for p in match_checks(cfg, base))
        path.write_text(
            yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True,
                           default_flow_style=False),
            encoding="utf-8")
        params, observations = load_grid_case(path, "fast", "on_time", "early")
        rows = run_matrix(path)
        summary = summarize(rows)
        for row in rows:
            row.update(arrival_hour=arrival, arm=name)
        all_rows.extend(rows)
        arms.append(dict(
            arm=name, arrival_hour=arrival,
            clean_path=list(cfg["clean_paths"]["early"]),
            request_profile=profile(observations, params),
            fixture=pin(path),
            evaluations=summary["total"],
            replay=summary["counts"],
            strategy=summary["strategy_counts"],
        ))
    return arms, all_rows, problems


def aggregate(arms):
    if not arms:
        raise ValueError("nonempty arms required")
    return dict(
        arms=len(arms),
        by_arrival={str(a["arrival_hour"]): dict(
            replay=a["replay"], strategy=a["strategy"]) for a in arms},
        replay_D1_total=sum(a["replay"]["D1_false_pass"] for a in arms),
        any_D2=any(a["replay"]["D2_false_reject"] or a["strategy"]["D2_false_reject"]
                   for a in arms),
        any_D5=any(a["replay"]["D5_undetermined"] or a["strategy"]["D5_undetermined"]
                   for a in arms),
        interpretation=("one arm per arrival hour; the three arms share totals, peaks and "
                        "hourly requests, so verdict differences are attributable to when "
                        "the recovery-capable hour arrives. Realized deferral and starting "
                        "debt remain policy outcomes and are not matched."),
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
    arms, rows, problems = scan(args.fixture, target)
    summary = aggregate(arms)

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_d_matching_v1",
        "created_utc": started.isoformat(),
        "formal_result": False, "resource_admission": False,
        "security_certified": False, "aggregate_contract_release": False,
        "solver_calls": 0, "external_downloads": 0,
        "base_fixture": pin(args.fixture),
        "arrival_hours": list(ARRIVAL_HOURS),
        "match_problems": problems,
        "summary": summary,
        "arms": arms,
        "rows": rows,
    }
    (target / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        sha256((target / "report.json").read_bytes()).hexdigest() + "\n", encoding="utf-8")

    print(json.dumps({"arms": summary["arms"],
                      "by_arrival": {k: v["replay"] for k, v in summary["by_arrival"].items()},
                      "match_problems": problems}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
