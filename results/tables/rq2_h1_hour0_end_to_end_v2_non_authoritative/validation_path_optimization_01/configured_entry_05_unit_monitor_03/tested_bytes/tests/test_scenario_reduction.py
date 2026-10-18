"""Tests for classic fast-forward scenario reduction (agent.md sections 4/8/9).

These pin ``src.scenarios.scenario_reduction.reduce_scenarios_fast_forward``:
the standard fast-forward selection + optimal order-1 Kantorovich redistribution
used to thin a *training* scenario tree without fabricating new data.

The scientific contract asserted here (the reason the reducer exists) is:

* the representatives are a genuine *subset* of the input -- demands and hours
  preserved byte-for-byte, only probability mass redistributed (agent.md 4/8:
  no new empirical content is minted);
* probability mass is conserved (the reduced tree is still a distribution);
* the selection is the real fast-forward recursion (verified against a
  hand-computed small case, not just "runs without error");
* the reported Kantorovich distance equals the closed-form optimal
  nearest-neighbour transport cost;
* the honesty tag is propagated so a reduced tree cannot be mistaken for data;
* malformed inputs (bad target, non-distribution, missing status) fail closed.
"""

from __future__ import annotations

import math

import pytest

from src.models.economic_stochastic import EconomicScenario
from src.scenarios.scenario_reduction import (
    SCENARIO_REDUCTION_PARAMETER_STATUS,
    reduce_scenarios_fast_forward,
)


_STATUS = "synthetic_test_only_not_for_engineering"


def _scenario(name, prob, grid, green, *, demand=1000.0, hours=1.0):
    return EconomicScenario(
        name=name,
        probability=prob,
        grid_need_mw=grid,
        green_call_mw=green,
        connected_demand_mw=demand,
        hours=hours,
    )


def _uniform_line(points):
    # Equal-probability scenarios placed on the grid_need axis (green fixed), so
    # the ground distance is just |grid_i - grid_j| and the whole reduction is
    # hand-checkable.
    n = len(points)
    return tuple(
        _scenario(f"s{i}", 1.0 / n, g, 0.0) for i, g in enumerate(points)
    )


# ---------------------------------------------------------------------------
# Structural contract: subset, mass conservation, honesty tag
# ---------------------------------------------------------------------------
def test_representatives_are_a_subset_with_preserved_demands_and_hours():
    scenarios = (
        _scenario("a", 0.2, 10.0, 5.0, demand=900.0, hours=2.0),
        _scenario("b", 0.3, 12.0, 6.0, demand=800.0, hours=3.0),
        _scenario("c", 0.5, 90.0, 40.0, demand=700.0, hours=4.0),
    )
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=2, parameter_status=_STATUS
    )
    by_name = {s.name: s for s in scenarios}
    assert len(result.reduced_scenarios) == 2
    for rep in result.reduced_scenarios:
        original = by_name[rep.name]
        # Only probability may change; every other field is preserved exactly.
        assert rep.grid_need_mw == original.grid_need_mw
        assert rep.green_call_mw == original.green_call_mw
        assert rep.connected_demand_mw == original.connected_demand_mw
        assert rep.hours == original.hours


def test_reduced_probabilities_sum_to_one():
    scenarios = _uniform_line([0.0, 1.0, 2.0, 10.0, 11.0])
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=2, parameter_status=_STATUS
    )
    assert math.isclose(
        sum(s.probability for s in result.reduced_scenarios), 1.0, abs_tol=1e-12
    )


def test_honesty_tag_is_propagated():
    scenarios = _uniform_line([0.0, 1.0, 5.0])
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=2, parameter_status=_STATUS
    )
    assert _STATUS in result.parameter_status
    assert SCENARIO_REDUCTION_PARAMETER_STATUS in result.parameter_status


# ---------------------------------------------------------------------------
# Algorithm correctness: fast-forward selection + optimal redistribution
# ---------------------------------------------------------------------------
def test_fast_forward_first_pick_minimises_weighted_distance():
    # Five points on a line at 0,1,2,3,100 with equal weight 0.2. Reducing to a
    # single scenario, fast forward must pick the point minimising the weighted
    # sum of distances to all others. Candidate objective z(u)=0.2*sum|x-u|:
    #   u=0  -> .2*(1+2+3+100)=21.2
    #   u=1  -> .2*(1+1+2+99)=20.6
    #   u=2  -> .2*(2+1+1+98)=20.4  <- min
    #   u=3  -> .2*(3+2+1+97)=20.6
    #   u=100-> huge
    # so the retained representative is the point at 2.0 (s2).
    scenarios = _uniform_line([0.0, 1.0, 2.0, 3.0, 100.0])
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=1, ground_norm_order=1.0, parameter_status=_STATUS
    )
    assert [s.name for s in result.reduced_scenarios] == ["s2"]
    # The single representative absorbs all mass.
    assert math.isclose(result.reduced_scenarios[0].probability, 1.0, abs_tol=1e-12)
    # Kantorovich distance = 0.2*(|0-2|+|1-2|+|3-2|+|100-2|) = 0.2*102 = 20.4.
    assert math.isclose(result.kantorovich_distance, 20.4, abs_tol=1e-9)


def test_reduction_keeps_both_clusters_and_redistributes_locally():
    # Two tight clusters far apart: {0,1,2} and {100,101}. Reducing to 2 must
    # keep one representative per cluster and redistribute mass within clusters,
    # not across the 100-wide gap.
    scenarios = _uniform_line([0.0, 1.0, 2.0, 100.0, 101.0])
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=2, ground_norm_order=1.0, parameter_status=_STATUS
    )
    kept = {s.name for s in result.reduced_scenarios}
    low_cluster = {"s0", "s1", "s2"}
    high_cluster = {"s3", "s4"}
    assert len(kept & low_cluster) == 1
    assert len(kept & high_cluster) == 1
    # Deleted points are assigned to the nearest retained scenario within their
    # own cluster, never across the gap.
    assignment = result.provenance["deleted_to_kept"]
    for deleted, target in assignment.items():
        deleted_in_low = deleted in low_cluster
        target_in_low = target in low_cluster
        assert deleted_in_low == target_in_low


