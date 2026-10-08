"""Audit the bounded Google ClusterData and Zeus public-data supplements."""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import statistics
from collections import Counter, defaultdict
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
GOOGLE_ROOT = ROOT / "data/raw/google_cluster_2019_public_supplement_v1/upstream"
ZEUS_ROOT = ROOT / "data/raw/zeus_training_energy_public_v1/upstream"
MAPPING_PATH = ROOT / "data/raw/google_power_2019/2019/upstream/machine_to_pdu_mapping.csv.gz"
MAPPING_SHA256 = "69b88e5662348030b074fef2008a4f2c16927a68b2d218a8c7c5cf350dc0aa8d"
DEFAULT_OUTPUT = ROOT / "results/tables/public_compute_supplements_v1_non_authoritative/summary.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _md5_base64(path: Path) -> str:
    digest = hashlib.md5()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return base64.b64encode(digest.digest()).decode("ascii")


def _verify_bundle(root: Path) -> tuple[dict[str, Any], dict[str, str]]:
    metadata_path = root / "SOURCE_METADATA.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    expected_paths = {entry["path"] for entry in metadata["files"]}
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.name != "SOURCE_METADATA.json"
    }
    if actual_paths != expected_paths:
        raise RuntimeError(f"Bundle membership drifted for {root}")
    hashes: dict[str, str] = {}
    for entry in metadata["files"]:
        path = root / entry["path"]
        if path.stat().st_size != int(entry["bytes"]):
            raise RuntimeError(f"Size drifted: {path}")
        hashes[entry["path"]] = _sha256(path)
        if hashes[entry["path"]] != entry["sha256"]:
            raise RuntimeError(f"SHA-256 drifted: {path}")
        if "md5_base64" in entry and _md5_base64(path) != entry["md5_base64"]:
            raise RuntimeError(f"MD5 drifted: {path}")
    return metadata, hashes


def _parquet_magic(path: Path) -> bool:
    with path.open("rb") as stream:
        first = stream.read(4)
        stream.seek(-4, 2)
        last = stream.read(4)
    return first == b"PAR1" and last == b"PAR1"


def _median_seconds(values_us: list[int]) -> str | None:
    if not values_us:
        return None
    ordered = sorted(values_us)
    middle = len(ordered) // 2
    numerator = ordered[middle] if len(ordered) % 2 else ordered[middle - 1] + ordered[middle]
    denominator = 1_000_000 if len(ordered) % 2 else 2_000_000
    with localcontext() as context:
        context.prec = 30
        return format(Decimal(numerator) / Decimal(denominator), "f")


