"""Tests for chronological fast-forward scenario reduction."""

from __future__ import annotations

from dataclasses import replace
from math import isclose

import pytest

from src.scenarios.temporal_scenario_reduction import (
    TEMPORAL_SCENARIO_REDUCTION_PARAMETER_STATUS,
    reduce_temporal_scenarios_fast_forward,
)
from src.scenarios.temporal_trace_scenario_generator import (
    TemporalNetworkScenario,
)

STATUS = "synthetic_temporal_test_not_empirical"
SCALES = {
    "network_call_active": 1.0,
    "green_call_mw": 10.0,
    "data_center_demand_mw": 100.0,
    "system_load_multiplier": 1.0,
}


def _scenario(
    name: str,
    probability: float,
    active: tuple[int, ...],
    *,
    green: tuple[float, ...] | None = None,
) -> TemporalNetworkScenario:
    horizon = len(active)
    return TemporalNetworkScenario(
        name=name,
        probability=probability,
        periods=("q1",) * horizon,
        system_load_multiplier=(1.0,) * horizon,
        data_center_demand_mw=(100.0,) * horizon,
        network_call_active=active,
        green_call_mw=green or (0.0,) * horizon,
        connected_demand_mw=(100.0,) * horizon,
        recovery_headroom_mw=(20.0,) * horizon,
        completed_periods=frozenset({"q1"}),
        require_terminal_event_inactive=True,
        boundary_state_status="clean_boundary_with_zero_carry_in",
    )


def test_representatives_are_input_paths_and_only_probability_changes():
    scenarios = (
        _scenario("a", 0.2, (1, 0, 0), green=(1.0, 2.0, 0.0)),
        _scenario("b", 0.3, (0, 1, 0), green=(2.0, 1.0, 0.0)),
        _scenario("c", 0.5, (0, 0, 1), green=(8.0, 8.0, 0.0)),
    )
    result = reduce_temporal_scenarios_fast_forward(
        scenarios,
        target_count=2,
        component_scales=SCALES,
        parameter_status=STATUS,
    )
    originals = {scenario.name: scenario for scenario in scenarios}

    assert len(result.reduced_scenarios) == 2
    assert isclose(
        sum(scenario.probability for scenario in result.reduced_scenarios),
        1.0,
        abs_tol=1.0e-12,
    )
    for representative in result.reduced_scenarios:
        original = originals[representative.name]
        assert replace(representative, probability=original.probability) == original


def test_fast_forward_selection_matches_hand_computed_temporal_case():
    scenarios = (
        _scenario("a", 0.25, (1, 0)),
        _scenario("b", 0.25, (0, 1)),
        _scenario("c", 0.25, (1, 1)),
        _scenario("d", 0.25, (0, 0)),
    )
    result = reduce_temporal_scenarios_fast_forward(
        scenarios,
        target_count=1,
        component_scales=SCALES,
        ground_norm_order=1.0,
        parameter_status=STATUS,
    )

    assert result.provenance["selection_order"] == ["a"]
    assert result.reduced_scenarios[0].probability == pytest.approx(1.0)
    assert result.kantorovich_distance == pytest.approx(1.0)


def test_distance_is_sensitive_to_hourly_order_not_only_window_mean():
    ordered = (
        _scenario("early", 0.5, (1, 0), green=(10.0, 0.0)),
        _scenario("late", 0.5, (0, 1), green=(0.0, 10.0)),
    )
    result = reduce_temporal_scenarios_fast_forward(
        ordered,
        target_count=1,
        component_scales=SCALES,
        ground_norm_order=2.0,
        parameter_status=STATUS,
    )

    assert result.kantorovich_distance == pytest.approx(1.0)
    assert result.provenance["ground_metric"]["flattening"] == (
        "component_major_then_chronological_hour"
    )


def test_component_scales_change_the_auditable_ground_metric():
    scenarios = (
        _scenario("origin", 1 / 3, (0, 0), green=(0.0, 0.0)),
        _scenario("event", 1 / 3, (1, 0), green=(0.0, 0.0)),
        _scenario("green", 1 / 3, (0, 0), green=(100.0, 0.0)),
    )
    result = reduce_temporal_scenarios_fast_forward(
        scenarios,
        target_count=1,
        component_scales={**SCALES, "green_call_mw": 1000.0},
        parameter_status=STATUS,
    )

    assert result.provenance["selection_order"] == ["origin"]
    assert result.provenance["ground_metric"]["component_scales"][
        "green_call_mw"
    ] == 1000.0


