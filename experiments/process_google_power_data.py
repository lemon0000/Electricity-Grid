"""Build an hourly normalized-power shape without inventing PDU capacities."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import tempfile
from pathlib import Path
from statistics import median

import yaml

from experiments.validate_google_power_data import (
    TRACE_NAME,
    run as validate_source,
)


OUTPUT_FIELDS = (
    "relative_hour",
    "source_start_time_microseconds",
    "source_end_time_microseconds",
    "eligible_domain_count",
    "complete_valid_domain_count",
    "measured_power_util_unweighted_mean",
    "measured_power_util_unweighted_median",
    "peak_normalized_unweighted_mean",
)
DOMAIN_FIELDS = (
    "file",
    "cell",
    "pdu",
    "complete_valid_hours",
    "total_hours",
    "complete_valid_hour_coverage",
    "full_window",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping_domains(path: Path) -> set[tuple[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        return {(row["cell"], row["pdu"]) for row in csv.DictReader(source)}


def _domain_hour_means(
    path: Path,
    *,
    metric: str,
    quality_flag: str,
    samples_per_hour: int,
) -> tuple[list[int], list[float | None]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        rows = sorted(csv.DictReader(source), key=lambda row: int(row["time"]))
    if len(rows) % samples_per_hour != 0:
        raise ValueError(f"{path.name} cannot be divided into complete hours")

    times = [int(row["time"]) for row in rows]
    hourly = []
    for start in range(0, len(rows), samples_per_hour):
        block = rows[start : start + samples_per_hour]
        valid = [
            float(row[metric])
            for row in block
            if row[quality_flag].lower() == "false"
        ]
        hourly.append(
            sum(valid) / len(valid) if len(valid) == samples_per_hour else None
        )
    return times, hourly


def _format_float(value: float) -> str:
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _write_domain_catalog(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=DOMAIN_FIELDS)
        writer.writeheader()
        writer.writerows(rows)


def _promote(staging: Path, output_root: Path, names: tuple[str, ...]) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for name in names:
        (staging / name).replace(output_root / name)


def run(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source_summary = validate_source(config_path, write_output=False)
    if not all(source_summary["checks"].values()):
        raise RuntimeError("Google source validation must pass before processing")

    root = Path(config["source"]["path"])
    processing = config["processing"]
    if processing["domain_scope"] != "workload_linkable_pdu_domains":
        raise ValueError("Unsupported Google power-domain scope")
    if processing["domain_hour_rule"] != "require_all_12_samples_valid":
        raise ValueError("Unsupported Google domain-hour rule")
    if processing["cross_domain_rule"] != (
        "unweighted_mean_and_median_no_capacity_weighting"
    ):
        raise ValueError("Unknown Google cross-domain aggregation rule")
    if processing["missing_policy"] != (
        "exclude_incomplete_domain_hour_without_imputation"
    ):
        raise ValueError("Unknown Google missing-value rule")
    if processing["normalization_rule"] != (
        "ex_post_full_window_peak_for_fixed_replay_only"
    ):
        raise ValueError("Unknown Google shape-normalization rule")

    samples_per_hour = int(processing["source_samples_per_hour"])
    if samples_per_hour != 12:
        raise ValueError("Google five-minute data require 12 samples per hour")
    mapping_domains = _mapping_domains(root / "machine_to_pdu_mapping.csv.gz")
    trace_paths = []
    for path in sorted(root.glob("cell*.csv.gz")):
        match = TRACE_NAME.fullmatch(path.name)
        if match is not None and match.group(2).startswith("pdu"):
            if (match.group(1), match.group(2)) in mapping_domains:
                trace_paths.append(path)
    if len(trace_paths) != int(processing["expected_eligible_domains"]):
        raise RuntimeError("Google eligible-domain count drifted")

    common_times: list[int] | None = None
    domain_hourly: list[list[float | None]] = []
    domain_catalog = []
    for path in trace_paths:
        times, hourly = _domain_hour_means(
            path,
            metric=str(processing["metric"]),
            quality_flag=str(processing["quality_flag"]),
            samples_per_hour=samples_per_hour,
        )
        if common_times is None:
            common_times = times
        elif times != common_times:
            raise RuntimeError(f"Google source calendar drifted in {path.name}")
        domain_hourly.append(hourly)
        match = TRACE_NAME.fullmatch(path.name)
        complete_hours = sum(value is not None for value in hourly)
        domain_catalog.append(
            {
                "file": path.name,
                "cell": match.group(1),
                "pdu": match.group(2),
                "complete_valid_hours": complete_hours,
                "total_hours": len(hourly),
                "complete_valid_hour_coverage": _format_float(
                    complete_hours / len(hourly)
                ),
                "full_window": str(complete_hours == len(hourly)).lower(),
            }
        )

    times = common_times or []
    hours = len(times) // samples_per_hour
    if hours != int(processing["expected_hours"]):
        raise RuntimeError("Google processed-hour count drifted")
    hourly_values = []
    for hour in range(hours):
        complete_values = [
            values[hour] for values in domain_hourly if values[hour] is not None
        ]
        if not complete_values:
            raise RuntimeError(f"No complete Google domains for relative hour {hour}")
        mean_value = sum(complete_values) / len(complete_values)
        hourly_values.append((complete_values, mean_value))
    peak_mean = max(mean_value for _, mean_value in hourly_values)
    if peak_mean <= 0.0:
        raise RuntimeError("Google normalized-power shape has no positive peak")

    rows = []
    for hour, (complete_values, mean_value) in enumerate(hourly_values):
        start = hour * samples_per_hour
        end = start + samples_per_hour - 1
        rows.append(
            {
                "relative_hour": hour,
                "source_start_time_microseconds": times[start],
                "source_end_time_microseconds": times[end],
                "eligible_domain_count": len(trace_paths),
                "complete_valid_domain_count": len(complete_values),
                "measured_power_util_unweighted_mean": _format_float(mean_value),
                "measured_power_util_unweighted_median": _format_float(
                    float(median(complete_values))
                ),
                "peak_normalized_unweighted_mean": _format_float(
                    mean_value / peak_mean
                ),
            }
        )

    valid_domain_counts = [int(row["complete_valid_domain_count"]) for row in rows]
    complete_domain_hours = sum(
        int(row["complete_valid_hours"]) for row in domain_catalog
    )
    full_window_domains = sum(row["full_window"] == "true" for row in domain_catalog)
    if complete_domain_hours != int(processing["expected_complete_domain_hours"]):
        raise RuntimeError("Google complete domain-hour count drifted")
    if full_window_domains != int(processing["expected_full_window_domains"]):
        raise RuntimeError("Google full-window domain count drifted")
    if min(valid_domain_counts) != int(
        processing["expected_minimum_complete_domains_per_hour"]
    ):
        raise RuntimeError("Google minimum hourly domain coverage drifted")
    output_root = output_directory or Path(processing["output_directory"])
    output_root.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_root.name}.processing-"
    with tempfile.TemporaryDirectory(dir=output_root.parent, prefix=prefix) as temp:
        staging = Path(temp)
        shape_path = staging / "hourly_shape.csv"
        _write_csv(shape_path, rows)
        domain_path = staging / "domain_quality.csv"
        _write_domain_catalog(domain_path, domain_catalog)
        shape_sha256 = _sha256(shape_path)
        domain_quality_sha256 = _sha256(domain_path)
        if shape_sha256 != processing["expected_hourly_shape_sha256"]:
            raise RuntimeError("Google processed shape hash drifted")
        if domain_quality_sha256 != processing["expected_domain_quality_sha256"]:
            raise RuntimeError("Google domain-quality hash drifted")
        summary = {
            "schema": processing["schema"],
            "source_dataset": config["source"]["dataset"],
            "source_documentation_commit": config["source"][
                "documentation_commit"
            ],
            "source_manifest_sha256": _sha256(root / "SHA256SUMS"),
            "metric": processing["metric"],
            "quality_flag": processing["quality_flag"],
            "domain_scope": processing["domain_scope"],
            "domain_hour_rule": processing["domain_hour_rule"],
            "cross_domain_rule": processing["cross_domain_rule"],
            "missing_policy": processing["missing_policy"],
            "normalization_rule": processing["normalization_rule"],
            "normalization_uses_future_window_peak": True,
            "normalization_allowed_use": (
                "fixed_replay_not_train_or_holdout_feature"
            ),
            "source_time_semantics": "anonymized_relative_microseconds",
            "output_time_semantics": "relative_hour_from_first_common_sample",
            "hours": len(rows),
            "eligible_domains": len(trace_paths),
            "complete_domain_hours": complete_domain_hours,
            "full_window_domains": full_window_domains,
            "minimum_complete_valid_domains_per_hour": min(valid_domain_counts),
            "maximum_complete_valid_domains_per_hour": max(valid_domain_counts),
            "hourly_shape_sha256": shape_sha256,
            "domain_quality_sha256": domain_quality_sha256,
            "absolute_power_mw_available": False,
            "capacity_weighted_aggregation": False,
            "imputation_used": False,
            "model_input_ready_without_separate_mw_mapping": False,
            "evidence_status": "observed_normalized_power_shape",
        }
        summary_path = staging / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if _sha256(summary_path) != processing["expected_summary_sha256"]:
            raise RuntimeError("Google processed summary hash drifted")
        manifest = [
            f"{_sha256(path)}  {path.name}"
            for path in (domain_path, shape_path, summary_path)
        ]
        (staging / "SHA256SUMS").write_text(
            "\n".join(manifest) + "\n",
            encoding="ascii",
        )
        _promote(
            staging,
            output_root,
            ("domain_quality.csv", "hourly_shape.csv", "summary.json", "SHA256SUMS"),
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/google_power_2019.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
