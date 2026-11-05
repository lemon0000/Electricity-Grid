"""Bounded tests of the D sensitivity scan; never formal results.

The load-bearing properties are that variant generation is a pure patch (only the
declared fields move), that the feasibility screen never silently drops a
combination, and that total and peak clean allocations stay matched across the
early/late paths the sensitivity relies on.
"""
from fractions import Fraction as Q
from pathlib import Path

import pytest
import yaml

from src.staged_deliverability_d_grid_v1 import run_matrix, summarize
from experiments.staged_deliverability_d_sensitivity_v1 import (
    BASE_FIXTURE, CFE_TARGET, ELIGIBLE, EQUIPMENT, feasibility_screen, patch_config,
    variant_name,
)

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "configs/staged_deliverability_d_v1.DRAFT.yaml"


def _base():
    return yaml.safe_load(BASE.read_text(encoding="utf-8"))


def test_axes_are_declared_and_ordered():
    assert ELIGIBLE == tuple(sorted(ELIGIBLE))
    assert Q(2, 5) in ELIGIBLE, "main-grid eligible share must be represented"
    assert Q(1) in EQUIPMENT, "base equipment scale must be represented"
    assert len(ELIGIBLE) >= 3 and len(EQUIPMENT) >= 2 and len(CFE_TARGET) >= 3


@pytest.mark.parametrize("eligible", ELIGIBLE)
@pytest.mark.parametrize("equipment", EQUIPMENT)
@pytest.mark.parametrize("cfe", CFE_TARGET)
def test_patch_moves_only_declared_fields(eligible, equipment, cfe):
    """A patch changes f, alpha, equipment capacity and idle -- nothing else."""
    base = _base()
    patched = patch_config(base, eligible, equipment, cfe)
    assert patched["flexible_fraction"] == str(eligible)
    assert patched["parameters"]["alpha"] == str(cfe)
    for original, module in zip(base["equipment"], patched["equipment"]):
        assert Q(module["capacity"]) == Q(original["capacity"]) * equipment
        assert Q(module["idle_mw"]) == Q(original["idle_mw"]) * equipment
        assert module["id"] == original["id"]
        assert module["start"] == original["start"]
        assert module["lead"] == original["lead"]
    for key in base:
        if key in ("flexible_fraction", "parameters", "equipment"):
            continue
        assert patched[key] == base[key], f"{key} must not change"


def test_patch_does_not_mutate_base():
    base = _base()
    before = yaml.safe_dump(base, sort_keys=True)
    patch_config(base, Q(1, 2), Q(1), Q(1))
    assert yaml.safe_dump(base, sort_keys=True) == before


def test_equipment_capacity_and_idle_scale_together():
    """Standing obligation: a capacity change must not be confounded with standby drain."""
    base = _base()
    for equipment in EQUIPMENT:
        patched = patch_config(base, Q(2, 5), equipment, Q(4, 5))
        for original, module in zip(base["equipment"], patched["equipment"]):
            ratio_cap = Q(module["capacity"]) / Q(original["capacity"])
            ratio_idle = Q(module["idle_mw"]) / Q(original["idle_mw"])
            assert ratio_cap == ratio_idle == equipment


def test_variant_name_is_unique_per_combination():
    names = [variant_name(f, k, a) for f in ELIGIBLE for k in EQUIPMENT for a in CFE_TARGET]
    assert len(names) == len(set(names))


def test_feasibility_screen_reports_infeasible_capacity():
    """Capacity below the post-ramp workload is a hard structural failure."""
    base = _base()
    patched = patch_config(base, Q(2, 5), Q(1, 2), Q(4, 5))
    infeasible, binding = feasibility_screen(patched)
    assert infeasible, "halved capacity cannot carry the post-ramp workload"
    assert any("capacity" in reason for reason in infeasible)


def test_feasibility_screen_accepts_declared_axis_values():
    """Every declared combination must pass the hard screen; none may be silently dropped."""
    base = _base()
    for eligible in ELIGIBLE:
        for equipment in EQUIPMENT:
            for cfe in CFE_TARGET:
                patched = patch_config(base, eligible, equipment, cfe)
                infeasible, _ = feasibility_screen(patched)
                assert not infeasible, (
                    f"{variant_name(eligible, equipment, cfe)} is structurally "
                    f"infeasible but is declared in the axis: {infeasible}")


def test_cfe_binding_is_advisory_not_exclusionary():
    """The conservative CFE bound may flag hours, but must never imply exclusion."""
    base = _base()
    patched = patch_config(base, Q(2, 5), Q(1), Q(1))
    infeasible, binding = feasibility_screen(patched)
    assert not infeasible
    # alpha=1 exceeds available clean at some hour by the no-deferral bound.
    assert binding, "the advisory bound should flag alpha=1"


def test_clean_paths_match_total_and_peak():
    """The matched recovery-timing comparison depends on this holding for both paths."""
    base = _base()
    early = [Q(v) for v in base["clean_paths"]["early"]]
    late = [Q(v) for v in base["clean_paths"]["late"]]
    assert len(early) == len(late)
    assert sum(early) == sum(late)
    assert max(early) == max(late)
    assert early != late, "paths must differ in timing, not be identical"


def test_declared_combination_runs_and_reports_both_axes(tmp_path):
    base = _base()
    patched = patch_config(base, Q(2, 5), Q(1), Q(4, 5))
    path = tmp_path / "variant.yaml"
    path.write_text(yaml.safe_dump(patched, sort_keys=False, allow_unicode=True),
                    encoding="utf-8")
    rows = run_matrix(path)
    summary = summarize(rows)
    assert summary["total"] == 24
    assert set(summary["counts"]) == {"D1_false_pass", "D2_false_reject", "D3_agree_pass",
                                      "D4_agree_fail", "D5_undetermined"}
    assert set(summary["strategy_counts"]) == set(summary["counts"])
    for row in rows:
        assert "strategy_label" in row
        assert row["strategy_label"] in summary["counts"]
        assert row["method_verdict"] is not None or row["label"] == "D5_undetermined"


def test_false_reject_never_occurs_across_declared_axes(tmp_path):
    """Both simplifications loosen constraints, so D2 must stay at zero everywhere."""
    base = _base()
    checked = 0
    for eligible in (Q(1, 5), Q(2, 5)):
        for cfe in (Q(3, 5), Q(4, 5)):
            patched = patch_config(base, eligible, Q(1), cfe)
            path = tmp_path / variant_name(eligible, Q(1), cfe)
            path = path.with_suffix(".yaml")
            path.write_text(yaml.safe_dump(patched, sort_keys=False, allow_unicode=True),
                            encoding="utf-8")
            summary = summarize(run_matrix(path))
            assert summary["counts"]["D2_false_reject"] == 0
            assert summary["strategy_counts"]["D2_false_reject"] == 0
            checked += 1
    assert checked == 4