def test_kantorovich_distance_matches_closed_form_nearest_neighbour():
    # Independent recomputation of the reported distance from scratch.
    points = [0.0, 1.0, 2.0, 40.0, 41.0, 42.0]
    scenarios = _uniform_line(points)
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=3, ground_norm_order=1.0, parameter_status=_STATUS
    )
    kept_points = {
        float(s.grid_need_mw): s.probability for s in result.reduced_scenarios
    }
    # Distance = sum over deleted points of p * min distance to a kept point.
    prob = 1.0 / len(points)
    expected = 0.0
    for x in points:
        if x not in kept_points:
            expected += prob * min(abs(x - k) for k in kept_points)
    assert math.isclose(result.kantorovich_distance, expected, abs_tol=1e-9)


def test_fast_forward_and_distance_on_2d_euclidean_default_metric():
    # Guards the *production/config* path: two demand dimensions and the default
    # ground_norm_order=2.0 (Euclidean), which the 1D order-1 cases above never
    # exercise. Four points, equal weight 0.25:
    #   A=(0,0)  B=(1,0)  C=(0,1)  D=(10,10)
    # Reducing to 2 must keep the isolated D and one anchor of the tight {A,B,C}
    # cluster. Fast-forward first pick minimises z(u)=0.25*sum||x-u||_2:
    #   u=A: .25*(1 + 1 + sqrt(200))          = .25*(2 + 14.14214) = 4.03553
    #   u=B: .25*(1 + sqrt2 + sqrt(81+100))   = .25*(1+1.41421+13.4536) = 3.96696
    #   u=C: symmetric to B                    = 3.96696
    #   u=D: .25*(sqrt200+sqrt181+sqrt181)     huge
    # so the first retained point is B (smaller index of the B/C tie), then D is
    # kept as the far outlier. A and C are redistributed to their nearest kept
    # point B: dist(A,B)=1, dist(C,B)=sqrt2. Distance = 0.25*(1 + sqrt2).
    scenarios = (
        _scenario("A", 0.25, 0.0, 0.0),
        _scenario("B", 0.25, 1.0, 0.0),
        _scenario("C", 0.25, 0.0, 1.0),
        _scenario("D", 0.25, 10.0, 10.0),
    )
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=2, parameter_status=_STATUS  # default ground_norm_order=2.0
    )
    assert {s.name for s in result.reduced_scenarios} == {"B", "D"}
    expected = 0.25 * (1.0 + math.sqrt(2.0))
    assert math.isclose(result.kantorovich_distance, expected, abs_tol=1e-9)
    # An order-1 (Manhattan) ground metric would instead give dist(C,B)=2, so the
    # distance pins the Euclidean norm specifically.
    assert not math.isclose(result.kantorovich_distance, 0.25 * (1.0 + 2.0), abs_tol=1e-9)


def test_no_reduction_when_target_at_least_input_size():
    scenarios = _uniform_line([0.0, 5.0, 9.0])
    result = reduce_scenarios_fast_forward(
        scenarios, target_count=3, parameter_status=_STATUS
    )
    assert len(result.reduced_scenarios) == 3
    assert result.kantorovich_distance == 0.0
    # Probabilities unchanged.
    assert all(math.isclose(s.probability, 1.0 / 3, abs_tol=1e-12)
               for s in result.reduced_scenarios)


def test_reduction_is_deterministic():
    scenarios = _uniform_line([0.0, 1.0, 2.0, 50.0, 51.0, 99.0])
    a = reduce_scenarios_fast_forward(
        scenarios, target_count=3, parameter_status=_STATUS
    )
    b = reduce_scenarios_fast_forward(
        scenarios, target_count=3, parameter_status=_STATUS
    )
    assert [s.name for s in a.reduced_scenarios] == [
        s.name for s in b.reduced_scenarios
    ]
    assert a.kantorovich_distance == b.kantorovich_distance


# ---------------------------------------------------------------------------
# Fail-closed input validation
# ---------------------------------------------------------------------------
def test_rejects_nonpositive_target():
    scenarios = _uniform_line([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="target_count"):
        reduce_scenarios_fast_forward(
            scenarios, target_count=0, parameter_status=_STATUS
        )


def test_rejects_boolean_target():
    scenarios = _uniform_line([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="target_count"):
        reduce_scenarios_fast_forward(
            scenarios, target_count=True, parameter_status=_STATUS
        )


def test_rejects_probabilities_that_do_not_sum_to_one():
    scenarios = (
        _scenario("a", 0.3, 0.0, 0.0),
        _scenario("b", 0.3, 1.0, 0.0),
    )
    with pytest.raises(ValueError, match="sum to one"):
        reduce_scenarios_fast_forward(
            scenarios, target_count=1, parameter_status=_STATUS
        )


def test_rejects_missing_parameter_status():
    scenarios = _uniform_line([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="parameter_status"):
        reduce_scenarios_fast_forward(
            scenarios, target_count=2, parameter_status=""
        )


def test_rejects_ground_norm_below_one():
    scenarios = _uniform_line([0.0, 1.0, 2.0])
    with pytest.raises(ValueError, match="ground_norm_order"):
        reduce_scenarios_fast_forward(
            scenarios, target_count=2, ground_norm_order=0.5, parameter_status=_STATUS
        )
