from __future__ import annotations

import copy
import json
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments import (
    record_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004_invalidation as invalidation,
)
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005_formal as formal,
)
from src.grid.rts_gmlc_cost_bisection import (
    CostBracket,
    CostOracleEvidence,
    classify_cost_oracle,
    run_bracketed_cost_bisection,
)
from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256
from src.grid.rts_gmlc_exact_cg_runner import ExactCgStageResult


def _snapshot(cost: float = 120.0, proxy: float = 0.3) -> SharedSnapshot:
    values = (("commitment", (0, "G1"), 1.0),)
    return SharedSnapshot(
        values,
        structured_sha256(
            [
                {
                    "component": "commitment",
                    "index": [0, "G1"],
                    "value_float_hex": (1.0).hex(),
                }
            ]
        ),
        proxy,
        cost,
    )


def _fallback_result() -> tuple[ExactCgStageResult, tuple[str, ...]]:
    snapshot = _snapshot()
    all_ids = ("normal", "branch_A11")
    residual = {"passed": True}
    audit = {
        "passed": True,
        "audited_state_ids": list(all_ids),
        "solution_usable": True,
        "shared_snapshot_fixed": True,
        "integer_variables_relaxed": True,
        "residual_audit_passed": True,
        "additional_audits_passed": True,
        "full_feasible_objective": 120.0,
        "callback_record": {
            "passed": True,
            "actual_operating_cost_usd": 120.0,
            "actual_proxy_fraction": 0.29999995,
            "commitment_capability_proxy_fraction": 0.3,
            "residual_audit": residual,
        },
    }
    record = {
        "schema": "rts_gmlc_exact_cg_stage_record_v1",
        "stage": "cost_normalization",
        "sense": "minimize",
        "eligible": False,
        "failure_reason": "final_bound_certificate_exceeds_maximum_acceptance",
        "proxy_floor": 0.2999999,
        "final_shared_snapshot_sha256": snapshot.sha256,
        "final_active_state_ids": ["normal"],
        "iteration_records": [
            {"screen_records": [{"state_id": "branch_A11", "status": "feasible"}]}
        ],
        "certificate": {
            "valid": True,
            "lower_bound": 118.0,
            "upper_bound": 120.0,
            "absolute_gap": 2.0,
            "relative_gap_to_feasible_incumbent": 1.0 / 60.0,
        },
        "maximum_acceptance": {
            "absolute_acceptance_passed": True,
            "relative_acceptance_passed": False,
            "maximum_acceptance_passed": False,
        },
        "final_full_state_audit": audit,
    }
    return ExactCgStageResult(None, record, audited_snapshot=snapshot), all_ids


