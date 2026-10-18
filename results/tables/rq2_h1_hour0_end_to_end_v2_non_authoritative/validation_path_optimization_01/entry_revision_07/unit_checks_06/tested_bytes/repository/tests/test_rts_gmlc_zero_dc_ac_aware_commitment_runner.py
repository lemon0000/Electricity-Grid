from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment as runner


def _candidate(
    requested_id: str,
    *,
    commitment_sha256: str,
    cost: float,
    delta: float,
) -> runner._Candidate:
    commitment = ({"g1": True},)
    return runner._Candidate(
        requested_candidate_id=requested_id,
        source="test",
        relative_cost_budget_delta=delta,
        cost_budget_usd=200.0,
        operating_cost_usd=cost,
        reactive_proxy_fraction=0.5,
        commitment_sha256=commitment_sha256,
        dispatch_sha256=f"dispatch-{requested_id}",
        commitment=commitment,
        startup=({"g1": False},),
        shutdown=({"g1": False},),
        generation_mw=({"g1": 10.0},),
        branch_flows_mw=({"b1": 1.0},),
        dc_flows_mw=({"d1": 0.0},),
        reserve_up_mw=({"g1": 1.0},),
        stage_audits={},
        residual_audit={},
    )


def test_config_freezes_nonadaptive_official_envelope() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml")
    )

    assert config["candidate_frontier"]["relative_cost_budget_deltas"] == [
        0.001,
        0.0025,
        0.005,
        0.01,
        0.02,
        0.05,
    ]
    assert config["joint_ac"]["voltage_limits_pu"] == [0.95, 1.05]
    assert config["joint_ac"]["voltage_bound_expansion_pu"] == 0.0
    assert config["joint_ac"]["reactive_power_bound_expansion_mvar"] == 0.0
    assert config["joint_ac"]["branch_rate_multiplier"] == 1.0
    assert not any(config["forbidden_adaptivity"].values())


def test_config_rejects_manual_failed_hours(tmp_path: Path) -> None:
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    config["forbidden_adaptivity"]["manual_failed_hours_allowed"] = True
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="forbidden adaptivity"):
        runner._read_config(path)


def test_config_rejects_reserve_scope_drift(tmp_path: Path) -> None:
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    config["joint_ac"]["reserve_eligible_categories"] = ["Coal"]
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="joint AC contract"):
        runner._read_config(path)


def test_joint_csv_schemas_have_unique_fields() -> None:
    schemas = (
        runner._JOINT_RUN_FIELDS,
        runner._JOINT_HOUR_FIELDS,
        runner._JOINT_GENERATOR_FIELDS,
        runner._JOINT_BUS_FIELDS,
        runner._JOINT_BRANCH_FIELDS,
        runner._JOINT_RESERVE_FIELDS,
    )

    assert all(len(fields) == len(set(fields)) for fields in schemas)


def test_csv_round_trip_preserves_dispatch_hash(tmp_path: Path) -> None:
    generation = ({"g1": float.fromhex("0x1.0000000000001p+0")},)
    branches = ({"b1": float.fromhex("0x1.0000000000001p-1")},)
    dc_flows = ({"d1": float.fromhex("0x1.0000000000001p-2")},)
    expected_hash = runner._dispatch_sha256(generation, branches, dc_flows)
    timestamp = "2020-01-01T00:00:00+00:00"
    runner._write_csv(
        tmp_path / "generation.csv",
        runner._GENERATION_FIELDS,
        [
            {
                "candidate_id": "candidate_00",
                "hour_index": 0,
                "timestamp": timestamp,
                "generator_uid": "g1",
                "generation_mw": generation[0]["g1"],
            }
        ],
    )
    runner._write_csv(
        tmp_path / "branches.csv",
        runner._BRANCH_FIELDS,
        [
            {
                "candidate_id": "candidate_00",
                "hour_index": 0,
                "timestamp": timestamp,
                "branch_uid": "b1",
                "flow_mw": branches[0]["b1"],
            }
        ],
    )
    runner._write_csv(
        tmp_path / "dc.csv",
        runner._DC_FLOW_FIELDS,
        [
            {
                "candidate_id": "candidate_00",
                "hour_index": 0,
                "timestamp": timestamp,
                "dc_branch_uid": "d1",
                "flow_mw": dc_flows[0]["d1"],
            }
        ],
    )

    loaded_generation = runner._csv_rows(
        tmp_path / "generation.csv", runner._GENERATION_FIELDS
    )
    loaded_branches = runner._csv_rows(tmp_path / "branches.csv", runner._BRANCH_FIELDS)
    loaded_dc = runner._csv_rows(tmp_path / "dc.csv", runner._DC_FLOW_FIELDS)
    observed_hash = runner._dispatch_sha256(
        ({"g1": float(loaded_generation[0]["generation_mw"])},),
        ({"b1": float(loaded_branches[0]["flow_mw"])},),
        ({"d1": float(loaded_dc[0]["flow_mw"])},),
    )

    assert observed_hash == expected_hash


