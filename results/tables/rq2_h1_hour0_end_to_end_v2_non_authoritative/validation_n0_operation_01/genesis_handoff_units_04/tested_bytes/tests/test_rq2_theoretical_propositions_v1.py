from __future__ import annotations

from itertools import product
from pathlib import Path

import numpy as np
import pytest

from src.scenarios.block_coupling import bound_transport_expectation


ROOT = Path(__file__).resolve().parents[1]
MEMO = ROOT / "docs" / "model_spec" / "rq2_theoretical_propositions_v1.md"


def _mw_only_reserves(
    grid_call: tuple[int, ...],
    cfe_call: tuple[int, ...],
) -> tuple[int, int]:
    shared = max(g + c for g, c in zip(grid_call, cfe_call, strict=True))
    separate = max(max(grid_call), max(cfe_call))
    return shared, separate


def _assert_uniform_marginals(coupling: np.ndarray) -> None:
    np.testing.assert_allclose(coupling.sum(axis=1), (0.5, 0.5))
    np.testing.assert_allclose(coupling.sum(axis=0), (0.5, 0.5))


def test_t1_bound_and_strict_overlap_condition_hold_exhaustively() -> None:
    for horizon in (1, 2, 3):
        sequences = tuple(product(range(3), repeat=horizon))
        for grid_call, cfe_call in product(sequences, repeat=2):
            shared, separate = _mw_only_reserves(grid_call, cfe_call)
            gap = shared - separate

            assert 0 <= gap <= min(max(grid_call), max(cfe_call))
            assert (gap > 0) == any(
                g + c > separate
                for g, c in zip(grid_call, cfe_call, strict=True)
            )


def test_t1_upper_bound_is_tight_and_zero_gap_has_distinct_cases() -> None:
    shared, separate = _mw_only_reserves((5, 1), (3, 0))
    assert shared - separate == min(5, 3)

    assert _mw_only_reserves((4, 0), (0, 3)) == (4, 4)
    assert _mw_only_reserves((5, 3), (0, 1)) == (5, 5)


def test_t2_sign_is_partially_identified_despite_zero_independence_mean() -> None:
    delta = np.asarray(((1.0, -1.0), (-1.0, 1.0)))
    result = bound_transport_expectation(
        (0.5, 0.5),
        (0.5, 0.5),
        delta,
    )

    assert result.minimum == pytest.approx(-1.0)
    assert result.maximum == pytest.approx(1.0)
    robust_positive = result.minimum > 0.0
    positivity_partially_identified = (
        result.minimum <= 0.0 < result.maximum
    )
    assert not robust_positive
    assert positivity_partially_identified

    minimizing = np.asarray(result.minimizing_coupling)
    maximizing = np.asarray(result.maximizing_coupling)
    _assert_uniform_marginals(minimizing)
    _assert_uniform_marginals(maximizing)
    assert np.sum(minimizing * delta) == pytest.approx(-1.0)
    assert np.sum(maximizing * delta) == pytest.approx(1.0)

    independent = np.full((2, 2), 0.25)
    _assert_uniform_marginals(independent)
    assert np.sum(independent * delta) == pytest.approx(0.0)


def test_t3_metric_endpoint_witnesses_cannot_be_spliced() -> None:
    diagonal = np.asarray(((1.0, 0.0), (0.0, 1.0)))
    off_diagonal = 1.0 - diagonal
    bound_a = bound_transport_expectation(
        (0.5, 0.5),
        (0.5, 0.5),
        diagonal,
    )
    bound_b = bound_transport_expectation(
        (0.5, 0.5),
        (0.5, 0.5),
        off_diagonal,
    )

    assert bound_a.maximum == pytest.approx(1.0)
    assert bound_b.maximum == pytest.approx(1.0)
    witness_a = np.asarray(bound_a.maximizing_coupling)
    witness_b = np.asarray(bound_b.maximizing_coupling)
    _assert_uniform_marginals(witness_a)
    _assert_uniform_marginals(witness_b)
    assert not np.allclose(witness_a, witness_b)
    assert np.sum(witness_a * off_diagonal) == pytest.approx(0.0)
    assert np.sum(witness_b * diagonal) == pytest.approx(0.0)

    for diagonal_mass in np.linspace(0.0, 0.5, 11):
        coupling = np.asarray(
            (
                (diagonal_mass, 0.5 - diagonal_mass),
                (0.5 - diagonal_mass, diagonal_mass),
            )
        )
        _assert_uniform_marginals(coupling)
        expectation_a = float(np.sum(coupling * diagonal))
        expectation_b = float(np.sum(coupling * off_diagonal))
        assert expectation_a + expectation_b == pytest.approx(1.0)
        assert not (
            expectation_a == pytest.approx(1.0)
            and expectation_b == pytest.approx(1.0)
        )


def test_theory_memo_keeps_required_scope_boundaries() -> None:
    memo = MEMO.read_text(encoding="utf-8")

    for proposition in ("## T1", "## T2", "## T3"):
        assert proposition in memo
    assert "instantaneous MW-only" in memo
    assert "independent coupling" in memo
    assert "同一个coupling" in memo
    assert "bootstrap endpoint interval" in memo
    assert "population identified set" in memo
    assert "formal_execution_ready=false" in memo
