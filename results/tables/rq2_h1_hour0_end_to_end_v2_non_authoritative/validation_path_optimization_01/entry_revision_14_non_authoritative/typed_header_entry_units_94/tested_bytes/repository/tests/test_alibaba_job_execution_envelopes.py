"""Integrity tests for the Alibaba job-level execution envelopes."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from pathlib import Path

PACKAGE = Path(
    "data/processed/model_inputs/alibaba_job_execution_envelopes_v1"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_job_envelope_manifest_and_evidence_boundary():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))

    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["candidate_task_rows"] == 732318
    assert summary["job_rows"] == 714903
    assert summary["evidence_status"] == {
        "checkpoint_state_observed": False,
        "deadline_observed": False,
        "power_conversion_applied": False,
        "preemptibility_observed": False,
        "recoverable_fraction_inferred": False,
        "workload_trace": "observed_anonymized_relative_chronology",
    }


def test_job_envelope_schema_and_observed_time_order():
    path = PACKAGE / "job_execution_envelopes.csv.gz"
    row_count = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        for row in reader:
            row_count += 1
            assert float(row["observed_completion_time_s"]) >= float(
                row["observed_release_time_s"]
            )
            assert float(row["declared_gpu_equivalents_sum"]) > 0
            assert row["deadline_observed"] == "0"
            assert row["checkpoint_state_observed"] == "0"
            assert row["preemptibility_observed"] == "0"
            assert row["recoverable_fraction_inferred"] == "0"
            assert row["power_conversion_applied"] == "0"
    assert row_count == 714903
