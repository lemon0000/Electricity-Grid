from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from experiments.run_rts_gmlc_multi_poi_scan import (
    _build_scan_context,
    _read_scan_config,
    _select_representatives,
    prepare_preregistration,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

CONFIG_PATH = Path("configs/rts_gmlc_google_day0_multi_poi_scan.yaml")
UPSTREAM_ROOT = Path("data/raw/rts_gmlc/v0.2.3/upstream")


requires_upstream = pytest.mark.skipif(
    not UPSTREAM_ROOT.exists(),
    reason="Run scripts/fetch_rts_gmlc.ps1 before the native multi-POI tests",
)


def test_multi_poi_config_freezes_the_candidate_and_comparison_protocols():
    config = _read_scan_config(CONFIG_PATH)

    assert config["candidate_design"]["candidate_order"] == [
        108,
        120,
        208,
        220,
        308,
        320,
    ]
    assert not config["preregistration"]["all_candidates_blind"]
    assert config["preregistration"]["legacy_seen_anchor_bus"] == 108
    assert not config["security_protocol"]["permit_post_prescreen_state_deletion"]
    assert config["comparison"]["completion_policy"] == (
        "all_candidates_required_no_replacement"
    )


def test_multi_poi_config_rejects_candidate_substitution(tmp_path):
    config = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    config["candidate_design"]["candidate_order"][-1] = 319
    path = tmp_path / "substituted.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="candidate_design contract drifted"):
        _read_scan_config(path)


@requires_upstream
def test_candidate_rule_reproduces_the_balanced_two_by_three_design():
    context = _build_scan_context(CONFIG_PATH)
    candidates = context.candidates

    assert tuple(item["dc_bus"] for item in candidates) == (
        108,
        120,
        208,
        220,
        308,
        320,
    )
    assert tuple(item["incident_ac_branch_count"] for item in candidates) == (
        3,
        4,
        3,
        4,
        3,
        4,
    )
    assert tuple(item["incident_continuous_rating_sum_mw"] for item in candidates) == (
        525.0,
        2000.0,
        525.0,
        2000.0,
        525.0,
        2000.0,
    )
    assert candidates[0]["legacy_seen_anchor"]
    assert all(not item["legacy_seen_anchor"] for item in candidates[1:])
    assert candidates[4]["colocated_generator_uids"] == ("308_RTPV_1",)
    assert len(candidates[5]["colocated_generator_uids"]) == 7
    assert set(context.registration_contract["implementation_sha256"]) >= {
        "experiments/run_rts_gmlc_multi_poi_scan.py",
        "src/grid/rts_gmlc_scuc.py",
    }
    assert len(context.registration_contract_sha256) == 64


@requires_upstream
def test_preregistration_is_idempotent_and_snapshots_the_live_contract(tmp_path):
    output = tmp_path / "scan"

    first = prepare_preregistration(CONFIG_PATH, output_directory=output)
    second = prepare_preregistration(CONFIG_PATH, output_directory=output)

    assert first == second
    assert common_input_signature_sha256(first["contract"]) == first["contract_sha256"]
    assert (output / "preregistration" / "scan_config.yaml").read_bytes() == (
        CONFIG_PATH.read_bytes()
    )
    assert (output / "preregistration" / "SHA256SUMS").is_file()


def _comparison_rows():
    return [
        {
            "candidate_order": 0,
            "dc_bus": 108,
            "lower_bound_usd": 99.0,
            "upper_bound_usd": 101.0,
            "stress_metric": 0.80,
        },
        {
            "candidate_order": 1,
            "dc_bus": 120,
            "lower_bound_usd": 100.5,
            "upper_bound_usd": 100.8,
            "stress_metric": 0.75,
        },
        {
            "candidate_order": 2,
            "dc_bus": 208,
            "lower_bound_usd": 105.0,
            "upper_bound_usd": 106.0,
            "stress_metric": 0.95,
        },
    ]


def test_representative_rule_does_not_call_an_overlapping_cost_rank_unique():
    selected = _select_representatives(
        _comparison_rows(),
        tolerance_usd=1.0e-6,
        legacy_anchor_bus=108,
    )

    assert selected["numerical_minimum_upper_bound_bus"] == 120
    assert not selected["certified_unique_minimum"]
    assert selected["certified_overlap_bus_ids"] == [108, 120]
    assert selected["primary_cost_representative_bus"] == 108
    assert selected["maximum_stress_representative_bus"] == 208
    assert selected["ac_representative_bus_ids"] == [108, 208]


def test_representative_rule_reports_a_separated_unique_minimum():
    rows = deepcopy(_comparison_rows())
    rows[1]["lower_bound_usd"] = 90.0
    rows[1]["upper_bound_usd"] = 91.0
    selected = _select_representatives(
        rows,
        tolerance_usd=1.0e-6,
        legacy_anchor_bus=108,
    )

    assert selected["certified_unique_minimum"]
    assert selected["primary_cost_representative_bus"] == 120
    assert selected["ac_representative_bus_ids"] == [120, 208, 108]