def test_boolean_transitions_use_one_frozen_initial_state() -> None:
    commitment = (
        {"g1": False, "g2": True},
        {"g1": True, "g2": True},
        {"g1": True, "g2": False},
    )

    startup, shutdown = runner._boolean_transitions(
        commitment, {"g1": False, "g2": False}
    )

    assert startup == (
        {"g1": False, "g2": True},
        {"g1": True, "g2": False},
        {"g1": False, "g2": False},
    )
    assert shutdown == (
        {"g1": False, "g2": False},
        {"g1": False, "g2": False},
        {"g1": False, "g2": True},
    )


def test_proxy_is_minimum_over_hours_areas_and_both_q_directions() -> None:
    generators = (
        SimpleNamespace(
            uid="g1",
            bus=101,
            unit_type="STEAM",
            enabled=True,
            dispatch_mode="committable",
        ),
        SimpleNamespace(
            uid="s1",
            bus=102,
            unit_type="SYNC_COND",
            enabled=False,
            dispatch_mode="disabled",
        ),
        SimpleNamespace(
            uid="s2",
            bus=201,
            unit_type="SYNC_COND",
            enabled=False,
            dispatch_mode="disabled",
        ),
        SimpleNamespace(
            uid="s3",
            bus=301,
            unit_type="SYNC_COND",
            enabled=False,
            dispatch_mode="disabled",
        ),
    )
    buses = (
        SimpleNamespace(uid=101, area=1),
        SimpleNamespace(uid=102, area=1),
        SimpleNamespace(uid=201, area=2),
        SimpleNamespace(uid=301, area=3),
    )
    points = (
        SimpleNamespace(
            generator_max_mw={uid: 1.0 for uid in ("g1", "s1", "s2", "s3")}
        ),
        SimpleNamespace(
            generator_max_mw={uid: 1.0 for uid in ("g1", "s1", "s2", "s3")}
        ),
    )
    context = SimpleNamespace(
        zero=SimpleNamespace(
            scan=SimpleNamespace(
                data=SimpleNamespace(generators=generators, buses=buses)
            )
        ),
        q_limits_by_uid={
            "g1": (-20.0, 40.0),
            "s1": (-20.0, 40.0),
            "s2": (-10.0, 10.0),
            "s3": (-10.0, 10.0),
        },
        config={"candidate_frontier": {"areas": [1, 2, 3]}},
    )

    value = runner._reactive_proxy_value(
        context,
        points,
        ({"g1": True}, {"g1": False}),
    )

    # Area 1 at hour 2 retains only the synchronous condenser: 40/(40+40)
    # injection and 20/(20+20) absorption. Other area-hour-directions are 1.
    assert value == pytest.approx(0.5)


def test_commitment_dedup_keeps_lowest_cost_then_budget() -> None:
    duplicate_expensive = _candidate(
        "delta_1", commitment_sha256="same", cost=110.0, delta=0.01
    )
    duplicate_winner = _candidate(
        "delta_2", commitment_sha256="same", cost=100.0, delta=0.02
    )
    distinct = _candidate("delta_3", commitment_sha256="other", cost=120.0, delta=0.03)

    rows, selected = runner._deduplicate_candidates(
        (duplicate_expensive, duplicate_winner, distinct)
    )

    assert len(selected) == 2
    row_by_requested = {row["requested_candidate_id"]: row for row in rows}
    assert not row_by_requested["delta_1"]["selected_unique_candidate"]
    assert row_by_requested["delta_1"]["duplicate_of_candidate_id"]
    assert row_by_requested["delta_2"]["selected_unique_candidate"]
    assert row_by_requested["delta_3"]["selected_unique_candidate"]