def _hybrid_fallback_checkpoint() -> tuple[SimpleNamespace, object, dict[str, object]]:
    direct, all_ids = _fallback_result()
    snapshot = direct.audited_snapshot
    assert snapshot is not None
    parent_config_path = Path(
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004.yaml"
    )
    parent_successor = formal.repair004._read_config(parent_config_path)[
        "formal_successor"
    ]
    raw_proxy_certificate = {"valid": True, "lower_bound": 0.3, "upper_bound": 0.3}
    proxy_certificate = formal.repair004._normalized_hybrid_certificate(
        raw_proxy_certificate, snapshot, parent_successor
    )
    proxy_evidence = {
        "schema": formal.repair004.HYBRID_EVIDENCE_SCHEMA,
        "method": "direct_exact_cg",
        "direct_stage_record": {
            "schema": "rts_gmlc_exact_cg_stage_record_v1",
            "stage": "proxy_maximization",
            "eligible": True,
            "certificate": raw_proxy_certificate,
        },
        "level_set_status": "not_required",
        "level_set_rounds": [],
        "fallback_lower_snapshot_sha256": snapshot.sha256,
        "predecessor_evidence_sha256": "a" * 64,
        "certificate": proxy_certificate,
        "accepted_proxy_snapshot": formal._snapshot_payload(snapshot),
        "accepted_proxy_snapshot_sha256": snapshot.sha256,
    }
    repeated_audit = {
        "schema": "rts_gmlc_v4_repair_005_repeated_cost_audit_v1",
        "passed": True,
        "audited_state_ids": list(all_ids),
        "shared_snapshot_sha256": snapshot.sha256,
        "solution_usable": True,
        "shared_snapshot_fixed": True,
        "integer_variables_relaxed": True,
        "residual_audit_passed": True,
        "additional_audits_passed": True,
        "full_feasible_objective": 120.0,
        "callback_record": {
            "passed": True,
            "actual_operating_cost_usd": 120.0,
            "actual_proxy_fraction": 0.3,
            "commitment_capability_proxy_fraction": 0.3,
            "residual_audit": {"passed": True},
        },
    }
    combined = {
        "schema": formal.COMBINED_COST_SCHEMA,
        "valid": True,
        "method": "direct_exact_cg_plus_cost_decision_bisection",
        "lower_bound": 119.0,
        "upper_bound": 120.0,
        "absolute_gap": 1.0,
        "relative_gap_to_feasible_incumbent": 1.0 / 120.0,
        "maximum_acceptance_passed": True,
        "decision_derived_cost_lower_bound": 119.0,
        "ordinary_dual_bound_usd": None,
        "direct_stage_ordinary_dual_bound_usd": 118.0,
        "decision_round_count": 1,
        "decision_cap_is_ordinary_dual_bound": False,
    }
    cost_evidence = {
        "schema": "rts_gmlc_v4_repair_005_cost_normalization_evidence_v1",
        "method": "direct_exact_cg_plus_cost_decision_bisection",
        "direct_stage_record": direct.stage_record,
        "initial_direct_upper_snapshot": formal._snapshot_payload(snapshot),
        "initial_direct_upper_snapshot_sha256": snapshot.sha256,
        "combined_certificate": combined,
        "cost_decision_status": "accepted",
        "cost_decision_rounds": [
            {"round_ordinal": 1, "round_sha256": "b" * 64, "manifest_sha256": "c" * 64}
        ],
        "cost_decision_predecessor_sha256": "d" * 64,
        "cost_decision_cross_attempt_resume_allowed": False,
        "final_repeated_full_state_audit": repeated_audit,
        "accepted_cost_snapshot": formal._snapshot_payload(snapshot),
        "accepted_cost_snapshot_sha256": snapshot.sha256,
        "proxy_floor": 0.2999999,
    }
    primary_regret = {
        "schema": "rts_gmlc_primary_proxy_regret_certificate_v1",
        "stage_one_certified_upper_bound": 0.3,
        "final_commitment_capability_proxy_fraction": 0.3,
        "observed_regret_upper_bound": 0.0,
        "stage_one_actual_absolute_gap": 0.0,
        "proxy_floor_tolerance": 1.0e-7,
        "numerical_audit_allowance": 1.0e-6,
        "derived_allowed_regret": 1.1e-6,
        "hard_maximum": 0.0010011,
        "passed": True,
    }
    candidate = formal.v4._Candidate(
        requested_candidate_id="q_proxy_delta_0p0200",
        source="q_proxy_repair_003_hybrid_certificate",
        relative_cost_budget_delta=0.02,
        cost_budget_usd=121.0,
        operating_cost_usd=120.0,
        reactive_proxy_fraction=0.3,
        commitment_sha256=formal.v4._commitment_sha256(()),
        dispatch_sha256=formal.v4._dispatch_sha256((), (), ()),
        commitment=(),
        startup=(),
        shutdown=(),
        generation_mw=(),
        branch_flows_mw=(),
        dc_flows_mw=(),
        reserve_up_mw=(),
        stage_audits={
            "proxy_maximization_hybrid": proxy_evidence,
            "cost_normalization_hybrid": cost_evidence,
            "primary_proxy_regret": primary_regret,
        },
        residual_audit={"passed": True},
    )
    controls = [
        {
            "mode": (
                "verified_repair_004_prefix"
                if ordinal <= 4
                else "direct_then_cost_decision_bisection"
            ),
            "relative_cost_budget_delta": delta,
        }
        for ordinal, delta in enumerate((0.001, 0.0025, 0.005, 0.01, 0.02, 0.05), 1)
    ]
    context = SimpleNamespace(
        config={
            "preregistration": {"id": "repair005-test"},
            "formal_solver": {
                "primary_regret": {
                    "proxy_floor_tolerance": 1.0e-7,
                    "numerical_audit_allowance": 1.0e-6,
                    "hard_maximum": 0.0010011,
                },
                "stages": {
                    "cost_normalization": {"proxy_floor_absolute_tolerance": 1.0e-7}
                },
            },
        },
        input_contract={
            "predecessor_repair_004": {"config_path": str(parent_config_path)},
            "formal_successor": {
                "candidate_controls": controls,
                "cost_match_tolerance_usd": 1.0e-4,
                "cost_decision_maximum_rounds": 4,
                "target_relative_gap": 1.0e-4,
                "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
            },
        },
        input_contract_sha256="e" * 64,
        selection=SimpleNamespace(
            states=tuple(SimpleNamespace(state_id=state_id) for state_id in all_ids)
        ),
    )
    evidence = {
        "schema": formal.HYBRID_EVIDENCE_SCHEMA,
        "proxy_evidence": proxy_evidence,
        "cost_evidence": cost_evidence,
        "accepted_proxy_snapshot": formal._snapshot_payload(snapshot),
        "accepted_proxy_snapshot_sha256": snapshot.sha256,
    }
    document = formal._checkpoint_payload(
        context,
        5,
        candidate,
        mode="direct_then_cost_decision_bisection",
        evidence=evidence,
    )
    return context, candidate, document


def test_config_locks_four_predecessor_checkpoints_and_candidate_hashes() -> None:
    config = formal._read_config(formal.DEFAULT_CONFIG_PATH)
    predecessor = config["predecessor_repair_004"]

    assert predecessor["candidate_checkpoint_manifest_sha256s"] == [
        "2bd1d1c6843c6397248d4cd5531f1911c2f91036174b00af0877987d01b74c41",
        "98ab92e1a59f668203a66988b324cca75d764c4ed440fdf1c547d2279a00e8b2",
        "42830c97b66be3f80231757aaa0f1a1732cfa5fa4d400f0c33be3b508c764f51",
        "f929c097922937f4f85ca86c3714da2095060a10d59b1a14dfc3a51ca6d0759c",
    ]
    assert predecessor["candidate_json_sha256s"] == [
        "60317c6f2ead2467d6a6e3b7e23dab692d054e8cb3e8f11691144ec2f32f737e",
        "451a6cb559489f67e0b3a1d2e4f0fc02b9295238b0cf05aee06c9cc99df7c0b0",
        "913c1f46d03f506c0c04f794eab5b6c64aabd084ac15d0f7f74b25472fe33b67",
        "5efa62039ad86e3129d51d3ceba7a198311c9cfe9eb7048e3f78acf128d72448",
    ]
    assert (
        config["formal_successor"]["cost_decision_cross_attempt_resume_allowed"]
        is False
    )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cost_decision_round_schema", "drifted"),
        ("cost_decision_maximum_rounds", 5),
    ],
)
def test_config_rejects_cost_round_contract_drift(
    tmp_path: Path, field: str, value: object
) -> None:
    config = yaml.safe_load(formal.DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    config["formal_successor"][field] = value
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="frozen contract drifted"):
        formal._read_config(path)


