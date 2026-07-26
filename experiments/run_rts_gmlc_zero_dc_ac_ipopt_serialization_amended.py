"""Publish the deterministic unique-header amendment of the IPOPT artifact."""

from __future__ import annotations

import argparse
import csv
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml

import experiments.run_rts_gmlc_zero_dc_ac_ipopt_diagnostic as parent
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import _sha256, _stable_json
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json
from src.scenarios.common_input_signature import common_input_signature_sha256

_CONFIG_PATH = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_ipopt_serialization_amendment.yaml"
)
_CONFIG_SHA256 = "f775f935dde758d17d8b969d186670d0285779095d48aa3e1a6ba434c5c87b1e"
_PARENT_CONFIG_PATH = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic.yaml"
)
_PARENT_RUNNER_PATH = Path("experiments/run_rts_gmlc_zero_dc_ac_ipopt_diagnostic.py")
_PARENT_CORE_PATH = Path("src/grid/rts_gmlc_ac_ipopt.py")
_PARENT_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v1"
)
_IMPLEMENTATION_PATH = Path(
    "experiments/run_rts_gmlc_zero_dc_ac_ipopt_serialization_amended.py"
)
_DUPLICATE_FIELD = "solver_objective_mw2"
_REMOVE_POSITION = 25
_RETAIN_POSITION = 43
_EXPECTED_ROWS = 96
_CORRECTED_CASE_FIELDS = tuple(
    field
    for position, field in enumerate(parent._CASE_FIELDS)
    if position != _REMOVE_POSITION
)


@dataclass(frozen=True)
class _AmendmentContext:
    config_path: Path
    config: dict[str, Any]
    parent_context: Any
    parent_registration: dict[str, Any]
    parent_summary: dict[str, Any]
    corrected_case_rows: tuple[tuple[str, ...], ...]
    output_root: Path
    input_contract: dict[str, Any]
    input_contract_sha256: str


def _read_config(config_path: Path) -> dict[str, Any]:
    if _sha256(config_path) != _CONFIG_SHA256:
        raise ValueError("RTS-GMLC IPOPT serialization config SHA-256 drifted")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    required = {
        "amendment",
        "parent_v1",
        "observed_serialization_issue",
        "deterministic_transformation",
        "interpretation",
        "evidence",
        "output",
    }
    if not isinstance(config, dict) or set(config) != required:
        raise ValueError("RTS-GMLC IPOPT serialization config schema drifted")
    amendment = config["amendment"]
    if (
        amendment.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_ipopt_serialization_amendment_v2"
        or amendment.get("solver_rerun_allowed") is not False
        or amendment.get("parent_outcomes_observed") is not True
    ):
        raise ValueError("RTS-GMLC IPOPT serialization amendment drifted")
    issue = config["observed_serialization_issue"]
    if issue != {
        "file": "ipopt_cases.csv",
        "parent_column_count": 71,
        "parent_unique_column_count": 70,
        "duplicate_field": _DUPLICATE_FIELD,
        "duplicate_zero_based_positions": [_REMOVE_POSITION, _RETAIN_POSITION],
        "parent_row_count": _EXPECTED_ROWS,
        "duplicate_values_identical_for_all_rows": True,
        "numerical_result_ambiguity": False,
        "detail_files_affected": False,
        "summary_affected": False,
    }:
        raise ValueError("RTS-GMLC IPOPT observed serialization issue drifted")
    transformation = config["deterministic_transformation"]
    if (
        transformation.get("remove_duplicate_zero_based_position") != _REMOVE_POSITION
        or transformation.get("retain_audit_zero_based_position_before_removal")
        != _RETAIN_POSITION
        or transformation.get("numeric_cell_reformatting_allowed") is not False
        or transformation.get("solver_call_count") != 0
        or transformation.get("parent_result_validator_required") is not True
    ):
        raise ValueError("RTS-GMLC IPOPT serialization transformation drifted")
    if config["output"] != {
        "directory": "results/tables/rts_gmlc_google_day0_zero_dc_ac_ipopt_diagnostic_v2"
    }:
        raise ValueError("RTS-GMLC IPOPT serialization output drifted")
    if (
        len(parent._CASE_FIELDS) != 71
        or len(_CORRECTED_CASE_FIELDS) != 70
        or len(set(_CORRECTED_CASE_FIELDS)) != 70
        or parent._CASE_FIELDS[_REMOVE_POSITION] != _DUPLICATE_FIELD
        or parent._CASE_FIELDS[_RETAIN_POSITION] != _DUPLICATE_FIELD
    ):
        raise RuntimeError("RTS-GMLC IPOPT in-code duplicate schema drifted")
    return config


