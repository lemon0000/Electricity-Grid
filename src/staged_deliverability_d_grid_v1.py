"""D-tier stage comparison grid: three evaluation methods x business/grid progress.

What this module adds
---------------------
B1 can run one trajectory of one method on one fixture. D needs the same exogenous
business, deadlines and clean resources under *two* business-progress paths and *two*
grid-progress paths, with every method evaluated by its own verdict and by the verdict
of its schedule replayed under full temporal constraints.

The business-progress variant is expressed by two declared assumptions only
(`change_hour` and `after`); physical parameters, equipment path, grid lead times and
clean paths are inherited unchanged from B1. `load_grid_case()` is therefore required
to be observation-for-observation identical to the frozen B1 loader when given the B1
business path, and a test pins that equivalence.

Scope and limits
----------------
- DRAFT_NONAUTHORITATIVE. Scalar mechanism model, no F/X certificate, no solver.
- Writes nothing; the caller owns attempt directories and reporting.
- Never re-plans a method's actions: the replay verdict comes from
  `staged_deliverability_replay_v1.replay_full_temporal`.
"""
from fractions import Fraction as Q
from pathlib import Path

import yaml

from src.staged_deliverability_development_v1 import (
    METHODS, ZERO, HourInput, Parameters, assessment, execute,
)
from src.staged_deliverability_replay_v1 import (
    LABELS, extract_actions, label_from, replay_full_temporal, verdicts,
)

BUSINESS_PATHS = ("baseline", "fast", "slow")
GRID_PATHS = ("on_time", "delayed")
CLEAN_PATHS = ("early", "late")
# `baseline` reproduces the frozen B1 fixture and exists only for loader equivalence;
# the D grid proper compares `fast` against `slow`.
GRID_BUSINESS = ("fast", "slow")

GRID_KEYS = ("status source_class first_hour last_hour deadline_lag flexible_fraction "
             "prehistory_clean parameters equipment business_paths grid clean_paths")


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _exact(value, name):
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{name} must use an exact string quantity")
    return Q(value)


def _integer(value, name):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{name} must be an integer")


def _keys(value, expected, label):
    if not isinstance(value, dict) or set(value) != set(expected.split()):
        raise ValueError(f"{label} fields differ from the declared schema")


def load_grid_config(path):
    """Parse and validate the D grid fixture; returns (cfg, params)."""
    cfg = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    _keys(cfg, GRID_KEYS, "grid fixture")
    _require(cfg["status"] == "DRAFT_NONAUTHORITATIVE"
             and cfg["source_class"] == "mechanism_assumption",
             "development-only fixture required")
    _keys(cfg["business_paths"], "baseline fast slow", "business_paths")
    for name, path in cfg["business_paths"].items():
        _keys(path, "before after change_hour", f"business path {name}")
        _exact(path["before"], f"{name} before")
        _exact(path["after"], f"{name} after")
        _integer(path["change_hour"], f"{name} change_hour")
        # Both progress paths must share the same exogenous tasks; only timing may differ.
        _require(path["before"] == cfg["business_paths"]["fast"]["before"],
                 "business paths must share the same pre-ramp workload")
        _require(path["after"] == cfg["business_paths"]["fast"]["after"],
                 "business paths must share the same post-ramp workload")
    for name in ("first_hour", "last_hour", "deadline_lag"):
        _integer(cfg[name], name)
    _require(cfg["first_hour"] <= cfg["last_hour"] and cfg["deadline_lag"] >= 0,
             "invalid observation window/deadline lag")
    _integer(cfg["grid"]["temporary_hour"], "temporary_hour")
    for m in cfg["equipment"]:
        _keys(m, "id capacity idle_mw start lead delay", "equipment module")
        _exact(m["capacity"], "module capacity")
        _exact(m["idle_mw"], "module idle")
    for name in ("before", "after"):
        _exact(cfg["grid"][name], name)
    _keys(cfg["clean_paths"], "early late", "clean_paths")
    for values in cfg["clean_paths"].values():
        _require(isinstance(values, list), "clean path must be an hourly list")
        for value in values:
            _exact(value, "clean")
    for value in cfg["grid"]["delays"].values():
        _integer(value, "grid delay")
    raw = cfg["parameters"]
    _require(not any(not isinstance(v, str) for k, v in raw.items()
                     if k not in ("max_events", "max_duration", "minimum_rest")),
             "physical parameters must use exact string quantities")
    params = Parameters(**{k: v if k in ("max_events", "max_duration", "minimum_rest")
                           else _exact(v, k) for k, v in raw.items()})
    return cfg, params


