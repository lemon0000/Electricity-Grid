"""Checkpointed Cartesian fixed-policy replay for public RQ2 marginals."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from dataclasses import asdict
from importlib.metadata import version
from pathlib import Path
from typing import Any

import yaml

from src.evaluation.rq2_provenance import (
    canonical_sha256,
    load_contract,
    sha256_file,
    stage_base_provenance,
    verify_stage_provenance,
    write_json,
)
from src.models.temporal_flexibility_capacity import (
    MinimumFlexibilityCapacity,
    plan_minimum_flexibility_pair,
)
from src.scenarios.rq2_public_replay import (
    CausalPolicyOutcome,
    ParameterCell,
    TemporalBlock,
    envelope_for_cell,
    execute_causal_grid_first_policy,
    expand_parameter_cells,
    load_power_blocks,
    load_workload_blocks,
    pair_scenario,
    select_weighted_quantile_representatives,
    training_model_inputs,
)

_ROOT = Path(__file__).resolve().parents[1]
_STAGE = "pairwise_replay_v2"
_GRID_STAGE = "grid_need_dispatch_v2"
_POLICY_FIELDS = (
    "cell_id",
    "varied_dimension",
    "variant",
    "resolved",
    "feasible",
    "proven_infeasible",
    "minimum_capacity",
    "termination_condition",
    "solver_status",
    "maximum_residual",
)
_PAIR_FIELDS = (
    "cell_id",
    "row_id",
    "column_id",
    "outcome_resolved",
    "correct_capacity",
    "b6_capacity",
    "capacity_underprovisioning",
    "correct_failure",
    "b6_failure",
    "correct_shortfall",
    "b6_shortfall",
    "correct_peak_debt",
    "b6_peak_debt",
    "correct_terminal_debt",
    "b6_terminal_debt",
    "correct_hard_temporal_failure",
    "b6_hard_temporal_failure",
    "correct_physical_policy_failure",
    "b6_physical_policy_failure",
    "correct_service_failure",
    "b6_service_failure",
    "correct_solver_unresolved",
    "b6_solver_unresolved",
)
_CELL_STATUS_FIELDS = (
    "cell_id",
    "varied_dimension",
    "training_resolved",
    "correct_training_feasible",
    "correct_training_proven_infeasible",
    "b6_training_feasible",
    "b6_training_proven_infeasible",
    "pairwise_eligible",
    "pair_count_expected",
    "pair_count_completed",
    "all_pairwise_outcomes_resolved",
)


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_json_manifest(
    directory: Path,
    expected_sha256: str,
    *,
    required_members: set[str],
    exact_members: bool = False,
) -> dict[str, str]:
    manifest_path = directory / "SHA256SUMS.json"
    if not manifest_path.is_file() or _sha256(manifest_path) != expected_sha256:
        raise ValueError(f"package manifest SHA-256 drifted: {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError(f"package manifest is invalid: {directory}")
    if not required_members.issubset(manifest):
        raise ValueError(f"package manifest omits consumed files: {directory}")
    if exact_members and set(manifest) != required_members:
        raise ValueError(f"package manifest member set drifted: {directory}")
    for name, digest in manifest.items():
        member = directory / name
        if not member.is_file() or _sha256(member) != digest:
            raise ValueError(f"package member drifted: {member}")
    return manifest


def _write_gzip_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _safe_id(raw: str) -> str:
    if not raw or not raw.replace("_", "").isalnum():
        raise ValueError(f"unsafe checkpoint identifier: {raw}")
    return raw


def _checkpoint_path(directory: Path, *parts: str) -> Path:
    return directory.joinpath(*(_safe_id(part) for part in parts)).with_suffix(
        ".json"
    )


def _write_checkpoint(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _load_checkpoint(
    path: Path,
    identity: Mapping[str, object],
    *,
    schema: str,
) -> dict[str, object] | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema") != schema or any(
        payload.get(key) != value for key, value in identity.items()
    ):
        raise ValueError(f"checkpoint identity drifted: {path}")
    return payload


def _capacity_row(
    cell: ParameterCell,
    variant: str,
    result: MinimumFlexibilityCapacity,
) -> dict[str, object]:
    return {
        "cell_id": cell.cell_id,
        "varied_dimension": cell.varied_dimension,
        "variant": variant,
        "resolved": result.feasible or result.proven_infeasible,
        "feasible": result.feasible,
        "proven_infeasible": result.proven_infeasible,
        "minimum_capacity": (
            "" if result.minimum_capacity is None else result.minimum_capacity
        ),
        "termination_condition": result.termination_condition,
        "solver_status": result.solver_status,
        "maximum_residual": (
            "" if result.maximum_residual is None else result.maximum_residual
        ),
    }


def _failure(outcome: CausalPolicyOutcome) -> bool:
    return (
        outcome.hard_grid_failure
        or outcome.physical_policy_failure
        or outcome.service_shortfall_failure
    )


def _pair_payload(
    cell: ParameterCell,
    power: TemporalBlock,
    workload: TemporalBlock,
    *,
    correct_capacity: float,
    b6_capacity: float,
    config: dict[str, Any],
) -> dict[str, object]:
    scenario = pair_scenario(
        power,
        workload,
        cell,
        name=f"holdout__{power.block_id}__{workload.block_id}",
    )
    envelope = envelope_for_cell(cell, policy=config["fixed_policy"])
    tolerance = float(config["fixed_policy"]["service_shortfall_tolerance"])
    correct = execute_causal_grid_first_policy(
        scenario,
        envelope,
        correct_capacity,
        service_shortfall_tolerance=tolerance,
    )
    b6 = execute_causal_grid_first_policy(
        scenario,
        envelope,
        b6_capacity,
        service_shortfall_tolerance=tolerance,
    )
    resolved = correct.resolved and b6.resolved
    row = {
        "cell_id": cell.cell_id,
        "row_id": power.block_id,
        "column_id": workload.block_id,
        "outcome_resolved": resolved,
        "correct_capacity": correct_capacity,
        "b6_capacity": b6_capacity,
        "capacity_underprovisioning": correct_capacity - b6_capacity,
        "correct_failure": _failure(correct) if resolved else "",
        "b6_failure": _failure(b6) if resolved else "",
        "correct_shortfall": (
            correct.access_shortfall if resolved else ""
        ),
        "b6_shortfall": b6.access_shortfall if resolved else "",
        "correct_peak_debt": (
            correct.peak_recovery_debt if resolved else ""
        ),
        "b6_peak_debt": b6.peak_recovery_debt if resolved else "",
        "correct_terminal_debt": (
            correct.terminal_recovery_debt if resolved else ""
        ),
        "b6_terminal_debt": (
            b6.terminal_recovery_debt if resolved else ""
        ),
        "correct_hard_temporal_failure": (
            correct.hard_grid_failure if resolved else ""
        ),
        "b6_hard_temporal_failure": (
            b6.hard_grid_failure if resolved else ""
        ),
        "correct_physical_policy_failure": (
            correct.physical_policy_failure if resolved else ""
        ),
        "b6_physical_policy_failure": (
            b6.physical_policy_failure if resolved else ""
        ),
        "correct_service_failure": (
            correct.service_shortfall_failure if resolved else ""
        ),
        "b6_service_failure": (
            b6.service_shortfall_failure if resolved else ""
        ),
        "correct_solver_unresolved": not correct.resolved,
        "b6_solver_unresolved": not b6.resolved,
    }
    return {
        "row": row,
        "correct_outcome": asdict(correct),
        "b6_outcome": asdict(b6),
    }


def _marginal_rows(
    blocks: tuple[TemporalBlock, ...],
    *,
    role: str,
) -> list[dict[str, object]]:
    return [
        {
            "id": block.block_id,
            "probability": block.probability,
            "stress_score": (
                max(
                    grid + cfe
                    for grid, cfe in zip(
                        block.grid_need,
                        block.cfe_call,
                        strict=True,
                    )
                )
                if role == "power"
                else max(block.workload)
            ),
        }
        for block in blocks
    ]


def _preflight(config_path: Path) -> tuple[dict[str, Any], dict[str, object]]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    inputs = config["input"]
    workload_package = _path(inputs["workload_package"], "workload_package")
    _verify_json_manifest(
        workload_package,
        str(inputs["workload_manifest_sha256"]),
        required_members={
            "holdout_marginal.csv.gz",
            "summary.json",
            "training_marginal.csv.gz",
            "workload_blocks.csv.gz",
        },
        exact_members=True,
    )
    workload_training = load_workload_blocks(workload_package, "training")
    workload_holdout = load_workload_blocks(workload_package, "holdout")
    workload_summary = json.loads(
        (workload_package / "summary.json").read_text(encoding="utf-8")
    )
    expected_workload_summary = {
        "schema": inputs["workload_schema"],
        "block_hours": int(inputs["block_hours"]),
        "training_block_count": int(inputs["workload_training_blocks"]),
        "holdout_block_count": int(inputs["workload_holdout_blocks"]),
        "workload_fraction_is_power": False,
        "job_split_policy": "exclude_jobs_contributing_to_both_sides",
        "config_sha256": inputs["workload_config_sha256"],
        "implementation_sha256": inputs[
            "workload_implementation_sha256"
        ],
        "source_sha256": inputs["workload_source_sha256"],
    }
    if not isinstance(workload_summary, dict) or any(
        workload_summary.get(key) != value
        for key, value in expected_workload_summary.items()
    ):
        raise ValueError("workload package summary contract drifted")
    if (
        len(workload_training) != int(inputs["workload_training_blocks"])
        or len(workload_holdout) != int(inputs["workload_holdout_blocks"])
        or any(
            len(block.workload) != int(inputs["block_hours"])
            for block in (*workload_training, *workload_holdout)
        )
    ):
        raise ValueError("workload block inventory drifted")
    power_ready = inputs["grid_need_dispatch_ready"] is True
    power_package = _path(
        inputs["power_system_dispatch_package"],
        "power_system_dispatch_package",
    )
    power_training: tuple[TemporalBlock, ...] = ()
    power_holdout: tuple[TemporalBlock, ...] = ()
    power_provenance_sha256 = None
    if power_ready:
        digest = inputs["power_system_dispatch_manifest_sha256"]
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("power-system dispatch manifest must be frozen")
        _verify_json_manifest(
            power_package,
            digest,
            required_members={
                "block_status.csv.gz",
                "checkpoint_inventory.json",
                "dispatched_power_system_blocks.csv.gz",
                "holdout_marginal.csv.gz",
                "provenance.json",
                "summary.json",
                "training_marginal.csv.gz",
            },
            exact_members=True,
        )
        power_training = load_power_blocks(power_package, "training")
        power_holdout = load_power_blocks(power_package, "holdout")
        power_summary = json.loads(
            (power_package / "summary.json").read_text(encoding="utf-8")
        )
        expected_power_summary = {
            "schema": inputs["power_system_dispatch_schema"],
            "training_block_count": int(inputs["power_training_blocks"]),
            "holdout_block_count": int(inputs["power_holdout_blocks"]),
            "all_blocks_resolved": True,
            "empirical_outage_probability_claimed": False,
            "full_N_minus_one": False,
            "AC_security": False,
            "security_certified": False,
            "config_sha256": inputs[
                "power_system_dispatch_config_sha256"
            ],
        }
        if not isinstance(power_summary, dict) or any(
            power_summary.get(key) != value
            for key, value in expected_power_summary.items()
        ):
            raise ValueError("power-system dispatch summary contract drifted")
        contract_path = _path(
            config["provenance"]["contract_path"],
            "provenance.contract_path",
        )
        grid_contract = load_contract(
            _ROOT,
            path=contract_path,
            expected_sha256=str(
                config["provenance"]["contract_sha256"]
            ),
            stage=_GRID_STAGE,
        )
        power_provenance_path = power_package / "provenance.json"
        power_provenance_sha256 = sha256_file(power_provenance_path)
        if (
            power_summary.get("provenance_sha256")
            != power_provenance_sha256
        ):
            raise ValueError("power-system dispatch provenance hash drifted")
        power_provenance = json.loads(
            power_provenance_path.read_text(encoding="utf-8")
        )
        verified_power_provenance = verify_stage_provenance(
            power_provenance,
            stage=_GRID_STAGE,
            expected_config_sha256=str(
                inputs["power_system_dispatch_config_sha256"]
            ),
            contract_identity=grid_contract,
            expected_inputs={
                "power_system_blocks_manifest_sha256": inputs[
                    "power_system_blocks_manifest_sha256"
                ],
                "rts_gmlc_source_manifest_sha256": inputs[
                    "rts_gmlc_source_manifest_sha256"
                ],
            },
        )
        checkpoint_inventory = json.loads(
            (power_package / "checkpoint_inventory.json").read_text(
                encoding="utf-8"
            )
        )
        if (
            checkpoint_inventory
            != verified_power_provenance["checkpoint_inventory"]
            or power_summary.get("checkpoint_inventory_sha256")
            != canonical_sha256(checkpoint_inventory)
        ):
            raise ValueError(
                "power-system checkpoint inventory provenance drifted"
            )
        if (
            len(power_training) != int(inputs["power_training_blocks"])
            or len(power_holdout) != int(inputs["power_holdout_blocks"])
            or any(
                len(block.grid_need) != int(inputs["block_hours"])
                for block in (*power_training, *power_holdout)
            )
        ):
            raise ValueError("power-system dispatch block inventory drifted")
    solver = config["solver"]
    if (
        solver["name"] != "highs"
        or version("highspy") != str(solver["expected_highspy_version"])
        or version("pyomo") != str(solver["expected_pyomo_version"])
    ):
        raise ValueError("pairwise replay solver identity drifted")
    contract_identity = load_contract(
        _ROOT,
        path=_path(
            config["provenance"]["contract_path"],
            "provenance.contract_path",
        ),
        expected_sha256=str(config["provenance"]["contract_sha256"]),
        stage=_STAGE,
    )
    cells = expand_parameter_cells(config)
    report = {
        "schema": "rq2_public_pairwise_replay_preflight_v2",
        "config_sha256": _sha256(config_path),
        "grid_need_dispatch_ready": power_ready,
        "power_training_blocks": len(power_training),
        "power_holdout_blocks": len(power_holdout),
        "workload_training_blocks": len(workload_training),
        "workload_holdout_blocks": len(workload_holdout),
        "parameter_cells": len(cells),
        "expected_holdout_pairs_per_cell": (
            len(power_holdout) * len(workload_holdout)
        ),
        "formal_execution_ready": config["execution"][
            "formal_execution_ready"
        ],
        "independent_R4_review_passed": config["execution"][
            "independent_R4_review_passed"
        ],
        "user_formal_run_authorized": config["execution"][
            "user_formal_run_authorized"
        ],
        "provenance_contract_sha256": contract_identity[
            "contract_sha256"
        ],
    }
    return config, {
        "report": report,
        "power_training": power_training,
        "power_holdout": power_holdout,
        "workload_training": workload_training,
        "workload_holdout": workload_holdout,
        "cells": cells,
        "contract_identity": contract_identity,
        "power_provenance_sha256": power_provenance_sha256,
    }


def run(
    config_path: Path,
    *,
    validate_only: bool = False,
    maximum_pairs: int | None = None,
) -> dict[str, object]:
    config_path = config_path.resolve()
    config, context = _preflight(config_path)
    if validate_only:
        return context["report"]
    execution = config["execution"]
    if (
        config["input"]["grid_need_dispatch_ready"] is not True
        or execution["formal_execution_ready"] is not True
        or execution["independent_R4_review_passed"] is not True
        or execution["user_formal_run_authorized"] is not True
    ):
        raise ValueError(
            "grid_need_dispatch_ready, formal_execution_ready, "
            "independent_R4_review_passed, and user_formal_run_authorized "
            "must all be true before replay"
        )
    if maximum_pairs is not None and (
        isinstance(maximum_pairs, bool) or maximum_pairs <= 0
    ):
        raise ValueError("maximum_pairs must be a positive integer")

    power_training = context["power_training"]
    power_holdout = context["power_holdout"]
    workload_training = context["workload_training"]
    workload_holdout = context["workload_holdout"]
    cells = context["cells"]
    selected_power = select_weighted_quantile_representatives(
        power_training,
        int(config["training_selection"]["power_system_representatives"]),
        role="power",
    )
    selected_workload = select_weighted_quantile_representatives(
        workload_training,
        int(config["training_selection"]["workload_representatives"]),
        role="workload",
    )
    config_sha = _sha256(config_path)
    stage_base = stage_base_provenance(
        stage=_STAGE,
        config_path=config_path,
        contract_identity=context["contract_identity"],
        inputs={
            "power_system_dispatch_manifest_sha256": config["input"][
                "power_system_dispatch_manifest_sha256"
            ],
            "power_system_dispatch_provenance_sha256": context[
                "power_provenance_sha256"
            ],
            "workload_manifest_sha256": config["input"][
                "workload_manifest_sha256"
            ],
            "workload_config_sha256": config["input"][
                "workload_config_sha256"
            ],
            "workload_implementation_sha256": config["input"][
                "workload_implementation_sha256"
            ],
            "workload_source_sha256": config["input"][
                "workload_source_sha256"
            ],
        },
    )
    stage_base_sha256 = canonical_sha256(stage_base)
    identity = {"stage_base_provenance_sha256": stage_base_sha256}
    checkpoint_root = _path(
        execution["checkpoint_directory"],
        "checkpoint_directory",
    )
    policy_checkpoints = []
    for cell in cells:
        path = _checkpoint_path(checkpoint_root / "policies", cell.cell_id)
        checkpoint = _load_checkpoint(
            path,
            {**identity, "cell_id": cell.cell_id},
            schema="rq2_public_policy_checkpoint_v2",
        )
        if checkpoint is None:
            model_inputs = training_model_inputs(
                selected_power,
                selected_workload,
                cell,
                config,
            )
            plan = plan_minimum_flexibility_pair(
                model_inputs,
                solver_name=str(config["solver"]["name"]),
                tee=bool(config["solver"]["tee"]),
            )
            checkpoint = {
                "schema": "rq2_public_policy_checkpoint_v2",
                **identity,
                "cell_id": cell.cell_id,
                "varied_dimension": cell.varied_dimension,
                "correct": asdict(plan.correct),
                "b6": asdict(plan.b6),
            }
            _write_checkpoint(path, checkpoint)
        policy_checkpoints.append(checkpoint)

    unresolved_training = [
        item["cell_id"]
        for item in policy_checkpoints
        if any(
            not result["feasible"] and not result["proven_infeasible"]
            for result in (item["correct"], item["b6"])
        )
    ]
    if execution["require_all_training_plans_resolved"] and unresolved_training:
        raise RuntimeError("at least one training policy remains unresolved")

    processed = 0
    pair_checkpoints = []
    cell_by_id = {cell.cell_id: cell for cell in cells}
    for policy in policy_checkpoints:
        correct = policy["correct"]
        b6 = policy["b6"]
        if not correct["feasible"] or not b6["feasible"]:
            continue
        cell = cell_by_id[policy["cell_id"]]
        policy_checkpoint_sha256 = _sha256(
            _checkpoint_path(checkpoint_root / "policies", cell.cell_id)
        )
        for power in power_holdout:
            for workload in workload_holdout:
                pair_key = f"{power.block_id}__{workload.block_id}"
                path = _checkpoint_path(
                    checkpoint_root / "pairs" / cell.cell_id,
                    pair_key,
                )
                pair_identity = {
                    **identity,
                    "cell_id": cell.cell_id,
                    "row_id": power.block_id,
                    "column_id": workload.block_id,
                    "correct_capacity": correct["minimum_capacity"],
                    "b6_capacity": b6["minimum_capacity"],
                    "policy_checkpoint_sha256": policy_checkpoint_sha256,
                }
                checkpoint = _load_checkpoint(
                    path,
                    pair_identity,
                    schema="rq2_public_pair_checkpoint_v2",
                )
                if checkpoint is None:
                    payload = _pair_payload(
                        cell,
                        power,
                        workload,
                        correct_capacity=float(correct["minimum_capacity"]),
                        b6_capacity=float(b6["minimum_capacity"]),
                        config=config,
                    )
                    checkpoint = {
                        "schema": "rq2_public_pair_checkpoint_v2",
                        **pair_identity,
                        **payload,
                    }
                    _write_checkpoint(path, checkpoint)
                    processed += 1
                pair_checkpoints.append(checkpoint)
                if maximum_pairs is not None and processed >= maximum_pairs:
                    return {
                        "schema": "rq2_public_pairwise_replay_progress_v1",
                        "processed_this_call": processed,
                        "policy_cells": len(policy_checkpoints),
                        "pair_checkpoints_seen": len(pair_checkpoints),
                        "formal_result_published": False,
                    }

    eligible_cells = {
        item["cell_id"]
        for item in policy_checkpoints
        if item["correct"]["feasible"] and item["b6"]["feasible"]
    }
    expected_per_cell = len(power_holdout) * len(workload_holdout)
    status_rows = []
    for policy in policy_checkpoints:
        cell_pairs = [
            item for item in pair_checkpoints if item["cell_id"] == policy["cell_id"]
        ]
        training_resolved = all(
            item["feasible"] or item["proven_infeasible"]
            for item in (policy["correct"], policy["b6"])
        )
        eligible = policy["cell_id"] in eligible_cells
        status_rows.append(
            {
                "cell_id": policy["cell_id"],
                "varied_dimension": policy["varied_dimension"],
                "training_resolved": training_resolved,
                "correct_training_feasible": policy["correct"]["feasible"],
                "correct_training_proven_infeasible": policy["correct"][
                    "proven_infeasible"
                ],
                "b6_training_feasible": policy["b6"]["feasible"],
                "b6_training_proven_infeasible": policy["b6"][
                    "proven_infeasible"
                ],
                "pairwise_eligible": eligible,
                "pair_count_expected": expected_per_cell if eligible else 0,
                "pair_count_completed": len(cell_pairs),
                "all_pairwise_outcomes_resolved": (
                    eligible
                    and len(cell_pairs) == expected_per_cell
                    and all(item["row"]["outcome_resolved"] for item in cell_pairs)
                ),
            }
        )
    unresolved_pairs = [
        (item["row_id"], item["column_id"])
        for item in pair_checkpoints
        if not item["row"]["outcome_resolved"]
    ]
    if execution["require_all_pairwise_outcomes_resolved"] and unresolved_pairs:
        raise RuntimeError("at least one pairwise outcome remains unresolved")

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        policy_rows = [
            _capacity_row(
                cell_by_id[item["cell_id"]],
                variant,
                MinimumFlexibilityCapacity(**item[variant]),
            )
            for item in policy_checkpoints
            for variant in ("correct", "b6")
        ]
        pair_rows = [item["row"] for item in pair_checkpoints]
        _write_gzip_csv(staging / "policy_table.csv.gz", _POLICY_FIELDS, policy_rows)
        _write_gzip_csv(
            staging / "pairwise_outcomes.csv.gz",
            _PAIR_FIELDS,
            pair_rows,
        )
        _write_gzip_csv(
            staging / "cell_status.csv.gz",
            _CELL_STATUS_FIELDS,
            status_rows,
        )
        _write_gzip_csv(
            staging / "power_system_holdout_marginal.csv.gz",
            ("id", "probability", "stress_score"),
            _marginal_rows(power_holdout, role="power"),
        )
        _write_gzip_csv(
            staging / "workload_holdout_marginal.csv.gz",
            ("id", "probability", "stress_score"),
            _marginal_rows(workload_holdout, role="workload"),
        )
        checkpoint_inventory = {
            f"policies/{cell.cell_id}.json": sha256_file(
                _checkpoint_path(
                    checkpoint_root / "policies",
                    cell.cell_id,
                )
            )
            for cell in cells
        }
        checkpoint_inventory.update(
            {
                (
                    f"pairs/{item['cell_id']}/{item['row_id']}__"
                    f"{item['column_id']}.json"
                ): sha256_file(
                    _checkpoint_path(
                        checkpoint_root / "pairs" / item["cell_id"],
                        f"{item['row_id']}__{item['column_id']}",
                    )
                )
                for item in pair_checkpoints
            }
        )
        checkpoint_inventory = dict(sorted(checkpoint_inventory.items()))
        write_json(
            staging / "checkpoint_inventory.json",
            checkpoint_inventory,
        )
        provenance_payload = {
            "base": stage_base,
            "checkpoint_inventory": checkpoint_inventory,
            "checkpoint_inventory_sha256": canonical_sha256(
                checkpoint_inventory
            ),
        }
        write_json(staging / "provenance.json", provenance_payload)
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": config_sha,
            "stage_base_provenance_sha256": stage_base_sha256,
            "provenance_sha256": sha256_file(staging / "provenance.json"),
            "checkpoint_inventory_sha256": canonical_sha256(
                checkpoint_inventory
            ),
            "power_system_dispatch_provenance_sha256": context[
                "power_provenance_sha256"
            ],
            "parameter_cell_count": len(cells),
            "training_resolved_cell_count": len(cells)
            - len(unresolved_training),
            "pairwise_eligible_cell_count": len(eligible_cells),
            "training_infeasible_cell_count": len(cells)
            - len(eligible_cells)
            - len(unresolved_training),
            "holdout_power_block_count": len(power_holdout),
            "holdout_workload_block_count": len(workload_holdout),
            "expected_pairs_per_eligible_cell": expected_per_cell,
            "pairwise_outcome_count": len(pair_rows),
            "all_eligible_pairwise_outcomes_resolved": not unresolved_pairs,
            "complete_cartesian_for_every_registered_cell": (
                len(eligible_cells) == len(cells) and not unresolved_pairs
            ),
            "training_infeasibility_is_not_pairwise_failure": True,
            "holdout_provision_reoptimized": False,
            "holdout_recourse_reoptimized": False,
            "operational_policy": (
                "causal_myopic_grid_first_then_CFE_with_current_state_only"
            ),
            "physical_execution_envelope": "correct_shared_envelope",
            "empirical_joint_distribution_claimed": False,
            "empirical_probability_claimed": False,
            "security_certified": False,
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = (
            "cell_status.csv.gz",
            "checkpoint_inventory.json",
            "pairwise_outcomes.csv.gz",
            "policy_table.csv.gz",
            "power_system_holdout_marginal.csv.gz",
            "provenance.json",
            "summary.json",
            "workload_holdout_marginal.csv.gz",
        )
        manifest = {name: _sha256(staging / name) for name in names}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_public_pairwise_replay_v2.yaml"),
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--maximum-pairs", type=int)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.config,
                validate_only=args.validate_only,
                maximum_pairs=args.maximum_pairs,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
