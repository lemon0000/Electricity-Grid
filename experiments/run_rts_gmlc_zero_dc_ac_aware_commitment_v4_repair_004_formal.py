"""Immutable repair-004 successor for the V4 candidate control plane."""

from __future__ import annotations

import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from typing import Any

import yaml
from pyomo.environ import value

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003 as repair,
)
from experiments import (
    record_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003_invalidation as invalidation,
)
from experiments.process_google_power_workload_day0 import _verify_manifest
from src.grid.rts_gmlc_exact_cg import SharedSnapshot
from src.grid.rts_gmlc_exact_cg_runner import (
    ExactCgTimeLimits,
    run_exact_cg_stage,
)
from src.grid.rts_gmlc_formal_cg_adapter import FormalCgModelAdapter
from src.grid.rts_gmlc_level_set import (
    ProxyBracket,
    _snapshot_from_payload,
    _snapshot_payload,
    acceptance_certificate,
)
from src.grid.rts_gmlc_v4_initial_proxy_warmstart import (
    V4InitialProxyWarmStartAdapter,
)
from src.scenarios.common_input_signature import common_input_signature_sha256
from src.solvers.execution_lease import ExecutionLease
from src.solvers.mip_progress import JsonlProgressWriter

DEFAULT_CONFIG_PATH = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004.yaml"
)
CHECKPOINT_SCHEMA = "rts_gmlc_v4_repair_004_hybrid_candidate_checkpoint_v1"
PREFIX_EVIDENCE_SCHEMA = "rts_gmlc_v4_repair_004_prefix_evidence_v1"
HYBRID_EVIDENCE_SCHEMA = "rts_gmlc_v4_repair_003_hybrid_evidence_v1"
FRONTIER_SCHEMA = "rts_gmlc_v4_repair_004_candidate_frontier_v1"
FLOAT_SERIALIZATION = "python_json_roundtrip_full_precision_v1"
_CONFIG_KEYS = {
    "schema",
    "preregistration",
    "base_v4",
    "predecessor_repair_002",
    "predecessor_repair_003",
    "control_plane_selection",
    "formal_successor",
    "implementation",
    "output",
    "logging",
}
_CHECKPOINT_FIELDS = {
    "schema",
    "float_serialization",
    "preregistration_id",
    "input_contract_sha256",
    "ordinal",
    "mode",
    "candidate",
    "evidence",
}
_SUCCESSOR_MODULE = (
    "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004_formal"
)


def _sha256(path: Path) -> str:
    return v4._sha256(path)


def _verify_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise RuntimeError(f"repair-004 {label} hash drifted")


def _read_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _CONFIG_KEYS:
        raise ValueError("repair-004 config schema drifted")
    preregistration = config["preregistration"]
    if (
        preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004"
        or preregistration.get("schema")
        != "rts_gmlc_zero_dc_ac_aware_commitment_preregistration_v4_repair_004"
        or preregistration.get("candidate_frontier_outcomes_observed") is not False
        or preregistration.get("joint_ac_outcomes_observed") is not False
    ):
        raise ValueError("repair-004 preregistration contract drifted")
    base = config["base_v4"]
    if (
        base.get("scientific_config_changed") is not False
        or base.get("joint_ac_protocol_changed") is not False
    ):
        raise ValueError("repair-004 changed the frozen V4 scientific protocol")
    predecessor = config["predecessor_repair_002"]
    if (
        predecessor.get("preregistration_manifest_sha256")
        != repair.PREDECESSOR_PREREGISTRATION_MANIFEST_SHA256
        or predecessor.get("input_contract_sha256")
        != repair.PREDECESSOR_INPUT_CONTRACT_SHA256
        or predecessor.get("failed_candidate_4_progress_sha256")
        != repair.FAILED_PROGRESS_SHA256
        or predecessor.get("completed_prefix_count") != 3
        or predecessor.get("candidate_frontier_published") is not False
        or predecessor.get("joint_ac_solver_call_count") != 0
        or predecessor.get("predecessor_resume_allowed") is not False
        or predecessor.get("candidate_checkpoint_manifest_sha256s")
        != [item.manifest_sha256 for item in repair.PREFIX_EXPECTATIONS]
    ):
        raise ValueError("repair-004 predecessor contract drifted")
    failed_parent = config["predecessor_repair_003"]
    if (
        failed_parent.get("config_sha256")
        != invalidation.EXPECTED_SOURCE_SHA256[
            "configs/"
            "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_003.yaml"
        ]
        or failed_parent.get("formal_runner_sha256")
        != invalidation.EXPECTED_SOURCE_SHA256[
            "experiments/"
            "run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003_formal.py"
        ]
        or failed_parent.get("monitor_sha256")
        != invalidation.EXPECTED_SOURCE_SHA256[
            "experiments/"
            "monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003.py"
        ]
        or failed_parent.get("launcher_sha256")
        != invalidation.EXPECTED_SOURCE_SHA256[
            "scripts/" "start_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003.ps1"
        ]
        or failed_parent.get("preregistration_manifest_sha256")
        != invalidation.EXPECTED_PREREGISTRATION_MANIFEST_SHA256
        or failed_parent.get("input_contract_sha256")
        != invalidation.EXPECTED_INPUT_CONTRACT_SHA256
        or failed_parent.get("failed_attempt_id") != invalidation.ATTEMPT_ID
        or failed_parent.get("failed_attempt_pid") != 50844
        or failed_parent.get("failed_progress_sha256")
        != invalidation.EXPECTED_ATTEMPT_FILE_SHA256["progress.jsonl"]
        or failed_parent.get("failed_attempt_file_sha256")
        != invalidation.EXPECTED_ATTEMPT_FILE_SHA256
        or failed_parent.get("failed_lease_sha256")
        != invalidation.EXPECTED_PARENT_FILE_SHA256[
            f"{invalidation.FAILED_LEASE_RELATIVE.as_posix()}/lease.json"
        ]
        or failed_parent.get("failed_terminal_sha256")
        != invalidation.EXPECTED_PARENT_FILE_SHA256[
            f"{invalidation.FAILED_LEASE_RELATIVE.as_posix()}/terminal.json"
        ]
        or failed_parent.get("prefix_master_passed") is not True
        or failed_parent.get("repeated_24_state_audit_passed") is not True
        or failed_parent.get("failure_is_infeasibility_evidence") is not False
        or failed_parent.get("valid_candidate_checkpoint_count") != 0
        or failed_parent.get("candidate_frontier_published") is not False
        or failed_parent.get("joint_ac_solver_call_count") != 0
        or failed_parent.get("predecessor_resume_allowed") is not False
    ):
        raise ValueError("repair-004 failed-parent contract drifted")
    selection = config["control_plane_selection"]
    if (
        selection.get("required_status") != "accepted"
        or selection.get("selected_method") != "direct_max_or_level_set_bisection"
        or selection.get("selected_level_set_method")
        != "bracketed_budget_feasibility_decision_mip"
        or selection.get("warm_start_selection_frozen") is not True
        or selection.get("objective_value_used_for_selection") is not False
        or selection.get("formal_candidate_result") is not False
        or selection.get("preregistration_published") is not False
        or selection.get("joint_ac_solver_call_count") != 0
    ):
        raise ValueError("repair-004 control-plane selection drifted")
    successor = config["formal_successor"]
    controls = successor.get("candidate_controls")
    if (
        successor.get("checkpoint_schema") != CHECKPOINT_SCHEMA
        or successor.get("algorithm_id")
        != "direct_exact_cg_then_bracketed_level_set_repair_003"
        or successor.get("direct_backend")
        != "exact_selected_state_constraint_generation"
        or successor.get("float_serialization") != FLOAT_SERIALIZATION
        or successor.get("prefix_candidate_count") != 3
        or successor.get("direct_phase_first_for_new_candidates") is not True
        or successor.get("prefix_old_stage_certificate_import_allowed") is not False
        or successor.get("fallback_lower_bound_source")
        != "immediately_preceding_published_successor_checkpoint"
        or successor.get(
            "fallback_upper_bound_uses_only_candidate_specific_preregistered_source"
        )
        is not True
        or successor.get("ineligible_direct_bounds_change_fallback_initial_bracket")
        is not False
        or successor.get("all_six_checkpoints_required_before_frontier") is not True
        or successor.get("frontier_required_before_joint_ac") is not True
        or successor.get("unresolved_is_infeasibility_evidence") is not False
        or float(successor.get("strict_cost_separation_margin_usd")) != 1.0e-4
        or float(successor.get("level_set_master_seconds_per_call")) != 3600.0
        or int(successor.get("level_set_maximum_rounds")) != 12
        or float(successor.get("target_relative_gap")) != 1.0e-4
        or float(successor.get("maximum_accepted_absolute_gap")) != 1.0e-3
        or float(successor.get("maximum_accepted_relative_gap_to_feasible_incumbent"))
        != 1.0e-3
        or not isinstance(controls, list)
        or len(controls) != 6
    ):
        raise ValueError("repair-004 formal successor contract drifted")
    expected_deltas = (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05)
    for ordinal, (control, delta) in enumerate(zip(controls, expected_deltas), 1):
        expected_mode = (
            "verified_predecessor_prefix" if ordinal <= 3 else "direct_then_level_set"
        )
        if (
            control.get("ordinal") != ordinal
            or float(control.get("relative_cost_budget_delta")) != delta
            or control.get("mode") != expected_mode
        ):
            raise ValueError("repair-004 candidate control order drifted")
    if (
        controls[3].get("upper_bound_source") != "candidate_4_failed_direct_certificate"
        or float(controls[3].get("initial_upper_bound")) != 0.2895372905465777
        or any(
            item.get("upper_bound_source") != "model_definition_global_upper_bound"
            or float(item.get("initial_upper_bound")) != 1.0
            or item.get("may_inherit_candidate_4_upper_bound") is not False
            for item in controls[4:]
        )
    ):
        raise ValueError("repair-004 candidate-specific upper bounds drifted")
    proof = successor.get("model_definition_upper_bound_proof")
    if (
        not isinstance(proof, Mapping)
        or float(proof.get("value")) != 1.0
        or proof.get("proof")
        != "numerator_is_a_nonnegative_subset_sum_of_denominator_terms"
    ):
        raise ValueError("repair-004 global proxy upper-bound proof drifted")
    if config["output"] != {
        "directory": (
            "results/tables/"
            "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004"
        )
    }:
        raise ValueError("repair-004 output contract drifted")
    return config


