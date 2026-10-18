"""Integrity checks for the NLR GenAI measured-power catalog."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

PACKAGE = Path("data/processed/model_inputs/nlr_genai_power_profiles_v2")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _rows(name: str) -> list[dict[str, str]]:
    with gzip.open(PACKAGE / name, "rt", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_nlr_manifest_and_evidence_boundary_are_fail_closed():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))

    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["source"]["archive_sha256"] == (
        "dcad6de800fb565d850b163902e2eddae48aabd1ed1c7336f9a1cdaf3012f137"
    )
    assert summary["measured_profile_rows"] == 2467
    assert summary["synthetic_facility_profile_rows"] == 8
    assert summary["measured_group_rows"] == 11
    assert summary["evidence_status"] == {
        "alibaba_pairing": "no_shared_jobs_hardware_or_clock",
        "checkpoint_state_observed": False,
        "deadline_observed": False,
        "direct_pai_gpu_to_power_mapping_ready": False,
        "dynamic_ramp_calibration_ready": False,
        "facility_power_observed": False,
        "facility_profiles": "synthetic_diploee_examples",
        "measured_hardware": "4x_nvidia_h100_per_node",
        "measured_power_scope": (
            "source_defined_aggregate_cpu_and_gpu_compute_node_power"
        ),
        "measured_profiles": "observed_hpc_compute_node_power",
        "published_measurement_intervals_s": [0.1, 0.2],
        "recoverable_fraction_observed": False,
        "source_aggregation_recomputed": False,
    }
    assert summary["profile_sample_intervals_s"] == {
        "0.001": 200,
        "0.1": 2226,
        "0.2": 41,
    }
    assert summary["profiles_below_published_measurement_resolution"] == 200


def test_measured_profile_population_and_physical_statistics():
    rows = _rows("measured_power_profile_catalog.csv.gz")
    assert Counter(row["workload_class"] for row in rows) == {
        "training": 41,
        "inference_offline": 1200,
        "inference_online_finite": 1026,
        "inference_online_rate": 200,
    }
    assert len({row["source_member"] for row in rows}) == 2467
    assert (
        sum(row["published_measurement_resolution_supported"] == "0" for row in rows)
        == 200
    )
    for row in rows:
        assert int(row["sample_count"]) >= 2
        assert float(row["sample_interval_s"]) > 0
        assert float(row["duration_s"]) > 0
        assert float(row["minimum_compute_power_w"]) >= 0
        assert float(row["maximum_compute_power_w"]) >= float(
            row["mean_compute_power_w"]
        )
        assert float(row["energy_wh"]) > 0
        assert int(row["gpu_slots"]) == 4 * int(row["node_count"])


def test_synthetic_facility_profiles_remain_separate():
    rows = _rows("synthetic_facility_profile_catalog.csv.gz")
    assert Counter(row["workload_class"] for row in rows) == {
        "colocation": 4,
        "inference": 4,
    }
    assert all(float(row["mean_power_mw"]) > 0 for row in rows)
