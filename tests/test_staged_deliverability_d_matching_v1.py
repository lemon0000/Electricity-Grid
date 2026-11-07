"""Bounded tests of the D recovery-timing matching arm; never formal results.

The load-bearing property is that the three arms share totals, peaks AND hourly
requests, so a verdict difference can only be attributed to when the recovery-capable
hour arrives. D's own `early`/`late` paths fail exactly this test, which is why the
arm exists.
"""
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.staged_deliverability_d_grid_v2 import load_grid_case
from src.staged_deliverability_development_v1 import power_mapping, ZERO
from experiments.staged_deliverability_d_matching_v1 import (
    ARRIVAL_HOURS, BASE_CLEAN, HIGH_CLEAN, LOW_CLEAN, clean_path, match_checks,
    patch_config, profile, variant_name,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"


def _base():
    return yaml.safe_load(BASE.read_text(encoding="utf-8"))


def test_paths_share_total_and_peak():
    paths = [clean_path(h) for h in ARRIVAL_HOURS]
    totals = {sum(Q(v) for v in p) for p in paths}
    peaks = {max(Q(v) for v in p) for p in paths}
    assert totals == {Q(317, 50)}
    assert peaks == {Q(26, 25)}


def test_exactly_one_high_hour_per_path():
    for hour in ARRIVAL_HOURS:
        path = [Q(v) for v in clean_path(hour)]
        assert [i for i, v in enumerate(path) if v == Q(26, 25)] == [hour]


def test_paths_stay_feasible_in_post_ramp_hours():
    """No post-ramp hour may fall below alpha * reference, or hourly_cfe binds everywhere."""
    cfg = patch_config(_base(), 3)
    path = [Q(v) for v in cfg["clean_paths"]["early"]]
    post = path[2:]
    assert all(v >= Q(21, 25) for v in post), post
    # The base level sits exactly at the bound: zero CFE request in those hours.
    assert all(v - Q(21, 25) >= 0 for v in post)


@pytest.mark.parametrize("arrival", ARRIVAL_HOURS)
def test_hourly_requests_are_identical_across_arrival_positions(arrival, tmp_path):
    """The match must hold in requests, not only in totals."""
    cfg = patch_config(_base(), arrival)
    path = tmp_path / f"{variant_name(arrival)}.yaml"
    path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
    params, observations = load_grid_case(path, "fast", "on_time", "early")
    got = profile(observations, params)

    reference_cfg = patch_config(_base(), ARRIVAL_HOURS[0])
    ref_path = tmp_path / "ref.yaml"
    ref_path.write_text(yaml.safe_dump(reference_cfg, sort_keys=False), encoding="utf-8")
    ref_params, ref_obs = load_grid_case(ref_path, "fast", "on_time", "early")
    assert got == profile(ref_obs, ref_params)


def test_match_checks_pass_on_a_valid_arm():
    base = _base()
    for arrival in ARRIVAL_HOURS:
        assert match_checks(patch_config(base, arrival), base) == []


def test_match_checks_catch_a_moved_parameter():
    base = _base()
    cfg = patch_config(base, 3)
    cfg["parameters"]["alpha"] = "1"
    assert any("parameters moved" in p for p in match_checks(cfg, base))


def test_match_checks_catch_a_total_that_does_not_match():
    base = _base()
    cfg = patch_config(base, 3)
    path = list(cfg["clean_paths"]["early"])
    path[2] = "1.00"
    cfg["clean_paths"] = {k: list(path) for k in cfg["clean_paths"]}
    assert match_checks(cfg, base)


def test_d_early_late_do_not_satisfy_the_match():
    """Pin why the arm exists: D's own early/late differ in the h2 CFE request."""
    params, early = load_grid_case(BASE, "fast", "on_time", "early")
    _, late = load_grid_case(BASE, "fast", "on_time", "late")
    pe, pl = profile(early, params), profile(late, params)
    assert pe != pl
    e_h2 = [row for row in pe if row[0] == 2][0]
    l_h2 = [row for row in pl if row[0] == 2][0]
    assert Q(e_h2[2]) == ZERO and Q(l_h2[2]) > ZERO


@pytest.mark.parametrize("arrival", ARRIVAL_HOURS)
def test_patch_moves_only_the_clean_path(arrival):
    base = _base()
    cfg = patch_config(base, arrival)
    assert cfg["parameters"] == base["parameters"]
    assert cfg["equipment"] == base["equipment"]
    assert cfg["business_paths"] == base["business_paths"]
    assert cfg["grid"] == base["grid"]
    assert cfg["first_hour"] == base["first_hour"]
    assert cfg["last_hour"] == base["last_hour"]
    assert cfg["deadline_lag"] == base["deadline_lag"]


def test_clean_path_shape():
    path = clean_path(4)
    assert path[0] == LOW_CLEAN[0] and path[1] == LOW_CLEAN[1]
    assert path[4] == HIGH_CLEAN
    assert all(v == BASE_CLEAN for i, v in enumerate(path) if i >= 2 and i != 4)