def _verify_parent_invalidation(
    config: Mapping[str, Any], invalidation_root: Path | None
) -> None:
    parent = config["predecessor_repair_003"]
    root = invalidation_root or (
        Path(parent["root"]) / str(parent["invalidation_relative_path"])
    )
    _verify_manifest(root)
    if _sha256(root / "SHA256SUMS") != parent["invalidation_manifest_sha256"]:
        raise RuntimeError("repair-004 parent invalidation manifest drifted")
    payload = v4._load_json(root, "invalidation.json")
    if (
        payload.get("status") != parent["required_invalidation_status"]
        or payload.get("preregistration_manifest_sha256")
        != parent["preregistration_manifest_sha256"]
        or payload.get("input_contract_sha256") != parent["input_contract_sha256"]
        or payload.get("prefix_master_termination_condition") != "optimal"
        or payload.get("repeated_24_state_full_state_audit_passed") is not True
        or payload.get("residual_audit_passed") is not True
        or payload.get("failure_is_infeasibility_evidence") is not False
        or payload.get("failure_is_post_audit_implementation_bug") is not True
        or payload.get("valid_candidate_checkpoint_count") != 0
        or payload.get("candidate_frontier_artifact_published") is not False
        or payload.get("joint_ac_solver_call_count") != 0
        or payload.get("repair_003_resume_allowed") is not False
        or payload.get("successor_must_restart_from_candidate_ordinal") != 1
        or payload.get("successor_must_use_new_preregistration_id") is not True
        or payload.get("scientific_protocol_changed") is not False
    ):
        raise RuntimeError("repair-004 parent invalidation content drifted")


def _verify_frozen_inputs(
    config: Mapping[str, Any], *, predecessor_invalidation_root: Path | None = None
) -> None:
    base = config["base_v4"]
    _verify_file(Path(base["config_path"]), str(base["config_sha256"]), "base config")
    _verify_file(Path(base["runner_path"]), str(base["runner_sha256"]), "base runner")
    for key, value_ in config["implementation"].items():
        if not key.endswith("_path"):
            continue
        hash_key = key.removesuffix("_path") + "_sha256"
        expected = str(config["implementation"].get(hash_key, ""))
        if expected == "PENDING" or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise RuntimeError(f"repair-004 implementation hash is not frozen: {key}")
        _verify_file(Path(value_), expected, key)
    selection = config["control_plane_selection"]
    pilot_root = Path(selection["root"])
    _verify_manifest(pilot_root)
    if (
        _sha256(pilot_root / "SHA256SUMS") != selection["result_manifest_sha256"]
        or _sha256(pilot_root / "summary.json") != selection["summary_sha256"]
    ):
        raise RuntimeError("repair-004 decision pilot hash drifted")
    summary = json.loads((pilot_root / "summary.json").read_text(encoding="utf-8"))
    certificate = summary.get("certificate")
    if (
        summary.get("schema") != selection["required_schema"]
        or summary.get("status") != selection["required_status"]
        or summary.get("run_id") != selection["run_id"]
        or summary.get("formal_candidate_result") is not False
        or summary.get("preregistration_published") is not False
        or summary.get("joint_ac_solver_call_count") != 0
        or not isinstance(certificate, Mapping)
        or certificate.get("valid") is not True
        or certificate.get("maximum_acceptance_passed") is not True
    ):
        raise RuntimeError("repair-004 decision pilot content drifted")
    imported = repair.verify_predecessor_prefix(
        Path(config["predecessor_repair_002"]["root"])
    )
    if len(imported) != 3:
        raise RuntimeError("repair-004 predecessor prefix drifted")
    candidate_four = repair.verify_candidate_four_upper_bound(
        Path(config["predecessor_repair_002"]["failed_candidate_4_progress_path"])
    )
    if candidate_four["upper_bound"] != 0.2895372905465777:
        raise RuntimeError("repair-004 candidate-4 upper bound drifted")
    _verify_parent_invalidation(config, predecessor_invalidation_root)


