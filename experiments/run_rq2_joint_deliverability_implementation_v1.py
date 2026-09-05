"""Implementation-only runner for the sealed RQ2 V5 scientific protocol.

The checked-in configuration keeps formal execution closed.  The public
functions provide the complete capacity-stage implementation for a later,
separately reviewed execution successor.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import yaml

from experiments.validate_rq2_joint_deliverability_implementation_v1 import (
    validate as validate_implementation_config,
)
from src.evaluation.rq2_joint_deliverability import (
    REGISTERED_METRICS,
    CapacityInterval,
    CellArmCapacity,
    bootstrap_draw_stream,
    bootstrap_transport_intervals,
    canonical_certificate_payload,
    capacity_attribution,
    certify_scalar_transport,
    execute_holdout_policy,
    finalize_capacity_certificate,
    finalize_operational_attribution,
    operational_labels,
    validate_transport_runtime,
)
from src.models.rq2_joint_deliverability import (
    FOUR_ARM_IDS,
    NETWORK_ONLY_SHARED,
    ArmPlanningCertificate,
    audit_fixed_service_trajectory,
    solve_arm_minimum_capacity,
)
from src.scenarios.rq2_joint_deliverability import (
    PowerBlock,
    RegisteredCell,
    WorkloadBlock,
    build_pair_scenario,
    condition_finite_power,
    expand_registered_cells,
    network_capacity_key,
    planning_inputs,
    scenario_track_requirements,
    select_representatives,
    structural_recovery_witness,
)
from src.solvers.rq2_solver_adapter import Rq2SolverSpec, solver_options

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_joint_deliverability_implementation_successor_v1.yaml"
CONFIG = ROOT / CONFIG_RELATIVE
V5_OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v5."
    "OUTER.SHA256SUMS.json"
)
V5_REVIEW_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_review_pass_v5.yaml"
)
V5_OUTER_SHA256 = "92a58498e1de5f84b132067e3d4a4443ae841747846785e9df54cd9afd7efdfd"
V5_REVIEW_SHA256 = "0ec073c38eac003255fa2d2753edb28f4d02e0f7756c34e185027ac23b140722"


class _UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise TypeError(f"YAML mapping key must be a string: {key!r}")
        if key in result:
            raise ValueError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_yaml(path: Path) -> dict[str, Any]:
    loaded = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    if not isinstance(loaded, dict):
        raise TypeError(f"{path} must contain a mapping")
    return loaded


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(value: object) -> str:
    payload = (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _cell_values(cell: RegisteredCell) -> tuple[object, ...]:
    return (
        cell.hourly_cfe_target,
        cell.flexible_fraction,
        cell.normalized_recovery_headroom,
        cell.recovery_efficiency,
        cell.maximum_event_duration_hours,
        cell.maximum_event_count,
        cell.normalized_energy_budget,
        cell.normalized_debt_limit,
    )


def _validate_solver_specification(
    design: Mapping[str, object],
    specification: Rq2SolverSpec,
) -> None:
    raw_expected = design.get("solver_contract")
    if not isinstance(raw_expected, Mapping):
        raise TypeError("sealed solver contract must be a mapping")
    expected = dict(raw_expected)
    required_fields = expected.pop("required_certificate_fields", None)
    if required_fields != [
        "incumbent_capacity",
        "objective_lower_bound",
        "objective_upper_bound",
        "absolute_gap",
        "incumbent_relative_gap",
        "maximum_constraint_residual",
        "termination_condition",
        "solver_status",
        "model_variables",
        "model_constraints",
        "solver_name",
        "solver_version",
        "solver_options",
    ]:
        raise ValueError("required solver certificate fields drifted")
    if asdict(specification) != expected:
        raise ValueError("solver specification drifted from the sealed V5 contract")


def _planning_input_sha256(
    inputs: object,
    arm_id: str,
    solver_specification: Rq2SolverSpec,
) -> str:
    scenarios = []
    for scenario in inputs.scenarios:
        payload = {
            "name": scenario.name,
            "power_block_id": scenario.power_block_id,
            "workload_block_id": scenario.workload_block_id,
            "probability": scenario.probability,
            "raw_grid_request": scenario.raw_grid_request,
            "effective_grid_request": scenario.effective_grid_request,
            "available_flexibility": scenario.available_flexibility,
            "connected_demand": scenario.connected_demand,
            "business_recovery_headroom": scenario.business_recovery_headroom,
        }
        if arm_id != NETWORK_ONLY_SHARED:
            payload.update(
                {
                    "raw_cfe_request": scenario.raw_cfe_request,
                    "effective_cfe_request": scenario.effective_cfe_request,
                    "cfe_service_recovery_headroom": (
                        scenario.cfe_service_recovery_headroom
                    ),
                }
            )
        scenarios.append(payload)
    scalar_inputs = {
        key: value for key, value in asdict(inputs).items() if key != "scenarios"
    }
    return _canonical_sha256(
        {
            "arm_id": arm_id,
            "scenarios": scenarios,
            "planning_parameters": scalar_inputs,
            "solver_specification": asdict(solver_specification),
        }
    )


def _renormalized_subset(inputs: object, scenarios: Sequence[object]) -> object:
    total = sum(float(scenario.probability) for scenario in scenarios)
    if total <= 0.0:
        raise ValueError("full-support fallback scenario mass must be positive")
    return replace(
        inputs,
        scenarios=tuple(
            replace(scenario, probability=float(scenario.probability) / total)
            for scenario in scenarios
        ),
    )


def _audit_full_support_candidate(
    full_inputs: object,
    arm_id: str,
    *,
    incumbent_capacity: float,
    solver_specification: Rq2SolverSpec,
    solve: Callable[
        [object, str, Rq2SolverSpec],
        ArmPlanningCertificate | Mapping[str, object],
    ],
    batch_size: int,
) -> dict[str, object]:
    """Audit full support, using exact MILP fallback when grid excess can help."""

    if (
        isinstance(batch_size, bool)
        or not isinstance(batch_size, int)
        or batch_size <= 0
    ):
        raise ValueError("full-support batch size must be a positive integer")
    tolerance = solver_specification.feasibility_tolerance
    failures: list[str] = []
    fallback_scenarios = []
    for scenario in full_inputs.scenarios:
        single = _renormalized_subset(full_inputs, (scenario,))
        audit = audit_fixed_service_trajectory(single, arm_id)
        if audit.required_capacity > incumbent_capacity + tolerance:
            failures.append(
                f"{scenario.name}:required_capacity_exceeds_representative_incumbent"
            )
            continue
        if not audit.violations:
            continue
        if arm_id == "cfe_only_shared":
            failures.extend(audit.violations)
        else:
            fallback_scenarios.append(scenario)

    fallback_certificates: list[dict[str, object]] = []
    fallback_solver_calls = 0
    unresolved = False
    for first in range(0, len(fallback_scenarios), batch_size):
        batch = fallback_scenarios[first : first + batch_size]
        batch_inputs = _renormalized_subset(full_inputs, batch)
        certificate = _candidate_mapping(
            solve(batch_inputs, arm_id, solver_specification)
        )
        _validate_solver_certificate_binding(certificate, solver_specification)
        verified = finalize_capacity_certificate(
            arm_id=arm_id,
            candidate=certificate,
            tolerance=tolerance,
        )
        fallback_solver_calls += 1
        fallback_certificates.append(certificate)
        if verified.status == "resolved" and verified.reported_point is not None:
            if verified.reported_point > incumbent_capacity + tolerance:
                failures.append(
                    "full_support_required_capacity_exceeds_representative_incumbent"
                )
        elif verified.status == (
            "proven_infeasible_at_registered_cap_estimand_undefined"
        ):
            failures.append("full_support_proven_infeasible_at_registered_cap")
        else:
            unresolved = True
    return {
        "status": (
            "failed" if failures else ("unresolved" if unresolved else "passed")
        ),
        "failures": tuple(dict.fromkeys(failures)),
        "fallback_scenario_count": len(fallback_scenarios),
        "fallback_solver_calls": fallback_solver_calls,
        "fallback_certificates": fallback_certificates,
    }


def planning_task_inventory(
    design: dict[str, Any],
) -> tuple[dict[str, object], ...]:
    """Return all 184 outputs and 157 unique solver task identities."""

    tasks = []
    for cell in expand_registered_cells(design):
        for arm_id in FOUR_ARM_IDS:
            key_values = (
                network_capacity_key(cell)
                if arm_id == NETWORK_ONLY_SHARED
                else _cell_values(cell)
            )
            solve_key = _canonical_sha256(
                {
                    "arm_id": arm_id,
                    "cell_parameters": key_values,
                }
            )
            tasks.append(
                {
                    "cell_id": cell.cell_id,
                    "arm_id": arm_id,
                    "solve_key": solve_key,
                    "network_alpha_reuse": arm_id == NETWORK_ONLY_SHARED,
                }
            )
    if (
        len(tasks) != 184
        or len({(str(task["arm_id"]), str(task["solve_key"])) for task in tasks}) != 157
    ):
        raise ValueError("planning task inventory drifted")
    return tuple(tasks)


def _representatives(
    design: dict[str, Any],
    power_blocks: tuple[PowerBlock, ...],
    workload_blocks: tuple[WorkloadBlock, ...],
) -> tuple[tuple[PowerBlock, ...], tuple[WorkloadBlock, ...], float]:
    if any(block.split != "training" for block in power_blocks):
        raise ValueError("capacity stage received non-training power")
    if any(block.split != "training" for block in workload_blocks):
        raise ValueError("capacity stage received non-training workload")
    finite_power, e0_mass = condition_finite_power(power_blocks)
    if not finite_power:
        raise ValueError("training support has no finite power blocks")
    selection = design["representative_selection"]
    targets = tuple(float(value) for value in selection["quantile_targets"])
    power = select_representatives(
        finite_power,
        role="power",
        quantile_targets=targets,
    )
    workload = select_representatives(
        workload_blocks,
        role="workload",
        quantile_targets=targets,
    )
    return power, workload, e0_mass


def _pair_scenarios(
    power_blocks: Sequence[PowerBlock],
    workload_blocks: Sequence[WorkloadBlock],
    cell: RegisteredCell,
    design: dict[str, Any],
) -> tuple[object, ...]:
    tolerance = float(design["temporal_envelope"]["service_shortfall_tolerance"])
    return tuple(
        build_pair_scenario(
            power,
            workload,
            cell,
            service_shortfall_tolerance=tolerance,
            name=f"{power.block_id}__{workload.block_id}",
        )
        for power in power_blocks
        for workload in workload_blocks
    )


def _first_structural_witness(
    cell: RegisteredCell,
    arm_id: str,
    scenarios: Sequence[object],
    design: dict[str, Any],
) -> dict[str, object] | None:
    temporal = design["temporal_envelope"]
    precheck = design["zero_recovery_structural_precheck"]
    for scenario in scenarios:
        for track, required, headroom in scenario_track_requirements(
            scenario,
            arm_id,
        ):
            witness = structural_recovery_witness(
                cell_id=cell.cell_id,
                arm_id=arm_id,
                track_id=track,
                power_block_id=scenario.power_block_id,
                workload_block_id=scenario.workload_block_id,
                required_call=required,
                recovery_headroom=headroom,
                maximum_recovery_power=cell.normalized_recovery_headroom,
                recovery_efficiency=cell.recovery_efficiency,
                initial_recovery_debt=float(temporal["initial_recovery_debt"]),
                terminal_recovery_debt_limit=float(
                    temporal["terminal_recovery_debt_limit"]
                ),
                time_step_hours=float(design["data_contract"]["time_step_hours"]),
                service_tolerance=float(temporal["service_shortfall_tolerance"]),
                tolerance=float(precheck["tolerance"]),
            )
            if witness is not None:
                return witness
    return None


def _candidate_mapping(
    certificate: ArmPlanningCertificate | Mapping[str, object],
) -> dict[str, object]:
    if isinstance(certificate, ArmPlanningCertificate):
        return asdict(certificate)
    return dict(certificate)


def _validate_solver_certificate_binding(
    certificate: Mapping[str, object],
    specification: Rq2SolverSpec,
) -> None:
    if (
        certificate.get("solver_name") != specification.name
        or certificate.get("solver_version") != specification.expected_package_version
        or certificate.get("solver_options") != solver_options(specification)
    ):
        raise ValueError("solver certificate identity or options drifted")


def _frontier_summary(rows: Sequence[Mapping[str, object]]) -> dict[str, object]:
    primary: dict[tuple[float, float], list[Mapping[str, object]]] = {}
    oat = []
    for row in rows:
        parameters = row["parameters"]
        if not isinstance(parameters, Mapping):
            raise TypeError("frontier cell parameters must be a mapping")
        if row["family"] == "primary_factorial":
            key = (
                float(parameters["flexible_fraction"]),
                float(parameters["normalized_recovery_headroom"]),
            )
            primary.setdefault(key, []).append(row)
        else:
            oat.append(
                {
                    "cell_id": row["cell_id"],
                    "capacity_attribution": row["capacity_attribution"],
                }
            )
    strata = []
    for (flexible, headroom), cells in sorted(primary.items()):
        ordered = sorted(
            cells,
            key=lambda item: float(item["parameters"]["hourly_cfe_target"]),
        )
        first_positive = next(
            (
                float(item["parameters"]["hourly_cfe_target"])
                for item in ordered
                if item["capacity_attribution"]["resolved"]
                and item["capacity_attribution"]["interval_labels"]["I_joint"]
                == "robust_positive"
            ),
            None,
        )
        first_negative = next(
            (
                float(item["parameters"]["hourly_cfe_target"])
                for item in ordered
                if item["capacity_attribution"]["resolved"]
                and item["capacity_attribution"]["interval_labels"]["I_joint"]
                == "robust_negative"
            ),
            None,
        )
        deliverable = [
            float(item["parameters"]["hourly_cfe_target"])
            for item in ordered
            if item["arms"]["joint_correct_shared"]["status"] == "resolved"
            and float(item["arms"]["joint_correct_shared"]["interval"]["upper"]) <= 1.0
        ]
        strata.append(
            {
                "flexible_fraction": flexible,
                "normalized_recovery_headroom": headroom,
                "cell_ids": [item["cell_id"] for item in ordered],
                "first_registered_robust_positive_joint_interaction": (
                    first_positive
                    if first_positive is not None
                    else "no_interval_supported_crossing_on_registered_grid"
                ),
                "first_registered_robust_negative_joint_interaction": (
                    first_negative
                    if first_negative is not None
                    else "no_interval_supported_crossing_on_registered_grid"
                ),
                "highest_registered_deliverable_target": (
                    max(deliverable) if deliverable else None
                ),
            }
        )
    return {
        "primary_strata": strata,
        "secondary_oat": sorted(
            oat,
            key=lambda item: str(item["cell_id"]).encode("utf-8"),
        ),
        "interpolation_used": False,
        "target_monotonicity_assumed": False,
    }


def execute_capacity_stage(
    design: dict[str, Any],
    *,
    training_power_blocks: tuple[PowerBlock, ...],
    training_workload_blocks: tuple[WorkloadBlock, ...],
    solver_specification: Rq2SolverSpec,
    solve_callback: Callable[
        [object, str, Rq2SolverSpec],
        ArmPlanningCertificate | Mapping[str, object],
    ]
    | None = None,
    full_support_batch_size: int = 256,
) -> dict[str, object]:
    """Execute the complete 46-cell capacity stage on in-memory inputs."""

    if full_support_batch_size != 256:
        raise ValueError("full-support fallback batch size drifted")
    _validate_solver_specification(design, solver_specification)
    solve = solve_callback or (
        lambda inputs, arm_id, spec: solve_arm_minimum_capacity(
            inputs,
            arm_id,
            solver_specification=spec,
        )
    )
    representative_power, representative_workload, training_e0_mass = _representatives(
        design,
        training_power_blocks,
        training_workload_blocks,
    )
    finite_power, _ = condition_finite_power(training_power_blocks)
    cells = expand_registered_cells(design)
    network_cache: dict[
        str,
        tuple[CellArmCapacity, dict[str, object]],
    ] = {}
    rows = []
    representative_solver_calls = 0
    full_support_fallback_solver_calls = 0
    network_cache_hits = 0
    for cell in cells:
        representative_scenarios = _pair_scenarios(
            representative_power,
            representative_workload,
            cell,
            design,
        )
        full_scenarios = _pair_scenarios(
            finite_power,
            training_workload_blocks,
            cell,
            design,
        )
        representative_inputs = planning_inputs(
            representative_scenarios,
            cell,
            design,
        )
        full_inputs = planning_inputs(full_scenarios, cell, design)
        arms: dict[str, CellArmCapacity] = {}
        arm_audits: dict[str, dict[str, object]] = {}
        arm_input_hashes: dict[str, str] = {}
        for arm_id in FOUR_ARM_IDS:
            input_sha256 = _planning_input_sha256(
                representative_inputs,
                arm_id,
                solver_specification,
            )
            arm_input_hashes[arm_id] = input_sha256
            if arm_id == NETWORK_ONLY_SHARED and input_sha256 in network_cache:
                arms[arm_id], arm_audits[arm_id] = network_cache[input_sha256]
                network_cache_hits += 1
                continue
            witness = _first_structural_witness(
                cell,
                arm_id,
                full_scenarios,
                design,
            )
            if witness is not None:
                finalized = finalize_capacity_certificate(
                    arm_id=arm_id,
                    structural_witness=witness,
                )
                support_audit = {
                    "status": "not_applicable_structural_infeasibility",
                    "failures": (),
                    "fallback_scenario_count": 0,
                    "fallback_solver_calls": 0,
                    "fallback_certificates": [],
                }
            else:
                candidate = _candidate_mapping(
                    solve(
                        representative_inputs,
                        arm_id,
                        solver_specification,
                    )
                )
                _validate_solver_certificate_binding(candidate, solver_specification)
                representative_solver_calls += 1
                if (
                    candidate.get("status") == "candidate_resolved"
                    and candidate.get("incumbent_capacity") is not None
                ):
                    support_audit = _audit_full_support_candidate(
                        full_inputs,
                        arm_id,
                        incumbent_capacity=float(candidate["incumbent_capacity"]),
                        solver_specification=solver_specification,
                        solve=solve,
                        batch_size=full_support_batch_size,
                    )
                    full_support_fallback_solver_calls += int(
                        support_audit["fallback_solver_calls"]
                    )
                else:
                    support_audit = {
                        "status": "not_applicable_candidate_unresolved",
                        "failures": (),
                        "fallback_scenario_count": 0,
                        "fallback_solver_calls": 0,
                        "fallback_certificates": [],
                    }
                finalized = finalize_capacity_certificate(
                    arm_id=arm_id,
                    candidate=candidate,
                    training_support_failures=support_audit["failures"],
                    training_support_unresolved=(
                        support_audit["status"] == "unresolved"
                    ),
                )
            arms[arm_id] = finalized
            arm_audits[arm_id] = support_audit
            if arm_id == NETWORK_ONLY_SHARED and finalized.structural_witness is None:
                network_cache[input_sha256] = (finalized, support_audit)
        rows.append(
            {
                "cell_id": cell.cell_id,
                "family": cell.family,
                "parameters": asdict(cell),
                "arms": {
                    arm_id: {
                        **asdict(arms[arm_id]),
                        "planning_input_sha256": arm_input_hashes[arm_id],
                        "full_support_audit": arm_audits[arm_id],
                    }
                    for arm_id in FOUR_ARM_IDS
                },
                "capacity_attribution": capacity_attribution(arms),
            }
        )
    frontier_summary = _frontier_summary(rows)
    return {
        "schema": "rq2_joint_deliverability_capacity_frontier_v3",
        "cell_count": len(rows),
        "arm_output_count": len(rows) * len(FOUR_ARM_IDS),
        "representative_solver_calls": representative_solver_calls,
        "full_support_fallback_solver_calls": full_support_fallback_solver_calls,
        "total_solver_calls": (
            representative_solver_calls + full_support_fallback_solver_calls
        ),
        "network_alpha_reuse_count": network_cache_hits,
        "training_E0_mass": training_e0_mass,
        "representative_power_ids": [block.block_id for block in representative_power],
        "representative_workload_ids": [
            block.block_id for block in representative_workload
        ],
        "frontier_summary": frontier_summary,
        "cells": rows,
    }


def _cell_from_capacity_row(row: Mapping[str, object]) -> RegisteredCell:
    parameters = row.get("parameters")
    if not isinstance(parameters, Mapping):
        raise TypeError("capacity cell parameters must be a mapping")
    cell = RegisteredCell(**dict(parameters))
    if cell.cell_id != row.get("cell_id"):
        raise ValueError("capacity cell identity drifted")
    return cell


def _arm_holdout_arguments(
    scenario: object,
    arm_id: str,
) -> tuple[Sequence[float], Sequence[float], Sequence[float]]:
    zeros = (0.0,) * len(scenario.raw_grid_request)
    grid = (
        scenario.raw_grid_request
        if arm_id
        in {
            "network_only_shared",
            "joint_correct_shared",
            "joint_b6_separate_planning_shared_execution",
        }
        else zeros
    )
    cfe = (
        scenario.raw_cfe_request
        if arm_id
        in {
            "cfe_only_shared",
            "joint_correct_shared",
            "joint_b6_separate_planning_shared_execution",
        }
        else zeros
    )
    recovery = (
        scenario.business_recovery_headroom
        if arm_id == "network_only_shared"
        else scenario.cfe_service_recovery_headroom
    )
    return grid, cfe, recovery


def execute_holdout_stage(
    design: dict[str, Any],
    *,
    capacity_frontier: Mapping[str, object],
    holdout_power_blocks: tuple[PowerBlock, ...],
    holdout_workload_blocks: tuple[WorkloadBlock, ...],
    retain_trajectories: bool = False,
) -> dict[str, object]:
    """Replay all eligible cells on the complete finite holdout Cartesian set."""

    if capacity_frontier.get("schema") != (
        "rq2_joint_deliverability_capacity_frontier_v3"
    ):
        raise ValueError("capacity frontier schema drifted")
    expected_cell_ids = {cell.cell_id for cell in expand_registered_cells(design)}
    capacity_rows = capacity_frontier.get("cells")
    if (
        not isinstance(capacity_rows, Sequence)
        or isinstance(capacity_rows, (str, bytes))
        or len(capacity_rows) != 46
        or {str(row["cell_id"]) for row in capacity_rows} != expected_cell_ids
    ):
        raise ValueError("capacity frontier cell inventory drifted")
    if any(block.split != "holdout" for block in holdout_power_blocks):
        raise ValueError("holdout stage received non-holdout power")
    if any(block.split != "holdout" for block in holdout_workload_blocks):
        raise ValueError("holdout stage received non-holdout workload")
    if (
        not holdout_workload_blocks
        or len({block.block_id for block in holdout_workload_blocks})
        != len(holdout_workload_blocks)
        or abs(math.fsum(block.probability for block in holdout_workload_blocks) - 1.0)
        > 1.0e-9
        or any(
            not math.isfinite(block.probability) or block.probability < 0.0
            for block in holdout_workload_blocks
        )
    ):
        raise ValueError("holdout workload marginal is invalid")
    finite_power, e0_mass = condition_finite_power(holdout_power_blocks)
    finite_power = tuple(
        sorted(finite_power, key=lambda block: block.block_id.encode("utf-8"))
    )
    ordered_power = tuple(
        sorted(
            holdout_power_blocks,
            key=lambda block: block.block_id.encode("utf-8"),
        )
    )
    ordered_workload = tuple(
        sorted(
            holdout_workload_blocks,
            key=lambda block: block.block_id.encode("utf-8"),
        )
    )
    temporal = design["temporal_envelope"]
    rows = []
    trajectory_hash_stream = hashlib.sha256()
    trajectory_hash_count = 0
    for raw_cell in capacity_rows:
        cell_row = dict(raw_cell)
        cell = _cell_from_capacity_row(cell_row)
        raw_arms = cell_row.get("arms")
        if not isinstance(raw_arms, Mapping) or set(raw_arms) != set(FOUR_ARM_IDS):
            raise ValueError("capacity cell arm inventory drifted")
        for arm_id in FOUR_ARM_IDS:
            arm = raw_arms[arm_id]
            if not isinstance(arm, Mapping):
                raise TypeError("capacity cell arm must be a mapping")
            if arm.get("status") == "resolved":
                audit = arm.get("full_support_audit")
                if not isinstance(audit, Mapping) or audit.get("status") != "passed":
                    raise ValueError(
                        "resolved capacity arm lacks a passed full-support audit"
                    )
        eligible = all(
            isinstance(raw_arms[arm_id], Mapping)
            and raw_arms[arm_id].get("status") == "resolved"
            and raw_arms[arm_id].get("reported_point") is not None
            and isinstance(raw_arms[arm_id].get("full_support_audit"), Mapping)
            and raw_arms[arm_id]["full_support_audit"].get("status") == "passed"
            for arm_id in FOUR_ARM_IDS
        )
        if not eligible:
            rows.append(
                {
                    "cell_id": cell.cell_id,
                    "status": "not_evaluable_capacity_unresolved",
                    "pairs": [],
                }
            )
            continue
        pair_rows = []
        for power in finite_power:
            for workload in ordered_workload:
                scenario = build_pair_scenario(
                    power,
                    workload,
                    cell,
                    service_shortfall_tolerance=float(
                        temporal["service_shortfall_tolerance"]
                    ),
                )
                arm_rows = {}
                for arm_id in FOUR_ARM_IDS:
                    capacity = float(raw_arms[arm_id]["reported_point"])
                    grid, cfe, recovery = _arm_holdout_arguments(
                        scenario,
                        arm_id,
                    )
                    outcome = execute_holdout_policy(
                        committed_capacity=capacity,
                        grid_request=grid,
                        cfe_request=cfe,
                        available_flexibility=scenario.available_flexibility,
                        connected_demand=scenario.connected_demand,
                        current_recovery_headroom=recovery,
                        maximum_recovery_power=(cell.normalized_recovery_headroom),
                        recovery_efficiency=cell.recovery_efficiency,
                        maximum_event_duration_hours=(
                            cell.maximum_event_duration_hours
                        ),
                        maximum_event_count=cell.maximum_event_count,
                        minimum_recovery_hours=float(
                            temporal["minimum_recovery_hours"]
                        ),
                        normalized_energy_budget=(cell.normalized_energy_budget),
                        normalized_debt_limit=cell.normalized_debt_limit,
                        terminal_recovery_debt_limit=float(
                            temporal["terminal_recovery_debt_limit"]
                        ),
                        time_step_hours=float(
                            design["data_contract"]["time_step_hours"]
                        ),
                        minimum_event_power=float(temporal["minimum_event_power"]),
                        curtailment_ramp_per_hour=float(
                            temporal["curtailment_ramp_per_hour"]
                        ),
                        response_time_hours=float(temporal["response_time_hours"]),
                        service_shortfall_tolerance=float(
                            temporal["service_shortfall_tolerance"]
                        ),
                    )
                    trajectory = outcome.pop("trajectory")
                    trajectory_key = (
                        f"{cell.cell_id}/{power.block_id}/{workload.block_id}/{arm_id}"
                    )
                    trajectory_sha256 = _canonical_sha256(trajectory)
                    trajectory_hash_stream.update(
                        f"{trajectory_key}\0{trajectory_sha256}\n".encode()
                    )
                    trajectory_hash_count += 1
                    arm_rows[arm_id] = {
                        "capacity": capacity,
                        "metrics": outcome["metrics"],
                        "trajectory_sha256": trajectory_sha256,
                        **({"trajectory": trajectory} if retain_trajectories else {}),
                    }
                pair_rows.append(
                    {
                        "power_block_id": power.block_id,
                        "workload_block_id": workload.block_id,
                        "conditioned_power_probability": power.probability,
                        "workload_probability": workload.probability,
                        "arms": arm_rows,
                    }
                )
        rows.append(
            {
                "cell_id": cell.cell_id,
                "status": (
                    "resolved"
                    if finite_power
                    else "finite_service_identification_unresolved"
                ),
                "pairs": pair_rows,
            }
        )
    return {
        "schema": "rq2_joint_deliverability_holdout_v3",
        "E0_mass": e0_mass,
        "E0_power_block_ids": [
            block.block_id
            for block in ordered_power
            if block.state == "exogenous_grid_infeasibility"
        ],
        "finite_power_block_ids": [block.block_id for block in finite_power],
        "workload_block_ids": [block.block_id for block in ordered_workload],
        "power_marginal": [
            {
                "block_id": block.block_id,
                "probability": block.probability,
                "state": block.state,
            }
            for block in ordered_power
        ],
        "workload_marginal": [
            {
                "block_id": block.block_id,
                "probability": block.probability,
            }
            for block in ordered_workload
        ],
        "trajectories_retained": retain_trajectories,
        "trajectory_hash_count": trajectory_hash_count,
        "trajectory_hash_stream_sha256": trajectory_hash_stream.hexdigest(),
        "cells": rows,
    }


def _metric_values(arms: Mapping[str, object]) -> dict[str, float]:
    prefixes = {
        "network_only_shared": "network_only",
        "cfe_only_shared": "cfe_only",
        "joint_correct_shared": "joint_correct",
        "joint_b6_separate_planning_shared_execution": "joint_b6",
    }
    result: dict[str, float] = {}
    metrics_by_arm: dict[str, Mapping[str, object]] = {}
    for arm_id, prefix in prefixes.items():
        arm = arms.get(arm_id)
        if not isinstance(arm, Mapping):
            raise TypeError("holdout pair arm inventory drifted")
        metrics = arm.get("metrics")
        if not isinstance(metrics, Mapping):
            raise TypeError("holdout pair metrics are missing")
        metrics_by_arm[arm_id] = metrics
        for source, suffix in (
            ("joint_service_failure", "joint_service_failure"),
            ("hard_grid_failure", "hard_grid_failure"),
            ("cfe_service_failure", "cfe_service_failure"),
            ("total_service_shortfall", "total_service_shortfall"),
            ("cfe_shortfall", "cfe_shortfall"),
        ):
            result[f"{prefix}_{suffix}"] = float(metrics[source])
    correct = metrics_by_arm["joint_correct_shared"]
    b6 = metrics_by_arm["joint_b6_separate_planning_shared_execution"]
    result.update(
        {
            "B6_minus_correct_joint_service_failure": float(b6["joint_service_failure"])
            - float(correct["joint_service_failure"]),
            "B6_minus_correct_total_service_shortfall": float(
                b6["total_service_shortfall"]
            )
            - float(correct["total_service_shortfall"]),
            "B6_minus_correct_cfe_shortfall": float(b6["cfe_shortfall"])
            - float(correct["cfe_shortfall"]),
        }
    )
    if set(result) != set(REGISTERED_METRICS):
        raise ValueError("registered holdout metric inventory drifted")
    return result


def _holdout_metric_matrices(
    cell: Mapping[str, object],
    power_ids: Sequence[str],
    workload_ids: Sequence[str],
) -> tuple[list[float], list[float], dict[str, dict[tuple[str, str], float]]]:
    pair_lookup = {
        (str(pair["power_block_id"]), str(pair["workload_block_id"])): pair
        for pair in cell["pairs"]
    }
    expected_pairs = {
        (power_id, workload_id)
        for power_id in power_ids
        for workload_id in workload_ids
    }
    if set(pair_lookup) != expected_pairs:
        raise ValueError("holdout Cartesian pair inventory drifted")
    row_probabilities = []
    for power_id in power_ids:
        probabilities = {
            float(pair_lookup[(power_id, workload_id)]["conditioned_power_probability"])
            for workload_id in workload_ids
        }
        if len(probabilities) != 1:
            raise ValueError("conditioned power probability drifted across pairs")
        row_probabilities.append(probabilities.pop())
    column_probabilities = []
    for workload_id in workload_ids:
        probabilities = {
            float(pair_lookup[(power_id, workload_id)]["workload_probability"])
            for power_id in power_ids
        }
        if len(probabilities) != 1:
            raise ValueError("workload probability drifted across pairs")
        column_probabilities.append(probabilities.pop())
    pair_metrics = {
        pair_id: _metric_values(pair["arms"]) for pair_id, pair in pair_lookup.items()
    }
    matrices = {
        metric: {
            (power_id, workload_id): pair_metrics[(power_id, workload_id)][metric]
            for power_id in power_ids
            for workload_id in workload_ids
        }
        for metric in REGISTERED_METRICS
    }
    return row_probabilities, column_probabilities, matrices


def _bootstrap_identification(
    design: Mapping[str, object],
    holdout: Mapping[str, object],
    metric_matrices: Mapping[
        str,
        Mapping[str, Mapping[tuple[str, str], float]],
    ],
    *,
    endpoint_solver: Callable[..., object],
) -> dict[str, object]:
    bootstrap = design["bootstrap_contract"]
    power_marginal = holdout["power_marginal"]
    workload_marginal = holdout["workload_marginal"]
    draws = bootstrap_draw_stream(
        [str(item["block_id"]) for item in power_marginal],
        [float(item["probability"]) for item in power_marginal],
        [str(item["block_id"]) for item in workload_marginal],
        [float(item["probability"]) for item in workload_marginal],
        power_draw_count=int(
            design["data_contract"]["power_system_blocks"]["holdout_blocks"]
        ),
        workload_draw_count=int(
            design["data_contract"]["workload_blocks"]["holdout_blocks"]
        ),
        replicates=int(bootstrap["replicate_count"]),
        seed=int(bootstrap["pseudorandom_generator"]["seed"]),
    )
    result = bootstrap_transport_intervals(
        draws=draws,
        state_by_power_id={
            str(item["block_id"]): str(item["state"]) for item in power_marginal
        },
        metric_matrices=metric_matrices,
        metric_order=REGISTERED_METRICS,
        endpoint_solver=endpoint_solver,
    )
    evaluated_cell_ids = sorted(
        metric_matrices,
        key=lambda item: item.encode("utf-8"),
    )
    return {
        **result,
        "evaluated_cell_ids": evaluated_cell_ids,
        "not_evaluable_cell_ids": sorted(
            (
                str(cell["cell_id"])
                for cell in holdout["cells"]
                if str(cell["cell_id"]) not in metric_matrices
            ),
            key=lambda item: item.encode("utf-8"),
        ),
    }


def execute_identification_stage(
    design: dict[str, Any],
    *,
    capacity_frontier: Mapping[str, object],
    holdout: Mapping[str, object],
    transport_solver: Callable[..., object] = certify_scalar_transport,
    execute_bootstrap: bool = True,
    bootstrap_solver: Callable[..., object] | None = None,
) -> dict[str, object]:
    """Compute all V5 scalar endpoints without any common-pi classifier."""

    if holdout.get("schema") != "rq2_joint_deliverability_holdout_v3":
        raise ValueError("holdout schema drifted")
    if not isinstance(execute_bootstrap, bool):
        raise TypeError("execute_bootstrap must be boolean")
    expected_cell_ids = [cell.cell_id for cell in expand_registered_cells(design)]
    capacity_rows = capacity_frontier["cells"]
    holdout_rows = holdout["cells"]
    capacity_by_cell = {str(row["cell_id"]): row for row in capacity_rows}
    holdout_cells = {str(row["cell_id"]): row for row in holdout_rows}
    if [str(row["cell_id"]) for row in capacity_rows] != expected_cell_ids or [
        str(row["cell_id"]) for row in holdout_rows
    ] != expected_cell_ids:
        raise ValueError("identification cell order or inventory drifted")
    power_ids = sorted(
        (str(value) for value in holdout["finite_power_block_ids"]),
        key=lambda item: item.encode("utf-8"),
    )
    workload_ids = sorted(
        (str(value) for value in holdout["workload_block_ids"]),
        key=lambda item: item.encode("utf-8"),
    )
    e0_mass = float(holdout["E0_mass"])
    if not power_ids:
        if e0_mass < 1.0 - 1.0e-9:
            raise ValueError("finite holdout support is unexpectedly empty")
        return {
            "schema": "rq2_joint_deliverability_identification_v3",
            "status": "finite_service_identification_unresolved",
            "E0_mass": e0_mass,
            "transport_solver_calls": 0,
            "bootstrap": {
                "status": "unresolved",
                "reason": "empty_finite_support",
                "endpoint_solver_calls": 0,
                "intervals": None,
            },
            "cells": [
                {
                    "cell_id": cell_id,
                    "status": "finite_service_identification_unresolved",
                    "capacity_attribution": capacity_by_cell[cell_id][
                        "capacity_attribution"
                    ],
                    "transport_certificates": None,
                    "operational_labels": None,
                }
                for cell_id in expected_cell_ids
            ],
        }
    identification_rows = []
    transport_calls = 0
    bootstrap_matrices = {}
    for cell_id in expected_cell_ids:
        raw_cell = holdout_cells[cell_id]
        cell = dict(raw_cell)
        if cell["status"] != "resolved":
            identification_rows.append(
                {
                    "cell_id": cell_id,
                    "status": "not_evaluable",
                    "capacity_attribution": capacity_by_cell[cell_id][
                        "capacity_attribution"
                    ],
                    "transport_certificates": None,
                    "operational_labels": None,
                }
            )
            continue
        row_probabilities, column_probabilities, metric_matrices = (
            _holdout_metric_matrices(cell, power_ids, workload_ids)
        )
        bootstrap_matrices[cell_id] = metric_matrices
        certificates = {}
        intervals = {}
        for metric in REGISTERED_METRICS:
            matrix = [
                [
                    metric_matrices[metric][(power_id, workload_id)]
                    for workload_id in workload_ids
                ]
                for power_id in power_ids
            ]
            certificate = transport_solver(
                row_probabilities,
                column_probabilities,
                matrix,
                metric_name=metric,
            )
            transport_calls += 2
            certificates[metric] = json.loads(
                canonical_certificate_payload(certificate)
            )
            if (
                certificate.resolved
                and certificate.lower is not None
                and certificate.upper is not None
            ):
                intervals[metric] = CapacityInterval(
                    certificate.lower.value,
                    certificate.upper.value,
                )
        if set(intervals) != set(REGISTERED_METRICS):
            status = "transport_unresolved"
            labels = None
        else:
            status = "resolved"
            labels = operational_labels(
                {
                    metric: intervals[metric]
                    for metric in (
                        "B6_minus_correct_joint_service_failure",
                        "B6_minus_correct_total_service_shortfall",
                        "B6_minus_correct_cfe_shortfall",
                    )
                }
            )
        capacity_row = capacity_by_cell.get(cell_id)
        if capacity_row is None:
            raise ValueError("holdout cell is absent from capacity frontier")
        raw_arms = capacity_row["arms"]
        arm_statuses = {
            arm_id: str(raw_arms[arm_id]["status"]) for arm_id in FOUR_ARM_IDS
        }
        attribution = (
            finalize_operational_attribution(
                capacity_row["capacity_attribution"],
                arm_statuses,
                intervals,
            )
            if status == "resolved"
            else capacity_row["capacity_attribution"]
        )
        identification_rows.append(
            {
                "cell_id": cell_id,
                "status": status,
                "capacity_attribution": attribution,
                "transport_certificates": certificates,
                "operational_labels": labels,
            }
        )
    if execute_bootstrap:
        bootstrap_result = (
            _bootstrap_identification(
                design,
                holdout,
                bootstrap_matrices,
                endpoint_solver=bootstrap_solver or transport_solver,
            )
            if bootstrap_matrices
            else {
                "status": "not_evaluable_no_resolved_cells",
                "endpoint_solver_calls": 0,
                "intervals": None,
                "evaluated_cell_ids": [],
                "not_evaluable_cell_ids": sorted(
                    expected_cell_ids,
                    key=lambda item: item.encode("utf-8"),
                ),
            }
        )
    else:
        bootstrap_result = {
            "status": "not_executed",
            "endpoint_solver_calls": 0,
            "intervals": None,
        }
    return {
        "schema": "rq2_joint_deliverability_identification_v3",
        "status": (
            "resolved"
            if all(row["status"] == "resolved" for row in identification_rows)
            else "partially_unresolved"
        ),
        "E0_mass": e0_mass,
        "transport_solver_calls": transport_calls,
        "bootstrap": bootstrap_result,
        "cells": identification_rows,
    }


def build_report(
    *,
    capacity_frontier: Mapping[str, object],
    holdout: Mapping[str, object],
    identification: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Build the registered report schema without altering scientific states."""

    if capacity_frontier.get("schema") != (
        "rq2_joint_deliverability_capacity_frontier_v3"
    ):
        raise ValueError("capacity frontier schema drifted")
    if holdout.get("schema") != "rq2_joint_deliverability_holdout_v3":
        raise ValueError("holdout schema drifted")
    if identification.get("schema") != ("rq2_joint_deliverability_identification_v3"):
        raise ValueError("identification schema drifted")
    capacity_cells = {row["cell_id"] for row in capacity_frontier["cells"]}
    holdout_cells = {row["cell_id"] for row in holdout["cells"]}
    identification_cells = {row["cell_id"] for row in identification["cells"]}
    if (
        len(capacity_cells) != 46
        or not capacity_cells == holdout_cells == identification_cells
    ):
        raise ValueError("report cell inventories drifted")
    return {
        "schema": "rq2_joint_deliverability_report_v3",
        "registered_cell_count": 46,
        "capacity_resolved_cell_count": sum(
            bool(row["capacity_attribution"]["resolved"])
            for row in capacity_frontier["cells"]
        ),
        "holdout_resolved_cell_count": sum(
            row["status"] == "resolved" for row in holdout["cells"]
        ),
        "identification_status": identification["status"],
        "capacity_frontier_sha256": _canonical_sha256(capacity_frontier),
        "holdout_sha256": _canonical_sha256(holdout),
        "identification_sha256": _canonical_sha256(identification),
        "provenance_sha256": _canonical_sha256(provenance),
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }


