"""Tests for RTS-GMLC sequential reliability inputs."""

from __future__ import annotations

import csv
from pathlib import Path

from src.scenarios.rts_gmlc_reliability import (
    ReliabilityComponent,
    hourly_outage_counts,
    load_reliability_components,
    simulate_outage_events,
)

RTS_ROOT = Path("data/raw/rts_gmlc/v0.2.3/upstream")


def _write_csv(path: Path, fields: tuple[str, ...], rows: list[dict[str, object]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def test_load_reliability_components_uses_documented_source_fields(tmp_path):
    source = tmp_path / "RTS_Data" / "SourceData"
    _write_csv(
        source / "gen.csv",
        ("GEN UID", "Bus ID", "FOR", "MTTF Hr", "MTTR Hr"),
        [
            {
                "GEN UID": "101_CT_1",
                "Bus ID": 101,
                "FOR": 0.1,
                "MTTF Hr": 450,
                "MTTR Hr": 50,
            },
            {
                "GEN UID": "101_PV_1",
                "Bus ID": 101,
                "FOR": 0,
                "MTTF Hr": 0,
                "MTTR Hr": 0,
            },
            {
                "GEN UID": "201_CT_1",
                "Bus ID": 201,
                "FOR": 0.1,
                "MTTF Hr": 450,
                "MTTR Hr": 50,
            },
        ],
    )
    _write_csv(
        source / "branch.csv",
        ("UID", "From Bus", "To Bus", "Perm OutRate", "Duration"),
        [
            {
                "UID": "A1",
                "From Bus": 101,
                "To Bus": 102,
                "Perm OutRate": 0.5,
                "Duration": 10,
            },
            {
                "UID": "AB1",
                "From Bus": 101,
                "To Bus": 202,
                "Perm OutRate": 0.5,
                "Duration": 10,
            },
        ],
    )

    components = load_reliability_components(tmp_path, area=1)

    assert [(item.component_type, item.uid) for item in components] == [
        ("branch", "A1"),
        ("generator", "101_CT_1"),
    ]
    branch = components[0]
    assert branch.mean_up_hours == 17520
    assert branch.mean_down_hours == 10
    assert components[1].implied_unavailability == 0.1


def test_simulation_is_deterministic_and_hourly_counts_match_events():
    components = (
        ReliabilityComponent(
            component_type="branch",
            uid="line",
            from_bus=1,
            to_bus=2,
            mean_up_hours=5,
            mean_down_hours=2,
            stated_for=None,
            source_rate=1752,
            source_rate_unit="occurrences_per_year",
        ),
    )

    first = simulate_outage_events(components, seed=11, horizon_hours=50)
    second = simulate_outage_events(components, seed=11, horizon_hours=50)
    counts = hourly_outage_counts(first, horizon_hours=50)

    assert first == second
    assert all(
        0 <= event.start_hour < event.end_hour_exclusive <= 50 for event in first
    )
    for hour, (_, branch_count) in enumerate(counts):
        expected = sum(
            event.start_hour <= hour < event.end_hour_exclusive for event in first
        )
        assert branch_count == expected


def test_real_area1_catalog_matches_rts24_component_scope():
    components = load_reliability_components(RTS_ROOT, area=1)

    assert sum(item.component_type == "generator" for item in components) == 30
    assert sum(item.component_type == "branch" for item in components) == 38
    assert (
        max(
            abs(item.stated_for - item.implied_unavailability)
            for item in components
            if item.stated_for is not None
        )
        == 0.0
    )
