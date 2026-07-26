from __future__ import annotations

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003 as repair,
)
from experiments.process_google_power_workload_day0 import _verify_manifest
from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256
from src.grid.rts_gmlc_exact_cg_runner import ExactCgStageResult


def _snapshot(proxy: float, cost: float = 100.0) -> SharedSnapshot:
    values = (("reactive_proxy", (), proxy),)
    digest = structured_sha256(
        [
            {
                "component": "reactive_proxy",
                "index": [],
                "value_float_hex": proxy.hex(),
            }
        ]
    )
    return SharedSnapshot(values, digest, proxy, cost)


def _direct_failure() -> ExactCgStageResult:
    return ExactCgStageResult(
        snapshot=None,
        audited_snapshot=None,
        stage_record={
            "eligible": False,
            "failure_reason": "final_bound_certificate_exceeds_maximum_acceptance",
            "certificate": {
                "valid": True,
                "lower_bound": 0.4,
                "upper_bound": 0.8,
            },
        },
    )


def _oracle_result(
    floor: float, *, feasible: bool, decision_cap: float = 100.0
) -> ExactCgStageResult:
    snapshot = _snapshot(floor) if feasible else None
    audit = (
        {
            "passed": True,
            "residual_audit_passed": True,
            "callback_record": {
                "commitment_capability_proxy_fraction": floor,
                "actual_operating_cost_usd": 99.0,
            },
        }
        if feasible
        else None
    )
    return ExactCgStageResult(
        snapshot=snapshot,
        audited_snapshot=snapshot,
        stage_record={
            "eligible": feasible,
            "failure_reason": None,
            "level_set_oracle_outcome": (
                "audited_feasible" if feasible else "bound_only_early_separation"
            ),
            "bound_only_early_separation": (
                None
                if feasible
                else {
                    "schema": "rts_gmlc_level_set_bound_only_early_separation_v1",
                    "valid": True,
                    "source": (
                        "active_budget_capped_decision_mip_global_infeasibility"
                    ),
                    "decision_budget_cap_usd": decision_cap,
                }
            ),
            "master_records": [
                {
                    "bound_valid": False,
                    "dual_bound": None,
                    "callback_record": {
                        "solve": {
                            "termination_condition": (
                                "optimal" if feasible else "infeasible"
                            )
                        }
                    },
                }
            ],
            "iteration_records": (
                [
                    {
                        "screen_round_complete": True,
                        "promotions": [],
                    }
                ]
                if feasible
                else []
            ),
            "final_full_state_audit": audit,
        },
    )