def test_prefix_wrapper_binds_source_without_claiming_recomputation() -> None:
    source = SimpleNamespace(
        source="old",
        stage_audits={"old": {"valid": True}},
    )
    candidate = formal.v4._Candidate(
        requested_candidate_id="q_proxy_delta_0p0010",
        source="old",
        relative_cost_budget_delta=0.001,
        cost_budget_usd=121.0,
        operating_cost_usd=120.0,
        reactive_proxy_fraction=0.3,
        commitment_sha256=formal.v4._commitment_sha256(()),
        dispatch_sha256=formal.v4._dispatch_sha256((), (), ()),
        commitment=(),
        startup=(),
        shutdown=(),
        generation_mw=(),
        branch_flows_mw=(),
        dc_flows_mw=(),
        reserve_up_mw=(),
        stage_audits=source.stage_audits,
        residual_audit={"passed": True},
    )
    context = SimpleNamespace(
        input_contract={
            "predecessor_repair_004": {
                "preregistration_manifest_sha256": "a" * 64,
                "input_contract_sha256": "b" * 64,
                "candidate_checkpoint_manifest_sha256s": ["c" * 64] * 4,
                "candidate_json_sha256s": ["d" * 64] * 4,
            }
        }
    )

    imported, observed, evidence = formal._prefix_candidate(
        context, 1, (candidate, _snapshot())
    )

    assert imported.source == "repair_005_verified_repair_004_prefix"
    assert evidence["source_imported_as_recomputed"] is False
    assert evidence["source_checkpoint_validated_by_repair_004_runner"] is True
    assert observed == _snapshot()


def test_exact_fallback_validator_returns_the_real_cost_bracket() -> None:
    result, all_ids = _fallback_result()

    bracket = formal._validated_cost_fallback_bracket(
        result,
        all_state_ids=all_ids,
        cost_tolerance_usd=1.0e-4,
        proxy_tolerance=1.0e-7,
    )

    assert bracket is not None
    assert bracket.lower_bound_usd == 118.0
    assert bracket.upper_bound_usd == 120.0


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("stage",), "proxy_maximization"),
        (("maximum_acceptance", "absolute_acceptance_passed"), False),
        (("maximum_acceptance", "relative_acceptance_passed"), True),
        (("final_full_state_audit", "solution_usable"), False),
        (("final_full_state_audit", "audited_state_ids"), ["normal"]),
        (
            (
                "final_full_state_audit",
                "callback_record",
                "actual_operating_cost_usd",
            ),
            119.0,
        ),
    ],
)
def test_any_exact_trigger_drift_is_fail_closed(
    path: tuple[str, ...], value: object
) -> None:
    result, all_ids = _fallback_result()
    record = result.stage_record.copy()
    cursor = record
    for key in path[:-1]:
        cursor[key] = dict(cursor[key])
        cursor = cursor[key]
    cursor[path[-1]] = value

    assert (
        formal._validated_cost_fallback_bracket(
            replace(result, stage_record=record),
            all_state_ids=all_ids,
            cost_tolerance_usd=1.0e-4,
            proxy_tolerance=1.0e-7,
        )
        is None
    )


def test_exact_effective_cap_subtracts_the_frozen_tolerance() -> None:
    cap = 1127994.2202963952
    budget = formal._budget_for_exact_effective_cap(cap, 1.0e-4)

    assert budget + 1.0e-4 == cap


def test_real_adapter_infeasibility_shape_is_cap_specific() -> None:
    cap = 110.0
    separation = {
        "schema": "rts_gmlc_level_set_bound_only_early_separation_v1",
        "source": "active_budget_capped_decision_mip_global_infeasibility",
        "claim_scope": "no_budget_feasible_solution_at_or_above_this_proxy_floor",
        "decision_budget_cap_usd": cap,
    }
    result = ExactCgStageResult(
        None,
        {
            "bound_only_early_separation": separation,
            "master_records": [
                {
                    "callback_record": {
                        "decision_mip": {
                            "solver_api_termination_condition": (
                                "TerminationCondition.provenInfeasible"
                            )
                        }
                    }
                }
            ],
        },
    )

    evidence = formal.level_evidence_from_stage_result(
        result,
        expected_cap_usd=cap,
        all_state_ids=("normal",),
        cost_tolerance_usd=1.0e-4,
    )

    assert classify_cost_oracle(evidence).status == "certified_infeasible_at_cap"
    assert evidence.termination == "TerminationCondition.provenInfeasible"
    assert evidence.decision_budget_cap_usd == cap


def test_combined_cost_certificate_never_calls_a_decision_cap_a_dual_bound() -> None:
    certificate = formal._combined_cost_certificate(
        {
            "schema": "rts_gmlc_cost_decision_bisection_certificate_v1",
            "valid": True,
            "lower_bound": 110.0,
            "upper_bound": 111.0,
            "maximum_acceptance_passed": True,
        },
        method="direct_exact_cg_plus_cost_decision_bisection",
        direct_lower_bound_usd=100.0,
        decision_round_count=1,
    )

    assert certificate["decision_derived_cost_lower_bound"] == 110.0
    assert certificate["ordinary_dual_bound_usd"] is None
    assert certificate["decision_cap_is_ordinary_dual_bound"] is False


