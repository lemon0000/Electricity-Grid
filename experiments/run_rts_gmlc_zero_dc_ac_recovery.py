"""Run the pre-registered zero-DC bounded P/Q/V AC-OPF recovery diagnostic."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import math
import platform
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml
from pypower.idx_brch import BR_STATUS, F_BUS, RATE_A, T_BUS
from pypower.idx_bus import BS, BUS_I, BUS_TYPE, GS, PD, QD
from pypower.idx_gen import GEN_BUS, GEN_STATUS, PMAX, PMIN, QMAX, QMIN, VG

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import (
    _sha256,
    _stable_json,
    _write_csv,
)
from experiments.run_rts_gmlc_multi_poi_ac_replay_voltage_control_amended import (
    _configure_q_capable_voltage_control,
)
from experiments.run_rts_gmlc_multi_poi_scan import (
    _publish_payload,
    _write_json,
)
from experiments.run_rts_gmlc_zero_dc_normal_ac_control import (
    _build_context as _build_zero_context,
    _load_zero_dispatch,
    _require_preregistration as _require_zero_preregistration,
)
from src.grid.rts_gmlc_ac import reconstruct_rts_gmlc_dc_flows
from src.grid.rts_gmlc_ac_recovery import (
    AcRecoveryBranchRecord,
    AcRecoveryBusRecord,
    AcRecoveryGeneratorRecord,
    AcRecoveryResult,
    prepare_rts_gmlc_ac_recovery,
    solve_and_audit_ac_recovery,
)
from src.scenarios.common_input_signature import common_input_signature_sha256


_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_recovery.yaml")
_CONFIG_SHA256 = "44abfdb5b0d8b3cdd71c34668f4b936c96e4ff01c327bc0e4ca15415a1f1f45d"
_ZERO_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_normal_ac_control.yaml")
_ZERO_RUNNER_PATH = Path("experiments/run_rts_gmlc_zero_dc_normal_ac_control.py")
_ZERO_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_normal_ac_control_v1"
)
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_zero_dc_ac_recovery.py"),
    Path("experiments/process_google_power_workload_day0.py"),
    Path("src/grid/rts_gmlc_ac_recovery.py"),
)
_MODES = ("reference_provider", "distributed_committable")
_EXPECTED_HOURS = 24
_EXPECTED_CASES = 48
_CSV_ROUNDING_ALLOWANCE = 1.0e-9
_DETAIL_LINEAR_TOLERANCE = 1.0e-6
_DETAIL_BALANCE_TOLERANCE = 1.0e-5
_DETAIL_OBJECTIVE_TOLERANCE = 1.0e-4
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
    "native_grid_demand_mw",
    "native_reactive_demand_mvar",
    "hvdc_dc1_flow_mw",
    "dc_flow_reconstruction_residual_mw",
)
_CASE_RESULT_FIELDS = tuple(
    field.name
    for field in fields(AcRecoveryResult)
    if field.name not in {"generator_records", "bus_records", "branch_records"}
)
_CASE_FIELDS = _CASE_PREFIX_FIELDS + _CASE_RESULT_FIELDS
_GENERATOR_FIELDS = (
    "hour_index",
    "timestamp",
    "mode",
) + tuple(field.name for field in fields(AcRecoveryGeneratorRecord))
_BUS_FIELDS = (
    "hour_index",
    "timestamp",
    "mode",
) + tuple(field.name for field in fields(AcRecoveryBusRecord))
_BRANCH_FIELDS = (
    "hour_index",
    "timestamp",
    "mode",
) + tuple(field.name for field in fields(AcRecoveryBranchRecord))
_CASE_NUMERIC_FIELDS = tuple(
    field
    for field in _CASE_FIELDS
    if field
    not in {
        "timestamp",
        "mode",
        "state_id",
        "reference_generator_uid",
        "active_power_envelope",
        "source_case_sha256",
        "recovery_case_sha256",
        "status",
        "solver_error_type",
        "solver_error_message",
        "solver_message",
    }
    and field
    not in {
        "zero_data_center",
        "evaluated",
        "solver_success",
        "independent_audit_passed",
        "recovered",
        "solver_input_case_unchanged",
        "recovery_input_fixed_fields_preserved",
        "solver_result_fixed_fields_preserved",
    }
)
_CASE_SUCCESS_REQUIRED_NUMERIC_FIELDS = tuple(
    field
    for field in _CASE_NUMERIC_FIELDS
    if field not in {"hour_index", "dc_bus_api_placeholder", "reference_bus"}
)


@dataclass(frozen=True)
class _RecoveryContext:
    config_path: Path
    config: dict[str, Any]
    zero: Any
    output_root: Path
    input_contract: dict[str, Any]
    input_contract_sha256: str


def _read_config(config_path: Path) -> dict[str, Any]:
    if _sha256(config_path) != _CONFIG_SHA256:
        raise ValueError("RTS-GMLC zero-DC recovery config SHA-256 drifted")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    required_sections = {
        "preregistration",
        "parent_zero_control",
        "observed_evidence_disclosure",
        "case_scope",
        "recovery_modes",
        "ac_opf",
        "solver_options",
        "independent_audit",
        "interpretation",
        "evidence",
        "output",
    }
    if not isinstance(config, dict) or set(config) != required_sections:
        raise ValueError("RTS-GMLC zero-DC recovery config schema drifted")
    preregistration = config["preregistration"]
    if preregistration != {
        "id": "rts_gmlc_google_day0_zero_dc_ac_recovery_v1",
        "schema": "rts_gmlc_zero_dc_ac_recovery_preregistration_v1",
        "status": (
            "repository_local_frozen_after_zero_direct_ac_outcomes_before_"
            "zero_recovery_solve"
        ),
        "externally_timestamped": False,
        "parent_treatment_outcomes_observed": True,
        "treatment_voltage_control_probe_observed": True,
        "legacy_vg_treatment_ac_opf_implementation_probe_observed": True,
        "treatment_probe_evidence_role": (
            "disclosed_implementation_diagnostic_excluded_from_zero_recovery_evidence"
        ),
        "zero_normal_ac_outcomes_observed": True,
        "zero_normal_ac_converged_count_observed": 24,
        "zero_normal_ac_secure_count_observed": 0,
        "zero_recovery_outcomes_observed": False,
        "all_zero_recovery_cases_blind": True,
    }:
        raise ValueError("RTS-GMLC zero-DC recovery preregistration drifted")
    if (
        config["case_scope"].get("modes") != list(_MODES)
        or config["case_scope"].get("expected_unique_cases") != _EXPECTED_CASES
    ):
        raise ValueError("RTS-GMLC zero-DC recovery case scope drifted")
    if (
        config["solver_options"].get("OPF_ALG") != 560
        or config["solver_options"].get("OPF_FLOW_LIM") != 0
    ):
        raise ValueError("RTS-GMLC zero-DC recovery solver contract drifted")
    if config["output"] != {
        "directory": "results/tables/rts_gmlc_google_day0_zero_dc_ac_recovery_v1"
    }:
        raise ValueError("RTS-GMLC zero-DC recovery output contract drifted")
    return config


def _software_versions() -> dict[str, str]:
    versions = {"python": platform.python_version(), "platform": platform.platform()}
    for package in ("numpy", "pypower", "pyyaml", "scipy"):
        versions[package] = importlib.metadata.version(package)
    return versions


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC zero-DC recovery artifact {root / name} drifted")
    return payload


def _verify_parent_artifacts(config: Mapping[str, Any], zero: Any) -> None:
    parent = config["parent_zero_control"]
    if (
        Path(parent["config_path"]) != _ZERO_CONFIG_PATH
        or _sha256(_ZERO_CONFIG_PATH) != parent["config_sha256"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC recovery parent config drifted")
    if (
        Path(parent["implementation_path"]) != _ZERO_RUNNER_PATH
        or _sha256(_ZERO_RUNNER_PATH) != parent["implementation_sha256"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC recovery parent implementation drifted")
    if zero.input_contract_sha256 != parent["input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC zero-DC recovery parent input contract drifted")
    if Path(parent["output_directory"]) != _ZERO_OUTPUT_ROOT:
        raise RuntimeError("RTS-GMLC zero-DC recovery parent output root drifted")
    for subdirectory, key in (
        ("preregistration", "preregistration_manifest_sha256"),
        ("dc_dispatch", "dc_dispatch_manifest_sha256"),
        ("ac_normal", "normal_ac_manifest_sha256"),
    ):
        root = _ZERO_OUTPUT_ROOT / subdirectory
        _verify_output_manifest(root)
        if _sha256(root / "SHA256SUMS") != parent[key]:
            raise RuntimeError(
                f"RTS-GMLC zero-DC recovery parent {subdirectory} manifest drifted"
            )
    _require_zero_preregistration(zero, _ZERO_OUTPUT_ROOT)
    _load_zero_dispatch(zero, _ZERO_OUTPUT_ROOT)
    ac_summary = _load_json(_ZERO_OUTPUT_ROOT / "ac_normal", "summary.json")
    expected_observed = config["observed_evidence_disclosure"]
    if (
        ac_summary.get("input_contract_sha256") != parent["input_contract_sha256"]
        or ac_summary.get("dc_dispatch_manifest_sha256")
        != parent["dc_dispatch_manifest_sha256"]
        or ac_summary.get("case_count")
        != expected_observed["zero_normal_ac_case_count"]
        or ac_summary.get("converged_case_count")
        != expected_observed["zero_normal_ac_converged_count"]
        or ac_summary.get("secure_case_count")
        != expected_observed["zero_normal_ac_secure_count"]
    ):
        raise RuntimeError("RTS-GMLC zero-DC observed AC evidence drifted")


def _build_context(config_path: Path) -> _RecoveryContext:
    config = _read_config(config_path)
    zero = _build_zero_context(_ZERO_CONFIG_PATH)
    _verify_parent_artifacts(config, zero)
    contract = {
        "schema": "rts_gmlc_zero_dc_ac_recovery_inputs_v1",
        "config_sha256": _sha256(config_path),
        "parent_zero_control": config["parent_zero_control"],
        "observed_evidence_disclosure": config["observed_evidence_disclosure"],
        "case_scope": config["case_scope"],
        "recovery_modes": config["recovery_modes"],
        "ac_opf": config["ac_opf"],
        "solver_options": config["solver_options"],
        "independent_audit": config["independent_audit"],
        "interpretation": config["interpretation"],
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "software_versions": _software_versions(),
        "evidence": config["evidence"],
    }
    return _RecoveryContext(
        config_path=config_path,
        config=config,
        zero=zero,
        output_root=Path(config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: _RecoveryContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


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
        "parent_treatment_outcomes_observed": True,
        "treatment_voltage_control_probe_observed": True,
        "legacy_vg_treatment_ac_opf_implementation_probe_observed": True,
        "treatment_probe_evidence_role": preregistration[
            "treatment_probe_evidence_role"
        ],
        "zero_normal_ac_outcomes_observed": True,
        "zero_recovery_outcomes_observed": False,
        "all_zero_recovery_cases_blind": True,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError(
                "Published RTS-GMLC zero-DC recovery registration drifted"
            )
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC zero-DC recovery config drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(
            "Cannot prepare recovery beside existing unregistered artifacts"
        )

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _RecoveryContext,
    output_root: Path,
) -> dict[str, Any]:
    registration = _load_json(output_root / "preregistration", "registration.json")
    if registration.get("input_contract") != _stable_json(context.input_contract):
        raise RuntimeError("RTS-GMLC zero-DC recovery live inputs drifted")
    if registration.get("input_contract_sha256") != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC zero-DC recovery input contract SHA drifted")
    if (output_root / "preregistration" / "config.yaml").read_bytes() != (
        context.config_path.read_bytes()
    ):
        raise RuntimeError("RTS-GMLC zero-DC recovery live config drifted")
    return registration


def _csv_rows(path: Path, expected_fields: tuple[str, ...]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise RuntimeError(f"RTS-GMLC zero-DC recovery CSV schema drifted: {path}")
        return list(reader)


def _parse_bool(value: object, *, label: str) -> bool:
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().lower()
    if normalized == "true":
        return True
    if normalized == "false":
        return False
    raise RuntimeError(f"RTS-GMLC zero-DC recovery {label} is not boolean")


def _finite(value: object, *, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise RuntimeError(
            f"RTS-GMLC zero-DC recovery {label} is not numeric"
        ) from error
    if not math.isfinite(parsed):
        raise RuntimeError(f"RTS-GMLC zero-DC recovery {label} is non-finite")
    return parsed


def _exact_int(value: object, *, label: str) -> int:
    parsed = _finite(value, label=label)
    integer = int(parsed)
    if parsed != integer:
        raise RuntimeError(f"RTS-GMLC zero-DC recovery {label} is not an integer")
    return integer


def _expected_case_metadata(
    context: _RecoveryContext,
) -> dict[tuple[str, str], dict[str, object]]:
    hourly, generation, commitment, flows = _load_zero_dispatch(
        context.zero, _ZERO_OUTPUT_ROOT
    )
    point_by_timestamp = {
        point.timestamp.isoformat(): point
        for point in context.zero.ac.scan_context.business.points
    }
    placeholder_bus = int(context.zero.config["zero_control"]["dc_bus_api_placeholder"])
    dc_tolerance_mw = float(context.zero.config["solver"]["tolerance_mw"])
    expected = {}
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
        for mode in _MODES:
            prepared = prepare_rts_gmlc_ac_recovery(
                configured,
                context.zero.ac.template,
                context.zero.ac.scan_context.data,
                mode=mode,
                voltage_limits_pu=tuple(context.config["ac_opf"]["voltage_limits_pu"]),
            )
            prepared_bus = prepared.case["bus"]
            prepared_generator = prepared.case["gen"]
            prepared_branch = prepared.case["branch"]
            expected[(timestamp, mode)] = {
                "hour_index": hour_index,
                "dc_bus_api_placeholder": placeholder_bus,
                "reference_bus": prepared.reference_bus,
                "reference_generator_uid": prepared.reference_generator_uid,
                "active_power_envelope": prepared.active_power_envelope,
                "adjustable_generator_count": len(prepared.adjustable_generator_rows),
                "fixed_generator_count": len(prepared.fixed_generator_rows),
                "source_case_sha256": prepared.source_case_sha256,
                "recovery_case_sha256": prepared.recovery_case_sha256,
                "native_grid_demand_mw": float(hourly_row["native_grid_demand_mw"]),
                "native_reactive_demand_mvar": configured.native_reactive_demand_mvar,
                "hvdc_dc1_flow_mw": dc_flows["DC1"],
                "dc_flow_reconstruction_residual_mw": residual,
                "expected_generator_fixed": {
                    uid: {
                        "generator_row": row,
                        "bus": int(prepared_generator[row, GEN_BUS]),
                        "online": bool(prepared_generator[row, GEN_STATUS] > 0.0),
                        "adjustable_active_power": row
                        in prepared.adjustable_generator_rows,
                        "target_pg_mw": prepared.target_generation_mw_by_row[row],
                        "pmin_mw": float(prepared_generator[row, PMIN]),
                        "pmax_mw": float(prepared_generator[row, PMAX]),
                        "qmin_mvar": float(prepared_generator[row, QMIN]),
                        "qmax_mvar": float(prepared_generator[row, QMAX]),
                        "source_vg_pu": float(prepared_generator[row, VG]),
                    }
                    for row, uid in enumerate(
                        context.zero.ac.template.generator_uid_by_row
                    )
                },
                "expected_bus_fixed": {
                    int(row[BUS_I]): {
                        "bus_type": int(row[BUS_TYPE]),
                        "pd_mw": float(row[PD]),
                        "qd_mvar": float(row[QD]),
                        "gs_mw_at_1pu": float(row[GS]),
                        "bs_mvar_at_1pu": float(row[BS]),
                    }
                    for row in prepared_bus
                },
                "expected_branch_fixed": {
                    uid: {
                        "branch_row": row,
                        "from_bus": int(prepared_branch[row, F_BUS]),
                        "to_bus": int(prepared_branch[row, T_BUS]),
                        "online": bool(prepared_branch[row, BR_STATUS] > 0.0),
                        "rate_a_mva": float(prepared_branch[row, RATE_A]),
                    }
                    for row, uid in enumerate(
                        context.zero.ac.template.branch_uid_by_row
                    )
                },
            }
    return expected


def _validate_result_rows(
    context: _RecoveryContext,
    case_rows: Sequence[Mapping[str, object]],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
) -> None:
    timestamps = tuple(
        point.timestamp.isoformat() for point in context.zero.zero_business.points
    )
    hour_index_by_timestamp = {
        timestamp: hour_index for hour_index, timestamp in enumerate(timestamps)
    }
    expected_case_keys = {
        (timestamp, mode) for timestamp in timestamps for mode in _MODES
    }
    observed_case_keys = {
        (str(row["timestamp"]), str(row["mode"])) for row in case_rows
    }
    if len(case_rows) != _EXPECTED_CASES or observed_case_keys != expected_case_keys:
        raise RuntimeError("RTS-GMLC zero-DC recovery case coverage drifted")
    expected_metadata = _expected_case_metadata(context)

    successful_keys = set()
    for row in case_rows:
        key = (str(row["timestamp"]), str(row["mode"]))
        metadata = expected_metadata[key]
        if str(row["state_id"]) != "normal" or not _parse_bool(
            row["zero_data_center"], label="zero_data_center"
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery case identity drifted")
        if (
            _exact_int(row["hour_index"], label="hour_index") != metadata["hour_index"]
            or _exact_int(row["dc_bus_api_placeholder"], label="dc_bus_api_placeholder")
            != metadata["dc_bus_api_placeholder"]
            or _exact_int(row["reference_bus"], label="reference_bus")
            != metadata["reference_bus"]
            or str(row["reference_generator_uid"])
            != metadata["reference_generator_uid"]
            or str(row["active_power_envelope"]) != metadata["active_power_envelope"]
            or _exact_int(
                row["adjustable_generator_count"], label="adjustable_generator_count"
            )
            != metadata["adjustable_generator_count"]
            or _exact_int(row["fixed_generator_count"], label="fixed_generator_count")
            != metadata["fixed_generator_count"]
            or str(row["source_case_sha256"]) != metadata["source_case_sha256"]
            or str(row["recovery_case_sha256"]) != metadata["recovery_case_sha256"]
            or _exact_int(row["solver_algorithm"], label="solver_algorithm") != 560
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery frozen case metadata drifted")
        for field in (
            "native_grid_demand_mw",
            "native_reactive_demand_mvar",
            "hvdc_dc1_flow_mw",
            "dc_flow_reconstruction_residual_mw",
        ):
            if (
                abs(_finite(row[field], label=field) - float(metadata[field]))
                > _CSV_ROUNDING_ALLOWANCE
            ):
                raise RuntimeError(
                    "RTS-GMLC zero-DC recovery frozen numeric metadata drifted"
                )
        for field in (
            "dc_bus_api_placeholder",
            "reference_bus",
            "adjustable_generator_count",
            "fixed_generator_count",
            "native_grid_demand_mw",
            "native_reactive_demand_mvar",
            "hvdc_dc1_flow_mw",
            "dc_flow_reconstruction_residual_mw",
        ):
            _finite(row[field], label=field)
        for field in (
            "dc_bus_api_placeholder",
            "reference_bus",
            "adjustable_generator_count",
            "fixed_generator_count",
        ):
            _exact_int(row[field], label=field)
        evaluated = _parse_bool(row["evaluated"], label="evaluated")
        solver_success = _parse_bool(row["solver_success"], label="solver_success")
        audited = _parse_bool(
            row["independent_audit_passed"], label="independent_audit_passed"
        )
        recovered = _parse_bool(row["recovered"], label="recovered")
        for field in _CASE_NUMERIC_FIELDS:
            if row[field] not in (None, ""):
                _finite(row[field], label=field)
        if row["solver_iterations"] not in (None, ""):
            _exact_int(row["solver_iterations"], label="solver_iterations")
        input_unchanged = _parse_bool(
            row["solver_input_case_unchanged"], label="solver_input_case_unchanged"
        )
        recovery_input_preserved = _parse_bool(
            row["recovery_input_fixed_fields_preserved"],
            label="recovery_input_fixed_fields_preserved",
        )
        result_fixed_fields_preserved = _parse_bool(
            row["solver_result_fixed_fields_preserved"],
            label="solver_result_fixed_fields_preserved",
        )
        if not input_unchanged or not recovery_input_preserved:
            raise RuntimeError("RTS-GMLC zero-DC recovery input audit failed")
        if solver_success and not evaluated:
            raise RuntimeError(
                "RTS-GMLC zero-DC recovery solver success was not evaluated"
            )
        status = str(row["status"])
        if not solver_success:
            state_valid = (
                not audited
                and not recovered
                and status == "not_recovered_by_local_solver"
            )
        elif not audited:
            state_valid = (
                not recovered and status == "solver_success_independent_audit_failed"
            )
        else:
            state_valid = recovered and status == "recovered_by_local_solver"
        if not state_valid:
            raise RuntimeError("RTS-GMLC zero-DC recovery acceptance semantics drifted")
        error_type = str(row["solver_error_type"] or "").strip()
        error_message = str(row["solver_error_message"] or "").strip()
        solver_message = str(row["solver_message"] or "").strip()
        if evaluated:
            execution_state_valid = (
                not error_type
                and not error_message
                and (solver_success or bool(solver_message))
            )
        else:
            execution_state_valid = (
                bool(error_type)
                and bool(error_message)
                and not solver_message
                and not solver_success
            )
        if not execution_state_valid:
            raise RuntimeError("RTS-GMLC zero-DC recovery execution semantics drifted")
        if audited:
            audit = context.config["independent_audit"]
            independent_objective = _finite(
                row["independent_objective_mw2"],
                label="independent_objective_mw2",
            )
            objective_limit = float(audit["objective_absolute_tolerance_mw2"]) + float(
                audit["objective_relative_tolerance"]
            ) * max(1.0, independent_objective)
            persisted_audit_passed = (
                _finite(
                    row["max_active_power_bound_violation_mw"],
                    label="max_active_power_bound_violation_mw",
                )
                <= float(audit["active_power_bound_tolerance_mw"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_reactive_power_bound_violation_mvar"],
                    label="max_reactive_power_bound_violation_mvar",
                )
                <= float(audit["reactive_power_bound_tolerance_mvar"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(row["max_offline_pg_mw"], label="max_offline_pg_mw")
                <= float(audit["offline_pg_qg_tolerance_mw_mvar"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(row["max_offline_qg_mvar"], label="max_offline_qg_mvar")
                <= float(audit["offline_pg_qg_tolerance_mw_mvar"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_offline_branch_flow_mva"],
                    label="max_offline_branch_flow_mva",
                )
                <= float(audit["offline_branch_flow_tolerance_mva"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_voltage_violation_pu"], label="max_voltage_violation_pu"
                )
                <= float(audit["voltage_bound_tolerance_pu"]) + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_output_vg_bus_vm_mismatch_pu"],
                    label="max_output_vg_bus_vm_mismatch_pu",
                )
                <= float(audit["voltage_bound_tolerance_pu"]) + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_branch_loading_fraction"],
                    label="max_branch_loading_fraction",
                )
                <= 1.0
                + float(audit["branch_loading_tolerance_fraction"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_fixed_pg_deviation_mw"],
                    label="max_fixed_pg_deviation_mw",
                )
                <= float(audit["fixed_generator_pg_tolerance_mw"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_p_balance_residual_mw"],
                    label="max_p_balance_residual_mw",
                )
                <= float(audit["nodal_p_q_balance_tolerance_mw_mvar"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["max_q_balance_residual_mvar"],
                    label="max_q_balance_residual_mvar",
                )
                <= float(audit["nodal_p_q_balance_tolerance_mw_mvar"])
                + _CSV_ROUNDING_ALLOWANCE
                and _finite(
                    row["objective_mismatch_mw2"], label="objective_mismatch_mw2"
                )
                <= objective_limit + _CSV_ROUNDING_ALLOWANCE
            )
            if not persisted_audit_passed:
                raise RuntimeError(
                    "RTS-GMLC zero-DC recovery persisted acceptance audit failed"
                )
        if solver_success:
            successful_keys.add(key)
            for field in _CASE_SUCCESS_REQUIRED_NUMERIC_FIELDS:
                _finite(row[field], label=field)
            if not result_fixed_fields_preserved:
                raise RuntimeError("RTS-GMLC zero-DC recovery input audit failed")

    generator_uids = set(context.zero.ac.template.generator_uid_by_row)
    bus_uids = set(context.zero.ac.template.bus_row_by_uid)
    branch_uids = set(context.zero.ac.template.branch_uid_by_row)
    expected_generator_keys = {
        (timestamp, mode, uid)
        for timestamp, mode in successful_keys
        for uid in generator_uids
    }
    expected_bus_keys = {
        (timestamp, mode, uid)
        for timestamp, mode in successful_keys
        for uid in bus_uids
    }
    expected_branch_keys = {
        (timestamp, mode, uid)
        for timestamp, mode in successful_keys
        for uid in branch_uids
    }
    observed_generator_keys = {
        (str(row["timestamp"]), str(row["mode"]), str(row["generator_uid"]))
        for row in generator_rows
    }
    observed_bus_keys = {
        (
            str(row["timestamp"]),
            str(row["mode"]),
            _exact_int(row["bus"], label="bus.bus"),
        )
        for row in bus_rows
    }
    observed_branch_keys = {
        (str(row["timestamp"]), str(row["mode"]), str(row["branch_uid"]))
        for row in branch_rows
    }
    if (
        len(generator_rows) != len(observed_generator_keys)
        or observed_generator_keys != expected_generator_keys
        or len(bus_rows) != len(observed_bus_keys)
        or observed_bus_keys != expected_bus_keys
        or len(branch_rows) != len(observed_branch_keys)
        or observed_branch_keys != expected_branch_keys
    ):
        raise RuntimeError("RTS-GMLC zero-DC recovery detail coverage drifted")
    case_by_key = {(str(row["timestamp"]), str(row["mode"])): row for row in case_rows}
    generator_row_by_uid = context.zero.ac.template.generator_row_by_uid
    adjustable_count_by_key = {key: 0 for key in successful_keys}
    online_count_by_key = {key: 0 for key in successful_keys}
    for row in generator_rows:
        key = (str(row["timestamp"]), str(row["mode"]))
        uid = str(row["generator_uid"])
        expected_row = generator_row_by_uid[uid]
        online = _parse_bool(row["online"], label="generator.online")
        adjustable = _parse_bool(
            row["adjustable_active_power"],
            label="generator.adjustable_active_power",
        )
        expected_fixed = expected_metadata[key]["expected_generator_fixed"][uid]
        if (
            _exact_int(row["hour_index"], label="generator.hour_index")
            != hour_index_by_timestamp[key[0]]
            or _exact_int(row["generator_row"], label="generator.generator_row")
            != expected_row
            or _exact_int(row["bus"], label="generator.bus") != expected_fixed["bus"]
            or online != expected_fixed["online"]
            or adjustable != expected_fixed["adjustable_active_power"]
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery generator identity drifted")
        for field in (
            "target_pg_mw",
            "pmin_mw",
            "pmax_mw",
            "qmin_mvar",
            "qmax_mvar",
            "source_vg_pu",
        ):
            _require_close(
                _finite(row[field], label=f"generator.{field}"),
                float(expected_fixed[field]),
                tolerance=_CSV_ROUNDING_ALLOWANCE,
                label=f"generator fixed input {field}",
            )
        online_count_by_key[key] += int(online)
        adjustable_count_by_key[key] += int(adjustable)
    for key in successful_keys:
        case_row = case_by_key[key]
        if adjustable_count_by_key[key] != _exact_int(
            case_row["adjustable_generator_count"],
            label="adjustable_generator_count",
        ) or online_count_by_key[key] - adjustable_count_by_key[key] != _exact_int(
            case_row["fixed_generator_count"], label="fixed_generator_count"
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery generator counts drifted")

    branch_row_by_uid = context.zero.ac.template.branch_row_by_uid
    for row in branch_rows:
        key = (str(row["timestamp"]), str(row["mode"]))
        uid = str(row["branch_uid"])
        expected_row = branch_row_by_uid[uid]
        expected_fixed = expected_metadata[key]["expected_branch_fixed"][uid]
        if (
            _exact_int(row["hour_index"], label="branch.hour_index")
            != hour_index_by_timestamp[key[0]]
            or _exact_int(row["branch_row"], label="branch.branch_row") != expected_row
            or _exact_int(row["from_bus"], label="branch.from_bus")
            != expected_fixed["from_bus"]
            or _exact_int(row["to_bus"], label="branch.to_bus")
            != expected_fixed["to_bus"]
            or _parse_bool(row["online"], label="branch.online")
            != expected_fixed["online"]
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery branch identity drifted")
        _require_close(
            _finite(row["rate_a_mva"], label="branch.rate_a_mva"),
            float(expected_fixed["rate_a_mva"]),
            tolerance=_CSV_ROUNDING_ALLOWANCE,
            label="branch fixed input RATE_A",
        )
    for row in bus_rows:
        key = (str(row["timestamp"]), str(row["mode"]))
        bus_uid = _exact_int(row["bus"], label="bus.bus")
        expected_fixed = expected_metadata[key]["expected_bus_fixed"][bus_uid]
        if (
            _exact_int(row["hour_index"], label="bus.hour_index")
            != hour_index_by_timestamp[key[0]]
            or _exact_int(row["bus_type"], label="bus.bus_type")
            != expected_fixed["bus_type"]
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery bus identity drifted")
        for field in (
            "pd_mw",
            "qd_mvar",
            "gs_mw_at_1pu",
            "bs_mvar_at_1pu",
        ):
            _require_close(
                _finite(row[field], label=f"bus.{field}"),
                float(expected_fixed[field]),
                tolerance=_CSV_ROUNDING_ALLOWANCE,
                label=f"bus fixed input {field}",
            )
    for rows, fields_to_check, label in (
        (
            generator_rows,
            tuple(
                field
                for field in _GENERATOR_FIELDS
                if field
                not in {
                    "timestamp",
                    "mode",
                    "generator_uid",
                    "online",
                    "adjustable_active_power",
                }
            ),
            "generator",
        ),
        (
            bus_rows,
            tuple(field for field in _BUS_FIELDS if field not in {"timestamp", "mode"}),
            "bus",
        ),
        (
            branch_rows,
            tuple(
                field
                for field in _BRANCH_FIELDS
                if field not in {"timestamp", "mode", "branch_uid", "online"}
            ),
            "branch",
        ),
    ):
        for row in rows:
            if label == "generator":
                _parse_bool(row["online"], label="generator.online")
                _parse_bool(
                    row["adjustable_active_power"],
                    label="generator.adjustable_active_power",
                )
            elif label == "branch":
                _parse_bool(row["online"], label="branch.online")
            for field in fields_to_check:
                if row[field] in (None, ""):
                    if label == "generator" and field in {
                        "q_bound_utilization",
                        "source_vg_to_optimized_vm_adjustment_pu",
                    }:
                        continue
                    raise RuntimeError(
                        f"RTS-GMLC zero-DC recovery {label} metric is missing"
                    )
                _finite(row[field], label=f"{label}.{field}")
    _validate_detail_aggregates(
        context,
        case_by_key,
        successful_keys,
        generator_rows,
        bus_rows,
        branch_rows,
    )


def _require_close(
    actual: float, expected: float, *, tolerance: float, label: str
) -> None:
    if abs(actual - expected) > tolerance:
        raise RuntimeError(f"RTS-GMLC zero-DC recovery {label} drifted")


def _validate_detail_aggregates(
    context: _RecoveryContext,
    case_by_key: Mapping[tuple[str, str], Mapping[str, object]],
    successful_keys: set[tuple[str, str]],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
) -> None:
    voltage_min, voltage_max = map(float, context.config["ac_opf"]["voltage_limits_pu"])
    for key in successful_keys:
        case = case_by_key[key]
        generators = [
            row
            for row in generator_rows
            if (str(row["timestamp"]), str(row["mode"])) == key
        ]
        buses = [
            row for row in bus_rows if (str(row["timestamp"]), str(row["mode"])) == key
        ]
        branches = [
            row
            for row in branch_rows
            if (str(row["timestamp"]), str(row["mode"])) == key
        ]
        bus_by_uid = {_exact_int(row["bus"], label="bus.bus"): row for row in buses}

        deviations = []
        active_deviations = []
        active_p_violations = []
        active_q_violations = []
        fixed_deviations = []
        offline_pg = []
        offline_qg = []
        output_vg_mismatches = []
        controller_adjustments = []
        total_generation = 0.0
        reference_deviation = None
        p_balance = {}
        q_balance = {}
        active_bus_uids = []
        voltage_violations = []
        total_demand = 0.0
        for bus_uid, row in bus_by_uid.items():
            bus_type = _exact_int(row["bus_type"], label="bus.bus_type")
            vm = _finite(row["vm_pu"], label="bus.vm_pu")
            pd = _finite(row["pd_mw"], label="bus.pd_mw")
            qd = _finite(row["qd_mvar"], label="bus.qd_mvar")
            gs = _finite(row["gs_mw_at_1pu"], label="bus.gs_mw_at_1pu")
            bs = _finite(row["bs_mvar_at_1pu"], label="bus.bs_mvar_at_1pu")
            p_balance[bus_uid] = -pd - gs * vm**2
            q_balance[bus_uid] = -qd + bs * vm**2
            total_demand += pd
            if bus_type != 4:
                active_bus_uids.append(bus_uid)
                voltage_violations.append(max(vm - voltage_max, voltage_min - vm, 0.0))

        for row in generators:
            uid = str(row["generator_uid"])
            bus_uid = _exact_int(row["bus"], label="generator.bus")
            online = _parse_bool(row["online"], label="generator.online")
            adjustable = _parse_bool(
                row["adjustable_active_power"],
                label="generator.adjustable_active_power",
            )
            target = _finite(row["target_pg_mw"], label="generator.target_pg_mw")
            pg = _finite(row["pg_mw"], label="generator.pg_mw")
            deviation = _finite(
                row["pg_deviation_mw"], label="generator.pg_deviation_mw"
            )
            pmin = _finite(row["pmin_mw"], label="generator.pmin_mw")
            pmax = _finite(row["pmax_mw"], label="generator.pmax_mw")
            qg = _finite(row["qg_mvar"], label="generator.qg_mvar")
            qmin = _finite(row["qmin_mvar"], label="generator.qmin_mvar")
            qmax = _finite(row["qmax_mvar"], label="generator.qmax_mvar")
            source_vg = _finite(row["source_vg_pu"], label="generator.source_vg_pu")
            output_vg = _finite(row["output_vg_pu"], label="generator.output_vg_pu")
            optimized_vm = _finite(
                row["optimized_bus_vm_pu"], label="generator.optimized_bus_vm_pu"
            )
            _require_close(
                deviation,
                pg - target,
                tolerance=_DETAIL_LINEAR_TOLERANCE,
                label="generator PG deviation",
            )
            _require_close(
                optimized_vm,
                _finite(bus_by_uid[bus_uid]["vm_pu"], label="bus.vm_pu"),
                tolerance=_DETAIL_LINEAR_TOLERANCE,
                label="generator optimized VM",
            )
            q_range = qmax - qmin
            q_utilization = row["q_bound_utilization"]
            if q_utilization not in (None, ""):
                _require_close(
                    _finite(q_utilization, label="generator.q_bound_utilization"),
                    (qg - qmin) / q_range,
                    tolerance=_DETAIL_LINEAR_TOLERANCE,
                    label="generator Q utilization",
                )
            controller_adjustment = row["source_vg_to_optimized_vm_adjustment_pu"]
            if controller_adjustment not in (None, ""):
                value = _finite(
                    controller_adjustment,
                    label="generator.source_vg_to_optimized_vm_adjustment_pu",
                )
                _require_close(
                    value,
                    optimized_vm - source_vg,
                    tolerance=_DETAIL_LINEAR_TOLERANCE,
                    label="generator controller adjustment",
                )
                controller_adjustments.append(abs(value))
            deviations.append(deviation)
            if online:
                active_deviations.append(deviation)
                active_p_violations.append(max(pg - pmax, pmin - pg, 0.0))
                active_q_violations.append(max(qg - qmax, qmin - qg, 0.0))
                if not adjustable:
                    fixed_deviations.append(abs(deviation))
                total_generation += pg
                p_balance[bus_uid] += pg
                q_balance[bus_uid] += qg
                output_vg_mismatches.append(abs(output_vg - optimized_vm))
            else:
                offline_pg.append(abs(pg))
                offline_qg.append(abs(qg))
            if uid == str(case["reference_generator_uid"]):
                reference_deviation = deviation

        loadings = []
        offline_branch_flows = []
        for row in branches:
            online = _parse_bool(row["online"], label="branch.online")
            from_bus = _exact_int(row["from_bus"], label="branch.from_bus")
            to_bus = _exact_int(row["to_bus"], label="branch.to_bus")
            pf = _finite(row["pf_mw"], label="branch.pf_mw")
            qf = _finite(row["qf_mvar"], label="branch.qf_mvar")
            pt = _finite(row["pt_mw"], label="branch.pt_mw")
            qt = _finite(row["qt_mvar"], label="branch.qt_mvar")
            from_mva = math.hypot(pf, qf)
            to_mva = math.hypot(pt, qt)
            terminal_mva = max(from_mva, to_mva)
            rate = _finite(row["rate_a_mva"], label="branch.rate_a_mva")
            loading = terminal_mva / rate if online else 0.0
            _require_close(
                _finite(row["from_mva"], label="branch.from_mva"),
                from_mva,
                tolerance=_DETAIL_LINEAR_TOLERANCE,
                label="branch from MVA",
            )
            _require_close(
                _finite(row["to_mva"], label="branch.to_mva"),
                to_mva,
                tolerance=_DETAIL_LINEAR_TOLERANCE,
                label="branch to MVA",
            )
            _require_close(
                _finite(row["loading_fraction"], label="branch.loading_fraction"),
                loading,
                tolerance=_DETAIL_LINEAR_TOLERANCE,
                label="branch loading",
            )
            if online:
                loadings.append(loading)
                p_balance[from_bus] -= pf
                q_balance[from_bus] -= qf
                p_balance[to_bus] -= pt
                q_balance[to_bus] -= qt
            else:
                offline_branch_flows.append(terminal_mva)

        for bus_uid in active_bus_uids:
            _require_close(
                _finite(
                    bus_by_uid[bus_uid]["p_balance_residual_mw"],
                    label="bus.p_balance_residual_mw",
                ),
                p_balance[bus_uid],
                tolerance=_DETAIL_BALANCE_TOLERANCE,
                label="bus P balance residual",
            )
            _require_close(
                _finite(
                    bus_by_uid[bus_uid]["q_balance_residual_mvar"],
                    label="bus.q_balance_residual_mvar",
                ),
                q_balance[bus_uid],
                tolerance=_DETAIL_BALANCE_TOLERANCE,
                label="bus Q balance residual",
            )

        independent_objective = sum(value**2 for value in deviations)
        expected_case_values = {
            "independent_objective_mw2": independent_objective,
            "squared_target_deviation_mw2": independent_objective,
            "l1_target_deviation_mw": sum(abs(value) for value in active_deviations),
            "l2_target_deviation_mw": math.sqrt(independent_objective),
            "max_target_deviation_mw": max(
                (abs(value) for value in active_deviations), default=0.0
            ),
            "total_up_redispatch_mw": sum(
                max(value, 0.0) for value in active_deviations
            ),
            "total_down_redispatch_mw": sum(
                max(-value, 0.0) for value in active_deviations
            ),
            "reference_redispatch_mw": reference_deviation,
            "total_generation_mw": total_generation,
            "total_active_demand_mw": total_demand,
            "ac_losses_mw": total_generation - total_demand,
            "max_active_power_bound_violation_mw": max(
                active_p_violations, default=0.0
            ),
            "max_reactive_power_bound_violation_mvar": max(
                active_q_violations, default=0.0
            ),
            "max_offline_pg_mw": max(offline_pg, default=0.0),
            "max_offline_qg_mvar": max(offline_qg, default=0.0),
            "max_offline_branch_flow_mva": max(offline_branch_flows, default=0.0),
            "max_voltage_violation_pu": max(voltage_violations, default=0.0),
            "max_branch_loading_fraction": max(loadings, default=0.0),
            "max_branch_loading_violation_fraction": max(
                max(loadings, default=0.0) - 1.0, 0.0
            ),
            "max_fixed_pg_deviation_mw": max(fixed_deviations, default=0.0),
            "max_p_balance_residual_mw": max(
                (abs(p_balance[uid]) for uid in active_bus_uids), default=0.0
            ),
            "max_q_balance_residual_mvar": max(
                (abs(q_balance[uid]) for uid in active_bus_uids), default=0.0
            ),
            "max_source_vg_to_optimized_vm_adjustment_pu": max(
                controller_adjustments, default=0.0
            ),
            "max_output_vg_bus_vm_mismatch_pu": max(output_vg_mismatches, default=0.0),
        }
        if reference_deviation is None:
            raise RuntimeError("RTS-GMLC zero-DC recovery reference detail is missing")
        for field, expected in expected_case_values.items():
            tolerance = (
                _DETAIL_OBJECTIVE_TOLERANCE
                if field
                in {
                    "independent_objective_mw2",
                    "squared_target_deviation_mw2",
                }
                else _DETAIL_LINEAR_TOLERANCE
            )
            _require_close(
                _finite(case[field], label=field),
                float(expected),
                tolerance=tolerance,
                label=f"case aggregate {field}",
            )
        solver_objective = _finite(
            case["solver_objective_mw2"], label="solver_objective_mw2"
        )
        _require_close(
            _finite(case["objective_mismatch_mw2"], label="objective_mismatch_mw2"),
            abs(solver_objective - independent_objective),
            tolerance=_DETAIL_OBJECTIVE_TOLERANCE,
            label="case objective mismatch",
        )


def _max_success_metric(
    case_rows: Sequence[Mapping[str, object]], field: str
) -> float | None:
    values = [
        float(row[field])
        for row in case_rows
        if _parse_bool(row["solver_success"], label="solver_success")
        and row[field] not in (None, "")
    ]
    return max(values, default=None)


def _run_cases(context: _RecoveryContext):
    hourly, generation, commitment, flows = _load_zero_dispatch(
        context.zero, _ZERO_OUTPUT_ROOT
    )
    point_by_timestamp = {
        point.timestamp.isoformat(): point
        for point in context.zero.ac.scan_context.business.points
    }
    placeholder_bus = int(context.zero.config["zero_control"]["dc_bus_api_placeholder"])
    solver_options = context.config["solver_options"]
    audit = context.config["independent_audit"]
    dc_tolerance_mw = float(context.zero.config["solver"]["tolerance_mw"])
    case_rows: list[dict[str, object]] = []
    generator_rows: list[dict[str, object]] = []
    bus_rows: list[dict[str, object]] = []
    branch_rows: list[dict[str, object]] = []

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
            raise RuntimeError("RTS-GMLC zero-DC recovery DC1 reconstruction drifted")
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
        generator = configured.case["gen"]
        expected_reference_row = context.zero.ac.template.generator_row_by_uid[
            configured.reference_generator_uid
        ]
        online_at_reference = [
            row
            for row in range(len(generator))
            if generator[row, GEN_STATUS] > 0.0
            and int(generator[row, GEN_BUS]) == configured.reference_bus
        ]
        if online_at_reference != [expected_reference_row]:
            raise RuntimeError("RTS-GMLC zero-DC recovery reference provider drifted")

        prepared_by_mode = {
            mode: prepare_rts_gmlc_ac_recovery(
                configured,
                context.zero.ac.template,
                context.zero.ac.scan_context.data,
                mode=mode,
                voltage_limits_pu=tuple(context.config["ac_opf"]["voltage_limits_pu"]),
            )
            for mode in _MODES
        }
        reference = prepared_by_mode["reference_provider"]
        distributed = prepared_by_mode["distributed_committable"]
        if not set(reference.adjustable_generator_rows).issubset(
            distributed.adjustable_generator_rows
        ):
            raise RuntimeError("RTS-GMLC zero-DC recovery modes are not nested")
        for row in range(len(generator)):
            if (
                reference.case["gen"][row, PMIN]
                < distributed.case["gen"][row, PMIN] - 1.0e-9
                or reference.case["gen"][row, PMAX]
                > distributed.case["gen"][row, PMAX] + 1.0e-9
            ):
                raise RuntimeError("RTS-GMLC zero-DC recovery P bounds are not nested")

        for mode in _MODES:
            prepared = prepared_by_mode[mode]
            result = solve_and_audit_ac_recovery(
                prepared,
                solver_options=solver_options,
                power_tolerance_mw=float(audit["active_power_bound_tolerance_mw"]),
                reactive_power_tolerance_mvar=float(
                    audit["reactive_power_bound_tolerance_mvar"]
                ),
                voltage_tolerance_pu=float(audit["voltage_bound_tolerance_pu"]),
                loading_tolerance=float(audit["branch_loading_tolerance_fraction"]),
                fixed_pg_tolerance_mw=float(audit["fixed_generator_pg_tolerance_mw"]),
                offline_tolerance_mw=float(audit["offline_pg_qg_tolerance_mw_mvar"]),
                offline_branch_tolerance_mva=float(
                    audit["offline_branch_flow_tolerance_mva"]
                ),
                balance_tolerance_mw=float(
                    audit["nodal_p_q_balance_tolerance_mw_mvar"]
                ),
                objective_tolerance_mw2=float(
                    audit["objective_absolute_tolerance_mw2"]
                ),
                objective_relative_tolerance=float(
                    audit["objective_relative_tolerance"]
                ),
            )
            result_payload = asdict(result)
            result_payload.pop("generator_records")
            result_payload.pop("bus_records")
            result_payload.pop("branch_records")
            case_rows.append(
                {
                    "hour_index": hour_index,
                    "timestamp": timestamp,
                    "mode": mode,
                    "state_id": "normal",
                    "zero_data_center": True,
                    "dc_bus_api_placeholder": placeholder_bus,
                    "reference_bus": prepared.reference_bus,
                    "reference_generator_uid": prepared.reference_generator_uid,
                    "active_power_envelope": prepared.active_power_envelope,
                    "adjustable_generator_count": len(
                        prepared.adjustable_generator_rows
                    ),
                    "fixed_generator_count": len(prepared.fixed_generator_rows),
                    "source_case_sha256": prepared.source_case_sha256,
                    "recovery_case_sha256": prepared.recovery_case_sha256,
                    "native_grid_demand_mw": float(hourly_row["native_grid_demand_mw"]),
                    "native_reactive_demand_mvar": (
                        configured.native_reactive_demand_mvar
                    ),
                    "hvdc_dc1_flow_mw": dc_flows["DC1"],
                    "dc_flow_reconstruction_residual_mw": residual,
                    **result_payload,
                }
            )
            for record in result.generator_records:
                generator_rows.append(
                    {
                        "hour_index": hour_index,
                        "timestamp": timestamp,
                        "mode": mode,
                        **asdict(record),
                    }
                )
            for record in result.bus_records:
                bus_rows.append(
                    {
                        "hour_index": hour_index,
                        "timestamp": timestamp,
                        "mode": mode,
                        **asdict(record),
                    }
                )
            for record in result.branch_records:
                branch_rows.append(
                    {
                        "hour_index": hour_index,
                        "timestamp": timestamp,
                        "mode": mode,
                        **asdict(record),
                    }
                )
    _validate_result_rows(context, case_rows, generator_rows, bus_rows, branch_rows)
    return case_rows, generator_rows, bus_rows, branch_rows


def _summary(
    context: _RecoveryContext,
    registration: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    mode_summaries = {}
    for mode in _MODES:
        rows = [row for row in case_rows if row["mode"] == mode]
        solver_success_count = sum(
            _parse_bool(row["solver_success"], label="solver_success") for row in rows
        )
        audit_pass_count = sum(
            _parse_bool(
                row["independent_audit_passed"], label="independent_audit_passed"
            )
            for row in rows
        )
        recovered_count = sum(
            _parse_bool(row["recovered"], label="recovered") for row in rows
        )
        mode_summaries[mode] = {
            "case_count": len(rows),
            "evaluated_count": sum(
                _parse_bool(row["evaluated"], label="evaluated") for row in rows
            ),
            "invocation_exception_count": sum(
                not _parse_bool(row["evaluated"], label="evaluated") for row in rows
            ),
            "solver_success_count": solver_success_count,
            "independent_audit_pass_count": audit_pass_count,
            "recovered_count": recovered_count,
            "solver_success_audit_failed_count": (
                solver_success_count - audit_pass_count
            ),
            "not_recovered_by_local_solver_count": sum(
                row["status"] == "not_recovered_by_local_solver" for row in rows
            ),
            "solver_returned_failure_count": sum(
                _parse_bool(row["evaluated"], label="evaluated")
                and not _parse_bool(row["solver_success"], label="solver_success")
                for row in rows
            ),
        }
    recovered_by_key = {
        (str(row["timestamp"]), str(row["mode"])): _parse_bool(
            row["recovered"], label="recovered"
        )
        for row in case_rows
    }
    nested_anomaly_timestamps = sorted(
        timestamp
        for timestamp, mode in recovered_by_key
        if mode == "reference_provider"
        and recovered_by_key[(timestamp, "reference_provider")]
        and not recovered_by_key[(timestamp, "distributed_committable")]
    )
    if nested_anomaly_timestamps:
        minimum_common_mode = None
    elif mode_summaries["reference_provider"]["recovered_count"] == _EXPECTED_HOURS:
        minimum_common_mode = "reference_provider"
    elif (
        mode_summaries["distributed_committable"]["recovered_count"] == _EXPECTED_HOURS
    ):
        minimum_common_mode = "distributed_committable"
    else:
        minimum_common_mode = None
    parent = context.config["parent_zero_control"]
    return {
        "schema": "rts_gmlc_zero_dc_ac_recovery_results_v1",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "parent_zero_dc_dispatch_manifest_sha256": parent[
            "dc_dispatch_manifest_sha256"
        ],
        "parent_zero_normal_ac_manifest_sha256": parent["normal_ac_manifest_sha256"],
        "case_count": len(case_rows),
        "expected_case_count": _EXPECTED_CASES,
        "all_cases_reported": len(case_rows) == _EXPECTED_CASES,
        "mode_summaries": mode_summaries,
        "minimum_common_recovery_mode": minimum_common_mode,
        "all_24_zero_hours_recovered_under_common_mode": minimum_common_mode
        is not None,
        "per_hour_favorable_mode_selection_used": False,
        "nested_mode_numerical_anomaly": bool(nested_anomaly_timestamps),
        "nested_mode_numerical_anomaly_timestamps": nested_anomaly_timestamps,
        "maximum_squared_target_deviation_mw2": _max_success_metric(
            case_rows, "squared_target_deviation_mw2"
        ),
        "maximum_target_deviation_mw": _max_success_metric(
            case_rows, "max_target_deviation_mw"
        ),
        "maximum_voltage_violation_pu": _max_success_metric(
            case_rows, "max_voltage_violation_pu"
        ),
        "maximum_branch_loading_fraction": _max_success_metric(
            case_rows, "max_branch_loading_fraction"
        ),
        "maximum_active_power_bound_violation_mw": _max_success_metric(
            case_rows, "max_active_power_bound_violation_mw"
        ),
        "maximum_reactive_power_bound_violation_mvar": _max_success_metric(
            case_rows, "max_reactive_power_bound_violation_mvar"
        ),
        "maximum_fixed_pg_deviation_mw": _max_success_metric(
            case_rows, "max_fixed_pg_deviation_mw"
        ),
        "maximum_offline_branch_flow_mva": _max_success_metric(
            case_rows, "max_offline_branch_flow_mva"
        ),
        "maximum_p_balance_residual_mw": _max_success_metric(
            case_rows, "max_p_balance_residual_mw"
        ),
        "maximum_q_balance_residual_mvar": _max_success_metric(
            case_rows, "max_q_balance_residual_mvar"
        ),
        "maximum_objective_mismatch_mw2": _max_success_metric(
            case_rows, "objective_mismatch_mw2"
        ),
        "maximum_source_vg_to_optimized_vm_adjustment_pu": _max_success_metric(
            case_rows, "max_source_vg_to_optimized_vm_adjustment_pu"
        ),
        "maximum_output_vg_bus_vm_mismatch_pu": _max_success_metric(
            case_rows, "max_output_vg_bus_vm_mismatch_pu"
        ),
        "solver_failure_does_not_prove_infeasibility": True,
        "local_solver_global_optimality_claimed": False,
        "physical_envelope_has_response_time_evidence": False,
        **context.config["evidence"],
    }


def _load_results(
    context: _RecoveryContext,
    target: Path,
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    summary = _load_json(target, "summary.json")
    case_rows = _csv_rows(target / "recovery_cases.csv", _CASE_FIELDS)
    generator_rows = _csv_rows(target / "generator_results.csv", _GENERATOR_FIELDS)
    bus_rows = _csv_rows(target / "bus_results.csv", _BUS_FIELDS)
    branch_rows = _csv_rows(target / "branch_results.csv", _BRANCH_FIELDS)
    _validate_result_rows(context, case_rows, generator_rows, bus_rows, branch_rows)
    expected_summary = _stable_json(_summary(context, registration, case_rows))
    if summary != expected_summary:
        raise RuntimeError("Published RTS-GMLC zero-DC recovery summary drifted")
    return summary


def run_recovery(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "recovery"
    if target.exists():
        return _load_results(context, target, registration)
    case_rows, generator_rows, bus_rows, branch_rows = _run_cases(context)
    summary = _summary(context, registration, case_rows)

    def writer(staging: Path) -> None:
        _write_csv(staging / "recovery_cases.csv", _CASE_FIELDS, case_rows)
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
        result = run_recovery(args.config)
    else:
        prepare_preregistration(args.config)
        result = run_recovery(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
