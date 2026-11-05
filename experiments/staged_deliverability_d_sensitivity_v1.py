"""Sensitivity scan over the D grid: eligible share, equipment headroom, CFE target.

DRAFT_NONAUTHORITATIVE. Zero solver calls, zero external downloads.

Why this exists
---------------
D attempt_01 rested on a single 10-hour fixture: only the business ramp timing
varied between arms, while the eligible share, equipment capacity and CFE target
were fixed at one value. A reviewer's first question is whether the false-pass
result survives moving those three parameters, so the grid is rerun across a
declared sensitivity set.

Protocol note
-------------
The D contract intended the sensitivity branch to run "label determination only,
without full replay" to control cost. Measuring attempt_01 showed the full grid
costs 1.12 s, so the abbreviated protocol saves nothing and would have weakened
the evidence by reporting only one axis. This runner executes the full grid for
every parameter combination and records both axes. The deviation is deliberate
and is stated in the report rather than silently applied.

Equipment scaling follows the standing obligation recorded in
`staged_evaluation_records.development_design()`: change K and idle demand
together, so a capacity change is not confounded with a standby-drain change.
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

from src.staged_deliverability_d_grid_v1 import run_matrix, summarize  # noqa: E402

BASE_FIXTURE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"
ROOT_OUT = ROOT / "results/tables/staged_deliverability_d_sensitivity_v1_non_authoritative"

# Declared sensitivity set. Eligible share and CFE target are the three-level axes
# named in the D contract; equipment headroom is the two-level axis.
ELIGIBLE = (Q(1, 5), Q(2, 5), Q(1, 2))           # 20%, 40% (main grid), 50%
EQUIPMENT = (Q(2, 3), Q(4, 5), Q(1))              # 2/3, 4/5, base (scale applied to K and idle)
CFE_TARGET = (Q(3, 5), Q(7, 10), Q(4, 5))         # 60%, 70%, 80% (base is the boundary)
# `2/5` is included so the main grid's inherited eligible share is represented;
# without it the sensitivity set would not overlap attempt_01 at all.
#
# Why these ranges and not the wider ones (recorded after attempt_03):
# attempt_03 used K=1/2 and alpha=1, both of which leave the feasible region, so all
# three methods stopped on the same blocking violation and D1 collapsed to zero for a
# degenerate reason rather than an informative one. Two couplings force the narrow band:
#   - equipment capacity must carry post-ramp workload: K_total * scale >= 7/10, so
#     scale >= 7/12; upward scaling is limited because idle demand scales with K and
#     raises metered power, which tightens the CFE check at the same hours;
#   - the CFE target is binding at the low-clean hour h0, where attributed demand is
#     alpha * (3/4) and available clean is 3/5, giving alpha <= 4/5 exactly.
# The screen below enforces these structurally before any comparison is read.

LABELS = ("D1_false_pass", "D2_false_reject", "D3_agree_pass",
          "D4_agree_fail", "D5_undetermined")


def _tag(value):
    return str(value).replace("/", "of")


def variant_name(eligible, equipment, cfe):
    return f"f_{_tag(eligible)}__K_{_tag(equipment)}__a_{_tag(cfe)}"


def patch_config(base, eligible, equipment, cfe):
    """Return a patched fixture: eligible share, CFE target, and scaled K with idle."""
    cfg = deepcopy(base)
    cfg["flexible_fraction"] = str(eligible)
    cfg["parameters"]["alpha"] = str(cfe)
    for module in cfg["equipment"]:
        module["capacity"] = str(Q(module["capacity"]) * equipment)
        module["idle_mw"] = str(Q(module["idle_mw"]) * equipment)
    return cfg


def pin(path: Path) -> dict:
    """Pin a file's bytes; paths outside the repo are recorded absolute, not dropped."""
    data = path.read_bytes()
    try:
        shown = path.resolve().relative_to(ROOT.resolve()).as_posix()
    except ValueError:
        shown = path.resolve().as_posix()
    return {"path": shown, "bytes": len(data), "sha256": sha256(data).hexdigest()}


def feasibility_screen(cfg):
    """Two separate verdicts, because they have different epistemic standing.

    `infeasible` is a HARD structural statement: commissioned capacity cannot carry the
    post-ramp workload at all, independent of policy. Every method then stops on the same
    blocking violation, so a zero false-pass count there says nothing about robustness.

    `cfe_binding_hours` is INFORMATIONAL and deliberately conservative: it assumes no
    deferral, so metered power stays at full workload and the CFE check looks tighter than
    any real trajectory. It over-flags. attempt_04 showed this directly — combinations
    marked by this bound still produced 11 false passes, because deferral lowers power in
    exactly the hours the bound treats as binding. It is therefore recorded as a hint for
    reading the results, never used to drop or dismiss a combination.
    """
    infeasible = []
    post_ramp = max(Q(p["after"]) for p in cfg["business_paths"].values())
    total_k = max(
        sum(Q(m["capacity"]) for m in cfg["equipment"] if h >= m["start"] + m["lead"] + m["delay"])
        for h in range(cfg["first_hour"], cfg["last_hour"] + 1))
    if total_k < post_ramp:
        infeasible.append(f"capacity {total_k} below post-ramp workload {post_ramp}")

    alpha = Q(cfg["parameters"]["alpha"])
    factor = Q(cfg["parameters"]["facility_factor"])
    aux = Q(cfg["parameters"]["auxiliary_mw"])
    beta = Q(cfg["parameters"]["beta"])
    clean = [Q(v) for v in cfg["clean_paths"]["early"]]
    binding = []
    for hour in range(max(cfg["first_hour"], 0), cfg["last_hour"] + 1):
        online = [m for m in cfg["equipment"] if hour >= m["start"] + m["lead"] + m["delay"]]
        idle = sum((Q(m["idle_mw"]) for m in online), Q(0))
        workload = max(Q(p["after"]) if hour >= p["change_hour"] else Q(p["before"])
                       for p in cfg["business_paths"].values())
        power = factor * (idle + beta * workload) + aux
        if alpha and alpha * power > clean[hour]:
            binding.append(f"h{hour}:{alpha * power}>{clean[hour]}")
    return infeasible, binding


