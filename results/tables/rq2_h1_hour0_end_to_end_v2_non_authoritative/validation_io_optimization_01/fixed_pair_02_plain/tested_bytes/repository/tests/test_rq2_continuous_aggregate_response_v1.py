from dataclasses import replace
from fractions import Fraction as Q

import pytest

from test_rq2_continuous_partial_response_v1 import rejected
from src.rq2_joint_deliverability_boundary_v1.aggregate_response import (
    DeclaredAggregateResponse as Action,AggregateResponseRecord,_evaluate_aggregate,
)


def record(action):
    cursor,r = rejected()
    return AggregateResponseRecord(cursor.execution,r,action,*_evaluate_aggregate(cursor.execution,r,action))


def test_fraction_response_has_no_lossy_projection_or_false_lost_work():
    q = Q(1,4)+Q(1,7)
    result = record(Action(Q(1,4),Q(1,7),Q(0),1-q))
    assert result.committed
    assert result.candidate_step.cursor.tracks[0][1].ledger.debt == q
    assert result.cfe_shortfall == Q(1,2)-Q(1,7)
    assert result.observation.hour.cfe_request == .5
    assert result.candidate_step.hour.cfe_request == Q(1,7)


def test_tiny_served_component_is_not_dropped_when_aggregate_active():
    result = record(Action(Q('.25'),Q('1e-8'),Q(0),Q('.75')-Q('1e-8')))
    assert result.committed
    assert result.candidate_step.cursor.tracks[0][1].ledger.debt == Q('.25000001')
    assert result.cfe_shortfall == Q('.49999999')


@pytest.mark.parametrize('field',['grid_served','cfe_served','recovery','actual_service_power'])
def test_exact_interface_rejects_float_fields(field):
    values = dict(grid_served=Q('.25'),cfe_served=Q('.25'),recovery=Q(0),actual_service_power=Q('.5'))
    with pytest.raises(ValueError,match='exact nonnegative Fraction'):
        Action(**dict(values,**{field:float(values[field])}))


@pytest.mark.parametrize('action',[
    Action(Q('.3'),Q('.2'),Q(0),Q('.5')),
    Action(Q('.25'),Q('.25'),Q(0),Q('.25')),
    Action(Q('.25'),Q('.5'),Q(0),Q('.25')),
    Action(Q('1e-6'),Q(0),Q(0),1-Q('1e-6')),
    Action(Q('.25'),Q('.25'),Q('.1'),Q('.6'),((1,Q('.08')),)),
    Action(Q('.25'),Q('.25'),Q('1e-7'),Q('.5000001')),
    Action(Q('.25'),Q('.25'),Q(0),Q('.5000001')),
    Action(Q(0),Q(0),Q('1e-7'),Q('1.0000001')),
])
def test_invalid_exact_actions_never_commit(action):
    result = record(action)
    assert not result.committed and result.candidate_step is None
    assert result.grid_service_failure is None


def test_grid_shortfall_is_only_candidate_and_original_record_is_bound():
    result = record(Action(Q('.125'),Q('.125'),Q(0),Q('.75')))
    assert result.candidate_step is not None and not result.committed
    assert result.grid_service_failure is True
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(result,grid_shortfall=Q(0))
