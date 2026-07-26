"""Generate and evaluate a preregistered zero-DC AC-aware commitment frontier."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import platform
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, fields, replace
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import yaml
import casadi as ca
from highspy import Highs
from pypower.idx_gen import QMAX, QMIN
from pyomo.environ import (
    Constraint,
    ConstraintList,
    Objective,
    SolverFactory,
    Var,
    maximize,
    value,
)
from pyomo.opt import TerminationCondition

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments import run_rts_gmlc_zero_dc_ac_step_control as step
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from experiments.run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended import (
    _configure_q_capable_voltage_control,
)
from experiments.run_rts_gmlc_zero_dc_ac_ipopt_diagnostic import (
    _verify_voltage_reference,
)
from experiments.run_rts_gmlc_zero_dc_normal_ac_control import (
    _build_context as _build_zero_context,
    _load_zero_dispatch,
    _require_preregistration as _require_zero_preregistration,
    _zero_request,
)
from src.grid.rts_gmlc_scuc import (
    RtsGmlcInitialState,
    _audit_solution,
    _build_context as _build_scuc_context,
    _build_model,
    _constraint_violation,
    _extract_branch_flows,
    _extract_commitment,
    _extract_dc_flows,
    _extract_generation,
    _integrality_violation,
    _solve,
    _validate_inputs,
    build_rts_gmlc_pre_registered_contingencies,
)
from src.grid.rts_gmlc_ac import reconstruct_rts_gmlc_dc_flows
from src.grid.rts_gmlc_ac_aware_commitment import (
    AcAwareChronology,
    AcAwareCommitmentResult,
    AcAwareCommitmentUnit,
    solve_ac_aware_commitment,
)
from src.grid.rts_gmlc_ac_ipopt import _FROZEN_IPOPT_OPTIONS
from src.grid.rts_gmlc_ac_recovery import prepare_rts_gmlc_ac_recovery
from src.grid.rts_gmlc_ac_step_control import (
    StepControlAudit,
    StepControlBranchRecord,
    StepControlBusRecord,
    StepControlGeneratorRecord,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml")
_ZERO_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_normal_ac_control.yaml")
_ZERO_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_normal_ac_control_v1"
)
_PRIMARY_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_recovery_v1/recovery"
)
_STEP_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_step_control_v1/step_control"
)
_IPOPT_V2_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v2"
)
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_zero_dc_ac_aware_commitment.py"),
    Path("src/grid/rts_gmlc_ac_aware_commitment.py"),
    Path("experiments/run_rts_gmlc_zero_dc_normal_ac_control.py"),
    Path("src/grid/rts_gmlc_scuc.py"),
    Path("src/grid/rts_gmlc_ac.py"),
    Path("src/grid/rts_gmlc_ac_recovery.py"),
    Path("src/grid/rts_gmlc_ac_step_control.py"),
    Path("src/grid/rts_gmlc_ac_ipopt.py"),
)
_EXPECTED_TOP_LEVEL_KEYS = {
    "preregistration",
    "protocol_amendment",
    "parent_zero_control",
    "observed_diagnostic_disclosure",
    "parent_diagnostics",
    "official_voltage_limit_reference",
    "candidate_frontier",
    "joint_ac",
    "independent_audit",
    "forbidden_adaptivity",
    "interpretation",
    "evidence",
    "output",
}
_CANDIDATE_FIELDS = (
    "requested_candidate_id",
    "candidate_id",
    "source",
    "relative_cost_budget_delta",
    "cost_budget_usd",
    "operating_cost_usd",
    "reactive_proxy_fraction",
    "commitment_sha256",
    "dispatch_sha256",
    "duplicate_of_candidate_id",
    "selected_unique_candidate",
)
_COMMITMENT_FIELDS = (
    "candidate_id",
    "hour_index",
    "timestamp",
    "generator_uid",
    "commitment",
    "startup",
    "shutdown",
)
_GENERATION_FIELDS = (
    "candidate_id",
    "hour_index",
    "timestamp",
    "generator_uid",
    "generation_mw",
)
_BRANCH_FIELDS = (
    "candidate_id",
    "hour_index",
    "timestamp",
    "branch_uid",
    "flow_mw",
)
_DC_FLOW_FIELDS = (
    "candidate_id",
    "hour_index",
    "timestamp",
    "dc_branch_uid",
    "flow_mw",
)
_RESERVE_FIELDS = (
    "candidate_id",
    "hour_index",
    "timestamp",
    "generator_uid",
    "reserve_up_mw",
)
_JOINT_RESULT_SCALAR_FIELDS = (
    "evaluated",
    "solver_success",
    "feasibility_witnessed",
    "return_status",
    "iterations",
    "initial_strategy",
    "normalized_objective",
    "independent_squared_target_deviation_mw2",
    "maximum_nlp_constraint_violation",
    "maximum_nlp_variable_bound_violation",
    "maximum_ramp_violation_mw",
    "maximum_reserve_bound_violation_mw",
    "maximum_reserve_headroom_violation_mw",
    "maximum_reserve_shortfall_mw",
    "solver_input_cases_unchanged",
)
_JOINT_RUN_FIELDS = (
    "candidate_id",
    "requested_candidate_id",
    "relative_cost_budget_delta",
    "operating_cost_usd",
    "reactive_proxy_fraction",
    "commitment_sha256",
    "dispatch_sha256",
    "joint_solution_sha256",
) + _JOINT_RESULT_SCALAR_FIELDS
_AUDIT_RECORD_FIELDS = {"generator_records", "bus_records", "branch_records"}
_AUDIT_SCALAR_FIELDS = tuple(
    field.name
    for field in fields(StepControlAudit)
    if field.name not in _AUDIT_RECORD_FIELDS
)
_JOINT_HOUR_FIELDS = (
    "candidate_id",
    "initial_strategy",
    "hour_index",
    "timestamp",
) + _AUDIT_SCALAR_FIELDS
_JOINT_GENERATOR_FIELDS = (
    "candidate_id",
    "initial_strategy",
    "hour_index",
    "timestamp",
) + tuple(field.name for field in fields(StepControlGeneratorRecord))
_JOINT_BUS_FIELDS = (
    "candidate_id",
    "initial_strategy",
    "hour_index",
    "timestamp",
) + tuple(field.name for field in fields(StepControlBusRecord))
_JOINT_BRANCH_FIELDS = (
    "candidate_id",
    "initial_strategy",
    "hour_index",
    "timestamp",
) + tuple(field.name for field in fields(StepControlBranchRecord))
_JOINT_RESERVE_FIELDS = (
    "candidate_id",
    "initial_strategy",
    "hour_index",
    "timestamp",
    "generator_uid",
    "reserve_up_mw",
)
_RESERVE_ELIGIBLE_CATEGORIES = (
    "Coal",
    "Gas CC",
    "Gas CT",
    "Oil CT",
    "Oil ST",
    "Solar PV",
    "Wind",
)
_EXPECTED_INDEPENDENT_AUDIT = {
    "nlp_constraint_tolerance": 1.0e-6,
    "nlp_variable_bound_tolerance": 1.0e-8,
    "active_power_bound_tolerance_mw": 1.0e-4,
    "reactive_power_bound_tolerance_mvar": 1.0e-4,
    "voltage_bound_tolerance_pu": 1.0e-6,
    "branch_loading_tolerance_fraction": 1.0e-6,
    "branch_angle_tolerance_degree": 1.0e-6,
    "fixed_generator_pg_tolerance_mw": 1.0e-6,
    "offline_pg_qg_tolerance_mw_mvar": 1.0e-6,
    "offline_branch_flow_tolerance_mva": 1.0e-6,
    "nodal_p_q_balance_tolerance_mw_mvar": 1.0e-4,
    "ybus_terminal_shunt_identity_tolerance_mva": 1.0e-6,
    "returned_recomputed_branch_flow_tolerance_mva": 1.0e-6,
    "reference_angle_tolerance_degree": 1.0e-6,
    "objective_absolute_tolerance_mw2": 1.0e-4,
    "objective_relative_tolerance": 1.0e-8,
    "ramp_tolerance_mw": 1.0e-6,
    "reserve_tolerance_mw": 1.0e-6,
}
_EXPECTED_INTERPRETATION = {
    "candidate_proxy_is_physical_feasibility_certificate": False,
    "candidate_proxy_is_economic_optimum_claim": False,
    "successful_claim": (
        "one_preregistered_24h_commitment_has_a_joint_normal_state_zero_dc_ac_"
        "numerical_feasibility_witness"
    ),
    "unsuccessful_claim": (
        "not_witnessed_by_registered_candidate_frontier_and_joint_local_solver_starts"
    ),
    "global_optimality_claimed": False,
    "global_infeasibility_claimed": False,
    "treatment_followup_gate": (
        "at_least_one_candidate_strategy_jointly_witnesses_all_24_hours"
    ),
    "treatment_execution_in_this_protocol": False,
}
_EXPECTED_EVIDENCE = {
    "evidence_status": "derived_benchmark",
    "result_evidence_ceiling": (
        "zero_dc_normal_state_ac_aware_commitment_joint_trajectory_diagnostic"
    ),
    "physical_envelope_has_response_time_evidence": False,
    "causal_poi_attribution_supported": False,
    "engineering_ac_parameters_available": False,
    "full_n_minus_one": False,
    "ac_security": False,
    "security_certified": False,
    "full_m6_model_input_ready": False,
    "formal_vma_published": False,
}
_EXPECTED_PROTOCOL_AMENDMENT = {
    "id": (
        "rts_gmlc_zero_dc_ac_aware_commitment_reference_bus_chronology_" "amendment_001"
    ),
    "schema": ("rts_gmlc_zero_dc_ac_aware_commitment_implementation_amendment_v1"),
    "parent_preregistration_id": (
        "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v1"
    ),
    "parent_config_path": (
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment.yaml"
    ),
    "parent_config_sha256": (
        "fee9870043b1269a0fea8cc9d8a38ca94bafa00cc6acc5c691b088962339b975"
    ),
    "parent_output_directory": (
        "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v1"
    ),
    "parent_input_contract_sha256": (
        "2892a459137998fe7825acafc2391d9367f9cbfb66dcaeb2dc5c06f0a49237e8"
    ),
    "parent_preregistration_manifest_sha256": (
        "1aa4763bb72e89bbad03deeed7ebc837ff1a3620baa5ba39b409203531c8beae"
    ),
    "parent_invalidation_manifest_sha256": (
        "7ac6a6a2ecc76304376654b36d6a0e83e5bd506e9f3ff537356fa13ad94ac3dd"
    ),
    "parent_ac_aware_core_sha256": (
        "1e236963042bbe5818c08381a0110162f642a864ff92c4a05e7cfc2949e6e48e"
    ),
    "corrected_ac_aware_core_sha256": (
        "bdd106e00bf1750b8867e9e3127c797054aa6f8ca9456821c4eb252ddf93d824"
    ),
    "failure_detected_by_pre_solver_input_validation": True,
    "failure": (
        "BUS_TYPE_was_incorrectly_required_to_be_cross_hour_static_even_though_"
        "reference_and_voltage_controller_bus_types_follow_hourly_commitment"
    ),
    "permitted_correction": (
        "exclude_BUS_TYPE_from_cross_hour_static_equality_and_require_each_hour_"
        "to_use_only_PQ_PV_REF_with_exactly_one_REF"
    ),
    "parent_candidate_generation_invocation_started": True,
    "parent_candidate_frontier_artifact_published": False,
    "parent_candidate_frontier_outcomes_available_to_amendment_design": False,
    "parent_joint_ac_solver_call_count": 0,
    "parent_joint_ac_outcomes_observed": False,
    "candidate_budget_grid_changed": False,
    "candidate_objectives_changed": False,
    "joint_ac_envelope_changed": False,
    "joint_ac_initial_strategies_changed": False,
}


@dataclass(frozen=True)
class _FrontierContext:
    config_path: Path
    config: dict[str, Any]
    zero: Any
    request: Any
    initial_state: RtsGmlcInitialState
    selection: Any
    q_limits_by_uid: dict[str, tuple[float, float]]
    output_root: Path
    input_contract: dict[str, Any]
    input_contract_sha256: str


@dataclass(frozen=True)
class _Candidate:
    requested_candidate_id: str
    source: str
    relative_cost_budget_delta: float
    cost_budget_usd: float
    operating_cost_usd: float
    reactive_proxy_fraction: float
    commitment_sha256: str
    dispatch_sha256: str
    commitment: tuple[dict[str, bool], ...]
    startup: tuple[dict[str, bool], ...]
    shutdown: tuple[dict[str, bool], ...]
    generation_mw: tuple[dict[str, float], ...]
    branch_flows_mw: tuple[dict[str, float], ...]
    dc_flows_mw: tuple[dict[str, float], ...]
    reserve_up_mw: tuple[dict[str, float], ...]
    stage_audits: dict[str, object]
    residual_audit: dict[str, object]


@dataclass(frozen=True)
class _LoadedCandidate:
    candidate_id: str
    requested_candidate_id: str
    relative_cost_budget_delta: float
    operating_cost_usd: float
    reactive_proxy_fraction: float
    commitment_sha256: str
    dispatch_sha256: str
    commitment: tuple[dict[str, bool], ...]
    startup: tuple[dict[str, bool], ...]
    shutdown: tuple[dict[str, bool], ...]
    generation_mw: tuple[dict[str, float], ...]
    branch_flows_mw: tuple[dict[str, float], ...]
    dc_flows_mw: tuple[dict[str, float], ...]


def _read_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _EXPECTED_TOP_LEVEL_KEYS:
        raise ValueError("RTS-GMLC AC-aware commitment config schema drifted")
    preregistration = config["preregistration"]
    if (
        not isinstance(preregistration, dict)
        or preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2"
        or preregistration.get("schema")
        != "rts_gmlc_zero_dc_ac_aware_commitment_preregistration_v2"
        or preregistration.get("candidate_frontier_outcomes_observed") is not False
        or preregistration.get("joint_ac_outcomes_observed") is not False
    ):
        raise ValueError("RTS-GMLC AC-aware preregistration drifted")
    if config["protocol_amendment"] != _EXPECTED_PROTOCOL_AMENDMENT:
        raise ValueError("RTS-GMLC AC-aware protocol amendment drifted")
    frontier = config["candidate_frontier"]
    deltas = tuple(float(item) for item in frontier["relative_cost_budget_deltas"])
    if (
        deltas != (0.001, 0.0025, 0.005, 0.01, 0.02, 0.05)
        or tuple(frontier["areas"]) != (1, 2, 3)
        or int(frontier["expected_hours"]) != 24
        or int(frontier["selected_n_minus_one_state_count_per_hour"]) != 24
        or frontier["candidate_generation_uses_ac_outcomes"] is not False
        or frontier["candidate_generation_completed_before_any_joint_ac_solve"]
        is not True
        or frontier["all_budget_candidates_completed_before_deduplication"] is not True
        or frontier["duplicate_rule"]
        != "commitment_sha256_keep_lowest_cost_then_lowest_budget"
    ):
        raise ValueError("RTS-GMLC AC-aware candidate frontier drifted")
    joint = config["joint_ac"]
    if (
        joint["engine"] != "casadi_nlpsol_ipopt"
        or int(joint["expected_hours"]) != 24
        or tuple(joint["initial_strategies"])
        != ("source", "midpoint", "flat_target_midq")
        or joint["all_candidates_and_strategies_run_no_early_stop"] is not True
        or joint["one_solver_call_per_candidate_strategy"] is not True
        or tuple(float(item) for item in joint["voltage_limits_pu"]) != (0.95, 1.05)
        or float(joint["voltage_bound_expansion_pu"]) != 0.0
        or float(joint["reactive_power_bound_expansion_mvar"]) != 0.0
        or float(joint["branch_rate_multiplier"]) != 1.0
        or joint["branch_rating"] != "RATE_A_mva_proxy"
        or joint["retry_or_fallback_allowed"] is not False
        or joint["per_hour_method_selection_allowed"] is not False
        or joint["same_commitment_and_joint_pg_trajectory_required"] is not True
        or joint["normal_state_only"] is not True
        or joint["branch_angle_limits_enforced"] is not True
        or joint["active_power_ramp_constraints_enforced"] is not True
        or joint["regional_spin_headroom_constraints_enforced"] is not True
        or joint["reserve_provider_scope"]
        != "online_committable_units_in_original_spin_categories_conservative_subset"
        or tuple(joint["reserve_eligible_categories"]) != _RESERVE_ELIGIBLE_CATEGORIES
        or joint["objective"]
        != "sum_squared_adjustable_pg_deviation_divided_by_base_mva_squared"
        or dict(joint["ipopt_options"]) != _FROZEN_IPOPT_OPTIONS
    ):
        raise ValueError("RTS-GMLC AC-aware joint AC contract drifted")
    if config["independent_audit"] != _EXPECTED_INDEPENDENT_AUDIT:
        raise ValueError("RTS-GMLC AC-aware independent audit contract drifted")
    if config["interpretation"] != _EXPECTED_INTERPRETATION:
        raise ValueError("RTS-GMLC AC-aware interpretation contract drifted")
    if config["evidence"] != _EXPECTED_EVIDENCE:
        raise ValueError("RTS-GMLC AC-aware evidence contract drifted")
    if any(bool(value) for value in config["forbidden_adaptivity"].values()):
        raise ValueError("RTS-GMLC AC-aware forbidden adaptivity was enabled")
    return config


def _verify_file_hash(path: Path, expected: str, *, label: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise RuntimeError(f"RTS-GMLC AC-aware {label} hash drifted")


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC AC-aware artifact {root / name} drifted")
    return payload


def _verify_protocol_amendment(config: Mapping[str, Any]) -> None:
    amendment = config["protocol_amendment"]
    parent_root = Path(amendment["parent_output_directory"])
    _verify_file_hash(
        Path(amendment["parent_config_path"]),
        amendment["parent_config_sha256"],
        label="protocol amendment parent config",
    )
    _verify_file_hash(
        Path("src/grid/rts_gmlc_ac_aware_commitment.py"),
        amendment["corrected_ac_aware_core_sha256"],
        label="protocol amendment corrected core",
    )
    for root, expected, label in (
        (
            parent_root / "preregistration",
            amendment["parent_preregistration_manifest_sha256"],
            "parent preregistration",
        ),
        (
            parent_root / "invalidation",
            amendment["parent_invalidation_manifest_sha256"],
            "parent invalidation",
        ),
    ):
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != expected:
            raise RuntimeError(f"RTS-GMLC AC-aware {label} manifest drifted")
    invalidation = _load_json(parent_root / "invalidation", "invalidation.json")
    if (
        invalidation.get("parent_input_contract_sha256")
        != amendment["parent_input_contract_sha256"]
        or invalidation.get("candidate_frontier_artifact_published") is not False
        or invalidation.get("joint_ac_solver_call_count") != 0
        or invalidation.get("joint_ac_outcomes_observed") is not False
    ):
        raise RuntimeError("RTS-GMLC AC-aware parent invalidation drifted")
    if (parent_root / "candidate_frontier").exists() or (
        parent_root / "joint_ac"
    ).exists():
        raise RuntimeError("RTS-GMLC AC-aware invalidated parent gained results")


def _format_value(value_: object) -> str:
    if isinstance(value_, bool):
        return str(value_).lower()
    if isinstance(value_, float):
        return format(value_, ".17g")
    if value_ is None:
        return ""
    return str(value_)


def _write_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows: Sequence[Mapping[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row[field]) for field in fieldnames})


def _write_exact_json(path: Path, payload: object) -> None:
    path.write_bytes(
        (json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )


def _software_versions() -> dict[str, str]:
    result = {"python": platform.python_version(), "platform": platform.platform()}
    for package in (
        "casadi",
        "highspy",
        "numpy",
        "pyomo",
        "pypower",
        "pyyaml",
        "scipy",
    ):
        result[package] = importlib.metadata.version(package)
    return result


def _verified_casadi_identity(config: Mapping[str, Any]) -> dict[str, object]:
    python_path = Path(ca.__file__)
    binary = __import__("casadi._casadi", fromlist=["__file__"])
    binary_path = Path(binary.__file__)
    identity = {
        "version": importlib.metadata.version("casadi"),
        "python_sha256": _sha256(python_path),
        "binary_sha256": _sha256(binary_path),
        "build_type": ca.CasadiMeta_build_type(),
        "compiler_id": ca.CasadiMeta_compiler_id(),
    }
    joint = config["joint_ac"]
    if (
        identity["version"] != joint["casadi_version"]
        or identity["python_sha256"] != joint["casadi_python_sha256"]
        or identity["binary_sha256"] != joint["casadi_binary_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware CasADi identity drifted")
    return identity


def _load_initial_state() -> RtsGmlcInitialState:
    path = _ZERO_OUTPUT_ROOT / "dc_dispatch" / "initial_state.csv"
    with path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows or tuple(rows[0]) != (
        "generator_uid",
        "commitment",
        "generation_mw",
        "time_in_state_hours",
        "source_scope",
    ):
        raise RuntimeError("RTS-GMLC AC-aware initial-state schema drifted")
    scopes = {row["source_scope"] for row in rows}
    if scopes != {"optimization_derived_free_boundary_not_observed_chronology"}:
        raise RuntimeError("RTS-GMLC AC-aware initial-state scope drifted")
    return RtsGmlcInitialState(
        commitment={row["generator_uid"]: row["commitment"] == "true" for row in rows},
        generation_mw={
            row["generator_uid"]: float(row["generation_mw"]) for row in rows
        },
        time_in_state_hours={
            row["generator_uid"]: float(row["time_in_state_hours"]) for row in rows
        },
        source_scope=scopes.pop(),
    )


def _verify_parent_artifacts(config: Mapping[str, Any], zero: Any) -> None:
    parent = config["parent_zero_control"]
    for path_key, hash_key in (
        ("config_path", "config_sha256"),
        ("runner_path", "runner_sha256"),
        ("scuc_core_path", "scuc_core_sha256"),
        ("ac_core_path", "ac_core_sha256"),
    ):
        _verify_file_hash(Path(parent[path_key]), parent[hash_key], label=path_key)
    for subdirectory, key in (
        ("preregistration", "preregistration_manifest_sha256"),
        ("dc_dispatch", "dc_dispatch_manifest_sha256"),
        ("ac_normal", "ac_normal_manifest_sha256"),
    ):
        root = _ZERO_OUTPUT_ROOT / subdirectory
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != parent[key]:
            raise RuntimeError(f"RTS-GMLC AC-aware zero parent {subdirectory} drifted")
    _require_zero_preregistration(zero, _ZERO_OUTPUT_ROOT)
    _load_zero_dispatch(zero, _ZERO_OUTPUT_ROOT)
    summary = _load_json(_ZERO_OUTPUT_ROOT / "dc_dispatch", "summary.json")
    if summary.get("input_contract_sha256") != parent[
        "input_contract_sha256"
    ] or not math.isclose(
        float(summary["fixed_commitment_ed_audit"]["objective_usd"]),
        float(parent["baseline_full_state_cost_usd"]),
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise RuntimeError("RTS-GMLC AC-aware zero parent summary drifted")
    diagnostics = config["parent_diagnostics"]
    for root, key in (
        (_PRIMARY_OUTPUT_ROOT, "primary_560_result_manifest_sha256"),
        (_STEP_OUTPUT_ROOT, "step_control_565_result_manifest_sha256"),
        (
            _IPOPT_V2_ROOT / "preregistration",
            "ipopt_v2_preregistration_manifest_sha256",
        ),
        (_IPOPT_V2_ROOT / "ipopt_diagnostic", "ipopt_v2_result_manifest_sha256"),
    ):
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != diagnostics[key]:
            raise RuntimeError(f"RTS-GMLC AC-aware diagnostic parent {key} drifted")


def _build_context(config_path: Path) -> _FrontierContext:
    config = _read_config(config_path)
    _verify_protocol_amendment(config)
    zero = _build_zero_context(_ZERO_CONFIG_PATH)
    _verify_parent_artifacts(config, zero)
    initial_state = _load_initial_state()
    request = replace(
        _zero_request(zero),
        initial_commitment=dict(initial_state.commitment),
        initial_generation_mw=dict(initial_state.generation_mw),
        initial_time_in_state_hours=dict(initial_state.time_in_state_hours),
    )
    security = zero.common_security["common_security_contract"]
    selection = build_rts_gmlc_pre_registered_contingencies(
        zero.scan.data,
        branch_uids=tuple(security["branch_uids"]),
        generator_uids=tuple(security["generator_uids"]),
    )
    if len(selection.states) != int(
        config["candidate_frontier"]["selected_n_minus_one_state_count_per_hour"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware selected-state count drifted")
    template = zero.ac.template
    q_limits = {
        uid: (
            float(template.case_template["gen"][row, QMIN]),
            float(template.case_template["gen"][row, QMAX]),
        )
        for uid, row in template.generator_row_by_uid.items()
    }
    voltage_reference = _verify_voltage_reference(config)
    casadi_identity = _verified_casadi_identity(config)
    contract = {
        "schema": "rts_gmlc_zero_dc_ac_aware_commitment_inputs_v2",
        "config_sha256": _sha256(config_path),
        "protocol_amendment": config["protocol_amendment"],
        "parent_zero_control": config["parent_zero_control"],
        "observed_diagnostic_disclosure": config["observed_diagnostic_disclosure"],
        "parent_diagnostics": config["parent_diagnostics"],
        "official_voltage_limit_reference": config["official_voltage_limit_reference"],
        "verified_voltage_reference": voltage_reference,
        "candidate_frontier": config["candidate_frontier"],
        "joint_ac": config["joint_ac"],
        "casadi_identity": casadi_identity,
        "independent_audit": config["independent_audit"],
        "forbidden_adaptivity": config["forbidden_adaptivity"],
        "interpretation": config["interpretation"],
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "software_versions": _software_versions(),
        "evidence": config["evidence"],
    }
    return _FrontierContext(
        config_path=config_path,
        config=config,
        zero=zero,
        request=request,
        initial_state=initial_state,
        selection=selection,
        q_limits_by_uid=q_limits,
        output_root=Path(config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: _FrontierContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    target = output_root / "preregistration"
    preregistration = context.config["preregistration"]
    payload = {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "previous_ac_outcomes_observed": True,
        "candidate_frontier_outcomes_observed": False,
        "joint_ac_outcomes_observed": False,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC AC-aware registration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC AC-aware config drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare beside existing AC-aware artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _FrontierContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    registration = _load_json(target, "registration.json")
    if registration.get("input_contract") != _stable_json(context.input_contract):
        raise RuntimeError("RTS-GMLC AC-aware live inputs drifted")
    if registration.get("input_contract_sha256") != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC AC-aware live contract SHA drifted")
    if (target / "config.yaml").read_bytes() != context.config_path.read_bytes():
        raise RuntimeError("RTS-GMLC AC-aware live config drifted")
    return registration


def _boolean_transitions(
    commitment: Sequence[Mapping[str, bool]],
    initial: Mapping[str, bool],
) -> tuple[tuple[dict[str, bool], ...], tuple[dict[str, bool], ...]]:
    startup = []
    shutdown = []
    previous = dict(initial)
    for row in commitment:
        if set(row) != set(previous):
            raise RuntimeError("RTS-GMLC AC-aware commitment UID coverage drifted")
        startup.append({uid: bool(row[uid] and not previous[uid]) for uid in row})
        shutdown.append({uid: bool(previous[uid] and not row[uid]) for uid in row})
        previous = dict(row)
    return tuple(startup), tuple(shutdown)


def _commitment_sha256(commitment: Sequence[Mapping[str, bool]]) -> str:
    return common_input_signature_sha256(
        {
            "schema": "rts_gmlc_24h_commitment_identity_v1",
            "hours": [dict(sorted(row.items())) for row in commitment],
        }
    )


def _dispatch_sha256(
    generation: Sequence[Mapping[str, float]],
    branch_flows: Sequence[Mapping[str, float]],
    dc_flows: Sequence[Mapping[str, float]],
) -> str:
    return common_input_signature_sha256(
        {
            "schema": "rts_gmlc_24h_dc_dispatch_identity_v1",
            "generation_mw": [dict(sorted(row.items())) for row in generation],
            "branch_flows_mw": [dict(sorted(row.items())) for row in branch_flows],
            "dc_flows_mw": [dict(sorted(row.items())) for row in dc_flows],
        }
    )


def _active_fixed_q_capability(
    generator: Any, qmin: float, qmax: float
) -> tuple[float, float]:
    if generator.unit_type == "SYNC_COND":
        active = True
    elif not generator.enabled:
        active = False
    else:
        active = generator.dispatch_mode != "committable"
    return (
        max(qmax, 0.0) if active else 0.0,
        max(-qmin, 0.0) if active else 0.0,
    )


def _proxy_components(context: _FrontierContext, points: Sequence[Any]):
    data = context.zero.scan.data
    generators = {generator.uid: generator for generator in data.generators}
    area_by_bus = {int(bus.uid): int(bus.area) for bus in data.buses}
    areas = tuple(int(area) for area in context.config["candidate_frontier"]["areas"])
    fixed = {area: [0.0, 0.0] for area in areas}
    variable: dict[int, dict[str, tuple[float, float]]] = {area: {} for area in areas}
    for uid, generator in generators.items():
        area = area_by_bus[int(generator.bus)]
        if area not in fixed:
            continue
        qmin, qmax = context.q_limits_by_uid[uid]
        up = max(qmax, 0.0)
        down = max(-qmin, 0.0)
        if generator.dispatch_mode == "committable":
            variable[area][uid] = (up, down)
        else:
            fixed_up, fixed_down = _active_fixed_q_capability(generator, qmin, qmax)
            fixed[area][0] += fixed_up
            fixed[area][1] += fixed_down
    denominators = []
    for time, point in enumerate(points):
        per_area = {}
        for area in areas:
            available = [fixed[area][0], fixed[area][1]]
            for uid, (up, down) in variable[area].items():
                if float(point.generator_max_mw[uid]) > 0.0:
                    available[0] += up
                    available[1] += down
            if min(available) <= 0.0:
                raise RuntimeError(
                    f"RTS-GMLC AC-aware area {area} hour {time} lacks bidirectional Q capability"
                )
            per_area[area] = tuple(available)
        denominators.append(per_area)
    return fixed, variable, tuple(denominators)


def _reactive_proxy_value(
    context: _FrontierContext,
    points: Sequence[Any],
    commitment: Sequence[Mapping[str, bool]],
) -> float:
    fixed, variable, denominators = _proxy_components(context, points)
    values = []
    for time, row in enumerate(commitment):
        for area in denominators[time]:
            for direction in (0, 1):
                numerator = fixed[area][direction] + sum(
                    capability[direction] * float(row[uid])
                    for uid, capability in variable[area].items()
                )
                values.append(numerator / denominators[time][area][direction])
    return min(values)


def _solver_options(frontier: Mapping[str, Any]) -> dict[str, float | int]:
    solver = frontier["solver"]
    return {
        "mip_rel_gap": float(solver["mip_relative_gap"]),
        "mip_abs_gap": 0.0,
        "random_seed": int(solver["random_seed"]),
        "threads": int(solver["threads"]),
        "primal_feasibility_tolerance": float(solver["feasibility_tolerance"]),
        "dual_feasibility_tolerance": float(solver["feasibility_tolerance"]),
        "mip_feasibility_tolerance": float(solver["feasibility_tolerance"]),
    }


def _solve_proxy_stage(model: Any, frontier: Mapping[str, Any]) -> dict[str, object]:
    solver_config = frontier["solver"]
    solver = SolverFactory(str(solver_config["name"]))
    if not solver.available(exception_flag=False):
        raise RuntimeError("RTS-GMLC AC-aware candidate solver is unavailable")
    Highs.resetGlobalScheduler(True)
    results = solver.solve(
        model,
        load_solutions=False,
        tee=False,
        options=_solver_options(frontier),
    )
    termination = results.solver.termination_condition
    if termination not in {
        TerminationCondition.optimal,
        TerminationCondition.globallyOptimal,
    }:
        raise RuntimeError(
            f"RTS-GMLC AC-aware proxy stage was not optimal: {termination}"
        )
    model.solutions.load_from(results)
    lower = float(results.problem.lower_bound)
    upper = float(results.problem.upper_bound)
    proxy = float(value(model.reactive_proxy))
    constraint_violation = float(_constraint_violation(model))
    integrality_violation = float(_integrality_violation(model))
    tolerance = float(solver_config["feasibility_tolerance"])
    gap = abs(upper - lower)
    gap_tolerance = max(
        tolerance,
        float(solver_config["mip_relative_gap"]) * max(abs(lower), abs(upper), 1.0),
    )
    if (
        not all(
            math.isfinite(item)
            for item in (
                lower,
                upper,
                proxy,
                constraint_violation,
                integrality_violation,
            )
        )
        or gap > gap_tolerance
        or constraint_violation > tolerance
        or integrality_violation > tolerance
    ):
        raise RuntimeError("RTS-GMLC AC-aware proxy-stage audit failed")
    return {
        "termination_condition": str(termination),
        "solver_status": str(results.solver.status),
        "proxy_fraction": proxy,
        "lower_bound": lower,
        "upper_bound": upper,
        "absolute_gap": gap,
        "gap_tolerance": gap_tolerance,
        "maximum_constraint_violation": constraint_violation,
        "maximum_integrality_violation": integrality_violation,
    }


def _extract_reserve(model: Any, scuc_context: Any) -> tuple[dict[str, float], ...]:
    return tuple(
        {
            uid: float(value(model.reserve_up[time, uid]))
            for uid in scuc_context.reserve_uids
        }
        for time in range(len(scuc_context.points))
    )


def _solve_frontier_candidate(
    context: _FrontierContext,
    *,
    relative_delta: float,
) -> _Candidate:
    frontier = context.config["candidate_frontier"]
    tolerance = float(frontier["solver"]["feasibility_tolerance"])
    points = _validate_inputs(context.zero.scan.data, context.request, tolerance)
    scuc_context = _build_scuc_context(
        context.zero.scan.data,
        context.request,
        points,
        context.selection.states,
    )
    model = _build_model(scuc_context, fixed_initial=context.initial_state)
    baseline_cost = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    cost_budget = baseline_cost * (1.0 + relative_delta)
    model.cost_cap = Constraint(
        expr=model.operating_cost
        <= cost_budget + float(frontier["cost_cap_absolute_tolerance_usd"])
    )
    fixed, variable, denominators = _proxy_components(context, points)
    model.reactive_proxy = Var(bounds=(0.0, 1.0))
    model.reactive_proxy_constraints = ConstraintList()
    for time in range(len(points)):
        for area in denominators[time]:
            for direction in (0, 1):
                numerator = fixed[area][direction] + sum(
                    capability[direction] * model.commitment[time, uid]
                    for uid, capability in variable[area].items()
                )
                model.reactive_proxy_constraints.add(
                    model.reactive_proxy
                    <= numerator / denominators[time][area][direction]
                )
    model.objective.deactivate()
    model.reactive_proxy_objective = Objective(
        expr=model.reactive_proxy, sense=maximize
    )
    proxy_audit = _solve_proxy_stage(model, frontier)
    proxy_target = float(value(model.reactive_proxy))
    model.reactive_proxy_floor = Constraint(
        expr=model.reactive_proxy
        >= proxy_target - float(frontier["proxy_floor_absolute_tolerance"])
    )
    model.reactive_proxy_objective.deactivate()
    model.objective.activate()
    cost_audit = _solve(
        model,
        solver_name=str(frontier["solver"]["name"]),
        tee=False,
        tolerance=tolerance,
        solver_threads=int(frontier["solver"]["threads"]),
        mip_relative_gap=float(frontier["solver"]["mip_relative_gap"]),
    )
    if not cost_audit.accepted or cost_audit.objective_usd is None:
        raise RuntimeError("RTS-GMLC AC-aware cost-normalization stage failed")
    residual = _audit_solution(model, scuc_context, context.initial_state, tolerance)
    flags = (
        residual.commitment_feasible_by_step
        + residual.ramp_feasible_by_step
        + residual.reserve_feasible_by_step
        + residual.normal_secure_by_step
        + residual.contingency_secure_by_step
    )
    if not all(flags):
        raise RuntimeError("RTS-GMLC AC-aware candidate DC audit failed")
    commitment = _extract_commitment(model, scuc_context)
    generation = _extract_generation(model, scuc_context, "normal")
    branch_flows = _extract_branch_flows(model, scuc_context, "normal")
    dc_flows = _extract_dc_flows(model, scuc_context, "normal")
    reserve = _extract_reserve(model, scuc_context)
    startup, shutdown = _boolean_transitions(
        commitment, context.initial_state.commitment
    )
    proxy_value = _reactive_proxy_value(context, points, commitment)
    if proxy_value + float(frontier["proxy_floor_absolute_tolerance"]) < proxy_target:
        raise RuntimeError("RTS-GMLC AC-aware reactive proxy reconstruction drifted")
    operating_cost = float(cost_audit.objective_usd)
    if operating_cost > cost_budget + float(
        frontier["cost_cap_absolute_tolerance_usd"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate exceeded its cost budget")
    requested_id = "q_proxy_delta_" + format(relative_delta, ".4f").replace(".", "p")
    return _Candidate(
        requested_candidate_id=requested_id,
        source="q_proxy_full_selected_n1_dc_scuc",
        relative_cost_budget_delta=relative_delta,
        cost_budget_usd=cost_budget,
        operating_cost_usd=operating_cost,
        reactive_proxy_fraction=proxy_value,
        commitment_sha256=_commitment_sha256(commitment),
        dispatch_sha256=_dispatch_sha256(generation, branch_flows, dc_flows),
        commitment=commitment,
        startup=startup,
        shutdown=shutdown,
        generation_mw=generation,
        branch_flows_mw=branch_flows,
        dc_flows_mw=dc_flows,
        reserve_up_mw=reserve,
        stage_audits={
            "proxy_maximization": proxy_audit,
            "cost_normalization": asdict(cost_audit),
        },
        residual_audit=asdict(residual),
    )


def _baseline_candidate(context: _FrontierContext) -> _Candidate:
    hourly, generation, commitment, branch_flows = _load_zero_dispatch(
        context.zero, _ZERO_OUTPUT_ROOT
    )
    timestamps = tuple(
        point.timestamp.isoformat() for point in context.zero.zero_business.points
    )
    commitment_rows = tuple(commitment[timestamp] for timestamp in timestamps)
    generation_rows = tuple(generation[timestamp] for timestamp in timestamps)
    branch_rows = tuple(branch_flows[timestamp] for timestamp in timestamps)
    dc_rows = tuple({"DC1": float(row["hvdc_dc1_flow_mw"])} for row in hourly)
    reserve_by_timestamp: dict[str, dict[str, float]] = {}
    reserve_path = _ZERO_OUTPUT_ROOT / "dc_dispatch" / "generator_dispatch.csv"
    with reserve_path.open("r", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            reserve_by_timestamp.setdefault(row["timestamp"], {})[
                row["generator_uid"]
            ] = float(row["spin_up_mw"])
    reserve_rows = tuple(reserve_by_timestamp[timestamp] for timestamp in timestamps)
    startup, shutdown = _boolean_transitions(
        commitment_rows, context.initial_state.commitment
    )
    summary = _load_json(_ZERO_OUTPUT_ROOT / "dc_dispatch", "summary.json")
    points = _validate_inputs(
        context.zero.scan.data,
        context.request,
        float(context.config["candidate_frontier"]["solver"]["feasibility_tolerance"]),
    )
    baseline_cost = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    return _Candidate(
        requested_candidate_id="parent_zero_dc_selected_n1_dispatch",
        source="frozen_parent_zero_dc_dispatch",
        relative_cost_budget_delta=0.0,
        cost_budget_usd=baseline_cost,
        operating_cost_usd=baseline_cost,
        reactive_proxy_fraction=_reactive_proxy_value(context, points, commitment_rows),
        commitment_sha256=_commitment_sha256(commitment_rows),
        dispatch_sha256=_dispatch_sha256(generation_rows, branch_rows, dc_rows),
        commitment=commitment_rows,
        startup=startup,
        shutdown=shutdown,
        generation_mw=generation_rows,
        branch_flows_mw=branch_rows,
        dc_flows_mw=dc_rows,
        reserve_up_mw=reserve_rows,
        stage_audits={
            "frozen_parent_scuc": summary["scuc_audit"],
            "frozen_parent_fixed_commitment_ed": summary["fixed_commitment_ed_audit"],
        },
        residual_audit=summary["residual_audit"],
    )


def _deduplicate_candidates(
    candidates: Sequence[_Candidate],
) -> tuple[list[dict[str, object]], list[tuple[str, _Candidate]]]:
    grouped: dict[str, list[_Candidate]] = {}
    for candidate in candidates:
        grouped.setdefault(candidate.commitment_sha256, []).append(candidate)
    winners = {
        key: min(
            values,
            key=lambda item: (
                item.operating_cost_usd,
                item.relative_cost_budget_delta,
                item.requested_candidate_id,
            ),
        )
        for key, values in grouped.items()
    }
    ordered_winners = sorted(
        winners.values(),
        key=lambda item: (
            item.relative_cost_budget_delta,
            item.operating_cost_usd,
            item.commitment_sha256,
        ),
    )
    candidate_id_by_requested = {
        candidate.requested_candidate_id: f"candidate_{index:02d}"
        for index, candidate in enumerate(ordered_winners)
    }
    winner_id_by_hash = {
        candidate.commitment_sha256: candidate_id_by_requested[
            candidate.requested_candidate_id
        ]
        for candidate in ordered_winners
    }
    rows = []
    for candidate in candidates:
        winner = winners[candidate.commitment_sha256]
        selected = candidate.requested_candidate_id == winner.requested_candidate_id
        winner_id = winner_id_by_hash[candidate.commitment_sha256]
        rows.append(
            {
                "requested_candidate_id": candidate.requested_candidate_id,
                "candidate_id": winner_id if selected else "",
                "source": candidate.source,
                "relative_cost_budget_delta": candidate.relative_cost_budget_delta,
                "cost_budget_usd": candidate.cost_budget_usd,
                "operating_cost_usd": candidate.operating_cost_usd,
                "reactive_proxy_fraction": candidate.reactive_proxy_fraction,
                "commitment_sha256": candidate.commitment_sha256,
                "dispatch_sha256": candidate.dispatch_sha256,
                "duplicate_of_candidate_id": "" if selected else winner_id,
                "selected_unique_candidate": selected,
            }
        )
    selected_candidates = [
        (candidate_id_by_requested[candidate.requested_candidate_id], candidate)
        for candidate in ordered_winners
    ]
    return rows, selected_candidates


def _candidate_detail_rows(
    selected: Sequence[tuple[str, _Candidate]],
    timestamps: Sequence[str],
):
    commitment_rows = []
    generation_rows = []
    branch_rows = []
    dc_rows = []
    reserve_rows = []
    audits = {}
    for candidate_id, candidate in selected:
        audits[candidate_id] = {
            "requested_candidate_id": candidate.requested_candidate_id,
            "stage_audits": candidate.stage_audits,
            "residual_audit": candidate.residual_audit,
        }
        for hour, timestamp in enumerate(timestamps):
            for uid in sorted(candidate.commitment[hour]):
                commitment_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "hour_index": hour,
                        "timestamp": timestamp,
                        "generator_uid": uid,
                        "commitment": candidate.commitment[hour][uid],
                        "startup": candidate.startup[hour][uid],
                        "shutdown": candidate.shutdown[hour][uid],
                    }
                )
            for uid in sorted(candidate.generation_mw[hour]):
                generation_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "hour_index": hour,
                        "timestamp": timestamp,
                        "generator_uid": uid,
                        "generation_mw": candidate.generation_mw[hour][uid],
                    }
                )
            for uid in sorted(candidate.branch_flows_mw[hour]):
                branch_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "hour_index": hour,
                        "timestamp": timestamp,
                        "branch_uid": uid,
                        "flow_mw": candidate.branch_flows_mw[hour][uid],
                    }
                )
            for uid in sorted(candidate.dc_flows_mw[hour]):
                dc_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "hour_index": hour,
                        "timestamp": timestamp,
                        "dc_branch_uid": uid,
                        "flow_mw": candidate.dc_flows_mw[hour][uid],
                    }
                )
            for uid in sorted(candidate.reserve_up_mw[hour]):
                reserve_rows.append(
                    {
                        "candidate_id": candidate_id,
                        "hour_index": hour,
                        "timestamp": timestamp,
                        "generator_uid": uid,
                        "reserve_up_mw": candidate.reserve_up_mw[hour][uid],
                    }
                )
    return commitment_rows, generation_rows, branch_rows, dc_rows, reserve_rows, audits


def generate_candidate_frontier(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "candidate_frontier"
    if target.exists():
        return _load_json(target, "summary.json")
    if (output_root / "joint_ac").exists():
        raise RuntimeError("Cannot generate candidates after joint AC has started")
    candidates = [_baseline_candidate(context)]
    for delta in context.config["candidate_frontier"]["relative_cost_budget_deltas"]:
        candidates.append(
            _solve_frontier_candidate(context, relative_delta=float(delta))
        )
    rows, selected = _deduplicate_candidates(candidates)
    timestamps = tuple(
        timestamp.isoformat() for timestamp in context.request.timestamps
    )
    details = _candidate_detail_rows(selected, timestamps)
    summary = {
        "schema": "rts_gmlc_zero_dc_ac_aware_candidate_frontier_v2",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "requested_candidate_count": len(candidates),
        "unique_candidate_count": len(selected),
        "all_budget_candidates_completed_before_deduplication": True,
        "candidate_generation_completed_before_any_joint_ac_solve": True,
        "candidate_generation_uses_ac_outcomes": False,
        "relative_cost_budget_deltas": context.config["candidate_frontier"][
            "relative_cost_budget_deltas"
        ],
        "candidate_ids": [candidate_id for candidate_id, _candidate in selected],
        "commitment_sha256s": [
            candidate.commitment_sha256 for _candidate_id, candidate in selected
        ],
        "minimum_reactive_proxy_fraction": min(
            candidate.reactive_proxy_fraction for _candidate_id, candidate in selected
        ),
        "maximum_reactive_proxy_fraction": max(
            candidate.reactive_proxy_fraction for _candidate_id, candidate in selected
        ),
        "joint_ac_solver_call_count": 0,
        **context.config["evidence"],
    }

    def writer(staging: Path) -> None:
        _write_csv(staging / "candidates.csv", _CANDIDATE_FIELDS, rows)
        _write_csv(staging / "commitment.csv", _COMMITMENT_FIELDS, details[0])
        _write_csv(staging / "normal_generation.csv", _GENERATION_FIELDS, details[1])
        _write_csv(staging / "normal_branch_flows.csv", _BRANCH_FIELDS, details[2])
        _write_csv(staging / "normal_dc_flows.csv", _DC_FLOW_FIELDS, details[3])
        _write_csv(staging / "reserve_up.csv", _RESERVE_FIELDS, details[4])
        _write_json(staging / "candidate_audits.json", details[5])
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def _csv_rows(path: Path, fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != fields:
            raise RuntimeError(f"RTS-GMLC AC-aware CSV schema drifted: {path}")
        return list(reader)


def _parse_bool(value_: object, *, label: str) -> bool:
    normalized = str(value_).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"RTS-GMLC AC-aware {label} is not boolean")


def _finite(value_: object, *, label: str) -> float:
    try:
        parsed = float(value_)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"RTS-GMLC AC-aware {label} is not numeric") from error
    if not math.isfinite(parsed):
        raise RuntimeError(f"RTS-GMLC AC-aware {label} is not finite")
    return parsed


def _exact_int(value_: object, *, label: str) -> int:
    parsed = _finite(value_, label=label)
    integer = int(parsed)
    if parsed != integer:
        raise RuntimeError(f"RTS-GMLC AC-aware {label} is not integral")
    return integer


def _group_candidate_hour_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    candidate_ids: Sequence[str],
    hours: int,
    identity_field: str,
    expected_identities: Sequence[str],
) -> dict[str, tuple[dict[str, Mapping[str, str]], ...]]:
    expected_candidates = set(candidate_ids)
    expected_items = set(expected_identities)
    grouped: dict[str, list[dict[str, Mapping[str, str]]]] = {
        candidate_id: [dict() for _ in range(hours)] for candidate_id in candidate_ids
    }
    seen = set()
    for row in rows:
        candidate_id = str(row["candidate_id"])
        hour = _exact_int(row["hour_index"], label="hour_index")
        identity = str(row[identity_field])
        key = (candidate_id, hour, identity)
        if (
            candidate_id not in expected_candidates
            or not 0 <= hour < hours
            or identity not in expected_items
            or key in seen
        ):
            raise RuntimeError("RTS-GMLC AC-aware candidate detail identity drifted")
        seen.add(key)
        grouped[candidate_id][hour][identity] = row
    expected_count = len(candidate_ids) * hours * len(expected_items)
    if len(seen) != expected_count or any(
        set(hour_rows) != expected_items
        for candidate_rows in grouped.values()
        for hour_rows in candidate_rows
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate detail coverage drifted")
    return {
        candidate_id: tuple(candidate_rows)
        for candidate_id, candidate_rows in grouped.items()
    }


def _load_candidate_frontier(
    context: _FrontierContext, output_root: Path
) -> tuple[list[_LoadedCandidate], str]:
    root = output_root / "candidate_frontier"
    summary = _load_json(root, "summary.json")
    if (
        summary.get("input_contract_sha256") != context.input_contract_sha256
        or summary.get("candidate_generation_completed_before_any_joint_ac_solve")
        is not True
        or summary.get("candidate_generation_uses_ac_outcomes") is not False
        or summary.get("joint_ac_solver_call_count") != 0
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate summary drifted")
    candidate_rows = _csv_rows(root / "candidates.csv", _CANDIDATE_FIELDS)
    selected_rows = [
        row
        for row in candidate_rows
        if _parse_bool(
            row["selected_unique_candidate"], label="selected_unique_candidate"
        )
    ]
    candidate_ids = tuple(str(row["candidate_id"]) for row in selected_rows)
    if (
        len(candidate_ids) != len(set(candidate_ids))
        or list(candidate_ids) != summary.get("candidate_ids")
        or len(candidate_ids) != int(summary["unique_candidate_count"])
    ):
        raise RuntimeError("RTS-GMLC AC-aware unique candidate identity drifted")
    hours = int(context.config["joint_ac"]["expected_hours"])
    timestamps = tuple(
        timestamp.isoformat() for timestamp in context.request.timestamps
    )
    if len(timestamps) != hours:
        raise RuntimeError("RTS-GMLC AC-aware request horizon drifted")
    generator_uids = tuple(
        generator.uid for generator in context.zero.scan.data.generators
    )
    branch_uids = tuple(branch.uid for branch in context.zero.scan.data.branches)
    dc_uids = tuple(branch.uid for branch in context.zero.scan.data.dc_branches)
    commitment = _group_candidate_hour_rows(
        _csv_rows(root / "commitment.csv", _COMMITMENT_FIELDS),
        candidate_ids=candidate_ids,
        hours=hours,
        identity_field="generator_uid",
        expected_identities=generator_uids,
    )
    generation = _group_candidate_hour_rows(
        _csv_rows(root / "normal_generation.csv", _GENERATION_FIELDS),
        candidate_ids=candidate_ids,
        hours=hours,
        identity_field="generator_uid",
        expected_identities=generator_uids,
    )
    branches = _group_candidate_hour_rows(
        _csv_rows(root / "normal_branch_flows.csv", _BRANCH_FIELDS),
        candidate_ids=candidate_ids,
        hours=hours,
        identity_field="branch_uid",
        expected_identities=branch_uids,
    )
    dc_flows = _group_candidate_hour_rows(
        _csv_rows(root / "normal_dc_flows.csv", _DC_FLOW_FIELDS),
        candidate_ids=candidate_ids,
        hours=hours,
        identity_field="dc_branch_uid",
        expected_identities=dc_uids,
    )
    by_candidate_row = {str(row["candidate_id"]): row for row in selected_rows}
    loaded = []
    for candidate_id in candidate_ids:
        commitment_rows = tuple(
            {
                uid: _parse_bool(hour_rows[uid]["commitment"], label="commitment")
                for uid in generator_uids
            }
            for hour_rows in commitment[candidate_id]
        )
        startup_rows = tuple(
            {
                uid: _parse_bool(hour_rows[uid]["startup"], label="startup")
                for uid in generator_uids
            }
            for hour_rows in commitment[candidate_id]
        )
        shutdown_rows = tuple(
            {
                uid: _parse_bool(hour_rows[uid]["shutdown"], label="shutdown")
                for uid in generator_uids
            }
            for hour_rows in commitment[candidate_id]
        )
        expected_startup, expected_shutdown = _boolean_transitions(
            commitment_rows, context.initial_state.commitment
        )
        if startup_rows != expected_startup or shutdown_rows != expected_shutdown:
            raise RuntimeError("RTS-GMLC AC-aware persisted transition drifted")
        generation_rows = tuple(
            {
                uid: _finite(hour_rows[uid]["generation_mw"], label="generation_mw")
                for uid in generator_uids
            }
            for hour_rows in generation[candidate_id]
        )
        branch_rows = tuple(
            {
                uid: _finite(hour_rows[uid]["flow_mw"], label="branch_flow_mw")
                for uid in branch_uids
            }
            for hour_rows in branches[candidate_id]
        )
        dc_rows = tuple(
            {
                uid: _finite(hour_rows[uid]["flow_mw"], label="dc_flow_mw")
                for uid in dc_uids
            }
            for hour_rows in dc_flows[candidate_id]
        )
        row = by_candidate_row[candidate_id]
        commitment_hash = _commitment_sha256(commitment_rows)
        dispatch_hash = _dispatch_sha256(generation_rows, branch_rows, dc_rows)
        if (
            commitment_hash != row["commitment_sha256"]
            or dispatch_hash != row["dispatch_sha256"]
        ):
            raise RuntimeError("RTS-GMLC AC-aware candidate content hash drifted")
        for hour, timestamp in enumerate(timestamps):
            persisted_timestamps = (
                {
                    commitment[candidate_id][hour][uid]["timestamp"]
                    for uid in generator_uids
                },
                {
                    generation[candidate_id][hour][uid]["timestamp"]
                    for uid in generator_uids
                },
                {branches[candidate_id][hour][uid]["timestamp"] for uid in branch_uids},
                {dc_flows[candidate_id][hour][uid]["timestamp"] for uid in dc_uids},
            )
            if any(values != {timestamp} for values in persisted_timestamps):
                raise RuntimeError("RTS-GMLC AC-aware candidate timestamp drifted")
        loaded.append(
            _LoadedCandidate(
                candidate_id=candidate_id,
                requested_candidate_id=str(row["requested_candidate_id"]),
                relative_cost_budget_delta=_finite(
                    row["relative_cost_budget_delta"], label="cost_budget_delta"
                ),
                operating_cost_usd=_finite(
                    row["operating_cost_usd"], label="operating_cost_usd"
                ),
                reactive_proxy_fraction=_finite(
                    row["reactive_proxy_fraction"], label="reactive_proxy_fraction"
                ),
                commitment_sha256=commitment_hash,
                dispatch_sha256=dispatch_hash,
                commitment=commitment_rows,
                startup=startup_rows,
                shutdown=shutdown_rows,
                generation_mw=generation_rows,
                branch_flows_mw=branch_rows,
                dc_flows_mw=dc_rows,
            )
        )
    return loaded, _sha256(root / "SHA256SUMS")


def _prepared_joint_cases(
    context: _FrontierContext, candidate: _LoadedCandidate
) -> tuple[Any, ...]:
    points = tuple(context.zero.ac.scan_context.business.points)
    if len(points) != len(candidate.commitment):
        raise RuntimeError("RTS-GMLC AC-aware AC point horizon drifted")
    placeholder_bus = int(context.zero.config["zero_control"]["dc_bus_api_placeholder"])
    dc_tolerance = float(
        context.config["candidate_frontier"]["solver"]["feasibility_tolerance"]
    )
    prepared = []
    for hour, point in enumerate(points):
        reconstructed_dc, residual = reconstruct_rts_gmlc_dc_flows(
            context.zero.scan.data,
            demand_by_bus_mw=point.demand_by_bus_mw,
            generation_mw=candidate.generation_mw[hour],
            ac_branch_flows_mw=candidate.branch_flows_mw[hour],
            tolerance_mw=dc_tolerance,
        )
        if residual > dc_tolerance or any(
            abs(reconstructed_dc[uid] - candidate.dc_flows_mw[hour][uid]) > dc_tolerance
            for uid in reconstructed_dc
        ):
            raise RuntimeError("RTS-GMLC AC-aware candidate DC reconstruction drifted")
        configured = _configure_q_capable_voltage_control(
            context.zero.ac.template,
            context.zero.scan.data,
            point,
            generation_mw=candidate.generation_mw[hour],
            commitment=candidate.commitment[hour],
            dc_bus=placeholder_bus,
            data_center_power_mw=0.0,
            data_center_power_factor=1.0,
            dc_flows_mw=reconstructed_dc,
        )
        prepared.append(
            prepare_rts_gmlc_ac_recovery(
                configured,
                context.zero.ac.template,
                context.zero.scan.data,
                mode="distributed_committable",
                voltage_limits_pu=(0.95, 1.05),
            )
        )
    return tuple(prepared)


def _joint_chronology(
    context: _FrontierContext, candidate: _LoadedCandidate
) -> AcAwareChronology:
    tolerance = float(
        context.config["candidate_frontier"]["solver"]["feasibility_tolerance"]
    )
    points = _validate_inputs(context.zero.scan.data, context.request, tolerance)
    expected_hours = int(context.config["joint_ac"]["expected_hours"])
    if (
        len(points) != expected_hours
        or len(candidate.commitment) != expected_hours
        or len(context.request.timestamps) != expected_hours
    ):
        raise RuntimeError("RTS-GMLC AC-aware chronology horizon drifted")
    data = context.zero.scan.data
    area_by_bus = {int(bus.uid): int(bus.area) for bus in data.buses}
    reserve_categories = frozenset(
        str(item) for item in context.config["joint_ac"]["reserve_eligible_categories"]
    )
    units = []
    for generator in data.generators:
        if generator.dispatch_mode != "committable":
            continue
        uid = generator.uid
        units.append(
            AcAwareCommitmentUnit(
                generator_uid=uid,
                area=area_by_bus[int(generator.bus)],
                p_max_mw=float(generator.p_max_mw),
                ramp_mw_per_hour=float(generator.ramp_mw_per_hour),
                ramp_mw_per_minute=float(generator.ramp_mw_per_minute),
                reserve_eligible=bool(
                    generator.enabled and generator.category in reserve_categories
                ),
                initial_generation_mw=float(context.initial_state.generation_mw[uid]),
                initial_commitment=bool(context.initial_state.commitment[uid]),
                commitment_by_hour=tuple(
                    bool(row[uid]) for row in candidate.commitment
                ),
                startup_by_hour=tuple(bool(row[uid]) for row in candidate.startup),
                shutdown_by_hour=tuple(bool(row[uid]) for row in candidate.shutdown),
            )
        )
    if not units:
        raise RuntimeError("RTS-GMLC AC-aware chronology has no committable units")
    return AcAwareChronology(
        timestamps=tuple(context.request.timestamps),
        time_step_hours=float(context.request.time_step_hours),
        units=tuple(units),
        spin_up_requirement_by_hour_area_mw=tuple(
            {
                int(area): float(requirement)
                for area, requirement in point.spin_up_requirement_by_area_mw.items()
            }
            for point in points
        ),
    )


def _joint_solution_sha256(
    hour_rows: Sequence[Mapping[str, object]],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
    reserve_rows: Sequence[Mapping[str, object]],
) -> str:
    tables = (
        (_JOINT_HOUR_FIELDS, hour_rows),
        (_JOINT_GENERATOR_FIELDS, generator_rows),
        (_JOINT_BUS_FIELDS, bus_rows),
        (_JOINT_BRANCH_FIELDS, branch_rows),
        (_JOINT_RESERVE_FIELDS, reserve_rows),
    )
    return common_input_signature_sha256(
        {
            "schema": "rts_gmlc_joint_ac_solution_identity_v1",
            "tables": [
                {
                    "fields": list(fieldnames),
                    "rows": [
                        [_format_value(row[field]) for field in fieldnames]
                        for row in rows
                    ],
                }
                for fieldnames, rows in tables
            ],
        }
    )


def _joint_result_rows(
    candidate: _LoadedCandidate,
    result: AcAwareCommitmentResult,
) -> tuple[
    dict[str, object],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
    list[dict[str, object]],
]:
    run_row = {
        "candidate_id": candidate.candidate_id,
        "requested_candidate_id": candidate.requested_candidate_id,
        "relative_cost_budget_delta": candidate.relative_cost_budget_delta,
        "operating_cost_usd": candidate.operating_cost_usd,
        "reactive_proxy_fraction": candidate.reactive_proxy_fraction,
        "commitment_sha256": candidate.commitment_sha256,
        "dispatch_sha256": candidate.dispatch_sha256,
        **{field: getattr(result, field) for field in _JOINT_RESULT_SCALAR_FIELDS},
    }
    hour_rows = []
    generator_rows = []
    bus_rows = []
    branch_rows = []
    reserve_rows = []
    for hour_index, hour_result in enumerate(result.hour_results):
        prefix = {
            "candidate_id": candidate.candidate_id,
            "initial_strategy": result.initial_strategy,
            "hour_index": hour_index,
            "timestamp": hour_result.timestamp.isoformat(),
        }
        audit = asdict(hour_result.audit)
        generator_records = audit.pop("generator_records")
        bus_records = audit.pop("bus_records")
        branch_records = audit.pop("branch_records")
        hour_rows.append({**prefix, **audit})
        generator_rows.extend({**prefix, **record} for record in generator_records)
        bus_rows.extend({**prefix, **record} for record in bus_records)
        branch_rows.extend({**prefix, **record} for record in branch_records)
        reserve_rows.extend(
            {
                **prefix,
                "generator_uid": uid,
                "reserve_up_mw": reserve,
            }
            for uid, reserve in sorted(
                hour_result.reserve_up_mw_by_generator_uid.items()
            )
        )
    run_row["joint_solution_sha256"] = _joint_solution_sha256(
        hour_rows,
        generator_rows,
        bus_rows,
        branch_rows,
        reserve_rows,
    )
    return (
        run_row,
        hour_rows,
        generator_rows,
        bus_rows,
        branch_rows,
        reserve_rows,
    )


def _joint_hour_key(row: Mapping[str, object]) -> tuple[str, str, int]:
    return (
        str(row["candidate_id"]),
        str(row["initial_strategy"]),
        _exact_int(row["hour_index"], label="hour_index"),
    )


def _validate_joint_result_rows(
    context: _FrontierContext,
    candidates: Sequence[_LoadedCandidate],
    prepared_by_candidate: Mapping[str, tuple[Any, ...]],
    chronology_by_candidate: Mapping[str, AcAwareChronology],
    run_rows: Sequence[Mapping[str, object]],
    hour_rows: Sequence[Mapping[str, object]],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
    reserve_rows: Sequence[Mapping[str, object]],
) -> None:
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    if (
        len(candidate_by_id) != len(candidates)
        or set(prepared_by_candidate) != set(candidate_by_id)
        or set(chronology_by_candidate) != set(candidate_by_id)
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint candidate identity drifted")
    strategies = tuple(context.config["joint_ac"]["initial_strategies"])
    expected_run_keys = {
        (candidate_id, strategy)
        for candidate_id in candidate_by_id
        for strategy in strategies
    }
    observed_runs: dict[tuple[str, str], Mapping[str, object]] = {}
    for row in run_rows:
        key = (str(row["candidate_id"]), str(row["initial_strategy"]))
        if key not in expected_run_keys or key in observed_runs:
            raise RuntimeError("RTS-GMLC AC-aware joint run coverage drifted")
        observed_runs[key] = row
    if set(observed_runs) != expected_run_keys:
        raise RuntimeError("RTS-GMLC AC-aware joint run coverage drifted")

    hours = int(context.config["joint_ac"]["expected_hours"])
    timestamps = tuple(
        timestamp.isoformat() for timestamp in context.request.timestamps
    )
    if len(timestamps) != hours:
        raise RuntimeError("RTS-GMLC AC-aware joint timestamp horizon drifted")
    expected_hour_keys = {
        (candidate_id, strategy, hour)
        for candidate_id, strategy in expected_run_keys
        for hour in range(hours)
    }
    observed_hours: dict[tuple[str, str, int], Mapping[str, object]] = {}
    for row in hour_rows:
        key = _joint_hour_key(row)
        if key not in expected_hour_keys or key in observed_hours:
            raise RuntimeError("RTS-GMLC AC-aware joint hour coverage drifted")
        if str(row["timestamp"]) != timestamps[key[2]]:
            raise RuntimeError("RTS-GMLC AC-aware joint hour timestamp drifted")
        observed_hours[key] = row
    if set(observed_hours) != expected_hour_keys:
        raise RuntimeError("RTS-GMLC AC-aware joint hour coverage drifted")

    grouped_details: list[dict[tuple[str, str, int], list[Mapping[str, object]]]] = []
    for rows in (generator_rows, bus_rows, branch_rows):
        grouped = {key: [] for key in expected_hour_keys}
        for row in rows:
            key = _joint_hour_key(row)
            if (
                key not in expected_hour_keys
                or str(row["timestamp"]) != timestamps[key[2]]
            ):
                raise RuntimeError("RTS-GMLC AC-aware joint detail identity drifted")
            grouped[key].append(row)
        grouped_details.append(grouped)

    grouped_reserve = {key: {} for key in expected_hour_keys}
    for row in reserve_rows:
        key = _joint_hour_key(row)
        uid = str(row["generator_uid"])
        if (
            key not in expected_hour_keys
            or str(row["timestamp"]) != timestamps[key[2]]
            or uid in grouped_reserve[key]
        ):
            raise RuntimeError("RTS-GMLC AC-aware joint reserve identity drifted")
        grouped_reserve[key][uid] = row

    audit_tolerances = context.config["independent_audit"]
    for run_key, run_row in observed_runs.items():
        candidate_id, strategy = run_key
        candidate = candidate_by_id[candidate_id]
        chronology = chronology_by_candidate[candidate_id]
        prepared_cases = prepared_by_candidate[candidate_id]
        if len(prepared_cases) != hours or len(chronology.timestamps) != hours:
            raise RuntimeError("RTS-GMLC AC-aware prepared horizon drifted")
        metadata = {
            "candidate_id": candidate.candidate_id,
            "requested_candidate_id": candidate.requested_candidate_id,
            "relative_cost_budget_delta": candidate.relative_cost_budget_delta,
            "operating_cost_usd": candidate.operating_cost_usd,
            "reactive_proxy_fraction": candidate.reactive_proxy_fraction,
            "commitment_sha256": candidate.commitment_sha256,
            "dispatch_sha256": candidate.dispatch_sha256,
            "initial_strategy": strategy,
        }
        for field, expected in metadata.items():
            step._assert_serialized(run_row[field], expected, label=field)
        run_hour_keys = [(candidate_id, strategy, hour) for hour in range(hours)]
        solution_hash = _joint_solution_sha256(
            [observed_hours[key] for key in run_hour_keys],
            [row for key in run_hour_keys for row in grouped_details[0][key]],
            [row for key in run_hour_keys for row in grouped_details[1][key]],
            [row for key in run_hour_keys for row in grouped_details[2][key]],
            [row for key in run_hour_keys for row in grouped_reserve[key].values()],
        )
        if str(run_row["joint_solution_sha256"]) != solution_hash:
            raise RuntimeError("RTS-GMLC AC-aware joint solution hash drifted")
        if (
            not step._parse_bool(run_row["evaluated"], label="evaluated")
            or not step._parse_bool(
                run_row["solver_input_cases_unchanged"],
                label="solver_input_cases_unchanged",
            )
            or step._integer(run_row["iterations"], label="iterations") < 0
            or not str(run_row["return_status"])
        ):
            raise RuntimeError("RTS-GMLC AC-aware joint solver identity drifted")
        for field in (
            "normalized_objective",
            "independent_squared_target_deviation_mw2",
            "maximum_nlp_constraint_violation",
            "maximum_nlp_variable_bound_violation",
            "maximum_ramp_violation_mw",
            "maximum_reserve_bound_violation_mw",
            "maximum_reserve_headroom_violation_mw",
            "maximum_reserve_shortfall_mw",
        ):
            if step._finite(run_row[field], label=field) < 0.0:
                raise RuntimeError(f"RTS-GMLC AC-aware joint {field} is negative")

        audits = []
        generation_by_hour_uid = []
        reserve_by_hour_uid = []
        reserve_uids = {
            unit.generator_uid for unit in chronology.units if unit.reserve_eligible
        }
        for hour, prepared in enumerate(prepared_cases):
            key = (candidate_id, strategy, hour)
            hour_row = observed_hours[key]
            audit = step._reconstruct_audit(
                SimpleNamespace(prepared=prepared),
                hour_row,
                grouped_details[0][key],
                grouped_details[1][key],
                grouped_details[2][key],
            )
            audit_payload = asdict(audit)
            expected_generator_records = audit_payload.pop("generator_records")
            expected_bus_records = audit_payload.pop("bus_records")
            expected_branch_records = audit_payload.pop("branch_records")
            for field, expected in audit_payload.items():
                step._assert_serialized(hour_row[field], expected, label=field)
            for persisted, expected_records, identity_field in (
                (
                    grouped_details[0][key],
                    expected_generator_records,
                    "generator_row",
                ),
                (grouped_details[1][key], expected_bus_records, "bus_row"),
                (grouped_details[2][key], expected_branch_records, "branch_row"),
            ):
                ordered = sorted(
                    persisted,
                    key=lambda item: step._integer(
                        item[identity_field], label=identity_field
                    ),
                )
                if len(ordered) != len(expected_records):
                    raise RuntimeError(
                        "RTS-GMLC AC-aware joint detail coverage drifted"
                    )
                for actual, expected_record in zip(
                    ordered, expected_records, strict=True
                ):
                    for field, expected in expected_record.items():
                        step._assert_serialized(actual[field], expected, label=field)
            generation = {
                record.generator_uid: record for record in audit.generator_records
            }
            if len(generation) != len(audit.generator_records):
                raise RuntimeError("RTS-GMLC AC-aware generator UID drifted")
            if set(grouped_reserve[key]) != reserve_uids:
                raise RuntimeError("RTS-GMLC AC-aware reserve coverage drifted")
            reserve = {
                uid: step._finite(row["reserve_up_mw"], label="reserve_up_mw")
                for uid, row in grouped_reserve[key].items()
            }
            audits.append(audit)
            generation_by_hour_uid.append(generation)
            reserve_by_hour_uid.append(reserve)

        independent_objective = sum(
            audit.reconstructed_objective_mw2 for audit in audits
        )
        normalized_objective = (
            independent_objective / float(prepared_cases[0].case["baseMVA"]) ** 2
        )
        step._assert_serialized(
            run_row["independent_squared_target_deviation_mw2"],
            independent_objective,
            label="independent_squared_target_deviation_mw2",
        )
        step._assert_serialized(
            run_row["normalized_objective"],
            normalized_objective,
            label="normalized_objective",
        )

        unit_by_uid = {unit.generator_uid: unit for unit in chronology.units}
        maximum_ramp_violation = 0.0
        for uid, unit in unit_by_uid.items():
            previous = unit.initial_generation_mw
            for hour, generation in enumerate(generation_by_hour_uid):
                if uid not in generation:
                    raise RuntimeError("RTS-GMLC AC-aware chronology unit disappeared")
                current = generation[uid].pg_mw
                delta = current - previous
                step_ramp = unit.ramp_mw_per_hour * chronology.time_step_hours
                lower = -step_ramp - unit.p_max_mw * float(unit.shutdown_by_hour[hour])
                upper = step_ramp + unit.p_max_mw * float(unit.startup_by_hour[hour])
                maximum_ramp_violation = max(
                    maximum_ramp_violation, lower - delta, delta - upper, 0.0
                )
                previous = current

        maximum_reserve_bound_violation = 0.0
        maximum_reserve_headroom_violation = 0.0
        maximum_reserve_shortfall = 0.0
        for hour, (generation, reserve) in enumerate(
            zip(generation_by_hour_uid, reserve_by_hour_uid, strict=True)
        ):
            area_reserve: dict[int, float] = {}
            for uid, reserve_up in reserve.items():
                unit = unit_by_uid[uid]
                record = generation[uid]
                cap = (
                    10.0
                    * unit.ramp_mw_per_minute
                    * float(unit.commitment_by_hour[hour])
                )
                headroom = record.pmax_mw - record.pg_mw
                maximum_reserve_bound_violation = max(
                    maximum_reserve_bound_violation,
                    -reserve_up,
                    reserve_up - cap,
                    0.0,
                )
                maximum_reserve_headroom_violation = max(
                    maximum_reserve_headroom_violation,
                    reserve_up - headroom,
                    0.0,
                )
                area_reserve[unit.area] = area_reserve.get(unit.area, 0.0) + reserve_up
            for area, requirement in chronology.spin_up_requirement_by_hour_area_mw[
                hour
            ].items():
                maximum_reserve_shortfall = max(
                    maximum_reserve_shortfall,
                    float(requirement) - area_reserve.get(area, 0.0),
                    0.0,
                )
        for field, expected in (
            ("maximum_ramp_violation_mw", maximum_ramp_violation),
            (
                "maximum_reserve_bound_violation_mw",
                maximum_reserve_bound_violation,
            ),
            (
                "maximum_reserve_headroom_violation_mw",
                maximum_reserve_headroom_violation,
            ),
            ("maximum_reserve_shortfall_mw", maximum_reserve_shortfall),
        ):
            step._assert_serialized(run_row[field], expected, label=field)

        solver_success = step._parse_bool(
            run_row["solver_success"], label="solver_success"
        )
        expected_witness = bool(
            solver_success
            and step._finite(
                run_row["maximum_nlp_constraint_violation"],
                label="maximum_nlp_constraint_violation",
            )
            <= float(audit_tolerances["nlp_constraint_tolerance"])
            and step._finite(
                run_row["maximum_nlp_variable_bound_violation"],
                label="maximum_nlp_variable_bound_violation",
            )
            <= float(audit_tolerances["nlp_variable_bound_tolerance"])
            and maximum_ramp_violation <= float(audit_tolerances["ramp_tolerance_mw"])
            and maximum_reserve_bound_violation
            <= float(audit_tolerances["reserve_tolerance_mw"])
            and maximum_reserve_headroom_violation
            <= float(audit_tolerances["reserve_tolerance_mw"])
            and maximum_reserve_shortfall
            <= float(audit_tolerances["reserve_tolerance_mw"])
            and all(
                audit.postsolve_network_equation_reconstruction_audit_passed
                for audit in audits
            )
        )
        if (
            step._parse_bool(
                run_row["feasibility_witnessed"], label="feasibility_witnessed"
            )
            != expected_witness
        ):
            raise RuntimeError("RTS-GMLC AC-aware joint witness drifted")


def _joint_summary(
    context: _FrontierContext,
    registration: Mapping[str, Any],
    candidates: Sequence[_LoadedCandidate],
    candidate_frontier_manifest_sha256: str,
    run_rows: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    strategies = tuple(context.config["joint_ac"]["initial_strategies"])
    rows_by_key = {
        (str(row["candidate_id"]), str(row["initial_strategy"])): row
        for row in run_rows
    }
    candidate_summaries = {}
    witnessed_candidate_ids = []
    not_witnessed_runs = []
    for candidate in candidates:
        witnessed_strategies = []
        strategy_statuses = {}
        for strategy in strategies:
            row = rows_by_key[(candidate.candidate_id, strategy)]
            witnessed = step._parse_bool(
                row["feasibility_witnessed"], label="feasibility_witnessed"
            )
            if witnessed:
                witnessed_strategies.append(strategy)
            else:
                not_witnessed_runs.append(
                    {
                        "candidate_id": candidate.candidate_id,
                        "initial_strategy": strategy,
                        "return_status": str(row["return_status"]),
                    }
                )
            strategy_statuses[strategy] = {
                "solver_success": step._parse_bool(
                    row["solver_success"], label="solver_success"
                ),
                "feasibility_witnessed": witnessed,
                "return_status": str(row["return_status"]),
                "iterations": step._integer(row["iterations"], label="iterations"),
            }
        if witnessed_strategies:
            witnessed_candidate_ids.append(candidate.candidate_id)
        candidate_summaries[candidate.candidate_id] = {
            "requested_candidate_id": candidate.requested_candidate_id,
            "relative_cost_budget_delta": candidate.relative_cost_budget_delta,
            "operating_cost_usd": candidate.operating_cost_usd,
            "reactive_proxy_fraction": candidate.reactive_proxy_fraction,
            "commitment_sha256": candidate.commitment_sha256,
            "dispatch_sha256": candidate.dispatch_sha256,
            "witnessed_initial_strategies": witnessed_strategies,
            "strategy_statuses": strategy_statuses,
        }
    treatment_gate = bool(witnessed_candidate_ids)
    interpretation = context.config["interpretation"]
    return {
        "schema": "rts_gmlc_zero_dc_ac_aware_joint_ac_results_v2",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "candidate_frontier_manifest_sha256": candidate_frontier_manifest_sha256,
        "candidate_count": len(candidates),
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "initial_strategies": list(strategies),
        "joint_ac_solver_call_count": len(run_rows),
        "expected_joint_ac_solver_call_count": len(candidates) * len(strategies),
        "all_candidates_and_strategies_reported": len(run_rows)
        == len(candidates) * len(strategies),
        "all_candidates_and_strategies_run_no_early_stop": True,
        "one_solver_call_per_candidate_strategy": True,
        "retry_or_fallback_used": False,
        "per_hour_method_selection_used": False,
        "normal_state_only": True,
        "candidate_summaries": candidate_summaries,
        "feasibility_witnessed_run_count": sum(
            step._parse_bool(
                row["feasibility_witnessed"], label="feasibility_witnessed"
            )
            for row in run_rows
        ),
        "feasibility_witnessed_candidate_ids": witnessed_candidate_ids,
        "not_witnessed_candidate_strategies": not_witnessed_runs,
        "treatment_followup_gate_passed": treatment_gate,
        "registered_result_claim": (
            interpretation["successful_claim"]
            if treatment_gate
            else interpretation["unsuccessful_claim"]
        ),
        "solver_reported_infeasibility_is_global_proof": False,
        "global_optimality_claimed": False,
        "global_infeasibility_claimed": False,
        "maximum_nlp_constraint_violation": max(
            step._finite(
                row["maximum_nlp_constraint_violation"],
                label="maximum_nlp_constraint_violation",
            )
            for row in run_rows
        ),
        "maximum_nlp_variable_bound_violation": max(
            step._finite(
                row["maximum_nlp_variable_bound_violation"],
                label="maximum_nlp_variable_bound_violation",
            )
            for row in run_rows
        ),
        "maximum_ramp_violation_mw": max(
            step._finite(
                row["maximum_ramp_violation_mw"],
                label="maximum_ramp_violation_mw",
            )
            for row in run_rows
        ),
        "maximum_reserve_bound_violation_mw": max(
            step._finite(
                row["maximum_reserve_bound_violation_mw"],
                label="maximum_reserve_bound_violation_mw",
            )
            for row in run_rows
        ),
        "maximum_reserve_headroom_violation_mw": max(
            step._finite(
                row["maximum_reserve_headroom_violation_mw"],
                label="maximum_reserve_headroom_violation_mw",
            )
            for row in run_rows
        ),
        "maximum_reserve_shortfall_mw": max(
            step._finite(
                row["maximum_reserve_shortfall_mw"],
                label="maximum_reserve_shortfall_mw",
            )
            for row in run_rows
        ),
        **context.config["evidence"],
    }


def _load_joint_results(
    context: _FrontierContext,
    target: Path,
    registration: Mapping[str, Any],
    candidates: Sequence[_LoadedCandidate],
    candidate_frontier_manifest_sha256: str,
    prepared_by_candidate: Mapping[str, tuple[Any, ...]],
    chronology_by_candidate: Mapping[str, AcAwareChronology],
) -> dict[str, Any]:
    summary = _load_json(target, "summary.json")
    run_rows = _csv_rows(target / "joint_runs.csv", _JOINT_RUN_FIELDS)
    hour_rows = _csv_rows(target / "joint_hours.csv", _JOINT_HOUR_FIELDS)
    generator_rows = _csv_rows(
        target / "generator_results.csv", _JOINT_GENERATOR_FIELDS
    )
    bus_rows = _csv_rows(target / "bus_results.csv", _JOINT_BUS_FIELDS)
    branch_rows = _csv_rows(target / "branch_results.csv", _JOINT_BRANCH_FIELDS)
    reserve_rows = _csv_rows(target / "reserve_results.csv", _JOINT_RESERVE_FIELDS)
    _validate_joint_result_rows(
        context,
        candidates,
        prepared_by_candidate,
        chronology_by_candidate,
        run_rows,
        hour_rows,
        generator_rows,
        bus_rows,
        branch_rows,
        reserve_rows,
    )
    expected_summary = _joint_summary(
        context,
        registration,
        candidates,
        candidate_frontier_manifest_sha256,
        run_rows,
    )
    if summary != expected_summary:
        raise RuntimeError("Published RTS-GMLC AC-aware joint summary drifted")
    return summary


def run_joint_ac(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    candidates, candidate_frontier_manifest_sha256 = _load_candidate_frontier(
        context, output_root
    )
    if not candidates:
        raise RuntimeError("RTS-GMLC AC-aware candidate frontier is empty")
    prepared_by_candidate = {
        candidate.candidate_id: _prepared_joint_cases(context, candidate)
        for candidate in candidates
    }
    chronology_by_candidate = {
        candidate.candidate_id: _joint_chronology(context, candidate)
        for candidate in candidates
    }
    target = output_root / "joint_ac"
    if target.exists():
        return _load_joint_results(
            context,
            target,
            registration,
            candidates,
            candidate_frontier_manifest_sha256,
            prepared_by_candidate,
            chronology_by_candidate,
        )

    run_rows = []
    hour_rows = []
    generator_rows = []
    bus_rows = []
    branch_rows = []
    reserve_rows = []
    for candidate in candidates:
        for strategy in context.config["joint_ac"]["initial_strategies"]:
            result = solve_ac_aware_commitment(
                prepared_by_candidate[candidate.candidate_id],
                chronology_by_candidate[candidate.candidate_id],
                initial_strategy=str(strategy),
                solver_options=context.config["joint_ac"]["ipopt_options"],
            )
            rows = _joint_result_rows(candidate, result)
            run_rows.append(rows[0])
            hour_rows.extend(rows[1])
            generator_rows.extend(rows[2])
            bus_rows.extend(rows[3])
            branch_rows.extend(rows[4])
            reserve_rows.extend(rows[5])
    _validate_joint_result_rows(
        context,
        candidates,
        prepared_by_candidate,
        chronology_by_candidate,
        run_rows,
        hour_rows,
        generator_rows,
        bus_rows,
        branch_rows,
        reserve_rows,
    )
    summary = _joint_summary(
        context,
        registration,
        candidates,
        candidate_frontier_manifest_sha256,
        run_rows,
    )

    def writer(staging: Path) -> None:
        _write_csv(staging / "joint_runs.csv", _JOINT_RUN_FIELDS, run_rows)
        _write_csv(staging / "joint_hours.csv", _JOINT_HOUR_FIELDS, hour_rows)
        _write_csv(
            staging / "generator_results.csv",
            _JOINT_GENERATOR_FIELDS,
            generator_rows,
        )
        _write_csv(staging / "bus_results.csv", _JOINT_BUS_FIELDS, bus_rows)
        _write_csv(staging / "branch_results.csv", _JOINT_BRANCH_FIELDS, branch_rows)
        _write_csv(staging / "reserve_results.csv", _JOINT_RESERVE_FIELDS, reserve_rows)
        _write_exact_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_joint_results(
        context,
        target,
        registration,
        candidates,
        candidate_frontier_manifest_sha256,
        prepared_by_candidate,
        chronology_by_candidate,
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=_CONFIG_PATH)
    parser.add_argument(
        "--stage",
        choices=("prepare", "generate-candidates", "run-joint-ac", "all"),
        required=True,
    )
    args = parser.parse_args()
    if args.stage == "prepare":
        result = prepare_preregistration(args.config)
    elif args.stage == "generate-candidates":
        result = generate_candidate_frontier(args.config)
    elif args.stage == "run-joint-ac":
        result = run_joint_ac(args.config)
    else:
        prepare_preregistration(args.config)
        generate_candidate_frontier(args.config)
        result = run_joint_ac(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
