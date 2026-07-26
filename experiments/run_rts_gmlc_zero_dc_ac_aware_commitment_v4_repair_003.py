"""Repair-003 hybrid certificate control plane.

This module prepares and pilots the successor algorithm.  It deliberately has
no command that publishes a preregistration, starts formal candidate
generation, or calls joint AC.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments import pilot_rts_gmlc_zero_dc_ac_aware_formulations as pilot
from src.grid.rts_gmlc_exact_cg import (
    SharedSnapshot,
    extract_shared_snapshot,
    relax_fixed_integer_variables,
)
from src.grid.rts_gmlc_exact_cg_runner import (
    ExactCgCall,
    ExactCgStageResult,
    ExactCgTimeLimits,
    run_exact_cg_stage,
)
from src.grid.rts_gmlc_formal_cg_adapter import (
    FormalCgModelAdapter,
    canonicalize_discrete_snapshot,
)
from src.grid.rts_gmlc_level_set import (
    BracketRunResult,
    LevelOracleEvidence,
    ProxyBracket,
    run_bracketed_level_set,
)
from src.solvers.mip_progress import JsonlProgressWriter

PREDECESSOR_ROOT = Path(
    "results/tables/"
    "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_"
    "warmstart_scope_repair_002"
)
PREDECESSOR_INPUT_CONTRACT_SHA256 = (
    "b9d40f95a0f5f24b546f77a6d21ee6f59c43e8d5e2732a64075fa82c8100cc21"
)
PREDECESSOR_PREREGISTRATION_MANIFEST_SHA256 = (
    "0fec4eb7eeae5aa83cdbce41bfffc04c2f73b76a3ce64579b2b00e046417e4df"
)
FAILED_ATTEMPT_ID = "formal_warmstart_repair_20260719T180650Z"
FAILED_PROGRESS_PATH = (
    Path("results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4")
    / FAILED_ATTEMPT_ID
    / "progress.jsonl"
)
FAILED_PROGRESS_SHA256 = (
    "c08a10cf92c3dbe5a8f1b7f229ac3d73c8ebb8231583b189924b4a8dd9980516"
)


@dataclass(frozen=True)
class PrefixExpectation:
    ordinal: int
    requested_candidate_id: str
    manifest_sha256: str
    commitment_sha256: str
    dispatch_sha256: str
    reactive_proxy_fraction: float


@dataclass(frozen=True)
class ImportedPrefixCandidate:
    expectation: PrefixExpectation
    candidate: object
    checkpoint_path: Path


@dataclass(frozen=True)
class HybridProxyResult:
    method: str
    snapshot: SharedSnapshot | None
    certificate: dict[str, object]
    direct_stage_record: dict[str, object]
    level_set: BracketRunResult | None
    failure_reason: str | None


@dataclass(frozen=True)
class RehydratedPrefixSnapshot:
    snapshot: SharedSnapshot
    reconstruction_record: dict[str, object]
    full_state_audit_record: dict[str, object]


PREFIX_EXPECTATIONS = (
    PrefixExpectation(
        1,
        "q_proxy_delta_0p0010",
        "ad854739ef601e95e0f50a304bf9a6dabe84692c9407dc9d8a2444a2e4cbe681",
        "6838623399f5d760741aaa5e3cb395f92a87459576f5833e9753ab83347f982e",
        "7dc7e40ca9a90cf09018db76c959a8a2dafcfae91b7183364fb3884021a4c6e3",
        0.24328147100424327,
    ),
    PrefixExpectation(
        2,
        "q_proxy_delta_0p0025",
        "bab8a48b9a3db0b452e4220e512ffa30de61d6bb4a27b5e04524e6bc7f83853f",
        "a53bc3509f7a1494991b310d2c84591ad388f385d43a53f0c41b6ec6965fd85f",
        "d0a07225b48dbdb097294e9906c6282c0a4997fd0eb3d773784d730dcd461b42",
        0.24328147100424327,
    ),
    PrefixExpectation(
        3,
        "q_proxy_delta_0p0050",
        "7fa4eead29345e287d304e7ec4e5a676f40d1f31d191ca092e88768ffc1ded34",
        "af291bb6238a6ea3b2adad70d94feb92af66e31356f55fd16d3bac4e56fe6ab8",
        "feae95861a8884301d6908eb86790ce26fe13f7579b42c969c561a72785e7d3c",
        0.24328147100424327,
    ),
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_recursive_manifest(root: Path) -> None:
    manifest_path = root / "SHA256SUMS"
    paths = sorted(
        path for path in root.rglob("*") if path.is_file() and path != manifest_path
    )
    manifest_path.write_bytes(
        "".join(
            f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n" for path in paths
        ).encode("ascii")
    )


def _validate_prefix_payload(
    document: Mapping[str, object], expectation: PrefixExpectation
) -> object:
    candidate_payload = document.get("candidate")
    if (
        document.get("schema") != v4._CHECKPOINT_SCHEMA
        or document.get("input_contract_sha256") != PREDECESSOR_INPUT_CONTRACT_SHA256
        or document.get("ordinal") != expectation.ordinal
        or not isinstance(candidate_payload, Mapping)
    ):
        raise RuntimeError("repair-002 predecessor checkpoint contract drifted")
    candidate = v4._candidate_from_checkpoint_payload(candidate_payload)
    if (
        candidate.requested_candidate_id != expectation.requested_candidate_id
        or candidate.commitment_sha256 != expectation.commitment_sha256
        or candidate.dispatch_sha256 != expectation.dispatch_sha256
        or candidate.reactive_proxy_fraction != expectation.reactive_proxy_fraction
    ):
        raise RuntimeError("repair-002 predecessor candidate identity drifted")
    return candidate


def verify_predecessor_prefix(
    root: Path = PREDECESSOR_ROOT,
    expectations: Sequence[PrefixExpectation] = PREFIX_EXPECTATIONS,
) -> tuple[ImportedPrefixCandidate, ...]:
    preregistration_root = root / "preregistration"
    v4._verify_output_manifest(preregistration_root)
    prereg_manifest = preregistration_root / "SHA256SUMS"
    if _sha256(prereg_manifest) != PREDECESSOR_PREREGISTRATION_MANIFEST_SHA256:
        raise RuntimeError("repair-002 preregistration manifest drifted")
    checkpoints_root = root / "candidate_checkpoints"
    expected_names = [
        f"{item.ordinal:02d}_{item.requested_candidate_id}" for item in expectations
    ]
    observed_names = sorted(
        path.name for path in checkpoints_root.iterdir() if path.is_dir()
    )
    if observed_names != expected_names:
        raise RuntimeError("repair-002 completed prefix is not exact and contiguous")
    imported = []
    for expectation in expectations:
        path = (
            checkpoints_root
            / f"{expectation.ordinal:02d}_{expectation.requested_candidate_id}"
        )
        v4._verify_output_manifest(path)
        if _sha256(path / "SHA256SUMS") != expectation.manifest_sha256:
            raise RuntimeError("repair-002 checkpoint manifest drifted")
        document = json.loads((path / "candidate.json").read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise RuntimeError("repair-002 checkpoint document drifted")
        candidate = _validate_prefix_payload(document, expectation)
        imported.append(ImportedPrefixCandidate(expectation, candidate, path))
    return tuple(imported)


def verify_candidate_four_upper_bound(
    progress_path: Path = FAILED_PROGRESS_PATH,
) -> dict[str, object]:
    if _sha256(progress_path) != FAILED_PROGRESS_SHA256:
        raise RuntimeError("candidate-4 failure progress log drifted")
    events = [
        json.loads(line)
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    completed = [
        event
        for event in events
        if event.get("event") == "exact_cg_stage_completed"
        and event.get("candidate_ordinal") == 4
        and event.get("stage") == "proxy_maximization"
    ]
    candidate_failed = [
        event
        for event in events
        if event.get("event") == "candidate_failed"
        and event.get("candidate_ordinal") == 4
    ]
    attempt_failed = [
        event for event in events if event.get("event") == "attempt_failed"
    ]
    if len(completed) != 1 or len(candidate_failed) != 1 or len(attempt_failed) != 1:
        raise RuntimeError("candidate-4 terminal event chain drifted")
    event = completed[0]
    certificate = event.get("certificate")
    if not isinstance(certificate, Mapping):
        raise RuntimeError("candidate-4 certificate is missing")
    expected = {
        "lower_bound": 0.2771084337349398,
        "upper_bound": 0.2895372905465777,
        "absolute_gap": 0.012428856811637856,
        "relative_gap_to_feasible_incumbent": 0.04485196153764964,
    }
    if (
        any(certificate.get(key) != value for key, value in expected.items())
        or certificate.get("valid") is not True
        or event.get("eligible") is not False
        or event.get("failure_reason")
        != "final_bound_certificate_exceeds_maximum_acceptance"
    ):
        raise RuntimeError("candidate-4 failed certificate drifted")
    checkpoint = PREDECESSOR_ROOT / "candidate_checkpoints" / "04_q_proxy_delta_0p0100"
    if (
        checkpoint.exists()
        or (PREDECESSOR_ROOT / "candidate_frontier").exists()
        or (PREDECESSOR_ROOT / "joint_ac").exists()
    ):
        raise RuntimeError("candidate-4 publication boundary drifted")
    return {
        "schema": "rts_gmlc_repair_003_imported_upper_bound_v1",
        "attempt_id": FAILED_ATTEMPT_ID,
        "progress_sha256": FAILED_PROGRESS_SHA256,
        "candidate_ordinal": 4,
        "requested_candidate_id": "q_proxy_delta_0p0100",
        "upper_bound": expected["upper_bound"],
        "lower_bound_value_observed_but_snapshot_not_importable": expected[
            "lower_bound"
        ],
        "lower_snapshot_imported": False,
        "failure_reason": event["failure_reason"],
        "joint_ac_solver_call_count": 0,
    }


def _fix_candidate_values(model: object, candidate: object) -> None:
    row_components = {
        "commitment": candidate.commitment,
        "startup": candidate.startup,
        "shutdown": candidate.shutdown,
        "reserve_up": candidate.reserve_up_mw,
    }
    for component_name, rows in row_components.items():
        component = getattr(model, component_name)
        for variable in component.values():
            index = variable.index()
            time_index, uid = index if isinstance(index, tuple) else (None, None)
            variable.fix(rows[int(time_index)][str(uid)])
    state_components = {
        "generation": candidate.generation_mw,
        "branch_flow": candidate.branch_flows_mw,
        "dc_flow": candidate.dc_flows_mw,
    }
    for component_name, rows in state_components.items():
        component = getattr(model, component_name)
        for variable in component.values():
            index = variable.index()
            if not isinstance(index, tuple) or str(index[0]) != "normal":
                continue
            time_index = int(index[1])
            uid = str(index[2])
            variable.fix(rows[time_index][uid])
    model.reactive_proxy.fix(float(candidate.reactive_proxy_fraction))


def rehydrate_prefix_snapshot(
    context: object,
    imported: ImportedPrefixCandidate,
    *,
    progress: object,
    log_root: Path,
) -> RehydratedPrefixSnapshot:
    """Reconstruct omitted shared values, then repeat the 24-state audit."""

    candidate = imported.candidate
    formal_solver = context.config["formal_solver"]
    frontier = context.config["candidate_frontier"]
    problem = v4._formal_problem(context, cost_budget_usd=candidate.cost_budget_usd)
    floor_tolerance = float(
        formal_solver["stages"]["cost_normalization"]["proxy_floor_absolute_tolerance"]
    )
    proxy_floor = float(candidate.reactive_proxy_fraction) - floor_tolerance
    call = ExactCgCall(
        call_id=(
            "level_set_cost_minimization.prefix_reconstruction_"
            f"{imported.expectation.ordinal:02d}.master"
        ),
        kind="master",
        stage="level_set_cost_minimization",
        iteration=1,
        active_state_ids=problem.all_state_ids,
        all_state_ids=problem.all_state_ids,
        time_limit_seconds=float(
            formal_solver["time_limits_seconds"]["final_full_state_audit_per_call"]
        ),
        target_relative_gap=float(
            formal_solver["stages"]["proxy_maximization"]["target_relative_gap"]
        ),
        proxy_floor=proxy_floor,
    )
    adapter = FormalCgModelAdapter(
        problem=problem,
        formal_solver=formal_solver,
        candidate_frontier=frontier,
        snapshot_contract=context.config["candidate_snapshot"],
        progress=progress,
        log_root=log_root,
        event_context={
            "candidate_ordinal": imported.expectation.ordinal,
            "requested_candidate_id": imported.expectation.requested_candidate_id,
            "repair_003_prefix_reconstruction": True,
        },
    )
    config = adapter._call_config(call)
    build_started = time.perf_counter()
    handle = pilot._build_model_handle(
        problem,
        config,
        problem.all_state_ids,
        stage=call.stage,
        proxy_floor=proxy_floor,
    )
    _fix_candidate_values(handle.model, candidate)
    relax_fixed_integer_variables(handle.model)
    build_seconds = time.perf_counter() - build_started
    solved = pilot._solve_handle(
        handle,
        config,
        native_log=adapter._native_log(call),
        progress=progress,
        solve_label=call.call_id,
    )
    if not solved["incumbent_usable"]:
        raise RuntimeError("repair-002 prefix snapshot reconstruction did not solve")
    raw_snapshot = extract_shared_snapshot(handle.model)
    snapshot, normalization = canonicalize_discrete_snapshot(
        handle.model, raw_snapshot, context.config["candidate_snapshot"]
    )
    commitment = v4._extract_commitment(handle.model, handle.scuc_context)
    generation = v4._extract_generation(handle.model, handle.scuc_context, "normal")
    branch = v4._extract_branch_flows(handle.model, handle.scuc_context, "normal")
    dc = v4._extract_dc_flows(handle.model, handle.scuc_context, "normal")
    reconstructed_proxy = v4._reactive_proxy_value(context, problem.points, commitment)
    if (
        v4._commitment_sha256(commitment) != candidate.commitment_sha256
        or v4._dispatch_sha256(generation, branch, dc) != candidate.dispatch_sha256
        or reconstructed_proxy != candidate.reactive_proxy_fraction
        or abs(snapshot.operating_cost_usd - candidate.operating_cost_usd)
        > float(frontier["cost_cap_absolute_tolerance_usd"])
    ):
        raise RuntimeError("repair-002 prefix reconstruction identity drifted")
    audit_call = ExactCgCall(
        call_id=(
            "level_set_cost_minimization.prefix_reconstruction_"
            f"{imported.expectation.ordinal:02d}.final_full_state_fixed_shared_audit"
        ),
        kind="final_audit",
        stage="level_set_cost_minimization",
        iteration=1,
        active_state_ids=problem.all_state_ids,
        all_state_ids=problem.all_state_ids,
        time_limit_seconds=call.time_limit_seconds,
        target_relative_gap=call.target_relative_gap,
        proxy_floor=proxy_floor,
        shared_snapshot=snapshot,
    )
    audit = adapter.audit_full_state(audit_call)
    if not (
        audit.solution_usable
        and audit.shared_snapshot_fixed
        and audit.integer_variables_relaxed
        and audit.residual_audit_passed
        and audit.additional_audits_passed
        and audit.audited_state_ids == problem.all_state_ids
    ):
        raise RuntimeError("repair-002 prefix repeated 24-state audit failed")
    return RehydratedPrefixSnapshot(
        snapshot,
        {
            "schema": "rts_gmlc_repair_003_prefix_snapshot_reconstruction_v1",
            "source_checkpoint_manifest_sha256": imported.expectation.manifest_sha256,
            "source_input_contract_sha256": PREDECESSOR_INPUT_CONTRACT_SHA256,
            "build_seconds": build_seconds,
            "solve": solved,
            "snapshot_normalization": normalization,
            "reconstructed_snapshot_sha256": snapshot.sha256,
            "reconstructed_commitment_sha256": v4._commitment_sha256(commitment),
            "reconstructed_dispatch_sha256": v4._dispatch_sha256(
                generation, branch, dc
            ),
            "recomputed_proxy_fraction": reconstructed_proxy,
        },
        dict(audit.record),
    )


def level_evidence_from_stage_result(
    result: ExactCgStageResult, *, proxy_floor: float
) -> LevelOracleEvidence:
    record = result.stage_record
    outcome = record.get("level_set_oracle_outcome")
    masters = record.get("master_records")
    termination = "unknown"
    if isinstance(masters, list):
        for master in masters:
            if not isinstance(master, Mapping):
                continue
            callback = master.get("callback_record")
            solve = callback.get("solve") if isinstance(callback, Mapping) else None
            if isinstance(solve, Mapping):
                termination = str(solve.get("termination_condition"))
    separation = record.get("bound_only_early_separation")
    if outcome == "bound_only_early_separation":
        if not (
            record.get("failure_reason") is None
            and record.get("eligible") is False
            and result.snapshot is None
            and result.audited_snapshot is None
            and isinstance(separation, Mapping)
            and separation.get("schema")
            == "rts_gmlc_level_set_bound_only_early_separation_v1"
            and separation.get("valid") is True
            and separation.get("source")
            == "active_budget_capped_decision_mip_global_infeasibility"
        ):
            raise RuntimeError("bound-only early-separation contract drifted")
        cap = separation.get("decision_budget_cap_usd")
        if not isinstance(cap, (int, float)) or not math.isfinite(float(cap)):
            raise RuntimeError("bound-only early-separation budget cap drifted")
        return LevelOracleEvidence(
            proxy_floor=proxy_floor,
            active_master_bound_valid=False,
            active_master_dual_lower_bound_usd=None,
            incumbent_snapshot=None,
            all_inactive_states_screened=False,
            final_full_state_audit_passed=False,
            residual_audit_passed=False,
            recomputed_proxy=None,
            audited_operating_cost_usd=None,
            active_master_globally_infeasible=True,
            active_master_budget_cap_usd=float(cap),
            termination=termination,
        )
    audit = record.get("final_full_state_audit")
    callback = audit.get("callback_record") if isinstance(audit, Mapping) else None
    audit_callback = callback if isinstance(callback, Mapping) else {}
    iterations = record.get("iteration_records")
    final_iteration = (
        iterations[-1] if isinstance(iterations, list) and iterations else None
    )
    screens_complete = bool(
        isinstance(final_iteration, Mapping)
        and final_iteration.get("screen_round_complete") is True
        and not final_iteration.get("promotions")
    )
    audited_witness = bool(
        outcome == "audited_feasible"
        and record.get("eligible") is True
        and record.get("failure_reason") is None
        and result.snapshot is not None
        and result.audited_snapshot is not None
    )
    return LevelOracleEvidence(
        proxy_floor=proxy_floor,
        active_master_bound_valid=False,
        active_master_dual_lower_bound_usd=None,
        incumbent_snapshot=result.audited_snapshot if audited_witness else None,
        all_inactive_states_screened=audited_witness and screens_complete,
        final_full_state_audit_passed=bool(
            audited_witness
            and isinstance(audit, Mapping)
            and audit.get("passed") is True
        ),
        residual_audit_passed=bool(
            audited_witness
            and isinstance(audit, Mapping)
            and audit.get("residual_audit_passed") is True
        ),
        recomputed_proxy=(
            float(audit_callback["commitment_capability_proxy_fraction"])
            if audited_witness
            and "commitment_capability_proxy_fraction" in audit_callback
            else None
        ),
        audited_operating_cost_usd=(
            float(audit_callback["actual_operating_cost_usd"])
            if audited_witness and "actual_operating_cost_usd" in audit_callback
            else None
        ),
        termination=termination,
    )


def run_hybrid_proxy_certificate(
    direct_result: ExactCgStageResult,
    *,
    fallback_lower_snapshot: SharedSnapshot,
    imported_upper_bound: float,
    level_oracle: Callable[[float, int], ExactCgStageResult],
    effective_budget_usd: float,
    strict_separation_margin_usd: float,
    target_relative_gap: float,
    maximum_absolute_gap: float,
    maximum_relative_gap: float,
    maximum_rounds: int,
    candidate_id: str,
    candidate_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
    checkpoint_root: Path | None = None,
) -> HybridProxyResult:
    direct_record = direct_result.stage_record
    direct_certificate = direct_record.get("certificate")
    if (
        direct_result.snapshot is not None
        and direct_record.get("eligible") is True
        and isinstance(direct_certificate, dict)
    ):
        return HybridProxyResult(
            "direct_exact_cg",
            direct_result.snapshot,
            dict(direct_certificate),
            direct_record,
            None,
            None,
        )
    upper_candidates = [float(imported_upper_bound)]
    if (
        isinstance(direct_certificate, Mapping)
        and direct_certificate.get("valid") is True
    ):
        upper = direct_certificate.get("upper_bound")
        if isinstance(upper, (int, float)) and math.isfinite(float(upper)):
            upper_candidates.append(float(upper))
    lower_snapshot = direct_result.audited_snapshot or fallback_lower_snapshot
    lower = float(lower_snapshot.reactive_proxy)
    bracket = ProxyBracket(lower, min(upper_candidates), lower_snapshot)
    bracketed = run_bracketed_level_set(
        bracket,
        oracle=lambda floor, ordinal: level_evidence_from_stage_result(
            level_oracle(floor, ordinal), proxy_floor=floor
        ),
        effective_budget_usd=effective_budget_usd,
        strict_separation_margin_usd=strict_separation_margin_usd,
        target_relative_gap=target_relative_gap,
        maximum_absolute_gap=maximum_absolute_gap,
        maximum_relative_gap=maximum_relative_gap,
        maximum_rounds=maximum_rounds,
        candidate_id=candidate_id,
        candidate_ordinal=candidate_ordinal,
        input_contract_sha256=input_contract_sha256,
        predecessor_manifest_sha256=predecessor_manifest_sha256,
        checkpoint_root=checkpoint_root,
    )
    return HybridProxyResult(
        "direct_max_or_level_set_bisection",
        bracketed.bracket.lower_snapshot if bracketed.status == "accepted" else None,
        bracketed.certificate,
        direct_record,
        bracketed,
        bracketed.failure_reason,
    )


def control_plane_inventory() -> dict[str, object]:
    prefix = verify_predecessor_prefix()
    candidate_four = verify_candidate_four_upper_bound()
    return {
        "schema": "rts_gmlc_v4_repair_003_control_plane_inventory_v1",
        "formal_candidate_generation_started": False,
        "joint_ac_started": False,
        "prefix_candidate_count": len(prefix),
        "prefix_checkpoint_manifest_sha256s": [
            item.expectation.manifest_sha256 for item in prefix
        ],
        "candidate_four": candidate_four,
        "certificate_method": "direct_max_or_level_set_bisection",
    }


def run_prefix_reaudit_smoke(
    *,
    ordinal: int,
    run_id: str,
    config_path: Path = Path(
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml"
    ),
) -> dict[str, object]:
    if ordinal not in {1, 2, 3}:
        raise ValueError("prefix reaudit ordinal must be 1, 2, or 3")
    context = v4._build_context(config_path)
    imported = verify_predecessor_prefix()[ordinal - 1]
    log_root = (
        Path("results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4")
        / run_id
        / f"prefix_{ordinal:02d}"
    )
    progress = JsonlProgressWriter(
        log_root.parent / "progress.jsonl",
        run_id=run_id,
        preregistration_id="repair_003_nonformal_control_plane_verification",
        input_contract_sha256=context.input_contract_sha256,
    )
    progress.emit(
        "repair_003_prefix_reaudit_started",
        candidate_ordinal=ordinal,
        requested_candidate_id=imported.expectation.requested_candidate_id,
        formal_candidate_result=False,
        joint_ac_solver_call_count=0,
    )
    rehydrated = rehydrate_prefix_snapshot(
        context,
        imported,
        progress=progress,
        log_root=log_root,
    )
    result = {
        "schema": "rts_gmlc_repair_003_prefix_reaudit_smoke_v1",
        "run_id": run_id,
        "candidate_ordinal": ordinal,
        "requested_candidate_id": imported.expectation.requested_candidate_id,
        "source_checkpoint_manifest_sha256": imported.expectation.manifest_sha256,
        "input_contract_sha256": context.input_contract_sha256,
        "reconstructed_snapshot_sha256": rehydrated.snapshot.sha256,
        "reconstructed_snapshot_value_count": len(rehydrated.snapshot.values),
        "recomputed_proxy_fraction": rehydrated.reconstruction_record[
            "recomputed_proxy_fraction"
        ],
        "repeated_full_state_audit_passed": rehydrated.full_state_audit_record[
            "passed"
        ],
        "formal_candidate_result": False,
        "preregistration_published": False,
        "joint_ac_solver_call_count": 0,
    }
    progress.emit(
        "repair_003_prefix_reaudit_completed",
        candidate_ordinal=ordinal,
        requested_candidate_id=imported.expectation.requested_candidate_id,
        source_checkpoint_manifest_sha256=imported.expectation.manifest_sha256,
        reconstructed_snapshot_sha256=rehydrated.snapshot.sha256,
        reconstructed_snapshot_value_count=len(rehydrated.snapshot.values),
        recomputed_proxy_fraction=rehydrated.reconstruction_record[
            "recomputed_proxy_fraction"
        ],
        repeated_full_state_audit_passed=rehydrated.full_state_audit_record["passed"],
        formal_candidate_result=False,
        preregistration_published=False,
        joint_ac_solver_call_count=0,
    )
    return result


def run_delta_0p0075_level_set_pilot(
    *,
    run_id: str,
    config_path: Path = Path(
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml"
    ),
    output_root: Path = Path(
        "results/tables/"
        "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_"
        "hybrid_certificate_repair_003_decision_pilot"
    ),
) -> dict[str, object]:
    """Run only the non-formal fallback at the frozen pilot delta."""

    context = v4._build_context(config_path)
    imported = verify_predecessor_prefix()[2]
    upper_evidence = verify_candidate_four_upper_bound()
    log_root = (
        Path("results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4")
        / run_id
    )
    progress = JsonlProgressWriter(
        log_root / "progress.jsonl",
        run_id=run_id,
        preregistration_id="repair_003_nonformal_delta_0p0075_pilot",
        input_contract_sha256=context.input_contract_sha256,
    )
    progress.emit(
        "repair_003_level_set_pilot_started",
        relative_cost_budget_delta=0.0075,
        direct_phase_executed=False,
        formal_candidate_result=False,
        preregistration_published=False,
        joint_ac_solver_call_count=0,
    )
    rehydrated = rehydrate_prefix_snapshot(
        context,
        imported,
        progress=progress,
        log_root=log_root / "prefix_lower_witness",
    )
    baseline = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    budget = baseline * 1.0075
    cost_tolerance = float(
        context.config["candidate_frontier"]["cost_cap_absolute_tolerance_usd"]
    )
    effective_budget = budget + cost_tolerance
    strict_margin = 1.0e-4
    maximum_rounds = 8
    problem = v4._formal_problem(context, cost_budget_usd=budget)
    proxy_spec = context.config["formal_solver"]["stages"]["proxy_maximization"]
    level_limits = ExactCgTimeLimits(
        master_seconds=3600.0,
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
    predecessor_evidence_sha256 = hashlib.sha256(
        json.dumps(
            {
                "predecessor_preregistration_manifest_sha256": (
                    PREDECESSOR_PREREGISTRATION_MANIFEST_SHA256
                ),
                "candidate_4_progress_sha256": FAILED_PROGRESS_SHA256,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    ).hexdigest()

    def oracle(floor: float, round_ordinal: int) -> LevelOracleEvidence:
        adapter = FormalCgModelAdapter(
            problem=problem,
            formal_solver=context.config["formal_solver"],
            candidate_frontier=context.config["candidate_frontier"],
            snapshot_contract=context.config["candidate_snapshot"],
            progress=progress,
            log_root=log_root / f"level_set_round_{round_ordinal:02d}",
            event_context={
                "pilot_relative_cost_budget_delta": 0.0075,
                "level_set_round_ordinal": round_ordinal,
                "formal_candidate_result": False,
            },
        )
        result = run_exact_cg_stage(
            stage="level_set_budget_feasibility",
            all_state_ids=problem.all_state_ids,
            seed_state_ids=problem.initial_active_state_ids,
            target_relative_gap=float(proxy_spec["target_relative_gap"]),
            maximum_accepted_relative_gap_to_feasible_incumbent=float(
                proxy_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
            ),
            maximum_accepted_absolute_gap=None,
            time_limits=level_limits,
            callbacks=adapter.callbacks(),
            proxy_floor=floor,
        )
        return level_evidence_from_stage_result(result, proxy_floor=floor)

    bracketed = run_bracketed_level_set(
        ProxyBracket(
            imported.expectation.reactive_proxy_fraction,
            float(upper_evidence["upper_bound"]),
            rehydrated.snapshot,
        ),
        oracle=oracle,
        effective_budget_usd=effective_budget,
        strict_separation_margin_usd=strict_margin,
        target_relative_gap=float(proxy_spec["target_relative_gap"]),
        maximum_absolute_gap=float(proxy_spec["maximum_accepted_absolute_gap"]),
        maximum_relative_gap=float(
            proxy_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_rounds=maximum_rounds,
        candidate_id="q_proxy_delta_0p0075_nonformal_pilot",
        candidate_ordinal=1,
        input_contract_sha256=context.input_contract_sha256,
        predecessor_manifest_sha256=predecessor_evidence_sha256,
        checkpoint_root=output_root / "pilot_checkpoints",
    )
    summary = {
        "schema": "rts_gmlc_v4_repair_003_level_set_decision_pilot_v2",
        "status": bracketed.status,
        "failure_reason": bracketed.failure_reason,
        "run_id": run_id,
        "input_contract_sha256": context.input_contract_sha256,
        "relative_cost_budget_delta": 0.0075,
        "cost_budget_usd": budget,
        "effective_cost_budget_usd": effective_budget,
        "strict_cost_separation_margin_usd": strict_margin,
        "decision_mip_budget_cap_usd": effective_budget,
        "decision_mip_global_infeasibility_is_strict_separation": True,
        "direct_phase_executed": False,
        "pilot_scope": "fallback_control_plane_only",
        "certificate_method": "bracketed_budget_feasibility_decision_mip",
        "initial_lower_bound": imported.expectation.reactive_proxy_fraction,
        "initial_lower_snapshot_sha256": rehydrated.snapshot.sha256,
        "initial_upper_bound": upper_evidence["upper_bound"],
        "upper_bound_budget_nesting_justification": (
            "delta_0p0075_feasible_set_is_subset_of_delta_0p0100"
        ),
        "round_count": len(bracketed.round_checkpoints),
        "certificate": bracketed.certificate,
        "final_lower_snapshot_sha256": bracketed.bracket.lower_snapshot.sha256,
        "predecessor_evidence_sha256": predecessor_evidence_sha256,
        "maximum_rounds": maximum_rounds,
        "level_master_seconds_per_call": level_limits.master_seconds,
        "formal_candidate_result": False,
        "preregistration_published": False,
        "warm_start_selection_frozen": False,
        "joint_ac_solver_call_count": 0,
    }
    output_root.mkdir(parents=True, exist_ok=True)
    v4._write_exact_json(output_root / "summary.json", summary)
    _write_recursive_manifest(output_root)
    progress.emit(
        "repair_003_level_set_pilot_completed",
        status=bracketed.status,
        failure_reason=bracketed.failure_reason,
        relative_cost_budget_delta=0.0075,
        round_count=len(bracketed.round_checkpoints),
        lower_bound=bracketed.bracket.lower_bound,
        upper_bound=bracketed.bracket.upper_bound,
        maximum_acceptance_passed=bracketed.certificate["maximum_acceptance_passed"],
        formal_candidate_result=False,
        preregistration_published=False,
        warm_start_selection_frozen=False,
        joint_ac_solver_call_count=0,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", action="store_true")
    parser.add_argument("--prefix-reaudit", type=int)
    parser.add_argument("--pilot-delta-0p0075", action="store_true")
    parser.add_argument("--run-id", default="repair_003_control_smoke")
    args = parser.parse_args()
    selected = sum(
        (args.inventory, args.prefix_reaudit is not None, args.pilot_delta_0p0075)
    )
    if selected != 1:
        parser.error(
            "choose exactly one of --inventory, --prefix-reaudit, or "
            "--pilot-delta-0p0075"
        )
    if args.inventory:
        result = control_plane_inventory()
    elif args.prefix_reaudit is not None:
        result = run_prefix_reaudit_smoke(
            ordinal=int(args.prefix_reaudit), run_id=str(args.run_id)
        )
    else:
        result = run_delta_0p0075_level_set_pilot(run_id=str(args.run_id))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "HybridProxyResult",
    "ImportedPrefixCandidate",
    "PrefixExpectation",
    "RehydratedPrefixSnapshot",
    "control_plane_inventory",
    "level_evidence_from_stage_result",
    "run_hybrid_proxy_certificate",
    "run_delta_0p0075_level_set_pilot",
    "run_prefix_reaudit_smoke",
    "rehydrate_prefix_snapshot",
    "verify_candidate_four_upper_bound",
    "verify_predecessor_prefix",
]
