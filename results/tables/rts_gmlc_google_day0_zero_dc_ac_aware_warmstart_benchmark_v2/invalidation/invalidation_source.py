"""Benchmark a fully audited parent dispatch as a HiGHS MIP start."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import shutil
import statistics
import time
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import MethodType
from typing import Any

import numpy as np
import yaml
from highspy import Highs, HighsSolution
from pyomo.environ import SolverFactory, Var, value

from experiments import pilot_rts_gmlc_zero_dc_ac_aware_formulations as formulation
from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v3 as v3
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.scenarios.common_input_signature import common_input_signature_sha256
from src.solvers.mip_progress import (
    JsonlProgressWriter,
    ProgressHeartbeat,
    highs_runtime_options,
)

_CONFIG_PATH = Path("configs/rts_gmlc_zero_dc_ac_aware_warmstart_benchmark.yaml")
_SCRIPT_PATH = Path(__file__).resolve()
_TOP_LEVEL_KEYS = {
    "preregistration",
    "provenance",
    "benchmark",
    "solver",
    "warm_start",
    "result_contract",
    "selection",
    "output",
}
_METHODS = ("highs_cold_start", "appsi_highs_full_mip_start")
_ACCEPTED_TERMINATIONS = {
    "optimal",
    "globallyOptimal",
    "maxTimeLimit",
    "feasible",
}
_V2_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v2"
)
_V2_ATTEMPT_ROOT = Path(
    "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v2/"
    "warmstart_benchmark_v2_registered_run1"
)


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _TOP_LEVEL_KEYS:
        raise ValueError("Warm-start benchmark config schema drifted")
    preregistration = config["preregistration"]
    benchmark = config["benchmark"]
    solver = config["solver"]
    warm = config["warm_start"]
    selection = config["selection"]
    if (
        preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v2"
        or preregistration.get("formal_candidate_result") is not False
        or preregistration.get("joint_ac_solver_call_count") != 0
        or preregistration.get("v3_runtime_outcome_used_to_motivate_pilot") is not True
        or preregistration.get("v3_objective_value_used_for_method_selection")
        is not False
        or preregistration.get(
            "v3_candidate_frontier_outcomes_used_for_method_selection"
        )
        is not False
        or tuple(benchmark.get("methods", ())) != _METHODS
        or benchmark.get("attempt_id") != "warmstart_benchmark_v2_registered_run1"
        or int(benchmark.get("repetitions", -1)) != 2
        or tuple(benchmark.get("execution_order", ()))
        != (
            "highs_cold_start_r1",
            "appsi_highs_full_mip_start_r1",
            "appsi_highs_full_mip_start_r2",
            "highs_cold_start_r2",
        )
        or benchmark.get("rebuild_model_for_every_run") is not True
        or benchmark.get("cross_run_solution_reuse_allowed") is not False
        or solver.get("cold_interface") != "highs"
        or solver.get("warm_interface") != "appsi_highs"
        or solver.get("warmstart_argument") is not True
        or int(solver.get("threads", -1)) != 4
        or float(solver.get("target_mip_relative_gap", -1.0)) != 1.0e-4
        or warm.get("submission_scope") != "every_solver_column"
        or warm.get("missing_values_allowed") is not False
        or warm.get("zero_fill_missing_values_allowed") is not False
        or warm.get("preaudit_required_before_submission") is not True
        or selection.get("objective_value_used") is not False
        or tuple(selection.get("ranking_rule", ()))
        != (
            "minimum_median_time_to_first_finite_incumbent_seconds",
            "minimum_median_solver_wall_seconds",
            "minimum_maximum_solver_wall_seconds",
            "method_order",
        )
    ):
        raise ValueError("Warm-start benchmark frozen contract drifted")
    return config


def _verify_manifest_hash(root: Path, expected: str, label: str) -> None:
    _verify_output_manifest(root)
    if _sha256(root / "SHA256SUMS") != expected:
        raise RuntimeError(f"Warm-start benchmark {label} manifest drifted")


def _verify_provenance(config: Mapping[str, Any]) -> dict[str, object]:
    provenance = config["provenance"]
    superseded_root = Path(provenance["superseded_v1_preparation_root"])
    _verify_manifest_hash(
        superseded_root,
        str(provenance["superseded_v1_preparation_manifest_sha256"]),
        "superseded v1 preparation",
    )
    superseded = json.loads(
        (superseded_root / "registration.json").read_text(encoding="utf-8")
    )
    if (
        provenance.get("superseded_v1_competitive_solve_executed") is not False
        or superseded.get("competitive_solve_executed") is not False
        or (superseded_root.parent / "benchmark").exists()
    ):
        raise RuntimeError("Superseded warm-start v1 preparation gained results")
    for path_key, hash_key in (
        ("v3_config_path", "v3_config_sha256"),
        ("v3_runner_path", "v3_runner_sha256"),
        ("formulation_module_path", "formulation_module_sha256"),
        ("scuc_core_path", "scuc_core_sha256"),
    ):
        path = Path(provenance[path_key])
        if not path.is_file() or _sha256(path) != provenance[hash_key]:
            raise RuntimeError(f"Warm-start benchmark {path_key} drifted")
    v3_preregistration = Path(provenance["v3_root"]) / "preregistration"
    _verify_manifest_hash(
        v3_preregistration,
        str(provenance["v3_preregistration_manifest_sha256"]),
        "v3 preregistration",
    )
    registration = json.loads(
        (v3_preregistration / "registration.json").read_text(encoding="utf-8")
    )
    if (
        registration.get("input_contract_sha256")
        != provenance["v3_input_contract_sha256"]
        or registration.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3"
    ):
        raise RuntimeError("Warm-start benchmark v3 registration drifted")
    zero_root = Path(provenance["parent_zero_dispatch_root"])
    _verify_manifest_hash(
        zero_root,
        str(provenance["parent_zero_dispatch_manifest_sha256"]),
        "parent zero dispatch",
    )
    return {
        "superseded_v1_preparation_manifest_sha256": provenance[
            "superseded_v1_preparation_manifest_sha256"
        ],
        "superseded_v1_competitive_solve_executed": False,
        "v3_preregistration_manifest_sha256": provenance[
            "v3_preregistration_manifest_sha256"
        ],
        "v3_input_contract_sha256": registration["input_contract_sha256"],
        "parent_zero_dispatch_manifest_sha256": provenance[
            "parent_zero_dispatch_manifest_sha256"
        ],
    }


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _parse_bool(candidate: str) -> bool:
    normalized = candidate.strip().lower()
    if normalized not in {"true", "false"}:
        raise RuntimeError(f"Invalid parent boolean {candidate!r}")
    return normalized == "true"


def _model_build_config(config: Mapping[str, Any]) -> dict[str, object]:
    formal = v3._read_config(Path(config["provenance"]["v3_config_path"]))[
        "formal_solver"
    ]
    return {
        "budget": {"cost_cap_absolute_tolerance_usd": 1.0e-4},
        "expected_full_model_size": dict(formal["expected_full_model_size"]),
    }


def _build_handle(config: Mapping[str, Any]) -> tuple[Any, Any]:
    context = v3._build_context(Path(config["provenance"]["v3_config_path"]))
    baseline = float(config["warm_start"]["expected_operating_cost_usd"])
    delta = float(config["benchmark"]["relative_cost_budget_delta"])
    problem = v3._formal_problem(context, cost_budget_usd=baseline * (1.0 + delta))
    if len(problem.initial_active_state_ids) != int(
        config["benchmark"]["expected_active_state_count"]
    ):
        raise RuntimeError("Warm-start benchmark active-state count drifted")
    handle = formulation._build_model_handle(
        problem,
        _model_build_config(config),
        problem.initial_active_state_ids,
        stage="proxy_maximization",
    )
    return problem, handle


def _parent_maps(root: Path) -> dict[str, dict[tuple[str, ...], dict[str, str]]]:
    files_and_keys = {
        "generator": ("generator_dispatch.csv", ("timestamp", "generator_uid")),
        "hourly": ("hourly_dispatch.csv", ("timestamp",)),
        "normal_branch": ("normal_branch_flows.csv", ("timestamp", "branch_uid")),
        "security_generator": (
            "security_generator_dispatch.csv",
            ("timestamp", "state_id", "generator_uid"),
        ),
        "security_branch": (
            "security_branch_flows.csv",
            ("timestamp", "state_id", "branch_uid"),
        ),
    }
    result = {}
    for label, (name, keys) in files_and_keys.items():
        rows = _csv_rows(root / name)
        mapping = {tuple(row[key] for key in keys): row for row in rows}
        if len(mapping) != len(rows):
            raise RuntimeError(f"Duplicate parent rows in {name}")
        result[label] = mapping
    return result


def _state_angles(
    handle: Any,
    state: Any,
    time_index: int,
    flows: Mapping[str, float],
) -> dict[int, float]:
    context = handle.scuc_context
    adjacency: dict[int, list[tuple[int, float]]] = defaultdict(list)
    for uid, branch in context.branch_by_uid.items():
        if state.kind == "branch" and state.element_uid == uid:
            continue
        coefficient = float(context.data.base_mva) / (
            float(branch.reactance_pu) * float(branch.tap_ratio)
        )
        difference = float(flows[uid]) / (coefficient * math.radians(1.0))
        from_bus = int(branch.from_bus)
        to_bus = int(branch.to_bus)
        adjacency[from_bus].append((to_bus, -difference))
        adjacency[to_bus].append((from_bus, difference))
    remaining = {int(bus) for bus in handle.model.BUS}
    angles: dict[int, float] = {}
    first_root = int(context.data.reference_bus)
    while remaining:
        root = first_root if first_root in remaining else min(remaining)
        angles[root] = 0.0
        queue = [root]
        remaining.remove(root)
        while queue:
            bus = queue.pop()
            for neighbor, increment in adjacency[bus]:
                candidate = angles[bus] + increment
                if neighbor not in angles:
                    angles[neighbor] = candidate
                    remaining.remove(neighbor)
                    queue.append(neighbor)
    if set(angles) != {int(bus) for bus in handle.model.BUS}:
        raise RuntimeError(
            f"Angle reconstruction failed for {state.state_id} {time_index}"
        )
    return angles


def _assignment_sha256(model: Any) -> str:
    digest = hashlib.sha256()
    for component in model.component_objects(Var, active=True):
        for variable in component.values():
            candidate = value(variable, exception=False)
            if candidate is None or not math.isfinite(float(candidate)):
                raise RuntimeError(f"Unassigned warm-start variable {variable.name}")
            payload = (
                f"{component.local_name}|{variable.index()!r}|"
                f"{float(candidate).hex()}\n"
            )
            digest.update(payload.encode("utf-8"))
    return digest.hexdigest()


def _assign_parent_start(
    config: Mapping[str, Any], problem: Any, handle: Any
) -> dict[str, object]:
    model = handle.model
    context = handle.scuc_context
    root = Path(config["provenance"]["parent_zero_dispatch_root"])
    maps = _parent_maps(root)
    timestamps = tuple(
        timestamp.isoformat() for timestamp in problem.request.timestamps
    )
    state_by_id = {str(state.state_id): state for state in problem.states}
    normal_generation: list[dict[str, float]] = []
    commitment_rows: list[dict[str, bool]] = []
    generation: dict[tuple[str, int, str], float] = {}
    branch_flow: dict[tuple[str, int, str], float] = {}

    for time_index, timestamp in enumerate(timestamps):
        commitment_row = {}
        generation_row = {}
        for uid in model.THERMAL:
            row = maps["generator"][(timestamp, str(uid))]
            commitment = _parse_bool(row["commitment"])
            model.commitment[time_index, uid].set_value(
                float(commitment), skip_validation=True
            )
            model.startup[time_index, uid].set_value(
                float(_parse_bool(row["startup"])), skip_validation=True
            )
            model.shutdown[time_index, uid].set_value(
                float(_parse_bool(row["shutdown"])), skip_validation=True
            )
            commitment_row[str(uid)] = commitment
        commitment_rows.append(commitment_row)
        for uid in model.GEN:
            row = maps["generator"][(timestamp, str(uid))]
            candidate = float(row["generation_mw"])
            generation[("normal", time_index, str(uid))] = candidate
            generation_row[str(uid)] = candidate
        normal_generation.append(generation_row)
        for uid in model.RESERVE_GEN:
            row = maps["generator"][(timestamp, str(uid))]
            model.reserve_up[time_index, uid].set_value(
                float(row["spin_up_mw"]), skip_validation=True
            )
        for uid in model.BRANCH:
            row = maps["normal_branch"][(timestamp, str(uid))]
            branch_flow[("normal", time_index, str(uid))] = float(row["flow_mw"])

        for state_id in handle.state_ids:
            if state_id == "normal":
                continue
            for uid in model.GEN:
                row = maps["security_generator"][(timestamp, state_id, str(uid))]
                generation[(state_id, time_index, str(uid))] = float(
                    row["generation_mw"]
                )
            for uid in model.BRANCH:
                row = maps["security_branch"][(timestamp, state_id, str(uid))]
                branch_flow[(state_id, time_index, str(uid))] = float(row["flow_mw"])

    for state_id in handle.state_ids:
        state = state_by_id[state_id]
        for time_index, timestamp in enumerate(timestamps):
            flows = {
                str(uid): branch_flow[(state_id, time_index, str(uid))]
                for uid in model.BRANCH
            }
            for uid in model.GEN:
                model.generation[state_id, time_index, uid].set_value(
                    generation[(state_id, time_index, str(uid))],
                    skip_validation=True,
                )
            for uid in model.BRANCH:
                model.branch_flow[state_id, time_index, uid].set_value(
                    flows[str(uid)], skip_validation=True
                )
            angles = _state_angles(handle, state, time_index, flows)
            for bus in model.BUS:
                model.angle_degrees[state_id, time_index, bus].set_value(
                    angles[int(bus)], skip_validation=True
                )

            if len(model.DC_BRANCH) != 1:
                raise RuntimeError("Warm-start reconstruction requires one HVDC branch")
            dc_uid = next(iter(model.DC_BRANCH))
            dc_branch = context.dc_branch_by_uid[str(dc_uid)]
            if state.response_mode == "fixed" or state_id == "normal":
                hourly = maps["hourly"][(timestamp,)]
                dc_value = float(hourly[f"hvdc_{str(dc_uid).lower()}_flow_mw"])
            else:
                from_bus = int(dc_branch.from_bus)
                bus_generation = sum(
                    generation[(state_id, time_index, str(uid))]
                    for uid in context.generators_at_bus[from_bus]
                )
                ac_export = sum(
                    flows[str(uid)] for uid in context.outgoing_branches[from_bus]
                ) - sum(flows[str(uid)] for uid in context.incoming_branches[from_bus])
                dc_value = (
                    bus_generation
                    - float(context.total_demand_by_bus_mw[time_index][from_bus])
                    - ac_export
                )
            model.dc_flow[state_id, time_index, dc_uid].set_value(
                dc_value, skip_validation=True
            )

    for time_index in model.TIME:
        for uid in model.THERMAL:
            generator = context.generator_by_uid[str(uid)]
            breakpoints = tuple(float(item) for item in generator.cost_breakpoints_mw)
            committed = float(value(model.commitment[time_index, uid]))
            remaining = max(
                float(normal_generation[int(time_index)][str(uid)])
                - breakpoints[0] * committed,
                0.0,
            )
            for segment in range(3):
                width = (breakpoints[segment + 1] - breakpoints[segment]) * committed
                segment_value = min(remaining, width)
                model.segment_power[time_index, uid, segment].set_value(
                    segment_value, skip_validation=True
                )
                remaining = max(remaining - segment_value, 0.0)
    proxy = v3._reactive_proxy_value(
        problem.parent_context, problem.points, tuple(commitment_rows)
    )
    model.reactive_proxy.set_value(proxy, skip_validation=True)

    assigned_count = sum(
        1 for _ in model.component_data_objects(Var, active=True, descend_into=True)
    )
    component_counts = {
        component.local_name: len(component)
        for component in model.component_objects(Var, active=True)
    }
    maximum_constraint_violation = float(formulation._constraint_violation(model))
    maximum_integrality_violation = float(formulation._integrality_violation(model))
    residual = formulation._residual_audit(
        handle,
        problem,
        float(config["solver"]["feasibility_tolerance"]),
    )
    operating_cost = float(value(model.operating_cost))
    expected_proxy = float(config["warm_start"]["expected_proxy_objective"])
    expected_cost = float(config["warm_start"]["expected_operating_cost_usd"])
    objective_tolerance = float(config["warm_start"]["objective_absolute_tolerance"])
    passed = bool(
        assigned_count == handle.formulation_variables
        and formulation._all_variables_finite(model)
        and maximum_constraint_violation
        <= float(config["warm_start"]["maximum_constraint_violation"])
        and maximum_integrality_violation
        <= float(config["warm_start"]["maximum_integrality_violation"])
        and residual["passed"]
        and abs(proxy - expected_proxy) <= objective_tolerance
        and abs(operating_cost - expected_cost) <= objective_tolerance
    )
    record = {
        "schema": "rts_gmlc_full_column_parent_warm_start_audit_v1",
        "passed": passed,
        "state_ids": list(handle.state_ids),
        "variable_count": assigned_count,
        "expected_variable_count": handle.formulation_variables,
        "component_counts": component_counts,
        "missing_variable_count": 0,
        "all_variables_finite": formulation._all_variables_finite(model),
        "assignment_sha256": _assignment_sha256(model),
        "maximum_constraint_violation": maximum_constraint_violation,
        "maximum_integrality_violation": maximum_integrality_violation,
        "reactive_proxy": proxy,
        "operating_cost_usd": operating_cost,
        "residual_audit": residual,
    }
    if not passed:
        raise RuntimeError(f"Parent full-column warm-start audit failed: {record}")
    return record


def _software_versions() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        **{
            package: importlib.metadata.version(package)
            for package in ("highspy", "numpy", "pyomo", "pyyaml")
        },
    }


def record_v2_invalidation() -> dict[str, object]:
    preparation_root = _V2_ROOT / "preparation"
    _verify_output_manifest(preparation_root)
    registration = json.loads(
        (preparation_root / "registration.json").read_text(encoding="utf-8")
    )
    if (
        registration.get("benchmark_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_warmstart_benchmark_v2"
        or registration.get("competitive_solve_executed") is not False
    ):
        raise RuntimeError("Warm-start v2 preparation drifted before invalidation")
    required_logs = (
        "attempt.json",
        "progress.jsonl",
        "highs_cold_start_r1.log",
        "appsi_highs_full_mip_start_r1.log",
        "launcher.stderr.log",
    )
    if any(not (_V2_ATTEMPT_ROOT / name).is_file() for name in required_logs):
        raise RuntimeError("Warm-start v2 invalidation evidence is incomplete")
    completed = []
    for line in (
        (_V2_ATTEMPT_ROOT / "progress.jsonl").read_text(encoding="utf-8").splitlines()
    ):
        event = json.loads(line)
        if event.get("event") == "warmstart_benchmark_solve_completed":
            completed.append(
                {
                    "method": event["method"],
                    "repetition": event["repetition"],
                    "eligible": event["eligible"],
                    "first_finite_incumbent_seconds": event["native_log_evidence"][
                        "first_finite_incumbent_seconds"
                    ],
                    "solve_seconds": event["solve_seconds"],
                    "certified_lower_bound": event["certified_lower_bound"],
                    "certified_upper_bound": event["certified_upper_bound"],
                    "relative_gap_to_incumbent": event["relative_gap_to_incumbent"],
                    "residual_audit_passed": bool(
                        event.get("residual_audit")
                        and event["residual_audit"].get("passed")
                    ),
                }
            )
    if [(item["method"], item["repetition"]) for item in completed] != [
        ("highs_cold_start", 1),
        ("appsi_highs_full_mip_start", 1),
    ]:
        raise RuntimeError("Warm-start v2 completed-run evidence drifted")
    core_path = Path("src/grid/rts_gmlc_ac_aware_commitment.py")
    restored_hash = _sha256(core_path)
    if (
        restored_hash
        != "bdd106e00bf1750b8867e9e3127c797054aa6f8ca9456821c4eb252ddf93d824"
    ):
        raise RuntimeError("Warm-start v2 core was not restored before invalidation")
    payload = {
        "schema": "rts_gmlc_zero_dc_ac_aware_warmstart_invalidation_v1",
        "benchmark_id": registration["benchmark_id"],
        "status": "invalidated_after_two_of_four_runs_due_to_shared_dependency_byte_drift",
        "preparation_manifest_sha256": _sha256(preparation_root / "SHA256SUMS"),
        "input_contract_sha256": registration["input_contract_sha256"],
        "competitive_solve_count": len(completed),
        "planned_solve_count": 4,
        "completed_runs_are_diagnostic_only": True,
        "completed_runs_allowed_for_successor_selection": False,
        "successor_must_rerun_complete_registered_matrix": True,
        "candidate_or_joint_ac_result": False,
        "failure": (
            "shared_ac_aware_core_line_endings_changed_after_warm_r1_and_strict_"
            "v3_hash_gate_stopped_before_warm_r2"
        ),
        "semantic_source_difference_observed": False,
        "byte_level_source_difference_observed": True,
        "restored_core_sha256": restored_hash,
        "diagnostic_completed_runs": completed,
        "evidence_sha256": {
            name: _sha256(_V2_ATTEMPT_ROOT / name) for name in required_logs
        },
    }
    target = _V2_ROOT / "invalidation"
    if target.exists():
        _verify_output_manifest(target)
        observed = json.loads(
            (target / "invalidation.json").read_text(encoding="utf-8")
        )
        if observed != _stable_json(payload):
            raise RuntimeError("Published warm-start v2 invalidation drifted")
        return observed

    def writer(staging: Path) -> None:
        _write_json(staging / "invalidation.json", payload)
        (staging / "invalidation_source.py").write_bytes(_SCRIPT_PATH.read_bytes())

    _publish_payload(target, writer)
    return json.loads((target / "invalidation.json").read_text(encoding="utf-8"))


def _output_root(config: Mapping[str, Any], override: Path | None) -> Path:
    return override or Path(config["output"]["directory"])


def prepare(
    config_path: Path = _CONFIG_PATH, *, output_directory: Path | None = None
) -> dict[str, object]:
    config = _read_config(config_path)
    verified = _verify_provenance(config)
    problem, handle = _build_handle(config)
    coverage = _assign_parent_start(config, problem, handle)
    input_contract = {
        "schema": "rts_gmlc_zero_dc_ac_aware_warmstart_inputs_v2",
        "config_sha256": _sha256(config_path),
        "script_sha256": _sha256(_SCRIPT_PATH),
        "verified_provenance": verified,
        "coverage_assignment_sha256": coverage["assignment_sha256"],
        "software_versions": _software_versions(),
    }
    input_contract_sha256 = common_input_signature_sha256(input_contract)
    output_root = _output_root(config, output_directory)
    target = output_root / config["output"]["preparation_subdirectory"]
    payload = {
        "schema": "rts_gmlc_zero_dc_ac_aware_warmstart_preparation_v2",
        "benchmark_id": config["preregistration"]["id"],
        "status": "prepared_full_column_start_audited_not_run",
        "competitive_solve_executed": False,
        "config_sha256": _sha256(config_path),
        "script_sha256": _sha256(_SCRIPT_PATH),
        "verified_provenance": verified,
        "coverage_audit": coverage,
        "input_contract": input_contract,
        "input_contract_sha256": input_contract_sha256,
        "software_versions": _software_versions(),
    }
    if target.exists():
        _verify_output_manifest(target)
        observed = json.loads(
            (target / "registration.json").read_text(encoding="utf-8")
        )
        if observed != _stable_json(payload):
            raise RuntimeError("Published warm-start preparation drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare beside existing warm-start artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        (staging / "benchmark.py").write_bytes(_SCRIPT_PATH.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return json.loads((target / "registration.json").read_text(encoding="utf-8"))


def _install_audited_appsi_warm_start(solver: Any) -> None:
    def warm_start(instance: Any) -> None:
        column_count = len(instance._pyomo_var_to_solver_var_map)
        column_values = np.empty(column_count, dtype=np.double)
        covered = np.zeros(column_count, dtype=bool)
        for var_id, column in instance._pyomo_var_to_solver_var_map.items():
            variable = instance._vars[var_id][0]
            candidate = value(variable, exception=False)
            if candidate is None or not math.isfinite(float(candidate)):
                raise RuntimeError(
                    f"Missing appsi warm-start value for {variable.name}"
                )
            column_values[column] = float(candidate)
            covered[column] = True
        if not bool(np.all(covered)):
            raise RuntimeError("Appsi warm-start solver-column coverage is incomplete")
        solution = HighsSolution()
        solution.col_value = column_values
        solution.value_valid = True
        solution.dual_valid = False
        status = instance._solver_model.setSolution(solution)
        instance._warmstart_submission_status = str(status)
        instance._warmstart_submitted_column_count = int(column_count)

    solver._warm_start = MethodType(warm_start, solver)


def _parse_native_log(
    path: Path, *, acceptance_text: str, rejection_text: str
) -> dict[str, object]:
    text = path.read_text(encoding="utf-8", errors="replace")
    accepted_lines = [
        line.strip() for line in text.splitlines() if acceptance_text in line
    ]
    rejected_lines = [
        line.strip() for line in text.splitlines() if rejection_text in line
    ]
    accepted_objective = None
    if accepted_lines:
        suffix = accepted_lines[0].split(acceptance_text, 1)[1].strip()
        try:
            accepted_objective = float(suffix.split()[0])
        except (ValueError, IndexError):
            accepted_objective = None
    first_incumbent_seconds = None
    first_incumbent_objective = None
    first_incumbent_source = None
    for line in text.splitlines():
        tokens = line.split()
        source_offset = (
            1 if tokens and len(tokens[0]) == 1 and tokens[0].isalpha() else 0
        )
        if (
            len(tokens) < 12 + source_offset
            or not tokens[3 + source_offset].endswith("%")
            or not tokens[-1].endswith("s")
        ):
            continue
        try:
            incumbent = float(tokens[5 + source_offset])
            seconds = float(tokens[-1][:-1])
        except ValueError:
            continue
        if math.isfinite(incumbent) and math.isfinite(seconds):
            first_incumbent_seconds = seconds
            first_incumbent_objective = incumbent
            first_incumbent_source = tokens[0] if source_offset else None
            break
    return {
        "mip_start_acceptance_line_count": len(accepted_lines),
        "mip_start_rejection_line_count": len(rejected_lines),
        "mip_start_accepted_objective": accepted_objective,
        "first_finite_incumbent_seconds": first_incumbent_seconds,
        "first_finite_incumbent_objective": first_incumbent_objective,
        "first_finite_incumbent_source": first_incumbent_source,
    }


def _fsync(path: Path) -> None:
    with path.open("ab") as output:
        output.flush()
        os.fsync(output.fileno())


def _solve_run(
    config: Mapping[str, Any],
    method: str,
    repetition: int,
    log_root: Path,
    progress: JsonlProgressWriter,
) -> dict[str, object]:
    problem, handle = _build_handle(config)
    warm_audit = None
    warm = method == "appsi_highs_full_mip_start"
    if warm:
        warm_audit = _assign_parent_start(config, problem, handle)
    interface = (
        config["solver"]["warm_interface"]
        if warm
        else config["solver"]["cold_interface"]
    )
    solver = SolverFactory(str(interface))
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Warm-start benchmark solver unavailable: {interface}")
    if warm:
        if not solver.warm_start_capable():
            raise RuntimeError("appsi_highs no longer reports warm-start capability")
        _install_audited_appsi_warm_start(solver)
    native_log = log_root / f"{method}_r{repetition}.log"
    if native_log.exists():
        raise FileExistsError(f"Warm-start native log exists: {native_log}")
    native_log.parent.mkdir(parents=True, exist_ok=True)
    options = highs_runtime_options(
        mip_relative_gap=float(config["solver"]["target_mip_relative_gap"]),
        threads=int(config["solver"]["threads"]),
        random_seed=int(config["solver"]["random_seed"]),
        feasibility_tolerance=float(config["solver"]["feasibility_tolerance"]),
        time_limit_seconds=float(config["solver"]["time_limit_seconds_per_run"]),
        log_file=native_log,
        mip_min_logging_interval_seconds=float(
            config["solver"]["mip_min_logging_interval_seconds"]
        ),
    )
    progress.emit(
        "warmstart_benchmark_solve_started",
        method=method,
        repetition=repetition,
        warm_start=warm,
        native_log=native_log.name,
    )
    Highs.resetGlobalScheduler(True)
    started = time.perf_counter()
    with ProgressHeartbeat(
        progress,
        interval_seconds=float(config["solver"]["heartbeat_interval_seconds"]),
        payload={"method": method, "repetition": repetition},
    ):
        results = solver.solve(
            handle.model,
            load_solutions=False,
            tee=False,
            options=options,
            **({"warmstart": True} if warm else {}),
        )
    solve_seconds = time.perf_counter() - started
    _fsync(native_log)
    termination = results.solver.termination_condition
    raw_lower = formulation._optional_float(results.problem.lower_bound)
    raw_upper = formulation._optional_float(results.problem.upper_bound)
    loaded = False
    try:
        handle.model.solutions.load_from(results)
        loaded = True
    except Exception:
        loaded = False
    objective = (
        formulation._optional_float(value(handle.model.reactive_proxy, exception=False))
        if loaded
        else None
    )
    constraint_violation = (
        float(formulation._constraint_violation(handle.model)) if loaded else None
    )
    integrality_violation = (
        float(formulation._integrality_violation(handle.model)) if loaded else None
    )
    tolerance = float(config["solver"]["feasibility_tolerance"])
    incumbent_usable = formulation._incumbent_is_usable(
        termination_condition=termination,
        solution_loaded=loaded,
        incumbent_objective=objective,
        maximum_constraint_violation=constraint_violation,
        maximum_integrality_violation=integrality_violation,
        variables_finite=(
            formulation._all_variables_finite(handle.model) if loaded else False
        ),
        feasibility_tolerance=tolerance,
    )
    bounds = formulation._orient_bound_interval(
        sense="maximize",
        raw_lower_bound=raw_lower,
        raw_upper_bound=raw_upper,
        incumbent_objective=objective,
        consistency_tolerance=float(config["solver"]["bound_consistency_tolerance"]),
    )
    residual = None
    if incumbent_usable:
        residual = formulation._residual_audit(handle, problem, tolerance)
    parsed_log = _parse_native_log(
        native_log,
        acceptance_text=str(config["warm_start"]["native_acceptance_text"]),
        rejection_text=str(config["warm_start"]["native_rejection_text"]),
    )
    set_solution_status = getattr(solver, "_warmstart_submission_status", None)
    submitted_columns = getattr(solver, "_warmstart_submitted_column_count", 0)
    result_parse_compatible = bool(
        str(termination) and raw_lower is not None and raw_upper is not None and loaded
    )
    start_gate = bool(
        not warm
        or (
            warm_audit is not None
            and warm_audit["passed"]
            and set_solution_status
            == str(config["warm_start"]["appsi_set_solution_status_required"])
            and submitted_columns == handle.formulation_variables
            and parsed_log["mip_start_acceptance_line_count"] == 1
            and parsed_log["mip_start_rejection_line_count"] == 0
            and parsed_log["first_finite_incumbent_seconds"] is not None
        )
    )
    relative_gap = bounds["relative_gap_to_incumbent"]
    eligible = bool(
        start_gate
        and result_parse_compatible
        and incumbent_usable
        and bounds["bound_valid"]
        and relative_gap is not None
        and float(relative_gap) <= float(config["solver"]["target_mip_relative_gap"])
        and residual is not None
        and residual["passed"]
        and parsed_log["first_finite_incumbent_seconds"] is not None
    )
    record = {
        "method": method,
        "repetition": repetition,
        "warm_start": warm,
        "warm_start_audit": warm_audit,
        "set_solution_status": set_solution_status,
        "submitted_solver_column_count": submitted_columns,
        "native_log": native_log.name,
        "native_log_evidence": parsed_log,
        "solve_seconds": solve_seconds,
        "termination_condition": str(termination),
        "solver_status": str(results.solver.status),
        "solution_loaded": loaded,
        "result_parse_compatible": result_parse_compatible,
        "incumbent_usable": incumbent_usable,
        "incumbent_objective": objective,
        "raw_lower_bound": raw_lower,
        "raw_upper_bound": raw_upper,
        "maximum_constraint_violation": constraint_violation,
        "maximum_integrality_violation": integrality_violation,
        "residual_audit": residual,
        "start_gate_passed": start_gate,
        "eligible": eligible,
        **bounds,
    }
    progress.emit("warmstart_benchmark_solve_completed", **record)
    return record


def _select_method(
    config: Mapping[str, Any], runs: Sequence[Mapping[str, object]]
) -> dict[str, object]:
    summaries = []
    for method in _METHODS:
        records = [record for record in runs if record["method"] == method]
        eligible = bool(
            len(records) == int(config["benchmark"]["repetitions"])
            and all(record["eligible"] for record in records)
        )
        first_incumbents = [
            float(record["native_log_evidence"]["first_finite_incumbent_seconds"])
            for record in records
            if record["native_log_evidence"]["first_finite_incumbent_seconds"]
            is not None
        ]
        solve_seconds = [float(record["solve_seconds"]) for record in records]
        summaries.append(
            {
                "method": method,
                "completed_repetitions": len(records),
                "eligible_repetitions": sum(
                    bool(record["eligible"]) for record in records
                ),
                "eligible": eligible,
                "median_time_to_first_finite_incumbent_seconds": (
                    statistics.median(first_incumbents)
                    if len(first_incumbents) == len(records) and records
                    else None
                ),
                "median_solver_wall_seconds": (
                    statistics.median(solve_seconds) if solve_seconds else None
                ),
                "maximum_solver_wall_seconds": (
                    max(solve_seconds) if solve_seconds else None
                ),
            }
        )
    method_order = {method: index for index, method in enumerate(_METHODS)}
    eligible_summaries = [summary for summary in summaries if summary["eligible"]]
    selected = (
        min(
            eligible_summaries,
            key=lambda item: (
                item["median_time_to_first_finite_incumbent_seconds"],
                item["median_solver_wall_seconds"],
                item["maximum_solver_wall_seconds"],
                method_order[item["method"]],
            ),
        )["method"]
        if eligible_summaries
        else None
    )
    return {
        "status": (
            "selected_by_preregistered_nonobjective_runtime_rule"
            if selected is not None
            else config["selection"]["no_eligible_method_rule"]
        ),
        "selected_method": selected,
        "methods": summaries,
        "objective_value_used": False,
    }


def run_benchmark(
    config_path: Path = _CONFIG_PATH, *, output_directory: Path | None = None
) -> dict[str, object]:
    config = _read_config(config_path)
    _verify_provenance(config)
    output_root = _output_root(config, output_directory)
    preparation_root = output_root / config["output"]["preparation_subdirectory"]
    _verify_output_manifest(preparation_root)
    registration = json.loads(
        (preparation_root / "registration.json").read_text(encoding="utf-8")
    )
    if (
        registration.get("config_sha256") != _sha256(config_path)
        or registration.get("script_sha256") != _sha256(_SCRIPT_PATH)
        or registration.get("coverage_audit", {}).get("passed") is not True
    ):
        raise RuntimeError("Warm-start benchmark preparation is stale")
    target = output_root / config["output"]["benchmark_subdirectory"]
    if target.exists():
        _verify_output_manifest(target)
        return json.loads((target / "summary.json").read_text(encoding="utf-8"))
    run_id = str(config["benchmark"]["attempt_id"])
    log_root = Path(config["output"]["log_directory"]) / run_id
    log_root.mkdir(parents=True, exist_ok=True)
    attempt_path = log_root / "attempt.json"
    attempt = {
        "schema": "rts_gmlc_zero_dc_ac_aware_warmstart_attempt_v1",
        "run_id": run_id,
        "process_id": os.getpid(),
        "benchmark_id": config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "preparation_manifest_sha256": _sha256(preparation_root / "SHA256SUMS"),
        "execution_order": list(config["benchmark"]["execution_order"]),
        "time_limit_seconds_per_run": config["solver"]["time_limit_seconds_per_run"],
    }
    if attempt_path.exists():
        raise FileExistsError(f"Warm-start attempt record exists: {attempt_path}")
    attempt_path.write_bytes(
        (json.dumps(attempt, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )
    _fsync(attempt_path)
    progress_path = log_root / "progress.jsonl"
    if progress_path.exists():
        raise FileExistsError(f"Warm-start progress log exists: {progress_path}")
    progress = JsonlProgressWriter(
        progress_path,
        run_id=run_id,
        preregistration_id=str(config["preregistration"]["id"]),
        input_contract_sha256=str(registration["input_contract_sha256"]),
    )
    runs = []
    for label in config["benchmark"]["execution_order"]:
        method, repetition_text = str(label).rsplit("_r", 1)
        runs.append(
            _solve_run(config, method, int(repetition_text), log_root, progress)
        )
    selection = _select_method(config, runs)
    summary = {
        "schema": "rts_gmlc_zero_dc_ac_aware_warmstart_benchmark_result_v2",
        "benchmark_id": config["preregistration"]["id"],
        "formal_candidate_result": False,
        "joint_ac_solver_call_count": 0,
        "all_runs_attempted": len(runs) == len(config["benchmark"]["execution_order"]),
        "run_count": len(runs),
        "run_id": run_id,
        "live_log_directory": log_root.as_posix(),
        "preparation_manifest_sha256": _sha256(preparation_root / "SHA256SUMS"),
        "selection": selection,
        "objective_value_used_for_selection": False,
        "software_versions": _software_versions(),
    }

    def writer(staging: Path) -> None:
        _write_json(staging / "runs.json", runs)
        _write_json(staging / "summary.json", summary)
        snapshot = staging / "live_logs_snapshot"
        snapshot.mkdir()
        for path in sorted(log_root.iterdir()):
            if path.is_file():
                shutil.copy2(path, snapshot / path.name)

    _publish_payload(target, writer)
    return json.loads((target / "summary.json").read_text(encoding="utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=_CONFIG_PATH)
    parser.add_argument(
        "--stage", choices=("invalidate-v2", "prepare", "run"), required=True
    )
    parser.add_argument("--output-directory", type=Path)
    args = parser.parse_args()
    if args.stage == "invalidate-v2":
        result = record_v2_invalidation()
    elif args.stage == "prepare":
        result = prepare(args.config, output_directory=args.output_directory)
    else:
        result = run_benchmark(args.config, output_directory=args.output_directory)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
