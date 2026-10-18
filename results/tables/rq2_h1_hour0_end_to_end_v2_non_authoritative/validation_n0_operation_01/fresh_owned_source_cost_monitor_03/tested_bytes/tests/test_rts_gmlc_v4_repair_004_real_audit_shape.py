from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004_formal as formal,
)
from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256


def _snapshot() -> SharedSnapshot:
    values = (("reactive_proxy", (), 0.24),)
    return SharedSnapshot(
        values=values,
        sha256=structured_sha256(
            [
                {
                    "component": "reactive_proxy",
                    "index": [],
                    "value_float_hex": float(0.24).hex(),
                }
            ]
        ),
        reactive_proxy=0.24,
        operating_cost_usd=100.0,
    )


def _candidate(evidence: dict[str, object]) -> formal.v4._Candidate:
    return formal.v4._Candidate(
        requested_candidate_id="q_proxy_delta_0p0010",
        source="repair_003_verified_predecessor_prefix",
        relative_cost_budget_delta=0.001,
        cost_budget_usd=100.1,
        operating_cost_usd=100.0,
        reactive_proxy_fraction=0.24,
        commitment_sha256=formal.v4._commitment_sha256(()),
        dispatch_sha256=formal.v4._dispatch_sha256((), (), ()),
        commitment=(),
        startup=(),
        shutdown=(),
        generation_mw=(),
        branch_flows_mw=(),
        dc_flows_mw=(),
        reserve_up_mw=(),
        stage_audits={"repair_003_prefix": evidence},
        residual_audit={"passed": True},
    )


def _context() -> SimpleNamespace:
    return SimpleNamespace(
        config={"preregistration": {"id": "repair-004-test"}},
        input_contract={
            "formal_successor": {
                "candidate_controls": [
                    {
                        "mode": "verified_predecessor_prefix",
                        "relative_cost_budget_delta": 0.001,
                    }
                ]
            }
        },
        input_contract_sha256="c" * 64,
    )


def _real_audit_record() -> dict[str, object]:
    return {
        "passed": True,
        "residual_audit": {"passed": True},
        "callback_record": {"diagnostic_only": True},
    }


def test_prefix_candidate_accepts_real_top_level_residual_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    imported_candidate = _candidate({})
    imported = SimpleNamespace(
        candidate=imported_candidate,
        expectation=SimpleNamespace(
            commitment_sha256=imported_candidate.commitment_sha256,
            dispatch_sha256=imported_candidate.dispatch_sha256,
            manifest_sha256="d" * 64,
            reactive_proxy_fraction=0.24,
        ),
    )
    rehydrated = SimpleNamespace(
        snapshot=snapshot,
        reconstruction_record={"passed": True},
        full_state_audit_record=_real_audit_record(),
    )
    monkeypatch.setattr(
        formal.repair,
        "rehydrate_prefix_snapshot",
        lambda *_args, **_kwargs: rehydrated,
    )

    candidate, observed_snapshot, evidence = formal._prefix_candidate(
        SimpleNamespace(),
        imported,
        progress=SimpleNamespace(),
        candidate_log_root=Path("unused"),
    )

    assert candidate.residual_audit == {"passed": True}
    assert observed_snapshot == snapshot
    assert evidence["repeated_full_state_audit"] == _real_audit_record()


def test_prefix_checkpoint_accepts_real_top_level_residual_audit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    evidence = {
        "schema": formal.PREFIX_EVIDENCE_SCHEMA,
        "source_checkpoint_manifest_sha256": (
            formal.repair.PREFIX_EXPECTATIONS[0].manifest_sha256
        ),
        "repeated_full_state_audit": _real_audit_record(),
        "accepted_proxy_snapshot": formal._snapshot_payload(snapshot),
        "accepted_proxy_snapshot_sha256": snapshot.sha256,
    }
    payload = formal._checkpoint_payload(
        _context(),
        1,
        _candidate(evidence),
        mode="verified_predecessor_prefix",
        evidence=evidence,
    )
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)

    candidate, observed_snapshot = formal._validate_checkpoint_document(
        payload, _context(), 1
    )

    assert candidate.residual_audit == {"passed": True}
    assert observed_snapshot == snapshot


@pytest.mark.parametrize(
    "audit",
    [
        {"passed": True, "callback_record": {"residual_audit": {"passed": True}}},
        {
            "passed": True,
            "residual_audit": {"passed": False},
            "callback_record": {"residual_audit": {"passed": True}},
        },
    ],
)
def test_legacy_nested_shape_cannot_mask_missing_or_failed_top_level_residual(
    monkeypatch: pytest.MonkeyPatch, audit: dict[str, object]
) -> None:
    snapshot = _snapshot()
    evidence = {
        "schema": formal.PREFIX_EVIDENCE_SCHEMA,
        "source_checkpoint_manifest_sha256": (
            formal.repair.PREFIX_EXPECTATIONS[0].manifest_sha256
        ),
        "repeated_full_state_audit": audit,
        "accepted_proxy_snapshot": formal._snapshot_payload(snapshot),
        "accepted_proxy_snapshot_sha256": snapshot.sha256,
    }
    candidate = _candidate(evidence)
    if isinstance(audit.get("residual_audit"), dict):
        candidate = replace(candidate, residual_audit=dict(audit["residual_audit"]))
    payload = formal._checkpoint_payload(
        _context(),
        1,
        candidate,
        mode="verified_predecessor_prefix",
        evidence=evidence,
    )
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)

    with pytest.raises(RuntimeError, match="prefix evidence"):
        formal._validate_checkpoint_document(payload, _context(), 1)