def _load_parent(config: Mapping[str, Any]):
    spec = config["parent_v1"]
    if (
        Path(spec["config_path"]) != _PARENT_CONFIG_PATH
        or _sha256(_PARENT_CONFIG_PATH) != spec["config_sha256"]
        or Path(spec["implementation_path"]) != _PARENT_RUNNER_PATH
        or _sha256(_PARENT_RUNNER_PATH) != spec["implementation_sha256"]
        or Path(spec["core_path"]) != _PARENT_CORE_PATH
        or _sha256(_PARENT_CORE_PATH) != spec["core_sha256"]
        or Path(spec["output_directory"]) != _PARENT_OUTPUT_ROOT
    ):
        raise RuntimeError("RTS-GMLC IPOPT serialization parent implementation drifted")
    for subdirectory, key in (
        ("preregistration", "preregistration_manifest_sha256"),
        ("ipopt_diagnostic", "result_manifest_sha256"),
    ):
        target = _PARENT_OUTPUT_ROOT / subdirectory
        _verify_output_manifest(target)
        if _sha256(target / "SHA256SUMS") != spec[key]:
            raise RuntimeError(
                f"RTS-GMLC IPOPT serialization parent {subdirectory} drifted"
            )
    context = parent._build_context(_PARENT_CONFIG_PATH)
    registration = parent._require_preregistration(context, _PARENT_OUTPUT_ROOT)
    summary = parent._load_results(
        context, _PARENT_OUTPUT_ROOT / "ipopt_diagnostic", registration
    )
    if context.input_contract_sha256 != spec["input_contract_sha256"]:
        raise RuntimeError("RTS-GMLC IPOPT serialization parent contract drifted")
    return context, registration, summary


def _read_and_correct_parent_cases() -> tuple[tuple[str, ...], ...]:
    path = _PARENT_OUTPUT_ROOT / "ipopt_diagnostic" / "ipopt_cases.csv"
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.reader(source)
        header = tuple(next(reader))
        rows = tuple(tuple(row) for row in reader)
    duplicate_positions = tuple(
        position for position, field in enumerate(header) if field == _DUPLICATE_FIELD
    )
    if (
        header != parent._CASE_FIELDS
        or duplicate_positions != (_REMOVE_POSITION, _RETAIN_POSITION)
        or len(rows) != _EXPECTED_ROWS
        or any(len(row) != len(header) for row in rows)
        or any(row[_REMOVE_POSITION] != row[_RETAIN_POSITION] for row in rows)
    ):
        raise RuntimeError("RTS-GMLC IPOPT parent duplicate-column evidence drifted")
    corrected = tuple(
        tuple(
            value for position, value in enumerate(row) if position != _REMOVE_POSITION
        )
        for row in rows
    )
    if any(len(row) != len(_CORRECTED_CASE_FIELDS) for row in corrected):
        raise RuntimeError("RTS-GMLC IPOPT corrected row width drifted")
    return corrected


