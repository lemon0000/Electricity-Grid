"""Integrity checks for Alibaba job-by-GPU telemetry."""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import tarfile
from collections import Counter
from pathlib import Path

PACKAGE = Path("data/processed/model_inputs/alibaba_gpu_telemetry_v1")
SOURCE = Path("data/raw/alibaba_gpu_2020_telemetry/v2020/upstream")
MACHINE_CATALOG = Path(
    "data/processed/alibaba_gpu_2020/v2020/machine_catalog.csv.gz"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_telemetry_manifest_and_source_population():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))

    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["source_sensor_rows"] == 3033232
    assert summary["implementation_sha256"] == _sha256(
        Path("experiments/process_alibaba_gpu_2020_telemetry.py")
    )
    assert summary["config_sha256"] == _sha256(
        Path("configs/alibaba_gpu_2020_telemetry_v1.yaml")
    )
    assert summary["candidate_job_population"] == 714903
    assert summary["candidate_job_gpu_rows"] == 576724
    assert summary["candidate_sensor_rows"] == 1964411
    assert summary["source_unmapped_machine_rows"] == 9
    assert summary["source_missing_numeric_counts"] == {
        "avg_gpu_wrk_mem": 0,
        "avg_mem": 1217,
        "cpu_usage": 5829,
        "gpu_wrk_util": 0,
        "max_gpu_wrk_mem": 0,
        "max_mem": 0,
        "read": 3,
        "read_count": 3,
        "write": 3,
        "write_count": 3,
    }


def test_telemetry_evidence_boundary_and_gpu_summary():
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))
    assert summary["evidence_status"] == {
        "continuous_time_series": False,
        "cross_instance_aggregation": "unweighted_mean_of_lifetime_averages",
        "direct_job_to_power_mapping_ready": False,
        "gpu_memory_observed": True,
        "gpu_work_utilization_percent_units_observed": True,
        "power_observed": False,
        "temporal_resolution": "lifetime_average_per_instance",
        "worker_machine_assignment_observed": True,
    }
    by_type = {row["gpu_type"]: row for row in summary["gpu_type_summary"]}
    assert by_type["T4"]["candidate_job_count"] == 144783
    assert by_type["T4"]["candidate_sensor_rows"] == 442198
    assert by_type["T4"]["hardware_reference_status"] == "exact_gpu_model"
    assert by_type["P100"]["hardware_reference_status"] == "unavailable"
    assert all(
        row["direct_job_power_mapping_ready"] == 0
        for row in summary["gpu_type_summary"]
    )


def test_job_gpu_telemetry_schema_and_row_count():
    path = PACKAGE / "job_gpu_telemetry.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        count = 0
        for row in reader:
            count += 1
            assert int(row["sensor_rows"]) > 0
            assert int(row["gpu_work_utilization_observed_rows"]) > 0
            assert float(row["mean_gpu_work_utilization_equivalents"]) >= 0
            assert row["direct_job_power_mapping_ready"] == "0"
    assert count == 576724


def test_raw_missing_values_and_unmapped_machines_are_independently_audited():
    with gzip.open(
        MACHINE_CATALOG, "rt", encoding="utf-8", newline=""
    ) as machine_source:
        known_machines = {
            row["machine"] for row in csv.DictReader(machine_source)
        }
    columns = (
        SOURCE / "pai_sensor_table.header"
    ).read_text(encoding="utf-8").strip().split(",")
    numeric_fields = (
        "cpu_usage",
        "gpu_wrk_util",
        "avg_mem",
        "max_mem",
        "avg_gpu_wrk_mem",
        "max_gpu_wrk_mem",
        "read",
        "write",
        "read_count",
        "write_count",
    )
    missing: Counter[str] = Counter()
    unmapped = 0
    rows = 0
    with tarfile.open(SOURCE / "pai_sensor_table.tar.gz", "r:gz") as archive:
        extracted = archive.extractfile("pai_sensor_table.csv")
        assert extracted is not None
        with gzip.open(
            PACKAGE / "gpu_type_telemetry_summary.csv.gz",
            "rt",
            encoding="utf-8",
            newline="",
        ) as summary_source:
            assert all(
                row["gpu_type"] != "UNMAPPED"
                for row in csv.DictReader(summary_source)
            )
        with io.TextIOWrapper(extracted, encoding="utf-8", newline="") as text:
            for values in csv.reader(text):
                row = dict(zip(columns, values))
                rows += 1
                unmapped += row["machine"] not in known_machines
                for field in numeric_fields:
                    missing[field] += row[field] == ""

    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))
    assert rows == summary["source_sensor_rows"] == 3033232
    assert unmapped == summary["source_unmapped_machine_rows"] == 9
    assert dict(missing) == summary["source_missing_numeric_counts"]
