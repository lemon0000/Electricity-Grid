from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256
from src.grid.rts_gmlc_level_set import (
    LevelOracleEvidence,
    ProxyBracket,
    acceptance_certificate,
    apply_level_oracle,
    build_round_checkpoint,
    classify_level_oracle,
    load_contiguous_round_checkpoints,
    midpoint_floor,
    publish_round_checkpoint,
    run_bracketed_level_set,
)


def _snapshot(label: str, *, proxy: float = 0.7, cost: float = 100.0) -> SharedSnapshot:
    values = (
        ("commitment", (0, f"g1-{label}"), 1.0),
        ("reactive_proxy", (), proxy),
    )
    payload = [
        {
            "component": component,
            "index": list(index),
            "value_float_hex": float(number).hex(),
        }
        for component, index, number in values
    ]
    return SharedSnapshot(
        values=values,
        sha256=structured_sha256(payload),
        reactive_proxy=proxy,
        operating_cost_usd=cost,
    )


def _evidence(
    floor: float,
    *,
    dual: float | None = None,
    snapshot: SharedSnapshot | None = None,
    recomputed_proxy: float | None = None,
    audited_cost: float | None = None,
    screens_complete: bool = False,
    audit_passed: bool = False,
) -> LevelOracleEvidence:
    return LevelOracleEvidence(
        proxy_floor=floor,
        active_master_bound_valid=dual is not None,
        active_master_dual_lower_bound_usd=dual,
        incumbent_snapshot=snapshot,
        all_inactive_states_screened=screens_complete,
        final_full_state_audit_passed=audit_passed,
        residual_audit_passed=audit_passed,
        recomputed_proxy=recomputed_proxy,
        audited_operating_cost_usd=audited_cost,
    )


def test_bound_only_master_can_strictly_separate_without_an_incumbent() -> None:
    evidence = _evidence(0.6, dual=100.000002)

    disposition = classify_level_oracle(
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )

    assert disposition.status == "certified_above_budget"
    assert disposition.bound_only


def test_budget_capped_decision_mip_global_infeasibility_separates() -> None:
    evidence = LevelOracleEvidence(
        proxy_floor=0.6,
        active_master_bound_valid=False,
        active_master_dual_lower_bound_usd=None,
        incumbent_snapshot=None,
        all_inactive_states_screened=False,
        final_full_state_audit_passed=False,
        residual_audit_passed=False,
        recomputed_proxy=None,
        audited_operating_cost_usd=None,
        active_master_globally_infeasible=True,
        active_master_budget_cap_usd=100.0,
    )

    disposition = classify_level_oracle(
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )

    assert disposition.status == "certified_above_budget"
    assert disposition.reason == (
        "active_budget_capped_decision_mip_globally_infeasible"
    )
    assert disposition.bound_only


def test_decision_infeasibility_at_a_smaller_cap_is_not_reused() -> None:
    evidence = LevelOracleEvidence(
        proxy_floor=0.6,
        active_master_bound_valid=False,
        active_master_dual_lower_bound_usd=None,
        incumbent_snapshot=None,
        all_inactive_states_screened=False,
        final_full_state_audit_passed=False,
        residual_audit_passed=False,
        recomputed_proxy=None,
        audited_operating_cost_usd=None,
        active_master_globally_infeasible=True,
        active_master_budget_cap_usd=99.0,
    )

    disposition = classify_level_oracle(
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )

    assert disposition.status == "unresolved"


def test_cost_separation_is_strict_and_rejects_equality() -> None:
    evidence = _evidence(0.6, dual=100.000001)

    disposition = classify_level_oracle(
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )

    assert disposition.status == "unresolved"
    assert disposition.reason == "strict_cost_separation_not_proven"


