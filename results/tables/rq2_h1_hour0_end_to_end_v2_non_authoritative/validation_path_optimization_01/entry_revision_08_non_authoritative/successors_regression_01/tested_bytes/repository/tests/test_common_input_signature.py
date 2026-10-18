from copy import deepcopy

import pytest

from src.scenarios.common_input_signature import (
    COMMON_INPUT_SIGNATURE_SCHEMA,
    build_common_input_signature,
    common_input_signature_sha256,
)


def _signature():
    return build_common_input_signature(
        case={"name": "case24_ieee_rts", "source": "pypower"},
        source_package="pypower",
        source_version="test",
        demand_path_source="frozen_path",
        quarters=(
            {
                "name": "q1",
                "system_load_multiplier": 0.8,
                "data_center_demand_mw": 50.0,
                "operating_hours": 2184.0,
                "continuous_validation_hours": 0.0,
                "discount_factor": 1.0,
            },
        ),
        poi={
            "bus": 8,
            "initial_capacity_mw": 50.0,
            "application_capacity_mw": 250.0,
        },
        project={
            "lead_time_quarters": 2,
            "rate_a_increase_mw": {12: 100.0, 11: 100.0},
            "rate_c_increase_mw": {11: 100.0, 12: 100.0},
            "poi_capacity_increase_mw": 200.0,
        },
        service_envelope={"max_conditional_capacity_mw": 75.0},
        service_configuration={
            "max_conditional_capacity_mw": 75.0,
            "continuous_window_status": "not_validated",
        },
        branch_indices=(11, 12),
        generator_indices=(0,),
        immediate_rating="rate_c",
        sustained_rating="rate_a",
        security_configuration={
            "branch_set": "all_non_islanding",
            "generator_set": "all_positive_capacity",
            "excluded_islanding_policy": "report_as_failure",
            "immediate_branch_rating": "rate_c",
            "sustained_rating": "rate_a",
            "redispatch_fraction_pmax": 0.5,
        },
        security_states=(
            {
                "name": "base",
                "branch_rating": "rate_a",
                "outaged_branch_indices": frozenset(),
                "outaged_generator_indices": frozenset(),
                "response_mode": "base",
            },
            {
                "name": "branch_11_sustained",
                "branch_rating": "rate_a",
                "outaged_branch_indices": frozenset((11,)),
                "outaged_generator_indices": frozenset(),
                "response_mode": "bounded",
            },
        ),
        redispatch_up_mw={0: 50.0},
        redispatch_down_mw={0: 50.0},
        objective={
            "planning_objectives": "lexicographic_physical",
            "unit_basis": "mwh",
            "access_shortfall_cost_per_mwh": 250.0,
            "posthoc_cost_scope": "display_only",
        },
        solver={"name": "highs"},
    )


def test_signature_is_canonical_and_contains_all_fair_input_groups():
    signature = _signature()

    assert signature["schema"] == COMMON_INPUT_SIGNATURE_SCHEMA
    assert signature["quarters"][0]["operating_hours"] == 2184.0
    assert signature["quarters"][0]["system_load_multiplier"] == 0.8
    assert signature["quarters"][0]["data_center_demand_mw"] == 50.0
    assert signature["poi"]["initial_capacity_mw"] == 50.0
    assert signature["project"]["rate_a_increase_mw"] == {
        "11": 100.0,
        "12": 100.0,
    }
    assert signature["service_envelope"]["max_conditional_capacity_mw"] == 75.0
    assert signature["security_states"][1]["response_mode"] == "bounded"
    assert signature["redispatch_up_mw"] == {"0": 50.0}
    assert signature["objective"]["planning_objectives"] == (
        "lexicographic_physical"
    )
    assert signature["solver"] == {"name": "highs"}

    reordered = {key: signature[key] for key in reversed(signature)}
    digest = common_input_signature_sha256(signature)
    assert len(digest) == 64
    assert common_input_signature_sha256(reordered) == digest


@pytest.mark.parametrize(
    ("path", "replacement"),
    (
        (("quarters", 0, "operating_hours"), 2000.0),
        (("quarters", 0, "system_load_multiplier"), 0.9),
        (("quarters", 0, "data_center_demand_mw"), 60.0),
        (("poi", "initial_capacity_mw"), 60.0),
        (("project", "poi_capacity_increase_mw"), 190.0),
        (("service_envelope", "max_conditional_capacity_mw"), 70.0),
        (("security_states", 1, "response_mode"), "fixed"),
        (("immediate_rating",), "rate_a"),
        (("redispatch_up_mw", "0"), 40.0),
        (("objective", "planning_objectives"), "economic"),
        (("solver", "name"), "appsi_highs"),
    ),
)
def test_signature_hash_detects_fair_input_drift(path, replacement):
    baseline = _signature()
    changed = deepcopy(baseline)
    target = changed
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = replacement

    assert common_input_signature_sha256(changed) != (
        common_input_signature_sha256(baseline)
    )


def test_signature_rejects_nonfinite_values():
    with pytest.raises(ValueError, match="finite numbers"):
        common_input_signature_sha256({"redispatch_up_mw": {0: float("nan")}})
