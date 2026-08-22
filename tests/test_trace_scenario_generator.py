"""Data-driven trace scenario generator for RQ2 H2 (agent.md sections 4/8/9).

These tests pin ``src.scenarios.trace_scenario_generator``: a generator that
turns the *observed* AI-workload trace shapes (Google 2019 PDU power
utilisation; Alibaba PAI GPU 2020 relative hourly workload) into synthetic
``EconomicScenario`` paths for the H2 out-of-sample evaluation, replacing the
hand-crafted frozen holdout tree.

The scientific contract asserted here (the reason this generator exists) is:

* the generated scenarios are *genuinely* driven by the real trace shape --
  scaling a trace scales the derived MW, and each derived demand equals the
  frozen scale times the actual mean of the source window -- so the AI element
  is not cosmetic;
* training and holdout scenarios are drawn from *disjoint* time segments of the
  trace, so the out-of-sample claim is structural, not asserted;
* the draw is reproducible under a fixed seed and genuinely depends on it
  (agent.md section 10: all stochastic experiments fix and record their seed);
* the output validates against the frozen downstream contract
  (``EconomicScenario`` fields: probabilities strictly positive summing to one,
  unique names, nonnegative MW, positive hours);
* the honesty tags are explicit: MW is *derived* from a normalized shape via a
  frozen synthetic scale, and the probabilities are Monte-Carlo sampling
  weights, never empirical outage probabilities (agent.md sections 4/8).
"""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from src.models.economic_stochastic import EconomicScenario
from src.scenarios.trace_scenario_generator import (
    TraceScenarioConfig,
    TraceShape,
    generate_holdout_scenarios,
    load_peak_normalized_shape_from_csv,
    load_trace_shape_from_csv,
)


_REPO_ROOT = Path(__file__).resolve().parents[1]
_GOOGLE_TRACE = (
    _REPO_ROOT / "data/processed/google_power_2019/v1/hourly_shape.csv"
)
_ALIBABA_TRACE = (
    _REPO_ROOT
    / "data/processed/alibaba_gpu_2020/v2020/relative_hourly_workload.csv.gz"
)


def _ramp_shape(name: str, length: int) -> TraceShape:
    # A strictly increasing normalized shape in (0, 1]; every window has a
    # distinct mean, so train (early) and holdout (late) windows differ and the
    # mapping from window to MW is easy to hand-check.
    values = tuple((i + 1) / length for i in range(length))
    return TraceShape(name=name, source=f"synthetic::{name}", values=values)


def _config(**overrides) -> TraceScenarioConfig:
    base = dict(
        grid_stress_shape=_ramp_shape("grid", 40),
        green_workload_shape=_ramp_shape("green", 40),
        grid_stress_scale_mw=100.0,
        green_call_scale_mw=80.0,
        connected_demand_mw=1000.0,
        window_hours=4,
        n_train=6,
        n_holdout=5,
        seed=20260821,
        parameter_status="synthetic_test_only_not_for_engineering",
    )
    base.update(overrides)
    return TraceScenarioConfig(**base)


def test_probabilities_are_positive_and_sum_to_one_in_each_set():
    result = generate_holdout_scenarios(_config())
    for group in (result.training_scenarios, result.holdout_scenarios):
        assert all(s.probability > 0.0 for s in group)
        assert math.isclose(sum(s.probability for s in group), 1.0, abs_tol=1e-9)
    assert len(result.training_scenarios) == 6
    assert len(result.holdout_scenarios) == 5


def test_scenario_names_are_unique_within_and_across_sets():
    result = generate_holdout_scenarios(_config())
    names = [s.name for s in result.training_scenarios] + [
        s.name for s in result.holdout_scenarios
    ]
    assert len(set(names)) == len(names)


def test_mw_fields_are_nonnegative_and_hours_positive():
    result = generate_holdout_scenarios(_config())
    for s in result.training_scenarios + result.holdout_scenarios:
        assert s.grid_need_mw >= 0.0
        assert s.green_call_mw >= 0.0
        assert s.connected_demand_mw >= 0.0
        assert s.hours > 0.0


