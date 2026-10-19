from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from decimal import Decimal
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1 import continuation_audit as audit
from src.rq2_joint_deliverability_boundary_v1.continuation_audit import (
    audit_continuation_availability,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_joint_deliverability_continuation_audit_v1.DRAFT.yaml"


@pytest.fixture(scope="module")
def audit_result() -> dict[str, object]:
    return audit_continuation_availability(CONFIG)


def _config() -> dict[str, object]:
    return yaml.safe_load(CONFIG.read_text(encoding="utf-8"))


def test_frozen_packages_have_exact_intrasplit_chains(
    audit_result: dict[str, object],
) -> None:
    summary = audit_result["summary"]
    power = summary["power_chronology"]
    assert power["row_count"] == 25704
    assert power["chain_count"] == 6
    assert power["hourly_source_and_timestamp_link_count"] == 25698
    assert power["active_event_change_link_count"] == 864
    assert power["block_boundary_links_by_split"] == {
        "training": 538,
        "holdout": 527,
    }
    workload = summary["workload_chronology"]
    assert workload["row_count"] == 1632
    assert workload["chain_count"] == 2
    assert workload["hourly_source_link_count"] == 1630
    assert workload["block_boundary_links_by_split"] == {
        "training": 33,
        "holdout": 33,
    }
    assert summary["potential_marginal_pair_adjacency"] == {
        "training": 17754,
        "holdout": 17391,
        "interpretation": "unregistered_cartesian_marginal_adjacency_only",
    }


def test_power_chain_ranges_and_cross_split_gaps_are_explicit(
    audit_result: dict[str, object],
) -> None:
    chains = {
        (item["split"], item["outage_seed"]): item
        for item in audit_result["chains"]["power"]
    }
    expected = {
        ("training", 20260822): (181, 0, 4343, (4344, 4391, 48), 180),
        ("training", 20260823): (180, 0, 4319, (4320, 4391, 72), 179),
        ("training", 20260824): (180, 0, 4319, (4320, 4391, 72), 179),
        ("holdout", 20260822): (181, 4440, 8783, (4392, 4439, 48), 180),
        ("holdout", 20260823): (176, 4560, 8783, (4392, 4559, 168), 175),
        ("holdout", 20260824): (173, 4632, 8783, (4392, 4631, 240), 172),
    }
    for key, (blocks, start, end, missing, links) in expected.items():
        chain = chains[key]
        assert (chain["block_count"], chain["source_start"], chain["source_end"]) == (
            blocks,
            start,
            end,
        )
        assert chain["block_boundary_link_count"] == links
        interval = chain["unavailable_in_frozen_margin"]
        assert len(interval) == 1
        assert chain["unavailable_in_frozen_margin_reason"] == (
            "whole_blocks_touching_cross_split_outage_event_excluded"
        )
        assert (
            interval[0]["start"],
            interval[0]["end_inclusive"],
            interval[0]["hour_count"],
        ) == missing
    assert audit_result["summary"]["cross_split_continuation_link_count"] == 0


def test_workload_ranges_and_training_normalization_are_preserved_raw(
    audit_result: dict[str, object],
) -> None:
    chains = {item["split"]: item for item in audit_result["chains"]["workload"]}
    assert (chains["training"]["source_start"], chains["training"]["source_end"]) == (
        0,
        815,
    )
    assert chains["training"]["unavailable_in_frozen_margin"] == [
        {"start": 816, "end_inclusive": 820, "hour_count": 5, "position": "trailing"}
    ]
    assert chains["training"]["unavailable_in_frozen_margin_reason"] == (
        "incomplete_terminal_block_dropped"
    )
    assert (chains["holdout"]["source_start"], chains["holdout"]["source_end"]) == (
        821,
        1636,
    )
    assert chains["holdout"]["unavailable_in_frozen_margin"] == [
        {
            "start": 1637,
            "end_inclusive": 1641,
            "hour_count": 5,
            "position": "trailing",
        }
    ]
    workload = audit_result["summary"]["workload_chronology"]
    assert workload["normalization_identity_verified_for_every_row"] is True
    assert workload["raw_fraction_above_one_hour_count_by_split"] == {
        "training": 0,
        "holdout": 6,
    }
    assert workload["raw_fraction_above_one_block_count_by_split"] == {
        "training": 0,
        "holdout": 3,
    }
    assert workload["raw_fraction_above_one_source_hours"] == {
        "training": [],
        "holdout": [1198, 1206, 1207, 1208, 1209, 1267],
    }
    assert workload["maximum_raw_fraction_by_split"]["holdout"] == (
        "1.070370705271957780430251624"
    )
    assert workload["raw_fraction_was_clipped"] is False


def test_contract_gaps_remain_blocking_not_filled(
    audit_result: dict[str, object],
) -> None:
    summary = audit_result["summary"]
    evidence = summary["contract_evidence"]
    assert evidence["cfe_call_fraction_present"] is True
    assert evidence["workload_occupancy_present"] is True
    for key in (
        "dispatched_grid_need_present",
        "shared_physical_clock_mapping_present",
        "absolute_workload_power_present",
        "flexible_fraction_observed",
        "call_limit_observed",
        "track_compatible_recovery_headroom_observed",
        "maximum_recovery_power_observed",
        "recovery_efficiency_observed",
        "flexibility_event_duration_contract_observed",
        "flexibility_event_count_contract_observed",
        "energy_budget_observed",
        "debt_limit_observed",
        "accounting_period_id_observed",
        "service_deadline_observed",
        "checkpoint_observed",
        "recoverability_observed",
    ):
        assert evidence[key] is False
    assert summary["full_joint_service_continuation_ready"] is False
    assert summary["raw_chronology_candidate_interpretation"] == (
        "within_each_frozen_margin_only_not_joint_service_readiness"
    )
    assert summary["power_outage_trajectory_semantics"] == (
        "sampled_from_published_rate_not_observed"
    )
    assert summary["single_margin_successor_is_sufficient_for_joint_continuation"] is (
        False
    )
    assert summary["formal_result"] is False
    assert summary["solver_calls"] == 0


def test_adjacency_classifier_keeps_split_and_trajectory_identity() -> None:
    blocks = [
        {
            "block_id": "a",
            "split": "training",
            "outage_seed": 1,
            "source_start": 0,
            "source_end": 23,
        },
        {
            "block_id": "b",
            "split": "training",
            "outage_seed": 1,
            "source_start": 24,
            "source_end": 47,
        },
        {
            "block_id": "gap",
            "split": "training",
            "outage_seed": 1,
            "source_start": 72,
            "source_end": 95,
        },
        {
            "block_id": "other_seed",
            "split": "training",
            "outage_seed": 2,
            "source_start": 24,
            "source_end": 47,
        },
        {
            "block_id": "other_split",
            "split": "holdout",
            "outage_seed": 1,
            "source_start": 24,
            "source_end": 47,
        },
    ]
    groups = audit._group_adjacencies(blocks, ("split", "outage_seed"))
    primary = next(group for group in groups if group[0] == ("training", 1))
    assert [(left["block_id"], right["block_id"]) for left, right in primary[2]] == [
        ("a", "b")
    ]
    assert primary[3] == [{"start": 48, "end_inclusive": 71, "hour_count": 24}]
    assert sum(len(group[2]) for group in groups) == 1


def test_adjacency_classifier_rejects_duplicate_or_overlapping_successors() -> None:
    base = {
        "block_id": "a",
        "split": "training",
        "outage_seed": 1,
        "source_start": 0,
        "source_end": 23,
    }
    duplicate = {**base, "block_id": "duplicate"}
    with pytest.raises(ValueError, match="duplicate source start"):
        audit._group_adjacencies([base, duplicate], ("split", "outage_seed"))
    overlap = {
        **base,
        "block_id": "overlap",
        "source_start": 20,
        "source_end": 43,
    }
    with pytest.raises(ValueError, match="overlapping"):
        audit._group_adjacencies([base, overlap], ("split", "outage_seed"))


def test_power_hour_link_rejects_source_or_timestamp_jump() -> None:
    audit._validate_power_hour_link(
        23, 24, "2020-01-01T23:00:00+00:00", "2020-01-02T00:00:00+00:00"
    )
    with pytest.raises(ValueError, match="not consecutive"):
        audit._validate_power_hour_link(
            23, 25, "2020-01-01T23:00:00+00:00", "2020-01-02T01:00:00+00:00"
        )
    with pytest.raises(ValueError, match="not consecutive"):
        audit._validate_power_hour_link(
            23, 24, "2020-01-01T23:00:00+00:00", "2020-01-02T01:00:00+00:00"
        )


def test_outage_state_changes_are_legal_but_type_or_uid_drift_is_rejected() -> None:
    event = {"event_id": "e1", "component_type": "generator", "component_uid": "G1"}
    active = {(1, 24): event}
    before = {
        "outage_seed": "1",
        "source_hour": "23",
        "active_event_id": "",
        "active_component_type": "",
        "active_component_uid": "",
    }
    after = {
        "outage_seed": "1",
        "source_hour": "24",
        "active_event_id": "e1",
        "active_component_type": "generator",
        "active_component_uid": "G1",
    }
    audit._validate_hourly_outage_state(before, active)
    audit._validate_hourly_outage_state(after, active)
    with pytest.raises(ValueError, match="event schedule"):
        audit._validate_hourly_outage_state(
            {**after, "active_component_uid": "G2"}, active
        )


def test_workload_normalization_rejects_drift_and_preserves_above_one() -> None:
    audit._validate_workload_normalization(
        Decimal(11), Decimal("1.1"), Decimal(10)
    )
    with pytest.raises(ValueError, match="training peak"):
        audit._validate_workload_normalization(
            Decimal(11), Decimal(1), Decimal(10)
        )


@pytest.mark.parametrize(
    ("section", "key", "bad_value"),
    [
        ("authority", "may_open_any_execution_gate", True),
        ("authority", "may_modify_predecessor_boundary_diagnostic", True),
        ("audit_contract", "cross_split_links_allowed", True),
        ("audit_contract", "power_and_workload_share_observed_clock", True),
        ("audit_contract", "potential_pair_adjacency_is_registered_coupling", True),
        ("audit_contract", "raw_workload_fraction_may_be_clipped", True),
        ("audit_contract", "dispatched_grid_continuation_audited", True),
        ("audit_contract", "full_joint_service_continuation_ready", True),
        ("audit_contract", "future_contract_parameters_may_be_invented", True),
        ("output", "overwrite_allowed", True),
    ],
)
def test_diagnostic_semantic_gates_fail_closed(
    tmp_path: Path,
    section: str,
    key: str,
    bad_value: object,
) -> None:
    config = deepcopy(_config())
    config[section][key] = bad_value
    path = tmp_path / "mutated.DRAFT.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError):
        audit_continuation_availability(path)


def test_input_hash_drift_is_rejected(tmp_path: Path) -> None:
    config = deepcopy(_config())
    config["inputs"]["power"]["manifest_sha256"] = "0" * 64
    path = tmp_path / "mutated.DRAFT.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    with pytest.raises(ValueError, match="manifest"):
        audit_continuation_availability(path)


def test_runner_is_self_hashing_and_refuses_overwrite(tmp_path: Path) -> None:
    from experiments.audit_rq2_joint_deliverability_continuation_v1 import (
        write_diagnostic,
    )

    output = tmp_path / "diagnostic"
    summary = write_diagnostic(CONFIG, output_override=output)
    assert summary["evidence_level"] == (
        "non_authoritative_zero_solver_raw_continuation_diagnostic"
    )
    manifest = json.loads((output / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert set(manifest) == {"chains.json", "summary.json"}
    for name, expected in manifest.items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    with pytest.raises(FileExistsError):
        write_diagnostic(CONFIG, output_override=output)


def test_predecessor_boundary_artifacts_remain_byte_identical() -> None:
    config = _config()["predecessor_boundary_diagnostic"]
    expected = {
        config["config_path"]: config["config_sha256"],
        config["audit_path"]: config["audit_sha256"],
        config["boundary_path"]: config["boundary_sha256"],
        config["runner_path"]: config["runner_sha256"],
    }
    directory = ROOT / config["result_directory"]
    expected.update(
        {
            str((directory / name).relative_to(ROOT)): digest
            for name, digest in config["result_files"].items()
        }
    )
    for relative, digest in expected.items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == digest
