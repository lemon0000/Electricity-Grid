"""Apply the q-capable voltage-control amendment to the RTS-GMLC AC replay."""

from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pypower.api import ppoption, runpf
from pypower.idx_bus import BUS_I, BUS_TYPE, PV, REF, VM
from pypower.idx_gen import GEN_BUS, GEN_STATUS, QG, QMAX, QMIN, VG

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
from experiments.run_rts_gmlc_multi_poi_ac_replay_slack_amended import (
    _AMENDMENT as _PARENT_AMENDMENT,
    _configure_unambiguous_slack,
    _require_amendment as _require_parent_amendment,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_timezone_amended import (
    _amended_context,
)
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.grid.rts_gmlc_ac import (
    reconstruct_rts_gmlc_dc_flows,
    validate_rts_gmlc_ac_power_flow,
)

_PARENT_AMENDMENT_CONFIG = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_slack_amendment.yaml"
)
_PARENT_RESULTS_SUBDIRECTORY = "results_unambiguous_slack"
_AMENDMENT_DIRECTORY = "004_q_capable_voltage_control"
_AMENDMENT = {
    "id": "rts_gmlc_ac_replay_q_capable_voltage_control_amendment_004",
    "schema": "rts_gmlc_ac_replay_implementation_amendment_v1",
    "parent_preregistration_id": "rts_gmlc_google_day0_multi_poi_ac_replay_v1",
    "parent_input_contract_sha256": (
        "7dc28350aaa137a3f99a90a83365ebafb58c8de739a2999a5a93ed4ea0babd41"
    ),
    "parent_amendment_id": ("rts_gmlc_ac_replay_unambiguous_slack_amendment_003"),
    "parent_amendment_config_sha256": (
        "ee0436c39530791ac055fedd5ec91624ba3926985c6f39b251d28f1ee504f2f1"
    ),
    "parent_amendment_implementation_sha256": (
        "6a9f2050a7882ef4c7fae72daefbc018d966ad46977bed22748383f15fe26ac0"
    ),
    "parent_amendment_manifest_sha256": (
        "3aa5c70b94f5771ba1822425b58eff4704ee1f93a7bb310146de7df8f79bfb87"
    ),
    "parent_corrected_batch_manifest_sha256": (
        "2b5b705d2074ddb8f846b7a8d897ed87d32021446fd867825b7dd3a0982e2a7e"
    ),
    "status": (
        "repository_local_amendment_after_corrected_batch_"
        "voltage_control_audit_failure"
    ),
    "externally_timestamped": False,
}
_DEMONSTRATED_CASE = {
    "dc_bus": 120,
    "power_factor_case": "unity",
    "timestamp": "2020-01-01T00:00:00+00:00",
    "state_id": "normal",
    "control_bus": 314,
    "controller_generator_uid": "314_SYNC_COND_1",
    "controller_source_vg_pu": 1.05,
    "q_inert_source_vg_pu": 1.0,
    "parent_solved_control_bus_voltage_pu": 1.0,
    "parent_controller_q_mvar": -102.20498757079912,
    "parent_controller_q_limit_violation_mvar": 52.20498757079912,
    "amended_probe_solved_control_bus_voltage_pu": 1.05,
    "amended_probe_controller_q_mvar": 9.163432253344993,
    "amended_probe_max_reactive_power_violation_mvar": 26.49335061366679,
    "amended_probe_max_reactive_power_violation_generator_uid": "116_STEAM_1",
    "amended_probe_max_voltage_violation_pu": 0.05714149350909459,
    "amended_probe_secure": False,
}
_OBSERVED = {
    "full_parent_batch_outcomes_observed": True,
    "parent_case_count": 2304,
    "failure_detail": (
        "pypower_duplicate_bus_voltage_initialization_allowed_online_q_inert_"
        "generator_vg_to_override_source_q_controller_vg"
    ),
    "voltage_control_corrected_probe_outcomes_observed_before_freeze": True,
    "full_voltage_control_corrected_batch_outcomes_observed": False,
    "demonstrated_case": _DEMONSTRATED_CASE,
    "parent_batch_status": (
        "invalidated_for_final_ac_outcome_conclusions_retained_as_diagnostic"
    ),
}
_SCOPE = {
    "permitted_change": (
        "copy_unique_online_q_capable_source_vg_to_colocated_online_q_inert_"
        "rows_at_pv_or_ref_buses"
    ),
    "controller_rule": "online_generator_with_qmax_minus_qmin_above_tolerance",
    "conflict_policy": (
        "fail_if_no_online_q_capable_controller_or_nonunique_controller_vg"
    ),
    "source_evidence_rule": (
        "generator_vg_is_the_pv_or_ref_control_target_and_bus_vm_remains_the_"
        "newton_initial_value"
    ),
    "forbidden_changes": [
        "parent_config",
        "representative_candidates",
        "hours_or_security_states",
        "power_factor_cases",
        "source_or_parent_dispatch_artifacts",
        "grid_point_values",
        "load_or_hvdc_mapping",
        "generator_active_power_or_commitment",
        "generator_q_limits",
        "q_capable_controller_source_vg",
        "bus_vm_or_va_initial_values",
        "bus_type_or_slack_selection",
        "branch_shunt_tap_status_or_rating_inputs",
        "power_flow_options",
        "q_limit_switching",
        "restoration_or_redispatch",
        "result_acceptance_or_summary_rules",
    ],
}
_NON_SLACK_PG_AUDIT_TOLERANCE_MW = 1.0e-6
_CONTROLLER_TOLERANCE = 1.0e-6
_CASE_KEY_FIELDS = ("dc_bus", "power_factor_case", "timestamp", "state_id")


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "amendment": _AMENDMENT,
        "observed_before_amendment": _OBSERVED,
        "scope": _SCOPE,
    }
    if not isinstance(config, dict) or set(config) != set(expected) | {"output"}:
        raise ValueError("RTS-GMLC AC voltage-control amendment schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"RTS-GMLC AC voltage-control amendment {key} drifted")
    output = config["output"]
    if not isinstance(output, dict) or set(output) != {
        "directory",
        "corrected_results_subdirectory",
    }:
        raise ValueError("RTS-GMLC AC voltage-control amendment output drifted")
    return config


def _harmonize_online_q_controller_vg(configured: Any, *, tolerance: float):
    bus = configured.case["bus"]
    generator = configured.case["gen"]
    for bus_row in range(len(bus)):
        if int(bus[bus_row, BUS_TYPE]) not in (PV, REF):
            continue
        bus_uid = int(bus[bus_row, BUS_I])
        online_rows = [
            row
            for row in range(len(generator))
            if generator[row, GEN_STATUS] > 0.0
            and int(generator[row, GEN_BUS]) == bus_uid
        ]
        controller_rows = [
            row
            for row in online_rows
            if generator[row, QMAX] - generator[row, QMIN] > tolerance
        ]
        if not controller_rows:
            raise RuntimeError(
                f"RTS-GMLC AC controlled bus {bus_uid} has no online Q controller"
            )
        controller_vg = {float(generator[row, VG]) for row in controller_rows}
        if len(controller_vg) != 1 or not all(
            math.isfinite(value) for value in controller_vg
        ):
            raise RuntimeError(
                f"RTS-GMLC AC controlled bus {bus_uid} has ambiguous controller VG"
            )
        target_vg = next(iter(controller_vg))
        for row in online_rows:
            if generator[row, QMAX] - generator[row, QMIN] <= tolerance:
                generator[row, VG] = target_vg
        if any(float(generator[row, VG]) != target_vg for row in online_rows):
            raise RuntimeError(
                f"RTS-GMLC AC controlled bus {bus_uid} retained conflicting online VG"
            )
    return configured


def _configure_q_capable_voltage_control(
    template: Any,
    data: Any,
    *args: Any,
    **kwargs: Any,
):
    configured = _configure_unambiguous_slack(template, data, *args, **kwargs)
    tolerance = float(kwargs.get("tolerance", _CONTROLLER_TOLERANCE))
    return _harmonize_online_q_controller_vg(configured, tolerance=tolerance)


def _demonstrated_configurations(parent_config_path: Path):
    context = _amended_context(parent_config_path)
    dc_bus = int(_DEMONSTRATED_CASE["dc_bus"])
    timestamp = str(_DEMONSTRATED_CASE["timestamp"])
    dispatch = _load_candidate_dispatch(context, dc_bus)
    point = next(
        (
            item
            for item in context.scan_context.business.points
            if item.timestamp.isoformat() == timestamp
        ),
        None,
    )
    if point is None:
        raise RuntimeError("RTS-GMLC AC voltage-control probe grid point drifted")
    if _DEMONSTRATED_CASE["state_id"] != "normal":
        raise RuntimeError("RTS-GMLC AC voltage-control probe state drifted")
    generation = dispatch.normal_generation[timestamp]
    branch_flows = dispatch.normal_branch_flows[timestamp]
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
        tolerance_mw=_CONTROLLER_TOLERANCE,
    )
    if residual > _CONTROLLER_TOLERANCE:
        raise RuntimeError("RTS-GMLC AC voltage-control probe DC residual drifted")
    kwargs = {
        "generation_mw": generation,
        "commitment": dispatch.commitment_by_timestamp[timestamp],
        "dc_bus": dc_bus,
        "data_center_power_mw": data_center_power,
        "data_center_power_factor": 1.0,
        "dc_flows_mw": dc_flows,
    }
    parent = _configure_unambiguous_slack(
        context.template,
        context.scan_context.data,
        point,
        **kwargs,
    )
    amended = _configure_q_capable_voltage_control(
        context.template,
        context.scan_context.data,
        point,
        **kwargs,
    )
    return context, parent, amended