def _build_context(config_path: Path) -> _AmendmentContext:
    config = _read_config(config_path)
    parent_context, parent_registration, parent_summary = _load_parent(config)
    corrected_rows = _read_and_correct_parent_cases()
    contract = {
        "schema": "rts_gmlc_zero_dc_ac_ipopt_serialization_inputs_v2",
        "config_sha256": _sha256(config_path),
        "parent_v1": config["parent_v1"],
        "observed_serialization_issue": config["observed_serialization_issue"],
        "deterministic_transformation": config["deterministic_transformation"],
        "interpretation": config["interpretation"],
        "implementation_sha256": {
            _IMPLEMENTATION_PATH.as_posix(): _sha256(_IMPLEMENTATION_PATH)
        },
        "evidence": config["evidence"],
    }
    return _AmendmentContext(
        config_path=config_path,
        config=config,
        parent_context=parent_context,
        parent_registration=parent_registration,
        parent_summary=parent_summary,
        corrected_case_rows=corrected_rows,
        output_root=Path(config["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(context: _AmendmentContext, output_directory: Path | None) -> Path:
    return output_directory or context.output_root


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"RTS-GMLC IPOPT v2 artifact {root / name} drifted")
    return payload


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    target = output_root / "preregistration"
    amendment = context.config["amendment"]
    payload = {
        "schema": amendment["schema"],
        "amendment_id": amendment["id"],
        "status": amendment["status"],
        "externally_timestamped": False,
        "parent_outcomes_observed": True,
        "solver_rerun_allowed": False,
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }
    if target.exists():
        observed = _load_json(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published RTS-GMLC IPOPT v2 registration drifted")
        if (target / "config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published RTS-GMLC IPOPT v2 config drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare beside existing IPOPT v2 artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "registration.json")


def _require_preregistration(
    context: _AmendmentContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    registration = _load_json(target, "registration.json")
    if registration.get("input_contract") != _stable_json(context.input_contract):
        raise RuntimeError("RTS-GMLC IPOPT v2 live inputs drifted")
    if registration.get("input_contract_sha256") != context.input_contract_sha256:
        raise RuntimeError("RTS-GMLC IPOPT v2 live contract SHA drifted")
    if (target / "config.yaml").read_bytes() != context.config_path.read_bytes():
        raise RuntimeError("RTS-GMLC IPOPT v2 live config drifted")
    return registration


def _write_corrected_cases(path: Path, rows: Sequence[Sequence[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(_CORRECTED_CASE_FIELDS)
        writer.writerows(rows)


def _read_corrected_cases(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if tuple(reader.fieldnames or ()) != _CORRECTED_CASE_FIELDS or len(
            set(reader.fieldnames or ())
        ) != len(_CORRECTED_CASE_FIELDS):
            raise RuntimeError("RTS-GMLC IPOPT v2 case schema drifted")
        return list(reader)


def _corrected_summary(context: _AmendmentContext) -> dict[str, Any]:
    summary = dict(context.parent_summary)
    summary.update(
        {
            "schema": "rts_gmlc_zero_dc_ac_ipopt_diagnostic_results_v2",
            "serialization_amendment_id": context.config["amendment"]["id"],
            "parent_v1_result_manifest_sha256": context.config["parent_v1"][
                "result_manifest_sha256"
            ],
            "duplicate_case_column_removed": _DUPLICATE_FIELD,
            "corrected_case_column_count": len(_CORRECTED_CASE_FIELDS),
            "corrected_case_columns_unique": True,
            "scientific_outcomes_changed": False,
            "solver_rerun_count": 0,
            "canonical_tabular_artifact": True,
        }
    )
    return summary


def _validate_corrected_results(
    context: _AmendmentContext,
    target: Path,
) -> list[dict[str, str]]:
    case_rows = _read_corrected_cases(target / "ipopt_cases.csv")
    generator_rows = parent._csv_rows(
        target / "generator_results.csv", parent._GENERATOR_FIELDS
    )
    bus_rows = parent._csv_rows(target / "bus_results.csv", parent._BUS_FIELDS)
    branch_rows = parent._csv_rows(target / "branch_results.csv", parent._BRANCH_FIELDS)
    parent._validate_result_rows(
        context.parent_context,
        case_rows,
        generator_rows,
        bus_rows,
        branch_rows,
    )
    expected_parent_summary = _stable_json(
        parent._summary(
            context.parent_context,
            context.parent_registration,
            case_rows,
        )
    )
    if expected_parent_summary != context.parent_summary:
        raise RuntimeError("RTS-GMLC IPOPT v2 scientific outcomes drifted")
    return case_rows


def _load_results(
    context: _AmendmentContext,
    target: Path,
) -> dict[str, Any]:
    summary = _load_json(target, "summary.json")
    case_rows = _validate_corrected_results(context, target)
    if len(case_rows) != _EXPECTED_ROWS:
        raise RuntimeError("RTS-GMLC IPOPT v2 case count drifted")
    if summary != _stable_json(_corrected_summary(context)):
        raise RuntimeError("Published RTS-GMLC IPOPT v2 summary drifted")
    return summary


def run_amendment(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    _require_preregistration(context, output_root)
    target = output_root / "ipopt_diagnostic"
    if target.exists():
        return _load_results(context, target)
    parent_target = _PARENT_OUTPUT_ROOT / "ipopt_diagnostic"

    def writer(staging: Path) -> None:
        _write_corrected_cases(staging / "ipopt_cases.csv", context.corrected_case_rows)
        for name in (
            "generator_results.csv",
            "bus_results.csv",
            "branch_results.csv",
        ):
            shutil.copyfile(parent_target / name, staging / name)
        _write_json(staging / "summary.json", _corrected_summary(context))

    _publish_payload(target, writer)
    return _load_results(context, target)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=_CONFIG_PATH)
    parser.add_argument("--stage", choices=("prepare", "run", "all"), required=True)
    args = parser.parse_args()
    if args.stage == "prepare":
        result = prepare_preregistration(args.config)
    elif args.stage == "run":
        result = run_amendment(args.config)
    else:
        prepare_preregistration(args.config)
        result = run_amendment(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