@pytest.mark.parametrize(
    ("screens_complete", "audit_passed"),
    ((False, True), (True, False)),
)
def test_unaudited_or_incompletely_screened_incumbent_is_unresolved(
    screens_complete: bool, audit_passed: bool
) -> None:
    snapshot = _snapshot("a", proxy=0.65, cost=99.0)
    evidence = _evidence(
        0.6,
        snapshot=snapshot,
        recomputed_proxy=0.65,
        audited_cost=99.0,
        screens_complete=screens_complete,
        audit_passed=audit_passed,
    )

    disposition = classify_level_oracle(
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )

    assert disposition.status == "unresolved"


def test_feasible_witness_raises_lower_bound_from_recomputed_proxy() -> None:
    old = ProxyBracket(0.4, 0.8, _snapshot("b", proxy=0.4))
    witness = _snapshot("c", proxy=0.7, cost=99.0)
    evidence = _evidence(
        0.6,
        snapshot=witness,
        recomputed_proxy=0.65,
        audited_cost=99.0,
        screens_complete=True,
        audit_passed=True,
    )

    update = apply_level_oracle(
        old,
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )

    assert update.disposition.status == "audited_feasible"
    assert update.bracket.lower_bound == 0.65
    assert update.bracket.upper_bound == 0.8
    assert update.bracket.lower_snapshot == witness


def test_floor_specific_evidence_cannot_be_applied_to_another_floor() -> None:
    old = ProxyBracket(0.4, 0.8, _snapshot("d", proxy=0.4))
    evidence = _evidence(0.61, dual=101.0)

    with pytest.raises(ValueError, match="floor-specific"):
        apply_level_oracle(
            old,
            evidence,
            effective_budget_usd=100.0,
            strict_separation_margin_usd=1.0e-6,
            expected_proxy_floor=0.6,
        )


def test_relative_acceptance_can_be_stricter_than_absolute_acceptance() -> None:
    bracket = ProxyBracket(0.0005, 0.0014, _snapshot("e", proxy=0.0005))

    certificate = acceptance_certificate(
        bracket,
        target_relative_gap=1.0e-4,
        maximum_absolute_gap=1.0e-3,
        maximum_relative_gap=1.0e-3,
    )

    assert certificate["absolute_acceptance_passed"]
    assert not certificate["relative_acceptance_passed"]
    assert not certificate["maximum_acceptance_passed"]


def test_acceptance_uses_an_upward_ulp_and_does_not_accept_exact_boundary() -> None:
    bracket = ProxyBracket(1.0, 1.001, _snapshot("f", proxy=1.0))

    certificate = acceptance_certificate(
        bracket,
        target_relative_gap=1.0e-4,
        maximum_absolute_gap=1.0e-3,
        maximum_relative_gap=1.0e-3,
    )

    assert not certificate["absolute_acceptance_passed"]
    assert not certificate["relative_acceptance_passed"]


def test_midpoint_is_strictly_inside_the_bracket() -> None:
    lower = 0.5
    upper = math.nextafter(lower, math.inf)

    assert (
        midpoint_floor(ProxyBracket(lower, upper, _snapshot("1", proxy=lower))) is None
    )
    floor = midpoint_floor(ProxyBracket(0.5, 0.75, _snapshot("2", proxy=0.5)))
    assert floor is not None
    assert 0.5 < floor < 0.75


