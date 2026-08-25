"""Tests for the RTS-GMLC hourly CFE-deficit derivation."""

from __future__ import annotations

import csv
import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from src.grid import (
    RtsGmlcChronologicalData,
    RtsGmlcChronologicalGenerator,
    RtsGmlcHourlyPoint,
)
from src.scenarios.rts_gmlc_cfe_deficit import (
    CFE_DEFICIT_COLUMNS,
    derive_rts_gmlc_cfe_deficit,
    load_rts_gmlc_cfe_deficit_profile,
)

PUBLISHED_PROFILE = Path(
    "data/processed/model_inputs/"
    "rts_gmlc_hourly_cfe_deficit_250mw_v1/hourly_cfe_deficit.csv"
)
PUBLISHED_PROFILE_SHA256 = (
    "f1c483fdf20ccc1ddc8e484d719b51f5b67a497bd99fd9bd7347dc57518586a5"
)
SUCCESSOR_PACKAGE = Path(
    "data/processed/model_inputs/rts_gmlc_hourly_cfe_deficit_250mw_v2"
)


def _generator(uid: str, unit_type: str, *, enabled: bool = True):
    return RtsGmlcChronologicalGenerator(
        uid=uid,
        bus=1,
        unit_type=unit_type,
        category=unit_type,
        fuel=unit_type,
        dispatch_mode="curtailable" if enabled else "disabled",
        enabled=enabled,
        disabled_reason=None if enabled else "test",
        p_min_mw=0.0,
        p_max_mw=100.0,
        minimum_down_time_hours=0.0,
        minimum_up_time_hours=0.0,
        ramp_mw_per_minute=100.0,
        ramp_mw_per_hour=6000.0,
        start_time_cold_hours=0.0,
        start_time_warm_hours=0.0,
        start_time_hot_hours=0.0,
        start_heat_cold_mmbtu=0.0,
        start_heat_warm_mmbtu=0.0,
        start_heat_hot_mmbtu=0.0,
        non_fuel_start_cost_usd=0.0,
        shutdown_cost_usd=0.0,
        fuel_price_usd_per_mmbtu=0.0,
        variable_om_usd_per_mwh=0.0,
        cold_start_cost_usd=0.0,
        warm_start_cost_usd=0.0,
        hot_start_cost_usd=0.0,
        cost_breakpoints_mw=(),
        cost_values_usd_per_hour=(),
    )


def _data() -> RtsGmlcChronologicalData:
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    renewable = (20.0, 50.0, 100.0)
    points = tuple(
        RtsGmlcHourlyPoint(
            timestamp=start + timedelta(hours=index),
            demand_by_bus_mw={1: 100.0},
            generator_min_mw={"wind": 0.0, "gas": 0.0},
            generator_max_mw={"wind": available, "gas": 100.0},
            spin_up_requirement_by_area_mw={1: 0.0},
        )
        for index, available in enumerate(renewable)
    )
    return RtsGmlcChronologicalData(
        base_mva=100.0,
        reference_bus=1,
        buses=(),
        branches=(),
        dc_branches=(),
        generators=(_generator("wind", "WIND"), _generator("gas", "CC")),
        hourly_points=points,
    )


def test_cfe_deficit_and_load_shift_call_match_hand_calculation():
    profile = derive_rts_gmlc_cfe_deficit(
        _data(),
        dc_demand_mw=80.0,
        hourly_cfe_target=0.5,
        renewable_unit_types=frozenset({"WIND"}),
        source="synthetic",
    )

    assert [point.renewable_share for point in profile.points] == pytest.approx(
        [0.2, 0.5, 1.0]
    )
    assert [point.cfe_deficit_mw for point in profile.points] == pytest.approx(
        [24.0, 0.0, 0.0]
    )
    assert profile.values == pytest.approx((48.0, 0.0, 0.0))


def test_disabled_renewable_and_thermal_capacity_are_excluded():
    data = _data()
    data = RtsGmlcChronologicalData(
        **{
            **data.__dict__,
            "generators": (
                _generator("wind", "WIND", enabled=False),
                _generator("gas", "CC"),
            ),
        }
    )
    with pytest.raises(ValueError, match="no enabled renewable"):
        derive_rts_gmlc_cfe_deficit(
            data,
            dc_demand_mw=80.0,
            hourly_cfe_target=1.0,
            renewable_unit_types=frozenset({"WIND"}),
            source="synthetic",
        )


