"""Run the frozen four-block HiGHS/Gurobi RQ2 successor pilot."""

from __future__ import annotations

import argparse
import json
import shutil
import statistics
import tempfile
import time
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from experiments.preflight_rq2_public_executor_v1 import _verify_bundle
from experiments.run_rts_gmlc_public_grid_need_dispatch_v4 import (
    _normal_baseline,
    _read_blocks,
    _sha256,
    _verify_json_manifest,
)
from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.evaluation.rq2_provenance_v3 import load_json_strict
from src.grid.rts_gmlc import (
    RTS_GMLC_MANIFEST_SHA256,
    load_rts_gmlc_chronological_data,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)
from src.grid.rts_gmlc_grid_need_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    assess_hourly_rts_gmlc_grid_need,
)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
from src.solvers.rq2_solver_adapter import solver_spec

_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_SCHEMA = "rq2_public_solver_pilot_config_v1"


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _event(row: dict[str, str]) -> N1OutageEvent | None:
    if not row["active_event_id"]:
        return None
    source_hour = int(row["source_hour"])
    return N1OutageEvent(
        seed=int(row["outage_seed"]),
        event_id=row["active_event_id"],
        component_type=row["active_component_type"],
        uid=row["active_component_uid"],
        start_hour=source_hour,
        end_hour_exclusive=source_hour + 1,
    )


