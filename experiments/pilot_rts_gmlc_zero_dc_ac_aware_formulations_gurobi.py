"""Compare a full selected-state proxy MILP with exact constraint generation."""

from __future__ import annotations

import argparse
import gc
import importlib.metadata
import json
import math
import os
import platform
import re
import shutil
import statistics
import time
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from highspy import Highs
from pyomo.contrib.solver.common.results import (
    TerminationCondition as V2TerminationCondition,
)
from pyomo.contrib.solver.solvers.highs import Highs as PyomoHighsV2
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

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment as parent
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.grid.rts_gmlc_scuc import (
    _audit_solution,
    _build_context as _build_scuc_context,
    _build_model,
    _constraint_violation,
    _integrality_violation,
    _validate_inputs,
)
from src.grid.rts_gmlc_exact_cg import (
    NORMAL_STATE_ID as _NORMAL_STATE_ID,
    STAGES as _STAGES,
    SharedSnapshot as _SharedSnapshot,
    apply_shared_snapshot as _apply_shared_snapshot,
    assert_conditionally_independent_recourse,
    extract_shared_snapshot,
    final_max_certificate as _final_proxy_certificate,
    orient_bound_interval as _orient_bound_interval,
    promotions as _promotions,
    relax_fixed_integer_variables as _relax_fixed_integer_variables,
    screen_plan as _screen_plan,
    shared_snapshot_violation as _shared_snapshot_violation,
    structured_sha256 as _structured_sha256,
)
from src.solvers.mip_progress import (
    JsonlProgressWriter,
    ProgressHeartbeat,
    highs_runtime_options,
)

_CONFIG_PATH = Path("configs/rts_gmlc_zero_dc_ac_aware_formulation_pilot.yaml")
_SCRIPT_PATH = Path(__file__).resolve()
_TOP_LEVEL_KEYS = {
    "pilot",
    "provenance",
    "formulations",
    "constraint_generation",
    "budget",
    "solver",
    "timing",
    "expected_full_model_size",
    "selection",
    "output",
}
_SEQUENCE_FIELDS = (
    "timestamps",
    "periods",
    "system_demand_by_bus_mw",
    "generator_availability",
    "dc_requested_mw",
    "dc_flexible_demand_mw",
    "dc_recoverable_flexible_mw",
    "dc_physical_maximum_mw",
    "dc_connected_capacity_mw",
    "dc_call_limit_mw",
    "recovery_headroom_mw",
)
_FORMULATIONS = (
    "full_state_monolith",
    "exact_selected_state_constraint_generation",
)
_INCUMBENT_TERMINATIONS = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
    TerminationCondition.maxTimeLimit,
    TerminationCondition.feasible,
}


@dataclass(frozen=True)
class _Problem:
    parent_context: Any
    request: Any
    points: tuple[Any, ...]
    states: tuple[Any, ...]
    all_state_ids: tuple[str, ...]
    initial_active_state_ids: tuple[str, ...]
    cost_budget_usd: float
    parent_full_cost_usd: float
    parent_horizon_cost_usd: float


@dataclass(frozen=True)
class _ModelHandle:
    model: Any
    scuc_context: Any
    state_ids: tuple[str, ...]
    stage: str
    sense: str
    base_variables: int
    base_constraints: int
    formulation_variables: int
    formulation_constraints: int
    decision_objective_target_usd: float | None = None


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _TOP_LEVEL_KEYS:
        raise ValueError("Formulation pilot config schema drifted")

    pilot = config["pilot"]
    if pilot != {
        "id": "rts_gmlc_google_day0_zero_dc_ac_aware_formulation_pilot_v1",
        "schema": "rts_gmlc_zero_dc_ac_aware_formulation_pilot_v1",
        "status": "repository_local_formulation_pilot_after_solver_benchmark_v1",
        "evidence_scope": "nonformal_formulation_runtime_pilot_no_candidate_or_ac_claim",
        "horizon_start_index": 0,
        "horizon_hours": 6,
        "selected_state_count": 24,
        "relative_cost_budget_delta": 0.0075,
        "candidate_or_joint_ac_outcomes_used": False,
    }:
        raise ValueError("Formulation pilot scope drifted")

    formulations = config["formulations"]
    if (
        formulations.get("included") != list(_FORMULATIONS)
        or formulations.get("execution_order")
        != [
            "full_state_monolith_r1",
            "exact_selected_state_constraint_generation_r1",
            "exact_selected_state_constraint_generation_r2",
            "full_state_monolith_r2",
        ]
        or formulations.get("stage_executed") != "proxy_maximization"
        or formulations.get("cost_normalization_executed") is not False
        or formulations.get("both_formulations_use_identical_full_problem_contract")
        is not True
        or formulations.get("no_formal_candidate_selection") is not True
    ):
        raise ValueError("Formulation pilot comparison contract drifted")

    cg = config["constraint_generation"]
    initial = tuple(str(item) for item in cg.get("initial_active_state_ids", ()))
    if (
        len(initial) != 9
        or initial[0] != _NORMAL_STATE_ID
        or len(set(initial)) != len(initial)
        or cg.get("initial_active_state_source") != "parent_zero_final_active_state_ids"
        or cg.get("screen_policy_by_stage")
        != {
            "proxy_maximization": "rescreen_every_inactive_state_after_every_master",
            "cost_normalization": "rescreen_every_inactive_state_after_every_master",
        }
        or cg.get("screen_statuses")
        != ["feasible", "certified_infeasible", "unresolved"]
        or cg.get("promote_statuses") != ["certified_infeasible", "unresolved"]
        or cg.get("unresolved_is_not_infeasibility_claim") is not True
        or cg.get("shared_variable_components")
        != [
            "commitment",
            "startup",
            "shutdown",
            "normal_generation",
            "normal_dc_flow",
            "normal_angle_degrees",
            "normal_branch_flow",
            "segment_power",
            "reserve_up",
            "reactive_proxy",
        ]
        or cg.get("shared_values_use_full_precision") is not True
        or cg.get("shared_value_rounding_or_clamping_allowed") is not False
        or cg.get("cross_contingency_shared_recourse_allowed") is not False
        or cg.get("final_verification")
        != "all_24_state_fixed_shared_lp_and_independent_residual_audit"
        or cg.get("proxy_certificate_lower_bound")
        != "final_full_feasible_incumbent_proxy"
        or cg.get("proxy_certificate_upper_bound")
        != "minimum_valid_dual_upper_bound_across_all_masters"
    ):
        raise ValueError("Exact constraint-generation contract drifted")

    solver = config["solver"]
    if (
        solver.get("name") not in ("highs", "gurobi")
        or int(solver.get("threads", -1)) != 4
        or solver.get("threads_source")
        != "published_solver_benchmark_v1_nonobjective_selection"
        or int(solver.get("repetitions", -1)) != 2
        or float(solver.get("target_mip_relative_gap")) != 1.0e-4
        or float(solver.get("mip_absolute_gap")) != 0.0
        or float(solver.get("feasibility_tolerance")) != 1.0e-6
        or float(solver.get("bound_consistency_tolerance")) != 1.0e-6
        or int(solver.get("random_seed", -1)) != 0
        or float(solver.get("time_limit_seconds_per_call")) != 120.0
        or int(solver.get("mip_report_level", -1)) != 2
        or float(solver.get("mip_min_logging_interval_seconds")) != 5.0
        or solver.get("time_limit_incumbent_allowed_for_screening") is not True
        or solver.get("eligibility_requires_final_full_audit_and_actual_gap")
        is not True
    ):
        raise ValueError("Formulation pilot solver contract drifted")

    budget = config["budget"]
    if budget != {
        "baseline": "published_parent_zero_dispatch_first_6h_reconstructed_with_scuc_cost_formula",
        "full_horizon_reconstruction_absolute_tolerance_usd": 1.0e-6,
        "cost_cap_absolute_tolerance_usd": 1.0e-4,
    }:
        raise ValueError("Formulation pilot budget drifted")

    if config["expected_full_model_size"] != {
        "base_variables": 53922,
        "base_constraints": 87508,
        "proxy_stage_variables": 53923,
        "proxy_stage_constraints": 87545,
    }:
        raise ValueError("Formulation pilot full-model size drifted")

    selection = config["selection"]
    if (
        selection.get("eligibility_rule")
        != "both_repetitions_pass_formulation_specific_full_audit_and_actual_gap"
        or selection.get("ranking_rule")
        != [
            "minimum_median_total_elapsed_seconds",
            "minimum_maximum_total_elapsed_seconds",
            "formulation_order",
        ]
        or selection.get("objective_value_used") is not False
        or selection.get("no_eligible_formulation_rule")
        != "inconclusive_no_formulation_selected"
    ):
        raise ValueError("Formulation pilot selection rule drifted")

    if config["timing"] != {
        "heartbeat_interval_seconds": 30.0,
        "measured_scope": [
            "model_build",
            "every_master_solve",
            "every_inactive_state_screen_build_and_solve",
            "active_set_rebuild",
            "final_full_state_fixed_shared_lp_build_solve_and_audit",
        ],
        "native_solver_logs_included": True,
        "durable_jsonl_events_fsync": True,
        "completed_live_logs_snapshotted_into_atomic_artifact": True,
    }:
        raise ValueError("Formulation pilot timing contract drifted")

    output = config["output"]
    if output != {
        "directory": "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_formulation_pilot_v1",
        "log_directory": "results/logs/rts_gmlc_zero_dc_ac_aware_formulation_pilot_v1",
        "preparation_subdirectory": "preparation",
        "comparison_subdirectory": "comparison",
    }:
        raise ValueError("Formulation pilot output contract drifted")
    return config


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object at {root / name}")
    return payload


