"""Operational restart successor for repair-005 interrupted candidate generation."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import shutil
import tempfile
from collections.abc import Mapping
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from time import monotonic
from typing import Any

import yaml
from pyomo.environ import value

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments import (
    record_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005_interruption as interruption,
)
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005_formal as repair005,
)
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004_formal as repair004,
)
from experiments.process_google_power_workload_day0 import _verify_manifest
from src.grid.rts_gmlc_exact_cg import SharedSnapshot
from src.grid.rts_gmlc_cost_bisection import (
    CostBisectionResult,
    CostBracket,
    CostOracleEvidence,
    acceptance_certificate as cost_acceptance_certificate,
    load_contiguous_round_checkpoints,
    run_bracketed_cost_bisection,
)
from src.grid.rts_gmlc_exact_cg_runner import (
    ExactCgCall,
    ExactCgStageResult,
    run_exact_cg_stage,
)
from src.grid.rts_gmlc_formal_cg_adapter import FormalCgModelAdapter
from src.grid.rts_gmlc_level_set import _snapshot_from_payload, _snapshot_payload
from src.scenarios.common_input_signature import common_input_signature_sha256
from src.solvers.execution_lease import ExecutionLease
from src.solvers.mip_progress import JsonlProgressWriter

DEFAULT_CONFIG_PATH = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_006.yaml"
)
CHECKPOINT_SCHEMA = "rts_gmlc_v4_repair_006_cost_bisection_candidate_checkpoint_v1"
PREFIX_EVIDENCE_SCHEMA = "rts_gmlc_v4_repair_006_prefix_import_evidence_v1"
HYBRID_EVIDENCE_SCHEMA = "rts_gmlc_v4_repair_006_hybrid_cost_evidence_v1"
COMBINED_COST_SCHEMA = "rts_gmlc_v4_repair_006_combined_cost_certificate_v1"
FRONTIER_SCHEMA = "rts_gmlc_v4_repair_006_candidate_frontier_v1"
FLOAT_SERIALIZATION = "python_json_roundtrip_full_precision_v1"
_SUCCESSOR_MODULE = (
    "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_006_formal"
)
_CONFIG_KEYS = {
    "schema",
    "preregistration",
    "base_v4",
    "predecessor_repair_005",
    "formal_successor",
    "implementation",
    "output",
    "logging",
}


def _sha256(path: Path) -> str:
    return v4._sha256(path)


def _verify_file(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise RuntimeError(f"repair-005 {label} hash drifted")


def _read_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _CONFIG_KEYS:
        raise ValueError("repair-006 config schema drifted")
    preregistration = config["preregistration"]
    predecessor = config["predecessor_repair_005"]
    successor = config["formal_successor"]
    controls = successor.get("candidate_controls")
    if (
        config.get("schema") != "rts_gmlc_v4_repair_006_formal_successor_config_v1"
        or preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_006"
        or preregistration.get("schema")
        != "rts_gmlc_zero_dc_ac_aware_commitment_preregistration_v4_repair_006"
        or preregistration.get("candidate_frontier_outcomes_observed") is not False
        or preregistration.get("joint_ac_outcomes_observed") is not False
        or config["base_v4"].get("scientific_config_changed") is not False
        or config["base_v4"].get("joint_ac_protocol_changed") is not False
        or predecessor.get("completed_prefix_count") != 4
        or predecessor.get("candidate_frontier_published") is not False
        or predecessor.get("joint_ac_solver_call_count") != 0
        or predecessor.get("predecessor_resume_allowed") is not False
        or predecessor.get("candidate_checkpoint_manifest_sha256s")
        != list(interruption.EXPECTED_CHECKPOINT_MANIFEST_SHA256S)
        or predecessor.get("candidate_json_sha256s")
        != list(interruption.EXPECTED_CANDIDATE_JSON_SHA256S)
        or successor.get("checkpoint_schema") != CHECKPOINT_SCHEMA
        or successor.get("prefix_evidence_schema") != PREFIX_EVIDENCE_SCHEMA
        or successor.get("hybrid_evidence_schema") != HYBRID_EVIDENCE_SCHEMA
        or successor.get("combined_cost_certificate_schema") != COMBINED_COST_SCHEMA
        or successor.get("float_serialization") != FLOAT_SERIALIZATION
        or successor.get("prefix_candidate_count") != 4
        or successor.get("proxy_algorithm_changed") is not False
        or successor.get("direct_cost_phase_first_for_new_candidates") is not True
        or successor.get("cost_fallback_trigger")
        != "exact_final_bound_certificate_exceeds_maximum_acceptance_only"
        or successor.get("cost_fallback_method")
        != "budget_capped_cost_decision_bisection"
        or successor.get("cost_decision_round_schema")
        != "rts_gmlc_cost_decision_round_v1"
        or successor.get("cost_decision_maximum_rounds") != 4
        or float(successor.get("cost_match_tolerance_usd")) != 1.0e-4
        or float(successor.get("target_relative_gap")) != 1.0e-4
        or float(successor.get("maximum_accepted_relative_gap_to_feasible_incumbent"))
        != 1.0e-3
        or successor.get("timeout_or_ambiguous_is_infeasibility_evidence") is not False
        or successor.get("decision_derived_bound_is_ordinary_dual_bound") is not False
        or successor.get("source_prefix_imported_as_recomputed") is not False
        or successor.get("cost_decision_cross_attempt_resume_allowed") is not False
        or successor.get("all_six_checkpoints_required_before_frontier") is not True
        or successor.get("frontier_required_before_joint_ac") is not True
        or not isinstance(controls, list)
        or len(controls) != 6
    ):
        raise ValueError("repair-006 frozen contract drifted")
    expected_deltas = (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05)
    for ordinal, (control, delta) in enumerate(zip(controls, expected_deltas), 1):
        mode = (
            "verified_repair_005_prefix"
            if ordinal <= 4
            else "direct_then_cost_decision_bisection"
        )
        if (
            control.get("ordinal") != ordinal
            or float(control.get("relative_cost_budget_delta")) != delta
            or control.get("mode") != mode
        ):
            raise ValueError("repair-005 candidate control order drifted")
    return config


def _verify_parent_interruption(
    config: Mapping[str, Any], interruption_root: Path | None
) -> None:
    predecessor = config["predecessor_repair_005"]
    root = interruption_root or (
        Path(predecessor["root"]) / str(predecessor["interruption_relative_path"])
    )
    _verify_manifest(root)
    if _sha256(root / "SHA256SUMS") != predecessor["interruption_manifest_sha256"]:
        raise RuntimeError("repair-006 parent interruption manifest drifted")
    payload = v4._load_json(root, "interruption.json")
    if (
        payload.get("status") != predecessor["required_interruption_status"]
        or payload.get("preregistration_manifest_sha256")
        != predecessor["preregistration_manifest_sha256"]
        or payload.get("input_contract_sha256") != predecessor["input_contract_sha256"]
        or payload.get("valid_candidate_checkpoint_count") != 4
        or payload.get("candidate_checkpoint_names")
        != list(predecessor["candidate_checkpoint_names"])
        or payload.get("mathematical_infeasibility_certified") is not False
        or payload.get("interruption_is_infeasibility_evidence") is not False
        or payload.get("interruption_is_formal_failure") is not False
        or payload.get("candidate_frontier_artifact_published") is not False
        or payload.get("joint_ac_solver_call_count") != 0
        or payload.get("repair_005_resume_allowed") is not False
        or payload.get("scientific_protocol_changed") is not False
    ):
        raise RuntimeError("repair-006 parent interruption content drifted")


def _source_context(config: Mapping[str, Any]) -> v4._FrontierContext:
    return repair005._build_context(
        Path(config["predecessor_repair_005"]["config_path"])
    )


def _verified_source_prefix(
    config: Mapping[str, Any],
) -> tuple[tuple[v4._Candidate, SharedSnapshot], ...]:
    predecessor = config["predecessor_repair_005"]
    root = Path(predecessor["root"])
    source_context = _source_context(config)
    loaded: list[tuple[v4._Candidate, SharedSnapshot]] = []
    for ordinal in range(1, 5):
        item = repair005._load_candidate_checkpoint(source_context, root, ordinal)
        if item is None:
            raise RuntimeError("repair-006 source prefix checkpoint is missing")
        candidate, snapshot = item
        path = v4._candidate_checkpoint_path(
            root, ordinal, candidate.requested_candidate_id
        )
        if (
            _sha256(path / "SHA256SUMS")
            != predecessor["candidate_checkpoint_manifest_sha256s"][ordinal - 1]
            or _sha256(path / "candidate.json")
            != predecessor["candidate_json_sha256s"][ordinal - 1]
        ):
            raise RuntimeError("repair-006 source prefix hash drifted")
        loaded.append((candidate, snapshot))
    return tuple(loaded)


def _verify_frozen_inputs(
    config: Mapping[str, Any], *, predecessor_interruption_root: Path | None = None
) -> None:
    base = config["base_v4"]
    _verify_file(Path(base["config_path"]), str(base["config_sha256"]), "base config")
    _verify_file(Path(base["runner_path"]), str(base["runner_sha256"]), "base runner")
    predecessor = config["predecessor_repair_005"]
    for key in ("config", "formal_runner", "monitor", "launcher"):
        _verify_file(
            Path(predecessor[f"{key}_path"]),
            str(predecessor[f"{key}_sha256"]),
            f"predecessor {key}",
        )
    for key, path_value in config["implementation"].items():
        if not key.endswith("_path"):
            continue
        expected = str(
            config["implementation"].get(key.removesuffix("_path") + "_sha256", "")
        )
        if re.fullmatch(r"[0-9a-f]{64}", expected) is None:
            raise RuntimeError(f"repair-006 implementation hash is not frozen: {key}")
        _verify_file(Path(path_value), expected, key)
    _verify_parent_interruption(config, predecessor_interruption_root)
    if len(_verified_source_prefix(config)) != 4:
        raise RuntimeError("repair-006 source prefix count drifted")


def _build_context(
    config_path: Path, *, predecessor_interruption_root: Path | None = None
) -> v4._FrontierContext:
    successor_config = _read_config(config_path)
    _verify_frozen_inputs(
        successor_config,
        predecessor_interruption_root=predecessor_interruption_root,
    )
    base = v4._build_context(Path(successor_config["base_v4"]["config_path"]))
    effective = copy.deepcopy(base.config)
    effective["preregistration"] = dict(successor_config["preregistration"])
    effective["output"] = dict(successor_config["output"])
    effective["formal_solver"]["algorithm"] = successor_config["formal_successor"][
        "algorithm_id"
    ]
    effective["formal_solver"]["progress_logging"]["log_directory"] = successor_config[
        "logging"
    ]["directory"]
    effective["joint_ac"]["runtime_control"]["log_directory"] = successor_config[
        "logging"
    ]["directory"]
    contract = {
        "schema": "rts_gmlc_v4_repair_006_formal_inputs_v1",
        "base_v4_input_contract": base.input_contract,
        "base_v4_input_contract_sha256": base.input_contract_sha256,
        "successor_config_sha256": _sha256(config_path),
        "predecessor_repair_005": successor_config["predecessor_repair_005"],
        "formal_successor": successor_config["formal_successor"],
        "implementation": successor_config["implementation"],
    }
    return replace(
        base,
        config_path=config_path,
        config=effective,
        output_root=Path(successor_config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


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
        "selected_candidate_method": context.config["formal_solver"]["algorithm"],
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    predecessor_interruption_root: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(
        config_path,
        predecessor_interruption_root=predecessor_interruption_root,
    )
    output_root = output_directory or context.output_root
    target = output_root / "preregistration"
    expected = _registration_payload(context)
    if target.exists():
        _verify_manifest(target)
        observed = v4._load_json(target, "registration.json")
        if (
            v4._exact_json_text(observed) != v4._exact_json_text(expected)
            or (target / "config.yaml").read_bytes() != config_path.read_bytes()
        ):
            raise RuntimeError("repair-006 published preregistration drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare repair-006 beside existing artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        v4._write_exact_json(staging / "registration.json", expected)

    v4._publish_immutable_payload(target, writer)
    return v4._load_json(target, "registration.json")


def _prefix_candidate(
    context: v4._FrontierContext,
    ordinal: int,
    source: tuple[v4._Candidate, SharedSnapshot],
) -> tuple[v4._Candidate, SharedSnapshot, dict[str, object]]:
    candidate, snapshot = source
    predecessor = context.input_contract["predecessor_repair_005"]
    evidence: dict[str, object] = {
        "schema": PREFIX_EVIDENCE_SCHEMA,
        "source_preregistration_manifest_sha256": predecessor[
            "preregistration_manifest_sha256"
        ],
        "source_input_contract_sha256": predecessor["input_contract_sha256"],
        "source_checkpoint_manifest_sha256": predecessor[
            "candidate_checkpoint_manifest_sha256s"
        ][ordinal - 1],
        "source_candidate_json_sha256": predecessor["candidate_json_sha256s"][
            ordinal - 1
        ],
        "source_stage_evidence_sha256": common_input_signature_sha256(
            candidate.stage_audits
        ),
        "source_checkpoint_validated_by_repair_005_runner": True,
        "source_imported_as_recomputed": False,
        "accepted_proxy_snapshot": _snapshot_payload(snapshot),
        "accepted_proxy_snapshot_sha256": snapshot.sha256,
    }
    imported = replace(
        candidate,
        source="repair_006_verified_repair_005_prefix",
        stage_audits={"repair_005_prefix": evidence},
    )
    return imported, snapshot, evidence


def _cost_fallback_trigger(stage_result: Any) -> bool:
    record = stage_result.stage_record
    certificate = record.get("certificate")
    audit = record.get("final_full_state_audit")
    callback = audit.get("callback_record") if isinstance(audit, Mapping) else None
    residual = callback.get("residual_audit") if isinstance(callback, Mapping) else None
    return bool(
        stage_result.snapshot is None
        and stage_result.audited_snapshot is not None
        and record.get("eligible") is False
        and record.get("failure_reason")
        == "final_bound_certificate_exceeds_maximum_acceptance"
        and isinstance(certificate, Mapping)
        and certificate.get("valid") is True
        and isinstance(audit, Mapping)
        and audit.get("passed") is True
        and audit.get("residual_audit_passed") is True
        and isinstance(callback, Mapping)
        and callback.get("passed") is True
        and isinstance(residual, Mapping)
        and residual.get("passed") is True
        and record.get("final_shared_snapshot_sha256")
        == stage_result.audited_snapshot.sha256
    )


@dataclass(frozen=True)
class HybridCostResult:
    snapshot: SharedSnapshot
    direct: ExactCgStageResult
    combined_certificate: dict[str, object]
    decision_bisection: CostBisectionResult | None
    final_audit_record: dict[str, object]
    final_handle: Any
    round_root: Path | None


def _all_states_screened(
    record: Mapping[str, object], all_state_ids: tuple[str, ...]
) -> bool:
    iterations = record.get("iteration_records")
    active = record.get("final_active_state_ids")
    if (
        not isinstance(iterations, list)
        or not iterations
        or not isinstance(active, list)
    ):
        return False
    final_iteration = iterations[-1]
    screens = (
        final_iteration.get("screen_records")
        if isinstance(final_iteration, Mapping)
        else None
    )
    if not isinstance(screens, list):
        return False
    screened: set[str] = set()
    for item in screens:
        if (
            not isinstance(item, Mapping)
            or item.get("status") != "feasible"
            or not isinstance(item.get("state_id"), str)
        ):
            return False
        screened.add(str(item["state_id"]))
    return set(active) | screened == set(all_state_ids)


def _validated_cost_fallback_bracket(
    stage_result: ExactCgStageResult,
    *,
    all_state_ids: tuple[str, ...],
    cost_tolerance_usd: float,
    proxy_tolerance: float,
) -> CostBracket | None:
    if not _cost_fallback_trigger(stage_result):
        return None
    record = stage_result.stage_record
    certificate = record["certificate"]
    audit = record["final_full_state_audit"]
    callback = audit["callback_record"]
    snapshot = stage_result.audited_snapshot
    assert snapshot is not None
    try:
        lower = float(certificate["lower_bound"])
        upper = float(certificate["upper_bound"])
        audited_cost = float(callback["actual_operating_cost_usd"])
        full_objective = float(audit["full_feasible_objective"])
        proxy_floor = float(record["proxy_floor"])
        actual_proxy = float(callback["actual_proxy_fraction"])
        commitment_proxy = float(callback["commitment_capability_proxy_fraction"])
    except (KeyError, TypeError, ValueError):
        return None
    maximum = record.get("maximum_acceptance")
    valid = bool(
        record.get("stage") == "cost_normalization"
        and record.get("sense") == "minimize"
        and math.isfinite(lower)
        and math.isfinite(upper)
        and lower <= upper
        and isinstance(maximum, Mapping)
        and maximum.get("absolute_acceptance_passed") is True
        and maximum.get("relative_acceptance_passed") is False
        and maximum.get("maximum_acceptance_passed") is False
        and audit.get("audited_state_ids") == list(all_state_ids)
        and audit.get("solution_usable") is True
        and audit.get("shared_snapshot_fixed") is True
        and audit.get("integer_variables_relaxed") is True
        and audit.get("additional_audits_passed") is True
        and audit.get("residual_audit_passed") is True
        and abs(upper - snapshot.operating_cost_usd) <= cost_tolerance_usd
        and abs(audited_cost - snapshot.operating_cost_usd) <= cost_tolerance_usd
        and abs(full_objective - snapshot.operating_cost_usd) <= cost_tolerance_usd
        and snapshot.reactive_proxy + proxy_tolerance >= proxy_floor
        and actual_proxy + proxy_tolerance >= proxy_floor
        and abs(commitment_proxy - snapshot.reactive_proxy) <= proxy_tolerance
        and _all_states_screened(record, all_state_ids)
    )
    return CostBracket(lower, upper, snapshot) if valid else None


def _strict_cost_fallback_trigger(
    stage_result: ExactCgStageResult,
    *,
    all_state_ids: tuple[str, ...],
    cost_tolerance_usd: float,
    proxy_tolerance: float,
) -> bool:
    return (
        _validated_cost_fallback_bracket(
            stage_result,
            all_state_ids=all_state_ids,
            cost_tolerance_usd=cost_tolerance_usd,
            proxy_tolerance=proxy_tolerance,
        )
        is not None
    )


def _budget_for_exact_effective_cap(cap: float, tolerance: float) -> float:
    candidate = float(cap) - float(tolerance)
    if candidate + tolerance == cap:
        return candidate
    lower = candidate
    upper = candidate
    for _ in range(8):
        lower = math.nextafter(lower, -math.inf)
        if lower + tolerance == cap:
            return lower
        upper = math.nextafter(upper, math.inf)
        if upper + tolerance == cap:
            return upper
    raise RuntimeError("repair-005 cannot represent the exact decision budget cap")


def _oracle_termination(record: Mapping[str, object]) -> str:
    masters = record.get("master_records")
    if not isinstance(masters, list) or not masters:
        return "missing"
    master = masters[-1]
    callback = master.get("callback_record") if isinstance(master, Mapping) else None
    decision = callback.get("decision_mip") if isinstance(callback, Mapping) else None
    if isinstance(decision, Mapping):
        return str(decision.get("solver_api_termination_condition"))
    solve = callback.get("solve") if isinstance(callback, Mapping) else None
    return (
        str(solve.get("termination_condition"))
        if isinstance(solve, Mapping)
        else "missing"
    )


def level_evidence_from_stage_result(
    stage_result: ExactCgStageResult,
    *,
    expected_cap_usd: float,
    all_state_ids: tuple[str, ...],
    cost_tolerance_usd: float,
) -> CostOracleEvidence:
    record = stage_result.stage_record
    separation = record.get("bound_only_early_separation")
    if isinstance(separation, Mapping):
        return CostOracleEvidence(
            cost_cap_usd=expected_cap_usd,
            active_master_globally_infeasible=True,
            incumbent_snapshot=None,
            all_inactive_states_screened=False,
            final_full_state_audit_passed=False,
            residual_audit_passed=False,
            audited_operating_cost_usd=None,
            termination=_oracle_termination(record),
            infeasibility_certificate_schema=str(separation.get("schema")),
            infeasibility_certificate_source=str(separation.get("source")),
            infeasibility_claim_scope=str(separation.get("claim_scope")),
            decision_budget_cap_usd=float(separation.get("decision_budget_cap_usd")),
            cost_match_tolerance_usd=cost_tolerance_usd,
        )
    snapshot = stage_result.snapshot
    audit = record.get("final_full_state_audit")
    callback = audit.get("callback_record") if isinstance(audit, Mapping) else None
    residual = callback.get("residual_audit") if isinstance(callback, Mapping) else None
    audited_cost = (
        callback.get("actual_operating_cost_usd")
        if isinstance(callback, Mapping)
        else None
    )
    return CostOracleEvidence(
        cost_cap_usd=expected_cap_usd,
        active_master_globally_infeasible=False,
        incumbent_snapshot=snapshot,
        all_inactive_states_screened=(
            snapshot is not None and _all_states_screened(record, all_state_ids)
        ),
        final_full_state_audit_passed=bool(
            isinstance(audit, Mapping) and audit.get("passed") is True
        ),
        residual_audit_passed=bool(
            isinstance(residual, Mapping) and residual.get("passed") is True
        ),
        audited_operating_cost_usd=(
            float(audited_cost) if audited_cost is not None else None
        ),
        termination=_oracle_termination(record),
        cost_match_tolerance_usd=cost_tolerance_usd,
    )


def _combined_cost_certificate(
    certificate: Mapping[str, object],
    *,
    method: str,
    direct_lower_bound_usd: float,
    decision_round_count: int,
) -> dict[str, object]:
    combined = dict(certificate)
    combined.update(
        {
            "schema": COMBINED_COST_SCHEMA,
            "valid": certificate.get("valid") is True,
            "method": method,
            "decision_derived_cost_lower_bound": (
                float(certificate["lower_bound"]) if decision_round_count > 0 else None
            ),
            "ordinary_dual_bound_usd": None,
            "direct_stage_ordinary_dual_bound_usd": direct_lower_bound_usd,
            "decision_round_count": decision_round_count,
            "decision_cap_is_ordinary_dual_bound": False,
        }
    )
    return combined


def _repeat_cost_audit(
    *,
    context: v4._FrontierContext,
    problem: Any,
    snapshot: SharedSnapshot,
    proxy_floor: float,
    progress: Any,
    log_root: Path,
    event_context: Mapping[str, object],
    deadline_monotonic: float,
) -> tuple[dict[str, object], Any]:
    remaining = float(deadline_monotonic) - float(monotonic())
    if remaining <= 0.0:
        raise RuntimeError(
            "repair-005 candidate deadline exhausted before repeated cost audit"
        )
    frozen_limit = repair004._stage_limits(
        context, "cost_normalization"
    ).final_audit_seconds
    limit = min(float(frozen_limit), remaining)
    adapter = FormalCgModelAdapter(
        problem=problem,
        formal_solver=context.config["formal_solver"],
        candidate_frontier=context.config["candidate_frontier"],
        snapshot_contract=context.config["candidate_snapshot"],
        progress=progress,
        log_root=log_root,
        event_context=dict(event_context),
    )
    call = ExactCgCall(
        call_id="cost_decision_bisection.final_repeated_full_state_audit",
        kind="final_audit",
        stage="level_set_budget_feasibility",
        iteration=1,
        active_state_ids=problem.all_state_ids,
        all_state_ids=problem.all_state_ids,
        time_limit_seconds=limit,
        target_relative_gap=float(
            context.input_contract["formal_successor"]["target_relative_gap"]
        ),
        proxy_floor=proxy_floor,
        shared_snapshot=snapshot,
    )
    audit = adapter.audit_full_state(call)
    if not (
        audit.solution_usable
        and audit.shared_snapshot_fixed
        and audit.integer_variables_relaxed
        and audit.residual_audit_passed
        and audit.additional_audits_passed
        and audit.shared_snapshot_sha256 == snapshot.sha256
    ):
        raise RuntimeError("repair-005 repeated cost full-state audit failed")
    handle = adapter.final_handles.get("level_set_budget_feasibility")
    if handle is None:
        raise RuntimeError("repair-005 repeated cost audit model was not retained")
    return {
        "schema": "rts_gmlc_v4_repair_005_repeated_cost_audit_v1",
        "passed": True,
        "audited_state_ids": list(audit.audited_state_ids),
        "shared_snapshot_sha256": audit.shared_snapshot_sha256,
        "solution_usable": bool(audit.solution_usable),
        "shared_snapshot_fixed": bool(audit.shared_snapshot_fixed),
        "integer_variables_relaxed": bool(audit.integer_variables_relaxed),
        "residual_audit_passed": bool(audit.residual_audit_passed),
        "additional_audits_passed": bool(audit.additional_audits_passed),
        "full_feasible_objective": audit.full_feasible_objective,
        "callback_record": dict(audit.record),
    }, handle


def _run_hybrid_cost_normalization(
    *,
    context: v4._FrontierContext,
    problem: Any,
    proxy_floor: float,
    progress: Any,
    candidate_log_root: Path,
    event_context: Mapping[str, object],
    deadline_monotonic: float,
    candidate_id: str,
    candidate_ordinal: int,
) -> HybridCostResult:
    successor = context.input_contract["formal_successor"]
    tolerance = float(successor["cost_match_tolerance_usd"])
    cost_spec = context.config["formal_solver"]["stages"]["cost_normalization"]
    direct_adapter = FormalCgModelAdapter(
        problem=problem,
        formal_solver=context.config["formal_solver"],
        candidate_frontier=context.config["candidate_frontier"],
        snapshot_contract=context.config["candidate_snapshot"],
        progress=progress,
        log_root=candidate_log_root / "cost_normalization_direct",
        event_context=dict(event_context),
    )
    direct = run_exact_cg_stage(
        stage="cost_normalization",
        all_state_ids=problem.all_state_ids,
        seed_state_ids=problem.initial_active_state_ids,
        target_relative_gap=float(cost_spec["target_relative_gap"]),
        maximum_accepted_relative_gap_to_feasible_incumbent=float(
            cost_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_accepted_absolute_gap=cost_spec["maximum_accepted_absolute_gap"],
        time_limits=repair004._stage_limits(context, "cost_normalization"),
        callbacks=direct_adapter.callbacks(),
        proxy_floor=proxy_floor,
        candidate_deadline_monotonic=deadline_monotonic,
    )
    direct_certificate = direct.stage_record.get("certificate")
    if direct.snapshot is not None and direct.stage_record.get("eligible") is True:
        if not isinstance(direct_certificate, Mapping):
            raise RuntimeError("repair-005 direct cost certificate is missing")
        maximum = direct.stage_record["maximum_acceptance"]
        certificate = {
            "schema": "rts_gmlc_cost_decision_bisection_certificate_v1",
            "valid": True,
            "lower_bound": float(direct_certificate["lower_bound"]),
            "upper_bound": float(direct_certificate["upper_bound"]),
            "absolute_gap": float(direct_certificate["absolute_gap"]),
            "relative_gap_to_feasible_incumbent": float(
                direct_certificate["relative_gap_to_feasible_incumbent"]
            ),
            "target_attained": bool(maximum["target_attained"]),
            "maximum_acceptance_passed": bool(maximum["maximum_acceptance_passed"]),
        }
        handle = direct_adapter.final_handles.get("cost_normalization")
        if handle is None:
            raise RuntimeError("repair-005 direct cost audit model was not retained")
        return HybridCostResult(
            direct.snapshot,
            direct,
            _combined_cost_certificate(
                certificate,
                method="direct_exact_cg",
                direct_lower_bound_usd=float(direct_certificate["lower_bound"]),
                decision_round_count=0,
            ),
            None,
            dict(direct.stage_record["final_full_state_audit"]),
            handle,
            None,
        )
    initial = _validated_cost_fallback_bracket(
        direct,
        all_state_ids=problem.all_state_ids,
        cost_tolerance_usd=tolerance,
        proxy_tolerance=float(cost_spec["proxy_floor_absolute_tolerance"]),
    )
    if initial is None:
        raise RuntimeError(
            "repair-005 cost normalization failed outside the permitted fallback: "
            + str(direct.stage_record.get("failure_reason"))
        )
    assert isinstance(direct_certificate, Mapping)
    assert direct.audited_snapshot is not None
    checkpoint_root = candidate_log_root / "cost_decision_checkpoints"
    predecessor_sha = common_input_signature_sha256(
        {
            "input_contract_sha256": context.input_contract_sha256,
            "candidate_ordinal": candidate_ordinal,
            "candidate_id": candidate_id,
            "proxy_floor": proxy_floor,
            "initial_lower_bound_usd": initial.lower_bound_usd,
            "initial_upper_bound_usd": initial.upper_bound_usd,
            "initial_upper_snapshot_sha256": initial.upper_snapshot.sha256,
            "cost_match_tolerance_usd": tolerance,
        }
    )

    def oracle(cap: float, round_ordinal: int) -> CostOracleEvidence:
        trial_budget = _budget_for_exact_effective_cap(cap, tolerance)
        trial_problem = v4._formal_problem(context, cost_budget_usd=trial_budget)
        adapter = FormalCgModelAdapter(
            problem=trial_problem,
            formal_solver=context.config["formal_solver"],
            candidate_frontier=context.config["candidate_frontier"],
            snapshot_contract=context.config["candidate_snapshot"],
            progress=progress,
            log_root=candidate_log_root / f"cost_decision_round_{round_ordinal:02d}",
            event_context={
                **event_context,
                "cost_decision_round_ordinal": round_ordinal,
            },
        )
        result = run_exact_cg_stage(
            stage="level_set_budget_feasibility",
            all_state_ids=trial_problem.all_state_ids,
            seed_state_ids=trial_problem.initial_active_state_ids,
            target_relative_gap=float(cost_spec["target_relative_gap"]),
            maximum_accepted_relative_gap_to_feasible_incumbent=float(
                cost_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
            ),
            maximum_accepted_absolute_gap=None,
            time_limits=repair004._stage_limits(context, "cost_normalization"),
            callbacks=adapter.callbacks(),
            proxy_floor=proxy_floor,
            candidate_deadline_monotonic=deadline_monotonic,
        )
        return level_evidence_from_stage_result(
            result,
            expected_cap_usd=cap,
            all_state_ids=trial_problem.all_state_ids,
            cost_tolerance_usd=tolerance,
        )

    bisection = run_bracketed_cost_bisection(
        initial,
        oracle=oracle,
        target_relative_gap=float(successor["target_relative_gap"]),
        maximum_relative_gap=float(
            successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_rounds=int(successor["cost_decision_maximum_rounds"]),
        candidate_id=candidate_id,
        candidate_ordinal=candidate_ordinal,
        input_contract_sha256=context.input_contract_sha256,
        predecessor_manifest_sha256=predecessor_sha,
        checkpoint_root=checkpoint_root,
    )
    if bisection.status != "accepted":
        raise RuntimeError(
            "repair-005 cost decision bisection unresolved: "
            + str(bisection.failure_reason)
        )
    repeated_audit, handle = _repeat_cost_audit(
        context=context,
        problem=problem,
        snapshot=bisection.bracket.upper_snapshot,
        proxy_floor=proxy_floor,
        progress=progress,
        log_root=candidate_log_root / "cost_decision_final_reaudit",
        event_context=event_context,
        deadline_monotonic=deadline_monotonic,
    )
    round_root = (
        checkpoint_root
        / f"{candidate_ordinal:02d}_{candidate_id}"
        / "cost_decision_rounds"
    )
    return HybridCostResult(
        bisection.bracket.upper_snapshot,
        direct,
        _combined_cost_certificate(
            bisection.certificate,
            method="direct_exact_cg_plus_cost_decision_bisection",
            direct_lower_bound_usd=float(direct_certificate["lower_bound"]),
            decision_round_count=len(bisection.round_checkpoints),
        ),
        bisection,
        repeated_audit,
        handle,
        round_root,
    )


def _round_references(root: Path | None) -> list[dict[str, object]]:
    if root is None:
        return []
    return [
        {
            "round_ordinal": int(path.name),
            "round_sha256": _sha256(path / "round.json"),
            "manifest_sha256": _sha256(path / "SHA256SUMS"),
        }
        for path in sorted(root.iterdir())
    ]


def _hybrid_candidate(
    context: v4._FrontierContext,
    *,
    ordinal: int,
    fallback_lower_snapshot: SharedSnapshot,
    progress: Any,
    candidate_log_root: Path,
    deadline_monotonic: float,
) -> tuple[
    v4._Candidate,
    SharedSnapshot,
    dict[str, object],
    dict[str, Path | None],
]:
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
        "repair_005_cost_bisection": True,
    }
    direct_adapter = repair004.V4InitialProxyWarmStartAdapter(
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
    direct_proxy = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=problem.all_state_ids,
        seed_state_ids=problem.initial_active_state_ids,
        target_relative_gap=float(successor["target_relative_gap"]),
        maximum_accepted_relative_gap_to_feasible_incumbent=float(
            successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_accepted_absolute_gap=float(
            context.config["formal_solver"]["stages"]["proxy_maximization"][
                "maximum_accepted_absolute_gap"
            ]
        ),
        time_limits=repair004._stage_limits(context, "proxy_maximization"),
        callbacks=direct_adapter.callbacks(),
        candidate_deadline_monotonic=deadline_monotonic,
    )
    proxy_round_checkpoint_root = candidate_log_root / "level_set_checkpoints"
    predecessor_evidence_sha = common_input_signature_sha256(
        {
            "input_contract_sha256": context.input_contract_sha256,
            "candidate_ordinal": ordinal,
            "fallback_lower_snapshot_sha256": fallback_lower_snapshot.sha256,
            "repair_005_proxy_successor_contract_sha256": (
                context.input_contract["predecessor_repair_005"][
                    "input_contract_sha256"
                ]
            ),
        }
    )

    def level_oracle(floor: float, round_ordinal: int) -> ExactCgStageResult:
        adapter = FormalCgModelAdapter(
            problem=problem,
            formal_solver=context.config["formal_solver"],
            candidate_frontier=context.config["candidate_frontier"],
            snapshot_contract=context.config["candidate_snapshot"],
            progress=progress,
            log_root=candidate_log_root / f"level_set_round_{round_ordinal:02d}",
            event_context={**event_context, "level_set_round_ordinal": round_ordinal},
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
            time_limits=repair004.ExactCgTimeLimits(
                master_seconds=float(
                    context.input_contract["predecessor_repair_005"].get(
                        "level_set_master_seconds_per_call", 3600.0
                    )
                ),
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
            ),
            callbacks=adapter.callbacks(),
            proxy_floor=floor,
            candidate_deadline_monotonic=deadline_monotonic,
        )

    parent_successor = repair005._read_config(
        Path(context.input_contract["predecessor_repair_005"]["config_path"])
    )["formal_successor"]
    # repair-004 functions read these keys directly; augment with fallbacks
    # so they work when successor is repair-005 formal_successor (which renamed/removed them)
    parent_successor = {
        **parent_successor,
        "maximum_accepted_absolute_gap": parent_successor.get(
            "maximum_accepted_absolute_gap", 1.0e-3
        ),
        "strict_cost_separation_margin_usd": parent_successor.get(
            "strict_cost_separation_margin_usd",
            parent_successor.get("cost_match_tolerance_usd", 1.0e-4),
        ),
        "level_set_maximum_rounds": parent_successor.get(
            "level_set_maximum_rounds",
            parent_successor.get("cost_decision_maximum_rounds", 12),
        ),
        "level_set_master_seconds_per_call": parent_successor.get(
            "level_set_master_seconds_per_call", 3600.0
        ),
    }
    proxy_hybrid = repair004.repair.run_hybrid_proxy_certificate(
        repair004._stable_fallback_input(direct_proxy),
        fallback_lower_snapshot=fallback_lower_snapshot,
        imported_upper_bound=1.0,
        level_oracle=level_oracle,
        effective_budget_usd=effective_budget,
        strict_separation_margin_usd=float(
            parent_successor.get("strict_cost_separation_margin_usd", parent_successor["cost_match_tolerance_usd"])
        ),
        target_relative_gap=float(parent_successor["target_relative_gap"]),
        maximum_absolute_gap=float(parent_successor.get("maximum_accepted_absolute_gap", 1.0e-3)),
        maximum_relative_gap=float(
            parent_successor["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_rounds=int(parent_successor.get("level_set_maximum_rounds", parent_successor["cost_decision_maximum_rounds"])),
        candidate_id=requested_id,
        candidate_ordinal=ordinal,
        input_contract_sha256=context.input_contract_sha256,
        predecessor_manifest_sha256=predecessor_evidence_sha,
        checkpoint_root=proxy_round_checkpoint_root,
    )
    proxy_hybrid = replace(proxy_hybrid, direct_stage_record=direct_proxy.stage_record)
    if proxy_hybrid.snapshot is not None:
        proxy_hybrid = replace(
            proxy_hybrid,
            certificate=repair004._normalized_hybrid_certificate(
                proxy_hybrid.certificate,
                proxy_hybrid.snapshot,
                parent_successor,
            ),
        )
    if (
        proxy_hybrid.snapshot is None
        or proxy_hybrid.certificate.get("valid") is not True
        or proxy_hybrid.certificate.get("maximum_acceptance_passed") is not True
    ):
        raise RuntimeError(
            "repair-005 proxy stage unresolved: " + str(proxy_hybrid.failure_reason)
        )
    accepted_proxy_snapshot = proxy_hybrid.snapshot
    floor_tolerance = float(
        context.config["formal_solver"]["stages"]["cost_normalization"][
            "proxy_floor_absolute_tolerance"
        ]
    )
    proxy_floor = float(proxy_hybrid.certificate["lower_bound"]) - floor_tolerance
    cost = _run_hybrid_cost_normalization(
        context=context,
        problem=problem,
        proxy_floor=proxy_floor,
        progress=progress,
        candidate_log_root=candidate_log_root,
        event_context=event_context,
        deadline_monotonic=deadline_monotonic,
        candidate_id=requested_id,
        candidate_ordinal=ordinal,
    )
    handle = cost.final_handle
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
        raise RuntimeError("repair-005 normalized candidate violated proxy or budget")
    regret_config = context.config["formal_solver"]["primary_regret"]
    proxy_gap = float(proxy_hybrid.certificate["absolute_gap"])
    observed_regret = max(
        float(proxy_hybrid.certificate["upper_bound"]) - proxy_value, 0.0
    )
    allowed_regret = (
        proxy_gap
        + float(regret_config["proxy_floor_tolerance"])
        + float(regret_config["numerical_audit_allowance"])
    )
    primary_regret = {
        "schema": "rts_gmlc_primary_proxy_regret_certificate_v1",
        "stage_one_certified_upper_bound": float(
            proxy_hybrid.certificate["upper_bound"]
        ),
        "final_commitment_capability_proxy_fraction": proxy_value,
        "observed_regret_upper_bound": observed_regret,
        "stage_one_actual_absolute_gap": proxy_gap,
        "proxy_floor_tolerance": float(regret_config["proxy_floor_tolerance"]),
        "numerical_audit_allowance": float(regret_config["numerical_audit_allowance"]),
        "derived_allowed_regret": allowed_regret,
        "hard_maximum": float(regret_config["hard_maximum"]),
        "passed": bool(
            observed_regret <= allowed_regret + 1.0e-12
            and observed_regret <= float(regret_config["hard_maximum"]) + 1.0e-12
        ),
    }
    if primary_regret["passed"] is not True:
        raise RuntimeError("repair-005 primary proxy regret audit failed")
    final_callback = cost.final_audit_record.get("callback_record")
    residual = (
        final_callback.get("residual_audit")
        if isinstance(final_callback, Mapping)
        else None
    )
    if not isinstance(residual, Mapping) or residual.get("passed") is not True:
        raise RuntimeError("repair-005 final candidate residual audit is missing")
    proxy_round_root = (
        proxy_round_checkpoint_root
        / f"{ordinal:02d}_{requested_id}"
        / "level_set_rounds"
        if proxy_hybrid.level_set is not None
        else None
    )
    proxy_evidence: dict[str, object] = {
        "schema": repair005.HYBRID_EVIDENCE_SCHEMA,
        "method": proxy_hybrid.method,
        "direct_stage_record": proxy_hybrid.direct_stage_record,
        "level_set_status": (
            proxy_hybrid.level_set.status
            if proxy_hybrid.level_set is not None
            else "not_required"
        ),
        "level_set_rounds": _round_references(proxy_round_root),
        "fallback_lower_snapshot_sha256": fallback_lower_snapshot.sha256,
        "predecessor_evidence_sha256": predecessor_evidence_sha,
        "certificate": proxy_hybrid.certificate,
        "accepted_proxy_snapshot": _snapshot_payload(accepted_proxy_snapshot),
        "accepted_proxy_snapshot_sha256": accepted_proxy_snapshot.sha256,
    }
    cost_evidence: dict[str, object] = {
        "schema": "rts_gmlc_v4_repair_005_cost_normalization_evidence_v1",
        "method": cost.combined_certificate["method"],
        "direct_stage_record": cost.direct.stage_record,
        "initial_direct_upper_snapshot": (
            _snapshot_payload(cost.direct.audited_snapshot)
            if cost.direct.audited_snapshot is not None
            else None
        ),
        "initial_direct_upper_snapshot_sha256": (
            cost.direct.audited_snapshot.sha256
            if cost.direct.audited_snapshot is not None
            else None
        ),
        "combined_certificate": cost.combined_certificate,
        "cost_decision_status": (
            cost.decision_bisection.status
            if cost.decision_bisection is not None
            else "not_required"
        ),
        "cost_decision_rounds": _round_references(cost.round_root),
        "cost_decision_predecessor_sha256": (
            cost.decision_bisection.round_checkpoints[0]["predecessor_manifest_sha256"]
            if cost.decision_bisection is not None
            else None
        ),
        "cost_decision_cross_attempt_resume_allowed": False,
        "final_repeated_full_state_audit": cost.final_audit_record,
        "accepted_cost_snapshot": _snapshot_payload(cost.snapshot),
        "accepted_cost_snapshot_sha256": cost.snapshot.sha256,
        "proxy_floor": proxy_floor,
    }
    evidence: dict[str, object] = {
        "schema": HYBRID_EVIDENCE_SCHEMA,
        "proxy_evidence": proxy_evidence,
        "cost_evidence": cost_evidence,
        "accepted_proxy_snapshot": _snapshot_payload(accepted_proxy_snapshot),
        "accepted_proxy_snapshot_sha256": accepted_proxy_snapshot.sha256,
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
            "proxy_maximization_hybrid": proxy_evidence,
            "cost_normalization_hybrid": cost_evidence,
            "primary_proxy_regret": primary_regret,
        },
        residual_audit=dict(residual),
    )
    return (
        candidate,
        accepted_proxy_snapshot,
        evidence,
        {
            "level_set_rounds": proxy_round_root,
            "cost_decision_rounds": cost.round_root,
        },
    )


def _require_preregistration(
    context: v4._FrontierContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    _verify_manifest(target)
    observed = v4._load_json(target, "registration.json")
    if (
        v4._exact_json_text(observed)
        != v4._exact_json_text(_registration_payload(context))
        or (target / "config.yaml").read_bytes() != context.config_path.read_bytes()
        or common_input_signature_sha256(observed["input_contract"])
        != context.input_contract_sha256
    ):
        raise RuntimeError("repair-005 preregistration contract drifted")
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
        raise RuntimeError("repair-005 checkpoint canonicalization drifted")
    return canonical


def _candidate_core(candidate: v4._Candidate) -> dict[str, object]:
    payload = asdict(candidate)
    payload.pop("source")
    payload.pop("stage_audits")
    return payload


def _validate_candidate_physics(
    candidate: v4._Candidate, context: v4._FrontierContext, ordinal: int
) -> None:
    controls = context.input_contract["formal_successor"]["candidate_controls"]
    control = controls[ordinal - 1]
    delta = float(control["relative_cost_budget_delta"])
    if (
        candidate.requested_candidate_id != v4._requested_candidate_id(delta)
        or candidate.relative_cost_budget_delta != delta
    ):
        raise RuntimeError("repair-005 candidate identity drifted")
    if ordinal <= 4:
        source_candidate = _verified_source_prefix(context.input_contract)[ordinal - 1][
            0
        ]
        if (
            candidate.source != "repair_006_verified_repair_005_prefix"
            or v4._exact_json_text(_candidate_core(candidate))
            != v4._exact_json_text(_candidate_core(source_candidate))
        ):
            raise RuntimeError("repair-005 imported prefix physics drifted")
        return
    source_context = _source_context(context.input_contract)
    repair005._validate_candidate_physics(candidate, source_context, ordinal)


def _context_state_ids(context: v4._FrontierContext) -> tuple[str, ...]:
    state_ids = tuple(str(state.state_id) for state in context.selection.states)
    if (
        not state_ids
        or state_ids[0] != "normal"
        or len(state_ids) != len(set(state_ids))
    ):
        raise RuntimeError("repair-005 formal state inventory drifted")
    return state_ids


def _validate_persisted_cost_audit(
    audit: Mapping[str, object],
    *,
    snapshot: SharedSnapshot,
    candidate: v4._Candidate,
    state_ids: tuple[str, ...],
    cost_tolerance_usd: float,
    proxy_tolerance: float,
    snapshot_sha_field: str,
    expected_schema: str | None = None,
) -> None:
    callback = audit.get("callback_record")
    residual = callback.get("residual_audit") if isinstance(callback, Mapping) else None
    try:
        full_objective = float(audit["full_feasible_objective"])
        actual_cost = float(callback["actual_operating_cost_usd"])
        actual_proxy = float(callback["actual_proxy_fraction"])
        commitment_proxy = float(callback["commitment_capability_proxy_fraction"])
    except (KeyError, TypeError, ValueError) as error:
        raise RuntimeError("repair-005 persisted cost audit drifted") from error
    if (
        (expected_schema is not None and audit.get("schema") != expected_schema)
        or audit.get("passed") is not True
        or audit.get("audited_state_ids") != list(state_ids)
        or audit.get(snapshot_sha_field) != snapshot.sha256
        or audit.get("solution_usable") is not True
        or audit.get("shared_snapshot_fixed") is not True
        or audit.get("integer_variables_relaxed") is not True
        or audit.get("residual_audit_passed") is not True
        or audit.get("additional_audits_passed") is not True
        or not isinstance(callback, Mapping)
        or callback.get("passed") is not True
        or not isinstance(residual, Mapping)
        or residual.get("passed") is not True
        or residual != candidate.residual_audit
        or not math.isfinite(full_objective)
        or abs(full_objective - candidate.operating_cost_usd) > cost_tolerance_usd
        or abs(actual_cost - candidate.operating_cost_usd) > cost_tolerance_usd
        or abs(snapshot.operating_cost_usd - candidate.operating_cost_usd)
        > cost_tolerance_usd
        or abs(actual_proxy - candidate.reactive_proxy_fraction) > proxy_tolerance
        or abs(commitment_proxy - candidate.reactive_proxy_fraction) > proxy_tolerance
        or abs(snapshot.reactive_proxy - candidate.reactive_proxy_fraction)
        > proxy_tolerance
    ):
        raise RuntimeError("repair-005 persisted cost audit drifted")


def _validate_proxy_checkpoint_evidence(
    proxy: Mapping[str, object],
    *,
    candidate: v4._Candidate,
    accepted_snapshot: SharedSnapshot,
    context: v4._FrontierContext,
) -> None:
    certificate = proxy.get("certificate")
    direct_record = proxy.get("direct_stage_record")
    proxy_snapshot_payload = proxy.get("accepted_proxy_snapshot")
    parent_successor = repair005._read_config(
        Path(context.input_contract["predecessor_repair_005"]["config_path"])
    )["formal_successor"]
    # repair-004 functions read these keys directly; augment with fallbacks
    # so they work when successor is repair-005 formal_successor (which renamed/removed them)
    parent_successor = {
        **parent_successor,
        "maximum_accepted_absolute_gap": parent_successor.get(
            "maximum_accepted_absolute_gap", 1.0e-3
        ),
        "strict_cost_separation_margin_usd": parent_successor.get(
            "strict_cost_separation_margin_usd",
            parent_successor.get("cost_match_tolerance_usd", 1.0e-4),
        ),
        "level_set_maximum_rounds": parent_successor.get(
            "level_set_maximum_rounds",
            parent_successor.get("cost_decision_maximum_rounds", 12),
        ),
        "level_set_master_seconds_per_call": parent_successor.get(
            "level_set_master_seconds_per_call", 3600.0
        ),
    }
    expected_certificate = (
        repair004._normalized_hybrid_certificate(
            certificate, accepted_snapshot, parent_successor
        )
        if isinstance(certificate, Mapping)
        else None
    )
    if (
        proxy.get("schema") != repair005.HYBRID_EVIDENCE_SCHEMA
        or not isinstance(direct_record, Mapping)
        or direct_record.get("schema") != "rts_gmlc_exact_cg_stage_record_v1"
        or direct_record.get("stage") != "proxy_maximization"
        or not isinstance(certificate, Mapping)
        or not isinstance(expected_certificate, Mapping)
        or v4._exact_json_text(certificate) != v4._exact_json_text(expected_certificate)
        or expected_certificate.get("maximum_acceptance_passed") is not True
        or not isinstance(proxy_snapshot_payload, Mapping)
        or _snapshot_from_payload(proxy_snapshot_payload) != accepted_snapshot
        or proxy.get("accepted_proxy_snapshot_sha256") != accepted_snapshot.sha256
    ):
        raise RuntimeError("repair-005 proxy evidence drifted")
    method = proxy.get("method")
    references = proxy.get("level_set_rounds")
    if method == "direct_exact_cg":
        raw_certificate = direct_record.get("certificate")
        if (
            direct_record.get("eligible") is not True
            or proxy.get("level_set_status") != "not_required"
            or references != []
            or not isinstance(raw_certificate, Mapping)
            or v4._exact_json_text(
                repair004._normalized_hybrid_certificate(
                    raw_certificate, accepted_snapshot, parent_successor
                )
            )
            != v4._exact_json_text(certificate)
        ):
            raise RuntimeError("repair-005 direct proxy evidence drifted")
    elif method == "direct_max_or_level_set_bisection":
        if (
            direct_record.get("eligible") is True
            or proxy.get("level_set_status") != "accepted"
            or not isinstance(references, list)
            or not 1
            <= len(references)
            <= int(parent_successor.get("level_set_maximum_rounds", parent_successor["cost_decision_maximum_rounds"]))
        ):
            raise RuntimeError("repair-005 fallback proxy evidence drifted")
    else:
        raise RuntimeError("repair-005 proxy method drifted")


def _validate_primary_proxy_regret(
    candidate: v4._Candidate,
    proxy_certificate: Mapping[str, object],
    context: v4._FrontierContext,
) -> None:
    regret = candidate.stage_audits.get("primary_proxy_regret")
    regret_config = context.config["formal_solver"]["primary_regret"]
    observed = max(
        float(proxy_certificate["upper_bound"]) - candidate.reactive_proxy_fraction,
        0.0,
    )
    proxy_gap = float(proxy_certificate["absolute_gap"])
    floor_tolerance = float(regret_config["proxy_floor_tolerance"])
    numerical_allowance = float(regret_config["numerical_audit_allowance"])
    allowed = proxy_gap + floor_tolerance + numerical_allowance
    hard_maximum = float(regret_config["hard_maximum"])
    passed = bool(observed <= allowed + 1.0e-12 and observed <= hard_maximum + 1.0e-12)
    if (
        not isinstance(regret, Mapping)
        or regret.get("schema") != "rts_gmlc_primary_proxy_regret_certificate_v1"
        or regret.get("passed") is not passed
        or not passed
        or not v4._checkpoint_close(
            regret.get("stage_one_certified_upper_bound"),
            proxy_certificate["upper_bound"],
        )
        or not v4._checkpoint_close(
            regret.get("final_commitment_capability_proxy_fraction"),
            candidate.reactive_proxy_fraction,
        )
        or not v4._checkpoint_close(regret.get("observed_regret_upper_bound"), observed)
        or not v4._checkpoint_close(
            regret.get("stage_one_actual_absolute_gap"), proxy_gap
        )
        or not v4._checkpoint_close(
            regret.get("proxy_floor_tolerance"), floor_tolerance
        )
        or not v4._checkpoint_close(
            regret.get("numerical_audit_allowance"), numerical_allowance
        )
        or not v4._checkpoint_close(regret.get("derived_allowed_regret"), allowed)
        or not v4._checkpoint_close(regret.get("hard_maximum"), hard_maximum)
    ):
        raise RuntimeError("repair-005 primary regret evidence drifted")


def _validate_checkpoint_document(
    observed: Mapping[str, Any],
    context: v4._FrontierContext,
    ordinal: int,
) -> tuple[v4._Candidate, SharedSnapshot]:
    if set(observed) != {
        "schema",
        "float_serialization",
        "preregistration_id",
        "input_contract_sha256",
        "ordinal",
        "mode",
        "candidate",
        "evidence",
    }:
        raise RuntimeError("repair-005 checkpoint fields drifted")
    control = context.input_contract["formal_successor"]["candidate_controls"][
        ordinal - 1
    ]
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
        raise RuntimeError("repair-005 checkpoint contract drifted")
    candidate = v4._candidate_from_checkpoint_payload(observed["candidate"])
    _validate_candidate_physics(candidate, context, ordinal)
    evidence = observed["evidence"]
    snapshot_payload = evidence.get("accepted_proxy_snapshot")
    if not isinstance(snapshot_payload, Mapping):
        raise RuntimeError("repair-005 accepted proxy snapshot is missing")
    snapshot = _snapshot_from_payload(snapshot_payload)
    if snapshot.sha256 != evidence.get("accepted_proxy_snapshot_sha256"):
        raise RuntimeError("repair-005 accepted proxy snapshot drifted")
    if ordinal <= 4:
        predecessor = context.input_contract["predecessor_repair_005"]
        if (
            evidence.get("schema") != PREFIX_EVIDENCE_SCHEMA
            or evidence.get("source_checkpoint_manifest_sha256")
            != predecessor["candidate_checkpoint_manifest_sha256s"][ordinal - 1]
            or evidence.get("source_candidate_json_sha256")
            != predecessor["candidate_json_sha256s"][ordinal - 1]
            or evidence.get("source_checkpoint_validated_by_repair_005_runner")
            is not True
            or evidence.get("source_imported_as_recomputed") is not False
            or candidate.stage_audits.get("repair_005_prefix") != evidence
        ):
            raise RuntimeError("repair-005 prefix evidence drifted")
        source_snapshot = _verified_source_prefix(context.input_contract)[ordinal - 1][
            1
        ]
        if snapshot != source_snapshot:
            raise RuntimeError("repair-005 prefix snapshot identity drifted")
        return candidate, snapshot
    proxy = evidence.get("proxy_evidence")
    cost = evidence.get("cost_evidence")
    if (
        evidence.get("schema") != HYBRID_EVIDENCE_SCHEMA
        or not isinstance(proxy, Mapping)
        or not isinstance(cost, Mapping)
        or candidate.stage_audits.get("proxy_maximization_hybrid") != proxy
        or candidate.stage_audits.get("cost_normalization_hybrid") != cost
    ):
        raise RuntimeError("repair-005 hybrid checkpoint evidence drifted")
    proxy_certificate = proxy.get("certificate")
    if not isinstance(proxy_certificate, Mapping):
        raise RuntimeError("repair-005 proxy certificate drifted")
    _validate_proxy_checkpoint_evidence(
        proxy,
        candidate=candidate,
        accepted_snapshot=snapshot,
        context=context,
    )
    _validate_primary_proxy_regret(candidate, proxy_certificate, context)
    direct_record = cost.get("direct_stage_record")
    direct_certificate = (
        direct_record.get("certificate") if isinstance(direct_record, Mapping) else None
    )
    combined = cost.get("combined_certificate")
    initial_snapshot_payload = cost.get("initial_direct_upper_snapshot")
    cost_snapshot_payload = cost.get("accepted_cost_snapshot")
    final_audit = cost.get("final_repeated_full_state_audit")
    if (
        proxy_certificate.get("valid") is not True
        or proxy_certificate.get("maximum_acceptance_passed") is not True
        or not isinstance(direct_record, Mapping)
        or direct_record.get("schema") != "rts_gmlc_exact_cg_stage_record_v1"
        or direct_record.get("stage") != "cost_normalization"
        or direct_record.get("sense") != "minimize"
        or not isinstance(direct_certificate, Mapping)
        or direct_certificate.get("valid") is not True
        or not isinstance(combined, Mapping)
        or combined.get("schema") != COMBINED_COST_SCHEMA
        or combined.get("valid") is not True
        or combined.get("maximum_acceptance_passed") is not True
        or combined.get("ordinary_dual_bound_usd") is not None
        or combined.get("decision_cap_is_ordinary_dual_bound") is not False
        or not v4._checkpoint_close(
            combined.get("direct_stage_ordinary_dual_bound_usd"),
            direct_certificate.get("lower_bound"),
        )
        or not isinstance(initial_snapshot_payload, Mapping)
        or not isinstance(cost_snapshot_payload, Mapping)
        or not isinstance(final_audit, Mapping)
        or cost.get("cost_decision_cross_attempt_resume_allowed") is not False
    ):
        raise RuntimeError("repair-005 cost evidence drifted")
    initial_snapshot = _snapshot_from_payload(initial_snapshot_payload)
    cost_snapshot = _snapshot_from_payload(cost_snapshot_payload)
    tolerance = float(
        context.input_contract["formal_successor"]["cost_match_tolerance_usd"]
    )
    proxy_tolerance = float(
        context.config["formal_solver"]["stages"]["cost_normalization"][
            "proxy_floor_absolute_tolerance"
        ]
    )
    state_ids = _context_state_ids(context)
    if (
        initial_snapshot.sha256 != cost.get("initial_direct_upper_snapshot_sha256")
        or cost_snapshot.sha256 != cost.get("accepted_cost_snapshot_sha256")
        or abs(cost_snapshot.operating_cost_usd - candidate.operating_cost_usd)
        > tolerance
        or abs(float(combined["upper_bound"]) - cost_snapshot.operating_cost_usd)
        > tolerance
        or not v4._checkpoint_close(
            cost.get("proxy_floor"), direct_record.get("proxy_floor")
        )
        or candidate.reactive_proxy_fraction + proxy_tolerance
        < float(cost["proxy_floor"])
    ):
        raise RuntimeError("repair-005 accepted cost witness drifted")
    method = cost.get("method")
    rounds = cost.get("cost_decision_rounds")
    if method == "direct_exact_cg":
        maximum = direct_record.get("maximum_acceptance")
        if (
            direct_record.get("eligible") is not True
            or direct_record.get("failure_reason") is not None
            or not isinstance(maximum, Mapping)
            or maximum.get("maximum_acceptance_passed") is not True
            or initial_snapshot != cost_snapshot
            or combined.get("decision_derived_cost_lower_bound") is not None
            or combined.get("decision_round_count") != 0
            or combined.get("method") != "direct_exact_cg"
            or not v4._checkpoint_close(
                combined.get("lower_bound"), direct_certificate.get("lower_bound")
            )
            or not v4._checkpoint_close(
                combined.get("upper_bound"), direct_certificate.get("upper_bound")
            )
            or not v4._checkpoint_close(
                combined.get("absolute_gap"), direct_certificate.get("absolute_gap")
            )
            or not v4._checkpoint_close(
                combined.get("relative_gap_to_feasible_incumbent"),
                direct_certificate.get("relative_gap_to_feasible_incumbent"),
            )
            or combined.get("target_attained") is not maximum.get("target_attained")
            or cost.get("cost_decision_status") != "not_required"
            or rounds != []
            or v4._exact_json_text(final_audit)
            != v4._exact_json_text(direct_record.get("final_full_state_audit"))
        ):
            raise RuntimeError("repair-005 direct cost evidence drifted")
        _validate_persisted_cost_audit(
            final_audit,
            snapshot=cost_snapshot,
            candidate=candidate,
            state_ids=state_ids,
            cost_tolerance_usd=tolerance,
            proxy_tolerance=proxy_tolerance,
            snapshot_sha_field="reported_shared_snapshot_sha256",
        )
    elif method == "direct_exact_cg_plus_cost_decision_bisection":
        fallback = _validated_cost_fallback_bracket(
            ExactCgStageResult(
                None,
                dict(direct_record),
                audited_snapshot=initial_snapshot,
            ),
            all_state_ids=state_ids,
            cost_tolerance_usd=tolerance,
            proxy_tolerance=proxy_tolerance,
        )
        if (
            fallback is None
            or not v4._checkpoint_close(
                fallback.lower_bound_usd, direct_certificate.get("lower_bound")
            )
            or not v4._checkpoint_close(
                fallback.upper_bound_usd, direct_certificate.get("upper_bound")
            )
            or fallback.upper_snapshot != initial_snapshot
            or combined.get("decision_derived_cost_lower_bound")
            != combined.get("lower_bound")
            or combined.get("method") != "direct_exact_cg_plus_cost_decision_bisection"
            or not isinstance(rounds, list)
            or len(rounds) != combined.get("decision_round_count")
            or not 1
            <= len(rounds)
            <= int(
                context.input_contract["formal_successor"][
                    "cost_decision_maximum_rounds"
                ]
            )
            or cost.get("cost_decision_status") != "accepted"
        ):
            raise RuntimeError("repair-005 fallback cost evidence drifted")
        _validate_persisted_cost_audit(
            final_audit,
            snapshot=cost_snapshot,
            candidate=candidate,
            state_ids=state_ids,
            cost_tolerance_usd=tolerance,
            proxy_tolerance=proxy_tolerance,
            snapshot_sha_field="shared_snapshot_sha256",
            expected_schema="rts_gmlc_v4_repair_005_repeated_cost_audit_v1",
        )
    else:
        raise RuntimeError("repair-005 cost method drifted")
    return candidate, snapshot


def _validate_round_artifacts(
    checkpoint_root: Path,
    context: v4._FrontierContext,
    ordinal: int,
    candidate: v4._Candidate,
    evidence: Mapping[str, object],
) -> None:
    if ordinal <= 4:
        if (checkpoint_root / "level_set_rounds").exists() or (
            checkpoint_root / "cost_decision_rounds"
        ).exists():
            raise RuntimeError("repair-005 prefix gained decision rounds")
        return
    proxy = evidence["proxy_evidence"]
    if not isinstance(proxy, Mapping):
        raise RuntimeError("repair-005 proxy round evidence is missing")
    repair005._validate_round_artifacts(
        checkpoint_root,
        context,
        ordinal,
        candidate,
        proxy,
    )
    cost = evidence["cost_evidence"]
    references = cost["cost_decision_rounds"]
    rounds_root = checkpoint_root / "cost_decision_rounds"
    if cost["method"] == "direct_exact_cg":
        if references != [] or rounds_root.exists():
            raise RuntimeError("repair-005 direct cost gained decision rounds")
        return
    if not rounds_root.is_dir():
        raise RuntimeError("repair-005 cost decision rounds are missing")
    loaded = load_contiguous_round_checkpoints(
        checkpoint_root.parent,
        candidate_id=candidate.requested_candidate_id,
        candidate_ordinal=ordinal,
        input_contract_sha256=context.input_contract_sha256,
        predecessor_manifest_sha256=common_input_signature_sha256(
            {
                "input_contract_sha256": context.input_contract_sha256,
                "candidate_ordinal": ordinal,
                "candidate_id": candidate.requested_candidate_id,
                "proxy_floor": cost["proxy_floor"],
                "initial_lower_bound_usd": cost["direct_stage_record"]["certificate"][
                    "lower_bound"
                ],
                "initial_upper_bound_usd": cost["direct_stage_record"]["certificate"][
                    "upper_bound"
                ],
                "initial_upper_snapshot_sha256": cost[
                    "initial_direct_upper_snapshot_sha256"
                ],
                "cost_match_tolerance_usd": context.input_contract["formal_successor"][
                    "cost_match_tolerance_usd"
                ],
            }
        ),
    )
    maximum_rounds = int(
        context.input_contract["formal_successor"]["cost_decision_maximum_rounds"]
    )
    if not 1 <= len(loaded) <= maximum_rounds:
        raise RuntimeError("repair-005 cost decision round count exceeds frozen limit")
    if len(loaded) != len(references):
        raise RuntimeError("repair-005 cost decision round count drifted")
    for payload, reference in zip(loaded, references, strict=True):
        path = rounds_root / f"{int(payload['round_ordinal']):02d}"
        if (
            not isinstance(reference, Mapping)
            or reference.get("round_ordinal") != payload["round_ordinal"]
            or reference.get("round_sha256") != _sha256(path / "round.json")
            or reference.get("manifest_sha256") != _sha256(path / "SHA256SUMS")
        ):
            raise RuntimeError("repair-005 cost decision round reference drifted")
    final_after = loaded[-1]["bracket_after"]
    if not isinstance(final_after, Mapping) or not isinstance(
        final_after.get("upper_snapshot"), Mapping
    ):
        raise RuntimeError("repair-005 final cost bracket drifted")
    final_bracket = CostBracket(
        float(final_after["lower_bound_usd"]),
        float(final_after["upper_bound_usd"]),
        _snapshot_from_payload(final_after["upper_snapshot"]),
    )
    expected_certificate = cost_acceptance_certificate(
        final_bracket,
        target_relative_gap=float(
            context.input_contract["formal_successor"]["target_relative_gap"]
        ),
        maximum_relative_gap=float(
            context.input_contract["formal_successor"][
                "maximum_accepted_relative_gap_to_feasible_incumbent"
            ]
        ),
    )
    combined = cost["combined_certificate"]
    certificate_fields = tuple(key for key in expected_certificate if key != "schema")
    persisted_certificate = {key: combined.get(key) for key in certificate_fields}
    expected_fields = {key: expected_certificate[key] for key in certificate_fields}
    if (
        v4._exact_json_text(persisted_certificate)
        != v4._exact_json_text(expected_fields)
        or cost.get("cost_decision_predecessor_sha256")
        != loaded[0].get("predecessor_manifest_sha256")
        or final_bracket.upper_snapshot.sha256
        != cost.get("accepted_cost_snapshot_sha256")
    ):
        raise RuntimeError("repair-005 final cost certificate drifted")


def _save_candidate_checkpoint(
    context: v4._FrontierContext,
    output_root: Path,
    ordinal: int,
    candidate: v4._Candidate,
    *,
    mode: str,
    evidence: Mapping[str, object],
    artifact_roots: Mapping[str, Path | None] | None = None,
) -> tuple[v4._Candidate, SharedSnapshot]:
    canonical = _checkpoint_payload(
        context, ordinal, candidate, mode=mode, evidence=evidence
    )
    target = v4._candidate_checkpoint_path(
        output_root, ordinal, candidate.requested_candidate_id
    )
    if target.exists():
        _verify_manifest(target)
        observed = v4._load_json(target, "candidate.json")
        loaded = _validate_checkpoint_document(observed, context, ordinal)
        _validate_round_artifacts(
            target, context, ordinal, loaded[0], observed["evidence"]
        )
        if v4._exact_json_text(observed) != v4._exact_json_text(canonical):
            raise RuntimeError("repair-005 existing checkpoint drifted")
        return loaded

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "candidate.json", canonical)
        for name, root in (artifact_roots or {}).items():
            if root is not None and root.is_dir():
                shutil.copytree(root, staging / name)

    def validator(staging: Path) -> None:
        observed = json.loads((staging / "candidate.json").read_text(encoding="utf-8"))
        _validate_checkpoint_document(observed, context, ordinal)
        with tempfile.TemporaryDirectory(dir=staging.parent) as temporary:
            wrapper = Path(temporary) / target.name
            wrapper.mkdir()
            for directory_name in ("level_set_rounds", "cost_decision_rounds"):
                source = staging / directory_name
                if source.is_dir():
                    shutil.copytree(source, wrapper / directory_name)
            _validate_round_artifacts(
                wrapper, context, ordinal, candidate, observed["evidence"]
            )

    repair004._publish_recursive_payload(target, writer, validator)
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
            raise RuntimeError("repair-005 all six checkpoints are required")
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
    candidates: list[v4._Candidate],
    selected: list[tuple[str, v4._Candidate]],
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
        or v4._exact_json_text(summary)
        != v4._exact_json_text(
            _frontier_summary(
                context,
                candidates,
                selected,
                manifests,
                attempt_id=attempt_id,
            )
        )
    ):
        raise RuntimeError("repair-005 frontier summary drifted")
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
                raise RuntimeError(f"repair-005 frontier file drifted: {name}")
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
        raise RuntimeError("Cannot generate repair-005 candidates after joint AC")
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
            "schema": "rts_gmlc_v4_repair_005_candidate_attempt_v1",
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
    source_prefix = _verified_source_prefix(context.input_contract)
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
            checkpoint = v4._candidate_checkpoint_path(
                output_root, ordinal, requested_id
            )
            progress.emit(
                "candidate_checkpoint_loaded",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                checkpoint_manifest_sha256=_sha256(checkpoint / "SHA256SUMS"),
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
        try:
            if ordinal <= 4:
                candidate, snapshot, evidence = _prefix_candidate(
                    context, ordinal, source_prefix[ordinal - 1]
                )
                progress.emit(
                    "source_checkpoint_imported",
                    candidate_ordinal=ordinal,
                    requested_candidate_id=requested_id,
                    source_checkpoint_manifest_sha256=evidence[
                        "source_checkpoint_manifest_sha256"
                    ],
                    source_candidate_json_sha256=evidence[
                        "source_candidate_json_sha256"
                    ],
                    solver_call_count=0,
                    imported_as_recomputed=False,
                )
                artifact_roots = None
            else:
                if previous_snapshot is None:
                    raise RuntimeError(
                        "repair-005 predecessor proxy snapshot is missing"
                    )
                candidate, snapshot, evidence, artifact_roots = _hybrid_candidate(
                    context,
                    ordinal=ordinal,
                    fallback_lower_snapshot=previous_snapshot,
                    progress=progress,
                    candidate_log_root=log_root / f"{ordinal:02d}_{requested_id}",
                    deadline_monotonic=monotonic() + total_limit,
                )
            candidate, previous_snapshot = _save_candidate_checkpoint(
                context,
                output_root,
                ordinal,
                candidate,
                mode=str(control["mode"]),
                evidence=evidence,
                artifact_roots=artifact_roots,
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
    output_root = output_directory or context.output_root
    _require_preregistration(context, output_root)
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("candidate_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid repair-005 candidate attempt ID")
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
                        "Failed to append repair-005 attempt_failed: "
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
    output_root = output_directory
    _require_preregistration(context, output_root)
    candidates, frontier_manifest = _load_candidate_frontier(context, output_root)
    matches = [item for item in candidates if item.candidate_id == candidate_id]
    if len(matches) != 1:
        raise RuntimeError("repair-005 worker candidate identity drifted")
    candidate = matches[0]
    if initial_strategy not in context.config["joint_ac"]["initial_strategies"]:
        raise RuntimeError("repair-005 worker strategy drifted")
    observed_call_manifest = v4._validate_joint_call_registration(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
    )
    if observed_call_manifest != call_registration_manifest_sha256:
        raise RuntimeError("repair-005 worker call registration drifted")
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
        raise RuntimeError("repair-005 worker parent identity drifted")
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
        raise RuntimeError("repair-005 worker execution lease drifted")
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


def _run_joint_ac_attempt(
    context: v4._FrontierContext,
    output_root: Path,
    registration: Mapping[str, Any],
    candidates: list[v4._LoadedCandidate],
    frontier_manifest: str,
    attempt_id: str,
    log_root: Path,
    progress: JsonlProgressWriter,
) -> dict[str, Any]:
    original = repair005._joint_worker_command
    repair005._joint_worker_command = _joint_worker_command
    try:
        return repair005._run_joint_ac_attempt(
            context,
            output_root,
            registration,
            candidates,
            frontier_manifest,
            attempt_id,
            log_root,
            progress,
        )
    finally:
        repair005._joint_worker_command = original


def run_joint_ac(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = output_directory or context.output_root
    registration = _require_preregistration(context, output_root)
    candidates, frontier_manifest = _load_candidate_frontier(context, output_root)
    if not candidates:
        raise RuntimeError("repair-005 candidate frontier is empty")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("joint_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid repair-005 joint attempt ID")
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
                "schema": "rts_gmlc_v4_repair_005_joint_attempt_v1",
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
                    "Failed to emit repair-005 joint attempt_failed: "
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
        item is None for item in worker_values
    ):
        parser.error("joint-call-worker requires candidate, strategy, result, and log")
    if args.stage != "joint-call-worker" and any(
        item is not None for item in worker_values
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


__all__ = [
    "CHECKPOINT_SCHEMA",
    "COMBINED_COST_SCHEMA",
    "DEFAULT_CONFIG_PATH",
    "HYBRID_EVIDENCE_SCHEMA",
    "PREFIX_EVIDENCE_SCHEMA",
    "_build_context",
    "_cost_fallback_trigger",
    "_prefix_candidate",
    "_read_config",
    "_verified_source_prefix",
    "prepare_preregistration",
]