def test_profile_loader_checks_hash_formula_and_hourly_continuity(tmp_path):
    profile = derive_rts_gmlc_cfe_deficit(
        _data(),
        dc_demand_mw=80.0,
        hourly_cfe_target=0.5,
        renewable_unit_types=frozenset({"WIND"}),
        source="synthetic",
    )
    path = tmp_path / "profile.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=CFE_DEFICIT_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for point in profile.points:
            writer.writerow(
                {
                    "timestamp": point.timestamp.isoformat(),
                    "system_load_mw": point.system_load_mw,
                    "renewable_available_mw": point.renewable_available_mw,
                    "renewable_share": point.renewable_share,
                    "dc_demand_mw": point.dc_demand_mw,
                    "hourly_cfe_target": point.hourly_cfe_target,
                    "attributed_cfe_mw": point.attributed_cfe_mw,
                    "cfe_deficit_mw": point.cfe_deficit_mw,
                    "green_call_mw": point.green_call_mw,
                    "green_call_fraction": (point.green_call_mw / point.dc_demand_mw),
                }
            )
    digest = hashlib.sha256(path.read_bytes()).hexdigest()

    loaded = load_rts_gmlc_cfe_deficit_profile(
        path, expected_sha256=digest, source="test"
    )

    assert loaded.values == pytest.approx(profile.values)
    with pytest.raises(ValueError, match="SHA-256"):
        load_rts_gmlc_cfe_deficit_profile(path, expected_sha256="0" * 64, source="test")

    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    rows[1]["hourly_cfe_target"] = "0.75"
    rows[1]["cfe_deficit_mw"] = "20.0"
    rows[1]["green_call_mw"] = str(20.0 / 0.75)
    rows[1]["green_call_fraction"] = str((20.0 / 0.75) / 80.0)
    mixed_path = tmp_path / "mixed.csv"
    with mixed_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=CFE_DEFICIT_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)
    mixed_digest = hashlib.sha256(mixed_path.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match="demand and target must be constant"):
        load_rts_gmlc_cfe_deficit_profile(
            mixed_path, expected_sha256=mixed_digest, source="test"
        )


def test_published_rts_gmlc_cfe_profile_is_hash_bound_and_complete():
    profile = load_rts_gmlc_cfe_deficit_profile(
        PUBLISHED_PROFILE,
        expected_sha256=PUBLISHED_PROFILE_SHA256,
        source="published_test_artifact",
    )

    assert len(profile.points) == 8784
    assert min(profile.values) == 0.0
    assert max(profile.values) == pytest.approx(244.07262873226085)
    assert sum(profile.values) / len(profile.values) == pytest.approx(
        133.89189560828532
    )


def test_cfe_successor_records_live_provenance_and_frozen_predecessor():
    summary = json.loads(
        (SUCCESSOR_PACKAGE / "summary.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (SUCCESSOR_PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert all(
        hashlib.sha256((SUCCESSOR_PACKAGE / name).read_bytes()).hexdigest()
        == digest
        for name, digest in manifest.items()
    )
    assert summary["schema"] == "rts_gmlc_hourly_cfe_deficit_v2"
    assert summary["config_sha256"] == hashlib.sha256(
        Path("configs/rts_gmlc_cfe_deficit_v2.yaml").read_bytes()
    ).hexdigest()
    assert summary["implementation_sha256"] == hashlib.sha256(
        Path("experiments/build_rts_gmlc_cfe_deficit.py").read_bytes()
    ).hexdigest()
    assert summary["derivation_module_sha256"] == hashlib.sha256(
        Path("src/scenarios/rts_gmlc_cfe_deficit.py").read_bytes()
    ).hexdigest()
    assert summary["predecessor"]["manifest_sha256"] == hashlib.sha256(
        Path(
            "data/processed/model_inputs/"
            "rts_gmlc_hourly_cfe_deficit_250mw_v1/SHA256SUMS.json"
        ).read_bytes()
    ).hexdigest()
    assert (
        manifest["hourly_cfe_deficit.csv"]
        == summary["predecessor"]["profile_sha256"]
        == PUBLISHED_PROFILE_SHA256
    )
