"""Bounded tests of the D stage comparison grid; never formal results.

The load-bearing test is loader equivalence: the D fixture's `baseline` business path
must reproduce the frozen B1 fixture observation-for-observation. Without it, D's
verdicts would not be comparable to the B1/B2/B3 evidence already on disk.
"""
from pathlib import Path

import pytest

from src.staged_deliverability_development_v1 import (
    METHODS, execute, load_small_case,
)
from src.staged_deliverability_d_grid_v1 import (
    BUSINESS_PATHS, CLEAN_PATHS, GRID_BUSINESS, GRID_PATHS, evaluate_cell,
    load_grid_case, load_grid_config, run_matrix, summarize,
)
from src.staged_deliverability_replay_v1 import extract_actions, replay_full_temporal

ROOT = Path(__file__).resolve().parents[1]
B1_FIXTURE = ROOT / "configs/staged_deliverability_small_case_v1.DRAFT.yaml"
D_FIXTURE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"
CELLS = [(b, p, c) for b in GRID_BUSINESS for p in GRID_PATHS for c in CLEAN_PATHS]


@pytest.mark.parametrize("plan", GRID_PATHS)
@pytest.mark.parametrize("clean", CLEAN_PATHS)
def test_baseline_path_reproduces_b1_observations(plan, clean):
    """Loader equivalence: baseline is observation-identical to the frozen B1 fixture."""
    b1_params, b1_obs = load_small_case(B1_FIXTURE, plan=plan, clean=clean)
    d_params, d_obs = load_grid_case(D_FIXTURE, business="baseline", plan=plan, clean=clean)
    assert d_params == b1_params
    assert d_obs == b1_obs


def test_grid_fixture_declares_all_three_business_paths():
    cfg, _ = load_grid_config(D_FIXTURE)
    assert set(cfg["business_paths"]) == set(BUSINESS_PATHS) == {"baseline", "fast", "slow"}
    assert GRID_BUSINESS == ("fast", "slow")


def test_business_paths_hold_exogenous_workload_fixed():
    """Only the ramp timing may differ; the task amounts must be shared."""
    cfg, _ = load_grid_config(D_FIXTURE)
    paths = cfg["business_paths"]
    assert len({(p["before"], p["after"]) for p in paths.values()}) == 1
    assert len({p["change_hour"] for p in paths.values()}) == len(paths)


def test_business_paths_differ_only_in_ramp_timing():
    fast_params, fast = load_grid_case(D_FIXTURE, business="fast", plan="on_time", clean="early")
    slow_params, slow = load_grid_case(D_FIXTURE, business="slow", plan="on_time", clean="early")
    assert fast_params == slow_params
    assert [(o.hour, o.compute_capacity, o.clean_mwh, o.supply_mw) for o in fast] == \
           [(o.hour, o.compute_capacity, o.clean_mwh, o.supply_mw) for o in slow]
    assert [o.workload for o in fast] != [o.workload for o in slow]


def test_unknown_dimension_rejected():
    with pytest.raises(ValueError, match="unknown business path"):
        load_grid_case(D_FIXTURE, business="medium")
    with pytest.raises(ValueError, match="unknown grid path"):
        load_grid_case(D_FIXTURE, plan="early")
    with pytest.raises(ValueError, match="unknown clean path"):
        load_grid_case(D_FIXTURE, clean="on_time")


@pytest.mark.parametrize("method", METHODS)
def test_cell_reports_both_verdicts(method):
    row = evaluate_cell(D_FIXTURE, "fast", "on_time", "early", method)
    assert row["method"] == method
    assert row["label"] in {"D1_false_pass", "D2_false_reject", "D3_agree_pass",
                            "D4_agree_fail", "D5_undetermined"}
    assert row["hours"] == 10
    assert row["business"] == "fast" and row["plan"] == "on_time" and row["clean"] == "early"


def test_full_temporal_cell_never_reports_a_disagreement():
    """A full-temporal schedule replays to itself, so its label cannot be D1 or D2."""
    for business, plan, clean in CELLS:
        row = evaluate_cell(D_FIXTURE, business, plan, clean, "full_temporal")
        assert row["label"] in {"D3_agree_pass", "D4_agree_fail", "D5_undetermined"}


def test_matrix_shape_and_labels():
    rows = run_matrix(D_FIXTURE)
    assert len(rows) == len(GRID_BUSINESS) * len(GRID_PATHS) * len(CLEAN_PATHS) * len(METHODS)
    assert len({r["trajectory"] for r in rows}) == len(rows)
    summary = summarize(rows)
    assert summary["total"] == len(rows)
    assert sum(summary["counts"].values()) == len(rows)
    assert set(summary["by_method"]) == set(METHODS)
    assert summary["formal_result"] is False
    assert summary["resource_admission"] is False


def test_summary_reports_every_label_including_unchosen_ones():
    """D3/D4/D5 must be disclosed, not omitted, whatever the outcome."""
    summary = summarize(run_matrix(D_FIXTURE))
    assert set(summary["counts"]) == {"D1_false_pass", "D2_false_reject", "D3_agree_pass",
                                      "D4_agree_fail", "D5_undetermined"}


def test_replay_executes_the_given_command_without_replanning():
    """Replay mirrors the given command; where it keeps going it issues the same (q, r).

    A method that stopped early supplies a prefix, and replay may stop earlier still
    (a blocking violation) — but it must never execute more hours than it was given,
    and every hour it does execute must carry the commanded action.
    """
    for business, plan, clean in CELLS:
        params, observations = load_grid_case(D_FIXTURE, business, plan, clean)
        native = execute(params, observations, method="fixed_headroom",
                         trajectory_id=f"{business}:{plan}:{clean}")
        actions = extract_actions(native)
        replayed = replay_full_temporal(params, observations, actions, trajectory_id="rt")
        executed = extract_actions(replayed)
        assert len(executed) <= len(actions)
        for (nh, nq, nr), (rh, rq, rr) in zip(actions, executed):
            assert (rh, rq, rr) == (nh, nq, nr)


def test_summary_rejects_empty_input():
    with pytest.raises(ValueError, match="nonempty rows"):
        summarize([])


def test_approximations_are_structurally_permissive():
    """Pin a structural property, not a numerical outcome.

    Both simplifications loosen constraints rather than tighten them:
      - `instantaneous` drops the whole event envelope from its call room;
      - `fixed_headroom` replaces the real recovery headroom with a constant.
    Neither can therefore be *more* conservative than the complete evaluation. The
    consequence is that D2 (simplification rejects, reference accepts) is unreachable
    with this method set, and the paper's C3 can only claim the false-pass direction.
    If a future simplification becomes conservative, this test must fail loudly.
    """
    for row in run_matrix(D_FIXTURE):
        if row["method"] == "full_temporal":
            continue
        if row["method_verdict"] is False:
            assert row["reference_verdict"] is False, (
                f"{row['trajectory']}: a simplification rejected a plan the complete "
                f"temporal strategy accepted; the permissiveness argument no longer holds"
            )
        assert row["strategy_label"] != "D2_false_reject"


def test_summary_keeps_the_two_axes_separate():
    summary = summarize(run_matrix(D_FIXTURE))
    assert summary["counts"] != summary["strategy_counts"] or \
           sum(summary["counts"].values()) == 0, (
        "the two axes happened to coincide; if that is genuine, update this test "
        "rather than merging the axes silently"
    )
    for method, views in summary["by_method"].items():
        assert set(views) == {"replay", "strategy"}
        assert sum(views["replay"].values()) == sum(views["strategy"].values())
