"""Run the registered cross-solver and voltage-limit AC diagnostic."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any, Mapping, Sequence

import casadi as ca
import yaml

import experiments.run_rts_gmlc_zero_dc_ac_step_control as step
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.grid.rts_gmlc_ac_ipopt import (
    AcIpoptEnvelope,
    AcIpoptResult,
    _FROZEN_IPOPT_OPTIONS,
    solve_ac_feasibility_ipopt,
)
from src.grid.rts_gmlc_ac_step_control import (
    StepControlAudit,
    StepControlBranchRecord,
    StepControlBusRecord,
    StepControlGeneratorRecord,
    _FROZEN_AUDIT_TOLERANCES,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic.yaml")
_CONFIG_SHA256 = "b088d4867aab2e24c3f54685dd04f09519c42b46ad4423830140e7af1c436e25"
_STEP_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_step_control.yaml")
_STEP_RUNNER_PATH = Path("experiments/run_rts_gmlc_zero_dc_ac_step_control.py")
_STEP_CORE_PATH = Path("src/grid/rts_gmlc_ac_step_control.py")
_STEP_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_step_control_v1"
)
_REFERENCE_ROOT = Path("data/raw/rts_gmlc/v0.2.3/matpower_reference")
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_zero_dc_ac_ipopt_diagnostic.py"),
    Path("src/grid/rts_gmlc_ac_ipopt.py"),
    Path("requirements.txt"),
    Path("scripts/fetch_rts_gmlc_matpower_reference.ps1"),
)
_EXPECTED_HOURS = 24
_EXPECTED_MODES = 4
_EXPECTED_RUNS = 96
_CSV_ABSOLUTE_TOLERANCE = 1.0e-10
_CSV_RELATIVE_TOLERANCE = 1.0e-12


@dataclass(frozen=True)
class _RunMode:
    run_id: str
    initial_strategy: str
    envelope: AcIpoptEnvelope


@dataclass(frozen=True)
class _IpoptContext:
    config_path: Path
    config: dict[str, Any]
    step_context: Any
    step_summary: dict[str, Any]
    run_modes: tuple[_RunMode, ...]
    output_root: Path
    input_contract: dict[str, Any]
    input_contract_sha256: str


_RESULT_SCALAR_FIELDS = tuple(
    field.name
    for field in fields(AcIpoptResult)
    if field.name not in {"audit", "solved_case"}
)
_AUDIT_FIELDS = tuple(
    field.name
    for field in fields(StepControlAudit)
    if field.name not in {"generator_records", "bus_records", "branch_records"}
)
_CASE_PREFIX_FIELDS = (
    "run_id",
    "hour_index",
    "timestamp",
    "state_id",
    "zero_data_center",
    "source_case_sha256",
    "recovery_case_sha256",
    "target_generation_sha256",
    "adjustable_generator_rows_sha256",
)
_CASE_EXTRA_FIELDS = (
    "registered_mode_feasibility_witnessed",
    "status",
    "solver_objective_mw2",
    "minimum_vm_pu",
    "maximum_vm_pu",
)
_CASE_FIELDS = (
    _CASE_PREFIX_FIELDS + _RESULT_SCALAR_FIELDS + _CASE_EXTRA_FIELDS + _AUDIT_FIELDS
)
_GENERATOR_FIELDS = ("run_id", "hour_index", "timestamp") + tuple(
    field.name for field in fields(StepControlGeneratorRecord)
)
_BUS_FIELDS = ("run_id", "hour_index", "timestamp") + tuple(
    field.name for field in fields(StepControlBusRecord)
)
_BRANCH_FIELDS = ("run_id", "hour_index", "timestamp") + tuple(
    field.name for field in fields(StepControlBranchRecord)
)


def _read_config(config_path: Path) -> dict[str, Any]:
    if _sha256(config_path) != _CONFIG_SHA256:
        raise ValueError("RTS-GMLC IPOPT diagnostic config SHA-256 drifted")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    required = {
        "preregistration",
        "parent_step_control",
        "official_voltage_limit_reference",
        "observed_probe_disclosure",
        "case_scope",
        "solver",
        "postsolve_audit",
        "interpretation",
        "evidence",
        "output",
    }
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("RTS-GMLC IPOPT diagnostic config schema drifted")
    preregistration = config["preregistration"]
    if (
        preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v1"
        or preregistration.get("schema")
        != "rts_gmlc_zero_dc_ac_ipopt_diagnostic_preregistration_v1"
        or preregistration.get("formal_full_24_mode_outcomes_observed") is not False
        or preregistration.get("all_formal_cases_blind") is not False
    ):
        raise ValueError("RTS-GMLC IPOPT diagnostic registration drifted")
    if config["solver"]["ipopt_options"] != _FROZEN_IPOPT_OPTIONS:
        raise ValueError("RTS-GMLC IPOPT diagnostic solver options drifted")
    if {
        key: config["postsolve_audit"].get(key) for key in _FROZEN_AUDIT_TOLERANCES
    } != _FROZEN_AUDIT_TOLERANCES:
        raise ValueError("RTS-GMLC IPOPT diagnostic audit tolerances drifted")
    scope = config["case_scope"]
    if (
        scope.get("expected_hours") != _EXPECTED_HOURS
        or scope.get("expected_run_modes") != _EXPECTED_MODES
        or scope.get("expected_runs") != _EXPECTED_RUNS
        or len(scope.get("run_modes", ())) != _EXPECTED_MODES
    ):
        raise ValueError("RTS-GMLC IPOPT diagnostic case scope drifted")
    if config["output"] != {
        "directory": "results/tables/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v1"
    }:
        raise ValueError("RTS-GMLC IPOPT diagnostic output drifted")
    return config


def _run_modes(config: Mapping[str, Any]) -> tuple[_RunMode, ...]:
    modes = tuple(
        _RunMode(
            run_id=str(item["id"]),
            initial_strategy=str(item["initial_strategy"]),
            envelope=AcIpoptEnvelope(
                branch_rate_multiplier=float(item["branch_rate_multiplier"]),
                reactive_power_bound_expansion_mvar=float(
                    item["reactive_power_bound_expansion_mvar"]
                ),
                voltage_bound_expansion_pu=float(item["voltage_bound_expansion_pu"]),
            ),
        )
        for item in config["case_scope"]["run_modes"]
    )
    expected = (
        _RunMode("original_source", "source", AcIpoptEnvelope()),
        _RunMode("original_midpoint", "midpoint", AcIpoptEnvelope()),
        _RunMode("original_flat_target_midq", "flat_target_midq", AcIpoptEnvelope()),
        _RunMode(
            "voltage_plus_0p01_source",
            "source",
            AcIpoptEnvelope(voltage_bound_expansion_pu=0.01),
        ),
    )
    if modes != expected:
        raise ValueError("RTS-GMLC IPOPT diagnostic run modes drifted")
    return modes


def _verify_parent(config: Mapping[str, Any]):
    parent = config["parent_step_control"]
    if (
        Path(parent["config_path"]) != _STEP_CONFIG_PATH
        or _sha256(_STEP_CONFIG_PATH) != parent["config_sha256"]
        or Path(parent["implementation_path"]) != _STEP_RUNNER_PATH
        or _sha256(_STEP_RUNNER_PATH) != parent["implementation_sha256"]
        or Path(parent["core_path"]) != _STEP_CORE_PATH
        or _sha256(_STEP_CORE_PATH) != parent["core_sha256"]
        or Path(parent["output_directory"]) != _STEP_OUTPUT_ROOT
    ):
        raise RuntimeError("RTS-GMLC IPOPT diagnostic parent implementation drifted")
    for subdirectory, key in (
        ("preregistration", "preregistration_manifest_sha256"),
        ("step_control", "result_manifest_sha256"),
    ):
        target = _STEP_OUTPUT_ROOT / subdirectory
        _verify_output_manifest(target)
        if _sha256(target / "SHA256SUMS") != parent[key]:
            raise RuntimeError(
                f"RTS-GMLC IPOPT diagnostic parent {subdirectory} drifted"
            )
    context = step._build_context(_STEP_CONFIG_PATH)
    registration = step._require_preregistration(context, _STEP_OUTPUT_ROOT)
    summary = step._load_results(
        context, _STEP_OUTPUT_ROOT / "step_control", registration
    )
    if context.input_contract_sha256 != parent["input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC IPOPT diagnostic parent contract drifted")
    if summary["step_control_feasibility_witness_count"] != 22 or summary[
        "step_control_not_witnessed_timestamps"
    ] != [
        "2020-01-01T15:00:00+00:00",
        "2020-01-01T21:00:00+00:00",
    ]:
        raise RuntimeError("RTS-GMLC IPOPT diagnostic parent outcomes drifted")
    return context, summary


def _verify_voltage_reference(config: Mapping[str, Any]) -> dict[str, object]:
    reference = config["official_voltage_limit_reference"]
    path = Path(reference["local_path"])
    manifest = Path(reference["manifest_path"])
    if (
        not path.is_file()
        or not manifest.is_file()
        or _sha256(path) != reference["local_sha256"]
        or _sha256(manifest) != reference["manifest_sha256"]
        or manifest.parent != _REFERENCE_ROOT
    ):
        raise RuntimeError("RTS-GMLC official MATPOWER reference drifted")
    _verify_output_manifest(_REFERENCE_ROOT)
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("mpc.bus = [") + 1
        end = lines.index("];", start)
    except ValueError as error:
        raise RuntimeError("RTS-GMLC official MATPOWER bus block drifted") from error
    rows = []
    for line in lines[start:end]:
        values = line.split()
        if len(values) != 13:
            raise RuntimeError("RTS-GMLC official MATPOWER bus row drifted")
        rows.append(tuple(float(value) for value in values))
    if (
        len(rows) != reference["expected_bus_count"]
        or {row[11] for row in rows} != {float(reference["expected_uniform_vmax_pu"])}
        or {row[12] for row in rows} != {float(reference["expected_uniform_vmin_pu"])}
    ):
        raise RuntimeError("RTS-GMLC official MATPOWER voltage limits drifted")
    return {
        "path": path.as_posix(),
        "sha256": _sha256(path),
        "manifest_sha256": _sha256(manifest),
        "bus_count": len(rows),
        "uniform_vmax_pu": rows[0][11],
        "uniform_vmin_pu": rows[0][12],
    }


def _casadi_identity(config: Mapping[str, Any]) -> dict[str, object]:
    python_path = Path(ca.__file__)
    binary = __import__("casadi._casadi", fromlist=["__file__"])
    binary_path = Path(binary.__file__)
    identity = {
        "version": importlib.metadata.version("casadi"),
        "python_sha256": _sha256(python_path),
        "binary_sha256": _sha256(binary_path),
        "build_type": ca.CasadiMeta_build_type(),
        "compiler_id": ca.CasadiMeta_compiler_id(),
    }
    solver = config["solver"]
    if (
        identity["version"] != solver["casadi_version"]
        or identity["python_sha256"] != solver["casadi_python_sha256"]
        or identity["binary_sha256"] != solver["casadi_binary_sha256"]
    ):
        raise RuntimeError("RTS-GMLC IPOPT diagnostic CasADi identity drifted")
    return identity


def _build_context(config_path: Path) -> _IpoptContext:
    config = _read_config(config_path)
    step_context, step_summary = _verify_parent(config)
    modes = _run_modes(config)
    voltage_reference = _verify_voltage_reference(config)
    casadi_identity = _casadi_identity(config)
    contract = {
        "schema": "rts_gmlc_zero_dc_ac_ipopt_diagnostic_inputs_v1",
        "config_sha256": _sha256(config_path),
        "parent_step_control": config["parent_step_control"],
        "official_voltage_limit_reference": config["official_voltage_limit_reference"],
        "verified_voltage_reference": voltage_reference,
        "observed_probe_disclosure": config["observed_probe_disclosure"],
        "case_scope": config["case_scope"],
        "solver": config["solver"],
        "casadi_identity": casadi_identity,
        "postsolve_audit": config["postsolve_audit"],
        "interpretation": config["interpretation"],
        "case_contracts": [step._case_contract(case) for case in step_context.cases],
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "evidence": config["evidence"],
    }
    return _IpoptContext(
        config_path=config_path,
        config=config,
        step_context=step_context,
        step_summary=step_summary,
        run_modes=modes,
        output_root=Path(config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: _IpoptContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC IPOPT artifact {root / name} drifted")
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
        "primary_and_step_control_outcomes_observed": True,
        "partial_ipopt_protocol_probes_observed": True,
        "formal_full_24_mode_outcomes_observed": False,
        "all_formal_cases_blind": False,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC IPOPT registration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC IPOPT config drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare beside existing IPOPT artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _IpoptContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    registration = _load_json(target, "registration.json")
    if registration.get("input_contract") != _stable_json(context.input_contract):
        raise RuntimeError("RTS-GMLC IPOPT live inputs drifted")
    if registration.get("input_contract_sha256") != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC IPOPT live contract SHA drifted")
    if (target / "config.yaml").read_bytes() != context.config_path.read_bytes():
        raise RuntimeError("RTS-GMLC IPOPT live config drifted")
    return registration


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return format(value, ".17g")
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
            raise RuntimeError(f"RTS-GMLC IPOPT CSV schema drifted: {path}")
        return list(reader)


def _is_original(mode: _RunMode) -> bool:
    return mode.envelope == AcIpoptEnvelope()


def _sensitivity_witness(result: AcIpoptResult) -> bool:
    audit = result.audit
    expansion = result.voltage_bound_expansion_pu
    tolerance = _FROZEN_AUDIT_TOLERANCES
    return bool(
        result.solver_success
        and result.maximum_nlp_constraint_violation <= 1.0e-6
        and result.maximum_nlp_variable_bound_violation <= 1.0e-8
        and audit.solver_result_fixed_fields_preserved
        and audit.reference_structure_valid
        and audit.max_active_power_bound_violation_mw
        <= tolerance["active_power_bound_tolerance_mw"]
        and audit.max_reactive_power_bound_violation_mvar
        <= tolerance["reactive_power_bound_tolerance_mvar"]
        and audit.max_offline_pg_mw <= tolerance["offline_pg_qg_tolerance_mw_mvar"]
        and audit.max_offline_qg_mvar <= tolerance["offline_pg_qg_tolerance_mw_mvar"]
        and audit.max_offline_branch_flow_mva
        <= tolerance["offline_branch_flow_tolerance_mva"]
        and audit.max_voltage_violation_pu
        <= expansion + tolerance["voltage_bound_tolerance_pu"]
        and audit.max_branch_loading_fraction
        <= 1.0 + tolerance["branch_loading_tolerance_fraction"]
        and audit.max_branch_angle_violation_degree
        <= tolerance["branch_angle_tolerance_degree"]
        and audit.max_fixed_pg_deviation_mw
        <= tolerance["fixed_generator_pg_tolerance_mw"]
        and audit.max_p_balance_residual_mw
        <= tolerance["nodal_p_q_balance_tolerance_mw_mvar"]
        and audit.max_q_balance_residual_mvar
        <= tolerance["nodal_p_q_balance_tolerance_mw_mvar"]
        and audit.max_ybus_terminal_shunt_identity_mismatch_mva
        <= tolerance["ybus_terminal_shunt_identity_tolerance_mva"]
        and audit.max_returned_recomputed_branch_flow_mismatch_mva
        <= tolerance["returned_recomputed_branch_flow_tolerance_mva"]
        and audit.max_reference_angle_drift_degree
        <= tolerance["reference_angle_tolerance_degree"]
        and audit.max_output_vg_bus_vm_mismatch_pu
        <= tolerance["voltage_bound_tolerance_pu"]
    )


def _status(mode: _RunMode, witness: bool) -> str:
    if _is_original(mode):
        return (
            "original_feasibility_witness"
            if witness
            else "original_not_witnessed_by_registered_ipopt_start"
        )
    return (
        "voltage_sensitivity_feasibility_witness"
        if witness
        else "voltage_sensitivity_not_witnessed"
    )


def _case_row(mode: _RunMode, case: Any, result: AcIpoptResult) -> dict[str, object]:
    payload = asdict(result)
    audit = payload.pop("audit")
    payload.pop("solved_case")
    for records in ("generator_records", "bus_records", "branch_records"):
        audit.pop(records)
    witness = (
        result.original_envelope_feasibility_witnessed
        if _is_original(mode)
        else _sensitivity_witness(result)
    )
    vm_values = [record.vm_pu for record in result.audit.bus_records]
    return {
        "run_id": mode.run_id,
        "hour_index": case.hour_index,
        "timestamp": case.timestamp,
        "state_id": "normal",
        "zero_data_center": True,
        "source_case_sha256": case.prepared.source_case_sha256,
        "recovery_case_sha256": case.prepared.recovery_case_sha256,
        "target_generation_sha256": case.target_generation_sha256,
        "adjustable_generator_rows_sha256": (case.adjustable_generator_rows_sha256),
        **payload,
        "registered_mode_feasibility_witnessed": witness,
        "status": _status(mode, witness),
        "solver_objective_mw2": result.independent_squared_target_deviation_mw2,
        "minimum_vm_pu": min(vm_values),
        "maximum_vm_pu": max(vm_values),
        **audit,
    }


def _detail_rows(mode: _RunMode, case: Any, result: AcIpoptResult):
    prefix = {
        "run_id": mode.run_id,
        "hour_index": case.hour_index,
        "timestamp": case.timestamp,
    }
    return (
        [{**prefix, **asdict(record)} for record in result.audit.generator_records],
        [{**prefix, **asdict(record)} for record in result.audit.bus_records],
        [{**prefix, **asdict(record)} for record in result.audit.branch_records],
    )


def _group_details(
    rows: Sequence[Mapping[str, object]],
) -> dict[tuple[str, str], list[Mapping[str, object]]]:
    grouped: dict[tuple[str, str], list[Mapping[str, object]]] = {}
    for row in rows:
        key = (str(row["run_id"]), str(row["timestamp"]))
        grouped.setdefault(key, []).append(row)
    return grouped


def _validate_result_rows(
    context: _IpoptContext,
    case_rows: Sequence[Mapping[str, object]],
    generator_rows: Sequence[Mapping[str, object]],
    bus_rows: Sequence[Mapping[str, object]],
    branch_rows: Sequence[Mapping[str, object]],
) -> None:
    expected = {
        (mode.run_id, case.timestamp): (mode, case)
        for mode in context.run_modes
        for case in context.step_context.cases
    }
    observed = {(str(row["run_id"]), str(row["timestamp"])): row for row in case_rows}
    if (
        len(case_rows) != _EXPECTED_RUNS
        or len(observed) != _EXPECTED_RUNS
        or set(observed) != set(expected)
    ):
        raise RuntimeError("RTS-GMLC IPOPT result coverage drifted")
    grouped_generator = _group_details(generator_rows)
    grouped_bus = _group_details(bus_rows)
    grouped_branch = _group_details(branch_rows)
    if any(
        set(grouped) != set(expected)
        for grouped in (grouped_generator, grouped_bus, grouped_branch)
    ):
        raise RuntimeError("RTS-GMLC IPOPT detail coverage drifted")

    for key, (mode, case) in expected.items():
        row = observed[key]
        prefix = {
            "run_id": mode.run_id,
            "hour_index": case.hour_index,
            "timestamp": case.timestamp,
            "state_id": "normal",
            "zero_data_center": True,
            "source_case_sha256": case.prepared.source_case_sha256,
            "recovery_case_sha256": case.prepared.recovery_case_sha256,
            "target_generation_sha256": case.target_generation_sha256,
            "adjustable_generator_rows_sha256": (case.adjustable_generator_rows_sha256),
        }
        for field, value in prefix.items():
            step._assert_serialized(row[field], value, label=field)
        if (
            not step._parse_bool(row["evaluated"], label="evaluated")
            or not step._parse_bool(
                row["solver_input_case_unchanged"],
                label="solver_input_case_unchanged",
            )
            or str(row["initial_strategy"]) != mode.initial_strategy
        ):
            raise RuntimeError("RTS-GMLC IPOPT solver identity drifted")
        for field, value in asdict(mode.envelope).items():
            step._assert_serialized(row[field], value, label=field)
        iterations = step._integer(row["iterations"], label="iterations")
        if iterations < 0 or not str(row["return_status"]):
            raise RuntimeError("RTS-GMLC IPOPT diagnostics drifted")
        for field in (
            "normalized_objective",
            "independent_squared_target_deviation_mw2",
            "maximum_nlp_constraint_violation",
            "maximum_nlp_variable_bound_violation",
            "solver_objective_mw2",
            "minimum_vm_pu",
            "maximum_vm_pu",
        ):
            step._finite(row[field], label=field)

        audit = step._reconstruct_audit(
            case,
            row,
            grouped_generator[key],
            grouped_bus[key],
            grouped_branch[key],
        )
        audit_payload = asdict(audit)
        expected_generator_records = audit_payload.pop("generator_records")
        expected_bus_records = audit_payload.pop("bus_records")
        expected_branch_records = audit_payload.pop("branch_records")
        for field, value in audit_payload.items():
            step._assert_serialized(row[field], value, label=field)
        for persisted, records, key_field in (
            (grouped_generator[key], expected_generator_records, "generator_row"),
            (grouped_bus[key], expected_bus_records, "bus_row"),
            (grouped_branch[key], expected_branch_records, "branch_row"),
        ):
            ordered = sorted(
                persisted,
                key=lambda item: step._integer(item[key_field], label=key_field),
            )
            for actual, expected_record in zip(ordered, records, strict=True):
                for field, value in expected_record.items():
                    step._assert_serialized(actual[field], value, label=field)
        vm_values = [record["vm_pu"] for record in expected_bus_records]
        step._assert_serialized(
            row["minimum_vm_pu"], min(vm_values), label="minimum_vm_pu"
        )
        step._assert_serialized(
            row["maximum_vm_pu"], max(vm_values), label="maximum_vm_pu"
        )

        solver_success = step._parse_bool(row["solver_success"], label="solver_success")
        original_claim = step._parse_bool(
            row["original_envelope_feasibility_witnessed"],
            label="original_envelope_feasibility_witnessed",
        )
        persisted_witness = step._parse_bool(
            row["registered_mode_feasibility_witnessed"],
            label="registered_mode_feasibility_witnessed",
        )
        if _is_original(mode):
            expected_witness = bool(
                solver_success
                and step._parse_bool(
                    row["postsolve_network_equation_reconstruction_audit_passed"],
                    label="postsolve audit",
                )
                and step._finite(
                    row["maximum_nlp_constraint_violation"],
                    label="maximum_nlp_constraint_violation",
                )
                <= 1.0e-6
                and step._finite(
                    row["maximum_nlp_variable_bound_violation"],
                    label="maximum_nlp_variable_bound_violation",
                )
                <= 1.0e-8
            )
            if original_claim != expected_witness:
                raise RuntimeError("RTS-GMLC IPOPT original witness drifted")
        else:
            if original_claim:
                raise RuntimeError(
                    "RTS-GMLC IPOPT sensitivity claimed original witness"
                )
            synthetic_result = AcIpoptResult(
                evaluated=True,
                solver_success=solver_success,
                original_envelope_feasibility_witnessed=False,
                return_status=str(row["return_status"]),
                iterations=iterations,
                normalized_objective=step._finite(
                    row["normalized_objective"], label="normalized_objective"
                ),
                independent_squared_target_deviation_mw2=step._finite(
                    row["independent_squared_target_deviation_mw2"],
                    label="independent_squared_target_deviation_mw2",
                ),
                maximum_nlp_constraint_violation=step._finite(
                    row["maximum_nlp_constraint_violation"],
                    label="maximum_nlp_constraint_violation",
                ),
                maximum_nlp_variable_bound_violation=step._finite(
                    row["maximum_nlp_variable_bound_violation"],
                    label="maximum_nlp_variable_bound_violation",
                ),
                initial_strategy=mode.initial_strategy,
                branch_rate_multiplier=mode.envelope.branch_rate_multiplier,
                reactive_power_bound_expansion_mvar=(
                    mode.envelope.reactive_power_bound_expansion_mvar
                ),
                voltage_bound_expansion_pu=mode.envelope.voltage_bound_expansion_pu,
                solver_input_case_unchanged=True,
                audit=audit,
                solved_case={},
            )
            expected_witness = _sensitivity_witness(synthetic_result)
        if persisted_witness != expected_witness:
            raise RuntimeError("RTS-GMLC IPOPT registered witness drifted")
        if str(row["status"]) != _status(mode, expected_witness):
            raise RuntimeError("RTS-GMLC IPOPT status drifted")


def _run_cases(context: _IpoptContext):
    case_rows = []
    generator_rows = []
    bus_rows = []
    branch_rows = []
    for mode in context.run_modes:
        for case in context.step_context.cases:
            result = solve_ac_feasibility_ipopt(
                case.prepared,
                initial_strategy=mode.initial_strategy,
                envelope=mode.envelope,
                solver_options=context.config["solver"]["ipopt_options"],
            )
            case_rows.append(_case_row(mode, case, result))
            generator, bus, branch = _detail_rows(mode, case, result)
            generator_rows.extend(generator)
            bus_rows.extend(bus)
            branch_rows.extend(branch)
    _validate_result_rows(context, case_rows, generator_rows, bus_rows, branch_rows)
    return case_rows, generator_rows, bus_rows, branch_rows


def _summary(
    context: _IpoptContext,
    registration: Mapping[str, Any],
    case_rows: Sequence[Mapping[str, object]],
) -> dict[str, Any]:
    mode_summaries = {}
    witnessed_by_mode = {}
    for mode in context.run_modes:
        rows = [row for row in case_rows if str(row["run_id"]) == mode.run_id]
        witnessed = frozenset(
            str(row["timestamp"])
            for row in rows
            if step._parse_bool(
                row["registered_mode_feasibility_witnessed"],
                label="registered_mode_feasibility_witnessed",
            )
        )
        witnessed_by_mode[mode.run_id] = witnessed
        mode_summaries[mode.run_id] = {
            "case_count": len(rows),
            "solver_success_count": sum(
                step._parse_bool(row["solver_success"], label="solver_success")
                for row in rows
            ),
            "registered_mode_feasibility_witness_count": len(witnessed),
            "not_witnessed_timestamps": sorted(
                set(case.timestamp for case in context.step_context.cases) - witnessed
            ),
            "initial_strategy": mode.initial_strategy,
            **asdict(mode.envelope),
        }
    original_union = frozenset().union(
        *(
            witnessed_by_mode[mode.run_id]
            for mode in context.run_modes
            if _is_original(mode)
        )
    )
    sensitivity = witnessed_by_mode["voltage_plus_0p01_source"]
    all_timestamps = set(case.timestamp for case in context.step_context.cases)
    return {
        "schema": "rts_gmlc_zero_dc_ac_ipopt_diagnostic_results_v1",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "parent_step_control_result_manifest_sha256": context.config[
            "parent_step_control"
        ]["result_manifest_sha256"],
        "case_count": len(case_rows),
        "expected_case_count": _EXPECTED_RUNS,
        "all_cases_reported": len(case_rows) == _EXPECTED_RUNS,
        "mode_summaries": mode_summaries,
        "original_multistart_feasibility_witness_count": len(original_union),
        "original_multistart_not_witnessed_timestamps": sorted(
            all_timestamps - original_union
        ),
        "all_24_original_envelope_cases_witnessed": len(original_union)
        == _EXPECTED_HOURS,
        "voltage_plus_0p01_feasibility_witness_count": len(sensitivity),
        "all_24_voltage_plus_0p01_cases_witnessed": len(sensitivity) == _EXPECTED_HOURS,
        "treatment_followup_gate_passed": len(original_union) == _EXPECTED_HOURS,
        "voltage_sensitivity_cannot_replace_official_bounds": True,
        "solver_reported_infeasibility_is_global_proof": False,
        "manual_per_hour_commitment_selection_used": False,
        "official_uniform_vmax_pu": 1.05,
        "official_uniform_vmin_pu": 0.95,
        "maximum_original_witness_p_balance_residual_mw": max(
            (
                step._finite(row["max_p_balance_residual_mw"], label="p residual")
                for row in case_rows
                if str(row["run_id"]).startswith("original_")
                and step._parse_bool(
                    row["registered_mode_feasibility_witnessed"], label="witness"
                )
            ),
            default=None,
        ),
        "maximum_original_witness_q_balance_residual_mvar": max(
            (
                step._finite(row["max_q_balance_residual_mvar"], label="q residual")
                for row in case_rows
                if str(row["run_id"]).startswith("original_")
                and step._parse_bool(
                    row["registered_mode_feasibility_witnessed"], label="witness"
                )
            ),
            default=None,
        ),
        "maximum_voltage_sensitivity_vm_pu": max(
            step._finite(row["maximum_vm_pu"], label="maximum_vm_pu")
            for row in case_rows
            if str(row["run_id"]) == "voltage_plus_0p01_source"
        ),
        "maximum_voltage_sensitivity_original_limit_violation_pu": max(
            step._finite(row["max_voltage_violation_pu"], label="voltage violation")
            for row in case_rows
            if str(row["run_id"]) == "voltage_plus_0p01_source"
        ),
        **context.config["evidence"],
    }


def _load_results(
    context: _IpoptContext,
    target: Path,
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    summary = _load_json(target, "summary.json")
    case_rows = _csv_rows(target / "ipopt_cases.csv", _CASE_FIELDS)
    generator_rows = _csv_rows(target / "generator_results.csv", _GENERATOR_FIELDS)
    bus_rows = _csv_rows(target / "bus_results.csv", _BUS_FIELDS)
    branch_rows = _csv_rows(target / "branch_results.csv", _BRANCH_FIELDS)
    _validate_result_rows(context, case_rows, generator_rows, bus_rows, branch_rows)
    expected_summary = _stable_json(_summary(context, registration, case_rows))
    if summary != expected_summary:
        raise RuntimeError("Published RTS-GMLC IPOPT summary drifted")
    return summary


def run_diagnostic(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "ipopt_diagnostic"
    if target.exists():
        return _load_results(context, target, registration)
    case_rows, generator_rows, bus_rows, branch_rows = _run_cases(context)
    summary = _summary(context, registration, case_rows)

    def writer(staging: Path) -> None:
        _write_csv(staging / "ipopt_cases.csv", _CASE_FIELDS, case_rows)
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
        result = run_diagnostic(args.config)
    else:
        prepare_preregistration(args.config)
        result = run_diagnostic(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
