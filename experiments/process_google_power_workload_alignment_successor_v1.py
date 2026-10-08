"""Build the non-authoritative Google 23-complete-hour alignment diagnostic."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
from collections import Counter
from collections.abc import Iterable
from decimal import ROUND_HALF_EVEN, Context, Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

import yaml

HOUR_US = 3_600_000_000
STABLE_DECIMAL_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
CPU_DECIMAL_FIELDS = (
    "observed_cpu_ncu_lower",
    "observed_cpu_ncu_upper",
    "observed_cpu_time_ncu_seconds_lower",
    "observed_cpu_time_ncu_seconds_upper",
    "observed_cpu_overlap_seconds",
    "missing_cpu_overlap_seconds",
    "cpu_conflict_overlap_seconds",
)
PAIR_FIELDS = (
    "source_hour_index",
    "common_raw_start_us",
    "common_raw_end_us",
    "trace_relative_start_us",
    "trace_relative_end_us",
    "power_source_first_time_us",
    "power_source_last_time_us",
    "power_sample_count",
    "measured_power_util_sum",
    "measured_power_util_mean_12dp",
    "bad_measurement_false_count",
    "bad_measurement_true_count",
    "bad_production_false_count",
    "bad_production_true_count",
    "cpu_source_row_count",
    *CPU_DECIMAL_FIELDS,
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decimal(raw: str, *, field: str) -> Decimal:
    try:
        value = Decimal(raw)
    except InvalidOperation as exc:
        raise RuntimeError(f"Invalid decimal in {field}: {raw!r}") from exc
    if not value.is_finite():
        raise RuntimeError(f"Non-finite decimal in {field}: {raw!r}")
    return value


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _flag(raw: str, *, field: str) -> bool:
    if raw == "true":
        return True
    if raw == "false":
        return False
    raise RuntimeError(f"Invalid boolean in {field}: {raw!r}")


def _aggregate_cpu_rows(
    rows: Iterable[dict[str, str]],
    *,
    expected_hours: range,
    collection_types: tuple[int, ...],
    priority_tiers: tuple[str, ...],
) -> dict[int, dict[str, Any]]:
    keyed: dict[tuple[int, int, str], dict[str, str]] = {}
    counts: Counter[str] = Counter()
    for row in rows:
        record_type = row["record_type"]
        counts[record_type] += 1
        if record_type != "hourly_usage":
            continue
        key = (int(row["hour_index"]), int(row["collection_type"]), row["priority_tier"])
        if key in keyed:
            raise RuntimeError(f"Duplicate hourly CPU key: {key}")
        keyed[key] = row

    required = {
        (hour, collection_type, tier)
        for hour in expected_hours
        for collection_type in collection_types
        for tier in priority_tiers
    }
    if set(keyed) != required:
        raise RuntimeError("Hourly CPU source does not contain the exact 24x2x7 grid")

    hourly: dict[int, dict[str, Any]] = {}
    for hour in expected_hours:
        source_rows = [keyed[(hour, collection_type, tier)] for collection_type in collection_types for tier in priority_tiers]
        aggregate: dict[str, Any] = {"cpu_source_row_count": len(source_rows)}
        for row in source_rows:
            ncu_lower = _decimal(row["observed_cpu_ncu_lower"], field="observed_cpu_ncu_lower")
            ncu_upper = _decimal(row["observed_cpu_ncu_upper"], field="observed_cpu_ncu_upper")
            time_lower = _decimal(
                row["observed_cpu_time_ncu_seconds_lower"],
                field="observed_cpu_time_ncu_seconds_lower",
            )
            time_upper = _decimal(
                row["observed_cpu_time_ncu_seconds_upper"],
                field="observed_cpu_time_ncu_seconds_upper",
            )
            if ncu_lower > ncu_upper or time_lower > time_upper:
                raise RuntimeError("A source hourly CPU row has inverted bounds")
        for field in CPU_DECIMAL_FIELDS:
            values = [_decimal(row[field], field=field) for row in source_rows]
            if any(value < 0 for value in values):
                raise RuntimeError(f"Negative hourly CPU value in {field}")
            with localcontext(STABLE_DECIMAL_CONTEXT):
                aggregate[field] = sum(values, Decimal(0))
        if aggregate["observed_cpu_ncu_lower"] > aggregate["observed_cpu_ncu_upper"]:
            raise RuntimeError("Hourly CPU NCU bounds are inverted")
        if aggregate["observed_cpu_time_ncu_seconds_lower"] > aggregate["observed_cpu_time_ncu_seconds_upper"]:
            raise RuntimeError("Hourly CPU-time bounds are inverted")
        hourly[hour] = aggregate
    hourly[-1] = {"record_type_counts": dict(counts)}
    return hourly


def _index_power_rows(
    rows: Iterable[dict[str, str]], *, cell: str, pdu: str
) -> dict[int, dict[str, Any]]:
    indexed: dict[int, dict[str, Any]] = {}
    for row in rows:
        if row["cell"] != cell or row["pdu"] != pdu:
            raise RuntimeError("Power source contains a different cell or PDU")
        time_us = int(row["time"])
        if time_us in indexed:
            raise RuntimeError(f"Duplicate power timestamp: {time_us}")
        measured = _decimal(row["measured_power_util"], field="measured_power_util")
        if not Decimal(0) <= measured <= Decimal(1):
            raise RuntimeError("measured_power_util is outside the documented [0,1] range")
        indexed[time_us] = {
            "measured": measured,
            "bad_measurement": _flag(row["bad_measurement_data"], field="bad_measurement_data"),
            "bad_production": _flag(row["bad_production_power_data"], field="bad_production_power_data"),
        }
    return indexed


def _build_aligned_rows(
    cpu_hours: dict[int, dict[str, Any]],
    power_by_time: dict[int, dict[str, Any]],
    *,
    start_us: int,
    end_us: int,
    trace_start_us: int,
    step_us: int,
    decimal_places: int,
) -> list[dict[str, Any]]:
    if start_us % HOUR_US or end_us % HOUR_US or end_us <= start_us:
        raise ValueError("Common interval must contain complete raw-clock hours")
    if HOUR_US % step_us:
        raise ValueError("Power step must divide one hour exactly")

    rows: list[dict[str, Any]] = []
    quantizer = Decimal(f"1e-{decimal_places}")
    for raw_start_us in range(start_us, end_us, HOUR_US):
        hour = raw_start_us // HOUR_US
        expected_times = list(range(raw_start_us, raw_start_us + HOUR_US, step_us))
        missing = [time_us for time_us in expected_times if time_us not in power_by_time]
        if missing:
            raise RuntimeError(f"Incomplete power coverage for raw hour {hour}: {missing}")
        power = [power_by_time[time_us] for time_us in expected_times]
        with localcontext(STABLE_DECIMAL_CONTEXT):
            measured_sum = sum((sample["measured"] for sample in power), Decimal(0))
            measured_mean = (measured_sum / Decimal(len(power))).quantize(quantizer)
        cpu = cpu_hours[hour]
        row: dict[str, Any] = {
            "source_hour_index": hour,
            "common_raw_start_us": raw_start_us,
            "common_raw_end_us": raw_start_us + HOUR_US,
            "trace_relative_start_us": raw_start_us - trace_start_us,
            "trace_relative_end_us": raw_start_us + HOUR_US - trace_start_us,
            "power_source_first_time_us": expected_times[0],
            "power_source_last_time_us": expected_times[-1],
            "power_sample_count": len(power),
            "measured_power_util_sum": _decimal_text(measured_sum),
            f"measured_power_util_mean_{decimal_places}dp": f"{measured_mean:.{decimal_places}f}",
            "bad_measurement_false_count": sum(not sample["bad_measurement"] for sample in power),
            "bad_measurement_true_count": sum(sample["bad_measurement"] for sample in power),
            "bad_production_false_count": sum(not sample["bad_production"] for sample in power),
            "bad_production_true_count": sum(sample["bad_production"] for sample in power),
            "cpu_source_row_count": cpu["cpu_source_row_count"],
        }
        for field in CPU_DECIMAL_FIELDS:
            row[field] = _decimal_text(cpu[field])
        rows.append(row)
    return rows


def _pair_csv_bytes(pair_rows: list[dict[str, Any]]) -> bytes:
    pair_buffer = io.StringIO(newline="")
    writer = csv.DictWriter(pair_buffer, fieldnames=PAIR_FIELDS, lineterminator="\n")
    writer.writeheader()
    writer.writerows(pair_rows)
    return pair_buffer.getvalue().encode("utf-8")


def _publish_diagnostic(output_root: Path, files: dict[str, bytes]) -> None:
    if output_root.exists():
        raise RuntimeError(f"Refusing to overwrite diagnostic directory: {output_root}")
    output_root.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{output_root.name}.processing-", dir=output_root.parent)
    )
    try:
        for name, payload in files.items():
            (staging / name).write_bytes(payload)
        if output_root.exists():
            raise RuntimeError(f"Diagnostic directory appeared during publication: {output_root}")
        staging.replace(output_root)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def run(config_path: Path, *, output_directory: Path | None = None) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["status"] != "DRAFT_NONAUTHORITATIVE":
        raise RuntimeError("Successor config is not a non-authoritative draft")
    source = config["source"]
    contract = config["source_contract"]
    alignment = config["alignment"]
    serialization = config["serialization"]
    if serialization != {
        "measured_power_mean_decimal_places": 12,
        "measured_power_mean_rounding": "ROUND_HALF_EVEN",
        "line_ending": "LF",
    }:
        raise RuntimeError("Unsupported deterministic serialization contract")
    interpretation = config["interpretation"]
    if interpretation != {
        "pairing_status": "provisional_temporal_alignment_only",
        "cpu_unit": "normalized_compute_unit_ncu",
        "cpu_bounds_scope": "extracted_population_only",
        "power_unit": "normalized_pdu_utilization_ratio",
        "population_is_complete_pdu_workload": False,
        "cpu_subhour_disaggregation_performed": False,
        "priority_strata_reconstructed": False,
        "priority_evidence_remains_in_bound_source": True,
        "machine_capacity_reconstructed": False,
        "machine_capacity_completeness_resolved": False,
        "capacity_used_to_normalize_cpu": False,
        "power_quality_flags_preserved_unfiltered": True,
        "power_quality_flag_semantics_resolved": False,
        "absolute_power_mw_available": False,
        "flexibility_observed": False,
        "deadline_observed": False,
        "recovery_parameters_observed": False,
        "complete_24h_pair": False,
        "continuous_input_ready": False,
        "model_input_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }:
        raise RuntimeError("Interpretation gates drifted")

    paths = {
        "workload_records": Path(source["workload_records_path"]),
        "workload_metadata": Path(source["workload_metadata_path"]),
        "workload_manifest": Path(source["workload_manifest_path"]),
        "power": Path(source["power_path"]),
        "power_manifest": Path(source["power_manifest_path"]),
    }
    for name, path in paths.items():
        expected = source[f"{name}_sha256"]
        found = _sha256(path)
        if found != expected:
            raise RuntimeError(f"Input hash drifted for {name}: expected {expected}, found {found}")

    metadata = json.loads(paths["workload_metadata"].read_text(encoding="utf-8"))
    if metadata["schema"] != contract["workload_schema"]:
        raise RuntimeError("Workload metadata schema drifted")
    if metadata["result_sha256"] != source["workload_records_sha256"]:
        raise RuntimeError("Workload metadata no longer binds the records file")

    with gzip.open(paths["workload_records"], "rt", encoding="utf-8", newline="") as source_file:
        workload_rows = list(csv.DictReader(source_file))
    if len(workload_rows) != int(contract["workload_rows"]):
        raise RuntimeError("Workload row count drifted")
    cpu_hours = _aggregate_cpu_rows(
        workload_rows,
        expected_hours=range(int(contract["source_hour_start"]), int(contract["source_hour_end_exclusive"])),
        collection_types=tuple(int(value) for value in contract["collection_types"]),
        priority_tiers=tuple(contract["priority_tiers"]),
    )
    expected_counts = {
        "hourly_usage": int(contract["hourly_usage_rows"]),
        "machine_event": int(contract["machine_event_rows"]),
        "audit": int(contract["audit_rows"]),
    }
    if cpu_hours.pop(-1)["record_type_counts"] != expected_counts:
        raise RuntimeError("Workload record-type counts drifted")

    with gzip.open(paths["power"], "rt", encoding="utf-8", newline="") as source_file:
        power_rows = list(csv.DictReader(source_file))
    if len(power_rows) != int(contract["power_domain_rows"]):
        raise RuntimeError("Power domain row count drifted")
    power_by_time = _index_power_rows(power_rows, cell=source["cell"], pdu=source["pdu"])

    step_us = int(alignment["power_step_us"])
    trace_start_us = int(alignment["trace_start_raw_us"])
    power_start_us = int(contract["legacy_power_window_start_us"])
    power_end_us = int(contract["legacy_power_window_end_us"])
    if (
        step_us != 300_000_000
        or trace_start_us != 600_000_000
        or power_start_us != 600_000_000
        or power_end_us != 87_000_000_000
    ):
        raise RuntimeError("Google source clock contract drifted")
    cpu_start_us = int(contract["source_hour_start"]) * HOUR_US
    cpu_end_us = int(contract["source_hour_end_exclusive"]) * HOUR_US
    derived_start_us = ((max(cpu_start_us, power_start_us) + HOUR_US - 1) // HOUR_US) * HOUR_US
    derived_end_us = (min(cpu_end_us, power_end_us) // HOUR_US) * HOUR_US
    derived_hours = (derived_end_us - derived_start_us) // HOUR_US
    derived_samples = derived_hours * (HOUR_US // step_us)
    declared_alignment = (
        int(alignment["common_raw_start_us"]),
        int(alignment["common_raw_end_us"]),
        int(alignment["expected_complete_hours"]),
        int(alignment["expected_power_samples"]),
    )
    if declared_alignment != (derived_start_us, derived_end_us, derived_hours, derived_samples):
        raise RuntimeError("Declared alignment is not the maximal complete raw-hour intersection")
    legacy_times = list(range(power_start_us, power_end_us, step_us))
    if any(time_us not in power_by_time for time_us in legacy_times):
        raise RuntimeError("Legacy power day window is incomplete")
    pair_rows = _build_aligned_rows(
        cpu_hours,
        power_by_time,
        start_us=int(alignment["common_raw_start_us"]),
        end_us=int(alignment["common_raw_end_us"]),
        trace_start_us=trace_start_us,
        step_us=step_us,
        decimal_places=int(serialization["measured_power_mean_decimal_places"]),
    )
    if len(pair_rows) != int(alignment["expected_complete_hours"]):
        raise RuntimeError("Complete-hour count drifted")
    if sum(int(row["power_sample_count"]) for row in pair_rows) != int(alignment["expected_power_samples"]):
        raise RuntimeError("Aligned power sample count drifted")

    pair_bytes = _pair_csv_bytes(pair_rows)
    pair_sha256 = hashlib.sha256(pair_bytes).hexdigest()

    start_us = int(alignment["common_raw_start_us"])
    end_us = int(alignment["common_raw_end_us"])
    summary: dict[str, Any] = {
        "status": config["status"],
        "schema": config["schema"],
        "pairing_status": config["interpretation"]["pairing_status"],
        "cell": source["cell"],
        "pdu": source["pdu"],
        "common_raw_interval_start_us": start_us,
        "common_raw_interval_end_us": end_us,
        "trace_relative_interval_start_us": start_us - trace_start_us,
        "trace_relative_interval_end_us": end_us - trace_start_us,
        "trace_relative_start_minutes": (start_us - trace_start_us) // 60_000_000,
        "trace_relative_end_minutes": (end_us - trace_start_us) // 60_000_000,
        "complete_hours": len(pair_rows),
        "common_interval_duration_us": end_us - start_us,
        "aligned_power_samples": sum(int(row["power_sample_count"]) for row in pair_rows),
        "excluded_cpu_source_hours": [0],
        "excluded_power_samples_before_common_interval": sum(time_us < start_us for time_us in legacy_times),
        "excluded_power_samples_after_common_interval": sum(time_us >= end_us for time_us in legacy_times),
        "quality_flag_counts": {
            key: sum(int(row[key]) for row in pair_rows)
            for key in (
                "bad_measurement_false_count",
                "bad_measurement_true_count",
                "bad_production_false_count",
                "bad_production_true_count",
            )
        },
        **interpretation,
        "input_sha256": {name: _sha256(path) for name, path in paths.items()},
        "config_sha256": _sha256(config_path),
        "implementation_sha256": _sha256(Path(__file__)),
        "aligned_hourly_pair_sha256": pair_sha256,
    }
    summary_bytes = (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")

    output_root = output_directory or Path(config["output"]["directory"])
    _publish_diagnostic(
        output_root,
        {
            config["output"]["pair_file"]: pair_bytes,
            config["output"]["summary_file"]: summary_bytes,
        },
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=Path("configs/google_power_workload_alignment_successor_v1.DRAFT.yaml"))
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    print(json.dumps(run(args.config, output_directory=args.output_dir), sort_keys=True))


if __name__ == "__main__":
    main()
