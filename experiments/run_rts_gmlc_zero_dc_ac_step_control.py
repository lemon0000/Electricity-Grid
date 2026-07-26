"""Run the registered zero-DC PIPS-sc numerical feasibility diagnostic."""

from __future__ import annotations

import argparse
import csv
import importlib
import json
import math
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import yaml
from pypower.idx_brch import BR_STATUS, F_BUS, PF, PT, QF, QT, T_BUS
from pypower.idx_bus import BUS_I, BUS_TYPE, NONE, VA, VM
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PG, QG, VG

import experiments.run_rts_gmlc_zero_dc_ac_recovery as primary
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended import (
    _configure_q_capable_voltage_control,
)
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.grid.rts_gmlc_ac import reconstruct_rts_gmlc_dc_flows
from src.grid.rts_gmlc_ac_recovery import (
    AcRecoveryInput,
    _case_sha256,
    prepare_rts_gmlc_ac_recovery,
)
from src.grid.rts_gmlc_ac_step_control import (
    StepControlAudit,
    StepControlBranchRecord,
    StepControlBusRecord,
    StepControlGeneratorRecord,
    StepControlSolveResult,
    _FROZEN_AUDIT_TOLERANCES,
    _FROZEN_SOLVER_OPTIONS,
    audit_step_control_solution,
    solve_and_audit_step_control,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_step_control.yaml")
_CONFIG_SHA256 = "7dbc31112c41800e42fe9aa245a2749ae15dd5d41802ee209e194f0e1cc49576"
_PRIMARY_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_recovery.yaml")
_PRIMARY_RUNNER_PATH = Path("experiments/run_rts_gmlc_zero_dc_ac_recovery.py")
_PRIMARY_CORE_PATH = Path("src/grid/rts_gmlc_ac_recovery.py")
_PRIMARY_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_recovery_v1"
)
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_zero_dc_ac_step_control.py"),
    Path("src/grid/rts_gmlc_ac_step_control.py"),
)
_SOURCE_MODULES = {
    "pipsopf_solver.py": "pypower.pipsopf_solver",
    "pips.py": "pypower.pips",
    "opf_execute.py": "pypower.opf_execute",
    "makeYbus.py": "pypower.makeYbus",
}
_EXPECTED_HOURS = 24
_MODE = "distributed_committable"
_CSV_ABSOLUTE_TOLERANCE = 1.0e-10
_CSV_RELATIVE_TOLERANCE = 1.0e-12


@dataclass(frozen=True)
class _StepCase:
    hour_index: int
    timestamp: str
    dc_bus_api_placeholder: int
    native_grid_demand_mw: float
    native_reactive_demand_mvar: float
    hvdc_dc1_flow_mw: float
    dc_flow_reconstruction_residual_mw: float
    target_generation_sha256: str
    adjustable_generator_rows_sha256: str
    prepared: AcRecoveryInput


@dataclass(frozen=True)
class _StepContext:
    config_path: Path
    config: dict[str, Any]
    primary_context: Any
    primary_summary: dict[str, Any]
    primary_recovered_timestamps: frozenset[str]
    cases: tuple[_StepCase, ...]
    output_root: Path
    input_contract: dict[str, Any]
    input_contract_sha256: str


_SOLVE_FIELDS = tuple(
    field.name for field in fields(StepControlSolveResult) if field.name != "audit"
)
_AUDIT_FIELDS = tuple(
    field.name
    for field in fields(StepControlAudit)
    if field.name not in {"generator_records", "bus_records", "branch_records"}
)
_CASE_PREFIX_FIELDS = (
    "hour_index",
    "timestamp",
    "mode",
    "state_id",
    "zero_data_center",
    "dc_bus_api_placeholder",
    "reference_bus",
    "reference_generator_uid",
    "active_power_envelope",
    "adjustable_generator_count",
    "fixed_generator_count",
    "source_case_sha256",
    "recovery_case_sha256",
    "target_generation_sha256",
    "adjustable_generator_rows_sha256",
    "native_grid_demand_mw",
    "native_reactive_demand_mvar",
    "hvdc_dc1_flow_mw",
    "dc_flow_reconstruction_residual_mw",
)
_CASE_FIELDS = _CASE_PREFIX_FIELDS + _SOLVE_FIELDS + _AUDIT_FIELDS
_GENERATOR_FIELDS = ("hour_index", "timestamp", "mode") + tuple(
    field.name for field in fields(StepControlGeneratorRecord)
)
_BUS_FIELDS = ("hour_index", "timestamp", "mode") + tuple(
    field.name for field in fields(StepControlBusRecord)
)
_BRANCH_FIELDS = ("hour_index", "timestamp", "mode") + tuple(
    field.name for field in fields(StepControlBranchRecord)
)


