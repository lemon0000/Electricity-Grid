from dataclasses import replace
from hashlib import sha256
from fractions import Fraction as Q
import sqlite3
import pytest

from test_rq2_scale_selector_store_v1 import request, LIMIT
from test_rq2_scale_selector_v1 import budget, ACT, SPEC
from test_rq2_hourly_transaction_v1 import source, mapping, audit, make_origin, arm_origin, obs
from src.rq2_joint_deliverability_boundary_v1 import scale_hourly_transaction as tx


def execute(root, req):
    with tx.replay.store.DevelopmentScaleSelectorStore(root, req, max_record_bytes=LIMIT) as owned:
        owned.execute()
    with sqlite3.connect(root/'selector.sqlite3') as db:
        data = db.execute('SELECT payload FROM result WHERE id=1').fetchone()[0]
    return data, dict(expected_sha256=sha256(data).hexdigest(),
        expected_replay_identity=tx.replay.implementation_identity(req), max_record_bytes=LIMIT)


def common(tmp_path):
    req = request()
    inputs = (req.info, req.disclosure, req.before)
    data, pins = execute(tmp_path/'reference_non_authoritative', req)
    publication = tx.publish_common_record(data, req, source(inputs, '45'), mapping('45'), audit(req.info),
        limits=obs(1, g=0., c=0., due=None).limits, due_hour=5, available_flexibility=1., **pins)
    return req, publication


def arm(req, pub, arm_id, capacity=1.):
    inputs = (req.info, req.disclosure, req.before)
    old = arm_origin(inputs, make_origin(inputs), arm_id, capacity)
    b = budget('actual:'+str(tx.ARMS.index(arm_id)))
    physical = old.grid.physical_origin
    grid = tx.replay.scale.initialize_actual_origin(req.info, physical.disclosure,
        grid_protocol=physical.protocol, generation_mw=physical.generation_mw,
        base_availability=physical.base_availability, selector=ACT, solver_specification=SPEC, budget=b,
        expected_policy_identity=tx.replay.scale.policy_identity(ACT, SPEC, b))
    return tx.initialize_arm(pub, old.business, grid), b


@pytest.mark.parametrize('arm_id', tx.ARMS)
def test_four_roles_replayed_business_grid_pair(tmp_path, arm_id):
    req, pub = common(tmp_path)
    before, b = arm(req, pub, arm_id)
    pending = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=b)
    data, pins = execute(tmp_path/'actual_non_authoritative', pending.dispatch_request)
    result = tx.finish_arm(pending, data, **pins)
    assert pub.current.observation.hour.grid_request == Q(1, 3)
    if arm_id == tx.CFE:
        assert result['status'] == 'physical_network_unresolved'
        assert result['published_pair'] is None and result['cursor'].halted
        assert result['cursor'].business == before.business
        assert not result['grid_service_applicable']
        assert result['grid_service_failure'] is result['candidate_grid_service_failure'] is None
    else:
        assert result['status'] == 'committed'
        cursor = result['cursor']
        assert cursor.business.execution.tracks[0][1].ledger.debt == Q(1, 3)
        assert cursor.grid.physical_carry.generation_mw == (('G1', 30.),)
        assert result['published_pair'] == (cursor.business, cursor.grid)
    assert not result['formal_result']


def test_wrong_role_and_repeated_publication_rejected(tmp_path):
    req, pub = common(tmp_path)
    before, b = arm(req, pub, tx.JOINT)
    with pytest.raises(ValueError, match='canonical business arm'):
        tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=replace(b, role='actual:0'))
    proposal = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=b)
    data, pins = execute(tmp_path/'actual_non_authoritative', proposal.dispatch_request)
    result = tx.finish_arm(proposal, data, **pins)
    with pytest.raises(ValueError, match='chain'):
        tx.prepare_arm(result['cursor'], pub, selector=ACT, solver_specification=SPEC, budget=b)