def test_direct_eligible_cost_bypasses_decision_bisection(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    direct = ExactCgStageResult(
        snapshot,
        {
            "eligible": True,
            "certificate": {
                "lower_bound": 119.9,
                "upper_bound": 120.0,
                "absolute_gap": 0.1,
                "relative_gap_to_feasible_incumbent": 0.1 / 120.0,
            },
            "maximum_acceptance": {
                "target_attained": False,
                "maximum_acceptance_passed": True,
            },
            "final_full_state_audit": {"passed": True},
        },
        audited_snapshot=snapshot,
    )
    handle = object()

    class Adapter:
        def __init__(self, **_kwargs: object) -> None:
            self.final_handles = {"cost_normalization": handle}

        def callbacks(self) -> object:
            return object()

    monkeypatch.setattr(formal, "FormalCgModelAdapter", Adapter)
    monkeypatch.setattr(formal, "run_exact_cg_stage", lambda **_kwargs: direct)
    monkeypatch.setattr(
        formal.repair004,
        "_stage_limits",
        lambda *_args: SimpleNamespace(final_audit_seconds=10.0),
    )
    monkeypatch.setattr(
        formal,
        "run_bracketed_cost_bisection",
        lambda *_args, **_kwargs: pytest.fail("decision fallback must not run"),
    )
    context = SimpleNamespace(
        input_contract={
            "formal_successor": {
                "cost_match_tolerance_usd": 1.0e-4,
                "target_relative_gap": 1.0e-4,
                "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
            }
        },
        config={
            "formal_solver": {
                "stages": {
                    "cost_normalization": {
                        "target_relative_gap": 1.0e-4,
                        "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
                        "maximum_accepted_absolute_gap": None,
                        "proxy_floor_absolute_tolerance": 1.0e-7,
                    }
                }
            },
            "candidate_frontier": {},
            "candidate_snapshot": {},
        },
    )
    problem = SimpleNamespace(
        all_state_ids=("normal",), initial_active_state_ids=("normal",)
    )

    observed = formal._run_hybrid_cost_normalization(
        context=context,
        problem=problem,
        proxy_floor=0.29,
        progress=SimpleNamespace(),
        candidate_log_root=Path("unused"),
        event_context={},
        deadline_monotonic=10.0,
        candidate_id="q_proxy_delta_0p0200",
        candidate_ordinal=5,
    )

    assert observed.decision_bisection is None
    assert observed.final_handle is handle
    assert observed.combined_certificate["ordinary_dual_bound_usd"] is None


def test_repeated_cost_audit_is_clipped_to_candidate_remaining_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    snapshot = _snapshot()
    observed_calls: list[object] = []
    handle = object()

    class Adapter:
        def __init__(self, **_kwargs: object) -> None:
            self.final_handles = {"level_set_budget_feasibility": handle}

        def audit_full_state(self, call: object) -> object:
            observed_calls.append(call)
            return SimpleNamespace(
                solution_usable=True,
                shared_snapshot_fixed=True,
                integer_variables_relaxed=True,
                residual_audit_passed=True,
                additional_audits_passed=True,
                shared_snapshot_sha256=snapshot.sha256,
                audited_state_ids=("normal",),
                full_feasible_objective=120.0,
                record={"passed": True},
            )

    monkeypatch.setattr(formal, "FormalCgModelAdapter", Adapter)
    monkeypatch.setattr(formal, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        formal.repair004,
        "_stage_limits",
        lambda *_args: SimpleNamespace(final_audit_seconds=10.0),
    )
    context = SimpleNamespace(
        input_contract={"formal_successor": {"target_relative_gap": 1.0e-4}},
        config={
            "formal_solver": {},
            "candidate_frontier": {},
            "candidate_snapshot": {},
        },
    )

    evidence, observed_handle = formal._repeat_cost_audit(
        context=context,
        problem=SimpleNamespace(all_state_ids=("normal",)),
        snapshot=snapshot,
        proxy_floor=0.29,
        progress=SimpleNamespace(),
        log_root=Path("unused"),
        event_context={},
        deadline_monotonic=103.5,
    )

    assert len(observed_calls) == 1
    assert observed_calls[0].time_limit_seconds == pytest.approx(3.5)
    assert evidence["passed"] is True
    assert observed_handle is handle


def test_repeated_cost_audit_rejects_exhausted_candidate_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(formal, "monotonic", lambda: 100.0)
    monkeypatch.setattr(
        formal,
        "FormalCgModelAdapter",
        lambda **_kwargs: pytest.fail("adapter must not be created after deadline"),
    )

    with pytest.raises(
        RuntimeError,
        match="candidate deadline exhausted before repeated cost audit",
    ):
        formal._repeat_cost_audit(
            context=SimpleNamespace(),
            problem=SimpleNamespace(),
            snapshot=_snapshot(),
            proxy_floor=0.29,
            progress=SimpleNamespace(),
            log_root=Path("unused"),
            event_context={},
            deadline_monotonic=100.0,
        )


def test_joint_worker_command_uses_only_the_repair_005_module() -> None:
    command = formal._joint_worker_command(
        python_executable=Path("python.exe"),
        config_path=Path("config.yaml"),
        output_root=Path("output"),
        candidate_id="candidate",
        initial_strategy="reference_provider",
        worker_result=Path("result"),
        native_log=Path("native.log"),
        call_manifest_sha256="a" * 64,
    )

    assert formal._SUCCESSOR_MODULE in command
    assert not any("repair_004_formal" in item for item in command)


def test_real_repair_004_evidence_publishes_an_invalidation_copy(
    tmp_path: Path,
) -> None:
    registration = invalidation._validate_parent_output(invalidation.OUTPUT_ROOT)
    evidence = invalidation._validate_attempt(invalidation.ATTEMPT_LOG_ROOT)
    invalidation._validate_sources(Path("."))
    payload = invalidation._payload(registration, evidence)
    target = tmp_path / "invalidation"

    invalidation._publish_payload(target, payload)

    formal._verify_manifest(target)
    assert (
        json.loads((target / "invalidation.json").read_text(encoding="utf-8"))
        == payload
    )
    assert payload["valid_candidate_checkpoint_count"] == 4
    assert payload["candidate_frontier_artifact_published"] is False
    assert payload["joint_ac_solver_call_count"] == 0
    assert payload["failure_is_infeasibility_evidence"] is False


@pytest.mark.parametrize("evidence_class", ["checkpoint", "attempt", "lease", "source"])
def test_repair_004_invalidation_rejects_each_evidence_class_drift(
    monkeypatch: pytest.MonkeyPatch,
    evidence_class: str,
) -> None:
    if evidence_class == "checkpoint":
        hashes = list(invalidation.EXPECTED_CHECKPOINT_MANIFEST_SHA256S)
        hashes[0] = "0" * 64
        monkeypatch.setattr(
            invalidation, "EXPECTED_CHECKPOINT_MANIFEST_SHA256S", tuple(hashes)
        )
    elif evidence_class == "attempt":
        hashes = dict(invalidation.EXPECTED_ATTEMPT_FILE_SHA256)
        hashes["progress.jsonl"] = "0" * 64
        monkeypatch.setattr(invalidation, "EXPECTED_ATTEMPT_FILE_SHA256", hashes)
    elif evidence_class == "lease":
        monkeypatch.setattr(invalidation, "EXPECTED_FAILED_LEASE_SHA256", "0" * 64)
    else:
        hashes = dict(invalidation.EXPECTED_SOURCE_SHA256)
        first = next(iter(hashes))
        hashes[first] = "0" * 64
        monkeypatch.setattr(invalidation, "EXPECTED_SOURCE_SHA256", hashes)

    with pytest.raises(RuntimeError, match="drifted"):
        if evidence_class in {"checkpoint", "lease"}:
            invalidation._validate_parent_output(invalidation.OUTPUT_ROOT)
        elif evidence_class == "attempt":
            invalidation._validate_attempt(invalidation.ATTEMPT_LOG_ROOT)
        else:
            invalidation._validate_sources(Path("."))


def _synthetic_invalidation_payload(config: dict[str, object]) -> dict[str, object]:
    predecessor = config["predecessor_repair_004"]
    assert isinstance(predecessor, dict)
    return {
        "status": predecessor["required_invalidation_status"],
        "preregistration_manifest_sha256": predecessor[
            "preregistration_manifest_sha256"
        ],
        "input_contract_sha256": predecessor["input_contract_sha256"],
        "valid_candidate_checkpoint_count": 4,
        "candidate_checkpoint_manifest_sha256s": predecessor[
            "candidate_checkpoint_manifest_sha256s"
        ],
        "candidate_json_sha256s": predecessor["candidate_json_sha256s"],
        "failure_is_infeasibility_evidence": False,
        "direct_cost_certificate_valid": True,
        "direct_cost_full_state_audit_passed": True,
        "direct_cost_residual_audit_passed": True,
        "candidate_frontier_artifact_published": False,
        "joint_ac_solver_call_count": 0,
        "repair_004_resume_allowed": False,
        "successor_must_restart_from_candidate_ordinal": 5,
        "scientific_protocol_changed": False,
    }


def test_parent_invalidation_manifest_is_required_and_immutable(tmp_path: Path) -> None:
    config = formal._read_config(formal.DEFAULT_CONFIG_PATH)
    root = tmp_path / "invalidation"
    invalidation._publish_payload(root, _synthetic_invalidation_payload(config))
    config["predecessor_repair_004"]["invalidation_manifest_sha256"] = formal._sha256(
        root / "SHA256SUMS"
    )

    formal._verify_parent_invalidation(config, root)
    payload = json.loads((root / "invalidation.json").read_text(encoding="utf-8"))
    payload["repair_004_resume_allowed"] = True
    formal.v4._write_exact_json(root / "invalidation.json", payload)
    formal.repair004.repair._write_recursive_manifest(root)

    with pytest.raises(RuntimeError, match="invalidation manifest drifted"):
        formal._verify_parent_invalidation(config, root)


def test_preregistration_reader_rejects_manifest_tamper(tmp_path: Path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text("schema: test\n", encoding="utf-8")
    context = SimpleNamespace(
        config_path=config_path,
        config={
            "preregistration": {
                "schema": "repair005-test",
                "id": "repair005-test",
                "status": "test",
            },
            "formal_solver": {"algorithm": "test"},
        },
        input_contract={"schema": "test"},
        input_contract_sha256=formal.common_input_signature_sha256({"schema": "test"}),
    )
    target = tmp_path / "output" / "preregistration"
    expected = formal._registration_payload(context)

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        formal.v4._write_exact_json(staging / "registration.json", expected)

    formal.v4._publish_immutable_payload(target, writer)
    assert formal._require_preregistration(context, tmp_path / "output") == expected
    (target / "SHA256SUMS").write_text("0" * 64 + "  config.yaml\n", encoding="ascii")

    with pytest.raises(RuntimeError, match="manifest"):
        formal._require_preregistration(context, tmp_path / "output")


def test_prefix_checkpoint_round_trip_rejects_rehashed_semantic_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    snapshot = _snapshot()
    source = formal.v4._Candidate(
        requested_candidate_id="q_proxy_delta_0p0010",
        source="repair_004_source",
        relative_cost_budget_delta=0.001,
        cost_budget_usd=121.0,
        operating_cost_usd=120.0,
        reactive_proxy_fraction=0.3,
        commitment_sha256=formal.v4._commitment_sha256(()),
        dispatch_sha256=formal.v4._dispatch_sha256((), (), ()),
        commitment=(),
        startup=(),
        shutdown=(),
        generation_mw=(),
        branch_flows_mw=(),
        dc_flows_mw=(),
        reserve_up_mw=(),
        stage_audits={"source": {"valid": True}},
        residual_audit={"passed": True},
    )
    predecessor = {
        "preregistration_manifest_sha256": "a" * 64,
        "input_contract_sha256": "b" * 64,
        "candidate_checkpoint_manifest_sha256s": ["c" * 64] * 4,
        "candidate_json_sha256s": ["d" * 64] * 4,
    }
    context = SimpleNamespace(
        config={"preregistration": {"id": "repair005-test"}},
        input_contract={
            "predecessor_repair_004": predecessor,
            "formal_successor": {
                "candidate_controls": [
                    {
                        "mode": "verified_repair_004_prefix",
                        "relative_cost_budget_delta": 0.001,
                    }
                ]
            },
        },
        input_contract_sha256="e" * 64,
    )
    imported, accepted, evidence = formal._prefix_candidate(
        context, 1, (source, snapshot)
    )
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)
    monkeypatch.setattr(
        formal,
        "_verified_source_prefix",
        lambda _contract: ((source, snapshot),) * 4,
    )

    saved = formal._save_candidate_checkpoint(
        context,
        tmp_path,
        1,
        imported,
        mode="verified_repair_004_prefix",
        evidence=evidence,
    )
    assert saved == (imported, accepted)
    checkpoint = tmp_path / "candidate_checkpoints" / "01_q_proxy_delta_0p0010"
    assert formal._load_candidate_checkpoint(context, tmp_path, 1) == saved

    document = json.loads((checkpoint / "candidate.json").read_text(encoding="utf-8"))
    document["evidence"]["source_candidate_json_sha256"] = "f" * 64
    formal.v4._write_exact_json(checkpoint / "candidate.json", document)
    formal.repair004.repair._write_recursive_manifest(checkpoint)
    formal._verify_manifest(checkpoint)

    with pytest.raises(RuntimeError, match="prefix evidence drifted"):
        formal._load_candidate_checkpoint(context, tmp_path, 1)


@pytest.mark.parametrize(
    ("tamper", "message"),
    [
        ("direct_trigger", "fallback cost evidence drifted"),
        ("final_audit", "persisted cost audit drifted"),
        ("primary_regret", "primary regret evidence drifted"),
    ],
)
def test_hybrid_checkpoint_rejects_rehashed_semantic_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tamper: str,
    message: str,
) -> None:
    context, candidate, document = _hybrid_fallback_checkpoint()
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)
    monkeypatch.setattr(formal, "_validate_round_artifacts", lambda *_args: None)
    assert formal._validate_checkpoint_document(document, context, 5)[0] == candidate

    tampered = copy.deepcopy(document)
    candidate_audits = tampered["candidate"]["stage_audits"]
    evidence = tampered["evidence"]
    if tamper == "direct_trigger":
        for cost in (
            evidence["cost_evidence"],
            candidate_audits["cost_normalization_hybrid"],
        ):
            cost["direct_stage_record"]["final_full_state_audit"][
                "solution_usable"
            ] = False
    elif tamper == "final_audit":
        for cost in (
            evidence["cost_evidence"],
            candidate_audits["cost_normalization_hybrid"],
        ):
            cost["final_repeated_full_state_audit"]["solution_usable"] = False
    else:
        candidate_audits["primary_proxy_regret"]["passed"] = False

    checkpoint = tmp_path / "candidate_checkpoints" / "05_q_proxy_delta_0p0200"
    checkpoint.mkdir(parents=True)
    formal.v4._write_exact_json(checkpoint / "candidate.json", tampered)
    formal.repair004.repair._write_recursive_manifest(checkpoint)
    formal._verify_manifest(checkpoint)

    with pytest.raises(RuntimeError, match=message):
        formal._load_candidate_checkpoint(context, tmp_path, 5)