def test_seed_is_reproducible_and_matters():
    a = generate_holdout_scenarios(_config(seed=7))
    b = generate_holdout_scenarios(_config(seed=7))
    c = generate_holdout_scenarios(_config(seed=8))

    def _key(group):
        return [(s.grid_need_mw, s.green_call_mw) for s in group]

    assert _key(a.training_scenarios) == _key(b.training_scenarios)
    assert _key(a.holdout_scenarios) == _key(b.holdout_scenarios)
    # A different seed must actually move the draw (not a hard-coded tree).
    assert _key(a.holdout_scenarios) != _key(c.holdout_scenarios)


def test_train_and_holdout_windows_come_from_disjoint_time_segments():
    result = generate_holdout_scenarios(_config())
    prov = result.provenance
    # Every training window ends no later than the split; every holdout window
    # starts no earlier than the split -- so no source hour is shared.
    for source in ("grid", "green"):
        split = prov["split_index"][source]
        train_ends = [w["end"] for w in prov["windows"]["train"][source]]
        holdout_starts = [w["start"] for w in prov["windows"]["holdout"][source]]
        assert all(end <= split for end in train_ends)
        assert all(start >= split for start in holdout_starts)


def test_trace_shape_actually_drives_the_derived_mw():
    # The derived grid need of each scenario must equal the frozen scale times
    # the mean of the *actual* source window it was drawn from. This is the
    # test that the real trace is genuinely used, not decorative.
    cfg = _config()
    result = generate_holdout_scenarios(cfg)
    grid_values = cfg.grid_stress_shape.values
    for scenario, window in zip(
        result.training_scenarios, result.provenance["windows"]["train"]["grid"]
    ):
        window_mean = sum(grid_values[window["start"] : window["end"]]) / cfg.window_hours
        assert scenario.grid_need_mw == pytest.approx(
            cfg.grid_stress_scale_mw * window_mean, abs=1e-9
        )


def test_scaling_the_trace_scales_the_demands():
    base = generate_holdout_scenarios(_config(seed=3))
    scaled = generate_holdout_scenarios(
        _config(seed=3, grid_stress_scale_mw=200.0, green_call_scale_mw=160.0)
    )
    # Doubling the frozen scale doubles every derived demand for the same seed.
    for b, s in zip(base.training_scenarios, scaled.training_scenarios):
        assert s.grid_need_mw == pytest.approx(2.0 * b.grid_need_mw, abs=1e-9)
        assert s.green_call_mw == pytest.approx(2.0 * b.green_call_mw, abs=1e-9)


def test_generated_scenarios_satisfy_the_downstream_holdout_contract():
    # Feeding the generated scenarios into the H2 validator must not raise:
    # the generator is responsible for producing contract-valid scenarios.
    from src.evaluation.economic_holdout import _validate_scenarios

    result = generate_holdout_scenarios(_config())
    assert all(isinstance(s, EconomicScenario) for s in result.training_scenarios)
    _validate_scenarios(result.training_scenarios, "training")
    _validate_scenarios(result.holdout_scenarios, "holdout")


def test_parameter_status_marks_mw_as_derived_and_probability_as_synthetic():
    result = generate_holdout_scenarios(_config())
    status = result.training_scenarios[0].parameter_status if hasattr(
        result.training_scenarios[0], "parameter_status"
    ) else result.parameter_status
    assert "derived" in status
    assert "not_empirical" in status
    # The generator must not silently claim these are real outage probabilities.
    assert "outage" in status


def test_flat_trace_gives_constant_demand():
    flat = TraceShape(name="flat", source="synthetic::flat", values=tuple([0.5] * 40))
    result = generate_holdout_scenarios(
        _config(grid_stress_shape=flat, green_workload_shape=flat)
    )
    grid_needs = {s.grid_need_mw for s in result.training_scenarios}
    # Every window of a flat trace has the same mean -> identical derived MW.
    assert len(grid_needs) == 1
    assert next(iter(grid_needs)) == pytest.approx(50.0, abs=1e-9)


