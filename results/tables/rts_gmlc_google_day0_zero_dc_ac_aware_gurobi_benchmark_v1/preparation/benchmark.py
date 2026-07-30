"""Reproducible Gurobi pilot for the AC-aware candidate solve.

Mirrors the frozen HiGHS pilot (same 6-hour horizon, same 24 selected states,
same 1/4/8-thread x2 matrix, same mechanical selection that never reads the
objective value).  Only the solver identity and its option names differ.
"""

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
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from pyomo.environ import Constraint, ConstraintList, Objective, SolverFactory, Var
from pyomo.environ import maximize, value
from pyomo.opt import TerminationCondition

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment as parent
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.grid.rts_gmlc_scuc import (
    _build_context as _build_scuc_context,
    _build_model,
    _constraint_violation,
    _integrality_violation,
    _validate_inputs,
)


_CONFIG_PATH = Path("configs/rts_gmlc_zero_dc_ac_aware_gurobi_benchmark.yaml")
_SCRIPT_PATH = Path(__file__).resolve()
_TOP_LEVEL_KEYS = {
    "benchmark",
    "parent",
    "formulation",
    "budget",
    "solver_matrix",
    "expected_model_size",
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
_OPTIMAL_TERMINATIONS = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}


@dataclass(frozen=True)
class _PilotModel:
    model: Any
    scuc_context: Any
    base_variables: int
    base_constraints: int
    benchmark_variables: int
    benchmark_constraints: int
    state_ids: tuple[str, ...]


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _TOP_LEVEL_KEYS:
        raise ValueError("Solver benchmark config schema drifted")
    benchmark = config["benchmark"]
    if (
        benchmark.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_gurobi_benchmark_v1"
        or benchmark.get("schema")
        != "rts_gmlc_zero_dc_ac_aware_gurobi_benchmark_v1"
        or int(benchmark.get("horizon_start_index", -1)) != 0
        or int(benchmark.get("horizon_hours", -1)) != 6
        or int(benchmark.get("selected_state_count_per_hour", -1)) != 24
        or benchmark.get("candidate_or_joint_ac_outcomes_used") is not False
        or benchmark.get("status")
        != "repository_local_solver_pilot_after_gurobi_academic_license_capacity_gate"
        or benchmark.get("evidence_scope")
        != "nonformal_solver_configuration_pilot_no_candidate_or_ac_claim"
    ):
        raise ValueError("Solver benchmark scope drifted")
    formulation = config["formulation"]
    if (
        formulation.get("included") != ["full_state_monolith"]
        or formulation.get("exact_selected_state_constraint_generation_included")
        is not False
        or formulation.get("stages_constructed")
        != ["proxy_maximization", "cost_normalization"]
        or formulation.get("stages_executed") != ["proxy_maximization"]
        or formulation.get("cost_normalization_executed") is not False
    ):
        raise ValueError("Solver benchmark formulation drifted")
    budget = config["budget"]
    if (
        float(budget.get("relative_delta", -1.0)) != 0.0075
        or budget.get("belongs_to_formal_v2_grid") is not False
        or float(budget.get("full_horizon_reconstruction_absolute_tolerance_usd"))
        != 1.0e-6
        or float(budget.get("cost_cap_absolute_tolerance_usd")) != 1.0e-4
        or float(budget.get("proxy_floor_absolute_tolerance")) != 1.0e-7
    ):
        raise ValueError("Solver benchmark budget drifted")
    solver = config["solver_matrix"]
    if (
        solver.get("name") != "gurobi"
        or solver.get("threads") != [1, 4, 8]
        or int(solver.get("repetitions", -1)) != 2
        or solver.get("execution_order")
        != ["t1_r1", "t4_r1", "t8_r1", "t8_r2", "t4_r2", "t1_r2"]
        or float(solver.get("time_limit_seconds_per_stage")) != 120.0
        or float(solver.get("target_mip_relative_gap")) != 1.0e-4
        or float(solver.get("mip_absolute_gap")) != 0.0
        or float(solver.get("feasibility_tolerance")) != 1.0e-6
        or not isinstance(solver.get("license_capacity_gate"), dict)
        or int(solver.get("random_seed", -1)) != 0
        or int(solver.get("mip_report_level", -1)) != 2
        or float(solver.get("mip_min_logging_interval_seconds")) != 5.0
    ):
        raise ValueError("Solver benchmark matrix drifted")
    expected = config["expected_model_size"]
    if expected != {
        "base_variables": 53922,
        "base_constraints": 87508,
        "cost_cap_constraints_added": 1,
        "proxy_variables_added": 1,
        "reactive_proxy_constraints_added": 36,
        "proxy_stage_total_variables": 53923,
        "proxy_stage_total_constraints": 87545,
    }:
        raise ValueError("Solver benchmark model size contract drifted")
    selection = config["selection"]
    if (
        selection.get("eligibility_rule")
        != "both_repetitions_attain_target_gap_and_pass_solution_audit"
        or selection.get("ranking_rule")
        != [
            "minimum_median_solver_wall_seconds",
            "minimum_maximum_solver_wall_seconds",
            "minimum_thread_count",
        ]
        or selection.get("no_eligible_configuration_rule")
        != "inconclusive_no_configuration_selected"
        or selection.get("objective_value_used") is not False
    ):
        raise ValueError("Solver benchmark selection rule drifted")
    parent_config = config["parent"]
    if (
        parent_config.get("v2_root")
        != "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2"
        or parent_config.get("v2_config_path")
        != "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml"
        or parent_config.get("preregistration_manifest_sha256")
        != "ee71eca750a4c6e8819c8d3b3c7de803c0736efa3327b5f89aec0d91edeff708"
        or parent_config.get("operational_termination_manifest_sha256")
        != "e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b"
        or parent_config.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2"
        or parent_config.get("input_contract_sha256")
        != "7cb101bfbdc26994354fd77d6525bfc2de5deaf97496cc970cea805ead9857d0"
        or parent_config.get("termination_status")
        != "terminated_before_candidate_frontier_publication_and_before_any_joint_ac_solver_call"
        or parent_config.get("zero_dispatch_root")
        != "results/tables/rts_gmlc_google_day0_zero_dc_normal_ac_control_v1/dc_dispatch"
        or parent_config.get("zero_dispatch_manifest_sha256")
        != "c7c5cb7f418382472f2adf949e62ce4e1abb399dfe906903bacc24037d40ca4d"
        or float(parent_config.get("expected_full_horizon_cost_usd"))
        != 1108454.611081534
    ):
        raise ValueError("Solver benchmark parent contract drifted")
    if config["output"] != {
        "directory": "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_gurobi_benchmark_v1",
        "log_directory": "results/logs/rts_gmlc_zero_dc_ac_aware_gurobi_benchmark_v1",
        "preparation_subdirectory": "preparation",
        "benchmark_subdirectory": "benchmark",
    }:
        raise ValueError("Solver benchmark output contract drifted")
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


