"""Derive checkpointed minimum grid-need trajectories for public RTS-GMLC blocks."""

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
from datetime import timezone
from itertools import pairwise
from pathlib import Path
from typing import Any

import yaml
from highspy import Highs

from src.evaluation.flexibility_envelope import ChronologicalFlexibilityEnvelope
from src.grid.chronological_dispatch import ChronologicalDispatchRequest
from src.grid.rts_gmlc import (
    RTS_GMLC_MANIFEST_SHA256,
    load_rts_gmlc_chronological_data,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)
from src.grid.rts_gmlc_grid_need import (
    RTS_GMLC_GRID_NEED_SCOPE,
    derive_hourly_rts_gmlc_grid_need,
)
from src.grid.rts_gmlc_scuc import (
    _extract_commitment,
    _extract_generation,
    _solve_normal_prescreen,
)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent

_ROOT = Path(__file__).resolve().parents[1]
_BLOCK_FIELDS = (
    "block_id",
    "split",
    "block_probability",
    "outage_seed",
    "hour_offset",
    "source_hour",
    "timestamp",
    "system_load_mw",
    "cfe_call_fraction",
    "active_event_id",
    "active_component_type",
    "active_component_uid",
)
_OUTPUT_FIELDS = (
    *_BLOCK_FIELDS,
    "grid_need_mw",
    "grid_need_fraction",
    "dispatch_resolved",
    "dispatch_proven_infeasible",
    "dispatch_termination_condition",
    "dispatch_solver_status",
    "maximum_constraint_violation",
)


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_json_manifest(directory: Path, expected_sha256: str) -> None:
    manifest_path = directory / "SHA256SUMS.json"
    if _sha256(manifest_path) != expected_sha256:
        raise ValueError("power-system block manifest SHA-256 drifted")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("power-system block manifest is invalid")
    for name, digest in manifest.items():
        if _sha256(directory / name) != digest:
            raise ValueError(f"power-system block member drifted: {name}")