def test_hybrid_checkpoint_rejects_rehashed_proxy_round_tamper(
    tmp_path: Path,
) -> None:
    checkpoint = tmp_path / "candidate_checkpoints" / "05_q_proxy_delta_0p0200"
    round_root = checkpoint / "level_set_rounds" / "01"
    round_root.mkdir(parents=True)
    candidate = SimpleNamespace(requested_candidate_id="q_proxy_delta_0p0200")
    context = SimpleNamespace(input_contract_sha256="a" * 64)
    lower_snapshot = {"sha256": "b" * 64}
    accepted_snapshot = {"sha256": "c" * 64}
    document = {
        "schema": "rts_gmlc_proxy_level_set_round_v1",
        "candidate_id": candidate.requested_candidate_id,
        "candidate_ordinal": 5,
        "round_ordinal": 1,
        "input_contract_sha256": context.input_contract_sha256,
        "predecessor_manifest_sha256": "d" * 64,
        "bracket_before": {
            "lower_bound": 0.2,
            "upper_bound": 0.4,
            "lower_snapshot": lower_snapshot,
        },
        "bracket_after": {
            "lower_bound": 0.3,
            "upper_bound": 0.3001,
            "lower_snapshot": accepted_snapshot,
        },
    }

    def reference() -> dict[str, object]:
        formal.v4._write_exact_json(round_root / "round.json", document)
        formal.repair004.repair._write_recursive_manifest(round_root)
        return {
            "round_ordinal": 1,
            "round_sha256": formal._sha256(round_root / "round.json"),
            "manifest_sha256": formal._sha256(round_root / "SHA256SUMS"),
        }

    proxy = {
        "method": "direct_max_or_level_set_bisection",
        "level_set_rounds": [reference()],
        "predecessor_evidence_sha256": "d" * 64,
        "fallback_lower_snapshot_sha256": lower_snapshot["sha256"],
        "accepted_proxy_snapshot_sha256": accepted_snapshot["sha256"],
        "certificate": {"lower_bound": 0.3, "upper_bound": 0.3001},
    }
    evidence = {
        "proxy_evidence": proxy,
        "cost_evidence": {"method": "direct_exact_cg", "cost_decision_rounds": []},
    }
    formal._validate_round_artifacts(checkpoint, context, 5, candidate, evidence)

    document["candidate_id"] = "tampered"
    proxy["level_set_rounds"] = [reference()]
    with pytest.raises(RuntimeError, match="level-set round chain drifted"):
        formal._validate_round_artifacts(checkpoint, context, 5, candidate, evidence)