def load_grid_case(path, business="fast", plan="on_time", clean="early"):
    """Build current-hour observations for one grid cell.

    Mirrors `staged_deliverability_development_v1.load_small_case` exactly, except that
    the workload change point and post-change level come from a declared business path.
    """
    _require(business in BUSINESS_PATHS, "unknown business path")
    _require(plan in GRID_PATHS, "unknown grid path")
    _require(clean in CLEAN_PATHS, "unknown clean path")
    cfg, params = load_grid_config(path)

    delay = cfg["grid"]["delays"][plan]
    for asset in cfg["equipment"]:
        for name in ("start", "lead", "delay"):
            _integer(asset[name], name)
        _require(asset["lead"] >= 0 and asset["delay"] >= 0,
                 "negative construction duration/delay")
    _require(delay >= 0, "negative grid delay")

    clean_values = cfg["clean_paths"][clean]
    _require(len(clean_values) == cfg["last_hour"] + 1, "incomplete hourly clean path")

    path_cfg = cfg["business_paths"][business]
    observations = []
    for hour in range(cfg["first_hour"], cfg["last_hour"] + 1):
        online = [m for m in cfg["equipment"]
                  if hour >= m["start"] + m["lead"] + m["delay"]]
        commissioned = hour >= cfg["grid"]["start"] + cfg["grid"]["lead"] + delay
        w = _exact(path_cfg["before"] if hour < path_cfg["change_hour"]
                   else path_cfg["after"], "workload")
        supply = _exact(cfg["grid"]["after"] if commissioned else cfg["grid"]["before"], "supply")
        if hour == cfg["grid"]["temporary_hour"]:
            supply = min(supply, _exact(cfg["grid"]["temporary_limit"], "temporary_limit"))
        observations.append(HourInput(
            hour, min(hour + cfg["deadline_lag"], cfg["last_hour"]) if hour >= 0 else hour,
            w, _exact(cfg["flexible_fraction"], "flexible_fraction"),
            sum((_exact(m["capacity"], "module capacity") for m in online), ZERO),
            sum((_exact(m["idle_mw"], "module idle") for m in online), ZERO),
            _exact(clean_values[hour], "clean") if hour >= 0
            else _exact(cfg["prehistory_clean"], "prehistory_clean"),
            supply, tuple(m["id"] for m in online), commissioned,
        ))
    return params, tuple(observations)


def strategy_verdict(path, business, plan, clean,
                     registration_end=4, expected_last_hour=7):
    """The complete temporal evaluation's own verdict on the same plan.

    This is the reference for the second comparison axis: a simplified method that
    rejects a plan the full temporal strategy completes is a *false reject*, and that
    direction is unreachable by replaying the simplifying method's own actions.
    """
    params, observations = load_grid_case(path, business, plan, clean)
    native = execute(params, observations, method="full_temporal",
                     trajectory_id=f"{business}:{plan}:{clean}:reference")
    return assessment(native, registration_end, expected_last_hour)["method_conditions_satisfied"]


def evaluate_cell(path, business, plan, clean, method,
                  registration_end=4, expected_last_hour=7):
    """One grid cell: two comparisons for the same plan and method.

    1. `replay_label`   — method verdict vs. its own arrangement replayed under full
                          temporal constraints (does the simplification's own schedule
                          actually survive the physics it ignored?)
    2. `strategy_label` — method verdict vs. the complete temporal strategy's verdict on
                          the same plan (does the simplification reject something the
                          full evaluation completes?)
    """
    _require(method in METHODS, "unknown method")
    params, observations = load_grid_case(path, business, plan, clean)
    identity = f"{business}:{plan}:{clean}:{method}"
    native = execute(params, observations, method=method, trajectory_id=identity)
    replayed = replay_full_temporal(params, observations, extract_actions(native),
                                    trajectory_id=identity + ":replay")
    verdict = verdicts(native, replayed, registration_end, expected_last_hour)
    reference = assessment(execute(params, observations, method="full_temporal",
                                   trajectory_id=identity + ":reference"),
                           registration_end, expected_last_hour)
    verdict.update(
        business=business, plan=plan, clean=clean, trajectory=identity,
        hours=len(observations),
        reference_verdict=reference["method_conditions_satisfied"],
        strategy_label=label_from(verdict["method_verdict"],
                                  reference["method_conditions_satisfied"]),
        native_violation_count=sum(len(r.violations) for r in native.records),
        replay_violation_count=sum(len(r.violations) for r in replayed.records),
    )
    return verdict


def run_matrix(path, businesses=GRID_BUSINESS, grid_paths=GRID_PATHS,
               clean_paths=CLEAN_PATHS, methods=METHODS,
               registration_end=4, expected_last_hour=7):
    """Declared D grid; returns one row per (business, plan, clean, method).

    Defaults to `GRID_BUSINESS` (fast/slow). `baseline` is excluded because it only
    exists to pin loader equivalence with the frozen B1 fixture.
    """
    rows = []
    for business in businesses:
        for plan in grid_paths:
            for clean in clean_paths:
                for method in methods:
                    rows.append(evaluate_cell(path, business, plan, clean, method,
                                              registration_end, expected_last_hour))
    return rows


def _distribution(rows, key):
    counts = {name: 0 for name in LABELS}
    for row in rows:
        if row[key] not in counts:
            raise ValueError(f"unexpected label in {key}")
        counts[row[key]] += 1
    return counts


def summarize(rows):
    """Label distributions plus the mandatory D3/D4/D5 disclosure the outline requires.

    Two axes are reported separately and must never be merged:
    `replay`   — method verdict vs. its own arrangement under full temporal constraints;
    `strategy` — method verdict vs. the complete temporal strategy's verdict.
    """
    if not rows:
        raise ValueError("nonempty rows required")
    total = len(rows)
    counts = _distribution(rows, "label")
    strategy = _distribution(rows, "strategy_label")
    by_method = {}
    for method in METHODS:
        subset = [r for r in rows if r["method"] == method]
        if subset:
            by_method[method] = dict(
                replay=_distribution(subset, "label"),
                strategy=_distribution(subset, "strategy_label"),
            )
    return dict(total=total, counts=counts,
                strategy_counts=strategy,
                fractions={k: v / total for k, v in counts.items()},
                strategy_fractions={k: v / total for k, v in strategy.items()},
                by_method=by_method,
                interpretation="counts cover the whole declared grid; D3/D4/D5 are "
                               "reported, never omitted, D5 is excluded from D1-D4, and "
                               "the replay and strategy axes are distinct comparisons",
                formal_result=False, resource_admission=False)