def _verify_manifest_hash(root: Path, expected: str, label: str) -> None:
    _verify_output_manifest(root)
    if _sha256(root / "SHA256SUMS") != expected:
        raise RuntimeError(f"{label} manifest drifted")


def _verify_provenance(config: Mapping[str, Any]) -> dict[str, Any]:
    frozen = config["provenance"]
    path_hashes = {
        str(frozen["v2_config_path"]): str(frozen["v2_config_sha256"]),
        str(frozen["v2_runner_path"]): str(frozen["v2_runner_sha256"]),
        str(frozen["solver_benchmark_config_path"]): str(
            frozen["solver_benchmark_config_sha256"]
        ),
        str(frozen["solver_benchmark_script_path"]): str(
            frozen["solver_benchmark_script_sha256"]
        ),
        str(frozen["scuc_core_path"]): str(frozen["scuc_core_sha256"]),
    }
    for raw_path, expected in path_hashes.items():
        path = Path(raw_path)
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(
                f"Frozen formulation-pilot dependency drifted: {raw_path}"
            )

    v2_root = Path(frozen["v2_root"])
    _verify_manifest_hash(
        v2_root / "preregistration",
        str(frozen["v2_preregistration_manifest_sha256"]),
        "v2 preregistration",
    )
    _verify_manifest_hash(
        v2_root / "operational_termination",
        str(frozen["v2_operational_termination_manifest_sha256"]),
        "v2 operational termination",
    )
    registration = _load_json(v2_root / "preregistration", "registration.json")
    termination = _load_json(v2_root / "operational_termination", "termination.json")
    if (
        registration.get("input_contract_sha256") != frozen["v2_input_contract_sha256"]
        or registration.get("candidate_frontier_outcomes_observed") is not False
        or registration.get("joint_ac_outcomes_observed") is not False
        or termination.get("partial_candidate_solution_persisted") is not False
        or termination.get("joint_ac_solver_call_count") != 0
    ):
        raise RuntimeError("Frozen v2 provenance contract drifted")

    zero_root = Path(frozen["zero_dispatch_root"])
    _verify_manifest_hash(
        zero_root,
        str(frozen["zero_dispatch_manifest_sha256"]),
        "parent zero dispatch",
    )
    zero_summary = _load_json(zero_root, "summary.json")
    if _sha256(zero_root / "summary.json") != frozen["zero_dispatch_summary_sha256"]:
        raise RuntimeError("Parent zero summary drifted")
    initial_ids = tuple(
        zero_summary["constraint_generation_audit"]["final_active_state_ids"]
    )
    expected_initial = tuple(
        config["constraint_generation"]["initial_active_state_ids"]
    )
    if initial_ids != expected_initial:
        raise RuntimeError("Parent zero active-state seed drifted")

    benchmark_root = Path(frozen["solver_benchmark_root"])
    _verify_manifest_hash(
        benchmark_root / "preparation",
        str(frozen["solver_benchmark_preparation_manifest_sha256"]),
        "solver benchmark preparation",
    )
    _verify_manifest_hash(
        benchmark_root / "benchmark",
        str(frozen["solver_benchmark_result_manifest_sha256"]),
        "solver benchmark result",
    )
    benchmark_summary = _load_json(benchmark_root / "benchmark", "summary.json")
    if (
        _sha256(benchmark_root / "benchmark" / "summary.json")
        != frozen["solver_benchmark_summary_sha256"]
        or benchmark_summary["selection"]["status"]
        != frozen["solver_benchmark_selection_status"]
        or benchmark_summary["selection"]["selected_threads"]
        != frozen["solver_benchmark_selected_threads"]
        or benchmark_summary.get("objective_value_used_for_selection") is not False
    ):
        raise RuntimeError("Published solver benchmark selection drifted")

    progress_path = Path(frozen["progress_helper_path"])
    exact_cg_path = Path(frozen["exact_cg_module_path"])
    if not progress_path.is_file() or not exact_cg_path.is_file():
        raise RuntimeError("Formulation pilot helper source is missing")
    return {
        "path_hashes": path_hashes,
        "progress_helper_sha256": _sha256(progress_path),
        "exact_cg_module_sha256": _sha256(exact_cg_path),
        "v2_preregistration_manifest_sha256": _sha256(
            v2_root / "preregistration" / "SHA256SUMS"
        ),
        "v2_operational_termination_manifest_sha256": _sha256(
            v2_root / "operational_termination" / "SHA256SUMS"
        ),
        "zero_dispatch_manifest_sha256": _sha256(zero_root / "SHA256SUMS"),
        "zero_dispatch_summary_sha256": _sha256(zero_root / "summary.json"),
        "solver_benchmark_preparation_manifest_sha256": _sha256(
            benchmark_root / "preparation" / "SHA256SUMS"
        ),
        "solver_benchmark_result_manifest_sha256": _sha256(
            benchmark_root / "benchmark" / "SHA256SUMS"
        ),
        "solver_benchmark_summary_sha256": _sha256(
            benchmark_root / "benchmark" / "summary.json"
        ),
        "initial_active_state_ids": list(initial_ids),
        "selected_threads": benchmark_summary["selection"]["selected_threads"],
    }


def _software_versions() -> dict[str, str]:
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for package in ("highspy", "numpy", "pyomo", "pyyaml"):
        versions[package] = importlib.metadata.version(package)
    return versions