def _probe_outcome(context: Any, configured: Any) -> dict[str, object]:
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
        raise RuntimeError("RTS-GMLC AC voltage-control probe no longer converges")
    result = validate_rts_gmlc_ac_power_flow(
        context.template,
        configured,
        branch_rating="continuous",
    )
    if (
        result.max_non_slack_pg_deviation_mw is None
        or result.max_non_slack_pg_deviation_mw > _NON_SLACK_PG_AUDIT_TOLERANCE_MW
    ):
        raise RuntimeError("RTS-GMLC AC voltage-control probe changed non-slack PG")
    control_bus = int(_DEMONSTRATED_CASE["control_bus"])
    controller_uid = str(_DEMONSTRATED_CASE["controller_generator_uid"])
    bus_row = context.template.bus_row_by_uid[control_bus]
    generator_row = context.template.generator_row_by_uid[controller_uid]
    q_mvar = float(solved["gen"][generator_row, QG])
    q_min = float(configured.case["gen"][generator_row, QMIN])
    q_max = float(configured.case["gen"][generator_row, QMAX])
    return {
        "solved_control_bus_voltage_pu": float(solved["bus"][bus_row, VM]),
        "controller_q_mvar": q_mvar,
        "controller_q_limit_violation_mvar": max(q_min - q_mvar, q_mvar - q_max, 0.0),
        "max_reactive_power_violation_mvar": (result.max_reactive_power_violation_mvar),
        "max_reactive_power_violation_generator_uid": (
            result.max_reactive_power_violation_generator_uid
        ),
        "max_voltage_violation_pu": result.max_voltage_violation_pu,
        "secure": result.secure,
    }


