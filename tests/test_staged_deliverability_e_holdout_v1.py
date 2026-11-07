"""Bounded tests of the E independent holdout; never formal results.

The load-bearing properties are that every holdout level is genuinely absent from D,
that nothing frozen moved, and that the two clean paths stay matched to each other in
total and peak so the arrival-time change is not confounded with an energy change.
"""
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from experiments.staged_deliverability_e_holdout_v1 import (
    CHANGE_HOURS, CLEAN_PATHS, EXPECTED_LAST_HOUR, GRID_DELAYS, LAST_HOUR,
    REGISTRATION_END, clean_path_stats, holdout_checks, patch_config, variant_name,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"


def _base():
    return yaml.safe_load(BASE.read_text(encoding="utf-8"))


def _cfg(change_hour=1, delay=1, clean="holdout_a"):
    return patch_config(_base(), change_hour, delay, clean)


def test_holdout_levels_are_absent_from_d():
    base = _base()
    d_hours = {p["change_hour"] for p in base["business_paths"].values()}
    d_delays = set(base["grid"]["delays"].values())
    d_clean = [list(v) for v in base["clean_paths"].values()]
    assert not (set(CHANGE_HOURS) & d_hours)
    assert not (set(GRID_DELAYS) & d_delays)
    for values in CLEAN_PATHS.values():
        assert list(values) not in d_clean
    assert LAST_HOUR != base["last_hour"]


def test_patch_moves_only_exogenous_paths():
    base = _base()
    cfg = _cfg()
    assert cfg["parameters"] == base["parameters"]
    assert cfg["equipment"] == base["equipment"]
    assert cfg["grid"]["lead"] == base["grid"]["lead"]
    assert cfg["grid"]["start"] == base["grid"]["start"]
    assert cfg["grid"]["before"] == base["grid"]["before"]
    assert cfg["grid"]["after"] == base["grid"]["after"]
    assert cfg["deadline_lag"] == base["deadline_lag"]
    assert cfg["flexible_fraction"] == base["flexible_fraction"]
    assert cfg["prehistory_clean"] == base["prehistory_clean"]
    assert cfg["last_hour"] == LAST_HOUR


def test_holdout_checks_pass_on_a_valid_patch():
    assert holdout_checks(_cfg(), _base()) == []


def test_holdout_checks_catch_a_reused_d_level():
    """A level copied from D must be reported, not silently accepted."""
    base = _base()
    problems = holdout_checks(_cfg(change_hour=2), base)
    assert any("ramp hour 2" in p for p in problems)


def test_holdout_checks_catch_a_moved_parameter():
    base = _base()
    cfg = _cfg()
    cfg["parameters"]["alpha"] = "1"
    problems = holdout_checks(cfg, base)
    assert any("parameter alpha moved" in p for p in problems)


def test_clean_paths_are_matched_to_each_other():
    """Total and peak must match across the two paths; only arrival time differs."""
    a = clean_path_stats(CLEAN_PATHS["holdout_a"])
    b = clean_path_stats(CLEAN_PATHS["holdout_b"])
    assert a["total"] == b["total"]
    assert a["peak"] == b["peak"]
    assert a["peak_hours"] != b["peak_hours"], "arrival time must actually differ"
    path_a = [Q(v) for v in CLEAN_PATHS["holdout_a"]]
    path_b = [Q(v) for v in CLEAN_PATHS["holdout_b"]]
    assert sum(path_a) == sum(path_b)
    assert sorted(path_a) != sorted(path_b) or path_a != path_b


def test_clean_paths_cover_the_extended_window():
    for name, values in CLEAN_PATHS.items():
        assert len(values) == LAST_HOUR + 1, name


def test_clean_paths_stay_feasible_in_post_ramp_hours(tmp_path):
    """Post-ramp clean must not fall below alpha * reference, or the holdout degenerates.

    `alpha * reference = 4/5 * 21/20 = 21/25` (reference includes standby idle). Attempt_02
    set post-ramp hours to .60/.64, which bound `hourly_cfe` in every post-ramp hour; all
    three methods then failed together and 7 of 8 cells were all-D4. The bound is asserted
    here so a future edit cannot reintroduce that degeneracy silently.
    """
    from src.staged_deliverability_development_v1 import power_mapping
    from src.staged_deliverability_d_grid_v2 import load_grid_case

    # Derive the bound from the loader itself rather than re-deriving it by hand: the
    # reference includes standby idle from every commissioned module.
    for clean in CLEAN_PATHS:
        for change_hour in CHANGE_HOURS:
            cfg = patch_config(_base(), change_hour, 1, clean)
            path = tmp_path / f"probe_{change_hour}_{clean}.yaml"
            path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
            params, observations = load_grid_case(path, "fast", "on_time", "early")
            by_hour = {o.hour: o for o in observations}
            post = [h for h in by_hour if h >= max(CHANGE_HOURS)]
            assert post, "post-ramp hours must exist"
            for hour in post:
                observation = by_hour[hour]
                _, _, reference = power_mapping(params, observation)
                bound = params.alpha * reference
                available = observation.clean_mwh
                assert available >= bound, (
                    f"{clean} c{change_hour} h{hour}: clean {available} < alpha*ref {bound}")


def test_phase_screen_is_label_independent_and_per_hour(tmp_path):
    """The screen must flag the hour no policy can serve, and never depend on labels."""
    from src.staged_deliverability_development_v1 import power_mapping
    from src.staged_deliverability_d_grid_v2 import load_grid_case
    from experiments.staged_deliverability_e_holdout_v1 import phase_screen

    blocked_by_ramp = {}
    for change_hour in CHANGE_HOURS:
        cfg = patch_config(_base(), change_hour, 1, "holdout_a")
        path = tmp_path / f"screen_{change_hour}.yaml"
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        params, observations = load_grid_case(path, "fast", "on_time", "early")
        blocked = phase_screen(cfg, params, observations)
        blocked_by_ramp[change_hour] = [b["hour"] for b in blocked]

    # Ramp at h1 lands on the grid's temporary-limit hour (supply 5/8): request 3/5
    # against a room of 1/5. Ramp at h4 avoids it.
    assert 1 in blocked_by_ramp[1]
    assert blocked_by_ramp[4] == []


def test_change_hour_one_is_structurally_infeasible_on_every_clean_path(tmp_path):
    """The all-D4 cells of attempt_03 were structural, not evidence about the methods."""
    from src.staged_deliverability_d_grid_v2 import load_grid_case
    from experiments.staged_deliverability_e_holdout_v1 import phase_screen

    for clean in CLEAN_PATHS:
        cfg = patch_config(_base(), 1, 1, clean)
        path = tmp_path / f"inf_{clean}.yaml"
        path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        params, observations = load_grid_case(path, "fast", "on_time", "early")
        assert phase_screen(cfg, params, observations), clean
    """D's 4/7 defaults would censor every E cell, so E must pass its own values."""
    assert EXPECTED_LAST_HOUR == LAST_HOUR
    assert 0 < REGISTRATION_END <= LAST_HOUR


@pytest.mark.parametrize("change_hour", CHANGE_HOURS)
@pytest.mark.parametrize("delay", GRID_DELAYS)
@pytest.mark.parametrize("clean", sorted(CLEAN_PATHS))
def test_patch_is_a_pure_function_of_the_declared_levels(change_hour, delay, clean):
    """The schema keys stay, and every one of them carries the holdout level.

    Collapsing `business_paths`/`clean_paths` to a single key would fail the D loader's
    schema check and, worse, let a mis-selected key read a stale D path.
    """
    cfg = _cfg(change_hour, delay, clean)
    assert sorted(cfg["business_paths"]) == ["baseline", "fast", "slow"]
    for path in cfg["business_paths"].values():
        assert path["change_hour"] == change_hour
    assert sorted(cfg["grid"]["delays"]) == ["delayed", "on_time"]
    assert set(cfg["grid"]["delays"].values()) == {delay}
    assert sorted(cfg["clean_paths"]) == ["early", "late"]
    assert list(cfg["clean_paths"].values()) == [list(CLEAN_PATHS[clean])] * 2
    assert variant_name(change_hour, delay, clean) == f"c{change_hour}__d{delay}__{clean}"