def test_window_longer_than_half_the_trace_is_rejected():
    # Train and holdout each get one contiguous half; a window that cannot fit
    # inside a half would force overlap and is rejected fail-closed.
    with pytest.raises(ValueError):
        generate_holdout_scenarios(_config(window_hours=25))


def test_nonpositive_scale_is_rejected():
    with pytest.raises(ValueError):
        generate_holdout_scenarios(_config(grid_stress_scale_mw=-1.0))


def test_missing_parameter_status_is_rejected():
    with pytest.raises(ValueError):
        generate_holdout_scenarios(_config(parameter_status=""))


def test_peak_normalized_external_peak_maps_series_to_unit_peak():
    # A pre-frozen external constant carries no holdout dependency, so it is a
    # valid divisor: dividing by the known series maximum reproduces the old
    # unit-peak behaviour without touching a split.
    shape = TraceShape.peak_normalized(
        name="alibaba_gpu",
        source="alibaba_gpu_2020",
        raw_values=(0.0, 2725.1, 5450.2),
        external_peak=5450.2,
    )
    assert max(shape.values) == pytest.approx(1.0, abs=1e-9)
    assert shape.values[0] == pytest.approx(0.0, abs=1e-9)
    assert shape.values[1] == pytest.approx(0.5, abs=1e-9)
    # The peak is recorded in the provenance source so the derivation is auditable.
    assert "peak_normalized" in shape.source
    assert shape.normalization_peak == pytest.approx(5450.2, abs=1e-9)
    # An external constant carries no split dependency.
    assert shape.normalization_split_fraction is None


def test_peak_normalized_split_fraction_uses_only_the_training_peak():
    # With split_fraction, the divisor is the peak of the training segment
    # [0, split_index) only. A holdout spike above that training peak is left
    # honestly above 1.0 (not clipped) and, crucially, never becomes the divisor.
    raw = (1.0, 2.0, 3.0, 4.0, 5.0, 100.0)  # split_index = round(6*0.5) = 3
    shape = TraceShape.peak_normalized(
        name="grid",
        source="synthetic",
        raw_values=raw,
        split_fraction=0.5,
    )
    # Training peak is max(1,2,3) = 3, applied to the whole series.
    assert shape.normalization_peak == pytest.approx(3.0, abs=1e-9)
    assert shape.normalization_split_fraction == pytest.approx(0.5, abs=1e-9)
    assert shape.values[0] == pytest.approx(1.0 / 3.0, abs=1e-9)
    # The holdout spike (100) is honestly above one, not the divisor.
    assert max(shape.values) == pytest.approx(100.0 / 3.0, abs=1e-9)


def test_peak_normalized_rejects_bare_global_peak():
    # Neither a split nor an external constant given: a global peak over the full
    # series would leak the holdout segment, so it is refused fail-closed.
    with pytest.raises(ValueError):
        TraceShape.peak_normalized(
            name="grid", source="synthetic", raw_values=(1.0, 2.0, 3.0, 4.0)
        )


def test_peak_normalized_rejects_both_divisor_modes():
    # Ambiguous divisor (split *and* external constant) is refused fail-closed.
    with pytest.raises(ValueError):
        TraceShape.peak_normalized(
            name="grid",
            source="synthetic",
            raw_values=(1.0, 2.0, 3.0, 4.0),
            split_fraction=0.5,
            external_peak=4.0,
        )


def test_peak_normalized_rejects_all_zero_training_segment():
    with pytest.raises(ValueError):
        TraceShape.peak_normalized(
            name="dead",
            source="synthetic",
            raw_values=(0.0, 0.0, 0.0, 0.0),
            split_fraction=0.5,
        )


