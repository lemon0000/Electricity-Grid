"""Build reproducible source-row, candidate-group, and cohort artifacts."""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import tempfile
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Iterable

import openpyxl
import yaml

from experiments.validate_us_major_power_outages_data import run as validate_source


_TEMPORAL_COLUMNS = (
    "OUTAGE.START.DATE",
    "OUTAGE.START.TIME",
    "OUTAGE.RESTORATION.DATE",
    "OUTAGE.RESTORATION.TIME",
    "OUTAGE.DURATION",
)
_COHORT_COLUMNS = (
    "primary_duration",
    "known_loss_sensitivity",
    "positive_loss_sensitivity",
    "zero_duration_sensitivity",
    "detail_complete_sensitivity",
    "single_nerc_sensitivity",
)


def _is_missing(value: object) -> bool:
    return value is None or (
        isinstance(value, str)
        and (not value.strip() or value.strip().upper() == "NA")
    )


def _normalize_text(value: object, missing_token: str) -> str:
    if _is_missing(value):
        return missing_token
    return " ".join(str(value).strip().lower().split())


def _date_part(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    raise ValueError(f"Expected a date value, got {value!r}")


def _time_part(value: object) -> time:
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, time):
        return value
    raise ValueError(f"Expected a time value, got {value!r}")


def _timestamp(record: dict[str, object], date_column: str, time_column: str) -> datetime | None:
    if _is_missing(record[date_column]) or _is_missing(record[time_column]):
        return None
    return datetime.combine(
        _date_part(record[date_column]),
        _time_part(record[time_column]),
    )


def _number(value: object) -> float | None:
    if _is_missing(value):
        return None
    number = float(value)
    if not math.isfinite(number):
        raise ValueError(f"Non-finite numeric value: {value!r}")
    return number


def _json_value(value: object, missing_token: str) -> str:
    if _is_missing(value):
        return missing_token
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return str(value)


def _csv_value(value: object, missing_token: str) -> str:
    if value is None or _is_missing(value):
        return missing_token
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"Cannot write non-finite CSV value: {value!r}")
        return format(value, ".15g")
    return str(value)


def _canonical_key(
    record: dict[str, object],
    *,
    missing_token: str,
) -> tuple[str, ...]:
    values = (
        str(record["POSTAL.CODE"]).strip().upper()
        if not _is_missing(record["POSTAL.CODE"])
        else missing_token,
        _json_value(record["OUTAGE.START.DATE"], missing_token),
        _json_value(record["OUTAGE.START.TIME"], missing_token),
        _json_value(record["OUTAGE.RESTORATION.DATE"], missing_token),
        _json_value(record["OUTAGE.RESTORATION.TIME"], missing_token),
        _normalize_text(record["CAUSE.CATEGORY"], missing_token),
        _normalize_text(record["CAUSE.CATEGORY.DETAIL"], missing_token),
    )
    return values


