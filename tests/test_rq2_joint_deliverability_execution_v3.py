from __future__ import annotations

import csv
import gzip
import hashlib
import inspect
import json
import os
import subprocess
import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from pyomo.environ import ConcreteModel, Constraint, Objective, Var
from pyomo.opt import SolverStatus, TerminationCondition

from experiments import run_rq2_joint_deliverability_execution_v3 as runner
from experiments import (
    run_rq2_joint_deliverability_implementation_v2 as implementation_runner,
)
from experiments import (
    validate_rq2_joint_deliverability_execution_v3 as validator,
)
from src.rq2_joint_deliverability_execution_v3 import core
from src.rq2_joint_deliverability_execution_v3.core import (
    EvidenceDrift,
    EvidenceStore,
    ExecutionBlocked,
    ExecutionEvidenceError,
    audit_registered_inputs,
    audit_split_inventory,
    bootstrap_draw_stream_sha256,
    canonical_json_bytes,
    capture_primal_evidence,
    commit_bootstrap_cell,
    commit_holdout_chunk,
    derive_static_authority,
    measure_synthetic_streaming_profile,
    replay_holdout_metric_matrices,
    replay_primal_evidence,
    run_identity,
    streaming_scale_projection,
    verify_flat_manifest,
)
from src.rq2_joint_deliverability_v2.evaluation import REGISTERED_METRICS
from src.rq2_joint_deliverability_v2.model import (
    FOUR_ARM_IDS,
    JointDeliverabilityPlanningInputs,
)
from src.rq2_joint_deliverability_v2.scenarios import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    PowerBlock,
    WorkloadBlock,
    expand_registered_cells,
)
from src.rq2_joint_deliverability_v2.solver_adapter import Rq2SolverSpec

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_joint_deliverability_execution_successor_v3.yaml"