def _reproduce_parent_voltage_control_failure(
    parent_config_path: Path,
) -> dict[str, object]:
    context, parent, amended = _demonstrated_configurations(parent_config_path)
    control_bus = int(_DEMONSTRATED_CASE["control_bus"])
    controller_uid = str(_DEMONSTRATED_CASE["controller_generator_uid"])
    controller_row = context.template.generator_row_by_uid[controller_uid]
    generator = parent.case["gen"]
    q_inert_vg = {
        float(generator[row, VG])
        for row in range(len(generator))
        if generator[row, GEN_STATUS] > 0.0
        and int(generator[row, GEN_BUS]) == control_bus
        and generator[row, QMAX] - generator[row, QMIN] <= _CONTROLLER_TOLERANCE
    }
    if len(q_inert_vg) != 1:
        raise RuntimeError("RTS-GMLC AC voltage-control probe Q-inert VG drifted")
    parent_outcome = _probe_outcome(context, parent)
    amended_outcome = _probe_outcome(context, amended)
    return {
        "dc_bus": _DEMONSTRATED_CASE["dc_bus"],
        "power_factor_case": _DEMONSTRATED_CASE["power_factor_case"],
        "timestamp": _DEMONSTRATED_CASE["timestamp"],
        "state_id": _DEMONSTRATED_CASE["state_id"],
        "control_bus": control_bus,
        "controller_generator_uid": controller_uid,
        "controller_source_vg_pu": float(generator[controller_row, VG]),
        "q_inert_source_vg_pu": next(iter(q_inert_vg)),
        "parent_solved_control_bus_voltage_pu": parent_outcome[
            "solved_control_bus_voltage_pu"
        ],
        "parent_controller_q_mvar": parent_outcome["controller_q_mvar"],
        "parent_controller_q_limit_violation_mvar": parent_outcome[
            "controller_q_limit_violation_mvar"
        ],
        "amended_probe_solved_control_bus_voltage_pu": amended_outcome[
            "solved_control_bus_voltage_pu"
        ],
        "amended_probe_controller_q_mvar": amended_outcome["controller_q_mvar"],
        "amended_probe_max_reactive_power_violation_mvar": amended_outcome[
            "max_reactive_power_violation_mvar"
        ],
        "amended_probe_max_reactive_power_violation_generator_uid": (
            amended_outcome["max_reactive_power_violation_generator_uid"]
        ),
        "amended_probe_max_voltage_violation_pu": amended_outcome[
            "max_voltage_violation_pu"
        ],
        "amended_probe_secure": amended_outcome["secure"],
    }