def _preparation_payload(
    config_path: Path, config: Mapping[str, Any]
) -> dict[str, Any]:
    contract = _stable_json(
        {key: config[key] for key in _TOP_LEVEL_KEYS if key != "output"}
    )
    provenance = _verify_provenance(config)
    input_contract_sha256 = _structured_sha256(
        {"contract": contract, "provenance": provenance}
    )
    return {
        "schema": "rts_gmlc_zero_dc_ac_aware_formulation_pilot_preparation_v1",
        "pilot_id": config["pilot"]["id"],
        "status": "prepared_not_run",
        "config_sha256": _sha256(config_path),
        "script_sha256": _sha256(_SCRIPT_PATH),
        "input_contract_sha256": input_contract_sha256,
        "contract": contract,
        "provenance": provenance,
        "software_versions": _software_versions(),
    }


def _output_root(config: Mapping[str, Any], override: Path | None) -> Path:
    return override or Path(config["output"]["directory"])


def prepare(
    config_path: Path = _CONFIG_PATH, *, output_directory: Path | None = None
) -> dict[str, Any]:
    config = _read_config(config_path)
    payload = _preparation_payload(config_path, config)
    output_root = _output_root(config, output_directory)
    target = output_root / config["output"]["preparation_subdirectory"]
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != payload:
            raise RuntimeError("Published formulation-pilot preparation drifted")
        return observed

    def writer(staging: Path) -> None:
        _write_json(staging / "registration.json", payload)
        shutil.copyfile(config_path, staging / "config.yaml")
        shutil.copyfile(_SCRIPT_PATH, staging / "pilot.py")
        snapshot_paths = {
            Path(config["provenance"]["v2_runner_path"]),
            Path(config["provenance"]["scuc_core_path"]),
            Path(config["provenance"]["progress_helper_path"]),
            Path(config["provenance"]["exact_cg_module_path"]),
            Path(config["provenance"]["solver_benchmark_config_path"]),
            Path(config["provenance"]["solver_benchmark_script_path"]),
        }
        for source in sorted(snapshot_paths, key=lambda item: item.as_posix()):
            destination = staging / "source_snapshot" / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        frozen = config["provenance"]
        artifact_paths = (
            Path(frozen["v2_root"]) / "preregistration" / "SHA256SUMS",
            Path(frozen["v2_root"]) / "operational_termination" / "SHA256SUMS",
            Path(frozen["zero_dispatch_root"]) / "SHA256SUMS",
            Path(frozen["zero_dispatch_root"]) / "summary.json",
            Path(frozen["solver_benchmark_root"]) / "preparation" / "SHA256SUMS",
            Path(frozen["solver_benchmark_root"]) / "benchmark" / "SHA256SUMS",
            Path(frozen["solver_benchmark_root"]) / "benchmark" / "summary.json",
        )
        for source in artifact_paths:
            relative = source.parent / (
                "manifest.txt" if source.name == "SHA256SUMS" else source.name
            )
            destination = staging / "artifact_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preparation(
    config_path: Path,
    config: Mapping[str, Any],
    output_root: Path,
) -> tuple[dict[str, Any], str]:
    root = output_root / config["output"]["preparation_subdirectory"]
    if not root.exists():
        raise RuntimeError("Run requires a published formulation-pilot preparation")
    observed = _load_json(root, "registration.json")
    expected = _preparation_payload(config_path, config)
    if observed != expected:
        raise RuntimeError("Formulation-pilot preparation no longer matches inputs")
    return observed, _sha256(root / "SHA256SUMS")


def _piecewise_cost(generator: Any, generation_mw: float, online: bool) -> float:
    generation = float(generation_mw)
    if not online:
        if abs(generation) > 1.0e-6:
            raise RuntimeError(f"Offline parent generator {generator.uid} has output")
        return 0.0
    breakpoints = tuple(float(item) for item in generator.cost_breakpoints_mw)
    costs = tuple(float(item) for item in generator.cost_values_usd_per_hour)
    if len(breakpoints) != 4 or len(costs) != 4:
        raise RuntimeError(f"Parent cost curve drifted for {generator.uid}")
    if generation < breakpoints[0] - 1.0e-6 or generation > breakpoints[-1] + 1.0e-6:
        raise RuntimeError(
            f"Parent generation is outside the cost curve for {generator.uid}"
        )
    remaining = max(0.0, generation - breakpoints[0])
    total = costs[0]
    for index in range(3):
        width = breakpoints[index + 1] - breakpoints[index]
        used = min(remaining, width)
        slope = (costs[index + 1] - costs[index]) / width
        total += slope * used
        remaining -= used
    if remaining > 1.0e-6:
        raise RuntimeError(f"Parent cost reconstruction overflowed for {generator.uid}")
    return total


def _reconstruct_hourly_costs(
    generators: Sequence[Any],
    timestamp_keys: Sequence[str],
    generation: Mapping[str, Mapping[str, float]],
    commitment: Mapping[str, Mapping[str, bool]],
    initial_commitment: Mapping[str, bool],
) -> tuple[float, ...]:
    thermal = tuple(
        generator
        for generator in generators
        if generator.dispatch_mode == "committable"
    )
    previous = dict(initial_commitment)
    hourly = []
    for timestamp in timestamp_keys:
        total = 0.0
        for generator in thermal:
            uid = generator.uid
            online = bool(commitment[timestamp][uid])
            total += _piecewise_cost(generator, generation[timestamp][uid], online)
            if online and not previous[uid]:
                total += float(generator.cold_start_cost_usd)
            if previous[uid] and not online:
                total += float(generator.shutdown_cost_usd)
            previous[uid] = online
        hourly.append(total)
    return tuple(hourly)


def _truncate_request(request: Any, start: int, hours: int) -> Any:
    stop = start + hours
    updates = {
        field: tuple(getattr(request, field)[start:stop]) for field in _SEQUENCE_FIELDS
    }
    if any(len(values) != hours for values in updates.values()):
        raise RuntimeError("Parent request is shorter than the pilot horizon")
    return replace(request, **updates)


def _build_problem(config: Mapping[str, Any]) -> _Problem:
    frozen = config["provenance"]
    context = parent._build_context(Path(frozen["v2_config_path"]))
    if context.input_contract_sha256 != frozen["v2_input_contract_sha256"]:
        raise RuntimeError("Parent v2 context drifted before formulation pilot")
    request = _truncate_request(
        context.request,
        int(config["pilot"]["horizon_start_index"]),
        int(config["pilot"]["horizon_hours"]),
    )
    tolerance = float(config["solver"]["feasibility_tolerance"])
    points = _validate_inputs(context.zero.scan.data, request, tolerance)
    states = tuple(context.selection.states)
    all_state_ids = tuple(str(state.state_id) for state in states)
    if (
        len(states) != int(config["pilot"]["selected_state_count"])
        or all_state_ids[0] != _NORMAL_STATE_ID
        or len(set(all_state_ids)) != len(all_state_ids)
    ):
        raise RuntimeError("Formulation-pilot selected-state contract drifted")
    initial_active = tuple(config["constraint_generation"]["initial_active_state_ids"])
    if not set(initial_active) <= set(all_state_ids):
        raise RuntimeError("Constraint-generation seed contains an unknown state")

    _hourly, generation, commitment, _flows = parent._load_zero_dispatch(
        context.zero, parent._ZERO_OUTPUT_ROOT
    )
    timestamp_keys = tuple(
        timestamp.isoformat() for timestamp in context.request.timestamps
    )
    hourly_costs = _reconstruct_hourly_costs(
        tuple(context.zero.scan.data.generators),
        timestamp_keys,
        generation,
        commitment,
        context.initial_state.commitment,
    )
    full_cost = sum(hourly_costs)
    if not math.isclose(
        full_cost,
        float(frozen["expected_full_horizon_cost_usd"]),
        rel_tol=0.0,
        abs_tol=float(
            config["budget"]["full_horizon_reconstruction_absolute_tolerance_usd"]
        ),
    ):
        raise RuntimeError("Parent full-horizon cost reconstruction drifted")
    hours = int(config["pilot"]["horizon_hours"])
    horizon_cost = sum(hourly_costs[:hours])
    budget = horizon_cost * (1.0 + float(config["pilot"]["relative_cost_budget_delta"]))
    return _Problem(
        parent_context=context,
        request=request,
        points=tuple(points),
        states=states,
        all_state_ids=all_state_ids,
        initial_active_state_ids=initial_active,
        cost_budget_usd=budget,
        parent_full_cost_usd=full_cost,
        parent_horizon_cost_usd=horizon_cost,
    )


