"""Build and verify the offline RQ2 public-data delivery catalog."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Iterator

import yaml

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/rq2_public_data_delivery_v1.DRAFT.yaml"
DEFAULT_OUTPUT = ROOT / "data/processed/rq2_public_data_delivery_v1_non_authoritative"
EVIDENCE_CLASSES = {
    "observed_source_value",
    "derived_from_observed_source",
    "derived_benchmark",
}
ROLES = {"identifier", "value", "diagnostic"}
DATASET_IDS = {
    "google_pdu17_744h_pair",
    "google_power_57_domains",
    "google_pdu17_capacity",
    "zeus_four_gpu_power_performance",
    "alibaba_job_execution_envelopes",
    "alibaba_gpu_telemetry",
    "alibaba_dimensionless_workload_blocks_v3",
    "rts_gmlc_power_blocks_v4",
    "rts_gmlc_cfe_deficit_v2",
    "nlr_genai_power_profiles_v2",
    "wattgpu_power_reference_v1",
    "continuation_availability_audit_v1",
}
TRUE_GATES = {
    "local_delivery_catalog_available",
    "offline_validation_and_loading_available",
    "google_unfiltered_alignment_available",
}
REQUIRED_FALSE_GATES = {
    "empirical_joint_distribution_ready",
    "direct_job_to_power_mapping_ready",
    "power_quality_flag_semantics_resolved",
    "complete_pdu_population_observed",
    "absolute_power_mw_available",
    "flexibility_contract_parameters_ready",
    "continuous_service_protocol_registered",
    "continuous_model_input_ready",
    "full_rq2_experiment_input_ready",
    "formal_experiment_authorized",
    "formal_result",
    "paper_claim",
    "security_certified",
}
REQUIRED_NULL_INPUTS = {
    "service_deadline",
    "recovery_deadline",
    "shared_flexibility_budget",
    "recovery_headroom",
    "recovery_efficiency",
    "absolute_google_pdu_power_mw",
    "observed_job_to_power_mapping",
    "flexible_fraction",
    "recoverable_fraction",
    "checkpoint_state",
    "preemptibility",
    "response_time_limit",
    "maximum_event_duration",
    "minimum_rest_time",
    "event_count_limit",
    "energy_debt_limit",
    "accounting_period_id",
    "initial_recovery_debt_carry_in",
    "maximum_recovery_power",
    "call_limit",
}
PROTOCOL_CHOICES = {
    "delivery_new_split",
    "cross_source_coupling",
    "raw_workload_fraction_above_one_mapping",
    "tail_handling",
    "censoring_estimand",
    "deadline_and_recovery_accounting",
}
OBSERVED_INPUTS = {
    "google_pdu_measured_power_ratio",
    "alibaba_anonymized_job_and_utilization_trace",
    "zeus_gpu_power_and_epoch_time",
    "nlr_compute_node_power_profiles",
    "wattgpu_device_power_experiments",
}
DERIVED_INPUTS = {
    "google_cpu_hourly_endpoints",
    "google_pdu17_hourly_capacity_integrals",
    "google_hourly_power_means",
    "alibaba_job_execution_envelopes",
    "alibaba_dimensionless_workload_blocks",
    "rts_gmlc_cfe_and_outage_blocks",
}
DELIVERY_FILES = {
    "README.md",
    "catalog.json",
    "data_dictionary.json",
    "google_pdu17_hourly_flat.jsonl.gz",
    "google_raw_origin_24h_blocks.json",
    "input_status.json",
    "summary.json",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty repository path")
    candidate = (ROOT / value).resolve()
    try:
        candidate.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} leaves the repository") from exc
    return candidate


def _json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")


def _flatten_fields(value: object, prefix: str = "") -> dict[str, str]:
    fields: dict[str, str] = {}
    if isinstance(value, dict):
        for key in sorted(value):
            child = f"{prefix}.{key}" if prefix else key
            fields.update(_flatten_fields(value[key], child))
    elif isinstance(value, list):
        child = prefix + ".item"
        if value:
            fields.update(_flatten_fields(value[0], child))
        else:
            fields[child] = "empty_list"
    else:
        fields[prefix] = type(value).__name__
    return fields


def _open_text(path: Path, fmt: str):
    if fmt in {"csv_gzip", "jsonl_gzip"}:
        return gzip.open(path, "rt", encoding="utf-8", newline="")
    return path.open("rt", encoding="utf-8", newline="")


def _schema_and_count(path: Path, fmt: str) -> tuple[dict[str, str], int]:
    if fmt in {"csv", "csv_gzip"}:
        with _open_text(path, fmt) as source:
            reader = csv.reader(source)
            try:
                header = next(reader)
            except StopIteration as exc:
                raise ValueError(f"empty CSV: {path}") from exc
            if not header or len(header) != len(set(header)):
                raise ValueError(f"invalid or duplicate CSV header: {path}")
            rows = 0
            for row in reader:
                if len(row) != len(header):
                    raise ValueError(f"CSV row width drifted: {path}")
                rows += 1
        return {name: "csv_string" for name in header}, rows
    if fmt == "jsonl_gzip":
        first: object | None = None
        rows = 0
        with _open_text(path, fmt) as source:
            for line in source:
                if not line.strip():
                    continue
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"JSONL row is not an object: {path}")
                if first is None:
                    first = value
                rows += 1
        if first is None:
            raise ValueError(f"empty JSONL: {path}")
        return _flatten_fields(first), rows
    if fmt == "json":
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            raise ValueError(f"JSON document is not an object: {path}")
        return _flatten_fields(value), 1
    raise ValueError(f"unsupported format: {fmt}")


def _verify_json_manifest(package: Path, manifest_path: Path) -> dict[str, str]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError(f"invalid package manifest: {manifest_path}")
    normalized: dict[str, str] = {}
    for relative, expected in sorted(manifest.items()):
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ValueError(f"invalid package manifest entry: {manifest_path}")
        member = (package / relative).resolve()
        try:
            member.relative_to(package.resolve())
        except ValueError as exc:
            raise ValueError(f"manifest member leaves package: {relative}") from exc
        if _sha256(member) != expected:
            raise ValueError(f"package member hash drifted: {member}")
        normalized[relative] = expected
    return normalized


def _field_dictionary(
    dataset_id: str,
    dataset: dict[str, object],
    schema: dict[str, str],
) -> list[dict[str, object]]:
    groups = dataset["field_groups"]
    if not isinstance(groups, dict) or set(groups) != {"identifier", "diagnostic"} | EVIDENCE_CLASSES:
        raise ValueError(f"{dataset_id} field groups are incomplete")
    field_role: dict[str, str] = {}
    field_evidence: dict[str, str] = {}
    for role in ("identifier", "diagnostic"):
        for field in groups[role]:
            if field in field_role:
                raise ValueError(f"{dataset_id} field has duplicate role: {field}")
            field_role[field] = role
    for evidence in EVIDENCE_CLASSES:
        for field in groups[evidence]:
            if field in field_role:
                raise ValueError(f"{dataset_id} value field also has another role: {field}")
            field_role[field] = "value"
            field_evidence[field] = evidence
    defaults = dataset["role_origin_defaults"]
    overrides = dataset.get("field_origin_overrides", {})
    for field, role in field_role.items():
        if field not in field_evidence:
            evidence = overrides.get(field, defaults[role])
            if evidence not in EVIDENCE_CLASSES:
                raise ValueError(f"{dataset_id} field has invalid evidence class: {field}")
            field_evidence[field] = evidence
    if set(schema) != set(field_role) or set(schema) != set(field_evidence):
        missing = sorted(set(schema) - set(field_role))
        extra = sorted(set(field_role) - set(schema))
        raise ValueError(
            f"{dataset_id} field contract drifted; missing={missing}, extra={extra}"
        )
    units = dataset.get("unit_overrides", {})
    missing_semantics = (
        "empty_field_loads_as_null; numeric_zero_is_preserved"
        if str(dataset["format"]).startswith("csv")
        else "JSON_null_is_preserved; numeric_zero_is_preserved"
    )
    return [
        {
            "dataset_id": dataset_id,
            "field": field,
            "storage_type": schema[field],
            "evidence_class": field_evidence[field],
            "role": field_role[field],
            "unit": units.get(field, "source_defined_or_not_applicable"),
            "missing_value_semantics": missing_semantics,
        }
        for field in sorted(schema)
    ]


def _validate_scientific_boundaries(
    summaries: dict[str, dict[str, object]], config: dict[str, object]
) -> None:
    pair = summaries["google_pdu17_744h_pair"]
    if pair["contract"]["hours"] != 744 or pair["contract"]["raw_origin_24h_blocks"] != 31:
        raise ValueError("Google 744-hour delivery contract drifted")
    if pair["interpretation"]["power_quality_flag_semantics_resolved"]:
        raise ValueError("Google power quality semantics must remain unresolved")
    prepare = summaries["google_power_57_domains"]
    if prepare["interpretation"]["absolute_power_mw_available"]:
        raise ValueError("Google normalized power cannot be relabeled as MW")
    envelope = summaries["alibaba_job_execution_envelopes"]
    if any(
        envelope["evidence_status"][key]
        for key in (
            "deadline_observed",
            "checkpoint_state_observed",
            "recoverable_fraction_inferred",
            "power_conversion_applied",
        )
    ):
        raise ValueError("Alibaba envelope evidence boundary drifted")
    telemetry = summaries["alibaba_gpu_telemetry"]
    if telemetry["evidence_status"]["continuous_time_series"]:
        raise ValueError("Alibaba telemetry is not a continuous time series")
    workload = summaries["alibaba_dimensionless_workload_blocks_v3"]
    if workload["workload_fraction_is_power"] or workload["deadline_observed"]:
        raise ValueError("Alibaba workload-block interpretation drifted")
    rts = summaries["rts_gmlc_power_blocks_v4"]
    if rts["security_certified"] or rts["grid_need_dispatch_completed"]:
        raise ValueError("RTS block gate drifted")
    cfe = summaries["rts_gmlc_cfe_deficit_v2"]
    if cfe["procurement_or_delivery_claimed"] or cfe["security_certified"]:
        raise ValueError("CFE benchmark boundary drifted")
    if summaries["nlr_genai_power_profiles_v2"]["evidence_status"][
        "direct_pai_gpu_to_power_mapping_ready"
    ]:
        raise ValueError("NLR direct mapping must remain false")
    if summaries["wattgpu_power_reference_v1"]["evidence_status"][
        "direct_pai_job_to_power_mapping_ready"
    ]:
        raise ValueError("WattGPU direct mapping must remain false")
    continuation = summaries["continuation_availability_audit_v1"]
    if any(
        continuation[key]
        for key in (
            "continuous_scientific_protocol_registered",
            "formal_execution_started",
            "formal_result",
            "full_joint_service_continuation_ready",
            "paper_claim",
            "security_certified",
        )
    ):
        raise ValueError("continuation audit boundary drifted")
    if continuation["workload_chronology"]["raw_fraction_was_clipped"]:
        raise ValueError("raw workload fractions must not be clipped")
    gates = config["gates"]
    if any(gates[name] is not False for name in REQUIRED_FALSE_GATES):
        raise ValueError("scientific/model/formal gates must remain false")
    for name in TRUE_GATES:
        if gates[name] is not True:
            raise ValueError(f"implemented delivery gate must remain true: {name}")
    unidentified = config["conceptual_inputs"]["unidentified"]
    names = {row["name"] for row in unidentified}
    if names != REQUIRED_NULL_INPUTS or any(row["value"] is not None for row in unidentified):
        raise ValueError("unidentified inputs must be complete and null")
    if any(
        row.get("value") is not None or row.get("status") != "unregistered"
        for row in config["protocol_choices"].values()
    ):
        raise ValueError("delivery must not select a scientific protocol")


def _load_and_validate_config(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_bytes())
    if config["schema"] != "rq2_public_data_delivery_config_v1":
        raise ValueError("delivery config schema drifted")
    if config["status"] != "DRAFT_NONAUTHORITATIVE_LOCAL_DATA_DELIVERY":
        raise ValueError("delivery status drifted")
    if config["output"] != {
        "directory": "data/processed/rq2_public_data_delivery_v1_non_authoritative",
        "schema": "rq2_public_data_delivery_v1",
    }:
        raise ValueError("delivery output contract drifted")
    if set(config.get("datasets", {})) != DATASET_IDS:
        raise ValueError("delivery dataset inventory drifted")
    if set(config.get("gates", {})) != REQUIRED_FALSE_GATES | TRUE_GATES:
        raise ValueError("delivery gate inventory drifted")
    if set(config.get("protocol_choices", {})) != PROTOCOL_CHOICES:
        raise ValueError("delivery protocol-choice inventory drifted")
    conceptual = config.get("conceptual_inputs", {})
    if set(conceptual) != {"observed", "derived", "unidentified"}:
        raise ValueError("delivery conceptual-input sections drifted")
    if {row.get("name") for row in conceptual["observed"]} != OBSERVED_INPUTS:
        raise ValueError("observed conceptual-input inventory drifted")
    if {row.get("name") for row in conceptual["derived"]} != DERIVED_INPUTS:
        raise ValueError("derived conceptual-input inventory drifted")
    return config


def _build_catalog(config: dict[str, object]) -> tuple[dict[str, object], list[dict[str, object]], dict[str, dict[str, object]]]:
    catalog: dict[str, object] = {}
    dictionary: list[dict[str, object]] = []
    summaries: dict[str, dict[str, object]] = {}
    for dataset_id, raw_dataset in config["datasets"].items():
        dataset = dict(raw_dataset)
        package = _path(dataset["package"], f"datasets.{dataset_id}.package")
        summary_path = _path(dataset["summary"], f"datasets.{dataset_id}.summary")
        primary = _path(dataset["primary"], f"datasets.{dataset_id}.primary")
        if _sha256(summary_path) != dataset["summary_sha256"]:
            raise ValueError(f"{dataset_id} summary hash drifted")
        if _sha256(primary) != dataset["primary_sha256"]:
            raise ValueError(f"{dataset_id} primary hash drifted")
        manifest_record = None
        if dataset.get("manifest") is not None:
            manifest_path = _path(dataset["manifest"], f"datasets.{dataset_id}.manifest")
            if _sha256(manifest_path) != dataset["manifest_sha256"]:
                raise ValueError(f"{dataset_id} manifest hash drifted")
            members = _verify_json_manifest(package, manifest_path)
            relative_primary = str(primary.relative_to(package)).replace("\\", "/")
            if members.get(relative_primary) != dataset["primary_sha256"]:
                raise ValueError(f"{dataset_id} primary is not bound by its manifest")
            manifest_record = {
                "path": str(manifest_path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": dataset["manifest_sha256"],
                "member_count": len(members),
            }
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if summary.get("schema") != dataset["expected_schema"]:
            raise ValueError(f"{dataset_id} summary schema drifted")
        if dataset.get("license_evidence") is not None:
            license_path = _path(dataset["license_evidence"], f"datasets.{dataset_id}.license_evidence")
            if _sha256(license_path) != dataset["license_evidence_sha256"]:
                raise ValueError(f"{dataset_id} license evidence drifted")
            license_record = {
                "identifier": dataset["license"],
                "evidence_path": str(license_path.relative_to(ROOT)).replace("\\", "/"),
                "evidence_sha256": dataset["license_evidence_sha256"],
                "legal_conclusion": False,
            }
        else:
            license_record = {
                "identifier": None,
                "evidence_path": None,
                "evidence_sha256": None,
                "legal_conclusion": False,
            }
        schema, records = _schema_and_count(primary, dataset["format"])
        if records != dataset["records"]:
            raise ValueError(f"{dataset_id} row count drifted: {records}")
        field_rows = _field_dictionary(dataset_id, dataset, schema)
        dictionary.extend(field_rows)
        summaries[dataset_id] = summary
        entry = {
            "dataset_id": dataset_id,
            "package_path": str(package.relative_to(ROOT)).replace("\\", "/"),
            "manifest": manifest_record,
            "summary_path": str(summary_path.relative_to(ROOT)).replace("\\", "/"),
            "summary_sha256": dataset["summary_sha256"],
            "summary_schema": dataset["expected_schema"],
            "primary_path": str(primary.relative_to(ROOT)).replace("\\", "/"),
            "primary_sha256": dataset["primary_sha256"],
            "format": dataset["format"],
            "record_count": records,
            "schema_fields": sorted(schema),
            "field_evidence_class_counts": {
                evidence: sum(row["evidence_class"] == evidence for row in field_rows)
                for evidence in sorted(EVIDENCE_CLASSES)
            },
            "license": license_record,
            "time_basis": dataset["time_basis"],
            "units": dataset["units"],
            "intended_use": dataset["intended_use"],
            "limitations": dataset["limitations"],
        }
        if dataset_id == "alibaba_dimensionless_workload_blocks_v3":
            entry["preserved_existing_split"] = {
                "split_fraction": summary["split_fraction"],
                "split_hour": summary["split_hour"],
                "policy": summary["job_split_policy"],
                "new_delivery_split_selected": False,
            }
        elif dataset_id == "rts_gmlc_power_blocks_v4":
            entry["preserved_existing_split"] = {
                "split_hour": summary["split_hour"],
                "training_block_count": summary["training_block_count"],
                "holdout_block_count": summary["holdout_block_count"],
                "new_delivery_split_selected": False,
            }
        catalog[dataset_id] = entry
    _validate_scientific_boundaries(summaries, config)
    return catalog, dictionary, summaries


def _iter_raw_records(path: Path, fmt: str) -> Iterator[dict[str, object]]:
    if fmt in {"csv", "csv_gzip"}:
        with _open_text(path, fmt) as source:
            for row in csv.DictReader(source):
                yield {key: (value if value != "" else None) for key, value in row.items()}
        return
    if fmt == "jsonl_gzip":
        with _open_text(path, fmt) as source:
            for line in source:
                if line.strip():
                    yield json.loads(line)
        return
    if fmt == "json":
        yield json.loads(path.read_text(encoding="utf-8"))
        return
    raise ValueError(f"unsupported format: {fmt}")


def _build_google_flat(pair_path: Path) -> tuple[bytes, list[dict[str, object]]]:
    lines: list[bytes] = []
    blocks: list[dict[str, object]] = []
    block_hours: dict[int, list[dict[str, object]]] = {}
    for row in _iter_raw_records(pair_path, "jsonl_gzip"):
        hour = row["hour_index"]
        block_index = hour // 24
        flat = {
            "hour_index": hour,
            "raw_origin_24h_block_index": block_index,
            "hour_offset_in_raw_origin_block": hour % 24,
            "raw_interval_start_us": row["raw_interval_start_us"],
            "raw_interval_end_us": row["raw_interval_end_us"],
            "natural_calendar_day_identified": False,
            "cpu_hourly_endpoint_sum_lower_ncu": row["cpu"]["hourly_endpoint_sum_lower_ncu"],
            "cpu_hourly_endpoint_sum_upper_ncu": row["cpu"]["hourly_endpoint_sum_upper_ncu"],
            "cpu_conflict_overlap_seconds": row["cpu"]["cpu_conflict_overlap_seconds"],
            "cpu_missing_overlap_seconds": row["cpu"]["missing_cpu_overlap_seconds"],
            "cpu_source_strata_count": row["cpu"]["source_strata_count"],
            "cpu_strata": row["cpu"]["strata"],
            "measured_power_util_mean": row["power"]["measured_power_util_mean"],
            "production_power_util_mean": row["power"]["production_power_util_mean"],
            "power_bad_flag_pair_counts": row["power"]["bad_flag_pair_counts"],
            "power_quality_filter_applied": row["power"]["quality_filter_applied"],
            "power_sample_count": row["power"]["sample_count"],
            "capacity": row["capacity"],
        }
        lines.append(json.dumps(flat, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
        block_hours.setdefault(block_index, []).append(flat)
    if len(lines) != 744 or sorted(block_hours) != list(range(31)):
        raise ValueError("Google flattened coverage drifted")
    for block_index, rows in block_hours.items():
        if len(rows) != 24:
            raise ValueError(f"Google block {block_index} is not 24 hours")
        blocks.append(
            {
                "block_index": block_index,
                "hour_start": rows[0]["hour_index"],
                "hour_end_exclusive": rows[-1]["hour_index"] + 1,
                "raw_interval_start_us": rows[0]["raw_interval_start_us"],
                "raw_interval_end_us": rows[-1]["raw_interval_end_us"],
                "hours": 24,
                "natural_calendar_day_identified": False,
            }
        )
    return gzip.compress(b"".join(lines), compresslevel=9, mtime=0), blocks


def _workload_audit(path: Path) -> dict[str, object]:
    maximum: Decimal | None = None
    above_one = 0
    for row in _iter_raw_records(path, "csv_gzip"):
        value = Decimal(row["workload_fraction"])
        maximum = value if maximum is None else max(maximum, value)
        above_one += value > 1
    if maximum is None or maximum <= 1 or above_one != 6:
        raise ValueError("unclipped workload-fraction evidence drifted")
    return {
        "maximum_raw_workload_fraction": str(maximum),
        "rows_above_one": above_one,
        "values_were_clipped": False,
    }


def _input_status_doc(config: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "rq2_public_data_input_status_v1",
        "observed": config["conceptual_inputs"]["observed"],
        "derived": config["conceptual_inputs"]["derived"],
        "unidentified": config["conceptual_inputs"]["unidentified"],
        "protocol_choices": config["protocol_choices"],
        "gates": config["gates"],
    }


def _catalog_doc(catalog: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "rq2_public_data_catalog_v1",
        "status": "DRAFT_NONAUTHORITATIVE_LOCAL_DATA_DELIVERY",
        "dataset_count": len(catalog),
        "datasets": catalog,
    }


def _dictionary_doc(dictionary: list[dict[str, object]]) -> dict[str, object]:
    return {
        "schema": "rq2_public_data_dictionary_v1",
        "evidence_class_axis": sorted(EVIDENCE_CLASSES),
        "role_axis": sorted(ROLES),
        "fields": dictionary,
    }


def _summary_doc(
    config_path: Path,
    config: dict[str, object],
    catalog: dict[str, object],
    dictionary: list[dict[str, object]],
    summaries: dict[str, dict[str, object]],
    output_bindings: dict[str, str],
) -> dict[str, object]:
    workload_path = _path(
        config["datasets"]["alibaba_dimensionless_workload_blocks_v3"]["primary"],
        "Alibaba workload blocks",
    )
    return {
        "schema": config["output"]["schema"],
        "status": "DRAFT_NONAUTHORITATIVE_LOCAL_DATA_DELIVERY_COMPLETE",
        "config_sha256": _sha256(config_path),
        "implementation_sha256": _sha256(Path(__file__)),
        "dataset_count": len(catalog),
        "dictionary_field_count": len(dictionary),
        "google_flattened_hours": 744,
        "google_raw_origin_24h_blocks": 31,
        "workload_raw_value_audit": _workload_audit(workload_path),
        "output_bindings": output_bindings,
        "source_summary_bindings": {
            dataset_id: entry["summary_sha256"] for dataset_id, entry in catalog.items()
        },
        "scope": {
            "local_data_delivery_software_scope_complete": True,
            "new_query_jobs": 0,
            "new_downloads": 0,
            "solver_calls": 0,
            "model_parameters_changed": False,
            "model_ready": False,
            "formal_result": False,
        },
        "google_quality": {
            "quality_filter_applied": False,
            "flag_semantics_resolved": False,
            "flag_pair_counts": summaries["google_pdu17_744h_pair"]["quality_audit"]["power_bad_flag_pair_counts"],
        },
    }


def _readme() -> str:
    return """# RQ2 public data delivery v1