def _audit_google_machine_events() -> dict[str, Any]:
    path = GOOGLE_ROOT / "machine_events-000000000000.json.gz"
    rows: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            rows.append(json.loads(line, parse_float=Decimal))
    schema = json.loads((GOOGLE_ROOT / "machine_events.schema.json").read_text(encoding="utf-8"))
    schema_fields = [field["name"] for field in schema]
    if schema_fields != ["time", "machine_id", "type", "switch_id", "capacity", "platform_id", "missing_data_reason"]:
        raise RuntimeError("Machine-events schema drifted")

    events_by_machine: dict[str, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    type_counts: Counter[str] = Counter()
    reason_presence = Counter()
    capacity_rows = 0
    capacity_cpus: list[Decimal] = []
    capacity_memory: list[Decimal] = []
    capacity_numeric_issues = Counter()
    natural_keys: Counter[tuple[int, str]] = Counter()
    for index, row in enumerate(rows):
        time_us = int(row["time"])
        machine_id = row["machine_id"]
        event_type = row["type"]
        events_by_machine[machine_id].append((time_us, index, row))
        type_counts[event_type] += 1
        natural_keys[(time_us, machine_id)] += 1
        if "missing_data_reason" not in row:
            reason_presence["field_absent"] += 1
        elif row["missing_data_reason"] is None:
            reason_presence["explicit_null"] += 1
        else:
            reason_presence[f"value_{row['missing_data_reason']}"] += 1
        capacity = row.get("capacity")
        if capacity is not None:
            capacity_rows += 1
            for field, values in (("cpus", capacity_cpus), ("memory", capacity_memory)):
                if capacity.get(field) is None:
                    capacity_numeric_issues[f"{field}_missing"] += 1
                    continue
                value = Decimal(str(capacity[field]))
                if not value.is_finite() or value < 0:
                    capacity_numeric_issues[f"{field}_nonfinite_or_negative"] += 1
                else:
                    values.append(value)

    time_zero = [row for row in rows if int(row["time"]) == 0]
    nonzero_times = [int(row["time"]) for row in rows if int(row["time"]) > 0]
    multiple_time_zero = Counter(row["machine_id"] for row in time_zero)
    missing_capacity = [row for row in rows if row.get("capacity") is None]
    recovery_delays: list[int] = []
    recovery_types: Counter[str] = Counter()
    first_missing_add = 0
    for row in missing_capacity:
        machine_id = row["machine_id"]
        sequence = sorted(events_by_machine[machine_id], key=lambda item: (item[0], item[1]))
        position = next(index for index, item in enumerate(sequence) if item[2] is row)
        if position == 0 and row["type"] == "1" and int(row["time"]) > 0:
            first_missing_add += 1
        next_known = next((item for item in sequence[position + 1 :] if item[2].get("capacity") is not None), None)
        if next_known is not None:
            recovery_delays.append(next_known[0] - int(row["time"]))
            recovery_types[next_known[2]["type"]] += 1

    with gzip.open(MAPPING_PATH, "rt", encoding="utf-8", newline="") as stream:
        mapping = list(csv.DictReader(stream))
    if _sha256(MAPPING_PATH) != MAPPING_SHA256 or set(mapping[0]) != {"machine_id", "pdu", "cell"}:
        raise RuntimeError("Existing machine-to-PDU mapping drifted")
    f_rows = [row for row in mapping if row["cell"] == "f"]
    f_machines = {row["machine_id"] for row in f_rows}
    pdu17_machines = {row["machine_id"] for row in f_rows if row["pdu"] == "pdu17"}
    event_machines = set(events_by_machine)
    snapshot = {
        row["machine_id"]: row["capacity"]
        for row in time_zero
        if row["type"] == "1" and row.get("capacity") is not None
    }
    pdu17_snapshot = [snapshot[machine] for machine in sorted(pdu17_machines & snapshot.keys())]
    with localcontext() as context:
        context.prec = 30
        pdu17_cpu = sum((Decimal(str(capacity["cpus"])) for capacity in pdu17_snapshot), Decimal(0))
        pdu17_memory = sum((Decimal(str(capacity["memory"])) for capacity in pdu17_snapshot), Decimal(0))

    return {
        "documented_json_table_complete_for_cell_f": True,
        "rows": len(rows),
        "machines": len(event_machines),
        "event_type_counts_by_code": dict(sorted(type_counts.items())),
        "event_type_code_labels": {"1": "ADD", "2": "REMOVE", "3": "UPDATE"},
        "time_zero": {
            "rows": len(time_zero),
            "machines": len({row["machine_id"] for row in time_zero}),
            "machines_with_multiple_rows": sum(count > 1 for count in multiple_time_zero.values()),
            "all_are_add_with_capacity": all(row["type"] == "1" and row.get("capacity") is not None for row in time_zero),
            "interpretation": "pre_trace_snapshot_special_value_not_an_ordinary_timestamp",
        },
        "nonzero_time_min_us": min(nonzero_times),
        "nonzero_time_max_us": max(nonzero_times),
        "duplicate_machine_time_keys": sum(count - 1 for count in natural_keys.values() if count > 1),
        "capacity": {
            "rows_present": capacity_rows,
            "rows_missing": len(missing_capacity),
            "missing_rows_that_are_first_nonzero_add": first_missing_add,
            "missing_rows_with_later_known_capacity": len(recovery_delays),
            "later_known_event_type_counts": dict(sorted(recovery_types.items())),
            "later_known_delay_seconds_min": format(Decimal(min(recovery_delays)) / Decimal(1_000_000), "f"),
            "later_known_delay_seconds_median": _median_seconds(recovery_delays),
            "later_known_delay_seconds_max": format(Decimal(max(recovery_delays)) / Decimal(1_000_000), "f"),
            "normalized_cpu_min": format(min(capacity_cpus), "f"),
            "normalized_cpu_max": format(max(capacity_cpus), "f"),
            "normalized_memory_min": format(min(capacity_memory), "f"),
            "normalized_memory_max": format(max(capacity_memory), "f"),
            "numeric_issue_counts": dict(sorted(capacity_numeric_issues.items())),
            "missing_intervals_must_remain_unknown": True,
        },
        "missing_data_reason_presence": dict(sorted(reason_presence.items())),
        "mapping": {
            "mapping_rows_all_cells": len(mapping),
            "cell_f_mapping_rows": len(f_rows),
            "cell_f_machines": len(f_machines),
            "cell_f_mapped_machines_without_events": len(f_machines - event_machines),
            "cell_f_event_machines_without_mapping": len(event_machines - f_machines),
            "pdu17_mapped_machines": len(pdu17_machines),
            "pdu17_time_zero_snapshot_machines": len(pdu17_snapshot),
            "pdu17_time_zero_normalized_cpu_sum": format(pdu17_cpu, "f"),
            "pdu17_time_zero_normalized_memory_sum": format(pdu17_memory, "f"),
            "snapshot_is_complete_physical_capacity": False,
        },
    }


def _decimal_range(rows: list[dict[str, str]], field: str) -> tuple[str, str, int]:
    values: list[Decimal] = []
    invalid = 0
    for row in rows:
        try:
            value = Decimal(row[field])
        except Exception:
            invalid += 1
            continue
        if not value.is_finite() or value <= 0:
            invalid += 1
        else:
            values.append(value)
    return format(min(values), "f"), format(max(values), "f"), invalid


def _audit_zeus() -> dict[str, Any]:
    trace = ZEUS_ROOT / "trace"
    with (trace / "summary_train.csv").open(encoding="utf-8", newline="") as stream:
        train = list(csv.DictReader(stream))
    expected_train = ["dataset", "network", "batch_size", "optimizer", "learning_rate", "run", "target_metric", "target_epoch"]
    if list(train[0]) != expected_train:
        raise RuntimeError("Zeus train schema drifted")
    target_epochs = Counter(row["target_epoch"] for row in train if not row["target_epoch"].isdigit())
    configs: dict[tuple[str, ...], set[str]] = defaultdict(set)
    invalid_train_numeric = 0
    for row in train:
        key = tuple(row[field] for field in ("dataset", "network", "batch_size", "optimizer", "learning_rate"))
        configs[key].add(row["run"])
        try:
            numeric_values = (Decimal(row["batch_size"]), Decimal(row["learning_rate"]), Decimal(row["run"]), Decimal(row["target_metric"]))
            if any(not value.is_finite() or value <= 0 for value in numeric_values):
                invalid_train_numeric += 1
        except Exception:
            invalid_train_numeric += 1

    power_tables: dict[str, Any] = {}
    expected_power = ["dataset", "network", "batch_size", "optimizer", "power_limit", "time_per_epoch", "average_power"]
    for path in sorted(trace.glob("summary_power_*.csv")):
        gpu = path.stem.removeprefix("summary_power_")
        with path.open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if list(rows[0]) != expected_power:
            raise RuntimeError(f"Zeus power schema drifted: {gpu}")
        keys = [tuple(row[field] for field in ("dataset", "network", "batch_size", "optimizer", "power_limit")) for row in rows]
        ranges = {field: _decimal_range(rows, field) for field in ("power_limit", "time_per_epoch", "average_power")}
        power_tables[gpu] = {
            "rows": len(rows),
            "dataset_network_pairs": len({(row["dataset"], row["network"]) for row in rows}),
            "duplicate_configuration_rows": len(keys) - len(set(keys)),
            "power_limit_w_min": ranges["power_limit"][0],
            "power_limit_w_max": ranges["power_limit"][1],
            "time_per_epoch_seconds_min": ranges["time_per_epoch"][0],
            "time_per_epoch_seconds_max": ranges["time_per_epoch"][1],
            "average_gpu_power_w_min": ranges["average_power"][0],
            "average_gpu_power_w_max": ranges["average_power"][1],
            "invalid_nonpositive_or_nonfinite_numeric_values": sum(value[2] for value in ranges.values()),
            "measurement_repeats_per_configuration": 1,
        }
    return {
        "train": {
            "rows": len(train),
            "dataset_network_pairs": len({(row["dataset"], row["network"]) for row in train}),
            "configurations": len(configs),
            "distinct_runs_per_configuration_min": min(len(runs) for runs in configs.values()),
            "distinct_runs_per_configuration_max": max(len(runs) for runs in configs.values()),
            "distinct_run_count_distribution": {
                str(count): frequency for count, frequency in sorted(Counter(len(runs) for runs in configs.values()).items())
            },
            "configurations_with_fewer_than_4_distinct_runs": sum(len(runs) < 4 for runs in configs.values()),
            "target_epoch_integer_rows": sum(row["target_epoch"].isdigit() for row in train),
            "target_epoch_sentinel_counts": dict(sorted(target_epochs.items())),
            "invalid_nonpositive_or_nonfinite_core_numeric_rows": invalid_train_numeric,
            "target_epoch_nan_interpretation_resolved": False,
            "target_epoch_is_business_deadline": False,
        },
        "power": power_tables,
        "power_measurements_are_repeated_samples": False,
        "alibaba_mapping_is_observed_job_power_link": False,
    }


def run(output_path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    google_metadata, google_hashes = _verify_bundle(GOOGLE_ROOT)
    zeus_metadata, zeus_hashes = _verify_bundle(ZEUS_ROOT)
    summary = {
        "status": "DRAFT_NONAUTHORITATIVE",
        "schema": "public_compute_supplements_v1",
        "google": {
            "source_metadata_sha256": _sha256(GOOGLE_ROOT / "SOURCE_METADATA.json"),
            "downloaded_file_sha256": google_hashes,
            "cell_bucket_inventory": google_metadata["cell_bucket_inventory"],
            "machine_events": _audit_google_machine_events(),
            "machine_events_parquet_transport_magic_valid": _parquet_magic(GOOGLE_ROOT / "machine_events-000000000000.parquet.gz"),
            "machine_events_json_parquet_content_equivalence_verified": False,
            "usage_pilot": {
                **google_metadata["usage_pilot"],
                "downloaded_object_bytes": (GOOGLE_ROOT / "instance_usage-000000000000.parquet.gz").stat().st_size,
                "parquet_transport_magic_valid": _parquet_magic(GOOGLE_ROOT / "instance_usage-000000000000.parquet.gz"),
            },
        },
        "zeus": {
            "source_metadata_sha256": _sha256(ZEUS_ROOT / "SOURCE_METADATA.json"),
            "downloaded_file_sha256": zeus_hashes,
            **_audit_zeus(),
        },
        "provenance": {
            "existing_mapping_sha256": _sha256(MAPPING_PATH),
            "implementation_sha256": _sha256(Path(__file__)),
            "new_raw_bytes": sum(path.stat().st_size for root in (GOOGLE_ROOT, ZEUS_ROOT) for path in root.rglob("*") if path.is_file()),
            "paid_queries": 0,
            "solver_calls": 0,
        },
        "interpretation": {
            "google_machine_event_chronology_available": True,
            "google_machine_capacity_complete": False,
            "google_usage_pilot_content_verified": False,
            "google_multiday_usage_complete": False,
            "zeus_controlled_training_power_evidence_available": True,
            "zeus_production_cluster_power_observed": False,
            "absolute_facility_power_mw_available": False,
            "flexibility_observed": False,
            "deadline_observed": False,
            "recovery_parameters_observed": False,
            "continuous_model_input_ready": False,
            "formal_result": False,
            "paper_claim": False,
            "security_certified": False,
        },
    }
    payload = (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")
    if output_path.exists() or (output_path.parent.exists() and any(output_path.parent.iterdir())):
        raise FileExistsError(f"Refusing to overwrite diagnostic output: {output_path.parent}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(payload)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
