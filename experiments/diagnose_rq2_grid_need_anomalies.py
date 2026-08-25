"""Diagnose the frozen RQ2 grid-need infeasibility checkpoints."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from dataclasses import asdict, replace
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rts_gmlc_public_grid_need_dispatch_v3 import (
    _normal_baseline,
    _preflight,
)
from src.evaluation.rq2_provenance_v2 import load_json_strict
from src.grid.rts_gmlc import load_rts_gmlc_chronological_data
from src.grid.rts_gmlc_grid_need_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
    assess_hourly_rts_gmlc_grid_need,
)
from src.scenarios.rts_gmlc_n1_chronology import N1OutageEvent
from src.solvers.rq2_solver_adapter import solver_spec

_ROOT = Path(__file__).resolve().parents[1]


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if config.get("schema") != "rq2_grid_need_anomaly_diagnostic_config_v1":
        raise ValueError("diagnostic config schema drifted")
    if config["scope"] != {
        "evidence_level": "development_diagnostic",
        "formal_grid_execution": False,
        "blocks": config["scope"]["blocks"],
    }:
        raise ValueError("diagnostic scope drifted")
    parent = config["parent"]
    parent_path = _path(parent["config_path"], "parent.config_path")
    if _sha256(parent_path) != parent["config_sha256"]:
        raise ValueError("parent grid config drifted")
    for key in ("runner", "grid_need_module"):
        if _sha256(_path(parent[f"{key}_path"], f"parent.{key}_path")) != parent[
            f"{key}_sha256"
        ]:
            raise ValueError(f"parent {key} drifted")
    return config


def run(config_path: Path) -> dict[str, object]:
    config_path = config_path.resolve()
    config = _load_config(config_path)
    parent_path = _path(config["parent"]["config_path"], "parent.config_path")
    parent, grid_root, blocks, _, _ = _preflight(parent_path)
    spec = solver_spec(config["solver"])
    if spec.name != parent["solver"]["name"]:
        raise ValueError("diagnostic and parent solver identities differ")
    data = load_rts_gmlc_chronological_data(
        grid_root,
        base_mva=float(parent["grid_source"]["base_mva"]),
    )
    relaxed_data = replace(
        data,
        branches=tuple(
            replace(
                branch,
                continuous_rating_mw=float(
                    config["diagnostic"]["thermal_relaxation_rating_mw"]
                ),
            )
            for branch in data.branches
        ),
    )
    checkpoint_root = _path(
        config["parent"]["checkpoint_directory"],
        "parent.checkpoint_directory",
    )
    rows = []
    for block_id, frozen in config["scope"]["blocks"].items():
        checkpoint_path = checkpoint_root / f"{block_id}.json"
        if _sha256(checkpoint_path) != frozen["checkpoint_sha256"]:
            raise ValueError(f"diagnostic checkpoint drifted: {block_id}")
        checkpoint = load_json_strict(checkpoint_path)
        expected_hours = tuple(int(value) for value in frozen["expected_source_hours"])
        observed_hours = tuple(
            int(item["source_hour"])
            for item in checkpoint["outcomes"]
            if item["proven_infeasible"]
        )
        if observed_hours != expected_hours:
            raise ValueError(f"checkpoint anomaly hours drifted: {block_id}")
        block = blocks[block_id]
        source_hours = tuple(int(item["source_hour"]) for item in block)
        generation, commitment, baseline_audit = _normal_baseline(
            data,
            source_hours,
            dc_bus=int(parent["model"]["dc_bus"]),
            dc_demand_mw=float(parent["model"]["dc_reference_demand_mw"]),
            solver=parent["solver"],
        )
        if not baseline_audit["accepted"]:
            raise RuntimeError(f"baseline was not accepted: {block_id}")
        by_hour = {int(item["source_hour"]): item for item in block}
        index_by_hour = {
            int(item["source_hour"]): index for index, item in enumerate(block)
        }
        for source_hour in expected_hours:
            source = by_hour[source_hour]
            event = N1OutageEvent(
                seed=int(source["outage_seed"]),
                event_id=source["active_event_id"],
                component_type=source["active_component_type"],
                uid=source["active_component_uid"],
                start_hour=source_hour,
                end_hour_exclusive=source_hour + 1,
            )
            index = index_by_hour[source_hour]
            arguments = {
                "point": data.hourly_points[source_hour],
                "baseline_generation_mw": generation[index],
                "baseline_commitment": commitment[index],
                "event": event,
                "source_hour": source_hour,
                "dc_bus": int(parent["model"]["dc_bus"]),
                "dc_demand_mw": float(
                    parent["model"]["dc_reference_demand_mw"]
                ),
                "solver_specification": spec,
                "tolerance_mw": float(parent["solver"]["tolerance_mw"]),
            }
            primary = assess_hourly_rts_gmlc_grid_need(data, **arguments)
            thermal_relaxation = assess_hourly_rts_gmlc_grid_need(
                relaxed_data,
                **arguments,
            )
            if (
                config["diagnostic"]["require_zero_dc_endpoint_infeasible"]
                and primary.state != EXOGENOUS_GRID_INFEASIBILITY
            ):
                raise RuntimeError("zero-DC endpoint did not confirm E0")
            rows.append(
                {
                    "block_id": block_id,
                    "source_hour": source_hour,
                    "event_id": event.event_id,
                    "component_type": event.component_type,
                    "component_uid": event.uid,
                    "baseline_audit": baseline_audit,
                    "assessment": asdict(primary),
                    "thermal_relaxation_assessment": asdict(
                        thermal_relaxation
                    ),
                    "thermal_limits_are_binding_evidence": (
                        thermal_relaxation.state == FINITE_GRID_NEED
                    ),
                }
            )
    summary = {
        "schema": config["output"]["schema"],
        "config_sha256": _sha256(config_path),
        "diagnosed_hour_count": len(rows),
        "all_hours_classified_exogenous_grid_infeasibility": all(
            row["assessment"]["state"] == EXOGENOUS_GRID_INFEASIBILITY
            for row in rows
        ),
        "all_hours_recover_when_thermal_limits_are_relaxed": all(
            row["thermal_limits_are_binding_evidence"] for row in rows
        ),
        "cross_solver_confirmation_completed": False,
        "formal_grid_execution_started": False,
        "security_certified": False,
    }
    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        (staging / "diagnostic.json").write_text(
            json.dumps(rows, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest = {
            name: _sha256(staging / name)
            for name in ("diagnostic.json", "summary.json")
        }
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
        default=Path("configs/rq2_grid_need_anomaly_diagnostic_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