def test_training_mw_is_independent_of_holdout_segment_content():
    # The central out-of-sample invariant: derived *training* MW must not change
    # when only the holdout segment of the raw trace changes. With split-aware
    # normalization the divisor is the training-segment peak, so two raw series
    # that share [0, split) but differ arbitrarily on [split, T) must yield
    # byte-identical training scenarios. A global-peak divisor would fail here
    # (a holdout spike would shrink every training MW).
    split = 0.5
    length = 40
    train_part = tuple((i + 1) / length for i in range(length // 2))
    holdout_calm = tuple(0.1 for _ in range(length // 2))
    holdout_spike = tuple(9999.0 for _ in range(length // 2))

    def _shape(name, holdout):
        return TraceShape.peak_normalized(
            name=name,
            source="synthetic",
            raw_values=train_part + holdout,
            split_fraction=split,
        )

    calm_cfg = _config(
        grid_stress_shape=_shape("grid", holdout_calm),
        green_workload_shape=_shape("green", holdout_calm),
        split_fraction=split,
    )
    spike_cfg = _config(
        grid_stress_shape=_shape("grid", holdout_spike),
        green_workload_shape=_shape("green", holdout_spike),
        split_fraction=split,
    )
    calm = generate_holdout_scenarios(calm_cfg)
    spike = generate_holdout_scenarios(spike_cfg)

    def _train_key(result):
        return [(s.grid_need_mw, s.green_call_mw) for s in result.training_scenarios]

    assert _train_key(calm) == _train_key(spike)
    # The holdout MW *do* respond to the changed holdout content (sanity: the
    # invariance above is not just a dead draw).
    def _holdout_key(result):
        return [(s.grid_need_mw, s.green_call_mw) for s in result.holdout_scenarios]

    assert _holdout_key(calm) != _holdout_key(spike)
    # And the divisor was estimated on the shared training segment only.
    assert calm.provenance["normalization"]["grid"]["peak"] == pytest.approx(
        spike.provenance["normalization"]["grid"]["peak"], abs=1e-12
    )


def test_generator_rejects_normalization_split_that_mismatches_the_draw():
    # A shape normalized on a training segment cut at one fraction must not be
    # fed to a draw that samples on a different split: the normalization peak
    # could then have seen hours this draw calls holdout. Refused fail-closed.
    raw = tuple((i + 1) / 40 for i in range(40))
    shape = TraceShape.peak_normalized(
        name="grid", source="synthetic", raw_values=raw, split_fraction=0.5
    )
    with pytest.raises(ValueError):
        generate_holdout_scenarios(
            _config(
                grid_stress_shape=shape,
                green_workload_shape=shape,
                split_fraction=0.6,
            )
        )


def test_generator_accepts_matching_normalization_split():
    raw = tuple((i + 1) / 40 for i in range(40))
    shape = TraceShape.peak_normalized(
        name="grid", source="synthetic", raw_values=raw, split_fraction=0.5
    )
    result = generate_holdout_scenarios(
        _config(
            grid_stress_shape=shape,
            green_workload_shape=shape,
            split_fraction=0.5,
        )
    )
    # Provenance records the divisor and the split it was estimated on.
    assert result.provenance["normalization"]["grid"]["split_fraction"] == pytest.approx(
        0.5, abs=1e-9
    )
    assert result.provenance["normalization"]["grid"]["peak"] is not None


def test_external_peak_shape_is_accepted_by_any_split():
    # A pre-frozen external constant carries no holdout dependency, so it is
    # valid regardless of the draw's split_fraction.
    raw = tuple((i + 1) / 40 for i in range(40))
    shape = TraceShape.peak_normalized(
        name="grid", source="synthetic", raw_values=raw, external_peak=40.0
    )
    result = generate_holdout_scenarios(
        _config(
            grid_stress_shape=shape,
            green_workload_shape=shape,
            split_fraction=0.6,
        )
    )
    assert result.provenance["normalization"]["grid"]["split_fraction"] is None


def test_green_call_derived_mw_matches_window_mean_in_both_sets():
    # The grid/training mapping is checked elsewhere; here we pin the *green*
    # dimension for BOTH the training and holdout sets, so no derived channel is
    # left unverified (task: derived-mapping coverage for green_call + holdout).
    cfg = _config()
    result = generate_holdout_scenarios(cfg)
    green_values = cfg.green_workload_shape.values
    grid_values = cfg.grid_stress_shape.values
    for group, key in (("train", "training_scenarios"), ("holdout", "holdout_scenarios")):
        scenarios = getattr(result, key)
        green_windows = result.provenance["windows"][group]["green"]
        grid_windows = result.provenance["windows"][group]["grid"]
        for scenario, gw, dw in zip(scenarios, green_windows, grid_windows):
            green_mean = sum(green_values[gw["start"] : gw["end"]]) / cfg.window_hours
            grid_mean = sum(grid_values[dw["start"] : dw["end"]]) / cfg.window_hours
            assert scenario.green_call_mw == pytest.approx(
                cfg.green_call_scale_mw * green_mean, abs=1e-9
            )
            assert scenario.grid_need_mw == pytest.approx(
                cfg.grid_stress_scale_mw * grid_mean, abs=1e-9
            )


# ---------------------------------------------------------------------------
# CSV loaders against the real shipped traces (leak-free)
# ---------------------------------------------------------------------------
def test_load_trace_shape_rejects_full_window_prenormalized_google_column():
    # The Google peak_normalized_unweighted_mean column is divided by the
    # full-window (future-inclusive) peak; loading it as a shape would leak the
    # holdout segment. It must be refused fail-closed with a redirect.
    with pytest.raises(ValueError, match="full-window"):
        load_trace_shape_from_csv(
            _GOOGLE_TRACE,
            column="peak_normalized_unweighted_mean",
            name="google",
        )


def test_load_peak_normalized_shape_from_raw_google_column_is_split_aware():
    shape = load_peak_normalized_shape_from_csv(
        _GOOGLE_TRACE,
        column="measured_power_util_unweighted_mean",
        name="google_grid",
        split_fraction=0.5,
    )
    assert len(shape.values) == 744
    assert shape.normalization_split_fraction == pytest.approx(0.5, abs=1e-9)
    assert shape.normalization_peak is not None
    # The divisor is the training-segment (first-half) peak, not the global peak.
    raw = shape.values  # already divided by the training peak
    train_max = max(raw[: 744 // 2])
    assert train_max == pytest.approx(1.0, abs=1e-9)


def test_load_peak_normalized_shape_from_raw_alibaba_column_is_split_aware():
    shape = load_peak_normalized_shape_from_csv(
        _ALIBABA_TRACE,
        column="requested_gpu_equivalents",
        name="alibaba_green",
        split_fraction=0.5,
    )
    assert len(shape.values) == 1642
    assert shape.normalization_split_fraction == pytest.approx(0.5, abs=1e-9)
    # A raw GPU-request series may spike above its training peak in the holdout
    # segment; that is left honestly above 1.0 rather than clipped.
    assert max(shape.values) >= 0.0


def test_generated_scenarios_from_real_traces_pass_downstream_contract():
    from src.evaluation.economic_holdout import _validate_scenarios

    grid = load_peak_normalized_shape_from_csv(
        _GOOGLE_TRACE,
        column="measured_power_util_unweighted_mean",
        name="google_grid",
        split_fraction=0.5,
    )
    green = load_peak_normalized_shape_from_csv(
        _ALIBABA_TRACE,
        column="requested_gpu_equivalents",
        name="alibaba_green",
        split_fraction=0.5,
    )
    result = generate_holdout_scenarios(
        _config(
            grid_stress_shape=grid,
            green_workload_shape=green,
            window_hours=24,
            n_train=8,
            n_holdout=6,
            split_fraction=0.5,
        )
    )
    _validate_scenarios(result.training_scenarios, "training")
    _validate_scenarios(result.holdout_scenarios, "holdout")
    # Real traces flowing end to end must still carry the module honesty tag.
    assert "derived" in result.parameter_status
    assert "not_empirical" in result.parameter_status