def _read_config(config_path: Path) -> dict[str, Any]:
    if _sha256(config_path) != _CONFIG_SHA256:
        raise ValueError("RTS-GMLC zero-DC step-control config SHA-256 drifted")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    required = {
        "preregistration",
        "parent_primary_recovery",
        "observed_outcomes_disclosure",
        "case_scope",
        "numerical_protocol",
        "solver_options",
        "solver_source_sha256",
        "postsolve_audit",
        "interpretation",
        "evidence",
        "output",
    }
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("RTS-GMLC zero-DC step-control config schema drifted")
    preregistration = config["preregistration"]
    if (
        preregistration.get("id") != "rts_gmlc_google_day0_zero_dc_ac_step_control_v1"
        or preregistration.get("schema")
        != "rts_gmlc_zero_dc_ac_step_control_preregistration_v1"
        or preregistration.get("formal_zero_step_control_outcomes_observed")
        is not False
        or preregistration.get("all_24_formal_step_control_cases_blind") is not True
    ):
        raise ValueError("RTS-GMLC zero-DC step-control preregistration drifted")
    if config["solver_options"] != _FROZEN_SOLVER_OPTIONS:
        raise ValueError("RTS-GMLC zero-DC step-control solver options drifted")
    audit = config["postsolve_audit"]
    if {
        key: audit.get(key) for key in _FROZEN_AUDIT_TOLERANCES
    } != _FROZEN_AUDIT_TOLERANCES:
        raise ValueError("RTS-GMLC zero-DC step-control audit tolerances drifted")
    scope = config["case_scope"]
    if (
        scope.get("mode") != _MODE
        or scope.get("expected_hours") != _EXPECTED_HOURS
        or scope.get("expected_unique_cases") != _EXPECTED_HOURS
        or scope.get("per_hour_method_selection") is not False
    ):
        raise ValueError("RTS-GMLC zero-DC step-control case scope drifted")
    protocol = config["numerical_protocol"]
    if (
        protocol.get("opf_alg") != 565
        or protocol.get("exactly_one_solver_call_per_case") is not True
        or protocol.get("retry_allowed") is not False
        or protocol.get("fallback_allowed") is not False
        or protocol.get("candidate_pg_lock_or_second_opf_used") is not False
        or protocol.get("original_prepared_case_used_unchanged") is not True
    ):
        raise ValueError("RTS-GMLC zero-DC step-control protocol drifted")
    if config["output"] != {
        "directory": "results/tables/rts_gmlc_google_day0_zero_dc_ac_step_control_v1"
    }:
        raise ValueError("RTS-GMLC zero-DC step-control output drifted")
    return config


def _source_hashes() -> dict[str, str]:
    observed = {}
    for filename, module_name in _SOURCE_MODULES.items():
        module = importlib.import_module(module_name)
        path = Path(module.__file__ or "")
        if not path.is_file():
            raise RuntimeError(f"Cannot locate frozen PYPOWER source {module_name}")
        observed[filename] = _sha256(path)
    return observed


def _hash_float64(values: Sequence[float], *, label: str) -> str:
    digest = sha256()
    digest.update(label.encode("ascii"))
    digest.update(np.ascontiguousarray(values, dtype=np.float64).tobytes())
    return digest.hexdigest()


def _hash_int64(values: Sequence[int], *, label: str) -> str:
    digest = sha256()
    digest.update(label.encode("ascii"))
    digest.update(np.ascontiguousarray(values, dtype=np.int64).tobytes())
    return digest.hexdigest()


def _load_primary(config: Mapping[str, Any]):
    parent = config["parent_primary_recovery"]
    if (
        Path(parent["config_path"]) != _PRIMARY_CONFIG_PATH
        or _sha256(_PRIMARY_CONFIG_PATH) != parent["config_sha256"]
        or Path(parent["implementation_path"]) != _PRIMARY_RUNNER_PATH
        or _sha256(_PRIMARY_RUNNER_PATH) != parent["implementation_sha256"]
        or Path(parent["core_path"]) != _PRIMARY_CORE_PATH
        or _sha256(_PRIMARY_CORE_PATH) != parent["core_sha256"]
        or Path(parent["output_directory"]) != _PRIMARY_OUTPUT_ROOT
    ):
        raise RuntimeError(
            "RTS-GMLC zero-DC step-control parent implementation drifted"
        )
    for subdirectory, key in (
        ("preregistration", "preregistration_manifest_sha256"),
        ("recovery", "recovery_manifest_sha256"),
    ):
        target = _PRIMARY_OUTPUT_ROOT / subdirectory
        _verify_output_manifest(target)
        if _sha256(target / "SHA256SUMS") != parent[key]:
            raise RuntimeError(
                f"RTS-GMLC zero-DC step-control parent {subdirectory} drifted"
            )
    context = primary._build_context(_PRIMARY_CONFIG_PATH)
    registration = primary._require_preregistration(context, _PRIMARY_OUTPUT_ROOT)
    summary = primary._load_results(
        context, _PRIMARY_OUTPUT_ROOT / "recovery", registration
    )
    if context.input_contract_sha256 != parent["input_contract_sha256"]:
        raise RuntimeError(
            "RTS-GMLC zero-DC step-control parent input contract drifted"
        )
    return context, summary


