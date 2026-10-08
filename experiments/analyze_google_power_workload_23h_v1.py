"""Non-authoritative descriptive association for the aligned Google 23-hour pair."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from decimal import Context, Decimal, ROUND_HALF_EVEN, localcontext
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[1]
PAIR_PATH = ROOT / "results/tables/google_power_workload_alignment_successor_v1_non_authoritative/aligned_hourly_pair.csv"
ALIGNMENT_SUMMARY_PATH = ROOT / "results/tables/google_power_workload_alignment_successor_v1_non_authoritative/summary.json"
ALIGNMENT_CONFIG_PATH = ROOT / "configs/google_power_workload_alignment_successor_v1.DRAFT.yaml"
ALIGNMENT_IMPLEMENTATION_PATH = ROOT / "experiments/process_google_power_workload_alignment_successor_v1.py"
DEFAULT_OUTPUT = ROOT / "results/tables/google_power_workload_23h_descriptive_v1_non_authoritative/summary.json"

EXPECTED_SHA256 = {
    "aligned_hourly_pair": "54d664f2fa261413c1dfb5c05479d6aa6977e74ea8a6f36c3a5f41dba79f5930",
    "alignment_summary": "e7d6edad6f2e5abf4ad07b096b2c6c584156532fbfea452648ce78d07b551d53",
    "alignment_config": "dc8285d3799d62c9ecebee47ecdf480f461d9f0f0ea033310fab88fbea945ae1",
    "alignment_implementation": "7011b96f3141a3937b49a2b6493b00ee01a05e770ed2fdf922d7bee1e76054d5",
}
ANALYSIS_CONTEXT = Context(prec=50, rounding=ROUND_HALF_EVEN)
COEFFICIENT_DECIMAL_PLACES = 18
MEAN_DECIMAL_PLACES = 18
HOUR_US = 3_600_000_000


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decimal_or_none(value: str | None) -> Decimal | None:
    if value is None or not value.strip():
        return None
    parsed = Decimal(value)
    return parsed if parsed.is_finite() else None


def _fixed(value: Decimal, places: int) -> str:
    with localcontext(ANALYSIS_CONTEXT):
        quantum = Decimal(1).scaleb(-places)
        return format(value.quantize(quantum), "f")


def _average_ranks(values: Sequence[Decimal]) -> list[Decimal]:
    order = sorted(range(len(values)), key=lambda index: values[index])
    ranks = [Decimal(0)] * len(values)
    with localcontext(ANALYSIS_CONTEXT):
        start = 0
        while start < len(order):
            end = start + 1
            while end < len(order) and values[order[end]] == values[order[start]]:
                end += 1
            average_rank = (Decimal(start + 1) + Decimal(end)) / Decimal(2)
            for position in range(start, end):
                ranks[order[position]] = average_rank
            start = end
    return ranks


def _pearson(
    left: Sequence[Decimal | None], right: Sequence[Decimal | None]
) -> dict[str, str | None]:
    if len(left) != len(right):
        raise ValueError("Correlation series lengths differ")
    if len(left) < 2:
        return {"status": "unavailable_insufficient_observations", "coefficient": None}
    if any(value is None for value in (*left, *right)):
        return {"status": "unavailable_null_observation", "coefficient": None}
    x = [value for value in left if value is not None]
    y = [value for value in right if value is not None]
    with localcontext(ANALYSIS_CONTEXT):
        n = Decimal(len(x))
        mean_x = sum(x, Decimal(0)) / n
        mean_y = sum(y, Decimal(0)) / n
        dx = [value - mean_x for value in x]
        dy = [value - mean_y for value in y]
        sum_xx = sum((value * value for value in dx), Decimal(0))
        sum_yy = sum((value * value for value in dy), Decimal(0))
        if sum_xx == 0 or sum_yy == 0:
            return {"status": "unavailable_constant_series", "coefficient": None}
        numerator = sum((a * b for a, b in zip(dx, dy)), Decimal(0))
        coefficient = numerator / (sum_xx * sum_yy).sqrt()
    return {"status": "available", "coefficient": _fixed(coefficient, COEFFICIENT_DECIMAL_PLACES)}


def _spearman(
    left: Sequence[Decimal | None], right: Sequence[Decimal | None]
) -> dict[str, str | None]:
    if len(left) != len(right):
        raise ValueError("Correlation series lengths differ")
    if len(left) < 2:
        return {"status": "unavailable_insufficient_observations", "coefficient": None}
    if any(value is None for value in (*left, *right)):
        return {"status": "unavailable_null_observation", "coefficient": None}
    x = [value for value in left if value is not None]
    y = [value for value in right if value is not None]
    return _pearson(_average_ranks(x), _average_ranks(y))


def _describe(values: Sequence[Decimal | None]) -> dict[str, Any]:
    if not values:
        return {"status": "unavailable_no_observations", "minimum": None, "maximum": None, "mean": None}
    if any(value is None for value in values):
        return {"status": "unavailable_null_observation", "minimum": None, "maximum": None, "mean": None}
    present = [value for value in values if value is not None]
    with localcontext(ANALYSIS_CONTEXT):
        mean = sum(present, Decimal(0)) / Decimal(len(present))
    return {
        "status": "available",
        "minimum": format(min(present), "f"),
        "maximum": format(max(present), "f"),
        "mean": _fixed(mean, MEAN_DECIMAL_PLACES),
    }


def _analyze_rows(rows: Iterable[dict[str, str]]) -> dict[str, Any]:
    ordered = sorted(rows, key=lambda row: int(row["source_hour_index"]))
    hours = [int(row["source_hour_index"]) for row in ordered]
    if hours != list(range(1, 24)):
        raise RuntimeError("Expected exactly the aligned source hours 1 through 23")

    lower: list[Decimal | None] = []
    upper: list[Decimal | None] = []
    power: list[Decimal | None] = []
    missing: list[Decimal] = []
    conflicts: list[Decimal] = []
    flag_names = (
        "bad_measurement_false_count",
        "bad_measurement_true_count",
        "bad_production_false_count",
        "bad_production_true_count",
    )
    flag_counts = {name: 0 for name in flag_names}
    for hour, row in zip(hours, ordered):
        if int(row["common_raw_start_us"]) != hour * HOUR_US or int(row["common_raw_end_us"]) != (hour + 1) * HOUR_US:
            raise RuntimeError("Aligned raw-hour interval drifted")
        sample_count = int(row["power_sample_count"])
        if sample_count != 12:
            raise RuntimeError("Expected twelve five-minute power samples per hour")
        if int(row["cpu_source_row_count"]) != 14:
            raise RuntimeError("Expected fourteen CPU source strata per hour")
        for name in flag_names:
            flag_counts[name] += int(row[name])
        if int(row["bad_measurement_false_count"]) + int(row["bad_measurement_true_count"]) != sample_count:
            raise RuntimeError("Measurement flag counts do not cover the hourly samples")
        if int(row["bad_production_false_count"]) + int(row["bad_production_true_count"]) != sample_count:
            raise RuntimeError("Production flag counts do not cover the hourly samples")
        lower_value = _decimal_or_none(row.get("observed_cpu_ncu_lower"))
        upper_value = _decimal_or_none(row.get("observed_cpu_ncu_upper"))
        if lower_value is not None and upper_value is not None and lower_value > upper_value:
            raise RuntimeError("CPU lower endpoint exceeds upper endpoint")
        lower.append(lower_value)
        upper.append(upper_value)
        power.append(_decimal_or_none(row.get("measured_power_util_mean_12dp")))
        missing_value = _decimal_or_none(row.get("missing_cpu_overlap_seconds"))
        conflict_value = _decimal_or_none(row.get("cpu_conflict_overlap_seconds"))
        if missing_value is None or conflict_value is None or missing_value < 0 or conflict_value < 0:
            raise RuntimeError("CPU missing/conflict diagnostics are invalid")
        missing.append(missing_value)
        conflicts.append(conflict_value)

    with localcontext(ANALYSIS_CONTEXT):
        missing_total = sum(missing, Decimal(0))
        conflict_total = sum(conflicts, Decimal(0))
    return {
        "observation_count": len(ordered),
        "series_descriptives": {
            "observed_cpu_ncu_lower": _describe(lower),
            "observed_cpu_ncu_upper": _describe(upper),
            "measured_power_util_mean": _describe(power),
        },
        "correlations": {
            "cpu_lower_vs_measured_power": {"pearson": _pearson(lower, power), "spearman": _spearman(lower, power)},
            "cpu_upper_vs_measured_power": {"pearson": _pearson(upper, power), "spearman": _spearman(upper, power)},
        },
        "quality_flag_counts_unfiltered": flag_counts,
        "cpu_aggregation_contract": {
            "source_rows_per_hour": 14,
            "collection_types_per_hour": 2,
            "priority_tiers_per_collection_type": 7,
            "endpoint_semantics": "hourly_sum_across_collection_types_and_priority_tiers",
        },
        "cpu_source_diagnostics": {
            "missing_cpu_overlap_seconds_total": format(missing_total, "f"),
            "hours_with_missing_cpu_overlap": sum(value > 0 for value in missing),
            "cpu_conflict_overlap_seconds_total": format(conflict_total, "f"),
            "hours_with_cpu_conflict_overlap": sum(value > 0 for value in conflicts),
        },
    }


def _summary_bytes(summary: dict[str, Any]) -> bytes:
    return (json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def run(output_path: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    paths = {
        "aligned_hourly_pair": PAIR_PATH,
        "alignment_summary": ALIGNMENT_SUMMARY_PATH,
        "alignment_config": ALIGNMENT_CONFIG_PATH,
        "alignment_implementation": ALIGNMENT_IMPLEMENTATION_PATH,
    }
    live_hashes = {name: _sha256(path) for name, path in paths.items()}
    if live_hashes != EXPECTED_SHA256:
        raise RuntimeError("Bound alignment source hash drifted")
    alignment_summary = json.loads(ALIGNMENT_SUMMARY_PATH.read_text(encoding="utf-8"))
    if (
        alignment_summary.get("aligned_hourly_pair_sha256") != EXPECTED_SHA256["aligned_hourly_pair"]
        or alignment_summary.get("config_sha256") != EXPECTED_SHA256["alignment_config"]
        or alignment_summary.get("implementation_sha256") != EXPECTED_SHA256["alignment_implementation"]
        or alignment_summary.get("complete_hours") != 23
        or alignment_summary.get("common_raw_interval_start_us") != 3_600_000_000
        or alignment_summary.get("common_raw_interval_end_us") != 86_400_000_000
        or alignment_summary.get("trace_relative_interval_start_us") != 3_000_000_000
        or alignment_summary.get("trace_relative_interval_end_us") != 85_800_000_000
        or alignment_summary.get("quality_flag_counts") is None
    ):
        raise RuntimeError("Alignment summary binding or scope drifted")
    with PAIR_PATH.open(encoding="utf-8", newline="") as stream:
        analysis = _analyze_rows(csv.DictReader(stream))
    if analysis["quality_flag_counts_unfiltered"] != alignment_summary["quality_flag_counts"]:
        raise RuntimeError("Unfiltered quality flag counts drifted from alignment summary")

    summary: dict[str, Any] = {
        "status": "DRAFT_NONAUTHORITATIVE",
        "schema": "google_power_workload_23h_descriptive_v1",
        "scope": "all_23_aligned_hours_unfiltered",
        **analysis,
        "source_interval": {
            "common_raw_start_us": alignment_summary["common_raw_interval_start_us"],
            "common_raw_end_us": alignment_summary["common_raw_interval_end_us"],
            "trace_relative_start_us": alignment_summary["trace_relative_interval_start_us"],
            "trace_relative_end_us": alignment_summary["trace_relative_interval_end_us"],
            "trace_relative_start_minutes": alignment_summary["trace_relative_start_minutes"],
            "trace_relative_end_minutes": alignment_summary["trace_relative_end_minutes"],
        },
        "source_sha256": live_hashes,
        "analysis_implementation_sha256": _sha256(Path(__file__)),
        "numeric_contract": {
            "decimal_context_precision": ANALYSIS_CONTEXT.prec,
            "decimal_rounding": "ROUND_HALF_EVEN",
            "coefficient_decimal_places": COEFFICIENT_DECIMAL_PLACES,
            "mean_decimal_places": MEAN_DECIMAL_PLACES,
            "spearman_tie_method": "average_rank",
        },
        "interpretation": {
            "correlations_are_separate_cpu_endpoint_analyses": True,
            "correlations_are_identification_bounds": False,
            "cpu_unit": "normalized_compute_unit_ncu",
            "cpu_bounds_scope": "extracted_population_only",
            "power_unit": "normalized_pdu_utilization_ratio",
            "cpu_overlap_seconds_are_aggregated_across_fragments_and_instances": True,
            "population_is_complete_pdu_workload": False,
            "population_parameter_estimated": False,
            "quality_flags_preserved_unfiltered": True,
            "power_quality_flag_semantics_resolved": False,
            "quality_eligibility_inferred": False,
            "complete_24h_pair": False,
            "p_values_computed": False,
            "confidence_intervals_computed": False,
            "lag_search_performed": False,
            "fit_or_calibration_performed": False,
            "flexibility_estimated": False,
            "flexibility_observed": False,
            "absolute_power_mw_available": False,
            "deadline_observed": False,
            "recovery_parameters_observed": False,
            "continuous_model_input_ready": False,
            "model_input_ready": False,
            "formal_result": False,
            "paper_claim": False,
            "security_certified": False,
        },
    }
    payload = _summary_bytes(summary)
    if output_path.exists() or output_path.parent.exists():
        raise FileExistsError(f"Refusing to overwrite diagnostic output: {output_path.parent}")
    output_path.parent.mkdir(parents=True)
    output_path.write_bytes(payload)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(run(args.output), sort_keys=True))


if __name__ == "__main__":
    main()
