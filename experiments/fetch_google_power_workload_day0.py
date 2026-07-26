"""Acquire a bounded Google ClusterData extract for one PDU and one day."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import re
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml
from google.cloud import bigquery

RAW_FILENAME = "records.csv.gz"
METADATA_FILENAME = "SOURCE_METADATA.json"
EXTRACT_QUERY_FILENAME = "extract_query.sql"
COMPACT_QUERY_FILENAME = "compact_query.sql"
HOURLY_QUERY_FILENAME = "hourly_query.sql"
MANIFEST_FILENAME = "SHA256SUMS"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_manifest(root: Path) -> bool:
    manifest_path = root / MANIFEST_FILENAME
    if not manifest_path.is_file():
        return False
    expected_paths: set[str] = set()
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        try:
            expected, relative = line.split("  ", maxsplit=1)
        except ValueError:
            return False
        expected_paths.add(relative)
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            return False
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.iterdir()
        if path.is_file() and path.name != MANIFEST_FILENAME
    }
    return actual_paths == expected_paths


def _mapping_fingerprint(
    path: Path,
    *,
    cell: str,
    pdu: str,
) -> tuple[int, str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        machine_ids = sorted(
            {
                int(row["machine_id"])
                for row in csv.DictReader(source)
                if row["cell"] == cell and row["pdu"] == pdu
            }
        )
    payload = "".join(f"{machine_id}\n" for machine_id in machine_ids)
    return len(machine_ids), hashlib.sha256(payload.encode()).hexdigest()


def _query_parameters(config: dict[str, Any]) -> list[Any]:
    parameters = config["parameters"]
    return [
        bigquery.ScalarQueryParameter("cell", "STRING", parameters["cell"]),
        bigquery.ScalarQueryParameter("pdu", "STRING", parameters["pdu"]),
        bigquery.ScalarQueryParameter(
            "window_start_us", "INT64", int(parameters["window_start_us"])
        ),
        bigquery.ScalarQueryParameter(
            "window_end_us", "INT64", int(parameters["window_end_us"])
        ),
    ]


def _schema_payload(fields: Iterable[Any]) -> list[dict[str, Any]]:
    return [
        {
            "name": field.name,
            "type": field.field_type,
            "mode": field.mode,
            "fields": _schema_payload(field.fields),
        }
        for field in fields
    ]


def _table_snapshots(client: Any, config: dict[str, Any]) -> dict[str, Any]:
    public_project = config["source"]["public_project"]
    expected = config["expected"]["table_snapshots"]
    snapshots: dict[str, Any] = {}
    for relative_id, frozen in expected.items():
        table_id = f"{public_project}.{relative_id}"
        table = client.get_table(table_id)
        actual = {
            "table_id": table_id,
            "etag": table.etag,
            "rows": int(table.num_rows),
            "bytes": int(table.num_bytes),
            "modified": table.modified.isoformat(),
            "time_partitioning": bool(table.time_partitioning),
            "range_partitioning": bool(table.range_partitioning),
            "clustering_fields": table.clustering_fields,
            "schema": _schema_payload(table.schema),
        }
        for key in ("etag", "rows", "bytes"):
            if actual[key] != frozen[key]:
                raise RuntimeError(
                    f"BigQuery table snapshot drifted for {relative_id}: {key}"
                )
        snapshots[relative_id] = actual
    return snapshots


def _extract_job_config(config: dict[str, Any], *, dry_run: bool) -> Any:
    cost_gate = config["cost_gate"]
    kwargs: dict[str, Any] = {
        "dry_run": dry_run,
        "use_query_cache": False,
        "query_parameters": _query_parameters(config),
        "labels": {"dataset": "google-power-workload", "schema": "day0-v1"},
    }
    if not dry_run:
        kwargs["maximum_bytes_billed"] = int(cost_gate["maximum_bytes_billed"])
    return bigquery.QueryJobConfig(**kwargs)


def _run_dry_run(client: Any, sql: str, config: dict[str, Any]) -> Any:
    job = client.query(
        sql,
        job_config=_extract_job_config(config, dry_run=True),
        location=config["source"]["location"],
    )
    expected_bytes = int(config["cost_gate"]["expected_dry_run_bytes"])
    if not job.dry_run or int(job.total_bytes_processed) != expected_bytes:
        raise RuntimeError(
            "BigQuery dry-run bytes drifted: "
            f"expected {expected_bytes}, found {job.total_bytes_processed}"
        )
    if expected_bytes > int(config["cost_gate"]["monthly_scan_budget_bytes"]):
        raise RuntimeError("Query exceeds the frozen monthly scan budget")
    return job


def _compact_job_config(config: dict[str, Any], *, dry_run: bool) -> Any:
    cost_gate = config["cost_gate"]
    parameters = config["parameters"]
    kwargs: dict[str, Any] = {
        "dry_run": dry_run,
        "use_query_cache": False,
        "query_parameters": [
            bigquery.ScalarQueryParameter(
                "window_start_us", "INT64", int(parameters["window_start_us"])
            ),
            bigquery.ScalarQueryParameter(
                "window_end_us", "INT64", int(parameters["window_end_us"])
            ),
        ],
        "labels": {"dataset": "google-power-workload", "schema": "compact-v1"},
    }
    if not dry_run:
        kwargs["maximum_bytes_billed"] = int(cost_gate["compact_maximum_bytes_billed"])
    return bigquery.QueryJobConfig(**kwargs)


def _run_compact_dry_run(
    client: Any,
    sql: str,
    config: dict[str, Any],
) -> Any:
    job = client.query(
        sql,
        job_config=_compact_job_config(config, dry_run=True),
        location=config["source"]["location"],
    )
    expected_bytes = int(config["cost_gate"]["expected_compact_dry_run_bytes"])
    if not job.dry_run or int(job.total_bytes_processed) != expected_bytes:
        raise RuntimeError(
            "BigQuery compact dry-run bytes drifted: "
            f"expected {expected_bytes}, found {job.total_bytes_processed}"
        )
    return job


def _hourly_job_config(config: dict[str, Any], *, dry_run: bool) -> Any:
    cost_gate = config["cost_gate"]
    kwargs: dict[str, Any] = {
        "dry_run": dry_run,
        "use_query_cache": False,
        "labels": {"dataset": "google-power-workload", "schema": "hourly-v1"},
    }
    if not dry_run:
        kwargs["maximum_bytes_billed"] = int(cost_gate["hourly_maximum_bytes_billed"])
    return bigquery.QueryJobConfig(**kwargs)


def _run_hourly_dry_run(client: Any, sql: str, config: dict[str, Any]) -> Any:
    job = client.query(
        sql,
        job_config=_hourly_job_config(config, dry_run=True),
        location=config["source"]["location"],
    )
    expected_bytes = int(config["cost_gate"]["expected_hourly_dry_run_bytes"])
    if not job.dry_run or int(job.total_bytes_processed) != expected_bytes:
        raise RuntimeError(
            "BigQuery hourly dry-run bytes drifted: "
            f"expected {expected_bytes}, found {job.total_bytes_processed}"
        )
    return job


def _validate_acquisition_budget(config: dict[str, Any]) -> int:
    cost_gate = config["cost_gate"]
    total = sum(
        int(cost_gate[key])
        for key in (
            "expected_dry_run_bytes",
            "expected_compact_dry_run_bytes",
            "expected_hourly_dry_run_bytes",
        )
    )
    if total > int(cost_gate["monthly_scan_budget_bytes"]):
        raise RuntimeError("Three-stage acquisition exceeds the monthly scan budget")
    return total


def _render_query_with_source(
    template: str,
    destination: Any,
) -> tuple[str, str]:
    table_id = f"{destination.project}.{destination.dataset_id}.{destination.table_id}"
    if re.fullmatch(r"[A-Za-z0-9_-]+\.[A-Za-z0-9_]+\.[A-Za-z0-9_]+", table_id) is None:
        raise ValueError(f"Unsafe BigQuery temporary table ID: {table_id}")
    token = "__SOURCE_TABLE__"
    if template.count(token) != 1:
        raise ValueError("Compact SQL must contain exactly one source-table token")
    return template.replace(token, table_id), table_id


def _csv_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("BigQuery returned a non-finite float")
        return format(value, ".17g")
    return str(value)


def _validate_row(
    values: dict[str, Any],
    *,
    window_start_us: int,
    window_end_us: int,
) -> None:
    record_type = values["record_type"]
    if record_type == "hourly_usage":
        hour = int(values["hour_index"])
        collection_type = int(values["collection_type"])
        tier = str(values["priority_tier"])
        if not 0 <= hour < 24 or collection_type not in {0, 1}:
            raise ValueError("Invalid hourly usage key")
        if tier not in {
            "1_free",
            "2_beb",
            "3_mid",
            "4_production",
            "5_monitoring",
            "ambiguous",
            "unknown",
        }:
            raise ValueError("Unknown priority tier")
        for field in (
            "observed_cpu_ncu_lower",
            "observed_cpu_ncu_upper",
            "observed_cpu_time_ncu_seconds_lower",
            "observed_cpu_time_ncu_seconds_upper",
            "synthesized_cpu_time_ncu_seconds_lower",
            "synthesized_cpu_time_ncu_seconds_upper",
        ):
            number = float(values[field])
            if not math.isfinite(number) or number < 0.0:
                raise ValueError(f"Invalid hourly value: {field}")
        for field in (
            "observed_cpu_overlap_seconds",
            "missing_cpu_overlap_seconds",
            "cpu_conflict_overlap_seconds",
            "fragment_piece_count",
            "usage_group_count",
            "cpu_conflict_usage_group_count",
            "exact_duplicate_usage_group_count",
        ):
            if int(values[field]) < 0:
                raise ValueError(f"Invalid hourly count: {field}")
        for bound in ("lower", "upper"):
            if not math.isclose(
                float(values[f"observed_cpu_ncu_{bound}"]) * 3600.0,
                float(values[f"observed_cpu_time_ncu_seconds_{bound}"]),
                rel_tol=1e-10,
                abs_tol=1e-8,
            ):
                raise ValueError("Hourly CPU average and CPU-time do not agree")
        if float(values["observed_cpu_ncu_lower"]) > float(
            values["observed_cpu_ncu_upper"]
        ):
            raise ValueError("Hourly CPU uncertainty bounds are inverted")
        if float(values["synthesized_cpu_time_ncu_seconds_lower"]) > float(
            values["synthesized_cpu_time_ncu_seconds_upper"]
        ):
            raise ValueError("Synthesized CPU-time bounds are inverted")
    elif record_type == "machine_event":
        if (
            values["machine_event_time"] is None
            or int(values["machine_event_time"]) < 0
            or int(values["machine_event_time"]) >= window_end_us
        ):
            raise ValueError("Machine event has an invalid timestamp")
        if values["machine_id"] is None:
            raise ValueError("Machine event has no machine ID")
        if int(values["machine_event_type"]) not in {1, 2, 3}:
            raise ValueError("Unknown machine event type")
        capacity = values["capacity_cpus"]
        if capacity is not None and (
            not math.isfinite(float(capacity)) or float(capacity) < 0.0
        ):
            raise ValueError("Machine event has invalid CPU capacity")
    elif record_type == "audit":
        if not values["audit_json"]:
            raise ValueError("Hourly extract has an empty audit record")
        json.loads(str(values["audit_json"]))
    else:
        raise ValueError(f"Unknown BigQuery record type: {record_type}")


def _write_result(
    path: Path,
    rows: Iterable[Any],
    fields: list[str],
    *,
    window_start_us: int,
    window_end_us: int,
) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    audit: dict[str, Any] | None = None
    missing_cpu_overlap_seconds = 0
    ambiguous_cpu_time_ncu_seconds = [0.0, 0.0]
    unknown_cpu_time_ncu_seconds = [0.0, 0.0]
    hourly_keys: set[tuple[int, int, str]] = set()
    with path.open("wb") as raw_output:
        with gzip.GzipFile(fileobj=raw_output, mode="wb", mtime=0) as compressed:
            with io.TextIOWrapper(
                compressed, encoding="utf-8", newline="", write_through=True
            ) as output:
                writer = csv.DictWriter(
                    output,
                    fieldnames=fields,
                    lineterminator="\n",
                )
                writer.writeheader()
                for row in rows:
                    values = {field: row[field] for field in fields}
                    _validate_row(
                        values,
                        window_start_us=window_start_us,
                        window_end_us=window_end_us,
                    )
                    counts[str(values["record_type"])] += 1
                    if values["record_type"] == "hourly_usage":
                        hourly_key = (
                            int(values["hour_index"]),
                            int(values["collection_type"]),
                            str(values["priority_tier"]),
                        )
                        if hourly_key in hourly_keys:
                            raise ValueError(
                                f"Duplicate hourly usage key: {hourly_key}"
                            )
                        hourly_keys.add(hourly_key)
                        missing_cpu_overlap_seconds += int(
                            values["missing_cpu_overlap_seconds"]
                        )
                        if values["priority_tier"] == "ambiguous":
                            ambiguous_cpu_time_ncu_seconds[0] += float(
                                values["observed_cpu_time_ncu_seconds_lower"]
                            )
                            ambiguous_cpu_time_ncu_seconds[1] += float(
                                values["observed_cpu_time_ncu_seconds_upper"]
                            )
                        elif values["priority_tier"] == "unknown":
                            unknown_cpu_time_ncu_seconds[0] += float(
                                values["observed_cpu_time_ncu_seconds_lower"]
                            )
                            unknown_cpu_time_ncu_seconds[1] += float(
                                values["observed_cpu_time_ncu_seconds_upper"]
                            )
                    elif values["record_type"] == "audit":
                        audit = json.loads(str(values["audit_json"]))
                    writer.writerow(
                        {field: _csv_value(values[field]) for field in fields}
                    )
    if set(counts) != {"hourly_usage", "machine_event", "audit"}:
        raise RuntimeError(f"Incomplete BigQuery record types: {dict(counts)}")
    if counts["hourly_usage"] != 24 * 2 * 7 or counts["audit"] != 1:
        raise RuntimeError(f"Unexpected hourly or audit row count: {dict(counts)}")
    expected_hourly_keys = {
        (hour, collection_type, priority_tier)
        for hour in range(24)
        for collection_type in (0, 1)
        for priority_tier in (
            "1_free",
            "2_beb",
            "3_mid",
            "4_production",
            "5_monitoring",
            "ambiguous",
            "unknown",
        )
    }
    if hourly_keys != expected_hourly_keys:
        raise RuntimeError("BigQuery result does not contain the complete hourly grid")
    return {
        "record_counts": dict(sorted(counts.items())),
        "rows": sum(counts.values()),
        "missing_cpu_overlap_seconds": missing_cpu_overlap_seconds,
        "ambiguous_cpu_time_ncu_seconds_lower": ambiguous_cpu_time_ncu_seconds[0],
        "ambiguous_cpu_time_ncu_seconds_upper": ambiguous_cpu_time_ncu_seconds[1],
        "unknown_cpu_time_ncu_seconds_lower": unknown_cpu_time_ncu_seconds[0],
        "unknown_cpu_time_ncu_seconds_upper": unknown_cpu_time_ncu_seconds[1],
        "audit": audit,
    }


def _isoformat(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _query_parameters_payload(parameters: Iterable[Any] | None) -> list[dict[str, Any]]:
    return [
        {
            "name": parameter.name,
            "type": str(parameter.type_).upper(),
            "value": parameter.value,
        }
        for parameter in (parameters or ())
    ]


def _destination_table_id(destination: Any) -> str:
    return f"{destination.project}.{destination.dataset_id}.{destination.table_id}"


def _job_payload(job: Any) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "destination_table": _destination_table_id(job.destination),
        "created": _isoformat(job.created),
        "started": _isoformat(job.started),
        "ended": _isoformat(job.ended),
        "cache_hit": bool(job.cache_hit),
        "total_bytes_processed": int(job.total_bytes_processed),
        "total_bytes_billed": int(job.total_bytes_billed),
        "maximum_bytes_billed": int(job.maximum_bytes_billed),
        "labels": dict(sorted(job.labels.items())),
        "query_parameters": _query_parameters_payload(job.query_parameters),
    }


def _temporary_result_payload(client: Any, job: Any) -> dict[str, Any]:
    table = client.get_table(job.destination)
    if table.expires is None:
        raise RuntimeError("Anonymous BigQuery result table has no expiration")
    return {
        "table_id": _destination_table_id(job.destination),
        "created": _isoformat(table.created),
        "expires": _isoformat(table.expires),
        "rows": int(table.num_rows),
        "bytes": int(table.num_bytes),
    }


def _query_parameter_signature(parameters: Iterable[Any] | None) -> tuple[Any, ...]:
    if parameters is None:
        raise RuntimeError("BigQuery job does not expose its query parameters")
    signature = tuple(
        sorted(
            (parameter.name, str(parameter.type_).upper(), parameter.value)
            for parameter in parameters
        )
    )
    names = [name for name, _type, _value in signature]
    if len(names) != len(set(names)):
        raise RuntimeError("BigQuery job has duplicate query-parameter names")
    return signature


def _validate_job_query_parameters(job: Any, expected: Iterable[Any]) -> None:
    actual_signature = _query_parameter_signature(
        getattr(job, "query_parameters", None)
    )
    expected_signature = _query_parameter_signature(expected)
    if actual_signature != expected_signature:
        raise RuntimeError(
            "Resumed BigQuery job used different query parameters: "
            f"expected {expected_signature}, found {actual_signature}"
        )


def _validate_extract_job(
    job: Any,
    sql: str,
    config: dict[str, Any],
) -> list[str]:
    iterator = job.result(max_results=0)
    if (
        hashlib.sha256(job.query.encode()).hexdigest()
        != config["source"]["query_sha256"]
    ):
        raise RuntimeError("Resumed extract job used different SQL")
    _validate_job_query_parameters(job, _query_parameters(config))
    expected_bytes = int(config["cost_gate"]["expected_dry_run_bytes"])
    if int(job.total_bytes_processed) != expected_bytes:
        raise RuntimeError("Executed BigQuery bytes differ from the dry-run gate")
    if int(job.total_bytes_billed) > int(config["cost_gate"]["maximum_bytes_billed"]):
        raise RuntimeError("Executed BigQuery job exceeded its billing cap")
    if job.destination is None:
        raise RuntimeError("BigQuery extract job has no temporary result table")
    fields = [field.name for field in iterator.schema]
    if fields != list(config["expected"]["extract_fields"]):
        raise RuntimeError(f"BigQuery extract schema drifted: {fields}")
    return fields


def _validate_compact_job(
    job: Any,
    sql: str,
    config: dict[str, Any],
) -> list[str]:
    iterator = job.result(max_results=0)
    if (
        hashlib.sha256(job.query.encode()).hexdigest()
        != hashlib.sha256(sql.encode()).hexdigest()
    ):
        raise RuntimeError("Resumed compact job used different SQL")
    _validate_job_query_parameters(
        job,
        _compact_job_config(config, dry_run=True).query_parameters,
    )
    expected_bytes = int(config["cost_gate"]["expected_compact_dry_run_bytes"])
    if int(job.total_bytes_processed) != expected_bytes:
        raise RuntimeError("Compact query bytes differ from its dry-run gate")
    if int(job.total_bytes_billed) > int(
        config["cost_gate"]["compact_maximum_bytes_billed"]
    ):
        raise RuntimeError("Compact query exceeded its billing cap")
    if job.destination is None:
        raise RuntimeError("Compact query has no temporary result table")
    fields = [field.name for field in iterator.schema]
    if fields != list(config["expected"]["compact_fields"]):
        raise RuntimeError(f"BigQuery compact schema drifted: {fields}")
    return fields


def _validate_existing_output(
    output_root: Path,
    metadata: dict[str, Any],
    config: dict[str, Any],
    *,
    mapping_count: int,
    mapping_sha: str,
    extract_job_id: str | None,
    compact_job_id: str | None,
) -> None:
    source = config["source"]
    parameters = config["parameters"]
    expected = config["expected"]
    cost_gate = config["cost_gate"]
    if metadata.get("query_parameters") != parameters:
        raise RuntimeError("Existing BigQuery extract used different parameters")
    expected_values = {
        "schema": "google_power_workload_bigquery_hourly_extract_v1",
        "dataset": source["dataset"],
        "billing_project": source["billing_project"],
        "public_project": source["public_project"],
        "location": source["location"],
        "documentation_commit": source["documentation_commit"],
        "query_sha256": source["query_sha256"],
        "compact_query_sha256": source["compact_query_sha256"],
        "hourly_query_sha256": source["hourly_query_sha256"],
        "population_rule": parameters["population_rule"],
        "mapping_machine_count": mapping_count,
        "mapping_machine_ids_sha256": mapping_sha,
        "dry_run_bytes": int(cost_gate["expected_dry_run_bytes"]),
        "maximum_bytes_billed": int(cost_gate["maximum_bytes_billed"]),
        "compact_dry_run_bytes": int(cost_gate["expected_compact_dry_run_bytes"]),
        "compact_maximum_bytes_billed": int(cost_gate["compact_maximum_bytes_billed"]),
        "hourly_dry_run_bytes": int(cost_gate["expected_hourly_dry_run_bytes"]),
        "hourly_maximum_bytes_billed": int(cost_gate["hourly_maximum_bytes_billed"]),
        "extract_fields": list(expected["extract_fields"]),
        "compact_fields": list(expected["compact_fields"]),
        "fields": list(expected["hourly_fields"]),
        "absolute_power_mw_available": False,
        "flexibility_observed": False,
        "recovery_parameters_observed": False,
    }
    for key, expected_value in expected_values.items():
        if metadata.get(key) != expected_value:
            raise RuntimeError(f"Existing BigQuery extract contract drifted: {key}")
    query_files = {
        EXTRACT_QUERY_FILENAME: source["query_sha256"],
        COMPACT_QUERY_FILENAME: source["compact_query_sha256"],
        HOURLY_QUERY_FILENAME: source["hourly_query_sha256"],
    }
    for filename, digest in query_files.items():
        if _sha256(output_root / filename) != digest:
            raise RuntimeError(f"Existing BigQuery query copy drifted: {filename}")
    if metadata.get("result_sha256") != _sha256(output_root / RAW_FILENAME):
        raise RuntimeError("Existing BigQuery result hash drifted")
    for relative_id, frozen in expected["table_snapshots"].items():
        actual = metadata.get("source_tables", {}).get(relative_id, {})
        if any(actual.get(key) != frozen[key] for key in ("etag", "rows", "bytes")):
            raise RuntimeError(
                f"Existing BigQuery source snapshot drifted: {relative_id}"
            )
    expected_jobs = {
        "extract_job": {
            "labels": {"dataset": "google-power-workload", "schema": "day0-v1"},
            "maximum_bytes_billed": int(cost_gate["maximum_bytes_billed"]),
            "query_parameters": _query_parameters_payload(_query_parameters(config)),
        },
        "compact_job": {
            "labels": {"dataset": "google-power-workload", "schema": "compact-v1"},
            "maximum_bytes_billed": int(cost_gate["compact_maximum_bytes_billed"]),
            "query_parameters": _query_parameters_payload(
                _compact_job_config(config, dry_run=True).query_parameters
            ),
        },
        "hourly_job": {
            "labels": {"dataset": "google-power-workload", "schema": "hourly-v1"},
            "maximum_bytes_billed": int(cost_gate["hourly_maximum_bytes_billed"]),
            "query_parameters": [],
        },
    }
    for job_name, expected_job in expected_jobs.items():
        actual_job = metadata.get(job_name, {})
        for key, expected_value in expected_job.items():
            if actual_job.get(key) != expected_value:
                raise RuntimeError(
                    f"Existing BigQuery {job_name} contract drifted: {key}"
                )
    successful_jobs = [metadata[name] for name in expected_jobs]
    if metadata.get("successful_jobs_total_bytes_processed") != sum(
        job["total_bytes_processed"] for job in successful_jobs
    ) or metadata.get("successful_jobs_total_bytes_billed") != sum(
        job["total_bytes_billed"] for job in successful_jobs
    ):
        raise RuntimeError("Existing BigQuery successful-job cost audit drifted")
    if metadata.get("monthly_scan_budget_bytes") != int(
        cost_gate["monthly_scan_budget_bytes"]
    ):
        raise RuntimeError("Existing BigQuery monthly scan budget drifted")
    if metadata.get("monthly_acquisition_bytes_processed") != sum(
        job["total_bytes_processed"] for job in successful_jobs
    ):
        raise RuntimeError("Existing BigQuery acquisition byte total drifted")
    if metadata.get("temporary_query_result_cleanup") != (
        "bigquery_automatic_expiry_not_deleted_by_fetcher"
    ):
        raise RuntimeError("Existing BigQuery temporary-result cleanup drifted")
    temporary_results = metadata.get("temporary_query_result_tables", {})
    for stage, job_name in (
        ("extract", "extract_job"),
        ("compact", "compact_job"),
        ("hourly", "hourly_job"),
    ):
        table = temporary_results.get(stage, {})
        if (
            table.get("table_id") != metadata[job_name].get("destination_table")
            or not table.get("created")
            or not table.get("expires")
            or table.get("rows", 0) <= 0
            or table.get("bytes", 0) < 0
        ):
            raise RuntimeError(
                f"Existing BigQuery temporary-result audit drifted: {stage}"
            )
    result = metadata.get("result", {})
    record_counts = result.get("record_counts")
    if (
        not isinstance(record_counts, dict)
        or set(record_counts) != {"audit", "hourly_usage", "machine_event"}
        or record_counts["audit"] != 1
        or record_counts["hourly_usage"] != 24 * 2 * 7
        or record_counts["machine_event"] <= 0
    ):
        raise RuntimeError("Existing BigQuery extract record counts drifted")
    if result.get("rows") != sum(record_counts.values()):
        raise RuntimeError("Existing BigQuery extract row total drifted")
    requested_jobs = {
        "extract_job": extract_job_id,
        "compact_job": compact_job_id,
    }
    for key, requested_id in requested_jobs.items():
        if (
            requested_id is not None
            and metadata.get(key, {}).get("job_id") != requested_id
        ):
            raise RuntimeError(f"Existing BigQuery extract used a different {key}")


def run(
    config_path: Path,
    *,
    execute: bool = False,
    client: Any | None = None,
    extract_job_id: str | None = None,
    compact_job_id: str | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    parameters = config["parameters"]
    expected = config["expected"]
    query_path = Path(source["query_path"])
    sql = query_path.read_text(encoding="utf-8")
    if _sha256(query_path) != source["query_sha256"]:
        raise RuntimeError("Frozen BigQuery SQL hash drifted")
    compact_query_path = Path(source["compact_query_path"])
    compact_template = compact_query_path.read_text(encoding="utf-8")
    if _sha256(compact_query_path) != source["compact_query_sha256"]:
        raise RuntimeError("Frozen compact BigQuery SQL hash drifted")
    hourly_query_path = Path(source["hourly_query_path"])
    hourly_template = hourly_query_path.read_text(encoding="utf-8")
    if _sha256(hourly_query_path) != source["hourly_query_sha256"]:
        raise RuntimeError("Frozen hourly BigQuery SQL hash drifted")
    planned_acquisition_bytes = _validate_acquisition_budget(config)

    mapping_count, mapping_sha = _mapping_fingerprint(
        Path(source["mapping_source_path"]),
        cell=str(parameters["cell"]),
        pdu=str(parameters["pdu"]),
    )
    if mapping_count != int(expected["mapping_machine_count"]):
        raise RuntimeError("Local PDU mapping machine count drifted")
    if mapping_sha != expected["mapping_machine_ids_sha256"]:
        raise RuntimeError("Local PDU mapping machine IDs drifted")

    output_root = Path(source["output_directory"])
    if output_root.exists():
        if not _verify_manifest(output_root):
            raise RuntimeError("Existing BigQuery extract has an invalid manifest")
        metadata = json.loads(
            (output_root / METADATA_FILENAME).read_text(encoding="utf-8")
        )
        _validate_existing_output(
            output_root,
            metadata,
            config,
            mapping_count=mapping_count,
            mapping_sha=mapping_sha,
            extract_job_id=extract_job_id,
            compact_job_id=compact_job_id,
        )
        return metadata

    active_client = client or bigquery.Client(project=source["billing_project"])
    snapshots_before = _table_snapshots(active_client, config)
    dry_job = _run_dry_run(active_client, sql, config)
    dry_summary = {
        "dry_run": True,
        "total_bytes_processed": int(dry_job.total_bytes_processed),
        "maximum_bytes_billed": int(config["cost_gate"]["maximum_bytes_billed"]),
        "compact_expected_bytes": int(
            config["cost_gate"]["expected_compact_dry_run_bytes"]
        ),
        "hourly_expected_bytes": int(
            config["cost_gate"]["expected_hourly_dry_run_bytes"]
        ),
    }
    if not execute:
        return dry_summary

    if extract_job_id is None:
        extract_job = active_client.query(
            sql,
            job_config=_extract_job_config(config, dry_run=False),
            location=source["location"],
        )
    else:
        extract_job = active_client.get_job(
            extract_job_id,
            location=source["location"],
        )
    extract_fields = _validate_extract_job(extract_job, sql, config)
    snapshots_after = _table_snapshots(active_client, config)
    if snapshots_after != snapshots_before:
        raise RuntimeError("BigQuery source tables changed during acquisition")

    compact_sql, _ = _render_query_with_source(
        compact_template,
        extract_job.destination,
    )
    compact_dry_job = _run_compact_dry_run(active_client, compact_sql, config)
    if compact_job_id is None:
        compact_job = active_client.query(
            compact_sql,
            job_config=_compact_job_config(config, dry_run=False),
            location=source["location"],
        )
    else:
        compact_job = active_client.get_job(
            compact_job_id,
            location=source["location"],
        )
    compact_fields = _validate_compact_job(compact_job, compact_sql, config)

    hourly_sql, _ = _render_query_with_source(
        hourly_template,
        compact_job.destination,
    )
    hourly_dry_job = _run_hourly_dry_run(active_client, hourly_sql, config)
    total_planned_bytes = sum(
        int(job.total_bytes_processed)
        for job in (dry_job, compact_dry_job, hourly_dry_job)
    )
    if total_planned_bytes > int(config["cost_gate"]["monthly_scan_budget_bytes"]):
        raise RuntimeError("Three-stage acquisition exceeds the monthly scan budget")
    if total_planned_bytes != planned_acquisition_bytes:
        raise RuntimeError("BigQuery dry-run total differs from the preflight budget")

    hourly_job = active_client.query(
        hourly_sql,
        job_config=_hourly_job_config(config, dry_run=False),
        location=source["location"],
    )
    hourly_iterator = hourly_job.result(page_size=10_000)
    hourly_fields = [field.name for field in hourly_iterator.schema]
    if hourly_fields != list(expected["hourly_fields"]):
        raise RuntimeError(f"BigQuery hourly schema drifted: {hourly_fields}")
    if int(hourly_job.total_bytes_processed) != int(
        config["cost_gate"]["expected_hourly_dry_run_bytes"]
    ):
        raise RuntimeError("Hourly query bytes differ from its dry-run gate")

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            dir=output_root.parent,
            prefix=f".{output_root.name}.acquiring-",
        )
    )
    try:
        result_summary = _write_result(
            staging / RAW_FILENAME,
            hourly_iterator,
            hourly_fields,
            window_start_us=int(parameters["window_start_us"]),
            window_end_us=int(parameters["window_end_us"]),
        )
        shutil.copyfile(query_path, staging / EXTRACT_QUERY_FILENAME)
        shutil.copyfile(compact_query_path, staging / COMPACT_QUERY_FILENAME)
        shutil.copyfile(hourly_query_path, staging / HOURLY_QUERY_FILENAME)
        metadata = {
            "schema": "google_power_workload_bigquery_hourly_extract_v1",
            "dataset": source["dataset"],
            "billing_project": source["billing_project"],
            "public_project": source["public_project"],
            "location": source["location"],
            "license": source["license"],
            "documentation_commit": source["documentation_commit"],
            "query_sha256": source["query_sha256"],
            "compact_query_sha256": source["compact_query_sha256"],
            "hourly_query_sha256": source["hourly_query_sha256"],
            "query_parameters": parameters,
            "population_is_complete_pdu_workload": False,
            "population_rule": parameters["population_rule"],
            "mapping_machine_count": mapping_count,
            "mapping_machine_ids_sha256": mapping_sha,
            "dry_run_bytes": int(dry_job.total_bytes_processed),
            "maximum_bytes_billed": int(config["cost_gate"]["maximum_bytes_billed"]),
            "compact_dry_run_bytes": int(compact_dry_job.total_bytes_processed),
            "compact_maximum_bytes_billed": int(
                config["cost_gate"]["compact_maximum_bytes_billed"]
            ),
            "hourly_dry_run_bytes": int(hourly_dry_job.total_bytes_processed),
            "hourly_maximum_bytes_billed": int(
                config["cost_gate"]["hourly_maximum_bytes_billed"]
            ),
            "monthly_acquisition_bytes_processed": total_planned_bytes,
            "successful_jobs_total_bytes_processed": sum(
                int(job.total_bytes_processed)
                for job in (extract_job, compact_job, hourly_job)
            ),
            "successful_jobs_total_bytes_billed": sum(
                int(job.total_bytes_billed)
                for job in (extract_job, compact_job, hourly_job)
            ),
            "monthly_scan_budget_bytes": int(
                config["cost_gate"]["monthly_scan_budget_bytes"]
            ),
            "extract_job": _job_payload(extract_job),
            "compact_job": _job_payload(compact_job),
            "hourly_job": _job_payload(hourly_job),
            "temporary_query_result_cleanup": (
                "bigquery_automatic_expiry_not_deleted_by_fetcher"
            ),
            "temporary_query_result_tables": {
                "extract": _temporary_result_payload(active_client, extract_job),
                "compact": _temporary_result_payload(active_client, compact_job),
                "hourly": _temporary_result_payload(active_client, hourly_job),
            },
            "result": result_summary,
            "result_sha256": _sha256(staging / RAW_FILENAME),
            "extract_fields": extract_fields,
            "compact_fields": compact_fields,
            "fields": hourly_fields,
            "source_tables": snapshots_before,
            "evidence_status": (
                "observed_same_system_cluster_usage_and_priority_extract"
            ),
            "absolute_power_mw_available": False,
            "flexibility_observed": False,
            "recovery_parameters_observed": False,
            "google_cloud_bigquery_version": bigquery.__version__,
        }
        (staging / METADATA_FILENAME).write_text(
            json.dumps(metadata, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest_paths = sorted(path for path in staging.iterdir() if path.is_file())
        (staging / MANIFEST_FILENAME).write_text(
            "".join(f"{_sha256(path)}  {path.name}\n" for path in manifest_paths),
            encoding="ascii",
        )
        if not _verify_manifest(staging):
            raise RuntimeError("Staged BigQuery manifest verification failed")
        staging.replace(output_root)
        return metadata
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/google_power_workload_day0.yaml"),
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Run the paid query after all dry-run and source-snapshot checks pass.",
    )
    parser.add_argument(
        "--extract-job-id",
        help="Reuse a completed guarded extract job instead of scanning public tables again.",
    )
    parser.add_argument(
        "--compact-job-id",
        help="Reuse a completed compact job instead of rebuilding priority fragments.",
    )
    args = parser.parse_args()
    print(
        json.dumps(
            run(
                args.config,
                execute=args.execute,
                extract_job_id=args.extract_job_id,
                compact_job_id=args.compact_job_id,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
