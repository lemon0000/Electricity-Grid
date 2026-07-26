from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_multi_poi_ac_replay_amended import (
    _amended_context,
    _read_config,
)

AMENDMENT_PATH = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay_amendment.yaml")
PARENT_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml")
PARENT_PREREGISTRATION = Path(
    "results/tables/rts_gmlc_google_day0_multi_poi_ac_replay_v1/"
    "preregistration/registration.json"
)


requires_parent_preregistration = pytest.mark.skipif(
    not PARENT_PREREGISTRATION.exists(),
    reason="Prepare the parent AC replay preregistration first",
)


def test_lookup_amendment_forbids_every_scientific_or_acceptance_change():
    config = _read_config(AMENDMENT_PATH)

    assert not config["observed_before_amendment"]["batch_ac_case_outcomes_observed"]
    assert config["observed_before_amendment"]["failure_stage"] == (
        "before_first_ac_case_configuration_or_power_flow"
    )
    assert config["scope"]["permitted_change"] == (
        "map_parent_business_timestamps_to_same_clock_rts_gmlc_hourly_grid_points"
    )
    assert "ac_case_assumptions" in config["scope"]["forbidden_changes"]
    assert "result_acceptance_or_summary_rules" in config["scope"]["forbidden_changes"]


def test_lookup_amendment_rejects_a_power_flow_option_change(tmp_path):
    config = yaml.safe_load(AMENDMENT_PATH.read_text(encoding="utf-8"))
    config["scope"]["forbidden_changes"].remove("power_flow_options")
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="scope drifted"):
        _read_config(path)


@requires_parent_preregistration
def test_lookup_amendment_maps_only_the_aligned_grid_point_type():
    context = _amended_context(PARENT_CONFIG)
    points = context.scan_context.business.points

    assert len(points) == 24
    assert all(hasattr(point, "demand_by_bus_mw") for point in points)
    assert tuple(point.timestamp for point in points) == tuple(
        point.timestamp.replace(tzinfo=None)
        for point in context.scan_context.data.hourly_points[:24]
    )
