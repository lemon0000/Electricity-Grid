"""Evidence for reuse boundaries; does not enable caching or certificate rebinding."""
from dataclasses import replace
from fractions import Fraction as Q

import pytest

from test_rq2_scale_hourly_transaction_v1 import execute, request, source, mapping, audit, obs, arm
from test_rq2_scale_selector_v1 import ACT, SPEC
from src.rq2_joint_deliverability_boundary_v1 import scale_hourly_transaction as tx


@pytest.fixture(scope='module')
def reference_record(tmp_path_factory):
    req=request()
    data,pins=execute(tmp_path_factory.mktemp('reuse_boundary')/'reference_non_authoritative',req)
    return req,data,pins


def publish(reference_record,**changes):
    req,data,pins=reference_record
    inputs=(req.info,req.disclosure,req.before)
    values=dict(limits=obs(1,g=0.,c=0.,due=None).limits,due_hour=5,available_flexibility=1.)
    cfe=changes.pop('cfe',Q(0))
    values.update(changes)
    return tx.publish_common_record(data,req,source(inputs,'45',cfe),mapping('45'),audit(req.info),**values,**pins)


@pytest.mark.parametrize('changes',[{'cfe':Q(3,20)},{'due_hour':6},{'available_flexibility':.5},
    {'limits':replace(obs(1,g=0.,c=0.,due=None).limits,call_limit=.49)}])
def test_same_reference_evidence_requires_cell_specific_publication(reference_record,monkeypatch,changes):
    def forbidden(*a,**kw): raise AssertionError('publication reran solver')
    monkeypatch.setattr(tx.replay.scale.native,'_solve',forbidden)
    first=publish(reference_record)
    second=publish(reference_record,**changes)
    assert first.reference_result==second.reference_result
    assert first.record_sha256==second.record_sha256
    assert first.current!=second.current
    assert first.identity!=second.identity


@pytest.mark.parametrize('field,value',[('task_id','different_episode'),('resource_contract_identity','b'*64),
    ('max_variables',10001)])
def test_same_physical_input_does_not_authorize_cross_task_record_rebinding(reference_record,field,value):
    req,data,pins=reference_record
    budget=replace(req.budget,**{field:value})
    policy=tx.replay.scale.policy_identity(req.selection_spec,req.solver_specification,budget)
    other=replace(req,budget=budget,expected_policy_identity=policy)
    assert other.expected_identity==req.expected_identity
    assert other.expected_policy_identity!=req.expected_policy_identity
    with pytest.raises(ValueError):
        tx.replay.replay_record(data,other,expected_sha256=pins['expected_sha256'],
            expected_implementation_identity=tx.replay.implementation_identity(other),
            max_record_bytes=pins['max_record_bytes'])


def test_capacity_changes_actual_action_and_dispatch_request(reference_record):
    req,_,_=reference_record
    publication=publish(reference_record,cfe=Q(3,20))
    high,budget=arm(req,publication,tx.JOINT,1.)
    low,_=arm(req,publication,tx.JOINT,.4)
    assert high.grid==low.grid
    assert high.business.policy_id!=low.business.policy_id
    a=tx.prepare_arm(high,publication,selector=ACT,solver_specification=SPEC,budget=budget)
    b=tx.prepare_arm(low,publication,selector=ACT,solver_specification=SPEC,budget=budget)
    assert a.dispatch_request is not None and b.dispatch_request is not None
    assert a.dispatch_request.power!=b.dispatch_request.power
    assert a.dispatch_request.expected_identity!=b.dispatch_request.expected_identity
    assert high.business.records==low.business.records==()


def test_identical_requested_power_still_binds_actual_predecessor():
    from test_rq2_scale_selector_v1 import actual_inputs,budget
    from src.rq2_joint_deliverability_boundary_v1 import scale_selector as scale
    b=budget('actual:0')
    info,disclosure,before,power=actual_inputs(b)
    physical=before.physical_origin
    changed=tuple((uid,value+1.) for uid,value in physical.generation_mw)
    other=scale.initialize_actual_origin(info,physical.disclosure,grid_protocol=physical.protocol,
        generation_mw=changed,base_availability=physical.base_availability,selector=ACT,
        solver_specification=SPEC,budget=b,expected_policy_identity=scale.policy_identity(ACT,SPEC,b))
    assert scale.actual.dispatch_input_identity(info,disclosure,before,power)!=scale.actual.dispatch_input_identity(info,disclosure,other,power)


def test_actual_role_is_part_of_policy_identity_even_with_equal_numeric_limits():
    from test_rq2_scale_selector_v1 import budget
    from src.rq2_joint_deliverability_boundary_v1 import scale_selector as scale
    first=budget('actual:0')
    second=replace(first,role='actual:1')
    assert scale.policy_identity(ACT,SPEC,first)!=scale.policy_identity(ACT,SPEC,second)
