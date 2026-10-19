from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from src.grid.rts_gmlc_cost_bisection import (
    CostBracket,
    CostOracleEvidence,
    acceptance_certificate,
    apply_cost_oracle,
    load_contiguous_round_checkpoints,
    midpoint_cap,
    run_bracketed_cost_bisection,
)
from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256

REAL_FAILURE_LB = 1127283.3411921486
REAL_FAILURE_UB = 1128705.0994006419
REAL_FAILURE_GAP = 0.0012596365598491668
PROXY_WITNESS_UB = 1130114.1984402775


def _snapshot(cost: float, *, proxy: float = 0.29915124370579915) -> SharedSnapshot:
    values = (("commitment", (0, "G1"), 1.0),)
    return SharedSnapshot(
        values=values,
        sha256=structured_sha256(
            [
                {
                    "component": "commitment",
                    "index": [0, "G1"],
                    "value_float_hex": (1.0).hex(),
                }
            ]
        ),
        reactive_proxy=proxy,
        operating_cost_usd=cost,
    )


def _feasible(cap: float, cost: float) -> CostOracleEvidence:
    return CostOracleEvidence(
        cost_cap_usd=cap,
        active_master_globally_infeasible=False,
        incumbent_snapshot=_snapshot(cost),
        all_inactive_states_screened=True,
        final_full_state_audit_passed=True,
        residual_audit_passed=True,
        audited_operating_cost_usd=cost,
        termination="objectiveLimit",
    )


def _infeasible(cap: float) -> CostOracleEvidence:
    return CostOracleEvidence(
        cost_cap_usd=cap,
        active_master_globally_infeasible=True,
        incumbent_snapshot=None,
        all_inactive_states_screened=False,
        final_full_state_audit_passed=False,
        residual_audit_passed=False,
        audited_operating_cost_usd=None,
        termination="TerminationCondition.provenInfeasible",
        infeasibility_certificate_schema=(
            "rts_gmlc_level_set_bound_only_early_separation_v1"
        ),
        infeasibility_certificate_source=(
            "active_budget_capped_decision_mip_global_infeasibility"
        ),
        infeasibility_claim_scope=(
            "no_budget_feasible_solution_at_or_above_this_proxy_floor"
        ),
        decision_budget_cap_usd=cap,
    )


def _rewrite_round(path: Path, mutate: object) -> None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    mutate(payload)
    encoded = (
        json.dumps(
            payload, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True
        )
        + "\n"
    ).encode("utf-8")
    path.write_bytes(encoded)
    path.with_name("SHA256SUMS").write_text(
        f"{hashlib.sha256(encoded).hexdigest()}  round.json\n",
        encoding="ascii",
    )


def test_real_repair_004_failure_shape_requires_a_successor() -> None:
    bracket = CostBracket(REAL_FAILURE_LB, REAL_FAILURE_UB, _snapshot(REAL_FAILURE_UB))
    certificate = acceptance_certificate(
        bracket,
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
    )

    assert certificate["relative_gap_to_feasible_incumbent"] == pytest.approx(
        REAL_FAILURE_GAP
    )
    assert certificate["target_attained"] is False
    assert certificate["maximum_acceptance_passed"] is False


@pytest.mark.parametrize("disposition", ["feasible", "infeasible"])
def test_one_decision_round_closes_the_real_direct_cost_interval(
    disposition: str,
) -> None:
    bracket = CostBracket(REAL_FAILURE_LB, REAL_FAILURE_UB, _snapshot(REAL_FAILURE_UB))
    cap = midpoint_cap(bracket)
    assert cap is not None
    evidence = _feasible(cap, cap) if disposition == "feasible" else _infeasible(cap)
    updated = apply_cost_oracle(bracket, evidence, expected_cost_cap_usd=cap)
    certificate = acceptance_certificate(
        updated.bracket,
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
    )

    assert certificate["maximum_acceptance_passed"] is True
    assert certificate["relative_gap_to_feasible_incumbent"] < 0.000631