def _config() -> dict:
    payload = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _requires_sealed(config: dict) -> bool:
    return config["lifecycle"]["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"


def _scientific() -> dict:
    path = ROOT / "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write_gzip_csv(
    path: Path,
    fieldnames: list[str],
    rows: list[dict[str, object]],
) -> None:
    with gzip.open(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _synthetic_split_package(
    path: Path,
    *,
    overlap_id: bool = False,
    overlap_source: bool = False,
    hourly_file: str = "hourly.csv.gz",
    source_field: str = "source_hour",
) -> None:
    path.mkdir()
    training_id = "shared" if overlap_id else "training"
    holdout_id = "shared" if overlap_id else "holdout"
    rows = []
    for split, block_id, base in (
        ("training", training_id, 0),
        ("holdout", holdout_id, 0 if overlap_source else 100),
    ):
        rows.extend(
            {
                "block_id": block_id,
                "split": split,
                "hour_offset": offset,
                source_field: base + offset,
                **(
                    {"workload_fraction": 1.0}
                    if source_field == "source_relative_hour"
                    else {}
                ),
            }
            for offset in range(24)
        )
    fieldnames = ["block_id", "split", "hour_offset", source_field]
    if source_field == "source_relative_hour":
        fieldnames.append("workload_fraction")
    _write_gzip_csv(
        path / hourly_file,
        fieldnames,
        rows,
    )
    for split, block_id in (
        ("training", training_id),
        ("holdout", holdout_id),
    ):
        _write_gzip_csv(
            path / f"{split}_marginal.csv.gz",
            ["id", "probability"],
            [{"id": block_id, "probability": 1.0}],
        )


def _synthetic_dispatched_grid_packages(
    root: Path,
) -> tuple[Path, Path, str, str, str]:
    power = root / "power"
    grid = root / "grid"
    checkpoints = root / "checkpoints"
    power.mkdir()
    grid.mkdir()
    checkpoints.mkdir()
    base_rows: list[dict[str, object]] = []
    for split, block_id, source_base in (
        ("training", "training", 0),
        ("holdout", "holdout", 100),
    ):
        base_rows.extend(
            {
                "block_id": block_id,
                "split": split,
                "block_probability": 1.0,
                "outage_seed": source_base,
                "hour_offset": offset,
                "source_hour": source_base + offset,
                "timestamp": f"2020-01-{1 + source_base // 100:02d}T{offset:02d}:00:00Z",
                "system_load_mw": 100.0 + offset,
                "cfe_call_fraction": 0.0,
                "active_event_id": f"{block_id}_event",
                "active_component_type": "branch",
                "active_component_uid": "A1",
            }
            for offset in range(24)
        )
    _write_gzip_csv(
        power / "power.csv.gz",
        list(core._GRID_BLOCK_FIELDS),
        base_rows,
    )
    for split, block_id in (("training", "training"), ("holdout", "holdout")):
        marginal = [{"id": block_id, "probability": 1.0}]
        _write_gzip_csv(
            power / f"{split}_marginal.csv.gz",
            ["id", "probability"],
            marginal,
        )
        _write_gzip_csv(
            grid / f"{split}_marginal.csv.gz",
            ["id", "probability"],
            marginal,
        )
    power_manifest = _manifest(power)
    dispatched_rows = [
        {
            **{field: str(row[field]) for field in core._GRID_BLOCK_FIELDS},
            "grid_need_mw": 25.0,
            "grid_need_fraction": 0.1,
            "dispatch_resolved": "true",
            "dispatch_proven_infeasible": "false",
            "dispatch_state": "finite_grid_need",
            "dispatch_objective_incumbent_mw": 25.0,
            "dispatch_lower_bound_mw": 25.0,
            "dispatch_upper_bound_mw": 25.0,
            "dispatch_absolute_gap_mw": 0.0,
            "dispatch_relative_gap": 0.0,
            "dispatch_gap_tolerance_mw": 2.5e-5,
            "dispatch_model_variables": 1,
            "dispatch_model_constraints": 1,
            "zero_dc_confirmation_termination_condition": "",
            "zero_dc_confirmation_solver_status": "",
            "zero_dc_confirmation_lower_bound_mw": "",
            "zero_dc_confirmation_upper_bound_mw": "",
            "zero_dc_confirmation_absolute_gap_mw": "",
            "zero_dc_confirmation_model_variables": "",
            "zero_dc_confirmation_model_constraints": "",
            "dispatch_termination_condition": "optimal",
            "dispatch_solver_status": "ok",
            "maximum_constraint_violation": 0.0,
        }
        for row in base_rows
    ]
    _write_gzip_csv(
        grid / "dispatched_power_system_blocks.csv.gz",
        list(core._GRID_OUTPUT_FIELDS),
        dispatched_rows,
    )
    _write_gzip_csv(
        grid / "block_status.csv.gz",
        [
            "block_id",
            "split",
            "all_hours_resolved",
            "baseline_accepted",
            "exogenous_grid_infeasibility_hour_count",
        ],
        [
            {
                "block_id": block_id,
                "split": split,
                "all_hours_resolved": True,
                "baseline_accepted": True,
                "exogenous_grid_infeasibility_hour_count": 0,
            }
            for split, block_id in (
                ("training", "training"),
                ("holdout", "holdout"),
            )
        ],
    )
    producer = root / "producer.py"
    module = root / "module.py"
    producer.write_text("# synthetic producer\n", encoding="utf-8")
    module.write_text("# synthetic module\n", encoding="utf-8")
    contract_path = root / "provenance-contract.yaml"
    contract = {
        "schema": "rq2_public_pipeline_provenance_contract_v3",
        "stages": {
            "grid_need_dispatch_v4": {
                "runner": {
                    "path": "producer.py",
                    "sha256": core.sha256_file(producer),
                },
                "modules": {
                    "synthetic": {
                        "path": "module.py",
                        "sha256": core.sha256_file(module),
                    }
                },
                "software": {"gurobipy": "13.0.2"},
            }
        },
    }
    contract_path.write_text(
        yaml.safe_dump(contract, sort_keys=False),
        encoding="utf-8",
    )
    grid_config = {
        "input": {
            "power_system_blocks_manifest_sha256": power_manifest,
        },
        "grid_source": {"manifest_sha256": "3" * 64},
        "model": {
            "dc_bus": 108,
            "dc_reference_demand_mw": 250.0,
            "time_step_hours": 1.0,
            "normal_baseline": "free_boundary_24h_normal_state_SCUC",
            "outage_response": "fixed_commitment_and_normal_dispatch_hourly_corrective_LP",
            "branch_rating": "continuous",
            "generator_response_limit": "published_hourly_ramp",
            "load_shedding_allowed": False,
            "full_N_minus_one": False,
            "AC_security": False,
        },
        "solver": {
            "name": "gurobi",
            "expected_package_version": "13.0.2",
            "threads": 4,
            "mip_relative_gap": 1.0e-6,
            "feasibility_tolerance": 1.0e-6,
            "optimality_tolerance": 1.0e-6,
            "integer_feasibility_tolerance": 1.0e-6,
            "random_seed": 0,
            "time_limit_seconds": None,
            "tolerance_mw": 1.0e-6,
            "tee": False,
        },
        "provenance": {
            "contract_path": "provenance-contract.yaml",
            "contract_sha256": core.sha256_file(contract_path),
        },
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
            "require_all_blocks_resolved": True,
            "checkpoint_directory": "checkpoints",
            "predecessor_HiGHS_checkpoint_reuse_allowed": False,
        },
        "output": {"schema": "rts_gmlc_public_grid_need_dispatch_v4"},
        "activation_authority": {
            "activation_path": "activation.yaml",
            "activation_sha256": "4" * 64,
            "post_result_review_path": "pilot-review.yaml",
            "post_result_review_sha256": "5" * 64,
            "pilot_result_manifest_sha256": "6" * 64,
            "grid_activation_review_path": "grid-review.yaml",
            "grid_activation_review_sha256": "7" * 64,
        },
    }
    (grid / "config.yaml").write_text(
        yaml.safe_dump(grid_config, sort_keys=False),
        encoding="utf-8",
    )
    grid_config_sha256 = core.sha256_file(grid / "config.yaml")
    stage_base = {
        "schema": "rq2_public_stage_provenance_v3",
        "stage": "grid_need_dispatch_v4",
        "config_sha256": grid_config_sha256,
        "contract_path": "provenance-contract.yaml",
        "contract_sha256": core.sha256_file(contract_path),
        "implementation": {
            "runner_sha256": core.sha256_file(producer),
            "module_sha256": {"synthetic": core.sha256_file(module)},
        },
        "software": {"gurobipy": "13.0.2"},
        "inputs": {
            "power_system_blocks_manifest_sha256": power_manifest,
            "rts_gmlc_source_manifest_sha256": "3" * 64,
        },
    }
    checkpoint_inventory = {}
    for split, block_id in (("training", "training"), ("holdout", "holdout")):
        block_rows = [
            row
            for row in base_rows
            if row["split"] == split and row["block_id"] == block_id
        ]
        output_rows = [
            row
            for row in dispatched_rows
            if row["split"] == split and row["block_id"] == block_id
        ]
        checkpoint_path = checkpoints / f"{block_id}.json"
        checkpoint_path.write_bytes(
            canonical_json_bytes(
                _synthetic_grid_checkpoint(
                    block_id=block_id,
                    split=split,
                    base_rows=block_rows,
                    output_rows=output_rows,
                    stage_base_sha256=core._provenance_sha256(stage_base),
                )
            )
        )
        checkpoint_inventory[block_id] = core.sha256_file(checkpoint_path)
    (grid / "checkpoint_inventory.json").write_bytes(
        canonical_json_bytes(checkpoint_inventory)
    )
    provenance = {
        "base": stage_base,
        "checkpoint_inventory": checkpoint_inventory,
        "checkpoint_inventory_sha256": core.canonical_sha256(checkpoint_inventory),
    }
    (grid / "provenance.json").write_bytes(canonical_json_bytes(provenance))
    summary = {
        "schema": "rts_gmlc_public_grid_need_dispatch_v4",
        "config_sha256": grid_config_sha256,
        "stage_base_provenance_sha256": core._provenance_sha256(stage_base),
        "input_manifest_sha256": power_manifest,
        "provenance_sha256": core.sha256_file(grid / "provenance.json"),
        "checkpoint_inventory_sha256": core.canonical_sha256(checkpoint_inventory),
        "block_count": 2,
        "training_block_count": 1,
        "holdout_block_count": 1,
        "all_blocks_resolved": True,
        "finite_grid_need_scope": core._GRID_NEED_SCOPE,
        "exogenous_grid_infeasibility_block_count": 0,
        "exogenous_grid_infeasibility_hour_count": 0,
        "exogenous_grid_infeasibility_has_finite_grid_need": False,
        "solver_name": "gurobi",
        "normal_scuc_model_scales": [[2, 3]],
        "corrective_lp_model_scales": [[1, 1]],
        "formal_execution_authorized": True,
        "empirical_outage_probability_claimed": False,
        "full_N_minus_one": False,
        "AC_security": False,
        "security_certified": False,
    }
    (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    return power, grid, power_manifest, _manifest(grid), grid_config_sha256


def _manifest(path: Path) -> str:
    payload = {
        child.name: hashlib.sha256(child.read_bytes()).hexdigest()
        for child in path.iterdir()
        if child.is_file() and child.name != "SHA256SUMS.json"
    }
    manifest = path / "SHA256SUMS.json"
    manifest.write_bytes(canonical_json_bytes(payload))
    return hashlib.sha256(manifest.read_bytes()).hexdigest()


def _synthetic_event_baseline_audit() -> dict[str, object]:
    return {
        "accepted": True,
        "termination_condition": "optimal",
        "solver_status": "ok",
        "solver_message": "synthetic optimal",
        "objective_usd": 100.0,
        "lower_bound_usd": 100.0,
        "upper_bound_usd": 100.0,
        "absolute_gap_usd": 0.0,
        "relative_gap": 0.0,
        "gap_tolerance_usd": max(1.0e-6, 1.0e-6 * 100.0),
        "maximum_constraint_violation": 0.0,
        "maximum_integrality_violation": 0.0,
        "solver_threads": 4,
        "configured_mip_relative_gap": 1.0e-6,
        "model_variables": 2,
        "model_constraints": 3,
        "solver_name": "gurobi",
        "solver_options": {
            "MIPGap": 1.0e-6,
            "MIPGapAbs": 0.0,
            "Seed": 0,
            "Threads": 4,
            "FeasibilityTol": 1.0e-6,
            "OptimalityTol": 1.0e-6,
            "IntFeasTol": 1.0e-6,
        },
    }


def _synthetic_grid_checkpoint(
    *,
    block_id: str,
    split: str,
    base_rows: list[dict[str, object]],
    output_rows: list[dict[str, object]],
    stage_base_sha256: str,
) -> dict[str, object]:
    outcomes = []
    for base_row in base_rows:
        outcomes.append(
            {
                "state": FINITE_GRID_NEED,
                "resolved_for_pipeline": True,
                "primary": {
                    "source_hour": int(base_row["source_hour"]),
                    "event_id": base_row["active_event_id"],
                    "component_type": base_row["active_component_type"],
                    "component_uid": base_row["active_component_uid"],
                    "resolved": True,
                    "proven_infeasible": False,
                    "grid_need_mw": 25.0,
                    "termination_condition": "optimal",
                    "solver_status": "ok",
                    "maximum_constraint_violation": 0.0,
                },
                "primary_certificate": {
                    "objective_incumbent_mw": 25.0,
                    "lower_bound_mw": 25.0,
                    "upper_bound_mw": 25.0,
                    "absolute_gap_mw": 0.0,
                    "relative_gap": 0.0,
                    "gap_tolerance_mw": 2.5e-5,
                    "model_variables": 1,
                    "model_constraints": 1,
                },
                "zero_dc_confirmation": None,
                "zero_dc_confirmation_certificate": None,
                "solver_name": "gurobi",
                "solver_options": {
                    "MIPGap": 1.0e-6,
                    "MIPGapAbs": 0.0,
                    "Seed": 0,
                    "Threads": 4,
                    "FeasibilityTol": 1.0e-6,
                    "OptimalityTol": 1.0e-6,
                    "IntFeasTol": 1.0e-6,
                },
            }
        )
    return {
        "schema": "rts_gmlc_public_grid_need_block_checkpoint_v4",
        "stage_base_provenance_sha256": stage_base_sha256,
        "block_id": block_id,
        "split": split,
        "baseline_audit": _synthetic_event_baseline_audit(),
        "all_hours_resolved": True,
        "exogenous_grid_infeasibility_hour_count": 0,
        "outcomes": outcomes,
        "rows": output_rows,
    }


def _rebind_synthetic_checkpoint_inventory(root: Path, grid: Path) -> str:
    checkpoints = root / "checkpoints"
    inventory = {
        path.stem: core.sha256_file(path)
        for path in sorted(checkpoints.glob("*.json"), key=lambda item: item.name)
    }
    (grid / "checkpoint_inventory.json").write_bytes(canonical_json_bytes(inventory))
    provenance = json.loads((grid / "provenance.json").read_text(encoding="utf-8"))
    provenance["checkpoint_inventory"] = inventory
    provenance["checkpoint_inventory_sha256"] = core.canonical_sha256(inventory)
    (grid / "provenance.json").write_bytes(canonical_json_bytes(provenance))
    summary = json.loads((grid / "summary.json").read_text(encoding="utf-8"))
    summary["checkpoint_inventory_sha256"] = core.canonical_sha256(inventory)
    summary["provenance_sha256"] = core.sha256_file(grid / "provenance.json")
    (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    return _manifest(grid)


def _set_nested_value(
    payload: object,
    path: tuple[str | int, ...],
    value: object,
) -> None:
    target = payload
    for component in path[:-1]:
        valid = (
            isinstance(component, int)
            and isinstance(target, list)
            or isinstance(component, str)
            and isinstance(target, dict)
        )
        if not valid:
            raise TypeError("synthetic checkpoint fault path is invalid")
        target = target[component]
    final = path[-1]
    valid = (
        isinstance(final, int)
        and isinstance(target, list)
        or isinstance(final, str)
        and isinstance(target, dict)
    )
    if not valid:
        raise TypeError("synthetic checkpoint fault path is invalid")
    target[final] = value


def _synthetic_e0_audit_case(
    root: Path,
    *,
    row_fault: tuple[str, object] | None = None,
    checkpoint_fault: tuple[tuple[str | int, ...], object] | None = None,
) -> tuple[dict[str, object], str]:
    (
        _power,
        grid,
        power_manifest,
        _grid_manifest,
        grid_config_sha256,
    ) = _synthetic_dispatched_grid_packages(root)
    workload = root / "workload"
    _synthetic_split_package(
        workload,
        hourly_file="workload_blocks.csv.gz",
        source_field="source_relative_hour",
    )
    workload_manifest = _manifest(workload)
    hourly_path = grid / "dispatched_power_system_blocks.csv.gz"
    with gzip.open(hourly_path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1].update(
        {
            "grid_need_mw": "",
            "grid_need_fraction": "",
            "dispatch_resolved": "false",
            "dispatch_proven_infeasible": "true",
            "dispatch_state": EXOGENOUS_GRID_INFEASIBILITY,
            "dispatch_objective_incumbent_mw": "",
            "dispatch_lower_bound_mw": "",
            "dispatch_upper_bound_mw": "",
            "dispatch_absolute_gap_mw": "",
            "dispatch_relative_gap": "",
            "dispatch_gap_tolerance_mw": "",
            "zero_dc_confirmation_termination_condition": "infeasible",
            "zero_dc_confirmation_solver_status": "warning",
            "zero_dc_confirmation_lower_bound_mw": "",
            "zero_dc_confirmation_upper_bound_mw": "",
            "zero_dc_confirmation_absolute_gap_mw": "",
            "zero_dc_confirmation_model_variables": "1",
            "zero_dc_confirmation_model_constraints": "1",
            "dispatch_termination_condition": "infeasible",
            "dispatch_solver_status": "warning",
            "maximum_constraint_violation": "",
        }
    )
    if row_fault is not None:
        field, value = row_fault
        rows[1][field] = value
    _write_gzip_csv(hourly_path, list(core._GRID_OUTPUT_FIELDS), rows)
    checkpoint_path = root / "checkpoints/training.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["rows"][1].update(
        {
            "grid_need_mw": "",
            "grid_need_fraction": "",
            "dispatch_resolved": "false",
            "dispatch_proven_infeasible": "true",
            "dispatch_state": EXOGENOUS_GRID_INFEASIBILITY,
            "dispatch_objective_incumbent_mw": "",
            "dispatch_lower_bound_mw": "",
            "dispatch_upper_bound_mw": "",
            "dispatch_absolute_gap_mw": "",
            "dispatch_relative_gap": "",
            "dispatch_gap_tolerance_mw": "",
            "zero_dc_confirmation_termination_condition": "infeasible",
            "zero_dc_confirmation_solver_status": "warning",
            "zero_dc_confirmation_lower_bound_mw": "",
            "zero_dc_confirmation_upper_bound_mw": "",
            "zero_dc_confirmation_absolute_gap_mw": "",
            "zero_dc_confirmation_model_variables": 1,
            "zero_dc_confirmation_model_constraints": 1,
            "dispatch_termination_condition": "infeasible",
            "dispatch_solver_status": "warning",
            "maximum_constraint_violation": "",
        }
    )
    primary = checkpoint["outcomes"][1]["primary"]
    primary.update(
        {
            "resolved": False,
            "proven_infeasible": True,
            "grid_need_mw": None,
            "termination_condition": "infeasible",
            "solver_status": "warning",
            "maximum_constraint_violation": None,
        }
    )
    checkpoint["outcomes"][1]["state"] = EXOGENOUS_GRID_INFEASIBILITY
    checkpoint["outcomes"][1]["primary_certificate"] = {
        "objective_incumbent_mw": None,
        "lower_bound_mw": None,
        "upper_bound_mw": None,
        "absolute_gap_mw": None,
        "relative_gap": None,
        "gap_tolerance_mw": None,
        "model_variables": 1,
        "model_constraints": 1,
    }
    checkpoint["outcomes"][1]["zero_dc_confirmation"] = dict(primary)
    checkpoint["outcomes"][1]["zero_dc_confirmation_certificate"] = dict(
        checkpoint["outcomes"][1]["primary_certificate"]
    )
    checkpoint["exogenous_grid_infeasibility_hour_count"] = 1
    if checkpoint_fault is not None:
        path, value = checkpoint_fault
        _set_nested_value(checkpoint, path, value)
    checkpoint_path.write_bytes(canonical_json_bytes(checkpoint))
    with gzip.open(
        grid / "block_status.csv.gz",
        "rt",
        encoding="utf-8",
        newline="",
    ) as handle:
        statuses = list(csv.DictReader(handle))
    statuses[0]["exogenous_grid_infeasibility_hour_count"] = "1"
    _write_gzip_csv(grid / "block_status.csv.gz", list(statuses[0]), statuses)
    summary = json.loads((grid / "summary.json").read_text(encoding="utf-8"))
    summary["exogenous_grid_infeasibility_block_count"] = 1
    summary["exogenous_grid_infeasibility_hour_count"] = 1
    (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    grid_manifest = _rebind_synthetic_checkpoint_inventory(root, grid)
    config: dict[str, object] = {
        "registered_inputs": {
            "power_base": {
                "package": "power",
                "manifest_path": "power/SHA256SUMS.json",
                "manifest_sha256": power_manifest,
                "hourly_file": "power.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "workload": {
                "package": "workload",
                "manifest_path": "workload/SHA256SUMS.json",
                "manifest_sha256": workload_manifest,
                "hourly_file": "workload_blocks.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "dispatched_grid": {
                "package": "grid",
                "manifest_path": "grid/SHA256SUMS.json",
                "manifest_sha256": grid_manifest,
                "hourly_file": "dispatched_power_system_blocks.csv.gz",
                "config_sha256": grid_config_sha256,
                "dc_reference_demand_mw": 250.0,
                "ready": False,
            },
        }
    }
    return config, grid_manifest


def _zero_policy() -> dict[str, object]:
    return {
        "maximum_recovery_power": 1.0,
        "recovery_efficiency": 1.0,
        "maximum_event_duration_hours": 4.0,
        "maximum_event_count": 2,
        "minimum_recovery_hours": 1.0,
        "normalized_energy_budget": 1.0,
        "normalized_debt_limit": 1.0,
        "terminal_recovery_debt_limit": 0.0,
        "time_step_hours": 1.0,
        "minimum_event_power": 1.0e-6,
        "curtailment_ramp_per_hour": 1.0,
        "response_time_hours": 1.0,
        "service_shortfall_tolerance": 1.0e-6,
    }


def _zero_outcome() -> dict[str, object]:
    return core.execute_holdout_policy(
        committed_capacity=1.0,
        grid_request=(0.0,) * 24,
        cfe_request=(0.0,) * 24,
        available_flexibility=(1.0,) * 24,
        connected_demand=(1.0,) * 24,
        current_recovery_headroom=(1.0,) * 24,
        **_zero_policy(),
    )


def _model(*, value: float = 0.5, objective_uses_x: bool = True) -> ConcreteModel:
    model = ConcreteModel()
    model.x = Var(bounds=(0.0, 1.0))
    model.x.set_value(value)
    model.minimum = Constraint(expr=model.x >= 0.2)
    model.objective = Objective(expr=model.x if objective_uses_x else 0.0)
    return model


def _planning_inputs() -> JointDeliverabilityPlanningInputs:
    return JointDeliverabilityPlanningInputs(
        scenarios=(),
        time_step_hours=1.0,
        maximum_flexibility_budget=1.0,
        minimum_event_power=1.0e-6,
        response_time_hours=1.0,
        curtailment_ramp_per_hour=1.0,
        minimum_recovery_hours=1.0,
        recovery_efficiency=1.0,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_recovery_headroom=1.0,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
        terminal_recovery_debt_limit=0.0,
        service_shortfall_tolerance=1.0e-6,
    )


def _checkpoint_endpoint(
    metric: str,
    lower: float,
    upper: float,
) -> dict[str, object]:
    return {
        "lower": lower,
        "upper": upper,
        "certificate": {
            "schema": "rq2_joint_deliverability_transport_certificate_v3",
            "metric": metric,
            "resolved": True,
            "lower": {"value": lower.hex()},
            "upper": {"value": upper.hex()},
        },
    }


def _commit_minimal_holdout_source(
    store: EvidenceStore,
    *,
    cell_id: str,
    power_id: str,
) -> None:
    store.commit(
        "holdout",
        f"{cell_id}__{power_id}",
        {
            "schema": "synthetic_holdout_source_v1",
            "cell_id": cell_id,
            "power_block_id": power_id,
        },
    )


def _synthetic_unresolved_capacity_frontier() -> dict[str, object]:
    return {
        "schema": "rq2_joint_deliverability_capacity_frontier_v3",
        "cell_count": 46,
        "arm_output_count": 184,
        "representative_solver_calls": 0,
        "full_support_fallback_solver_calls": 0,
        "total_solver_calls": 0,
        "cells": [
            {
                "cell_id": cell.cell_id,
                "family": cell.family,
                "parameters": asdict(cell),
                "arms": {
                    arm_id: {
                        "arm_id": arm_id,
                        "status": "unresolved",
                        "planning_input_sha256": core.canonical_sha256(
                            {"cell_id": cell.cell_id, "arm_id": arm_id}
                        ),
                        "solver_certificate": None,
                        "full_support_audit": {"fallback_certificates": []},
                    }
                    for arm_id in FOUR_ARM_IDS
                },
            }
            for cell in expand_registered_cells(_scientific())
        ],
    }


def _commit_synthetic_planning_authority(
    store: EvidenceStore,
    *,
    input_audit: dict[str, object],
    capacity_frontier: dict[str, object],
) -> dict[str, object]:
    input_audit_pointer = store.commit(
        "input_audit",
        "registered",
        input_audit,
    )
    packages = input_audit["packages"]
    capacity_pointer = store.commit(
        "capacity_frontier",
        "registered",
        capacity_frontier,
    )
    return store.commit(
        "planning_index",
        "capacity_frontier",
        {
            "schema": "rq2_joint_deliverability_planning_evidence_index_v1",
            "capacity_frontier_sha256": core.canonical_sha256(capacity_frontier),
            "capacity_frontier_object_sha256": capacity_pointer["object_sha256"],
            "scientific_design_sha256": core.canonical_sha256(_scientific()),
            "registered_input_audit_sha256": core.canonical_sha256(input_audit),
            "input_audit_object_sha256": input_audit_pointer["object_sha256"],
            "training_power_inventory_sha256": packages["dispatched_grid"][
                "training_block_inventory_sha256"
            ],
            "training_workload_inventory_sha256": packages["workload"][
                "training_block_inventory_sha256"
            ],
            "solve_record_count": 0,
            "records": [],
        },
    )


def _commit_bootstrap_holdout_summary(
    store: EvidenceStore,
    *,
    input_audit: dict[str, object],
    power_blocks: tuple[PowerBlock, ...],
    workload_blocks: tuple[WorkloadBlock, ...],
    status: str,
    input_audit_object_sha256: str | None = None,
    planning_index_object_sha256: str | None = None,
    status_overrides: dict[str, str] | None = None,
) -> None:
    finite_ids = sorted(
        (block.block_id for block in power_blocks if block.state == FINITE_GRID_NEED),
        key=str.encode,
    )
    cells = expand_registered_cells(_scientific())
    statuses = {
        cell.cell_id: (
            status_overrides.get(cell.cell_id, status)
            if status_overrides is not None
            else status
        )
        for cell in cells
    }
    capacity_frontier = _synthetic_unresolved_capacity_frontier()
    planning_pointer = _commit_synthetic_planning_authority(
        store,
        input_audit=input_audit,
        capacity_frontier=capacity_frontier,
    )
    store.commit(
        "holdout_summary",
        "registered",
        {
            "schema": "rq2_joint_deliverability_holdout_stream_v1",
            "E0_mass": sum(
                block.probability
                for block in power_blocks
                if block.state == EXOGENOUS_GRID_INFEASIBILITY
            ),
            "E0_power_block_ids": sorted(
                (
                    block.block_id
                    for block in power_blocks
                    if block.state == EXOGENOUS_GRID_INFEASIBILITY
                ),
                key=str.encode,
            ),
            "finite_power_block_ids": finite_ids,
            "workload_block_ids": sorted(
                (block.block_id for block in workload_blocks),
                key=str.encode,
            ),
            "trajectory_chunk_count": sum(
                len(finite_ids) if cell_status == "resolved" else 0
                for cell_status in statuses.values()
            ),
            "trajectory_chunk_stream_sha256": (
                hashlib.sha256().hexdigest()
                if all(cell_status != "resolved" for cell_status in statuses.values())
                else "0" * 64
            ),
            "cells": [
                {
                    "cell_id": cell.cell_id,
                    "status": statuses[cell.cell_id],
                    "chunk_count": (
                        len(finite_ids) if statuses[cell.cell_id] == "resolved" else 0
                    ),
                }
                for cell in cells
            ],
            "registered_input_audit_sha256": core.canonical_sha256(input_audit),
            "input_audit_object_sha256": (
                core.canonical_sha256(input_audit)
                if input_audit_object_sha256 is None
                else input_audit_object_sha256
            ),
            "planning_index_object_sha256": (
                planning_pointer["object_sha256"]
                if planning_index_object_sha256 is None
                else planning_index_object_sha256
            ),
            "capacity_frontier_sha256": core.canonical_sha256(capacity_frontier),
            "scientific_design_sha256": core.canonical_sha256(_scientific()),
        },
    )


def test_static_candidate_and_validate_only_are_closed() -> None:
    config = _config()
    static = validator.validate(config, require_sealed=_requires_sealed(config))
    draft_config = deepcopy(config)
    draft_config["lifecycle"] = {
        "status": "DRAFT_NONAUTHORITATIVE",
        "pre_seal_audit_complete": False,
        "sealed_ready_for_independent_review": False,
    }
    draft_config["gates"]["execution_candidate_complete"] = False
    draft_config["gates"]["pre_seal_audit_complete"] = False
    draft = validator.validate(draft_config, require_sealed=False)
    report = runner.run(validate_only=True)

    assert static["valid"] is True
    assert draft["lifecycle"] == "DRAFT_NONAUTHORITATIVE"
    assert report["formal_execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["formal_result_files_written"] == 0
    assert report["input_audit"]["registered_inputs_ready"] is False
    assert report["input_audit"]["packages"]["dispatched_grid"]["status"] == (
        "blocked_missing_dispatched_grid_package"
    )
    with pytest.raises(RuntimeError, match="activation wrapper"):
        runner.run(validate_only=False)


@pytest.mark.parametrize(
    ("section", "key", "replacement"),
    (
        ("execution_outer", "sha256", "0" * 64),
        ("official_review", "sha256", "1" * 64),
        ("official_review", "verdict", "PASS"),
        ("official_review", "major_findings", 0),
        ("superseded_review", "sha256", "2" * 64),
        ("superseded_review", "current_authority", True),
        ("fixed_pass_authority", "required_absent", False),
    ),
)
def test_validator_binds_v2_escalation_predecessor(
    section: str,
    key: str,
    replacement: object,
) -> None:
    config = _config()
    config["predecessor_authority"][section][key] = replacement
    with pytest.raises(ValueError, match="predecessor authority binding drifted"):
        validator.validate(config, require_sealed=_requires_sealed(config))


@pytest.mark.parametrize(
    ("exists_at_path", "symlink_at_path"),
    ((True, False), (False, True)),
    ids=("regular_entry", "dangling_symlink"),
)
def test_validator_rejects_restored_v2_fixed_pass_authority(
    monkeypatch: pytest.MonkeyPatch,
    exists_at_path: bool,
    symlink_at_path: bool,
) -> None:
    config = _config()
    fixed_path = (
        validator.ROOT / config["predecessor_authority"]["fixed_pass_authority"]["path"]
    )
    original_exists = Path.exists
    original_is_symlink = Path.is_symlink

    def exists(path: Path) -> bool:
        return exists_at_path if path == fixed_path else original_exists(path)

    def is_symlink(path: Path) -> bool:
        return symlink_at_path if path == fixed_path else original_is_symlink(path)

    monkeypatch.setattr(Path, "exists", exists)
    monkeypatch.setattr(Path, "is_symlink", is_symlink)
    with pytest.raises(
        ValueError,
        match="predecessor fixed PASS authority is not absent",
    ):
        validator.validate(config, require_sealed=_requires_sealed(config))


def test_public_stage_entries_are_closed_without_live_authority_assumptions(
    tmp_path: Path,
) -> None:
    for entry in (
        core.execute_planning_stage_with_evidence,
        core.stream_holdout_stage,
        core.execute_bootstrap_resumable,
        core.aggregate_bootstrap_checkpoints,
    ):
        parameters = inspect.signature(entry).parameters
        assert "root" not in parameters
        assert "execution_outer_sha256" not in parameters
        assert "activated_grid_manifest_sha256" not in parameters
        assert "registered_input_audit" not in parameters
        assert "training_power_blocks" not in parameters
        assert "holdout_power_blocks" not in parameters
        assert "design" not in parameters
        assert "endpoint_solver" not in parameters
        assert "solver_specification" not in parameters
    assert "solve_arm_with_native_evidence" not in core.__all__
    assert "EvidenceSolvingCallback" not in core.__all__
    assert "commit_planning_evidence_index" not in core.__all__

    with pytest.raises(EvidenceDrift, match="repository root"):
        core._load_live_registered_inputs(tmp_path)
    with pytest.raises(TypeError, match="root"):
        core.execute_planning_stage_with_evidence(  # type: ignore[call-arg]
            root=tmp_path,
            store=EvidenceStore(
                tmp_path / "caller-root",
                run_identity_sha256="1" * 64,
            ),
        )
    with pytest.raises(TypeError, match="execution_outer_sha256"):
        core.execute_planning_stage_with_evidence(  # type: ignore[call-arg]
            execution_outer_sha256="0" * 64,
            store=EvidenceStore(
                tmp_path / "caller-authority",
                run_identity_sha256="1" * 64,
            ),
        )
    closed_store = EvidenceStore(
        tmp_path / "closed-public-stage",
        run_identity_sha256="2" * 64,
    )
    for call in (
        lambda: core.execute_planning_stage_with_evidence(store=closed_store),
        lambda: core.stream_holdout_stage(
            capacity_frontier={},
            store=closed_store,
        ),
        lambda: core.execute_bootstrap_resumable(store=closed_store),
        lambda: core.aggregate_bootstrap_checkpoints(closed_store),
    ):
        with pytest.raises(ExecutionBlocked, match="fresh-process activation"):
            call()


def test_closed_public_planning_stage_precedes_authority_and_callback(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authority_calls = 0
    callback_constructions = 0

    def reject_authority(*_args: object, **_kwargs: object) -> object:
        nonlocal authority_calls
        authority_calls += 1
        raise EvidenceDrift("injected authority rejection")

    class ForbiddenCallback:
        def __init__(self, _store: EvidenceStore) -> None:
            nonlocal callback_constructions
            callback_constructions += 1

    monkeypatch.setattr(core, "_load_live_registered_inputs", reject_authority)
    monkeypatch.setattr(core, "_EvidenceSolvingCallback", ForbiddenCallback)
    with pytest.raises(ExecutionBlocked, match="fresh-process activation"):
        core.execute_planning_stage_with_evidence(
            store=EvidenceStore(
                tmp_path / "evidence",
                run_identity_sha256="1" * 64,
            ),
        )
    assert authority_calls == 0
    assert callback_constructions == 0


def test_planning_same_stage_extra_is_rejected_by_private_prestate_gate(
    tmp_path: Path,
) -> None:
    run_sha256 = "2" * 64
    store = EvidenceStore(
        tmp_path / "evidence",
        run_identity_sha256=run_sha256,
    )
    store.commit("solve", "forged", {"value": 1})

    with pytest.raises(EvidenceDrift, match="planning evidence store is not empty"):
        core._validate_planning_store_prestate(store)
    with pytest.raises(EvidenceDrift, match="planning evidence store is not empty"):
        core._execute_planning_stage_with_evidence_from_audit(
            design={},
            registered_input_audit={},
            training_power_blocks=(),
            training_workload_blocks=(),
            store=store,
        )


def test_private_planning_orchestration_orders_gate_solver_commit_and_poststate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_store = EvidenceStore(
        tmp_path / "evidence",
        run_identity_sha256="3" * 64,
    )
    expected_design = {"solver_contract": {"sealed": True}}
    expected_audit = {"audit": True}
    training_power = (object(),)
    training_workload = (object(),)
    registered_power = (object(),)
    registered_workload = (object(),)
    specification = object()
    expected_frontier = {"frontier": True}
    planning_index_pointer = {"object_sha256": "4" * 64}
    planning_authority = {
        "input_audit_object_sha256": "5" * 64,
        "planning_index_object_sha256": "4" * 64,
    }
    events: list[str] = []

    def validate_prestate(current_store: EvidenceStore) -> dict[str, object]:
        assert current_store is expected_store
        events.append("prestate")
        return {}

    def registered_support(
        audit: object,
        power: object,
        workload: object,
    ) -> tuple[tuple[object, ...], tuple[object, ...]]:
        assert audit is expected_audit
        assert power is training_power
        assert workload is training_workload
        events.append("registered_support")
        return registered_power, registered_workload

    def parse_solver_contract(raw: object) -> object:
        assert raw is expected_design["solver_contract"]
        events.append("solver_contract")
        return specification

    class RecordingCallback:
        def __init__(self, current_store: EvidenceStore) -> None:
            assert current_store is expected_store
            events.append("callback")
            self.records = [{"record": True}]

    def execute_capacity(
        current_design: object,
        *,
        training_power_blocks: object,
        training_workload_blocks: object,
        solver_specification: object,
        solve_callback: object,
    ) -> dict[str, object]:
        assert current_design == expected_design
        assert training_power_blocks is registered_power
        assert training_workload_blocks is registered_workload
        assert solver_specification is specification
        assert isinstance(solve_callback, RecordingCallback)
        events.append("capacity")
        return expected_frontier

    def commit_index(
        current_design: object,
        *,
        capacity_frontier: object,
        solve_records: object,
        registered_input_audit: object,
        training_power_blocks: object,
        training_workload_blocks: object,
        solver_specification: object,
        store: object,
    ) -> dict[str, object]:
        assert current_design == expected_design
        assert capacity_frontier is expected_frontier
        assert solve_records == [{"record": True}]
        assert registered_input_audit is expected_audit
        assert training_power_blocks is registered_power
        assert training_workload_blocks is registered_workload
        assert solver_specification is specification
        assert store is expected_store
        events.append("index")
        return planning_index_pointer

    def validate_poststate(
        current_store: EvidenceStore,
        *,
        allowed_stages: set[str],
        allowed_blob_namespaces: set[str],
    ) -> dict[str, object]:
        assert current_store is expected_store
        assert allowed_stages == core._PLANNING_EVIDENCE_STAGES
        assert allowed_blob_namespaces == {"solver_log"}
        events.append("inventory")
        return {}

    def replay_poststate(
        current_store: EvidenceStore,
        *,
        design: object,
        registered_input_audit: object,
        training_power_blocks: object,
        training_workload_blocks: object,
        capacity_frontier_sha256: str,
    ) -> dict[str, str]:
        assert current_store is expected_store
        assert design == expected_design
        assert registered_input_audit is expected_audit
        assert training_power_blocks is registered_power
        assert training_workload_blocks is registered_workload
        assert capacity_frontier_sha256 == core.canonical_sha256(expected_frontier)
        events.append("poststate_replay")
        return planning_authority

    monkeypatch.setattr(core, "_validate_planning_store_prestate", validate_prestate)
    monkeypatch.setattr(core, "_registered_training_support", registered_support)
    monkeypatch.setattr(core, "solver_spec", parse_solver_contract)
    monkeypatch.setattr(core, "_EvidenceSolvingCallback", RecordingCallback)
    monkeypatch.setattr(
        implementation_runner,
        "execute_capacity_stage",
        execute_capacity,
    )
    monkeypatch.setattr(
        core,
        "_commit_planning_evidence_index_from_audit",
        commit_index,
    )
    monkeypatch.setattr(core, "_validate_stage_store", validate_poststate)
    monkeypatch.setattr(core, "_registered_planning_evidence", replay_poststate)

    result = core._execute_planning_stage_with_evidence_from_audit(
        design=expected_design,
        registered_input_audit=expected_audit,
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        store=expected_store,
    )

    assert events == [
        "prestate",
        "registered_support",
        "solver_contract",
        "callback",
        "capacity",
        "index",
        "inventory",
        "poststate_replay",
    ]
    assert result == {
        "schema": "rq2_joint_deliverability_planning_stage_v1",
        "capacity_frontier": expected_frontier,
        "capacity_frontier_sha256": core.canonical_sha256(expected_frontier),
        "planning_index_pointer": planning_index_pointer,
        **planning_authority,
    }
    parameters = inspect.signature(
        core._execute_planning_stage_with_evidence_from_audit
    ).parameters
    assert "solve_driver" not in parameters
    assert "model_factory" not in parameters
    assert "solver_specification" not in parameters


def test_reviewed_loader_advances_to_unbound_grid_gate_without_input_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = deepcopy(_config())
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_ready_for_independent_review": True,
    }
    audit_calls = 0

    def sealed_member(
        _root: Path,
        *,
        member_relative: str,
        **_kwargs: object,
    ) -> dict[str, object]:
        return config if member_relative == runner.CONFIG_RELATIVE else _scientific()

    def forbidden_audit(*_args: object, **_kwargs: object) -> object:
        nonlocal audit_calls
        audit_calls += 1
        raise AssertionError("unbound grid reached input audit")

    monkeypatch.setattr(
        core,
        "_load_reviewed_execution_config",
        lambda _root: (
            config,
            {
                "execution_outer_sha256": "0" * 64,
                "execution_review_sha256": "2" * 64,
            },
        ),
    )
    monkeypatch.setattr(core, "_sealed_yaml_member", sealed_member)
    monkeypatch.setattr(core, "derive_static_authority", lambda *_args: {})
    monkeypatch.setattr(core, "_audit_registered_input_snapshot", forbidden_audit)
    with pytest.raises(core.ExecutionBlocked, match="not bound"):
        core._load_live_registered_inputs(ROOT)
    assert audit_calls == 0


def test_execution_review_receipt_is_the_fixed_outer_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    review_contract = {
        "path": core._EXECUTION_REVIEW_RELATIVE,
        "schema": "rq2_joint_deliverability_execution_review_pass_v3",
        "review_scope": ("rq2_joint_deliverability_execution_successor_v3_exact_outer"),
        "reviewer_role": "independent_sol_reviewer",
        "required_verdict": "PASS",
        "required_effect": {
            "independent_v3_R3_review_passed": True,
            "independent_review_gate_closed": True,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "paper_claim": False,
            "security_certified": False,
        },
    }
    core_relative = "src/rq2_joint_deliverability_execution_v3/core.py"
    loaded_core = tmp_path / core_relative
    loaded_core.parent.mkdir(parents=True)
    loaded_core.write_text("# synthetic loaded module\n", encoding="utf-8")
    config_payload = {
        "execution_review_authority": review_contract,
        "implementation": {"core": {"path": core_relative}},
    }
    config_bytes = yaml.safe_dump(config_payload, sort_keys=False).encode()
    config_path = tmp_path / runner.CONFIG_RELATIVE
    config_path.parent.mkdir(parents=True)
    config_path.write_bytes(config_bytes)
    inner_path = tmp_path / (
        "configs/rq2_joint_deliverability_execution_successor_v3.SHA256SUMS.json"
    )
    inner_payload = {
        "schema": "rq2_joint_deliverability_execution_inner_v3",
        "version": 3,
        "files": {
            runner.CONFIG_RELATIVE: hashlib.sha256(config_bytes).hexdigest(),
        },
    }
    inner_path.write_bytes(canonical_json_bytes(inner_payload))
    outer_path = tmp_path / core._EXECUTION_OUTER_RELATIVE
    outer_payload = {
        "schema": "rq2_joint_deliverability_execution_outer_v3",
        "version": 3,
        "inner": {
            "path": inner_path.relative_to(tmp_path).as_posix(),
            "sha256": core.sha256_file(inner_path),
        },
    }
    outer_path.write_bytes(canonical_json_bytes(outer_payload))
    receipt = {
        "schema": "rq2_joint_deliverability_execution_review_pass_v3",
        "review_scope": ("rq2_joint_deliverability_execution_successor_v3_exact_outer"),
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "reviewed_subject": {
            "outer_path": core._EXECUTION_OUTER_RELATIVE,
            "outer_sha256": core.sha256_file(outer_path),
            "inner_sha256": core.sha256_file(inner_path),
            "sealed_member_count": 1,
        },
        "review_conclusion": {
            "blocker_findings": [],
            "major_findings": [],
            "minor_findings": [],
        },
        "effect": review_contract["required_effect"],
    }
    review_path = tmp_path / core._EXECUTION_REVIEW_RELATIVE
    with pytest.raises(ExecutionEvidenceError, match="required path is absent"):
        core._load_reviewed_execution_config(tmp_path)
    review_path.write_text(yaml.safe_dump(receipt, sort_keys=False), encoding="utf-8")
    monkeypatch.setattr(core, "__file__", str(loaded_core))

    loaded, authority = core._load_reviewed_execution_config(tmp_path)

    assert loaded == config_payload
    assert authority["execution_outer_sha256"] == core.sha256_file(outer_path)
    assert authority["execution_review_sha256"] == core.sha256_file(review_path)
    receipt["reviewed_subject"]["outer_sha256"] = "f" * 64
    review_path.write_text(yaml.safe_dump(receipt, sort_keys=False), encoding="utf-8")
    with pytest.raises(EvidenceDrift, match="outer manifest SHA-256 drifted"):
        core._load_reviewed_execution_config(tmp_path)


def test_sealed_yaml_member_parses_the_hashed_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    member_relative = "configs/member.yaml"
    member = tmp_path / member_relative
    member.parent.mkdir(parents=True)
    trusted_bytes = b"value: trusted\n"
    member.write_bytes(trusted_bytes)
    inner_relative = "configs/inner.json"
    inner = tmp_path / inner_relative
    inner.write_bytes(
        canonical_json_bytes(
            {
                "schema": "synthetic_inner_v1",
                "files": {
                    member_relative: hashlib.sha256(trusted_bytes).hexdigest(),
                },
            }
        )
    )
    outer_relative = "configs/outer.json"
    outer = tmp_path / outer_relative
    outer.write_bytes(
        canonical_json_bytes(
            {
                "schema": "synthetic_outer_v1",
                "inner": {
                    "path": inner_relative,
                    "sha256": core.sha256_file(inner),
                },
            }
        )
    )
    original_safe_load = yaml.safe_load

    def mutate_after_read(raw: str) -> object:
        member.write_text("value: forged\n", encoding="utf-8")
        return original_safe_load(raw)

    monkeypatch.setattr(core.yaml, "safe_load", mutate_after_read)
    payload = core._sealed_yaml_member(
        tmp_path,
        outer_relative=outer_relative,
        member_relative=member_relative,
        expected_outer_sha256=core.sha256_file(outer),
    )

    assert payload == {"value": "trusted"}
    assert member.read_text(encoding="utf-8") == "value: forged\n"


def test_content_addressed_object_parses_the_hashed_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="a" * 64)
    digest = store.put_object("stage", {"value": "trusted"})
    object_path = store.object_path("stage", digest)
    original_parser = core._json_bytes_mapping

    def mutate_after_read(payload: bytes, *, label: str) -> dict[str, object]:
        object_path.write_bytes(canonical_json_bytes({"value": "forged"}))
        return original_parser(payload, label=label)

    monkeypatch.setattr(core, "_json_bytes_mapping", mutate_after_read)
    payload = store.load_object("stage", digest)

    assert payload == {"value": "trusted"}
    assert json.loads(object_path.read_text(encoding="utf-8")) == {"value": "forged"}


def test_validate_only_runner_supports_direct_script_invocation() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "experiments/run_rq2_joint_deliverability_execution_v3.py"),
            "--validate-only",
        ],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    report = json.loads(completed.stdout)

    assert report["formal_execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["formal_result_files_written"] == 0


def test_live_static_authority_and_available_input_packages() -> None:
    config = _config()
    authority = derive_static_authority(ROOT, config)
    audit = audit_registered_inputs(ROOT, config)

    assert len(authority["files"]) == 10
    assert len(authority["authority_sha256"]) == 64
    assert authority["recursive_chains"]["scientific_outer"]["member_count"] == 5
    assert authority["recursive_chains"]["implementation_outer"]["member_count"] == 14
    assert audit["packages"]["power_base"]["training_blocks"] == 541
    assert audit["packages"]["power_base"]["holdout_blocks"] == 530
    assert audit["packages"]["workload"]["training_blocks"] == 34
    assert audit["packages"]["workload"]["holdout_blocks"] == 34


def test_caller_digest_cannot_bind_unregistered_dispatched_grid(
    tmp_path: Path,
) -> None:
    (
        _power,
        _grid,
        power_manifest,
        grid_manifest,
        grid_config_sha256,
    ) = _synthetic_dispatched_grid_packages(tmp_path)
    workload = tmp_path / "workload"
    _synthetic_split_package(
        workload,
        hourly_file="workload_blocks.csv.gz",
        source_field="source_relative_hour",
    )
    workload_manifest = _manifest(workload)
    config = {
        "registered_inputs": {
            "power_base": {
                "package": "power",
                "manifest_path": "power/SHA256SUMS.json",
                "manifest_sha256": power_manifest,
                "hourly_file": "power.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "workload": {
                "package": "workload",
                "manifest_path": "workload/SHA256SUMS.json",
                "manifest_sha256": workload_manifest,
                "hourly_file": "workload_blocks.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "dispatched_grid": {
                "package": "grid",
                "manifest_path": "grid/SHA256SUMS.json",
                "manifest_sha256": None,
                "hourly_file": "dispatched_power_system_blocks.csv.gz",
                "config_sha256": grid_config_sha256,
                "dc_reference_demand_mw": 250.0,
                "ready": False,
            },
        }
    }

    audit = audit_registered_inputs(
        tmp_path,
        config,
        activated_grid_manifest_sha256=grid_manifest,
    )

    assert audit["registered_inputs_ready"] is False
    assert audit["packages"]["dispatched_grid"]["status"] == (
        "blocked_unbound_dispatched_grid_manifest"
    )


def test_external_grid_e0_certificate_is_replayed(
    tmp_path: Path,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(tmp_path)

    audit = audit_registered_inputs(
        tmp_path,
        config,
        activated_grid_manifest_sha256=grid_manifest,
    )
    assert audit["registered_inputs_ready"] is True


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("dispatch_lower_bound_mw", "0", "dispatch bound certificate"),
        ("dispatch_upper_bound_mw", "0", "dispatch bound certificate"),
        ("dispatch_absolute_gap_mw", "0", "dispatch bound certificate"),
        ("dispatch_relative_gap", "0", "dispatch relative-gap certificate"),
        ("dispatch_gap_tolerance_mw", "0", "dispatch relative-gap certificate"),
        (
            "zero_dc_confirmation_lower_bound_mw",
            "0",
            "zero_dc_confirmation bound certificate",
        ),
        (
            "zero_dc_confirmation_upper_bound_mw",
            "0",
            "zero_dc_confirmation bound certificate",
        ),
        (
            "zero_dc_confirmation_absolute_gap_mw",
            "0",
            "zero_dc_confirmation bound certificate",
        ),
        ("dispatch_solver_status", "ok", "E0 dispatched-grid state"),
        (
            "zero_dc_confirmation_solver_status",
            "ok",
            "E0 zero-DC confirmation",
        ),
        (
            "zero_dc_confirmation_model_variables",
            "2",
            "E0 primary and zero-DC model scale",
        ),
        ("dispatch_termination_condition", "maxTimeLimit", "E0 dispatched-grid state"),
        (
            "zero_dc_confirmation_termination_condition",
            "maxTimeLimit",
            "E0 zero-DC confirmation",
        ),
    ],
)
def test_external_grid_e0_single_field_faults_fail_closed(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(
        tmp_path,
        row_fault=(field, value),
    )
    with pytest.raises(EvidenceDrift, match=message):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


@pytest.mark.parametrize(
    ("path", "value", "message"),
    [
        (
            ("outcomes", 1, "zero_dc_confirmation", "resolved"),
            True,
            "zero-DC E0 outcome",
        ),
        (
            ("outcomes", 1, "zero_dc_confirmation", "proven_infeasible"),
            False,
            "zero-DC E0 outcome",
        ),
        (
            ("outcomes", 1, "zero_dc_confirmation", "grid_need_mw"),
            0.0,
            "zero-DC E0 outcome",
        ),
        (
            (
                "outcomes",
                1,
                "zero_dc_confirmation",
                "maximum_constraint_violation",
            ),
            0.0,
            "zero-DC E0 outcome",
        ),
        (
            ("outcomes", 1, "zero_dc_confirmation", "source_hour"),
            2,
            "zero-DC E0 metadata",
        ),
        (
            ("outcomes", 1, "zero_dc_confirmation", "event_id"),
            "forged_event",
            "zero-DC E0 metadata",
        ),
        (
            ("outcomes", 1, "zero_dc_confirmation", "component_type"),
            "generator",
            "zero-DC E0 metadata",
        ),
        (
            ("outcomes", 1, "zero_dc_confirmation", "component_uid"),
            "forged_uid",
            "zero-DC E0 metadata",
        ),
        (
            (
                "outcomes",
                1,
                "zero_dc_confirmation_certificate",
                "objective_incumbent_mw",
            ),
            0.0,
            "zero-DC E0 certificate",
        ),
        (
            (
                "outcomes",
                1,
                "zero_dc_confirmation_certificate",
                "relative_gap",
            ),
            0.0,
            "zero-DC E0 certificate",
        ),
        (
            (
                "outcomes",
                1,
                "zero_dc_confirmation_certificate",
                "gap_tolerance_mw",
            ),
            0.0,
            "zero-DC E0 certificate",
        ),
    ],
)
def test_external_grid_e0_checkpoint_single_field_faults_fail_closed(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: object,
    message: str,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(
        tmp_path,
        checkpoint_fault=(path, value),
    )
    with pytest.raises(EvidenceDrift, match=message):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


@pytest.mark.parametrize("fault", ["missing", "extra"])
def test_external_grid_checkpoint_inventory_requires_exact_payload_files(
    tmp_path: Path,
    fault: str,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(tmp_path)
    if fault == "missing":
        (tmp_path / "checkpoints/training.json").unlink()
    else:
        (tmp_path / "checkpoints/extra.json").write_text(
            "{}\n",
            encoding="utf-8",
        )

    with pytest.raises(EvidenceDrift, match="checkpoint file inventory"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_external_grid_checkpoint_digest_drift_is_rejected(
    tmp_path: Path,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(tmp_path)
    checkpoint = tmp_path / "checkpoints/training.json"
    checkpoint.write_bytes(checkpoint.read_bytes() + b" ")

    with pytest.raises(EvidenceDrift, match="checkpoint digest"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_external_grid_checkpoint_row_projection_drift_is_rejected(
    tmp_path: Path,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(
        tmp_path,
        checkpoint_fault=(("rows", 0, "system_load_mw"), 999.0),
    )

    with pytest.raises(EvidenceDrift, match="checkpoint row projection"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("baseline_audit", "objective_usd"), 101.0),
        (("baseline_audit", "objective_usd"), 100.00005),
        (("baseline_audit", "lower_bound_usd"), 99.0),
        (("baseline_audit", "absolute_gap_usd"), 2.0e-12),
        (("baseline_audit", "maximum_constraint_violation"), 2.0e-6),
        (("baseline_audit", "maximum_integrality_violation"), 2.0e-6),
        (("baseline_audit", "termination_condition"), "globallyOptimal"),
        (("baseline_audit", "solver_name"), "highs"),
        (("baseline_audit", "solver_options", "Threads"), 8),
        (("baseline_audit", "model_variables"), 0),
    ],
)
def test_external_grid_baseline_single_field_faults_fail_closed(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: object,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(
        tmp_path,
        checkpoint_fault=(path, value),
    )

    with pytest.raises(EvidenceDrift, match="baseline"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_grid_checkpoint_baseline_gap_cannot_use_one_nanodollar_slack() -> None:
    solver = {
        "name": "gurobi",
        "threads": 4,
        "mip_relative_gap": 1.0e-6,
        "integer_feasibility_tolerance": 1.0e-6,
        "tolerance_mw": 1.0e-6,
    }
    baseline = _synthetic_event_baseline_audit()
    upper = 100.0
    tolerance = float(baseline["gap_tolerance_usd"])
    lower = upper - (tolerance + 4.0e-10)
    gap = upper - lower
    baseline.update(
        {
            "objective_usd": upper,
            "lower_bound_usd": lower,
            "upper_bound_usd": upper,
            "absolute_gap_usd": gap,
            "relative_gap": gap / upper,
        }
    )

    with pytest.raises(EvidenceDrift, match="baseline"):
        core._validate_grid_checkpoint_baseline(
            baseline,
            has_event=True,
            grid_solver=solver,
            expected_solver_options=baseline["solver_options"],
        )


def test_finite_grid_incumbent_cannot_use_solver_gap_to_escape_interval() -> None:
    with pytest.raises(EvidenceDrift, match="incumbent is outside bounds"):
        core._validate_grid_minimization_certificate(
            incumbent=25.00001,
            lower=25.0,
            upper=25.0,
            absolute_gap=0.0,
            relative_gap=0.0,
            reported_gap_tolerance=2.5e-5,
            model_tolerance=1.0e-6,
            configured_relative_gap=1.0e-6,
            label="synthetic finite certificate",
        )


def test_finite_grid_relative_gap_cannot_hide_under_absolute_tolerance() -> None:
    upper = 0.1
    lower = 0.0999995
    gap = upper - lower
    with pytest.raises(EvidenceDrift, match="registered gap limit"):
        core._validate_grid_minimization_certificate(
            incumbent=upper,
            lower=lower,
            upper=upper,
            absolute_gap=gap,
            relative_gap=gap / upper,
            reported_gap_tolerance=1.0e-6,
            model_tolerance=1.0e-6,
            configured_relative_gap=1.0e-6,
            label="synthetic finite certificate",
        )


def test_no_event_grid_certificate_requires_zero_values() -> None:
    values = {
        "grid_need_mw": 0.0,
        "grid_need_fraction": 0.0,
        "objective_incumbent_mw": 0.0,
        "lower_bound_mw": 0.0,
        "upper_bound_mw": 0.0,
        "absolute_gap_mw": 0.0,
        "relative_gap": 0.0,
        "gap_tolerance_mw": 0.0,
        "maximum_constraint_violation": 0.0,
    }
    core._validate_no_event_grid_values(values)
    with pytest.raises(EvidenceDrift, match="must be zero"):
        core._validate_no_event_grid_values({**values, "grid_need_mw": 25.0})


def test_grid_checkpoint_no_event_baseline_requires_exact_minimal_payload() -> None:
    solver = {
        "name": "gurobi",
        "threads": 4,
        "mip_relative_gap": 1.0e-6,
        "integer_feasibility_tolerance": 1.0e-6,
        "tolerance_mw": 1.0e-6,
    }
    baseline = {
        "accepted": True,
        "termination_condition": "not_applicable_no_active_outage",
    }

    assert (
        core._validate_grid_checkpoint_baseline(
            baseline,
            has_event=False,
            grid_solver=solver,
            expected_solver_options={},
        )
        is None
    )
    with pytest.raises(EvidenceDrift, match="no-event baseline"):
        core._validate_grid_checkpoint_baseline(
            {**baseline, "solver_status": "not_applicable"},
            has_event=False,
            grid_solver=solver,
            expected_solver_options={},
        )


def test_external_grid_summary_normal_scuc_scales_are_rebuilt(
    tmp_path: Path,
) -> None:
    config, _grid_manifest = _synthetic_e0_audit_case(tmp_path)
    grid = tmp_path / "grid"
    summary = json.loads((grid / "summary.json").read_text(encoding="utf-8"))
    summary["normal_scuc_model_scales"] = []
    (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    grid_manifest = _manifest(grid)
    config["registered_inputs"]["dispatched_grid"]["manifest_sha256"] = grid_manifest

    with pytest.raises(EvidenceDrift, match="summary contract"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_external_grid_duplicate_json_key_is_rejected(
    tmp_path: Path,
) -> None:
    config, _grid_manifest = _synthetic_e0_audit_case(tmp_path)
    checkpoint = tmp_path / "checkpoints/training.json"
    payload = checkpoint.read_text(encoding="utf-8").rstrip("\n")
    checkpoint.write_text(
        payload[:-1] + ',"schema":"rts_gmlc_public_grid_need_block_checkpoint_v4"}\n',
        encoding="utf-8",
    )
    grid_manifest = _rebind_synthetic_checkpoint_inventory(
        tmp_path,
        tmp_path / "grid",
    )
    config["registered_inputs"]["dispatched_grid"]["manifest_sha256"] = grid_manifest

    with pytest.raises(ExecutionEvidenceError, match="invalid JSON"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_static_validator_duplicate_json_key_is_rejected(tmp_path: Path) -> None:
    payload = tmp_path / "duplicate.json"
    payload.write_text('{"value":1,"value":1}\n', encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate JSON object key"):
        validator._load_json(payload)


@pytest.mark.parametrize("literal", ["1e999", "-1e999"])
def test_external_json_exponent_overflow_is_rejected(
    tmp_path: Path,
    literal: str,
) -> None:
    payload = f'{{"value":{literal}}}\n'

    with pytest.raises(ExecutionEvidenceError, match="invalid JSON"):
        core._json_bytes_mapping(payload.encode("utf-8"), label="synthetic overflow")
    path = tmp_path / "overflow.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        validator._load_json(path)


@pytest.mark.parametrize("literal", ["NaN", "Infinity", "-Infinity"])
def test_external_json_nonfinite_constant_is_rejected(
    tmp_path: Path,
    literal: str,
) -> None:
    payload = f'{{"value":{literal}}}\n'

    with pytest.raises(ExecutionEvidenceError, match="invalid JSON"):
        core._json_bytes_mapping(payload.encode("utf-8"), label="synthetic constant")
    path = tmp_path / "nonfinite.json"
    path.write_text(payload, encoding="utf-8")
    with pytest.raises(ValueError, match="non-finite JSON number"):
        validator._load_json(path)


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("outcomes", 0, "primary", "resolved"), "true"),
        (("outcomes", 0, "primary", "proven_infeasible"), "false"),
    ],
)
def test_external_grid_finite_checkpoint_boolean_type_drift_is_rejected(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: object,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(
        tmp_path,
        checkpoint_fault=(path, value),
    )

    with pytest.raises(EvidenceDrift, match="primary outcome projection"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_external_grid_rejects_unregistered_globally_optimal_status(
    tmp_path: Path,
) -> None:
    config, _grid_manifest = _synthetic_e0_audit_case(tmp_path)
    grid = tmp_path / "grid"
    hourly_path = grid / "dispatched_power_system_blocks.csv.gz"
    with gzip.open(hourly_path, "rt", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[0]["dispatch_termination_condition"] = "globallyOptimal"
    _write_gzip_csv(hourly_path, list(core._GRID_OUTPUT_FIELDS), rows)

    checkpoint_path = tmp_path / "checkpoints/training.json"
    checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
    checkpoint["rows"][0]["dispatch_termination_condition"] = "globallyOptimal"
    checkpoint["outcomes"][0]["primary"]["termination_condition"] = "globallyOptimal"
    checkpoint_path.write_bytes(canonical_json_bytes(checkpoint))
    grid_manifest = _rebind_synthetic_checkpoint_inventory(tmp_path, grid)
    config["registered_inputs"]["dispatched_grid"]["manifest_sha256"] = grid_manifest

    with pytest.raises(EvidenceDrift, match="solver state"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


@pytest.mark.parametrize(
    ("path", "value"),
    [
        (("rows", 0, "source_hour"), 0),
        (("rows", 0, "grid_need_mw"), 25.0 + 5.0e-13),
    ],
)
def test_external_grid_checkpoint_requires_exact_producer_row_representation(
    tmp_path: Path,
    path: tuple[str | int, ...],
    value: object,
) -> None:
    config, grid_manifest = _synthetic_e0_audit_case(
        tmp_path,
        checkpoint_fault=(path, value),
    )

    with pytest.raises(EvidenceDrift, match="checkpoint row projection"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


def test_external_grid_csv_extra_trailing_column_is_rejected(
    tmp_path: Path,
) -> None:
    config, _grid_manifest = _synthetic_e0_audit_case(tmp_path)
    grid = tmp_path / "grid"
    hourly_path = grid / "dispatched_power_system_blocks.csv.gz"
    with gzip.open(hourly_path, "rt", encoding="utf-8", newline="") as handle:
        lines = handle.readlines()
    lines[1] = lines[1].rstrip("\r\n") + ",opaque\n"
    with gzip.open(hourly_path, "wt", encoding="utf-8", newline="") as handle:
        handle.writelines(lines)
    grid_manifest = _manifest(grid)
    config["registered_inputs"]["dispatched_grid"]["manifest_sha256"] = grid_manifest

    with pytest.raises(EvidenceDrift, match="CSV row width"):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ("\n", "CSV header"),
        (",b\n1,2\n", "CSV header"),
        ("a,a\n1,2\n", "CSV header"),
        ("a,b\n1\n", "CSV row width"),
    ],
)
def test_csv_loader_rejects_header_and_short_row_drift(
    payload: str,
    message: str,
) -> None:
    with pytest.raises(EvidenceDrift, match=message):
        core._gzip_csv_rows(
            gzip.compress(payload.encode("utf-8"), mtime=0),
            label="synthetic CSV",
        )


def test_registered_input_parsing_consumes_verified_package_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (
        _power,
        grid,
        power_manifest,
        grid_manifest,
        grid_config_sha256,
    ) = _synthetic_dispatched_grid_packages(tmp_path)
    workload = tmp_path / "workload"
    _synthetic_split_package(
        workload,
        hourly_file="workload_blocks.csv.gz",
        source_field="source_relative_hour",
    )
    workload_manifest = _manifest(workload)
    config = {
        "registered_inputs": {
            "power_base": {
                "package": "power",
                "manifest_path": "power/SHA256SUMS.json",
                "manifest_sha256": power_manifest,
                "hourly_file": "power.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "workload": {
                "package": "workload",
                "manifest_path": "workload/SHA256SUMS.json",
                "manifest_sha256": workload_manifest,
                "hourly_file": "workload_blocks.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "dispatched_grid": {
                "package": "grid",
                "manifest_path": "grid/SHA256SUMS.json",
                "manifest_sha256": grid_manifest,
                "hourly_file": "dispatched_power_system_blocks.csv.gz",
                "config_sha256": grid_config_sha256,
                "dc_reference_demand_mw": 250.0,
                "ready": True,
            },
        }
    }
    original_parser = core._snapshot_power_blocks
    mutated = False

    def mutate_after_snapshot(
        files: dict[str, bytes],
        split: str,
    ) -> tuple[PowerBlock, ...]:
        nonlocal mutated
        if not mutated:
            mutated = True
            (grid / "dispatched_power_system_blocks.csv.gz").write_bytes(b"forged")
        return original_parser(files, split)

    monkeypatch.setattr(core, "_snapshot_power_blocks", mutate_after_snapshot)
    audit = audit_registered_inputs(
        tmp_path,
        config,
        activated_grid_manifest_sha256=grid_manifest,
    )

    assert audit["registered_inputs_ready"] is True
    assert (
        core.sha256_file(grid / "dispatched_power_system_blocks.csv.gz")
        != (
            json.loads((grid / "SHA256SUMS.json").read_text(encoding="utf-8"))[
                "dispatched_power_system_blocks.csv.gz"
            ]
        )
    )


@pytest.mark.parametrize(
    "drift",
    (
        "source_row",
        "grid_fraction",
        "solver_bound",
        "solver_gap",
        "solver_negative",
        "solver_relative_gap",
        "solver_tolerance",
        "solver_termination",
        "solver_status",
        "solver_residual",
        "solver_scale",
        "block_status",
        "config",
        "provenance",
        "summary",
    ),
)
def test_external_grid_semantic_drift_is_rejected(
    tmp_path: Path,
    drift: str,
) -> None:
    (
        _power,
        grid,
        power_manifest,
        _grid_manifest,
        grid_config_sha256,
    ) = _synthetic_dispatched_grid_packages(tmp_path)
    workload = tmp_path / "workload"
    _synthetic_split_package(
        workload,
        hourly_file="workload_blocks.csv.gz",
        source_field="source_relative_hour",
    )
    workload_manifest = _manifest(workload)
    if drift.startswith("solver_") or drift in {"source_row", "grid_fraction"}:
        with gzip.open(
            grid / "dispatched_power_system_blocks.csv.gz",
            "rt",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        if drift == "source_row":
            rows[0]["system_load_mw"] = "999.0"
        elif drift == "grid_fraction":
            rows[0]["grid_need_fraction"] = "999.0"
        elif drift == "solver_bound":
            rows[0]["dispatch_lower_bound_mw"] = "100.0"
        elif drift == "solver_gap":
            rows[0]["dispatch_absolute_gap_mw"] = "1.0"
        elif drift == "solver_negative":
            rows[0]["grid_need_mw"] = "0.0"
            rows[0]["grid_need_fraction"] = "0.0"
            rows[0]["dispatch_objective_incumbent_mw"] = "-1.0"
            rows[0]["dispatch_lower_bound_mw"] = "-1.0"
            rows[0]["dispatch_upper_bound_mw"] = "-1.0"
            rows[0]["dispatch_absolute_gap_mw"] = "0.0"
            rows[0]["dispatch_relative_gap"] = "0.0"
            rows[0]["dispatch_gap_tolerance_mw"] = "1e-6"
        elif drift == "solver_relative_gap":
            rows[0]["dispatch_relative_gap"] = "1.0"
        elif drift == "solver_tolerance":
            rows[0]["dispatch_gap_tolerance_mw"] = "1.0"
        elif drift == "solver_termination":
            rows[0]["dispatch_termination_condition"] = "maxTimeLimit"
        elif drift == "solver_status":
            rows[0]["dispatch_solver_status"] = "error"
        elif drift == "solver_residual":
            rows[0]["maximum_constraint_violation"] = "1000000000.0"
        else:
            rows[0]["dispatch_model_variables"] = "0"
        _write_gzip_csv(
            grid / "dispatched_power_system_blocks.csv.gz",
            list(core._GRID_OUTPUT_FIELDS),
            rows,
        )
    elif drift == "block_status":
        with gzip.open(
            grid / "block_status.csv.gz",
            "rt",
            encoding="utf-8",
            newline="",
        ) as handle:
            rows = list(csv.DictReader(handle))
        rows[0]["exogenous_grid_infeasibility_hour_count"] = "1"
        _write_gzip_csv(
            grid / "block_status.csv.gz",
            list(rows[0]),
            rows,
        )
    elif drift == "config":
        payload = yaml.safe_load((grid / "config.yaml").read_text(encoding="utf-8"))
        payload["model"]["dc_reference_demand_mw"] = 200.0
        (grid / "config.yaml").write_text(
            yaml.safe_dump(payload, sort_keys=False),
            encoding="utf-8",
        )
        summary = json.loads((grid / "summary.json").read_text(encoding="utf-8"))
        summary["config_sha256"] = core.sha256_file(grid / "config.yaml")
        (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    elif drift == "provenance":
        provenance = json.loads((grid / "provenance.json").read_text(encoding="utf-8"))
        provenance["base"]["stage"] = "forged"
        (grid / "provenance.json").write_bytes(canonical_json_bytes(provenance))
        summary = json.loads((grid / "summary.json").read_text(encoding="utf-8"))
        summary["provenance_sha256"] = core.sha256_file(grid / "provenance.json")
        (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    else:
        summary = json.loads((grid / "summary.json").read_text(encoding="utf-8"))
        summary["all_blocks_resolved"] = False
        (grid / "summary.json").write_bytes(canonical_json_bytes(summary))
    grid_manifest = _manifest(grid)
    config = {
        "registered_inputs": {
            "power_base": {
                "package": "power",
                "manifest_path": "power/SHA256SUMS.json",
                "manifest_sha256": power_manifest,
                "hourly_file": "power.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "workload": {
                "package": "workload",
                "manifest_path": "workload/SHA256SUMS.json",
                "manifest_sha256": workload_manifest,
                "hourly_file": "workload_blocks.csv.gz",
                "training_blocks": 1,
                "holdout_blocks": 1,
            },
            "dispatched_grid": {
                "package": "grid",
                "manifest_path": "grid/SHA256SUMS.json",
                "manifest_sha256": grid_manifest,
                "hourly_file": "dispatched_power_system_blocks.csv.gz",
                "config_sha256": grid_config_sha256,
                "dc_reference_demand_mw": 250.0,
                "ready": False,
            },
        }
    }
    with pytest.raises(EvidenceDrift):
        audit_registered_inputs(
            tmp_path,
            config,
            activated_grid_manifest_sha256=grid_manifest,
        )


@pytest.mark.parametrize(
    ("field", "label"),
    (
        ("dispatch_lower_bound_mw", "dispatch lower"),
        ("dispatch_upper_bound_mw", "dispatch upper"),
    ),
)
def test_grid_bound_certificate_rejects_each_negative_field(
    field: str,
    label: str,
) -> None:
    row = {
        "dispatch_lower_bound_mw": "0.0",
        "dispatch_upper_bound_mw": "0.0",
        "dispatch_absolute_gap_mw": "0.0",
        "dispatch_relative_gap": "0.0",
        "dispatch_gap_tolerance_mw": "0.0",
    }
    row[field] = "-1.0"
    with pytest.raises(EvidenceDrift, match=label):
        core._validate_bound_fields(
            row,
            prefix="dispatch",
            include_relative_and_tolerance=True,
        )


def test_grid_incumbent_certificate_rejects_negative_value() -> None:
    with pytest.raises(EvidenceDrift, match="registered domain"):
        core._finite_csv_float(
            "-1.0",
            "dispatch objective incumbent",
            minimum=0.0,
        )


def test_fresh_process_local_import_closure_is_bound() -> None:
    script = """
import json
import sys
from pathlib import Path

root = Path.cwd().resolve()
import experiments.run_rq2_joint_deliverability_execution_v3  # noqa: F401

observed = set()
for module in sys.modules.values():
    raw = getattr(module, "__file__", None)
    if raw is None:
        continue
    path = Path(raw).resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        continue
    if relative.suffix == ".py":
        observed.add(relative.as_posix())
print(json.dumps(sorted(observed)))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    observed = set(json.loads(completed.stdout))
    expected = {
        "experiments/__init__.py",
        "experiments/run_rq2_joint_deliverability_execution_v3.py",
        "experiments/validate_rq2_joint_deliverability_execution_v3.py",
        "src/__init__.py",
        "src/rq2_joint_deliverability_execution_v3/__init__.py",
        "src/rq2_joint_deliverability_execution_v3/core.py",
        "src/rq2_joint_deliverability_v2/__init__.py",
        "src/rq2_joint_deliverability_v2/evaluation.py",
        "src/rq2_joint_deliverability_v2/model.py",
        "src/rq2_joint_deliverability_v2/scenarios.py",
        "src/rq2_joint_deliverability_v2/solver_adapter.py",
    }
    implementation_inner = json.loads(
        (
            ROOT
            / "configs/rq2_joint_deliverability_implementation_successor_v2.SHA256SUMS.json"
        ).read_text(encoding="utf-8")
    )
    recursively_bound = set(validator.EXPECTED_MEMBERS) | set(
        implementation_inner["files"]
    )

    assert observed == expected
    assert observed <= recursively_bound


def test_cached_implementation_module_cannot_open_public_stage_surface() -> None:
    script = """
import src.rq2_joint_deliverability_v2.evaluation as evaluation
import src.rq2_joint_deliverability_v2.model as model
import src.rq2_joint_deliverability_v2.scenarios as scenarios
import src.rq2_joint_deliverability_v2.solver_adapter as solver_adapter

def poisoned(*args, **kwargs):
    raise AssertionError("cached implementation symbol was invoked")

evaluation.certify_scalar_transport = poisoned
evaluation.execute_holdout_policy = poisoned
model.build_arm_planning_model = poisoned
scenarios.expand_registered_cells = poisoned
solver_adapter.create_solver = poisoned

from src.rq2_joint_deliverability_execution_v3 import core

calls = (
    lambda: core.execute_planning_stage_with_evidence(store=object()),
    lambda: core.stream_holdout_stage(capacity_frontier={}, store=object()),
    lambda: core.execute_bootstrap_resumable(store=object()),
    lambda: core.aggregate_bootstrap_checkpoints(object()),
)
for call in calls:
    try:
        call()
    except core.ExecutionBlocked as error:
        assert "fresh-process activation" in str(error)
    else:
        raise AssertionError("public stage unexpectedly opened")
"""
    subprocess.run(
        [sys.executable, "-c", script],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )


def test_split_inventory_rejects_block_and_source_overlap(tmp_path: Path) -> None:
    package = tmp_path / "block-overlap"
    _synthetic_split_package(package, overlap_id=True)
    with pytest.raises(EvidenceDrift, match="block IDs overlap|inventories differ"):
        audit_split_inventory(
            package,
            hourly_file="hourly.csv.gz",
            source_field="source_hour",
            training_blocks=1,
            holdout_blocks=1,
        )

    package = tmp_path / "source-overlap"
    _synthetic_split_package(package, overlap_source=True)
    with pytest.raises(EvidenceDrift, match="source support overlaps"):
        audit_split_inventory(
            package,
            hourly_file="hourly.csv.gz",
            source_field="source_hour",
            training_blocks=1,
            holdout_blocks=1,
        )


def test_manifest_rejects_member_and_inventory_drift(tmp_path: Path) -> None:
    package = tmp_path / "package"
    _synthetic_split_package(package)
    digest = _manifest(package)
    members = verify_flat_manifest(
        package,
        manifest_name="SHA256SUMS.json",
        expected_manifest_sha256=digest,
    )
    assert len(members) == 3

    (package / "extra.txt").write_text("unexpected\n", encoding="utf-8")
    with pytest.raises(EvidenceDrift, match="inventory drifted"):
        verify_flat_manifest(
            package,
            manifest_name="SHA256SUMS.json",
            expected_manifest_sha256=digest,
        )


def test_evidence_store_is_idempotent_and_rejects_drift(tmp_path: Path) -> None:
    identity = "1" * 64
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256=identity)
    first = store.commit("stage", "key", {"value": 1})
    second = store.commit("stage", "key", {"value": 1})

    assert first == second
    assert store.load("stage", "key") == {"value": 1}
    inventory = store.inventory()
    assert len(inventory["files"]) == 2
    assert len(inventory["inventory_sha256"]) == 64
    with pytest.raises(EvidenceDrift, match="immutable evidence drifted"):
        store.commit("stage", "key", {"value": 2})

    object_path = store.object_path("stage", str(first["object_sha256"]))
    object_path.write_text('{"value":2}\n', encoding="utf-8")
    with pytest.raises(EvidenceDrift, match="content-addressed object drifted"):
        store.load("stage", "key")


def test_evidence_inventory_adopts_inert_orphans_and_rejects_broken_pointer_closure(
    tmp_path: Path,
) -> None:
    orphan_object_store = EvidenceStore(
        tmp_path / "orphan-object",
        run_identity_sha256="1" * 64,
    )
    orphan_object_digest = orphan_object_store.put_object("stage", {"orphan": True})
    object_inventory = orphan_object_store.inventory()
    assert object_inventory["inert_content_addressed_objects"] == [
        f"objects/stage/{orphan_object_digest[:2]}/{orphan_object_digest}.json"
    ]
    orphan_object_store.commit("stage", "adopted", {"orphan": True})
    assert orphan_object_store.inventory()["inert_content_addressed_objects"] == []

    orphan_blob_store = EvidenceStore(
        tmp_path / "orphan-blob",
        run_identity_sha256="2" * 64,
    )
    orphan_blob_digest = orphan_blob_store.put_blob("solver_log", b"orphan")
    blob_inventory = orphan_blob_store.inventory()
    assert blob_inventory["inert_content_addressed_blobs"] == [
        f"blobs/solver_log/{orphan_blob_digest[:2]}/{orphan_blob_digest}.bin"
    ]
    orphan_blob_store.commit(
        "solve",
        "adopted",
        {"native_log_sha256": orphan_blob_digest},
    )
    assert orphan_blob_store.inventory()["inert_content_addressed_blobs"] == []

    broken_pointer_store = EvidenceStore(
        tmp_path / "broken-pointer",
        run_identity_sha256="3" * 64,
    )
    broken_pointer_store.commit("stage", "key", {"value": 1})
    pointer_path = broken_pointer_store.root / "checkpoints" / "stage" / "key.json"
    pointer = json.loads(pointer_path.read_text(encoding="utf-8"))
    pointer["object_sha256"] = "f" * 64
    pointer_path.write_bytes(canonical_json_bytes(pointer))
    with pytest.raises(EvidenceDrift, match="checkpoint object is missing"):
        broken_pointer_store.inventory()


def test_evidence_inventory_rejects_unregistered_empty_directory(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="4" * 64)
    (store.root / "unregistered" / "empty").mkdir(parents=True)

    with pytest.raises(EvidenceDrift, match="empty evidence directory"):
        store.inventory()


def test_stage_inventory_rejects_unrelated_checkpoint_before_effects(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="5" * 64)
    store.commit("bootstrap", "r000__cell", {"value": 1})

    with pytest.raises(EvidenceDrift, match="unrelated stage"):
        core._validate_stage_store(
            store,
            allowed_stages=core._PLANNING_EVIDENCE_STAGES,
            allowed_blob_namespaces={"solver_log"},
        )

    same_stage = EvidenceStore(
        tmp_path / "same-stage",
        run_identity_sha256="6" * 64,
    )
    same_stage.commit("solve", "forged", {"value": 1})
    with pytest.raises(EvidenceDrift, match="planning evidence store is not empty"):
        core._validate_planning_store_prestate(same_stage)


def test_private_stage_helpers_validate_full_inventory_before_effects(
    tmp_path: Path,
) -> None:
    def holdout(store: EvidenceStore) -> object:
        return core._stream_holdout_stage_from_audit(
            {},
            capacity_frontier={},
            registered_input_audit={},
            training_power_blocks=(),
            holdout_power_blocks=(),
            training_workload_blocks=(),
            holdout_workload_blocks=(),
            store=store,
        )

    def bootstrap(store: EvidenceStore) -> object:
        return core._execute_bootstrap_resumable_from_audit(
            design={},
            registered_input_audit={},
            training_power_blocks=(),
            holdout_power_blocks=(),
            training_workload_blocks=(),
            holdout_workload_blocks=(),
            store=store,
        )

    def aggregate(store: EvidenceStore) -> object:
        return core._aggregate_bootstrap_checkpoints_from_audit(
            store,
            design={},
            registered_input_audit={},
            training_power_blocks=(),
            holdout_power_blocks=(),
            training_workload_blocks=(),
            holdout_workload_blocks=(),
        )

    for name, invoke in (
        ("holdout", holdout),
        ("bootstrap", bootstrap),
        ("aggregate", aggregate),
    ):
        store = EvidenceStore(
            tmp_path / name,
            run_identity_sha256="7" * 64,
        )
        lock = store.root / "objects" / "holdout" / "aa" / "orphan.json.lock"
        lock.parent.mkdir(parents=True)
        lock.write_bytes(b"locked\n")
        before = tuple(
            sorted(path.relative_to(store.root) for path in store.root.rglob("*"))
        )

        with pytest.raises(EvidenceDrift, match="not sealed-ready"):
            invoke(store)

        after = tuple(
            sorted(path.relative_to(store.root) for path in store.root.rglob("*"))
        )
        assert after == before


def test_store_identity_must_match_internally_derived_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(core, "_REPOSITORY_ROOT", tmp_path)
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="7" * 64)

    with pytest.raises(EvidenceDrift, match="run identity drifted"):
        core._require_store_run_identity(
            store,
            {
                "run_identity_sha256": "8" * 64,
                "evidence_root_relative": "evidence",
            },
        )
    core._require_store_run_identity(
        store,
        {
            "run_identity_sha256": "7" * 64,
            "evidence_root_relative": "evidence",
        },
    )
    other_store = EvidenceStore(
        tmp_path / "other-evidence",
        run_identity_sha256="7" * 64,
    )
    with pytest.raises(EvidenceDrift, match="store root drifted"):
        core._require_store_run_identity(
            other_store,
            {
                "run_identity_sha256": "7" * 64,
                "evidence_root_relative": "evidence",
            },
        )


def test_evidence_store_rejects_symlink_component(tmp_path: Path) -> None:
    real = tmp_path / "real"
    real.mkdir()
    link = tmp_path / "link"
    try:
        os.symlink(real, link)
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")
    with pytest.raises(ExecutionEvidenceError, match="symlink or reparse"):
        EvidenceStore(link, run_identity_sha256="2" * 64)


def test_evidence_store_rejects_internal_symlink_before_external_write(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="2" * 64)
    external = tmp_path / "external"
    external.mkdir()
    try:
        os.symlink(external, store.root / "objects")
    except (OSError, NotImplementedError):
        pytest.skip("symlink creation is unavailable")

    with pytest.raises(ExecutionEvidenceError, match="symlink or reparse"):
        store.put_object("stage", {"value": 1})

    assert list(external.iterdir()) == []


def test_evidence_store_fsyncs_each_new_directory_entry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="2" * 64)
    flushed: list[Path] = []
    monkeypatch.setattr(
        core,
        "_fsync_directory",
        lambda path: flushed.append(path),
    )

    store.put_object("stage", {"value": 1})

    assert store.root in flushed
    assert store.root / "objects" in flushed
    assert store.root / "objects" / "stage" in flushed


def test_durable_mkdir_fsyncs_file_exists_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="2" * 64)
    raced_directory = store.root / "objects"
    original_mkdir = os.mkdir
    flushed: list[Path] = []

    def race_mkdir(path: object, mode: int = 0o777) -> None:
        candidate = Path(path)
        if candidate == raced_directory:
            original_mkdir(candidate, mode)
            raise FileExistsError(str(candidate))
        original_mkdir(candidate, mode)

    monkeypatch.setattr(os, "mkdir", race_mkdir)
    monkeypatch.setattr(
        core,
        "_fsync_directory",
        lambda path: flushed.append(path),
    )

    store.put_object("stage", {"value": 1})

    assert raced_directory in flushed
    assert store.root in flushed


def test_evidence_store_preserves_indeterminate_lock_after_parent_fsync_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="2" * 64)
    payload = {"value": 1}
    digest = core.canonical_sha256(payload)
    target_parent = store.root / "objects" / "stage" / digest[:2]
    target_parent.mkdir(parents=True)
    target_parent_flushes = 0

    def fail_fsync(path: Path) -> None:
        nonlocal target_parent_flushes
        if path == target_parent:
            target_parent_flushes += 1
            if target_parent_flushes == 2:
                raise OSError("injected parent fsync failure")

    monkeypatch.setattr(core, "_fsync_directory", fail_fsync)
    with pytest.raises(ExecutionEvidenceError, match="commit is indeterminate"):
        store.put_object("stage", payload)

    objects = list((store.root / "objects" / "stage").rglob("*.json"))
    locks = list((store.root / "objects" / "stage").rglob("*.lock"))
    assert len(objects) == 1
    assert len(locks) == 1
    monkeypatch.undo()
    with pytest.raises(ExecutionEvidenceError, match="write lock exists"):
        store.put_object("stage", payload)
    with pytest.raises(EvidenceDrift, match="not sealed-ready"):
        store.inventory()


@pytest.mark.skipif(os.name != "nt", reason="requires native Windows filesystem")
def test_windows_directory_flush_uses_native_write_capable_handle(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "flush-target"
    directory.mkdir()
    core._fsync_directory(directory)


def test_holdout_chunk_requires_metric_replay(tmp_path: Path) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="3" * 64)
    outcome = _zero_outcome()
    trajectory = outcome["trajectory"]
    metrics = outcome["metrics"]
    payload = {
        "schema": "rq2_joint_deliverability_holdout_chunk_v1",
        "cell_id": "cell",
        "power_block_id": "power",
        "conditioned_power_probability": 1.0,
        "policy_parameters": _zero_policy(),
        "workloads": [
            {
                "workload_block_id": "workload",
                "workload_probability": 1.0,
                "available_flexibility": [1.0] * 24,
                "connected_demand": [1.0] * 24,
                "arms": {
                    arm_id: {
                        "capacity": 1.0,
                        "raw_grid_request": [0.0] * 24,
                        "raw_cfe_request": [0.0] * 24,
                        "recovery_headroom": [1.0] * 24,
                        "trajectory": trajectory,
                        "metrics": metrics,
                    }
                    for arm_id in FOUR_ARM_IDS
                },
            }
        ],
    }
    pointer = commit_holdout_chunk(
        store,
        payload,
        time_step_hours=1.0,
        tolerance=1.0e-6,
        terminal_recovery_debt_limit=0.0,
    )
    assert store.load("holdout", "cell__power") == payload
    assert len(str(pointer["object_sha256"])) == 64

    forged = deepcopy(payload)
    forged["cell_id"] = "forged"
    forged["workloads"][0]["arms"][FOUR_ARM_IDS[0]]["metrics"][
        "joint_service_failure"
    ] = True
    with pytest.raises(EvidenceDrift, match="do not replay"):
        commit_holdout_chunk(
            store,
            forged,
            time_step_hours=1.0,
            tolerance=1.0e-6,
            terminal_recovery_debt_limit=0.0,
        )


def test_holdout_chunk_independently_recomputes_metrics(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="4" * 64)
    outcome = _zero_outcome()
    forged_metrics = deepcopy(outcome["metrics"])
    forged_metrics["joint_service_failure"] = True
    payload = {
        "schema": "rq2_joint_deliverability_holdout_chunk_v1",
        "cell_id": "cell",
        "power_block_id": "power",
        "conditioned_power_probability": 1.0,
        "policy_parameters": _zero_policy(),
        "workloads": [
            {
                "workload_block_id": "workload",
                "workload_probability": 1.0,
                "available_flexibility": [1.0] * 24,
                "connected_demand": [1.0] * 24,
                "arms": {
                    arm_id: {
                        "capacity": 1.0,
                        "raw_grid_request": [0.0] * 24,
                        "raw_cfe_request": [0.0] * 24,
                        "recovery_headroom": [1.0] * 24,
                        "trajectory": outcome["trajectory"],
                        "metrics": forged_metrics,
                    }
                    for arm_id in FOUR_ARM_IDS
                },
            }
        ],
    }
    monkeypatch.setattr(
        core,
        "execute_holdout_policy",
        lambda **_kwargs: {
            "trajectory": outcome["trajectory"],
            "metrics": forged_metrics,
        },
    )

    with pytest.raises(EvidenceDrift, match="independently replay"):
        commit_holdout_chunk(
            store,
            payload,
            time_step_hours=1.0,
            tolerance=1.0e-6,
            terminal_recovery_debt_limit=0.0,
        )


def test_streaming_holdout_and_metric_replay(tmp_path: Path) -> None:
    design = _scientific()
    cells = expand_registered_cells(design)
    resolved_arm = {
        "status": "resolved",
        "reported_point": 1.0,
        "full_support_audit": {"status": "passed"},
    }
    capacity_rows = []
    for index, cell in enumerate(cells):
        arms = {
            arm_id: (deepcopy(resolved_arm) if index == 0 else {"status": "unresolved"})
            for arm_id in FOUR_ARM_IDS
        }
        capacity_rows.append(
            {
                "cell_id": cell.cell_id,
                "parameters": asdict(cell),
                "arms": arms,
            }
        )
    capacity = {
        "schema": "rq2_joint_deliverability_capacity_frontier_v3",
        "cells": capacity_rows,
    }
    power = PowerBlock(
        block_id="power",
        split="holdout",
        probability=1.0,
        source_hours=tuple(range(24)),
        cfe_call_fraction_at_alpha_1=(0.0,) * 24,
        grid_need=(0.0,) * 24,
        state=FINITE_GRID_NEED,
    )
    workload = WorkloadBlock(
        block_id="workload",
        split="holdout",
        probability=1.0,
        source_relative_hours=tuple(range(24)),
        raw_workload_fraction=(1.0,) * 24,
    )
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="7" * 64)
    summary = core._stream_holdout_stage(
        design,
        capacity_frontier=capacity,
        holdout_power_blocks=(power,),
        holdout_workload_blocks=(workload,),
        store=store,
        commit=True,
    )
    matrices = replay_holdout_metric_matrices(
        store,
        cell_id=cells[0].cell_id,
        power_ids=["power"],
        workload_ids=["workload"],
        time_step_hours=1.0,
        tolerance=1.0e-6,
        terminal_recovery_debt_limit=0.0,
    )

    assert summary["trajectory_chunk_count"] == 1
    assert all(values[("power", "workload")] == 0.0 for values in matrices.values())
    assert len(store.keys("holdout")) == 1
    matrix_pointer = core.commit_holdout_metric_matrices(
        store,
        cell_id=cells[0].cell_id,
        power_ids=["power"],
        workload_ids=["workload"],
        matrices=matrices,
    )
    replayed_matrices, matrix_sha256 = core.load_holdout_metric_matrices(
        store,
        cell_id=cells[0].cell_id,
        power_ids=["power"],
        workload_ids=["workload"],
    )
    assert replayed_matrices == matrices
    assert matrix_sha256 == matrix_pointer["object_sha256"]
    assert store.inventory()["schema"] == (
        "rq2_joint_deliverability_evidence_inventory_v2"
    )
    preseed_store = EvidenceStore(
        tmp_path / "preseed-evidence",
        run_identity_sha256="5" * 64,
    )
    source_chunk = store.load("holdout", f"{cells[0].cell_id}__power")
    preseed_store.commit("holdout", f"{cells[0].cell_id}__power", source_chunk)
    forged_matrices = deepcopy(matrices)
    forged_matrices[REGISTERED_METRICS[0]][("power", "workload")] = 1.0
    core.commit_holdout_metric_matrices(
        preseed_store,
        cell_id=cells[0].cell_id,
        power_ids=["power"],
        workload_ids=["workload"],
        matrices=forged_matrices,
    )
    with pytest.raises(EvidenceDrift, match="immutable evidence drifted"):
        core.replay_and_commit_holdout_metric_matrices(
            preseed_store,
            cell_id=cells[0].cell_id,
            power_ids=["power"],
            workload_ids=["workload"],
            time_step_hours=1.0,
            tolerance=1.0e-6,
            terminal_recovery_debt_limit=0.0,
        )
    forged_chunk = deepcopy(store.load("holdout", f"{cells[0].cell_id}__power"))
    forged_chunk["extra"] = "forged"
    forged_digest = store.put_object("holdout", forged_chunk)
    pointer_path = (
        store.root / "checkpoints" / "holdout" / f"{cells[0].cell_id}__power.json"
    )
    pointer_path.write_bytes(
        canonical_json_bytes(
            {
                "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
                "run_identity_sha256": store.run_identity_sha256,
                "stage": "holdout",
                "key": f"{cells[0].cell_id}__power",
                "object_sha256": forged_digest,
            }
        )
    )
    with pytest.raises(EvidenceDrift, match="holdout_chunk_stream_sha256|identity"):
        core.load_holdout_metric_matrices(
            store,
            cell_id=cells[0].cell_id,
            power_ids=["power"],
            workload_ids=["workload"],
        )

    forged_store = EvidenceStore(
        tmp_path / "forged-evidence",
        run_identity_sha256="6" * 64,
    )
    forged = deepcopy(store.load("holdout", f"{cells[0].cell_id}__power"))
    forged["workloads"][0]["arms"][FOUR_ARM_IDS[0]]["raw_grid_request"][0] = 0.5
    forged_store.commit("holdout", f"{cells[0].cell_id}__power", forged)
    with pytest.raises(EvidenceDrift, match="policy replay"):
        replay_holdout_metric_matrices(
            forged_store,
            cell_id=cells[0].cell_id,
            power_ids=["power"],
            workload_ids=["workload"],
            time_step_hours=1.0,
            tolerance=1.0e-6,
            terminal_recovery_debt_limit=0.0,
        )


def test_formal_holdout_entry_requires_exact_registered_dimensions(
    tmp_path: Path,
) -> None:
    design = _scientific()
    capacity = _synthetic_unresolved_capacity_frontier()
    one_power = PowerBlock(
        block_id="power",
        split="holdout",
        probability=1.0,
        source_hours=tuple(range(24)),
        cfe_call_fraction_at_alpha_1=(0.0,) * 24,
        grid_need=(0.0,) * 24,
        state=FINITE_GRID_NEED,
    )
    one_workload = WorkloadBlock(
        block_id="workload",
        split="holdout",
        probability=1.0,
        source_relative_hours=tuple(range(24)),
        raw_workload_fraction=(1.0,) * 24,
    )
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="6" * 64)
    one_block_audit = {
        "schema": "rq2_joint_deliverability_input_audit_v1",
        "registered_inputs_ready": True,
        "packages": {
            "dispatched_grid": {
                "status": "verified",
                "holdout_block_inventory_sha256": (
                    core.power_block_inventory_sha256((one_power,))
                ),
            },
            "workload": {
                "status": "verified",
                "holdout_block_inventory_sha256": (
                    core.workload_block_inventory_sha256((one_workload,))
                ),
            },
        },
    }
    with pytest.raises(EvidenceDrift, match="registered holdout block inventory"):
        core._stream_holdout_stage_from_audit(
            design,
            capacity_frontier=capacity,
            registered_input_audit=one_block_audit,
            training_power_blocks=(),
            holdout_power_blocks=(one_power,),
            training_workload_blocks=(),
            holdout_workload_blocks=(one_workload,),
            store=store,
        )

    power_blocks = tuple(
        PowerBlock(
            block_id=f"p{index:03d}",
            split="holdout",
            probability=1.0 / 530,
            source_hours=tuple(range(24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(0.0,) * 24,
            state=FINITE_GRID_NEED,
        )
        for index in range(530)
    )
    workload_blocks = tuple(
        WorkloadBlock(
            block_id=f"w{index:02d}",
            split="holdout",
            probability=1.0 / 34,
            source_relative_hours=tuple(range(24)),
            raw_workload_fraction=(1.0,) * 24,
        )
        for index in range(34)
    )
    training_power_blocks = tuple(
        PowerBlock(
            block_id=f"tp{index:03d}",
            split="training",
            probability=1.0 / 541,
            source_hours=tuple(range(24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(0.0,) * 24,
            state=FINITE_GRID_NEED,
        )
        for index in range(541)
    )
    training_workload_blocks = tuple(
        WorkloadBlock(
            block_id=f"tw{index:02d}",
            split="training",
            probability=1.0 / 34,
            source_relative_hours=tuple(range(24)),
            raw_workload_fraction=(1.0,) * 24,
        )
        for index in range(34)
    )
    registered_input_audit = {
        "schema": "rq2_joint_deliverability_input_audit_v1",
        "registered_inputs_ready": True,
        "packages": {
            "dispatched_grid": {
                "status": "verified",
                "training_block_inventory_sha256": (
                    core.power_block_inventory_sha256(training_power_blocks)
                ),
                "holdout_block_inventory_sha256": (
                    core.power_block_inventory_sha256(power_blocks)
                ),
            },
            "workload": {
                "status": "verified",
                "training_block_inventory_sha256": (
                    core.workload_block_inventory_sha256(training_workload_blocks)
                ),
                "holdout_block_inventory_sha256": (
                    core.workload_block_inventory_sha256(workload_blocks)
                ),
            },
        },
    }
    drifted_power = list(power_blocks)
    drifted_power[0] = PowerBlock(
        **{
            **asdict(drifted_power[0]),
            "source_hours": tuple(range(1, 25)),
        }
    )
    with pytest.raises(EvidenceDrift, match="audited input authority"):
        core._stream_holdout_stage_from_audit(
            design,
            capacity_frontier=capacity,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power_blocks,
            holdout_power_blocks=tuple(drifted_power),
            training_workload_blocks=training_workload_blocks,
            holdout_workload_blocks=workload_blocks,
            store=store,
        )
    drifted_workload = list(workload_blocks)
    drifted_workload[0] = WorkloadBlock(
        **{
            **asdict(drifted_workload[0]),
            "raw_workload_fraction": (0.5,) + (1.0,) * 23,
        }
    )
    with pytest.raises(EvidenceDrift, match="audited input authority"):
        core._stream_holdout_stage_from_audit(
            design,
            capacity_frontier=capacity,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power_blocks,
            holdout_power_blocks=power_blocks,
            training_workload_blocks=training_workload_blocks,
            holdout_workload_blocks=tuple(drifted_workload),
            store=store,
        )
    with pytest.raises(EvidenceDrift, match="planning evidence authority"):
        core._stream_holdout_stage_from_audit(
            design,
            capacity_frontier=capacity,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power_blocks,
            holdout_power_blocks=power_blocks,
            training_workload_blocks=training_workload_blocks,
            holdout_workload_blocks=workload_blocks,
            store=store,
        )
    forged_capacity = deepcopy(capacity)
    forged_capacity["cells"][0]["arms"][FOUR_ARM_IDS[0]]["status"] = "resolved"
    forged_store = EvidenceStore(
        tmp_path / "forged-planning",
        run_identity_sha256="7" * 64,
    )
    _commit_synthetic_planning_authority(
        forged_store,
        input_audit=registered_input_audit,
        capacity_frontier=forged_capacity,
    )
    with pytest.raises(EvidenceDrift, match="planning evidence authority drifted"):
        core._stream_holdout_stage_from_audit(
            design,
            capacity_frontier=forged_capacity,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power_blocks,
            holdout_power_blocks=power_blocks,
            training_workload_blocks=training_workload_blocks,
            holdout_workload_blocks=workload_blocks,
            store=forged_store,
        )
    _commit_synthetic_planning_authority(
        store,
        input_audit=registered_input_audit,
        capacity_frontier=capacity,
    )
    drifted_design = deepcopy(design)
    drifted_design["temporal_envelope"]["minimum_recovery_hours"] = 999.0
    with pytest.raises(EvidenceDrift, match="planning evidence authority drifted"):
        core._stream_holdout_stage_from_audit(
            drifted_design,
            capacity_frontier=capacity,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power_blocks,
            holdout_power_blocks=power_blocks,
            training_workload_blocks=training_workload_blocks,
            holdout_workload_blocks=workload_blocks,
            store=store,
        )
    with pytest.raises(EvidenceDrift, match="planning evidence authority drifted"):
        core._stream_holdout_stage_from_audit(
            design,
            capacity_frontier=capacity,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power_blocks,
            holdout_power_blocks=power_blocks,
            training_workload_blocks=training_workload_blocks,
            holdout_workload_blocks=workload_blocks,
            store=store,
        )


def test_holdout_resume_validates_later_checkpoint_before_any_write(
    tmp_path: Path,
) -> None:
    design = _scientific()
    cells = expand_registered_cells(design)
    resolved_arm = {
        "status": "resolved",
        "reported_point": 1.0,
        "full_support_audit": {"status": "passed"},
    }
    capacity_rows = []
    for index, cell in enumerate(cells):
        capacity_rows.append(
            {
                "cell_id": cell.cell_id,
                "parameters": asdict(cell),
                "arms": {
                    arm_id: (
                        deepcopy(resolved_arm)
                        if index == 0
                        else {"status": "unresolved"}
                    )
                    for arm_id in FOUR_ARM_IDS
                },
            }
        )
    capacity = {
        "schema": "rq2_joint_deliverability_capacity_frontier_v3",
        "cells": capacity_rows,
    }
    power_blocks = tuple(
        PowerBlock(
            block_id=block_id,
            split="holdout",
            probability=0.5,
            source_hours=tuple(range(offset, offset + 24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(0.0,) * 24,
            state=FINITE_GRID_NEED,
        )
        for block_id, offset in (("p0", 0), ("p1", 24))
    )
    workload = WorkloadBlock(
        block_id="workload",
        split="holdout",
        probability=1.0,
        source_relative_hours=tuple(range(24)),
        raw_workload_fraction=(1.0,) * 24,
    )
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="6" * 64)
    forged_arms = deepcopy(capacity_rows[0]["arms"])
    for arm in forged_arms.values():
        arm["reported_point"] = 0.5
    forged_late_chunk = core._holdout_chunk_payload(
        design,
        cell=cells[0],
        raw_arms=forged_arms,
        power=power_blocks[1],
        workloads=(workload,),
    )
    store.commit(
        "holdout",
        f"{cells[0].cell_id}__p1",
        forged_late_chunk,
    )

    with pytest.raises(EvidenceDrift, match="not a prefix"):
        core._stream_holdout_stage(
            design,
            capacity_frontier=capacity,
            holdout_power_blocks=power_blocks,
            holdout_workload_blocks=(workload,),
            store=store,
            commit=False,
        )
    assert store.keys("holdout") == (f"{cells[0].cell_id}__p1",)


def test_bootstrap_aggregate_rejects_unreplayed_endpoint_payloads(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="4" * 64)
    draws = [
        {"replicate": 0, "power": {"p": 1.0}, "workload": {"w": 1.0}},
        {"replicate": 1, "power": {"p": 1.0}, "workload": {"w": 1.0}},
    ]
    draw_sha = bootstrap_draw_stream_sha256(draws)
    matrices = {metric: {("p", "w"): 0.5} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(store, cell_id="cell", power_id="p")
    matrix_pointer = core.commit_holdout_metric_matrices(
        store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    for replicate in range(2):
        endpoints = {
            metric: _checkpoint_endpoint(
                metric,
                float(replicate),
                float(replicate + 1),
            )
            for metric in REGISTERED_METRICS
        }
        commit_bootstrap_cell(
            store,
            replicate=replicate,
            cell_id="cell",
            endpoint_invocation_start_ordinal=(replicate * len(REGISTERED_METRICS) * 2),
            draw_stream_sha256=draw_sha,
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_matrix_sha256=matrix_pointer["object_sha256"],
            endpoints=endpoints,
        )
    with pytest.raises(EvidenceDrift, match="certificate identity"):
        core._aggregate_bootstrap_checkpoints(
            store,
            draws=draws,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            draw_stream_sha256=draw_sha,
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (
                matrices,
                matrix_pointer["object_sha256"],
            ),
        )
    with pytest.raises(EvidenceDrift, match="draw order drifted"):
        bootstrap_draw_stream_sha256([{"replicate": 1, "power": {}, "workload": {}}])


def test_bootstrap_checkpoint_rejects_identity_and_payload_drift(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="5" * 64)
    endpoints = {
        metric: _checkpoint_endpoint(metric, 0.0, 1.0) for metric in REGISTERED_METRICS
    }
    commit_bootstrap_cell(
        store,
        replicate=0,
        cell_id="cell",
        endpoint_invocation_start_ordinal=0,
        draw_stream_sha256="6" * 64,
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_matrix_sha256="7" * 64,
        endpoints=endpoints,
    )
    changed = deepcopy(endpoints)
    changed[REGISTERED_METRICS[0]] = _checkpoint_endpoint(
        REGISTERED_METRICS[0],
        0.0,
        2.0,
    )
    with pytest.raises(EvidenceDrift, match="immutable evidence drifted"):
        commit_bootstrap_cell(
            store,
            replicate=0,
            cell_id="cell",
            endpoint_invocation_start_ordinal=0,
            draw_stream_sha256="6" * 64,
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_matrix_sha256="7" * 64,
            endpoints=changed,
        )
    with pytest.raises(EvidenceDrift, match="inventory is incomplete"):
        core._aggregate_bootstrap_checkpoints(
            store,
            draws=[
                {"replicate": 0, "power": {"p": 1.0}, "workload": {"w": 1.0}},
                {"replicate": 1, "power": {"p": 1.0}, "workload": {"w": 1.0}},
            ],
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            draw_stream_sha256="6" * 64,
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (
                {metric: {("p", "w"): 0.0} for metric in REGISTERED_METRICS},
                "7" * 64,
            ),
        )
    ordinal_store = EvidenceStore(
        tmp_path / "ordinal-drift",
        run_identity_sha256="7" * 64,
    )
    matrices = {metric: {("p", "w"): 0.0} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(ordinal_store, cell_id="cell", power_id="p")
    matrix_pointer = core.commit_holdout_metric_matrices(
        ordinal_store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    commit_bootstrap_cell(
        ordinal_store,
        replicate=0,
        cell_id="cell",
        endpoint_invocation_start_ordinal=len(REGISTERED_METRICS) * 2,
        draw_stream_sha256="6" * 64,
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_matrix_sha256=matrix_pointer["object_sha256"],
        endpoints=endpoints,
    )
    with pytest.raises(EvidenceDrift, match="checkpoint identity drifted"):
        core._aggregate_bootstrap_checkpoints(
            ordinal_store,
            draws=[{"replicate": 0, "power": {"p": 1.0}, "workload": {"w": 1.0}}],
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            draw_stream_sha256="6" * 64,
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (
                matrices,
                str(matrix_pointer["object_sha256"]),
            ),
        )


def test_bootstrap_execution_resumes_without_repeating_endpoints(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="8" * 64)
    draws = [
        {"replicate": 0, "power": {"p": 1.0}, "workload": {"w": 1.0}},
        {"replicate": 1, "power": {"p": 1.0}, "workload": {"w": 1.0}},
    ]
    matrices = {metric: {("p", "w"): 0.5} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(store, cell_id="cell", power_id="p")
    matrix_pointer = core.commit_holdout_metric_matrices(
        store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )

    def load_metric_evidence(
        _cell_id: str,
    ) -> tuple[dict[str, dict[tuple[str, str], float]], str]:
        return matrices, str(matrix_pointer["object_sha256"])

    draw_sha = bootstrap_draw_stream_sha256(draws)
    first = core._execute_bootstrap_draws(
        draws=draws,
        draw_stream_sha256=draw_sha,
        state_by_power_id={"p": FINITE_GRID_NEED},
        cell_ids=["cell"],
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_loader=load_metric_evidence,
        metric_prevalidator=load_metric_evidence,
        store=store,
    )
    second = core._execute_bootstrap_draws(
        draws=draws,
        draw_stream_sha256=draw_sha,
        state_by_power_id={"p": FINITE_GRID_NEED},
        cell_ids=["cell"],
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_loader=load_metric_evidence,
        metric_prevalidator=load_metric_evidence,
        store=store,
    )

    assert first["status"] == "resolved"
    assert first["committed_checkpoints"] == 2
    assert first["endpoint_solver_calls"] == 92
    assert first["aggregate"]["intervals"]["cell"][REGISTERED_METRICS[0]]["lower"] == [
        0.5,
        0.5,
    ]
    assert second["status"] == "resolved"
    assert second["resumed_checkpoints"] == 2
    assert second["endpoint_solver_calls"] == 0
    with pytest.raises(EvidenceDrift, match="checkpoint identity drifted"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=draw_sha,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="c" * 64,
            metric_loader=load_metric_evidence,
            metric_prevalidator=load_metric_evidence,
            store=store,
        )
    with pytest.raises(EvidenceDrift, match="checkpoint identity drifted"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=draw_sha,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (matrices, "9" * 64),
            metric_prevalidator=load_metric_evidence,
            store=store,
        )
    forged_matrices = {metric: {("p", "w"): 0.75} for metric in REGISTERED_METRICS}
    with pytest.raises(EvidenceDrift, match="certificate does not replay"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=draw_sha,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (
                forged_matrices,
                matrix_pointer["object_sha256"],
            ),
            metric_prevalidator=load_metric_evidence,
            store=store,
        )
    persisted_endpoints = store.load("bootstrap", "r001__cell")["endpoints"]
    forged_transport = deepcopy(
        persisted_endpoints[REGISTERED_METRICS[0]]["certificate"]
    )
    forged_transport["lower"]["solver_status"] = "forged"
    with pytest.raises(EvidenceDrift, match="solver status drifted"):
        core._validate_transport_evidence(
            forged_transport,
            metric_name=REGISTERED_METRICS[0],
            row_probabilities=[1.0],
            column_probabilities=[1.0],
            metric_matrix=[[0.5]],
        )
    bad_store = EvidenceStore(
        tmp_path / "bad-late-checkpoint",
        run_identity_sha256="f" * 64,
    )
    _commit_minimal_holdout_source(bad_store, cell_id="cell", power_id="p")
    bad_matrix_pointer = core.commit_holdout_metric_matrices(
        bad_store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    commit_bootstrap_cell(
        bad_store,
        replicate=1,
        cell_id="cell",
        endpoint_invocation_start_ordinal=len(REGISTERED_METRICS) * 2,
        draw_stream_sha256=draw_sha,
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="c" * 64,
        metric_matrix_sha256=bad_matrix_pointer["object_sha256"],
        endpoints=persisted_endpoints,
    )
    endpoint_calls = 0

    def reject_endpoint_call(*_args: object, **_kwargs: object) -> object:
        nonlocal endpoint_calls
        endpoint_calls += 1
        raise AssertionError("endpoint solver ran before resume prevalidation")

    def load_bad_metric_evidence(
        _cell_id: str,
    ) -> tuple[dict[str, dict[tuple[str, str], float]], str]:
        return matrices, str(bad_matrix_pointer["object_sha256"])

    with pytest.raises(EvidenceDrift, match="checkpoint identity drifted"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=draw_sha,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=load_bad_metric_evidence,
            metric_prevalidator=load_bad_metric_evidence,
            store=bad_store,
            endpoint_solver=reject_endpoint_call,
        )
    assert endpoint_calls == 0
    assert bad_store.keys("bootstrap") == ("r001__cell",)

    order_store = EvidenceStore(
        tmp_path / "out-of-order-checkpoint",
        run_identity_sha256="d" * 64,
    )
    _commit_minimal_holdout_source(order_store, cell_id="cell", power_id="p")
    order_matrix_pointer = core.commit_holdout_metric_matrices(
        order_store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    commit_bootstrap_cell(
        order_store,
        replicate=1,
        cell_id="cell",
        endpoint_invocation_start_ordinal=len(REGISTERED_METRICS) * 2,
        draw_stream_sha256=draw_sha,
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_matrix_sha256=order_matrix_pointer["object_sha256"],
        endpoints=persisted_endpoints,
    )

    def load_order_metric_evidence(
        _cell_id: str,
    ) -> tuple[dict[str, dict[tuple[str, str], float]], str]:
        return matrices, str(order_matrix_pointer["object_sha256"])

    with pytest.raises(EvidenceDrift, match="not a prefix"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=draw_sha,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=load_order_metric_evidence,
            metric_prevalidator=load_order_metric_evidence,
            store=order_store,
            endpoint_solver=reject_endpoint_call,
        )
    assert endpoint_calls == 0
    assert order_store.keys("bootstrap") == ("r001__cell",)

    extra_store = EvidenceStore(
        tmp_path / "extra-checkpoint",
        run_identity_sha256="e" * 64,
    )
    commit_bootstrap_cell(
        extra_store,
        replicate=0,
        cell_id="extra",
        endpoint_invocation_start_ordinal=0,
        draw_stream_sha256=draw_sha,
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_matrix_sha256="d" * 64,
        endpoints=persisted_endpoints,
    )
    with pytest.raises(EvidenceDrift, match="extra key"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=draw_sha,
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (_ for _ in ()).throw(
                AssertionError("metric loader ran before inventory validation")
            ),
            metric_prevalidator=lambda _cell_id: (_ for _ in ()).throw(
                AssertionError("prevalidator ran before inventory validation")
            ),
            store=extra_store,
            endpoint_solver=reject_endpoint_call,
        )
    assert endpoint_calls == 0


def test_bootstrap_endpoint_execution_is_replicate_major_and_ordinal_bound(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OMP_NUM_THREADS", "1")
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="c" * 64)
    power_ids = ["p0", "p1"]
    workload_ids = ["w"]
    matrices_by_cell = {
        cell_id: {
            metric: {
                ("p0", "w"): base,
                ("p1", "w"): base + 1.0,
            }
            for metric in REGISTERED_METRICS
        }
        for cell_id, base in (("a", 0.0), ("b", 10.0))
    }
    for cell_id, matrices in matrices_by_cell.items():
        for power_id in power_ids:
            _commit_minimal_holdout_source(
                store,
                cell_id=cell_id,
                power_id=power_id,
            )
        core.commit_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=power_ids,
            workload_ids=workload_ids,
            matrices=matrices,
        )

    def load_metric_evidence(
        cell_id: str,
    ) -> tuple[dict[str, dict[tuple[str, str], float]], str]:
        return core.load_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=power_ids,
            workload_ids=workload_ids,
        )

    observed: list[tuple[tuple[float, ...], float, str]] = []

    def recording_endpoint_solver(
        row_probabilities: object,
        column_probabilities: object,
        matrix: object,
        *,
        metric_name: str,
    ) -> object:
        rows = list(row_probabilities)  # type: ignore[arg-type]
        values = list(matrix)  # type: ignore[arg-type]
        observed.append(
            (
                tuple(float(value) for value in rows),
                float(values[0][0]),
                metric_name,
            )
        )
        return core.certify_scalar_transport(
            rows,
            list(column_probabilities),  # type: ignore[arg-type]
            values,
            metric_name=metric_name,
        )

    draws = [
        {
            "replicate": 0,
            "power": {"p0": 1.0, "p1": 0.0},
            "workload": {"w": 1.0},
        },
        {
            "replicate": 1,
            "power": {"p0": 0.0, "p1": 1.0},
            "workload": {"w": 1.0},
        },
    ]
    result = core._execute_bootstrap_draws(
        draws=draws,
        draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
        state_by_power_id={
            "p0": FINITE_GRID_NEED,
            "p1": FINITE_GRID_NEED,
        },
        cell_ids=["b", "a"],
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_loader=load_metric_evidence,
        metric_prevalidator=load_metric_evidence,
        store=store,
        endpoint_solver=recording_endpoint_solver,
    )

    metric_count = len(REGISTERED_METRICS)
    assert result["status"] == "resolved"
    assert [(rows, value) for rows, value, _metric in observed[::metric_count]] == [
        ((1.0, 0.0), 0.0),
        ((1.0, 0.0), 10.0),
        ((0.0, 1.0), 0.0),
        ((0.0, 1.0), 10.0),
    ]
    assert [
        store.load("bootstrap", key)["endpoint_invocation_start_ordinal"]
        for key in ("r000__a", "r000__b", "r001__a", "r001__b")
    ] == [0, 46, 92, 138]
    assert all(
        store.load("bootstrap", key)["endpoint_invocation_count"] == 46
        for key in ("r000__a", "r000__b", "r001__a", "r001__b")
    )


def test_bootstrap_prevalidates_matrix_without_checkpoint_before_write(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="d" * 64)
    matrices = {metric: {("p", "w"): 0.5} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(store, cell_id="z", power_id="p")
    core.commit_holdout_metric_matrices(
        store,
        cell_id="z",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    loader_calls = 0
    endpoint_calls = 0

    def reject_loader(_cell_id: str) -> object:
        nonlocal loader_calls
        loader_calls += 1
        raise AssertionError("metric loader ran before matrix prevalidation")

    def reject_prevalidator(_cell_id: str) -> object:
        raise EvidenceDrift("preseeded metric matrix drifted")

    def reject_endpoint(*_args: object, **_kwargs: object) -> object:
        nonlocal endpoint_calls
        endpoint_calls += 1
        raise AssertionError("endpoint solver ran before matrix prevalidation")

    draws = [{"replicate": 0, "power": {"p": 1.0}, "workload": {"w": 1.0}}]
    with pytest.raises(EvidenceDrift, match="preseeded metric matrix drifted"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
            state_by_power_id={"p": FINITE_GRID_NEED},
            cell_ids=["a", "z"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=reject_loader,
            metric_prevalidator=reject_prevalidator,
            store=store,
            endpoint_solver=reject_endpoint,
        )
    assert loader_calls == 0
    assert endpoint_calls == 0
    assert store.keys("bootstrap") == ()


@pytest.mark.parametrize(
    "state_by_power_id",
    (
        {"e": EXOGENOUS_GRID_INFEASIBILITY},
        {
            "e": EXOGENOUS_GRID_INFEASIBILITY,
            "p": FINITE_GRID_NEED,
        },
    ),
)
def test_bootstrap_empty_finite_draw_prevalidates_existing_matrix(
    tmp_path: Path,
    state_by_power_id: dict[str, str],
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="e" * 64)
    matrices = {metric: {("p", "w"): 0.5} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(store, cell_id="cell", power_id="p")
    core.commit_holdout_metric_matrices(
        store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    prevalidation_calls = 0

    def reject_prevalidator(_cell_id: str) -> object:
        nonlocal prevalidation_calls
        prevalidation_calls += 1
        raise EvidenceDrift("empty-draw matrix drifted")

    power_draw = {"e": 1.0}
    if "p" in state_by_power_id:
        power_draw["p"] = 0.0
    draws = [{"replicate": 0, "power": power_draw, "workload": {"w": 1.0}}]
    with pytest.raises(EvidenceDrift, match="empty-draw matrix drifted"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
            state_by_power_id=state_by_power_id,
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (_ for _ in ()).throw(
                AssertionError("metric loader ran")
            ),
            metric_prevalidator=reject_prevalidator,
            store=store,
            endpoint_solver=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("endpoint solver ran")
            ),
        )
    assert prevalidation_calls == 1
    assert store.keys("bootstrap") == ()


def test_bootstrap_aggregate_empty_finite_draw_validates_existing_evidence(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="f" * 64)
    matrices = {metric: {("p", "w"): 0.5} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(store, cell_id="cell", power_id="p")
    core.commit_holdout_metric_matrices(
        store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    loader_calls = 0

    def reject_loader(_cell_id: str) -> object:
        nonlocal loader_calls
        loader_calls += 1
        raise EvidenceDrift("aggregate matrix drifted")

    draws = [
        {
            "replicate": 0,
            "power": {"e": 1.0, "p": 0.0},
            "workload": {"w": 1.0},
        }
    ]
    with pytest.raises(EvidenceDrift, match="aggregate matrix drifted"):
        core._aggregate_bootstrap_checkpoints(
            store,
            draws=draws,
            state_by_power_id={
                "e": EXOGENOUS_GRID_INFEASIBILITY,
                "p": FINITE_GRID_NEED,
            },
            cell_ids=["cell"],
            draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=reject_loader,
        )
    assert loader_calls == 1
    with pytest.raises(EvidenceDrift, match="metric-matrix inventory is incomplete"):
        core._aggregate_bootstrap_checkpoints(
            store,
            draws=[
                {
                    "replicate": 0,
                    "power": {"e": 1.0},
                    "workload": {"w": 1.0},
                }
            ],
            state_by_power_id={"e": EXOGENOUS_GRID_INFEASIBILITY},
            cell_ids=[],
            draw_stream_sha256=bootstrap_draw_stream_sha256(
                [
                    {
                        "replicate": 0,
                        "power": {"e": 1.0},
                        "workload": {"w": 1.0},
                    }
                ]
            ),
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (_ for _ in ()).throw(
                AssertionError("metric loader ran")
            ),
        )
    empty_store = EvidenceStore(
        tmp_path / "empty-evidence",
        run_identity_sha256="0" * 64,
    )
    unresolved = core._aggregate_bootstrap_checkpoints(
        empty_store,
        draws=draws,
        state_by_power_id={
            "e": EXOGENOUS_GRID_INFEASIBILITY,
            "p": FINITE_GRID_NEED,
        },
        cell_ids=["cell"],
        draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_loader=lambda _cell_id: (_ for _ in ()).throw(
            AssertionError("metric loader ran")
        ),
    )
    assert unresolved["status"] == "unresolved"
    assert unresolved["reason"] == "finite_service_identification_unresolved"


def test_bootstrap_empty_finite_draw_rejects_existing_checkpoint(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="1" * 64)
    matrices = {metric: {("p", "w"): 0.5} for metric in REGISTERED_METRICS}
    _commit_minimal_holdout_source(store, cell_id="cell", power_id="p")
    matrix_pointer = core.commit_holdout_metric_matrices(
        store,
        cell_id="cell",
        power_ids=["p"],
        workload_ids=["w"],
        matrices=matrices,
    )
    draws = [
        {
            "replicate": 0,
            "power": {"e": 1.0, "p": 0.0},
            "workload": {"w": 1.0},
        }
    ]
    commit_bootstrap_cell(
        store,
        replicate=0,
        cell_id="cell",
        endpoint_invocation_start_ordinal=0,
        draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
        input_audit_object_sha256="a" * 64,
        planning_index_object_sha256="b" * 64,
        metric_matrix_sha256=str(matrix_pointer["object_sha256"]),
        endpoints={
            metric: _checkpoint_endpoint(metric, 0.0, 1.0)
            for metric in REGISTERED_METRICS
        },
    )

    with pytest.raises(EvidenceDrift, match="checkpoint exists after empty"):
        core._execute_bootstrap_draws(
            draws=draws,
            draw_stream_sha256=bootstrap_draw_stream_sha256(draws),
            state_by_power_id={
                "e": EXOGENOUS_GRID_INFEASIBILITY,
                "p": FINITE_GRID_NEED,
            },
            cell_ids=["cell"],
            input_audit_object_sha256="a" * 64,
            planning_index_object_sha256="b" * 64,
            metric_loader=lambda _cell_id: (
                matrices,
                str(matrix_pointer["object_sha256"]),
            ),
            metric_prevalidator=lambda _cell_id: (
                matrices,
                str(matrix_pointer["object_sha256"]),
            ),
            store=store,
            endpoint_solver=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("endpoint solver ran")
            ),
        )


def test_synthetic_bootstrap_helper_derives_sealed_v5_draw_stream(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def capture(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "captured"}

    execute_draws = core._execute_bootstrap_draws
    registered_cells = core._registered_bootstrap_cells
    monkeypatch.setattr(core, "_execute_bootstrap_draws", capture)
    power_ids = [f"p{index:03d}" for index in range(530)]
    workload_ids = [f"w{index:02d}" for index in range(34)]
    power_blocks = tuple(
        PowerBlock(
            block_id=block_id,
            split="holdout",
            probability=1.0 / 530,
            source_hours=tuple(range(24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(0.0,) * 24,
            state=FINITE_GRID_NEED,
        )
        for block_id in power_ids
    )
    workload_blocks = tuple(
        WorkloadBlock(
            block_id=block_id,
            split="holdout",
            probability=1.0 / 34,
            source_relative_hours=tuple(range(24)),
            raw_workload_fraction=(1.0,) * 24,
        )
        for block_id in workload_ids
    )
    input_audit = {
        "schema": "rq2_joint_deliverability_input_audit_v1",
        "registered_inputs_ready": True,
        "packages": {
            "dispatched_grid": {
                "status": "verified",
                "training_block_inventory_sha256": "2" * 64,
                "holdout_block_inventory_sha256": (
                    core.power_block_inventory_sha256(power_blocks)
                ),
            },
            "workload": {
                "status": "verified",
                "training_block_inventory_sha256": "3" * 64,
                "holdout_block_inventory_sha256": (
                    core.workload_block_inventory_sha256(workload_blocks)
                ),
            },
        },
    }
    evidence_store = EvidenceStore(
        tmp_path / "evidence",
        run_identity_sha256="8" * 64,
    )
    status_mode = {"value": "resolved"}

    def synthetic_registered_cells(
        _store: EvidenceStore,
        **_kwargs: object,
    ) -> tuple[tuple[str, ...], dict[str, str], dict[str, str]]:
        cell_ids = tuple(
            cell.cell_id for cell in expand_registered_cells(_scientific())
        )
        statuses = {cell_id: status_mode["value"] for cell_id in cell_ids}
        return (
            cell_ids if status_mode["value"] == "resolved" else (),
            statuses,
            {
                "input_audit_object_sha256": core.canonical_sha256(input_audit),
                "planning_index_object_sha256": "4" * 64,
            },
        )

    monkeypatch.setattr(
        core,
        "_registered_bootstrap_cells",
        synthetic_registered_cells,
    )
    result = core._execute_bootstrap_resumable_from_audit(
        design=_scientific(),
        registered_input_audit=input_audit,
        training_power_blocks=(),
        holdout_power_blocks=power_blocks,
        training_workload_blocks=(),
        holdout_workload_blocks=workload_blocks,
        store=evidence_store,
    )

    assert result["status"] == "captured"
    assert result["non_evaluable_cell_ids"] == []
    assert set(result["cell_statuses"].values()) == {"resolved"}
    assert len(captured["draws"]) == 200
    assert len(captured["cell_ids"]) == 46
    assert len(str(captured["draw_stream_sha256"])) == 64
    assert captured["input_audit_object_sha256"] == core.canonical_sha256(input_audit)
    assert len(str(captured["planning_index_object_sha256"])) == 64
    non_evaluable_store = EvidenceStore(
        tmp_path / "non-evaluable",
        run_identity_sha256="d" * 64,
    )
    status_mode["value"] = "not_evaluable_capacity_unresolved"

    def capture_resolved(**kwargs: object) -> dict[str, object]:
        captured.update(kwargs)
        return {"status": "resolved", "aggregate": {"intervals": {}}}

    monkeypatch.setattr(core, "_execute_bootstrap_draws", capture_resolved)
    non_evaluable = core._execute_bootstrap_resumable_from_audit(
        design=_scientific(),
        registered_input_audit=input_audit,
        training_power_blocks=(),
        holdout_power_blocks=power_blocks,
        training_workload_blocks=(),
        holdout_workload_blocks=workload_blocks,
        store=non_evaluable_store,
    )
    assert non_evaluable["status"] == "unresolved"
    assert non_evaluable["reason"] == "non_evaluable_holdout_cells"
    assert len(non_evaluable["non_evaluable_cell_ids"]) == 46
    with pytest.raises(EvidenceDrift, match="audited input authority"):
        core._execute_bootstrap_resumable_from_audit(
            design=_scientific(),
            registered_input_audit=input_audit,
            training_power_blocks=(),
            holdout_power_blocks=power_blocks[:-1],
            training_workload_blocks=(),
            holdout_workload_blocks=workload_blocks,
            store=EvidenceStore(
                tmp_path / "wrong-dimensions",
                run_identity_sha256="a" * 64,
            ),
        )
    monkeypatch.setattr(core, "_execute_bootstrap_draws", execute_draws)
    e0_power_blocks = tuple(
        PowerBlock(
            **{
                **asdict(block),
                "grid_need": (None,) * 24,
                "state": EXOGENOUS_GRID_INFEASIBILITY,
            }
        )
        for block in power_blocks
    )
    e0_input_audit = deepcopy(input_audit)
    e0_input_audit["packages"]["dispatched_grid"]["holdout_block_inventory_sha256"] = (
        core.power_block_inventory_sha256(e0_power_blocks)
    )
    e0_store = EvidenceStore(
        tmp_path / "all-e0",
        run_identity_sha256="b" * 64,
    )
    status_mode["value"] = "finite_service_identification_unresolved"
    unresolved = core._execute_bootstrap_resumable_from_audit(
        design=_scientific(),
        registered_input_audit=e0_input_audit,
        training_power_blocks=(),
        holdout_power_blocks=e0_power_blocks,
        training_workload_blocks=(),
        holdout_workload_blocks=workload_blocks,
        store=e0_store,
    )
    assert unresolved["status"] == "unresolved"
    assert unresolved["reason"] == "finite_service_identification_unresolved"
    assert unresolved["aggregate"] is None
    aggregate_unresolved = core._aggregate_bootstrap_checkpoints_from_audit(
        e0_store,
        design=_scientific(),
        registered_input_audit=e0_input_audit,
        training_power_blocks=(),
        holdout_power_blocks=e0_power_blocks,
        training_workload_blocks=(),
        holdout_workload_blocks=workload_blocks,
    )
    assert aggregate_unresolved["status"] == "unresolved"
    assert aggregate_unresolved["reason"] == "finite_service_identification_unresolved"
    assert aggregate_unresolved["intervals"] == {}
    assert len(aggregate_unresolved["non_evaluable_cell_ids"]) == 46
    mixed_e0_store = EvidenceStore(
        tmp_path / "mixed-all-e0",
        run_identity_sha256="e" * 64,
    )
    first_cell_id = expand_registered_cells(_scientific())[0].cell_id
    status_mode["value"] = "finite_service_identification_unresolved"

    def mixed_registered_cells(
        _store: EvidenceStore,
        **_kwargs: object,
    ) -> tuple[tuple[str, ...], dict[str, str], dict[str, str]]:
        cell_ids = tuple(
            cell.cell_id for cell in expand_registered_cells(_scientific())
        )
        statuses = {
            cell_id: "finite_service_identification_unresolved" for cell_id in cell_ids
        }
        statuses[first_cell_id] = "not_evaluable_capacity_unresolved"
        return (
            (),
            statuses,
            {
                "input_audit_object_sha256": core.canonical_sha256(e0_input_audit),
                "planning_index_object_sha256": "4" * 64,
            },
        )

    monkeypatch.setattr(core, "_registered_bootstrap_cells", mixed_registered_cells)
    mixed_unresolved = core._aggregate_bootstrap_checkpoints_from_audit(
        mixed_e0_store,
        design=_scientific(),
        registered_input_audit=e0_input_audit,
        training_power_blocks=(),
        holdout_power_blocks=e0_power_blocks,
        training_workload_blocks=(),
        holdout_workload_blocks=workload_blocks,
    )
    assert mixed_unresolved["reason"] == "finite_service_identification_unresolved"
    monkeypatch.setattr(core, "_registered_bootstrap_cells", registered_cells)
    monkeypatch.setattr(
        core,
        "_registered_planning_evidence",
        lambda evidence_store, **_kwargs: {
            "input_audit_object_sha256": core.canonical_sha256(input_audit),
            "planning_index_object_sha256": core.canonical_sha256(
                evidence_store.load("planning_index", "capacity_frontier")
            ),
        },
    )
    closed_store = EvidenceStore(
        tmp_path / "closed-holdout",
        run_identity_sha256="1" * 64,
    )
    _commit_bootstrap_holdout_summary(
        closed_store,
        input_audit=input_audit,
        power_blocks=power_blocks,
        workload_blocks=workload_blocks,
        status="not_evaluable_capacity_unresolved",
    )
    cell_ids, statuses, _authority = core._registered_bootstrap_cells(
        closed_store,
        design=_scientific(),
        registered_input_audit=input_audit,
        training_power_blocks=(),
        power_blocks=power_blocks,
        training_workload_blocks=(),
        workload_blocks=workload_blocks,
    )
    assert cell_ids == ()
    assert set(statuses.values()) == {"not_evaluable_capacity_unresolved"}
    forged_store = EvidenceStore(
        tmp_path / "forged-holdout",
        run_identity_sha256="2" * 64,
    )
    _commit_bootstrap_holdout_summary(
        forged_store,
        input_audit=input_audit,
        power_blocks=power_blocks,
        workload_blocks=workload_blocks,
        status="not_evaluable_capacity_unresolved",
        status_overrides={first_cell_id: "resolved"},
    )
    with pytest.raises(EvidenceDrift, match="summary/chunk closure drifted"):
        core._registered_bootstrap_cells(
            forged_store,
            design=_scientific(),
            registered_input_audit=input_audit,
            training_power_blocks=(),
            power_blocks=power_blocks,
            training_workload_blocks=(),
            workload_blocks=workload_blocks,
        )
    with pytest.raises(TypeError, match="unexpected keyword argument 'draws'"):
        core.execute_bootstrap_resumable(  # type: ignore[call-arg]
            draws=[],
            store=EvidenceStore(
                tmp_path / "second-evidence",
                run_identity_sha256="9" * 64,
            ),
        )
    with pytest.raises(TypeError, match="unexpected keyword argument 'metric_loader'"):
        core.execute_bootstrap_resumable(  # type: ignore[call-arg]
            metric_loader=lambda _cell_id: {},
            store=EvidenceStore(
                tmp_path / "third-evidence",
                run_identity_sha256="c" * 64,
            ),
        )
    with pytest.raises(
        TypeError,
        match="unexpected keyword argument 'registered_input_audit'",
    ):
        core.execute_bootstrap_resumable(  # type: ignore[call-arg]
            registered_input_audit=input_audit,
            store=EvidenceStore(
                tmp_path / "caller-audit",
                run_identity_sha256="d" * 64,
            ),
        )


def test_bootstrap_contract_and_rng_probe_are_fail_closed() -> None:
    contract = deepcopy(_scientific()["bootstrap_contract"])
    contract["pseudorandom_generator"]["seed"] += 1
    with pytest.raises(EvidenceDrift, match="contract drifted"):
        core._registered_bootstrap_draws(
            bootstrap_contract=contract,
            power_ids=["p"],
            power_probabilities=[1.0],
            workload_ids=["w"],
            workload_probabilities=[1.0],
        )


def test_primal_evidence_replays_on_fresh_model(tmp_path: Path) -> None:
    native_log = tmp_path / "native.log"
    native_log.write_text("synthetic native solver log\n", encoding="utf-8")
    certificate = {
        "arm_id": "synthetic",
        "status": "candidate_resolved",
        "incumbent_capacity": 0.5,
    }
    evidence = capture_primal_evidence(
        _model(),
        arm_id="synthetic",
        certificate=certificate,
        native_log_path=native_log,
    )
    replay = replay_primal_evidence(
        _model,
        evidence,
        expected_arm_id="synthetic",
        certificate=certificate,
        native_log=native_log.read_bytes(),
        feasibility_tolerance=1.0e-9,
    )

    assert replay["passed"] is True
    assert replay["arm_id"] == "synthetic"
    assert replay["maximum_constraint_residual"] == 0.0
    with pytest.raises(EvidenceDrift, match="native solver log binding"):
        replay_primal_evidence(
            _model,
            evidence,
            expected_arm_id="synthetic",
            certificate=certificate,
            native_log=b"forged",
            feasibility_tolerance=1.0e-9,
        )
    forged = deepcopy(evidence)
    forged["objective_hex"] = (0.6).hex()
    with pytest.raises(EvidenceDrift, match="objective replay"):
        replay_primal_evidence(
            _model,
            forged,
            expected_arm_id="synthetic",
            certificate=certificate,
            native_log=native_log.read_bytes(),
            feasibility_tolerance=1.0e-9,
        )
    forged = deepcopy(evidence)
    forged["arm_id"] = "other"
    with pytest.raises(EvidenceDrift, match="certificate binding"):
        replay_primal_evidence(
            _model,
            forged,
            expected_arm_id="synthetic",
            certificate=certificate,
            native_log=native_log.read_bytes(),
            feasibility_tolerance=1.0e-9,
        )
    for forged_certificate in (
        {key: value for key, value in certificate.items() if key != "arm_id"},
        {**certificate, "arm_id": "other"},
    ):
        with pytest.raises(EvidenceDrift, match="certificate binding"):
            replay_primal_evidence(
                _model,
                evidence,
                expected_arm_id="synthetic",
                certificate=forged_certificate,
                native_log=native_log.read_bytes(),
                feasibility_tolerance=1.0e-9,
            )
    forged = deepcopy(evidence)
    forged["extra"] = True
    with pytest.raises(EvidenceDrift, match="certificate binding"):
        replay_primal_evidence(
            _model,
            forged,
            expected_arm_id="synthetic",
            certificate=certificate,
            native_log=native_log.read_bytes(),
            feasibility_tolerance=1.0e-9,
        )


def test_solver_callback_persists_native_primal_and_replay(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="9" * 64)
    specification = Rq2SolverSpec(
        name="gurobi",
        expected_package_version="13.0.2",
        threads=4,
        mip_relative_gap=1.0e-6,
        feasibility_tolerance=1.0e-6,
        optimality_tolerance=1.0e-6,
        integer_feasibility_tolerance=1.0e-6,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )

    def model_factory(
        _inputs: JointDeliverabilityPlanningInputs,
        _arm_id: str,
    ) -> ConcreteModel:
        model = ConcreteModel()
        model.capacity = Var(bounds=(0.0, 1.0), initialize=0.5)
        model.minimum = Constraint(expr=model.capacity >= 0.2)
        model.objective = Objective(expr=model.capacity)
        return model

    def solve_driver(
        model: ConcreteModel,
        _specification: Rq2SolverSpec,
        _options: object,
        native_log_path: Path,
    ) -> tuple[object, str]:
        model.capacity.set_value(0.5)
        native_log_path.write_text("synthetic gurobi native log\n", encoding="utf-8")
        result = SimpleNamespace(
            solver=SimpleNamespace(
                termination_condition=TerminationCondition.optimal,
                status=SolverStatus.ok,
            ),
            problem=SimpleNamespace(lower_bound=0.5, upper_bound=0.5),
            solution=[],
        )
        return result, "13.0.2"

    record = core._solve_arm_with_native_evidence(
        _planning_inputs(),
        "network_only_shared",
        specification,
        store=store,
        solve_driver=solve_driver,
        model_factory=model_factory,
    )

    assert record["certificate"].status == "candidate_resolved"
    assert record["planning_evidence_key"] == (
        implementation_runner._planning_input_sha256(
            _planning_inputs(),
            "network_only_shared",
            specification,
        )
    )
    assert record["primal_pointer"] is not None
    assert record["replay_pointer"] is not None
    assert record["solve_pointer"] is not None
    assert store.load_blob("solver_log", record["native_log_sha256"]).startswith(
        b"synthetic gurobi"
    )
    assert store.inventory()["schema"] == (
        "rq2_joint_deliverability_evidence_inventory_v2"
    )

    def wrong_version_driver(
        model: ConcreteModel,
        current_specification: Rq2SolverSpec,
        options: object,
        native_log_path: Path,
    ) -> tuple[object, str]:
        result, _ = solve_driver(
            model,
            current_specification,
            options,
            native_log_path,
        )
        return result, "13.0.1"

    with pytest.raises(EvidenceDrift, match="package version drifted"):
        core._solve_arm_with_native_evidence(
            _planning_inputs(),
            "network_only_shared",
            specification,
            store=store,
            solve_driver=wrong_version_driver,
            model_factory=model_factory,
        )


def test_planning_evidence_index_binds_capacity_output_locations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="c" * 64)
    production_replay = core.replay_primal_evidence
    specification = Rq2SolverSpec(
        name="gurobi",
        expected_package_version="13.0.2",
        threads=4,
        mip_relative_gap=1.0e-6,
        feasibility_tolerance=1.0e-6,
        optimality_tolerance=1.0e-6,
        integer_feasibility_tolerance=1.0e-6,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )
    low_probability = 0.495 / 8.0
    finite_training_power = tuple(
        PowerBlock(
            block_id=f"p{index}",
            split="training",
            probability=low_probability,
            source_hours=tuple(range(24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(0.0,) * 24,
            state=FINITE_GRID_NEED,
        )
        for index in range(8)
    ) + (
        PowerBlock(
            block_id="z",
            split="training",
            probability=0.005,
            source_hours=tuple(range(24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(0.1, 0.0, 0.1) + (0.0,) * 21,
            state=FINITE_GRID_NEED,
        ),
    )
    training_power = finite_training_power + tuple(
        PowerBlock(
            block_id=f"e{index:03d}",
            split="training",
            probability=0.5 / 532.0,
            source_hours=tuple(range(24)),
            cfe_call_fraction_at_alpha_1=(0.0,) * 24,
            grid_need=(None,) * 24,
            state=EXOGENOUS_GRID_INFEASIBILITY,
        )
        for index in range(532)
    )
    training_workload = tuple(
        WorkloadBlock(
            block_id=f"w{index:02d}",
            split="training",
            probability=1.0 / 34.0,
            source_relative_hours=tuple(range(24)),
            raw_workload_fraction=(1.0, 0.0) + (1.0,) * 22,
        )
        for index in range(34)
    )
    registered_input_audit = {
        "schema": "rq2_joint_deliverability_input_audit_v1",
        "registered_inputs_ready": True,
        "packages": {
            "dispatched_grid": {
                "status": "verified",
                "training_block_inventory_sha256": (
                    core.power_block_inventory_sha256(training_power)
                ),
            },
            "workload": {
                "status": "verified",
                "training_block_inventory_sha256": (
                    core.workload_block_inventory_sha256(training_workload)
                ),
            },
        },
    }
    records: list[dict[str, object]] = []

    def record_solve(
        inputs: JointDeliverabilityPlanningInputs,
        arm_id: str,
        current_specification: Rq2SolverSpec,
    ) -> dict[str, object]:
        planning_hash = core.planning_input_sha256(
            inputs,
            arm_id,
            current_specification,
        )
        certificate = {
            "arm_id": arm_id,
            "status": "candidate_resolved",
            "incumbent_capacity": 1.0,
            "objective_lower_bound": 1.0,
            "objective_upper_bound": 1.0,
            "absolute_gap": 0.0,
            "incumbent_relative_gap": 0.0,
            "maximum_constraint_residual": 0.0,
            "termination_condition": "optimal",
            "solver_status": "ok",
            "model_variables": 1,
            "model_constraints": 1,
            "solver_name": current_specification.name,
            "solver_version": current_specification.expected_package_version,
            "solver_options": core.solver_options(current_specification),
        }
        certificate_sha256 = core.canonical_sha256(certificate)
        native_log_sha256 = store.put_blob("solver_log", b"analytic replay\n")
        primal_pointer = store.commit(
            "primal",
            planning_hash,
            {
                "schema": "synthetic_primal_v1",
                "arm_id": arm_id,
                "certificate_sha256": certificate_sha256,
                "native_log_sha256": native_log_sha256,
            },
        )
        replay_pointer = store.commit(
            "primal_replay",
            planning_hash,
            {
                "schema": "rq2_joint_deliverability_primal_replay_v1",
                "arm_id": arm_id,
                "certificate_sha256": certificate_sha256,
                "native_log_sha256": native_log_sha256,
                "objective": 1.0,
                "maximum_constraint_residual": 0.0,
                "variable_count": 1,
                "constraint_count": 1,
                "passed": True,
            },
        )
        solve_pointer = store.commit(
            "solve",
            planning_hash,
            {
                "schema": "rq2_joint_deliverability_native_solve_record_v1",
                "planning_input_sha256": planning_hash,
                "arm_id": arm_id,
                "certificate": certificate,
                "native_log_sha256": native_log_sha256,
                "primal_pointer": primal_pointer,
                "replay_pointer": replay_pointer,
            },
        )
        ordinal = len(records)
        order_pointer = store.commit(
            "solve_order",
            f"s{ordinal:06d}",
            {
                "schema": "rq2_joint_deliverability_solve_order_v1",
                "invocation_ordinal": ordinal,
                "planning_input_sha256": planning_hash,
                "arm_id": arm_id,
                "certificate_sha256": certificate_sha256,
                "solve_object_sha256": solve_pointer["object_sha256"],
            },
        )
        records.append(
            {
                "certificate": certificate,
                "planning_evidence_key": planning_hash,
                "native_log_sha256": native_log_sha256,
                "primal_pointer": primal_pointer,
                "replay_pointer": replay_pointer,
                "solve_pointer": solve_pointer,
                "invocation_ordinal": ordinal,
                "order_pointer": order_pointer,
                "scenario_count": len(inputs.scenarios),
            }
        )
        return certificate

    frontier = implementation_runner.execute_capacity_stage(
        _scientific(),
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=specification,
        solve_callback=record_solve,
    )
    solve_records = [
        {key: value for key, value in record.items() if key != "scenario_count"}
        for record in records
    ]
    assert frontier["full_support_fallback_solver_calls"] > 0

    with pytest.raises(EvidenceDrift, match="primal evidence certificate binding"):
        core._commit_planning_evidence_index_from_audit(
            _scientific(),
            capacity_frontier=frontier,
            solve_records=solve_records,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power,
            training_workload_blocks=training_workload,
            solver_specification=specification,
            store=store,
        )

    def synthetic_replay(
        _model_factory: object,
        evidence: dict[str, object],
        *,
        expected_arm_id: str,
        certificate: dict[str, object],
        native_log: bytes,
        feasibility_tolerance: float,
    ) -> dict[str, object]:
        assert feasibility_tolerance == specification.feasibility_tolerance
        return {
            "schema": "rq2_joint_deliverability_primal_replay_v1",
            "arm_id": expected_arm_id,
            "certificate_sha256": core.canonical_sha256(certificate),
            "native_log_sha256": hashlib.sha256(native_log).hexdigest(),
            "objective": 1.0,
            "maximum_constraint_residual": 0.0,
            "variable_count": 1,
            "constraint_count": 1,
            "passed": True,
        }

    monkeypatch.setattr(core, "replay_primal_evidence", synthetic_replay)
    pointer = core._commit_planning_evidence_index_from_audit(
        _scientific(),
        capacity_frontier=frontier,
        solve_records=solve_records,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=specification,
        store=store,
    )
    index = store.load("planning_index", "capacity_frontier")

    assert pointer["object_sha256"] == core.canonical_sha256(index)
    assert index["solve_record_count"] == len(solve_records)
    assert core.canonical_json_bytes(
        store.load("capacity_frontier", "registered")
    ) == core.canonical_json_bytes(frontier)
    assert index["capacity_frontier_object_sha256"] == core.canonical_sha256(frontier)
    assert store.load("input_audit", "registered") == registered_input_audit
    assert index["registered_input_audit_sha256"] == core.canonical_sha256(
        registered_input_audit
    )
    assert index["input_audit_object_sha256"] == core.canonical_sha256(
        registered_input_audit
    )
    assert index["training_power_inventory_sha256"] == (
        core.power_block_inventory_sha256(training_power)
    )
    assert index["training_workload_inventory_sha256"] == (
        core.workload_block_inventory_sha256(training_workload)
    )
    fallback_index = next(
        position
        for position, record in enumerate(index["records"])
        if record["solve_role"] == "full_support_fallback"
    )
    assert (
        index["records"][fallback_index]["planning_input_sha256"]
        == (solve_records[fallback_index]["planning_evidence_key"])
    )
    assert (
        index["records"][fallback_index]["output_indices"][0]["fallback_ordinal"] >= 0
    )
    monkeypatch.setattr(core, "replay_primal_evidence", production_replay)
    with pytest.raises(EvidenceDrift, match="primal evidence certificate binding"):
        core._registered_planning_evidence(
            store,
            design=_scientific(),
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power,
            training_workload_blocks=training_workload,
            capacity_frontier_sha256=core.canonical_sha256(frontier),
        )
    monkeypatch.setattr(core, "replay_primal_evidence", synthetic_replay)
    planning_authority = core._registered_planning_evidence(
        store,
        design=_scientific(),
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        capacity_frontier_sha256=core.canonical_sha256(frontier),
    )
    assert (
        planning_authority["planning_index_object_sha256"] == (pointer["object_sha256"])
    )
    assert store.inventory()["schema"] == (
        "rq2_joint_deliverability_evidence_inventory_v2"
    )
    drifted_training_power = list(training_power)
    drifted_training_power[0] = PowerBlock(
        **{
            **asdict(drifted_training_power[0]),
            "source_hours": tuple(range(1, 25)),
        }
    )
    with pytest.raises(EvidenceDrift, match="audited input authority"):
        core._commit_planning_evidence_index_from_audit(
            _scientific(),
            capacity_frontier=frontier,
            solve_records=solve_records,
            registered_input_audit=registered_input_audit,
            training_power_blocks=tuple(drifted_training_power),
            training_workload_blocks=training_workload,
            solver_specification=specification,
            store=store,
        )
    forged_records = deepcopy(solve_records)
    forged_records[fallback_index]["planning_evidence_key"] = "f" * 64
    with pytest.raises(EvidenceDrift, match="invocation input binding"):
        core._commit_planning_evidence_index_from_audit(
            _scientific(),
            capacity_frontier=frontier,
            solve_records=forged_records,
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power,
            training_workload_blocks=training_workload,
            solver_specification=specification,
            store=store,
        )
    with pytest.raises(EvidenceDrift, match="invocation replay is incomplete"):
        core._commit_planning_evidence_index_from_audit(
            _scientific(),
            capacity_frontier=frontier,
            solve_records=[],
            registered_input_audit=registered_input_audit,
            training_power_blocks=training_power,
            training_workload_blocks=training_workload,
            solver_specification=specification,
            store=EvidenceStore(
                tmp_path / "missing",
                run_identity_sha256="f" * 64,
            ),
        )


def test_nonoptimal_feasible_incumbent_is_preserved_but_unresolved(
    tmp_path: Path,
) -> None:
    store = EvidenceStore(tmp_path / "evidence", run_identity_sha256="b" * 64)
    specification = Rq2SolverSpec(
        name="gurobi",
        expected_package_version="13.0.2",
        threads=4,
        mip_relative_gap=1.0e-6,
        feasibility_tolerance=1.0e-6,
        optimality_tolerance=1.0e-6,
        integer_feasibility_tolerance=1.0e-6,
        random_seed=0,
        time_limit_seconds=None,
        tee=False,
    )

    def model_factory(
        _inputs: JointDeliverabilityPlanningInputs,
        _arm_id: str,
    ) -> ConcreteModel:
        model = ConcreteModel()
        model.capacity = Var(bounds=(0.0, 1.0), initialize=0.4)
        model.minimum = Constraint(expr=model.capacity >= 0.2)
        model.objective = Objective(expr=model.capacity)
        return model

    def solve_driver(
        model: ConcreteModel,
        _specification: Rq2SolverSpec,
        _options: object,
        native_log_path: Path,
    ) -> tuple[object, str]:
        model.capacity.set_value(0.4)
        native_log_path.write_text("time limit with incumbent\n", encoding="utf-8")
        return (
            SimpleNamespace(
                solver=SimpleNamespace(
                    termination_condition=TerminationCondition.maxTimeLimit,
                    status=SolverStatus.warning,
                ),
                problem=SimpleNamespace(lower_bound=0.3, upper_bound=0.4),
                solution=[],
            ),
            "13.0.2",
        )

    record = core._solve_arm_with_native_evidence(
        _planning_inputs(),
        "network_only_shared",
        specification,
        store=store,
        solve_driver=solve_driver,
        model_factory=model_factory,
    )

    certificate = record["certificate"]
    assert certificate.status == "unresolved"
    assert certificate.incumbent_capacity == pytest.approx(0.4)
    assert certificate.objective_lower_bound == pytest.approx(0.3)
    assert certificate.objective_upper_bound == pytest.approx(0.4)
    assert certificate.absolute_gap == pytest.approx(0.1)
    assert certificate.maximum_constraint_residual == 0.0
    assert record["primal_pointer"] is not None
    assert record["replay_pointer"] is not None
    assert record["solve_pointer"] is not None
    assert store.inventory()["schema"] == (
        "rq2_joint_deliverability_evidence_inventory_v2"
    )


def test_primal_replay_rejects_infeasible_assignment(tmp_path: Path) -> None:
    native_log = tmp_path / "native.log"
    native_log.write_text("synthetic native solver log\n", encoding="utf-8")
    certificate = {"arm_id": "synthetic", "status": "candidate_resolved"}
    evidence = capture_primal_evidence(
        _model(objective_uses_x=False),
        arm_id="synthetic",
        certificate=certificate,
        native_log_path=native_log,
    )
    evidence["variables"]["x"] = (0.0).hex()
    with pytest.raises(EvidenceDrift, match="violates model constraints"):
        replay_primal_evidence(
            lambda: _model(objective_uses_x=False),
            evidence,
            expected_arm_id="synthetic",
            certificate=certificate,
            native_log=native_log.read_bytes(),
            feasibility_tolerance=1.0e-9,
        )


def test_run_identity_and_streaming_projection() -> None:
    identity = run_identity(
        static_authority_sha256="1" * 64,
        execution_outer_sha256="2" * 64,
        execution_review_sha256="3" * 64,
        grid_manifest_sha256="4" * 64,
        runtime_receipt_sha256="5" * 64,
        activation_sha256="6" * 64,
    )
    projection = streaming_scale_projection(_config())

    assert len(identity) == 64
    assert projection["maximum_pairs_in_memory"] == 34
    assert projection["maximum_trajectories_in_memory"] == 136
    assert projection["registered_metric_count"] == 23
    assert projection["bootstrap_replicates"] == 200
    assert projection["numeric_payload_bytes_by_component"][
        "single_cell_metric_matrices"
    ] == (23 * 530 * 34 * 8)
    assert projection["numeric_payload_bytes_by_component"][
        "single_cell_bootstrap_endpoint_samples"
    ] == (23 * 2 * 200 * 8)
    assert projection["numeric_payload_bytes_by_component"][
        "aggregate_interval_output"
    ] == (46 * 23 * 2 * 2 * 8)
    assert (
        projection["python_object_overhead"][
            "included_in_required_tracemalloc_measurement"
        ]
        is True
    )
    assert projection["independent_of_registered_cell_count"] is False
    assert projection["independent_of_power_holdout_count"] is False
    assert projection["static_projection_is_acceptance_evidence"] is False
    profile = measure_synthetic_streaming_profile(
        item_count=1000,
        payload_factory=lambda index: {"index": index, "values": [0.0] * 24},
    )
    assert profile["item_count"] == 1000
    assert profile["peak_bytes"] < 2_000_000
    assert profile["includes_python_object_overhead"] is True
    assert profile["registered_dimension_measurement"] is False
    assert profile["acceptance_evidence"] is False
    with pytest.raises(ValueError, match="invalid digest"):
        run_identity(
            static_authority_sha256="bad",
            execution_outer_sha256="2" * 64,
            execution_review_sha256="3" * 64,
            grid_manifest_sha256="4" * 64,
            runtime_receipt_sha256="5" * 64,
            activation_sha256="6" * 64,
        )


@pytest.mark.parametrize(
    ("section", "key", "replacement", "expected_error"),
    (
        ("scope", "formal_execution", True, "execution scope drifted"),
        ("gates", "formal_execution_ready", True, "execution gate inventory drifted"),
        (
            "gates",
            "user_formal_run_authorized",
            True,
            "execution gate inventory drifted",
        ),
        ("gates", "security_certified", True, "execution gate inventory drifted"),
        (
            "execution_contract",
            "formal_activation_wrapper",
            "implemented",
            "execution capability contract drifted",
        ),
    ),
)
def test_validator_rejects_opened_gates(
    section: str,
    key: str,
    replacement: object,
    expected_error: str,
) -> None:
    config = _config()
    config[section][key] = replacement
    with pytest.raises(ValueError, match=expected_error):
        validator.validate(config, require_sealed=_requires_sealed(config))
