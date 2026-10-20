from __future__ import annotations

import numpy as np
import pytest

from src.scenarios.block_coupling import (
    bound_transport_expectation,
    quantile_coupling,
)


def test_two_by_two_transport_bounds_match_hand_calculation():
    result = bound_transport_expectation(
        (0.5, 0.5),
        (0.5, 0.5),
        ((0.0, 1.0), (1.0, 0.0)),
    )

    assert result.minimum == pytest.approx(0.0)
    assert result.maximum == pytest.approx(1.0)
    np.testing.assert_allclose(
        np.asarray(result.minimizing_coupling),
        ((0.5, 0.0), (0.0, 0.5)),
    )
    np.testing.assert_allclose(
        np.asarray(result.maximizing_coupling),
        ((0.0, 0.5), (0.5, 0.0)),
    )


def test_transport_support_can_tighten_the_identification_interval():
    result = bound_transport_expectation(
        (0.5, 0.5),
        (0.5, 0.5),
        ((0.0, 1.0), (1.0, 0.0)),
        allowed_support=((True, False), (False, True)),
    )

    assert result.minimum == pytest.approx(0.0)
    assert result.maximum == pytest.approx(0.0)


def test_infeasible_support_is_rejected():
    with pytest.raises(ValueError, match="coupling polytope is infeasible"):
        bound_transport_expectation(
            (0.5, 0.5),
            (0.5, 0.5),
            ((0.0, 1.0), (1.0, 0.0)),
            allowed_support=((True, False), (True, False)),
        )


def test_quantile_couplings_preserve_nonuniform_marginals():
    comonotone = np.asarray(
        quantile_coupling(
            (0.25, 0.75),
            (0.5, 0.5),
            (1.0, 2.0),
            (10.0, 20.0),
        )
    )
    countermonotone = np.asarray(
        quantile_coupling(
            (0.25, 0.75),
            (0.5, 0.5),
            (1.0, 2.0),
            (10.0, 20.0),
            reverse_columns=True,
        )
    )

    assert comonotone.sum(axis=1) == pytest.approx((0.25, 0.75))
    assert comonotone.sum(axis=0) == pytest.approx((0.5, 0.5))
    assert countermonotone.sum(axis=1) == pytest.approx((0.25, 0.75))
    assert countermonotone.sum(axis=0) == pytest.approx((0.5, 0.5))
    assert comonotone[0, 0] == pytest.approx(0.25)
    assert countermonotone[0, 1] == pytest.approx(0.25)
