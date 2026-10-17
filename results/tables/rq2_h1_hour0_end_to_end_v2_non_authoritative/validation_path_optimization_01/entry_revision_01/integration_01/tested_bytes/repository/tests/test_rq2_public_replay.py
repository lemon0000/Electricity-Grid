from __future__ import annotations

import pytest

from src.scenarios.rq2_public_replay import (
    ParameterCell,
    TemporalBlock,
    envelope_for_cell,
    execute_causal_grid_first_policy,
    expand_parameter_cells,
    pair_scenario,
    select_weighted_quantile_representatives,
    training_model_inputs,
)


def _block(
    block_id: str,
    probability: float,
    *,
    split: str = "training",
    grid: tuple[float, ...] = (),
    cfe: tuple[float, ...] = (),
    workload: tuple[float, ...] = (),
) -> TemporalBlock:
    return TemporalBlock(
        block_id=block_id,
        split=split,
        probability=probability,
        first_source_hour=0,
        grid_need=grid,
        cfe_call=cfe,
        workload=workload,
    )


def _cell() -> ParameterCell:
    return ParameterCell(
        cell_id="base",
        varied_dimension="base",
        flexible_fraction=0.2,
        recovery_efficiency=1.0,
        normalized_recovery_headroom=0.1,
        maximum_event_duration_hours=4.0,
        maximum_event_count=2,
        normalized_energy_budget=1.0,
        normalized_debt_limit=1.0,
    )


def _config() -> dict:
    return {
        "fixed_policy": {
            "minimum_recovery_hours": 1.0,
            "minimum_event_power": 1.0e-6,
            "response_time_hours": 1.0,
            "curtailment_ramp_per_hour": 1.0,
            "maximum_flexibility_budget": 1.0,
        }
    }


def test_weighted_representatives_reassign_all_probability_mass():
    blocks = (
        _block("p0", 0.1, grid=(0.0,), cfe=(0.0,)),
        _block("p1", 0.2, grid=(0.2,), cfe=(0.0,)),
        _block("p2", 0.3, grid=(0.4,), cfe=(0.0,)),
        _block("p3", 0.4, grid=(0.8,), cfe=(0.0,)),
    )

    selected = select_weighted_quantile_representatives(
        blocks,
        2,
        role="power",
    )

    assert len(selected) == 2
    assert sum(block.probability for block in selected) == pytest.approx(1.0)
    assert {block.block_id for block in selected}.issubset(
        {block.block_id for block in blocks}
    )


def test_parameter_grid_is_one_factor_at_a_time_with_one_base_cell():
    base = {
        "flexible_fraction": 0.2,
        "recovery_efficiency": 0.85,
        "normalized_recovery_headroom": 0.1,
        "maximum_event_duration_hours": 4,
        "maximum_event_count": 2,
        "normalized_energy_budget": 0.4,
        "normalized_debt_limit": 0.2,
    }
    config = {
        "registered_cells": {
            "base": base,
            "levels": {
                name: [value, value + 1] for name, value in base.items()
            },
        }
    }

    cells = expand_parameter_cells(config)

    assert len(cells) == 8
    assert sum(cell.varied_dimension == "base" for cell in cells) == 1
    assert all(
        sum(
            getattr(cell, name) != value
            for name, value in base.items()
        )
        <= 1
        for cell in cells
    )


def test_pair_scenario_uses_workload_only_as_availability_shape():
    power = _block(
        "power",
        0.5,
        grid=(0.1, 0.3, 0.0),
        cfe=(0.9, 0.1, 0.5),
    )
    workload = _block(
        "workload",
        0.25,
        workload=(0.5, 1.5, 0.0),
    )

    scenario = pair_scenario(power, workload, _cell(), name="pair")

    assert scenario.probability == pytest.approx(0.125)
    assert scenario.grid_need_mw == (0.1, 0.3, 0.0)
    assert scenario.available_flexibility_mw == pytest.approx((0.1, 0.2, 0.0))
    assert scenario.green_call_mw == pytest.approx((0.1, 0.1, 0.0))
    assert scenario.recovery_headroom_mw == pytest.approx((0.05, 0.0, 0.1))
    assert scenario.connected_demand_mw == (1.0, 1.0, 1.0)


def test_pair_scenario_rejects_cross_split_pairing():
    power = _block("power", 1.0, grid=(0.0,), cfe=(0.0,))
    workload = _block(
        "workload",
        1.0,
        split="holdout",
        workload=(1.0,),
    )

    with pytest.raises(ValueError, match="same split"):
        pair_scenario(power, workload, _cell(), name="pair")