def _verify_parent(config: Mapping[str, Any]) -> dict[str, Any]:
    frozen = config["parent"]
    root = Path(frozen["v2_root"])
    preregistration = root / "preregistration"
    termination_root = root / "operational_termination"
    _verify_manifest_hash(
        preregistration,
        str(frozen["preregistration_manifest_sha256"]),
        "v2 preregistration",
    )
    _verify_manifest_hash(
        termination_root,
        str(frozen["operational_termination_manifest_sha256"]),
        "v2 operational termination",
    )
    registration = _load_json(preregistration, "registration.json")
    termination = _load_json(termination_root, "termination.json")
    if (
        registration.get("preregistration_id") != frozen["preregistration_id"]
        or registration.get("input_contract_sha256")
        != frozen["input_contract_sha256"]
        or registration.get("candidate_frontier_outcomes_observed") is not False
        or registration.get("joint_ac_outcomes_observed") is not False
    ):
        raise RuntimeError("v2 preregistration contract drifted")
    if (
        termination.get("status") != frozen["termination_status"]
        or termination.get("input_contract_sha256")
        != frozen["input_contract_sha256"]
        or termination.get("preregistration_manifest_sha256")
        != frozen["preregistration_manifest_sha256"]
        or termination.get("candidate_frontier_artifact_published") is not False
        or termination.get("partial_candidate_solution_persisted") is not False
        or termination.get("joint_ac_solver_call_count") != 0
        or termination.get("joint_ac_outcomes_observed") is not False
        or termination.get("termination_is_infeasibility_evidence") is not False
        or termination.get("successor_must_use_new_preregistration_id") is not True
    ):
        raise RuntimeError("v2 operational termination contract drifted")
    if (root / "candidate_frontier").exists() or (root / "joint_ac").exists():
        raise RuntimeError("Terminated v2 unexpectedly gained result artifacts")
    source_hashes = termination.get("source_snapshot_hashes")
    if not isinstance(source_hashes, dict) or not source_hashes:
        raise RuntimeError("v2 termination source hashes are missing")
    for relative, expected in source_hashes.items():
        current = Path(relative)
        snapshot = termination_root / "source_snapshot" / relative
        if (
            not current.is_file()
            or _sha256(current) != expected
            or not snapshot.is_file()
            or _sha256(snapshot) != expected
        ):
            raise RuntimeError(f"v2 terminated source drifted: {relative}")
    zero_root = Path(frozen["zero_dispatch_root"])
    _verify_manifest_hash(
        zero_root,
        str(frozen["zero_dispatch_manifest_sha256"]),
        "parent zero dispatch",
    )
    return {
        "preregistration_manifest_sha256": _sha256(
            preregistration / "SHA256SUMS"
        ),
        "operational_termination_manifest_sha256": _sha256(
            termination_root / "SHA256SUMS"
        ),
        "zero_dispatch_manifest_sha256": _sha256(zero_root / "SHA256SUMS"),
        "registration_sha256": _sha256(preregistration / "registration.json"),
        "termination_sha256": _sha256(termination_root / "termination.json"),
        "source_snapshot_hashes": dict(source_hashes),
    }