def _group_id(key: tuple[str, ...]) -> str:
    payload = json.dumps(list(key), ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _resolve(path: str | Path) -> Path:
    candidate = Path(path)
    return candidate if candidate.is_absolute() else Path.cwd() / candidate


def _output_path(
    configured_path: str | Path,
    *,
    output_root: Path | None,
) -> Path:
    if output_root is not None:
        return output_root / Path(configured_path).name
    return _resolve(configured_path)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(
    path: Path,
    fieldnames: Iterable[str],
    rows: Iterable[dict[str, object]],
    *,
    missing_token: str,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(fieldnames)
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {field: _csv_value(row.get(field), missing_token) for field in fields}
            )


def _promote(staging: Path, output_root: Path, names: tuple[str, ...]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (staging / name).replace(output_root / name)


def _read_source_records(
    config: dict[str, object],
) -> tuple[list[str], list[dict[str, object]], str]:
    source = config["source"]
    expected = config["expected"]
    root = _resolve(str(source["path"]))
    supplement_path = root / "supplementary_files.zip"
    with zipfile.ZipFile(supplement_path) as archive:
        workbook_bytes = archive.read(str(expected["workbook_member"]))
        workbook_sha256 = hashlib.sha256(workbook_bytes).hexdigest()
    workbook = openpyxl.load_workbook(
        io.BytesIO(workbook_bytes),
        read_only=True,
        data_only=True,
    )
    worksheet = workbook[str(expected["sheet"])]
    headers = [cell.value for cell in worksheet[int(expected["header_row"])]]
    if len(headers) != len(set(headers)):
        raise ValueError("Source workbook headers must be unique")
    required = set(expected["required_columns"])
    if not required.issubset(headers):
        raise ValueError(f"Source workbook is missing columns: {sorted(required - set(headers))}")
    records = [
        dict(zip(headers, row))
        for row in worksheet.iter_rows(
            min_row=int(expected["data_start_row"]),
            values_only=True,
        )
    ]
    if len(records) != int(expected["source_rows"]):
        raise ValueError(f"Unexpected source row count: {len(records)}")
    return list(headers), records, workbook_sha256


def _annotate_records(
    records: list[dict[str, object]],
    *,
    missing_token: str,
) -> dict[tuple[str, ...], list[dict[str, object]]]:
    grouped: dict[tuple[str, ...], list[dict[str, object]]] = defaultdict(list)
    for record in records:
        key = _canonical_key(record, missing_token=missing_token)
        record["_candidate_key"] = key
        record["_candidate_group_id"] = _group_id(key)
        record["_start_timestamp"] = _timestamp(
            record, "OUTAGE.START.DATE", "OUTAGE.START.TIME"
        )
        record["_restoration_timestamp"] = _timestamp(
            record,
            "OUTAGE.RESTORATION.DATE",
            "OUTAGE.RESTORATION.TIME",
        )
        record["_reported_duration_min"] = _number(record["OUTAGE.DURATION"])
        record["_demand_loss_mw"] = _number(record["DEMAND.LOSS.MW"])
        record["_customers_affected"] = _number(record["CUSTOMERS.AFFECTED"])
        start = record["_start_timestamp"]
        restoration = record["_restoration_timestamp"]
        record["_complete_temporal"] = (
            all(not _is_missing(record[column]) for column in _TEMPORAL_COLUMNS)
        )
        if start is not None and restoration is not None:
            record["_timestamp_duration_min"] = (
                restoration - start
            ).total_seconds() / 60.0
        else:
            record["_timestamp_duration_min"] = None
        timestamp_duration = record["_timestamp_duration_min"]
        reported_duration = record["_reported_duration_min"]
        record["_timestamp_duration_nonnegative"] = bool(
            timestamp_duration is not None and timestamp_duration >= 0.0
        )
        record["_duration_delta_min"] = (
            None
            if timestamp_duration is None or reported_duration is None
            else reported_duration - timestamp_duration
        )
        record["_reported_duration_positive"] = bool(
            reported_duration is not None and reported_duration > 0.0
        )
        record["_reported_duration_nonnegative"] = bool(
            reported_duration is not None and reported_duration >= 0.0
        )
        loss = record["_demand_loss_mw"]
        record["_demand_loss_known"] = loss is not None
        record["_demand_loss_positive"] = bool(loss is not None and loss > 0.0)
        record["_demand_loss_zero"] = bool(loss is not None and loss == 0.0)
        grouped[key].append(record)
    for rows in grouped.values():
        rows.sort(key=lambda row: int(row["OBS"]))
        for rank, row in enumerate(rows, start=1):
            row["_candidate_row_rank"] = rank
            row["_candidate_group_size"] = len(rows)
            row["_duplicate_candidate"] = len(rows) > 1
            row["_duplicate_excess_row"] = len(rows) > 1 and rank > 1
    return grouped


def _group_record(
    key: tuple[str, ...],
    rows: list[dict[str, object]],
    *,
    missing_token: str,
) -> dict[str, object]:
    complete_temporal = all(bool(row["_complete_temporal"]) for row in rows)
    timestamp_durations = [
        float(row["_timestamp_duration_min"])
        for row in rows
        if row["_timestamp_duration_min"] is not None
    ]
    reported_durations = [
        float(row["_reported_duration_min"])
        for row in rows
        if row["_reported_duration_min"] is not None
    ]
    deltas = [
        float(row["_duration_delta_min"])
        for row in rows
        if row["_duration_delta_min"] is not None
    ]
    losses = [
        float(row["_demand_loss_mw"])
        for row in rows
        if row["_demand_loss_mw"] is not None
    ]
    customers = [
        float(row["_customers_affected"])
        for row in rows
        if row["_customers_affected"] is not None
    ]
    nerc_regions = sorted(
        {
            str(row["NERC.REGION"]).strip().upper()
            for row in rows
            if not _is_missing(row["NERC.REGION"])
        }
    )
    timestamp_nonnegative = complete_temporal and all(
        duration >= 0.0 for duration in timestamp_durations
    )
    reported_positive = complete_temporal and all(
        duration > 0.0 for duration in reported_durations
    )
    reported_nonnegative = complete_temporal and all(
        duration >= 0.0 for duration in reported_durations
    )
    known_loss = bool(losses)
    positive_loss = any(loss > 0.0 for loss in losses)
    detail_missing = key[-1] == missing_token
    primary = complete_temporal and timestamp_nonnegative and reported_positive
    known_cohort = primary and known_loss
    positive_cohort = primary and positive_loss
    zero_cohort = complete_temporal and timestamp_nonnegative and reported_nonnegative
    detail_cohort = primary and not detail_missing
    single_nerc_cohort = primary and len(nerc_regions) <= 1
    return {
        "candidate_group_id": _group_id(key),
        "candidate_key_json": json.dumps(list(key), ensure_ascii=True, separators=(",", ":")),
        "candidate_group_size": len(rows),
        "source_obs_ids": ";".join(str(int(row["OBS"])) for row in rows),
        "postal_code": key[0],
        "start_timestamp_local": rows[0]["_start_timestamp"],
        "restoration_timestamp_local": rows[0]["_restoration_timestamp"],
        "cause_category": key[5],
        "normalized_cause_category_detail": key[6],
        "cause_detail_complete": not detail_missing,
        "nerc_regions": ";".join(nerc_regions),
        "multi_nerc": len(nerc_regions) > 1,
        "reported_duration_min": min(reported_durations, default=None),
        "reported_duration_min_min": min(reported_durations, default=None),
        "reported_duration_min_max": max(reported_durations, default=None),
        "timestamp_duration_min": min(timestamp_durations, default=None),
        "timestamp_duration_min_min": min(timestamp_durations, default=None),
        "timestamp_duration_min_max": max(timestamp_durations, default=None),
        "duration_delta_min": min(deltas, default=None),
        "duration_delta_min_min": min(deltas, default=None),
        "duration_delta_min_max": max(deltas, default=None),
        "complete_temporal": complete_temporal,
        "timestamp_duration_nonnegative": timestamp_nonnegative,
        "reported_duration_positive": reported_positive,
        "reported_duration_nonnegative": reported_nonnegative,
        "demand_loss_known": known_loss,
        "demand_loss_positive": positive_loss,
        "demand_loss_zero": any(loss == 0.0 for loss in losses),
        "demand_loss_known_count": len(losses),
        "demand_loss_max_mw": max(losses, default=None),
        "demand_loss_min_mw": min(losses, default=None),
        "customers_known_count": len(customers),
        "customers_max": max(customers, default=None),
        "customers_min": min(customers, default=None),
        "primary_duration_member": primary,
        "known_loss_sensitivity_member": known_cohort,
        "positive_loss_sensitivity_member": positive_cohort,
        "zero_duration_sensitivity_member": zero_cohort,
        "detail_complete_sensitivity_member": detail_cohort,
        "single_nerc_sensitivity_member": single_nerc_cohort,
        "source_rows_primary_duration": len(rows) if primary else 0,
        "source_rows_known_loss_sensitivity": len(rows) if known_cohort else 0,
        "source_rows_positive_loss_sensitivity": len(rows) if positive_cohort else 0,
        "source_rows_zero_duration_sensitivity": len(rows) if zero_cohort else 0,
    }


def _source_row_cohort_flags(record: dict[str, object]) -> dict[str, bool]:
    primary = bool(
        record["_complete_temporal"]
        and record["_timestamp_duration_nonnegative"]
        and record["_reported_duration_positive"]
    )
    known = primary and bool(record["_demand_loss_known"])
    positive = primary and bool(record["_demand_loss_positive"])
    zero = bool(
        record["_complete_temporal"]
        and record["_timestamp_duration_nonnegative"]
        and record["_reported_duration_nonnegative"]
    )
    return {
        "source_row_primary_duration_member": primary,
        "source_row_known_loss_member": known,
        "source_row_positive_loss_member": positive,
        "source_row_zero_duration_member": zero,
    }


def _assert_expected_counts(
    summary: dict[str, object],
    expected: dict[str, object],
) -> None:
    checks = {
        "source_rows": summary["source_rows"] == expected["source_rows"],
        "candidate_groups": summary["candidate_groups"] == expected["candidate_groups"],
        "duplicate_candidate_event_groups": summary["duplicate_candidate_event_groups"]
        == expected["duplicate_candidate_event_groups"],
        "duplicate_candidate_rows": summary["duplicate_candidate_rows"]
        == expected["duplicate_candidate_rows"],
        "duplicate_candidate_excess_rows": summary["duplicate_candidate_excess_rows"]
        == expected["duplicate_candidate_excess_rows"],
    }
    for name, expected_cohort in expected["cohorts"].items():
        actual_cohort = summary["cohorts"].get(name, {})
        for field, value in expected_cohort.items():
            if field.endswith("_rows") or field in {"candidate_groups", "duplicate_excess_rows"}:
                checks[f"{name}.{field}"] = actual_cohort.get(field) == value
    for name, value in expected.get("intersections", {}).items():
        checks[f"intersections.{name}"] = summary["intersections"].get(name) == value
    if not all(checks.values()):
        failed = {name: value for name, value in checks.items() if not value}
        raise RuntimeError(f"Frozen outage processing counts failed: {failed}")


def run(
    config_path: Path,
    *,
    output_root: Path | None = None,
    write_output: bool = True,
) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    processing = config["processing"]
    missing_token = str(processing["missing_token"])
    expected_key = [
        "POSTAL.CODE",
        "OUTAGE.START.DATE",
        "OUTAGE.START.TIME",
        "OUTAGE.RESTORATION.DATE",
        "OUTAGE.RESTORATION.TIME",
        "CAUSE.CATEGORY",
        "normalized_cause_category_detail",
    ]
    if list(processing["candidate_key"]) != expected_key:
        raise ValueError("Unsupported candidate key processing contract")
    source_validation = validate_source(config_path, write_output=False)
    headers, records, workbook_sha256 = _read_source_records(config)
    grouped = _annotate_records(records, missing_token=missing_token)
    groups = [
        _group_record(key, rows, missing_token=missing_token)
        for key, rows in sorted(grouped.items())
    ]

    source_rows_primary = sum(
        bool(
            row["_complete_temporal"]
            and row["_timestamp_duration_nonnegative"]
            and row["_reported_duration_positive"]
        )
        for row in records
    )
    source_rows_known = sum(
        bool(
            row["_complete_temporal"]
            and row["_timestamp_duration_nonnegative"]
            and row["_reported_duration_positive"]
            and row["_demand_loss_known"]
        )
        for row in records
    )
    source_rows_positive = sum(
        bool(
            row["_complete_temporal"]
            and row["_timestamp_duration_nonnegative"]
            and row["_reported_duration_positive"]
            and row["_demand_loss_positive"]
        )
        for row in records
    )
    source_rows_zero = sum(
        bool(
            row["_complete_temporal"]
            and row["_timestamp_duration_nonnegative"]
            and row["_reported_duration_nonnegative"]
        )
        for row in records
    )

    cohort_specs = {
        "primary_duration": "primary_duration_member",
        "known_loss_sensitivity": "known_loss_sensitivity_member",
        "positive_loss_sensitivity": "positive_loss_sensitivity_member",
        "zero_duration_sensitivity": "zero_duration_sensitivity_member",
        "detail_complete_sensitivity": "detail_complete_sensitivity_member",
        "single_nerc_sensitivity": "single_nerc_sensitivity_member",
    }
    cohort_summary: dict[str, dict[str, object]] = {}
    for name, flag in cohort_specs.items():
        selected = [group for group in groups if bool(group[flag])]
        cohort_summary[name] = {
            "unit": processing["cohorts"][name]["unit"],
            "rule": processing["cohorts"][name]["rule"],
            "candidate_groups": len(selected),
            "source_rows": sum(int(group["candidate_group_size"]) for group in selected),
            "duplicate_excess_rows": sum(
                int(group["candidate_group_size"]) - 1 for group in selected
            ),
            "cause_counts": dict(
                sorted(Counter(str(group["cause_category"]) for group in selected).items())
            ),
        }
    cohort_summary["source_rows_sensitivity"] = {
        "unit": processing["cohorts"]["source_rows_sensitivity"]["unit"],
        "rule": processing["cohorts"]["source_rows_sensitivity"]["rule"],
        "primary_duration_rows": source_rows_primary,
        "known_loss_rows": source_rows_known,
        "positive_loss_rows": source_rows_positive,
        "zero_duration_rows": source_rows_zero,
    }

    primary_groups = [group for group in groups if group["primary_duration_member"]]
    intersections = {
        "complete_timed_known_loss_candidate_groups": sum(
            bool(
                group["complete_temporal"]
                and group["timestamp_duration_nonnegative"]
                and group["demand_loss_known"]
            )
            for group in groups
        ),
        "complete_timed_positive_loss_candidate_groups": sum(
            bool(
                group["complete_temporal"]
                and group["timestamp_duration_nonnegative"]
                and group["demand_loss_positive"]
            )
            for group in groups
        ),
        "complete_sustained_known_loss_candidate_groups": cohort_summary[
            "known_loss_sensitivity"
        ]["candidate_groups"],
        "complete_sustained_positive_loss_candidate_groups": cohort_summary[
            "positive_loss_sensitivity"
        ]["candidate_groups"],
    }
    cause_group_names = {
        str(cause): group_name
        for group_name, causes in processing["cause_groups"].items()
        for cause in causes
    }
    primary_cause_groups = Counter(
        cause_group_names.get(str(group["cause_category"]), "unmapped")
        for group in primary_groups
    )
    duplicate_groups = [group for group in groups if int(group["candidate_group_size"]) > 1]
    summary: dict[str, object] = {
        "processing_id": processing["id"],
        "source_validation_summary_sha256": hashlib.sha256(
            json.dumps(source_validation, sort_keys=True, default=str).encode("utf-8")
        ).hexdigest(),
        "source_workbook_member_sha256": workbook_sha256,
        "source_rows": len(records),
        "candidate_groups": len(groups),
        "duplicate_candidate_event_groups": len(duplicate_groups),
        "duplicate_candidate_rows": sum(
            int(group["candidate_group_size"]) for group in duplicate_groups
        ),
        "duplicate_candidate_excess_rows": sum(
            int(group["candidate_group_size"]) - 1 for group in duplicate_groups
        ),
        "cohorts": cohort_summary,
        "intersections": intersections,
        "primary_cause_group_counts": dict(sorted(primary_cause_groups.items())),
        "duration_mismatch_minutes": source_validation["duration_mismatch_minutes"],
        "zero_duration_records": source_validation["zero_duration_records"],
        "zero_duration_timestamp_consistent_records": source_validation[
            "zero_duration_timestamp_consistent_records"
        ],
        "missing": source_validation["missing"],
        "evidence": config["evidence"],
        "forbidden_inferences": processing["forbidden_inferences"],
        "outputs": {},
    }
    _assert_expected_counts(summary, processing["expected_counts"])

    output = config["output"]
    source_rows_path = _output_path(output["source_rows_path"], output_root=output_root)
    candidate_groups_path = _output_path(
        output["candidate_groups_path"], output_root=output_root
    )
    cohort_membership_path = _output_path(
        output["cohort_membership_path"], output_root=output_root
    )
    processing_summary_path = _output_path(
        output["processing_summary_path"], output_root=output_root
    )
    summary["outputs"] = {
        "source_rows": source_rows_path.name,
        "candidate_groups": candidate_groups_path.name,
        "cohort_membership": cohort_membership_path.name,
        "processing_summary": processing_summary_path.name,
    }

    source_derived_fields = [
        "candidate_group_id",
        "candidate_group_size",
        "candidate_row_rank",
        "duplicate_candidate",
        "duplicate_excess_row",
        "normalized_cause_category_detail",
        "start_timestamp_local",
        "restoration_timestamp_local",
        "reported_duration_min",
        "timestamp_duration_min",
        "duration_delta_min",
        "complete_temporal",
        "timestamp_duration_nonnegative",
        "reported_duration_positive",
        "reported_duration_nonnegative",
        "demand_loss_mw_numeric",
        "demand_loss_known",
        "demand_loss_positive",
        "demand_loss_zero",
        "customers_affected_numeric",
        "nerc_regions",
        "multi_nerc",
        "source_row_primary_duration_member",
        "source_row_known_loss_member",
        "source_row_positive_loss_member",
        "source_row_zero_duration_member",
    ]
    source_output_rows = []
    for record in records:
        flags = _source_row_cohort_flags(record)
        source_output_rows.append(
            {
                **{header: record.get(header) for header in headers},
                "candidate_group_id": record["_candidate_group_id"],
                "candidate_group_size": record["_candidate_group_size"],
                "candidate_row_rank": record["_candidate_row_rank"],
                "duplicate_candidate": record["_duplicate_candidate"],
                "duplicate_excess_row": record["_duplicate_excess_row"],
                "normalized_cause_category_detail": record["_candidate_key"][-1],
                "start_timestamp_local": record["_start_timestamp"],
                "restoration_timestamp_local": record["_restoration_timestamp"],
                "reported_duration_min": record["_reported_duration_min"],
                "timestamp_duration_min": record["_timestamp_duration_min"],
                "duration_delta_min": record["_duration_delta_min"],
                "complete_temporal": record["_complete_temporal"],
                "timestamp_duration_nonnegative": record["_timestamp_duration_nonnegative"],
                "reported_duration_positive": record["_reported_duration_positive"],
                "reported_duration_nonnegative": record["_reported_duration_nonnegative"],
                "demand_loss_mw_numeric": record["_demand_loss_mw"],
                "demand_loss_known": record["_demand_loss_known"],
                "demand_loss_positive": record["_demand_loss_positive"],
                "demand_loss_zero": record["_demand_loss_zero"],
                "customers_affected_numeric": record["_customers_affected"],
                "nerc_regions": str(record["NERC.REGION"]).strip().upper()
                if not _is_missing(record["NERC.REGION"])
                else missing_token,
                "multi_nerc": len(
                    {
                        str(row["NERC.REGION"]).strip().upper()
                        for row in grouped[record["_candidate_key"]]
                        if not _is_missing(row["NERC.REGION"])
                    }
                )
                > 1,
                **flags,
            }
        )
    group_fields = [
        "candidate_group_id",
        "candidate_key_json",
        "candidate_group_size",
        "source_obs_ids",
        "postal_code",
        "start_timestamp_local",
        "restoration_timestamp_local",
        "cause_category",
        "normalized_cause_category_detail",
        "cause_detail_complete",
        "nerc_regions",
        "multi_nerc",
        "reported_duration_min",
        "reported_duration_min_min",
        "reported_duration_min_max",
        "timestamp_duration_min",
        "timestamp_duration_min_min",
        "timestamp_duration_min_max",
        "duration_delta_min",
        "duration_delta_min_min",
        "duration_delta_min_max",
        "complete_temporal",
        "timestamp_duration_nonnegative",
        "reported_duration_positive",
        "reported_duration_nonnegative",
        "demand_loss_known",
        "demand_loss_positive",
        "demand_loss_zero",
        "demand_loss_known_count",
        "demand_loss_max_mw",
        "demand_loss_min_mw",
        "customers_known_count",
        "customers_max",
        "customers_min",
    ]
    membership_fields = [
        "candidate_group_id",
        "candidate_group_size",
        "source_obs_ids",
        "cause_category",
        "normalized_cause_category_detail",
        "nerc_regions",
        "multi_nerc",
        "complete_temporal",
        "timestamp_duration_nonnegative",
        "reported_duration_positive",
        "reported_duration_nonnegative",
        "demand_loss_known",
        "demand_loss_positive",
        "cause_detail_complete",
        "primary_duration_member",
        "known_loss_sensitivity_member",
        "positive_loss_sensitivity_member",
        "zero_duration_sensitivity_member",
        "detail_complete_sensitivity_member",
        "single_nerc_sensitivity_member",
        "source_rows_primary_duration",
        "source_rows_known_loss_sensitivity",
        "source_rows_positive_loss_sensitivity",
        "source_rows_zero_duration_sensitivity",
    ]
    if write_output:
        final_paths = (
            source_rows_path,
            candidate_groups_path,
            cohort_membership_path,
            processing_summary_path,
        )
        publication_roots = {path.parent.resolve() for path in final_paths}
        if len(publication_roots) != 1:
            raise ValueError("Processed outage outputs must share one directory")
        publication_root = final_paths[0].parent
        publication_root.parent.mkdir(parents=True, exist_ok=True)
        prefix = f".{publication_root.name}.processing-"
        with tempfile.TemporaryDirectory(
            dir=publication_root.parent,
            prefix=prefix,
        ) as temp:
            staging = Path(temp)
            staged_outputs = {
                "source_rows": staging / source_rows_path.name,
                "candidate_groups": staging / candidate_groups_path.name,
                "cohort_membership": staging / cohort_membership_path.name,
            }
            _write_csv(
                staged_outputs["source_rows"],
                [*headers, *source_derived_fields],
                source_output_rows,
                missing_token=missing_token,
            )
            _write_csv(
                staged_outputs["candidate_groups"],
                group_fields,
                groups,
                missing_token=missing_token,
            )
            _write_csv(
                staged_outputs["cohort_membership"],
                membership_fields,
                groups,
                missing_token=missing_token,
            )
            output_files = {
                label: {
                    "path": path.name,
                    "bytes": path.stat().st_size,
                    "sha256": _sha256(path),
                }
                for label, path in staged_outputs.items()
            }
            summary["output_files"] = output_files
            expected_output_sha256 = processing["expected_output_sha256"]
            for label, metadata in output_files.items():
                if metadata["sha256"] != expected_output_sha256[label]:
                    raise RuntimeError(f"Processed outage {label} hash drifted")

            staged_summary = staging / processing_summary_path.name
            staged_summary.write_text(
                json.dumps(summary, indent=2, sort_keys=True, default=str) + "\n",
                encoding="utf-8",
            )
            if _sha256(staged_summary) != expected_output_sha256[
                "processing_summary"
            ]:
                raise RuntimeError("Processed outage summary hash drifted")
            manifest_names = (
                source_rows_path.name,
                candidate_groups_path.name,
                cohort_membership_path.name,
                processing_summary_path.name,
            )
            (staging / "SHA256SUMS").write_text(
                "".join(
                    f"{_sha256(staging / name)}  {name}\n"
                    for name in manifest_names
                ),
                encoding="ascii",
            )
            _promote(staging, publication_root, (*manifest_names, "SHA256SUMS"))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/us_major_power_outages.yaml"),
    )
    parser.add_argument("--output-root", type=Path, default=None)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    result = run(
        args.config,
        output_root=args.output_root,
        write_output=not args.no_write,
    )
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