def test_repair_manifest_covers_nested_manifests(tmp_path: Path) -> None:
    root = tmp_path / "artifact"
    nested = root / "nested"
    nested.mkdir(parents=True)
    (root / "summary.json").write_text("{}\n", encoding="utf-8")
    (nested / "round.json").write_text("{}\n", encoding="utf-8")
    repair._write_recursive_manifest(nested)

    repair._write_recursive_manifest(root)

    entries = {
        line.split("  ", maxsplit=1)[1]
        for line in (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    }
    assert entries == {
        "nested/SHA256SUMS",
        "nested/round.json",
        "summary.json",
    }
    _verify_manifest(root)


def test_repair_002_prefix_and_candidate_four_evidence_are_locked() -> None:
    prefix = repair.verify_predecessor_prefix()
    fourth = repair.verify_candidate_four_upper_bound()

    assert [item.expectation.ordinal for item in prefix] == [1, 2, 3]
    assert fourth["upper_bound"] == 0.2895372905465777
    assert fourth["lower_snapshot_imported"] is False
    assert fourth["joint_ac_solver_call_count"] == 0


@pytest.mark.parametrize(
    "relative_path",
    ["preregistration/registration.json", "preregistration/config.yaml"],
)
def test_predecessor_preregistration_content_tamper_is_rejected(
    tmp_path: Path, relative_path: str
) -> None:
    copied_root = tmp_path / "predecessor"
    shutil.copytree(repair.PREDECESSOR_ROOT, copied_root)
    tampered = copied_root / relative_path
    tampered.write_bytes(tampered.read_bytes() + b"\n# tampered\n")

    with pytest.raises(RuntimeError, match="manifest hash drifted"):
        repair.verify_predecessor_prefix(root=copied_root)


def test_prefix_candidate_hash_drift_is_rejected() -> None:
    imported = repair.verify_predecessor_prefix()[0]
    document = repair.json.loads(
        (imported.checkpoint_path / "candidate.json").read_text(encoding="utf-8")
    )
    document["candidate"]["commitment_sha256"] = "0" * 64

    with pytest.raises(RuntimeError, match="identity"):
        repair._validate_prefix_payload(document, imported.expectation)


def test_candidate_four_cannot_supply_a_missing_lower_snapshot() -> None:
    fourth = repair.verify_candidate_four_upper_bound()

    assert "lower_bound_value_observed_but_snapshot_not_importable" in fourth
    assert "lower_snapshot" not in fourth


def test_direct_failure_mechanically_switches_to_bisection() -> None:
    calls = []

    def oracle(floor: float, ordinal: int) -> ExactCgStageResult:
        calls.append((floor, ordinal))
        if floor > 0.6:
            return _oracle_result(floor, feasible=False)
        return _oracle_result(floor, feasible=True)

    result = repair.run_hybrid_proxy_certificate(
        _direct_failure(),
        fallback_lower_snapshot=_snapshot(0.4),
        imported_upper_bound=0.8,
        level_oracle=oracle,
        effective_budget_usd=100.0,
        strict_separation_margin_usd=1.0e-6,
        target_relative_gap=1.0e-4,
        maximum_absolute_gap=0.11,
        maximum_relative_gap=0.2,
        maximum_rounds=10,
        candidate_id="q_proxy_delta_0p0075",
        candidate_ordinal=1,
        input_contract_sha256="a" * 64,
        predecessor_manifest_sha256="b" * 64,
    )

    assert result.method == "direct_max_or_level_set_bisection"
    assert result.snapshot is not None
    assert result.certificate["maximum_acceptance_passed"]
    assert calls


def test_failed_generic_stage_cannot_supply_a_level_set_upper_bound() -> None:
    failed = ExactCgStageResult(
        snapshot=None,
        audited_snapshot=None,
        stage_record={
            "eligible": False,
            "failure_reason": "final_full_state_fixed_shared_audit_failed",
            "level_set_oracle_outcome": "unresolved",
            "bound_only_early_separation": None,
            "master_records": [
                {
                    "bound_valid": True,
                    "dual_bound": 101.0,
                    "callback_record": {"solve": {"termination_condition": "optimal"}},
                }
            ],
        },
    )

    evidence = repair.level_evidence_from_stage_result(failed, proxy_floor=0.6)

    assert not evidence.active_master_bound_valid
    assert evidence.active_master_dual_lower_bound_usd is None
    assert not evidence.active_master_globally_infeasible
    assert evidence.incumbent_snapshot is None


def test_direct_eligible_certificate_never_calls_level_oracle() -> None:
    snapshot = _snapshot(0.7)
    direct = replace(
        _direct_failure(),
        snapshot=snapshot,
        audited_snapshot=snapshot,
        stage_record={
            "eligible": True,
            "certificate": {
                "valid": True,
                "lower_bound": 0.7,
                "upper_bound": 0.7001,
            },
        },
    )

    result = repair.run_hybrid_proxy_certificate(
        direct,
        fallback_lower_snapshot=_snapshot(0.4),
        imported_upper_bound=0.8,
        level_oracle=lambda *_args: pytest.fail("level oracle was called"),
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

    assert result.method == "direct_exact_cg"
    assert result.snapshot == snapshot


def test_prefix_smoke_completion_event_does_not_override_writer_fields(
    monkeypatch,
) -> None:
    events = []
    context = type(
        "Context",
        (),
        {"input_contract_sha256": "a" * 64},
    )()
    imported = repair.ImportedPrefixCandidate(
        repair.PREFIX_EXPECTATIONS[0], object(), Path("unused")
    )
    rehydrated = repair.RehydratedPrefixSnapshot(
        _snapshot(0.4),
        {"recomputed_proxy_fraction": 0.4},
        {"passed": True},
    )

    class Progress:
        def emit(self, event: str, **payload: object) -> None:
            assert not {"schema", "run_id", "input_contract_sha256"} & set(payload)
            events.append(event)

    monkeypatch.setattr(repair.v4, "_build_context", lambda _path: context)
    monkeypatch.setattr(repair, "verify_predecessor_prefix", lambda: (imported,) * 3)
    monkeypatch.setattr(
        repair, "JsonlProgressWriter", lambda *_args, **_kwargs: Progress()
    )
    monkeypatch.setattr(
        repair, "rehydrate_prefix_snapshot", lambda *_args, **_kwargs: rehydrated
    )

    result = repair.run_prefix_reaudit_smoke(ordinal=1, run_id="test")

    assert result["repeated_full_state_audit_passed"]
    assert events == [
        "repair_003_prefix_reaudit_started",
        "repair_003_prefix_reaudit_completed",
    ]


def test_delta_pilot_is_nonformal_and_uses_frozen_certificate_controls(
    monkeypatch, tmp_path: Path
) -> None:
    events = []
    captured = {}
    lower_snapshot = _snapshot(repair.PREFIX_EXPECTATIONS[2].reactive_proxy_fraction)
    context = type(
        "Context",
        (),
        {
            "input_contract_sha256": "a" * 64,
            "config": {
                "parent_zero_control": {
                    "baseline_full_state_cost_usd": 1000.0,
                },
                "candidate_frontier": {
                    "cost_cap_absolute_tolerance_usd": 1.0e-4,
                },
                "candidate_snapshot": {},
                "formal_solver": {
                    "stages": {
                        "proxy_maximization": {
                            "target_relative_gap": 1.0e-4,
                            "maximum_accepted_absolute_gap": 1.0e-3,
                            "maximum_accepted_relative_gap_to_feasible_incumbent": (
                                1.0e-3
                            ),
                        },
                    },
                    "time_limits_seconds": {
                        "inactive_state_screen_per_call": 300.0,
                        "final_full_state_audit_per_call": 1800.0,
                    },
                },
            },
        },
    )()
    imported = repair.ImportedPrefixCandidate(
        repair.PREFIX_EXPECTATIONS[2], object(), Path("unused")
    )
    rehydrated = repair.RehydratedPrefixSnapshot(lower_snapshot, {}, {"passed": True})
    problem = type(
        "Problem",
        (),
        {"all_state_ids": ("normal",), "initial_active_state_ids": ("normal",)},
    )()

    class Progress:
        def emit(self, event: str, **payload: object) -> None:
            events.append((event, payload))

    def fake_bracket(initial, **kwargs):
        captured["initial"] = initial
        captured.update(kwargs)
        certificate = {
            "maximum_acceptance_passed": True,
            "lower_bound": initial.lower_bound,
            "upper_bound": initial.upper_bound,
        }
        return repair.BracketRunResult("accepted", initial, certificate, (), None)

    def fake_stage(**kwargs):
        floor = kwargs["proxy_floor"]
        kwargs["callbacks"].emit(
            "exact_cg_stage_started",
            {"stage": "level_set_budget_feasibility", "proxy_floor": floor},
        )
        return _oracle_result(floor, feasible=False, decision_cap=1007.5001)

    monkeypatch.setattr(repair.v4, "_build_context", lambda _path: context)
    monkeypatch.setattr(repair, "verify_predecessor_prefix", lambda: (imported,) * 3)
    monkeypatch.setattr(
        repair,
        "verify_candidate_four_upper_bound",
        lambda: {"upper_bound": 0.2895372905465777},
    )
    monkeypatch.setattr(repair, "JsonlProgressWriter", lambda *_a, **_kw: Progress())
    monkeypatch.setattr(
        repair, "rehydrate_prefix_snapshot", lambda *_a, **_kw: rehydrated
    )
    monkeypatch.setattr(repair.v4, "_formal_problem", lambda *_a, **_kw: problem)
    monkeypatch.setattr(repair, "run_bracketed_level_set", fake_bracket)
    monkeypatch.setattr(repair, "run_exact_cg_stage", fake_stage)

    summary = repair.run_delta_0p0075_level_set_pilot(
        run_id="pilot-test", output_root=tmp_path / "pilot"
    )

    assert summary["cost_budget_usd"] == pytest.approx(1007.5)
    assert summary["effective_cost_budget_usd"] == pytest.approx(1007.5001)
    assert summary["direct_phase_executed"] is False
    assert summary["formal_candidate_result"] is False
    assert summary["preregistration_published"] is False
    assert summary["warm_start_selection_frozen"] is False
    assert summary["joint_ac_solver_call_count"] == 0
    assert captured["strict_separation_margin_usd"] == 1.0e-4
    assert captured["maximum_rounds"] == 8
    assert captured["maximum_absolute_gap"] == 1.0e-3
    assert captured["maximum_relative_gap"] == 1.0e-3
    assert captured["checkpoint_root"] == tmp_path / "pilot" / "pilot_checkpoints"
    evidence = captured["oracle"](0.26, 1)
    assert evidence.proxy_floor == 0.26
    assert [event for event, _payload in events] == [
        "repair_003_level_set_pilot_started",
        "repair_003_level_set_pilot_completed",
        "exact_cg_stage_started",
    ]
