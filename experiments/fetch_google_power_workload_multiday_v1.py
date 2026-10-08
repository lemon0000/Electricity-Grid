"""Acquire a guarded full-month PDU17 hourly ClusterData aggregate."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml
from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from experiments.fetch_google_power_workload_day0 import (
    _job_payload,
    _mapping_fingerprint,
    _sha256,
    _table_snapshots,
    _temporary_result_payload,
    _validate_job_query_parameters,
    _verify_manifest,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/google_power_workload_multiday_v1.DRAFT.yaml"
LEGACY_HELPER = ROOT / "experiments/fetch_google_power_workload_day0.py"
LEGACY_HELPER_SHA256 = "a32a3c3fffbc5375c0b38ec6bf061d2cc6cefd8b35ec0591b6a561613af39582"
RAW_FILENAME = "records.csv.gz"
METADATA_FILENAME = "SOURCE_METADATA.json"
MANIFEST_FILENAME = "SHA256SUMS"
HOUR_US = 3_600_000_000
BILLING_PROJECT = "exalted-summer-490612-m6"
LOCATION = "US"
TASK_CUMULATIVE_BILLED_CAP_BYTES = 1_099_511_627_776
MAXIMUM_BYTES_BILLED = 600_000_000_000
CONNECTIVITY_JOB_ID = "google_pdu17_multiday_v1_connectivity_20260912"
ORACLE_JOB_ID = "google_pdu17_multiday_v1_oracle_db3367e901fd2392"


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    parameters = config["parameters"]
    if config["status"] != "DRAFT_NONAUTHORITATIVE_DATA_ACQUISITION":
        raise RuntimeError("Unexpected acquisition status")
    if (parameters["cell"], parameters["pdu"]) != ("f", "pdu17"):
        raise RuntimeError("This version is fixed to cell f / pdu17")
    if int(parameters["window_start_us"]) != 600_000_000 or int(parameters["window_end_us"]) != 2_679_000_000_000:
        raise RuntimeError("Full-month raw-clock window drifted")
    duration = int(parameters["window_end_us"]) - int(parameters["window_start_us"])
    if duration % HOUR_US or duration // HOUR_US != 744 or int(parameters["hours"]) != 744:
        raise RuntimeError("Full-month window must contain exactly 744 hours")
    if int(parameters["expected_machine_count"]) != 1295:
        raise RuntimeError("Expected PDU17 machine count drifted")
    if config["source"]["billing_project"] != BILLING_PROJECT or config["source"]["location"] != LOCATION:
        raise RuntimeError("Billing project or query location drifted")
    cost = config["cost_gate"]
    if int(cost["task_cumulative_billed_cap_bytes"]) != TASK_CUMULATIVE_BILLED_CAP_BYTES:
        raise RuntimeError("Authorized cumulative billing cap drifted")
    if int(cost["maximum_bytes_billed"]) != MAXIMUM_BYTES_BILLED:
        raise RuntimeError("Per-job billing cap drifted")
    expected_query_job_id = f"google_pdu17_multiday_v1_{config['source']['query_sha256'][:16]}"
    if cost["query_job_id"] != expected_query_job_id:
        raise RuntimeError("Main query job ID is not bound to the SQL hash")
    if cost["connectivity_job_id"] != CONNECTIVITY_JOB_ID or cost["oracle_job_id"] != ORACLE_JOB_ID:
        raise RuntimeError("Fixed verification job ID drifted")
    if int(cost["maximum_bytes_billed"]) > int(cost["task_cumulative_billed_cap_bytes"]):
        raise RuntimeError("Per-job billing cap exceeds task cap")
    if int(cost["expected_dry_run_bytes"]) > int(cost["maximum_bytes_billed"]):
        raise RuntimeError("Expected scan exceeds per-job billing cap")
    return config


def _query_parameters(config: dict[str, Any]) -> list[Any]:
    parameters = config["parameters"]
    return [
        bigquery.ScalarQueryParameter("cell", "STRING", parameters["cell"]),
        bigquery.ScalarQueryParameter("pdu", "STRING", parameters["pdu"]),
        bigquery.ScalarQueryParameter("window_start_us", "INT64", int(parameters["window_start_us"])),
        bigquery.ScalarQueryParameter("window_end_us", "INT64", int(parameters["window_end_us"])),
        bigquery.ScalarQueryParameter(
            "expected_machine_count", "INT64", int(parameters["expected_machine_count"])
        ),
    ]


def _job_config(config: dict[str, Any], *, dry_run: bool) -> Any:
    kwargs: dict[str, Any] = {
        "dry_run": dry_run,
        "use_query_cache": False,
        "query_parameters": _query_parameters(config),
        "labels": {"pipeline": "google-pdu17-month", "status": "nonauthoritative"},
    }
    if not dry_run:
        kwargs["maximum_bytes_billed"] = int(config["cost_gate"]["maximum_bytes_billed"])
    return bigquery.QueryJobConfig(**kwargs)


def _run_dry_run(client: Any, sql: str, config: dict[str, Any]) -> Any:
    job = client.query(
        sql,
        job_config=_job_config(config, dry_run=True),
        location=config["source"]["location"],
    )
    expected = int(config["cost_gate"]["expected_dry_run_bytes"])
    if not job.dry_run or int(job.total_bytes_processed) != expected:
        raise RuntimeError(f"Dry-run bytes drifted: expected {expected}, found {job.total_bytes_processed}")
    return job


def _get_job_or_none(client: Any, job_id: str, location: str) -> Any | None:
    try:
        return client.get_job(job_id, location=location)
    except NotFound:
        return None


def _task_billed_bytes(client: Any, config: dict[str, Any]) -> int:
    location = config["source"]["location"]
    ids = (
        config["cost_gate"]["connectivity_job_id"],
        config["cost_gate"]["oracle_job_id"],
        config["cost_gate"]["query_job_id"],
    )
    return sum(
        int(job.total_bytes_billed or 0)
        for job_id in ids
        if (job := _get_job_or_none(client, job_id, location)) is not None
    )


def _verification_job_payload(job: Any) -> dict[str, Any]:
    destination = getattr(job, "destination", None)
    return {
        "job_id": job.job_id,
        "query_sha256": hashlib.sha256(job.query.encode()).hexdigest(),
        "destination_table": (
            f"{destination.project}.{destination.dataset_id}.{destination.table_id}"
            if destination is not None
            else None
        ),
        "created": job.created.isoformat() if job.created is not None else None,
        "started": job.started.isoformat() if job.started is not None else None,
        "ended": job.ended.isoformat() if job.ended is not None else None,
        "cache_hit": bool(job.cache_hit),
        "total_bytes_processed": int(job.total_bytes_processed or 0),
        "total_bytes_billed": int(job.total_bytes_billed or 0),
        "maximum_bytes_billed": (
            int(job.maximum_bytes_billed) if job.maximum_bytes_billed is not None else None
        ),
        "labels": dict(sorted((job.labels or {}).items())),
    }


def _validate_zero_byte_jobs(client: Any, config: dict[str, Any], oracle_sql: str) -> dict[str, Any]:
    location = config["source"]["location"]
    connectivity = _get_job_or_none(client, config["cost_gate"]["connectivity_job_id"], location)
    oracle = _get_job_or_none(client, config["cost_gate"]["oracle_job_id"], location)
    if connectivity is None or oracle is None:
        raise RuntimeError("Required fixed zero-byte verification jobs are missing")
    connectivity_rows = [dict(row.items()) for row in connectivity.result()]
    oracle_rows = [dict(row.items()) for row in oracle.result()]
    expected_oracle = [
        {"priority_tier": "1_free", "cpu_time_lower": "600.000000", "cpu_time_upper": "720.000000", "conflict_fragments": 1, "exact_duplicate_fragments": 1},
        {"priority_tier": "ambiguous", "cpu_time_lower": "600.000000", "cpu_time_upper": "720.000000", "conflict_fragments": 1, "exact_duplicate_fragments": 1},
        {"priority_tier": "unknown", "cpu_time_lower": "1500.000000", "cpu_time_upper": "1620.000000", "conflict_fragments": 1, "exact_duplicate_fragments": 1},
    ]
    if connectivity.query != "SELECT 1 AS connectivity_ok" or connectivity_rows != [{"connectivity_ok": 1}]:
        raise RuntimeError("Connectivity job contents drifted")
    if hashlib.sha256(oracle.query.encode()).hexdigest() != hashlib.sha256(oracle_sql.encode()).hexdigest():
        raise RuntimeError("Oracle job SQL drifted")
    if oracle_rows != expected_oracle:
        raise RuntimeError(f"Oracle result drifted: {oracle_rows}")
    for job in (connectivity, oracle):
        if int(job.total_bytes_processed or 0) != 0 or int(job.total_bytes_billed or 0) != 0:
            raise RuntimeError("A fixed verification job was not zero-byte")
    return {
        "connectivity": _verification_job_payload(connectivity),
        "oracle": _verification_job_payload(oracle),
        "oracle_rows": oracle_rows,
    }


def _validate_existing_output(
    output_root: Path,
    config_path: Path,
    query_path: Path,
    oracle_path: Path,
    config: dict[str, Any],
) -> dict[str, Any]:
    if not _verify_manifest(output_root):
        raise RuntimeError("Existing output failed manifest verification")
    metadata = json.loads((output_root / METADATA_FILENAME).read_text(encoding="utf-8"))
    expected = {
        "status": "DRAFT_NONAUTHORITATIVE_PUBLIC_DATA_ACQUISITION",
        "schema": "google_power_workload_multiday_bigquery_v1",
        "query_sha256": _sha256(query_path),
        "oracle_query_sha256": _sha256(oracle_path),
        "config_sha256": _sha256(config_path),
        "implementation_sha256": _sha256(Path(__file__)),
        "shared_helper_sha256": _sha256(LEGACY_HELPER),
        "query_parameters": config["parameters"],
    }
    for field, value in expected.items():
        if metadata.get(field) != value:
            raise RuntimeError(f"Existing output metadata drifted: {field}")
    if metadata.get("query_job", {}).get("job_id") != config["cost_gate"]["query_job_id"]:
        raise RuntimeError("Existing output query job ID drifted")
    zero_jobs = metadata.get("zero_byte_verification_jobs", {})
    if zero_jobs.get("connectivity", {}).get("job_id") != config["cost_gate"]["connectivity_job_id"]:
        raise RuntimeError("Existing output connectivity job ID drifted")
    if zero_jobs.get("oracle", {}).get("job_id") != config["cost_gate"]["oracle_job_id"]:
        raise RuntimeError("Existing output oracle job ID drifted")
    source_tables = metadata.get("source_tables", {})
    for relative_id, frozen in config["expected"]["table_snapshots"].items():
        observed = source_tables.get(relative_id, {})
        if observed.get("table_id") != f"{config['source']['public_project']}.{relative_id}":
            raise RuntimeError(f"Existing output source table ID drifted: {relative_id}")
        for field in ("etag", "rows", "bytes"):
            if observed.get(field) != frozen[field]:
                raise RuntimeError(f"Existing output source snapshot drifted: {relative_id}/{field}")
    copied = {
        "query.sql": metadata["query_sha256"],
        "oracle_query.sql": metadata["oracle_query_sha256"],
        "config.yaml": metadata["config_sha256"],
        RAW_FILENAME: metadata["result_sha256"],
    }
    for name, expected_sha in copied.items():
        if _sha256(output_root / name) != expected_sha:
            raise RuntimeError(f"Existing output file binding drifted: {name}")
    return metadata


def _validate_query_job(job: Any, sql: str, config: dict[str, Any]) -> None:
    if job.job_id != config["cost_gate"]["query_job_id"]:
        raise RuntimeError("Query job ID drifted")
    if hashlib.sha256(job.query.encode()).hexdigest() != hashlib.sha256(sql.encode()).hexdigest():
        raise RuntimeError("Executed SQL drifted")
    _validate_job_query_parameters(job, _query_parameters(config))
    if int(job.total_bytes_processed) != int(config["cost_gate"]["expected_dry_run_bytes"]):
        raise RuntimeError("Executed bytes differ from dry-run gate")
    if int(job.total_bytes_billed) > int(config["cost_gate"]["maximum_bytes_billed"]):
        raise RuntimeError("Executed job exceeded its billing cap")
    if job.destination is None:
        raise RuntimeError("Executed query has no temporary result table")


def _get_or_submit_query_job(
    client: Any,
    sql: str,
    config: dict[str, Any],
    previous_billed: int,
) -> Any:
    source = config["source"]
    cost = config["cost_gate"]
    query_job_id = cost["query_job_id"]
    existing = _get_job_or_none(client, query_job_id, source["location"])
    if existing is not None:
        return existing
    if previous_billed + int(cost["maximum_bytes_billed"]) > int(
        cost["task_cumulative_billed_cap_bytes"]
    ):
        raise RuntimeError("Task cumulative billing cap cannot accommodate the guarded query")
    return client.query(
        sql,
        job_id=query_job_id,
        job_retry=None,
        job_config=_job_config(config, dry_run=False),
        location=source["location"],
    )


def _validate_and_sort_rows(rows: list[dict[str, Any]], config: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = config["expected"]
    tiers = tuple(expected["priority_tiers"])
    hourly = [row for row in rows if row["record_type"] == "hourly_usage"]
    audits = [row for row in rows if row["record_type"] == "audit"]
    if len(hourly) != int(expected["hourly_rows"]) or len(audits) != int(expected["audit_rows"]):
        raise RuntimeError("BigQuery result row counts drifted")
    expected_keys = {(hour, collection, tier) for hour in range(744) for collection in (0, 1) for tier in tiers}
    actual_keys = {(int(row["hour_index"]), int(row["collection_type"]), row["priority_tier"]) for row in hourly}
    if actual_keys != expected_keys or len(actual_keys) != len(hourly):
        raise RuntimeError("Hourly key grid is incomplete or duplicated")
    numeric_fields = (
        "observed_cpu_ncu_lower",
        "observed_cpu_ncu_upper",
        "observed_cpu_time_ncu_seconds_lower",
        "observed_cpu_time_ncu_seconds_upper",
        "observed_cpu_overlap_seconds",
        "missing_cpu_overlap_seconds",
        "cpu_conflict_overlap_seconds",
        "synthesized_cpu_time_ncu_seconds_lower",
        "synthesized_cpu_time_ncu_seconds_upper",
    )
    for row in hourly:
        hour = int(row["hour_index"])
        if int(row["raw_interval_start_us"]) != 600_000_000 + hour * HOUR_US:
            raise RuntimeError("Hourly raw-clock start drifted")
        if int(row["raw_interval_end_us"]) != 600_000_000 + (hour + 1) * HOUR_US:
            raise RuntimeError("Hourly raw-clock end drifted")
        values = {field: Decimal(str(row[field])) for field in numeric_fields}
        if any(not value.is_finite() or value < 0 for value in values.values()):
            raise RuntimeError("Hourly result contains invalid numeric values")
        if values["observed_cpu_ncu_lower"] > values["observed_cpu_ncu_upper"]:
            raise RuntimeError("CPU endpoint order failed")
        for field in ("fragment_piece_count", "usage_group_count", "cpu_conflict_usage_group_count", "exact_duplicate_usage_group_count"):
            if int(row[field]) < 0:
                raise RuntimeError("Hourly result contains a negative count")
    audit = json.loads(audits[0]["audit_json"])
    for field in (
        "incomplete_or_invalid_key_rows",
        "invalid_cpu_source_rows",
        "coverage_mismatch_groups",
        "overlapping_fragments",
        "future_priority_rows",
        "out_of_window_fragment_rows",
        "inconsistent_cpu_variant_fragments",
        "invalid_cpu_usage_groups",
        "unexpected_collection_type_fragments",
        "invalid_priority_fragments",
    ):
        if int(audit[field]) != 0:
            raise RuntimeError(f"Audit gate is nonzero: {field}")
    if int(audit["pdu_machine_count"]) != 1295 or int(audit["usage_source_rows"]) <= 0:
        raise RuntimeError("Audit population gate failed")
    hourly.sort(key=lambda row: (int(row["hour_index"]), int(row["collection_type"]), tiers.index(row["priority_tier"])))
    return hourly + audits, audit


def _write_csv_gzip(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text:
                writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
                writer.writeheader()
                writer.writerows(rows)


def run(config_path: Path = DEFAULT_CONFIG, *, execute: bool = False, client: Any | None = None) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = _load_config(config_path)
    source = config["source"]
    query_path = (ROOT / source["query_path"]).resolve()
    oracle_path = (ROOT / source["oracle_query_path"]).resolve()
    sql = query_path.read_text(encoding="utf-8")
    oracle_sql = oracle_path.read_text(encoding="utf-8")
    if _sha256(query_path) != source["query_sha256"] or _sha256(oracle_path) != source["oracle_query_sha256"]:
        raise RuntimeError("Acquisition SQL hash drifted")
    if _sha256(LEGACY_HELPER) != LEGACY_HELPER_SHA256:
        raise RuntimeError("Shared acquisition helper drifted")
    mapping_count, mapping_sha = _mapping_fingerprint(
        ROOT / source["mapping_source_path"], cell="f", pdu="pdu17"
    )
    if mapping_count != 1295 or mapping_sha != config["expected"]["mapping_machine_ids_sha256"]:
        raise RuntimeError("PDU17 mapping fingerprint drifted")
    output_root = (ROOT / source["output_directory"]).resolve()
    if execute and output_root.exists():
        return _validate_existing_output(
            output_root, config_path, query_path, oracle_path, config
        )

    active_client = client or bigquery.Client(project=source["billing_project"])
    snapshots_before = _table_snapshots(active_client, config)
    dry_job = _run_dry_run(active_client, sql, config)
    dry_summary = {
        "status": "DRAFT_NONAUTHORITATIVE_DRY_RUN",
        "query_sha256": source["query_sha256"],
        "config_sha256": _sha256(config_path),
        "total_bytes_processed": int(dry_job.total_bytes_processed),
        "maximum_bytes_billed": int(config["cost_gate"]["maximum_bytes_billed"]),
        "task_cumulative_billed_cap_bytes": int(config["cost_gate"]["task_cumulative_billed_cap_bytes"]),
        "source_tables": snapshots_before,
        "execute": False,
    }
    if not execute:
        return dry_summary

    zero_jobs = _validate_zero_byte_jobs(active_client, config, oracle_sql)
    previous_billed = _task_billed_bytes(active_client, config)
    task_cap = int(config["cost_gate"]["task_cumulative_billed_cap_bytes"])
    query_job = _get_or_submit_query_job(active_client, sql, config, previous_billed)
    iterator = query_job.result(page_size=20_000)
    _validate_query_job(query_job, sql, config)
    fields = [field.name for field in iterator.schema]
    if fields != list(config["expected"]["fields"]):
        raise RuntimeError(f"Result schema drifted: {fields}")
    rows, audit = _validate_and_sort_rows([dict(row.items()) for row in iterator], config)
    snapshots_after = _table_snapshots(active_client, config)
    if snapshots_after != snapshots_before:
        raise RuntimeError("Public source tables changed during acquisition")
    task_billed = _task_billed_bytes(active_client, config)
    if task_billed > task_cap:
        raise RuntimeError("Task cumulative billed bytes exceeded the authorized cap")

    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=output_root.parent, prefix=f".{output_root.name}.acquiring-"))
    try:
        _write_csv_gzip(staging / RAW_FILENAME, rows, fields)
        shutil.copyfile(query_path, staging / "query.sql")
        shutil.copyfile(oracle_path, staging / "oracle_query.sql")
        shutil.copyfile(config_path, staging / "config.yaml")
        metadata = {
            "status": "DRAFT_NONAUTHORITATIVE_PUBLIC_DATA_ACQUISITION",
            "schema": "google_power_workload_multiday_bigquery_v1",
            "query_sha256": _sha256(query_path),
            "oracle_query_sha256": _sha256(oracle_path),
            "config_sha256": _sha256(config_path),
            "implementation_sha256": _sha256(Path(__file__)),
            "shared_helper_sha256": _sha256(LEGACY_HELPER),
            "query_parameters": config["parameters"],
            "dry_run_bytes": int(dry_job.total_bytes_processed),
            "maximum_bytes_billed": int(config["cost_gate"]["maximum_bytes_billed"]),
            "task_cumulative_billed_cap_bytes": task_cap,
            "task_cumulative_billed_bytes": task_billed,
            "query_job": _job_payload(query_job),
            "zero_byte_verification_jobs": zero_jobs,
            "temporary_result": _temporary_result_payload(active_client, query_job),
            "source_tables": snapshots_before,
            "fields": fields,
            "result": {"rows": len(rows), "hourly_rows": 10416, "audit_rows": 1, "audit": audit},
            "result_sha256": _sha256(staging / RAW_FILENAME),
            "population_is_complete_pdu_workload": False,
            "absolute_power_mw_available": False,
            "flexibility_observed": False,
            "deadline_observed": False,
            "recovery_parameters_observed": False,
            "continuous_model_input_ready": False,
            "model_parameter_changed": False,
            "formal_result": False,
            "paper_claim": False,
            "security_certified": False,
            "google_cloud_bigquery_version": bigquery.__version__,
        }
        (staging / METADATA_FILENAME).write_text(
            json.dumps(metadata, indent=2, sort_keys=True, allow_nan=False) + "\n", encoding="utf-8", newline="\n"
        )
        files = sorted(path for path in staging.iterdir() if path.is_file())
        (staging / MANIFEST_FILENAME).write_text(
            "".join(f"{_sha256(path)}  {path.name}\n" for path in files), encoding="ascii", newline="\n"
        )
        if not _verify_manifest(staging):
            raise RuntimeError("Staged acquisition manifest failed verification")
        os.replace(staging, output_root)
        return metadata
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    print(json.dumps(run(args.config, execute=args.execute), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