This is the single offline entry point for the repository-local public-data packages used by RQ2. It is a `DRAFT_NONAUTHORITATIVE` delivery artifact, not a model-ready or formal-result bundle.

Validate every bound package, manifest, schema, row count, and delivery hash without network access:

```powershell
D:\\Miniconda3\\envs\\compute\\python.exe -B -m experiments.prepare_rq2_public_data_delivery_v1 --verify-existing
```

Load a small exact-value sample. CSV numbers remain strings, empty CSV fields become `None`, JSON numbers retain their JSON type, and no value is clipped or replaced with zero:

```python
from experiments.prepare_rq2_public_data_delivery_v1 import load_records
rows = load_records("alibaba_dimensionless_workload_blocks_v3", limit=3)
```

Files:

- `catalog.json`: paths, hashes, schemas, licenses where locally evidenced, time bases, units, uses, limitations, and preserved historical splits.
- `data_dictionary.json`: one row per primary field with separate evidence provenance and field role.
- `input_status.json`: observed/derived inputs, unidentified null inputs, unregistered protocol choices, and closed scientific gates.
- `google_pdu17_hourly_flat.jsonl.gz`: a convenience projection of the existing 744-hour pair; it preserves CPU endpoints/strata, power flag counts, and capacity unknowns.
- `google_raw_origin_24h_blocks.json`: 31 mechanical raw-origin blocks. They are not identified natural days or a selected split.
- `summary.json` and `FILE_HASHES.json`: delivery-scope status and byte bindings.