def scan(base_fixture: Path, target: Path) -> dict:
    base = yaml.safe_load(base_fixture.read_text(encoding="utf-8"))
    fixtures = target / "fixtures"
    fixtures.mkdir(exist_ok=True)

    combos, all_rows = [], []
    for eligible in ELIGIBLE:
        for equipment in EQUIPMENT:
            for cfe in CFE_TARGET:
                name = variant_name(eligible, equipment, cfe)
                path = fixtures / f"{name}.yaml"
                cfg = patch_config(base, eligible, equipment, cfe)
                path.write_text(
                    yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True,
                                   default_flow_style=False),
                    encoding="utf-8")
                infeasible, cfe_binding = feasibility_screen(cfg)
                rows = run_matrix(path)
                summary = summarize(rows)
                for row in rows:
                    row.update(variant=name, eligible=str(eligible),
                               equipment_scale=str(equipment), cfe_target=str(cfe),
                               structurally_infeasible=bool(infeasible))
                all_rows.extend(rows)
                combos.append(dict(
                    variant=name,
                    eligible=str(eligible), equipment_scale=str(equipment),
                    cfe_target=str(cfe),
                    fixture=pin(path),
                    evaluations=summary["total"],
                    replay=summary["counts"],
                    strategy=summary["strategy_counts"],
                    false_pass_any=(summary["counts"]["D1_false_pass"] > 0
                                    or summary["strategy_counts"]["D1_false_pass"] > 0),
                    structurally_infeasible=bool(infeasible),
                    infeasible_reasons=infeasible,
                    cfe_binding_hours=cfe_binding,
                ))
    return combos, all_rows


def aggregate(combos):
    """Where does the false-pass result survive, and where does it vanish."""
    if not combos:
        raise ValueError("nonempty combos required")
    with_fp = [c for c in combos if c["false_pass_any"]]
    without = [c for c in combos if not c["false_pass_any"]]
    by_eligible, by_equipment, by_cfe = {}, {}, {}
    for axis, key in ((by_eligible, "eligible"), (by_equipment, "equipment_scale"),
                      (by_cfe, "cfe_target")):
        for combo in combos:
            bucket = axis.setdefault(combo[key], {"combos": 0, "with_false_pass": 0,
                                                  "replay_D1": 0, "strategy_D1": 0})
            bucket["combos"] += 1
            bucket["with_false_pass"] += int(combo["false_pass_any"])
            bucket["replay_D1"] += combo["replay"]["D1_false_pass"]
            bucket["strategy_D1"] += combo["strategy"]["D1_false_pass"]
    total_replay = sum(c["replay"]["D1_false_pass"] for c in combos)
    total_strategy = sum(c["strategy"]["D1_false_pass"] for c in combos)
    return dict(
        combos=len(combos),
        combos_with_false_pass=len(with_fp),
        combos_without_false_pass=len(without),
        combos_without_false_pass_names=[c["variant"] for c in without],
        replay_D1_total=total_replay,
        strategy_D1_total=total_strategy,
        replay_D1_max=max(c["replay"]["D1_false_pass"] for c in combos),
        replay_D1_min=min(c["replay"]["D1_false_pass"] for c in combos),
        any_D2=any(c["replay"]["D2_false_reject"] or c["strategy"]["D2_false_reject"]
                   for c in combos),
        any_D5=any(c["replay"]["D5_undetermined"] or c["strategy"]["D5_undetermined"]
                   for c in combos),
        by_eligible=by_eligible, by_equipment=by_equipment, by_cfe_target=by_cfe,
        interpretation=(
            "counts cover the declared sensitivity set only; a combination without a "
            "false pass is reported as such and is never dropped from the table"),
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
    combos, rows = scan(args.fixture, target)
    summary = aggregate(combos)

    report = {
        "authority": "DRAFT_NONAUTHORITATIVE",
        "scope": "staged_deliverability_d_sensitivity_v1",
        "created_utc": started.isoformat(),
        "formal_result": False, "resource_admission": False,
        "security_certified": False, "aggregate_contract_release": False,
        "solver_calls": 0, "external_downloads": 0,
        "base_fixture": pin(args.fixture),
        "axes": {"eligible_share": [str(v) for v in ELIGIBLE],
                 "equipment_scale": [str(v) for v in EQUIPMENT],
                 "cfe_target": [str(v) for v in CFE_TARGET]},
        "protocol_note": ("full grid on both axes for every combination, not the "
                          "contract's abbreviated label-only branch; measured cost "
                          "made the abbreviation pointless"),
        "equipment_scaling_note": "K and idle demand scale together by construction",
        "summary": summary,
        "combos": combos,
        "rows": rows,
    }
    (target / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    (target / "report.sha256").write_text(
        sha256((target / "report.json").read_bytes()).hexdigest() + "\n", encoding="utf-8")

    print(json.dumps({"combos": summary["combos"],
                      "with_false_pass": summary["combos_with_false_pass"],
                      "without": summary["combos_without_false_pass_names"],
                      "replay_D1_range": [summary["replay_D1_min"],
                                          summary["replay_D1_max"]],
                      "any_D2": summary["any_D2"], "any_D5": summary["any_D5"]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