def _component_count(model: Any, component: Any) -> int:
    return sum(1 for _ in model.component_data_objects(component, active=True))


def _ordered_states(problem: _Problem, state_ids: Sequence[str]) -> tuple[Any, ...]:
    requested = tuple(str(item) for item in state_ids)
    if (
        not requested
        or requested[0] != _NORMAL_STATE_ID
        or len(requested) != len(set(requested))
        or not set(requested) <= set(problem.all_state_ids)
    ):
        raise ValueError("Invalid active-state subset")
    requested_set = set(requested)
    ordered = tuple(
        state for state in problem.states if str(state.state_id) in requested_set
    )
    if tuple(str(state.state_id) for state in ordered) != tuple(
        state_id for state_id in problem.all_state_ids if state_id in requested_set
    ):
        raise RuntimeError("Active-state ordering drifted")
    return ordered


def _build_model_handle(
    problem: _Problem,
    config: Mapping[str, Any],
    state_ids: Sequence[str],
    *,
    stage: str,
    proxy_floor: float | None = None,
) -> _ModelHandle:
    if stage not in _STAGES:
        raise ValueError(f"Unknown candidate stage {stage}")
    states = _ordered_states(problem, state_ids)
    scuc_context = _build_scuc_context(
        problem.parent_context.zero.scan.data,
        problem.request,
        problem.points,
        states,
    )
    model = _build_model(
        scuc_context, fixed_initial=problem.parent_context.initial_state
    )
    base_variables = _component_count(model, Var)
    base_constraints = _component_count(model, Constraint)
    decision_objective_target = None
    if stage != "level_set_cost_minimization":
        cost_cap = problem.cost_budget_usd + float(
            config["budget"]["cost_cap_absolute_tolerance_usd"]
        )
        model.cost_cap = Constraint(expr=model.operating_cost <= cost_cap)
        if stage == "level_set_budget_feasibility":
            decision_objective_target = cost_cap
    fixed, variable, denominators = parent._proxy_components(
        problem.parent_context, problem.points
    )
    model.reactive_proxy = Var(bounds=(0.0, 1.0))
    model.reactive_proxy_constraints = ConstraintList()
    for time_index in range(len(problem.points)):
        for area in denominators[time_index]:
            for direction in (0, 1):
                numerator = fixed[area][direction] + sum(
                    capability[direction] * model.commitment[time_index, uid]
                    for uid, capability in variable[area].items()
                )
                model.reactive_proxy_constraints.add(
                    model.reactive_proxy
                    <= numerator / denominators[time_index][area][direction]
                )
    if stage == "proxy_maximization":
        if proxy_floor is not None:
            raise ValueError("Proxy stage cannot receive a proxy floor")
        model.objective.deactivate()
        model.reactive_proxy_objective = Objective(
            expr=model.reactive_proxy, sense=maximize
        )
        sense = "maximize"
    else:
        if proxy_floor is None or not math.isfinite(float(proxy_floor)):
            raise ValueError("Cost stage requires a finite proxy floor")
        model.reactive_proxy_floor = Constraint(
            expr=model.reactive_proxy >= float(proxy_floor)
        )
        sense = "minimize"

    handle = _ModelHandle(
        model=model,
        scuc_context=scuc_context,
        state_ids=tuple(str(state.state_id) for state in states),
        stage=stage,
        sense=sense,
        base_variables=base_variables,
        base_constraints=base_constraints,
        formulation_variables=_component_count(model, Var),
        formulation_constraints=_component_count(model, Constraint),
        decision_objective_target_usd=decision_objective_target,
    )
    _assert_conditionally_independent_recourse(handle)
    if handle.state_ids == problem.all_state_ids and stage == "proxy_maximization":
        expected = config["expected_full_model_size"]
        observed = (
            handle.base_variables,
            handle.base_constraints,
            handle.formulation_variables,
            handle.formulation_constraints,
        )
        required = (
            int(expected["base_variables"]),
            int(expected["base_constraints"]),
            int(expected["proxy_stage_variables"]),
            int(expected["proxy_stage_constraints"]),
        )
        if observed != required:
            raise RuntimeError(
                "Formulation-pilot full model size drifted: "
                f"observed={observed}, expected={required}"
            )
    return handle


def _assert_conditionally_independent_recourse(handle: _ModelHandle) -> None:
    assert_conditionally_independent_recourse(handle.model)


def _extract_shared_snapshot(handle: _ModelHandle) -> _SharedSnapshot:
    return extract_shared_snapshot(handle.model)


def _all_variables_finite(model: Any) -> bool:
    for variable in model.component_data_objects(Var, active=True):
        candidate = value(variable, exception=False)
        if candidate is None or not math.isfinite(float(candidate)):
            return False
    return True


def _incumbent_is_usable(
    *,
    termination_condition: object,
    solution_loaded: bool,
    incumbent_objective: object,
    maximum_constraint_violation: object,
    maximum_integrality_violation: object,
    variables_finite: bool,
    feasibility_tolerance: float,
) -> bool:
    objective = _optional_float(incumbent_objective)
    constraint_violation = _optional_float(maximum_constraint_violation)
    integrality_violation = _optional_float(maximum_integrality_violation)
    return bool(
        termination_condition in _INCUMBENT_TERMINATIONS
        and solution_loaded
        and objective is not None
        and constraint_violation is not None
        and constraint_violation <= float(feasibility_tolerance)
        and integrality_violation is not None
        and integrality_violation <= float(feasibility_tolerance)
        and variables_finite
    )


def _optional_float(item: object) -> float | None:
    try:
        candidate = float(item)
    except (TypeError, ValueError):
        return None
    return candidate if math.isfinite(candidate) else None


def _fsync_if_present(path: Path) -> None:
    if not path.exists():
        return
    with path.open("ab") as output:
        output.flush()
        os.fsync(output.fileno())


def _legacy_incumbent_termination(v2_termination: object) -> object:
    if v2_termination == V2TerminationCondition.convergenceCriteriaSatisfied:
        return TerminationCondition.optimal
    if v2_termination == V2TerminationCondition.maxTimeLimit:
        return TerminationCondition.maxTimeLimit
    if v2_termination == V2TerminationCondition.objectiveLimit:
        return TerminationCondition.feasible
    return TerminationCondition.unknown




# Keys whose values were fixed by the frozen Gurobi pilot benchmark or by the
# per-call contract. A config-supplied override of any of these would silently
# change the frozen solver selection, so it is refused instead of applied.
FROZEN_GUROBI_OPTION_KEYS = frozenset(
    {
        "MIPGap",
        "MIPGapAbs",
        "Seed",
        "Threads",
        "FeasibilityTol",
        "OptimalityTol",
        "TimeLimit",
        "LogToConsole",
        "LogFile",
        "DisplayInterval",
        "Cutoff",
    }
)