def _preflight(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema") != _CONFIG_SCHEMA:
        raise ValueError("solver pilot config schema drifted")
    implementation = config["implementation"]
    runner_path = _path(implementation["runner_path"], "implementation.runner_path")
    if (
        runner_path.resolve() != Path(__file__).resolve()
        or _sha256(runner_path) != implementation["runner_sha256"]
    ):
        raise ValueError("solver pilot implementation drifted")
    bundle = config["bundle"]
    handoff_path = _path(bundle["handoff_path"], "bundle.handoff_path")
    if _sha256(handoff_path) != bundle["handoff_sha256"]:
        raise ValueError("solver pilot handoff authority drifted")
    handoff = yaml.safe_load(handoff_path.read_text(encoding="utf-8"))
    if (
        not isinstance(handoff, dict)
        or handoff.get("schema")
        != "rq2_public_executor_handoff_config_v1"
    ):
        raise ValueError("solver pilot handoff schema drifted")
    bundle_report = _verify_bundle(handoff)
    scope = config["scope"]
    if (
        scope.get("evidence_level") != "nonformal_cross_solver_pilot"
        or scope.get("formal_grid_execution") is not False
        or scope.get("formal_pairwise_execution") is not False
        or scope.get("formal_identification_execution") is not False
        or scope.get("source_outcomes_observed") is not True
        or scope.get("pilot_results_observed") is not False
    ):
        raise ValueError("solver pilot scope drifted")
    package = _path(
        config["input"]["power_system_blocks_package"],
        "power_system_blocks_package",
    )
    _verify_json_manifest(
        package,
        str(config["input"]["power_system_blocks_manifest_sha256"]),
    )
    package_summary = load_json_strict(package / "summary.json")
    if (
        not isinstance(package_summary, dict)
        or package_summary.get("schema")
        != config["input"]["power_system_blocks_schema"]
    ):
        raise ValueError("power-system block package schema drifted")
    blocks = _read_blocks(package / "power_system_blocks.csv.gz")
    pilot_rows = config["pilot_blocks"]
    pilot_ids = tuple(item["block_id"] for item in pilot_rows)
    if (
        len(pilot_ids) != 4
        or len(set(pilot_ids)) != 4
        or any(block_id not in blocks for block_id in pilot_ids)
    ):
        raise ValueError("solver pilot block inventory drifted")
    expected_hours = {
        item["block_id"]: tuple(int(value) for value in item["expected_exogenous_source_hours"])
        for item in pilot_rows
    }
    if expected_hours != {
        "holdout_s20260822_0013": (),
        "holdout_s20260822_0091": (),
        "holdout_s20260822_0089": (6598,),
        "holdout_s20260822_0150": (8057, 8058, 8059),
    }:
        raise ValueError("solver pilot E0 expectations drifted")
    specifications = {
        name: solver_spec(payload)
        for name, payload in config["solvers"].items()
    }
    if set(specifications) != {"highs", "gurobi"} or any(
        name != specification.name
        for name, specification in specifications.items()
    ):
        raise ValueError("solver pilot matrix drifted")
    execution = config["execution"]
    repetitions = int(execution["repetitions"])
    expected_run_ids = {
        f"{solver}_r{repetition}"
        for solver in specifications
        for repetition in range(1, repetitions + 1)
    }
    execution_order = execution["execution_order"]
    if (
        repetitions != 2
        or len(execution_order) != len(expected_run_ids)
        or set(execution_order) != expected_run_ids
        or execution.get("pilot_execution_authorized") is not True
    ):
        raise ValueError("solver pilot execution contract drifted")
    grid_source = {
        "repository": "https://github.com/GridMod/RTS-GMLC",
        "release": "v0.2.3",
        "commit": "3ece0d3725c844056132393ee252b3083dd4eab4",
        "path": config["input"]["grid_source_path"],
        "manifest_sha256": config["input"]["grid_source_manifest_sha256"],
    }
    validate_rts_gmlc_source_identity(grid_source)
    if grid_source["manifest_sha256"] != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest identity drifted")
    grid_root = _path(grid_source["path"], "grid_source_path")
    if (
        _sha256(grid_root / "SHA256SUMS") != grid_source["manifest_sha256"]
        or not verify_sha256_manifest(grid_root)
    ):
        raise ValueError("RTS-GMLC source manifest verification failed")
    return config, {
        "blocks": {block_id: blocks[block_id] for block_id in pilot_ids},
        "expected_exogenous_hours": expected_hours,
        "grid_root": grid_root,
        "solver_specifications": specifications,
        "report": {
            "schema": "rq2_public_solver_pilot_preflight_v1",
            "config_sha256": _sha256(config_path),
            "implementation_sha256": implementation["runner_sha256"],
            "bundle_manifest_sha256": bundle_report[
                "bundle_manifest_sha256"
            ],
            "pilot_blocks": list(pilot_ids),
            "solver_names": sorted(specifications),
            "execution_host": execution_host_status(execution),
            "formal_grid_execution_started": False,
        },
    }


def _run_block(
    data: Any,
    block: list[dict[str, str]],
    *,
    solver_payload: dict[str, object],
    dc_bus: int,
    dc_demand_mw: float,
    tolerance_mw: float,
) -> dict[str, object]:
    source_hours = tuple(int(row["source_hour"]) for row in block)
    baseline_started = time.perf_counter()
    generation, commitment, baseline_audit = _normal_baseline(
        data,
        source_hours,
        dc_bus=dc_bus,
        dc_demand_mw=dc_demand_mw,
        solver={**solver_payload, "tolerance_mw": tolerance_mw},
    )
    baseline_wall = time.perf_counter() - baseline_started
    specification = solver_spec(solver_payload)
    hourly_started = time.perf_counter()
    hours = []
    for index, row in enumerate(block):
        assessment = assess_hourly_rts_gmlc_grid_need(
            data,
            data.hourly_points[int(row["source_hour"])],
            generation[index],
            commitment[index],
            _event(row),
            source_hour=int(row["source_hour"]),
            dc_bus=dc_bus,
            dc_demand_mw=dc_demand_mw,
            solver_specification=specification,
            tolerance_mw=tolerance_mw,
        )
        hours.append(
            {
                "source_hour": int(row["source_hour"]),
                "active_event_id": row["active_event_id"] or None,
                **asdict(assessment),
            }
        )
    hourly_wall = time.perf_counter() - hourly_started
    return {
        "block_id": block[0]["block_id"],
        "baseline_wall_seconds": baseline_wall,
        "hourly_wall_seconds": hourly_wall,
        "total_wall_seconds": baseline_wall + hourly_wall,
        "baseline_audit": baseline_audit,
        "hours": hours,
    }


def _within(left: float | None, right: float | None, tolerance: float) -> bool:
    return left is not None and right is not None and abs(left - right) <= tolerance


def _same_optional(
    left: float | None,
    right: float | None,
    tolerance: float,
) -> bool:
    if left is None or right is None:
        return left is None and right is None
    return abs(float(left) - float(right)) <= tolerance


def _certificate_matches(
    left: dict[str, object] | None,
    right: dict[str, object] | None,
    *,
    absolute_tolerance: float,
    relative_tolerance: float,
) -> bool:
    if left is None or right is None:
        return left is None and right is None
    if (
        left["model_variables"] != right["model_variables"]
        or left["model_constraints"] != right["model_constraints"]
    ):
        return False
    absolute_fields = (
        "objective_incumbent_mw",
        "lower_bound_mw",
        "upper_bound_mw",
        "absolute_gap_mw",
        "gap_tolerance_mw",
    )
    return all(
        _same_optional(left[field], right[field], absolute_tolerance)
        for field in absolute_fields
    ) and _same_optional(
        left["relative_gap"],
        right["relative_gap"],
        relative_tolerance,
    )


def _hour_status_matches(
    left: dict[str, object],
    right: dict[str, object],
) -> bool:
    for field in ("primary", "zero_dc_confirmation"):
        left_result = left[field]
        right_result = right[field]
        if left_result is None or right_result is None:
            if left_result is not None or right_result is not None:
                return False
            continue
        if (
            left_result["termination_condition"]
            != right_result["termination_condition"]
            or left_result["solver_status"] != right_result["solver_status"]
        ):
            return False
    return True


def _compare(
    config: dict[str, Any],
    context: dict[str, Any],
    runs: list[dict[str, object]],
) -> dict[str, object]:
    acceptance = config["acceptance"]
    objective_tolerance = float(
        acceptance["maximum_baseline_objective_difference_usd"]
    )
    grid_tolerance = float(
        acceptance["maximum_finite_grid_need_difference_mw"]
    )
    residual_limit = float(acceptance["maximum_constraint_violation"])
    relative_gap_tolerance = max(
        float(payload["mip_relative_gap"])
        for payload in config["solvers"].values()
    )
    records = {
        (run["solver_name"], run["repetition"], block["block_id"]): {
            **block,
            "solver_name": run["solver_name"],
            "repetition": run["repetition"],
        }
        for run in runs
        for block in run["blocks"]
    }
    checks = []
    for block_id, expected_e0_hours in context[
        "expected_exogenous_hours"
    ].items():
        block_records = [
            record
            for key, record in records.items()
            if key[2] == block_id
        ]
        checks.append(
            {
                "block_id": block_id,
                "check": "all_baselines_accepted",
                "passed": all(
                    record["baseline_audit"]["accepted"]
                    and record["baseline_audit"]["relative_gap"] is not None
                    and record["baseline_audit"]["maximum_constraint_violation"]
                    <= residual_limit
                    for record in block_records
                ),
            }
        )
        checks.append(
            {
                "block_id": block_id,
                "check": "expected_E0_hour_set",
                "passed": all(
                    tuple(
                        hour["source_hour"]
                        for hour in record["hours"]
                        if hour["state"] == EXOGENOUS_GRID_INFEASIBILITY
                    )
                    == expected_e0_hours
                    for record in block_records
                ),
            }
        )
        checks.append(
            {
                "block_id": block_id,
                "check": "all_hours_resolved_for_pipeline",
                "passed": all(
                    all(hour["resolved_for_pipeline"] for hour in record["hours"])
                    for record in block_records
                ),
            }
        )
        checks.append(
            {
                "block_id": block_id,
                "check": "finite_hour_residuals",
                "passed": all(
                    hour["state"] != FINITE_GRID_NEED
                    or hour["primary"]["maximum_constraint_violation"]
                    <= residual_limit
                    for record in block_records
                    for hour in record["hours"]
                ),
            }
        )
        for left_index, left in enumerate(block_records):
            for right in block_records[left_index + 1 :]:
                pair = (
                    f"{left['solver_name']}_r{left['repetition']}__"
                    f"{right['solver_name']}_r{right['repetition']}"
                )
                left_audit = left["baseline_audit"]
                right_audit = right["baseline_audit"]
                checks.extend(
                    (
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "baseline_model_scale",
                            "passed": (
                                left_audit["model_variables"]
                                == right_audit["model_variables"]
                                and left_audit["model_constraints"]
                                == right_audit["model_constraints"]
                            ),
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "baseline_termination_and_status",
                            "passed": (
                                left_audit["termination_condition"]
                                == right_audit["termination_condition"]
                                and left_audit["solver_status"]
                                == right_audit["solver_status"]
                            ),
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "baseline_incumbent_bounds_and_gap",
                            "passed": all(
                                _same_optional(
                                    left_audit[field],
                                    right_audit[field],
                                    objective_tolerance,
                                )
                                for field in (
                                    "objective_usd",
                                    "lower_bound_usd",
                                    "upper_bound_usd",
                                    "absolute_gap_usd",
                                    "gap_tolerance_usd",
                                )
                            ),
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "baseline_relative_gap",
                            "passed": _same_optional(
                                left_audit["relative_gap"],
                                right_audit["relative_gap"],
                                relative_gap_tolerance,
                            ),
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "baseline_residuals",
                            "passed": all(
                                _same_optional(
                                    left_audit[field],
                                    right_audit[field],
                                    residual_limit,
                                )
                                for field in (
                                    "maximum_constraint_violation",
                                    "maximum_integrality_violation",
                                )
                            ),
                        },
                    )
                )
                left_hours = {
                    hour["source_hour"]: hour for hour in left["hours"]
                }
                right_hours = {
                    hour["source_hour"]: hour for hour in right["hours"]
                }
                states_match = all(
                    left_hours[hour]["state"] == right_hours[hour]["state"]
                    for hour in left_hours
                )
                finite_values_match = all(
                    left_hours[hour]["state"] != FINITE_GRID_NEED
                    or _within(
                        left_hours[hour]["primary"]["grid_need_mw"],
                        right_hours[hour]["primary"]["grid_need_mw"],
                        grid_tolerance,
                    )
                    for hour in left_hours
                )
                model_scales_match = all(
                    all(
                        (
                            left_hours[hour][certificate]["model_variables"],
                            left_hours[hour][certificate][
                                "model_constraints"
                            ],
                        )
                        == (
                            right_hours[hour][certificate]["model_variables"],
                            right_hours[hour][certificate][
                                "model_constraints"
                            ],
                        )
                        for certificate in (
                            "primary_certificate",
                            "zero_dc_confirmation_certificate",
                        )
                        if left_hours[hour][certificate] is not None
                        and right_hours[hour][certificate] is not None
                    )
                    and (
                        (
                            left_hours[hour][
                                "zero_dc_confirmation_certificate"
                            ]
                            is None
                        )
                        == (
                            right_hours[hour][
                                "zero_dc_confirmation_certificate"
                            ]
                            is None
                        )
                    )
                    for hour in left_hours
                )
                status_matches = all(
                    _hour_status_matches(
                        left_hours[hour],
                        right_hours[hour],
                    )
                    for hour in left_hours
                )
                certificates_match = all(
                    _certificate_matches(
                        left_hours[hour][certificate],
                        right_hours[hour][certificate],
                        absolute_tolerance=grid_tolerance,
                        relative_tolerance=relative_gap_tolerance,
                    )
                    for hour in left_hours
                    for certificate in (
                        "primary_certificate",
                        "zero_dc_confirmation_certificate",
                    )
                )
                residuals_match = all(
                    _same_optional(
                        left_hours[hour][result][
                            "maximum_constraint_violation"
                        ],
                        right_hours[hour][result][
                            "maximum_constraint_violation"
                        ],
                        residual_limit,
                    )
                    for hour in left_hours
                    for result in ("primary", "zero_dc_confirmation")
                    if left_hours[hour][result] is not None
                    and right_hours[hour][result] is not None
                ) and all(
                    (left_hours[hour][result] is None)
                    == (right_hours[hour][result] is None)
                    for hour in left_hours
                    for result in ("primary", "zero_dc_confirmation")
                )
                checks.extend(
                    (
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "hourly_state_classification",
                            "passed": states_match,
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "finite_grid_need",
                            "passed": finite_values_match,
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "corrective_model_scale",
                            "passed": model_scales_match,
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "hourly_termination_and_status",
                            "passed": status_matches,
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "hourly_incumbent_bounds_and_gap",
                            "passed": certificates_match,
                        },
                        {
                            "block_id": block_id,
                            "comparison": pair,
                            "check": "hourly_residuals",
                            "passed": residuals_match,
                        },
                    )
                )
    wall_times: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for run in runs:
        for block in run["blocks"]:
            wall_times[run["solver_name"]][block["block_id"]].append(
                float(block["total_wall_seconds"])
            )
    wall_summary = {
        solver: {
            block_id: {
                "repetitions": len(values),
                "median_seconds": statistics.median(values),
                "maximum_seconds": max(values),
            }
            for block_id, values in sorted(blocks.items())
        }
        for solver, blocks in sorted(wall_times.items())
    }
    failed = [check for check in checks if not check["passed"]]
    return {
        "checks": checks,
        "failed_checks": failed,
        "all_non_runtime_acceptance_checks_passed": not failed,
        "gurobi_eligible_for_formal_successor": not failed,
        "wall_time_summary": wall_summary,
    }


