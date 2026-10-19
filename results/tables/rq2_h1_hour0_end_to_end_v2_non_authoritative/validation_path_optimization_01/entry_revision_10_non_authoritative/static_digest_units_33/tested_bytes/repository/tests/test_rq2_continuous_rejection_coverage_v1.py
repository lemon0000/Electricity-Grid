"""Additional rejection coverage; all inputs are synthetic mechanism assumptions."""

from dataclasses import replace

import pytest

from test_rq2_continuous_recovery_controller_v1 import init, obs
from src.rq2_joint_deliverability_boundary_v1.actual_actions import ActualActionCursor
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import B6, CFE, JOINT, NETWORK
from src.rq2_joint_deliverability_boundary_v1.recovery_controller import (
    advance_composite_policy,
    summarize_composite_policy,
)


@pytest.mark.parametrize(
    "arm,grid,cfe,baseline,message",
    [
        (NETWORK, .25, 0., .125, "exceeds baseline power"),
        (CFE, 0., .25, .125, "exceeds baseline power"),
        (JOINT, .125, .125, .125, "exceeds baseline power"),
        (B6, .25, 0., .125, "exceeds baseline power"),
        (B6, .125, 6e-7, 1., "effective obligations differ"),
    ],
)
def test_primary_decision_rejection_preserves_state_and_cannot_start_actual_suffix(
    arm, grid, cfe, baseline, message,
):
    # Keep a committed prefix so the check distinguishes last valid time from
    # the submitted but unevaluated rejection hour.
    before = advance_composite_policy(init(arm), obs(1, g=0., c=0.))
    row = obs(2, g=grid, c=cfe, due=5)
    row = replace(row, hour=replace(row.hour, workload_occupancy=baseline))
    stopped = advance_composite_policy(before, row)
    record = stopped.primary.records[-1]

    assert stopped.stopped
    assert record.stage == "policy_decision" and message in record.error
    assert record.observation == row
    assert record.accepted_step is None and record.planned_step is None
    assert stopped.primary.execution == before.primary.execution
    assert stopped.primary.planning == before.primary.planning
    assert stopped.primary.records[:-1] == before.primary.records
    assert stopped.policy_id == before.policy_id
    assert stopped.recovery_records == () and stopped.actual is None

    summary = summarize_composite_policy(stopped)
    assert summary["submitted_unique_hours"] == 2
    assert summary["validated_unique_hours"] == 1
    assert summary["last_validated_hour"] == 1
    assert summary["risk_probability"] is None
    assert summary["formal_result"] is False
    with pytest.raises(ValueError, match="requires separate diagnosis"):
        ActualActionCursor(stopped.primary)
    with pytest.raises(ValueError, match="cannot consume"):
        advance_composite_policy(stopped, obs(3))