def validate_runtime_config(config: Mapping[str, object]) -> dict[str, object]:
    """Validate immutable scientific authority and closed execution gates."""

    if config.get("schema") != "rq2_joint_deliverability_implementation_successor_v1":
        raise ValueError("implementation config schema drifted")
    if config.get("scientific_config") != (
        "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
    ):
        raise ValueError("implementation scientific config drifted")
    scope = config.get("scope")
    if (
        not isinstance(scope, Mapping)
        or scope.get("formal_execution") is not False
        or scope.get("formal_result") is not False
        or scope.get("paper_claim") is not False
        or scope.get("security_certification") is not False
    ):
        raise ValueError("implementation scope opened a forbidden effect")
    formal_scale = config.get("formal_scale")
    if (
        not isinstance(formal_scale, Mapping)
        or formal_scale.get("status") != "blocked_pending_streaming_execution_successor"
    ):
        raise ValueError("formal-scale execution blocker drifted")
    authority = config.get("scientific_authority")
    if not isinstance(authority, Mapping):
        raise TypeError("scientific authority must be a mapping")
    expected = {
        "sealed_v5_outer": {
            "path": V5_OUTER_RELATIVE,
            "sha256": V5_OUTER_SHA256,
        },
        "v5_pass_receipt": {
            "path": V5_REVIEW_RELATIVE,
            "sha256": V5_REVIEW_SHA256,
        },
    }
    if authority != expected:
        raise ValueError("scientific authority binding drifted")
    for item in expected.values():
        path = ROOT / item["path"]
        if not path.is_file() or path.is_symlink() or _sha256(path) != item["sha256"]:
            raise ValueError(f"scientific authority file drifted: {item['path']}")
    gates = config.get("gates")
    if not isinstance(gates, Mapping):
        raise TypeError("implementation gates must be a mapping")
    expected_false = {
        "independent_R3_review_passed",
        "upstream_grid_package_ready",
        "user_formal_run_authorized",
        "formal_execution_ready",
        "formal_result",
        "paper_claim",
    }
    if any(gates.get(key) is not False for key in expected_false):
        raise ValueError("implementation candidate opened a forbidden gate")
    return {
        "scientific_authority_valid": True,
        "formal_execution_ready": False,
    }


