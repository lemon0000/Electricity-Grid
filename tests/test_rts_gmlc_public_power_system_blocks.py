from __future__ import annotations

import csv
import gzip
import hashlib
import json
from itertools import pairwise
from pathlib import Path

import pytest
import yaml

import experiments.build_rts_gmlc_public_power_system_blocks as builder
from src.scenarios.rts_gmlc_n1_chronology import (
    N1OutageEvent,
    N1ReliabilityComponent,
    event_by_hour,
    simulate_n_minus_one_events,
)

PACKAGE = Path(
    "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4"
)
CONFIG = Path("configs/rts_gmlc_public_power_system_blocks_v4.yaml")
IMPLEMENTATION = Path("experiments/build_rts_gmlc_public_power_system_blocks.py")
N1_MODULE = Path("src/scenarios/rts_gmlc_n1_chronology.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_package_manifest(directory: Path) -> str:
    manifest = {
        path.name: _sha256(path)
        for path in sorted(directory.iterdir())
        if path.name != "SHA256SUMS.json"
    }
    path = directory / "SHA256SUMS.json"
    path.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return _sha256(path)


def test_n1_competing_risk_chronology_is_reproducible_and_nonoverlapping():
    components = (
        N1ReliabilityComponent("branch", "L1", 0.2, 2.0),
        N1ReliabilityComponent("generator", "G1", 0.1, 4.0),
    )

    first = simulate_n_minus_one_events(components, seed=17, horizon_hours=200)
    second = simulate_n_minus_one_events(components, seed=17, horizon_hours=200)
    active = event_by_hour(first, horizon_hours=200)

    assert first == second
    assert first
    assert all(
        earlier.end_hour_exclusive <= later.start_hour
        for earlier, later in pairwise(first)
    )
    assert sum(event is not None for event in active) == sum(
        event.duration_hours for event in first
    )
    assert len({event.event_id for event in first}) == len(first)


def test_event_expansion_rejects_overlap():
    events = (
        N1OutageEvent(1, "a", "branch", "L1", 1, 3),
        N1OutageEvent(1, "b", "generator", "G1", 2, 4),
    )

    with pytest.raises(ValueError, match="overlapping"):
        event_by_hour(events, horizon_hours=5)


def _synthetic_config(tmp_path: Path) -> Path:
    grid = tmp_path / "grid"
    source_data = grid / "RTS_Data" / "SourceData"
    cfe = tmp_path / "cfe"
    source_data.mkdir(parents=True)
    cfe.mkdir()
    with (source_data / "gen.csv").open(
        "w", encoding="utf-8", newline=""
    ) as target:
        writer = csv.DictWriter(
            target,
            fieldnames=("GEN UID", "Unit Type", "MTTF Hr", "MTTR Hr", "FOR"),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerow(
            {
                "GEN UID": "G1",
                "Unit Type": "CT",
                "MTTF Hr": 200,
                "MTTR Hr": 3,
                "FOR": 0.0148,
            }
        )
    with (source_data / "branch.csv").open(
        "w", encoding="utf-8", newline=""
    ) as target:
        writer = csv.DictWriter(
            target,
            fieldnames=(
                "UID",
                "From Bus",
                "To Bus",
                "Perm OutRate",
                "Duration",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            [
                {
                    "UID": "L1",
                    "From Bus": 1,
                    "To Bus": 2,
                    "Perm OutRate": 87.6,
                    "Duration": 2,
                },
                {
                    "UID": "L2",
                    "From Bus": 1,
                    "To Bus": 2,
                    "Perm OutRate": 43.8,
                    "Duration": 2,
                },
            ]
        )
    grid_manifest_lines = []
    for path in sorted(source_data.iterdir()):
        relative = path.relative_to(grid)
        grid_manifest_lines.append(f"{_sha256(path)}  {relative.as_posix()}")
    (grid / "SHA256SUMS").write_text(
        "\n".join(grid_manifest_lines) + "\n",
        encoding="ascii",
    )
    grid_manifest = _sha256(grid / "SHA256SUMS")
    cfe_path = cfe / "hourly_cfe_deficit.csv"
    with cfe_path.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(
            target,
            fieldnames=(
                "timestamp",
                "system_load_mw",
                "green_call_fraction",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        for hour in range(24):
            writer.writerow(
                {
                    "timestamp": f"2020-01-01T{hour:02d}:00:00",
                    "system_load_mw": 1000 + hour,
                    "green_call_fraction": hour / 24,
                }
            )
    cfe_manifest = _write_package_manifest(cfe)
    config = {
        "source": {
            "repository": "https://github.com/GridMod/RTS-GMLC",
            "release": "v0.2.3",
            "commit": "3ece0d3725c844056132393ee252b3083dd4eab4",
            "grid_root": str(grid),
            "grid_manifest_sha256": grid_manifest,
            "cfe_package": str(cfe),
            "cfe_manifest_sha256": cfe_manifest,
        },
        "derivation": {
            "reliability_scope": (
                "enabled_generators_and_nonislanding_AC_branches_in_full_RTS_GMLC"
            ),
            "excluded_generator_unit_types": ["CSP", "STORAGE", "SYNC_COND"],
            "excluded_branch_rule": (
                "removal_increases_AC_connected_component_count"
            ),
            "outage_seeds": [7],
            "outage_model": (
                "stationary_system_level_competing_risks_N_minus_one"
            ),
            "split_fraction": 0.5,
            "split_rounding": "floor",
            "cross_split_event_policy": (
                "exclude_every_block_touched_by_cross_split_event"
            ),
            "block_hours": 4,
            "block_stride_hours": 4,
            "training_marginal_role": "policy_fitting_only",
            "holdout_marginal_role": (
                "transport_row_and_fixed_policy_evaluation"
            ),
            "outage_frequency_semantics": "sampled_from_published_rate",
        },
        "output": {
            "schema": "test_power_system_blocks",
            "directory": str(tmp_path / "output"),
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        yaml.safe_dump(config, sort_keys=True),
        encoding="utf-8",
    )
    return config_path


def test_builder_preserves_clock_and_excludes_cross_split_event(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config = _synthetic_config(tmp_path)
    config_payload = yaml.safe_load(config.read_text(encoding="utf-8"))
    monkeypatch.setattr(
        builder,
        "RTS_GMLC_MANIFEST_SHA256",
        config_payload["source"]["grid_manifest_sha256"],
    )

    def fake_events(components, *, seed, horizon_hours):
        assert components
        assert seed == 7
        assert horizon_hours == 24
        return (
            N1OutageEvent(seed, "cross", "branch", "L1", 10, 14),
            N1OutageEvent(seed, "holdout", "generator", "G1", 16, 18),
        )

    monkeypatch.setattr(builder, "simulate_n_minus_one_events", fake_events)
    summary = builder.run(config)

    output = tmp_path / "output"
    with gzip.open(
        output / "power_system_blocks.csv.gz",
        "rt",
        encoding="utf-8",
        newline="",
    ) as source:
        rows = list(csv.DictReader(source))
    assert summary["training_block_count"] == 2
    assert summary["holdout_block_count"] == 2
    assert summary["cross_split_event_counts"] == {"7": 1}
    assert len(rows) == 16
    assert {row["active_event_id"] for row in rows} == {"", "holdout"}
    assert all(row["active_event_id"] != "cross" for row in rows)
    assert all(row["timestamp"].endswith("+00:00") for row in rows)
    assert {
        int(row["source_hour"])
        for row in rows
        if row["split"] == "training"
    } == set(range(8))
    assert {
        int(row["source_hour"])
        for row in rows
        if row["split"] == "holdout"
    } == set(range(16, 24))

    manifest = json.loads(
        (output / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert all(_sha256(output / name) == digest for name, digest in manifest.items())
    for split in ("training", "holdout"):
        with gzip.open(
            output / f"{split}_marginal.csv.gz",
            "rt",
            encoding="utf-8",
            newline="",
        ) as source:
            marginal = list(csv.DictReader(source))
        assert sum(float(row["probability"]) for row in marginal) == pytest.approx(1)


def test_builder_rejects_package_manifest_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    config_path = _synthetic_config(tmp_path)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    expected = config["source"]["grid_manifest_sha256"]
    monkeypatch.setattr(builder, "RTS_GMLC_MANIFEST_SHA256", expected)
    config["source"]["grid_manifest_sha256"] = "0" * 64
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="manifest identity drifted"):
        builder.run(config_path)


def test_published_v4_package_integrity_and_scope():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))
    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["config_sha256"] == _sha256(CONFIG)
    assert summary["implementation_sha256"] == _sha256(IMPLEMENTATION)
    assert summary["n1_chronology_module_sha256"] == _sha256(N1_MODULE)
    assert summary["reliability_components"] == 211
    assert summary["generator_reliability_components"] == 93
    assert summary["branch_reliability_components"] == 118
    assert summary["excluded_disabled_generator_uids"] == ["212_CSP_1"]
    assert summary["excluded_islanding_branch_uids"] == ["B11", "C11"]
    assert summary["maximum_simultaneous_outages"] == 1
    assert summary["training_block_count"] == 541
    assert summary["holdout_block_count"] == 530
    assert summary["block_hours"] == 24
    assert not summary["grid_need_dispatch_completed"]
    assert not summary["empirical_outage_probability_claimed"]
    assert not summary["security_certified"]

    with gzip.open(
        PACKAGE / "power_system_blocks.csv.gz",
        "rt",
        encoding="utf-8",
        newline="",
    ) as source:
        rows = list(csv.DictReader(source))
    assert len(rows) == (541 + 530) * 24
    for split, expected_blocks in (("training", 541), ("holdout", 530)):
        split_rows = [row for row in rows if row["split"] == split]
        assert len({row["block_id"] for row in split_rows}) == expected_blocks
        with gzip.open(
            PACKAGE / f"{split}_marginal.csv.gz",
            "rt",
            encoding="utf-8",
            newline="",
        ) as source:
            marginal = list(csv.DictReader(source))
        assert sum(float(row["probability"]) for row in marginal) == pytest.approx(1)
