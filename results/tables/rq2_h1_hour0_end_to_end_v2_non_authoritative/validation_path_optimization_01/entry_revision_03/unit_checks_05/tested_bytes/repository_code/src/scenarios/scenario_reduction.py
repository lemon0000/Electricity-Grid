"""Classic scenario reduction for RQ2 stochastic programs (agent.md sections 4/8/9).

Why this exists
---------------
A data-driven draw (``trace_scenario_generator``) can emit far more training
scenarios than the L5 economic program needs to be planned on. Solving on the
full draw is wasteful, and a reviewer will (rightly) ask whether the H2
overestimation / under-delivery result survives a *principled* thinning of the
training tree rather than an arbitrary sub-sample. This module answers that with
the standard **fast-forward selection** heuristic for optimal scenario reduction
(Dupacova, Growe-Kuska & Roemisch 2003; Heitsch & Roemisch 2003), followed by
the **optimal redistribution** rule for the order-1 Kantorovich (Wasserstein)
distance.

What the method does
--------------------
Given a discrete distribution ``{(xi_i, p_i)}`` over ``N`` scenarios and a target
size ``n < N``:

* **Select** ``n`` representative scenarios one at a time. At each step it keeps
  the scenario that minimises the probability-weighted distance from every
  not-yet-kept scenario to the *nearest already-kept* scenario -- exactly the
  fast-forward recursion, which greedily minimises the remaining order-1
  Kantorovich distance of the reduced distribution to the original.
* **Redistribute** the probability of every deleted scenario onto the *nearest*
  retained scenario. For the order-1 Kantorovich distance this nearest-neighbour
  rule is the optimal redistribution: it is the transport plan that attains the
  distance, so no post-hoc reweighting can do better.

The remaining order-1 Kantorovich distance ``sum_{j deleted} p_j * min_{u kept}
d(xi_j, xi_u)`` is returned so the quality of the reduction is auditable rather
than asserted.

Honesty boundaries (agent.md sections 4/8/9)
-------------------------------------------
* This is a *transformation of an existing training distribution*, nothing more.
  The retained scenarios are a **subset of the input** with their demands and
  hours preserved byte-for-byte; only probability mass is redistributed. The
  method never fabricates a new demand point, never averages scenarios, and
  carries no new empirical content -- the ``parameter_status`` of the input is
  propagated and tagged, so a reduced set can never be mistaken for fresh data.
* The distance is measured on the two demand dimensions the L5 mechanism reads,
  ``(grid_need_mw, green_call_mw)`` (default Euclidean ground metric). Reduction
  merges probability mass only; because it never mixes demands or hours, a
  retained scenario stays a faithful, self-consistent path.
* **Out-of-sample safety.** This module reduces whatever distribution it is
  handed and has no notion of a holdout. The caller must apply it to the
  *training* distribution only; reducing a holdout set, or a set that pools
  train and holdout, would corrupt the section-9 train/holdout separation. The
  RQ2 ablation entry point applies it to generated *training* scenarios alone
  and leaves the shared holdout untouched.
* No solve, no certification, no security-limit relaxation happens here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from numbers import Real

import numpy as np

from ..models.economic_stochastic import EconomicScenario


# Reduction is a probability-mass transformation of an existing distribution; the
# retained scenarios are a subset of the input and carry no new empirical
# content. This tag is propagated so no downstream artifact can mistake a reduced
# training tree for fresh data (agent.md sections 4/8).
SCENARIO_REDUCTION_PARAMETER_STATUS = (
    "training_distribution_reduced_by_fast_forward_selection_with_optimal_"
    "kantorovich_redistribution_representatives_are_a_subset_of_the_input_with_"
    "redistributed_probability_mass_not_new_empirical_data"
)

_PROBABILITY_TOLERANCE = 1.0e-9


@dataclass(frozen=True)
class ScenarioReductionResult:
    """Result of one fast-forward reduction.

    ``reduced_scenarios`` is a subset of the input (same names, demands and
    hours) whose probabilities are the redistributed masses summing to one.
    ``kantorovich_distance`` is the remaining order-1 Kantorovich distance of the
    reduced distribution to the original. ``provenance`` records the algorithm,
    the ground metric, which scenarios were kept, and the deleted->kept
    assignment so the whole reduction can be hand-checked.
    """

    reduced_scenarios: tuple[EconomicScenario, ...]
    kantorovich_distance: float
    parameter_status: str
    provenance: dict = field(default_factory=dict)


def _finite(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, Real) or not isfinite(value):
        raise ValueError(f"{name} must be a finite number")
    return float(value)


def _validate_distribution(scenarios: tuple[EconomicScenario, ...]) -> np.ndarray:
    if not scenarios:
        raise ValueError("scenarios must be a nonempty tuple")
    names = [s.name for s in scenarios]
    if any(not n for n in names) or len(set(names)) != len(names):
        raise ValueError("scenario names must be nonempty and unique")
    total = 0.0
    for s in scenarios:
        p = _finite(f"probability[{s.name}]", s.probability)
        if p <= 0.0:
            raise ValueError("scenario probabilities must be strictly positive")
        total += p
        _finite(f"grid_need_mw[{s.name}]", s.grid_need_mw)
        _finite(f"green_call_mw[{s.name}]", s.green_call_mw)
    if abs(total - 1.0) > _PROBABILITY_TOLERANCE:
        raise ValueError("scenario probabilities must sum to one")
    return np.array([s.probability for s in scenarios], dtype=float)


def reduce_scenarios_fast_forward(
    scenarios: tuple[EconomicScenario, ...],
    *,
    target_count: int,
    ground_norm_order: float = 2.0,
    parameter_status: str | None = None,
) -> ScenarioReductionResult:
    """Reduce ``scenarios`` to ``target_count`` representatives (fast forward).

    Uses fast-forward selection to choose the representatives and optimal
    order-1 Kantorovich redistribution to reweight them. The ground distance on
    the demand vector ``(grid_need_mw, green_call_mw)`` is the ``ground_norm_order``
    norm (default Euclidean). ``parameter_status`` (or the input's, if the caller
    passes ``None`` it must be supplied) is propagated with the reduction tag so
    the reduced tree cannot be mistaken for fresh empirical data.

    ``target_count >= len(scenarios)`` is a no-op (returns the input unchanged
    with zero distance); ``target_count < 1`` is rejected fail-closed.
    """

    if isinstance(target_count, bool) or not isinstance(target_count, int):
        raise ValueError("target_count must be an integer")
    if target_count < 1:
        raise ValueError("target_count must be a positive integer")
    if not isinstance(parameter_status, str) or not parameter_status:
        raise ValueError("parameter_status must be a nonempty string")
    order = _finite("ground_norm_order", ground_norm_order)
    if order < 1.0:
        raise ValueError("ground_norm_order must be >= 1 to be a metric")

    probs = _validate_distribution(scenarios)
    n_total = len(scenarios)
    combined_status = f"{parameter_status}::{SCENARIO_REDUCTION_PARAMETER_STATUS}"

    if target_count >= n_total:
        # Nothing to reduce: return the input unchanged (distance 0). Still tag
        # the status so callers get a uniform contract.
        return ScenarioReductionResult(
            reduced_scenarios=tuple(scenarios),
            kantorovich_distance=0.0,
            parameter_status=combined_status,
            provenance={
                "algorithm": "fast_forward_selection_no_reduction_needed",
                "ground_metric": f"norm_order_{order:g}_on_(grid_need_mw,green_call_mw)",
                "original_count": n_total,
                "target_count": target_count,
                "kept_names": [s.name for s in scenarios],
                "deleted_to_kept": {},
                "kantorovich_distance": 0.0,
            },
        )

    demands = np.array(
        [[s.grid_need_mw, s.green_call_mw] for s in scenarios], dtype=float
    )
    # Pairwise ground distances ``cost[k, u] = ||demand_k - demand_u||_order``.
    diff = demands[:, None, :] - demands[None, :, :]
    cost = np.linalg.norm(diff, ord=order, axis=2)

    # Fast-forward selection. ``c_min[k]`` is the distance from k to the nearest
    # already-kept scenario (inf before any is kept). At each step we keep the
    # candidate u minimising the probability-weighted sum, over not-yet-kept k,
    # of ``min(c_min[k], cost[k, u])`` -- the remaining Kantorovich distance were
    # u added next. Ties break on the smaller original index (deterministic).
    remaining = np.ones(n_total, dtype=bool)
    c_min = np.full(n_total, np.inf)
    kept: list[int] = []
    for _ in range(target_count):
        best_u = -1
        best_z = np.inf
        for u in np.nonzero(remaining)[0]:
            candidate = np.minimum(c_min, cost[:, u])
            mask = remaining.copy()
            mask[u] = False
            z = float(np.sum(probs[mask] * candidate[mask]))
            if z < best_z - 1.0e-15:
                best_z = z
                best_u = int(u)
        kept.append(best_u)
        remaining[best_u] = False
        c_min = np.minimum(c_min, cost[:, best_u])

    kept_set = np.array(kept, dtype=int)
    # Optimal order-1 redistribution: each deleted scenario gives its mass to the
    # nearest retained scenario (ties -> earliest-selected retained scenario, the
    # first argmin over ``kept`` in selection order).
    reduced_prob = {int(k): float(probs[k]) for k in kept}
    deleted_to_kept: dict[str, str] = {}
    kantorovich = 0.0
    for j in np.nonzero(remaining)[0]:
        dists = cost[j, kept_set]
        nearest_pos = int(np.argmin(dists))
        nearest = int(kept_set[nearest_pos])
        reduced_prob[nearest] += float(probs[j])
        kantorovich += float(probs[j]) * float(dists[nearest_pos])
        deleted_to_kept[scenarios[j].name] = scenarios[nearest].name

    # Emit representatives in their original order for a stable, auditable tree.
    reduced_scenarios = tuple(
        EconomicScenario(
            name=scenarios[k].name,
            probability=reduced_prob[k],
            grid_need_mw=scenarios[k].grid_need_mw,
            green_call_mw=scenarios[k].green_call_mw,
            connected_demand_mw=scenarios[k].connected_demand_mw,
            hours=scenarios[k].hours,
        )
        for k in sorted(kept)
    )

    provenance = {
        "algorithm": (
            "fast_forward_selection_with_optimal_kantorovich_redistribution_"
            "heitsch_romisch_2003"
        ),
        "ground_metric": f"norm_order_{order:g}_on_(grid_need_mw,green_call_mw)",
        "original_count": n_total,
        "target_count": target_count,
        "kept_names": [scenarios[k].name for k in sorted(kept)],
        "deleted_to_kept": deleted_to_kept,
        "kantorovich_distance": kantorovich,
    }

    return ScenarioReductionResult(
        reduced_scenarios=reduced_scenarios,
        kantorovich_distance=kantorovich,
        parameter_status=combined_status,
        provenance=provenance,
    )


__all__ = [
    "SCENARIO_REDUCTION_PARAMETER_STATUS",
    "ScenarioReductionResult",
    "reduce_scenarios_fast_forward",
]