def _read_blocks(path: Path) -> dict[str, list[dict[str, str]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(_BLOCK_FIELDS):
            raise ValueError("power-system block CSV schema drifted")
        rows = list(reader)
    if not rows:
        raise ValueError("power-system block CSV must be nonempty")
    blocks: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        blocks.setdefault(row["block_id"], []).append(row)
    for block_id, block in blocks.items():
        offsets = [int(row["hour_offset"]) for row in block]
        source_hours = [int(row["source_hour"]) for row in block]
        if offsets != list(range(len(block))):
            raise ValueError(f"block {block_id} hour offsets are not contiguous")
        if any(
            later != earlier + 1
            for earlier, later in pairwise(source_hours)
        ):
            raise ValueError(f"block {block_id} source hours are not contiguous")
        if len({row["split"] for row in block}) != 1:
            raise ValueError(f"block {block_id} crosses split labels")
        if len({row["outage_seed"] for row in block}) != 1:
            raise ValueError(f"block {block_id} crosses outage seeds")
        for row in block:
            event_fields = (
                row["active_event_id"],
                row["active_component_type"],
                row["active_component_uid"],
            )
            if bool(event_fields[0]) != all(bool(item) for item in event_fields):
                raise ValueError(f"block {block_id} has partial event identity")
    return blocks


def _read_marginal(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["id", "probability"]:
            raise ValueError("power-system marginal schema drifted")
        rows = list(reader)
    if not rows or abs(sum(float(row["probability"]) for row in rows) - 1.0) > 1e-9:
        raise ValueError("power-system marginal must be nonempty and sum to one")
    if len({row["id"] for row in rows}) != len(rows):
        raise ValueError("power-system marginal IDs must be unique")
    return rows


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


def _zero_envelope() -> ChronologicalFlexibilityEnvelope:
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=0.0,
        maximum_events_by_period={"block": 0},
        maximum_curtailment_energy_mwh_by_period={"block": 0.0},
        maximum_recovery_debt_mwh=0.0,
        maximum_recovery_power_mw=0.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=1.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={"block": 0.0},
        parameter_status="zero_flexibility_normal_baseline_only",
    )


def _normal_baseline(
    data: Any,
    source_hours: tuple[int, ...],
    *,
    dc_bus: int,
    dc_demand_mw: float,
    solver: Mapping[str, object],
) -> tuple[
    tuple[dict[str, float], ...],
    tuple[dict[str, bool], ...],
    dict[str, object],
]:
    points = tuple(data.hourly_points[hour] for hour in source_hours)
    generator_uids = tuple(generator.uid for generator in data.generators)
    availability = {
        generator.uid: bool(generator.enabled) for generator in data.generators
    }
    request = ChronologicalDispatchRequest(
        timestamps=tuple(
            point.timestamp.replace(tzinfo=timezone.utc) for point in points
        ),
        periods=("block",) * len(points),
        time_step_hours=1.0,
        system_demand_by_bus_mw=tuple(
            dict(point.demand_by_bus_mw) for point in points
        ),
        generator_availability=tuple(dict(availability) for _ in points),
        dc_bus=dc_bus,
        dc_requested_mw=(dc_demand_mw,) * len(points),
        dc_flexible_demand_mw=(0.0,) * len(points),
        dc_recoverable_flexible_mw=(0.0,) * len(points),
        dc_physical_maximum_mw=(dc_demand_mw,) * len(points),
        dc_connected_capacity_mw=(dc_demand_mw,) * len(points),
        dc_call_limit_mw=(0.0,) * len(points),
        recovery_headroom_mw=(0.0,) * len(points),
        flexibility_envelope=_zero_envelope(),
        flexibility_boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset({"block"}),
        initial_has_prior_event=False,
        initial_recovery_debt_mwh=0.0,
        initial_grid_call_mw=0.0,
        initial_active_event_duration_hours=0.0,
        initial_interevent_rest_hours=None,
        initial_event_count_by_period={},
        initial_curtailment_energy_mwh_by_period={},
        require_terminal_event_inactive=True,
        incidents=(),
        initial_commitment={uid: False for uid in generator_uids},
        initial_generation_mw={uid: 0.0 for uid in generator_uids},
        initial_time_in_state_hours={uid: 0.0 for uid in generator_uids},
    )
    if str(solver["name"]).lower() in {"highs", "appsi_highs"}:
        Highs.resetGlobalScheduler(True)
    context, model, audit, _, _ = _solve_normal_prescreen(
        data,
        request,
        points,
        solver_name=str(solver["name"]),
        tee=bool(solver["tee"]),
        tolerance=float(solver["tolerance_mw"]),
        solver_threads=int(solver["threads"]),
        mip_relative_gap=float(solver["mip_relative_gap"]),
    )
    if not audit.accepted:
        raise RuntimeError("normal block baseline was not accepted")
    return (
        _extract_generation(model, context, "normal"),
        _extract_commitment(model, context),
        asdict(audit),
    )


def _process_block(
    data: Any,
    block: list[dict[str, str]],
    *,
    dc_bus: int,
    dc_demand_mw: float,
    solver: Mapping[str, object],
) -> dict[str, object]:
    source_hours = tuple(int(row["source_hour"]) for row in block)
    has_event = any(row["active_event_id"] for row in block)
    if has_event:
        generation, commitment, baseline_audit = _normal_baseline(
            data,
            source_hours,
            dc_bus=dc_bus,
            dc_demand_mw=dc_demand_mw,
            solver=solver,
        )
    else:
        generation = tuple({} for _ in block)
        commitment = tuple({} for _ in block)
        baseline_audit = {
            "accepted": True,
            "termination_condition": "not_applicable_no_active_outage",
        }
    outcomes = []
    output_rows = []
    for index, row in enumerate(block):
        event = (
            N1OutageEvent(
                seed=int(row["outage_seed"]),
                event_id=row["active_event_id"],
                component_type=row["active_component_type"],
                uid=row["active_component_uid"],
                start_hour=int(row["source_hour"]),
                end_hour_exclusive=int(row["source_hour"]) + 1,
            )
            if row["active_event_id"]
            else None
        )
        outcome = derive_hourly_rts_gmlc_grid_need(
            data,
            data.hourly_points[int(row["source_hour"])],
            generation[index],
            commitment[index],
            event,
            source_hour=int(row["source_hour"]),
            dc_bus=dc_bus,
            dc_demand_mw=dc_demand_mw,
            solver_name=str(solver["name"]),
            tee=bool(solver["tee"]),
            tolerance_mw=float(solver["tolerance_mw"]),
        )
        outcomes.append(asdict(outcome))
        output_rows.append(
            {
                **row,
                "grid_need_mw": (
                    "" if outcome.grid_need_mw is None else outcome.grid_need_mw
                ),
                "grid_need_fraction": (
                    ""
                    if outcome.grid_need_mw is None
                    else outcome.grid_need_mw / dc_demand_mw
                ),
                "dispatch_resolved": str(outcome.resolved).lower(),
                "dispatch_proven_infeasible": str(
                    outcome.proven_infeasible
                ).lower(),
                "dispatch_termination_condition": outcome.termination_condition,
                "dispatch_solver_status": outcome.solver_status,
                "maximum_constraint_violation": (
                    ""
                    if outcome.maximum_constraint_violation is None
                    else outcome.maximum_constraint_violation
                ),
            }
        )
    return {
        "block_id": block[0]["block_id"],
        "split": block[0]["split"],
        "baseline_audit": baseline_audit,
        "all_hours_resolved": all(item["resolved"] for item in outcomes),
        "outcomes": outcomes,
        "rows": output_rows,
    }


def _checkpoint_path(directory: Path, block_id: str) -> Path:
    if not block_id.replace("_", "").isalnum():
        raise ValueError("block_id is not safe for checkpoint naming")
    return directory / f"{block_id}.json"


def _write_checkpoint(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _preflight(
    config_path: Path,
) -> tuple[
    dict[str, Any],
    Path,
    dict[str, list[dict[str, str]]],
    dict[str, list[dict[str, str]]],
]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    package = _path(
        config["input"]["power_system_blocks_package"],
        "power_system_blocks_package",
    )
    _verify_json_manifest(
        package,
        config["input"]["power_system_blocks_manifest_sha256"],
    )
    blocks = _read_blocks(package / "power_system_blocks.csv.gz")
    marginals = {
        split: _read_marginal(package / f"{split}_marginal.csv.gz")
        for split in ("training", "holdout")
    }
    for split, rows in marginals.items():
        expected = {
            block_id
            for block_id, block in blocks.items()
            if block[0]["split"] == split
        }
        if {row["id"] for row in rows} != expected:
            raise ValueError(f"{split} marginal IDs do not match block IDs")
    grid = config["grid_source"]
    validate_rts_gmlc_source_identity(grid)
    if grid["manifest_sha256"] != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest identity drifted")
    grid_root = _path(grid["path"], "grid_source.path")
    if (
        _sha256(grid_root / "SHA256SUMS") != grid["manifest_sha256"]
        or not verify_sha256_manifest(grid_root)
    ):
        raise ValueError("RTS-GMLC source manifest verification failed")
    model = config["model"]
    expected_model = {
        "dc_bus": 108,
        "dc_reference_demand_mw": 250.0,
        "time_step_hours": 1.0,
        "normal_baseline": "free_boundary_24h_normal_state_SCUC",
        "outage_response": (
            "fixed_commitment_and_normal_dispatch_hourly_corrective_LP"
        ),
        "branch_rating": "continuous",
        "generator_response_limit": "published_hourly_ramp",
        "load_shedding_allowed": False,
        "full_N_minus_one": False,
        "AC_security": False,
    }
    if model != expected_model:
        raise ValueError("grid-need model contract drifted")
    return config, grid_root, blocks, marginals


def run(
    config_path: Path,
    *,
    validate_only: bool = False,
    maximum_blocks: int | None = None,
) -> dict[str, object]:
    config_path = config_path.resolve()
    config, grid_root, blocks, marginals = _preflight(config_path)
    execution = config["execution"]
    if validate_only:
        return {
            "schema": "rts_gmlc_public_grid_need_dispatch_preflight_v1",
            "config_sha256": _sha256(config_path),
            "power_system_block_count": len(blocks),
            "training_block_count": len(marginals["training"]),
            "holdout_block_count": len(marginals["holdout"]),
            "formal_execution_ready": execution["formal_execution_ready"],
            "independent_R4_review_passed": execution[
                "independent_R4_review_passed"
            ],
            "user_formal_run_authorized": execution[
                "user_formal_run_authorized"
            ],
        }
    if (
        execution["formal_execution_ready"] is not True
        or execution["independent_R4_review_passed"] is not True
        or execution["user_formal_run_authorized"] is not True
    ):
        raise ValueError(
            "formal_execution_ready, independent_R4_review_passed, and "
            "user_formal_run_authorized must all be true before dispatch"
        )
    if maximum_blocks is not None and (
        isinstance(maximum_blocks, bool) or maximum_blocks <= 0
    ):
        raise ValueError("maximum_blocks must be a positive integer")

    implementation_sha = _sha256(Path(__file__))
    config_sha = _sha256(config_path)
    input_manifest_sha = config["input"]["power_system_blocks_manifest_sha256"]
    checkpoint_directory = _path(
        execution["checkpoint_directory"],
        "execution.checkpoint_directory",
    )
    data = load_rts_gmlc_chronological_data(
        grid_root,
        base_mva=float(config["grid_source"]["base_mva"]),
    )
    processed = 0
    for block_id in sorted(blocks):
        checkpoint_path = _checkpoint_path(checkpoint_directory, block_id)
        if checkpoint_path.exists():
            checkpoint = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            expected_identity = {
                "block_id": block_id,
                "config_sha256": config_sha,
                "implementation_sha256": implementation_sha,
                "input_manifest_sha256": input_manifest_sha,
            }
            if any(
                checkpoint.get(key) != expected
                for key, expected in expected_identity.items()
            ):
                raise ValueError(f"checkpoint identity drifted: {block_id}")
            continue
        result = _process_block(
            data,
            blocks[block_id],
            dc_bus=int(config["model"]["dc_bus"]),
            dc_demand_mw=float(config["model"]["dc_reference_demand_mw"]),
            solver=config["solver"],
        )
        checkpoint = {
            "schema": "rts_gmlc_public_grid_need_block_checkpoint_v1",
            "config_sha256": config_sha,
            "implementation_sha256": implementation_sha,
            "input_manifest_sha256": input_manifest_sha,
            **result,
        }
        _write_checkpoint(checkpoint_path, checkpoint)
        processed += 1
        if maximum_blocks is not None and processed >= maximum_blocks:
            return {
                "schema": "rts_gmlc_public_grid_need_dispatch_progress_v1",
                "processed_this_call": processed,
                "total_blocks": len(blocks),
                "checkpoint_directory": str(checkpoint_directory),
                "formal_result_published": False,
            }

    checkpoints = []
    for block_id in sorted(blocks):
        path = _checkpoint_path(checkpoint_directory, block_id)
        if not path.exists():
            raise RuntimeError(f"missing completed checkpoint: {block_id}")
        checkpoints.append(json.loads(path.read_text(encoding="utf-8")))
    all_resolved = all(item["all_hours_resolved"] for item in checkpoints)
    if execution["require_all_blocks_resolved"] and not all_resolved:
        raise RuntimeError("at least one grid-need block remains unresolved")

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        rows = [row for checkpoint in checkpoints for row in checkpoint["rows"]]
        _write_gzip_csv(
            staging / "dispatched_power_system_blocks.csv.gz",
            _OUTPUT_FIELDS,
            rows,
        )
        for split in ("training", "holdout"):
            _write_gzip_csv(
                staging / f"{split}_marginal.csv.gz",
                ("id", "probability"),
                marginals[split],
            )
        block_status = [
            {
                "block_id": item["block_id"],
                "split": item["split"],
                "all_hours_resolved": item["all_hours_resolved"],
                "baseline_accepted": item["baseline_audit"]["accepted"],
            }
            for item in checkpoints
        ]
        _write_gzip_csv(
            staging / "block_status.csv.gz",
            (
                "block_id",
                "split",
                "all_hours_resolved",
                "baseline_accepted",
            ),
            block_status,
        )
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": config_sha,
            "implementation_sha256": implementation_sha,
            "grid_need_module_sha256": _sha256(
                _ROOT / "src/grid/rts_gmlc_grid_need.py"
            ),
            "input_manifest_sha256": input_manifest_sha,
            "block_count": len(checkpoints),
            "training_block_count": len(marginals["training"]),
            "holdout_block_count": len(marginals["holdout"]),
            "all_blocks_resolved": all_resolved,
            "grid_need_scope": RTS_GMLC_GRID_NEED_SCOPE,
            "formal_execution_authorized": True,
            "empirical_outage_probability_claimed": False,
            "full_N_minus_one": False,
            "AC_security": False,
            "security_certified": False,
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = (
            "block_status.csv.gz",
            "dispatched_power_system_blocks.csv.gz",
            "holdout_marginal.csv.gz",
            "summary.json",
            "training_marginal.csv.gz",
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
        default=Path("configs/rts_gmlc_public_grid_need_dispatch_v1.yaml"),
    )
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--maximum-blocks", type=int)
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.config,
                validate_only=args.validate_only,
                maximum_blocks=args.maximum_blocks,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
