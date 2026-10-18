"""Integrity checks for the synchronized RQ2 input package."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path

PACKAGE = Path("data/processed/model_inputs/rq2_joint_data_v1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _count_rows(path: Path) -> int:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        return sum(1 for _ in csv.DictReader(source))


def _hour_key_counts(path: Path) -> Counter[tuple[int, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        return Counter(
            (int(row["source_hour"]), row["timestamp"])
            for row in csv.DictReader(source)
        )


def test_joint_package_manifest_and_scientific_status_are_fail_closed():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))

    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["hours"] == 8784
    assert summary["buses"] == 24
    assert summary["renewable_generators"] == 27
    assert summary["reliability_components"] == 68
    assert summary["maximum_generator_for_identity_error"] == 0
    assert summary["evidence_status"] == {
        "cfe_contract": "eligible_resource_universe_not_allocated_portfolio",
        "empirical_outage_probability_claimed": False,
        "load_and_renewable": "observed_rts_gmlc_benchmark_chronology",
        "outages": "derived_sequential_reliability_benchmark",
        "security_certified": False,
    }


def test_joint_package_has_complete_expected_relations():
    assert _count_rows(PACKAGE / "reliability_components.csv.gz") == 68
    assert _count_rows(PACKAGE / "hourly_outage_counts.csv.gz") == 3 * 8784
    assert _count_rows(PACKAGE / "hourly_bus_load.csv.gz") == 24 * 8784
    assert (
        _count_rows(PACKAGE / "hourly_renewable_availability.csv.gz") == 27 * 8784
    )


def test_joint_hourly_relations_share_the_exact_chronology():
    outage = _hour_key_counts(PACKAGE / "hourly_outage_counts.csv.gz")
    load = _hour_key_counts(PACKAGE / "hourly_bus_load.csv.gz")
    renewable = _hour_key_counts(
        PACKAGE / "hourly_renewable_availability.csv.gz"
    )

    assert len(outage) == len(load) == len(renewable) == 8784
    assert set(outage) == set(load) == set(renewable)
    assert set(outage.values()) == {3}
    assert set(load.values()) == {24}
    assert set(renewable.values()) == {27}
    ordered = sorted(outage)
    assert [source_hour for source_hour, _ in ordered] == list(range(8784))
