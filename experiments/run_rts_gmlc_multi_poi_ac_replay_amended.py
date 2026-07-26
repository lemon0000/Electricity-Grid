"""Apply the frozen grid-point lookup amendment to the AC replay batch."""

from __future__ import annotations

import argparse
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json, _write_csv
from experiments.run_rts_gmlc_multi_poi_ac_replay import (
    _CASE_FIELDS,
    _EVIDENCE,
    _PREREGISTRATION,
    _SUMMARY_FIELDS,
    _build_context,
    _evaluate_cases,
    _group_summaries,
    _load_json,
    _require_preregistration,
)
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json

_AMENDMENT = {
    "id": "rts_gmlc_ac_replay_grid_point_lookup_amendment_001",
    "schema": "rts_gmlc_ac_replay_implementation_amendment_v1",
    "parent_preregistration_id": "rts_gmlc_google_day0_multi_poi_ac_replay_v1",
    "parent_input_contract_sha256": (
        "7dc28350aaa137a3f99a90a83365ebafb58c8de739a2999a5a93ed4ea0babd41"
    ),
    "parent_runner_sha256": (
        "0e2277f9c8096eaff695f70f95cc3e3898cf42ea0d69339cad8655e66c5d6e06"
    ),
    "parent_ac_module_sha256": (
        "dafb8b307b074f3cf9079c5e80f8e2a1077550e9d0dec93edc4dc33676dc8c0e"
    ),
    "status": "repository_local_amendment_after_pre_batch_lookup_failure",
    "externally_timestamped": False,
}
_OBSERVED = {
    "batch_ac_case_outcomes_observed": False,
    "failure_type": "AttributeError",
    "failure_detail": "business_chronology_point_has_no_demand_by_bus_mw",
    "failure_stage": "before_first_ac_case_configuration_or_power_flow",
}
_SCOPE = {
    "permitted_change": (
        "map_parent_business_timestamps_to_same_clock_rts_gmlc_hourly_grid_points"
    ),
    "forbidden_changes": [
        "parent_config",
        "representative_candidates",
        "hours_or_security_states",
        "power_factor_cases",
        "source_or_parent_artifacts",
        "ac_case_assumptions",
        "power_flow_options",
        "ac_case_module",
        "result_acceptance_or_summary_rules",
    ],
}


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "amendment": _AMENDMENT,
        "observed_before_amendment": _OBSERVED,
        "scope": _SCOPE,
    }
    if not isinstance(config, dict) or set(config) != set(expected) | {"output"}:
        raise ValueError("RTS-GMLC AC lookup amendment schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"RTS-GMLC AC lookup amendment {key} drifted")
    if not isinstance(config["output"], dict) or set(config["output"]) != {"directory"}:
        raise ValueError("RTS-GMLC AC lookup amendment output drifted")
    return config


def _amended_context(parent_config_path: Path):
    context = _build_context(parent_config_path)
    business_points = context.scan_context.business.points
    grid_points = context.scan_context.data.hourly_points[: len(business_points)]
    business_timestamps = tuple(point.timestamp for point in business_points)
    grid_timestamps = tuple(
        point.timestamp.replace(tzinfo=business_timestamps[index].tzinfo)
        for index, point in enumerate(grid_points)
    )
    if grid_timestamps != business_timestamps:
        raise RuntimeError("RTS-GMLC AC amended grid/business clocks do not align")
    amended_business = replace(context.scan_context.business, points=grid_points)
    amended_scan = replace(context.scan_context, business=amended_business)
    return replace(context, scan_context=amended_scan)


def _amendment_payload(
    amendment_path: Path,
    parent_config_path: Path,
) -> dict[str, Any]:
    context = _build_context(parent_config_path)
    registration = _require_preregistration(context)
    if (
        registration["input_contract_sha256"]
        != _AMENDMENT["parent_input_contract_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC lookup amendment parent inputs drifted")
    if (
        context.input_contract["implementation_sha256"][
            "experiments/run_rts_gmlc_multi_poi_ac_replay.py"
        ]
        != _AMENDMENT["parent_runner_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC lookup amendment parent runner drifted")
    if (
        context.input_contract["implementation_sha256"]["src/grid/rts_gmlc_ac.py"]
        != _AMENDMENT["parent_ac_module_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC lookup amendment AC module drifted")
    return {
        "schema": _AMENDMENT["schema"],
        "amendment_id": _AMENDMENT["id"],
        "status": _AMENDMENT["status"],
        "externally_timestamped": False,
        "amendment_config_sha256": _sha256(amendment_path),
        "amendment_implementation_sha256": _sha256(Path(__file__)),
        "parent_input_contract_sha256": registration["input_contract_sha256"],
        "parent_preregistration_manifest_sha256": _sha256(
            context.output_root / "preregistration" / "SHA256SUMS"
        ),
        "observed_before_amendment": _OBSERVED,
        "scope": _SCOPE,
    }


def prepare_amendment(
    amendment_path: Path,
    *,
    parent_config_path: Path,
) -> dict[str, Any]:
    config = _read_config(amendment_path)
    context = _build_context(parent_config_path)
    if Path(config["output"]["directory"]) != context.output_root:
        raise RuntimeError("RTS-GMLC AC lookup amendment output root drifted")
    if (context.output_root / "results").exists():
        raise RuntimeError("Cannot prepare lookup amendment after AC batch results")
    payload = _amendment_payload(amendment_path, parent_config_path)
    target = context.output_root / "amendments" / "001_grid_point_lookup"
    if target.exists():
        observed = _load_json(target, "amendment.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC AC lookup amendment drifted")
        return observed

    def writer(staging: Path) -> None:
        (staging / "amendment_config.yaml").write_bytes(amendment_path.read_bytes())
        _write_json(staging / "amendment.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "amendment.json")


def _require_amendment(
    amendment_path: Path,
    parent_config_path: Path,
) -> tuple[Any, dict[str, Any]]:
    context = _build_context(parent_config_path)
    target = context.output_root / "amendments" / "001_grid_point_lookup"
    _verify_output_manifest(target)
    observed = json.loads((target / "amendment.json").read_text(encoding="utf-8"))
    expected = _stable_json(_amendment_payload(amendment_path, parent_config_path))
    if observed != expected:
        raise RuntimeError("RTS-GMLC AC lookup amendment no longer matches parent")
    if (target / "amendment_config.yaml").read_bytes() != amendment_path.read_bytes():
        raise RuntimeError("RTS-GMLC AC lookup amendment config snapshot drifted")
    return context, observed


def run(
    amendment_path: Path,
    *,
    parent_config_path: Path,
) -> dict[str, Any]:
    context, amendment = _require_amendment(amendment_path, parent_config_path)
    target = context.output_root / "results"
    if target.exists():
        summary = _load_json(target, "summary.json")
        if (
            summary["amendment_implementation_sha256"]
            != amendment["amendment_implementation_sha256"]
        ):
            raise RuntimeError("Published amended AC results drifted")
        return summary
    rows = _evaluate_cases(_amended_context(parent_config_path))
    grouped = _group_summaries(rows)
    summary = {
        "schema": "rts_gmlc_multi_poi_ac_replay_results_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "implementation_amendment_id": _AMENDMENT["id"],
        "amendment_implementation_sha256": amendment["amendment_implementation_sha256"],
        "case_count": len(rows),
        "expected_case_count": 2304,
        "all_cases_reported": len(rows) == 2304,
        "converged_case_count": sum(bool(row["converged"]) for row in rows),
        "secure_case_count": sum(bool(row["secure"]) for row in rows),
        "candidate_power_factor_summaries": grouped,
        "maximum_dc_flow_reconstruction_residual_mw": max(
            float(row["dc_flow_reconstruction_residual_mw"]) for row in rows
        ),
        "direct_ac_replay_only": True,
        "q_limit_switching_used": False,
        "restoration_or_redispatch_used": False,
        "all_ac_cases_blind": False,
        "observed_probe_cases_before_freeze": _PREREGISTRATION[
            "observed_probe_cases_before_freeze"
        ],
        **_EVIDENCE,
    }

    def writer(staging: Path) -> None:
        _write_csv(staging / "ac_replay_cases.csv", _CASE_FIELDS, rows)
        _write_csv(
            staging / "candidate_power_factor_summary.csv",
            _SUMMARY_FIELDS,
            grouped,
        )
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--amendment-config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay_amendment.yaml"),
    )
    parser.add_argument(
        "--parent-config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("prepare-amendment", "run"),
        required=True,
    )
    args = parser.parse_args()
    result = (
        prepare_amendment(
            args.amendment_config,
            parent_config_path=args.parent_config,
        )
        if args.stage == "prepare-amendment"
        else run(
            args.amendment_config,
            parent_config_path=args.parent_config,
        )
    )
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
