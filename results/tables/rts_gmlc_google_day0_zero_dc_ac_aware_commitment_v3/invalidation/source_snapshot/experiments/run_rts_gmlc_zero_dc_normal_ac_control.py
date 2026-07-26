"""Run the pre-registered zero-data-center normal-state AC control."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import platform
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any

import yaml
from pypower.idx_gen import GEN_BUS, GEN_STATUS

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import (
    INCIDENT_FIELDS,
    _CSV_FIELDS,
    _artifact_rows,
    _build_request,
    _sha256,
    _stable_json,
    _write_csv,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay import (
    _CASE_FIELDS as _PARENT_CASE_FIELDS,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_timezone_amended import (
    _amended_context,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended import (
    _configure_q_capable_voltage_control,
    _require_amendment as _require_voltage_control_amendment,
)
from experiments.run_rts_gmlc_multi_poi_scan import (
    _build_scan_context,
    _publish_payload,
    _require_common_security,
    _write_json,
)
from src.evaluation import (
    INCIDENT_CHRONOLOGY_SCHEMA,
    EvidenceSource,
    IncidentChronology,
)
from src.grid import solve_rts_gmlc_scuc, validate_chronological_dispatch
from src.grid.rts_gmlc_ac import (
    reconstruct_rts_gmlc_dc_flows,
    validate_rts_gmlc_ac_power_flow,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

_SCAN_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_scan.yaml")
_PARENT_AC_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml")
_SLACK_AMENDMENT_CONFIG = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_slack_amendment.yaml"
)
_VOLTAGE_CONTROL_AMENDMENT_CONFIG = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_" "voltage_control_amendment.yaml"
)
_PARENT_SCAN_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_selected_n1_dc_scuc_v1"
)
_PARENT_AC_ROOT = Path("results/tables/rts_gmlc_google_day0_multi_poi_ac_replay_v1")
_PREREGISTRATION = {
    "id": "rts_gmlc_google_day0_zero_dc_normal_ac_control_v1",
    "schema": "rts_gmlc_zero_dc_normal_ac_control_preregistration_v1",
    "status": (
        "repository_local_frozen_after_treatment_outcomes_before_zero_control_solve"
    ),
    "externally_timestamped": False,
    "parent_treatment_outcomes_observed": True,
    "zero_control_outcomes_observed": False,
    "all_zero_control_cases_blind": True,
}
_PARENT_CONTRACTS = {
    "multi_poi_scan_config_path": _SCAN_CONFIG.as_posix(),
    "multi_poi_scan_config_sha256": (
        "14f578c5ed1b781449759f479b804c324a7634301380ca478b23334b46b240e4"
    ),
    "multi_poi_registration_contract_sha256": (
        "16d9edc57d965e802dd17106a3a0aa7a99ae93f0f493ba977d8490573ce3fb78"
    ),
    "common_security_manifest_sha256": (
        "96d476b082d96b6204eca6093c9daf4f4f1aae175076122042960b0d9358347e"
    ),
    "common_security_contract_sha256": (
        "7865c7544817acd2d0dd6a461766862af52f7175eb24f2c1466f52e70115aa87"
    ),
    "parent_ac_config_path": _PARENT_AC_CONFIG.as_posix(),
    "parent_ac_config_sha256": (
        "5c3c6d3925b78f743cf9e2e55578d1034c3d907782d03edfaa1dda3bdd1a5a9c"
    ),
    "parent_ac_input_contract_sha256": (
        "7dc28350aaa137a3f99a90a83365ebafb58c8de739a2999a5a93ed4ea0babd41"
    ),
    "slack_amendment_config_path": _SLACK_AMENDMENT_CONFIG.as_posix(),
    "slack_amendment_config_sha256": (
        "ee0436c39530791ac055fedd5ec91624ba3926985c6f39b251d28f1ee504f2f1"
    ),
    "slack_amendment_implementation_sha256": (
        "6a9f2050a7882ef4c7fae72daefbc018d966ad46977bed22748383f15fe26ac0"
    ),
    "slack_amendment_manifest_sha256": (
        "3aa5c70b94f5771ba1822425b58eff4704ee1f93a7bb310146de7df8f79bfb87"
    ),
    "slack_corrected_ac_result_manifest_sha256": (
        "2b5b705d2074ddb8f846b7a8d897ed87d32021446fd867825b7dd3a0982e2a7e"
    ),
    "voltage_control_amendment_config_path": (
        _VOLTAGE_CONTROL_AMENDMENT_CONFIG.as_posix()
    ),
    "voltage_control_amendment_config_sha256": (
        "67d118fb769474ee891ce17cebfe261f64b46e02b1bb8a606c5bc3889449da6e"
    ),
    "voltage_control_amendment_id": (
        "rts_gmlc_ac_replay_q_capable_voltage_control_amendment_004"
    ),
    "voltage_control_amendment_implementation_sha256": (
        "b49a867f518fd29571a364bc0597b26085e32ed4b698c60128a9cfe6511dc56e"
    ),
    "voltage_control_amendment_manifest_sha256": (
        "19001629898bbaf0af191978beabdf6b1d5c779246bf304242c072b2e03b9f9a"
    ),
    "voltage_control_corrected_ac_result_manifest_sha256": (
        "ee4894bba4e65433ffed4b31e4d96c78035bd2413dd4fa6accb3eb9f16c0609a"
    ),
}
_ZERO_CONTROL = {
    "source_business_rule": (
        "preserve_parent_timestamps_and_periods_zero_all_power_fields"
    ),
    "zero_fields": [
        "requested_demand_mw",
        "flexible_demand_mw",
        "recoverable_flexible_mw",
        "physical_maximum_demand_mw",
        "recovery_headroom_mw",
    ],
    "connected_capacity_mw": 0.0,
    "contract_call_limit_mw": 0.0,
    "dc_bus_api_placeholder": 120,
    "placeholder_is_not_a_poi_comparison": True,
    "commitment_and_initial_state": ("reoptimized_free_boundary_for_zero_dc_control"),
    "fixed_treatment_commitment_used": False,
    "common_selected_n_minus_one_states_retained": True,
    "native_grid_inputs_changed": False,
}
_CASE_SCOPE = {
    "dc_horizon": "all_24_hours",
    "dc_security_states": "all_24_parent_common_states",
    "ac_security_states": "normal_only",
    "expected_unique_ac_cases": 24,
    "power_factor_case": "not_applicable_zero_active_power",
    "configured_power_factor_value": 1.0,
    "branch_rating": "continuous",
    "completion_policy": "all_24_cases_reported_no_failure_deletion",
}
_AC_ASSUMPTIONS = {
    "reuse_parent_ac_numerical_inputs": True,
    "unambiguous_single_online_committable_slack_required": True,
    "voltage_control_target": "common_online_q_capable_generator_vg",
    "source_bus_vm_role": "newton_start_not_control_fallback",
    "colocated_q_inert_vg_normalized": True,
    "conflicting_online_q_capable_vg_policy": "fail_before_runpf",
    "q_limit_switching": False,
    "restoration_or_redispatch": False,
    "poi_connection_equipment_added": False,
    "hvdc_converter_reactive_power_modeled": False,
    "source_mw_rating_used_as_mva_proxy": True,
    "voltage_limits_pu": [0.95, 1.05],
}
_POWER_FLOW = {
    "engine": "pypower_runpf",
    "algorithm": "newton",
    "tolerance": 1.0e-8,
    "maximum_iterations": 20,
    "voltage_violation_tolerance_pu": 1.0e-6,
    "power_violation_tolerance": 1.0e-4,
    "non_slack_pg_audit_tolerance_mw": 1.0e-6,
    "loading_tolerance": 1.0e-6,
}
_EVIDENCE = {
    "evidence_status": "derived_benchmark",
    "result_evidence_ceiling": "public_rts_gmlc_zero_dc_normal_ac_control_only",
    "control_interpretation": "reoptimized_no_data_center_operational_counterfactual",
    "causal_poi_attribution_supported": False,
    "engineering_ac_parameters_available": False,
    "full_n_minus_one": False,
    "ac_security": False,
    "security_certified": False,
    "formal_vma_published": False,
}
_SOLVER = {
    "name": "highs",
    "tee": False,
    "tolerance_mw": 1.0e-6,
    "threads": 4,
    "mip_relative_gap": 1.0e-6,
}
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_zero_dc_normal_ac_control.py"),
    Path("experiments/run_rts_gmlc_day0_scuc.py"),
    Path("experiments/run_rts_gmlc_multi_poi_scan.py"),
    Path("experiments/run_rts_gmlc_multi_poi_ac_replay.py"),
    Path("experiments/run_rts_gmlc_multi_poi_ac_replay_timezone_amended.py"),
    Path("experiments/run_rts_gmlc_multi_poi_ac_replay_slack_amended.py"),
    Path("experiments/run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended.py"),
    Path("src/evaluation/chronology_inputs.py"),
    Path("src/grid/chronological_dispatch.py"),
    Path("src/grid/rts_gmlc.py"),
    Path("src/grid/rts_gmlc_scuc.py"),
    Path("src/grid/rts_gmlc_ac.py"),
)
_RESULT_FIELDS = _PARENT_CASE_FIELDS[_PARENT_CASE_FIELDS.index("evaluated") :]
_AC_FIELDS = (
    "hour_index",
    "timestamp",
    "control_id",
    "zero_data_center",
    "poi_applicable",
    "dc_bus_api_placeholder",
    "power_factor_case",
    "configured_power_factor_value",
    "state_id",
    "branch_rating",
    "native_grid_demand_mw",
    "data_center_power_mw",
    "data_center_reactive_demand_mvar",
    "native_reactive_demand_mvar",
    "hvdc_dc1_flow_mw",
    "dc_flow_reconstruction_residual_mw",
) + _RESULT_FIELDS
_HOURLY_ZERO_FIELDS = (
    "data_center_requested_mw",
    "data_center_flexible_demand_mw",
    "data_center_recoverable_flexible_mw",
    "data_center_physical_maximum_mw",
    "data_center_connected_capacity_mw",
    "data_center_call_limit_mw",
    "data_center_recovery_headroom_mw",
    "data_center_grid_call_mw",
    "data_center_recovery_power_mw",
    "data_center_power_mw",
)
_HOURLY_FINITE_FIELDS = (
    "native_grid_demand_mw",
    *_HOURLY_ZERO_FIELDS,
    "total_demand_mw",
    "network_losses_mw",
    "total_generation_mw",
    "generation_balance_residual_mw",
    "committed_thermal_units",
    "spin_requirement_mw",
    "spin_provided_mw",
    "maximum_normal_branch_loading_fraction",
    "hvdc_dc1_flow_mw",
)
_HOURLY_TRUE_FIELDS = (
    "commitment_feasible",
    "ramp_feasible",
    "reserve_feasible",
    "normal_secure",
    "selected_contingencies_secure",
)
_GENERATOR_FINITE_FIELDS = (
    "bus",
    "generation_mw",
    "minimum_mw",
    "maximum_mw",
    "spin_up_mw",
)
_BRANCH_FINITE_FIELDS = (
    "from_bus",
    "to_bus",
    "flow_mw",
    "continuous_rating_mw",
    "loading_fraction",
)
_SECURITY_AUDIT_FINITE_FIELDS = (
    "total_generation_mw",
    "maximum_branch_loading_fraction",
    "maximum_branch_rating_violation_mw",
    "outaged_element_output_mw",
)
_SECURITY_GENERATOR_FINITE_FIELDS = ("generation_mw",)
_SECURITY_BRANCH_FINITE_FIELDS = (
    "flow_mw",
    "rating_mw",
    "loading_fraction",
)
_AC_FINITE_FIELDS = (
    "hour_index",
    "dc_bus_api_placeholder",
    "configured_power_factor_value",
    "native_grid_demand_mw",
    "data_center_power_mw",
    "data_center_reactive_demand_mvar",
    "native_reactive_demand_mvar",
    "hvdc_dc1_flow_mw",
    "dc_flow_reconstruction_residual_mw",
    "min_voltage_pu",
    "min_voltage_bus",
    "max_voltage_pu",
    "max_voltage_bus",
    "max_voltage_violation_pu",
    "max_branch_loading_fraction",
    "max_active_power_violation_mw",
    "max_reactive_power_violation_mvar",
    "max_non_slack_pg_deviation_mw",
    "reference_bus",
    "active_generator_count",
    "requested_generation_mw",
    "ac_generation_mw",
    "slack_and_loss_adjustment_mw",
)
_AC_NULLABLE_FINITE_FIELDS = frozenset(
    {
        "min_voltage_pu",
        "min_voltage_bus",
        "max_voltage_pu",
        "max_voltage_bus",
        "max_voltage_violation_pu",
        "max_branch_loading_fraction",
        "max_active_power_violation_mw",
        "max_reactive_power_violation_mvar",
        "max_non_slack_pg_deviation_mw",
        "requested_generation_mw",
        "ac_generation_mw",
        "slack_and_loss_adjustment_mw",
    }
)


@dataclass(frozen=True)
class _ControlContext:
    config_path: Path
    config: dict[str, Any]
    scan: Any
    ac: Any
    common_security: dict[str, Any]
    output_root: Path
    zero_business: Any
    input_contract: dict[str, Any]
    input_contract_sha256: str


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "preregistration": _PREREGISTRATION,
        "parent_contracts": _PARENT_CONTRACTS,
        "zero_control": _ZERO_CONTROL,
        "case_scope": _CASE_SCOPE,
        "ac_assumptions": _AC_ASSUMPTIONS,
        "power_flow": _POWER_FLOW,
        "evidence": _EVIDENCE,
        "solver": _SOLVER,
    }
    if not isinstance(config, dict) or set(config) != set(expected) | {"output"}:
        raise ValueError("RTS-GMLC zero-DC control config schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"RTS-GMLC zero-DC control {key} drifted")
    if not isinstance(config["output"], dict) or set(config["output"]) != {"directory"}:
        raise ValueError("RTS-GMLC zero-DC output contract drifted")
    return config


def _zero_business(parent: Any) -> Any:
    return replace(
        parent,
        points=tuple(
            replace(
                point,
                requested_demand_mw=0.0,
                flexible_demand_mw=0.0,
                recoverable_flexible_mw=0.0,
                physical_maximum_demand_mw=0.0,
                recovery_headroom_mw=0.0,
            )
            for point in parent.points
        ),
    )


def _zero_business_payload(business: Any) -> dict[str, object]:
    return {
        "schema": "rts_gmlc_zero_dc_business_transform_v1",
        "source_business_rule": _ZERO_CONTROL["source_business_rule"],
        "points": [
            {
                "timestamp": point.timestamp.isoformat(),
                "period": point.period,
                **{
                    field: float(getattr(point, field))
                    for field in _ZERO_CONTROL["zero_fields"]
                },
            }
            for point in business.points
        ],
    }


def _empty_incidents() -> IncidentChronology:
    empty_sha = _sha256_bytes((",".join(INCIDENT_FIELDS) + "\n").encode("utf-8"))
    return IncidentChronology(
        schema=INCIDENT_CHRONOLOGY_SCHEMA,
        incidents=(),
        source=EvidenceSource(
            dataset_id="rts_gmlc_zero_dc_control_empty_incidents_v1",
            source_kind="synthetic_sensitivity",
            citation="empty diagnostic incident window; no frequency implied",
            version="v1",
            sha256=empty_sha,
        ),
    )


def _sha256_bytes(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _zero_model(base_model: dict[str, Any], *, dc_bus: int | None = None):
    model = dict(base_model)
    model["dc_bus"] = int(
        _ZERO_CONTROL["dc_bus_api_placeholder"] if dc_bus is None else dc_bus
    )
    model["dc_connected_capacity_mw"] = 0.0
    model["contract_call_limit_mw"] = 0.0
    return model


def _software_versions() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for package in ("highspy", "numpy", "pyomo", "pypower", "pyyaml", "scipy"):
        versions[package] = importlib.metadata.version(package)
    return versions


def _build_context(config_path: Path) -> _ControlContext:
    config = _read_config(config_path)
    for path_key, hash_key in (
        ("multi_poi_scan_config_path", "multi_poi_scan_config_sha256"),
        ("parent_ac_config_path", "parent_ac_config_sha256"),
        ("slack_amendment_config_path", "slack_amendment_config_sha256"),
        (
            "voltage_control_amendment_config_path",
            "voltage_control_amendment_config_sha256",
        ),
    ):
        if _sha256(Path(_PARENT_CONTRACTS[path_key])) != _PARENT_CONTRACTS[hash_key]:
            raise RuntimeError(f"RTS-GMLC zero-DC parent {path_key} drifted")

    scan = _build_scan_context(_SCAN_CONFIG)
    if (
        scan.registration_contract_sha256
        != _PARENT_CONTRACTS["multi_poi_registration_contract_sha256"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC parent scan contract drifted")
    common = _require_common_security(scan, _PARENT_SCAN_ROOT)
    if (
        common["common_security_contract_sha256"]
        != _PARENT_CONTRACTS["common_security_contract_sha256"]
        or _sha256(_PARENT_SCAN_ROOT / "common_security" / "SHA256SUMS")
        != _PARENT_CONTRACTS["common_security_manifest_sha256"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC common security drifted")

    ac = _amended_context(_PARENT_AC_CONFIG)
    if ac.input_contract_sha256 != _PARENT_CONTRACTS["parent_ac_input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC zero-DC parent AC contract drifted")
    _context, amendment, _amendment_config = _require_voltage_control_amendment(
        _VOLTAGE_CONTROL_AMENDMENT_CONFIG,
        _PARENT_AC_CONFIG,
    )
    if (
        amendment["amendment_id"] != _PARENT_CONTRACTS["voltage_control_amendment_id"]
        or amendment["amendment_implementation_sha256"]
        != _PARENT_CONTRACTS["voltage_control_amendment_implementation_sha256"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC voltage-control amendment drifted")
    for root, expected_hash in (
        (
            _PARENT_AC_ROOT / "amendments" / "003_unambiguous_slack",
            _PARENT_CONTRACTS["slack_amendment_manifest_sha256"],
        ),
        (
            _PARENT_AC_ROOT / "results_unambiguous_slack",
            _PARENT_CONTRACTS["slack_corrected_ac_result_manifest_sha256"],
        ),
        (
            _PARENT_AC_ROOT / "amendments" / "004_q_capable_voltage_control",
            _PARENT_CONTRACTS["voltage_control_amendment_manifest_sha256"],
        ),
        (
            _PARENT_AC_ROOT / "results_q_capable_voltage_control",
            _PARENT_CONTRACTS["voltage_control_corrected_ac_result_manifest_sha256"],
        ),
    ):
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != expected_hash:
            raise RuntimeError(f"RTS-GMLC zero-DC parent artifact {root} drifted")

    zero_business = _zero_business(scan.business)
    zero_payload = _zero_business_payload(zero_business)
    contract = {
        "schema": "rts_gmlc_zero_dc_normal_ac_control_inputs_v1",
        "config_sha256": _sha256(config_path),
        "parent_contracts": config["parent_contracts"],
        "zero_control": config["zero_control"],
        "zero_business_payload": zero_payload,
        "zero_business_payload_sha256": common_input_signature_sha256(zero_payload),
        "case_scope": config["case_scope"],
        "ac_assumptions": config["ac_assumptions"],
        "power_flow": config["power_flow"],
        "solver": config["solver"],
        "common_security_contract": common["common_security_contract"],
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "software_versions": _software_versions(),
        "evidence": config["evidence"],
    }
    return _ControlContext(
        config_path=config_path,
        config=config,
        scan=scan,
        ac=ac,
        common_security=common,
        output_root=Path(config["output"]["directory"]),
        zero_business=zero_business,
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: _ControlContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC zero-DC artifact {root / name} is not an object")
    return payload


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    target = output_root / "preregistration"
    payload = {
        "schema": _PREREGISTRATION["schema"],
        "preregistration_id": _PREREGISTRATION["id"],
        "status": _PREREGISTRATION["status"],
        "externally_timestamped": False,
        "parent_treatment_outcomes_observed": True,
        "zero_control_outcomes_observed": False,
        "all_zero_control_cases_blind": True,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC zero-DC preregistration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC zero-DC config snapshot drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare zero-DC control beside existing artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _ControlContext,
    output_root: Path,
) -> dict[str, Any]:
    observed = _load_json(output_root / "preregistration", "registration.json")
    if observed["input_contract"] != _stable_json(context.input_contract):
        raise RuntimeError("RTS-GMLC zero-DC live inputs drifted from preregistration")
    if observed["input_contract_sha256"] != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC zero-DC input contract SHA-256 drifted")
    if (output_root / "preregistration" / "config.yaml").read_bytes() != (
        context.config_path.read_bytes()
    ):
        raise RuntimeError("RTS-GMLC zero-DC live config drifted")
    return observed


def _zero_request(context: _ControlContext, *, dc_bus: int | None = None):
    request = _build_request(
        context.scan.data,
        context.zero_business,
        _empty_incidents(),
        _zero_model(context.scan.base_config["model"], dc_bus=dc_bus),
    )
    zero_series = (
        request.dc_requested_mw,
        request.dc_flexible_demand_mw,
        request.dc_recoverable_flexible_mw,
        request.dc_physical_maximum_mw,
        request.dc_connected_capacity_mw,
        request.dc_call_limit_mw,
        request.recovery_headroom_mw,
    )
    if any(float(value) != 0.0 for values in zero_series for value in values):
        raise RuntimeError("RTS-GMLC zero-DC request retained a nonzero business field")
    return request


def run_dc_dispatch(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "dc_dispatch"
    if target.exists():
        summary = _load_json(target, "summary.json")
        if summary["input_contract_sha256"] != context.input_contract_sha256:
            raise RuntimeError("Published RTS-GMLC zero-DC dispatch drifted")
        _load_zero_dispatch(context, output_root)
        return summary

    request = _zero_request(context)
    security = context.common_security["common_security_contract"]
    solved = solve_rts_gmlc_scuc(
        context.scan.data,
        request,
        solver_name=str(_SOLVER["name"]),
        tee=bool(_SOLVER["tee"]),
        tolerance_mw=float(_SOLVER["tolerance_mw"]),
        solver_threads=int(_SOLVER["threads"]),
        mip_relative_gap=float(_SOLVER["mip_relative_gap"]),
        pre_registered_branch_uids=tuple(security["branch_uids"]),
        pre_registered_generator_uids=tuple(security["generator_uids"]),
    )
    validate_chronological_dispatch(
        solved.dispatch_request,
        solved.dispatch_result,
        tolerance_mw=float(_SOLVER["tolerance_mw"]),
    )
    state_ids = tuple(state.state_id for state in solved.critical_selection.states)
    if state_ids != tuple(security["state_ids"]):
        raise RuntimeError("RTS-GMLC zero-DC dispatch changed the common states")
    if any(float(value) != 0.0 for value in solved.dispatch_result.dc_power_mw):
        raise RuntimeError("RTS-GMLC zero-DC dispatch served nonzero data-center power")
    rows_by_file = _artifact_rows(context.scan.data, solved)
    hourly = rows_by_file["hourly_dispatch.csv"]
    _validate_and_index_zero_dispatch(
        hourly_rows=hourly,
        generator_rows=rows_by_file["generator_dispatch.csv"],
        branch_rows=rows_by_file["normal_branch_flows.csv"],
        security_rows=rows_by_file["security_audit.csv"],
        security_generator_rows=rows_by_file["security_generator_dispatch.csv"],
        security_branch_rows=rows_by_file["security_branch_flows.csv"],
        expected_timestamps=tuple(
            point.timestamp.isoformat() for point in context.zero_business.points
        ),
        expected_native_demand_mw=tuple(
            sum(point.demand_by_bus_mw.values())
            for point in context.scan.data.hourly_points[:24]
        ),
        generator_uids=frozenset(
            generator.uid for generator in context.scan.data.generators
        ),
        branch_uids=frozenset(branch.uid for branch in context.scan.data.branches),
        expected_state_ids=tuple(security["state_ids"]),
        tolerance_mw=float(_SOLVER["tolerance_mw"]),
    )
    summary = {
        "schema": "rts_gmlc_zero_dc_dispatch_artifacts_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "hours": len(hourly),
        "first_timestamp": solved.dispatch_result.timestamps[0].isoformat(),
        "last_timestamp": solved.dispatch_result.timestamps[-1].isoformat(),
        "zero_data_center": True,
        "dc_bus_api_placeholder": _ZERO_CONTROL["dc_bus_api_placeholder"],
        "placeholder_is_not_a_poi_comparison": True,
        "commitment_reoptimized": True,
        "fixed_treatment_commitment_used": False,
        "critical_branch_uids": solved.critical_selection.branch_uids,
        "critical_generator_uids": solved.critical_selection.generator_uids,
        "security_state_ids": state_ids,
        "security_state_count_per_hour": len(state_ids),
        "prescreen_audit": asdict(solved.prescreen_audit),
        "scuc_audit": asdict(solved.scuc_audit),
        "fixed_commitment_ed_audit": asdict(solved.sced_audit),
        "constraint_generation_audit": asdict(solved.constraint_generation_audit),
        "residual_audit": asdict(solved.residual_audit),
        "all_data_center_power_fields_zero": True,
        "dispatch_artifact_contract_validated": True,
        "native_grid_inputs_changed": False,
        **_EVIDENCE,
    }

    def writer(staging: Path) -> None:
        _write_csv(staging / "incident_chronology.csv", INCIDENT_FIELDS, ())
        for name, rows in rows_by_file.items():
            _write_csv(staging / name, _CSV_FIELDS[name], rows)
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def _csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _finite_float(value: object, *, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"RTS-GMLC zero-DC {label} is not numeric") from error
    if not math.isfinite(parsed):
        raise RuntimeError(f"RTS-GMLC zero-DC {label} is not finite")
    return parsed


def _require_finite_fields(
    rows: Sequence[Mapping[str, object]],
    fields: tuple[str, ...],
    *,
    label: str,
    nullable_fields: frozenset[str] = frozenset(),
) -> None:
    for row_index, row in enumerate(rows):
        for field in fields:
            value = row[field]
            if value is None:
                if field in nullable_fields:
                    continue
                raise RuntimeError(
                    f"RTS-GMLC zero-DC {label} row {row_index} field {field} "
                    "is missing"
                )
            _finite_float(value, label=f"{label} row {row_index} field {field}")


def _parse_boolean(value: object, *, label: str) -> bool:
    if type(value) is bool:
        return bool(value)
    if value == "true":
        return True
    if value == "false":
        return False
    raise RuntimeError(f"RTS-GMLC zero-DC {label} is not boolean")


def _validate_and_index_zero_dispatch(
    *,
    hourly_rows: Sequence[Mapping[str, object]],
    generator_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
    security_rows: Sequence[Mapping[str, object]],
    security_generator_rows: Sequence[Mapping[str, object]],
    security_branch_rows: Sequence[Mapping[str, object]],
    expected_timestamps: tuple[str, ...],
    expected_native_demand_mw: tuple[float, ...],
    generator_uids: frozenset[str],
    branch_uids: frozenset[str],
    expected_state_ids: tuple[str, ...],
    tolerance_mw: float,
) -> tuple[
    dict[str, dict[str, float]],
    dict[str, dict[str, bool]],
    dict[str, dict[str, float]],
]:
    if (
        len(expected_timestamps) != len(expected_native_demand_mw)
        or len(set(expected_timestamps)) != len(expected_timestamps)
        or not expected_state_ids
        or expected_state_ids[0] != "normal"
        or len(set(expected_state_ids)) != len(expected_state_ids)
    ):
        raise RuntimeError("RTS-GMLC zero-DC expected chronology drifted")
    observed_timestamps = tuple(str(row["timestamp"]) for row in hourly_rows)
    if observed_timestamps != expected_timestamps or len(
        set(observed_timestamps)
    ) != len(observed_timestamps):
        raise RuntimeError("RTS-GMLC zero-DC hourly timestamp coverage drifted")
    _require_finite_fields(
        hourly_rows,
        _HOURLY_FINITE_FIELDS,
        label="hourly dispatch",
    )
    for index, row in enumerate(hourly_rows):
        if any(float(row[field]) != 0.0 for field in _HOURLY_ZERO_FIELDS):
            raise RuntimeError("RTS-GMLC zero-DC hourly power field is not zero")
        if not all(
            _parse_boolean(row[field], label=f"hourly {field}")
            for field in _HOURLY_TRUE_FIELDS
        ):
            raise RuntimeError("RTS-GMLC zero-DC hourly feasibility flag is false")
        native = float(row["native_grid_demand_mw"])
        total = float(row["total_demand_mw"])
        expected_native = float(expected_native_demand_mw[index])
        if (
            abs(native - expected_native) > tolerance_mw
            or abs(total - native) > tolerance_mw
        ):
            raise RuntimeError("RTS-GMLC zero-DC native demand drifted")
        if abs(float(row["generation_balance_residual_mw"])) > tolerance_mw:
            raise RuntimeError("RTS-GMLC zero-DC generation balance residual drifted")

    _require_finite_fields(
        generator_rows,
        _GENERATOR_FINITE_FIELDS,
        label="generator dispatch",
    )
    expected_generator_keys = {
        (timestamp, uid) for timestamp in expected_timestamps for uid in generator_uids
    }
    observed_generator_keys: set[tuple[str, str]] = set()
    generation: dict[str, dict[str, float]] = {}
    commitment: dict[str, dict[str, bool]] = {}
    for row in generator_rows:
        timestamp = str(row["timestamp"])
        uid = str(row["generator_uid"])
        key = (timestamp, uid)
        if key in observed_generator_keys:
            raise RuntimeError("RTS-GMLC zero-DC duplicate generator dispatch key")
        observed_generator_keys.add(key)
        generation.setdefault(timestamp, {})[uid] = float(row["generation_mw"])
        commitment.setdefault(timestamp, {})[uid] = _parse_boolean(
            row["commitment"],
            label="generator commitment",
        )
    if observed_generator_keys != expected_generator_keys:
        raise RuntimeError("RTS-GMLC zero-DC generator dispatch coverage drifted")

    _require_finite_fields(
        branch_rows,
        _BRANCH_FINITE_FIELDS,
        label="normal branch flow",
    )
    expected_branch_keys = {
        (timestamp, uid) for timestamp in expected_timestamps for uid in branch_uids
    }
    observed_branch_keys: set[tuple[str, str]] = set()
    flows: dict[str, dict[str, float]] = {}
    for row in branch_rows:
        timestamp = str(row["timestamp"])
        uid = str(row["branch_uid"])
        key = (timestamp, uid)
        if key in observed_branch_keys:
            raise RuntimeError("RTS-GMLC zero-DC duplicate branch flow key")
        observed_branch_keys.add(key)
        flows.setdefault(timestamp, {})[uid] = float(row["flow_mw"])
    if observed_branch_keys != expected_branch_keys:
        raise RuntimeError("RTS-GMLC zero-DC branch flow coverage drifted")

    _require_finite_fields(
        security_rows,
        _SECURITY_AUDIT_FINITE_FIELDS,
        label="security audit",
    )
    expected_security_keys = {
        (timestamp, state_id)
        for timestamp in expected_timestamps
        for state_id in expected_state_ids
    }
    observed_security_keys = {
        (str(row["timestamp"]), str(row["state_id"])) for row in security_rows
    }
    if (
        len(security_rows) != len(observed_security_keys)
        or observed_security_keys != expected_security_keys
    ):
        raise RuntimeError("RTS-GMLC zero-DC security audit coverage drifted")
    if any(
        abs(float(row["maximum_branch_rating_violation_mw"])) > tolerance_mw
        or abs(float(row["outaged_element_output_mw"])) > tolerance_mw
        for row in security_rows
    ):
        raise RuntimeError("RTS-GMLC zero-DC security audit violation drifted")

    nonnormal_state_ids = expected_state_ids[1:]
    _require_finite_fields(
        security_generator_rows,
        _SECURITY_GENERATOR_FINITE_FIELDS,
        label="security generator dispatch",
    )
    expected_security_generator_keys = {
        (timestamp, state_id, uid)
        for timestamp in expected_timestamps
        for state_id in nonnormal_state_ids
        for uid in generator_uids
    }
    observed_security_generator_keys = {
        (
            str(row["timestamp"]),
            str(row["state_id"]),
            str(row["generator_uid"]),
        )
        for row in security_generator_rows
    }
    if (
        len(security_generator_rows) != len(observed_security_generator_keys)
        or observed_security_generator_keys != expected_security_generator_keys
    ):
        raise RuntimeError("RTS-GMLC zero-DC security generator coverage drifted")

    _require_finite_fields(
        security_branch_rows,
        _SECURITY_BRANCH_FINITE_FIELDS,
        label="security branch flow",
    )
    expected_security_branch_keys = {
        (timestamp, state_id, uid)
        for timestamp in expected_timestamps
        for state_id in nonnormal_state_ids
        for uid in branch_uids
    }
    observed_security_branch_keys = {
        (
            str(row["timestamp"]),
            str(row["state_id"]),
            str(row["branch_uid"]),
        )
        for row in security_branch_rows
    }
    if (
        len(security_branch_rows) != len(observed_security_branch_keys)
        or observed_security_branch_keys != expected_security_branch_keys
    ):
        raise RuntimeError("RTS-GMLC zero-DC security branch coverage drifted")
    return generation, commitment, flows


def _load_zero_dispatch(
    context: _ControlContext,
    output_root: Path,
) -> tuple[
    list[dict[str, str]],
    dict[str, dict[str, float]],
    dict[str, dict[str, bool]],
    dict[str, dict[str, float]],
]:
    root = output_root / "dc_dispatch"
    summary = _load_json(root, "summary.json")
    if summary["input_contract_sha256"] != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC zero-DC dispatch input contract drifted")
    hourly = _csv_rows(root / "hourly_dispatch.csv")
    generation, commitment, flows = _validate_and_index_zero_dispatch(
        hourly_rows=hourly,
        generator_rows=_csv_rows(root / "generator_dispatch.csv"),
        branch_rows=_csv_rows(root / "normal_branch_flows.csv"),
        security_rows=_csv_rows(root / "security_audit.csv"),
        security_generator_rows=_csv_rows(root / "security_generator_dispatch.csv"),
        security_branch_rows=_csv_rows(root / "security_branch_flows.csv"),
        expected_timestamps=tuple(
            point.timestamp.isoformat() for point in context.zero_business.points
        ),
        expected_native_demand_mw=tuple(
            sum(point.demand_by_bus_mw.values())
            for point in context.scan.data.hourly_points[:24]
        ),
        generator_uids=frozenset(
            generator.uid for generator in context.scan.data.generators
        ),
        branch_uids=frozenset(branch.uid for branch in context.scan.data.branches),
        expected_state_ids=tuple(
            context.common_security["common_security_contract"]["state_ids"]
        ),
        tolerance_mw=float(_SOLVER["tolerance_mw"]),
    )
    return hourly, generation, commitment, flows


def _max_or_none(rows: list[dict[str, object]], field: str):
    values = [float(row[field]) for row in rows if row[field] is not None]
    return max(values, default=None)


def _min_or_none(rows: list[dict[str, object]], field: str):
    values = [float(row[field]) for row in rows if row[field] is not None]
    return min(values, default=None)


def _require_non_slack_pg_control(
    rows: Sequence[Mapping[str, object]],
    *,
    tolerance_mw: float,
) -> None:
    for row in rows:
        if not bool(row["converged"]):
            continue
        value = row["max_non_slack_pg_deviation_mw"]
        if (
            value is None
            or not math.isfinite(float(value))
            or float(value) > tolerance_mw
        ):
            raise RuntimeError("RTS-GMLC zero-DC AC retained non-slack PG drift")


def _require_ac_case_numerics(rows: Sequence[Mapping[str, object]]) -> None:
    _require_finite_fields(
        rows,
        _AC_FINITE_FIELDS,
        label="AC normal case",
        nullable_fields=_AC_NULLABLE_FINITE_FIELDS,
    )
    for row_index, row in enumerate(rows):
        if bool(row["converged"]) and any(
            row[field] is None for field in _AC_NULLABLE_FINITE_FIELDS
        ):
            raise RuntimeError(
                f"RTS-GMLC zero-DC converged AC case {row_index} is missing metrics"
            )


def run_ac_normal(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "ac_normal"
    if target.exists():
        summary = _load_json(target, "summary.json")
        if summary["input_contract_sha256"] != context.input_contract_sha256:
            raise RuntimeError("Published RTS-GMLC zero-DC AC result drifted")
        _load_zero_dispatch(context, output_root)
        dc_manifest = _sha256(output_root / "dc_dispatch" / "SHA256SUMS")
        if summary.get("dc_dispatch_manifest_sha256") != dc_manifest:
            raise RuntimeError("Published RTS-GMLC zero-DC AC/DC binding drifted")
        return summary

    hourly, generation, commitment, flows = _load_zero_dispatch(context, output_root)
    dc_manifest = _sha256(output_root / "dc_dispatch" / "SHA256SUMS")
    point_by_timestamp = {
        point.timestamp.isoformat(): point
        for point in context.ac.scan_context.business.points
    }
    rows: list[dict[str, object]] = []
    placeholder_bus = int(_ZERO_CONTROL["dc_bus_api_placeholder"])
    for hour_index, hourly_row in enumerate(hourly):
        timestamp = hourly_row["timestamp"]
        point = point_by_timestamp[timestamp]
        dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
            context.ac.scan_context.data,
            demand_by_bus_mw=point.demand_by_bus_mw,
            generation_mw=generation[timestamp],
            ac_branch_flows_mw=flows[timestamp],
            tolerance_mw=float(_SOLVER["tolerance_mw"]),
        )
        if abs(dc_flows["DC1"] - float(hourly_row["hvdc_dc1_flow_mw"])) > float(
            _SOLVER["tolerance_mw"]
        ):
            raise RuntimeError("RTS-GMLC zero-DC normal DC1 reconstruction drifted")
        configured = _configure_q_capable_voltage_control(
            context.ac.template,
            context.ac.scan_context.data,
            point,
            generation_mw=generation[timestamp],
            commitment=commitment[timestamp],
            dc_bus=placeholder_bus,
            data_center_power_mw=0.0,
            data_center_power_factor=float(
                _CASE_SCOPE["configured_power_factor_value"]
            ),
            dc_flows_mw=dc_flows,
        )
        generator = configured.case["gen"]
        online_at_reference = [
            row
            for row in range(len(generator))
            if generator[row, GEN_STATUS] > 0.0
            and int(generator[row, GEN_BUS]) == configured.reference_bus
        ]
        expected_reference_row = context.ac.template.generator_row_by_uid[
            configured.reference_generator_uid
        ]
        if online_at_reference != [expected_reference_row]:
            raise RuntimeError("RTS-GMLC zero-DC AC slack is not unambiguous")
        result = validate_rts_gmlc_ac_power_flow(
            context.ac.template,
            configured,
            branch_rating=str(_CASE_SCOPE["branch_rating"]),
            voltage_tolerance_pu=float(_POWER_FLOW["voltage_violation_tolerance_pu"]),
            power_tolerance=float(_POWER_FLOW["power_violation_tolerance"]),
            loading_tolerance=float(_POWER_FLOW["loading_tolerance"]),
        )
        rows.append(
            {
                "hour_index": hour_index,
                "timestamp": timestamp,
                "control_id": "zero_dc_reoptimized_common_selected_n1_dispatch",
                "zero_data_center": True,
                "poi_applicable": False,
                "dc_bus_api_placeholder": placeholder_bus,
                "power_factor_case": _CASE_SCOPE["power_factor_case"],
                "configured_power_factor_value": _CASE_SCOPE[
                    "configured_power_factor_value"
                ],
                "state_id": "normal",
                "branch_rating": _CASE_SCOPE["branch_rating"],
                "native_grid_demand_mw": float(hourly_row["native_grid_demand_mw"]),
                "data_center_power_mw": 0.0,
                "data_center_reactive_demand_mvar": (
                    configured.data_center_reactive_demand_mvar
                ),
                "native_reactive_demand_mvar": (configured.native_reactive_demand_mvar),
                "hvdc_dc1_flow_mw": dc_flows["DC1"],
                "dc_flow_reconstruction_residual_mw": residual,
                **asdict(result),
            }
        )
    if len(rows) != int(_CASE_SCOPE["expected_unique_ac_cases"]):
        raise RuntimeError("RTS-GMLC zero-DC AC case count drifted")
    if len({row["timestamp"] for row in rows}) != len(rows):
        raise RuntimeError("RTS-GMLC zero-DC AC contains duplicate cases")
    _require_ac_case_numerics(rows)
    _require_non_slack_pg_control(
        rows,
        tolerance_mw=float(_POWER_FLOW["non_slack_pg_audit_tolerance_mw"]),
    )
    converged = [row for row in rows if bool(row["converged"])]
    voltage_tolerance = float(_POWER_FLOW["voltage_violation_tolerance_pu"])
    power_tolerance = float(_POWER_FLOW["power_violation_tolerance"])
    loading_tolerance = float(_POWER_FLOW["loading_tolerance"])
    summary = {
        "schema": "rts_gmlc_zero_dc_normal_ac_control_results_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "dc_dispatch_manifest_sha256": dc_manifest,
        "case_count": len(rows),
        "expected_case_count": _CASE_SCOPE["expected_unique_ac_cases"],
        "all_cases_reported": len(rows) == _CASE_SCOPE["expected_unique_ac_cases"],
        "converged_case_count": len(converged),
        "secure_case_count": sum(bool(row["secure"]) for row in rows),
        "not_converged_case_count": len(rows) - len(converged),
        "voltage_violation_count": sum(
            float(row["max_voltage_violation_pu"] or 0.0) > voltage_tolerance
            for row in converged
        ),
        "branch_loading_violation_count": sum(
            float(row["max_branch_loading_fraction"] or 0.0) > 1.0 + loading_tolerance
            for row in converged
        ),
        "active_power_violation_count": sum(
            float(row["max_active_power_violation_mw"] or 0.0) > power_tolerance
            for row in converged
        ),
        "reactive_power_violation_count": sum(
            float(row["max_reactive_power_violation_mvar"] or 0.0) > power_tolerance
            for row in converged
        ),
        "minimum_voltage_pu": _min_or_none(converged, "min_voltage_pu"),
        "maximum_voltage_pu": _max_or_none(converged, "max_voltage_pu"),
        "maximum_voltage_violation_pu": _max_or_none(
            converged, "max_voltage_violation_pu"
        ),
        "maximum_branch_loading_fraction": _max_or_none(
            converged, "max_branch_loading_fraction"
        ),
        "maximum_active_power_violation_mw": _max_or_none(
            converged, "max_active_power_violation_mw"
        ),
        "maximum_reactive_power_violation_mvar": _max_or_none(
            converged, "max_reactive_power_violation_mvar"
        ),
        "maximum_non_slack_pg_deviation_mw": _max_or_none(
            converged, "max_non_slack_pg_deviation_mw"
        ),
        "non_slack_pg_audit_tolerance_mw": _POWER_FLOW[
            "non_slack_pg_audit_tolerance_mw"
        ],
        "all_converged_cases_pass_non_slack_pg_audit": True,
        "maximum_dc_flow_reconstruction_residual_mw": max(
            float(row["dc_flow_reconstruction_residual_mw"]) for row in rows
        ),
        "power_factor_not_applicable_at_zero_active_power": True,
        "poi_not_applicable_at_zero_injection": True,
        "q_capable_voltage_control_used": True,
        "direct_ac_replay_only": True,
        "q_limit_switching_used": False,
        "restoration_or_redispatch_used": False,
        **_EVIDENCE,
    }

    def writer(staging: Path) -> None:
        _write_csv(staging / "ac_normal_cases.csv", _AC_FIELDS, rows)
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_zero_dc_normal_ac_control.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("prepare", "run-dc", "run-ac", "all"),
        required=True,
    )
    args = parser.parse_args()
    if args.stage == "prepare":
        result = prepare_preregistration(args.config)
    elif args.stage == "run-dc":
        result = run_dc_dispatch(args.config)
    elif args.stage == "run-ac":
        result = run_ac_normal(args.config)
    else:
        prepare_preregistration(args.config)
        run_dc_dispatch(args.config)
        result = run_ac_normal(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