def test_training_cartesian_probabilities_sum_to_one():
    power = (
        _block("p0", 0.25, grid=(0.0,), cfe=(0.1,)),
        _block("p1", 0.75, grid=(0.1,), cfe=(0.1,)),
    )
    workload = (
        _block("w0", 0.4, workload=(0.5,)),
        _block("w1", 0.6, workload=(1.0,)),
    )

    inputs = training_model_inputs(power, workload, _cell(), _config())

    assert len(inputs.scenarios) == 4
    assert sum(item.probability for item in inputs.scenarios) == pytest.approx(1.0)
    assert {item.name for item in inputs.scenarios} == {
        "train__p0__w0",
        "train__p0__w1",
        "train__p1__w0",
        "train__p1__w1",
    }


def test_causal_grid_first_policy_serves_without_future_reoptimization():
    power = _block(
        "power",
        1.0,
        split="holdout",
        grid=(0.0, 0.0, 0.0, 0.0),
        cfe=(0.1, 0.0, 0.0, 0.0),
    )
    workload = _block(
        "workload",
        1.0,
        split="holdout",
        workload=(1.0, 0.0, 0.0, 0.0),
    )
    scenario = pair_scenario(power, workload, _cell(), name="pair")

    outcome = execute_causal_grid_first_policy(
        scenario,
        envelope_for_cell(_cell(), policy=_config()["fixed_policy"]),
        0.2,
        service_shortfall_tolerance=1.0e-6,
    )

    assert outcome.resolved
    assert not outcome.hard_grid_failure
    assert not outcome.physical_policy_failure
    assert not outcome.service_shortfall_failure
    assert outcome.green_served == pytest.approx((0.1, 0.0, 0.0, 0.0))
    assert outcome.access_shortfall == pytest.approx(0.0)


def test_causal_policy_capacity_shortfall_is_deterministic():
    power = _block(
        "power",
        1.0,
        split="holdout",
        grid=(0.0, 0.0),
        cfe=(0.1, 0.0),
    )
    workload = _block(
        "workload",
        1.0,
        split="holdout",
        workload=(1.0, 0.0),
    )
    cell = _cell()
    scenario = pair_scenario(power, workload, cell, name="pair")

    outcome = execute_causal_grid_first_policy(
        scenario,
        envelope_for_cell(cell, policy=_config()["fixed_policy"]),
        0.05,
        service_shortfall_tolerance=1.0e-6,
    )

    assert outcome.service_shortfall_failure
    assert outcome.green_served == pytest.approx((0.05, 0.0))
    assert outcome.access_shortfall == pytest.approx(0.05)


def test_causal_policy_first_action_does_not_depend_on_future_requests():
    workload = _block(
        "workload",
        1.0,
        split="holdout",
        workload=(1.0, 1.0, 0.0),
    )
    outcomes = []
    for future_call in (0.0, 0.2):
        power = _block(
            f"power_{future_call}",
            1.0,
            split="holdout",
            grid=(0.0, 0.0, 0.0),
            cfe=(0.1, future_call, 0.0),
        )
        scenario = pair_scenario(power, workload, _cell(), name="pair")
        outcomes.append(
            execute_causal_grid_first_policy(
                scenario,
                envelope_for_cell(
                    _cell(),
                    policy=_config()["fixed_policy"],
                ),
                0.2,
                service_shortfall_tolerance=1.0e-6,
            )
        )

    assert outcomes[0].green_served[0] == pytest.approx(0.1)
    assert outcomes[1].green_served[0] == pytest.approx(0.1)


def test_mandatory_grid_call_above_available_flexibility_is_hard_failure():
    power = _block(
        "power",
        1.0,
        split="holdout",
        grid=(0.3, 0.0),
        cfe=(0.0, 0.0),
    )
    workload = _block(
        "workload",
        1.0,
        split="holdout",
        workload=(1.0, 0.0),
    )
    cell = _cell()
    outcome = execute_causal_grid_first_policy(
        pair_scenario(power, workload, cell, name="pair"),
        envelope_for_cell(cell, policy=_config()["fixed_policy"]),
        0.2,
        service_shortfall_tolerance=1.0e-6,
    )

    assert outcome.hard_grid_failure
    assert outcome.physical_policy_failure


def test_terminal_interevent_recovery_requirement_fails_closed():
    power = _block(
        "power",
        1.0,
        split="holdout",
        grid=(0.0, 0.0),
        cfe=(0.1, 0.0),
    )
    workload = _block(
        "workload",
        1.0,
        split="holdout",
        workload=(1.0, 0.0),
    )
    cell = _cell()
    policy = dict(_config()["fixed_policy"])
    policy["minimum_recovery_hours"] = 2.0
    outcome = execute_causal_grid_first_policy(
        pair_scenario(power, workload, cell, name="pair"),
        envelope_for_cell(cell, policy=policy),
        0.2,
        service_shortfall_tolerance=1.0e-6,
    )

    assert not outcome.hard_grid_failure
    assert outcome.physical_policy_failure
    assert "policy_terminal_recovery_incomplete" in outcome.physical_violations
