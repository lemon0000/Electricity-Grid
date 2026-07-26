"""Apply an unambiguous PYPOWER slack-bus amendment to the AC replay."""

from __future__ import annotations

import argparse
import csv
import json
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pypower.api import ppoption, runpf
from pypower.idx_bus import BUS_I, BUS_TYPE, PQ, PV, REF
from pypower.idx_gen import (
    GEN_BUS,
    GEN_STATUS,
    PG,
    PMAX,
    PMIN,
    QMAX,
    QMIN,
)

import experiments.run_rts_gmlc_multi_poi_ac_replay as _parent_runner
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
    _group_summaries,
    _load_candidate_dispatch,
    _load_json,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_timezone_amended import (
    _AMENDMENT as _PARENT_AMENDMENT,
    _amended_context,
    _require_amendment as _require_parent_amendment,
)
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.grid.rts_gmlc_ac import (
    configure_rts_gmlc_ac_case as _configure_parent_case,
    reconstruct_rts_gmlc_dc_flows,
)

_PARENT_AMENDMENT_CONFIG = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_timezone_amendment.yaml"
)
_AMENDMENT = {
    "id": "rts_gmlc_ac_replay_unambiguous_slack_amendment_003",
    "schema": "rts_gmlc_ac_replay_implementation_amendment_v1",
    "parent_preregistration_id": "rts_gmlc_google_day0_multi_poi_ac_replay_v1",
    "parent_input_contract_sha256": (
        "7dc28350aaa137a3f99a90a83365ebafb58c8de739a2999a5a93ed4ea0babd41"
    ),
    "parent_amendment_id": "rts_gmlc_ac_replay_grid_point_timezone_amendment_002",
    "parent_amendment_implementation_sha256": (
        "4435727b3250af380b1ec4f20f0e6ba700902d6e6199da971c5758a9fced157a"
    ),
    "parent_batch_manifest_sha256": (
        "51ba90b32ca7702d92b49fa70832a56160b41ad9ee286990d2d937142ee9e05e"
    ),
    "status": "repository_local_amendment_after_full_batch_slack_audit_failure",
    "externally_timestamped": False,
}
_DEMONSTRATED_CASE = {
    "dc_bus": 108,
    "power_factor_case": "lagging_095",
    "timestamp": "2020-01-01T18:00:00+00:00",
    "state_id": "branch_CA-1_immediate",
    "reported_reference_generator_uid": "213_CC_3",
    "actual_slack_generator_uid": "213_RTPV_1",
    "actual_slack_adjustment_mw": 236.37316929152658,
}
_OBSERVED = {
    "full_parent_batch_outcomes_observed": True,
    "parent_case_count": 2304,
    "failure_detail": (
        "pypower_internal_generator_sort_selected_colocated_zero_pmax_rtpv_as_"
        "actual_slack"
    ),
    "demonstrated_case": _DEMONSTRATED_CASE,
    "parent_batch_status": (
        "invalidated_for_final_ac_conclusions_retained_as_diagnostic"
    ),
}
_SCOPE = {
    "permitted_change": (
        "select_reference_bus_with_exactly_one_online_generator_and_that_"
        "generator_committable"
    ),
    "reference_ordering": (
        "maximum_up_headroom_then_down_headroom_then_q_range_then_lowest_bus_uid"
    ),
    "forbidden_changes": [
        "parent_config",
        "representative_candidates",
        "hours_or_security_states",
        "power_factor_cases",
        "source_or_parent_dispatch_artifacts",
        "grid_point_values",
        "load_or_hvdc_mapping",
        "voltage_q_or_rating_assumptions",
        "power_flow_options",
        "q_limit_switching",
        "restoration_or_redispatch",
        "result_acceptance_or_summary_rules",
    ],
}
_NON_SLACK_PG_AUDIT_TOLERANCE_MW = 1.0e-6


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "amendment": _AMENDMENT,
        "observed_before_amendment": _OBSERVED,
        "scope": _SCOPE,
    }
    if not isinstance(config, dict) or set(config) != set(expected) | {"output"}:
        raise ValueError("RTS-GMLC AC slack amendment schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"RTS-GMLC AC slack amendment {key} drifted")
    output = config["output"]
    if not isinstance(output, dict) or set(output) != {
        "directory",
        "corrected_results_subdirectory",
    }:
        raise ValueError("RTS-GMLC AC slack amendment output drifted")
    return config


def _configure_unambiguous_slack(
    template: Any,
    data: Any,
    *args: Any,
    **kwargs: Any,
):
    configured = _configure_parent_case(template, data, *args, **kwargs)
    case = configured.case
    bus = case["bus"]
    generator = case["gen"]
    tolerance = float(kwargs.get("tolerance", 1.0e-6))
    committable = {
        item.uid for item in data.generators if item.dispatch_mode == "committable"
    }
    online_rows_by_bus: dict[int, list[int]] = {}
    for row in range(len(generator)):
        if generator[row, GEN_STATUS] <= 0.0:
            continue
        online_rows_by_bus.setdefault(int(generator[row, GEN_BUS]), []).append(row)
    eligible = []
    for bus_uid, rows in online_rows_by_bus.items():
        if len(rows) != 1:
            continue
        row = rows[0]
        uid = template.generator_uid_by_row[row]
        if uid not in committable or generator[row, PMAX] <= tolerance:
            continue
        eligible.append((bus_uid, row, uid))
    if not eligible:
        raise RuntimeError("RTS-GMLC AC case has no unambiguous committable slack bus")

    reference_bus, reference_row, reference_uid = max(
        eligible,
        key=lambda item: (
            float(generator[item[1], PMAX] - generator[item[1], PG]),
            float(generator[item[1], PG] - generator[item[1], PMIN]),
            float(generator[item[1], QMAX] - generator[item[1], QMIN]),
            -item[0],
        ),
    )
    active_q_buses = {
        int(generator[row, GEN_BUS])
        for row in range(len(generator))
        if generator[row, GEN_STATUS] > 0.0
        and generator[row, QMAX] - generator[row, QMIN] > tolerance
    }
    for row in range(len(bus)):
        bus_uid = int(bus[row, BUS_I])
        bus[row, BUS_TYPE] = PV if bus_uid in active_q_buses else PQ
    bus[template.bus_row_by_uid[reference_bus], BUS_TYPE] = REF
    return replace(
        configured,
        reference_bus=reference_bus,
        reference_generator_uid=reference_uid,
    )


def _reproduce_parent_slack_failure(parent_config_path: Path) -> dict[str, object]:
    context = _amended_context(parent_config_path)
    dc_bus = int(_DEMONSTRATED_CASE["dc_bus"])
    timestamp = str(_DEMONSTRATED_CASE["timestamp"])
    state_id = str(_DEMONSTRATED_CASE["state_id"])
    dispatch = _load_candidate_dispatch(context, dc_bus)
    matching_points = [
        point
        for point in context.scan_context.business.points
        if point.timestamp.isoformat() == timestamp
    ]
    if len(matching_points) != 1:
        raise RuntimeError("RTS-GMLC AC demonstrated grid point drifted")
    point = matching_points[0]
    metadata = dispatch.state_metadata[(timestamp, state_id)]
    if metadata["kind"] != "branch" or not metadata["element_uid"]:
        raise RuntimeError("RTS-GMLC AC demonstrated outage metadata drifted")
    generation = dispatch.security_generation[(timestamp, state_id)]
    branch_flows = dispatch.security_branch_flows[(timestamp, state_id)]
    data_center_power = float(
        dispatch.hourly_by_timestamp[timestamp]["data_center_power_mw"]
    )
    total_demand = dict(point.demand_by_bus_mw)
    total_demand[dc_bus] += data_center_power
    dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
        context.scan_context.data,
        demand_by_bus_mw=total_demand,
        generation_mw=generation,
        ac_branch_flows_mw=branch_flows,
        tolerance_mw=1.0e-6,
    )
    if residual > 1.0e-6:
        raise RuntimeError("RTS-GMLC AC demonstrated DC reconstruction drifted")
    configured = _configure_parent_case(
        context.template,
        context.scan_context.data,
        point,
        generation_mw=generation,
        commitment=dispatch.commitment_by_timestamp[timestamp],
        dc_bus=dc_bus,
        data_center_power_mw=data_center_power,
        data_center_power_factor=0.95,
        dc_flows_mw=dc_flows,
        outaged_branch_uid=metadata["element_uid"],
    )
    solved, success = runpf(
        configured.case,
        ppoption(
            VERBOSE=0,
            OUT_ALL=0,
            PF_ALG=1,
            PF_TOL=1.0e-8,
            PF_MAX_IT=20,
            ENFORCE_Q_LIMS=0,
        ),
    )
    if not success:
        raise RuntimeError(
            "RTS-GMLC AC demonstrated parent failure no longer converges"
        )
    target = np.asarray(configured.target_generation_mw_by_row)
    deviations = np.abs(solved["gen"][:, PG] - target)
    actual_row = int(np.argmax(deviations))
    return {
        "reported_reference_generator_uid": configured.reference_generator_uid,
        "actual_slack_generator_uid": context.template.generator_uid_by_row[actual_row],
        "actual_slack_adjustment_mw": float(solved["gen"][actual_row, PG])
        - float(target[actual_row]),
        "maximum_pg_deviation_mw": float(deviations[actual_row]),
    }