def test_honesty_tag_and_noop_are_preserved():
    scenarios = (
        _scenario("a", 0.5, (1, 0)),
        _scenario("b", 0.5, (0, 1)),
    )
    result = reduce_temporal_scenarios_fast_forward(
        scenarios,
        target_count=2,
        component_scales=SCALES,
        parameter_status=STATUS,
    )

    assert result.reduced_scenarios == scenarios
    assert result.kantorovich_distance == 0.0
    assert STATUS in result.parameter_status
    assert TEMPORAL_SCENARIO_REDUCTION_PARAMETER_STATUS in result.parameter_status


@pytest.mark.parametrize(
    ("scenarios", "target", "scales", "message"),
    [
        ((), 1, SCALES, "nonempty"),
        ((_scenario("a", 1.0, (0,)),), 0, SCALES, "target_count"),
        (
            (
                _scenario("a", 0.4, (0,)),
                _scenario("b", 0.4, (1,)),
            ),
            1,
            SCALES,
            "sum to one",
        ),
        (
            (
                _scenario("a", 0.5, (0,)),
                _scenario("b", 0.5, (1,)),
            ),
            1,
            {**SCALES, "green_call_mw": 0.0},
            "strictly positive",
        ),
    ],
)
def test_malformed_reduction_inputs_fail_closed(
    scenarios, target, scales, message
):
    with pytest.raises((TypeError, ValueError), match=message):
        reduce_temporal_scenarios_fast_forward(
            scenarios,
            target_count=target,
            component_scales=scales,
            parameter_status=STATUS,
        )


def test_rejects_mismatched_horizons_and_nonbinary_event_indicator():
    with pytest.raises(ValueError, match="same horizon"):
        reduce_temporal_scenarios_fast_forward(
            (
                _scenario("a", 0.5, (0,)),
                _scenario("b", 0.5, (0, 1)),
            ),
            target_count=1,
            component_scales=SCALES,
            parameter_status=STATUS,
        )


def test_rejects_invalid_preserved_physical_or_boundary_fields():
    valid = _scenario("valid", 0.5, (0, 1))
    malformed = (
        replace(
            _scenario("bad", 0.5, (1, 0)),
            recovery_headroom_mw=(-1.0, 20.0),
        ),
        replace(
            _scenario("bad", 0.5, (1, 0)),
            connected_demand_mw=(99.0, 100.0),
        ),
        replace(
            _scenario("bad", 0.5, (1, 0)),
            boundary_state_status="unknown",
        ),
    )
    for scenario in malformed:
        with pytest.raises(ValueError):
            reduce_temporal_scenarios_fast_forward(
                (valid, scenario),
                target_count=1,
                component_scales=SCALES,
                parameter_status=STATUS,
            )


@pytest.mark.parametrize(
    ("changed", "message"),
    [
        ({"periods": ("q2", "q2")}, "period sequence"),
        ({"periods": ("q1", "q2", "q1")}, "same horizon"),
        ({"completed_periods": frozenset()}, "completed_periods"),
        ({"require_terminal_event_inactive": False}, "terminal event"),
        ({"recovery_headroom_mw": (10.0, 20.0)}, "recovery_headroom"),
    ],
)
def test_rejects_reduction_across_different_decision_semantics(
    changed, message
):
    reference = _scenario("reference", 0.5, (0, 1))
    candidate = replace(_scenario("candidate", 0.5, (1, 0)), **changed)
    with pytest.raises(ValueError, match=message):
        reduce_temporal_scenarios_fast_forward(
            (reference, candidate),
            target_count=1,
            component_scales=SCALES,
            parameter_status=STATUS,
        )
    with pytest.raises(ValueError, match="binary"):
        reduce_temporal_scenarios_fast_forward(
            (
                _scenario("a", 0.5, (0, 2)),
                _scenario("b", 0.5, (0, 1)),
            ),
            target_count=1,
            component_scales=SCALES,
            parameter_status=STATUS,
        )
