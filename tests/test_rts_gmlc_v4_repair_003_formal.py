from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003_formal as formal,
)
from src.grid.rts_gmlc_exact_cg_runner import ExactCgStageResult
from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256


def test_formal_config_locks_accepted_control_plane_benchmark() -> None:
    config = formal._read_config(formal.DEFAULT_CONFIG_PATH)

    selection = config["control_plane_selection"]
    assert selection["required_status"] == "accepted"
    assert selection["result_manifest_sha256"] == (
        "c1aff33bce2098923a274a72373597ae19dda1e3ad669ef125d7b986c4344023"
    )
    assert selection["summary_sha256"] == (
        "5fabf96f1279b94056ca1c75a1d727fb3d0662f392ba3c33c5cfeb0bd121a888"
    )
    assert selection["selected_method"] == "direct_max_or_level_set_bisection"
    assert selection["warm_start_selection_frozen"] is True


def test_upper_bound_sources_are_candidate_specific() -> None:
    config = formal._read_config(formal.DEFAULT_CONFIG_PATH)
    controls = config["formal_successor"]["candidate_controls"]

    assert [item["ordinal"] for item in controls] == [1, 2, 3, 4, 5, 6]
    assert controls[3]["upper_bound_source"] == "candidate_4_failed_direct_certificate"
    assert controls[3]["initial_upper_bound"] == 0.2895372905465777
    assert controls[4]["upper_bound_source"] == "model_definition_global_upper_bound"
    assert controls[4]["initial_upper_bound"] == 1.0
    assert controls[5]["upper_bound_source"] == "model_definition_global_upper_bound"
    assert controls[5]["initial_upper_bound"] == 1.0
    assert controls[4]["may_inherit_candidate_4_upper_bound"] is False
    assert controls[5]["may_inherit_candidate_4_upper_bound"] is False
    assert config["formal_successor"]["algorithm_id"] == (
        "direct_exact_cg_then_bracketed_level_set_repair_003"
    )
    assert config["formal_successor"]["direct_backend"] == (
        "exact_selected_state_constraint_generation"
    )


def test_successor_registers_every_algorithm_source_explicitly() -> None:
    implementation = formal._read_config(formal.DEFAULT_CONFIG_PATH)["implementation"]

    assert {
        "formulation_pilot_path",
        "pilot_module_path",
        "exact_cg_core_path",
        "exact_cg_runner_path",
        "formal_adapter_path",
        "level_set_path",
        "warm_start_adapter_path",
        "runner_path",
        "monitor_path",
        "launcher_path",
    } <= set(implementation)


def test_prefix_checkpoint_rejects_copied_predecessor_stage_claim(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = formal.v4._Candidate(
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
        stage_audits={
            "proxy_maximization": {
                "schema": "rts_gmlc_exact_cg_stage_record_v1",
            }
        },
        residual_audit={"passed": True},
    )
    context = type(
        "Context",
        (),
        {
            "config": {
                "preregistration": {"id": "repair-003-test"},
                "candidate_frontier": {
                    "relative_cost_budget_deltas": [0.001],
                },
            },
            "input_contract": {
                "formal_successor": {
                    "candidate_controls": [
                        {
                            "mode": "verified_predecessor_prefix",
                            "relative_cost_budget_delta": 0.001,
                        }
                    ]
                }
            },
            "input_contract_sha256": "c" * 64,
        },
    )()
    payload = formal._checkpoint_payload(
        context,
        1,
        candidate,
        mode="verified_predecessor_prefix",
        evidence={
            "schema": formal.PREFIX_EVIDENCE_SCHEMA,
            "source_checkpoint_manifest_sha256": "d" * 64,
            "repeated_full_state_audit": {"passed": True},
        },
    )
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_a: None)

    with pytest.raises(RuntimeError, match="old exact-CG"):
        formal._validate_checkpoint_document(payload, context, 1)