def _verify_parent_failure(context: Any, parent_config_path: Path) -> None:
    parent_results = context.output_root / "results"
    _verify_output_manifest(parent_results)
    if (
        _sha256(parent_results / "SHA256SUMS")
        != _AMENDMENT["parent_batch_manifest_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC slack amendment parent batch drifted")
    with (parent_results / "ac_replay_cases.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        matches = [
            row
            for row in csv.DictReader(source)
            if int(row["dc_bus"]) == _DEMONSTRATED_CASE["dc_bus"]
            and row["power_factor_case"] == _DEMONSTRATED_CASE["power_factor_case"]
            and row["timestamp"] == _DEMONSTRATED_CASE["timestamp"]
            and row["state_id"] == _DEMONSTRATED_CASE["state_id"]
        ]
    if len(matches) != 1:
        raise RuntimeError("RTS-GMLC AC demonstrated slack case drifted")
    row = matches[0]
    if (
        row["reference_generator_uid"]
        != _DEMONSTRATED_CASE["reported_reference_generator_uid"]
    ):
        raise RuntimeError("RTS-GMLC AC reported slack identity drifted")
    if (
        abs(
            float(row["max_non_slack_pg_deviation_mw"])
            - _DEMONSTRATED_CASE["actual_slack_adjustment_mw"]
        )
        > 1.0e-6
    ):
        raise RuntimeError("RTS-GMLC AC demonstrated slack adjustment drifted")
    reproduced = _reproduce_parent_slack_failure(parent_config_path)
    for field in (
        "reported_reference_generator_uid",
        "actual_slack_generator_uid",
    ):
        if reproduced[field] != _DEMONSTRATED_CASE[field]:
            raise RuntimeError(f"RTS-GMLC AC demonstrated {field} drifted")
    for field in ("actual_slack_adjustment_mw", "maximum_pg_deviation_mw"):
        if (
            abs(
                float(reproduced[field])
                - float(_DEMONSTRATED_CASE["actual_slack_adjustment_mw"])
            )
            > 1.0e-6
        ):
            raise RuntimeError(f"RTS-GMLC AC demonstrated {field} drifted")


def _amendment_payload(
    amendment_path: Path,
    parent_config_path: Path,
) -> dict[str, Any]:
    context, parent = _require_parent_amendment(
        _PARENT_AMENDMENT_CONFIG,
        parent_config_path,
    )
    if context.input_contract_sha256 != _AMENDMENT["parent_input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC AC slack amendment parent inputs drifted")
    if parent["amendment_id"] != _AMENDMENT["parent_amendment_id"]:
        raise RuntimeError("RTS-GMLC AC slack amendment parent ID drifted")
    if (
        parent["amendment_implementation_sha256"]
        != _AMENDMENT["parent_amendment_implementation_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC slack amendment parent code drifted")
    _verify_parent_failure(context, parent_config_path)
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
            context.output_root
            / "amendments"
            / "002_grid_point_timezone"
            / "SHA256SUMS"
        ),
        "parent_batch_manifest_sha256": _sha256(
            context.output_root / "results" / "SHA256SUMS"
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
        raise RuntimeError("RTS-GMLC AC slack amendment output root drifted")
    corrected = context.output_root / config["output"]["corrected_results_subdirectory"]
    if corrected.exists():
        raise RuntimeError("Cannot prepare slack amendment after corrected results")
    payload = _amendment_payload(amendment_path, parent_config_path)
    target = context.output_root / "amendments" / "003_unambiguous_slack"
    if target.exists():
        observed = _load_json(target, "amendment.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC AC slack amendment drifted")
        return observed

    def writer(staging: Path) -> None:
        (staging / "amendment_config.yaml").write_bytes(amendment_path.read_bytes())
        _write_json(staging / "amendment.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "amendment.json")


def _require_amendment(
    amendment_path: Path,
    parent_config_path: Path,
) -> tuple[Any, dict[str, Any], dict[str, Any]]:
    config = _read_config(amendment_path)
    context = _build_context(parent_config_path)
    target = context.output_root / "amendments" / "003_unambiguous_slack"
    _verify_output_manifest(target)
    observed = json.loads((target / "amendment.json").read_text(encoding="utf-8"))
    expected = _stable_json(_amendment_payload(amendment_path, parent_config_path))
    if observed != expected:
        raise RuntimeError("RTS-GMLC AC slack amendment no longer matches parent")
    if (target / "amendment_config.yaml").read_bytes() != amendment_path.read_bytes():
        raise RuntimeError("RTS-GMLC AC slack amendment config snapshot drifted")
    return context, observed, config


def run(
    amendment_path: Path,
    *,
    parent_config_path: Path,
) -> dict[str, Any]:
    context, amendment, config = _require_amendment(
        amendment_path,
        parent_config_path,
    )
    target = context.output_root / config["output"]["corrected_results_subdirectory"]
    if target.exists():
        summary = _load_json(target, "summary.json")
        if (
            summary["amendment_implementation_sha256"]
            != amendment["amendment_implementation_sha256"]
        ):
            raise RuntimeError("Published slack-amended AC results drifted")
        return summary

    original = _parent_runner.configure_rts_gmlc_ac_case
    _parent_runner.configure_rts_gmlc_ac_case = _configure_unambiguous_slack
    try:
        rows = _parent_runner._evaluate_cases(_amended_context(parent_config_path))
    finally:
        _parent_runner.configure_rts_gmlc_ac_case = original
    converged_rows = [row for row in rows if bool(row["converged"])]
    non_slack_drift = [
        row
        for row in converged_rows
        if row["max_non_slack_pg_deviation_mw"] is None
        or float(row["max_non_slack_pg_deviation_mw"])
        > _NON_SLACK_PG_AUDIT_TOLERANCE_MW
    ]
    if non_slack_drift:
        raise RuntimeError("RTS-GMLC AC corrected batch retained non-slack PG drift")
    grouped = _group_summaries(rows)
    summary = {
        "schema": "rts_gmlc_multi_poi_ac_replay_results_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "implementation_amendment_ids": [
            "rts_gmlc_ac_replay_grid_point_lookup_amendment_001",
            _PARENT_AMENDMENT["id"],
            _AMENDMENT["id"],
        ],
        "amendment_implementation_sha256": amendment["amendment_implementation_sha256"],
        "invalidated_parent_batch_manifest_sha256": amendment[
            "parent_batch_manifest_sha256"
        ],
        "case_count": len(rows),
        "expected_case_count": 2304,
        "all_cases_reported": len(rows) == 2304,
        "converged_case_count": sum(bool(row["converged"]) for row in rows),
        "secure_case_count": sum(bool(row["secure"]) for row in rows),
        "candidate_power_factor_summaries": grouped,
        "maximum_dc_flow_reconstruction_residual_mw": max(
            float(row["dc_flow_reconstruction_residual_mw"]) for row in rows
        ),
        "maximum_non_slack_pg_deviation_mw": max(
            (float(row["max_non_slack_pg_deviation_mw"]) for row in converged_rows),
            default=None,
        ),
        "non_slack_pg_audit_tolerance_mw": _NON_SLACK_PG_AUDIT_TOLERANCE_MW,
        "all_converged_cases_pass_non_slack_pg_audit": True,
        "unambiguous_single_online_committable_slack_bus_required": True,
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
            "configs/rts_gmlc_google_day0_multi_poi_ac_replay_slack_amendment.yaml"
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
