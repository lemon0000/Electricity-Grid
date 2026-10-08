"""Prepare bounded public compute traces without changing model inputs or gates."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import os
import shutil
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
GOOGLE_SUPPLEMENT = ROOT / "data/raw/google_cluster_2019_public_supplement_v1/upstream"
GOOGLE_FOOTERS = ROOT / "data/raw/google_cluster_2019_usage_footer_probe_v1/upstream"
GOOGLE_OPERATIONS = ROOT / "data/raw/google_operational_flexibility_evidence_v1/upstream"
POWER_ROOT = ROOT / "data/raw/google_power_2019/2019/upstream"
ZEUS_ROOT = ROOT / "data/raw/zeus_training_energy_public_v1/upstream"
MAPPING_PATH = POWER_ROOT / "machine_to_pdu_mapping.csv.gz"
DEFAULT_OUTPUT = ROOT / "results/tables/public_compute_multiday_v1_non_authoritative"

TRACE_START_RAW_US = 600_000_000
TRACE_END_RAW_US = 2_679_000_000_000
HOUR_US = 3_600_000_000
POWER_STEP_US = 300_000_000
HOURS = 744
POWER_DOMAINS = 57
POWER_ROWS_PER_DOMAIN = 8_928
PDU17_MACHINES = 1_295
FULL_USAGE_PARQUET_BYTES = 447_312_709_954
FULL_USAGE_ROWS_FROM_PUBLIC_TABLE_METADATA = 7_707_808_700
SIX_COLUMN_DRY_RUN_BYTES = 369_974_817_600
REQUIRED_USAGE_COLUMNS = {
    "start_time",
    "end_time",
    "machine_id",
    "alloc_collection_id",
    "collection_type",
    "average_usage.cpus",
}
EXPECTED_SOURCE_HASHES = {
    GOOGLE_SUPPLEMENT / "SOURCE_METADATA.json": "bdb2ab90cb6572bfc4567bbe4f2b93d7c613d8bd8ae5eaaf1f130b4c1dcf6d8c",
    ZEUS_ROOT / "SOURCE_METADATA.json": "1e2c680d924cd5f9e8ce206a5357b49ed92152b6351ca34906f8c0db038b8214",
    MAPPING_PATH: "69b88e5662348030b074fef2008a4f2c16927a68b2d218a8c7c5cf350dc0aa8d",
    POWER_ROOT / "SHA256SUMS": "fc11c3a59cc078799bcc289cc40579025d8b82b5c009679b1690f987b91c7c47",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_pyarrow():
    import pyarrow
    import pyarrow.parquet as pq

    if pyarrow.__version__ != "23.0.1":
        raise RuntimeError(f"Expected PyArrow 23.0.1, found {pyarrow.__version__}")
    return pyarrow, pq


def _verify_fixed_sources() -> None:
    for path, expected in EXPECTED_SOURCE_HASHES.items():
        if _sha256(path) != expected:
            raise RuntimeError(f"Protected source drifted: {path}")


def _verify_bundle(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    metadata_path = root / "SOURCE_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected = {entry["path"] for entry in metadata["files"]}
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SOURCE_METADATA.json"
    }
    if actual != expected:
        raise RuntimeError(f"Source bundle membership drifted: {root}")
    hashes: dict[str, str] = {}
    for entry in metadata["files"]:
        path = root / entry["path"]
        if path.stat().st_size != int(entry["bytes"]):
            raise RuntimeError(f"Source size drifted: {path}")
        hashes[entry["path"]] = _sha256(path)
        if hashes[entry["path"]] != entry["sha256"]:
            raise RuntimeError(f"Source SHA-256 drifted: {path}")
    return metadata, hashes


def _write_jsonl_gzip(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    count = 0
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as stream:
            for row in rows:
                payload = json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
                stream.write(payload.encode("utf-8") + b"\n")
                count += 1
    return count


def _normalized_capacity(capacity: Any) -> tuple[Decimal, Decimal] | None:
    if capacity is None:
        return None
    cpus = Decimal(str(capacity["cpus"]))
    memory = Decimal(str(capacity["memory"]))
    if not cpus.is_finite() or not memory.is_finite() or cpus < 0 or memory < 0:
        raise RuntimeError("Invalid normalized machine capacity")
    return cpus, memory


def _normalize_machine_row(row: dict[str, Any]) -> tuple[Any, ...]:
    capacity = _normalized_capacity(row.get("capacity"))
    return (
        int(row["time"]),
        int(row["machine_id"]),
        int(row["type"]),
        row.get("switch_id"),
        capacity,
        row.get("platform_id"),
        None if row.get("missing_data_reason") is None else int(row["missing_data_reason"]),
    )


def _read_machine_events() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _, pq = _require_pyarrow()
    json_path = GOOGLE_SUPPLEMENT / "machine_events-000000000000.json.gz"
    parquet_path = GOOGLE_SUPPLEMENT / "machine_events-000000000000.parquet.gz"
    with gzip.open(json_path, "rt", encoding="utf-8") as stream:
        json_rows = [json.loads(line, parse_float=Decimal) for line in stream]
    parquet_rows = pq.read_table(parquet_path).to_pylist()
    json_normalized = [_normalize_machine_row(row) for row in json_rows]
    parquet_normalized = [_normalize_machine_row(row) for row in parquet_rows]
    if json_normalized != parquet_normalized:
        raise RuntimeError("Fixed machine-events JSON and Parquet contents differ")
    return json_rows, {
        "rows_each_format": len(json_rows),
        "row_order_exact_equal": True,
        "content_multiset_equal": True,
        "json_sha256": _sha256(json_path),
        "parquet_sha256": _sha256(parquet_path),
        "pyarrow_version": "23.0.1",
    }


def _pdu17_machine_ids() -> set[int]:
    with gzip.open(MAPPING_PATH, "rt", encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    ids = {int(row["machine_id"]) for row in rows if row["cell"] == "f" and row["pdu"] == "pdu17"}
    if len(ids) != PDU17_MACHINES:
        raise RuntimeError("PDU17 mapping population drifted")
    return ids


def _pdu17_capacity_hours(events: list[dict[str, Any]], machines: set[int]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_machine: dict[int, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    for index, row in enumerate(events):
        machine = int(row["machine_id"])
        if machine in machines:
            by_machine[machine].append((int(row["time"]), index, row))
    if set(by_machine) != machines:
        raise RuntimeError("PDU17 contains mapped machines without machine events")

    accumulators = [
        {
            "known_cpu_us": Decimal(0),
            "known_memory_us": Decimal(0),
            "known_active_us": 0,
            "unknown_active_us": 0,
            "inactive_us": 0,
        }
        for _ in range(HOURS)
    ]
    missing_add_segments = 0
    transitions = Counter()
    final_active = 0
    final_inactive = 0

    def add_interval(start: int, end: int, active: bool, capacity: tuple[Decimal, Decimal] | None) -> None:
        if end <= start:
            return
        cursor = start
        while cursor < end:
            hour = (cursor - TRACE_START_RAW_US) // HOUR_US
            boundary = min(end, TRACE_START_RAW_US + (hour + 1) * HOUR_US)
            duration = boundary - cursor
            target = accumulators[hour]
            if not active:
                target["inactive_us"] += duration
            elif capacity is None:
                target["unknown_active_us"] += duration
            else:
                target["known_active_us"] += duration
                target["known_cpu_us"] += capacity[0] * duration
                target["known_memory_us"] += capacity[1] * duration
            cursor = boundary

    for machine in sorted(machines):
        sequence = sorted(by_machine[machine], key=lambda item: (item[0], item[1]))
        zero = [item for item in sequence if item[0] == 0]
        if len(zero) > 1 or (zero and int(zero[0][2]["type"]) != 1):
            raise RuntimeError("Ambiguous PDU17 time-zero state")
        active = bool(zero)
        capacity = _normalized_capacity(zero[0][2].get("capacity")) if zero else None
        cursor = TRACE_START_RAW_US
        for time_us, _, row in sequence:
            if time_us == 0:
                continue
            if time_us < TRACE_START_RAW_US or time_us > TRACE_END_RAW_US:
                raise RuntimeError("Machine event outside fixed trace window")
            add_interval(cursor, time_us, active, capacity)
            event_type = int(row["type"])
            if event_type == 1:
                if active:
                    raise RuntimeError("ADD applied to active machine")
                active = True
                capacity = _normalized_capacity(row.get("capacity"))
                if capacity is None:
                    missing_add_segments += 1
                transitions["ADD"] += 1
            elif event_type == 2:
                if not active:
                    raise RuntimeError("REMOVE applied to inactive machine")
                active = False
                capacity = None
                transitions["REMOVE"] += 1
            elif event_type == 3:
                if not active:
                    raise RuntimeError("UPDATE applied to inactive machine")
                capacity = _normalized_capacity(row.get("capacity"))
                transitions["UPDATE"] += 1
            else:
                raise RuntimeError(f"Unknown machine event type: {event_type}")
            cursor = time_us
        add_interval(cursor, TRACE_END_RAW_US, active, capacity)
        final_active += int(active)
        final_inactive += int(not active)

    rows: list[dict[str, Any]] = []
    total_unknown_us = 0
    with localcontext() as context:
        context.prec = 50
        for hour, values in enumerate(accumulators):
            accounted = values["known_active_us"] + values["unknown_active_us"] + values["inactive_us"]
            if accounted != PDU17_MACHINES * HOUR_US:
                raise RuntimeError("PDU17 hourly machine-state balance failed")
            total_unknown_us += values["unknown_active_us"]
            rows.append(
                {
                    "hour_index": hour,
                    "raw_interval_start_us": TRACE_START_RAW_US + hour * HOUR_US,
                    "raw_interval_end_us": TRACE_START_RAW_US + (hour + 1) * HOUR_US,
                    "known_active_normalized_cpu_seconds": format(values["known_cpu_us"] / Decimal(1_000_000), "f"),
                    "known_active_normalized_memory_seconds": format(values["known_memory_us"] / Decimal(1_000_000), "f"),
                    "known_active_machine_seconds": format(Decimal(values["known_active_us"]) / Decimal(1_000_000), "f"),
                    "unknown_active_machine_seconds": format(Decimal(values["unknown_active_us"]) / Decimal(1_000_000), "f"),
                    "inactive_machine_seconds": format(Decimal(values["inactive_us"]) / Decimal(1_000_000), "f"),
                    "mapped_machine_seconds": str(PDU17_MACHINES * 3600),
                }
            )
    return rows, {
        "mapped_machines": len(machines),
        "hours": len(rows),
        "trace_window_raw_us": [TRACE_START_RAW_US, TRACE_END_RAW_US],
        "time_zero_is_pre_trace_snapshot": True,
        "invalid_state_transitions": 0,
        "nonzero_transition_counts": dict(sorted(transitions.items())),
        "missing_capacity_add_segments": missing_add_segments,
        "unknown_active_machine_seconds_total": format(Decimal(total_unknown_us) / Decimal(1_000_000), "f"),
        "end_active_machines": final_active,
        "end_inactive_machines": final_inactive,
        "remove_capacity_carried_forward": False,
        "missing_capacity_filled": False,
        "capacity_unit": "normalized_available_resource_not_physical_cores_or_MW",
    }


def _power_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = {}
    for line in (POWER_ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
        digest, name = line.split(maxsplit=1)
        expected[name.strip()] = digest
    source_paths = sorted(path for path in POWER_ROOT.glob("*.csv.gz") if path.name != MAPPING_PATH.name)
    if len(source_paths) != POWER_DOMAINS:
        raise RuntimeError("Power-domain count drifted")
    output: list[dict[str, Any]] = []
    domain_summaries = []
    flag_counts: Counter[tuple[bool, bool]] = Counter()
    measured_min: Decimal | None = None
    measured_max: Decimal | None = None
    production_min: Decimal | None = None
    production_max: Decimal | None = None
    expected_header = [
        "time",
        "cell",
        "pdu",
        "measured_power_util",
        "production_power_util",
        "bad_measurement_data",
        "bad_production_power_data",
    ]
    for path in source_paths:
        if expected.get(path.name) != _sha256(path):
            raise RuntimeError(f"Power source drifted: {path}")
        with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != expected_header:
                raise RuntimeError(f"Power schema drifted: {path}")
            rows = list(reader)
        if len(rows) != POWER_ROWS_PER_DOMAIN:
            raise RuntimeError(f"Power row count drifted: {path}")
        rows.sort(key=lambda row: int(row["time"]))
        times = [int(row["time"]) for row in rows]
        if times[0] != TRACE_START_RAW_US or times[-1] != TRACE_END_RAW_US - POWER_STEP_US:
            raise RuntimeError(f"Power time range drifted: {path}")
        if any(right - left != POWER_STEP_US for left, right in zip(times, times[1:])):
            raise RuntimeError(f"Power cadence drifted: {path}")
        cell, pdu = rows[0]["cell"], rows[0]["pdu"]
        if any(row["cell"] != cell or row["pdu"] != pdu for row in rows):
            raise RuntimeError(f"Mixed power domain: {path}")
        local_flags = Counter()
        for row in rows:
            measured = Decimal(row["measured_power_util"])
            production = Decimal(row["production_power_util"])
            if any(not value.is_finite() or value < 0 or value > 1 for value in (measured, production)):
                raise RuntimeError(f"Power utilization outside documented [0,1] range: {path}")
            measured_min = measured if measured_min is None else min(measured_min, measured)
            measured_max = measured if measured_max is None else max(measured_max, measured)
            production_min = production if production_min is None else min(production_min, production)
            production_max = production if production_max is None else max(production_max, production)
            measured_flag = row["bad_measurement_data"].lower() == "true"
            production_flag = row["bad_production_power_data"].lower() == "true"
            if row["bad_measurement_data"].lower() not in {"true", "false"} or row["bad_production_power_data"].lower() not in {"true", "false"}:
                raise RuntimeError(f"Unknown power flag token: {path}")
            local_flags[(measured_flag, production_flag)] += 1
            flag_counts[(measured_flag, production_flag)] += 1
            time_us = int(row["time"])
            output.append(
                {
                    "source_object": path.name,
                    "cell": cell,
                    "pdu": pdu,
                    "raw_interval_start_us": time_us,
                    "raw_interval_end_us": time_us + POWER_STEP_US,
                    "trace_relative_start_us": time_us - TRACE_START_RAW_US,
                    "measured_power_util": row["measured_power_util"],
                    "production_power_util": row["production_power_util"],
                    "bad_measurement_data": measured_flag,
                    "bad_production_power_data": production_flag,
                }
            )
        domain_summaries.append(
            {
                "cell": cell,
                "pdu": pdu,
                "rows": len(rows),
                "bad_flag_pair_counts": {f"{int(a)}{int(b)}": n for (a, b), n in sorted(local_flags.items())},
            }
        )
    output.sort(key=lambda row: (row["cell"], row["pdu"], row["raw_interval_start_us"]))
    return output, {
        "domains": len(domain_summaries),
        "rows": len(output),
        "rows_per_domain": POWER_ROWS_PER_DOMAIN,
        "hours": HOURS,
        "cadence_us": POWER_STEP_US,
        "raw_interval": [TRACE_START_RAW_US, TRACE_END_RAW_US],
        "all_domains_continuous_complete_5_minute_grid": True,
        "all_source_rows_retained": True,
        "quality_filter_applied": False,
        "measured_power_util_min": format(measured_min, "f"),
        "measured_power_util_max": format(measured_max, "f"),
        "production_power_util_min": format(production_min, "f"),
        "production_power_util_max": format(production_max, "f"),
        "bad_flag_pair_counts": {f"{int(a)}{int(b)}": n for (a, b), n in sorted(flag_counts.items())},
        "flag_true_means_low_confidence_resolved": False,
        "domains_detail": domain_summaries,
    }


def _zeus_power_rows() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    table_counts = {}
    with localcontext() as context:
        context.prec = 50
        for path in sorted((ZEUS_ROOT / "trace").glob("summary_power_*.csv")):
            gpu = path.stem.removeprefix("summary_power_")
            with path.open(encoding="utf-8", newline="") as stream:
                source = list(csv.DictReader(stream))
            seen = set()
            for row in source:
                key = tuple(row[field] for field in ("dataset", "network", "batch_size", "optimizer", "power_limit"))
                if key in seen:
                    raise RuntimeError(f"Duplicate Zeus power configuration: {gpu} {key}")
                seen.add(key)
                duration = Decimal(row["time_per_epoch"])
                average_power = Decimal(row["average_power"])
                power_limit = Decimal(row["power_limit"])
                if any(not value.is_finite() or value <= 0 for value in (duration, average_power, power_limit)):
                    raise RuntimeError(f"Invalid Zeus power value: {gpu} {key}")
                rows.append(
                    {
                        "gpu": gpu,
                        "dataset": row["dataset"],
                        "network": row["network"],
                        "batch_size": int(row["batch_size"]),
                        "optimizer": row["optimizer"],
                        "power_limit_w": format(power_limit, "f"),
                        "time_per_epoch_seconds": format(duration, "f"),
                        "average_gpu_power_w": format(average_power, "f"),
                        "derived_energy_per_epoch_joule": format(duration * average_power, "f"),
                    }
                )
            table_counts[gpu] = len(source)
    if set(table_counts) != {"a40", "p100", "rtx6000", "v100"}:
        raise RuntimeError("Zeus GPU table set drifted")
    rows.sort(key=lambda row: tuple(str(row[field]) for field in ("gpu", "dataset", "network", "batch_size", "optimizer", "power_limit_w")))
    return rows, {
        "rows": len(rows),
        "rows_by_gpu": dict(sorted(table_counts.items())),
        "energy_per_epoch_is_direct_product_not_fitted": True,
        "measurements_per_configuration": 1,
        "production_cluster_or_pdu_power": False,
        "alibaba_observed_job_power_join": False,
    }


def _row_group_prunable(
    *,
    start_min: int | None,
    end_max: int | None,
    machine_min: int | None,
    machine_max: int | None,
    target_start: int,
    target_end: int,
    target_machines: set[int],
) -> bool:
    time_disjoint = False if start_min is None or end_max is None else end_max <= target_start or start_min >= target_end
    machine_disjoint = False if machine_min is None or machine_max is None else not any(
        machine_min <= machine <= machine_max for machine in target_machines
    )
    return time_disjoint or machine_disjoint


def _footer_audit(metadata: dict[str, Any], pdu17_machines: set[int]) -> dict[str, Any]:
    _, pq = _require_pyarrow()
    sample_object_bytes = 0
    sample_projected_bytes = 0
    sample_rows = 0
    details = []
    all_row_groups_unprunable = True
    any_required_page_index = False
    for entry in metadata["files"]:
        payload = (GOOGLE_FOOTERS / entry["path"]).read_bytes()
        if payload[-4:] != b"PAR1" or int.from_bytes(payload[-8:-4], "little") != len(payload) - 8:
            raise RuntimeError(f"Invalid retained Parquet footer: {entry['path']}")
        parquet = pq.ParquetFile(io.BytesIO(b"PAR1" + payload))
        projected = 0
        row_groups = []
        for index in range(parquet.metadata.num_row_groups):
            group = parquet.metadata.row_group(index)
            columns = {group.column(i).path_in_schema: group.column(i) for i in range(group.num_columns)}
            if not REQUIRED_USAGE_COLUMNS.issubset(columns):
                raise RuntimeError("Usage footer schema drifted")
            projected += sum(columns[name].total_compressed_size for name in REQUIRED_USAGE_COLUMNS)
            start_stats = columns["start_time"].statistics
            end_stats = columns["end_time"].statistics
            machine_stats = columns["machine_id"].statistics
            indexed = any(
                columns[name].has_column_index or columns[name].has_offset_index for name in REQUIRED_USAGE_COLUMNS
            )
            prunable = _row_group_prunable(
                start_min=None if start_stats is None else start_stats.min,
                end_max=None if end_stats is None else end_stats.max,
                machine_min=None if machine_stats is None else machine_stats.min,
                machine_max=None if machine_stats is None else machine_stats.max,
                target_start=TRACE_START_RAW_US,
                target_end=TRACE_END_RAW_US,
                target_machines=pdu17_machines,
            )
            all_row_groups_unprunable &= not prunable
            any_required_page_index |= indexed
            row_groups.append(
                {
                    "rows": group.num_rows,
                    "start_time_min_us": None if start_stats is None else start_stats.min,
                    "start_time_max_us": None if start_stats is None else start_stats.max,
                    "end_time_min_us": None if end_stats is None else end_stats.min,
                    "end_time_max_us": None if end_stats is None else end_stats.max,
                    "machine_id_min": None if machine_stats is None else machine_stats.min,
                    "machine_id_max": None if machine_stats is None else machine_stats.max,
                    "required_columns_have_any_page_index": indexed,
                    "prunable_by_full_trace_time_or_pdu17_machine_range_stats": prunable,
                }
            )
        sample_object_bytes += int(entry["object_bytes"])
        sample_projected_bytes += projected
        sample_rows += parquet.metadata.num_rows
        details.append(
            {
                "object_name": entry["object_name"],
                "generation": entry["generation"],
                "footer_sha256": entry["sha256"],
                "object_bytes": int(entry["object_bytes"]),
                "rows": parquet.metadata.num_rows,
                "row_groups": row_groups,
                "required_six_columns_compressed_bytes": projected,
            }
        )
    with localcontext() as context:
        context.prec = 50
        ratio = Decimal(sample_projected_bytes) / Decimal(sample_object_bytes)
        estimated = int((ratio * Decimal(FULL_USAGE_PARQUET_BYTES)).to_integral_value())
    return {
        "sampled_objects": len(details),
        "selection_is_fixed_spread_not_random": True,
        "sample_object_bytes": sample_object_bytes,
        "sample_rows": sample_rows,
        "required_six_columns": sorted(REQUIRED_USAGE_COLUMNS),
        "required_six_columns_compressed_bytes": sample_projected_bytes,
        "sample_compressed_ratio": format(ratio, ".12f"),
        "indicative_full_table_six_column_transfer_bytes": estimated,
        "all_sampled_row_groups_unprunable_by_time_or_pdu17_range": all_row_groups_unprunable,
        "required_columns_have_any_page_index_in_sample": any_required_page_index,
        "supports_proof_for_all_12259_objects": False,
        "complete_pdu17_usage_extracted": False,
        "details": details,
    }


def _verify_operational_evidence(metadata: dict[str, Any]) -> dict[str, Any]:
    for entry in metadata["files"]:
        text = (GOOGLE_OPERATIONS / entry["path"]).read_text(encoding="utf-8")
        if any(marker not in text for marker in entry["evidence_markers"]):
            raise RuntimeError(f"Operational evidence marker missing: {entry['path']}")
    return metadata["interpretation"]


def run(output_dir: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite output: {output_dir}")
    _verify_fixed_sources()
    _, google_existing_hashes = _verify_bundle(GOOGLE_SUPPLEMENT)
    _, zeus_existing_hashes = _verify_bundle(ZEUS_ROOT)
    footer_metadata, footer_hashes = _verify_bundle(GOOGLE_FOOTERS)
    operations_metadata, operations_hashes = _verify_bundle(GOOGLE_OPERATIONS)
    machine_events, equivalence = _read_machine_events()
    pdu17_machines = _pdu17_machine_ids()
    capacity_rows, capacity_summary = _pdu17_capacity_hours(machine_events, pdu17_machines)
    power_rows, power_summary = _power_rows()
    zeus_rows, zeus_summary = _zeus_power_rows()
    footer_summary = _footer_audit(footer_metadata, pdu17_machines)
    operations_summary = _verify_operational_evidence(operations_metadata)

    output_dir.parent.mkdir(parents=True, exist_ok=True)
    stage = output_dir.parent / f".{output_dir.name}.tmp-{os.getpid()}"
    if stage.exists():
        raise FileExistsError(f"Staging path already exists: {stage}")
    stage.mkdir()
    try:
        files = {
            "google_power_57_domains_unfiltered.jsonl.gz": (power_rows, len(power_rows)),
            "pdu17_hourly_normalized_capacity.jsonl.gz": (capacity_rows, len(capacity_rows)),
            "zeus_four_gpu_power_performance.jsonl.gz": (zeus_rows, len(zeus_rows)),
        }
        output_files = {}
        for name, (rows, expected_count) in files.items():
            actual_count = _write_jsonl_gzip(stage / name, rows)
            if actual_count != expected_count:
                raise RuntimeError(f"Output row count drifted: {name}")
            output_files[name] = {
                "rows": actual_count,
                "bytes": (stage / name).stat().st_size,
                "sha256": _sha256(stage / name),
            }
        summary = {
            "status": "DRAFT_NONAUTHORITATIVE_DATA_PREPARATION",
            "schema": "public_compute_multiday_v1",
            "source_bindings": {
                "protected_source_sha256": {str(path.relative_to(ROOT)).replace("\\", "/"): value for path, value in EXPECTED_SOURCE_HASHES.items()},
                "google_existing_bundle_file_sha256": google_existing_hashes,
                "zeus_existing_bundle_file_sha256": zeus_existing_hashes,
                "footer_source_metadata_sha256": _sha256(GOOGLE_FOOTERS / "SOURCE_METADATA.json"),
                "footer_range_sha256": footer_hashes,
                "operational_source_metadata_sha256": _sha256(GOOGLE_OPERATIONS / "SOURCE_METADATA.json"),
                "operational_html_sha256": operations_hashes,
                "implementation_sha256": _sha256(Path(__file__)),
            },
            "machine_events_format_equivalence": equivalence,
            "pdu17_hourly_capacity": capacity_summary,
            "google_power": power_summary,
            "zeus_four_gpu_power": zeus_summary,
            "usage_footer_audit": footer_summary,
            "unbound_bigquery_session_observation": {
                "evidence_status": "unbound_session_observation_not_a_budget_ledger",
                "checked_at_utc": "2026-09-12",
                "public_instance_usage_rows": FULL_USAGE_ROWS_FROM_PUBLIC_TABLE_METADATA,
                "public_instance_usage_logical_bytes": 2_297_003_786_056,
                "table_partitioned": False,
                "table_clustered": False,
                "six_column_dry_run_scan_bytes": SIX_COLUMN_DRY_RUN_BYTES,
                "dry_run_only": True,
                "query_jobs_executed": 0,
                "accessible_projects_checked": 2,
                "month_to_date_jobs_visible_to_all_users": 0,
                "billing_account_wide_usage_verified": False,
                "usable_to_authorize_or_account_for_a_paid_query": False,
                "reason": "Cloud Billing API was disabled; no API was enabled and no query was executed. A later query successor must bind its own dry run, SQL, parameters, job ID, and billed bytes.",
            },
            "operational_evidence": operations_summary,
            "output_files": output_files,
            "interpretation": {
                "all_power_source_values_and_flags_prepared": True,
                "pdu17_normalized_capacity_time_integral_prepared": True,
                "zeus_controlled_gpu_performance_prepared": True,
                "complete_pdu17_multiday_cpu_usage_prepared": False,
                "quality_flag_semantics_resolved": False,
                "machine_population_complete_for_pdu_workload": False,
                "absolute_power_mw_available": False,
                "observed_job_flexibility_available": False,
                "true_job_deadline_observed": False,
                "true_recovery_deadline_observed": False,
                "shared_flexibility_budget_observed": False,
                "continuous_model_input_ready": False,
                "model_parameter_changed": False,
                "formal_result": False,
                "paper_claim": False,
                "security_certified": False,
            },
        }
        (stage / "summary.json").write_text(
            json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        os.replace(stage, output_dir)
        return summary
    except Exception:
        if stage.exists():
            shutil.rmtree(stage)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.output_dir), ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