def test_business_rejection_preserves_both_states(tmp_path):
    req, pub = common(tmp_path)
    before, b = arm(req, pub, tx.JOINT, .125)
    proposal = tx.prepare_arm(before, pub, selector=ACT, solver_specification=SPEC, budget=b)
    assert proposal.dispatch_request is None
    result = tx.finish_arm(proposal)
    assert result['status'] == 'business_rejected'
    assert result['cursor'].business == before.business and result['cursor'].grid == before.grid
    assert result['cursor'].halted and result['published_pair'] is None
    assert result['candidate_grid_service_failure'] is True and result['grid_service_failure'] is None


def test_same_arm_policy_swap_rejected_before_business_advance(tmp_path, monkeypatch):
    req, pub = common(tmp_path)
    before, b = arm(req, pub, tx.JOINT)
    different, _ = arm(req, pub, tx.JOINT, .125)
    assert before.business.policy_id != different.business.policy_id
    changed = tx._owned(tx.ArmCursor, **dict(vars(before), business=different.business))
    def forbidden(*args, **kwargs): raise AssertionError('changed policy reached business advance')
    monkeypatch.setattr(tx.legacy, 'advance_capacity_policy', forbidden)
    with pytest.raises(ValueError, match='chain'):
        tx.prepare_arm(changed, pub, selector=ACT, solver_specification=SPEC, budget=b)


@pytest.mark.parametrize('recovery', [False, True])
def test_two_hour_chain_preserves_or_repays_debt(tmp_path, recovery):
    from types import SimpleNamespace
    from test_rq2_hourly_transaction_v1 import next_hour
    req, first = common(tmp_path)
    before, b = arm(req, first, tx.JOINT)
    pending = tx.prepare_arm(before, first, selector=ACT, solver_specification=SPEC, budget=b)
    data, pins = execute(tmp_path/'first_actual_non_authoritative', pending.dispatch_request)
    active = tx.finish_arm(pending, data, **pins)['cursor']
    info, disclosure = next_hour(SimpleNamespace(reference_state=first.reference_result.next_state),
        demand=0. if recovery else 20., cap=30. if recovery else 25.)
    inputs = (info, disclosure, first.reference_result.next_state)
    ref_budget = replace(req.budget, source_hour=2)
    second_request = replace(req, info=info, disclosure=disclosure, before=inputs[2], budget=ref_budget,
        expected_identity=tx.replay.scale.reference.reference_input_identity(*inputs))
    data, pins = execute(tmp_path/'second_reference_non_authoritative', second_request)
    hour = replace(source(inputs, '45'), power_source_hour=2, workload_source_hour=102)
    limits = first.current.observation.limits
    if recovery:
        limits = replace(limits, business_recovery_headroom=Q(1,45),
            cfe_compatible_surplus=Q(1,45), maximum_recovery_power=Q(1,45))
    second = tx.publish_common_record(data, second_request, hour, first.mapping, audit(info),
        previous=first, limits=limits, due_hour=None if recovery else 5, available_flexibility=1., **pins)
    pending = tx.prepare_arm(active, second, selector=ACT, solver_specification=SPEC, budget=replace(b, source_hour=2))
    data, pins = execute(tmp_path/'second_actual_non_authoritative', pending.dispatch_request)
    result = tx.finish_arm(pending, data, **pins)
    assert result['status'] == 'committed'
    assert result['cursor'].grid.physical_carry.source_hour == 2
    debt = result['cursor'].business.execution.tracks[0][1].ledger.debt
    assert debt < Q(1,3) if recovery else debt == Q(2,3)
    if recovery: assert 25 < pending.dispatch_request.power.exact_mw <= 26
    assert active.business.execution.tracks[0][1].ledger.debt == Q(1,3)
    assert result['cursor'].origin_identity == before.origin_identity
    assert result['cursor'].business_policy_identity == before.business_policy_identity
    assert second.previous_identity == first.identity
