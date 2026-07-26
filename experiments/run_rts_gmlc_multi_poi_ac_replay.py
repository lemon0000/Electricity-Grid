"""Run the pre-registered direct AC replay for selected multi-POI outcomes."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import yaml

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import (
    _sha256,
    _stable_json,
    _write_csv,
)
from experiments.run_rts_gmlc_multi_poi_scan import (
    _build_scan_context,
    _publish_payload,
    _write_json,
)
from src.grid.rts_gmlc_ac import (
    RtsGmlcAcTemplate,
    configure_rts_gmlc_ac_case,
    load_rts_gmlc_ac_template,
    reconstruct_rts_gmlc_dc_flows,
    validate_rts_gmlc_ac_power_flow,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

_SCAN_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_scan.yaml")
_PREREGISTRATION = {
    "id": "rts_gmlc_google_day0_multi_poi_ac_replay_v1",
    "schema": "rts_gmlc_multi_poi_ac_replay_preregistration_v1",
    "status": "repository_local_frozen_before_full_ac_batch",
    "externally_timestamped": False,
    "all_ac_cases_blind": False,
    "observed_probe_cases_before_freeze": [
        {
            "dc_bus": 108,
            "hour_index": 0,
            "state_id": "normal",
            "power_factor_case": "unity",
        },
        {
            "dc_bus": 108,
            "hour_index": 0,
            "state_id": "normal",
            "power_factor_case": "lagging_095",
        },
    ],
}
_PARENT_SCAN = {
    "preregistration_contract_sha256": (
        "16d9edc57d965e802dd17106a3a0aa7a99ae93f0f493ba977d8490573ce3fb78"
    ),
    "common_security_contract_sha256": (
        "7865c7544817acd2d0dd6a461766862af52f7175eb24f2c1466f52e70115aa87"
    ),
    "aggregate_manifest_sha256": (
        "85f157a5f14f73ffa851c8dc1bc263f67719d794a900101b987dcab3f21dac66"
    ),
    "representative_bus_order": [120, 108],
    "representative_candidate_manifest_sha256": {
        120: "c5baf3ca95c44e4bbd5dd1de1372bc897d9da47c8fc7cb975d0d6ff00a5fb0dd",
        108: "3c686a142e5936a9a6f03dac9876f7d55907851c6336a5c31a63bd197037e194",
    },
}
_AC_SOURCE = {
    "upstream_path": "data/raw/rts_gmlc/v0.2.3/upstream",
    "upstream_manifest_sha256": (
        "95c1294626cdf00ee029659108bf1f30d4ec176a258192b784f097462226a914"
    ),
    "official_matpower_reference_path": (
        "data/raw/rts_gmlc/v0.2.3/ac_reference/RTS_GMLC.m"
    ),
    "official_matpower_reference_sha256": (
        "10573aee70f793c28a0602516f85c4345e6f171512852f1162c3bb3b02ba575b"
    ),
    "base_mva": 100.0,
}
_CASE_SCOPE = {
    "hours": "all_24",
    "security_states": "all_24_common_states",
    "expected_cases_per_candidate_power_factor": 576,
    "candidate_representatives": [120, 108],
    "power_factor_cases": [
        {"id": "unity", "value": 1.0, "direction": "lagging"},
        {"id": "lagging_095", "value": 0.95, "direction": "lagging"},
    ],
    "completion_policy": "all_2304_cases_reported_no_failure_deletion",
}
_AC_ASSUMPTIONS = {
    "native_reactive_demand": (
        "static_nodal_power_factor_scaled_with_hourly_active_demand"
    ),
    "data_center_reactive_demand": ("synthetic_power_factor_sensitivity_not_observed"),
    "voltage_limits_pu": [0.95, 1.05],
    "generator_q_limits_and_v_setpoints": "pinned_source_data",
    "generator_mbase_mva": "official_matpower_conversion_system_base_100",
    "synchronous_condensers": ("online_for_reactive_support_with_zero_active_power"),
    "csp_and_storage": "offline_matching_dc_active_power_scope",
    "fixed_bus_shunts": "pinned_source_data_not_scaled_with_hourly_load",
    "initial_voltage_magnitude_and_angle": (
        "pinned_source_snapshot_used_as_newton_start"
    ),
    "transformer_taps": "pinned_source_fixed_values",
    "branch_phase_shift_degrees": "zero_matching_official_conversion",
    "poi_connection_equipment": (
        "absent_direct_bus_injection_without_transformer_or_line"
    ),
    "hvdc": (
        "reconstruct_lossless_dc1_flow_from_saved_nodal_balances_as_fixed_"
        "endpoint_p_injections"
    ),
    "hvdc_converter_reactive_power": "zero_not_modeled",
    "branch_rate_a": "source_cont_rating_used_as_mva_proxy",
    "branch_rate_b": "source_lte_rating_used_as_mva_proxy",
    "branch_rate_c": "source_ste_rating_used_as_mva_proxy",
    "source_rating_unit_is_mw_not_engineering_mva": True,
    "q_limit_switching": False,
    "active_power_slack": (
        "first_online_real_generator_at_reference_bus_absorbs_ac_losses"
    ),
    "restoration_or_redispatch": False,
}
_POWER_FLOW = {
    "engine": "pypower_runpf",
    "algorithm": "newton",
    "tolerance": 1.0e-8,
    "maximum_iterations": 20,
    "voltage_violation_tolerance_pu": 1.0e-6,
    "power_violation_tolerance": 1.0e-4,
    "loading_tolerance": 1.0e-6,
}
_EVIDENCE = {
    "evidence_status": "derived_benchmark",
    "result_evidence_ceiling": ("public_rts_gmlc_direct_ac_replay_sensitivity_only"),
    "engineering_ac_parameters_available": False,
    "full_n_minus_one": False,
    "ac_security": False,
    "security_certified": False,
    "formal_vma_published": False,
}


@dataclass(frozen=True)
class _AcReplayContext:
    config_path: Path
    config: dict[str, Any]
    scan_context: Any
    template: RtsGmlcAcTemplate
    output_root: Path
    input_contract: dict[str, object]
    input_contract_sha256: str


@dataclass(frozen=True)
class _CandidateDispatch:
    dc_bus: int
    candidate: dict[str, object]
    state_ids: tuple[str, ...]
    timestamps: tuple[str, ...]
    hourly_by_timestamp: dict[str, dict[str, str]]
    commitment_by_timestamp: dict[str, dict[str, bool]]
    normal_generation: dict[str, dict[str, float]]
    normal_branch_flows: dict[str, dict[str, float]]
    security_generation: dict[tuple[str, str], dict[str, float]]
    security_branch_flows: dict[tuple[str, str], dict[str, float]]
    state_metadata: dict[tuple[str, str], dict[str, str]]


def _read_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    expected = {
        "preregistration": _PREREGISTRATION,
        "parent_scan": _PARENT_SCAN,
        "ac_source": _AC_SOURCE,
        "case_scope": _CASE_SCOPE,
        "ac_assumptions": _AC_ASSUMPTIONS,
        "power_flow": _POWER_FLOW,
        "evidence": _EVIDENCE,
    }
    if not isinstance(config, dict) or set(config) != set(expected) | {"output"}:
        raise ValueError("RTS-GMLC AC replay preregistration schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"RTS-GMLC AC replay {key} contract drifted")
    if not isinstance(config["output"], dict) or set(config["output"]) != {"directory"}:
        raise ValueError("RTS-GMLC AC replay output contract drifted")
    return config


def _rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _group_values(
    rows: list[dict[str, str]],
    *,
    group_fields: tuple[str, ...],
    key_field: str,
    value_field: str,
    value_parser,
) -> dict[Any, dict[str, Any]]:
    grouped: dict[Any, dict[str, Any]] = {}
    for row in rows:
        group = tuple(row[field] for field in group_fields)
        group_key: Any = group[0] if len(group) == 1 else group
        key = row[key_field]
        values = grouped.setdefault(group_key, {})
        if key in values:
            raise ValueError(f"Duplicate AC replay input key {group_key}/{key}")
        values[key] = value_parser(row[value_field])
    return grouped


def _load_candidate_dispatch(ctx: _AcReplayContext, dc_bus: int) -> _CandidateDispatch:
    root = ctx.scan_context.config["output"]["directory"]
    candidate_root = Path(root) / "candidates" / f"bus_{dc_bus}"
    _verify_output_manifest(candidate_root)
    summary = json.loads((candidate_root / "summary.json").read_text(encoding="utf-8"))
    if summary["candidate"]["dc_bus"] != dc_bus:
        raise ValueError(f"RTS-GMLC AC candidate {dc_bus} metadata drifted")
    state_ids = tuple(summary["security_state_ids"])
    if len(state_ids) != 24 or state_ids[0] != "normal":
        raise ValueError("RTS-GMLC AC replay requires all 24 common states")
    hourly_rows = _rows(candidate_root / "hourly_dispatch.csv")
    timestamps = tuple(row["timestamp"] for row in hourly_rows)
    if len(timestamps) != 24 or len(set(timestamps)) != 24:
        raise ValueError("RTS-GMLC AC replay hourly timestamps drifted")
    hourly = {row["timestamp"]: row for row in hourly_rows}

    generator_rows = _rows(candidate_root / "generator_dispatch.csv")
    commitment = _group_values(
        generator_rows,
        group_fields=("timestamp",),
        key_field="generator_uid",
        value_field="commitment",
        value_parser=lambda value: value == "true",
    )
    normal_generation = _group_values(
        generator_rows,
        group_fields=("timestamp",),
        key_field="generator_uid",
        value_field="generation_mw",
        value_parser=float,
    )
    normal_flows = _group_values(
        _rows(candidate_root / "normal_branch_flows.csv"),
        group_fields=("timestamp",),
        key_field="branch_uid",
        value_field="flow_mw",
        value_parser=float,
    )
    security_generation = _group_values(
        _rows(candidate_root / "security_generator_dispatch.csv"),
        group_fields=("timestamp", "state_id"),
        key_field="generator_uid",
        value_field="generation_mw",
        value_parser=float,
    )
    security_flows = _group_values(
        _rows(candidate_root / "security_branch_flows.csv"),
        group_fields=("timestamp", "state_id"),
        key_field="branch_uid",
        value_field="flow_mw",
        value_parser=float,
    )
    audit_rows = _rows(candidate_root / "security_audit.csv")
    metadata = {}
    for row in audit_rows:
        key = (row["timestamp"], row["state_id"])
        if key in metadata:
            raise ValueError(f"Duplicate RTS-GMLC AC state metadata {key}")
        metadata[key] = row

    generator_uids = {generator.uid for generator in ctx.scan_context.data.generators}
    branch_uids = {branch.uid for branch in ctx.scan_context.data.branches}
    nonnormal = set(state_ids) - {"normal"}
    if any(set(commitment[time]) != generator_uids for time in timestamps):
        raise ValueError("RTS-GMLC AC commitment coverage drifted")
    if any(set(normal_generation[time]) != generator_uids for time in timestamps):
        raise ValueError("RTS-GMLC AC normal generation coverage drifted")
    if any(set(normal_flows[time]) != branch_uids for time in timestamps):
        raise ValueError("RTS-GMLC AC normal branch coverage drifted")
    expected_security_keys = {
        (timestamp, state_id) for timestamp in timestamps for state_id in nonnormal
    }
    if (
        set(security_generation) != expected_security_keys
        or set(security_flows) != expected_security_keys
    ):
        raise ValueError("RTS-GMLC AC security table coverage drifted")
    if any(set(values) != generator_uids for values in security_generation.values()):
        raise ValueError("RTS-GMLC AC security generation keys drifted")
    if any(set(values) != branch_uids for values in security_flows.values()):
        raise ValueError("RTS-GMLC AC security branch keys drifted")
    if set(metadata) != {
        (timestamp, state_id) for timestamp in timestamps for state_id in state_ids
    }:
        raise ValueError("RTS-GMLC AC state metadata coverage drifted")
    return _CandidateDispatch(
        dc_bus=dc_bus,
        candidate=summary["candidate"],
        state_ids=state_ids,
        timestamps=timestamps,
        hourly_by_timestamp=hourly,
        commitment_by_timestamp=commitment,
        normal_generation=normal_generation,
        normal_branch_flows=normal_flows,
        security_generation=security_generation,
        security_branch_flows=security_flows,
        state_metadata=metadata,
    )


def _build_context(config_path: Path) -> _AcReplayContext:
    config = _read_config(config_path)
    scan = _build_scan_context(_SCAN_CONFIG)
    if (
        scan.registration_contract_sha256
        != _PARENT_SCAN["preregistration_contract_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC parent registration drifted")
    scan_root = Path(scan.config["output"]["directory"])
    common = json.loads(
        (scan_root / "common_security" / "summary.json").read_text(encoding="utf-8")
    )
    if (
        common["common_security_contract_sha256"]
        != _PARENT_SCAN["common_security_contract_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC parent common security drifted")
    aggregate_root = scan_root / "aggregate"
    _verify_output_manifest(aggregate_root)
    if (
        _sha256(aggregate_root / "SHA256SUMS")
        != _PARENT_SCAN["aggregate_manifest_sha256"]
    ):
        raise RuntimeError("RTS-GMLC AC parent aggregate manifest drifted")
    representatives = json.loads(
        (aggregate_root / "representatives.json").read_text(encoding="utf-8")
    )
    if (
        representatives["ac_representative_bus_ids"]
        != _PARENT_SCAN["representative_bus_order"]
    ):
        raise RuntimeError("RTS-GMLC AC representative selection drifted")
    for dc_bus, digest in _PARENT_SCAN[
        "representative_candidate_manifest_sha256"
    ].items():
        root = scan_root / "candidates" / f"bus_{dc_bus}"
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != digest:
            raise RuntimeError(f"RTS-GMLC AC candidate {dc_bus} manifest drifted")

    upstream = Path(_AC_SOURCE["upstream_path"])
    if _sha256(upstream / "SHA256SUMS") != _AC_SOURCE["upstream_manifest_sha256"]:
        raise RuntimeError("RTS-GMLC AC upstream manifest drifted")
    reference = Path(_AC_SOURCE["official_matpower_reference_path"])
    if _sha256(reference) != _AC_SOURCE["official_matpower_reference_sha256"]:
        raise RuntimeError("RTS-GMLC official MATPOWER reference drifted")
    template = load_rts_gmlc_ac_template(
        upstream,
        base_mva=float(_AC_SOURCE["base_mva"]),
        voltage_minimum_pu=float(_AC_ASSUMPTIONS["voltage_limits_pu"][0]),
        voltage_maximum_pu=float(_AC_ASSUMPTIONS["voltage_limits_pu"][1]),
    )
    output_root = Path(config["output"]["directory"])
    contract = {
        "schema": "rts_gmlc_multi_poi_ac_replay_inputs_v1",
        "config_sha256": _sha256(config_path),
        "parent_scan": config["parent_scan"],
        "ac_source": config["ac_source"],
        "case_scope": config["case_scope"],
        "ac_assumptions": config["ac_assumptions"],
        "power_flow": config["power_flow"],
        "evidence": config["evidence"],
        "implementation_sha256": {
            "experiments/run_rts_gmlc_multi_poi_ac_replay.py": _sha256(Path(__file__)),
            "src/grid/rts_gmlc_ac.py": _sha256(Path("src/grid/rts_gmlc_ac.py")),
        },
        "software_versions": {
            "numpy": importlib.metadata.version("numpy"),
            "pypower": importlib.metadata.version("pypower"),
            "scipy": importlib.metadata.version("scipy"),
        },
    }
    return _AcReplayContext(
        config_path=config_path,
        config=config,
        scan_context=scan,
        template=template,
        output_root=output_root,
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def prepare_preregistration(config_path: Path) -> dict[str, Any]:
    ctx = _build_context(config_path)
    target = ctx.output_root / "preregistration"
    payload = {
        "schema": _PREREGISTRATION["schema"],
        "preregistration_id": _PREREGISTRATION["id"],
        "status": _PREREGISTRATION["status"],
        "externally_timestamped": False,
        "all_ac_cases_blind": False,
        "observed_probe_cases_before_freeze": _PREREGISTRATION[
            "observed_probe_cases_before_freeze"
        ],
        "input_contract": ctx.input_contract,
        "input_contract_sha256": ctx.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC AC preregistration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC AC config snapshot drifted")
        return observed
    if ctx.output_root.exists() and any(ctx.output_root.iterdir()):
        raise RuntimeError("Cannot prepare AC preregistration beside existing results")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC AC artifact {root / name} is not an object")
    return payload


def _require_preregistration(ctx: _AcReplayContext) -> dict[str, Any]:
    observed = _load_json(ctx.output_root / "preregistration", "registration.json")
    if observed["input_contract"] != _stable_json(ctx.input_contract):
        raise RuntimeError("RTS-GMLC AC live inputs drifted from preregistration")
    if observed["input_contract_sha256"] != ctx.input_contract_sha256:
        raise RuntimeError("RTS-GMLC AC input contract SHA-256 drifted")
    if (ctx.output_root / "preregistration" / "config.yaml").read_bytes() != (
        ctx.config_path.read_bytes()
    ):
        raise RuntimeError("RTS-GMLC AC live config drifted")
    return observed


_CASE_FIELDS = (
    "candidate_order",
    "candidate_id",
    "dc_bus",
    "bus_name",
    "power_factor_case",
    "data_center_power_factor",
    "hour_index",
    "timestamp",
    "state_order",
    "state_id",
    "kind",
    "element_uid",
    "response_mode",
    "branch_rating",
    "data_center_power_mw",
    "data_center_reactive_demand_mvar",
    "native_reactive_demand_mvar",
    "hvdc_dc1_flow_mw",
    "dc_flow_reconstruction_residual_mw",
    "evaluated",
    "converged",
    "secure",
    "status",
    "min_voltage_pu",
    "min_voltage_bus",
    "max_voltage_pu",
    "max_voltage_bus",
    "max_voltage_violation_pu",
    "max_branch_loading_fraction",
    "max_loaded_branch_uid",
    "max_active_power_violation_mw",
    "max_active_power_violation_generator_uid",
    "max_reactive_power_violation_mvar",
    "max_reactive_power_violation_generator_uid",
    "max_non_slack_pg_deviation_mw",
    "reference_bus",
    "reference_generator_uid",
    "active_generator_count",
    "requested_generation_mw",
    "ac_generation_mw",
    "slack_and_loss_adjustment_mw",
)


_SUMMARY_FIELDS = (
    "candidate_id",
    "dc_bus",
    "power_factor_case",
    "data_center_power_factor",
    "case_count",
    "converged_count",
    "secure_count",
    "not_converged_count",
    "voltage_violation_count",
    "branch_loading_violation_count",
    "active_power_violation_count",
    "reactive_power_violation_count",
    "minimum_voltage_pu",
    "maximum_voltage_pu",
    "maximum_voltage_violation_pu",
    "maximum_branch_loading_fraction",
    "maximum_active_power_violation_mw",
    "maximum_reactive_power_violation_mvar",
    "maximum_non_slack_pg_deviation_mw",
    "maximum_absolute_slack_and_loss_adjustment_mw",
    "maximum_dc_flow_reconstruction_residual_mw",
)


def _evaluate_cases(ctx: _AcReplayContext) -> list[dict[str, object]]:
    rows = []
    point_by_timestamp = {
        point.timestamp.isoformat(): point for point in ctx.scan_context.business.points
    }
    for dc_bus in _CASE_SCOPE["candidate_representatives"]:
        dispatch = _load_candidate_dispatch(ctx, int(dc_bus))
        for pf_case in _CASE_SCOPE["power_factor_cases"]:
            power_factor = float(pf_case["value"])
            for hour_index, timestamp in enumerate(dispatch.timestamps):
                try:
                    point = point_by_timestamp[timestamp]
                except KeyError as error:
                    raise ValueError(
                        "RTS-GMLC AC timestamp does not match day-0"
                    ) from error
                hourly = dispatch.hourly_by_timestamp[timestamp]
                data_center_power = float(hourly["data_center_power_mw"])
                commitment = dispatch.commitment_by_timestamp[timestamp]
                for state_order, state_id in enumerate(dispatch.state_ids):
                    metadata = dispatch.state_metadata[(timestamp, state_id)]
                    if state_id == "normal":
                        generation = dispatch.normal_generation[timestamp]
                        branch_flows = dispatch.normal_branch_flows[timestamp]
                    else:
                        key = (timestamp, state_id)
                        generation = dispatch.security_generation[key]
                        branch_flows = dispatch.security_branch_flows[key]
                    total_demand = dict(point.demand_by_bus_mw)
                    total_demand[int(dc_bus)] += data_center_power
                    dc_flows, reconstruction_residual = reconstruct_rts_gmlc_dc_flows(
                        ctx.scan_context.data,
                        demand_by_bus_mw=total_demand,
                        generation_mw=generation,
                        ac_branch_flows_mw=branch_flows,
                        tolerance_mw=1.0e-6,
                    )
                    if (
                        state_id == "normal"
                        and abs(dc_flows["DC1"] - float(hourly["hvdc_dc1_flow_mw"]))
                        > 1.0e-6
                    ):
                        raise RuntimeError(
                            "RTS-GMLC AC normal DC1 reconstruction drifted"
                        )
                    kind = metadata["kind"]
                    element_uid = metadata["element_uid"] or None
                    configured = configure_rts_gmlc_ac_case(
                        ctx.template,
                        ctx.scan_context.data,
                        point,
                        generation_mw=generation,
                        commitment=commitment,
                        dc_bus=int(dc_bus),
                        data_center_power_mw=data_center_power,
                        data_center_power_factor=power_factor,
                        dc_flows_mw=dc_flows,
                        outaged_branch_uid=(element_uid if kind == "branch" else None),
                        outaged_generator_uid=(
                            element_uid if kind == "generator" else None
                        ),
                    )
                    result = validate_rts_gmlc_ac_power_flow(
                        ctx.template,
                        configured,
                        branch_rating=metadata["branch_rating"],
                        voltage_tolerance_pu=float(
                            _POWER_FLOW["voltage_violation_tolerance_pu"]
                        ),
                        power_tolerance=float(_POWER_FLOW["power_violation_tolerance"]),
                        loading_tolerance=float(_POWER_FLOW["loading_tolerance"]),
                    )
                    rows.append(
                        {
                            "candidate_order": dispatch.candidate["candidate_order"],
                            "candidate_id": dispatch.candidate["candidate_id"],
                            "dc_bus": int(dc_bus),
                            "bus_name": dispatch.candidate["bus_name"],
                            "power_factor_case": pf_case["id"],
                            "data_center_power_factor": power_factor,
                            "hour_index": hour_index,
                            "timestamp": timestamp,
                            "state_order": state_order,
                            "state_id": state_id,
                            "kind": kind,
                            "element_uid": element_uid,
                            "response_mode": metadata["response_mode"],
                            "branch_rating": metadata["branch_rating"],
                            "data_center_power_mw": data_center_power,
                            "data_center_reactive_demand_mvar": (
                                configured.data_center_reactive_demand_mvar
                            ),
                            "native_reactive_demand_mvar": (
                                configured.native_reactive_demand_mvar
                            ),
                            "hvdc_dc1_flow_mw": dc_flows["DC1"],
                            "dc_flow_reconstruction_residual_mw": (
                                reconstruction_residual
                            ),
                            **asdict(result),
                        }
                    )
    expected_count = (
        len(_CASE_SCOPE["candidate_representatives"])
        * len(_CASE_SCOPE["power_factor_cases"])
        * int(_CASE_SCOPE["expected_cases_per_candidate_power_factor"])
    )
    if len(rows) != expected_count:
        raise RuntimeError("RTS-GMLC AC replay case count drifted")
    return rows


def _group_summaries(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    summaries = []
    voltage_tolerance = float(_POWER_FLOW["voltage_violation_tolerance_pu"])
    power_tolerance = float(_POWER_FLOW["power_violation_tolerance"])
    loading_tolerance = float(_POWER_FLOW["loading_tolerance"])
    for dc_bus in _CASE_SCOPE["candidate_representatives"]:
        for pf_case in _CASE_SCOPE["power_factor_cases"]:
            group = [
                row
                for row in rows
                if row["dc_bus"] == dc_bus and row["power_factor_case"] == pf_case["id"]
            ]
            converged = [row for row in group if row["converged"]]

            def values(field: str) -> list[float]:
                return [
                    float(row[field]) for row in converged if row[field] is not None
                ]

            summaries.append(
                {
                    "candidate_id": group[0]["candidate_id"],
                    "dc_bus": dc_bus,
                    "power_factor_case": pf_case["id"],
                    "data_center_power_factor": pf_case["value"],
                    "case_count": len(group),
                    "converged_count": len(converged),
                    "secure_count": sum(bool(row["secure"]) for row in group),
                    "not_converged_count": len(group) - len(converged),
                    "voltage_violation_count": sum(
                        float(row["max_voltage_violation_pu"] or 0.0)
                        > voltage_tolerance
                        for row in converged
                    ),
                    "branch_loading_violation_count": sum(
                        float(row["max_branch_loading_fraction"] or 0.0)
                        > 1.0 + loading_tolerance
                        for row in converged
                    ),
                    "active_power_violation_count": sum(
                        float(row["max_active_power_violation_mw"] or 0.0)
                        > power_tolerance
                        for row in converged
                    ),
                    "reactive_power_violation_count": sum(
                        float(row["max_reactive_power_violation_mvar"] or 0.0)
                        > power_tolerance
                        for row in converged
                    ),
                    "minimum_voltage_pu": min(values("min_voltage_pu"), default=None),
                    "maximum_voltage_pu": max(values("max_voltage_pu"), default=None),
                    "maximum_voltage_violation_pu": max(
                        values("max_voltage_violation_pu"), default=None
                    ),
                    "maximum_branch_loading_fraction": max(
                        values("max_branch_loading_fraction"), default=None
                    ),
                    "maximum_active_power_violation_mw": max(
                        values("max_active_power_violation_mw"), default=None
                    ),
                    "maximum_reactive_power_violation_mvar": max(
                        values("max_reactive_power_violation_mvar"), default=None
                    ),
                    "maximum_non_slack_pg_deviation_mw": max(
                        values("max_non_slack_pg_deviation_mw"), default=None
                    ),
                    "maximum_absolute_slack_and_loss_adjustment_mw": max(
                        (
                            abs(value)
                            for value in values("slack_and_loss_adjustment_mw")
                        ),
                        default=None,
                    ),
                    "maximum_dc_flow_reconstruction_residual_mw": max(
                        float(row["dc_flow_reconstruction_residual_mw"])
                        for row in group
                    ),
                }
            )
    return summaries


def run(config_path: Path) -> dict[str, Any]:
    ctx = _build_context(config_path)
    registration = _require_preregistration(ctx)
    target = ctx.output_root / "results"
    if target.exists():
        summary = _load_json(target, "summary.json")
        if summary["input_contract_sha256"] != ctx.input_contract_sha256:
            raise RuntimeError("Published RTS-GMLC AC result inputs drifted")
        return summary
    rows = _evaluate_cases(ctx)
    grouped = _group_summaries(rows)
    summary = {
        "schema": "rts_gmlc_multi_poi_ac_replay_results_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
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
            staging / "candidate_power_factor_summary.csv", _SUMMARY_FIELDS, grouped
        )
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("prepare", "run"),
        default="run",
    )
    args = parser.parse_args()
    result = (
        prepare_preregistration(args.config)
        if args.stage == "prepare"
        else run(args.config)
    )
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