def test_only_a_fully_audited_witness_can_lower_the_upper_bound() -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    incomplete = replace(_feasible(110.0, 109.0), all_inactive_states_screened=False)

    update = apply_cost_oracle(bracket, incomplete, expected_cost_cap_usd=110.0)

    assert update.disposition.status == "unresolved"
    assert update.bracket == bracket


def test_feasible_witness_uses_an_explicit_frozen_cost_tolerance() -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    evidence = replace(
        _feasible(110.0, 109.0),
        incumbent_snapshot=_snapshot(109.00005),
        cost_match_tolerance_usd=1.0e-4,
    )

    update = apply_cost_oracle(bracket, evidence, expected_cost_cap_usd=110.0)

    assert update.disposition.status == "audited_feasible"
    assert update.bracket.upper_bound_usd == 109.00005


def test_only_scoped_global_infeasibility_can_raise_the_lower_bound() -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    ambiguous = replace(_infeasible(110.0), active_master_globally_infeasible=False)

    update = apply_cost_oracle(bracket, ambiguous, expected_cost_cap_usd=110.0)

    assert update.disposition.status == "unresolved"
    assert update.bracket == bracket


def test_timeout_is_fail_closed_and_never_reinterpreted_as_infeasible() -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))

    result = run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: CostOracleEvidence(
            cost_cap_usd=cap,
            active_master_globally_infeasible=False,
            incumbent_snapshot=None,
            all_inactive_states_screened=False,
            final_full_state_audit_passed=False,
            residual_audit_passed=False,
            audited_operating_cost_usd=None,
            termination="maxTimeLimit",
        ),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=8,
    )

    assert result.status == "unresolved"
    assert result.bracket == bracket
    assert result.failure_reason == "cost_decision_oracle_unresolved"


def test_inconsistent_feasible_and_infeasible_evidence_is_rejected() -> None:
    evidence = replace(_feasible(110.0, 109.0), active_master_globally_infeasible=True)

    with pytest.raises(RuntimeError, match="inconsistent"):
        apply_cost_oracle(
            CostBracket(100.0, 120.0, _snapshot(120.0)),
            evidence,
            expected_cost_cap_usd=110.0,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("termination", "maxTimeLimit"),
        ("decision_budget_cap_usd", 109.0),
        ("infeasibility_certificate_schema", "wrong_schema"),
        ("infeasibility_certificate_source", "wrong_source"),
        ("infeasibility_claim_scope", "mathematical_infeasibility"),
    ],
)
def test_infeasibility_requires_exact_scoped_certificate(
    field: str, value: object
) -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))

    update = apply_cost_oracle(
        bracket,
        replace(_infeasible(110.0), **{field: value}),
        expected_cost_cap_usd=110.0,
    )

    assert update.disposition.status == "unresolved"
    assert update.bracket == bracket


def test_outward_ulp_guard_rejects_an_exact_unprotected_boundary() -> None:
    bracket = CostBracket(99.9, 100.0, _snapshot(100.0))
    unguarded = (bracket.upper_bound_usd - bracket.lower_bound_usd) / 100.0

    certificate = acceptance_certificate(
        bracket,
        target_relative_gap=0.0,
        maximum_relative_gap=unguarded,
    )

    assert certificate["relative_gap_to_feasible_incumbent"] == unguarded
    assert certificate["guarded_relative_gap_to_feasible_incumbent"] > unguarded
    assert certificate["maximum_acceptance_passed"] is False


def test_proxy_witness_interval_needs_two_successful_rounds() -> None:
    bracket = CostBracket(
        REAL_FAILURE_LB,
        PROXY_WITNESS_UB,
        _snapshot(PROXY_WITNESS_UB),
    )

    result = run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: _infeasible(cap),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=5,
    )

    assert result.status == "accepted"
    assert len(result.round_checkpoints) == 2
    assert result.certificate["maximum_acceptance_passed"] is True
    assert result.certificate["target_attained"] is False