def _publish_hybrid_cost_round_checkpoint(
    tmp_path: Path,
    *,
    direct_lower_bound_usd: float = 119.8,
    maximum_rounds: int = 4,
) -> tuple[SimpleNamespace, Path]:
    context, candidate, document = _hybrid_fallback_checkpoint()
    checkpoint_parent = tmp_path / "candidate_checkpoints"
    initial_snapshot = _snapshot()
    persisted_costs = (
        document["evidence"]["cost_evidence"],
        document["candidate"]["stage_audits"]["cost_normalization_hybrid"],
    )
    for persisted in persisted_costs:
        certificate = persisted["direct_stage_record"]["certificate"]
        certificate["lower_bound"] = direct_lower_bound_usd
        certificate["absolute_gap"] = 120.0 - direct_lower_bound_usd
        certificate["relative_gap_to_feasible_incumbent"] = (
            120.0 - direct_lower_bound_usd
        ) / 120.0
    cost_evidence = persisted_costs[0]
    direct_certificate = cost_evidence["direct_stage_record"]["certificate"]
    predecessor_sha256 = formal.common_input_signature_sha256(
        {
            "input_contract_sha256": context.input_contract_sha256,
            "candidate_ordinal": 5,
            "candidate_id": candidate.requested_candidate_id,
            "proxy_floor": cost_evidence["proxy_floor"],
            "initial_lower_bound_usd": direct_certificate["lower_bound"],
            "initial_upper_bound_usd": direct_certificate["upper_bound"],
            "initial_upper_snapshot_sha256": initial_snapshot.sha256,
            "cost_match_tolerance_usd": context.input_contract["formal_successor"][
                "cost_match_tolerance_usd"
            ],
        }
    )

    def infeasible_oracle(cap: float, _round_ordinal: int) -> CostOracleEvidence:
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

    bisection = run_bracketed_cost_bisection(
        CostBracket(direct_lower_bound_usd, 120.0, initial_snapshot),
        oracle=infeasible_oracle,
        target_relative_gap=1.0e-4,
        maximum_relative_gap=1.0e-3,
        maximum_rounds=maximum_rounds,
        candidate_id=candidate.requested_candidate_id,
        candidate_ordinal=5,
        input_contract_sha256=context.input_contract_sha256,
        predecessor_manifest_sha256=predecessor_sha256,
        checkpoint_root=checkpoint_parent,
    )
    assert bisection.status == "accepted"
    assert 1 <= len(bisection.round_checkpoints) <= maximum_rounds

    checkpoint = formal.v4._candidate_checkpoint_path(
        tmp_path, 5, candidate.requested_candidate_id
    )
    references = formal._round_references(checkpoint / "cost_decision_rounds")
    combined = formal._combined_cost_certificate(
        bisection.certificate,
        method="direct_exact_cg_plus_cost_decision_bisection",
        direct_lower_bound_usd=direct_lower_bound_usd,
        decision_round_count=len(references),
    )
    for persisted in persisted_costs:
        persisted["combined_certificate"] = combined
        persisted["cost_decision_rounds"] = references
        persisted["cost_decision_predecessor_sha256"] = predecessor_sha256
    formal.v4._write_exact_json(checkpoint / "candidate.json", document)
    formal.repair004.repair._write_recursive_manifest(checkpoint)
    return context, checkpoint


