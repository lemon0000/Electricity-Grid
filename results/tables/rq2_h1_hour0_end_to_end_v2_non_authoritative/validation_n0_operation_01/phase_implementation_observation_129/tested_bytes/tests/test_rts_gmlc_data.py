from collections import Counter
from pathlib import Path

import pytest

from src.grid import (
    RTS_GMLC_COMMIT,
    RTS_GMLC_MANIFEST_SHA256,
    RTS_GMLC_RELEASE,
    RTS_GMLC_REPOSITORY,
    load_rts24_area1_load_multipliers,
    load_rts_gmlc_chronological_data,
    summarize_rts_gmlc,
)

UPSTREAM_ROOT = Path("data/raw/rts_gmlc/v0.2.3/upstream")


pytestmark = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_rts_gmlc.ps1 to enable source-data tests",
)


@pytest.fixture(scope="module")
def chronological_data():
    return load_rts_gmlc_chronological_data(UPSTREAM_ROOT)


def test_pinned_rts_gmlc_source_is_complete_and_verified():
    summary = summarize_rts_gmlc(UPSTREAM_ROOT)
    assert summary.source_repository == RTS_GMLC_REPOSITORY
    assert summary.source_release == RTS_GMLC_RELEASE
    assert summary.source_commit == RTS_GMLC_COMMIT
    assert summary.source_manifest_sha256 == RTS_GMLC_MANIFEST_SHA256
    assert summary.sha256_manifest_valid
    assert summary.buses == 73
    assert summary.generators == 158
    assert summary.ac_branches == 120
    assert summary.static_load_mw == pytest.approx(8550.0)
    assert summary.day_ahead_hours == 8784
    assert all(rows == 8784 for rows in summary.day_ahead_rows.values())
    assert all(summary.day_ahead_series_timestamp_continuous.values())
    assert summary.day_ahead_series_common_calendar
    assert summary.day_ahead_core_pointer_columns_complete
    assert summary.generators_with_positive_ramp == 155


def test_area1_hourly_load_proxy_is_continuous_and_peak_normalized():
    multipliers = load_rts24_area1_load_multipliers(UPSTREAM_ROOT)
    values = [value for _, value in multipliers]
    assert len(values) == 8784
    assert min(values) == pytest.approx(0.30133597228070175)
    assert max(values) == pytest.approx(1.0)


def test_leap_year_quarter_hours_come_from_the_continuous_timestamps():
    multipliers = load_rts24_area1_load_multipliers(UPSTREAM_ROOT)
    hours = Counter((timestamp.month - 1) // 3 + 1 for timestamp, _ in multipliers)

    assert hours == {1: 2184, 2: 2184, 3: 2208, 4: 2208}


def test_native_chronological_topology_is_typed_and_preserves_parallel_lines(
    chronological_data,
):
    assert chronological_data.base_mva == 100.0
    assert chronological_data.reference_bus == 113
    assert len(chronological_data.buses) == 73
    assert len(chronological_data.branches) == 120
    assert len(chronological_data.dc_branches) == 1
    assert len(chronological_data.generators) == 158
    assert len(chronological_data.hourly_points) == 8784

    endpoint_counts = Counter(
        tuple(sorted((branch.from_bus, branch.to_bus)))
        for branch in chronological_data.branches
    )
    assert sum(count > 1 for count in endpoint_counts.values()) == 12
    assert max(endpoint_counts.values()) == 2

    dc_branch = chronological_data.dc_branches[0]
    assert dc_branch.uid == "DC1"
    assert (dc_branch.from_bus, dc_branch.to_bus) == (113, 316)
    assert dc_branch.p_min_mw == -100.0
    assert dc_branch.p_max_mw == 100.0


def test_native_generator_modes_and_pointer_bounds_use_unscaled_mw(
    chronological_data,
):
    generators = {
        generator.uid: generator for generator in chronological_data.generators
    }
    assert Counter(generator.dispatch_mode for generator in generators.values()) == {
        "committable": 73,
        "fixed": 51,
        "curtailable": 29,
        "disabled": 5,
    }

    first = chronological_data.hourly_points[0]
    assert first.generator_min_mw["122_HYDRO_1"] == pytest.approx(4.2)
    assert first.generator_max_mw["122_HYDRO_1"] == pytest.approx(4.2)
    assert first.generator_min_mw["309_WIND_1"] == 0.0
    assert first.generator_max_mw["309_WIND_1"] == pytest.approx(142.8)
    assert first.generator_min_mw["308_RTPV_1"] == 0.0
    assert first.generator_max_mw["308_RTPV_1"] == 0.0

    for uid in ("212_CSP_1", "313_STORAGE_1", "114_SYNC_COND_1"):
        assert not generators[uid].enabled
        assert generators[uid].disabled_reason
        assert first.generator_min_mw[uid] == 0.0
        assert first.generator_max_mw[uid] == 0.0


def test_native_hourly_load_reconstructs_regions_and_spin_requirements(
    chronological_data,
):
    buses = {bus.uid: bus for bus in chronological_data.buses}
    first = chronological_data.hourly_points[0]
    expected_regional_load = {1: 985.0197922, 2: 1102.675901, 3: 1249.636191}
    for area, expected_mw in expected_regional_load.items():
        actual_mw = sum(
            first.demand_by_bus_mw[bus.uid]
            for bus in buses.values()
            if bus.area == area
        )
        assert actual_mw == pytest.approx(expected_mw)
    assert first.demand_by_bus_mw[101] == pytest.approx(
        expected_regional_load[1] * 108.0 / 2850.0
    )
    assert first.spin_up_requirement_by_area_mw == pytest.approx(
        {1: 29.551, 2: 33.08, 3: 37.489}
    )


def test_native_thermal_cost_and_intertemporal_parameters_are_complete(
    chronological_data,
):
    generators = {
        generator.uid: generator for generator in chronological_data.generators
    }
    generator = generators["101_CT_1"]
    assert generator.minimum_down_time_hours == 1
    assert generator.minimum_up_time_hours == 1
    assert generator.ramp_mw_per_minute == 3.0
    assert generator.ramp_mw_per_hour == 180.0
    assert generator.cost_breakpoints_mw == pytest.approx((8.0, 12.0, 16.0, 20.0))
    assert generator.cold_start_cost_usd == pytest.approx(51.747)
    assert generator.warm_start_cost_usd == pytest.approx(51.747)
    assert generator.hot_start_cost_usd == pytest.approx(51.747)

    slopes = [
        (later_cost - earlier_cost) / (later_mw - earlier_mw)
        for earlier_mw, later_mw, earlier_cost, later_cost in zip(
            generator.cost_breakpoints_mw,
            generator.cost_breakpoints_mw[1:],
            generator.cost_values_usd_per_hour,
            generator.cost_values_usd_per_hour[1:],
        )
    ]
    assert slopes == sorted(slopes)


def test_native_chronological_loader_rejects_a_noncanonical_base_mva():
    with pytest.raises(ValueError, match="100 MVA"):
        load_rts_gmlc_chronological_data(UPSTREAM_ROOT, base_mva=99.0)
