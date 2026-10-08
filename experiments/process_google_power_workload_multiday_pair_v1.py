"""Build a non-authoritative 744-hour CPU-power-capacity alignment."""

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
from collections import Counter, defaultdict
from decimal import Context, Decimal, InvalidOperation, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any, Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs/google_power_workload_multiday_pair_v1.DRAFT.yaml"
DEFAULT_OUTPUT = ROOT / "results/tables/google_power_workload_multiday_pair_v1_non_authoritative"
HOUR_US = 3_600_000_000
POWER_STEP_US = 300_000_000
WINDOW_START_US = 600_000_000
WINDOW_END_US = 2_679_000_000_000
HOURS = 744
TIERS = (
    "1_free",
    "2_beb",
    "3_mid",
    "4_production",
    "5_monitoring",
    "ambiguous",
    "unknown",
)
DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
Q12 = Decimal("0.000000000001")

CPU_DECIMAL_FIELDS = (
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
CPU_COUNT_FIELDS = (
    "fragment_piece_count",
    "usage_group_count",
    "cpu_conflict_usage_group_count",
    "exact_duplicate_usage_group_count",
)
CPU_PAYLOAD_FIELDS = CPU_DECIMAL_FIELDS + CPU_COUNT_FIELDS
CPU_SOURCE_FIELDS = (
    "record_type",
    "hour_index",
    "raw_interval_start_us",
    "raw_interval_end_us",
    "collection_type",
    "priority_tier",
    *CPU_DECIMAL_FIELDS[:7],
    *CPU_COUNT_FIELDS,
    *CPU_DECIMAL_FIELDS[7:],
    "audit_json",
)
POWER_SOURCE_FIELDS = (
    "bad_measurement_data",
    "bad_production_power_data",
    "cell",
    "measured_power_util",
    "pdu",
    "production_power_util",
    "raw_interval_end_us",
    "raw_interval_start_us",
    "source_object",
    "trace_relative_start_us",
)
CAPACITY_FIELDS = (
    "mapped_machine_seconds",
    "known_active_machine_seconds",
    "unknown_active_machine_seconds",
    "inactive_machine_seconds",
    "known_active_normalized_cpu_seconds",
    "known_active_normalized_memory_seconds",
)
CAPACITY_SOURCE_FIELDS = ("hour_index", "raw_interval_start_us", "raw_interval_end_us", *CAPACITY_FIELDS)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise RuntimeError(f"Invalid decimal in {name}: {value!r}") from exc
    if not result.is_finite():
        raise RuntimeError(f"Non-finite decimal in {name}")
    return result


def _sum(values: Iterable[Decimal]) -> Decimal:
    with localcontext(DECIMAL_CONTEXT):
        total = Decimal(0)
        for value in values:
            total += value
        return +total


def _fixed(value: Decimal, places: int) -> str:
    quantum = Decimal(1).scaleb(-places)
    with localcontext(DECIMAL_CONTEXT):
        return format(value.quantize(quantum), f".{places}f")


def _load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    contract = config["contract"]
    expected = {
        "status": "DRAFT_NONAUTHORITATIVE_ALIGNMENT",
        "cell": "f",
        "pdu": "pdu17",
        "raw_window_start_us": WINDOW_START_US,
        "raw_window_end_us": WINDOW_END_US,
        "hours": HOURS,
        "raw_origin_24h_blocks": 31,
        "power_step_us": POWER_STEP_US,
        "power_samples_per_hour": 12,
        "cpu_collection_types": [0, 1],
        "cpu_priority_tiers": list(TIERS),
        "cpu_strata_per_hour": 14,
        "power_decimal_places": 12,
        "decimal_precision": 50,
        "decimal_rounding": "ROUND_HALF_EVEN",
        "json_line_ending": "LF",
    }
    if config["status"] != expected.pop("status"):
        raise RuntimeError("Alignment status drifted")
    for field, value in expected.items():
        if contract[field] != value:
            raise RuntimeError(f"Alignment contract drifted: {field}")
    expected_interpretation = {
        "unfiltered_alignment_available": True,
        "power_quality_filter_applied": False,
        "power_quality_flag_semantics_resolved": False,
        "population_is_complete_pdu_workload": False,
        "cpu_capacity_ratio_computed": False,
        "absolute_power_mw_available": False,
        "headroom_computed": False,
        "flexibility_observed": False,
        "deadline_observed": False,
        "recovery_parameters_observed": False,
        "natural_calendar_days_identified": False,
        "continuous_model_input_ready": False,
        "model_parameter_changed": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }
    if config["interpretation"] != expected_interpretation:
        raise RuntimeError("Alignment interpretation gates drifted")
    return config


def _source_paths(config: dict[str, Any]) -> dict[str, Path]:
    source = config["source"]
    paths = {
        "cpu": ROOT / source["cpu_path"],
        "cpu_metadata": ROOT / source["cpu_metadata_path"],
        "power": ROOT / source["power_path"],
        "capacity": ROOT / source["capacity_path"],
        "prepare_summary": ROOT / source["prepare_summary_path"],
    }
    for name, path in paths.items():
        if _sha256(path) != source[f"{name}_sha256"]:
            raise RuntimeError(f"Source hash drifted: {name}")
    cpu_metadata = json.loads(paths["cpu_metadata"].read_text(encoding="utf-8"))
    if (
        cpu_metadata.get("status") != "DRAFT_NONAUTHORITATIVE_PUBLIC_DATA_ACQUISITION"
        or cpu_metadata.get("schema") != "google_power_workload_multiday_bigquery_v1"
        or cpu_metadata.get("result_sha256") != source["cpu_sha256"]
        or cpu_metadata.get("fields") != list(CPU_SOURCE_FIELDS)
        or cpu_metadata.get("result", {}).get("hourly_rows") != 10_416
        or cpu_metadata.get("result", {}).get("audit_rows") != 1
    ):
        raise RuntimeError("CPU source metadata binding drifted")
    prepare_summary = json.loads(paths["prepare_summary"].read_text(encoding="utf-8"))
    output_files = prepare_summary.get("output_files", {})
    if (
        prepare_summary.get("status") != "DRAFT_NONAUTHORITATIVE_DATA_PREPARATION"
        or prepare_summary.get("schema") != "public_compute_multiday_v1"
        or output_files.get("google_power_57_domains_unfiltered.jsonl.gz", {}).get("sha256")
        != source["power_sha256"]
        or output_files.get("pdu17_hourly_normalized_capacity.jsonl.gz", {}).get("sha256")
        != source["capacity_sha256"]
        or prepare_summary.get("google_power", {}).get("raw_interval")
        != [WINDOW_START_US, WINDOW_END_US]
        or prepare_summary.get("pdu17_hourly_capacity", {}).get("trace_window_raw_us")
        != [WINDOW_START_US, WINDOW_END_US]
    ):
        raise RuntimeError("Prepared source metadata binding drifted")
    return paths


def _read_cpu(path: Path) -> tuple[dict[int, list[dict[str, str]]], dict[str, Any]]:
    by_hour: dict[int, list[dict[str, str]]] = defaultdict(list)
    audits: list[dict[str, Any]] = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(CPU_SOURCE_FIELDS):
            raise RuntimeError("CPU source schema drifted")
        for row in reader:
            if row["record_type"] == "audit":
                audits.append(json.loads(row["audit_json"]))
                continue
            if row["record_type"] != "hourly_usage":
                raise RuntimeError("Unexpected CPU record type")
            hour = int(row["hour_index"])
            if not 0 <= hour < HOURS:
                raise RuntimeError("CPU hour index out of range")
            if int(row["raw_interval_start_us"]) != WINDOW_START_US + hour * HOUR_US:
                raise RuntimeError("CPU raw interval start drifted")
            if int(row["raw_interval_end_us"]) != WINDOW_START_US + (hour + 1) * HOUR_US:
                raise RuntimeError("CPU raw interval end drifted")
            collection = int(row["collection_type"])
            tier = row["priority_tier"]
            if collection not in (0, 1) or tier not in TIERS:
                raise RuntimeError("Unexpected CPU stratum")
            numbers = {field: _decimal(row[field], field) for field in CPU_DECIMAL_FIELDS}
            if any(value < 0 for value in numbers.values()):
                raise RuntimeError("Negative CPU diagnostic")
            if numbers["observed_cpu_ncu_lower"] > numbers["observed_cpu_ncu_upper"]:
                raise RuntimeError("CPU NCU endpoints inverted")
            if (
                numbers["observed_cpu_time_ncu_seconds_lower"]
                > numbers["observed_cpu_time_ncu_seconds_upper"]
            ):
                raise RuntimeError("CPU-time endpoints inverted")
            if (
                numbers["synthesized_cpu_time_ncu_seconds_lower"]
                > numbers["synthesized_cpu_time_ncu_seconds_upper"]
            ):
                raise RuntimeError("Synthesized CPU-time endpoints inverted")
            if any(int(row[field]) < 0 for field in CPU_COUNT_FIELDS):
                raise RuntimeError("Negative CPU count")
            payload = {"collection_type": collection, "priority_tier": tier}
            payload.update({field: row[field] for field in CPU_PAYLOAD_FIELDS})
            by_hour[hour].append(payload)
    if len(audits) != 1:
        raise RuntimeError("CPU source must contain exactly one audit row")
    expected_keys = {(collection, tier) for collection in (0, 1) for tier in TIERS}
    if set(by_hour) != set(range(HOURS)):
        raise RuntimeError("CPU source is missing an hour")
    for hour, rows in by_hour.items():
        keys = {(row["collection_type"], row["priority_tier"]) for row in rows}
        if len(rows) != 14 or keys != expected_keys:
            raise RuntimeError(f"CPU stratum grid is missing or duplicated at hour {hour}")
        rows.sort(key=lambda row: (row["collection_type"], TIERS.index(row["priority_tier"])))
    return dict(by_hour), audits[0]


def _power_hours(rows: Iterable[dict[str, Any]], *, hours: int = HOURS) -> dict[int, dict[str, Any]]:
    samples: dict[int, dict[int, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        if set(row) != set(POWER_SOURCE_FIELDS):
            raise RuntimeError("Power source schema drifted")
        start = int(row["raw_interval_start_us"])
        end = int(row["raw_interval_end_us"])
        if start < WINDOW_START_US or start >= WINDOW_START_US + hours * HOUR_US:
            raise RuntimeError("Power sample outside fixed window")
        if end != start + POWER_STEP_US or (start - WINDOW_START_US) % POWER_STEP_US:
            raise RuntimeError("Power sample cadence or interval drifted")
        hour = (start - WINDOW_START_US) // HOUR_US
        if start in samples[hour]:
            raise RuntimeError("Duplicate power timestamp")
        measured = _decimal(row["measured_power_util"], "measured_power_util")
        production = _decimal(row["production_power_util"], "production_power_util")
        if measured < 0 or measured > 1 or production < 0 or production > 1:
            raise RuntimeError("Power utilization outside documented [0,1]")
        if type(row["bad_measurement_data"]) is not bool or type(row["bad_production_power_data"]) is not bool:
            raise RuntimeError("Power quality flag is not boolean")
        samples[hour][start] = {**row, "_measured": measured, "_production": production}
    if set(samples) != set(range(hours)):
        raise RuntimeError("Power source is missing an hour")
    result: dict[int, dict[str, Any]] = {}
    for hour in range(hours):
        expected_starts = [WINDOW_START_US + hour * HOUR_US + index * POWER_STEP_US for index in range(12)]
        if set(samples[hour]) != set(expected_starts):
            raise RuntimeError(f"Power sample grid is missing or shifted at hour {hour}")
        ordered = [samples[hour][start] for start in expected_starts]
        with localcontext(DECIMAL_CONTEXT):
            measured_mean = _sum(row["_measured"] for row in ordered) / Decimal(12)
            production_mean = _sum(row["_production"] for row in ordered) / Decimal(12)
        flags = Counter(
            f"{int(row['bad_measurement_data'])}{int(row['bad_production_power_data'])}"
            for row in ordered
        )
        result[hour] = {
            "unit": "normalized_PDU_power_ratio",
            "sample_count": 12,
            "measured_power_util_mean": _fixed(measured_mean, 12),
            "production_power_util_mean": _fixed(production_mean, 12),
            "bad_flag_pair_counts": {key: flags.get(key, 0) for key in ("00", "01", "10", "11")},
            "quality_filter_applied": False,
        }
    return result


def _read_power(path: Path) -> dict[int, dict[str, Any]]:
    selected = []
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if set(row) != set(POWER_SOURCE_FIELDS):
                raise RuntimeError("Power source schema drifted")
            if row["cell"] == "f" and row["pdu"] == "pdu17":
                selected.append(row)
    if len(selected) != HOURS * 12:
        raise RuntimeError("PDU17 power source row count drifted")
    return _power_hours(selected)


def _capacity_hours(rows: Iterable[dict[str, Any]], *, hours: int = HOURS) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for row in rows:
        if set(row) != set(CAPACITY_SOURCE_FIELDS):
            raise RuntimeError("Capacity source schema drifted")
        hour = int(row["hour_index"])
        if hour in result or not 0 <= hour < hours:
            raise RuntimeError("Capacity hour is duplicated or out of range")
        if int(row["raw_interval_start_us"]) != WINDOW_START_US + hour * HOUR_US:
            raise RuntimeError("Capacity raw interval start drifted")
        if int(row["raw_interval_end_us"]) != WINDOW_START_US + (hour + 1) * HOUR_US:
            raise RuntimeError("Capacity raw interval end drifted")
        values = {field: _decimal(row[field], field) for field in CAPACITY_FIELDS}
        if any(value < 0 for value in values.values()):
            raise RuntimeError("Negative capacity diagnostic")
        if values["mapped_machine_seconds"] != Decimal(1295 * 3600):
            raise RuntimeError("Mapped-machine capacity denominator drifted")
        if _sum(
            values[field]
            for field in (
                "known_active_machine_seconds",
                "unknown_active_machine_seconds",
                "inactive_machine_seconds",
            )
        ) != values["mapped_machine_seconds"]:
            raise RuntimeError("Capacity machine-seconds do not balance")
        result[hour] = {
            "unit": "normalized_available_resource_time_not_physical_cores_or_MW",
            **{field: str(row[field]) for field in CAPACITY_FIELDS},
        }
    if set(result) != set(range(hours)):
        raise RuntimeError("Capacity source is missing an hour")
    return result


def _read_capacity(path: Path) -> dict[int, dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        return _capacity_hours(json.loads(line) for line in stream)


def _cpu_hour(rows: list[dict[str, str]]) -> dict[str, Any]:
    lower = _sum(_decimal(row["observed_cpu_ncu_lower"], "cpu lower") for row in rows)
    upper = _sum(_decimal(row["observed_cpu_ncu_upper"], "cpu upper") for row in rows)
    missing = _sum(_decimal(row["missing_cpu_overlap_seconds"], "missing overlap") for row in rows)
    conflict = _sum(_decimal(row["cpu_conflict_overlap_seconds"], "conflict overlap") for row in rows)
    return {
        "unit": "normalized_compute_units_for_selected_root_usage_population",
        "source_strata_count": 14,
        "hourly_endpoint_sum_lower_ncu": _fixed(lower, 12),
        "hourly_endpoint_sum_upper_ncu": _fixed(upper, 12),
        "missing_cpu_overlap_seconds": _fixed(missing, 6),
        "cpu_conflict_overlap_seconds": _fixed(conflict, 6),
        "strata": rows,
    }


def _build_rows(
    cpu: dict[int, list[dict[str, str]]],
    power: dict[int, dict[str, Any]],
    capacity: dict[int, dict[str, Any]],
) -> list[dict[str, Any]]:
    if set(cpu) != set(power) or set(cpu) != set(capacity) or set(cpu) != set(range(HOURS)):
        raise RuntimeError("Hourly source keys do not align")
    return [
        {
            "hour_index": hour,
            "raw_interval_start_us": WINDOW_START_US + hour * HOUR_US,
            "raw_interval_end_us": WINDOW_START_US + (hour + 1) * HOUR_US,
            "cpu": _cpu_hour(cpu[hour]),
            "power": power[hour],
            "capacity": capacity[hour],
        }
        for hour in range(HOURS)
    ]


def _block_audit(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    blocks = []
    for block_index in range(31):
        block_rows = rows[block_index * 24 : (block_index + 1) * 24]
        flags = {key: sum(row["power"]["bad_flag_pair_counts"][key] for row in block_rows) for key in ("00", "01", "10", "11")}
        blocks.append(
            {
                "block_index": block_index,
                "raw_interval_start_us": block_rows[0]["raw_interval_start_us"],
                "raw_interval_end_us": block_rows[-1]["raw_interval_end_us"],
                "aligned_hours": 24,
                "cpu_strata_rows": 24 * 14,
                "power_samples": 24 * 12,
                "capacity_rows": 24,
                "bad_flag_pair_counts": flags,
                "hours_with_cpu_conflict_overlap": sum(Decimal(row["cpu"]["cpu_conflict_overlap_seconds"]) > 0 for row in block_rows),
                "hours_with_missing_cpu_overlap": sum(Decimal(row["cpu"]["missing_cpu_overlap_seconds"]) > 0 for row in block_rows),
                "hours_with_unknown_active_capacity": sum(Decimal(row["capacity"]["unknown_active_machine_seconds"]) > 0 for row in block_rows),
                "natural_calendar_day_identified": False,
            }
        )
    return blocks


def _json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _write_jsonl_gzip(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, compresslevel=9, mtime=0) as compressed:
            for row in rows:
                compressed.write(_json_bytes(row))


README = """# Google PDU17 744-hour CPU-power-capacity alignment

This DRAFT_NONAUTHORITATIVE package aligns three existing local sources on raw clock
`[600000000,2679000000000)`. Each JSONL row contains 14 CPU strata, 12-sample unfiltered
measured/production PDU power means with original flag counts, and the matching hourly
normalized-capacity evidence. The 31 coverage blocks start at the raw trace origin and are
not identified as natural calendar days.

CPU and capacity use normalized units. No CPU/capacity ratio, MW conversion, headroom,
flexibility, deadline, recovery parameter, p-value, fit, or train/holdout selection is produced.
The population is incomplete and the power quality-flag direction remains unresolved.
"""


def run(config_path: Path = DEFAULT_CONFIG, output_dir: Path | None = None) -> dict[str, Any]:
    config_path = config_path.resolve()
    config = _load_config(config_path)
    paths = _source_paths(config)
    target = (output_dir or (ROOT / config["source"]["output_directory"])).resolve()
    if target.exists():
        raise RuntimeError("Refusing to overwrite an existing alignment output")

    cpu, cpu_source_audit = _read_cpu(paths["cpu"])
    power = _read_power(paths["power"])
    capacity = _read_capacity(paths["capacity"])
    rows = _build_rows(cpu, power, capacity)
    blocks = _block_audit(rows)

    flag_totals = {
        key: sum(row["power"]["bad_flag_pair_counts"][key] for row in rows)
        for key in ("00", "01", "10", "11")
    }
    summary = {
        "status": "DRAFT_NONAUTHORITATIVE_ALIGNMENT",
        "schema": "google_power_workload_multiday_pair_v1",
        "source_bindings": {
            name: {"path": config["source"][f"{name}_path"], "sha256": config["source"][f"{name}_sha256"]}
            for name in ("cpu", "cpu_metadata", "power", "capacity", "prepare_summary")
        },
        "config_sha256": _sha256(config_path),
        "implementation_sha256": _sha256(Path(__file__)),
        "contract": config["contract"],
        "units": {
            "cpu": "normalized_compute_units_for_selected_root_usage_population",
            "power": "normalized_PDU_power_ratio",
            "capacity": "normalized_available_resource_time_not_physical_cores_or_MW",
        },
        "coverage": {
            "hours": len(rows),
            "cpu_strata_rows": len(rows) * 14,
            "power_samples": len(rows) * 12,
            "capacity_rows": len(rows),
            "raw_origin_24h_blocks": blocks,
            "natural_calendar_days_identified": False,
        },
        "quality_audit": {
            "power_bad_flag_pair_counts": flag_totals,
            "hours_with_any_bad_measurement_flag": sum(
                row["power"]["bad_flag_pair_counts"]["10"] + row["power"]["bad_flag_pair_counts"]["11"] > 0
                for row in rows
            ),
            "hours_with_any_bad_production_flag": sum(
                row["power"]["bad_flag_pair_counts"]["01"] + row["power"]["bad_flag_pair_counts"]["11"] > 0
                for row in rows
            ),
            "hours_with_cpu_conflict_overlap": sum(Decimal(row["cpu"]["cpu_conflict_overlap_seconds"]) > 0 for row in rows),
            "hours_with_missing_cpu_overlap": sum(Decimal(row["cpu"]["missing_cpu_overlap_seconds"]) > 0 for row in rows),
            "hours_with_unknown_tier_usage": sum(
                any(stratum["priority_tier"] == "unknown" and int(stratum["usage_group_count"]) > 0 for stratum in row["cpu"]["strata"])
                for row in rows
            ),
            "hours_with_unknown_active_capacity": sum(Decimal(row["capacity"]["unknown_active_machine_seconds"]) > 0 for row in rows),
            "unknown_active_capacity_machine_seconds": _fixed(
                _sum(Decimal(row["capacity"]["unknown_active_machine_seconds"]) for row in rows), 6
            ),
            "power_quality_filter_applied": False,
            "power_quality_flag_semantics_resolved": False,
            "cpu_source_audit": cpu_source_audit,
        },
        "interpretation": config["interpretation"],
    }

    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.building-"))
    try:
        aligned_path = staging / "aligned_hourly.jsonl.gz"
        readme_path = staging / "README.md"
        _write_jsonl_gzip(aligned_path, rows)
        readme_path.write_text(README, encoding="utf-8", newline="\n")
        summary["output_bindings"] = {
            "aligned_hourly_sha256": _sha256(aligned_path),
            "readme_sha256": _sha256(readme_path),
        }
        (staging / "summary.json").write_bytes(_json_bytes(summary))
        os.replace(staging, target)
        return summary
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.config, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
