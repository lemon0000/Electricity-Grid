"""Apply the frozen timezone-key amendment to the RTS-GMLC AC replay."""

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
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_amended import (
    _AMENDMENT as _PARENT_AMENDMENT,
    _amended_context as _parent_amended_context,
    _require_amendment as _require_parent_amendment,
)
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json

_PARENT_AMENDMENT_CONFIG = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_amendment.yaml"
)
_AMENDMENT = {
    "id": "rts_gmlc_ac_replay_grid_point_timezone_amendment_002",
    "schema": "rts_gmlc_ac_replay_implementation_amendment_v1",
    "parent_preregistration_id": "rts_gmlc_google_day0_multi_poi_ac_replay_v1",
    "parent_input_contract_sha256": (
        "7dc28350aaa137a3f99a90a83365ebafb58c8de739a2999a5a93ed4ea0babd41"
    ),
    "parent_amendment_id": "rts_gmlc_ac_replay_grid_point_lookup_amendment_001",
    "parent_amendment_implementation_sha256": (
        "bf628231bb1b32b8b8d2b7ddcc631ebca1d4c7d41b7a647444e542276a0dcb4b"
    ),
    "status": "repository_local_amendment_after_pre_batch_timezone_key_failure",
    "externally_timestamped": False,
}
_OBSERVED = {
    "batch_ac_case_outcomes_observed": False,
    "failure_type": "KeyError",
    "failure_detail": (
        "naive_grid_timestamp_did_not_match_aware_parent_artifact_timestamp"
    ),
    "failure_stage": "before_first_ac_case_configuration_or_power_flow",
}
_SCOPE = {
    "permitted_change": (
        "replace_mapped_grid_point_timestamp_with_same_instant_parent_business_"
        "timestamp"
    ),
    "forbidden_changes": [
        "parent_config",
        "representative_candidates",
        "hours_or_security_states",
        "power_factor_cases",
        "source_or_parent_artifacts",
        "grid_point_numerical_fields",
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
        raise ValueError("RTS-GMLC AC timezone amendment schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"RTS-GMLC AC timezone amendment {key} drifted")
    if not isinstance(config["output"], dict) or set(config["output"]) != {"directory"}:
        raise ValueError("RTS-GMLC AC timezone amendment output drifted")
    return config


def _amended_context(parent_config_path: Path):
    base_context = _build_context(parent_config_path)
    parent_context = _parent_amended_context(parent_config_path)
    business_timestamps = tuple(
        point.timestamp for point in base_context.scan_context.business.points
    )
    grid_points = parent_context.scan_context.business.points
    if len(grid_points) != len(business_timestamps):
        raise RuntimeError("RTS-GMLC AC timezone amendment horizon drifted")
    normalized_points = tuple(
        replace(point, timestamp=business_timestamps[index])
        for index, point in enumerate(grid_points)
    )
    if any(
        normalized.timestamp.replace(tzinfo=None) != original.timestamp
        for normalized, original in zip(
            normalized_points,
            base_context.scan_context.data.hourly_points,
        )
    ):
        raise RuntimeError("RTS-GMLC AC timezone amendment changed an instant")
    amended_business = replace(
        parent_context.scan_context.business,
        points=normalized_points,
    )
    amended_scan = replace(
        parent_context.scan_context,
        business=amended_business,
    )
    return replace(parent_context, scan_context=amended_scan)


def _amendment_payload(
    amendment_path: Path,
    parent_config_path: Path,
) -> dict[str, Any]:
    context, parent = _require_parent_amendment(
        _PARENT_AMENDMENT_CONFIG,
        parent_config_path,
    )
    if context.input_contract_sha256 != _AMENDMENT["parent_input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC AC timezone amendment parent inputs drifted")
    if parent["amendment_id"] != _AMENDMENT["parent_amendment_id"]:
        raise RuntimeError("RTS-GMLC AC timezone amendment parent ID drifted")
    if (
        parent["amendment_implementation_sha256"]
        != _AMENDMENT["parent_amendment_implementation_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC timezone amendment parent code drifted")
    return {
        "schema": _AMENDMENT["schema"],
        "amendment_id": _AMENDMENT["id"],
        "status": _AMENDMENT["status"],
        "externally_timestamped": False,
        "amendment_config_sha256": _sha256(amendment_path),
        "amendment_implementation_sha256": _sha256(Path(__file__)),
        "parent_input_contract_sha256": context.input_contract_sha256,
        "parent_amendment_id": parent["amendment_id"],
        "parent_amendment_implementation_sha256": parent[
            "amendment_implementation_sha256"
        ],
        "parent_amendment_manifest_sha256": _sha256(
            context.output_root / "amendments" / "001_grid_point_lookup" / "SHA256SUMS"
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
        raise RuntimeError("RTS-GMLC AC timezone amendment output root drifted")
    if (context.output_root / "results").exists():
        raise RuntimeError("Cannot prepare timezone amendment after AC batch results")
    payload = _amendment_payload(amendment_path, parent_config_path)
    target = context.output_root / "amendments" / "002_grid_point_timezone"
    if target.exists():
        observed = _load_json(target, "amendment.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC AC timezone amendment drifted")
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
    target = context.output_root / "amendments" / "002_grid_point_timezone"
    _verify_output_manifest(target)
    observed = json.loads((target / "amendment.json").read_text(encoding="utf-8"))
    expected = _stable_json(_amendment_payload(amendment_path, parent_config_path))
    if observed != expected:
        raise RuntimeError("RTS-GMLC AC timezone amendment no longer matches parent")
    if (target / "amendment_config.yaml").read_bytes() != amendment_path.read_bytes():
        raise RuntimeError("RTS-GMLC AC timezone amendment config snapshot drifted")
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
            raise RuntimeError("Published timezone-amended AC results drifted")
        return summary
    rows = _evaluate_cases(_amended_context(parent_config_path))
    grouped = _group_summaries(rows)
    summary = {
        "schema": "rts_gmlc_multi_poi_ac_replay_results_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "implementation_amendment_ids": [
            _PARENT_AMENDMENT["id"],
            _AMENDMENT["id"],
        ],
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
        default=Path(
            "configs/rts_gmlc_google_day0_multi_poi_ac_replay_timezone_amendment.yaml"
        ),
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