def _software_versions() -> dict[str, str]:
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for package in ("gurobipy", "numpy", "pyomo", "pyyaml"):
        versions[package] = importlib.metadata.version(package)
    return versions


def _preparation_payload(
    config_path: Path, config: Mapping[str, Any]
) -> dict[str, Any]:
    return {
        "schema": "rts_gmlc_zero_dc_ac_aware_solver_benchmark_preparation_v1",
        "benchmark_id": config["benchmark"]["id"],
        "status": "prepared_not_run",
        "config_sha256": _sha256(config_path),
        "script_sha256": _sha256(_SCRIPT_PATH),
        "parent": _verify_parent(config),
        "benchmark_contract": _stable_json(
            {key: config[key] for key in _TOP_LEVEL_KEYS if key != "output"}
        ),
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
            raise RuntimeError("Published solver benchmark preparation drifted")
        return observed

    def writer(staging: Path) -> None:
        _write_json(staging / "registration.json", payload)
        shutil.copyfile(config_path, staging / "config.yaml")
        shutil.copyfile(_SCRIPT_PATH, staging / "benchmark.py")
        parent_root = Path(config["parent"]["v2_root"])
        for subdirectory, name in (
            ("preregistration", "registration.json"),
            ("preregistration", "SHA256SUMS"),
            ("operational_termination", "termination.json"),
            ("operational_termination", "SHA256SUMS"),
        ):
            snapshot_name = "manifest.txt" if name == "SHA256SUMS" else name
            destination = staging / "parent" / subdirectory / snapshot_name
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(parent_root / subdirectory / name, destination)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preparation(
    config_path: Path,
    config: Mapping[str, Any],
    output_root: Path,
) -> tuple[dict[str, Any], str]:
    root = output_root / config["output"]["preparation_subdirectory"]
    if not root.exists():
        raise RuntimeError("Run requires a published solver benchmark preparation")
    observed = _load_json(root, "registration.json")
    expected = _preparation_payload(config_path, config)
    if observed != expected:
        raise RuntimeError("Solver benchmark preparation no longer matches inputs")
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
        raise RuntimeError(f"Parent generation is outside the cost curve for {generator.uid}")
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
        row_commitment = commitment[timestamp]
        row_generation = generation[timestamp]
        total = 0.0
        for generator in thermal:
            uid = generator.uid
            online = bool(row_commitment[uid])
            total += _piecewise_cost(generator, row_generation[uid], online)
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


def _component_count(model: Any, component: Any) -> int:
    return sum(1 for _ in model.component_data_objects(component, active=True))


def _build_proxy_model(
    context: Any, config: Mapping[str, Any], cost_budget_usd: float
) -> _PilotModel:
    benchmark = config["benchmark"]
    request = _truncate_request(
        context.request,
        int(benchmark["horizon_start_index"]),
        int(benchmark["horizon_hours"]),
    )
    tolerance = float(config["solver_matrix"]["feasibility_tolerance"])
    points = _validate_inputs(context.zero.scan.data, request, tolerance)
    states = tuple(context.selection.states)
    if len(states) != int(benchmark["selected_state_count_per_hour"]):
        raise RuntimeError("Pilot selected-state count drifted")
    scuc_context = _build_scuc_context(
        context.zero.scan.data, request, points, states
    )
    model = _build_model(scuc_context, fixed_initial=context.initial_state)
    base_variables = _component_count(model, Var)
    base_constraints = _component_count(model, Constraint)
    expected = config["expected_model_size"]
    if (
        base_variables != int(expected["base_variables"])
        or base_constraints != int(expected["base_constraints"])
    ):
        raise RuntimeError(
            f"Pilot base model size drifted: {base_variables} vars, "
            f"{base_constraints} constraints"
        )
    model.cost_cap = Constraint(
        expr=model.operating_cost
        <= cost_budget_usd + float(config["budget"]["cost_cap_absolute_tolerance_usd"])
    )
    fixed, variable, denominators = parent._proxy_components(context, points)
    model.reactive_proxy = Var(bounds=(0.0, 1.0))
    model.reactive_proxy_constraints = ConstraintList()
    for time_index in range(len(points)):
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
    model.objective.deactivate()
    model.reactive_proxy_objective = Objective(
        expr=model.reactive_proxy, sense=maximize
    )
    benchmark_variables = _component_count(model, Var)
    benchmark_constraints = _component_count(model, Constraint)
    if (
        benchmark_variables - base_variables
        != int(expected["proxy_variables_added"])
        or benchmark_constraints - base_constraints
        != int(expected["cost_cap_constraints_added"])
        + int(expected["reactive_proxy_constraints_added"])
        or benchmark_variables != int(expected["proxy_stage_total_variables"])
        or benchmark_constraints != int(expected["proxy_stage_total_constraints"])
    ):
        raise RuntimeError("Pilot proxy model additions drifted")
    return _PilotModel(
        model=model,
        scuc_context=scuc_context,
        base_variables=base_variables,
        base_constraints=base_constraints,
        benchmark_variables=benchmark_variables,
        benchmark_constraints=benchmark_constraints,
        state_ids=tuple(state.state_id for state in states),
    )


def _activate_cost_normalization_stage(
    model: Any, proxy_target: float, floor_tolerance: float
) -> None:
    model.reactive_proxy_floor = Constraint(
        expr=model.reactive_proxy >= float(proxy_target) - float(floor_tolerance)
    )
    model.reactive_proxy_objective.deactivate()
    model.objective.activate()


def _append_jsonl(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(_stable_json(payload), allow_nan=False, sort_keys=True) + "\n"
    with path.open("a", encoding="utf-8", newline="\n") as output:
        output.write(line)
        output.flush()
        os.fsync(output.fileno())


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _optional_float(item: object) -> float | None:
    try:
        parsed = float(item)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _solve_proxy_once(
    pilot: _PilotModel,
    config: Mapping[str, Any],
    *,
    threads: int,
    repetition: int,
    log_path: Path,
) -> dict[str, Any]:
    solver_config = config["solver_matrix"]
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if log_path.exists():
        raise FileExistsError(f"Solver benchmark log already exists: {log_path}")
    solver = SolverFactory("gurobi")
    if not solver.available(exception_flag=False):
        raise RuntimeError("Gurobi is unavailable for the solver pilot")
    options = {
        "Threads": threads,
        "Seed": int(solver_config["random_seed"]),
        "TimeLimit": float(solver_config["time_limit_seconds_per_stage"]),
        "MIPGap": float(solver_config["target_mip_relative_gap"]),
        "MIPGapAbs": float(solver_config["mip_absolute_gap"]),
        "FeasibilityTol": float(solver_config["feasibility_tolerance"]),
        "OptimalityTol": float(solver_config["feasibility_tolerance"]),
        "IntFeasTol": float(solver_config["feasibility_tolerance"]),
        "LogToConsole": 0,
        "LogFile": str(log_path.resolve()),
        "DisplayInterval": int(
            max(1.0, float(solver_config["mip_min_logging_interval_seconds"]))
        ),
    }
    started = time.perf_counter()
    try:
        results = solver.solve(
            pilot.model, load_solutions=False, tee=False, options=options
        )
        wall_seconds = time.perf_counter() - started
    except Exception as error:
        return {
            "threads": threads,
            "repetition": repetition,
            "solver_wall_seconds": time.perf_counter() - started,
            "termination_condition": None,
            "solver_status": None,
            "lower_bound": None,
            "upper_bound": None,
            "absolute_gap": None,
            "relative_gap": None,
            "proxy_fraction": None,
            "maximum_constraint_violation": None,
            "maximum_integrality_violation": None,
            "solution_audited": False,
            "target_gap_attained": False,
            "accepted": False,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "native_log": log_path.as_posix(),
        }
    termination = results.solver.termination_condition
    lower = _optional_float(results.problem.lower_bound)
    upper = _optional_float(results.problem.upper_bound)
    absolute_gap = (
        abs(upper - lower) if lower is not None and upper is not None else None
    )
    relative_gap = (
        absolute_gap / max(abs(lower), abs(upper), 1.0)
        if absolute_gap is not None
        else None
    )
    loaded = False
    try:
        pilot.model.solutions.load_from(results)
        loaded = True
    except Exception:
        loaded = False
    proxy = _optional_float(value(pilot.model.reactive_proxy, exception=False))
    constraint_violation = (
        float(_constraint_violation(pilot.model)) if loaded else None
    )
    integrality_violation = (
        float(_integrality_violation(pilot.model)) if loaded else None
    )
    tolerance = float(solver_config["feasibility_tolerance"])
    solution_audited = bool(
        loaded
        and proxy is not None
        and constraint_violation is not None
        and constraint_violation <= tolerance
        and integrality_violation is not None
        and integrality_violation <= tolerance
    )
    target_gap_attained = bool(
        relative_gap is not None
        and relative_gap <= float(solver_config["target_mip_relative_gap"])
    )
    return {
        "threads": threads,
        "repetition": repetition,
        "solver_wall_seconds": wall_seconds,
        "termination_condition": str(termination),
        "solver_status": str(results.solver.status),
        "lower_bound": lower,
        "upper_bound": upper,
        "absolute_gap": absolute_gap,
        "relative_gap": relative_gap,
        "proxy_fraction": proxy,
        "maximum_constraint_violation": constraint_violation,
        "maximum_integrality_violation": integrality_violation,
        "solution_audited": solution_audited,
        "target_gap_attained": target_gap_attained,
        "accepted": bool(
            termination in _OPTIMAL_TERMINATIONS
            and solution_audited
            and target_gap_attained
        ),
        "error_type": None,
        "error_message": None,
        "native_log": log_path.as_posix(),
    }


def _execution_specs(config: Mapping[str, Any]) -> tuple[tuple[int, int], ...]:
    specs = []
    for item in config["solver_matrix"]["execution_order"]:
        match = re.fullmatch(r"t(\d+)_r(\d+)", str(item))
        if match is None:
            raise ValueError("Invalid solver benchmark execution order")
        specs.append((int(match.group(1)), int(match.group(2))))
    expected = {
        (threads, repetition)
        for threads in config["solver_matrix"]["threads"]
        for repetition in range(1, int(config["solver_matrix"]["repetitions"]) + 1)
    }
    if len(specs) != len(expected) or set(specs) != expected:
        raise ValueError("Solver benchmark execution matrix is incomplete")
    return tuple(specs)


def _select_configuration(
    records: Sequence[Mapping[str, Any]],
    threads_values: Sequence[int],
    repetitions: int,
) -> dict[str, Any]:
    configurations = []
    for threads in threads_values:
        runs = [record for record in records if int(record["threads"]) == threads]
        accepted = len(runs) == repetitions and all(bool(run["accepted"]) for run in runs)
        wall = [float(run["solver_wall_seconds"]) for run in runs]
        configurations.append(
            {
                "threads": threads,
                "completed_repetitions": len(runs),
                "accepted_repetitions": sum(bool(run["accepted"]) for run in runs),
                "eligible": accepted,
                "median_solver_wall_seconds": statistics.median(wall) if wall else None,
                "maximum_solver_wall_seconds": max(wall) if wall else None,
            }
        )
    eligible = [item for item in configurations if item["eligible"]]
    eligible.sort(
        key=lambda item: (
            item["median_solver_wall_seconds"],
            item["maximum_solver_wall_seconds"],
            item["threads"],
        )
    )
    selected = eligible[0]["threads"] if eligible else None
    return {
        "status": (
            "selected_by_preregistered_nonobjective_rule"
            if selected is not None
            else "inconclusive_no_configuration_selected"
        ),
        "selected_threads": selected,
        "objective_value_used": False,
        "configurations": configurations,
    }


def run_benchmark(
    config_path: Path = _CONFIG_PATH, *, output_directory: Path | None = None
) -> dict[str, Any]:
    config = _read_config(config_path)
    output_root = _output_root(config, output_directory)
    preparation, preparation_manifest = _require_preparation(
        config_path, config, output_root
    )
    target = output_root / config["output"]["benchmark_subdirectory"]
    if target.exists():
        return _load_json(target, "summary.json")
    log_root = Path(config["output"]["log_directory"])
    if log_root.exists() and any(log_root.iterdir()):
        raise RuntimeError("Solver benchmark live log directory is not empty")
    log_root.mkdir(parents=True, exist_ok=True)
    context = parent._build_context(Path(config["parent"]["v2_config_path"]))
    if context.input_contract_sha256 != config["parent"]["input_contract_sha256"]:
        raise RuntimeError("Parent v2 context drifted before pilot execution")
    _hourly, generation, commitment, _flows = parent._load_zero_dispatch(
        context.zero, parent._ZERO_OUTPUT_ROOT
    )
    timestamp_keys = tuple(timestamp.isoformat() for timestamp in context.request.timestamps)
    hourly_costs = _reconstruct_hourly_costs(
        tuple(context.zero.scan.data.generators),
        timestamp_keys,
        generation,
        commitment,
        context.initial_state.commitment,
    )
    full_cost = sum(hourly_costs)
    expected_full_cost = float(config["parent"]["expected_full_horizon_cost_usd"])
    if not math.isclose(
        full_cost,
        expected_full_cost,
        rel_tol=0.0,
        abs_tol=float(
            config["budget"]["full_horizon_reconstruction_absolute_tolerance_usd"]
        ),
    ):
        raise RuntimeError("Parent 24h SCUC cost reconstruction drifted")
    hours = int(config["benchmark"]["horizon_hours"])
    first_cost = sum(hourly_costs[:hours])
    cost_budget = first_cost * (1.0 + float(config["budget"]["relative_delta"]))
    specs = _execution_specs(config)

    def writer(staging: Path) -> None:
        progress_path = log_root / "progress.jsonl"
        _append_jsonl(
            progress_path,
            {
                "event": "benchmark_started",
                "timestamp_utc": _utc_now(),
                "execution_order": config["solver_matrix"]["execution_order"],
            },
        )
        records = []
        model_metadata = None
        for threads, repetition in specs:
            build_started = time.perf_counter()
            pilot = _build_proxy_model(context, config, cost_budget)
            build_seconds = time.perf_counter() - build_started
            if model_metadata is None:
                model_metadata = {
                    "base_variables": pilot.base_variables,
                    "base_constraints": pilot.base_constraints,
                    "benchmark_variables": pilot.benchmark_variables,
                    "benchmark_constraints": pilot.benchmark_constraints,
                    "state_ids": list(pilot.state_ids),
                }
            relative_log = Path(f"gurobi_t{threads}_r{repetition}.log")
            _append_jsonl(
                progress_path,
                {
                    "event": "run_started",
                    "timestamp_utc": _utc_now(),
                    "threads": threads,
                    "repetition": repetition,
                    "native_log": relative_log.as_posix(),
                },
            )
            record = _solve_proxy_once(
                pilot,
                config,
                threads=threads,
                repetition=repetition,
                log_path=log_root / relative_log,
            )
            record["model_build_seconds"] = build_seconds
            record["native_log"] = relative_log.as_posix()
            records.append(record)
            _append_jsonl(
                progress_path,
                {
                    "event": "run_completed",
                    "timestamp_utc": _utc_now(),
                    **record,
                },
            )
            del pilot
            gc.collect()
        selection = _select_configuration(
            records,
            tuple(config["solver_matrix"]["threads"]),
            int(config["solver_matrix"]["repetitions"]),
        )
        _append_jsonl(
            progress_path,
            {
                "event": "selection_completed",
                "timestamp_utc": _utc_now(),
                **selection,
            },
        )
        summary = {
            "schema": "rts_gmlc_zero_dc_ac_aware_solver_benchmark_result_v1",
            "benchmark_id": config["benchmark"]["id"],
            "evidence_scope": config["benchmark"]["evidence_scope"],
            "preparation_manifest_sha256": preparation_manifest,
            "input_contract_sha256": config["parent"]["input_contract_sha256"],
            "horizon_hours": hours,
            "selected_state_count_per_hour": len(model_metadata["state_ids"]),
            "formulations_executed": config["formulation"]["included"],
            "stages_executed": config["formulation"]["stages_executed"],
            "cost_normalization_executed": False,
            "parent_full_horizon_reconstructed_cost_usd": full_cost,
            "parent_first_6h_reconstructed_cost_usd": first_cost,
            "relative_cost_budget_delta": config["budget"]["relative_delta"],
            "pilot_cost_budget_usd": cost_budget,
            "model": model_metadata,
            "run_count": len(records),
            "all_matrix_entries_attempted": len(records) == len(specs),
            "selection": selection,
            "objective_value_used_for_selection": False,
            "live_log_directory": log_root.as_posix(),
            "candidate_frontier_published": False,
            "joint_ac_solver_call_count": 0,
            "formal_candidate_result": False,
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
    if args.stage == "prepare":
        result = prepare(args.config, output_directory=args.output_directory)
    else:
        result = run_benchmark(args.config, output_directory=args.output_directory)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