def test_round_chain_rejects_semantic_tampering_even_with_rehashed_manifest(
    tmp_path: Path,
) -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    result = run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: _infeasible(cap),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=1,
        candidate_id="candidate_5",
        candidate_ordinal=5,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )
    assert result.status == "round_limit"
    round_path = (
        tmp_path / "05_candidate_5" / "cost_decision_rounds" / "01" / "round.json"
    )
    _rewrite_round(
        round_path,
        lambda payload: payload["bracket_after"].__setitem__("lower_bound_usd", 119.0),
    )

    with pytest.raises(RuntimeError, match="recomputed update drifted"):
        load_contiguous_round_checkpoints(
            tmp_path,
            candidate_id="candidate_5",
            candidate_ordinal=5,
            input_contract_sha256="a" * 64,
            predecessor_manifest_sha256="b" * 64,
        )


def test_round_chain_rejects_wrong_cap_and_wrong_termination(
    tmp_path: Path,
) -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: _infeasible(cap),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=1,
        candidate_id="candidate_5",
        candidate_ordinal=5,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )
    round_path = (
        tmp_path / "05_candidate_5" / "cost_decision_rounds" / "01" / "round.json"
    )
    _rewrite_round(
        round_path,
        lambda payload: payload["oracle_evidence"].__setitem__(
            "termination", "maxTimeLimit"
        ),
    )

    with pytest.raises(RuntimeError, match="disposition drifted"):
        load_contiguous_round_checkpoints(
            tmp_path,
            candidate_id="candidate_5",
            candidate_ordinal=5,
            input_contract_sha256="a" * 64,
            predecessor_manifest_sha256="b" * 64,
        )


def test_round_chain_rejects_rehashed_internally_consistent_non_midpoint_cap(
    tmp_path: Path,
) -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: _infeasible(cap),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=1,
        candidate_id="candidate_5",
        candidate_ordinal=5,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )
    round_path = (
        tmp_path / "05_candidate_5" / "cost_decision_rounds" / "01" / "round.json"
    )

    def mutate(payload: dict[str, object]) -> None:
        non_midpoint = 115.0
        payload["cost_cap_usd"] = non_midpoint
        payload["oracle_evidence"]["cost_cap_usd"] = non_midpoint
        payload["oracle_evidence"]["decision_budget_cap_usd"] = non_midpoint
        payload["bracket_after"]["lower_bound_usd"] = non_midpoint

    _rewrite_round(round_path, mutate)

    with pytest.raises(RuntimeError, match="checkpoint cap drifted"):
        load_contiguous_round_checkpoints(
            tmp_path,
            candidate_id="candidate_5",
            candidate_ordinal=5,
            input_contract_sha256="a" * 64,
            predecessor_manifest_sha256="b" * 64,
        )


def test_round_chain_requires_contiguous_directories(tmp_path: Path) -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: _infeasible(cap),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=1,
        candidate_id="candidate_5",
        candidate_ordinal=5,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )
    rounds = tmp_path / "05_candidate_5" / "cost_decision_rounds"
    (rounds / "01").rename(rounds / "02")

    with pytest.raises(RuntimeError, match="not contiguous"):
        load_contiguous_round_checkpoints(
            tmp_path,
            candidate_id="candidate_5",
            candidate_ordinal=5,
            input_contract_sha256="a" * 64,
            predecessor_manifest_sha256="b" * 64,
        )


def test_resume_continues_with_the_next_round(tmp_path: Path) -> None:
    bracket = CostBracket(100.0, 120.0, _snapshot(120.0))
    first = run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, _ordinal: _infeasible(cap),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=0.05,
        maximum_rounds=1,
        candidate_id="candidate_5",
        candidate_ordinal=5,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )
    observed_ordinals: list[int] = []

    second = run_bracketed_cost_bisection(
        bracket,
        oracle=lambda cap, ordinal: (
            observed_ordinals.append(ordinal) or _feasible(cap, cap)
        ),
        target_relative_gap=1.0e-4,
        maximum_relative_gap=0.05,
        maximum_rounds=2,
        candidate_id="candidate_5",
        candidate_ordinal=5,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
        checkpoint_root=tmp_path,
    )

    assert first.status == "round_limit"
    assert second.status == "accepted"
    assert observed_ordinals == [2]
    assert len(second.round_checkpoints) == 2