class UnreadableSolverOptionError(RuntimeError):
    """Raised when configured Gurobi options cannot be applied as declared."""


def gurobi_runtime_options(
    *,
    mip_relative_gap: float,
    threads: int,
    random_seed: int,
    feasibility_tolerance: float,
    time_limit_seconds: float,
    log_file: Path,
    mip_min_logging_interval_seconds: float,
    objective_cutoff: float | None = None,
    extra_options: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Gurobi option dict (legacy Pyomo SolverFactory interface).

    Defined here rather than in src/solvers/mip_progress.py because
    mip_progress.py is frozen in the base-v4 _IMPLEMENTATION_PATHS chain;
    any change to it invalidates all repair checkpoint contracts.

    ``extra_options`` carries preregistered Gurobi parameters such as
    ``IntegralityFocus``. It may introduce new keys and may retune
    ``IntFeasTol``, but it may not override any key in
    ``FROZEN_GUROBI_OPTION_KEYS``.
    """
    resolved_log = Path(log_file).resolve()
    resolved_log.parent.mkdir(parents=True, exist_ok=True)
    opts: dict[str, object] = {
        "MIPGap": float(mip_relative_gap),
        "MIPGapAbs": 0.0,
        "Seed": int(random_seed),
        "Threads": int(threads),
        "FeasibilityTol": float(feasibility_tolerance),
        "OptimalityTol": float(feasibility_tolerance),
        "IntFeasTol": float(feasibility_tolerance),
        "TimeLimit": float(time_limit_seconds),
        "LogToConsole": 0,
        "LogFile": str(resolved_log),
        "DisplayInterval": max(1, int(mip_min_logging_interval_seconds)),
    }
    if objective_cutoff is not None:
        opts["Cutoff"] = float(objective_cutoff)
    if extra_options:
        refused = sorted(set(extra_options) & FROZEN_GUROBI_OPTION_KEYS)
        if refused:
            raise UnreadableSolverOptionError(
                "Configured Gurobi options may not override frozen keys: "
                f"{refused}"
            )
        opts.update(dict(extra_options))
    return opts


def assemble_gurobi_options(
    solver_config: Mapping[str, Any],
    *,
    native_log: Path,
    objective_cutoff: float | None,
) -> dict[str, object]:
    """Build the option dict handed to ``solver.solve`` for a Gurobi call.

    Kept separate from ``_solve_handle`` so the configuration read path can be
    tested without a solver. repair-009 lost five hours to a preregistered
    ``IntegralityFocus`` that no code read; the post-condition below makes that
    failure loud instead of silent.
    """
    configured = dict(solver_config.get("options") or {})
    options = gurobi_runtime_options(
        mip_relative_gap=float(solver_config["target_mip_relative_gap"]),
        threads=int(solver_config["threads"]),
        random_seed=int(solver_config["random_seed"]),
        feasibility_tolerance=float(solver_config["feasibility_tolerance"]),
        time_limit_seconds=float(solver_config["time_limit_seconds_per_call"]),
        log_file=native_log,
        mip_min_logging_interval_seconds=float(
            solver_config["mip_min_logging_interval_seconds"]
        ),
        objective_cutoff=objective_cutoff,
        extra_options=configured,
    )
    unapplied = sorted(
        name for name, expected in configured.items() if options.get(name) != expected
    )
    if unapplied:
        raise UnreadableSolverOptionError(
            f"Configured Gurobi options did not reach the solver: {unapplied}"
        )
    return options


def _solve_handle(
    handle: _ModelHandle,
    config: Mapping[str, Any],
    *,
    native_log: Path,
    progress: JsonlProgressWriter,
    solve_label: str,
) -> dict[str, object]:
    if native_log.exists():
        raise FileExistsError(f"Native HiGHS log already exists: {native_log}")
    solver_config = config["solver"]
    _gurobi_mode = solver_config.get("name") == "gurobi"
    if _gurobi_mode:
        decision_api = False
        solver = SolverFactory("gurobi")
        if not bool(solver.available(exception_flag=False)):
            raise RuntimeError("Gurobi is unavailable for the formulation pilot")
        solver_api = "pyomo.environ.SolverFactory.gurobi_legacy"
        objective_target = (
            _optional_float(handle.decision_objective_target_usd)
            if handle.stage == "level_set_budget_feasibility"
            else None
        )
        options = assemble_gurobi_options(
            solver_config,
            native_log=native_log,
            objective_cutoff=objective_target,
        )
    else:
        decision_api = handle.stage == "level_set_budget_feasibility"
        solver = PyomoHighsV2() if decision_api else SolverFactory("highs")
        available = (
            bool(solver.available())
            if decision_api
            else bool(solver.available(exception_flag=False))
        )
        if not available:
            raise RuntimeError("HiGHS is unavailable for the formulation pilot")
        solver_api = (
            "pyomo.contrib.solver.highs_v2"
            if decision_api
            else "pyomo.environ.SolverFactory.highs_legacy"
        )
        declared = dict(solver_config.get("options") or {})
        if declared:
            raise UnreadableSolverOptionError(
                "Gurobi-only solver options were configured for a HiGHS solve: "
                f"{sorted(declared)}"
            )
        objective_target = None
        options = highs_runtime_options(
            mip_relative_gap=float(solver_config["target_mip_relative_gap"]),
            threads=int(solver_config["threads"]),
            random_seed=int(solver_config["random_seed"]),
            feasibility_tolerance=float(solver_config["feasibility_tolerance"]),
            time_limit_seconds=float(solver_config["time_limit_seconds_per_call"]),
            log_file=native_log,
            mip_min_logging_interval_seconds=float(
                solver_config["mip_min_logging_interval_seconds"]
            ),
        )
    if decision_api:
        objective_target = _optional_float(handle.decision_objective_target_usd)
        if objective_target is None:
            raise RuntimeError("Budget decision MIP requires a finite objective target")
        options["objective_target"] = objective_target
    else:
        objective_target = None
    progress.emit(
        "solve_started",
        solve_label=solve_label,
        stage=handle.stage,
        sense=handle.sense,
        state_ids=list(handle.state_ids),
        native_log=native_log.name,
        solver_api=solver_api,
        effective_solver_options={
            key: (str(value) if isinstance(value, Path) else value)
            for key, value in sorted(options.items())
        },
    )
    if not _gurobi_mode:
        Highs.resetGlobalScheduler(True)
    started = time.perf_counter()
    try:
        with ProgressHeartbeat(
            progress,
            interval_seconds=float(config["timing"]["heartbeat_interval_seconds"]),
            payload={"solve_label": solve_label, "native_log": native_log.name},
        ):
            if decision_api:
                results = solver.solve(
                    handle.model,
                    load_solutions=False,
                    raise_exception_on_nonoptimal_result=False,
                    solver_options=options,
                )
            else:
                results = solver.solve(
                    handle.model, load_solutions=False, tee=False, options=options
                )
        solve_seconds = time.perf_counter() - started
    except Exception as error:
        _fsync_if_present(native_log)
        record = {
            "solve_label": solve_label,
            "stage": handle.stage,
            "sense": handle.sense,
            "solve_seconds": time.perf_counter() - started,
            "termination_condition": None,
            "solver_status": None,
            "solver_api": solver_api,
            "solver_api_solution_status": None,
            "global_infeasibility_certified": False,
            "solver_objective_bound": None,
            "solver_objective_incumbent": None,
            "decision_objective_target_usd": objective_target,
            "solution_loaded": False,
            "incumbent_usable": False,
            "raw_lower_bound": None,
            "raw_upper_bound": None,
            "incumbent_objective": None,
            "maximum_constraint_violation": None,
            "maximum_integrality_violation": None,
            "error_type": type(error).__name__,
            "error_message": str(error) or repr(error),
            "native_log": native_log.name,
            **_orient_bound_interval(
                sense=handle.sense,
                raw_lower_bound=None,
                raw_upper_bound=None,
                incumbent_objective=None,
                consistency_tolerance=float(
                    solver_config["bound_consistency_tolerance"]
                ),
            ),
        }
        progress.emit("solve_failed", **record)
        return record
    solver_objective_bound = None
    solver_objective_incumbent = None
    global_infeasibility_certified = False
    if decision_api:
        api_termination = results.termination_condition
        termination = _legacy_incumbent_termination(api_termination)
        termination_label = str(api_termination)
        solver_status = None
        solution_status = str(results.solution_status)
        solver_objective_bound = _optional_float(results.objective_bound)
        solver_objective_incumbent = _optional_float(results.incumbent_objective)
        raw_lower = None
        raw_upper = None
        loaded = False
        if solver_objective_incumbent is not None:
            try:
                results.solution_loader.load_vars()
                loaded = True
            except Exception:
                loaded = False
        global_infeasibility_certified = bool(
            api_termination == V2TerminationCondition.provenInfeasible
            and solver_objective_incumbent is None
            and not loaded
        )
    else:
        termination = results.solver.termination_condition
        termination_label = str(termination)
        solver_status = str(results.solver.status)
        solution_status = None
        raw_lower = _optional_float(results.problem.lower_bound)
        raw_upper = _optional_float(results.problem.upper_bound)
        loaded = False
        try:
            handle.model.solutions.load_from(results)
            loaded = True
        except Exception:
            loaded = False
    _fsync_if_present(native_log)
    objective = None
    constraint_violation = None
    integrality_violation = None
    if loaded:
        objective_expression = (
            handle.model.reactive_proxy
            if handle.sense == "maximize"
            else handle.model.operating_cost
        )
        objective = _optional_float(value(objective_expression, exception=False))
        constraint_violation = float(_constraint_violation(handle.model))
        integrality_violation = float(_integrality_violation(handle.model))
    tolerance = float(solver_config["feasibility_tolerance"])
    incumbent_usable = _incumbent_is_usable(
        termination_condition=termination,
        solution_loaded=loaded,
        incumbent_objective=objective,
        maximum_constraint_violation=constraint_violation,
        maximum_integrality_violation=integrality_violation,
        variables_finite=_all_variables_finite(handle.model) if loaded else False,
        feasibility_tolerance=tolerance,
    )
    bounds = _orient_bound_interval(
        sense=handle.sense,
        raw_lower_bound=raw_lower,
        raw_upper_bound=raw_upper,
        incumbent_objective=objective,
        consistency_tolerance=float(solver_config["bound_consistency_tolerance"]),
    )
    record = {
        "solve_label": solve_label,
        "stage": handle.stage,
        "sense": handle.sense,
        "solve_seconds": solve_seconds,
        "termination_condition": termination_label,
        "solver_status": solver_status,
        "solver_api": solver_api,
        "solver_api_solution_status": solution_status,
        "global_infeasibility_certified": global_infeasibility_certified,
        "solver_objective_bound": solver_objective_bound,
        "solver_objective_incumbent": solver_objective_incumbent,
        "decision_objective_target_usd": objective_target,
        "solution_loaded": loaded,
        "incumbent_usable": incumbent_usable,
        "raw_lower_bound": raw_lower,
        "raw_upper_bound": raw_upper,
        "incumbent_objective": objective,
        "maximum_constraint_violation": constraint_violation,
        "maximum_integrality_violation": integrality_violation,
        "error_type": None,
        "error_message": None,
        "native_log": native_log.name,
        **bounds,
    }
    progress.emit("solve_completed", **record)
    return record


def _residual_audit(
    handle: _ModelHandle, problem: _Problem, tolerance: float
) -> dict[str, object]:
    residual = _audit_solution(
        handle.model,
        handle.scuc_context,
        problem.parent_context.initial_state,
        tolerance,
    )
    flags = (
        residual.commitment_feasible_by_step
        + residual.ramp_feasible_by_step
        + residual.reserve_feasible_by_step
        + residual.normal_secure_by_step
        + residual.contingency_secure_by_step
    )
    return {"passed": all(flags), **asdict(residual)}


def _screen_state(
    problem: _Problem,
    config: Mapping[str, Any],
    snapshot: _SharedSnapshot,
    state_id: str,
    *,
    stage: str,
    proxy_floor: float | None,
    native_log: Path,
    progress: JsonlProgressWriter,
    solve_label: str,
) -> dict[str, object]:
    handle = _build_model_handle(
        problem,
        config,
        (_NORMAL_STATE_ID, state_id),
        stage=stage,
        proxy_floor=proxy_floor,
    )
    _apply_shared_snapshot(handle.model, snapshot)
    _relax_fixed_integer_variables(handle.model)
    solved = _solve_handle(
        handle,
        config,
        native_log=native_log,
        progress=progress,
        solve_label=solve_label,
    )
    tolerance = float(config["solver"]["feasibility_tolerance"])
    shared_violation = (
        _shared_snapshot_violation(handle.model, snapshot)
        if solved["solution_loaded"]
        else None
    )
    residual = None
    if solved["incumbent_usable"] and shared_violation is not None:
        try:
            residual = _residual_audit(handle, problem, tolerance)
        except Exception:
            residual = None
    feasible = bool(
        solved["incumbent_usable"]
        and shared_violation is not None
        and shared_violation <= tolerance
        and residual is not None
        and residual["passed"]
    )
    if feasible:
        status = "feasible"
    elif solved.get("global_infeasibility_certified") is True:
        status = "certified_infeasible"
    else:
        status = "unresolved"
    record = {
        "state_id": state_id,
        "status": status,
        "unresolved_is_infeasibility_claim": False,
        "shared_snapshot_sha256": snapshot.sha256,
        "maximum_shared_value_violation": shared_violation,
        "residual_audit": residual,
        "solve": solved,
    }
    progress.emit("state_screen_completed", **record)
    return record


def _commitment_proxy_from_snapshot(
    problem: _Problem, snapshot: _SharedSnapshot, tolerance: float
) -> float:
    values = {
        (component, index): number for component, index, number in snapshot.values
    }
    thermal_uids = tuple(
        generator.uid
        for generator in problem.parent_context.zero.scan.data.generators
        if generator.dispatch_mode == "committable"
    )
    rows = []
    for time_index in range(len(problem.points)):
        row = {}
        for uid in thermal_uids:
            observed = values[("commitment", (time_index, uid))]
            nearest = round(observed)
            if abs(observed - nearest) > tolerance:
                raise RuntimeError("Shared commitment is not integral")
            row[uid] = bool(nearest)
        rows.append(row)
    return float(
        parent._reactive_proxy_value(
            problem.parent_context,
            problem.points,
            tuple(rows),
        )
    )


def _verify_full_fixed_snapshot(
    problem: _Problem,
    config: Mapping[str, Any],
    snapshot: _SharedSnapshot,
    *,
    stage: str,
    proxy_floor: float | None,
    native_log: Path,
    progress: JsonlProgressWriter,
    solve_label: str,
) -> dict[str, object]:
    handle = _build_model_handle(
        problem,
        config,
        problem.all_state_ids,
        stage=stage,
        proxy_floor=proxy_floor,
    )
    _apply_shared_snapshot(handle.model, snapshot)
    _relax_fixed_integer_variables(handle.model)
    solved = _solve_handle(
        handle,
        config,
        native_log=native_log,
        progress=progress,
        solve_label=solve_label,
    )
    tolerance = float(config["solver"]["feasibility_tolerance"])
    shared_violation = (
        _shared_snapshot_violation(handle.model, snapshot)
        if solved["solution_loaded"]
        else None
    )
    residual = None
    if solved["incumbent_usable"] and shared_violation is not None:
        try:
            residual = _residual_audit(handle, problem, tolerance)
        except Exception:
            residual = None
    commitment_proxy = _commitment_proxy_from_snapshot(problem, snapshot, tolerance)
    proxy_consistent = snapshot.reactive_proxy <= commitment_proxy + tolerance
    passed = bool(
        solved["incumbent_usable"]
        and shared_violation is not None
        and shared_violation <= tolerance
        and residual is not None
        and residual["passed"]
        and proxy_consistent
        and handle.state_ids == problem.all_state_ids
    )
    record = {
        "passed": passed,
        "state_count": len(handle.state_ids),
        "state_ids": list(handle.state_ids),
        "shared_snapshot_sha256": snapshot.sha256,
        "maximum_shared_value_violation": shared_violation,
        "snapshot_proxy_fraction": snapshot.reactive_proxy,
        "commitment_capability_proxy_fraction": commitment_proxy,
        "proxy_consistent": proxy_consistent,
        "residual_audit": residual,
        "solve": solved,
    }
    progress.emit("full_fixed_shared_audit_completed", **record)
    return record


def _run_monolith(
    problem: _Problem,
    config: Mapping[str, Any],
    *,
    repetition: int,
    run_log_root: Path,
    progress: JsonlProgressWriter,
) -> dict[str, object]:
    started = time.perf_counter()
    progress.emit("formulation_started", formulation="full_state_monolith")
    build_started = time.perf_counter()
    handle = _build_model_handle(
        problem,
        config,
        problem.all_state_ids,
        stage="proxy_maximization",
    )
    build_seconds = time.perf_counter() - build_started
    progress.emit(
        "model_built",
        formulation="full_state_monolith",
        build_seconds=build_seconds,
        state_ids=list(handle.state_ids),
        variables=handle.formulation_variables,
        constraints=handle.formulation_constraints,
    )
    solved = _solve_handle(
        handle,
        config,
        native_log=run_log_root / "monolith.log",
        progress=progress,
        solve_label="monolith",
    )
    tolerance = float(config["solver"]["feasibility_tolerance"])
    residual = None
    snapshot = None
    full_audit = False
    if solved["incumbent_usable"]:
        try:
            residual = _residual_audit(handle, problem, tolerance)
            snapshot = _extract_shared_snapshot(handle)
            full_audit = bool(residual["passed"])
        except Exception:
            residual = None
            snapshot = None
            full_audit = False
    certificate = _final_proxy_certificate(
        full_feasible_objective=(snapshot.reactive_proxy if snapshot else None),
        master_dual_upper_bounds=(solved["dual_bound"],),
        target_relative_gap=float(config["solver"]["target_mip_relative_gap"]),
    )
    eligible = bool(
        full_audit and solved["bound_valid"] and certificate["target_gap_attained"]
    )
    total = time.perf_counter() - started
    record = {
        "formulation": "full_state_monolith",
        "repetition": repetition,
        "eligible": eligible,
        "total_elapsed_seconds": total,
        "model_build_seconds": build_seconds,
        "shared_snapshot_sha256": snapshot.sha256 if snapshot else None,
        "full_state_audit_passed": full_audit,
        "residual_audit": residual,
        "certificate": certificate,
        "solve": solved,
    }
    progress.emit("formulation_completed", **record)
    return record


def _run_constraint_generation(
    problem: _Problem,
    config: Mapping[str, Any],
    *,
    repetition: int,
    run_log_root: Path,
    progress: JsonlProgressWriter,
    stage: str = "proxy_maximization",
    proxy_floor: float | None = None,
) -> dict[str, object]:
    if stage != "proxy_maximization" or proxy_floor is not None:
        raise ValueError("This formulation pilot executes proxy maximization only")
    started = time.perf_counter()
    formulation = "exact_selected_state_constraint_generation"
    progress.emit("formulation_started", formulation=formulation, stage=stage)
    active_ids = list(problem.initial_active_state_ids)
    master_records = []
    iteration_records = []
    master_dual_upper_bounds = []
    final_snapshot = None
    failure_reason = None
    maximum_iterations = len(problem.all_state_ids) - len(active_ids) + 1
    for iteration in range(1, maximum_iterations + 1):
        build_started = time.perf_counter()
        master = _build_model_handle(
            problem,
            config,
            tuple(active_ids),
            stage=stage,
            proxy_floor=proxy_floor,
        )
        build_seconds = time.perf_counter() - build_started
        progress.emit(
            "master_built",
            iteration=iteration,
            stage=stage,
            build_seconds=build_seconds,
            active_state_ids=list(active_ids),
            variables=master.formulation_variables,
            constraints=master.formulation_constraints,
        )
        solved = _solve_handle(
            master,
            config,
            native_log=run_log_root / f"iteration_{iteration:02d}_master.log",
            progress=progress,
            solve_label=f"iteration_{iteration:02d}_master",
        )
        solved = {**solved, "build_seconds": build_seconds}
        master_records.append(solved)
        if not solved["incumbent_usable"] or not solved["bound_valid"]:
            failure_reason = "master_lacked_audited_incumbent_or_valid_dual_bound"
            break
        tolerance = float(config["solver"]["feasibility_tolerance"])
        try:
            master_residual = _residual_audit(master, problem, tolerance)
            snapshot = _extract_shared_snapshot(master)
        except Exception:
            failure_reason = "master_shared_snapshot_or_residual_audit_failed"
            break
        if not master_residual["passed"]:
            failure_reason = "master_residual_audit_failed"
            break
        master_dual_upper_bounds.append(solved["dual_bound"])
        screen_ids = _screen_plan(
            stage=stage,
            all_state_ids=problem.all_state_ids,
            active_state_ids=active_ids,
        )
        progress.emit(
            "screen_round_started",
            iteration=iteration,
            stage=stage,
            active_state_ids=list(active_ids),
            screened_state_ids=list(screen_ids),
            shared_snapshot_sha256=snapshot.sha256,
        )
        screens = []
        for ordinal, state_id in enumerate(screen_ids, start=1):
            screens.append(
                _screen_state(
                    problem,
                    config,
                    snapshot,
                    state_id,
                    stage=stage,
                    proxy_floor=proxy_floor,
                    native_log=run_log_root
                    / f"iteration_{iteration:02d}_screen_{ordinal:02d}_{state_id}.log",
                    progress=progress,
                    solve_label=(
                        f"iteration_{iteration:02d}_screen_{ordinal:02d}_{state_id}"
                    ),
                )
            )
        promotions = _promotions(screens, problem.all_state_ids)
        iteration_records.append(
            {
                "iteration": iteration,
                "stage": stage,
                "active_state_ids": list(active_ids),
                "shared_snapshot_sha256": snapshot.sha256,
                "master_residual_audit": master_residual,
                "screen_records": screens,
                "promotions": list(promotions),
            }
        )
        if promotions:
            promoted_ids = {item["state_id"] for item in promotions}
            active_ids.extend(
                state_id
                for state_id in problem.all_state_ids
                if state_id in promoted_ids and state_id not in active_ids
            )
            progress.emit(
                "active_set_expanded",
                iteration=iteration,
                stage=stage,
                promotions=list(promotions),
                active_state_ids=list(active_ids),
            )
            continue
        final_snapshot = snapshot
        break
    else:
        failure_reason = "constraint_generation_iteration_limit_exceeded"

    final_audit = None
    certificate = _final_proxy_certificate(
        full_feasible_objective=None,
        master_dual_upper_bounds=master_dual_upper_bounds,
        target_relative_gap=float(config["solver"]["target_mip_relative_gap"]),
    )
    if failure_reason is None and final_snapshot is not None:
        final_audit = _verify_full_fixed_snapshot(
            problem,
            config,
            final_snapshot,
            stage=stage,
            proxy_floor=proxy_floor,
            native_log=run_log_root / "final_full_state_fixed_shared.log",
            progress=progress,
            solve_label="final_full_state_fixed_shared",
        )
        certificate = _final_proxy_certificate(
            full_feasible_objective=(
                final_snapshot.reactive_proxy if final_audit["passed"] else None
            ),
            master_dual_upper_bounds=master_dual_upper_bounds,
            target_relative_gap=float(config["solver"]["target_mip_relative_gap"]),
        )
    eligible = bool(
        final_audit is not None
        and final_audit["passed"]
        and certificate["valid"]
        and certificate["target_gap_attained"]
    )
    total = time.perf_counter() - started
    record = {
        "formulation": formulation,
        "repetition": repetition,
        "stage": stage,
        "eligible": eligible,
        "failure_reason": failure_reason,
        "total_elapsed_seconds": total,
        "initial_active_state_ids": list(problem.initial_active_state_ids),
        "final_active_state_ids": list(active_ids),
        "master_records": master_records,
        "iteration_records": iteration_records,
        "final_shared_snapshot_sha256": (
            final_snapshot.sha256 if final_snapshot else None
        ),
        "final_full_state_audit": final_audit,
        "certificate": certificate,
        "unresolved_promoted_is_infeasibility_claim": False,
    }
    progress.emit("formulation_completed", **record)
    return record


def _execution_specs(config: Mapping[str, Any]) -> tuple[tuple[str, int], ...]:
    specs = []
    for item in config["formulations"]["execution_order"]:
        match = re.fullmatch(
            r"(full_state_monolith|exact_selected_state_constraint_generation)_r(\d+)",
            str(item),
        )
        if match is None:
            raise ValueError("Invalid formulation-pilot execution order")
        specs.append((match.group(1), int(match.group(2))))
    expected = {
        (formulation, repetition)
        for formulation in _FORMULATIONS
        for repetition in range(1, int(config["solver"]["repetitions"]) + 1)
    }
    if len(specs) != len(expected) or set(specs) != expected:
        raise ValueError("Formulation-pilot execution matrix is incomplete")
    return tuple(specs)


def _select_formulation(
    records: Sequence[Mapping[str, object]],
    formulations: Sequence[str],
    repetitions: int,
) -> dict[str, object]:
    summaries = []
    order = {name: index for index, name in enumerate(formulations)}
    for formulation in formulations:
        runs = [
            record for record in records if str(record["formulation"]) == formulation
        ]
        elapsed = [float(record["total_elapsed_seconds"]) for record in runs]
        eligible = len(runs) == repetitions and all(
            bool(record["eligible"]) for record in runs
        )
        summaries.append(
            {
                "formulation": formulation,
                "completed_repetitions": len(runs),
                "eligible_repetitions": sum(
                    bool(record["eligible"]) for record in runs
                ),
                "eligible": eligible,
                "median_total_elapsed_seconds": (
                    statistics.median(elapsed) if elapsed else None
                ),
                "maximum_total_elapsed_seconds": max(elapsed) if elapsed else None,
            }
        )
    eligible_summaries = [item for item in summaries if item["eligible"]]
    eligible_summaries.sort(
        key=lambda item: (
            item["median_total_elapsed_seconds"],
            item["maximum_total_elapsed_seconds"],
            order[str(item["formulation"])],
        )
    )
    selected = str(eligible_summaries[0]["formulation"]) if eligible_summaries else None
    return {
        "status": (
            "selected_by_preregistered_nonobjective_runtime_rule"
            if selected is not None
            else "inconclusive_no_formulation_selected"
        ),
        "selected_formulation": selected,
        "objective_value_used": False,
        "formulations": summaries,
    }


def run_pilot(
    config_path: Path = _CONFIG_PATH, *, output_directory: Path | None = None
) -> dict[str, Any]:
    config = _read_config(config_path)
    output_root = _output_root(config, output_directory)
    preparation, preparation_manifest = _require_preparation(
        config_path, config, output_root
    )
    target = output_root / config["output"]["comparison_subdirectory"]
    if target.exists():
        return _load_json(target, "summary.json")
    log_root = Path(config["output"]["log_directory"])
    if log_root.exists() and any(log_root.iterdir()):
        raise RuntimeError("Formulation-pilot live log directory is not empty")
    log_root.mkdir(parents=True, exist_ok=True)
    problem = _build_problem(config)
    specs = _execution_specs(config)

    def writer(staging: Path) -> None:
        records = []
        for formulation, repetition in specs:
            run_id = f"{formulation}_r{repetition}"
            run_log_root = log_root / run_id
            progress = JsonlProgressWriter(
                run_log_root / "progress.jsonl",
                run_id=run_id,
                preregistration_id=str(config["pilot"]["id"]),
                input_contract_sha256=str(preparation["input_contract_sha256"]),
            )
            progress.emit(
                "run_started",
                formulation=formulation,
                repetition=repetition,
                preparation_manifest_sha256=preparation_manifest,
            )
            if formulation == "full_state_monolith":
                record = _run_monolith(
                    problem,
                    config,
                    repetition=repetition,
                    run_log_root=run_log_root,
                    progress=progress,
                )
            else:
                record = _run_constraint_generation(
                    problem,
                    config,
                    repetition=repetition,
                    run_log_root=run_log_root,
                    progress=progress,
                )
            progress.emit("run_completed", **record)
            records.append(record)
            gc.collect()
        selection = _select_formulation(
            records,
            tuple(config["formulations"]["included"]),
            int(config["solver"]["repetitions"]),
        )
        summary = {
            "schema": "rts_gmlc_zero_dc_ac_aware_formulation_pilot_result_v1",
            "pilot_id": config["pilot"]["id"],
            "evidence_scope": config["pilot"]["evidence_scope"],
            "preparation_manifest_sha256": preparation_manifest,
            "input_contract_sha256": preparation["input_contract_sha256"],
            "horizon_hours": len(problem.points),
            "state_count": len(problem.all_state_ids),
            "state_ids": list(problem.all_state_ids),
            "relative_cost_budget_delta": config["pilot"]["relative_cost_budget_delta"],
            "parent_full_cost_usd": problem.parent_full_cost_usd,
            "parent_horizon_cost_usd": problem.parent_horizon_cost_usd,
            "cost_budget_usd": problem.cost_budget_usd,
            "threads": config["solver"]["threads"],
            "target_mip_relative_gap": config["solver"]["target_mip_relative_gap"],
            "run_count": len(records),
            "all_runs_attempted": len(records) == len(specs),
            "selection": selection,
            "objective_value_used_for_selection": False,
            "formal_candidate_result": False,
            "joint_ac_solver_call_count": 0,
            "live_log_directory": log_root.as_posix(),
            "software_versions": preparation["software_versions"],
        }
        _write_json(staging / "runs.json", records)
        _write_json(staging / "summary.json", summary)
        shutil.copytree(log_root, staging / "live_logs_snapshot")

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=_CONFIG_PATH)
    parser.add_argument("--stage", choices=("prepare", "run"), required=True)
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    result = (
        prepare(args.config, output_directory=args.output_directory)
        if args.stage == "prepare"
        else run_pilot(args.config, output_directory=args.output_directory)
    )
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
