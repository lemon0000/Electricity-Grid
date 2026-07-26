from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_multi_poi_ac_replay import _load_candidate_dispatch
from experiments.run_rts_gmlc_multi_poi_ac_replay_timezone_amended import (
    _amended_context,
    _read_config,
)

AMENDMENT_PATH = Path(
    "configs/rts_gmlc_google_day0_multi_poi_ac_replay_timezone_amendment.yaml"
)
PARENT_CONFIG = Path("configs/rts_gmlc_google_day0_multi_poi_ac_replay.yaml")


def test_timezone_amendment_is_limited_to_timestamp_representation():
    config = _read_config(AMENDMENT_PATH)

    assert not config["observed_before_amendment"]["batch_ac_case_outcomes_observed"]
    assert config["scope"]["permitted_change"] == (
        "replace_mapped_grid_point_timestamp_with_same_instant_parent_business_"
        "timestamp"
    )
    assert "grid_point_numerical_fields" in config["scope"]["forbidden_changes"]
    assert "result_acceptance_or_summary_rules" in config["scope"]["forbidden_changes"]


def test_timezone_amendment_rejects_numerical_scope_creep(tmp_path):
    config = yaml.safe_load(AMENDMENT_PATH.read_text(encoding="utf-8"))
    config["scope"]["forbidden_changes"].remove("grid_point_numerical_fields")
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="scope drifted"):
        _read_config(path)


def test_timezone_amendment_matches_parent_keys_without_changing_grid_values():
    context = _amended_context(PARENT_CONFIG)
    dispatch = _load_candidate_dispatch(context, 120)
    normalized = context.scan_context.business.points
    original = context.scan_context.data.hourly_points[:24]

    assert {point.timestamp.isoformat() for point in normalized} == set(
        dispatch.timestamps
    )
    for changed, source in zip(normalized, original):
        assert changed.timestamp.replace(tzinfo=None) == source.timestamp
        assert changed.demand_by_bus_mw == source.demand_by_bus_mw
        assert changed.generator_min_mw == source.generator_min_mw
        assert changed.generator_max_mw == source.generator_max_mw
        assert (
            changed.spin_up_requirement_by_area_mw
            == source.spin_up_requirement_by_area_mw
        )