def _verify_demonstrated_failure(parent_config_path: Path) -> None:
    reproduced = _reproduce_parent_voltage_control_failure(parent_config_path)
    for field, expected in _DEMONSTRATED_CASE.items():
        observed = reproduced[field]
        if type(expected) is float:
            if abs(float(observed) - expected) > 1.0e-8:
                raise RuntimeError(f"RTS-GMLC AC voltage-control probe {field} drifted")
        elif observed != expected:
            raise RuntimeError(f"RTS-GMLC AC voltage-control probe {field} drifted")


def _amendment_payload(
    amendment_path: Path,
    parent_config_path: Path,
) -> dict[str, Any]:
    context, parent, _parent_config = _require_parent_amendment(
        _PARENT_AMENDMENT_CONFIG,
        parent_config_path,
    )
    if context.input_contract_sha256 != _AMENDMENT["parent_input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC AC voltage-control parent inputs drifted")
    if parent["amendment_id"] != _AMENDMENT["parent_amendment_id"]:
        raise RuntimeError("RTS-GMLC AC voltage-control parent amendment drifted")
    if (
        _sha256(_PARENT_AMENDMENT_CONFIG)
        != _AMENDMENT["parent_amendment_config_sha256"]
        or parent["amendment_implementation_sha256"]
        != _AMENDMENT["parent_amendment_implementation_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC voltage-control parent code drifted")
    parent_amendment_root = context.output_root / "amendments" / "003_unambiguous_slack"
    parent_results_root = context.output_root / _PARENT_RESULTS_SUBDIRECTORY
    for root, expected in (
        (
            parent_amendment_root,
            _AMENDMENT["parent_amendment_manifest_sha256"],
        ),
        (
            parent_results_root,
            _AMENDMENT["parent_corrected_batch_manifest_sha256"],
        ),
    ):
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != expected:
            raise RuntimeError(
                f"RTS-GMLC AC voltage-control parent artifact {root} drifted"
            )
    _verify_demonstrated_failure(parent_config_path)
    return {
        "schema": _AMENDMENT["schema"],
        "amendment_id": _AMENDMENT["id"],
        "status": _AMENDMENT["status"],
        "externally_timestamped": False,
        "amendment_config_sha256": _sha256(amendment_path),
        "amendment_implementation_sha256": _sha256(Path(__file__)),
        "parent_input_contract_sha256": context.input_contract_sha256,
        "parent_amendment_id": parent["amendment_id"],
        "parent_amendment_config_sha256": _sha256(_PARENT_AMENDMENT_CONFIG),
        "parent_amendment_implementation_sha256": parent[
            "amendment_implementation_sha256"
        ],
        "parent_amendment_manifest_sha256": _sha256(
            parent_amendment_root / "SHA256SUMS"
        ),
        "parent_corrected_batch_manifest_sha256": _sha256(
            parent_results_root / "SHA256SUMS"
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
        raise RuntimeError("RTS-GMLC AC voltage-control output root drifted")
    payload = _amendment_payload(amendment_path, parent_config_path)
    target = context.output_root / "amendments" / _AMENDMENT_DIRECTORY
    if target.exists():
        observed = _load_json(target, "amendment.json")
        if observed != _stable_json(payload):
            raise RuntimeError(
                "Published RTS-GMLC AC voltage-control amendment drifted"
            )
        if (
            target / "amendment_config.yaml"
        ).read_bytes() != amendment_path.read_bytes():
            raise RuntimeError("Published voltage-control amendment config drifted")
        return observed
    corrected = context.output_root / config["output"]["corrected_results_subdirectory"]
    if corrected.exists():
        raise RuntimeError(
            "Cannot prepare voltage-control amendment after corrected results"
        )

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
    if Path(config["output"]["directory"]) != context.output_root:
        raise RuntimeError("RTS-GMLC AC voltage-control output root drifted")
    target = context.output_root / "amendments" / _AMENDMENT_DIRECTORY
    _verify_output_manifest(target)
    observed = json.loads((target / "amendment.json").read_text(encoding="utf-8"))
    expected = _stable_json(_amendment_payload(amendment_path, parent_config_path))
    if observed != expected:
        raise RuntimeError(
            "RTS-GMLC AC voltage-control amendment no longer matches parent"
        )
    if (target / "amendment_config.yaml").read_bytes() != amendment_path.read_bytes():
        raise RuntimeError("RTS-GMLC AC voltage-control config snapshot drifted")
    return context, observed, config


def _require_finite_rows(rows: list[dict[str, object]]) -> None:
    for row_index, row in enumerate(rows):
        for field, value in row.items():
            if isinstance(value, (float, np.floating)) and not math.isfinite(
                float(value)
            ):
                raise RuntimeError(
                    f"RTS-GMLC AC voltage-control case {row_index} field {field} "
                    "is not finite"
                )


def _case_keys(rows: list[dict[str, object]]) -> set[tuple[str, ...]]:
    return {tuple(str(row[field]) for field in _CASE_KEY_FIELDS) for row in rows}


def _load_parent_case_keys(path: Path) -> set[tuple[str, ...]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    keys = _case_keys(rows)
    if len(rows) != 2304 or len(keys) != 2304:
        raise RuntimeError("RTS-GMLC AC voltage-control parent scope drifted")
    return keys


def _require_exact_case_scope(
    rows: list[dict[str, object]],
    *,
    expected_keys: set[tuple[str, ...]],
) -> None:
    observed_keys = _case_keys(rows)
    if (
        len(rows) != len(expected_keys)
        or len(observed_keys) != len(rows)
        or observed_keys != expected_keys
    ):
        raise RuntimeError("RTS-GMLC AC voltage-control batch scope drifted")


def _require_non_slack_pg_control(rows: list[dict[str, object]]) -> None:
    for row in rows:
        if not bool(row["converged"]):
            continue
        value = row["max_non_slack_pg_deviation_mw"]
        if (
            value is None
            or not math.isfinite(float(value))
            or float(value) > _NON_SLACK_PG_AUDIT_TOLERANCE_MW
        ):
            raise RuntimeError(
                "RTS-GMLC AC voltage-control batch retained non-slack PG drift"
            )


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
            raise RuntimeError("Published voltage-control AC results drifted")
        return summary

    original = _parent_runner.configure_rts_gmlc_ac_case
    _parent_runner.configure_rts_gmlc_ac_case = _configure_q_capable_voltage_control
    try:
        rows = _parent_runner._evaluate_cases(_amended_context(parent_config_path))
    finally:
        _parent_runner.configure_rts_gmlc_ac_case = original
    _require_finite_rows(rows)
    expected_keys = _load_parent_case_keys(
        context.output_root / _PARENT_RESULTS_SUBDIRECTORY / "ac_replay_cases.csv"
    )
    _require_exact_case_scope(rows, expected_keys=expected_keys)
    converged_rows = [row for row in rows if bool(row["converged"])]
    _require_non_slack_pg_control(rows)
    grouped = _group_summaries(rows)
    summary = {
        "schema": "rts_gmlc_multi_poi_ac_replay_results_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "implementation_amendment_ids": [
            "rts_gmlc_ac_replay_grid_point_lookup_amendment_001",
            "rts_gmlc_ac_replay_grid_point_timezone_amendment_002",
            _PARENT_AMENDMENT["id"],
            _AMENDMENT["id"],
        ],
        "amendment_implementation_sha256": amendment["amendment_implementation_sha256"],
        "invalidated_parent_batch_manifest_sha256": amendment[
            "parent_corrected_batch_manifest_sha256"
        ],
        "case_count": len(rows),
        "expected_case_count": 2304,
        "all_cases_reported": len(rows) == 2304,
        "converged_case_count": len(converged_rows),
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
        "q_capable_voltage_control_rule": _SCOPE["permitted_change"],
        "ambiguous_or_missing_controller_policy": _SCOPE["conflict_policy"],
        "voltage_control_corrected_probe_outcomes_observed_before_freeze": True,
        "full_voltage_control_corrected_batch_outcomes_observed_before_freeze": False,
        "all_other_voltage_control_corrected_cases_blind": True,
        "unambiguous_single_online_committable_slack_bus_required": True,
        "direct_ac_replay_only": True,
        "q_limit_switching_used": False,
        "restoration_or_redispatch_used": False,
        "all_ac_cases_blind": False,
        "observed_probe_cases_before_freeze": _PREREGISTRATION[
            "observed_probe_cases_before_freeze"
        ],
        "voltage_control_observed_probe": {
            key: _DEMONSTRATED_CASE[key]
            for key in ("dc_bus", "power_factor_case", "timestamp", "state_id")
        },
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
            "configs/rts_gmlc_google_day0_multi_poi_ac_replay_"
            "voltage_control_amendment.yaml"
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