def run(
    config_path: Path,
    *,
    validate_only: bool = False,
) -> dict[str, object]:
    config_path = config_path.resolve()
    config, context = _preflight(config_path)
    if validate_only:
        return context["report"]
    require_execution_host(config["execution"])
    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite pilot output: {target}")
    data = load_rts_gmlc_chronological_data(
        context["grid_root"],
        base_mva=float(config["input"]["base_mva"]),
    )
    run_records = []
    for run_id in config["execution"]["execution_order"]:
        solver_name, repetition_text = run_id.rsplit("_r", maxsplit=1)
        blocks = []
        for pilot in config["pilot_blocks"]:
            result = _run_block(
                data,
                context["blocks"][pilot["block_id"]],
                solver_payload=config["solvers"][solver_name],
                dc_bus=int(config["model"]["dc_bus"]),
                dc_demand_mw=float(
                    config["model"]["dc_reference_demand_mw"]
                ),
                tolerance_mw=float(config["model"]["tolerance_mw"]),
            )
            result["role"] = pilot["role"]
            blocks.append(result)
        run_records.append(
            {
                "run_id": run_id,
                "solver_name": solver_name,
                "repetition": int(repetition_text),
                "blocks": blocks,
            }
        )
    comparison = _compare(config, context, run_records)
    config_sha = _sha256(config_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        if _sha256(config_path) != config_sha:
            raise ValueError("solver pilot config drifted during execution")
        shutil.copyfile(config_path, staging / "config.yaml")
        (staging / "runs.json").write_text(
            json.dumps(run_records, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / "comparison.json").write_text(
            json.dumps(comparison, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": config_sha,
            "implementation_sha256": config["implementation"]["runner_sha256"],
            "bundle_manifest_sha256": context["report"][
                "bundle_manifest_sha256"
            ],
            "pilot_block_count": len(config["pilot_blocks"]),
            "solver_count": len(config["solvers"]),
            "repetitions_per_solver": int(
                config["execution"]["repetitions"]
            ),
            "gurobi_eligible_for_formal_successor": comparison[
                "gurobi_eligible_for_formal_successor"
            ],
            "failed_check_count": len(comparison["failed_checks"]),
            "formal_grid_execution_started": False,
            "timeout_is_infeasibility_evidence": False,
            "security_certified": False,
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = ("comparison.json", "config.yaml", "runs.json", "summary.json")
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
        default=Path("configs/rq2_public_solver_pilot_v1.yaml"),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.config, validate_only=args.validate_only),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