def test_hybrid_cost_round_chain_round_trips_a_combined_certificate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context, _checkpoint = _publish_hybrid_cost_round_checkpoint(tmp_path)
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)

    loaded = formal._load_candidate_checkpoint(context, tmp_path, 5)

    assert loaded is not None
    assert loaded[0].operating_cost_usd == 120.0


def test_hybrid_cost_round_chain_rejects_rehashed_fifth_round(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    context, _checkpoint = _publish_hybrid_cost_round_checkpoint(
        tmp_path,
        direct_lower_bound_usd=118.0,
        maximum_rounds=5,
    )
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)

    with pytest.raises(RuntimeError, match="fallback cost evidence drifted"):
        formal._load_candidate_checkpoint(context, tmp_path, 5)


@pytest.mark.parametrize("tamper", ["final_bracket", "combined_certificate"])
def test_hybrid_cost_round_chain_rejects_rehashed_final_tamper(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    tamper: str,
) -> None:
    context, checkpoint = _publish_hybrid_cost_round_checkpoint(tmp_path)
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_args: None)
    assert formal._load_candidate_checkpoint(context, tmp_path, 5) is not None

    if tamper == "final_bracket":
        final_round = checkpoint / "cost_decision_rounds" / "01"
        payload = json.loads((final_round / "round.json").read_text(encoding="utf-8"))
        payload["bracket_after"]["lower_bound_usd"] = 119.85
        formal.v4._write_exact_json(final_round / "round.json", payload)
        formal.repair004.repair._write_recursive_manifest(final_round)
        expected = "recomputed update drifted"
    else:
        document = json.loads(
            (checkpoint / "candidate.json").read_text(encoding="utf-8")
        )
        for persisted in (
            document["evidence"]["cost_evidence"],
            document["candidate"]["stage_audits"]["cost_normalization_hybrid"],
        ):
            persisted["combined_certificate"]["lower_bound"] = 119.85
            persisted["combined_certificate"][
                "decision_derived_cost_lower_bound"
            ] = 119.85
        formal.v4._write_exact_json(checkpoint / "candidate.json", document)
        expected = "final cost certificate drifted"
    formal.repair004.repair._write_recursive_manifest(checkpoint)

    with pytest.raises(RuntimeError, match=expected):
        formal._load_candidate_checkpoint(context, tmp_path, 5)


