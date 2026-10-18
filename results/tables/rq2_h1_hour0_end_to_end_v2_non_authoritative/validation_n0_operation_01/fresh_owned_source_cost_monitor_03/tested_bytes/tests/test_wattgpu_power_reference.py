"""Integrity checks for the WattGPU heterogeneous-power reference."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

PACKAGE = Path("data/processed/model_inputs/wattgpu_power_reference_v1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(name: str) -> list[dict[str, str]]:
    with gzip.open(PACKAGE / name, "rt", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_wattgpu_manifest_and_source_identity():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))

    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["source"]["commit"] == (
        "4e010359c167ac8c65b55aabd1aafbf765ae5d91"
    )
    assert summary["source"]["license"] == "Apache-2.0"
    assert summary["implementation_sha256"] == _sha256(
        Path("experiments/process_wattgpu_power_reference.py")
    )
    assert summary["config_sha256"] == _sha256(
        Path("configs/wattgpu_power_reference_v1.yaml")
    )
    assert summary["experiment_rows"] == 4798
    assert summary["model_count"] == 49
    assert summary["measured_gpu_count"] == 8
    assert summary["gpu_scenario_group_rows"] == 24


def test_wattgpu_experiment_population_and_reported_quality_limits():
    rows = _rows("experiment_power_reference.csv.gz")
    assert Counter(row["scenario"] for row in rows) == {
        "offline": 1598,
        "server_low_qps": 1600,
        "server_high_qps": 1600,
    }
    assert len({row["source_row_index"] for row in rows}) == 4798
    assert (
        sum(row["prompt_generation_request_counts_match"] == "0" for row in rows)
        == 200
    )
    assert (
        sum(float(row["energy_mean_relative_difference"]) > 0.01 for row in rows)
        == 266
    )
    for row in rows:
        assert float(row["measurement_duration_s"]) > 0
        assert float(row["gpu_energy_j"]) > 0
        assert 0 <= float(row["reported_minimum_gpu_power_w"])
        assert float(row["reported_minimum_gpu_power_w"]) <= float(
            row["reported_mean_gpu_power_w"]
        )
        assert float(row["reported_mean_gpu_power_w"]) <= float(
            row["reported_maximum_gpu_power_w"]
        )


def test_alibaba_hardware_overlap_is_not_promoted_to_job_mapping():
    rows = {
        row["alibaba_gpu_type"]: row
        for row in _rows("alibaba_hardware_coverage.csv.gz")
    }
    assert rows["T4"]["mapping_status"] == "exact_gpu_model"
    assert rows["T4"]["candidate_task_count"] == "196065"
    assert rows["T4"]["reference_experiment_count"] == "240"
    assert rows["T4"]["direct_job_power_mapping_ready"] == "0"
    assert rows["V100M32"]["mapping_status"] == (
        "memory_capacity_match_form_factor_unverified"
    )
    assert rows["P100"]["mapping_status"] == "unavailable"