def _validate_prepared_case(prepared: AcRecoveryInput) -> None:
    if prepared.mode != _MODE or not prepared.fixed_inputs_preserved:
        raise RuntimeError("RTS-GMLC zero-DC step-control prepared mode drifted")
    if prepared.recovery_case_sha256 != _case_sha256(prepared.case):
        raise RuntimeError("RTS-GMLC zero-DC step-control prepared hash drifted")
    bus = np.asarray(prepared.case["bus"], dtype=float)
    generator = np.asarray(prepared.case["gen"], dtype=float)
    branch = np.asarray(prepared.case["branch"], dtype=float)
    bus_ids = bus[:, BUS_I].astype(np.int64)
    if (
        not np.array_equal(bus[:, BUS_I], bus_ids)
        or len(set(bus_ids.tolist())) != len(bus_ids)
        or np.any(bus[:, BUS_TYPE] == NONE)
        or not np.all(np.isin(generator[:, GEN_STATUS], (0.0, 1.0)))
        or not np.all(np.isin(branch[:, BR_STATUS], (0.0, 1.0)))
    ):
        raise RuntimeError("RTS-GMLC zero-DC step-control topology contract drifted")
    known = set(bus_ids.tolist())
    endpoints = np.concatenate(
        (generator[:, GEN_BUS], branch[:, F_BUS], branch[:, T_BUS])
    )
    if not np.array_equal(endpoints, endpoints.astype(np.int64)) or any(
        int(value) not in known for value in endpoints
    ):
        raise RuntimeError("RTS-GMLC zero-DC step-control element mapping drifted")


def _build_cases(
    context: Any,
    primary_rows: Mapping[str, Mapping[str, str]],
) -> tuple[_StepCase, ...]:
    hourly, generation, commitment, flows = primary._load_zero_dispatch(
        context.zero, primary._ZERO_OUTPUT_ROOT
    )
    point_by_timestamp = {
        point.timestamp.isoformat(): point
        for point in context.zero.ac.scan_context.business.points
    }
    placeholder_bus = int(context.zero.config["zero_control"]["dc_bus_api_placeholder"])
    dc_tolerance_mw = float(context.zero.config["solver"]["tolerance_mw"])
    cases = []
    for hour_index, hourly_row in enumerate(hourly):
        timestamp = str(hourly_row["timestamp"])
        point = point_by_timestamp[timestamp]
        dc_flows, residual = reconstruct_rts_gmlc_dc_flows(
            context.zero.ac.scan_context.data,
            demand_by_bus_mw=point.demand_by_bus_mw,
            generation_mw=generation[timestamp],
            ac_branch_flows_mw=flows[timestamp],
            tolerance_mw=dc_tolerance_mw,
        )
        if (
            abs(dc_flows["DC1"] - float(hourly_row["hvdc_dc1_flow_mw"]))
            > dc_tolerance_mw
        ):
            raise RuntimeError(
                "RTS-GMLC zero-DC step-control DC1 reconstruction drifted"
            )
        configured = _configure_q_capable_voltage_control(
            context.zero.ac.template,
            context.zero.ac.scan_context.data,
            point,
            generation_mw=generation[timestamp],
            commitment=commitment[timestamp],
            dc_bus=placeholder_bus,
            data_center_power_mw=0.0,
            data_center_power_factor=1.0,
            dc_flows_mw=dc_flows,
        )
        prepared = prepare_rts_gmlc_ac_recovery(
            configured,
            context.zero.ac.template,
            context.zero.ac.scan_context.data,
            mode=_MODE,
            voltage_limits_pu=tuple(context.config["ac_opf"]["voltage_limits_pu"]),
        )
        _validate_prepared_case(prepared)
        parent_row = primary_rows[timestamp]
        if (
            int(parent_row["hour_index"]) != hour_index
            or parent_row["source_case_sha256"] != prepared.source_case_sha256
            or parent_row["recovery_case_sha256"] != prepared.recovery_case_sha256
        ):
            raise RuntimeError(
                "RTS-GMLC zero-DC step-control parent case identity drifted"
            )
        cases.append(
            _StepCase(
                hour_index=hour_index,
                timestamp=timestamp,
                dc_bus_api_placeholder=placeholder_bus,
                native_grid_demand_mw=float(hourly_row["native_grid_demand_mw"]),
                native_reactive_demand_mvar=float(
                    configured.native_reactive_demand_mvar
                ),
                hvdc_dc1_flow_mw=float(dc_flows["DC1"]),
                dc_flow_reconstruction_residual_mw=float(residual),
                target_generation_sha256=_hash_float64(
                    prepared.target_generation_mw_by_row,
                    label="target_generation_mw_by_row_v1",
                ),
                adjustable_generator_rows_sha256=_hash_int64(
                    prepared.adjustable_generator_rows,
                    label="adjustable_generator_rows_v1",
                ),
                prepared=prepared,
            )
        )
    if len(cases) != _EXPECTED_HOURS or [case.hour_index for case in cases] != list(
        range(_EXPECTED_HOURS)
    ):
        raise RuntimeError("RTS-GMLC zero-DC step-control hour coverage drifted")
    return tuple(cases)