def _build_context(
    config_path: Path, *, predecessor_invalidation_root: Path | None = None
) -> v4._FrontierContext:
    successor_config = _read_config(config_path)
    _verify_frozen_inputs(
        successor_config,
        predecessor_invalidation_root=predecessor_invalidation_root,
    )
    base_path = Path(successor_config["base_v4"]["config_path"])
    base = v4._build_context(base_path)
    effective_config = copy.deepcopy(base.config)
    effective_config["preregistration"] = dict(successor_config["preregistration"])
    effective_config["output"] = dict(successor_config["output"])
    effective_config["formal_solver"]["algorithm"] = successor_config[
        "formal_successor"
    ]["algorithm_id"]
    effective_config["formal_solver"]["progress_logging"]["log_directory"] = (
        successor_config["logging"]["directory"]
    )
    effective_config["joint_ac"]["runtime_control"]["log_directory"] = successor_config[
        "logging"
    ]["directory"]
    contract = {
        "schema": "rts_gmlc_v4_repair_004_formal_inputs_v1",
        "base_v4_input_contract": base.input_contract,
        "base_v4_input_contract_sha256": base.input_contract_sha256,
        "successor_config_sha256": _sha256(config_path),
        "predecessor_repair_002": successor_config["predecessor_repair_002"],
        "predecessor_repair_003": successor_config["predecessor_repair_003"],
        "control_plane_selection": successor_config["control_plane_selection"],
        "formal_successor": successor_config["formal_successor"],
        "implementation": successor_config["implementation"],
    }
    return replace(
        base,
        config_path=config_path,
        config=effective_config,
        output_root=Path(successor_config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: v4._FrontierContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


def _registration_payload(context: v4._FrontierContext) -> dict[str, Any]:
    preregistration = context.config["preregistration"]
    return {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "previous_ac_outcomes_observed": True,
        "candidate_frontier_outcomes_observed": False,
        "joint_ac_outcomes_observed": False,
        "warm_start_selection_frozen": True,
        "selected_candidate_method": "direct_max_or_level_set_bisection",
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    predecessor_invalidation_root: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(
        config_path,
        predecessor_invalidation_root=predecessor_invalidation_root,
    )
    output_root = _output_root(context, output_directory)
    target = output_root / "preregistration"
    expected = _registration_payload(context)
    if target.exists():
        observed = v4._load_json(target, "registration.json")
        if (
            v4._exact_json_text(observed) != v4._exact_json_text(expected)
            or (target / "config.yaml").read_bytes() != config_path.read_bytes()
        ):
            raise RuntimeError("repair-004 published preregistration drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare repair-004 beside existing artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        v4._write_exact_json(staging / "registration.json", expected)

    v4._publish_immutable_payload(target, writer)
    return v4._load_json(target, "registration.json")


def _require_preregistration(
    context: v4._FrontierContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    observed = v4._load_json(target, "registration.json")
    if (
        v4._exact_json_text(observed)
        != v4._exact_json_text(_registration_payload(context))
        or (target / "config.yaml").read_bytes() != context.config_path.read_bytes()
        or common_input_signature_sha256(observed["input_contract"])
        != context.input_contract_sha256
    ):
        raise RuntimeError("repair-004 preregistration contract drifted")
    return observed


def _checkpoint_payload(
    context: v4._FrontierContext,
    ordinal: int,
    candidate: v4._Candidate,
    *,
    mode: str,
    evidence: Mapping[str, object],
) -> dict[str, object]:
    payload = {
        "schema": CHECKPOINT_SCHEMA,
        "float_serialization": FLOAT_SERIALIZATION,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "ordinal": ordinal,
        "mode": mode,
        "candidate": asdict(candidate),
        "evidence": dict(evidence),
    }
    canonical = v4._exact_json_payload(payload)
    if not isinstance(canonical, dict):
        raise RuntimeError("repair-004 checkpoint payload drifted")
    return canonical


def _validate_candidate_physics(
    candidate: v4._Candidate, context: v4._FrontierContext, ordinal: int
) -> None:
    controls = context.input_contract["formal_successor"]["candidate_controls"]
    control = controls[ordinal - 1]
    delta = float(control["relative_cost_budget_delta"])
    baseline = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    budget = baseline * (1.0 + delta)
    expected_id = v4._requested_candidate_id(delta)
    hours = int(context.config["candidate_frontier"]["expected_hours"])
    generator_uids = tuple(item.uid for item in context.zero.scan.data.generators)
    branch_uids = tuple(item.uid for item in context.zero.scan.data.branches)
    dc_uids = tuple(item.uid for item in context.zero.scan.data.dc_branches)
    expected_source = (
        "repair_003_verified_predecessor_prefix"
        if ordinal <= 3
        else "q_proxy_repair_003_hybrid_certificate"
    )
    components = (
        (candidate.commitment, generator_uids),
        (candidate.startup, generator_uids),
        (candidate.shutdown, generator_uids),
        (candidate.generation_mw, generator_uids),
        (candidate.branch_flows_mw, branch_uids),
        (candidate.dc_flows_mw, dc_uids),
        (candidate.reserve_up_mw, generator_uids),
    )
    if (
        candidate.source != expected_source
        or candidate.requested_candidate_id != expected_id
        or candidate.relative_cost_budget_delta != delta
        or not v4._checkpoint_close(candidate.cost_budget_usd, budget)
        or candidate.operating_cost_usd
        > budget
        + float(context.config["candidate_frontier"]["cost_cap_absolute_tolerance_usd"])
        or not -1.0e-9 <= candidate.reactive_proxy_fraction <= 1.0 + 1.0e-9
        or any(
            len(rows) != hours or any(set(row) != set(expected) for row in rows)
            for rows, expected in components
        )
        or v4._commitment_sha256(candidate.commitment) != candidate.commitment_sha256
        or v4._dispatch_sha256(
            candidate.generation_mw,
            candidate.branch_flows_mw,
            candidate.dc_flows_mw,
        )
        != candidate.dispatch_sha256
        or candidate.residual_audit.get("passed") is not True
    ):
        raise RuntimeError("repair-004 candidate physical contract drifted")
    startup, shutdown = v4._boolean_transitions(
        candidate.commitment, context.initial_state.commitment
    )
    if candidate.startup != startup or candidate.shutdown != shutdown:
        raise RuntimeError("repair-004 candidate transition drifted")
    if ordinal <= 3:
        expected = repair.PREFIX_EXPECTATIONS[ordinal - 1]
        if (
            candidate.commitment_sha256 != expected.commitment_sha256
            or candidate.dispatch_sha256 != expected.dispatch_sha256
            or candidate.reactive_proxy_fraction != expected.reactive_proxy_fraction
        ):
            raise RuntimeError("repair-004 prefix physical identity drifted")
    reserve_provider_uids = {
        item.uid
        for item in context.zero.scan.data.generators
        if item.enabled
        and item.dispatch_mode in {"committable", "curtailable"}
        and item.category in v4._RESERVE_ELIGIBLE_CATEGORIES
    }
    if any(
        reserve != 0.0
        for row in candidate.reserve_up_mw
        for uid, reserve in row.items()
        if uid not in reserve_provider_uids
    ):
        raise RuntimeError("repair-004 non-provider reserve drifted")


def _validate_checkpoint_document(
    observed: Mapping[str, Any],
    context: v4._FrontierContext,
    ordinal: int,
) -> tuple[v4._Candidate, SharedSnapshot]:
    if set(observed) != _CHECKPOINT_FIELDS:
        raise RuntimeError("repair-004 checkpoint fields drifted")
    controls = context.input_contract["formal_successor"]["candidate_controls"]
    if not 1 <= ordinal <= len(controls):
        raise RuntimeError("repair-004 checkpoint ordinal drifted")
    control = controls[ordinal - 1]
    if (
        observed.get("schema") != CHECKPOINT_SCHEMA
        or observed.get("float_serialization") != FLOAT_SERIALIZATION
        or observed.get("preregistration_id") != context.config["preregistration"]["id"]
        or observed.get("input_contract_sha256") != context.input_contract_sha256
        or observed.get("ordinal") != ordinal
        or observed.get("mode") != control["mode"]
        or not isinstance(observed.get("candidate"), Mapping)
        or not isinstance(observed.get("evidence"), Mapping)
    ):
        raise RuntimeError("repair-004 checkpoint contract drifted")
    candidate = v4._candidate_from_checkpoint_payload(observed["candidate"])
    _validate_candidate_physics(candidate, context, ordinal)
    evidence = observed["evidence"]
    if ordinal <= 3:
        old_stage = candidate.stage_audits.get("proxy_maximization")
        if (
            isinstance(old_stage, Mapping)
            and old_stage.get("schema") == "rts_gmlc_exact_cg_stage_record_v1"
        ):
            raise RuntimeError("repair-004 prefix copied an old exact-CG stage claim")
    snapshot_payload = evidence.get("accepted_proxy_snapshot")
    if not isinstance(snapshot_payload, Mapping):
        raise RuntimeError("repair-004 accepted proxy snapshot is missing")
    snapshot = _snapshot_from_payload(snapshot_payload)
    if snapshot.sha256 != evidence.get("accepted_proxy_snapshot_sha256"):
        raise RuntimeError("repair-004 accepted proxy snapshot drifted")
    if ordinal <= 3:
        expected = repair.PREFIX_EXPECTATIONS[ordinal - 1]
        audit = evidence.get("repeated_full_state_audit")
        residual = audit.get("residual_audit") if isinstance(audit, Mapping) else None
        if (
            evidence.get("schema") != PREFIX_EVIDENCE_SCHEMA
            or evidence.get("source_checkpoint_manifest_sha256")
            != expected.manifest_sha256
            or not isinstance(audit, Mapping)
            or audit.get("passed") is not True
            or not isinstance(residual, Mapping)
            or residual.get("passed") is not True
            or residual != candidate.residual_audit
            or snapshot.reactive_proxy != candidate.reactive_proxy_fraction
            or not v4._checkpoint_close(
                snapshot.operating_cost_usd, candidate.operating_cost_usd
            )
            or candidate.stage_audits.get("repair_003_prefix") != evidence
        ):
            raise RuntimeError("repair-004 prefix evidence drifted")
    else:
        certificate = evidence.get("certificate")
        source = evidence.get("upper_bound_source")
        method = evidence.get("method")
        direct_record = evidence.get("direct_stage_record")
        round_references = evidence.get("level_set_rounds")
        expected_certificate = (
            _normalized_hybrid_certificate(
                certificate,
                snapshot,
                context.input_contract["formal_successor"],
            )
            if isinstance(certificate, Mapping)
            else None
        )
        if (
            evidence.get("schema") != HYBRID_EVIDENCE_SCHEMA
            or source != control["upper_bound_source"]
            or method not in {"direct_exact_cg", "direct_max_or_level_set_bisection"}
            or not v4._checkpoint_close(
                evidence.get("initial_upper_bound"), control["initial_upper_bound"]
            )
            or not isinstance(direct_record, Mapping)
            or direct_record.get("schema") != "rts_gmlc_exact_cg_stage_record_v1"
            or direct_record.get("stage") != "proxy_maximization"
            or not isinstance(certificate, Mapping)
            or v4._exact_json_text(certificate)
            != v4._exact_json_text(expected_certificate)
            or expected_certificate.get("maximum_acceptance_passed") is not True
            or candidate.stage_audits.get("proxy_maximization_hybrid") != evidence
            or evidence.get("model_definition_upper_bound_proof")
            != (
                context.input_contract["formal_successor"][
                    "model_definition_upper_bound_proof"
                ]
                if ordinal >= 5
                else None
            )
        ):
            raise RuntimeError("repair-004 hybrid evidence drifted")
        if method == "direct_exact_cg":
            raw_direct_certificate = direct_record.get("certificate")
            if (
                direct_record.get("eligible") is not True
                or evidence.get("level_set_status") != "not_required"
                or round_references != []
                or not isinstance(raw_direct_certificate, Mapping)
                or v4._exact_json_text(
                    _normalized_hybrid_certificate(
                        raw_direct_certificate,
                        snapshot,
                        context.input_contract["formal_successor"],
                    )
                )
                != v4._exact_json_text(certificate)
            ):
                raise RuntimeError("repair-004 direct proxy evidence drifted")
        elif (
            direct_record.get("eligible") is True
            or evidence.get("level_set_status") != "accepted"
            or not isinstance(round_references, list)
            or not 1
            <= len(round_references)
            <= int(
                context.input_contract["formal_successor"]["level_set_maximum_rounds"]
            )
        ):
            raise RuntimeError("repair-004 fallback proxy evidence drifted")
        v4._validated_stage_certificate(candidate, context, "cost_normalization")
        regret = candidate.stage_audits.get("primary_proxy_regret")
        regret_config = context.config["formal_solver"]["primary_regret"]
        observed_regret = max(
            float(certificate["upper_bound"]) - candidate.reactive_proxy_fraction,
            0.0,
        )
        allowed_regret = (
            float(certificate["absolute_gap"])
            + float(regret_config["proxy_floor_tolerance"])
            + float(regret_config["numerical_audit_allowance"])
        )
        hard_maximum = float(regret_config["hard_maximum"])
        expected_regret_passed = bool(
            observed_regret <= allowed_regret + 1.0e-12
            and observed_regret <= hard_maximum + 1.0e-12
        )
        if (
            not isinstance(regret, Mapping)
            or regret.get("schema") != "rts_gmlc_primary_proxy_regret_certificate_v1"
            or regret.get("passed") is not expected_regret_passed
            or not expected_regret_passed
            or not v4._checkpoint_close(
                regret.get("stage_one_certified_upper_bound"),
                certificate["upper_bound"],
            )
            or not v4._checkpoint_close(
                regret.get("final_commitment_capability_proxy_fraction"),
                candidate.reactive_proxy_fraction,
            )
            or not v4._checkpoint_close(
                regret.get("observed_regret_upper_bound"), observed_regret
            )
            or not v4._checkpoint_close(
                regret.get("stage_one_actual_absolute_gap"),
                certificate["absolute_gap"],
            )
            or not v4._checkpoint_close(
                regret.get("derived_allowed_regret"), allowed_regret
            )
            or not v4._checkpoint_close(regret.get("hard_maximum"), hard_maximum)
        ):
            raise RuntimeError("repair-004 primary regret evidence drifted")
        cost_record = candidate.stage_audits["cost_normalization"]
        floor_tolerance = float(
            context.config["formal_solver"]["stages"]["cost_normalization"][
                "proxy_floor_absolute_tolerance"
            ]
        )
        expected_floor = float(certificate["lower_bound"]) - floor_tolerance
        cost_audit = cost_record.get("final_full_state_audit")
        cost_callback = (
            cost_audit.get("callback_record")
            if isinstance(cost_audit, Mapping)
            else None
        )
        if (
            not isinstance(cost_callback, Mapping)
            or not v4._checkpoint_close(cost_record.get("proxy_floor"), expected_floor)
            or candidate.reactive_proxy_fraction + floor_tolerance < expected_floor
            or cost_callback.get("residual_audit") != candidate.residual_audit
            or not v4._checkpoint_close(
                cost_callback.get("actual_operating_cost_usd"),
                candidate.operating_cost_usd,
            )
            or not v4._checkpoint_close(
                cost_callback.get("commitment_capability_proxy_fraction"),
                candidate.reactive_proxy_fraction,
            )
        ):
            raise RuntimeError("repair-004 cost audit evidence drifted")
    return candidate, snapshot


def _publish_recursive_payload(target: Path, writer: Any, validator: Any) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Immutable artifact already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        writer(staging)
        repair._write_recursive_manifest(staging)
        _verify_manifest(staging)
        validator(staging)
        staging.rename(target)
        _verify_manifest(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _validate_round_artifacts(
    checkpoint_root: Path,
    context: v4._FrontierContext,
    ordinal: int,
    candidate: v4._Candidate,
    evidence: Mapping[str, object],
) -> None:
    if ordinal <= 3:
        if (checkpoint_root / "level_set_rounds").exists():
            raise RuntimeError("repair-004 prefix gained level-set rounds")
        return
    method = evidence.get("method")
    references = evidence.get("level_set_rounds")
    rounds_root = checkpoint_root / "level_set_rounds"
    if method == "direct_exact_cg":
        if references != [] or rounds_root.exists():
            raise RuntimeError("repair-004 direct checkpoint gained level-set rounds")
        return
    if (
        method != "direct_max_or_level_set_bisection"
        or not isinstance(references, list)
        or not references
        or not rounds_root.is_dir()
    ):
        raise RuntimeError("repair-004 level-set round inventory is missing")
    directories = sorted(path for path in rounds_root.iterdir() if path.is_dir())
    if [path.name for path in directories] != [
        f"{index:02d}" for index in range(1, len(references) + 1)
    ]:
        raise RuntimeError("repair-004 level-set round order drifted")
    previous_after = None
    final_after = None
    for round_ordinal, (reference, path) in enumerate(zip(references, directories), 1):
        if not isinstance(reference, Mapping):
            raise RuntimeError("repair-004 level-set round reference drifted")
        _verify_manifest(path)
        document = json.loads((path / "round.json").read_text(encoding="utf-8"))
        before = document.get("bracket_before")
        after = document.get("bracket_after")
        if (
            document.get("schema") != "rts_gmlc_proxy_level_set_round_v1"
            or document.get("candidate_id") != candidate.requested_candidate_id
            or document.get("candidate_ordinal") != ordinal
            or document.get("round_ordinal") != round_ordinal
            or document.get("input_contract_sha256") != context.input_contract_sha256
            or document.get("predecessor_manifest_sha256")
            != evidence.get("predecessor_evidence_sha256")
            or reference.get("round_ordinal") != round_ordinal
            or reference.get("round_sha256") != _sha256(path / "round.json")
            or reference.get("manifest_sha256") != _sha256(path / "SHA256SUMS")
            or not isinstance(before, Mapping)
            or not isinstance(after, Mapping)
            or (
                previous_after is not None
                and v4._exact_json_text(before) != v4._exact_json_text(previous_after)
            )
        ):
            raise RuntimeError("repair-004 level-set round chain drifted")
        if round_ordinal == 1:
            lower_snapshot = before.get("lower_snapshot")
            if not isinstance(lower_snapshot, Mapping) or lower_snapshot.get(
                "sha256"
            ) != evidence.get("fallback_lower_snapshot_sha256"):
                raise RuntimeError("repair-004 fallback lower witness drifted")
        previous_after = after
        final_after = after
    final_snapshot = final_after.get("lower_snapshot")
    certificate = evidence["certificate"]
    if (
        not isinstance(final_snapshot, Mapping)
        or final_snapshot.get("sha256")
        != evidence.get("accepted_proxy_snapshot_sha256")
        or not v4._checkpoint_close(
            final_after.get("lower_bound"), certificate.get("lower_bound")
        )
        or not v4._checkpoint_close(
            final_after.get("upper_bound"), certificate.get("upper_bound")
        )
    ):
        raise RuntimeError("repair-004 final level-set bracket drifted")


def _save_candidate_checkpoint(
    context: v4._FrontierContext,
    output_root: Path,
    ordinal: int,
    candidate: v4._Candidate,
    *,
    mode: str,
    evidence: Mapping[str, object],
    round_root: Path | None = None,
) -> tuple[v4._Candidate, SharedSnapshot]:
    canonical = v4._exact_json_payload(
        _checkpoint_payload(context, ordinal, candidate, mode=mode, evidence=evidence)
    )
    if not isinstance(canonical, dict):
        raise RuntimeError("repair-004 checkpoint canonicalization drifted")
    target = v4._candidate_checkpoint_path(
        output_root, ordinal, candidate.requested_candidate_id
    )
    if target.exists():
        observed = v4._load_json(target, "candidate.json")
        loaded = _validate_checkpoint_document(observed, context, ordinal)
        _validate_round_artifacts(
            target, context, ordinal, loaded[0], observed["evidence"]
        )
        if v4._exact_json_text(observed) != v4._exact_json_text(canonical):
            raise RuntimeError("repair-004 existing checkpoint drifted")
        return loaded

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "candidate.json", canonical)
        if round_root is not None and round_root.is_dir():
            shutil.copytree(round_root, staging / "level_set_rounds")

    def validator(staging: Path) -> None:
        observed = json.loads((staging / "candidate.json").read_text(encoding="utf-8"))
        loaded, _snapshot = _validate_checkpoint_document(observed, context, ordinal)
        _validate_round_artifacts(
            staging, context, ordinal, loaded, observed["evidence"]
        )

    _publish_recursive_payload(target, writer, validator)
    observed = v4._load_json(target, "candidate.json")
    loaded = _validate_checkpoint_document(observed, context, ordinal)
    _validate_round_artifacts(target, context, ordinal, loaded[0], observed["evidence"])
    return loaded


def _load_candidate_checkpoint(
    context: v4._FrontierContext,
    output_root: Path,
    ordinal: int,
) -> tuple[v4._Candidate, SharedSnapshot] | None:
    delta = float(
        context.input_contract["formal_successor"]["candidate_controls"][ordinal - 1][
            "relative_cost_budget_delta"
        ]
    )
    target = v4._candidate_checkpoint_path(
        output_root, ordinal, v4._requested_candidate_id(delta)
    )
    if not target.exists():
        return None
    _verify_manifest(target)
    observed = v4._load_json(target, "candidate.json")
    loaded = _validate_checkpoint_document(observed, context, ordinal)
    _validate_round_artifacts(target, context, ordinal, loaded[0], observed["evidence"])
    return loaded


def _prefix_candidate(
    context: v4._FrontierContext,
    imported: repair.ImportedPrefixCandidate,
    *,
    progress: JsonlProgressWriter,
    candidate_log_root: Path,
) -> tuple[v4._Candidate, SharedSnapshot, dict[str, object]]:
    rehydrated = repair.rehydrate_prefix_snapshot(
        context,
        imported,
        progress=progress,
        log_root=candidate_log_root / "prefix_reconstruction",
    )
    audit = rehydrated.full_state_audit_record
    residual = audit.get("residual_audit")
    if not isinstance(residual, Mapping) or residual.get("passed") is not True:
        raise RuntimeError("repair-004 prefix residual audit is missing")
    source = imported.candidate
    evidence: dict[str, object] = {
        "schema": PREFIX_EVIDENCE_SCHEMA,
        "source_preregistration_manifest_sha256": (
            repair.PREDECESSOR_PREREGISTRATION_MANIFEST_SHA256
        ),
        "source_input_contract_sha256": repair.PREDECESSOR_INPUT_CONTRACT_SHA256,
        "source_checkpoint_manifest_sha256": imported.expectation.manifest_sha256,
        "source_stage_evidence_sha256": common_input_signature_sha256(
            source.stage_audits
        ),
        "source_stage_evidence_imported_as_successor_certificate": False,
        "reconstruction": rehydrated.reconstruction_record,
        "repeated_full_state_audit": audit,
        "accepted_proxy_snapshot": _snapshot_payload(rehydrated.snapshot),
        "accepted_proxy_snapshot_sha256": rehydrated.snapshot.sha256,
    }
    candidate = replace(
        source,
        source="repair_003_verified_predecessor_prefix",
        operating_cost_usd=rehydrated.snapshot.operating_cost_usd,
        reactive_proxy_fraction=rehydrated.snapshot.reactive_proxy,
        stage_audits={"repair_003_prefix": evidence},
        residual_audit=dict(residual),
    )
    if (
        candidate.commitment_sha256 != imported.expectation.commitment_sha256
        or candidate.dispatch_sha256 != imported.expectation.dispatch_sha256
        or candidate.reactive_proxy_fraction
        != imported.expectation.reactive_proxy_fraction
    ):
        raise RuntimeError("repair-004 prefix successor identity drifted")
    return candidate, rehydrated.snapshot, evidence


def _stage_limits(context: v4._FrontierContext, stage: str) -> ExactCgTimeLimits:
    return v4._stage_time_limits(context.config["formal_solver"], stage)


def _stable_fallback_input(direct: Any) -> Any:
    if direct.stage_record.get("eligible") is True:
        return direct
    sanitized_record = dict(direct.stage_record)
    sanitized_record["certificate"] = {"valid": False}
    return replace(
        direct,
        snapshot=None,
        audited_snapshot=None,
        stage_record=sanitized_record,
    )


def _normalized_hybrid_certificate(
    certificate: Mapping[str, object],
    snapshot: SharedSnapshot,
    successor: Mapping[str, object],
) -> dict[str, object]:
    if certificate.get("valid") is not True:
        raise RuntimeError("repair-004 proxy certificate is invalid")
    lower = float(certificate["lower_bound"])
    upper = float(certificate["upper_bound"])
    return acceptance_certificate(
        ProxyBracket(lower, upper, snapshot),
        target_relative_gap=float(successor["target_relative_gap"]),
        maximum_absolute_gap=float(successor["maximum_accepted_absolute_gap"]),
        maximum_relative_gap=float(
            successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
    )


def _hybrid_candidate(
    context: v4._FrontierContext,
    *,
    ordinal: int,
    fallback_lower_snapshot: SharedSnapshot,
    progress: JsonlProgressWriter,
    candidate_log_root: Path,
    deadline_monotonic: float,
) -> tuple[v4._Candidate, SharedSnapshot, dict[str, object], Path | None]:
    successor = context.input_contract["formal_successor"]
    control = successor["candidate_controls"][ordinal - 1]
    delta = float(control["relative_cost_budget_delta"])
    requested_id = v4._requested_candidate_id(delta)
    baseline = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    cost_budget = baseline * (1.0 + delta)
    effective_budget = cost_budget + float(
        context.config["candidate_frontier"]["cost_cap_absolute_tolerance_usd"]
    )
    problem = v4._formal_problem(context, cost_budget_usd=cost_budget)
    event_context = {
        "candidate_ordinal": ordinal,
        "requested_candidate_id": requested_id,
        "relative_cost_budget_delta": delta,
        "repair_003_hybrid": True,
    }
    direct_adapter = V4InitialProxyWarmStartAdapter(
        problem=problem,
        formal_solver=context.config["formal_solver"],
        candidate_frontier=context.config["candidate_frontier"],
        snapshot_contract=context.config["candidate_snapshot"],
        progress=progress,
        log_root=candidate_log_root / "direct_proxy",
        event_context=event_context,
        warm_start=context.config["solver_selection_provenance"][
            "initial_proxy_warm_start"
        ],
    )
    direct = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=problem.all_state_ids,
        seed_state_ids=problem.initial_active_state_ids,
        target_relative_gap=float(successor["target_relative_gap"]),
        maximum_accepted_relative_gap_to_feasible_incumbent=float(
            successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_accepted_absolute_gap=float(successor["maximum_accepted_absolute_gap"]),
        time_limits=_stage_limits(context, "proxy_maximization"),
        callbacks=direct_adapter.callbacks(),
        candidate_deadline_monotonic=deadline_monotonic,
    )
    round_checkpoint_root = candidate_log_root / "level_set_checkpoints"
    predecessor_evidence_sha = common_input_signature_sha256(
        {
            "input_contract_sha256": context.input_contract_sha256,
            "candidate_ordinal": ordinal,
            "fallback_lower_snapshot_sha256": fallback_lower_snapshot.sha256,
            "upper_bound_source": control["upper_bound_source"],
            "initial_upper_bound": control["initial_upper_bound"],
        }
    )
    level_limits = ExactCgTimeLimits(
        master_seconds=float(successor["level_set_master_seconds_per_call"]),
        screen_seconds=float(
            context.config["formal_solver"]["time_limits_seconds"][
                "inactive_state_screen_per_call"
            ]
        ),
        final_audit_seconds=float(
            context.config["formal_solver"]["time_limits_seconds"][
                "final_full_state_audit_per_call"
            ]
        ),
    )

    def level_oracle(floor: float, round_ordinal: int):
        adapter = FormalCgModelAdapter(
            problem=problem,
            formal_solver=context.config["formal_solver"],
            candidate_frontier=context.config["candidate_frontier"],
            snapshot_contract=context.config["candidate_snapshot"],
            progress=progress,
            log_root=candidate_log_root / f"level_set_round_{round_ordinal:02d}",
            event_context={
                **event_context,
                "level_set_round_ordinal": round_ordinal,
            },
        )
        return run_exact_cg_stage(
            stage="level_set_budget_feasibility",
            all_state_ids=problem.all_state_ids,
            seed_state_ids=problem.initial_active_state_ids,
            target_relative_gap=float(successor["target_relative_gap"]),
            maximum_accepted_relative_gap_to_feasible_incumbent=float(
                successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
            ),
            maximum_accepted_absolute_gap=None,
            time_limits=level_limits,
            callbacks=adapter.callbacks(),
            proxy_floor=floor,
            candidate_deadline_monotonic=deadline_monotonic,
        )

    hybrid_input = _stable_fallback_input(direct)
    hybrid = repair.run_hybrid_proxy_certificate(
        hybrid_input,
        fallback_lower_snapshot=fallback_lower_snapshot,
        imported_upper_bound=float(control["initial_upper_bound"]),
        level_oracle=level_oracle,
        effective_budget_usd=effective_budget,
        strict_separation_margin_usd=float(
            successor["strict_cost_separation_margin_usd"]
        ),
        target_relative_gap=float(successor["target_relative_gap"]),
        maximum_absolute_gap=float(successor["maximum_accepted_absolute_gap"]),
        maximum_relative_gap=float(
            successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_rounds=int(successor["level_set_maximum_rounds"]),
        candidate_id=requested_id,
        candidate_ordinal=ordinal,
        input_contract_sha256=context.input_contract_sha256,
        predecessor_manifest_sha256=predecessor_evidence_sha,
        checkpoint_root=round_checkpoint_root,
    )
    hybrid = replace(hybrid, direct_stage_record=direct.stage_record)
    if hybrid.snapshot is not None:
        hybrid = replace(
            hybrid,
            certificate=_normalized_hybrid_certificate(
                hybrid.certificate, hybrid.snapshot, successor
            ),
        )
    if (
        hybrid.snapshot is None
        or hybrid.certificate.get("valid") is not True
        or hybrid.certificate.get("maximum_acceptance_passed") is not True
    ):
        raise RuntimeError(
            "repair-004 hybrid proxy stage unresolved: " + str(hybrid.failure_reason)
        )
    accepted_snapshot = hybrid.snapshot
    floor_tolerance = float(
        context.config["formal_solver"]["stages"]["cost_normalization"][
            "proxy_floor_absolute_tolerance"
        ]
    )
    proxy_floor = float(hybrid.certificate["lower_bound"]) - floor_tolerance
    cost_adapter = FormalCgModelAdapter(
        problem=problem,
        formal_solver=context.config["formal_solver"],
        candidate_frontier=context.config["candidate_frontier"],
        snapshot_contract=context.config["candidate_snapshot"],
        progress=progress,
        log_root=candidate_log_root / "cost_normalization",
        event_context=event_context,
    )
    cost_spec = context.config["formal_solver"]["stages"]["cost_normalization"]
    cost_result = run_exact_cg_stage(
        stage="cost_normalization",
        all_state_ids=problem.all_state_ids,
        seed_state_ids=problem.initial_active_state_ids,
        target_relative_gap=float(cost_spec["target_relative_gap"]),
        maximum_accepted_relative_gap_to_feasible_incumbent=float(
            cost_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_accepted_absolute_gap=cost_spec["maximum_accepted_absolute_gap"],
        time_limits=_stage_limits(context, "cost_normalization"),
        callbacks=cost_adapter.callbacks(),
        proxy_floor=proxy_floor,
        candidate_deadline_monotonic=deadline_monotonic,
    )
    if cost_result.snapshot is None:
        raise RuntimeError(
            "repair-004 cost normalization failed: "
            + str(cost_result.stage_record.get("failure_reason"))
        )
    handle = cost_adapter.final_handles.get("cost_normalization")
    if handle is None:
        raise RuntimeError("repair-004 cost audit model was not retained")
    model = handle.model
    scuc_context = handle.scuc_context
    commitment = v4._extract_commitment(model, scuc_context)
    generation = v4._extract_generation(model, scuc_context, "normal")
    branch_flows = v4._extract_branch_flows(model, scuc_context, "normal")
    dc_flows = v4._extract_dc_flows(model, scuc_context, "normal")
    reserve = v4._extract_reserve(model, scuc_context)
    startup, shutdown = v4._boolean_transitions(
        commitment, context.initial_state.commitment
    )
    proxy_value = v4._reactive_proxy_value(context, problem.points, commitment)
    operating_cost = float(value(model.operating_cost))
    if proxy_value + floor_tolerance < proxy_floor or operating_cost > effective_budget:
        raise RuntimeError("repair-004 normalized candidate violated proxy or budget")
    regret_config = context.config["formal_solver"]["primary_regret"]
    absolute_gap = float(hybrid.certificate["absolute_gap"])
    observed_regret = max(float(hybrid.certificate["upper_bound"]) - proxy_value, 0.0)
    allowed_regret = (
        absolute_gap
        + float(regret_config["proxy_floor_tolerance"])
        + float(regret_config["numerical_audit_allowance"])
    )
    regret_passed = bool(
        observed_regret <= allowed_regret + 1.0e-12
        and observed_regret <= float(regret_config["hard_maximum"]) + 1.0e-12
    )
    primary_regret = {
        "schema": "rts_gmlc_primary_proxy_regret_certificate_v1",
        "stage_one_certified_upper_bound": float(hybrid.certificate["upper_bound"]),
        "final_commitment_capability_proxy_fraction": proxy_value,
        "observed_regret_upper_bound": observed_regret,
        "stage_one_actual_absolute_gap": absolute_gap,
        "proxy_floor_tolerance": float(regret_config["proxy_floor_tolerance"]),
        "numerical_audit_allowance": float(regret_config["numerical_audit_allowance"]),
        "derived_allowed_regret": allowed_regret,
        "hard_maximum": float(regret_config["hard_maximum"]),
        "passed": regret_passed,
    }
    if not regret_passed:
        raise RuntimeError("repair-004 primary proxy regret audit failed")
    final_audit = cost_result.stage_record["final_full_state_audit"]
    residual = final_audit["callback_record"]["residual_audit"]
    round_refs = []
    published_round_root: Path | None = None
    if hybrid.level_set is not None:
        published_round_root = (
            round_checkpoint_root / f"{ordinal:02d}_{requested_id}" / "level_set_rounds"
        )
        for path in sorted(published_round_root.iterdir()):
            round_refs.append(
                {
                    "round_ordinal": int(path.name),
                    "round_sha256": _sha256(path / "round.json"),
                    "manifest_sha256": _sha256(path / "SHA256SUMS"),
                }
            )
    evidence: dict[str, object] = {
        "schema": HYBRID_EVIDENCE_SCHEMA,
        "method": hybrid.method,
        "direct_stage_record": hybrid.direct_stage_record,
        "upper_bound_source": control["upper_bound_source"],
        "initial_upper_bound": float(control["initial_upper_bound"]),
        "model_definition_upper_bound_proof": (
            context.input_contract["formal_successor"][
                "model_definition_upper_bound_proof"
            ]
            if ordinal >= 5
            else None
        ),
        "level_set_status": (
            hybrid.level_set.status if hybrid.level_set is not None else "not_required"
        ),
        "level_set_rounds": round_refs,
        "fallback_lower_snapshot_sha256": fallback_lower_snapshot.sha256,
        "predecessor_evidence_sha256": predecessor_evidence_sha,
        "certificate": hybrid.certificate,
        "accepted_proxy_snapshot": _snapshot_payload(accepted_snapshot),
        "accepted_proxy_snapshot_sha256": accepted_snapshot.sha256,
        "cost_normalization_stage_record_sha256": common_input_signature_sha256(
            cost_result.stage_record
        ),
    }
    candidate = v4._Candidate(
        requested_candidate_id=requested_id,
        source="q_proxy_repair_003_hybrid_certificate",
        relative_cost_budget_delta=delta,
        cost_budget_usd=cost_budget,
        operating_cost_usd=operating_cost,
        reactive_proxy_fraction=proxy_value,
        commitment_sha256=v4._commitment_sha256(commitment),
        dispatch_sha256=v4._dispatch_sha256(generation, branch_flows, dc_flows),
        commitment=commitment,
        startup=startup,
        shutdown=shutdown,
        generation_mw=generation,
        branch_flows_mw=branch_flows,
        dc_flows_mw=dc_flows,
        reserve_up_mw=reserve,
        stage_audits={
            "proxy_maximization_hybrid": evidence,
            "cost_normalization": cost_result.stage_record,
            "primary_proxy_regret": primary_regret,
        },
        residual_audit=dict(residual),
    )
    return candidate, accepted_snapshot, evidence, published_round_root


def _candidate_to_loaded(
    candidate_id: str, candidate: v4._Candidate
) -> v4._LoadedCandidate:
    return v4._LoadedCandidate(
        candidate_id=candidate_id,
        requested_candidate_id=candidate.requested_candidate_id,
        relative_cost_budget_delta=candidate.relative_cost_budget_delta,
        operating_cost_usd=candidate.operating_cost_usd,
        reactive_proxy_fraction=candidate.reactive_proxy_fraction,
        commitment_sha256=candidate.commitment_sha256,
        dispatch_sha256=candidate.dispatch_sha256,
        commitment=candidate.commitment,
        startup=candidate.startup,
        shutdown=candidate.shutdown,
        generation_mw=candidate.generation_mw,
        branch_flows_mw=candidate.branch_flows_mw,
        dc_flows_mw=candidate.dc_flows_mw,
    )


def _frontier_material(
    context: v4._FrontierContext,
    output_root: Path,
) -> tuple[
    list[v4._Candidate],
    list[dict[str, object]],
    list[tuple[str, v4._Candidate]],
    tuple[Any, ...],
    dict[str, str],
]:
    candidates = [v4._baseline_candidate(context)]
    manifests: dict[str, str] = {}
    for ordinal in range(1, 7):
        loaded = _load_candidate_checkpoint(context, output_root, ordinal)
        if loaded is None:
            raise RuntimeError("repair-004 all six checkpoints are required")
        candidate, _snapshot = loaded
        candidates.append(candidate)
        path = v4._candidate_checkpoint_path(
            output_root, ordinal, candidate.requested_candidate_id
        )
        manifests[candidate.requested_candidate_id] = _sha256(path / "SHA256SUMS")
    rows, selected = v4._deduplicate_candidates(candidates)
    timestamps = tuple(item.isoformat() for item in context.request.timestamps)
    details = v4._candidate_detail_rows(selected, timestamps)
    return candidates, rows, selected, details, manifests


def _frontier_summary(
    context: v4._FrontierContext,
    candidates: Sequence[v4._Candidate],
    selected: Sequence[tuple[str, v4._Candidate]],
    manifests: Mapping[str, str],
    *,
    attempt_id: str,
) -> dict[str, Any]:
    return {
        "schema": FRONTIER_SCHEMA,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "requested_candidate_count": len(candidates),
        "requested_budget_candidate_count": 6,
        "parent_baseline_included": True,
        "unique_candidate_count": len(selected),
        "all_budget_candidates_completed_before_deduplication": True,
        "candidate_generation_completed_before_any_joint_ac_solve": True,
        "candidate_generation_uses_ac_outcomes": False,
        "candidate_generation_attempt_id": attempt_id,
        "algorithm": context.config["formal_solver"]["algorithm"],
        "solver": context.config["formal_solver"]["solver"],
        "candidate_checkpoint_manifest_sha256s": dict(manifests),
        "checkpoint_schema": CHECKPOINT_SCHEMA,
        "float_serialization": FLOAT_SERIALIZATION,
        "relative_cost_budget_deltas": context.config["candidate_frontier"][
            "relative_cost_budget_deltas"
        ],
        "candidate_ids": [candidate_id for candidate_id, _item in selected],
        "commitment_sha256s": [item.commitment_sha256 for _id, item in selected],
        "minimum_reactive_proxy_fraction": min(
            item.reactive_proxy_fraction for _id, item in selected
        ),
        "maximum_reactive_proxy_fraction": max(
            item.reactive_proxy_fraction for _id, item in selected
        ),
        "joint_ac_solver_call_count": 0,
        **context.config["evidence"],
    }


def _load_candidate_frontier(
    context: v4._FrontierContext,
    output_root: Path,
    *,
    frontier_root: Path | None = None,
) -> tuple[list[v4._LoadedCandidate], str]:
    root = frontier_root or output_root / "candidate_frontier"
    _verify_manifest(root)
    summary = v4._load_json(root, "summary.json")
    candidates, rows, selected, details, manifests = _frontier_material(
        context, output_root
    )
    attempt_id = summary.get("candidate_generation_attempt_id")
    if (
        not isinstance(attempt_id, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None
    ):
        raise RuntimeError("repair-004 frontier attempt identity drifted")
    expected_summary = _frontier_summary(
        context,
        candidates,
        selected,
        manifests,
        attempt_id=attempt_id,
    )
    if v4._exact_json_text(summary) != v4._exact_json_text(expected_summary):
        raise RuntimeError("repair-004 frontier summary drifted")
    with tempfile.TemporaryDirectory() as temporary:
        expected = Path(temporary)
        v4._write_csv(expected / "candidates.csv", v4._CANDIDATE_FIELDS, rows)
        v4._write_csv(expected / "commitment.csv", v4._COMMITMENT_FIELDS, details[0])
        v4._write_csv(
            expected / "normal_generation.csv", v4._GENERATION_FIELDS, details[1]
        )
        v4._write_csv(
            expected / "normal_branch_flows.csv", v4._BRANCH_FIELDS, details[2]
        )
        v4._write_csv(expected / "normal_dc_flows.csv", v4._DC_FLOW_FIELDS, details[3])
        v4._write_csv(expected / "reserve_up.csv", v4._RESERVE_FIELDS, details[4])
        v4._write_exact_json(expected / "candidate_audits.json", details[5])
        for name in (
            "candidates.csv",
            "commitment.csv",
            "normal_generation.csv",
            "normal_branch_flows.csv",
            "normal_dc_flows.csv",
            "reserve_up.csv",
            "candidate_audits.json",
        ):
            if (root / name).read_bytes() != (expected / name).read_bytes():
                raise RuntimeError(f"repair-004 frontier file drifted: {name}")
    return (
        [_candidate_to_loaded(candidate_id, item) for candidate_id, item in selected],
        _sha256(root / "SHA256SUMS"),
    )


def _generate_candidate_frontier_unleased(
    context: v4._FrontierContext,
    output_root: Path,
    *,
    attempt_id: str,
) -> dict[str, Any]:
    _require_preregistration(context, output_root)
    target = output_root / "candidate_frontier"
    if target.exists():
        _load_candidate_frontier(context, output_root)
        return v4._load_json(target, "summary.json")
    if (output_root / "joint_ac").exists():
        raise RuntimeError("Cannot generate repair-004 candidates after joint AC")
    log_root = (
        Path(context.config["formal_solver"]["progress_logging"]["log_directory"])
        / attempt_id
    )
    progress = JsonlProgressWriter(
        log_root / "progress.jsonl",
        run_id=attempt_id,
        preregistration_id=context.config["preregistration"]["id"],
        input_contract_sha256=context.input_contract_sha256,
    )
    started = datetime.now(timezone.utc)
    v4._write_exact_json(
        log_root / "attempt.json",
        {
            "schema": "rts_gmlc_v4_repair_004_candidate_attempt_v1",
            "attempt_id": attempt_id,
            "pid": os.getpid(),
            "started_utc": started.isoformat(),
            "preregistration_id": context.config["preregistration"]["id"],
            "input_contract_sha256": context.input_contract_sha256,
            "checkpoint_schema": CHECKPOINT_SCHEMA,
        },
    )
    progress.emit(
        "attempt_started",
        stage="candidate_generation",
        candidate_count=6,
        completed_budget_candidate_count=0,
        started_utc=started.isoformat(),
    )
    imported = repair.verify_predecessor_prefix()
    previous_snapshot: SharedSnapshot | None = None
    total_limit = float(
        context.config["formal_solver"]["time_limits_seconds"]["per_candidate_total"]
    )
    for ordinal in range(1, 7):
        control = context.input_contract["formal_successor"]["candidate_controls"][
            ordinal - 1
        ]
        requested_id = v4._requested_candidate_id(
            float(control["relative_cost_budget_delta"])
        )
        loaded = _load_candidate_checkpoint(context, output_root, ordinal)
        if loaded is not None:
            candidate, previous_snapshot = loaded
            progress.emit(
                "candidate_checkpoint_loaded",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                checkpoint_manifest_sha256=_sha256(
                    v4._candidate_checkpoint_path(output_root, ordinal, requested_id)
                    / "SHA256SUMS"
                ),
                completed_budget_candidate_count=ordinal,
            )
            continue
        progress.emit(
            "candidate_started",
            candidate_ordinal=ordinal,
            requested_candidate_id=requested_id,
            relative_cost_budget_delta=control["relative_cost_budget_delta"],
            mode=control["mode"],
            total_limit_seconds=total_limit,
            completed_budget_candidate_count=ordinal - 1,
        )
        candidate_log_root = log_root / f"{ordinal:02d}_{requested_id}"
        try:
            if ordinal <= 3:
                candidate, snapshot, evidence = _prefix_candidate(
                    context,
                    imported[ordinal - 1],
                    progress=progress,
                    candidate_log_root=candidate_log_root,
                )
                round_root = None
            else:
                if previous_snapshot is None:
                    raise RuntimeError(
                        "repair-004 predecessor lower snapshot is missing"
                    )
                deadline = monotonic() + total_limit
                candidate, snapshot, evidence, round_root = _hybrid_candidate(
                    context,
                    ordinal=ordinal,
                    fallback_lower_snapshot=previous_snapshot,
                    progress=progress,
                    candidate_log_root=candidate_log_root,
                    deadline_monotonic=deadline,
                )
            candidate, previous_snapshot = _save_candidate_checkpoint(
                context,
                output_root,
                ordinal,
                candidate,
                mode=str(control["mode"]),
                evidence=evidence,
                round_root=round_root,
            )
        except Exception as error:
            progress.emit(
                "candidate_failed",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                error_type=type(error).__name__,
                error_message=str(error) or repr(error),
                completed_budget_candidate_count=ordinal - 1,
            )
            raise
        checkpoint = v4._candidate_checkpoint_path(output_root, ordinal, requested_id)
        progress.emit(
            "candidate_completed",
            candidate_ordinal=ordinal,
            requested_candidate_id=requested_id,
            checkpoint_manifest_sha256=_sha256(checkpoint / "SHA256SUMS"),
            commitment_sha256=candidate.commitment_sha256,
            dispatch_sha256=candidate.dispatch_sha256,
            completed_budget_candidate_count=ordinal,
        )
    candidates, rows, selected, details, manifests = _frontier_material(
        context, output_root
    )
    summary = _frontier_summary(
        context, candidates, selected, manifests, attempt_id=attempt_id
    )

    def writer(staging: Path) -> None:
        v4._write_csv(staging / "candidates.csv", v4._CANDIDATE_FIELDS, rows)
        v4._write_csv(staging / "commitment.csv", v4._COMMITMENT_FIELDS, details[0])
        v4._write_csv(
            staging / "normal_generation.csv", v4._GENERATION_FIELDS, details[1]
        )
        v4._write_csv(
            staging / "normal_branch_flows.csv", v4._BRANCH_FIELDS, details[2]
        )
        v4._write_csv(staging / "normal_dc_flows.csv", v4._DC_FLOW_FIELDS, details[3])
        v4._write_csv(staging / "reserve_up.csv", v4._RESERVE_FIELDS, details[4])
        v4._write_exact_json(staging / "candidate_audits.json", details[5])
        v4._write_exact_json(staging / "summary.json", summary)

    v4._publish_immutable_payload(
        target,
        writer,
        validator=lambda staging: _load_candidate_frontier(
            context, output_root, frontier_root=staging
        ),
    )
    _load_candidate_frontier(context, output_root)
    manifest = _sha256(target / "SHA256SUMS")
    progress.emit(
        "frontier_published",
        candidate_frontier_manifest_sha256=manifest,
        completed_budget_candidate_count=6,
    )
    progress.emit(
        "attempt_completed",
        stage="candidate_generation",
        candidate_frontier_manifest_sha256=manifest,
        completed_budget_candidate_count=6,
    )
    return v4._load_json(target, "summary.json")


def generate_candidate_frontier(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    _require_preregistration(context, output_root)
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("candidate_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid repair-004 candidate attempt ID")
    progress_path = (
        Path(context.config["formal_solver"]["progress_logging"]["log_directory"])
        / attempt_id
        / "progress.jsonl"
    )
    with ExecutionLease.acquire(
        output_root / "execution_lease",
        stage="generate_candidates",
        attempt_id=attempt_id,
    ):
        try:
            return _generate_candidate_frontier_unleased(
                context, output_root, attempt_id=attempt_id
            )
        except BaseException as error:
            if progress_path.is_file():
                try:
                    v4._append_attempt_failed(progress_path, error)
                except Exception as logging_error:
                    error.add_note(
                        "Failed to append repair-004 attempt_failed: "
                        + (str(logging_error) or repr(logging_error))
                    )
            raise


def _joint_worker_command(
    *,
    python_executable: Path,
    config_path: Path,
    output_root: Path,
    candidate_id: str,
    initial_strategy: str,
    worker_result: Path,
    native_log: Path,
    call_manifest_sha256: str,
) -> list[str]:
    return [
        str(python_executable),
        "-B",
        "-m",
        _SUCCESSOR_MODULE,
        "--config",
        str(config_path.resolve()),
        "--stage",
        "joint-call-worker",
        "--output-directory",
        str(output_root.resolve()),
        "--candidate-id",
        candidate_id,
        "--initial-strategy",
        initial_strategy,
        "--worker-result-directory",
        str(worker_result.resolve()),
        "--native-solver-log",
        str(native_log.resolve()),
        "--call-registration-manifest-sha256",
        call_manifest_sha256,
    ]


def run_joint_call_worker(
    config_path: Path,
    *,
    output_directory: Path,
    candidate_id: str,
    initial_strategy: str,
    result_directory: Path,
    native_solver_log: Path,
    call_registration_manifest_sha256: str,
) -> dict[str, object]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    _require_preregistration(context, output_root)
    candidates, frontier_manifest = _load_candidate_frontier(context, output_root)
    matches = [item for item in candidates if item.candidate_id == candidate_id]
    if len(matches) != 1:
        raise RuntimeError("repair-004 worker candidate identity drifted")
    candidate = matches[0]
    if initial_strategy not in context.config["joint_ac"]["initial_strategies"]:
        raise RuntimeError("repair-004 worker strategy drifted")
    observed_call_manifest = v4._validate_joint_call_registration(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
    )
    if observed_call_manifest != call_registration_manifest_sha256:
        raise RuntimeError("repair-004 worker call registration drifted")
    call_root = v4._joint_call_registration_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    call_registration = v4._load_json(call_root, "call.json")
    parent_pid = call_registration["parent_pid"]
    parent_attempt_id = call_registration["parent_attempt_id"]
    registered_result, registered_native, _ = v4._registered_joint_worker_paths(
        context, call_registration
    )
    if (
        parent_pid != os.getppid()
        or registered_result != result_directory.resolve()
        or registered_native != native_solver_log.resolve()
    ):
        raise RuntimeError("repair-004 worker parent identity drifted")
    active_lease = json.loads(
        (output_root / "execution_lease" / "active" / "lease.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        not isinstance(active_lease, dict)
        or active_lease.get("schema") != "execution_lease_v1"
        or active_lease.get("pid") != parent_pid
        or active_lease.get("stage") != "run_joint_ac"
        or active_lease.get("attempt_id") != parent_attempt_id
    ):
        raise RuntimeError("repair-004 worker execution lease drifted")
    runtime = context.config["joint_ac"]["runtime_control"]
    with v4.ParentProcessWatchdog(
        int(parent_pid),
        interval_seconds=float(runtime["parent_watchdog_interval_seconds"]),
    ):
        return v4._execute_joint_call_worker(
            context,
            candidate,
            initial_strategy,
            frontier_manifest,
            result_directory,
            native_solver_log,
            call_registration_manifest_sha256,
        )


def _run_joint_worker_process(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
    log_root: Path,
    progress: JsonlProgressWriter,
    call_manifest: str,
) -> tuple[v4._JointRows, Path, str]:
    key = v4._joint_call_key(candidate.candidate_id, initial_strategy)
    worker_result, native_log, process_log = v4._joint_worker_paths(
        log_root, candidate.candidate_id, initial_strategy
    )
    if any(path.exists() for path in (worker_result, native_log, process_log)):
        raise FileExistsError("repair-004 joint worker artifact already exists")
    process_log.parent.mkdir(parents=True, exist_ok=True)
    native_log.parent.mkdir(parents=True, exist_ok=True)
    runtime = context.config["joint_ac"]["runtime_control"]
    wall_limit = float(runtime["max_wall_time_seconds_per_call"])
    termination_grace = float(runtime["termination_grace_seconds"])
    command = _joint_worker_command(
        python_executable=Path(sys.executable),
        config_path=context.config_path,
        output_root=output_root,
        candidate_id=candidate.candidate_id,
        initial_strategy=initial_strategy,
        worker_result=worker_result,
        native_log=native_log,
        call_manifest_sha256=call_manifest,
    )
    call_id = f"joint_ac.{key}"
    with process_log.open("xb") as output:
        process = subprocess.Popen(
            command,
            cwd=Path(__file__).resolve().parents[1],
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            deadline_monotonic = monotonic() + wall_limit
            deadline_utc = datetime.now(timezone.utc) + timedelta(seconds=wall_limit)
            progress.emit(
                "joint_call_started",
                stage="joint_ac",
                call_id=call_id,
                candidate_id=candidate.candidate_id,
                requested_candidate_id=candidate.requested_candidate_id,
                initial_strategy=initial_strategy,
                deadline_utc=deadline_utc.isoformat(),
                max_wall_time_seconds=wall_limit,
                termination_grace_seconds=termination_grace,
                native_log=str(native_log.resolve()),
                worker_pid=process.pid,
                call_registration_manifest_sha256=call_manifest,
            )
            with v4._CheckedProgressHeartbeat(
                progress,
                interval_seconds=float(runtime["heartbeat_interval_seconds"]),
                payload={
                    "stage": "joint_ac",
                    "call_id": call_id,
                    "candidate_id": candidate.candidate_id,
                    "requested_candidate_id": candidate.requested_candidate_id,
                    "initial_strategy": initial_strategy,
                    "deadline_utc": deadline_utc.isoformat(),
                    "native_log": str(native_log.resolve()),
                    "worker_pid": process.pid,
                },
            ) as heartbeat:
                while process.poll() is None:
                    heartbeat.raise_if_failed()
                    remaining = deadline_monotonic - monotonic()
                    if remaining <= 0.0:
                        raise subprocess.TimeoutExpired(command, wall_limit)
                    try:
                        process.wait(timeout=min(remaining, 5.0))
                    except subprocess.TimeoutExpired:
                        continue
                heartbeat.raise_if_failed()
        except subprocess.TimeoutExpired as error:
            process.terminate()
            try:
                process.wait(timeout=termination_grace)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=termination_grace)
            raise TimeoutError(
                f"repair-004 joint call exceeded {wall_limit} seconds"
            ) from error
        except BaseException:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=termination_grace)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=termination_grace)
            raise
    if process.returncode != 0:
        raise RuntimeError(
            f"repair-004 joint worker failed with exit code {process.returncode}; "
            f"see {process_log}"
        )
    rows, worker_manifest = v4._load_joint_worker_result(
        context,
        worker_result,
        native_log,
        candidate,
        initial_strategy,
        frontier_manifest,
        call_manifest,
        prepared_cases,
        chronology,
    )
    return rows, native_log, worker_manifest


def _run_joint_ac_attempt(
    context: v4._FrontierContext,
    output_root: Path,
    registration: Mapping[str, Any],
    candidates: Sequence[v4._LoadedCandidate],
    frontier_manifest: str,
    attempt_id: str,
    log_root: Path,
    progress: JsonlProgressWriter,
) -> dict[str, Any]:
    runtime = context.config["joint_ac"]["runtime_control"]
    progress.emit("joint_preparation_started", stage="joint_ac_preparation")
    with v4._CheckedProgressHeartbeat(
        progress,
        interval_seconds=float(runtime["heartbeat_interval_seconds"]),
        payload={"stage": "joint_ac_preparation"},
    ):
        prepared = {
            item.candidate_id: v4._prepared_joint_cases(context, item)
            for item in candidates
        }
        chronology = {
            item.candidate_id: v4._joint_chronology(context, item)
            for item in candidates
        }
    progress.emit("joint_preparation_completed", stage="joint_ac_preparation")
    target = output_root / "joint_ac"
    if target.exists():
        return v4._load_joint_results(
            context,
            target,
            registration,
            candidates,
            frontier_manifest,
            prepared,
            chronology,
        )
    parts = []
    completed = 0
    total = len(candidates) * len(context.config["joint_ac"]["initial_strategies"])
    for candidate in candidates:
        for strategy_value in context.config["joint_ac"]["initial_strategies"]:
            strategy = str(strategy_value)
            loaded = v4._load_joint_checkpoint(
                context,
                output_root,
                candidate,
                strategy,
                frontier_manifest,
                prepared[candidate.candidate_id],
                chronology[candidate.candidate_id],
            )
            if loaded is not None:
                rows, checkpoint_manifest, call_manifest = loaded
                parts.append(rows)
                completed += 1
                progress.emit(
                    "joint_checkpoint_loaded",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    completed_joint_call_count=completed,
                    expected_joint_call_count=total,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=call_manifest,
                )
                continue
            existing_call_manifest = v4._validate_joint_call_registration(
                context, output_root, candidate, strategy, frontier_manifest
            )
            if existing_call_manifest is not None:
                call_registration = v4._load_json(
                    v4._joint_call_registration_path(
                        output_root, candidate.candidate_id, strategy
                    ),
                    "call.json",
                )
                registered_result, registered_native, _ = (
                    v4._registered_joint_worker_paths(context, call_registration)
                )
                if not registered_result.is_dir() or not registered_native.is_file():
                    raise RuntimeError(
                        "repair-004 joint call is incomplete; retry is forbidden"
                    )
                worker_rows, worker_manifest = v4._load_joint_worker_result(
                    context,
                    registered_result,
                    registered_native,
                    candidate,
                    strategy,
                    frontier_manifest,
                    existing_call_manifest,
                    prepared[candidate.candidate_id],
                    chronology[candidate.candidate_id],
                )
                rows, checkpoint_manifest, observed_call_manifest = (
                    v4._save_joint_checkpoint(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        frontier_manifest,
                        existing_call_manifest,
                        prepared[candidate.candidate_id],
                        chronology[candidate.candidate_id],
                        worker_rows,
                        registered_native,
                        worker_manifest,
                    )
                )
                if observed_call_manifest != existing_call_manifest:
                    raise RuntimeError("repair-004 recovered call manifest drifted")
                parts.append(rows)
                completed += 1
                progress.emit(
                    "joint_worker_result_recovered",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    worker_result_manifest_sha256=worker_manifest,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=existing_call_manifest,
                    completed_joint_call_count=completed,
                    expected_joint_call_count=total,
                )
                continue
            worker_result, native_log_path, process_log_path = v4._joint_worker_paths(
                log_root, candidate.candidate_id, strategy
            )
            call_manifest = v4._register_joint_call(
                context,
                output_root,
                candidate,
                strategy,
                frontier_manifest,
                parent_attempt_id=attempt_id,
                parent_pid=os.getpid(),
                worker_result_directory=worker_result,
                native_solver_log=native_log_path,
                worker_process_log=process_log_path,
            )
            try:
                worker_rows, native_log, worker_manifest = _run_joint_worker_process(
                    context,
                    output_root,
                    candidate,
                    strategy,
                    frontier_manifest,
                    prepared[candidate.candidate_id],
                    chronology[candidate.candidate_id],
                    log_root,
                    progress,
                    call_manifest,
                )
                rows, checkpoint_manifest, observed_call_manifest = (
                    v4._save_joint_checkpoint(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        frontier_manifest,
                        call_manifest,
                        prepared[candidate.candidate_id],
                        chronology[candidate.candidate_id],
                        worker_rows,
                        native_log,
                        worker_manifest,
                    )
                )
            except BaseException as error:
                progress.emit(
                    "joint_call_failed",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    error_type=type(error).__name__,
                    error_message=str(error) or repr(error),
                    completed_joint_call_count=completed,
                    expected_joint_call_count=total,
                )
                raise
            if observed_call_manifest != call_manifest:
                raise RuntimeError("repair-004 joint call manifest drifted")
            parts.append(rows)
            completed += 1
            run_row = rows.runs[0]
            progress.emit(
                "joint_call_completed",
                stage="joint_ac",
                candidate_id=candidate.candidate_id,
                requested_candidate_id=candidate.requested_candidate_id,
                initial_strategy=strategy,
                solver_success=v4._parse_bool(
                    run_row["solver_success"], label="solver_success"
                ),
                feasibility_witnessed=v4._parse_bool(
                    run_row["feasibility_witnessed"], label="feasibility_witnessed"
                ),
                return_status=str(run_row["return_status"]),
                iterations=v4._exact_int(run_row["iterations"], label="iterations"),
                native_log=str(native_log.resolve()),
                native_log_sha256=_sha256(native_log),
                worker_result_manifest_sha256=worker_manifest,
                checkpoint_manifest_sha256=checkpoint_manifest,
                call_registration_manifest_sha256=call_manifest,
                completed_joint_call_count=completed,
                expected_joint_call_count=total,
            )
    merged = v4._merge_joint_rows(parts)
    checkpoint_rows, checkpoint_manifests, call_manifests = (
        v4._load_all_joint_checkpoints(
            context,
            output_root,
            candidates,
            frontier_manifest,
            prepared,
            chronology,
        )
    )
    if merged != checkpoint_rows:
        raise RuntimeError("repair-004 resumed joint row order drifted")
    v4._validate_joint_result_rows(
        context,
        candidates,
        prepared,
        chronology,
        merged.runs,
        merged.hours,
        merged.generators,
        merged.buses,
        merged.branches,
        merged.reserves,
    )
    summary = v4._joint_summary(
        context,
        registration,
        candidates,
        frontier_manifest,
        merged.runs,
        checkpoint_manifests,
        call_manifests,
    )

    def writer(staging: Path) -> None:
        v4._write_joint_rows(staging, merged)
        v4._write_exact_json(staging / "summary.json", summary)

    v4._publish_immutable_payload(
        target,
        writer,
        validator=lambda staging: v4._load_joint_results(
            context,
            staging,
            registration,
            candidates,
            frontier_manifest,
            prepared,
            chronology,
        ),
    )
    result = v4._load_joint_results(
        context,
        target,
        registration,
        candidates,
        frontier_manifest,
        prepared,
        chronology,
    )
    manifest = _sha256(target / "SHA256SUMS")
    progress.emit(
        "joint_results_published",
        stage="joint_ac",
        joint_manifest_sha256=manifest,
        completed_joint_call_count=completed,
        expected_joint_call_count=total,
    )
    progress.emit(
        "attempt_completed",
        stage="joint_ac",
        joint_manifest_sha256=manifest,
        completed_joint_call_count=completed,
        expected_joint_call_count=total,
    )
    return result


def run_joint_ac(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    candidates, frontier_manifest = _load_candidate_frontier(context, output_root)
    if not candidates:
        raise RuntimeError("repair-004 candidate frontier is empty")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("joint_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid repair-004 joint attempt ID")
    log_root = (
        Path(context.config["joint_ac"]["runtime_control"]["log_directory"])
        / attempt_id
    )
    target = output_root / "joint_ac"
    with ExecutionLease.acquire(
        output_root / "execution_lease",
        stage="run_joint_ac",
        attempt_id=attempt_id,
    ):
        if target.exists():
            prepared = {
                item.candidate_id: v4._prepared_joint_cases(context, item)
                for item in candidates
            }
            chronology = {
                item.candidate_id: v4._joint_chronology(context, item)
                for item in candidates
            }
            return v4._load_joint_results(
                context,
                target,
                registration,
                candidates,
                frontier_manifest,
                prepared,
                chronology,
            )
        progress = JsonlProgressWriter(
            log_root / "progress.jsonl",
            run_id=attempt_id,
            preregistration_id=context.config["preregistration"]["id"],
            input_contract_sha256=context.input_contract_sha256,
        )
        started = datetime.now(timezone.utc)
        v4._write_exact_json(
            log_root / "attempt.json",
            {
                "schema": "rts_gmlc_v4_repair_004_joint_attempt_v1",
                "attempt_id": attempt_id,
                "pid": os.getpid(),
                "started_utc": started.isoformat(),
                "preregistration_id": context.config["preregistration"]["id"],
                "input_contract_sha256": context.input_contract_sha256,
                "candidate_frontier_manifest_sha256": frontier_manifest,
            },
        )
        progress.emit(
            "attempt_started",
            stage="joint_ac",
            started_utc=started.isoformat(),
            expected_joint_call_count=len(candidates)
            * len(context.config["joint_ac"]["initial_strategies"]),
            completed_joint_call_count=0,
        )
        try:
            return _run_joint_ac_attempt(
                context,
                output_root,
                registration,
                candidates,
                frontier_manifest,
                attempt_id,
                log_root,
                progress,
            )
        except BaseException as error:
            try:
                progress.emit(
                    "attempt_failed",
                    stage="joint_ac",
                    error_type=type(error).__name__,
                    error_message=str(error) or repr(error),
                )
            except Exception as logging_error:
                error.add_note(
                    "Failed to emit repair-004 joint attempt_failed: "
                    + (str(logging_error) or repr(logging_error))
                )
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--stage",
        choices=(
            "prepare",
            "generate-candidates",
            "run-joint-ac",
            "joint-call-worker",
        ),
        required=True,
    )
    parser.add_argument("--attempt-id")
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--candidate-id")
    parser.add_argument("--initial-strategy")
    parser.add_argument("--worker-result-directory", type=Path)
    parser.add_argument("--native-solver-log", type=Path)
    parser.add_argument("--call-registration-manifest-sha256")
    args = parser.parse_args()
    worker_values = (
        args.candidate_id,
        args.initial_strategy,
        args.worker_result_directory,
        args.native_solver_log,
        args.call_registration_manifest_sha256,
    )
    if args.stage == "joint-call-worker" and any(
        value_ is None for value_ in worker_values
    ):
        parser.error("joint-call-worker requires candidate, strategy, result, and log")
    if args.stage != "joint-call-worker" and any(
        value_ is not None for value_ in worker_values
    ):
        parser.error("joint worker arguments are only valid for joint-call-worker")
    if args.stage == "prepare":
        result = prepare_preregistration(
            args.config, output_directory=args.output_directory
        )
    elif args.stage == "generate-candidates":
        result = generate_candidate_frontier(
            args.config,
            output_directory=args.output_directory,
            attempt_id=args.attempt_id,
        )
    elif args.stage == "run-joint-ac":
        result = run_joint_ac(
            args.config,
            output_directory=args.output_directory,
            attempt_id=args.attempt_id,
        )
    else:
        if args.output_directory is None:
            parser.error("joint-call-worker requires --output-directory")
        result = run_joint_call_worker(
            args.config,
            output_directory=args.output_directory,
            candidate_id=str(args.candidate_id),
            initial_strategy=str(args.initial_strategy),
            result_directory=args.worker_result_directory,
            native_solver_log=args.native_solver_log,
            call_registration_manifest_sha256=str(
                args.call_registration_manifest_sha256
            ),
        )
    print(json.dumps(v4._exact_json_payload(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
