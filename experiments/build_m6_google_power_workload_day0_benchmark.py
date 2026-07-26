"""Build a no-flex M6 benchmark from the paired Google day-0 evidence."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from experiments.process_google_power_workload_day0 import (
    PAIR_FIELDS,
    _publish_directory,
    _verify_manifest,
)
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
CANDIDATE_AUDIT_FIELDS = (
    "timestamp",
    "hour_index",
    "measured_power_util_mean",
    "derived_requested_demand_mw",
    "observed_cpu_ncu_lower",
    "observed_cpu_ncu_upper",
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
    "unknown_capacity_machine_seconds",
    "machine_capacity_complete",
    "priority_candidate_semantics",
    "candidate_proxy_used_as_flexibility",
    "cpu_share_mapped_to_power",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _format_float(value: float) -> str:
    if not math.isfinite(value):
        raise ValueError("Cannot serialize a non-finite benchmark value")
    return f"{value:.12f}".rstrip("0").rstrip(".")


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _validate_source_summary(
    summary: dict[str, Any],
    source: dict[str, Any],
) -> None:
    expected = {
        "schema": source["schema"],
        "hours": int(source["expected_hours"]),
        "hourly_pair_sha256": source["sha256"],
        "evidence_status": "observed_same_system_normalized_power_and_ncu_usage_pair",
        "power_is_normalized_utilization_not_watts_or_mw": True,
        "production_power_used": False,
        "population_is_complete_pdu_workload": False,
        "capacity_used_to_normalize_usage": False,
        "absolute_power_mw_available": False,
        "flexibility_observed": False,
        "recovery_parameters_observed": False,
        "model_input_ready": False,
        "priority_candidate_semantics": (
            "low_priority_usage_candidate_not_observed_flexibility"
        ),
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ValueError(f"Paired Google source summary drifted: {key}")


def _load_pair_rows(path: Path, *, expected_hours: int) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != list(PAIR_FIELDS):
            raise ValueError("Paired Google hourly columns drifted")
        rows = list(reader)
    if len(rows) != expected_hours:
        raise ValueError("Paired Google benchmark horizon drifted")
    if [int(row["hour_index"]) for row in rows] != list(range(expected_hours)):
        raise ValueError("Paired Google hours must be continuous from zero")
    for hour, row in enumerate(rows):
        if (
            int(row["cluster_window_start_us"]) != hour * 3_600_000_000
            or int(row["cluster_window_end_us"]) != (hour + 1) * 3_600_000_000
            or int(row["power_valid_sample_count"]) != 12
        ):
            raise ValueError("Paired Google hourly clock or sample count drifted")
        power_minimum = float(row["measured_power_util_min"])
        power_mean = float(row["measured_power_util_mean"])
        power_maximum = float(row["measured_power_util_max"])
        if not 0.0 <= power_minimum <= power_mean <= power_maximum <= 1.0:
            raise ValueError("Paired Google normalized power is outside [0, 1]")
        for prefix in (
            "observed_cpu_ncu",
            "priority_candidate_cpu_ncu",
            "priority_candidate_cpu_share",
            "ambiguous_priority_cpu_share",
            "unknown_priority_cpu_share",
            "synthesized_priority_cpu_share",
        ):
            lower = float(row[f"{prefix}_lower"])
            upper = float(row[f"{prefix}_upper"])
            if not 0.0 <= lower <= upper:
                raise ValueError(f"Paired Google bounds are invalid: {prefix}")
            if prefix.endswith("share") and upper > 1.0:
                raise ValueError(f"Paired Google share exceeds one: {prefix}")
    return rows


def run(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    benchmark = config["benchmark"]
    source = config["source_pair"]
    mapping = config["mapping"]
    candidate = config["candidate_proxy"]
    recovery_config = config["recovery"]

    if benchmark != {
        "id": "m6_google_power_workload_day0_no_flex_250mw_v1",
        "evidence_status": "derived_benchmark",
        "result_evidence_ceiling": "business_input_contract_only",
        "chronological_grid_dispatch_coupled": False,
        "security_certified": False,
    }:
        raise ValueError("Day-0 benchmark evidence contract drifted")
    if mapping["rule"] != ("measured_power_util_times_assumed_reference_capacity"):
        raise ValueError("Unsupported day-0 normalized-power mapping")
    if mapping["assumed_reference_capacity_observed"] is not False:
        raise ValueError("The benchmark reference capacity is not observed")
    if mapping["requested_demand_semantics"] != (
        "scaled_realized_pdu_power_proxy_not_uncapped_request"
    ):
        raise ValueError("Day-0 realized power must remain a demand proxy")
    if mapping["physical_maximum_semantics"] != (
        "assumed_reference_capacity_not_observed_pdu_rating"
    ):
        raise ValueError("Day-0 physical maximum must remain an assumption")
    if mapping["contract_semantics_available"] is not False:
        raise ValueError("The paired day-0 source has no contract semantics")
    if mapping["reference_clock_semantics"] != (
        "synthetic_rebase_for_derived_benchmark"
    ):
        raise ValueError("Day-0 benchmark clock must remain a synthetic rebase")
    if candidate != {
        "semantics": "low_priority_usage_candidate_not_observed_flexibility",
        "candidate_proxy_used_as_flexibility": False,
        "cpu_share_mapped_to_power": False,
        "ambiguous_priority_reassigned": False,
        "unknown_priority_reassigned": False,
    }:
        raise ValueError("Day-0 candidate proxy cannot be upgraded to flexibility")

    pair_path = Path(source["path"])
    source_summary_path = Path(source["summary_path"])
    _verify_manifest(pair_path.parent)
    if _sha256(pair_path) != source["sha256"]:
        raise ValueError("Paired Google hourly SHA-256 drifted")
    if _sha256(source_summary_path) != source["summary_sha256"]:
        raise ValueError("Paired Google summary SHA-256 drifted")
    source_summary = json.loads(source_summary_path.read_text(encoding="utf-8"))
    _validate_source_summary(source_summary, source)
    expected_hours = int(source["expected_hours"])
    pair_rows = _load_pair_rows(pair_path, expected_hours=expected_hours)

    assumed_capacity_mw = float(mapping["assumed_reference_capacity_mw"])
    if assumed_capacity_mw <= 0.0:
        raise ValueError("Assumed reference capacity must be positive")
    if assumed_capacity_mw != 250.0:
        raise ValueError(
            "Assumed reference capacity must match the 250 MW benchmark ID"
        )
    reference_start = datetime.fromisoformat(mapping["reference_start"])
    if reference_start.utcoffset() is None:
        raise ValueError("Day-0 benchmark reference start needs a UTC offset")

    business_rows: list[dict[str, Any]] = []
    audit_rows: list[dict[str, Any]] = []
    requested_values = []
    for row in pair_rows:
        hour = int(row["hour_index"])
        timestamp = (reference_start + timedelta(hours=hour)).isoformat()
        power_util = float(row["measured_power_util_mean"])
        requested = power_util * assumed_capacity_mw
        requested_values.append(requested)
        business_rows.append(
            {
                "timestamp": timestamp,
                "period": mapping["period"],
                "requested_demand_mw": _format_float(requested),
                "flexible_demand_mw": "0",
                "recoverable_flexible_mw": "0",
                "physical_maximum_demand_mw": _format_float(assumed_capacity_mw),
                "recovery_headroom_mw": "0",
            }
        )
        audit_rows.append(
            {
                "timestamp": timestamp,
                "hour_index": hour,
                "measured_power_util_mean": row["measured_power_util_mean"],
                "derived_requested_demand_mw": _format_float(requested),
                "observed_cpu_ncu_lower": row["observed_cpu_ncu_lower"],
                "observed_cpu_ncu_upper": row["observed_cpu_ncu_upper"],
                "priority_candidate_cpu_ncu_lower": row[
                    "priority_candidate_cpu_ncu_lower"
                ],
                "priority_candidate_cpu_ncu_upper": row[
                    "priority_candidate_cpu_ncu_upper"
                ],
                "priority_candidate_cpu_share_lower": row[
                    "priority_candidate_cpu_share_lower"
                ],
                "priority_candidate_cpu_share_upper": row[
                    "priority_candidate_cpu_share_upper"
                ],
                "ambiguous_priority_cpu_share_lower": row[
                    "ambiguous_priority_cpu_share_lower"
                ],
                "ambiguous_priority_cpu_share_upper": row[
                    "ambiguous_priority_cpu_share_upper"
                ],
                "unknown_priority_cpu_share_lower": row[
                    "unknown_priority_cpu_share_lower"
                ],
                "unknown_priority_cpu_share_upper": row[
                    "unknown_priority_cpu_share_upper"
                ],
                "synthesized_priority_cpu_share_lower": row[
                    "synthesized_priority_cpu_share_lower"
                ],
                "synthesized_priority_cpu_share_upper": row[
                    "synthesized_priority_cpu_share_upper"
                ],
                "missing_cpu_overlap_seconds": row["missing_cpu_overlap_seconds"],
                "cpu_conflict_overlap_seconds": row["cpu_conflict_overlap_seconds"],
                "unknown_capacity_machine_seconds": row[
                    "unknown_capacity_machine_seconds"
                ],
                "machine_capacity_complete": row["machine_capacity_complete"],
                "priority_candidate_semantics": candidate["semantics"],
                "candidate_proxy_used_as_flexibility": "false",
                "cpu_share_mapped_to_power": "false",
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
    } or recovery_config["parameter_status"] != (
        "neutral_no_recoverable_load_baseline_not_empirical_recovery"
    ):
        raise ValueError("Day-0 no-flex recovery contract drifted")

    output_root = output_directory or Path(config["output"]["directory"])
    output_root.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_root.name}.processing-"
    with tempfile.TemporaryDirectory(dir=output_root.parent, prefix=prefix) as temp:
        staging = Path(temp)
        business_path = staging / "business_chronology.csv"
        audit_path = staging / "candidate_proxy_audit.csv"
        recovery_path = staging / "recovery_parameters.json"
        _write_csv(business_path, BUSINESS_FIELDS, business_rows)
        _write_csv(audit_path, CANDIDATE_AUDIT_FIELDS, audit_rows)
        recovery_path.write_text(
            json.dumps(recovery_payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        business_sha = _sha256(business_path)
        audit_sha = _sha256(audit_path)
        recovery_sha = _sha256(recovery_path)
        workload_source = EvidenceSource(
            dataset_id=benchmark["id"],
            source_kind="derived_benchmark",
            citation=(
                "Google PowerData and ClusterData 2019 day-0 pair plus the "
                "locked assumed reference-capacity mapping"
            ),
            version="v1",
            sha256=business_sha,
        )
        recovery = RecoveryParameters(
            maximum_recovery_power_mw=0.0,
            recovery_efficiency=1.0,
            source=EvidenceSource(
                dataset_id="neutral_no_recoverable_load_baseline_v1",
                source_kind="derived_benchmark",
                citation=str(recovery_config["parameter_status"]),
                version="v1",
                sha256=recovery_sha,
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
            raise RuntimeError("Day-0 M6 business chronology validation failed")

        summary = {
            "benchmark_id": benchmark["id"],
            "schema": loaded.schema,
            "hours": len(loaded.points),
            "time_step_hours": loaded.time_step_hours,
            "first_timestamp": loaded.points[0].timestamp.isoformat(),
            "last_timestamp": loaded.points[-1].timestamp.isoformat(),
            "assumed_reference_capacity_mw": assumed_capacity_mw,
            "assumed_reference_capacity_observed": False,
            "mapping_rule": mapping["rule"],
            "minimum_requested_demand_mw": min(requested_values),
            "maximum_requested_demand_mw": max(requested_values),
            "flexible_demand_mw": 0.0,
            "recoverable_flexible_mw": 0.0,
            "recovery_headroom_mw": 0.0,
            "source_pair_sha256": source["sha256"],
            "source_summary_sha256": source["summary_sha256"],
            "source_pair_manifest_sha256": _sha256(pair_path.parent / "SHA256SUMS"),
            "business_chronology_sha256": business_sha,
            "candidate_proxy_audit_sha256": audit_sha,
            "recovery_parameters_sha256": recovery_sha,
            "source_evidence_status": source_summary["evidence_status"],
            "evidence_status": benchmark["evidence_status"],
            "result_evidence_ceiling": benchmark["result_evidence_ceiling"],
            "source_clock_rebased": True,
            "reference_clock_semantics": mapping["reference_clock_semantics"],
            "requested_demand_semantics": mapping["requested_demand_semantics"],
            "physical_maximum_semantics": mapping["physical_maximum_semantics"],
            "power_is_normalized_utilization_not_watts_or_mw": True,
            "production_power_used": False,
            "absolute_power_mw_available": False,
            "population_is_complete_pdu_workload": False,
            "capacity_used_to_normalize_usage": False,
            "flexibility_observed": False,
            "priority_candidate_semantics": candidate["semantics"],
            "candidate_proxy_used_as_flexibility": False,
            "cpu_share_mapped_to_power": False,
            "ambiguous_priority_reassigned": False,
            "unknown_priority_reassigned": False,
            "cpu_conflict_bounds_preserved": True,
            "capacity_incomplete_hours": source_summary["capacity_incomplete_hours"],
            "recovery_parameters_observed": False,
            "contract_semantics_available": False,
            "model_business_input_contract_loaded": True,
            "full_m6_model_input_ready": False,
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
        observed_hashes = {
            "business_chronology.csv": business_sha,
            "candidate_proxy_audit.csv": audit_sha,
            "recovery_parameters.json": recovery_sha,
            "summary.json": _sha256(summary_path),
        }
        expected_hashes = config["expected"]["artifact_sha256"]
        if observed_hashes != expected_hashes:
            raise RuntimeError(
                "Day-0 M6 benchmark artifact hashes drifted: "
                + json.dumps(observed_hashes, sort_keys=True)
            )
        expected_values = config["expected"]
        if not math.isclose(
            min(requested_values),
            float(expected_values["minimum_requested_demand_mw"]),
            abs_tol=1e-9,
        ) or not math.isclose(
            max(requested_values),
            float(expected_values["maximum_requested_demand_mw"]),
            abs_tol=1e-9,
        ):
            raise RuntimeError("Day-0 derived demand range drifted")
        (staging / "SHA256SUMS").write_text(
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
        default=Path("configs/m6_google_power_workload_day0_benchmark.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