def test_first_solver_path_begins_at_candidate_five(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    snapshot = _snapshot()
    controls = [
        {
            "mode": (
                "verified_repair_004_prefix"
                if ordinal <= 4
                else "direct_then_cost_decision_bisection"
            ),
            "relative_cost_budget_delta": delta,
        }
        for ordinal, delta in enumerate((0.001, 0.0025, 0.005, 0.01, 0.02, 0.05), 1)
    ]
    candidates = [
        SimpleNamespace(
            requested_candidate_id=formal.v4._requested_candidate_id(
                float(control["relative_cost_budget_delta"])
            ),
            commitment_sha256="a" * 64,
            dispatch_sha256="b" * 64,
        )
        for control in controls[:4]
    ]
    events: list[tuple[str, dict[str, object]]] = []
    solver_ordinals: list[int] = []

    class Progress:
        def __init__(self, *_args: object, **_kwargs: object) -> None:
            pass

        def emit(self, event: str, **payload: object) -> None:
            events.append((event, payload))

    context = SimpleNamespace(
        config={
            "preregistration": {"id": "repair005-test"},
            "formal_solver": {
                "progress_logging": {"log_directory": str(tmp_path / "logs")},
                "time_limits_seconds": {"per_candidate_total": 43200.0},
            },
        },
        input_contract={"formal_successor": {"candidate_controls": controls}},
        input_contract_sha256="c" * 64,
    )
    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: {})
    monkeypatch.setattr(formal, "JsonlProgressWriter", Progress)
    monkeypatch.setattr(
        formal,
        "_verified_source_prefix",
        lambda _contract: tuple((candidate, snapshot) for candidate in candidates),
    )
    monkeypatch.setattr(formal, "_load_candidate_checkpoint", lambda *_args: None)
    monkeypatch.setattr(
        formal,
        "_prefix_candidate",
        lambda _context, ordinal, item: (
            candidates[ordinal - 1],
            snapshot,
            {
                "source_checkpoint_manifest_sha256": "d" * 64,
                "source_candidate_json_sha256": "e" * 64,
            },
        ),
    )
    monkeypatch.setattr(
        formal,
        "_save_candidate_checkpoint",
        lambda _context, _root, _ordinal, candidate, **_kwargs: (candidate, snapshot),
    )
    monkeypatch.setattr(formal, "_sha256", lambda _path: "f" * 64)

    def first_solver_path(
        _context: object, *, ordinal: int, **_kwargs: object
    ) -> object:
        solver_ordinals.append(ordinal)
        raise RuntimeError("stop at first solver path")

    monkeypatch.setattr(formal, "_hybrid_candidate", first_solver_path)

    with pytest.raises(RuntimeError, match="stop at first solver path"):
        formal._generate_candidate_frontier_unleased(
            context, tmp_path / "output", attempt_id="candidate-test"
        )

    assert solver_ordinals == [5]
    imported = [
        payload for event, payload in events if event == "source_checkpoint_imported"
    ]
    assert [payload["candidate_ordinal"] for payload in imported] == [1, 2, 3, 4]
    assert all(payload["solver_call_count"] == 0 for payload in imported)


@pytest.mark.parametrize("missing_ordinal", range(1, 7))
def test_frontier_rejects_any_missing_checkpoint(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    missing_ordinal: int,
) -> None:
    candidate = SimpleNamespace(requested_candidate_id="candidate")
    monkeypatch.setattr(formal.v4, "_baseline_candidate", lambda _context: candidate)
    monkeypatch.setattr(
        formal,
        "_load_candidate_checkpoint",
        lambda _context, _root, ordinal: (
            None if ordinal == missing_ordinal else (candidate, _snapshot())
        ),
    )
    monkeypatch.setattr(formal, "_sha256", lambda _path: "a" * 64)

    with pytest.raises(RuntimeError, match="all six checkpoints are required"):
        formal._frontier_material(SimpleNamespace(), tmp_path)


@pytest.mark.parametrize(
    ("mutation", "message"),
    [
        ("call", "call registration drifted"),
        ("frontier", "frontier manifest drifted"),
        ("parent", "parent identity drifted"),
        ("lease", "execution lease drifted"),
    ],
)
def test_joint_worker_fails_closed_on_control_identity_drift(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    mutation: str,
    message: str,
) -> None:
    parent_pid = 12345
    attempt_id = "joint-test"
    call_manifest = "a" * 64
    frontier_manifest = "b" * 64
    candidate = SimpleNamespace(candidate_id="candidate")
    result = tmp_path / "worker-result"
    native = tmp_path / "worker.log"
    context = SimpleNamespace(
        config={
            "joint_ac": {
                "initial_strategies": ["reference_provider"],
                "runtime_control": {"parent_watchdog_interval_seconds": 1.0},
            }
        }
    )
    lease = {
        "schema": "execution_lease_v1",
        "pid": parent_pid,
        "stage": "run_joint_ac",
        "attempt_id": "wrong" if mutation == "lease" else attempt_id,
    }
    lease_path = tmp_path / "execution_lease" / "active" / "lease.json"
    lease_path.parent.mkdir(parents=True)
    lease_path.write_text(json.dumps(lease), encoding="utf-8")
    monkeypatch.setattr(formal, "_build_context", lambda _path: context)
    monkeypatch.setattr(formal, "_require_preregistration", lambda *_args: {})
    monkeypatch.setattr(
        formal,
        "_load_candidate_frontier",
        lambda *_args: ([candidate], frontier_manifest),
    )

    def validate_call(*args: object) -> str:
        if mutation == "frontier":
            raise RuntimeError("frontier manifest drifted")
        assert args[-1] == frontier_manifest
        return call_manifest

    monkeypatch.setattr(formal.v4, "_validate_joint_call_registration", validate_call)
    monkeypatch.setattr(
        formal.v4,
        "_load_json",
        lambda *_args: {"parent_pid": parent_pid, "parent_attempt_id": attempt_id},
    )
    monkeypatch.setattr(
        formal.v4,
        "_registered_joint_worker_paths",
        lambda *_args: (result.resolve(), native.resolve(), None),
    )
    monkeypatch.setattr(
        formal.os,
        "getppid",
        lambda: parent_pid + 1 if mutation == "parent" else parent_pid,
    )
    monkeypatch.setattr(
        formal.v4, "ParentProcessWatchdog", lambda *_args, **_kwargs: nullcontext()
    )
    monkeypatch.setattr(
        formal.v4,
        "_execute_joint_call_worker",
        lambda *_args: {"status": "passed"},
    )

    supplied_manifest = "c" * 64 if mutation == "call" else call_manifest
    with pytest.raises(RuntimeError, match=message):
        formal.run_joint_call_worker(
            Path("config.yaml"),
            output_directory=tmp_path,
            candidate_id="candidate",
            initial_strategy="reference_provider",
            result_directory=result,
            native_solver_log=native,
            call_registration_manifest_sha256=supplied_manifest,
        )