def test_joint_worker_command_uses_successor_module() -> None:
    command = formal._joint_worker_command(
        python_executable=Path("python.exe"),
        config_path=Path("successor.yaml"),
        output_root=Path("output"),
        candidate_id="candidate_00",
        initial_strategy="source",
        worker_result=Path("worker"),
        native_log=Path("native.log"),
        call_manifest_sha256="e" * 64,
    )

    assert (
        "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003_formal"
        in command
    )
    assert "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4" not in command


def test_ineligible_direct_evidence_cannot_change_resumable_fallback_bracket() -> None:
    direct = ExactCgStageResult(
        snapshot=object(),
        audited_snapshot=object(),
        stage_record={
            "eligible": False,
            "certificate": {"valid": True, "upper_bound": 0.28},
        },
    )

    sanitized = formal._stable_fallback_input(direct)

    assert sanitized.snapshot is None
    assert sanitized.audited_snapshot is None
    assert sanitized.stage_record["certificate"] == {"valid": False}
    assert direct.stage_record["certificate"]["upper_bound"] == 0.28


def test_direct_certificate_is_normalized_to_frozen_acceptance_fields() -> None:
    values = (("reactive_proxy", (), 0.24),)
    snapshot = SharedSnapshot(
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

    certificate = formal._normalized_hybrid_certificate(
        {"valid": True, "lower_bound": 0.24, "upper_bound": 0.2401},
        snapshot,
        {
            "target_relative_gap": 1.0e-4,
            "maximum_accepted_absolute_gap": 1.0e-3,
            "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
        },
    )

    assert certificate["valid"] is True
    assert certificate["maximum_acceptance_passed"] is True
    assert certificate["target_attained"] is False


def test_prefix_checkpoint_is_recursively_manifested_and_round_trips(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    values = (("reactive_proxy", (), 0.24),)
    snapshot = SharedSnapshot(
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
    evidence = {
        "schema": formal.PREFIX_EVIDENCE_SCHEMA,
        "source_checkpoint_manifest_sha256": (
            formal.repair.PREFIX_EXPECTATIONS[0].manifest_sha256
        ),
        "repeated_full_state_audit": {
            "passed": True,
            "callback_record": {"residual_audit": {"passed": True}},
        },
        "accepted_proxy_snapshot": formal._snapshot_payload(snapshot),
        "accepted_proxy_snapshot_sha256": snapshot.sha256,
    }
    candidate = formal.v4._Candidate(
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
    context = type(
        "Context",
        (),
        {
            "config": {"preregistration": {"id": "repair-003-test"}},
            "input_contract": {
                "formal_successor": {
                    "candidate_controls": [
                        {
                            "mode": "verified_predecessor_prefix",
                            "relative_cost_budget_delta": 0.001,
                        }
                    ]
                }
            },
            "input_contract_sha256": "c" * 64,
        },
    )()
    monkeypatch.setattr(formal, "_validate_candidate_physics", lambda *_a: None)

    saved, saved_snapshot = formal._save_candidate_checkpoint(
        context,
        tmp_path,
        1,
        candidate,
        mode="verified_predecessor_prefix",
        evidence=evidence,
    )

    assert saved == candidate
    assert saved_snapshot == snapshot
    checkpoint = tmp_path / "candidate_checkpoints" / "01_q_proxy_delta_0p0010"
    formal._verify_manifest(checkpoint)
    assert formal._load_candidate_checkpoint(context, tmp_path, 1) == (
        candidate,
        snapshot,
    )


@pytest.mark.parametrize(
    "tamper",
    [
        "nested_manifest",
        "bracket_chain",
        "candidate_id",
        "input_contract",
        "final_bracket",
    ],
)
def test_level_set_round_chain_rejects_tampering(tmp_path: Path, tamper: str) -> None:
    input_contract_sha256 = "a" * 64
    predecessor_sha256 = "b" * 64
    candidate = SimpleNamespace(requested_candidate_id="q_proxy_delta_0p0075")
    context = SimpleNamespace(
        input_contract_sha256=input_contract_sha256,
        input_contract={"formal_successor": {"level_set_maximum_rounds": 12}},
    )
    checkpoint = tmp_path / "checkpoint"
    rounds_root = checkpoint / "level_set_rounds"
    lower_snapshot = {"sha256": "c" * 64}
    middle_snapshot = {"sha256": "d" * 64}
    accepted_snapshot = {"sha256": "e" * 64}
    round_documents = [
        {
            "schema": "rts_gmlc_proxy_level_set_round_v1",
            "candidate_id": candidate.requested_candidate_id,
            "candidate_ordinal": 4,
            "round_ordinal": 1,
            "input_contract_sha256": input_contract_sha256,
            "predecessor_manifest_sha256": predecessor_sha256,
            "bracket_before": {
                "lower_bound": 0.2,
                "upper_bound": 0.4,
                "lower_snapshot": lower_snapshot,
            },
            "bracket_after": {
                "lower_bound": 0.3,
                "upper_bound": 0.4,
                "lower_snapshot": middle_snapshot,
            },
        },
        {
            "schema": "rts_gmlc_proxy_level_set_round_v1",
            "candidate_id": candidate.requested_candidate_id,
            "candidate_ordinal": 4,
            "round_ordinal": 2,
            "input_contract_sha256": input_contract_sha256,
            "predecessor_manifest_sha256": predecessor_sha256,
            "bracket_before": {
                "lower_bound": 0.3,
                "upper_bound": 0.4,
                "lower_snapshot": middle_snapshot,
            },
            "bracket_after": {
                "lower_bound": 0.3,
                "upper_bound": 0.35,
                "lower_snapshot": accepted_snapshot,
            },
        },
    ]

    def publish_rounds(documents: list[dict[str, object]]) -> list[dict[str, object]]:
        references = []
        for ordinal, document in enumerate(documents, 1):
            path = rounds_root / f"{ordinal:02d}"
            path.mkdir(parents=True, exist_ok=True)
            formal.v4._write_exact_json(path / "round.json", document)
            formal.repair._write_recursive_manifest(path)
            references.append(
                {
                    "round_ordinal": ordinal,
                    "round_sha256": formal._sha256(path / "round.json"),
                    "manifest_sha256": formal._sha256(path / "SHA256SUMS"),
                }
            )
        return references

    references = publish_rounds(round_documents)
    evidence = {
        "method": "direct_max_or_level_set_bisection",
        "level_set_rounds": references,
        "predecessor_evidence_sha256": predecessor_sha256,
        "fallback_lower_snapshot_sha256": lower_snapshot["sha256"],
        "accepted_proxy_snapshot_sha256": accepted_snapshot["sha256"],
        "certificate": {"lower_bound": 0.3, "upper_bound": 0.35},
    }
    formal._validate_round_artifacts(checkpoint, context, 4, candidate, evidence)

    tampered = copy.deepcopy(round_documents)
    if tamper == "nested_manifest":
        round_path = rounds_root / "01" / "round.json"
        document = json.loads(round_path.read_text(encoding="utf-8"))
        document["candidate_id"] = "tampered"
        formal.v4._write_exact_json(round_path, document)
    else:
        if tamper == "bracket_chain":
            tampered[1]["bracket_before"]["lower_bound"] = 0.29
        elif tamper == "candidate_id":
            tampered[0]["candidate_id"] = "tampered"
        elif tamper == "input_contract":
            tampered[0]["input_contract_sha256"] = "f" * 64
        elif tamper == "final_bracket":
            tampered[1]["bracket_after"]["upper_bound"] = 0.36
        evidence["level_set_rounds"] = publish_rounds(tampered)

    with pytest.raises(RuntimeError):
        formal._validate_round_artifacts(checkpoint, context, 4, candidate, evidence)
