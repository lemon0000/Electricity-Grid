"""Pair one PDU day of normalized power with same-system NCU usage."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

import yaml

HOUR_US = 3_600_000_000
PRIORITY_TIERS = (
    "1_free",
    "2_beb",
    "3_mid",
    "4_production",
    "5_monitoring",
    "ambiguous",
    "unknown",
)
PAIR_FIELDS = (
    "hour_index",
    "cluster_window_start_us",
    "cluster_window_end_us",
    "power_source_first_sample_time_us",
    "power_source_last_sample_time_us",
    "power_valid_sample_count",
    "measured_power_util_mean",
    "measured_power_util_min",
    "measured_power_util_max",
    "observed_cpu_ncu_lower",
    "observed_cpu_ncu_upper",
    "observed_cpu_time_ncu_seconds_lower",
    "observed_cpu_time_ncu_seconds_upper",
    "priority_candidate_cpu_ncu_lower",
    "priority_candidate_cpu_ncu_upper",
    "priority_candidate_cpu_share_lower",
    "priority_candidate_cpu_share_upper",
    "ambiguous_priority_cpu_share_lower",
    "ambiguous_priority_cpu_share_upper",
    "unknown_priority_cpu_share_lower",
    "unknown_priority_cpu_share_upper",
    "synthesized_priority_cpu_share_lower",
    "synthesized_priority_cpu_share_upper",
    "missing_cpu_overlap_seconds",
    "cpu_conflict_overlap_seconds",
    "known_machine_capacity_ncu_time_average",
    "active_machine_count_time_average",
    "known_capacity_machine_count_time_average",
    "unknown_capacity_machine_seconds",
    "machine_capacity_complete",
)
PRIORITY_FIELDS = (
    "hour_index",
    "priority_tier",
    "priority_interpretation",
    "observed_cpu_ncu_lower",
    "observed_cpu_ncu_upper",
    "observed_cpu_time_ncu_seconds_lower",
    "observed_cpu_time_ncu_seconds_upper",
    "priority_cpu_share_lower",
    "priority_cpu_share_upper",
    "observed_cpu_overlap_seconds",
    "missing_cpu_overlap_seconds",
    "cpu_conflict_overlap_seconds",
    "fragment_piece_count",
    "usage_group_count",
    "cpu_conflict_usage_group_count",
    "exact_duplicate_usage_group_count",
    "synthesized_cpu_time_ncu_seconds_lower",
    "synthesized_cpu_time_ncu_seconds_upper",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _verify_manifest(root: Path) -> None:
    manifest_path = root / "SHA256SUMS"
    if not manifest_path.is_file():
        raise RuntimeError(f"Missing source manifest: {manifest_path}")
    expected: dict[str, str] = {}
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        try:
            digest, relative = line.split("  ", maxsplit=1)
        except ValueError as exc:
            raise RuntimeError(f"Malformed source manifest: {manifest_path}") from exc
        if relative in expected:
            raise RuntimeError(f"Duplicate source manifest entry: {relative}")
        expected[relative] = digest
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest_path
    }
    if actual != set(expected):
        raise RuntimeError(f"Source manifest file set drifted: {manifest_path}")
    for relative, digest in expected.items():
        if _sha256(root / relative) != digest:
            raise RuntimeError(f"Source manifest hash drifted: {relative}")


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("Cannot serialize a non-finite value")
    return format(value, ".15g")


def _power_fingerprint_float(value: float) -> str:
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    parsed = float(value)
    if not math.isfinite(parsed) or parsed < 0.0:
        raise ValueError(f"Invalid nonnegative numeric value: {value}")
    return parsed


def _serialize(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return _format_float(value)
    return str(value)


def _write_csv(
    path: Path, fields: tuple[str, ...], rows: Iterable[dict[str, Any]]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _serialize(row[field]) for field in fields})


def _publish_directory(staging: Path, output_root: Path) -> None:
    backup = output_root.with_name(f".{output_root.name}.previous")
    if output_root.is_dir() and not any(output_root.iterdir()):
        output_root.rmdir()
    if backup.exists():
        if output_root.exists():
            _verify_manifest(output_root)
            shutil.rmtree(backup)
        else:
            backup.replace(output_root)
    if output_root.exists():
        _verify_manifest(output_root)
        output_root.replace(backup)
    try:
        staging.replace(output_root)
        _verify_manifest(output_root)
    except BaseException:
        if output_root.exists() and not staging.exists():
            output_root.replace(staging)
        if backup.exists():
            backup.replace(output_root)
        raise
    if backup.exists():
        shutil.rmtree(backup)


def _load_mapping(path: Path, *, cell: str, pdu: str) -> set[int]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        machine_ids = {
            int(row["machine_id"])
            for row in csv.DictReader(source)
            if row["cell"] == cell and row["pdu"] == pdu
        }
    if not machine_ids:
        raise RuntimeError("The configured PDU has no mapped machines")
    return machine_ids


def _build_power_hours(
    path: Path,
    config: dict[str, Any],
    *,
    cell: str,
    pdu: str,
) -> tuple[list[dict[str, Any]], str]:
    offset = int(config["source_time_offset_us"])
    samples = int(config["samples"])
    hours = int(config["hours"])
    samples_per_hour = int(config["samples_per_hour"])
    step = int(config["time_step_us"])
    start = offset
    end = offset + hours * HOUR_US
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        selected = [
            row for row in csv.DictReader(source) if start <= int(row["time"]) < end
        ]
    selected.sort(key=lambda row: int(row["time"]))
    times = [int(row["time"]) for row in selected]
    expected_times = [start + index * step for index in range(samples)]
    if times != expected_times:
        raise RuntimeError(
            "Power day-0 timestamps are missing, duplicated, or misaligned"
        )
    if samples != hours * samples_per_hour:
        raise ValueError("Power sample and hour configuration is inconsistent")
    if start != int(config["first_time_us"]) or expected_times[-1] != int(
        config["last_time_us"]
    ):
        raise ValueError("Power day-0 endpoint configuration is inconsistent")
    if any(row["cell"] != cell or row["pdu"] != pdu for row in selected):
        raise RuntimeError("Power day-0 selection contains a different domain")
    quality_values = {
        row[field].lower()
        for row in selected
        for field in ("bad_measurement_data", "bad_production_power_data")
    }
    if not quality_values <= {"true", "false"}:
        raise RuntimeError("Power day-0 contains an invalid quality flag")
    bad_measurement = sum(
        row["bad_measurement_data"].lower() == "true" for row in selected
    )
    bad_production = sum(
        row["bad_production_power_data"].lower() == "true" for row in selected
    )
    if bad_measurement != int(config["bad_measurement_rows"]):
        raise RuntimeError("Power day-0 measurement quality drifted")
    if bad_production != int(config["bad_production_rows"]):
        raise RuntimeError("Power day-0 production quality drifted")
    if bad_measurement:
        raise RuntimeError("Power day-0 has unusable measured-power samples")

    values = [float(row["measured_power_util"]) for row in selected]
    if not all(math.isfinite(value) and value >= 0.0 for value in values):
        raise RuntimeError("Power day-0 has invalid measured-power values")
    if not math.isclose(
        min(values), float(config["minimum_measured_power_util"]), abs_tol=1e-12
    ) or not math.isclose(
        max(values), float(config["maximum_measured_power_util"]), abs_tol=1e-12
    ):
        raise RuntimeError("Power day-0 measured range drifted")

    rows = []
    fingerprint_lines = []
    for hour in range(hours):
        block = selected[hour * samples_per_hour : (hour + 1) * samples_per_hour]
        block_values = [float(row["measured_power_util"]) for row in block]
        mean_value = sum(block_values) / samples_per_hour
        first_time = int(block[0]["time"])
        last_time = int(block[-1]["time"])
        rows.append(
            {
                "hour_index": hour,
                "source_first_time_us": first_time,
                "source_last_time_us": last_time,
                "valid_samples": len(block),
                "mean": mean_value,
                "minimum": min(block_values),
                "maximum": max(block_values),
            }
        )
        fingerprint_lines.append(
            f"{hour},{first_time},{last_time},{_power_fingerprint_float(mean_value)}\n"
        )
    fingerprint = hashlib.sha256("".join(fingerprint_lines).encode("ascii")).hexdigest()
    if fingerprint != config["hourly_power_sha256"]:
        raise RuntimeError(
            "Power hourly fingerprint drifted: "
            f"expected {config['hourly_power_sha256']}, found {fingerprint}"
        )
    return rows, fingerprint


def _share_bounds(
    part_lower: float,
    part_upper: float,
    total_lower: float,
    total_upper: float,
) -> tuple[float | None, float | None]:
    if not (0.0 <= part_lower <= part_upper and 0.0 <= total_lower <= total_upper):
        raise ValueError("Invalid interval for a priority share")
    other_lower = total_lower - part_lower
    other_upper = total_upper - part_upper
    tolerance = 1e-8
    if other_lower < -tolerance or other_upper < -tolerance:
        raise ValueError("Priority interval is not a subset of the total interval")
    other_lower = max(0.0, other_lower)
    other_upper = max(0.0, other_upper)
    if part_upper + other_upper == 0.0:
        return None, None
    lower_denominator = part_lower + other_upper
    upper_denominator = part_upper + other_lower
    lower = 0.0 if lower_denominator == 0.0 else part_lower / lower_denominator
    upper = 0.0 if upper_denominator == 0.0 else part_upper / upper_denominator
    if lower > upper + tolerance:
        raise RuntimeError("Priority share bounds are inverted")
    return lower, upper


def _aggregate_usage(
    rows: list[dict[str, str]],
    candidate_tiers: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    float_fields = (
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
    count_fields = (
        "fragment_piece_count",
        "usage_group_count",
        "cpu_conflict_usage_group_count",
        "exact_duplicate_usage_group_count",
    )
    grouped: dict[tuple[int, str], dict[str, Any]] = {}
    source_keys: set[tuple[int, int, str]] = set()
    for row in rows:
        hour = int(row["hour_index"])
        collection_type = int(row["collection_type"])
        tier = row["priority_tier"]
        source_key = (hour, collection_type, tier)
        if source_key in source_keys:
            raise RuntimeError(f"Duplicate raw hourly usage key: {source_key}")
        source_keys.add(source_key)
        if (
            not 0 <= hour < 24
            or collection_type not in (0, 1)
            or tier not in PRIORITY_TIERS
        ):
            raise RuntimeError(f"Invalid raw hourly usage key: {source_key}")
        target = grouped.setdefault(
            (hour, tier),
            {field: 0.0 for field in float_fields}
            | {field: 0 for field in count_fields},
        )
        for field in float_fields:
            value = float(row[field])
            if not math.isfinite(value) or value < 0.0:
                raise RuntimeError(f"Invalid raw hourly value: {field}")
            target[field] += value
        for field in count_fields:
            value = int(row[field])
            if value < 0:
                raise RuntimeError(f"Invalid raw hourly count: {field}")
            target[field] += value
    expected_keys = {
        (hour, collection_type, tier)
        for hour in range(24)
        for collection_type in (0, 1)
        for tier in PRIORITY_TIERS
    }
    if source_keys != expected_keys:
        raise RuntimeError("Raw usage does not contain the complete 24x2x7 grid")

    details: list[dict[str, Any]] = []
    hourly: list[dict[str, Any]] = []
    for hour in range(24):
        hour_rows = {tier: grouped[(hour, tier)] for tier in PRIORITY_TIERS}
        total_lower = sum(
            row["observed_cpu_time_ncu_seconds_lower"] for row in hour_rows.values()
        )
        total_upper = sum(
            row["observed_cpu_time_ncu_seconds_upper"] for row in hour_rows.values()
        )
        for tier, values in hour_rows.items():
            share = _share_bounds(
                values["observed_cpu_time_ncu_seconds_lower"],
                values["observed_cpu_time_ncu_seconds_upper"],
                total_lower,
                total_upper,
            )
            if tier in candidate_tiers:
                interpretation = "low_priority_usage_candidate_not_observed_flexibility"
            elif tier == "ambiguous":
                interpretation = "ambiguous_priority_not_reassigned"
            elif tier == "unknown":
                interpretation = "unknown_priority_not_reassigned"
            else:
                interpretation = "noncandidate_priority_tier"
            details.append(
                {
                    "hour_index": hour,
                    "priority_tier": tier,
                    "priority_interpretation": interpretation,
                    **values,
                    "priority_cpu_share_lower": share[0],
                    "priority_cpu_share_upper": share[1],
                }
            )
        candidate_lower = sum(
            hour_rows[tier]["observed_cpu_time_ncu_seconds_lower"]
            for tier in candidate_tiers
        )
        candidate_upper = sum(
            hour_rows[tier]["observed_cpu_time_ncu_seconds_upper"]
            for tier in candidate_tiers
        )
        ambiguous = hour_rows["ambiguous"]
        unknown = hour_rows["unknown"]
        synthesized_lower = sum(
            row["synthesized_cpu_time_ncu_seconds_lower"] for row in hour_rows.values()
        )
        synthesized_upper = sum(
            row["synthesized_cpu_time_ncu_seconds_upper"] for row in hour_rows.values()
        )
        hourly.append(
            {
                "observed_cpu_time_ncu_seconds_lower": total_lower,
                "observed_cpu_time_ncu_seconds_upper": total_upper,
                "observed_cpu_ncu_lower": total_lower / 3600.0,
                "observed_cpu_ncu_upper": total_upper / 3600.0,
                "candidate_cpu_time_lower": candidate_lower,
                "candidate_cpu_time_upper": candidate_upper,
                "candidate_share": _share_bounds(
                    candidate_lower, candidate_upper, total_lower, total_upper
                ),
                "ambiguous_share": _share_bounds(
                    ambiguous["observed_cpu_time_ncu_seconds_lower"],
                    ambiguous["observed_cpu_time_ncu_seconds_upper"],
                    total_lower,
                    total_upper,
                ),
                "unknown_share": _share_bounds(
                    unknown["observed_cpu_time_ncu_seconds_lower"],
                    unknown["observed_cpu_time_ncu_seconds_upper"],
                    total_lower,
                    total_upper,
                ),
                "synthesized_share": _share_bounds(
                    synthesized_lower,
                    synthesized_upper,
                    total_lower,
                    total_upper,
                ),
                "synthesized_cpu_time_lower": synthesized_lower,
                "synthesized_cpu_time_upper": synthesized_upper,
                "ambiguous_cpu_time_lower": ambiguous[
                    "observed_cpu_time_ncu_seconds_lower"
                ],
                "ambiguous_cpu_time_upper": ambiguous[
                    "observed_cpu_time_ncu_seconds_upper"
                ],
                "unknown_cpu_time_lower": unknown[
                    "observed_cpu_time_ncu_seconds_lower"
                ],
                "unknown_cpu_time_upper": unknown[
                    "observed_cpu_time_ncu_seconds_upper"
                ],
                "missing_cpu_overlap_seconds": sum(
                    row["missing_cpu_overlap_seconds"] for row in hour_rows.values()
                ),
                "cpu_conflict_overlap_seconds": sum(
                    row["cpu_conflict_overlap_seconds"] for row in hour_rows.values()
                ),
            }
        )
    return details, hourly


def _build_capacity_hours(
    rows: list[dict[str, Any]],
    mapping_machine_ids: set[int],
    *,
    window_end_us: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    events = sorted(
        rows,
        key=lambda row: (int(row["machine_event_time"]), int(row["machine_id"])),
    )
    seen_machine_times: set[tuple[int, int]] = set()
    event_machines: set[int] = set()
    event_counts: Counter[int] = Counter()
    null_capacity_adds = 0
    state: dict[int, float | None] = {}
    hourly = [
        {
            "active_machine_seconds": 0.0,
            "known_capacity_machine_seconds": 0.0,
            "unknown_capacity_machine_seconds": 0.0,
            "known_capacity_ncu_seconds": 0.0,
        }
        for _ in range(window_end_us // HOUR_US)
    ]

    def accrue(start_us: int, end_us: int) -> None:
        active_count = len(state)
        known_capacities = [
            capacity for capacity in state.values() if capacity is not None
        ]
        known_count = len(known_capacities)
        unknown_count = active_count - known_count
        known_capacity = sum(known_capacities)
        cursor = start_us
        while cursor < end_us:
            hour = cursor // HOUR_US
            boundary = min(end_us, (hour + 1) * HOUR_US)
            seconds = (boundary - cursor) / 1_000_000.0
            target = hourly[hour]
            target["active_machine_seconds"] += active_count * seconds
            target["known_capacity_machine_seconds"] += known_count * seconds
            target["unknown_capacity_machine_seconds"] += unknown_count * seconds
            target["known_capacity_ncu_seconds"] += known_capacity * seconds
            cursor = boundary

    previous_time = 0
    for row in events:
        event_time = int(row["machine_event_time"])
        machine_id = int(row["machine_id"])
        event_type = int(row["machine_event_type"])
        if not 0 <= event_time < window_end_us:
            raise RuntimeError("Machine event falls outside the processing window")
        if machine_id not in mapping_machine_ids:
            raise RuntimeError("Machine event is outside the configured PDU mapping")
        machine_time = (machine_id, event_time)
        if machine_time in seen_machine_times:
            raise RuntimeError("A machine has conflicting events at the same time")
        seen_machine_times.add(machine_time)
        missing_reason = row.get("machine_missing_data_reason")
        if missing_reason not in (None, "", 0, "0"):
            raise RuntimeError("Machine event has a nonzero missing-data reason")
        capacity = _optional_float(row.get("capacity_cpus"))
        accrue(previous_time, event_time)
        previous_time = event_time
        event_machines.add(machine_id)
        event_counts[event_type] += 1
        if event_type == 1:
            if machine_id in state:
                raise RuntimeError("Machine ADD occurred while the machine was active")
            state[machine_id] = capacity
            null_capacity_adds += capacity is None
        elif event_type == 2:
            if machine_id not in state:
                raise RuntimeError(
                    "Machine REMOVE occurred while the machine was inactive"
                )
            del state[machine_id]
        elif event_type == 3:
            if machine_id not in state:
                raise RuntimeError(
                    "Machine UPDATE occurred while the machine was inactive"
                )
            state[machine_id] = capacity
        else:
            raise RuntimeError(f"Unknown machine event type: {event_type}")
    accrue(previous_time, window_end_us)

    for values in hourly:
        values["active_machine_count_time_average"] = (
            values["active_machine_seconds"] / 3600.0
        )
        values["known_capacity_machine_count_time_average"] = (
            values["known_capacity_machine_seconds"] / 3600.0
        )
        values["known_machine_capacity_ncu_time_average"] = (
            values["known_capacity_ncu_seconds"] / 3600.0
        )
        values["machine_capacity_complete"] = math.isclose(
            values["unknown_capacity_machine_seconds"], 0.0, abs_tol=1e-9
        )
    known_final_capacity = sum(
        capacity for capacity in state.values() if capacity is not None
    )
    summary = {
        "mapping_machine_count": len(mapping_machine_ids),
        "machines_with_events": len(event_machines),
        "mapping_machines_without_events": len(mapping_machine_ids - event_machines),
        "machine_event_rows": len(events),
        "machine_event_type_counts": {
            str(event_type): event_counts[event_type] for event_type in (1, 2, 3)
        },
        "add_events_with_unknown_capacity": null_capacity_adds,
        "unknown_capacity_machine_seconds": sum(
            row["unknown_capacity_machine_seconds"] for row in hourly
        ),
        "capacity_incomplete_hours": [
            index
            for index, row in enumerate(hourly)
            if not row["machine_capacity_complete"]
        ],
        "final_event_active_machine_count": len(state),
        "final_event_active_known_capacity_machine_count": sum(
            capacity is not None for capacity in state.values()
        ),
        "final_known_machine_capacity_ncu": known_final_capacity,
        "machines_without_events_semantics": "not_observed_added_during_day0",
    }
    return hourly, summary


def run(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    parameters = config["parameters"]
    power_config = config["power_day0"]
    processing = config["processing"]
    raw_root = Path(source["output_directory"])
    power_path = Path(power_config["source_path"])
    _verify_manifest(raw_root)
    _verify_manifest(power_path.parent)

    metadata_path = raw_root / "SOURCE_METADATA.json"
    raw_path = raw_root / "records.csv.gz"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["schema"] != "google_power_workload_bigquery_hourly_extract_v1":
        raise RuntimeError("Unsupported BigQuery workload schema")
    if metadata["query_parameters"] != parameters:
        raise RuntimeError(
            "BigQuery workload parameters do not match processing config"
        )
    if metadata["result_sha256"] != _sha256(raw_path):
        raise RuntimeError("BigQuery workload result hash drifted")
    if metadata["fields"] != list(config["expected"]["hourly_fields"]):
        raise RuntimeError("BigQuery workload field contract drifted")
    for key in ("query_sha256", "compact_query_sha256", "hourly_query_sha256"):
        if metadata[key] != source[key]:
            raise RuntimeError(f"BigQuery workload SQL contract drifted: {key}")
    if metadata["monthly_acquisition_bytes_processed"] > int(
        config["cost_gate"]["monthly_scan_budget_bytes"]
    ):
        raise RuntimeError("BigQuery acquisition exceeded the configured scan budget")
    if any(
        metadata[key]
        for key in (
            "absolute_power_mw_available",
            "flexibility_observed",
            "recovery_parameters_observed",
        )
    ):
        raise RuntimeError(
            "Raw evidence flags exceed this processor's evidence ceiling"
        )
    if metadata["population_is_complete_pdu_workload"]:
        raise RuntimeError("Raw workload population scope unexpectedly changed")

    with gzip.open(raw_path, "rt", encoding="utf-8", newline="") as source_file:
        raw_rows = list(csv.DictReader(source_file))
    by_type: dict[str, list[dict[str, str]]] = {
        record_type: [row for row in raw_rows if row["record_type"] == record_type]
        for record_type in ("hourly_usage", "machine_event", "audit")
    }
    counts = {key: len(value) for key, value in by_type.items()}
    if counts != metadata["result"]["record_counts"] or sum(counts.values()) != len(
        raw_rows
    ):
        raise RuntimeError("BigQuery workload record counts drifted")
    raw_audit = json.loads(by_type["audit"][0]["audit_json"])
    if raw_audit != metadata["result"]["audit"]:
        raise RuntimeError("BigQuery workload audit record drifted")

    candidate_tiers = set(processing["priority_candidate_tiers"])
    if tuple(processing["priority_tiers"]) != PRIORITY_TIERS:
        raise ValueError("Priority-tier processing configuration drifted")
    if not candidate_tiers or not candidate_tiers < set(PRIORITY_TIERS):
        raise ValueError("Invalid priority-candidate tier configuration")
    if processing["priority_candidate_semantics"] != (
        "low_priority_usage_candidate_not_observed_flexibility"
    ):
        raise ValueError(
            "Priority candidates must not be labeled as observed flexibility"
        )
    if processing["evidence_status"] != (
        "observed_same_system_normalized_power_and_ncu_usage_pair"
    ) or any(
        processing[key]
        for key in (
            "absolute_power_mw_available",
            "flexibility_observed",
            "recovery_parameters_observed",
        )
    ):
        raise ValueError(
            "Processed evidence flags exceed the supported evidence ceiling"
        )
    priority_rows, usage_hours = _aggregate_usage(
        by_type["hourly_usage"], candidate_tiers
    )
    mapping_ids = _load_mapping(
        Path(source["mapping_source_path"]),
        cell=str(parameters["cell"]),
        pdu=str(parameters["pdu"]),
    )
    if len(mapping_ids) != int(metadata["mapping_machine_count"]):
        raise RuntimeError("PDU mapping count drifted after acquisition")
    capacity_hours, capacity_summary = _build_capacity_hours(
        by_type["machine_event"],
        mapping_ids,
        window_end_us=int(parameters["window_end_us"]),
    )
    power_hours, power_fingerprint = _build_power_hours(
        power_path,
        power_config,
        cell=str(parameters["cell"]),
        pdu=str(parameters["pdu"]),
    )

    pair_rows = []
    for hour, (power, usage, capacity) in enumerate(
        zip(power_hours, usage_hours, capacity_hours, strict=True)
    ):
        pair_rows.append(
            {
                "hour_index": hour,
                "cluster_window_start_us": hour * HOUR_US,
                "cluster_window_end_us": (hour + 1) * HOUR_US,
                "power_source_first_sample_time_us": power["source_first_time_us"],
                "power_source_last_sample_time_us": power["source_last_time_us"],
                "power_valid_sample_count": power["valid_samples"],
                "measured_power_util_mean": power["mean"],
                "measured_power_util_min": power["minimum"],
                "measured_power_util_max": power["maximum"],
                "observed_cpu_ncu_lower": usage["observed_cpu_ncu_lower"],
                "observed_cpu_ncu_upper": usage["observed_cpu_ncu_upper"],
                "observed_cpu_time_ncu_seconds_lower": usage[
                    "observed_cpu_time_ncu_seconds_lower"
                ],
                "observed_cpu_time_ncu_seconds_upper": usage[
                    "observed_cpu_time_ncu_seconds_upper"
                ],
                "priority_candidate_cpu_ncu_lower": usage["candidate_cpu_time_lower"]
                / 3600.0,
                "priority_candidate_cpu_ncu_upper": usage["candidate_cpu_time_upper"]
                / 3600.0,
                "priority_candidate_cpu_share_lower": usage["candidate_share"][0],
                "priority_candidate_cpu_share_upper": usage["candidate_share"][1],
                "ambiguous_priority_cpu_share_lower": usage["ambiguous_share"][0],
                "ambiguous_priority_cpu_share_upper": usage["ambiguous_share"][1],
                "unknown_priority_cpu_share_lower": usage["unknown_share"][0],
                "unknown_priority_cpu_share_upper": usage["unknown_share"][1],
                "synthesized_priority_cpu_share_lower": usage["synthesized_share"][0],
                "synthesized_priority_cpu_share_upper": usage["synthesized_share"][1],
                "missing_cpu_overlap_seconds": usage["missing_cpu_overlap_seconds"],
                "cpu_conflict_overlap_seconds": usage["cpu_conflict_overlap_seconds"],
                "known_machine_capacity_ncu_time_average": capacity[
                    "known_machine_capacity_ncu_time_average"
                ],
                "active_machine_count_time_average": capacity[
                    "active_machine_count_time_average"
                ],
                "known_capacity_machine_count_time_average": capacity[
                    "known_capacity_machine_count_time_average"
                ],
                "unknown_capacity_machine_seconds": capacity[
                    "unknown_capacity_machine_seconds"
                ],
                "machine_capacity_complete": capacity["machine_capacity_complete"],
            }
        )

    output_root = output_directory or Path(processing["output_directory"])
    output_root.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_root.name}.processing-"
    with tempfile.TemporaryDirectory(dir=output_root.parent, prefix=prefix) as temp:
        staging = Path(temp)
        pair_path = staging / "hourly_pair.csv"
        priority_path = staging / "hourly_priority_usage.csv"
        _write_csv(pair_path, PAIR_FIELDS, pair_rows)
        _write_csv(priority_path, PRIORITY_FIELDS, priority_rows)
        pair_sha = _sha256(pair_path)
        priority_sha = _sha256(priority_path)

        total_lower = sum(
            hour["observed_cpu_time_ncu_seconds_lower"] for hour in usage_hours
        )
        total_upper = sum(
            hour["observed_cpu_time_ncu_seconds_upper"] for hour in usage_hours
        )
        candidate_shares = [
            value
            for hour in usage_hours
            for value in hour["candidate_share"]
            if value is not None
        ]
        summary = {
            "schema": processing["schema"],
            "cell": parameters["cell"],
            "pdu": parameters["pdu"],
            "cluster_window_start_us": int(parameters["window_start_us"]),
            "cluster_window_end_us": int(parameters["window_end_us"]),
            "power_source_time_offset_us": int(power_config["source_time_offset_us"]),
            "power_metric": "measured_power_util",
            "power_is_normalized_utilization_not_watts_or_mw": True,
            "production_power_used": False,
            "hours": len(pair_rows),
            "priority_rows": len(priority_rows),
            "power_valid_samples": sum(row["valid_samples"] for row in power_hours),
            "power_hourly_fingerprint_rule": power_config[
                "hourly_power_fingerprint_rule"
            ],
            "power_hourly_sha256": power_fingerprint,
            "bigquery_result_sha256": metadata["result_sha256"],
            "bigquery_manifest_sha256": _sha256(raw_root / "SHA256SUMS"),
            "power_source_sha256": _sha256(power_path),
            "power_source_manifest_sha256": _sha256(power_path.parent / "SHA256SUMS"),
            "hourly_pair_sha256": pair_sha,
            "hourly_priority_usage_sha256": priority_sha,
            "observed_cpu_time_ncu_seconds_lower": total_lower,
            "observed_cpu_time_ncu_seconds_upper": total_upper,
            "cpu_conflict_uncertainty_width_ncu_seconds": total_upper - total_lower,
            "priority_candidate_tiers": sorted(candidate_tiers),
            "priority_candidate_semantics": processing["priority_candidate_semantics"],
            "minimum_hourly_priority_candidate_share": min(candidate_shares),
            "maximum_hourly_priority_candidate_share": max(candidate_shares),
            "ambiguous_priority_cpu_time_ncu_seconds_lower": sum(
                hour["ambiguous_cpu_time_lower"] for hour in usage_hours
            ),
            "ambiguous_priority_cpu_time_ncu_seconds_upper": sum(
                hour["ambiguous_cpu_time_upper"] for hour in usage_hours
            ),
            "unknown_priority_cpu_time_ncu_seconds_lower": sum(
                hour["unknown_cpu_time_lower"] for hour in usage_hours
            ),
            "unknown_priority_cpu_time_ncu_seconds_upper": sum(
                hour["unknown_cpu_time_upper"] for hour in usage_hours
            ),
            "synthesized_priority_cpu_time_ncu_seconds_lower": sum(
                hour["synthesized_cpu_time_lower"] for hour in usage_hours
            ),
            "synthesized_priority_cpu_time_ncu_seconds_upper": sum(
                hour["synthesized_cpu_time_upper"] for hour in usage_hours
            ),
            "raw_quality_audit": raw_audit,
            **capacity_summary,
            "population_is_complete_pdu_workload": False,
            "capacity_used_to_normalize_usage": False,
            "absolute_power_mw_available": False,
            "flexibility_observed": False,
            "recovery_parameters_observed": False,
            "model_input_ready": False,
            "evidence_status": processing["evidence_status"],
        }
        summary_path = staging / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        observed_hashes = {
            "hourly_pair.csv": pair_sha,
            "hourly_priority_usage.csv": priority_sha,
            "summary.json": _sha256(summary_path),
        }
        if observed_hashes != processing["expected_artifact_sha256"]:
            raise RuntimeError(
                "Processed Google day-0 artifact hashes drifted: "
                + json.dumps(observed_hashes, sort_keys=True)
            )
        manifest_path = staging / "SHA256SUMS"
        manifest_path.write_text(
            "".join(
                f"{digest}  {name}\n"
                for name, digest in sorted(observed_hashes.items())
            ),
            encoding="ascii",
        )
        _publish_directory(staging, output_root)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/google_power_workload_day0.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