def run(*, validate_only: bool = True) -> dict[str, object]:
    """Validate the implementation candidate; formal execution remains closed."""

    config = _load_yaml(CONFIG)
    lifecycle = config.get("lifecycle")
    require_sealed = (
        isinstance(lifecycle, Mapping)
        and lifecycle.get("status") == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    )
    static_validation = validate_implementation_config(
        config,
        require_sealed=require_sealed,
    )
    authority = validate_runtime_config(config)
    scientific = _load_yaml(ROOT / config["scientific_config"])
    transport_runtime = validate_transport_runtime(
        scientific["holdout_identification"]["transport"]["software"],
        require_thread_environment=False,
    )
    tasks = planning_task_inventory(scientific)
    if not validate_only:
        raise RuntimeError(
            "formal execution is not authorized by implementation successor v1"
        )
    return {
        "schema": "rq2_joint_deliverability_implementation_validation_v1",
        **authority,
        "lifecycle": static_validation["lifecycle"],
        "registered_cell_count": 46,
        "arm_output_count": len(tasks),
        "unique_solver_task_count": len(
            {(str(task["arm_id"]), str(task["solve_key"])) for task in tasks}
        ),
        "transport_runtime": transport_runtime,
        "solver_calls": 0,
        "result_files_written": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    if not arguments.validate_only:
        parser.error("only --validate-only is permitted before a reviewed activation")
    print(json.dumps(run(validate_only=True), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