def test_round_checkpoint_resume_requires_contiguous_hash_valid_chain(
    tmp_path: Path,
) -> None:
    snapshot = _snapshot("3", proxy=0.4)
    before = ProxyBracket(0.4, 0.8, snapshot)
    first_evidence = _evidence(0.6, dual=101.0)
    first_update = apply_level_oracle(
        before,
        first_evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )
    first = build_round_checkpoint(
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        round_ordinal=1,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        bracket_before=before,
        evidence=first_evidence,
        update=first_update,
    )
    publish_round_checkpoint(tmp_path, first)
    second_evidence = _evidence(
        0.5,
        snapshot=_snapshot("4", proxy=0.55, cost=99.0),
        recomputed_proxy=0.55,
        audited_cost=99.0,
        screens_complete=True,
        audit_passed=True,
    )
    second_update = apply_level_oracle(
        first_update.bracket,
        second_evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )
    second = build_round_checkpoint(
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        round_ordinal=2,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        bracket_before=first_update.bracket,
        evidence=second_evidence,
        update=second_update,
    )
    publish_round_checkpoint(tmp_path, second)

    loaded = load_contiguous_round_checkpoints(
        tmp_path,
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
    )

    assert [item["round_ordinal"] for item in loaded] == [1, 2]
    assert loaded[-1]["bracket_after"]["lower_snapshot"]["values"]

    checkpoint = next(tmp_path.rglob("round.json"))
    payload = json.loads(checkpoint.read_text(encoding="utf-8"))
    payload["input_contract_sha256"] = "c" * 64
    checkpoint.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(RuntimeError, match="manifest"):
        load_contiguous_round_checkpoints(
            tmp_path,
            candidate_id="q_proxy_delta_0p0075",
            candidate_ordinal=1,
            input_contract_sha256="a" * 64,
            predecessor_manifest_sha256="b" * 64,
        )


def test_round_checkpoint_loader_rejects_a_gap(tmp_path: Path) -> None:
    before = ProxyBracket(0.4, 0.8, _snapshot("5", proxy=0.4))
    evidence = _evidence(0.6, dual=101.0)
    update = apply_level_oracle(
        before,
        evidence,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
    )
    payload = build_round_checkpoint(
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        round_ordinal=2,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        bracket_before=before,
        evidence=evidence,
        update=update,
    )
    publish_round_checkpoint(tmp_path, payload)

    with pytest.raises(RuntimeError, match="contiguous"):
        load_contiguous_round_checkpoints(
            tmp_path,
            candidate_id="q_proxy_delta_0p0075",
            candidate_ordinal=1,
            input_contract_sha256="a" * 64,
            predecessor_manifest_sha256="b" * 64,
        )


def test_bisection_stops_fail_closed_on_timeout_without_bound_or_audit() -> None:
    initial = ProxyBracket(0.4, 0.8, _snapshot("6", proxy=0.4))

    def oracle(floor: float, _round: int) -> LevelOracleEvidence:
        return LevelOracleEvidence(
            proxy_floor=floor,
            active_master_bound_valid=False,
            active_master_dual_lower_bound_usd=None,
            incumbent_snapshot=None,
            all_inactive_states_screened=False,
            final_full_state_audit_passed=False,
            residual_audit_passed=False,
            recomputed_proxy=None,
            audited_operating_cost_usd=None,
            termination="maxTimeLimit",
        )

    result = run_bracketed_level_set(
        initial,
        oracle=oracle,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
        target_relative_gap=1.0e-4,
        maximum_absolute_gap=1.0e-3,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=10,
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
    )

    assert result.status == "unresolved"
    assert result.bracket == initial
    assert not result.certificate["maximum_acceptance_passed"]
    assert len(result.round_checkpoints) == 1


def test_bisection_resumes_after_the_last_contiguous_round(tmp_path: Path) -> None:
    initial = ProxyBracket(0.4, 0.8, _snapshot("7", proxy=0.4))
    calls: list[int] = []

    def oracle(floor: float, round_ordinal: int) -> LevelOracleEvidence:
        calls.append(round_ordinal)
        return _evidence(floor, dual=101.0)

    first = run_bracketed_level_set(
        initial,
        oracle=oracle,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
        target_relative_gap=1.0e-4,
        maximum_absolute_gap=0.01,
        maximum_relative_gap=0.01,
        maximum_rounds=1,
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )
    assert first.status == "round_limit"
    assert calls == [1]

    second = run_bracketed_level_set(
        initial,
        oracle=oracle,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
        target_relative_gap=1.0e-4,
        maximum_absolute_gap=0.01,
        maximum_relative_gap=0.01,
        maximum_rounds=2,
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )

    assert second.status == "round_limit"
    assert calls == [1, 2]
    assert len(second.round_checkpoints) == 2
