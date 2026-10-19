"""Regression for repair-009 persisted cost-audit proxy tolerance alignment.

Candidate 6 of the ifocus2 attempt failed with ``persisted cost audit drifted``
after the solver-path audit had already passed. The continuous re-solve
``actual_proxy_fraction`` differed from the commitment-capability proxy by
~1e-7; the persistence gate used ``proxy_floor_absolute_tolerance`` (1e-7)
while ``FormalCgModelAdapter.audit_full_state`` accepted the same gap under
``feasibility_tolerance`` (1e-6).
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal import (
    _validate_persisted_cost_audit,
)

# Measured from ifocus2 progress.jsonl formal_full_state_audit_completed for
# candidate 6 cost_normalization final audit (2026-08-09T06:12:52Z).
_CAND6_ACTUAL_PROXY = 0.3917962224893918
_CAND6_COMMITMENT_PROXY = 0.3917963224893918
_CAND6_COST = 1158001.0972401924
_STATE_IDS = tuple(f"state_{index}" for index in range(24))
_RESIDUAL = {"passed": True, "maximum_balance_residual_mw": 2.61138666246552e-10}
_SNAPSHOT_SHA = "a" * 64


def _audit(*, actual_proxy: float, commitment_proxy: float) -> dict[str, object]:
    return {
        "passed": True,
        "audited_state_ids": list(_STATE_IDS),
        "reported_shared_snapshot_sha256": _SNAPSHOT_SHA,
        "solution_usable": True,
        "shared_snapshot_fixed": True,
        "integer_variables_relaxed": True,
        "residual_audit_passed": True,
        "additional_audits_passed": True,
        "full_feasible_objective": _CAND6_COST,
        "callback_record": {
            "passed": True,
            "actual_operating_cost_usd": _CAND6_COST,
            "actual_proxy_fraction": actual_proxy,
            "commitment_capability_proxy_fraction": commitment_proxy,
            "residual_audit": dict(_RESIDUAL),
        },
    }


def _candidate(*, proxy: float) -> SimpleNamespace:
    return SimpleNamespace(
        operating_cost_usd=_CAND6_COST,
        reactive_proxy_fraction=proxy,
        residual_audit=dict(_RESIDUAL),
    )


def _snapshot(*, proxy: float) -> SimpleNamespace:
    return SimpleNamespace(
        sha256=_SNAPSHOT_SHA,
        operating_cost_usd=_CAND6_COST,
        reactive_proxy=proxy,
    )


def test_cand6_actual_proxy_gap_passes_under_feasibility_tolerance() -> None:
    _validate_persisted_cost_audit(
        _audit(
            actual_proxy=_CAND6_ACTUAL_PROXY,
            commitment_proxy=_CAND6_COMMITMENT_PROXY,
        ),
        snapshot=_snapshot(proxy=_CAND6_COMMITMENT_PROXY),
        candidate=_candidate(proxy=_CAND6_COMMITMENT_PROXY),
        state_ids=_STATE_IDS,
        cost_tolerance_usd=1.0e-4,
        proxy_tolerance=1.0e-7,
        actual_proxy_tolerance=1.0e-6,
        snapshot_sha_field="reported_shared_snapshot_sha256",
    )


def test_cand6_snapshot_actual_proxy_gap_passes_under_feasibility_tolerance() -> None:
    """ifocus3: accepted cost snapshot stores continuous actual proxy.

    Candidate stores commitment-capability proxy; snapshot stores actual.
    The knife-edge gap is ~1e-7 and must use feasibility_tolerance, not the
    floor tolerance (same root cause as the actual_proxy field check).
    """
    _validate_persisted_cost_audit(
        _audit(
            actual_proxy=_CAND6_ACTUAL_PROXY,
            commitment_proxy=_CAND6_COMMITMENT_PROXY,
        ),
        snapshot=_snapshot(proxy=_CAND6_ACTUAL_PROXY),
        candidate=_candidate(proxy=_CAND6_COMMITMENT_PROXY),
        state_ids=_STATE_IDS,
        cost_tolerance_usd=1.0e-4,
        proxy_tolerance=1.0e-7,
        actual_proxy_tolerance=1.0e-6,
        snapshot_sha_field="reported_shared_snapshot_sha256",
    )


def test_cand6_snapshot_gap_still_fails_under_floor_tolerance() -> None:
    with pytest.raises(RuntimeError, match="persisted cost audit drifted"):
        _validate_persisted_cost_audit(
            _audit(
                actual_proxy=_CAND6_ACTUAL_PROXY,
                commitment_proxy=_CAND6_COMMITMENT_PROXY,
            ),
            snapshot=_snapshot(proxy=_CAND6_ACTUAL_PROXY),
            candidate=_candidate(proxy=_CAND6_COMMITMENT_PROXY),
            state_ids=_STATE_IDS,
            cost_tolerance_usd=1.0e-4,
            proxy_tolerance=1.0e-7,
            actual_proxy_tolerance=1.0e-7,
            snapshot_sha_field="reported_shared_snapshot_sha256",
        )


def test_cand6_actual_proxy_gap_still_fails_under_floor_tolerance() -> None:
    with pytest.raises(RuntimeError, match="persisted cost audit drifted"):
        _validate_persisted_cost_audit(
            _audit(
                actual_proxy=_CAND6_ACTUAL_PROXY,
                commitment_proxy=_CAND6_COMMITMENT_PROXY,
            ),
            snapshot=_snapshot(proxy=_CAND6_COMMITMENT_PROXY),
            candidate=_candidate(proxy=_CAND6_COMMITMENT_PROXY),
            state_ids=_STATE_IDS,
            cost_tolerance_usd=1.0e-4,
            proxy_tolerance=1.0e-7,
            actual_proxy_tolerance=1.0e-7,
            snapshot_sha_field="reported_shared_snapshot_sha256",
        )


def test_actual_proxy_still_rejects_material_drift() -> None:
    with pytest.raises(RuntimeError, match="persisted cost audit drifted"):
        _validate_persisted_cost_audit(
            _audit(
                actual_proxy=_CAND6_COMMITMENT_PROXY + 2.0e-6,
                commitment_proxy=_CAND6_COMMITMENT_PROXY,
            ),
            snapshot=_snapshot(proxy=_CAND6_COMMITMENT_PROXY),
            candidate=_candidate(proxy=_CAND6_COMMITMENT_PROXY),
            state_ids=_STATE_IDS,
            cost_tolerance_usd=1.0e-4,
            proxy_tolerance=1.0e-7,
            actual_proxy_tolerance=1.0e-6,
            snapshot_sha_field="reported_shared_snapshot_sha256",
        )


def test_commitment_proxy_identity_still_uses_floor_tolerance() -> None:
    with pytest.raises(RuntimeError, match="persisted cost audit drifted"):
        _validate_persisted_cost_audit(
            _audit(
                actual_proxy=_CAND6_COMMITMENT_PROXY,
                commitment_proxy=_CAND6_COMMITMENT_PROXY + 2.0e-7,
            ),
            snapshot=_snapshot(proxy=_CAND6_COMMITMENT_PROXY),
            candidate=_candidate(proxy=_CAND6_COMMITMENT_PROXY),
            state_ids=_STATE_IDS,
            cost_tolerance_usd=1.0e-4,
            proxy_tolerance=1.0e-7,
            actual_proxy_tolerance=1.0e-6,
            snapshot_sha_field="reported_shared_snapshot_sha256",
        )
