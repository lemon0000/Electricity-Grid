"""Generate and evaluate a preregistered zero-DC AC-aware commitment frontier."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, fields, replace
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from typing import Any

import casadi as ca
import yaml
from pypower.idx_gen import QMAX, QMIN
from pyomo.environ import value

from experiments import pilot_rts_gmlc_zero_dc_ac_aware_formulations as formulation
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments import run_rts_gmlc_zero_dc_ac_step_control as step
from experiments.run_rts_gmlc_day0_scuc import _sha256
from experiments.run_rts_gmlc_multi_poi_scan import _write_manifest
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
    _extract_branch_flows,
    _extract_commitment,
    _extract_dc_flows,
    _extract_generation,
    _validate_inputs,
    build_rts_gmlc_pre_registered_contingencies,
)
from src.grid.rts_gmlc_ac import reconstruct_rts_gmlc_dc_flows
from src.grid.rts_gmlc_ac_aware_commitment import (
    AcAwareChronology,
    AcAwareCommitmentResult,
    AcAwareCommitmentUnit,
)
from src.grid.rts_gmlc_ac_ipopt import _FROZEN_IPOPT_OPTIONS
from src.grid.rts_gmlc_ac_recovery import prepare_rts_gmlc_ac_recovery
from src.grid.rts_gmlc_ac_step_control import (
    StepControlAudit,
    StepControlBranchRecord,
    StepControlBusRecord,
    StepControlGeneratorRecord,
)
from src.grid.rts_gmlc_exact_cg_runner import (
    ExactCgTimeLimits,
    run_exact_cg_stage,
)
from src.grid.rts_gmlc_v4_initial_proxy_warmstart import (
    V4InitialProxyWarmStartAdapter,
)
from src.scenarios.common_input_signature import common_input_signature_sha256
from src.solvers.execution_lease import (
    ExecutionLease,
    ParentProcessWatchdog,
    probe_process,
)
from src.solvers.mip_progress import JsonlProgressWriter

_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
_RUNNER_PATH = Path("experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4.py")
_WARMSTART_ADAPTER_PATH = Path("src/grid/rts_gmlc_v4_initial_proxy_warmstart.py")
_REPAIR_PARENT_OUTPUT_ROOT = Path(
    "results/tables/"
    "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_"
    "checkpoint_json_shape_repair_001"
)
_REPAIR_AMENDMENT_NAME = "implementation_repair_amendment.json"
_REPAIR_AMENDMENT_SCHEMA = (
    "rts_gmlc_zero_dc_ac_aware_commitment_implementation_repair_amendment_v1"
)
_REPAIR_AMENDMENT_ID = "rts_gmlc_zero_dc_ac_aware_commitment_warmstart_scope_repair_002"
_REPAIR_PARENT_INPUT_CONTRACT_SHA256 = (
    "b3aed21beff6b1e14d7c1c1c4a136bdf143e5f48f6d1dc1fab115ae07ef9faa8"
)
_REPAIR_PARENT_PREREGISTRATION_MANIFEST_SHA256 = (
    "c7de877bf23c2bb0b9769cf2fd1c464da6599176c232ac13ba7a9b3d0c970b77"
)
_REPAIR_PARENT_RUNNER_SHA256 = (
    "f7cfbbde5403ba49203efc60916f0ccb08a953b1b3d528a01e6f012863e8a82a"
)
_REPAIR_PARENT_ADAPTER_SHA256 = (
    "1e35878998f6b464b9d3583d769a5461a8cab99efc788810fec1ed75756f9ce0"
)
_REPAIR_SUCCESSOR_ADAPTER_SHA256 = (
    "c655a3d60af60655a4430000f87651441b888e7b949d8b853e86af45628efcd3"
)
_REPAIR_PARENT_AMENDMENT_CONTENT_SHA256 = (
    "78eef7beedd356717b43849f323778bc79a328bf986a9edf9dc16c3a258cc57a"
)
_REPAIR_FROZEN_CONFIG_SHA256 = (
    "b107aba3908b04bbd677994ac272eeb98d35d5d957978dd42a70f5e44672b84b"
)
_REPAIR_SHARED_AC_CORE_SHA256 = (
    "bdd106e00bf1750b8867e9e3127c797054aa6f8ca9456821c4eb252ddf93d824"
)
_REPAIR_FAILURE_ARTIFACTS = {
    (
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4/"
        "formal_repair_20260719T165115Z/attempt.json"
    ): "e7922ae4d300faa556a2dc78983a500eb4458c3c7657501d07ce0d0652381ba2",
    (
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4/"
        "formal_repair_20260719T165115Z/progress.jsonl"
    ): "55183208e86807e03ca6f4c3840007470fa4b5e3e940f8136275a7d9217b4f33",
    (
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4/"
        "formal_repair_20260719T165115Z/01_q_proxy_delta_0p0010/"
        "proxy_maximization/proxy_maximization__iteration_01__master.log"
    ): "64bf0ee9147bca47c3e4fa09dcb878c4bddff30fd5b0ff892dc07dd256bafa02",
    (
        "results/tables/"
        "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_"
        "checkpoint_json_shape_repair_001/execution_lease/active/lease.json"
    ): "a2118b4fd6fcc93b129afc4e08c9767b50fbe09f84fb9da33dcef29cb9346e0c",
}
_REPAIR_TEST_PATHS = (
    Path("tests/test_rts_gmlc_zero_dc_ac_aware_commitment_v4_checkpoint_core.py"),
    Path("tests/test_rts_gmlc_zero_dc_ac_aware_commitment_v4_formal_contract.py"),
    Path("tests/test_rts_gmlc_zero_dc_ac_aware_commitment_v4_runner.py"),
    Path("tests/test_rts_gmlc_exact_cg_runner.py"),
)
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
    _RUNNER_PATH,
    Path("experiments/pilot_rts_gmlc_zero_dc_ac_aware_formulations.py"),
    Path("src/grid/rts_gmlc_exact_cg.py"),
    Path("src/grid/rts_gmlc_exact_cg_runner.py"),
    Path("src/grid/rts_gmlc_formal_cg_adapter.py"),
    Path("src/grid/rts_gmlc_v4_initial_proxy_warmstart.py"),
    Path("src/solvers/execution_lease.py"),
    Path("src/solvers/mip_progress.py"),
    Path("src/grid/rts_gmlc_ac_aware_commitment.py"),
    Path("src/grid/rts_gmlc_ac_aware_commitment_v4_adapter.py"),
    Path("experiments/run_rts_gmlc_zero_dc_normal_ac_control.py"),
    Path("src/grid/rts_gmlc_scuc.py"),
    Path("src/grid/rts_gmlc_ac.py"),
    Path("src/grid/rts_gmlc_ac_recovery.py"),
    Path("src/grid/rts_gmlc_ac_step_control.py"),
    Path("src/grid/rts_gmlc_ac_ipopt.py"),
    Path("experiments/monitor_rts_gmlc_zero_dc_ac_aware_commitment_v3.py"),
    Path("experiments/monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4.py"),
    Path("scripts/start_rts_gmlc_zero_dc_ac_aware_commitment_v4.ps1"),
)
_EXPECTED_TOP_LEVEL_KEYS = {
    "preregistration",
    "predecessor_v2",
    "predecessor_v3",
    "solver_selection_provenance",
    "formal_solver",
    "candidate_snapshot",
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
_CHECKPOINT_SCHEMA = "rts_gmlc_zero_dc_ac_aware_candidate_checkpoint_v2_full_precision"
_CHECKPOINT_FLOAT_SERIALIZATION = "python_json_roundtrip_full_precision_v1"
_JOINT_CHECKPOINT_SCHEMA = "rts_gmlc_zero_dc_ac_aware_joint_call_checkpoint_v1"
_JOINT_CALL_SCHEMA = "rts_gmlc_zero_dc_ac_aware_joint_call_registration_v1"
_JOINT_WORKER_SCHEMA = "rts_gmlc_zero_dc_ac_aware_joint_call_worker_result_v1"
_CHECKPOINT_FIELDS = {
    "schema",
    "float_serialization",
    "preregistration_id",
    "input_contract_sha256",
    "ordinal",
    "candidate",
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
_EXPECTED_JOINT_RUNTIME_CONTROL = {
    "max_cpu_time_seconds_per_call": 7200.0,
    "max_wall_time_seconds_per_call": 7500.0,
    "heartbeat_interval_seconds": 30.0,
    "parent_watchdog_interval_seconds": 5.0,
    "termination_grace_seconds": 30.0,
    "native_file_print_level": 5,
    "native_solver_logs_required": True,
    "checkpoint_each_completed_call": True,
    "retry_incomplete_call_allowed": False,
    "isolated_worker_process_required": True,
    "worker_pid_event_required": True,
    "log_directory": (
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4"
    ),
}
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
        "rts_gmlc_zero_dc_ac_aware_commitment_reference_bus_chronology_amendment_001"
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
_EXPECTED_PREDECESSOR_V2 = {
    "root": "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2",
    "config_path": "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml",
    "config_sha256": (
        "91a173d8c24d2aed6a91261b6c22130ddd7ae0bb1c5053cc62270f7fa1494b9a"
    ),
    "runner_path": "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment.py",
    "runner_sha256": (
        "5ace7a4d314f3a7031c8c30f63fa6fa9262c6196784baab15dc4ef62f8978c11"
    ),
    "preregistration_manifest_sha256": (
        "ee71eca750a4c6e8819c8d3b3c7de803c0736efa3327b5f89aec0d91edeff708"
    ),
    "operational_termination_manifest_sha256": (
        "e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b"
    ),
    "input_contract_sha256": (
        "7cb101bfbdc26994354fd77d6525bfc2de5deaf97496cc970cea805ead9857d0"
    ),
    "required_status": (
        "terminated_before_candidate_frontier_publication_and_before_any_joint_"
        "ac_solver_call"
    ),
    "candidate_frontier_artifact_published": False,
    "partial_candidate_solution_persisted": False,
    "joint_ac_solver_call_count": 0,
    "termination_is_infeasibility_evidence": False,
}
_EXPECTED_PREDECESSOR_V3 = {
    "root": "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3",
    "config_path": "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml",
    "config_sha256": (
        "68c89f2e2a14143e0c5581bff86193a530b935a57cdc388abbbf2806d27b95ba"
    ),
    "runner_path": "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v3.py",
    "runner_sha256": (
        "f421465fbf2415fc98fd0f3b8f2022215afd923613ad315f2fb620f64d79cbfb"
    ),
    "preregistration_manifest_sha256": (
        "01646721d15395668bf0079cb6fe218dc0625187d1fbf108c5db74e47ae33f88"
    ),
    "invalidation_manifest_sha256": (
        "30a112dc9c074533f7dbef07e0eb1508c85f6808f1af68631497b8104f1da548"
    ),
    "input_contract_sha256": (
        "af4a388d80c211611a8e1dad3861936decb7f3c3e2de3a422116c87c013d8aa0"
    ),
    "required_status": (
        "invalidated_after_one_semantically_invalid_budget_checkpoint_was_"
        "persisted_before_any_valid_budget_checkpoint_frontier_or_joint_ac_"
        "solver_call"
    ),
    "valid_budget_candidate_checkpoint_count": 0,
    "invalid_budget_candidate_checkpoint_count": 1,
    "invalid_checkpoint_relative_path": (
        "candidate_checkpoints/01_q_proxy_delta_0p0010"
    ),
    "invalid_checkpoint_manifest_sha256": (
        "e2f4e8849985cce5a72e2f9ad9ce906231c589e0d605b3f6dfbccc3df36e83bc"
    ),
    "stored_dispatch_sha256": (
        "7dc7e40ca9a90cf09018db76c959a8a2dafcfae91b7183364fb3884021a4c6e3"
    ),
    "recomputed_persisted_dispatch_sha256": (
        "d50253747b3ba20adbb33c52eed4497465a369cd0f7a39f60c8608262bb13658"
    ),
    "candidate_frontier_artifact_published": False,
    "joint_ac_solver_call_count": 0,
    "joint_ac_outcomes_observed": False,
    "failure_is_infeasibility_evidence": False,
    "invalid_checkpoint_is_resume_eligible": False,
    "v3_resume_allowed": False,
    "successor_must_use_new_preregistration_id": True,
    "parent_first_budget_solver_outcomes_observed": True,
    "parent_invalid_checkpoint_payload_observed": True,
}
_EXPECTED_SOLVER_SELECTION_PROVENANCE = {
    "solver_inventory": {
        "root": "results/tables/rts_gmlc_solver_inventory_v1",
        "manifest_sha256": (
            "ad39836b9ef94bc520ea2939750f9c4513b9db051d8c97513b813f566d97c9bf"
        ),
        "required_schema": "rts_gmlc_solver_inventory_v1",
        "required_status": "environment_inventory_completed_without_project_model_solve",
        "formal_candidate_started": False,
        "project_model_built_or_solved": False,
        "only_formally_eligible_solver": "highs",
    },
    "thread_benchmark": {
        "root": (
            "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_solver_benchmark_v1"
        ),
        "preparation_manifest_sha256": (
            "df3ed026af2bfbf77169e816713f361ef36374f89c255cb84de1621677f3485b"
        ),
        "result_manifest_sha256": (
            "4b05c7d7fcbd8f64ddb9eb61d4ee15c571a7905d8ebd453ac19d07cbf56c63d1"
        ),
        "summary_sha256": (
            "4688a7280ca79694b731e3f1ae76ac171c2fcb75d058983c0a97a89a173d925a"
        ),
        "required_selection_status": ("selected_by_preregistered_nonobjective_rule"),
        "selected_threads": 4,
        "objective_value_used_for_selection": False,
        "formal_candidate_result": False,
    },
    "formulation_pilot": {
        "root": (
            "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_formulation_pilot_v1"
        ),
        "preparation_manifest_sha256": (
            "ae3c19536341c0767f43dcbddb7ccabd60c9607f0baae7ab152507e750cf763a"
        ),
        "result_manifest_sha256": (
            "82f1f0cb72d574b2054f193f6354383c5629bd30796b42a919323ef326c0d7e1"
        ),
        "summary_sha256": (
            "4b00c772adca19232de12fdf91967db88199123c928719a742bbdf431f211f30"
        ),
        "input_contract_sha256": (
            "4c28c2b792c48c3c794d33cc05c419fd99927d2bd74732c6148d2ba10d707b34"
        ),
        "required_selection_status": (
            "selected_by_preregistered_nonobjective_runtime_rule"
        ),
        "selected_formulation": "exact_selected_state_constraint_generation",
        "required_eligible_repetitions": 2,
        "required_completed_repetitions": 2,
        "objective_value_used_for_selection": False,
        "formal_candidate_result": False,
    },
    "initial_proxy_warm_start": {
        "root": (
            "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_"
            "benchmark_v3"
        ),
        "preparation_manifest_sha256": (
            "99ed1475e9f4d69af50eb418753d09d311bba4f0d6bb81eeefbf0b2fdf93aa83"
        ),
        "result_manifest_sha256": (
            "e6b906a9038b51db08ca1f1775ac028a9cc221532d0b5c24e324d538797d23d2"
        ),
        "summary_sha256": (
            "e345d8038e4ae74a1e528d48b4df503c4d6c6f0c6a8f9e9d4a0f4e5b226f2774"
        ),
        "adapter_source_path": (
            "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_"
            "benchmark_v3/preparation/benchmark.py"
        ),
        "adapter_source_sha256": (
            "f2fa65a52277a258ea6d0888ed7816b13ca2f772f3914e3d6c353ca8a338397c"
        ),
        "required_selection_status": (
            "selected_by_preregistered_nonobjective_runtime_rule"
        ),
        "selected_method": "appsi_highs_full_mip_start",
        "solver_interface": "appsi_highs",
        "submission_scope": "every_solver_column",
        "application_scope": "initial_proxy_maximization_master_only",
        "selected_method_completed_repetitions": 2,
        "selected_method_eligible_repetitions": 2,
        "objective_value_used_for_selection": False,
        "formal_candidate_result": False,
    },
}
_EXPECTED_FORMAL_SOLVER = {
    "algorithm": "exact_selected_state_constraint_generation",
    "optimality_reporting": {
        "reported_interval": "actual_certified_lower_and_upper_bounds",
        "report_actual_absolute_gap": True,
        "report_actual_relative_gap_to_feasible_incumbent": True,
        "actual_interval_recomputed_for_every_completed_stage": True,
        "target_and_maximum_acceptance_frozen_before_formal_start": True,
        "post_result_threshold_relaxation_allowed": False,
    },
    "solver": {
        "name": "highs",
        "threads": 4,
        "random_seed": 0,
        "feasibility_tolerance": 1.0e-6,
        "bound_consistency_tolerance": 1.0e-6,
    },
    "stages": {
        "proxy_maximization": {
            "objective_sense": "maximize",
            "gap_measure": "certified_bound_interval_width",
            "target_relative_gap": 1.0e-4,
            "maximum_accepted_absolute_gap": 1.0e-3,
            "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
            "feasible_bound": ("lower_bound_from_final_full_state_feasible_incumbent"),
            "certified_bound": ("upper_bound_from_valid_active_master_dual_bound"),
            "relative_gap_denominator": "max_abs_feasible_bound_1e-12",
        },
        "cost_normalization": {
            "objective_sense": "minimize",
            "gap_measure": "certified_bound_interval_width",
            "target_relative_gap": 1.0e-4,
            "maximum_accepted_absolute_gap": None,
            "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
            "feasible_bound": ("upper_bound_from_final_full_state_feasible_incumbent"),
            "certified_bound": ("lower_bound_from_valid_active_master_dual_bound"),
            "relative_gap_denominator": "max_abs_feasible_bound_1e-12",
            "restart_constraint_generation_from_frozen_seed": True,
            "proxy_floor_absolute_tolerance": 1.0e-7,
        },
    },
    "primary_regret": {
        "observed_regret_upper_bound": (
            "stage1_actual_absolute_gap_plus_proxy_floor_tolerance_plus_"
            "numerical_audit_allowance"
        ),
        "proxy_floor_tolerance": 1.0e-7,
        "numerical_audit_allowance": 1.0e-6,
        "hard_maximum": 0.0010011,
    },
    "constraint_generation": {
        "initial_active_state_source": "parent_zero_final_active_state_ids",
        "rescreen_every_inactive_state_after_every_master": True,
        "unresolved_screen_action": "promote_and_label_unresolved_promoted",
        "unresolved_is_infeasibility_evidence": False,
        "cross_contingency_shared_recourse_allowed": False,
    },
    "time_limits_seconds": {
        "per_candidate_total": 43200.0,
        "proxy_master_per_call": 7200.0,
        "cost_master_per_call": 7200.0,
        "inactive_state_screen_per_call": 300.0,
        "final_full_state_audit_per_call": 1800.0,
    },
    "progress_logging": {
        "log_directory": (
            "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4"
        ),
        "heartbeat_interval_seconds": 30.0,
        "native_solver_log_interval_seconds": 5.0,
        "native_solver_logs_required": True,
        "durable_jsonl_flush_and_fsync_each_event": True,
        "report_actual_lower_bound_upper_bound_interval_and_gap": True,
    },
    "final_audit": {
        "required_after_each_stage": True,
        "selected_state_count": 24,
        "method": (
            "all_selected_states_fixed_shared_lp_and_independent_residual_audit"
        ),
        "eligible_requires_full_state_feasible_incumbent": True,
        "eligible_requires_actual_gap_within_frozen_maximum": True,
    },
    "expected_full_model_size": {
        "base_variables": 215688,
        "base_constraints": 350470,
        "proxy_stage_variables": 215689,
        "proxy_stage_constraints": 350615,
    },
}
_EXPECTED_CANDIDATE_SNAPSHOT = {
    "schema": "exact_shared_snapshot_v1",
    "discrete_components": ["commitment", "startup", "shutdown"],
    "exact_binary_normalization_allowed": True,
    "maximum_distance_to_nearest_binary_before_normalization": 1.0e-8,
    "normalized_values": [0.0, 1.0],
    "continuous_components": [
        "generation",
        "angle_degrees",
        "branch_flow",
        "dc_flow",
        "segment_power",
        "reserve_up",
        "reactive_proxy",
        "operating_cost",
    ],
    "continuous_values_use_full_precision": True,
    "continuous_rounding_or_clamping_allowed": False,
    "normalized_snapshot_requires_new_24_state_final_audit": True,
    "checkpoint_schema": _CHECKPOINT_SCHEMA,
    "checkpoint_float_serialization": _CHECKPOINT_FLOAT_SERIALIZATION,
    "checkpoint_prepublication_roundtrip_identity_validation": True,
    "checkpoint_existing_target_overwrite_allowed": False,
    "frontier_continuous_json_uses_full_precision": True,
}
_EXPECTED_FORBIDDEN_ADAPTIVITY = {
    "forced_generator_uids_allowed": False,
    "manual_failed_hours_allowed": False,
    "per_hour_commitment_override_allowed": False,
    "per_hour_solver_options_allowed": False,
    "candidate_addition_after_joint_ac_start_allowed": False,
    "voltage_or_q_or_rating_relaxation_allowed": False,
    "post_result_gap_or_time_limit_tuning_allowed": False,
    "acceptance_threshold_change_after_formal_start_allowed": False,
    "result_conditioned_retry_allowed": False,
    "cross_solver_or_formulation_candidate_stitching_allowed": False,
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


@dataclass(frozen=True)
class _JointRows:
    runs: tuple[dict[str, object], ...]
    hours: tuple[dict[str, object], ...]
    generators: tuple[dict[str, object], ...]
    buses: tuple[dict[str, object], ...]
    branches: tuple[dict[str, object], ...]
    reserves: tuple[dict[str, object], ...]


class _CheckedProgressHeartbeat:
    def __init__(
        self,
        writer: JsonlProgressWriter,
        *,
        interval_seconds: float,
        payload: Mapping[str, Any],
    ) -> None:
        if float(interval_seconds) <= 0.0:
            raise ValueError("heartbeat interval must be positive")
        self._writer = writer
        self._interval_seconds = float(interval_seconds)
        self._payload = dict(payload)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._error: BaseException | None = None

    def __enter__(self) -> _CheckedProgressHeartbeat:
        def run() -> None:
            while not self._stop.wait(self._interval_seconds):
                try:
                    self._writer.emit("heartbeat", **self._payload)
                except BaseException as error:
                    self._error = error
                    return

        self._thread = threading.Thread(
            target=run,
            name="checked-progress-heartbeat",
            daemon=True,
        )
        self._thread.start()
        return self

    def raise_if_failed(self) -> None:
        if self._error is not None:
            raise RuntimeError("Progress heartbeat failed") from self._error

    def __exit__(
        self,
        _error_type: type[BaseException] | None,
        error: BaseException | None,
        _traceback: object,
    ) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds + 1.0)
        if self._error is not None:
            if error is None:
                raise RuntimeError("Progress heartbeat failed") from self._error
            error.add_note(
                "Progress heartbeat failed: " + (str(self._error) or repr(self._error))
            )


def _candidate_checkpoint_path(
    output_root: Path,
    ordinal: int,
    requested_candidate_id: str,
) -> Path:
    if (
        ordinal < 0
        or not requested_candidate_id
        or any(
            character not in "abcdefghijklmnopqrstuvwxyz0123456789_"
            for character in requested_candidate_id
        )
    ):
        raise ValueError("Invalid candidate checkpoint identity")
    return (
        output_root
        / "candidate_checkpoints"
        / f"{ordinal:02d}_{requested_candidate_id}"
    )


def _candidate_from_checkpoint_payload(payload: Mapping[str, Any]) -> _Candidate:
    expected_fields = {field.name for field in fields(_Candidate)}
    if set(payload) != expected_fields:
        raise RuntimeError("Candidate checkpoint schema drifted")

    def boolean_rows(name: str) -> tuple[dict[str, bool], ...]:
        rows = payload[name]
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(f"Candidate checkpoint {name} drifted")
        if any(not isinstance(value_, bool) for row in rows for value_ in row.values()):
            raise RuntimeError(f"Candidate checkpoint {name} is not boolean")
        return tuple(
            {str(key): bool(value_) for key, value_ in row.items()} for row in rows
        )

    def numeric_rows(name: str) -> tuple[dict[str, float], ...]:
        rows = payload[name]
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(f"Candidate checkpoint {name} drifted")
        parsed = tuple(
            {str(key): float(value_) for key, value_ in row.items()} for row in rows
        )
        if any(not math.isfinite(value_) for row in parsed for value_ in row.values()):
            raise RuntimeError(f"Candidate checkpoint {name} is not finite")
        return parsed

    stage_audits = payload["stage_audits"]
    residual_audit = payload["residual_audit"]
    if not isinstance(stage_audits, dict) or not isinstance(residual_audit, dict):
        raise RuntimeError("Candidate checkpoint audits drifted")
    candidate = _Candidate(
        requested_candidate_id=str(payload["requested_candidate_id"]),
        source=str(payload["source"]),
        relative_cost_budget_delta=float(payload["relative_cost_budget_delta"]),
        cost_budget_usd=float(payload["cost_budget_usd"]),
        operating_cost_usd=float(payload["operating_cost_usd"]),
        reactive_proxy_fraction=float(payload["reactive_proxy_fraction"]),
        commitment_sha256=str(payload["commitment_sha256"]),
        dispatch_sha256=str(payload["dispatch_sha256"]),
        commitment=boolean_rows("commitment"),
        startup=boolean_rows("startup"),
        shutdown=boolean_rows("shutdown"),
        generation_mw=numeric_rows("generation_mw"),
        branch_flows_mw=numeric_rows("branch_flows_mw"),
        dc_flows_mw=numeric_rows("dc_flows_mw"),
        reserve_up_mw=numeric_rows("reserve_up_mw"),
        stage_audits=dict(stage_audits),
        residual_audit=dict(residual_audit),
    )
    scalar_values = (
        candidate.relative_cost_budget_delta,
        candidate.cost_budget_usd,
        candidate.operating_cost_usd,
        candidate.reactive_proxy_fraction,
    )
    if (
        not all(math.isfinite(item) for item in scalar_values)
        or _commitment_sha256(candidate.commitment) != candidate.commitment_sha256
        or _dispatch_sha256(
            candidate.generation_mw,
            candidate.branch_flows_mw,
            candidate.dc_flows_mw,
        )
        != candidate.dispatch_sha256
    ):
        raise RuntimeError("Candidate checkpoint identity audit failed")
    if candidate.source == "q_proxy_exact_selected_state_constraint_generation":
        for stage in ("proxy_maximization", "cost_normalization"):
            record = candidate.stage_audits.get(stage)
            if not isinstance(record, dict):
                raise RuntimeError("Candidate checkpoint stage audit is missing")
            certificate = record.get("certificate")
            final_audit = record.get("final_full_state_audit")
            acceptance = record.get("maximum_acceptance")
            if (
                record.get("eligible") is not True
                or record.get("eligibility_status")
                not in {"target_attained", "eligible_within_maximum"}
                or not isinstance(certificate, dict)
                or certificate.get("valid") is not True
                or not isinstance(final_audit, dict)
                or final_audit.get("passed") is not True
                or not isinstance(acceptance, dict)
                or acceptance.get("maximum_acceptance_passed") is not True
            ):
                raise RuntimeError("Candidate checkpoint stage certificate drifted")
        regret = candidate.stage_audits.get("primary_proxy_regret")
        if (
            not isinstance(regret, dict)
            or regret.get("passed") is not True
            or candidate.residual_audit.get("passed") is not True
        ):
            raise RuntimeError("Candidate checkpoint final audit drifted")
    return candidate


def _checkpoint_number(value_: object, *, label: str) -> float:
    if isinstance(value_, bool):
        raise RuntimeError(f"Candidate checkpoint {label} is not numeric")
    try:
        number = float(value_)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"Candidate checkpoint {label} is not numeric") from error
    if not math.isfinite(number):
        raise RuntimeError(f"Candidate checkpoint {label} is not finite")
    return number


def _checkpoint_close(left: object, right: object) -> bool:
    return math.isclose(
        _checkpoint_number(left, label="comparison left"),
        _checkpoint_number(right, label="comparison right"),
        rel_tol=1.0e-12,
        abs_tol=1.0e-9,
    )


def _validated_stage_certificate(
    candidate: _Candidate,
    context: _FrontierContext,
    stage: str,
) -> dict[str, float]:
    record = candidate.stage_audits.get(stage)
    if not isinstance(record, dict):
        raise RuntimeError(f"Candidate checkpoint {stage} audit is missing")
    spec = context.config["formal_solver"]["stages"][stage]
    sense = "maximize" if stage == "proxy_maximization" else "minimize"
    target = float(spec["target_relative_gap"])
    maximum_relative = float(
        spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
    )
    maximum_absolute = spec["maximum_accepted_absolute_gap"]
    certificate = record.get("certificate")
    acceptance = record.get("maximum_acceptance")
    audit = record.get("final_full_state_audit")
    masters = record.get("master_records")
    if (
        record.get("schema") != "rts_gmlc_exact_cg_stage_record_v1"
        or record.get("stage") != stage
        or record.get("sense") != sense
        or not isinstance(certificate, dict)
        or not isinstance(acceptance, dict)
        or not isinstance(audit, dict)
        or not isinstance(masters, list)
        or not masters
    ):
        raise RuntimeError(f"Candidate checkpoint {stage} record drifted")

    lower = _checkpoint_number(certificate.get("lower_bound"), label=f"{stage} LB")
    upper = _checkpoint_number(certificate.get("upper_bound"), label=f"{stage} UB")
    absolute_gap = _checkpoint_number(
        certificate.get("absolute_gap"), label=f"{stage} absolute gap"
    )
    if lower > upper or not _checkpoint_close(absolute_gap, upper - lower):
        raise RuntimeError(f"Candidate checkpoint {stage} bound interval drifted")
    feasible = lower if sense == "maximize" else upper
    relative_to_feasible = absolute_gap / max(abs(feasible), 1.0e-12)
    generic_relative = absolute_gap / max(abs(lower), abs(upper), 1.0)
    target_attained = relative_to_feasible <= target
    relative_passed = relative_to_feasible <= maximum_relative
    absolute_passed = bool(
        maximum_absolute is None or absolute_gap <= float(maximum_absolute)
    )
    maximum_passed = bool(relative_passed and absolute_passed)
    if (
        certificate.get("valid") is not True
        or not _checkpoint_close(
            certificate.get("relative_gap_to_feasible_incumbent"),
            relative_to_feasible,
        )
        or not _checkpoint_close(certificate.get("relative_gap"), generic_relative)
        or certificate.get("target_gap_attained") is not (generic_relative <= target)
        or not _checkpoint_close(record.get("target_relative_gap"), target)
        or record.get("target_attained") is not target_attained
        or record.get("eligible") is not maximum_passed
        or record.get("eligibility_status")
        != ("target_attained" if target_attained else "eligible_within_maximum")
        or record.get("failure_reason") is not None
        or acceptance.get("target_attained") is not target_attained
        or acceptance.get("relative_acceptance_passed") is not relative_passed
        or acceptance.get("absolute_acceptance_passed") is not absolute_passed
        or acceptance.get("maximum_acceptance_passed") is not maximum_passed
        or not _checkpoint_close(
            acceptance.get("target_relative_gap_to_feasible_incumbent"), target
        )
        or not _checkpoint_close(
            acceptance.get("maximum_accepted_relative_gap_to_feasible_incumbent"),
            maximum_relative,
        )
        or (
            maximum_absolute is None
            and acceptance.get("maximum_accepted_absolute_gap") is not None
        )
        or (
            maximum_absolute is not None
            and not _checkpoint_close(
                acceptance.get("maximum_accepted_absolute_gap"), maximum_absolute
            )
        )
    ):
        raise RuntimeError(f"Candidate checkpoint {stage} acceptance drifted")

    dual_bounds = [
        _checkpoint_number(master.get("dual_bound"), label=f"{stage} dual bound")
        for master in masters
        if isinstance(master, dict)
    ]
    if len(dual_bounds) != len(masters):
        raise RuntimeError(f"Candidate checkpoint {stage} master records drifted")
    certified = min(dual_bounds) if sense == "maximize" else max(dual_bounds)
    certificate_bound = upper if sense == "maximize" else lower
    if not _checkpoint_close(certified, certificate_bound):
        raise RuntimeError(f"Candidate checkpoint {stage} dual certificate drifted")

    expected_state_ids = tuple(state.state_id for state in context.selection.states)
    snapshot_sha = record.get("final_shared_snapshot_sha256")
    if (
        tuple(audit.get("audited_state_ids", ())) != expected_state_ids
        or len(expected_state_ids)
        != int(context.config["formal_solver"]["final_audit"]["selected_state_count"])
        or not isinstance(snapshot_sha, str)
        or not snapshot_sha
        or audit.get("shared_snapshot_sha256") != snapshot_sha
        or audit.get("reported_shared_snapshot_sha256") != snapshot_sha
        or any(
            audit.get(key) is not True
            for key in (
                "passed",
                "solution_usable",
                "shared_snapshot_fixed",
                "integer_variables_relaxed",
                "residual_audit_passed",
                "additional_audits_passed",
            )
        )
        or not _checkpoint_close(audit.get("full_feasible_objective"), feasible)
    ):
        raise RuntimeError(f"Candidate checkpoint {stage} final audit drifted")
    return {
        "lower_bound": lower,
        "upper_bound": upper,
        "absolute_gap": absolute_gap,
        "relative_gap_to_feasible_incumbent": relative_to_feasible,
    }


def _validate_formal_candidate_contract(
    candidate: _Candidate,
    context: _FrontierContext,
    ordinal: int,
) -> None:
    frontier = context.config.get("candidate_frontier")
    if not isinstance(frontier, Mapping):
        return
    deltas = tuple(float(item) for item in frontier["relative_cost_budget_deltas"])
    if not 1 <= ordinal <= len(deltas):
        raise RuntimeError("Candidate checkpoint ordinal is outside the budget grid")
    expected_delta = deltas[ordinal - 1]
    baseline_cost = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    expected_budget = baseline_cost * (1.0 + expected_delta)
    expected_hours = int(frontier["expected_hours"])
    generator_uids = tuple(
        generator.uid for generator in context.zero.scan.data.generators
    )
    reserve_provider_uids = {
        generator.uid
        for generator in context.zero.scan.data.generators
        if generator.enabled
        and generator.dispatch_mode in {"committable", "curtailable"}
        and generator.category in _RESERVE_ELIGIBLE_CATEGORIES
    }
    branch_uids = tuple(branch.uid for branch in context.zero.scan.data.branches)
    dc_uids = tuple(branch.uid for branch in context.zero.scan.data.dc_branches)
    components = (
        ("commitment", candidate.commitment, generator_uids),
        ("startup", candidate.startup, generator_uids),
        ("shutdown", candidate.shutdown, generator_uids),
        ("generation_mw", candidate.generation_mw, generator_uids),
        ("branch_flows_mw", candidate.branch_flows_mw, branch_uids),
        ("dc_flows_mw", candidate.dc_flows_mw, dc_uids),
        ("reserve_up_mw", candidate.reserve_up_mw, generator_uids),
    )
    if (
        candidate.source != "q_proxy_exact_selected_state_constraint_generation"
        or candidate.requested_candidate_id != _requested_candidate_id(expected_delta)
        or candidate.relative_cost_budget_delta != expected_delta
        or not _checkpoint_close(candidate.cost_budget_usd, expected_budget)
        or candidate.operating_cost_usd
        > expected_budget + float(frontier["cost_cap_absolute_tolerance_usd"])
        or not -1.0e-9 <= candidate.reactive_proxy_fraction <= 1.0 + 1.0e-9
        or any(
            len(rows) != expected_hours
            or any(set(row) != set(expected_uids) for row in rows)
            for _name, rows, expected_uids in components
        )
    ):
        raise RuntimeError("Candidate checkpoint formal candidate contract drifted")
    expected_startup, expected_shutdown = _boolean_transitions(
        candidate.commitment, context.initial_state.commitment
    )
    if candidate.startup != expected_startup or candidate.shutdown != expected_shutdown:
        raise RuntimeError("Candidate checkpoint commitment transition drifted")
    if any(
        reserve != 0.0
        for row in candidate.reserve_up_mw
        for uid, reserve in row.items()
        if uid not in reserve_provider_uids
    ):
        raise RuntimeError("Candidate checkpoint non-provider reserve drifted")

    proxy_certificate = _validated_stage_certificate(
        candidate, context, "proxy_maximization"
    )
    cost_certificate = _validated_stage_certificate(
        candidate, context, "cost_normalization"
    )
    if not _checkpoint_close(
        candidate.operating_cost_usd, cost_certificate["upper_bound"]
    ):
        raise RuntimeError("Candidate checkpoint operating cost certificate drifted")
    floor_tolerance = float(
        context.config["formal_solver"]["stages"]["cost_normalization"][
            "proxy_floor_absolute_tolerance"
        ]
    )
    expected_floor = proxy_certificate["lower_bound"] - floor_tolerance
    cost_record = candidate.stage_audits["cost_normalization"]
    if (
        not _checkpoint_close(cost_record.get("proxy_floor"), expected_floor)
        or candidate.reactive_proxy_fraction + floor_tolerance < expected_floor
    ):
        raise RuntimeError("Candidate checkpoint proxy floor drifted")

    regret = candidate.stage_audits.get("primary_proxy_regret")
    regret_config = context.config["formal_solver"]["primary_regret"]
    if not isinstance(regret, dict):
        raise RuntimeError("Candidate checkpoint primary regret is missing")
    observed_regret = max(
        proxy_certificate["upper_bound"] - candidate.reactive_proxy_fraction,
        0.0,
    )
    derived_allowed = (
        proxy_certificate["absolute_gap"]
        + float(regret_config["proxy_floor_tolerance"])
        + float(regret_config["numerical_audit_allowance"])
    )
    hard_maximum = float(regret_config["hard_maximum"])
    regret_passed = bool(
        observed_regret <= derived_allowed + 1.0e-12
        and observed_regret <= hard_maximum + 1.0e-12
    )
    if (
        regret.get("schema") != "rts_gmlc_primary_proxy_regret_certificate_v1"
        or regret.get("passed") is not regret_passed
        or not regret_passed
        or not _checkpoint_close(
            regret.get("stage_one_certified_upper_bound"),
            proxy_certificate["upper_bound"],
        )
        or not _checkpoint_close(
            regret.get("final_commitment_capability_proxy_fraction"),
            candidate.reactive_proxy_fraction,
        )
        or not _checkpoint_close(
            regret.get("observed_regret_upper_bound"), observed_regret
        )
        or not _checkpoint_close(
            regret.get("stage_one_actual_absolute_gap"),
            proxy_certificate["absolute_gap"],
        )
        or not _checkpoint_close(regret.get("derived_allowed_regret"), derived_allowed)
        or not _checkpoint_close(regret.get("hard_maximum"), hard_maximum)
    ):
        raise RuntimeError("Candidate checkpoint primary regret drifted")

    residual = candidate.residual_audit
    numerical_tolerance = float(
        context.config["formal_solver"]["solver"]["feasibility_tolerance"]
    )
    final_audit = cost_record["final_full_state_audit"]
    callback = final_audit.get("callback_record")
    callback_residual = (
        callback.get("residual_audit") if isinstance(callback, dict) else None
    )
    if (
        not isinstance(callback, dict)
        or not isinstance(callback_residual, dict)
        or _exact_json_text(callback_residual) != _exact_json_text(residual)
        or any(
            callback.get(key) is not True
            for key in (
                "passed",
                "cost_consistent",
                "proxy_consistent",
                "snapshot_proxy_consistent",
            )
        )
        or not _checkpoint_close(
            callback.get("actual_operating_cost_usd"),
            candidate.operating_cost_usd,
        )
        or not _checkpoint_close(
            callback.get("commitment_capability_proxy_fraction"),
            candidate.reactive_proxy_fraction,
        )
        or abs(
            _checkpoint_number(
                callback.get("maximum_shared_value_violation"),
                label="cost callback maximum shared value violation",
            )
        )
        > numerical_tolerance
        or not math.isfinite(
            _checkpoint_number(
                callback.get("actual_proxy_fraction"),
                label="cost callback actual proxy fraction",
            )
        )
    ):
        raise RuntimeError("Candidate checkpoint cost callback drifted")
    if residual.get("passed") is not True:
        raise RuntimeError("Candidate checkpoint residual audit failed")
    for key, value_ in residual.items():
        if key.startswith("maximum_") and (
            abs(_checkpoint_number(value_, label=key)) > numerical_tolerance
        ):
            raise RuntimeError(f"Candidate checkpoint residual exceeded: {key}")
        if key.endswith("_by_step") and (
            not isinstance(value_, list)
            or len(value_) != expected_hours
            or any(item is not True for item in value_)
        ):
            raise RuntimeError(f"Candidate checkpoint residual series drifted: {key}")


def _checkpoint_payload(
    context: _FrontierContext,
    ordinal: int,
    candidate: _Candidate,
) -> dict[str, object]:
    return {
        "schema": _CHECKPOINT_SCHEMA,
        "float_serialization": _CHECKPOINT_FLOAT_SERIALIZATION,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "ordinal": ordinal,
        "candidate": asdict(candidate),
    }


def _validate_checkpoint_document(
    observed: Mapping[str, Any],
    context: _FrontierContext,
    ordinal: int,
    requested_candidate_id: str,
) -> _Candidate:
    if set(observed) != _CHECKPOINT_FIELDS:
        raise RuntimeError("Candidate checkpoint serialization contract drifted")
    if (
        observed.get("schema") != _CHECKPOINT_SCHEMA
        or observed.get("float_serialization") != _CHECKPOINT_FLOAT_SERIALIZATION
    ):
        raise RuntimeError("Candidate checkpoint serialization contract drifted")
    if (
        observed.get("preregistration_id") != context.config["preregistration"]["id"]
        or observed.get("input_contract_sha256") != context.input_contract_sha256
        or observed.get("ordinal") != ordinal
        or not isinstance(observed.get("candidate"), dict)
    ):
        raise RuntimeError("Candidate checkpoint contract drifted")
    candidate = _candidate_from_checkpoint_payload(observed["candidate"])
    if candidate.requested_candidate_id != requested_candidate_id:
        raise RuntimeError("Candidate checkpoint requested ID drifted")
    _validate_formal_candidate_contract(candidate, context, ordinal)
    return candidate


def _save_candidate_checkpoint(
    context: _FrontierContext,
    output_root: Path,
    ordinal: int,
    candidate: _Candidate,
) -> _Candidate:
    # Audit records may contain tuples from dataclass serialization. Normalize the
    # in-memory object to the immutable JSON representation before identity checks.
    canonical_candidate_payload = _exact_json_payload(asdict(candidate))
    if not isinstance(canonical_candidate_payload, dict):
        raise RuntimeError("Candidate checkpoint canonicalization drifted")
    candidate = _candidate_from_checkpoint_payload(canonical_candidate_payload)
    target = _candidate_checkpoint_path(
        output_root,
        ordinal,
        candidate.requested_candidate_id,
    )
    payload = _checkpoint_payload(context, ordinal, candidate)
    expected = _exact_json_payload(payload)
    expected_text = _exact_json_text(expected)
    if target.exists():
        observed = _load_json(target, "candidate.json")
        loaded = _validate_checkpoint_document(
            observed, context, ordinal, candidate.requested_candidate_id
        )
        if _exact_json_text(observed) != expected_text or loaded != candidate:
            raise RuntimeError("Existing candidate checkpoint drifted")
        return loaded

    def writer(staging: Path) -> None:
        path = staging / "candidate.json"
        _write_exact_json(path, payload)
        observed = json.loads(path.read_text(encoding="utf-8"))
        if (
            not isinstance(observed, dict)
            or _exact_json_text(observed) != expected_text
        ):
            raise RuntimeError("Candidate checkpoint staging round-trip drifted")
        loaded = _validate_checkpoint_document(
            observed, context, ordinal, candidate.requested_candidate_id
        )
        if loaded != candidate:
            raise RuntimeError("Candidate checkpoint staging identity drifted")

    _publish_immutable_payload(target, writer)
    observed = _load_json(target, "candidate.json")
    loaded = _validate_checkpoint_document(
        observed, context, ordinal, candidate.requested_candidate_id
    )
    if _exact_json_text(observed) != expected_text or loaded != candidate:
        raise RuntimeError("Published candidate checkpoint drifted")
    return loaded


def _load_candidate_checkpoint(
    context: _FrontierContext,
    output_root: Path,
    ordinal: int,
    requested_candidate_id: str,
) -> _Candidate | None:
    target = _candidate_checkpoint_path(output_root, ordinal, requested_candidate_id)
    if not target.exists():
        return None
    observed = _load_json(target, "candidate.json")
    return _validate_checkpoint_document(
        observed, context, ordinal, requested_candidate_id
    )


def _read_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _EXPECTED_TOP_LEVEL_KEYS:
        raise ValueError("RTS-GMLC AC-aware commitment config schema drifted")
    preregistration = config["preregistration"]
    if (
        not isinstance(preregistration, dict)
        or preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4"
        or preregistration.get("schema")
        != "rts_gmlc_zero_dc_ac_aware_commitment_preregistration_v4"
        or preregistration.get("candidate_frontier_outcomes_observed") is not False
        or preregistration.get("joint_ac_outcomes_observed") is not False
        or preregistration.get("parent_first_budget_solver_outcomes_observed")
        is not True
        or preregistration.get("parent_invalid_checkpoint_payload_observed") is not True
        or preregistration.get("parent_candidate_frontier_artifact_published")
        is not False
    ):
        raise ValueError("RTS-GMLC AC-aware preregistration drifted")
    if config["protocol_amendment"] != _EXPECTED_PROTOCOL_AMENDMENT:
        raise ValueError("RTS-GMLC AC-aware protocol amendment drifted")
    if config["predecessor_v2"] != _EXPECTED_PREDECESSOR_V2:
        raise ValueError("RTS-GMLC AC-aware v2 predecessor contract drifted")
    if config["predecessor_v3"] != _EXPECTED_PREDECESSOR_V3:
        raise ValueError("RTS-GMLC AC-aware v3 predecessor contract drifted")
    if config["solver_selection_provenance"] != _EXPECTED_SOLVER_SELECTION_PROVENANCE:
        raise ValueError("RTS-GMLC AC-aware solver-selection provenance drifted")
    if config["formal_solver"] != _EXPECTED_FORMAL_SOLVER:
        raise ValueError("RTS-GMLC AC-aware formal solver contract drifted")
    if config["candidate_snapshot"] != _EXPECTED_CANDIDATE_SNAPSHOT:
        raise ValueError("RTS-GMLC AC-aware candidate snapshot contract drifted")
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
        or frontier["solver"]
        != {
            "name": "highs",
            "threads": 4,
            "random_seed": 0,
            "mip_relative_gap": 1.0e-4,
            "feasibility_tolerance": 1.0e-6,
        }
        or float(frontier["proxy_floor_absolute_tolerance"])
        != config["formal_solver"]["stages"]["cost_normalization"][
            "proxy_floor_absolute_tolerance"
        ]
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
        or joint.get("runtime_control") != _EXPECTED_JOINT_RUNTIME_CONTROL
    ):
        raise ValueError("RTS-GMLC AC-aware joint AC contract drifted")
    if config["independent_audit"] != _EXPECTED_INDEPENDENT_AUDIT:
        raise ValueError("RTS-GMLC AC-aware independent audit contract drifted")
    if config["interpretation"] != _EXPECTED_INTERPRETATION:
        raise ValueError("RTS-GMLC AC-aware interpretation contract drifted")
    if config["evidence"] != _EXPECTED_EVIDENCE:
        raise ValueError("RTS-GMLC AC-aware evidence contract drifted")
    if config["forbidden_adaptivity"] != _EXPECTED_FORBIDDEN_ADAPTIVITY or any(
        bool(value) for value in config["forbidden_adaptivity"].values()
    ):
        raise ValueError("RTS-GMLC AC-aware forbidden adaptivity was enabled")
    if config["output"] != {
        "directory": (
            "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4"
        )
    }:
        raise ValueError("RTS-GMLC AC-aware output contract drifted")
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


def _verify_manifest_hash(root: Path, expected: str, *, label: str) -> None:
    _verify_output_manifest(root)
    if _sha256(root / "SHA256SUMS") != expected:
        raise RuntimeError(f"RTS-GMLC AC-aware {label} manifest drifted")


def _verify_v3_predecessor(config: Mapping[str, Any]) -> dict[str, Any]:
    predecessor = config["predecessor_v3"]
    root = Path(predecessor["root"])
    _verify_file_hash(
        Path(predecessor["config_path"]),
        predecessor["config_sha256"],
        label="v3 predecessor config",
    )
    _verify_file_hash(
        Path(predecessor["runner_path"]),
        predecessor["runner_sha256"],
        label="v3 predecessor runner",
    )
    _verify_manifest_hash(
        root / "preregistration",
        predecessor["preregistration_manifest_sha256"],
        label="v3 predecessor preregistration",
    )
    registration = _load_json(root / "preregistration", "registration.json")
    if (
        registration.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3"
        or registration.get("input_contract_sha256")
        != predecessor["input_contract_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware v3 registration content drifted")

    _verify_manifest_hash(
        root / "invalidation",
        predecessor["invalidation_manifest_sha256"],
        label="v3 checkpoint invalidation",
    )
    invalidation = _load_json(root / "invalidation", "invalidation.json")
    exact_fields = (
        "required_status",
        "valid_budget_candidate_checkpoint_count",
        "invalid_budget_candidate_checkpoint_count",
        "invalid_checkpoint_relative_path",
        "invalid_checkpoint_manifest_sha256",
        "stored_dispatch_sha256",
        "recomputed_persisted_dispatch_sha256",
        "candidate_frontier_artifact_published",
        "joint_ac_solver_call_count",
        "joint_ac_outcomes_observed",
        "failure_is_infeasibility_evidence",
        "invalid_checkpoint_is_resume_eligible",
        "v3_resume_allowed",
        "successor_must_use_new_preregistration_id",
        "parent_first_budget_solver_outcomes_observed",
        "parent_invalid_checkpoint_payload_observed",
    )
    for key in exact_fields:
        source_key = "status" if key == "required_status" else key
        if invalidation.get(source_key) != predecessor[key]:
            raise RuntimeError(
                f"RTS-GMLC AC-aware v3 invalidation field drifted: {source_key}"
            )
    if (
        invalidation.get("input_contract_sha256")
        != predecessor["input_contract_sha256"]
        or invalidation.get("scientific_inputs_or_ac_outcomes_changed") is not False
    ):
        raise RuntimeError("RTS-GMLC AC-aware v3 invalidation content drifted")

    checkpoint = root / predecessor["invalid_checkpoint_relative_path"]
    _verify_manifest_hash(
        checkpoint,
        predecessor["invalid_checkpoint_manifest_sha256"],
        label="v3 invalid checkpoint",
    )
    checkpoint_root = root / "candidate_checkpoints"
    if {path.resolve() for path in checkpoint_root.iterdir()} != {checkpoint.resolve()}:
        raise RuntimeError("RTS-GMLC AC-aware v3 checkpoint inventory drifted")
    if any((root / name).exists() for name in ("candidate_frontier", "joint_ac")):
        raise RuntimeError("RTS-GMLC AC-aware v3 predecessor gained formal results")
    if any(path.name.startswith(".") for path in root.iterdir()):
        raise RuntimeError("RTS-GMLC AC-aware v3 predecessor gained staging artifacts")
    return {
        "manifest_sha256": predecessor["invalidation_manifest_sha256"],
        "status": invalidation["status"],
        "valid_budget_candidate_checkpoint_count": 0,
        "invalid_budget_candidate_checkpoint_count": 1,
        "candidate_frontier_artifact_published": False,
        "joint_ac_solver_call_count": 0,
        "v3_resume_allowed": False,
    }


def _verify_solver_predecessors(config: Mapping[str, Any]) -> dict[str, Any]:
    v3_predecessor = _verify_v3_predecessor(config)
    predecessor = config["predecessor_v2"]
    predecessor_root = Path(predecessor["root"])
    _verify_file_hash(
        Path(predecessor["config_path"]),
        predecessor["config_sha256"],
        label="v2 predecessor config",
    )
    _verify_file_hash(
        Path(predecessor["runner_path"]),
        predecessor["runner_sha256"],
        label="v2 predecessor runner",
    )
    _verify_manifest_hash(
        predecessor_root / "preregistration",
        predecessor["preregistration_manifest_sha256"],
        label="v2 predecessor preregistration",
    )
    termination_root = predecessor_root / "operational_termination"
    _verify_manifest_hash(
        termination_root,
        predecessor["operational_termination_manifest_sha256"],
        label="v2 operational termination",
    )
    termination = _load_json(termination_root, "termination.json")
    if (
        termination.get("status") != predecessor["required_status"]
        or termination.get("input_contract_sha256")
        != predecessor["input_contract_sha256"]
        or termination.get("candidate_frontier_artifact_published")
        is not predecessor["candidate_frontier_artifact_published"]
        or termination.get("partial_candidate_solution_persisted")
        is not predecessor["partial_candidate_solution_persisted"]
        or termination.get("joint_ac_solver_call_count")
        != predecessor["joint_ac_solver_call_count"]
        or termination.get("termination_is_infeasibility_evidence")
        is not predecessor["termination_is_infeasibility_evidence"]
        or termination.get("scientific_inputs_or_ac_outcomes_changed") is not False
    ):
        raise RuntimeError("RTS-GMLC AC-aware v2 termination content drifted")
    if any(
        (predecessor_root / name).exists()
        for name in ("candidate_checkpoints", "candidate_frontier", "joint_ac")
    ):
        raise RuntimeError("RTS-GMLC AC-aware v2 predecessor gained formal results")

    provenance = config["solver_selection_provenance"]
    inventory_config = provenance["solver_inventory"]
    inventory_root = Path(inventory_config["root"])
    _verify_manifest_hash(
        inventory_root,
        inventory_config["manifest_sha256"],
        label="solver inventory",
    )
    inventory = _load_json(inventory_root, "inventory.json")
    eligibility = inventory.get("eligibility")
    if not isinstance(eligibility, dict):
        raise RuntimeError("RTS-GMLC AC-aware solver inventory eligibility drifted")
    eligible_for_formal = sorted(
        name
        for name, record in eligibility.items()
        if isinstance(record, dict) and record.get("eligible_for_formal") is True
    )
    expected_size = config["formal_solver"]["expected_full_model_size"]
    inventory_size = inventory.get("model_sizes", {}).get(
        "formal_24h_candidate_proxy_stage"
    )
    if (
        inventory.get("schema") != inventory_config["required_schema"]
        or inventory.get("status") != inventory_config["required_status"]
        or inventory.get("formal_candidate_started")
        is not inventory_config["formal_candidate_started"]
        or inventory.get("project_model_built_or_solved")
        is not inventory_config["project_model_built_or_solved"]
        or eligible_for_formal != [inventory_config["only_formally_eligible_solver"]]
        or inventory_size
        != {
            "variables": expected_size["proxy_stage_variables"],
            "constraints": expected_size["proxy_stage_constraints"],
        }
    ):
        raise RuntimeError("RTS-GMLC AC-aware solver inventory content drifted")

    benchmark_config = provenance["thread_benchmark"]
    benchmark_root = Path(benchmark_config["root"])
    _verify_manifest_hash(
        benchmark_root / "preparation",
        benchmark_config["preparation_manifest_sha256"],
        label="thread benchmark preparation",
    )
    benchmark_result_root = benchmark_root / "benchmark"
    _verify_manifest_hash(
        benchmark_result_root,
        benchmark_config["result_manifest_sha256"],
        label="thread benchmark result",
    )
    _verify_file_hash(
        benchmark_result_root / "summary.json",
        benchmark_config["summary_sha256"],
        label="thread benchmark summary",
    )
    benchmark = _load_json(benchmark_result_root, "summary.json")
    benchmark_selection = benchmark.get("selection", {})
    if (
        benchmark_selection.get("status")
        != benchmark_config["required_selection_status"]
        or benchmark_selection.get("selected_threads")
        != benchmark_config["selected_threads"]
        or benchmark_selection.get("objective_value_used")
        is not benchmark_config["objective_value_used_for_selection"]
        or benchmark.get("objective_value_used_for_selection")
        is not benchmark_config["objective_value_used_for_selection"]
        or benchmark.get("formal_candidate_result")
        is not benchmark_config["formal_candidate_result"]
        or benchmark.get("candidate_frontier_published") is not False
        or benchmark.get("joint_ac_solver_call_count") != 0
        or benchmark.get("input_contract_sha256")
        != predecessor["input_contract_sha256"]
        or benchmark.get("all_matrix_entries_attempted") is not True
    ):
        raise RuntimeError("RTS-GMLC AC-aware thread benchmark content drifted")

    pilot_config = provenance["formulation_pilot"]
    pilot_root = Path(pilot_config["root"])
    _verify_manifest_hash(
        pilot_root / "preparation",
        pilot_config["preparation_manifest_sha256"],
        label="formulation pilot preparation",
    )
    pilot_result_root = pilot_root / "comparison"
    _verify_manifest_hash(
        pilot_result_root,
        pilot_config["result_manifest_sha256"],
        label="formulation pilot result",
    )
    _verify_file_hash(
        pilot_result_root / "summary.json",
        pilot_config["summary_sha256"],
        label="formulation pilot summary",
    )
    pilot = _load_json(pilot_result_root, "summary.json")
    pilot_selection = pilot.get("selection", {})
    formulation_records = pilot_selection.get("formulations", [])
    exact_record = next(
        (
            record
            for record in formulation_records
            if isinstance(record, dict)
            and record.get("formulation") == pilot_config["selected_formulation"]
        ),
        None,
    )
    if (
        pilot_selection.get("status") != pilot_config["required_selection_status"]
        or pilot_selection.get("selected_formulation")
        != pilot_config["selected_formulation"]
        or pilot_selection.get("objective_value_used")
        is not pilot_config["objective_value_used_for_selection"]
        or pilot.get("objective_value_used_for_selection")
        is not pilot_config["objective_value_used_for_selection"]
        or pilot.get("formal_candidate_result")
        is not pilot_config["formal_candidate_result"]
        or pilot.get("input_contract_sha256") != pilot_config["input_contract_sha256"]
        or pilot.get("preparation_manifest_sha256")
        != pilot_config["preparation_manifest_sha256"]
        or pilot.get("all_runs_attempted") is not True
        or pilot.get("joint_ac_solver_call_count") != 0
        or pilot.get("threads") != config["formal_solver"]["solver"]["threads"]
        or not isinstance(exact_record, dict)
        or exact_record.get("eligible") is not True
        or exact_record.get("eligible_repetitions")
        != pilot_config["required_eligible_repetitions"]
        or exact_record.get("completed_repetitions")
        != pilot_config["required_completed_repetitions"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware formulation pilot content drifted")

    warm_config = provenance["initial_proxy_warm_start"]
    warm_root = Path(warm_config["root"])
    _verify_manifest_hash(
        warm_root / "preparation",
        warm_config["preparation_manifest_sha256"],
        label="initial proxy warm-start preparation",
    )
    warm_result_root = warm_root / "benchmark"
    _verify_manifest_hash(
        warm_result_root,
        warm_config["result_manifest_sha256"],
        label="initial proxy warm-start result",
    )
    _verify_file_hash(
        warm_result_root / "summary.json",
        warm_config["summary_sha256"],
        label="initial proxy warm-start summary",
    )
    _verify_file_hash(
        Path(warm_config["adapter_source_path"]),
        warm_config["adapter_source_sha256"],
        label="initial proxy warm-start adapter source",
    )
    warm_summary = _load_json(warm_result_root, "summary.json")
    warm_selection = warm_summary.get("selection")
    warm_methods = (
        warm_selection.get("methods") if isinstance(warm_selection, dict) else None
    )
    selected_warm_method = next(
        (
            record
            for record in warm_methods or ()
            if isinstance(record, dict)
            and record.get("method") == warm_config["selected_method"]
        ),
        None,
    )
    if (
        not isinstance(warm_selection, dict)
        or warm_summary.get("benchmark_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v3"
        or warm_selection.get("status") != warm_config["required_selection_status"]
        or warm_selection.get("selected_method") != warm_config["selected_method"]
        or warm_selection.get("objective_value_used")
        is not warm_config["objective_value_used_for_selection"]
        or warm_summary.get("objective_value_used_for_selection")
        is not warm_config["objective_value_used_for_selection"]
        or warm_summary.get("formal_candidate_result")
        is not warm_config["formal_candidate_result"]
        or warm_summary.get("joint_ac_solver_call_count") != 0
        or warm_summary.get("all_runs_attempted") is not True
        or not isinstance(selected_warm_method, dict)
        or selected_warm_method.get("completed_repetitions")
        != warm_config["selected_method_completed_repetitions"]
        or selected_warm_method.get("eligible_repetitions")
        != warm_config["selected_method_eligible_repetitions"]
        or selected_warm_method.get("eligible") is not True
    ):
        raise RuntimeError(
            "RTS-GMLC AC-aware initial proxy warm-start evidence drifted"
        )

    return {
        "v3_checkpoint_invalidation": v3_predecessor,
        "v2_operational_termination": {
            "manifest_sha256": predecessor["operational_termination_manifest_sha256"],
            "status": termination["status"],
            "candidate_frontier_artifact_published": False,
            "partial_candidate_solution_persisted": False,
            "joint_ac_solver_call_count": 0,
            "termination_is_infeasibility_evidence": False,
        },
        "solver_inventory": {
            "manifest_sha256": inventory_config["manifest_sha256"],
            "only_formally_eligible_solver": eligible_for_formal[0],
            "formal_proxy_stage_model_size": inventory_size,
        },
        "thread_benchmark": {
            "preparation_manifest_sha256": benchmark_config[
                "preparation_manifest_sha256"
            ],
            "result_manifest_sha256": benchmark_config["result_manifest_sha256"],
            "selected_threads": benchmark_selection["selected_threads"],
            "selection_status": benchmark_selection["status"],
        },
        "formulation_pilot": {
            "preparation_manifest_sha256": pilot_config["preparation_manifest_sha256"],
            "result_manifest_sha256": pilot_config["result_manifest_sha256"],
            "selected_formulation": pilot_selection["selected_formulation"],
            "selection_status": pilot_selection["status"],
            "eligible_repetitions": exact_record["eligible_repetitions"],
        },
        "initial_proxy_warm_start": {
            "preparation_manifest_sha256": warm_config["preparation_manifest_sha256"],
            "result_manifest_sha256": warm_config["result_manifest_sha256"],
            "selected_method": warm_selection["selected_method"],
            "selection_status": warm_selection["status"],
            "eligible_repetitions": selected_warm_method["eligible_repetitions"],
        },
    }


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
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )


def _publish_immutable_payload(
    target: Path,
    writer: Callable[[Path], None],
    *,
    validator: Callable[[Path], None] | None = None,
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Immutable artifact already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        writer(staging)
        _write_manifest(staging)
        _verify_output_manifest(staging)
        if validator is not None:
            validator(staging)
        if target.exists():
            raise FileExistsError(f"Immutable artifact already exists: {target}")
        staging.rename(target)
        _verify_output_manifest(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _exact_json_payload(payload: object) -> object:
    return json.loads(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _exact_json_text(payload: object) -> str:
    return json.dumps(
        payload,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def _json_delta_paths(
    parent: object,
    successor: object,
    *,
    prefix: str = "",
) -> tuple[str, ...]:
    if isinstance(parent, Mapping) and isinstance(successor, Mapping):
        paths: list[str] = []
        keys = sorted(set(parent) | set(successor), key=str)
        for key in keys:
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in parent or key not in successor:
                paths.append(path)
                continue
            paths.extend(_json_delta_paths(parent[key], successor[key], prefix=path))
        return tuple(paths)
    if isinstance(parent, list) and isinstance(successor, list):
        if len(parent) != len(successor):
            return (prefix,)
        paths = []
        for index, (parent_item, successor_item) in enumerate(
            zip(parent, successor, strict=True)
        ):
            paths.extend(
                _json_delta_paths(
                    parent_item,
                    successor_item,
                    prefix=f"{prefix}[{index}]",
                )
            )
        return tuple(paths)
    return () if parent == successor else (prefix,)


def _repair_required(context: _FrontierContext) -> bool:
    implementation = context.input_contract.get("implementation_sha256")
    return isinstance(implementation, Mapping) and (
        implementation.get(_RUNNER_PATH.as_posix()) != _REPAIR_PARENT_RUNNER_SHA256
        or implementation.get(_WARMSTART_ADAPTER_PATH.as_posix())
        != _REPAIR_PARENT_ADAPTER_SHA256
    )


def _repair_parent_registration() -> dict[str, Any]:
    target = _REPAIR_PARENT_OUTPUT_ROOT / "preregistration"
    _verify_output_manifest(target)
    if _sha256(target / "SHA256SUMS") != _REPAIR_PARENT_PREREGISTRATION_MANIFEST_SHA256:
        raise RuntimeError("RTS-GMLC AC-aware repair parent manifest drifted")
    registration = _load_json(target, "registration.json")
    contract = registration.get("input_contract")
    implementation = (
        contract.get("implementation_sha256") if isinstance(contract, Mapping) else None
    )
    amendment_reference = registration.get("implementation_repair_amendment")
    if (
        registration.get("input_contract_sha256")
        != _REPAIR_PARENT_INPUT_CONTRACT_SHA256
        or not isinstance(contract, dict)
        or common_input_signature_sha256(contract)
        != _REPAIR_PARENT_INPUT_CONTRACT_SHA256
        or contract.get("config_sha256") != _REPAIR_FROZEN_CONFIG_SHA256
        or not isinstance(implementation, Mapping)
        or implementation.get(_RUNNER_PATH.as_posix()) != _REPAIR_PARENT_RUNNER_SHA256
        or implementation.get(_WARMSTART_ADAPTER_PATH.as_posix())
        != _REPAIR_PARENT_ADAPTER_SHA256
        or not isinstance(amendment_reference, Mapping)
        or amendment_reference.get("content_sha256")
        != _REPAIR_PARENT_AMENDMENT_CONTENT_SHA256
        or registration.get("candidate_frontier_outcomes_observed") is not False
        or registration.get("joint_ac_outcomes_observed") is not False
        or registration.get("parent_candidate_frontier_artifact_published") is not False
    ):
        raise RuntimeError("RTS-GMLC AC-aware repair parent registration drifted")
    parent_amendment = _load_json(target, _REPAIR_AMENDMENT_NAME)
    if (
        common_input_signature_sha256(parent_amendment)
        != _REPAIR_PARENT_AMENDMENT_CONTENT_SHA256
        or parent_amendment.get("successor_preregistration", {}).get(
            "input_contract_sha256"
        )
        != _REPAIR_PARENT_INPUT_CONTRACT_SHA256
    ):
        raise RuntimeError("RTS-GMLC AC-aware chained repair amendment drifted")
    if (
        (_REPAIR_PARENT_OUTPUT_ROOT / "candidate_frontier").exists()
        or (_REPAIR_PARENT_OUTPUT_ROOT / "joint_ac").exists()
        or any((_REPAIR_PARENT_OUTPUT_ROOT / "candidate_checkpoints").glob("*"))
    ):
        raise RuntimeError("RTS-GMLC AC-aware repair parent gained formal results")
    return registration


def _verify_repair_failure_artifacts() -> None:
    for path_text, expected_sha256 in _REPAIR_FAILURE_ARTIFACTS.items():
        _verify_file_hash(
            Path(path_text),
            expected_sha256,
            label=f"repair failure evidence {path_text}",
        )
    progress_path = Path(
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4/"
        "formal_repair_20260719T165115Z/progress.jsonl"
    )
    events = [
        json.loads(line)
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    event_names = [event.get("event") for event in events]
    master_calls = [
        event for event in events if event.get("event") == "exact_cg_call_started"
    ]
    if (
        len(events) != 49
        or len(master_calls) != 1
        or master_calls[0].get("call_id") != "proxy_maximization.iteration_01.master"
        or master_calls[0].get("kind") != "master"
        or master_calls[0].get("iteration") != 1
        or master_calls[0].get("stage") != "proxy_maximization"
        or "formal_initial_proxy_warm_start_submitted" in event_names
        or any(
            name
            in {
                "candidate_checkpoint_loaded",
                "candidate_failed",
                "candidate_frontier_published",
                "frontier_published",
                "attempt_completed",
                "attempt_failed",
            }
            for name in event_names
        )
        or event_names[-1] != "heartbeat"
    ):
        raise RuntimeError("RTS-GMLC AC-aware warm-start failure evidence drifted")
    native_log = Path(
        "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4/"
        "formal_repair_20260719T165115Z/01_q_proxy_delta_0p0010/"
        "proxy_maximization/proxy_maximization__iteration_01__master.log"
    ).read_text(encoding="utf-8")
    native_lower = native_log.lower()
    if (
        "mip start" in native_lower
        or "bestsol" not in native_lower
        or "-inf" not in native_lower
        or "solving report" in native_lower
    ):
        raise RuntimeError("RTS-GMLC AC-aware cold-start native evidence drifted")
    lease_path = (
        _REPAIR_PARENT_OUTPUT_ROOT / "execution_lease" / "active" / "lease.json"
    )
    lease = json.loads(lease_path.read_text(encoding="utf-8"))
    if (
        lease.get("attempt_id") != "formal_repair_20260719T165115Z"
        or lease.get("pid") != 4684
        or lease.get("stage") != "generate_candidates"
        or probe_process(4684) is not False
    ):
        raise RuntimeError("RTS-GMLC AC-aware dead repair lease evidence drifted")


def _repair_amendment_payload(
    context: _FrontierContext,
    output_root: Path,
) -> dict[str, object]:
    if output_root.resolve() == _REPAIR_PARENT_OUTPUT_ROOT.resolve():
        raise RuntimeError("Repair successor requires a new immutable output root")
    parent_registration = _repair_parent_registration()
    _verify_repair_failure_artifacts()
    if _sha256(context.config_path) != _REPAIR_FROZEN_CONFIG_SHA256:
        raise RuntimeError("RTS-GMLC AC-aware frozen repair config drifted")
    if (
        context.config_path.read_bytes()
        != (_REPAIR_PARENT_OUTPUT_ROOT / "preregistration" / "config.yaml").read_bytes()
    ):
        raise RuntimeError("RTS-GMLC AC-aware frozen repair config bytes drifted")
    _verify_file_hash(
        Path("src/grid/rts_gmlc_ac_aware_commitment.py"),
        _REPAIR_SHARED_AC_CORE_SHA256,
        label="repair shared AC-aware core",
    )
    parent_contract = parent_registration["input_contract"]
    delta_paths = _json_delta_paths(parent_contract, context.input_contract)
    expected_delta = (
        f"implementation_sha256.{_RUNNER_PATH.as_posix()}",
        f"implementation_sha256.{_WARMSTART_ADAPTER_PATH.as_posix()}",
    )
    if delta_paths != expected_delta:
        raise RuntimeError(
            "RTS-GMLC AC-aware repair exceeded its registered implementation scope"
        )
    current_implementation = context.input_contract["implementation_sha256"]
    current_runner_sha256 = current_implementation[_RUNNER_PATH.as_posix()]
    current_adapter_sha256 = current_implementation[_WARMSTART_ADAPTER_PATH.as_posix()]
    if current_runner_sha256 != _sha256(_RUNNER_PATH):
        raise RuntimeError("RTS-GMLC AC-aware repaired runner identity drifted")
    if (
        current_adapter_sha256 != _REPAIR_SUCCESSOR_ADAPTER_SHA256
        or current_adapter_sha256 != _sha256(_WARMSTART_ADAPTER_PATH)
    ):
        raise RuntimeError("RTS-GMLC AC-aware repaired warm-start adapter drifted")
    test_hashes = {
        path.as_posix(): _sha256(path) for path in _REPAIR_TEST_PATHS if path.is_file()
    }
    if len(test_hashes) != len(_REPAIR_TEST_PATHS):
        raise RuntimeError("RTS-GMLC AC-aware repair test evidence is missing")
    return {
        "schema": _REPAIR_AMENDMENT_SCHEMA,
        "amendment_id": _REPAIR_AMENDMENT_ID,
        "status": "implementation_only_repair_preregistered_before_successor_run",
        "scope": "initial_proxy_warm_start_first_master_scope_correction_only",
        "successor_output_directory": output_root.as_posix(),
        "parent_preregistration": {
            "output_directory": _REPAIR_PARENT_OUTPUT_ROOT.as_posix(),
            "manifest_sha256": _REPAIR_PARENT_PREREGISTRATION_MANIFEST_SHA256,
            "input_contract_sha256": _REPAIR_PARENT_INPUT_CONTRACT_SHA256,
            "runner_sha256": _REPAIR_PARENT_RUNNER_SHA256,
            "warm_start_adapter_sha256": _REPAIR_PARENT_ADAPTER_SHA256,
            "implementation_repair_amendment_content_sha256": (
                _REPAIR_PARENT_AMENDMENT_CONTENT_SHA256
            ),
            "candidate_frontier_artifact_published": False,
            "valid_budget_candidate_checkpoint_count": 0,
            "joint_ac_solver_call_count": 0,
        },
        "successor_preregistration": {
            "input_contract_sha256": context.input_contract_sha256,
            "runner_sha256": current_runner_sha256,
            "warm_start_adapter_sha256": current_adapter_sha256,
        },
        "root_cause": {
            "failure": (
                "warm_start_scope_predicate_used_the_wrong_exact_CG_iteration_"
                "ordinal_so_proxy_maximization_iteration_01_used_the_cold_"
                "FormalCgModelAdapter_path"
            ),
            "permitted_correction": (
                "match_the_one_based_exact_CG_iteration_01_master_and_preserve_"
                "all_warm_start_mapping_submission_and_acceptance_gates"
            ),
            "model_or_feasible_region_changed": False,
            "solver_options_changed": False,
            "warm_start_values_changed": False,
            "acceptance_evidence_gates_weakened": False,
        },
        "implementation_delta": {
            "old_runner_sha256": _REPAIR_PARENT_RUNNER_SHA256,
            "new_runner_sha256": current_runner_sha256,
            "old_warm_start_adapter_sha256": _REPAIR_PARENT_ADAPTER_SHA256,
            "new_warm_start_adapter_sha256": current_adapter_sha256,
            "input_contract_delta_paths": list(delta_paths),
            "all_other_registered_implementation_hashes_unchanged": True,
        },
        "frozen_protocol_proof": {
            "config_path": context.config_path.as_posix(),
            "old_config_sha256": _REPAIR_FROZEN_CONFIG_SHA256,
            "new_config_sha256": _sha256(context.config_path),
            "config_bytes_identical_to_parent_preregistration": True,
            "shared_ac_aware_core_sha256": _REPAIR_SHARED_AC_CORE_SHA256,
            "exact_cg_runner_sha256": (
                "50933c925ead6051a376b0773e2687505f42e2db222a3f9a3f141d6e864a036f"
            ),
            "model_changed": False,
            "candidate_budget_grid_changed": False,
            "solver_or_algorithm_changed": False,
            "time_limits_changed": False,
            "acceptance_thresholds_changed": False,
            "joint_ac_protocol_changed": False,
            "scientific_interpretation_changed": False,
            "formal_solver": context.input_contract["formal_solver"],
            "candidate_budget_grid": context.input_contract["candidate_frontier"][
                "relative_cost_budget_deltas"
            ],
            "candidate_frontier_contract_sha256": common_input_signature_sha256(
                context.input_contract["candidate_frontier"]
            ),
            "joint_ac_contract_sha256": common_input_signature_sha256(
                context.input_contract["joint_ac"]
            ),
        },
        "failed_attempts": [
            {
                "attempt_id": "formal_repair_20260719T165115Z",
                "pid": 4684,
                "pid_confirmed_dead_before_amendment": True,
                "terminal_state": "process_ended_without_terminal_progress_event",
                "failure_classification": "implementation_scope_failure",
                "first_master_execution_mode": "cold_start",
                "formal_initial_proxy_warm_start_submitted_event_count": 0,
                "native_mip_start_acceptance_line_count": 0,
                "native_mip_start_rejection_line_count": 0,
                "last_native_best_solution": "-inf",
                "completed_budget_candidate_checkpoint_count": 0,
                "candidate_frontier_artifact_published": False,
                "joint_ac_solver_call_count": 0,
                "formal_result_published": False,
                "eligible_for_resume": False,
                "failure_is_infeasibility_evidence": False,
            },
        ],
        "failure_artifact_sha256": dict(_REPAIR_FAILURE_ARTIFACTS),
        "verification_evidence": {
            "test_source_sha256": test_hashes,
            "warm_start_scope_repair_executor": {
                "targeted_scope": "2 passed, 33 deselected",
                "broader_v4_before_second_amendment": "58 passed, 2 failed",
                "broader_v4_failure_classification": (
                    "both_failures_were_expected_old_amendment_rejections_of_"
                    "the_adapter_SHA_drift"
                ),
                "ruff": "passed",
                "py_compile": "passed",
            },
            "warm_start_scope_repair_independent_review": {
                "verdict": "PASS",
                "targeted_scope": "2 passed",
                "exact_cg": "18 passed",
                "combined_before_second_amendment": "53 passed, 2 failed",
                "combined_failure_classification": (
                    "both_failures_were_expected_old_amendment_rejections_of_"
                    "the_adapter_SHA_drift"
                ),
                "ruff": "passed",
                "black": "passed",
                "py_compile": "passed",
                "full_column_submission_gate_preserved": True,
                "highs_status_k_ok_gate_preserved": True,
                "native_acceptance_exactly_one_gate_preserved": True,
                "native_rejection_zero_gate_preserved": True,
                "external_signature_claimed": False,
            },
        },
    }


def _repair_amendment_reference(payload: Mapping[str, object]) -> dict[str, str]:
    return {
        "schema": _REPAIR_AMENDMENT_SCHEMA,
        "amendment_id": _REPAIR_AMENDMENT_ID,
        "relative_path": _REPAIR_AMENDMENT_NAME,
        "content_sha256": common_input_signature_sha256(payload),
    }


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
    verified_solver_predecessors = _verify_solver_predecessors(config)
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
        "schema": "rts_gmlc_zero_dc_ac_aware_commitment_inputs_v4",
        "config_sha256": _sha256(config_path),
        "predecessor_v2": config["predecessor_v2"],
        "predecessor_v3": config["predecessor_v3"],
        "solver_selection_provenance": config["solver_selection_provenance"],
        "verified_solver_predecessors": verified_solver_predecessors,
        "formal_solver": config["formal_solver"],
        "candidate_snapshot": config["candidate_snapshot"],
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
    repair_amendment = (
        _repair_amendment_payload(context, output_root)
        if _repair_required(context)
        else None
    )
    payload = {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "previous_ac_outcomes_observed": True,
        "candidate_frontier_outcomes_observed": False,
        "joint_ac_outcomes_observed": False,
        "parent_first_budget_solver_outcomes_observed": True,
        "parent_invalid_checkpoint_payload_observed": True,
        "parent_candidate_frontier_artifact_published": False,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if repair_amendment is not None:
        payload["implementation_repair_amendment"] = _repair_amendment_reference(
            repair_amendment
        )
    if target.exists():
        observed = _load_json(target, "registration.json")
        if _exact_json_text(observed) != _exact_json_text(_exact_json_payload(payload)):
            raise RuntimeError("Published RTS-GMLC AC-aware registration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC AC-aware config drifted")
        if repair_amendment is not None:
            observed_amendment = _load_json(target, _REPAIR_AMENDMENT_NAME)
            if _exact_json_text(observed_amendment) != _exact_json_text(
                _exact_json_payload(repair_amendment)
            ):
                raise RuntimeError(
                    "Published RTS-GMLC AC-aware repair amendment drifted"
                )
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare beside existing AC-aware artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_exact_json(staging / "registration.json", payload)
        if repair_amendment is not None:
            _write_exact_json(
                staging / _REPAIR_AMENDMENT_NAME,
                repair_amendment,
            )

    _publish_immutable_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _FrontierContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    registration = _load_json(target, "registration.json")
    preregistration = context.config["preregistration"]
    expected = {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "previous_ac_outcomes_observed": True,
        "candidate_frontier_outcomes_observed": False,
        "joint_ac_outcomes_observed": False,
        "parent_first_budget_solver_outcomes_observed": True,
        "parent_invalid_checkpoint_payload_observed": True,
        "parent_candidate_frontier_artifact_published": False,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    repair_amendment = None
    if _repair_required(context):
        repair_amendment = _repair_amendment_payload(context, output_root)
        expected["implementation_repair_amendment"] = _repair_amendment_reference(
            repair_amendment
        )
    if _exact_json_text(registration) != _exact_json_text(
        _exact_json_payload(expected)
    ):
        raise RuntimeError("RTS-GMLC AC-aware registration payload drifted")
    if (
        common_input_signature_sha256(registration["input_contract"])
        != context.input_contract_sha256
    ):
        raise RuntimeError("RTS-GMLC AC-aware published contract content hash drifted")
    if (target / "config.yaml").read_bytes() != context.config_path.read_bytes():
        raise RuntimeError("RTS-GMLC AC-aware live config drifted")
    if repair_amendment is not None:
        observed_amendment = _load_json(target, _REPAIR_AMENDMENT_NAME)
        if common_input_signature_sha256(observed_amendment) != expected[
            "implementation_repair_amendment"
        ]["content_sha256"] or _exact_json_text(observed_amendment) != _exact_json_text(
            _exact_json_payload(repair_amendment)
        ):
            raise RuntimeError("RTS-GMLC AC-aware repair amendment drifted")
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


def _extract_reserve(model: Any, scuc_context: Any) -> tuple[dict[str, float], ...]:
    reserve_uids = set(scuc_context.reserve_uids)
    return tuple(
        {
            uid: (
                float(value(model.reserve_up[time, uid]))
                if uid in reserve_uids
                else 0.0
            )
            for uid in scuc_context.generator_by_uid
        }
        for time in range(len(scuc_context.points))
    )


def _requested_candidate_id(relative_delta: float) -> str:
    return "q_proxy_delta_" + format(relative_delta, ".4f").replace(".", "p")


def _constraint_generation_seed(context: _FrontierContext) -> tuple[str, ...]:
    summary = _load_json(_ZERO_OUTPUT_ROOT / "dc_dispatch", "summary.json")
    seed = tuple(
        str(item)
        for item in summary["constraint_generation_audit"]["final_active_state_ids"]
    )
    all_state_ids = tuple(str(state.state_id) for state in context.selection.states)
    if (
        not seed
        or seed[0] != "normal"
        or len(seed) != len(set(seed))
        or not set(seed) <= set(all_state_ids)
    ):
        raise RuntimeError("RTS-GMLC exact-CG seed state contract drifted")
    return seed


def _formal_problem(
    context: _FrontierContext, *, cost_budget_usd: float
) -> formulation._Problem:
    tolerance = float(
        context.config["formal_solver"]["solver"]["feasibility_tolerance"]
    )
    points = tuple(_validate_inputs(context.zero.scan.data, context.request, tolerance))
    states = tuple(context.selection.states)
    all_state_ids = tuple(str(state.state_id) for state in states)
    if (
        len(points) != 24
        or len(states)
        != int(context.config["formal_solver"]["final_audit"]["selected_state_count"])
        or not all_state_ids
        or all_state_ids[0] != "normal"
        or len(all_state_ids) != len(set(all_state_ids))
    ):
        raise RuntimeError("RTS-GMLC formal exact-CG problem contract drifted")
    baseline = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    return formulation._Problem(
        parent_context=context,
        request=context.request,
        points=points,
        states=states,
        all_state_ids=all_state_ids,
        initial_active_state_ids=_constraint_generation_seed(context),
        cost_budget_usd=float(cost_budget_usd),
        parent_full_cost_usd=baseline,
        parent_horizon_cost_usd=baseline,
    )


def _stage_time_limits(
    formal_solver: Mapping[str, Any], stage: str
) -> ExactCgTimeLimits:
    limits = formal_solver["time_limits_seconds"]
    master_key = (
        "proxy_master_per_call"
        if stage == "proxy_maximization"
        else "cost_master_per_call"
    )
    return ExactCgTimeLimits(
        master_seconds=float(limits[master_key]),
        screen_seconds=float(limits["inactive_state_screen_per_call"]),
        final_audit_seconds=float(limits["final_full_state_audit_per_call"]),
    )


def _solve_frontier_candidate(
    context: _FrontierContext,
    *,
    relative_delta: float,
    progress: JsonlProgressWriter,
    candidate_log_root: Path,
    candidate_ordinal: int,
    deadline_monotonic: float,
) -> _Candidate:
    frontier = context.config["candidate_frontier"]
    formal_solver = context.config["formal_solver"]
    baseline_cost = float(
        context.config["parent_zero_control"]["baseline_full_state_cost_usd"]
    )
    cost_budget = baseline_cost * (1.0 + relative_delta)
    problem = _formal_problem(context, cost_budget_usd=cost_budget)
    requested_id = _requested_candidate_id(relative_delta)
    event_context = {
        "candidate_ordinal": candidate_ordinal,
        "requested_candidate_id": requested_id,
        "relative_cost_budget_delta": relative_delta,
    }
    adapter = V4InitialProxyWarmStartAdapter(
        problem=problem,
        formal_solver=formal_solver,
        candidate_frontier=frontier,
        snapshot_contract=context.config["candidate_snapshot"],
        progress=progress,
        log_root=candidate_log_root,
        event_context=event_context,
        warm_start=context.config["solver_selection_provenance"][
            "initial_proxy_warm_start"
        ],
    )
    proxy_spec = formal_solver["stages"]["proxy_maximization"]
    proxy_result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=problem.all_state_ids,
        seed_state_ids=problem.initial_active_state_ids,
        target_relative_gap=float(proxy_spec["target_relative_gap"]),
        maximum_accepted_relative_gap_to_feasible_incumbent=float(
            proxy_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_accepted_absolute_gap=float(
            proxy_spec["maximum_accepted_absolute_gap"]
        ),
        time_limits=_stage_time_limits(formal_solver, "proxy_maximization"),
        callbacks=adapter.callbacks(),
        candidate_deadline_monotonic=deadline_monotonic,
    )
    if proxy_result.snapshot is None:
        raise RuntimeError(
            "RTS-GMLC exact-CG proxy stage failed: "
            + str(proxy_result.stage_record["failure_reason"])
        )
    proxy_certificate = proxy_result.stage_record["certificate"]
    proxy_feasible = float(proxy_certificate["lower_bound"])
    floor_tolerance = float(
        formal_solver["stages"]["cost_normalization"]["proxy_floor_absolute_tolerance"]
    )
    proxy_floor = proxy_feasible - floor_tolerance
    cost_spec = formal_solver["stages"]["cost_normalization"]
    cost_result = run_exact_cg_stage(
        stage="cost_normalization",
        all_state_ids=problem.all_state_ids,
        seed_state_ids=problem.initial_active_state_ids,
        target_relative_gap=float(cost_spec["target_relative_gap"]),
        maximum_accepted_relative_gap_to_feasible_incumbent=float(
            cost_spec["maximum_accepted_relative_gap_to_feasible_incumbent"]
        ),
        maximum_accepted_absolute_gap=cost_spec["maximum_accepted_absolute_gap"],
        time_limits=_stage_time_limits(formal_solver, "cost_normalization"),
        callbacks=adapter.callbacks(),
        proxy_floor=proxy_floor,
        candidate_deadline_monotonic=deadline_monotonic,
    )
    if cost_result.snapshot is None:
        raise RuntimeError(
            "RTS-GMLC exact-CG cost stage failed: "
            + str(cost_result.stage_record["failure_reason"])
        )
    handle = adapter.final_handles.get("cost_normalization")
    if handle is None:
        raise RuntimeError("RTS-GMLC exact-CG cost audit model was not retained")
    model = handle.model
    scuc_context = handle.scuc_context
    commitment = _extract_commitment(model, scuc_context)
    generation = _extract_generation(model, scuc_context, "normal")
    branch_flows = _extract_branch_flows(model, scuc_context, "normal")
    dc_flows = _extract_dc_flows(model, scuc_context, "normal")
    reserve = _extract_reserve(model, scuc_context)
    startup, shutdown = _boolean_transitions(
        commitment, context.initial_state.commitment
    )
    proxy_value = _reactive_proxy_value(context, problem.points, commitment)
    if proxy_value + floor_tolerance < proxy_floor:
        raise RuntimeError("RTS-GMLC AC-aware reactive proxy reconstruction drifted")
    operating_cost = float(value(model.operating_cost))
    if operating_cost > cost_budget + float(
        frontier["cost_cap_absolute_tolerance_usd"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate exceeded its cost budget")
    regret_config = formal_solver["primary_regret"]
    stage_one_gap = float(proxy_certificate["absolute_gap"])
    observed_regret = max(float(proxy_certificate["upper_bound"]) - proxy_value, 0.0)
    allowed_regret = (
        stage_one_gap
        + float(regret_config["proxy_floor_tolerance"])
        + float(regret_config["numerical_audit_allowance"])
    )
    regret_passed = bool(
        observed_regret <= allowed_regret + 1.0e-12
        and observed_regret <= float(regret_config["hard_maximum"]) + 1.0e-12
    )
    primary_regret = {
        "schema": "rts_gmlc_primary_proxy_regret_certificate_v1",
        "stage_one_certified_upper_bound": float(proxy_certificate["upper_bound"]),
        "final_commitment_capability_proxy_fraction": proxy_value,
        "observed_regret_upper_bound": observed_regret,
        "stage_one_actual_absolute_gap": stage_one_gap,
        "proxy_floor_tolerance": float(regret_config["proxy_floor_tolerance"]),
        "numerical_audit_allowance": float(regret_config["numerical_audit_allowance"]),
        "derived_allowed_regret": allowed_regret,
        "hard_maximum": float(regret_config["hard_maximum"]),
        "passed": regret_passed,
    }
    if not regret_passed:
        raise RuntimeError("RTS-GMLC primary proxy regret audit failed")
    final_audit = cost_result.stage_record["final_full_state_audit"]
    residual = final_audit["callback_record"]["residual_audit"]
    return _Candidate(
        requested_candidate_id=requested_id,
        source="q_proxy_exact_selected_state_constraint_generation",
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
            "proxy_maximization": proxy_result.stage_record,
            "cost_normalization": cost_result.stage_record,
            "primary_proxy_regret": primary_regret,
        },
        residual_audit=dict(residual),
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


def _generate_candidate_frontier_unleased(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
    _context: _FrontierContext | None = None,
) -> dict[str, Any]:
    context = _context or _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "candidate_frontier"
    if target.exists():
        _load_candidate_frontier(context, output_root)
        return _load_json(target, "summary.json")
    if (output_root / "joint_ac").exists():
        raise RuntimeError("Cannot generate candidates after joint AC has started")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("candidate_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid candidate-generation attempt ID")
    log_root = (
        Path(context.config["formal_solver"]["progress_logging"]["log_directory"])
        / attempt_id
    )
    progress = JsonlProgressWriter(
        log_root / "progress.jsonl",
        run_id=attempt_id,
        preregistration_id=str(context.config["preregistration"]["id"]),
        input_contract_sha256=context.input_contract_sha256,
    )
    started_utc = datetime.now(timezone.utc)
    _write_exact_json(
        log_root / "attempt.json",
        {
            "schema": "rts_gmlc_candidate_generation_attempt_v2",
            "attempt_id": attempt_id,
            "pid": os.getpid(),
            "started_utc": started_utc.isoformat(),
            "preregistration_id": context.config["preregistration"]["id"],
            "input_contract_sha256": context.input_contract_sha256,
            "config_path": context.config_path.as_posix(),
            "checkpoint_schema": _CHECKPOINT_SCHEMA,
            "float_serialization": _CHECKPOINT_FLOAT_SERIALIZATION,
            "implementation_repair_amendment": registration.get(
                "implementation_repair_amendment"
            ),
        },
    )
    deltas = tuple(
        float(item)
        for item in context.config["candidate_frontier"]["relative_cost_budget_deltas"]
    )
    progress.emit(
        "attempt_started",
        candidate_count=len(deltas),
        completed_candidate_count=0,
        completed_budget_candidate_count=0,
        started_utc=started_utc.isoformat(),
    )
    candidates = [_baseline_candidate(context)]
    progress.emit(
        "candidate_completed",
        candidate_ordinal=0,
        requested_candidate_id=candidates[0].requested_candidate_id,
        source=candidates[0].source,
        completed_candidate_count=1,
        completed_budget_candidate_count=0,
        parent_baseline_completed=True,
    )
    checkpoint_manifests: dict[str, str] = {}
    total_limit = float(
        context.config["formal_solver"]["time_limits_seconds"]["per_candidate_total"]
    )
    for ordinal, delta in enumerate(deltas, start=1):
        requested_id = _requested_candidate_id(delta)
        checkpoint = _load_candidate_checkpoint(
            context, output_root, ordinal, requested_id
        )
        if checkpoint is not None:
            candidates.append(checkpoint)
            checkpoint_path = _candidate_checkpoint_path(
                output_root, ordinal, requested_id
            )
            checkpoint_manifests[requested_id] = _sha256(checkpoint_path / "SHA256SUMS")
            progress.emit(
                "candidate_checkpoint_loaded",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                relative_cost_budget_delta=delta,
                checkpoint_manifest_sha256=checkpoint_manifests[requested_id],
                completed_candidate_count=len(candidates),
                completed_budget_candidate_count=len(candidates) - 1,
            )
            continue
        candidate_started = datetime.now(timezone.utc)
        deadline_utc = candidate_started + timedelta(seconds=total_limit)
        deadline_monotonic = monotonic() + total_limit
        progress.emit(
            "candidate_started",
            candidate_ordinal=ordinal,
            requested_candidate_id=requested_id,
            relative_cost_budget_delta=delta,
            total_limit_seconds=total_limit,
            deadline_utc=deadline_utc.isoformat(),
            completed_candidate_count=len(candidates),
            completed_budget_candidate_count=len(candidates) - 1,
        )
        try:
            candidate = _solve_frontier_candidate(
                context,
                relative_delta=delta,
                progress=progress,
                candidate_log_root=log_root / f"{ordinal:02d}_{requested_id}",
                candidate_ordinal=ordinal,
                deadline_monotonic=deadline_monotonic,
            )
            candidate = _save_candidate_checkpoint(
                context, output_root, ordinal, candidate
            )
        except Exception as error:
            progress.emit(
                "candidate_failed",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                relative_cost_budget_delta=delta,
                error_type=type(error).__name__,
                error_message=str(error) or repr(error),
                completed_candidate_count=len(candidates),
                completed_budget_candidate_count=len(candidates) - 1,
            )
            raise
        candidates.append(candidate)
        checkpoint_path = _candidate_checkpoint_path(output_root, ordinal, requested_id)
        checkpoint_manifests[requested_id] = _sha256(checkpoint_path / "SHA256SUMS")
        progress.emit(
            "candidate_completed",
            candidate_ordinal=ordinal,
            requested_candidate_id=requested_id,
            relative_cost_budget_delta=delta,
            commitment_sha256=candidate.commitment_sha256,
            dispatch_sha256=candidate.dispatch_sha256,
            checkpoint_manifest_sha256=checkpoint_manifests[requested_id],
            completed_candidate_count=len(candidates),
            completed_budget_candidate_count=len(candidates) - 1,
        )
    rows, selected = _deduplicate_candidates(candidates)
    timestamps = tuple(
        timestamp.isoformat() for timestamp in context.request.timestamps
    )
    details = _candidate_detail_rows(selected, timestamps)
    summary = {
        "schema": "rts_gmlc_zero_dc_ac_aware_candidate_frontier_v4",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "implementation_repair_amendment": registration.get(
            "implementation_repair_amendment"
        ),
        "requested_candidate_count": len(candidates),
        "requested_budget_candidate_count": len(deltas),
        "parent_baseline_included": True,
        "unique_candidate_count": len(selected),
        "all_budget_candidates_completed_before_deduplication": True,
        "candidate_generation_completed_before_any_joint_ac_solve": True,
        "candidate_generation_uses_ac_outcomes": False,
        "candidate_generation_attempt_id": attempt_id,
        "algorithm": context.config["formal_solver"]["algorithm"],
        "solver": context.config["formal_solver"]["solver"],
        "candidate_checkpoint_manifest_sha256s": checkpoint_manifests,
        "checkpoint_schema": _CHECKPOINT_SCHEMA,
        "float_serialization": _CHECKPOINT_FLOAT_SERIALIZATION,
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
        _write_exact_json(staging / "candidate_audits.json", details[5])
        _write_exact_json(staging / "summary.json", summary)

    _publish_immutable_payload(
        target,
        writer,
        validator=lambda staging: _load_candidate_frontier(
            context,
            output_root,
            frontier_root=staging,
        ),
    )
    _load_candidate_frontier(context, output_root)
    manifest_sha256 = _sha256(target / "SHA256SUMS")
    progress.emit(
        "frontier_published",
        candidate_frontier_manifest_sha256=manifest_sha256,
        completed_candidate_count=len(candidates),
        completed_budget_candidate_count=len(candidates) - 1,
    )
    progress.emit(
        "attempt_completed",
        candidate_frontier_manifest_sha256=manifest_sha256,
        completed_candidate_count=len(candidates),
        completed_budget_candidate_count=len(candidates) - 1,
    )
    return _load_json(target, "summary.json")


def _append_attempt_failed(progress_path: Path, error: BaseException) -> None:
    records = [
        json.loads(line)
        for line in progress_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if not records or not isinstance(records[-1], dict):
        raise RuntimeError("Cannot append terminal event to empty progress log")
    last = records[-1]
    if last.get("event") in {"attempt_completed", "attempt_failed"}:
        return
    attempt = json.loads(
        (progress_path.parent / "attempt.json").read_text(encoding="utf-8")
    )
    if not isinstance(attempt, dict):
        raise RuntimeError("Attempt metadata is not an object")
    started = datetime.fromisoformat(str(attempt["started_utc"]))
    if started.tzinfo is None or started.utcoffset() is None:
        raise RuntimeError("Attempt start timestamp is not timezone-aware")
    observed_at = datetime.now(timezone.utc)
    terminal = {
        "schema": last["schema"],
        "run_id": last["run_id"],
        "preregistration_id": last["preregistration_id"],
        "input_contract_sha256": last["input_contract_sha256"],
        "pid": last["pid"],
        "timestamp_utc": observed_at.isoformat(),
        "monotonic_elapsed_seconds": max(
            (observed_at - started).total_seconds(),
            float(last.get("monotonic_elapsed_seconds", 0.0)),
        ),
        "event": "attempt_failed",
        "stage": "candidate_generation",
        "error_type": type(error).__name__,
        "error_message": str(error) or repr(error),
    }
    encoded = json.dumps(
        terminal,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    with progress_path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(encoded + "\n")
        output.flush()
        os.fsync(output.fileno())


def generate_candidate_frontier(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    _require_preregistration(context, output_root)
    target = output_root / "candidate_frontier"
    if target.exists():
        return _generate_candidate_frontier_unleased(
            config_path,
            output_directory=output_directory,
            attempt_id=attempt_id,
            _context=context,
        )
    if (output_root / "joint_ac").exists():
        raise RuntimeError("Cannot generate candidates after joint AC has started")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("candidate_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid candidate-generation attempt ID")
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
                config_path,
                output_directory=output_directory,
                attempt_id=attempt_id,
                _context=context,
            )
        except BaseException as error:
            if progress_path.is_file():
                try:
                    _append_attempt_failed(progress_path, error)
                except Exception as logging_error:
                    error.add_note(
                        "Failed to append attempt_failed: "
                        + (str(logging_error) or repr(logging_error))
                    )
            raise


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
    context: _FrontierContext,
    output_root: Path,
    *,
    frontier_root: Path | None = None,
) -> tuple[list[_LoadedCandidate], str]:
    root = frontier_root or output_root / "candidate_frontier"
    summary = _load_json(root, "summary.json")
    if (
        summary.get("schema") != "rts_gmlc_zero_dc_ac_aware_candidate_frontier_v4"
        or summary.get("checkpoint_schema") != _CHECKPOINT_SCHEMA
        or summary.get("float_serialization") != _CHECKPOINT_FLOAT_SERIALIZATION
        or summary.get("preregistration_id") != context.config["preregistration"]["id"]
        or summary.get("input_contract_sha256") != context.input_contract_sha256
        or summary.get("algorithm") != context.config["formal_solver"]["algorithm"]
        or _exact_json_text(summary.get("solver"))
        != _exact_json_text(
            _exact_json_payload(context.config["formal_solver"]["solver"])
        )
        or summary.get("relative_cost_budget_deltas")
        != context.config["candidate_frontier"]["relative_cost_budget_deltas"]
        or summary.get("all_budget_candidates_completed_before_deduplication")
        is not True
        or summary.get("candidate_generation_completed_before_any_joint_ac_solve")
        is not True
        or summary.get("candidate_generation_uses_ac_outcomes") is not False
        or summary.get("joint_ac_solver_call_count") != 0
        or any(
            summary.get(key) != value_
            for key, value_ in context.config["evidence"].items()
        )
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate summary drifted")
    deltas = tuple(
        float(item)
        for item in context.config["candidate_frontier"]["relative_cost_budget_deltas"]
    )
    expected_checkpoint_ids = tuple(_requested_candidate_id(item) for item in deltas)
    checkpoint_manifests = summary.get("candidate_checkpoint_manifest_sha256s")
    if (
        summary.get("requested_budget_candidate_count") != len(deltas)
        or summary.get("requested_candidate_count") != len(deltas) + 1
        or summary.get("parent_baseline_included") is not True
        or not isinstance(checkpoint_manifests, dict)
        or set(checkpoint_manifests) != set(expected_checkpoint_ids)
    ):
        raise RuntimeError("RTS-GMLC AC-aware checkpoint summary drifted")
    expected_checkpoint_paths = {
        _candidate_checkpoint_path(output_root, ordinal, requested_id).resolve()
        for ordinal, requested_id in enumerate(expected_checkpoint_ids, start=1)
    }
    checkpoint_root = output_root / "candidate_checkpoints"
    if (
        not checkpoint_root.is_dir()
        or {path.resolve() for path in checkpoint_root.iterdir()}
        != expected_checkpoint_paths
    ):
        raise RuntimeError("RTS-GMLC AC-aware checkpoint inventory drifted")
    checkpoint_candidates: dict[str, _Candidate] = {}
    for ordinal, requested_id in enumerate(expected_checkpoint_ids, start=1):
        checkpoint = _load_candidate_checkpoint(
            context, output_root, ordinal, requested_id
        )
        checkpoint_path = _candidate_checkpoint_path(output_root, ordinal, requested_id)
        if (
            checkpoint is None
            or _sha256(checkpoint_path / "SHA256SUMS")
            != checkpoint_manifests[requested_id]
        ):
            raise RuntimeError("RTS-GMLC AC-aware checkpoint manifest drifted")
        checkpoint_candidates[requested_id] = checkpoint
    baseline_candidate = _baseline_candidate(context)
    reference_candidates = {
        baseline_candidate.requested_candidate_id: baseline_candidate,
        **checkpoint_candidates,
    }
    reserve_uids = tuple(sorted(baseline_candidate.reserve_up_mw[0]))
    if not reserve_uids or any(
        tuple(sorted(row)) != reserve_uids
        for candidate in reference_candidates.values()
        for row in candidate.reserve_up_mw
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate reserve UID coverage drifted")
    candidate_rows = _csv_rows(root / "candidates.csv", _CANDIDATE_FIELDS)
    rows_by_requested = {
        str(row["requested_candidate_id"]): row for row in candidate_rows
    }
    if len(rows_by_requested) != len(candidate_rows) or set(rows_by_requested) != set(
        reference_candidates
    ):
        raise RuntimeError("RTS-GMLC AC-aware requested candidate rows drifted")
    for requested_id, checkpoint in reference_candidates.items():
        row = rows_by_requested[requested_id]
        if (
            row["source"] != checkpoint.source
            or _finite(row["relative_cost_budget_delta"], label="cost_budget_delta")
            != checkpoint.relative_cost_budget_delta
            or _finite(row["cost_budget_usd"], label="cost_budget_usd")
            != checkpoint.cost_budget_usd
            or _finite(row["operating_cost_usd"], label="operating_cost_usd")
            != checkpoint.operating_cost_usd
            or _finite(row["reactive_proxy_fraction"], label="reactive_proxy_fraction")
            != checkpoint.reactive_proxy_fraction
            or row["commitment_sha256"] != checkpoint.commitment_sha256
            or row["dispatch_sha256"] != checkpoint.dispatch_sha256
        ):
            raise RuntimeError("RTS-GMLC AC-aware checkpoint frontier row drifted")
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
    candidate_audits = _load_json(root, "candidate_audits.json")
    if set(candidate_audits) != set(candidate_ids):
        raise RuntimeError("RTS-GMLC AC-aware candidate audit identity drifted")
    selected_by_requested = {
        str(row["requested_candidate_id"]): str(row["candidate_id"])
        for row in selected_rows
    }
    for requested_id, candidate_id in selected_by_requested.items():
        checkpoint = reference_candidates[requested_id]
        expected_audit = {
            "requested_candidate_id": requested_id,
            "stage_audits": checkpoint.stage_audits,
            "residual_audit": checkpoint.residual_audit,
        }
        if _exact_json_text(candidate_audits[candidate_id]) != _exact_json_text(
            _exact_json_payload(expected_audit)
        ):
            raise RuntimeError("RTS-GMLC AC-aware candidate checkpoint audit drifted")
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
    reserves = _group_candidate_hour_rows(
        _csv_rows(root / "reserve_up.csv", _RESERVE_FIELDS),
        candidate_ids=candidate_ids,
        hours=hours,
        identity_field="generator_uid",
        expected_identities=reserve_uids,
    )
    by_candidate_row = {str(row["candidate_id"]): row for row in selected_rows}
    loaded = []
    for candidate_id in candidate_ids:
        commitment_rows = tuple(
            {
                uid: _parse_bool(hour_rows[uid]["commitment"], label="commitment")
                for uid in reserve_uids
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
        reserve_rows = tuple(
            {
                uid: _finite(hour_rows[uid]["reserve_up_mw"], label="reserve_up_mw")
                for uid in generator_uids
            }
            for hour_rows in reserves[candidate_id]
        )
        reference = reference_candidates[str(row["requested_candidate_id"])]
        if reserve_rows != reference.reserve_up_mw:
            raise RuntimeError("RTS-GMLC AC-aware candidate reserve content drifted")
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
                    for uid in reserve_uids
                },
                {
                    generation[candidate_id][hour][uid]["timestamp"]
                    for uid in generator_uids
                },
                {branches[candidate_id][hour][uid]["timestamp"] for uid in branch_uids},
                {dc_flows[candidate_id][hour][uid]["timestamp"] for uid in dc_uids},
                {
                    reserves[candidate_id][hour][uid]["timestamp"]
                    for uid in generator_uids
                },
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
    if (
        summary.get("commitment_sha256s")
        != [candidate.commitment_sha256 for candidate in loaded]
        or not _checkpoint_close(
            summary.get("minimum_reactive_proxy_fraction"),
            min(candidate.reactive_proxy_fraction for candidate in loaded),
        )
        or not _checkpoint_close(
            summary.get("maximum_reactive_proxy_fraction"),
            max(candidate.reactive_proxy_fraction for candidate in loaded),
        )
    ):
        raise RuntimeError("RTS-GMLC AC-aware candidate frontier summary drifted")
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
    *,
    initial_strategies: Sequence[str] | None = None,
) -> None:
    candidate_by_id = {candidate.candidate_id: candidate for candidate in candidates}
    if (
        len(candidate_by_id) != len(candidates)
        or set(prepared_by_candidate) != set(candidate_by_id)
        or set(chronology_by_candidate) != set(candidate_by_id)
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint candidate identity drifted")
    strategies = tuple(
        context.config["joint_ac"]["initial_strategies"]
        if initial_strategies is None
        else initial_strategies
    )
    if not strategies or not set(strategies) <= set(
        context.config["joint_ac"]["initial_strategies"]
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint strategy contract drifted")
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


def _joint_call_key(candidate_id: str, initial_strategy: str) -> str:
    key = f"{candidate_id}__{initial_strategy}"
    if re.fullmatch(r"[a-z0-9_]+", key) is None:
        raise RuntimeError("RTS-GMLC AC-aware joint call key drifted")
    return key


def _joint_log_root(context: _FrontierContext, parent_attempt_id: str) -> Path:
    if re.fullmatch(r"[A-Za-z0-9_.-]+", parent_attempt_id) is None:
        raise RuntimeError("RTS-GMLC AC-aware joint parent attempt ID drifted")
    return (
        Path(context.config["joint_ac"]["runtime_control"]["log_directory"])
        / parent_attempt_id
    ).resolve()


def _joint_relative_path(log_root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(log_root).as_posix()
    except ValueError as error:
        raise RuntimeError(
            "RTS-GMLC AC-aware joint worker path escaped its log root"
        ) from error


def _resolve_joint_relative_path(log_root: Path, value: object) -> Path:
    if not isinstance(value, str):
        raise RuntimeError("RTS-GMLC AC-aware joint relative path drifted")
    relative = Path(value)
    if (
        relative.is_absolute()
        or not value
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint relative path drifted")
    resolved = (log_root / relative).resolve()
    if resolved == log_root or log_root not in resolved.parents:
        raise RuntimeError("RTS-GMLC AC-aware joint relative path escaped log root")
    return resolved


def _registered_joint_worker_paths(
    context: _FrontierContext, registration: Mapping[str, object]
) -> tuple[Path, Path, Path]:
    parent_attempt_id = registration.get("parent_attempt_id")
    if not isinstance(parent_attempt_id, str):
        raise RuntimeError("RTS-GMLC AC-aware joint call runtime identity drifted")
    log_root = _joint_log_root(context, parent_attempt_id)
    return (
        _resolve_joint_relative_path(
            log_root, registration.get("worker_result_relative_path")
        ),
        _resolve_joint_relative_path(
            log_root, registration.get("native_solver_log_relative_path")
        ),
        _resolve_joint_relative_path(
            log_root, registration.get("worker_process_log_relative_path")
        ),
    )


def _joint_call_registration_payload(
    context: _FrontierContext,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    *,
    parent_attempt_id: str,
    parent_pid: int,
    worker_result_directory: Path,
    native_solver_log: Path,
    worker_process_log: Path,
) -> dict[str, object]:
    log_root = _joint_log_root(context, parent_attempt_id)
    return {
        "schema": _JOINT_CALL_SCHEMA,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "candidate_frontier_manifest_sha256": candidate_frontier_manifest_sha256,
        "candidate_id": candidate.candidate_id,
        "requested_candidate_id": candidate.requested_candidate_id,
        "commitment_sha256": candidate.commitment_sha256,
        "dispatch_sha256": candidate.dispatch_sha256,
        "initial_strategy": initial_strategy,
        "engine": context.config["joint_ac"]["engine"],
        "ipopt_options": context.config["joint_ac"]["ipopt_options"],
        "runtime_control": context.config["joint_ac"]["runtime_control"],
        "parent_attempt_id": parent_attempt_id,
        "parent_pid": parent_pid,
        "worker_result_relative_path": _joint_relative_path(
            log_root, worker_result_directory
        ),
        "native_solver_log_relative_path": _joint_relative_path(
            log_root, native_solver_log
        ),
        "worker_process_log_relative_path": _joint_relative_path(
            log_root, worker_process_log
        ),
        "retry_allowed": False,
    }


def _joint_call_registration_path(
    output_root: Path, candidate_id: str, initial_strategy: str
) -> Path:
    return (
        output_root
        / "joint_call_registry"
        / _joint_call_key(candidate_id, initial_strategy)
    )


def _joint_checkpoint_path(
    output_root: Path, candidate_id: str, initial_strategy: str
) -> Path:
    return (
        output_root
        / "joint_call_checkpoints"
        / _joint_call_key(candidate_id, initial_strategy)
    )


def _register_joint_call(
    context: _FrontierContext,
    output_root: Path,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    *,
    parent_attempt_id: str,
    parent_pid: int,
    worker_result_directory: Path,
    native_solver_log: Path,
    worker_process_log: Path,
) -> str:
    target = _joint_call_registration_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    payload = _joint_call_registration_payload(
        context,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        parent_attempt_id=parent_attempt_id,
        parent_pid=parent_pid,
        worker_result_directory=worker_result_directory,
        native_solver_log=native_solver_log,
        worker_process_log=worker_process_log,
    )
    if target.exists():
        raise RuntimeError(
            "RTS-GMLC AC-aware joint call was already registered; retry is forbidden"
        )

    def writer(staging: Path) -> None:
        _write_exact_json(staging / "call.json", payload)

    _publish_immutable_payload(target, writer)
    observed = _load_json(target, "call.json")
    if _exact_json_text(observed) != _exact_json_text(_exact_json_payload(payload)):
        raise RuntimeError("RTS-GMLC AC-aware joint call registration drifted")
    return _sha256(target / "SHA256SUMS")


def _write_joint_rows(root: Path, rows: _JointRows) -> None:
    _write_csv(root / "joint_runs.csv", _JOINT_RUN_FIELDS, rows.runs)
    _write_csv(root / "joint_hours.csv", _JOINT_HOUR_FIELDS, rows.hours)
    _write_csv(
        root / "generator_results.csv",
        _JOINT_GENERATOR_FIELDS,
        rows.generators,
    )
    _write_csv(root / "bus_results.csv", _JOINT_BUS_FIELDS, rows.buses)
    _write_csv(root / "branch_results.csv", _JOINT_BRANCH_FIELDS, rows.branches)
    _write_csv(root / "reserve_results.csv", _JOINT_RESERVE_FIELDS, rows.reserves)


def _load_joint_rows(root: Path) -> _JointRows:
    return _JointRows(
        runs=tuple(_csv_rows(root / "joint_runs.csv", _JOINT_RUN_FIELDS)),
        hours=tuple(_csv_rows(root / "joint_hours.csv", _JOINT_HOUR_FIELDS)),
        generators=tuple(
            _csv_rows(root / "generator_results.csv", _JOINT_GENERATOR_FIELDS)
        ),
        buses=tuple(_csv_rows(root / "bus_results.csv", _JOINT_BUS_FIELDS)),
        branches=tuple(_csv_rows(root / "branch_results.csv", _JOINT_BRANCH_FIELDS)),
        reserves=tuple(_csv_rows(root / "reserve_results.csv", _JOINT_RESERVE_FIELDS)),
    )


_JOINT_WORKER_RESULT_FILES = {
    "joint_runs.csv",
    "joint_hours.csv",
    "generator_results.csv",
    "bus_results.csv",
    "branch_results.csv",
    "reserve_results.csv",
    "worker.json",
}


def _validate_embedded_worker_evidence(
    root: Path, expected_manifest_sha256: str
) -> dict[str, Any]:
    manifest = root / "worker.SHA256SUMS"
    if not manifest.is_file() or _sha256(manifest) != expected_manifest_sha256:
        raise RuntimeError("RTS-GMLC AC-aware embedded worker manifest drifted")
    entries: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        try:
            digest, relative = line.split("  ", maxsplit=1)
        except ValueError as error:
            raise RuntimeError(
                "RTS-GMLC AC-aware embedded worker manifest is malformed"
            ) from error
        if (
            relative in entries
            or relative not in _JOINT_WORKER_RESULT_FILES
            or re.fullmatch(r"[0-9a-f]{64}", digest) is None
        ):
            raise RuntimeError("RTS-GMLC AC-aware embedded worker manifest drifted")
        entries[relative] = digest
    if set(entries) != _JOINT_WORKER_RESULT_FILES or any(
        not (root / relative).is_file() or _sha256(root / relative) != digest
        for relative, digest in entries.items()
    ):
        raise RuntimeError("RTS-GMLC AC-aware embedded worker evidence drifted")
    worker = json.loads((root / "worker.json").read_text(encoding="utf-8"))
    if not isinstance(worker, dict):
        raise RuntimeError("RTS-GMLC AC-aware embedded worker metadata drifted")
    return worker


def _joint_checkpoint_metadata(
    context: _FrontierContext,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    call_registration_manifest_sha256: str,
    worker_result_manifest_sha256: str,
    native_solver_log_sha256: str,
) -> dict[str, object]:
    return {
        "schema": _JOINT_CHECKPOINT_SCHEMA,
        "float_serialization": _CHECKPOINT_FLOAT_SERIALIZATION,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "candidate_frontier_manifest_sha256": candidate_frontier_manifest_sha256,
        "call_registration_manifest_sha256": call_registration_manifest_sha256,
        "worker_result_manifest_sha256": worker_result_manifest_sha256,
        "candidate_id": candidate.candidate_id,
        "requested_candidate_id": candidate.requested_candidate_id,
        "commitment_sha256": candidate.commitment_sha256,
        "dispatch_sha256": candidate.dispatch_sha256,
        "initial_strategy": initial_strategy,
        "native_solver_log_sha256": native_solver_log_sha256,
    }


def _validate_joint_call_registration(
    context: _FrontierContext,
    output_root: Path,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
) -> str | None:
    target = _joint_call_registration_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    if not target.exists():
        return None
    _verify_output_manifest(target)
    observed = _load_json(target, "call.json")
    parent_attempt_id = observed.get("parent_attempt_id")
    parent_pid = observed.get("parent_pid")
    if (
        not isinstance(parent_attempt_id, str)
        or re.fullmatch(r"[A-Za-z0-9_.-]+", parent_attempt_id) is None
        or isinstance(parent_pid, bool)
        or not isinstance(parent_pid, int)
        or parent_pid <= 0
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint call runtime identity drifted")
    expected_log_root = _joint_log_root(context, parent_attempt_id)
    expected_worker_result, expected_native_log, expected_process_log = (
        _joint_worker_paths(expected_log_root, candidate.candidate_id, initial_strategy)
    )
    worker_result_directory, native_solver_log, worker_process_log = (
        _registered_joint_worker_paths(context, observed)
    )
    if (
        worker_result_directory != expected_worker_result.resolve()
        or native_solver_log != expected_native_log.resolve()
        or worker_process_log != expected_process_log.resolve()
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint call path drifted")
    expected = _joint_call_registration_payload(
        context,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        parent_attempt_id=parent_attempt_id,
        parent_pid=parent_pid,
        worker_result_directory=expected_worker_result,
        native_solver_log=expected_native_log,
        worker_process_log=expected_process_log,
    )
    if _exact_json_text(observed) != _exact_json_text(_exact_json_payload(expected)):
        raise RuntimeError("RTS-GMLC AC-aware joint call registration drifted")
    return _sha256(target / "SHA256SUMS")


def _load_joint_checkpoint(
    context: _FrontierContext,
    output_root: Path,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    prepared_cases: tuple[Any, ...],
    chronology: AcAwareChronology,
) -> tuple[_JointRows, str, str] | None:
    registration_manifest = _validate_joint_call_registration(
        context,
        output_root,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
    )
    target = _joint_checkpoint_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    if not target.exists():
        return None
    if registration_manifest is None:
        raise RuntimeError("RTS-GMLC AC-aware joint checkpoint lacks call registration")
    _verify_output_manifest(target)
    observed_metadata = _load_json(target, "checkpoint.json")
    native_log_sha256 = observed_metadata.get("native_solver_log_sha256")
    worker_manifest_sha256 = observed_metadata.get("worker_result_manifest_sha256")
    if (
        not isinstance(native_log_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", native_log_sha256) is None
        or not isinstance(worker_manifest_sha256, str)
        or re.fullmatch(r"[0-9a-f]{64}", worker_manifest_sha256) is None
        or _sha256(target / "ipopt.log") != native_log_sha256
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint native log drifted")
    expected_metadata = _joint_checkpoint_metadata(
        context,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        registration_manifest,
        worker_manifest_sha256,
        native_log_sha256,
    )
    if _exact_json_text(observed_metadata) != _exact_json_text(
        _exact_json_payload(expected_metadata)
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint checkpoint metadata drifted")
    rows = _load_joint_rows(target)
    _validate_joint_result_rows(
        context,
        (candidate,),
        {candidate.candidate_id: prepared_cases},
        {candidate.candidate_id: chronology},
        rows.runs,
        rows.hours,
        rows.generators,
        rows.buses,
        rows.branches,
        rows.reserves,
        initial_strategies=(initial_strategy,),
    )
    embedded_worker = _validate_embedded_worker_evidence(target, worker_manifest_sha256)
    expected_worker = _joint_worker_metadata(
        context,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        registration_manifest,
        native_log_sha256,
    )
    if _exact_json_text(embedded_worker) != _exact_json_text(
        _exact_json_payload(expected_worker)
    ):
        raise RuntimeError("RTS-GMLC AC-aware joint worker evidence drifted")
    return rows, _sha256(target / "SHA256SUMS"), registration_manifest


def _save_joint_checkpoint(
    context: _FrontierContext,
    output_root: Path,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    call_registration_manifest_sha256: str,
    prepared_cases: tuple[Any, ...],
    chronology: AcAwareChronology,
    rows: _JointRows,
    native_solver_log: Path,
    worker_result_manifest_sha256: str,
) -> tuple[_JointRows, str, str]:
    target = _joint_checkpoint_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    if not native_solver_log.is_file() or native_solver_log.stat().st_size <= 0:
        raise RuntimeError("RTS-GMLC AC-aware joint native solver log is missing")
    if re.fullmatch(r"[0-9a-f]{64}", worker_result_manifest_sha256) is None:
        raise RuntimeError("RTS-GMLC AC-aware worker result manifest drifted")
    observed_call_manifest = _validate_joint_call_registration(
        context,
        output_root,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
    )
    if observed_call_manifest != call_registration_manifest_sha256:
        raise RuntimeError("RTS-GMLC AC-aware joint call manifest drifted")
    call_registration = _load_json(
        _joint_call_registration_path(
            output_root, candidate.candidate_id, initial_strategy
        ),
        "call.json",
    )
    worker_result_root, registered_native_log, _ = _registered_joint_worker_paths(
        context, call_registration
    )
    if registered_native_log != native_solver_log.resolve():
        raise RuntimeError("RTS-GMLC AC-aware joint native log path drifted")
    worker_rows, observed_worker_manifest = _load_joint_worker_result(
        context,
        worker_result_root,
        native_solver_log,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        call_registration_manifest_sha256,
        prepared_cases,
        chronology,
    )
    if worker_rows != rows or observed_worker_manifest != worker_result_manifest_sha256:
        raise RuntimeError("RTS-GMLC AC-aware joint worker result drifted")
    native_log_sha256 = _sha256(native_solver_log)
    metadata = _joint_checkpoint_metadata(
        context,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        call_registration_manifest_sha256,
        worker_result_manifest_sha256,
        native_log_sha256,
    )

    def validate(staging: Path) -> None:
        observed = _load_json(staging, "checkpoint.json")
        if (
            _exact_json_text(observed)
            != _exact_json_text(_exact_json_payload(metadata))
            or _sha256(staging / "ipopt.log") != native_log_sha256
        ):
            raise RuntimeError("RTS-GMLC AC-aware joint checkpoint staging drifted")
        embedded_worker = _validate_embedded_worker_evidence(
            staging, worker_result_manifest_sha256
        )
        expected_worker = _joint_worker_metadata(
            context,
            candidate,
            initial_strategy,
            candidate_frontier_manifest_sha256,
            call_registration_manifest_sha256,
            native_log_sha256,
        )
        if _exact_json_text(embedded_worker) != _exact_json_text(
            _exact_json_payload(expected_worker)
        ):
            raise RuntimeError("RTS-GMLC AC-aware embedded worker metadata drifted")
        staged_rows = _load_joint_rows(staging)
        _validate_joint_result_rows(
            context,
            (candidate,),
            {candidate.candidate_id: prepared_cases},
            {candidate.candidate_id: chronology},
            staged_rows.runs,
            staged_rows.hours,
            staged_rows.generators,
            staged_rows.buses,
            staged_rows.branches,
            staged_rows.reserves,
            initial_strategies=(initial_strategy,),
        )

    def writer(staging: Path) -> None:
        _write_joint_rows(staging, rows)
        (staging / "ipopt.log").write_bytes(native_solver_log.read_bytes())
        (staging / "worker.json").write_bytes(
            (worker_result_root / "worker.json").read_bytes()
        )
        (staging / "worker.SHA256SUMS").write_bytes(
            (worker_result_root / "SHA256SUMS").read_bytes()
        )
        _write_exact_json(staging / "checkpoint.json", metadata)

    _publish_immutable_payload(target, writer, validator=validate)
    loaded = _load_joint_checkpoint(
        context,
        output_root,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        prepared_cases,
        chronology,
    )
    if loaded is None:
        raise RuntimeError("Published RTS-GMLC AC-aware joint checkpoint is missing")
    return loaded


def _merge_joint_rows(parts: Sequence[_JointRows]) -> _JointRows:
    return _JointRows(
        runs=tuple(row for part in parts for row in part.runs),
        hours=tuple(row for part in parts for row in part.hours),
        generators=tuple(row for part in parts for row in part.generators),
        buses=tuple(row for part in parts for row in part.buses),
        branches=tuple(row for part in parts for row in part.branches),
        reserves=tuple(row for part in parts for row in part.reserves),
    )


def _load_all_joint_checkpoints(
    context: _FrontierContext,
    output_root: Path,
    candidates: Sequence[_LoadedCandidate],
    candidate_frontier_manifest_sha256: str,
    prepared_by_candidate: Mapping[str, tuple[Any, ...]],
    chronology_by_candidate: Mapping[str, AcAwareChronology],
) -> tuple[_JointRows, dict[str, str], dict[str, str]]:
    expected_keys = {
        _joint_call_key(candidate.candidate_id, str(strategy))
        for candidate in candidates
        for strategy in context.config["joint_ac"]["initial_strategies"]
    }
    for name in ("joint_call_registry", "joint_call_checkpoints"):
        root = output_root / name
        if not root.is_dir() or {path.name for path in root.iterdir()} != expected_keys:
            raise RuntimeError("RTS-GMLC AC-aware joint checkpoint inventory drifted")
    parts = []
    checkpoint_manifests = {}
    call_manifests = {}
    for candidate in candidates:
        for strategy_value in context.config["joint_ac"]["initial_strategies"]:
            strategy = str(strategy_value)
            loaded = _load_joint_checkpoint(
                context,
                output_root,
                candidate,
                strategy,
                candidate_frontier_manifest_sha256,
                prepared_by_candidate[candidate.candidate_id],
                chronology_by_candidate[candidate.candidate_id],
            )
            if loaded is None:
                raise RuntimeError("RTS-GMLC AC-aware joint checkpoint is missing")
            rows, checkpoint_manifest, call_manifest = loaded
            key = _joint_call_key(candidate.candidate_id, strategy)
            parts.append(rows)
            checkpoint_manifests[key] = checkpoint_manifest
            call_manifests[key] = call_manifest
    return _merge_joint_rows(parts), checkpoint_manifests, call_manifests


def _joint_summary(
    context: _FrontierContext,
    registration: Mapping[str, Any],
    candidates: Sequence[_LoadedCandidate],
    candidate_frontier_manifest_sha256: str,
    run_rows: Sequence[Mapping[str, object]],
    joint_checkpoint_manifest_sha256s: Mapping[str, str],
    joint_call_registration_manifest_sha256s: Mapping[str, str],
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
        "schema": "rts_gmlc_zero_dc_ac_aware_joint_ac_results_v4",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "candidate_frontier_manifest_sha256": candidate_frontier_manifest_sha256,
        "candidate_count": len(candidates),
        "candidate_ids": [candidate.candidate_id for candidate in candidates],
        "initial_strategies": list(strategies),
        "joint_ac_solver_call_count": len(run_rows),
        "expected_joint_ac_solver_call_count": len(candidates) * len(strategies),
        "joint_checkpoint_schema": _JOINT_CHECKPOINT_SCHEMA,
        "joint_checkpoint_manifest_sha256s": dict(joint_checkpoint_manifest_sha256s),
        "joint_call_registration_schema": _JOINT_CALL_SCHEMA,
        "joint_call_registration_manifest_sha256s": dict(
            joint_call_registration_manifest_sha256s
        ),
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
    if summary.get("schema") != "rts_gmlc_zero_dc_ac_aware_joint_ac_results_v4":
        raise RuntimeError("Published RTS-GMLC AC-aware joint schema drifted")
    published_rows = _load_joint_rows(target)
    _validate_joint_result_rows(
        context,
        candidates,
        prepared_by_candidate,
        chronology_by_candidate,
        published_rows.runs,
        published_rows.hours,
        published_rows.generators,
        published_rows.buses,
        published_rows.branches,
        published_rows.reserves,
    )
    checkpoint_rows, checkpoint_manifests, call_manifests = _load_all_joint_checkpoints(
        context,
        target.parent,
        candidates,
        candidate_frontier_manifest_sha256,
        prepared_by_candidate,
        chronology_by_candidate,
    )
    if published_rows != checkpoint_rows:
        raise RuntimeError("Published RTS-GMLC AC-aware joint checkpoint rows drifted")
    expected_summary = _joint_summary(
        context,
        registration,
        candidates,
        candidate_frontier_manifest_sha256,
        published_rows.runs,
        checkpoint_manifests,
        call_manifests,
    )
    if summary != expected_summary:
        raise RuntimeError("Published RTS-GMLC AC-aware joint summary drifted")
    return summary


def _joint_worker_metadata(
    context: _FrontierContext,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    call_registration_manifest_sha256: str,
    native_solver_log_sha256: str,
) -> dict[str, object]:
    return {
        "schema": _JOINT_WORKER_SCHEMA,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "candidate_frontier_manifest_sha256": candidate_frontier_manifest_sha256,
        "call_registration_manifest_sha256": (call_registration_manifest_sha256),
        "candidate_id": candidate.candidate_id,
        "requested_candidate_id": candidate.requested_candidate_id,
        "commitment_sha256": candidate.commitment_sha256,
        "dispatch_sha256": candidate.dispatch_sha256,
        "initial_strategy": initial_strategy,
        "native_solver_log_sha256": native_solver_log_sha256,
        "runtime_control": context.config["joint_ac"]["runtime_control"],
    }


def _load_joint_worker_result(
    context: _FrontierContext,
    result_root: Path,
    native_solver_log: Path,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    call_registration_manifest_sha256: str,
    prepared_cases: tuple[Any, ...],
    chronology: AcAwareChronology,
) -> tuple[_JointRows, str]:
    _verify_output_manifest(result_root)
    if not native_solver_log.is_file() or native_solver_log.stat().st_size <= 0:
        raise RuntimeError("RTS-GMLC AC-aware worker native solver log is missing")
    expected = _joint_worker_metadata(
        context,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        call_registration_manifest_sha256,
        _sha256(native_solver_log),
    )
    observed = _load_json(result_root, "worker.json")
    if _exact_json_text(observed) != _exact_json_text(_exact_json_payload(expected)):
        raise RuntimeError("RTS-GMLC AC-aware joint worker metadata drifted")
    rows = _load_joint_rows(result_root)
    _validate_joint_result_rows(
        context,
        (candidate,),
        {candidate.candidate_id: prepared_cases},
        {candidate.candidate_id: chronology},
        rows.runs,
        rows.hours,
        rows.generators,
        rows.buses,
        rows.branches,
        rows.reserves,
        initial_strategies=(initial_strategy,),
    )
    return rows, _sha256(result_root / "SHA256SUMS")


def _execute_joint_call_worker(
    context: _FrontierContext,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    result_directory: Path,
    native_solver_log: Path,
    call_registration_manifest_sha256: str,
) -> dict[str, object]:
    from src.grid.rts_gmlc_ac_aware_commitment_v4_adapter import (
        solve_ac_aware_commitment_v4_worker,
    )

    prepared_cases = _prepared_joint_cases(context, candidate)
    chronology = _joint_chronology(context, candidate)
    runtime = context.config["joint_ac"]["runtime_control"]
    result = solve_ac_aware_commitment_v4_worker(
        prepared_cases,
        chronology,
        initial_strategy=initial_strategy,
        base_options=context.config["joint_ac"]["ipopt_options"],
        runtime_options={
            "ipopt.max_cpu_time": float(runtime["max_cpu_time_seconds_per_call"]),
            "ipopt.output_file": str(native_solver_log.resolve()),
            "ipopt.file_print_level": int(runtime["native_file_print_level"]),
        },
    )
    result_tuple = _joint_result_rows(candidate, result)
    rows = _JointRows(
        runs=(result_tuple[0],),
        hours=tuple(result_tuple[1]),
        generators=tuple(result_tuple[2]),
        buses=tuple(result_tuple[3]),
        branches=tuple(result_tuple[4]),
        reserves=tuple(result_tuple[5]),
    )
    _validate_joint_result_rows(
        context,
        (candidate,),
        {candidate.candidate_id: prepared_cases},
        {candidate.candidate_id: chronology},
        rows.runs,
        rows.hours,
        rows.generators,
        rows.buses,
        rows.branches,
        rows.reserves,
        initial_strategies=(initial_strategy,),
    )
    if not native_solver_log.is_file() or native_solver_log.stat().st_size <= 0:
        raise RuntimeError("RTS-GMLC AC-aware worker native solver log is missing")
    metadata = _joint_worker_metadata(
        context,
        candidate,
        initial_strategy,
        frontier_manifest,
        call_registration_manifest_sha256,
        _sha256(native_solver_log),
    )

    def writer(staging: Path) -> None:
        _write_joint_rows(staging, rows)
        _write_exact_json(staging / "worker.json", metadata)

    def validate(staging: Path) -> None:
        observed = _load_json(staging, "worker.json")
        if _exact_json_text(observed) != _exact_json_text(
            _exact_json_payload(metadata)
        ):
            raise RuntimeError("RTS-GMLC AC-aware joint worker staging drifted")
        staged_rows = _load_joint_rows(staging)
        _validate_joint_result_rows(
            context,
            (candidate,),
            {candidate.candidate_id: prepared_cases},
            {candidate.candidate_id: chronology},
            staged_rows.runs,
            staged_rows.hours,
            staged_rows.generators,
            staged_rows.buses,
            staged_rows.branches,
            staged_rows.reserves,
            initial_strategies=(initial_strategy,),
        )

    _publish_immutable_payload(
        result_directory,
        writer,
        validator=validate,
    )
    _load_joint_worker_result(
        context,
        result_directory,
        native_solver_log,
        candidate,
        initial_strategy,
        frontier_manifest,
        call_registration_manifest_sha256,
        prepared_cases,
        chronology,
    )
    return metadata


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
        raise RuntimeError("RTS-GMLC AC-aware worker candidate identity drifted")
    candidate = matches[0]
    if initial_strategy not in context.config["joint_ac"]["initial_strategies"]:
        raise RuntimeError("RTS-GMLC AC-aware worker strategy drifted")
    observed_call_manifest = _validate_joint_call_registration(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
    )
    if observed_call_manifest != call_registration_manifest_sha256:
        raise RuntimeError("RTS-GMLC AC-aware worker call registration drifted")
    call_root = _joint_call_registration_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    call_registration = _load_json(call_root, "call.json")
    parent_pid = call_registration["parent_pid"]
    parent_attempt_id = call_registration["parent_attempt_id"]
    registered_result_directory, registered_native_solver_log, _ = (
        _registered_joint_worker_paths(context, call_registration)
    )
    if (
        parent_pid != os.getppid()
        or registered_result_directory != result_directory.resolve()
        or registered_native_solver_log != native_solver_log.resolve()
    ):
        raise RuntimeError("RTS-GMLC AC-aware worker parent identity drifted")
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
        raise RuntimeError("RTS-GMLC AC-aware worker execution lease drifted")
    runtime = context.config["joint_ac"]["runtime_control"]
    with ParentProcessWatchdog(
        int(parent_pid),
        interval_seconds=float(runtime["parent_watchdog_interval_seconds"]),
    ):
        return _execute_joint_call_worker(
            context,
            candidate,
            initial_strategy,
            frontier_manifest,
            result_directory,
            native_solver_log,
            call_registration_manifest_sha256,
        )


def _joint_worker_paths(
    log_root: Path, candidate_id: str, initial_strategy: str
) -> tuple[Path, Path, Path]:
    key = _joint_call_key(candidate_id, initial_strategy)
    return (
        log_root / "worker_results" / key,
        log_root / "native" / f"{key}.log",
        log_root / "worker_process" / f"{key}.log",
    )


def _run_joint_worker_process(
    context: _FrontierContext,
    output_root: Path,
    candidate: _LoadedCandidate,
    initial_strategy: str,
    candidate_frontier_manifest_sha256: str,
    prepared_cases: tuple[Any, ...],
    chronology: AcAwareChronology,
    log_root: Path,
    progress: JsonlProgressWriter,
    call_registration_manifest_sha256: str,
) -> tuple[_JointRows, Path, str]:
    key = _joint_call_key(candidate.candidate_id, initial_strategy)
    worker_result, native_log, process_log = _joint_worker_paths(
        log_root, candidate.candidate_id, initial_strategy
    )
    if any(path.exists() for path in (worker_result, native_log, process_log)):
        raise FileExistsError("RTS-GMLC AC-aware joint worker artifact already exists")
    process_log.parent.mkdir(parents=True, exist_ok=True)
    native_log.parent.mkdir(parents=True, exist_ok=True)
    runtime = context.config["joint_ac"]["runtime_control"]
    wall_limit = float(runtime["max_wall_time_seconds_per_call"])
    termination_grace = float(runtime["termination_grace_seconds"])
    command = [
        sys.executable,
        "-B",
        "-m",
        "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4",
        "--config",
        str(context.config_path.resolve()),
        "--stage",
        "joint-call-worker",
        "--output-directory",
        str(output_root.resolve()),
        "--candidate-id",
        candidate.candidate_id,
        "--initial-strategy",
        initial_strategy,
        "--worker-result-directory",
        str(worker_result.resolve()),
        "--native-solver-log",
        str(native_log.resolve()),
        "--call-registration-manifest-sha256",
        call_registration_manifest_sha256,
    ]
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
                call_registration_manifest_sha256=(call_registration_manifest_sha256),
            )
            with _CheckedProgressHeartbeat(
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
                f"RTS-GMLC AC-aware joint call exceeded {wall_limit} seconds"
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
            "RTS-GMLC AC-aware joint worker failed with exit code "
            f"{process.returncode}; see {process_log}"
        )
    rows, worker_manifest = _load_joint_worker_result(
        context,
        worker_result,
        native_log,
        candidate,
        initial_strategy,
        candidate_frontier_manifest_sha256,
        call_registration_manifest_sha256,
        prepared_cases,
        chronology,
    )
    return rows, native_log, worker_manifest


def _run_joint_ac_attempt(
    context: _FrontierContext,
    output_root: Path,
    registration: Mapping[str, Any],
    candidates: Sequence[_LoadedCandidate],
    candidate_frontier_manifest_sha256: str,
    attempt_id: str,
    log_root: Path,
    progress: JsonlProgressWriter,
) -> dict[str, Any]:
    runtime = context.config["joint_ac"]["runtime_control"]
    progress.emit("joint_preparation_started", stage="joint_ac_preparation")
    with _CheckedProgressHeartbeat(
        progress,
        interval_seconds=float(runtime["heartbeat_interval_seconds"]),
        payload={"stage": "joint_ac_preparation"},
    ):
        prepared_by_candidate = {
            candidate.candidate_id: _prepared_joint_cases(context, candidate)
            for candidate in candidates
        }
        chronology_by_candidate = {
            candidate.candidate_id: _joint_chronology(context, candidate)
            for candidate in candidates
        }
    progress.emit("joint_preparation_completed", stage="joint_ac_preparation")
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

    parts = []
    completed_calls = 0
    total_calls = len(candidates) * len(
        context.config["joint_ac"]["initial_strategies"]
    )
    for candidate in candidates:
        for strategy_value in context.config["joint_ac"]["initial_strategies"]:
            strategy = str(strategy_value)
            loaded = _load_joint_checkpoint(
                context,
                output_root,
                candidate,
                strategy,
                candidate_frontier_manifest_sha256,
                prepared_by_candidate[candidate.candidate_id],
                chronology_by_candidate[candidate.candidate_id],
            )
            if loaded is not None:
                rows, checkpoint_manifest, call_manifest = loaded
                parts.append(rows)
                completed_calls += 1
                progress.emit(
                    "joint_checkpoint_loaded",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    completed_joint_call_count=completed_calls,
                    expected_joint_call_count=total_calls,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=call_manifest,
                )
                continue
            existing_call_manifest = _validate_joint_call_registration(
                context,
                output_root,
                candidate,
                strategy,
                candidate_frontier_manifest_sha256,
            )
            if existing_call_manifest is not None:
                call_registration = _load_json(
                    _joint_call_registration_path(
                        output_root, candidate.candidate_id, strategy
                    ),
                    "call.json",
                )
                registered_worker_result, registered_native_log, _ = (
                    _registered_joint_worker_paths(context, call_registration)
                )
                if (
                    not registered_worker_result.is_dir()
                    or not registered_native_log.is_file()
                ):
                    raise RuntimeError(
                        "RTS-GMLC AC-aware joint call is incomplete; retry is forbidden"
                    )
                worker_rows, worker_manifest = _load_joint_worker_result(
                    context,
                    registered_worker_result,
                    registered_native_log,
                    candidate,
                    strategy,
                    candidate_frontier_manifest_sha256,
                    existing_call_manifest,
                    prepared_by_candidate[candidate.candidate_id],
                    chronology_by_candidate[candidate.candidate_id],
                )
                rows, checkpoint_manifest, observed_call_manifest = (
                    _save_joint_checkpoint(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        candidate_frontier_manifest_sha256,
                        existing_call_manifest,
                        prepared_by_candidate[candidate.candidate_id],
                        chronology_by_candidate[candidate.candidate_id],
                        worker_rows,
                        registered_native_log,
                        worker_manifest,
                    )
                )
                if observed_call_manifest != existing_call_manifest:
                    raise RuntimeError(
                        "RTS-GMLC AC-aware recovered call manifest drifted"
                    )
                parts.append(rows)
                completed_calls += 1
                progress.emit(
                    "joint_worker_result_recovered",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    worker_result_manifest_sha256=worker_manifest,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=existing_call_manifest,
                    completed_joint_call_count=completed_calls,
                    expected_joint_call_count=total_calls,
                )
                continue
            worker_result, native_log_path, process_log_path = _joint_worker_paths(
                log_root, candidate.candidate_id, strategy
            )
            call_manifest = _register_joint_call(
                context,
                output_root,
                candidate,
                strategy,
                candidate_frontier_manifest_sha256,
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
                    candidate_frontier_manifest_sha256,
                    prepared_by_candidate[candidate.candidate_id],
                    chronology_by_candidate[candidate.candidate_id],
                    log_root,
                    progress,
                    call_manifest,
                )
                rows, checkpoint_manifest, observed_call_manifest = (
                    _save_joint_checkpoint(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        candidate_frontier_manifest_sha256,
                        call_manifest,
                        prepared_by_candidate[candidate.candidate_id],
                        chronology_by_candidate[candidate.candidate_id],
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
                    completed_joint_call_count=completed_calls,
                    expected_joint_call_count=total_calls,
                )
                raise
            if observed_call_manifest != call_manifest:
                raise RuntimeError("RTS-GMLC AC-aware joint call manifest drifted")
            parts.append(rows)
            completed_calls += 1
            run_row = rows.runs[0]
            progress.emit(
                "joint_call_completed",
                stage="joint_ac",
                candidate_id=candidate.candidate_id,
                requested_candidate_id=candidate.requested_candidate_id,
                initial_strategy=strategy,
                solver_success=_parse_bool(
                    run_row["solver_success"], label="solver_success"
                ),
                feasibility_witnessed=_parse_bool(
                    run_row["feasibility_witnessed"], label="feasibility_witnessed"
                ),
                return_status=str(run_row["return_status"]),
                iterations=_exact_int(run_row["iterations"], label="iterations"),
                native_log=str(native_log.resolve()),
                native_log_sha256=_sha256(native_log),
                worker_result_manifest_sha256=worker_manifest,
                checkpoint_manifest_sha256=checkpoint_manifest,
                call_registration_manifest_sha256=call_manifest,
                completed_joint_call_count=completed_calls,
                expected_joint_call_count=total_calls,
            )

    merged = _merge_joint_rows(parts)
    checkpoint_rows, checkpoint_manifests, call_manifests = _load_all_joint_checkpoints(
        context,
        output_root,
        candidates,
        candidate_frontier_manifest_sha256,
        prepared_by_candidate,
        chronology_by_candidate,
    )
    if merged != checkpoint_rows:
        raise RuntimeError("RTS-GMLC AC-aware resumed joint row order drifted")
    _validate_joint_result_rows(
        context,
        candidates,
        prepared_by_candidate,
        chronology_by_candidate,
        merged.runs,
        merged.hours,
        merged.generators,
        merged.buses,
        merged.branches,
        merged.reserves,
    )
    summary = _joint_summary(
        context,
        registration,
        candidates,
        candidate_frontier_manifest_sha256,
        merged.runs,
        checkpoint_manifests,
        call_manifests,
    )

    def writer(staging: Path) -> None:
        _write_joint_rows(staging, merged)
        _write_exact_json(staging / "summary.json", summary)

    _publish_immutable_payload(
        target,
        writer,
        validator=lambda staging: _load_joint_results(
            context,
            staging,
            registration,
            candidates,
            candidate_frontier_manifest_sha256,
            prepared_by_candidate,
            chronology_by_candidate,
        ),
    )
    result = _load_joint_results(
        context,
        target,
        registration,
        candidates,
        candidate_frontier_manifest_sha256,
        prepared_by_candidate,
        chronology_by_candidate,
    )
    manifest_sha256 = _sha256(target / "SHA256SUMS")
    progress.emit(
        "joint_results_published",
        stage="joint_ac",
        joint_manifest_sha256=manifest_sha256,
        completed_joint_call_count=completed_calls,
        expected_joint_call_count=total_calls,
    )
    progress.emit(
        "attempt_completed",
        stage="joint_ac",
        joint_manifest_sha256=manifest_sha256,
        completed_joint_call_count=completed_calls,
        expected_joint_call_count=total_calls,
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
    candidates, candidate_frontier_manifest_sha256 = _load_candidate_frontier(
        context, output_root
    )
    if not candidates:
        raise RuntimeError("RTS-GMLC AC-aware candidate frontier is empty")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("joint_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid joint AC attempt ID")
    runtime = context.config["joint_ac"]["runtime_control"]
    log_root = Path(runtime["log_directory"]) / attempt_id
    target = output_root / "joint_ac"
    with ExecutionLease.acquire(
        output_root / "execution_lease",
        stage="run_joint_ac",
        attempt_id=attempt_id,
    ):
        if target.exists():
            prepared_by_candidate = {
                candidate.candidate_id: _prepared_joint_cases(context, candidate)
                for candidate in candidates
            }
            chronology_by_candidate = {
                candidate.candidate_id: _joint_chronology(context, candidate)
                for candidate in candidates
            }
            return _load_joint_results(
                context,
                target,
                registration,
                candidates,
                candidate_frontier_manifest_sha256,
                prepared_by_candidate,
                chronology_by_candidate,
            )
        progress = JsonlProgressWriter(
            log_root / "progress.jsonl",
            run_id=attempt_id,
            preregistration_id=str(context.config["preregistration"]["id"]),
            input_contract_sha256=context.input_contract_sha256,
        )
        started_utc = datetime.now(timezone.utc)
        _write_exact_json(
            log_root / "attempt.json",
            {
                "schema": "rts_gmlc_joint_ac_attempt_v1",
                "attempt_id": attempt_id,
                "pid": os.getpid(),
                "started_utc": started_utc.isoformat(),
                "preregistration_id": context.config["preregistration"]["id"],
                "input_contract_sha256": context.input_contract_sha256,
                "candidate_frontier_manifest_sha256": (
                    candidate_frontier_manifest_sha256
                ),
                "config_path": context.config_path.as_posix(),
                "implementation_repair_amendment": registration.get(
                    "implementation_repair_amendment"
                ),
            },
        )
        progress.emit(
            "attempt_started",
            stage="joint_ac",
            started_utc=started_utc.isoformat(),
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
                candidate_frontier_manifest_sha256,
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
                    "Failed to emit joint attempt_failed: "
                    + (str(logging_error) or repr(logging_error))
                )
            raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=_CONFIG_PATH)
    parser.add_argument(
        "--stage",
        choices=(
            "prepare",
            "generate-candidates",
            "run-joint-ac",
            "joint-call-worker",
            "all",
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
        value is None for value in worker_values
    ):
        parser.error("joint-call-worker requires candidate, strategy, result, and log")
    if args.stage != "joint-call-worker" and any(
        value is not None for value in worker_values
    ):
        parser.error("joint worker arguments are only valid for joint-call-worker")
    if args.attempt_id is not None and args.stage not in {
        "generate-candidates",
        "run-joint-ac",
        "all",
    }:
        parser.error("--attempt-id is only valid for formal parent stages")
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
    elif args.stage == "joint-call-worker":
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
    else:
        prepare_preregistration(args.config, output_directory=args.output_directory)
        generate_candidate_frontier(
            args.config,
            output_directory=args.output_directory,
            attempt_id=args.attempt_id,
        )
        joint_attempt_id = (
            None if args.attempt_id is None else f"{args.attempt_id}_joint"
        )
        result = run_joint_ac(
            args.config,
            output_directory=args.output_directory,
            attempt_id=joint_attempt_id,
        )
    print(
        json.dumps(
            _exact_json_payload(result),
            allow_nan=False,
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