def _case_contract(case: _StepCase) -> dict[str, object]:
    prepared = case.prepared
    return {
        "hour_index": case.hour_index,
        "timestamp": case.timestamp,
        "source_case_sha256": prepared.source_case_sha256,
        "recovery_case_sha256": prepared.recovery_case_sha256,
        "target_generation_sha256": case.target_generation_sha256,
        "adjustable_generator_rows_sha256": case.adjustable_generator_rows_sha256,
        "adjustable_generator_count": len(prepared.adjustable_generator_rows),
        "fixed_generator_count": len(prepared.fixed_generator_rows),
        "generator_count": len(prepared.generator_uid_by_row),
        "bus_count": len(prepared.case["bus"]),
        "branch_count": len(prepared.branch_uid_by_row),
        "reference_bus": prepared.reference_bus,
        "reference_generator_uid": prepared.reference_generator_uid,
    }


def _build_context(config_path: Path) -> _StepContext:
    config = _read_config(config_path)
    actual_source_hashes = _source_hashes()
    if actual_source_hashes != config["solver_source_sha256"]:
        raise RuntimeError("RTS-GMLC zero-DC step-control PYPOWER source drifted")
    primary_context, primary_summary = _load_primary(config)
    rows = primary._csv_rows(
        _PRIMARY_OUTPUT_ROOT / "recovery" / "recovery_cases.csv",
        primary._CASE_FIELDS,
    )
    distributed = {row["timestamp"]: row for row in rows if row["mode"] == _MODE}
    if len(distributed) != _EXPECTED_HOURS:
        raise RuntimeError("RTS-GMLC zero-DC step-control primary coverage drifted")
    recovered = frozenset(
        timestamp
        for timestamp, row in distributed.items()
        if primary._parse_bool(row["recovered"], label="primary recovered")
    )
    observed = config["observed_outcomes_disclosure"]
    failed = sorted(set(distributed) - recovered)
    if (
        primary_summary["mode_summaries"][_MODE]["recovered_count"]
        != observed["primary_witnessed_count"]
        or len(recovered) != observed["primary_witnessed_count"]
        or failed != sorted(observed["primary_failed_timestamps"])
        or [int(distributed[timestamp]["hour_index"]) for timestamp in failed]
        != observed["primary_failed_hour_indices"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC step-control observed outcomes drifted")
    cases = _build_cases(primary_context, distributed)
    contract = {
        "schema": "rts_gmlc_zero_dc_ac_step_control_inputs_v1",
        "config_sha256": _sha256(config_path),
        "parent_primary_recovery": config["parent_primary_recovery"],
        "observed_outcomes_disclosure": observed,
        "case_scope": config["case_scope"],
        "numerical_protocol": config["numerical_protocol"],
        "solver_options": config["solver_options"],
        "solver_source_sha256": actual_source_hashes,
        "postsolve_audit": config["postsolve_audit"],
        "interpretation": config["interpretation"],
        "case_contracts": [_case_contract(case) for case in cases],
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "software_versions": primary._software_versions(),
        "evidence": config["evidence"],
    }
    return _StepContext(
        config_path=config_path,
        config=config,
        primary_context=primary_context,
        primary_summary=primary_summary,
        primary_recovered_timestamps=recovered,
        cases=cases,
        output_root=Path(config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: _StepContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC step-control artifact {root / name} drifted")
    return payload


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    target = output_root / "preregistration"
    preregistration = context.config["preregistration"]
    payload = {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "primary_zero_recovery_outcomes_observed": True,
        "formal_zero_step_control_outcomes_observed": False,
        "all_24_formal_step_control_cases_blind": True,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published step-control registration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published step-control config snapshot drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare beside existing step-control artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _StepContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    registration = _load_json(target, "registration.json")
    if registration.get("input_contract") != _stable_json(context.input_contract):
        raise RuntimeError("RTS-GMLC step-control live inputs drifted")
    if registration.get("input_contract_sha256") != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC step-control input contract SHA drifted")
    if (target / "config.yaml").read_bytes() != context.config_path.read_bytes():
        raise RuntimeError("RTS-GMLC step-control live config drifted")
    return registration


def _format_value(value: object) -> str:
    if isinstance(value, (bool, np.bool_)):
        return str(bool(value)).lower()
    if isinstance(value, (float, np.floating)):
        return format(float(value), ".17g")
    if value is None:
        return ""
    return str(value)


def _write_csv(
    path: Path, fieldnames: tuple[str, ...], rows: Sequence[Mapping[str, object]]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row[field]) for field in fieldnames})


def _csv_rows(path: Path, fieldnames: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != fieldnames:
            raise RuntimeError(f"RTS-GMLC step-control CSV schema drifted: {path}")
        return list(reader)


def _parse_bool(value: object, *, label: str) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    normalized = str(value).strip().lower()
    if normalized not in {"true", "false"}:
        raise RuntimeError(f"RTS-GMLC step-control {label} is not boolean")
    return normalized == "true"


def _finite(value: object, *, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(f"RTS-GMLC step-control {label} is not numeric") from error
    if not math.isfinite(parsed):
        raise RuntimeError(f"RTS-GMLC step-control {label} is non-finite")
    return parsed


def _integer(value: object, *, label: str) -> int:
    parsed = _finite(value, label=label)
    integer = int(parsed)
    if parsed != integer:
        raise RuntimeError(f"RTS-GMLC step-control {label} is not an integer")
    return integer


def _empty(value: object) -> bool:
    return value is None or str(value) == ""


def _assert_serialized(value: object, expected: object, *, label: str) -> None:
    if isinstance(expected, bool):
        if _parse_bool(value, label=label) != expected:
            raise RuntimeError(f"RTS-GMLC step-control {label} drifted")
    elif isinstance(expected, int):
        if _integer(value, label=label) != expected:
            raise RuntimeError(f"RTS-GMLC step-control {label} drifted")
    elif isinstance(expected, float):
        observed = _finite(value, label=label)
        if not math.isclose(
            observed,
            expected,
            rel_tol=_CSV_RELATIVE_TOLERANCE,
            abs_tol=_CSV_ABSOLUTE_TOLERANCE,
        ):
            raise RuntimeError(f"RTS-GMLC step-control {label} drifted")
    elif expected is None:
        if not _empty(value):
            raise RuntimeError(f"RTS-GMLC step-control {label} drifted")
    elif str(value) != str(expected):
        raise RuntimeError(f"RTS-GMLC step-control {label} drifted")


def _flatten_result(result: StepControlSolveResult) -> dict[str, object]:
    payload = asdict(result)
    audit = payload.pop("audit")
    if audit is None:
        payload.update({field: None for field in _AUDIT_FIELDS})
    else:
        for records in ("generator_records", "bus_records", "branch_records"):
            audit.pop(records)
        payload.update(audit)
    return payload


def _case_row(case: _StepCase, result: StepControlSolveResult) -> dict[str, object]:
    prepared = case.prepared
    return {
        "hour_index": case.hour_index,
        "timestamp": case.timestamp,
        "mode": _MODE,
        "state_id": "normal",
        "zero_data_center": True,
        "dc_bus_api_placeholder": case.dc_bus_api_placeholder,
        "reference_bus": prepared.reference_bus,
        "reference_generator_uid": prepared.reference_generator_uid,
        "active_power_envelope": prepared.active_power_envelope,
        "adjustable_generator_count": len(prepared.adjustable_generator_rows),
        "fixed_generator_count": len(prepared.fixed_generator_rows),
        "source_case_sha256": prepared.source_case_sha256,
        "recovery_case_sha256": prepared.recovery_case_sha256,
        "target_generation_sha256": case.target_generation_sha256,
        "adjustable_generator_rows_sha256": case.adjustable_generator_rows_sha256,
        "native_grid_demand_mw": case.native_grid_demand_mw,
        "native_reactive_demand_mvar": case.native_reactive_demand_mvar,
        "hvdc_dc1_flow_mw": case.hvdc_dc1_flow_mw,
        "dc_flow_reconstruction_residual_mw": case.dc_flow_reconstruction_residual_mw,
        **_flatten_result(result),
    }


def _detail_rows(case: _StepCase, result: StepControlSolveResult):
    if result.audit is None:
        return [], [], []
    prefix = {
        "hour_index": case.hour_index,
        "timestamp": case.timestamp,
        "mode": _MODE,
    }
    return (
        [{**prefix, **asdict(record)} for record in result.audit.generator_records],
        [{**prefix, **asdict(record)} for record in result.audit.bus_records],
        [{**prefix, **asdict(record)} for record in result.audit.branch_records],
    )


def _reconstruct_audit(
    case: _StepCase,
    case_row: Mapping[str, object],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
) -> StepControlAudit:
    prepared = case.prepared
    source_bus = np.asarray(prepared.case["bus"], dtype=float)
    source_generator = np.asarray(prepared.case["gen"], dtype=float)
    source_branch = np.asarray(prepared.case["branch"], dtype=float)
    if (
        len(generator_rows) != len(source_generator)
        or len(bus_rows) != len(source_bus)
        or len(branch_rows) != len(source_branch)
    ):
        raise RuntimeError("RTS-GMLC step-control detail coverage drifted")
    generator_rows = sorted(
        generator_rows,
        key=lambda row: _integer(row["generator_row"], label="generator_row"),
    )
    bus_rows = sorted(
        bus_rows, key=lambda row: _integer(row["bus_row"], label="bus_row")
    )
    branch_rows = sorted(
        branch_rows, key=lambda row: _integer(row["branch_row"], label="branch_row")
    )
    bus = np.array(source_bus, copy=True)
    generator = np.array(source_generator, copy=True)
    branch = np.zeros((len(source_branch), max(source_branch.shape[1], QT + 1)))
    branch[:, : source_branch.shape[1]] = source_branch
    for row_index, row in enumerate(bus_rows):
        if _integer(row["bus_row"], label="bus_row") != row_index:
            raise RuntimeError("RTS-GMLC step-control bus row ordering drifted")
        bus[row_index, VM] = _finite(row["vm_pu"], label="vm_pu")
        bus[row_index, VA] = _finite(row["va_degree"], label="va_degree")
    for row_index, row in enumerate(generator_rows):
        if _integer(row["generator_row"], label="generator_row") != row_index:
            raise RuntimeError("RTS-GMLC step-control generator row ordering drifted")
        generator[row_index, PG] = _finite(row["pg_mw"], label="pg_mw")
        generator[row_index, QG] = _finite(row["qg_mvar"], label="qg_mvar")
        generator[row_index, VG] = _finite(row["output_vg_pu"], label="output_vg_pu")
    for row_index, row in enumerate(branch_rows):
        if _integer(row["branch_row"], label="branch_row") != row_index:
            raise RuntimeError("RTS-GMLC step-control branch row ordering drifted")
        for column, field in (
            (PF, "returned_pf_mw"),
            (QF, "returned_qf_mvar"),
            (PT, "returned_pt_mw"),
            (QT, "returned_qt_mvar"),
        ):
            branch[row_index, column] = _finite(row[field], label=field)
    solved = {
        "bus": bus,
        "gen": generator,
        "branch": branch,
        "gencost": deepcopy(prepared.case["gencost"]),
    }
    return audit_step_control_solution(
        prepared,
        solved,
        solver_objective_mw2=_finite(
            case_row["solver_objective_mw2"], label="solver_objective_mw2"
        ),
        audit_tolerances=_FROZEN_AUDIT_TOLERANCES,
    )


def _validate_result_rows(
    context: _StepContext,
    case_rows: Sequence[Mapping[str, object]],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
) -> None:
    expected = {case.timestamp: case for case in context.cases}
    observed = {str(row["timestamp"]): row for row in case_rows}
    if len(case_rows) != _EXPECTED_HOURS or set(observed) != set(expected):
        raise RuntimeError("RTS-GMLC step-control result coverage drifted")
    if len(observed) != len(case_rows):
        raise RuntimeError("RTS-GMLC step-control duplicate case identity")

    details_by_timestamp = []
    for rows in (generator_rows, bus_rows, branch_rows):
        grouped: dict[str, list[Mapping[str, object]]] = {}
        for row in rows:
            timestamp = str(row["timestamp"])
            if timestamp not in expected or str(row["mode"]) != _MODE:
                raise RuntimeError("RTS-GMLC step-control detail identity drifted")
            grouped.setdefault(timestamp, []).append(row)
        details_by_timestamp.append(grouped)

    for timestamp, case in expected.items():
        row = observed[timestamp]
        prefix_expected = _case_row(
            case,
            StepControlSolveResult(
                evaluated=False,
                solver_success=False,
                feasibility_witnessed=False,
                status="solver_invocation_exception_no_witness",
                solver_error_type="placeholder",
                solver_error_message="placeholder",
                solver_algorithm=565,
                solver_reported_algorithm=None,
                solver_elapsed_seconds=None,
                solver_iterations=None,
                solver_message=None,
                solver_final_feasibility_condition=None,
                solver_final_gradient_condition=None,
                solver_final_complementarity_condition=None,
                solver_final_cost_condition=None,
                solver_input_case_unchanged=True,
                recovery_input_fixed_fields_preserved=True,
                audit=None,
            ),
        )
        for field in _CASE_PREFIX_FIELDS:
            _assert_serialized(row[field], prefix_expected[field], label=field)
        evaluated = _parse_bool(row["evaluated"], label="evaluated")
        solver_success = _parse_bool(row["solver_success"], label="solver_success")
        witnessed = _parse_bool(
            row["feasibility_witnessed"], label="feasibility_witnessed"
        )
        if _integer(row["solver_algorithm"], label="solver_algorithm") != 565:
            raise RuntimeError("RTS-GMLC step-control algorithm drifted")
        if not _parse_bool(
            row["solver_input_case_unchanged"], label="solver_input_case_unchanged"
        ) or not _parse_bool(
            row["recovery_input_fixed_fields_preserved"],
            label="recovery_input_fixed_fields_preserved",
        ):
            raise RuntimeError("RTS-GMLC step-control input immutability audit failed")

        generator_detail = details_by_timestamp[0].get(timestamp, [])
        bus_detail = details_by_timestamp[1].get(timestamp, [])
        branch_detail = details_by_timestamp[2].get(timestamp, [])
        if not solver_success:
            if witnessed or any((generator_detail, bus_detail, branch_detail)):
                raise RuntimeError("RTS-GMLC step-control failure state drifted")
            if any(not _empty(row[field]) for field in _AUDIT_FIELDS):
                raise RuntimeError(
                    "RTS-GMLC step-control failed case contains audit data"
                )
            if evaluated:
                if (
                    str(row["status"])
                    != "not_witnessed_by_registered_step_control_pipeline"
                ):
                    raise RuntimeError(
                        "RTS-GMLC step-control solver failure label drifted"
                    )
                if not _empty(row["solver_error_type"]) or not _empty(
                    row["solver_error_message"]
                ):
                    raise RuntimeError(
                        "RTS-GMLC step-control solver failure error drifted"
                    )
                for field in (
                    "solver_reported_algorithm",
                    "solver_elapsed_seconds",
                    "solver_iterations",
                    "solver_final_feasibility_condition",
                    "solver_final_gradient_condition",
                    "solver_final_complementarity_condition",
                    "solver_final_cost_condition",
                ):
                    _finite(row[field], label=field)
                if _integer(
                    row["solver_reported_algorithm"], label="solver_reported_algorithm"
                ) != 565 or _empty(row["solver_message"]):
                    raise RuntimeError(
                        "RTS-GMLC step-control solver diagnostics drifted"
                    )
            else:
                if str(row["status"]) != "solver_invocation_exception_no_witness":
                    raise RuntimeError("RTS-GMLC step-control invocation label drifted")
                if _empty(row["solver_error_type"]) or _empty(
                    row["solver_error_message"]
                ):
                    raise RuntimeError("RTS-GMLC step-control invocation error omitted")
            continue

        if (
            not evaluated
            or _integer(
                row["solver_reported_algorithm"], label="solver_reported_algorithm"
            )
            != 565
        ):
            raise RuntimeError("RTS-GMLC step-control success diagnostics drifted")
        if not _empty(row["solver_error_type"]) or not _empty(
            row["solver_error_message"]
        ):
            raise RuntimeError("RTS-GMLC step-control successful case contains error")
        for field in (
            "solver_elapsed_seconds",
            "solver_iterations",
            "solver_final_feasibility_condition",
            "solver_final_gradient_condition",
            "solver_final_complementarity_condition",
            "solver_final_cost_condition",
        ):
            _finite(row[field], label=field)
        audit = _reconstruct_audit(
            case, row, generator_detail, bus_detail, branch_detail
        )
        audit_payload = asdict(audit)
        expected_generator_records = audit_payload.pop("generator_records")
        expected_bus_records = audit_payload.pop("bus_records")
        expected_branch_records = audit_payload.pop("branch_records")
        for field, value in audit_payload.items():
            _assert_serialized(row[field], value, label=field)
        for records, expected_records, key_field in (
            (generator_detail, expected_generator_records, "generator_row"),
            (bus_detail, expected_bus_records, "bus_row"),
            (branch_detail, expected_branch_records, "branch_row"),
        ):
            ordered = sorted(
                records, key=lambda item: _integer(item[key_field], label=key_field)
            )
            for persisted, expected_record in zip(
                ordered, expected_records, strict=True
            ):
                for field, value in expected_record.items():
                    _assert_serialized(persisted[field], value, label=field)
        audit_passed = audit.postsolve_network_equation_reconstruction_audit_passed
        if witnessed != audit_passed:
            raise RuntimeError("RTS-GMLC step-control witness status drifted")
        expected_status = (
            "audited_numerical_feasibility_witness"
            if witnessed
            else "solver_success_postsolve_audit_failed"
        )
        if str(row["status"]) != expected_status:
            raise RuntimeError("RTS-GMLC step-control success label drifted")


def _run_cases(context: _StepContext):
    case_rows = []
    generator_rows = []
    bus_rows = []
    branch_rows = []
    audit_tolerances = {
        key: context.config["postsolve_audit"][key] for key in _FROZEN_AUDIT_TOLERANCES
    }
    for case in context.cases:
        result = solve_and_audit_step_control(
            case.prepared,
            solver_options=context.config["solver_options"],
            audit_tolerances=audit_tolerances,
        )
        case_rows.append(_case_row(case, result))
        generator, bus, branch = _detail_rows(case, result)
        generator_rows.extend(generator)
        bus_rows.extend(bus)
        branch_rows.extend(branch)
    _validate_result_rows(context, case_rows, generator_rows, bus_rows, branch_rows)
    return case_rows, generator_rows, bus_rows, branch_rows


def _max_witness_metric(
    rows: Sequence[Mapping[str, object]], field: str
) -> float | None:
    values = [
        _finite(row[field], label=field)
        for row in rows
        if _parse_bool(row["feasibility_witnessed"], label="feasibility_witnessed")
    ]
    return max(values, default=None)


def _summary(
    context: _StepContext,
    registration: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    witnessed = frozenset(
        str(row["timestamp"])
        for row in case_rows
        if _parse_bool(row["feasibility_witnessed"], label="feasibility_witnessed")
    )
    solver_success_count = sum(
        _parse_bool(row["solver_success"], label="solver_success") for row in case_rows
    )
    invocation_exception_count = sum(
        not _parse_bool(row["evaluated"], label="evaluated") for row in case_rows
    )
    audit_failed_count = sum(
        _parse_bool(row["solver_success"], label="solver_success")
        and not _parse_bool(row["feasibility_witnessed"], label="feasibility_witnessed")
        for row in case_rows
    )
    portfolio = witnessed | context.primary_recovered_timestamps
    all_step = len(witnessed) == _EXPECTED_HOURS
    all_portfolio = len(portfolio) == _EXPECTED_HOURS
    return {
        "schema": "rts_gmlc_zero_dc_ac_step_control_results_v1",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "parent_primary_recovery_manifest_sha256": context.config[
            "parent_primary_recovery"
        ]["recovery_manifest_sha256"],
        "case_count": len(case_rows),
        "expected_case_count": _EXPECTED_HOURS,
        "all_cases_reported": len(case_rows) == _EXPECTED_HOURS,
        "solver_invocation_exception_count": invocation_exception_count,
        "solver_success_count": solver_success_count,
        "solver_returned_failure_count": len(case_rows)
        - invocation_exception_count
        - solver_success_count,
        "solver_success_postsolve_audit_failed_count": audit_failed_count,
        "step_control_feasibility_witness_count": len(witnessed),
        "step_control_not_witnessed_count": _EXPECTED_HOURS - len(witnessed),
        "step_control_not_witnessed_timestamps": sorted(
            set(case.timestamp for case in context.cases) - witnessed
        ),
        "primary_direct_560_witness_count": len(context.primary_recovered_timestamps),
        "primary_step_control_witness_intersection_count": len(
            witnessed & context.primary_recovered_timestamps
        ),
        "primary_step_control_witness_union_count": len(portfolio),
        "portfolio_not_witnessed_timestamps": sorted(
            set(case.timestamp for case in context.cases) - portfolio
        ),
        "all_24_witnessed_by_registered_step_control": all_step,
        "all_24_witnessed_by_preregistered_solver_portfolio": all_portfolio,
        "treatment_followup_existence_gate_passed": all_step,
        "treatment_followup_gate_interpretation": (
            "distributed_envelope_numerical_existence_only"
        ),
        "primary_minimum_common_recovery_mode": context.primary_summary[
            "minimum_common_recovery_mode"
        ],
        "primary_minimum_common_recovery_mode_rewritten": False,
        "per_hour_method_or_parameter_selection_used": False,
        "exactly_one_step_control_call_per_case": True,
        "retry_or_fallback_used": False,
        "independent_solver_claimed": False,
        "global_or_minimum_optimality_claimed": False,
        "solver_failure_does_not_prove_infeasibility": True,
        "maximum_active_power_bound_violation_mw": _max_witness_metric(
            case_rows, "max_active_power_bound_violation_mw"
        ),
        "maximum_reactive_power_bound_violation_mvar": _max_witness_metric(
            case_rows, "max_reactive_power_bound_violation_mvar"
        ),
        "maximum_voltage_violation_pu": _max_witness_metric(
            case_rows, "max_voltage_violation_pu"
        ),
        "maximum_branch_loading_fraction": _max_witness_metric(
            case_rows, "max_branch_loading_fraction"
        ),
        "maximum_branch_angle_violation_degree": _max_witness_metric(
            case_rows, "max_branch_angle_violation_degree"
        ),
        "maximum_fixed_pg_deviation_mw": _max_witness_metric(
            case_rows, "max_fixed_pg_deviation_mw"
        ),
        "maximum_p_balance_residual_mw": _max_witness_metric(
            case_rows, "max_p_balance_residual_mw"
        ),
        "maximum_q_balance_residual_mvar": _max_witness_metric(
            case_rows, "max_q_balance_residual_mvar"
        ),
        "maximum_ybus_terminal_shunt_identity_mismatch_mva": _max_witness_metric(
            case_rows, "max_ybus_terminal_shunt_identity_mismatch_mva"
        ),
        "maximum_returned_recomputed_branch_flow_mismatch_mva": _max_witness_metric(
            case_rows, "max_returned_recomputed_branch_flow_mismatch_mva"
        ),
        "maximum_objective_mismatch_mw2": _max_witness_metric(
            case_rows, "objective_mismatch_mw2"
        ),
        **context.config["evidence"],
    }


def _load_results(
    context: _StepContext,
    target: Path,
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    summary = _load_json(target, "summary.json")
    case_rows = _csv_rows(target / "step_control_cases.csv", _CASE_FIELDS)
    generator_rows = _csv_rows(target / "generator_results.csv", _GENERATOR_FIELDS)
    bus_rows = _csv_rows(target / "bus_results.csv", _BUS_FIELDS)
    branch_rows = _csv_rows(target / "branch_results.csv", _BRANCH_FIELDS)
    _validate_result_rows(context, case_rows, generator_rows, bus_rows, branch_rows)
    expected_summary = _stable_json(_summary(context, registration, case_rows))
    if summary != expected_summary:
        raise RuntimeError("Published RTS-GMLC step-control summary drifted")
    return summary


def run_step_control(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "step_control"
    if target.exists():
        return _load_results(context, target, registration)
    case_rows, generator_rows, bus_rows, branch_rows = _run_cases(context)
    summary = _summary(context, registration, case_rows)

    def writer(staging: Path) -> None:
        _write_csv(staging / "step_control_cases.csv", _CASE_FIELDS, case_rows)
        _write_csv(staging / "generator_results.csv", _GENERATOR_FIELDS, generator_rows)
        _write_csv(staging / "bus_results.csv", _BUS_FIELDS, bus_rows)
        _write_csv(staging / "branch_results.csv", _BRANCH_FIELDS, branch_rows)
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_results(context, target, registration)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=_CONFIG_PATH)
    parser.add_argument("--stage", choices=("prepare", "run", "all"), required=True)
    args = parser.parse_args()
    if args.stage == "prepare":
        result = prepare_preregistration(args.config)
    elif args.stage == "run":
        result = run_step_control(args.config)
    else:
        prepare_preregistration(args.config)
        result = run_step_control(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