The Google power flags are retained without filtering. The official PDF and notebook still conflict on flag direction; the current official files were rechecked on 2026-09-12 with no identified correction, so the filtering rule remains unresolved. Existing Alibaba and RTS train/holdout splits are cataloged unchanged; this delivery makes no new split or cross-source coupling choice. Workload fractions above one remain exact source-derived strings.

All deadline, recovery, shared-budget, headroom, checkpoint, preemptibility, event-contract, and job-to-power inputs listed in `input_status.json` remain `null`. Local delivery completeness does not make the empirical dataset, continuous model, formal result, paper claim, or security certification complete.
"""


def run(config_path: Path = DEFAULT_CONFIG) -> dict[str, object]:
    config_path = config_path.resolve()
    config = _load_and_validate_config(config_path)
    catalog, dictionary, summaries = _build_catalog(config)
    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable delivery already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-"))
    try:
        catalog_doc = _catalog_doc(catalog)
        dictionary_doc = _dictionary_doc(dictionary)
        input_status = _input_status_doc(config)
        pair_path = _path(config["datasets"]["google_pdu17_744h_pair"]["primary"], "google pair")
        google_flat, blocks = _build_google_flat(pair_path)
        outputs = {
            "catalog.json": _json_bytes(catalog_doc),
            "data_dictionary.json": _json_bytes(dictionary_doc),
            "input_status.json": _json_bytes(input_status),
            "google_pdu17_hourly_flat.jsonl.gz": google_flat,
            "google_raw_origin_24h_blocks.json": _json_bytes(
                {"schema": "google_raw_origin_24h_blocks_v1", "blocks": blocks}
            ),
            "README.md": _readme().encode("utf-8"),
        }
        for name, content in outputs.items():
            (staging / name).write_bytes(content)
        output_bindings = {name: _sha256(staging / name) for name in sorted(outputs)}
        summary = _summary_doc(
            config_path, config, catalog, dictionary, summaries, output_bindings
        )
        (staging / "summary.json").write_bytes(_json_bytes(summary))
        file_hashes = {
            name: _sha256(staging / name)
            for name in sorted([*outputs, "summary.json"])
        }
        (staging / "FILE_HASHES.json").write_bytes(_json_bytes(file_hashes))
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary


def verify_existing(
    config_path: Path = DEFAULT_CONFIG,
    delivery_root: Path = DEFAULT_OUTPUT,
) -> dict[str, object]:
    config_path = config_path.resolve()
    config = _load_and_validate_config(config_path)
    delivery_root = delivery_root.resolve()
    summary = json.loads((delivery_root / "summary.json").read_text(encoding="utf-8"))
    if summary.get("schema") != "rq2_public_data_delivery_v1":
        raise ValueError("delivery summary schema drifted")
    if summary.get("config_sha256") != _sha256(config_path):
        raise ValueError("delivery config binding drifted")
    if summary.get("implementation_sha256") != _sha256(Path(__file__)):
        raise ValueError("delivery implementation binding drifted")
    file_hashes = json.loads((delivery_root / "FILE_HASHES.json").read_text(encoding="utf-8"))
    if set(file_hashes) != DELIVERY_FILES:
        raise ValueError("delivery file-hash inventory drifted")
    for relative, expected in file_hashes.items():
        if _sha256(delivery_root / relative) != expected:
            raise ValueError(f"delivery artifact hash drifted: {relative}")
    catalog, dictionary, summaries = _build_catalog(config)
    catalog_doc = json.loads((delivery_root / "catalog.json").read_text(encoding="utf-8"))
    if catalog_doc != _catalog_doc(catalog):
        raise ValueError("delivery catalog is stale")
    dictionary_doc = json.loads((delivery_root / "data_dictionary.json").read_text(encoding="utf-8"))
    if dictionary_doc != _dictionary_doc(dictionary):
        raise ValueError("delivery data dictionary is stale")
    expected_input_status = _input_status_doc(config)
    observed_input_status = json.loads(
        (delivery_root / "input_status.json").read_text(encoding="utf-8")
    )
    if observed_input_status != expected_input_status:
        raise ValueError("delivery input status is stale")
    pair_path = _path(
        config["datasets"]["google_pdu17_744h_pair"]["primary"], "google pair"
    )
    expected_flat, expected_blocks = _build_google_flat(pair_path)
    deterministic = {
        "catalog.json": _json_bytes(catalog_doc),
        "data_dictionary.json": _json_bytes(dictionary_doc),
        "input_status.json": _json_bytes(expected_input_status),
        "google_pdu17_hourly_flat.jsonl.gz": expected_flat,
        "google_raw_origin_24h_blocks.json": _json_bytes(
            {"schema": "google_raw_origin_24h_blocks_v1", "blocks": expected_blocks}
        ),
        "README.md": _readme().encode("utf-8"),
    }
    deterministic_hashes = {
        name: hashlib.sha256(content).hexdigest() for name, content in deterministic.items()
    }
    if summary.get("output_bindings") != deterministic_hashes:
        raise ValueError("delivery deterministic output binding drifted")
    expected_summary = _summary_doc(
        config_path,
        config,
        catalog,
        dictionary,
        summaries,
        deterministic_hashes,
    )
    if summary != expected_summary:
        raise ValueError("delivery summary content drifted")
    return summary


def iter_records(
    dataset_id: str,
    *,
    limit: int | None = None,
    delivery_root: Path = DEFAULT_OUTPUT,
    verify: bool = True,
) -> Iterator[dict[str, object]]:
    if limit is not None and limit < 0:
        raise ValueError("limit must be nonnegative or None")
    if verify:
        verify_existing(delivery_root=delivery_root)
    catalog = json.loads((delivery_root / "catalog.json").read_text(encoding="utf-8"))
    if dataset_id not in catalog["datasets"]:
        raise KeyError(f"unknown dataset_id: {dataset_id}")
    entry = catalog["datasets"][dataset_id]
    count = 0
    for row in _iter_raw_records(_path(entry["primary_path"], "catalog primary"), entry["format"]):
        if limit is not None and count >= limit:
            break
        yield row
        count += 1


def load_records(
    dataset_id: str,
    *,
    limit: int | None = 100,
    delivery_root: Path = DEFAULT_OUTPUT,
    verify: bool = True,
) -> list[dict[str, object]]:
    return list(
        iter_records(
            dataset_id,
            limit=limit,
            delivery_root=delivery_root,
            verify=verify,
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()
    result = verify_existing(args.config) if args.verify_existing else run(args.config)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
