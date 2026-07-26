"""Map the Google normalized shape into a no-flexibility M6 benchmark input."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from experiments.process_google_power_workload_day0 import _publish_directory
from src.evaluation import (
    BUSINESS_CHRONOLOGY_SCHEMA,
    EvidenceSource,
    RecoveryParameters,
    load_business_chronology_csv,
)

BUSINESS_FIELDS = (
    "timestamp",
    "period",
    "requested_demand_mw",
    "flexible_demand_mw",
    "recoverable_flexible_mw",
    "physical_maximum_demand_mw",
    "recovery_headroom_mw",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_float(value: float) -> str:
    return f"{value:.12f}".rstrip("0").rstrip(".")


def run(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    benchmark = config["benchmark"]
    source = config["source_shape"]
    mapping = config["mapping"]
    recovery_config = config["recovery"]

    if benchmark["evidence_status"] != "derived_benchmark":
        raise ValueError("MW-scaled Google shape must remain a derived benchmark")
    if benchmark["result_evidence_ceiling"] != "business_input_contract_only":
        raise ValueError("Google benchmark result evidence ceiling drifted")
    if benchmark["chronological_grid_dispatch_coupled"] is not False:
        raise ValueError("No chronological grid solver is coupled to this benchmark")
    if benchmark["security_certified"] is not False:
        raise ValueError("Google business-only benchmark cannot be security certified")
    if source["schema"] != "google_power_2019_hourly_shape_v1":
        raise ValueError("Unsupported processed Google shape schema")
    if source["metric"] != "peak_normalized_unweighted_mean":
        raise ValueError("Unsupported processed Google shape metric")
    if source["normalization_rule"] != (
        "ex_post_full_window_peak_for_fixed_replay_only"
    ):
        raise ValueError("Google normalization is only allowed for fixed replay")
    if source["source_time_semantics"] != "anonymized_relative_microseconds":
        raise ValueError("Google source clock cannot be presented as a real calendar")
    if mapping["rule"] != "peak_normalized_shape_times_nominal_peak":
        raise ValueError("Unsupported Google shape-to-MW mapping")
    if mapping["physical_maximum_rule"] != "nominal_peak_mw":
        raise ValueError("Unsupported Google physical-maximum rule")
    if mapping["requested_demand_semantics"] != (
        "scaled_realized_pdu_power_proxy_not_uncapped_request"
    ):
        raise ValueError("Google realized power must remain an explicit demand proxy")
    if mapping["physical_maximum_semantics"] != (
        "assumed_project_benchmark_peak_not_observed_capacity"
    ):
        raise ValueError("Google benchmark peak must remain an explicit assumption")
    if mapping["contract_semantics_available"] is not False:
        raise ValueError("Google power shape has no observed contract semantics")
    if mapping["reference_clock_semantics"] != (
        "synthetic_rebase_for_derived_benchmark"
    ):
        raise ValueError("Google reference clock must remain a synthetic rebase")
    zero_rules = (
        mapping["flexible_demand_rule"],
        mapping["recoverable_flexible_rule"],
        mapping["recovery_headroom_rule"],
    )
    if zero_rules != (
        "zero_until_sourced_flexibility_evidence_exists",
        "zero_until_sourced_recovery_evidence_exists",
        "zero_for_no_flexibility_baseline",
    ):
        raise ValueError("This benchmark only supports the registered zero-flex rules")

    shape_path = Path(source["path"])
    if _sha256(shape_path) != source["sha256"]:
        raise ValueError("Processed Google shape SHA-256 drifted")
    processed_summary_path = Path(source["summary_path"])
    if _sha256(processed_summary_path) != source["summary_sha256"]:
        raise ValueError("Processed Google summary SHA-256 drifted")
    processed_summary = json.loads(processed_summary_path.read_text(encoding="utf-8"))
    expected_processed_metadata = {
        "schema": source["schema"],
        "metric": "measured_power_util",
        "hourly_shape_sha256": source["sha256"],
        "normalization_rule": source["normalization_rule"],
        "evidence_status": "observed_normalized_power_shape",
        "absolute_power_mw_available": False,
        "model_input_ready_without_separate_mw_mapping": False,
    }
    if any(
        processed_summary.get(key) != value
        for key, value in expected_processed_metadata.items()
    ):
        raise ValueError("Processed Google summary metadata drifted")
    with shape_path.open("r", encoding="utf-8", newline="") as input_file:
        shape_rows = list(csv.DictReader(input_file))
    expected_hours = int(mapping["expected_hours"])
    if len(shape_rows) != expected_hours:
        raise ValueError("Processed Google shape has an unexpected horizon")
    relative_hours = [int(row["relative_hour"]) for row in shape_rows]
    if relative_hours != list(range(expected_hours)):
        raise ValueError("Processed Google relative hours must be continuous from zero")

    nominal_peak_mw = float(mapping["nominal_peak_mw"])
    if nominal_peak_mw <= 0.0:
        raise ValueError("Nominal benchmark peak must be positive")
    reference_start = datetime.fromisoformat(mapping["reference_start"])
    if reference_start.utcoffset() is None:
        raise ValueError("Benchmark reference start must include a UTC offset")

    business_rows = []
    requested_values = []
    for row in shape_rows:
        shape = float(row[str(source["metric"])])
        if not 0.0 <= shape <= 1.0:
            raise ValueError("Peak-normalized Google shape must lie in [0, 1]")
        requested = nominal_peak_mw * shape
        requested_values.append(requested)
        business_rows.append(
            {
                "timestamp": (
                    reference_start + timedelta(hours=int(row["relative_hour"]))
                ).isoformat(),
                "period": mapping["period"],
                "requested_demand_mw": _format_float(requested),
                "flexible_demand_mw": "0",
                "recoverable_flexible_mw": "0",
                "physical_maximum_demand_mw": _format_float(nominal_peak_mw),
                "recovery_headroom_mw": "0",
            }
        )

    recovery_payload = {
        "schema": recovery_config["schema"],
        "maximum_recovery_power_mw": float(
            recovery_config["maximum_recovery_power_mw"]
        ),
        "recovery_efficiency": float(recovery_config["recovery_efficiency"]),
    }
    if recovery_payload != {
        "schema": "m6_recovery_parameters_v1",
        "maximum_recovery_power_mw": 0.0,
        "recovery_efficiency": 1.0,
    }:
        raise ValueError("No-flexibility benchmark recovery parameters drifted")
    if recovery_config["parameter_status"] != (
        "neutral_no_recoverable_load_baseline_not_empirical_recovery"
    ):
        raise ValueError("Neutral recovery evidence status drifted")
    output_root = output_directory or Path(config["output"]["directory"])
    output_root.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_root.name}.processing-"
    with tempfile.TemporaryDirectory(dir=output_root.parent, prefix=prefix) as temp:
        staging = Path(temp)
        business_path = staging / "business_chronology.csv"
        with business_path.open("w", encoding="utf-8", newline="") as output:
            writer = csv.DictWriter(output, fieldnames=BUSINESS_FIELDS)
            writer.writeheader()
            writer.writerows(business_rows)
        recovery_path = staging / "recovery_parameters.json"
        recovery_path.write_text(
            json.dumps(recovery_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        business_sha256 = _sha256(business_path)
        recovery_sha256 = _sha256(recovery_path)
        expected = config["expected"]
        if business_sha256 != expected["business_chronology_sha256"]:
            raise RuntimeError("M6 Google business chronology hash drifted")
        if recovery_sha256 != expected["recovery_parameters_sha256"]:
            raise RuntimeError("M6 neutral recovery artifact hash drifted")
        minimum_expected = float(expected["minimum_requested_demand_mw"])
        if abs(min(requested_values) - minimum_expected) > 1e-9:
            raise RuntimeError("M6 Google minimum requested demand drifted")
        if max(requested_values) != float(expected["maximum_requested_demand_mw"]):
            raise RuntimeError("M6 Google maximum requested demand drifted")
        workload_source = EvidenceSource(
            dataset_id=str(benchmark["id"]),
            source_kind="derived_benchmark",
            citation="Google PowerData 2019 plus the locked project MW mapping",
            version="v1",
            sha256=business_sha256,
        )
        recovery = RecoveryParameters(
            maximum_recovery_power_mw=0.0,
            recovery_efficiency=1.0,
            source=EvidenceSource(
                dataset_id="neutral_no_recoverable_load_baseline_v1",
                source_kind="derived_benchmark",
                citation=str(recovery_config["parameter_status"]),
                version="v1",
                sha256=recovery_sha256,
            ),
            source_artifact_path=recovery_path,
        )
        loaded = load_business_chronology_csv(
            business_path,
            time_step_hours=1.0,
            workload_source=workload_source,
            recovery=recovery,
        )
        if loaded.schema != BUSINESS_CHRONOLOGY_SCHEMA:
            raise RuntimeError("M6 business chronology schema validation failed")

        summary = {
            "benchmark_id": benchmark["id"],
            "schema": loaded.schema,
            "hours": len(loaded.points),
            "time_step_hours": loaded.time_step_hours,
            "first_timestamp": loaded.points[0].timestamp.isoformat(),
            "last_timestamp": loaded.points[-1].timestamp.isoformat(),
            "nominal_peak_mw": nominal_peak_mw,
            "minimum_requested_demand_mw": min(requested_values),
            "maximum_requested_demand_mw": max(requested_values),
            "flexible_demand_mw": 0.0,
            "recoverable_flexible_mw": 0.0,
            "source_shape_sha256": source["sha256"],
            "business_chronology_sha256": business_sha256,
            "recovery_parameters_sha256": recovery_sha256,
            "source_clock_rebased": True,
            "source_clock_semantics": source["source_time_semantics"],
            "reference_clock_semantics": mapping["reference_clock_semantics"],
            "requested_demand_semantics": mapping["requested_demand_semantics"],
            "physical_maximum_semantics": mapping["physical_maximum_semantics"],
            "contract_semantics_available": False,
            "normalization_rule": source["normalization_rule"],
            "normalization_allowed_use": ("fixed_replay_not_train_or_holdout_feature"),
            "evidence_status": benchmark["evidence_status"],
            "result_evidence_ceiling": benchmark["result_evidence_ceiling"],
            "model_business_input_contract_loaded": True,
            "incident_chronology_available": False,
            "chronological_dispatch_request_built": False,
            "chronological_grid_dispatch_coupled": False,
            "security_certified": False,
        }
        summary_path = staging / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if _sha256(summary_path) != expected["summary_sha256"]:
            raise RuntimeError("M6 Google benchmark summary hash drifted")
        manifest_paths = (business_path, recovery_path, summary_path)
        (staging / "SHA256SUMS").write_text(
            "\n".join(f"{_sha256(path)}  {path.name}" for path in manifest_paths)
            + "\n",
            encoding="ascii",
        )
        _publish_directory(staging, output_root)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/m6_google_power_shape_benchmark.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
