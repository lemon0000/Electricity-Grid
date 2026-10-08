from dataclasses import replace
from fractions import Fraction as Q
from itertools import product

import pytest
import yaml

from test_rq2_continuous_recovery_controller_v1 import ROOT, F, anchor, obs
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK,CFE,JOINT,B6
from src.rq2_joint_deliverability_boundary_v1.capacity_policy_bidirectional import (
    BidirectionalPolicy,BidirectionalObservation,initialize_capacity_policy,
    advance_capacity_policy as advance,_continuous_response,
)

CONFIG = yaml.safe_load((ROOT/'configs/rq2_bidirectional_capacity_policy_v1.DRAFT.yaml').read_text(encoding='utf-8'))
CF = CONFIG['fixture']


def init(arm=JOINT,envelope=None,**changes):
    spec = replace(BidirectionalPolicy.from_config(CONFIG,arm),**changes)
    return initialize_capacity_policy(spec,anchor=anchor(),envelope=F['envelope'] if envelope is None else envelope,
        accounting_period_id='synthetic-period',zero_carry_in_assumption=True)


def current(t,g=0.,c=0.,available=None,**changes):
    return BidirectionalObservation(obs(t,g=g,c=c,due=t+4 if g+c else None,**changes),
                               CF['available_flexibility'] if available is None else available)


def test_analytic_grid_cfe_ramp_and_recovery():
    cursor = init()
    cursor = advance(cursor,current(1,g=.125,c=.25))
    a = cursor.records[-1].response.action
    assert (a.grid_served,a.cfe_served,a.recovery,a.actual_service_power) == (.125,0.,0.,.875)
    assert cursor.records[-1].response.cfe_shortfall == Q('.25')
    cursor = advance(cursor,current(2,g=.125,c=.25))
    a = cursor.records[-1].response.action
    assert (a.grid_served,a.cfe_served) == (.125,.125)
    assert cursor.execution.tracks[0][1].ledger.debt == Q('.375')
    cursor = advance(cursor,current(3))
    assert cursor.records[-1].response.action.recovery == .3125
    cursor = advance(cursor,current(4))
    assert cursor.records[-1].response.action.recovery == .15625
    assert cursor.execution.tracks[0][1].ledger.debt == 0


@pytest.mark.parametrize('arm',[NETWORK,CFE,JOINT,B6])
def test_four_arm_projection_uses_shared_execution(arm):
    cursor = advance(init(arm),current(1,g=.0625,c=.125))
    assert not cursor.stopped and cursor.execution.mode == 'physical_execution'
    a = cursor.records[-1].response.action
    assert a.grid_served == (0. if arm == CFE else .0625)
    assert a.cfe_served == (0. if arm == NETWORK else (.125 if arm == CFE else .0625))
    assert cursor.records[-1].response.observation.hour.cfe_request == .125


def test_grid_shortfall_does_not_commit_or_consume_suffix():
    cursor = init()
    before = cursor.execution
    cursor = advance(cursor,current(1,g=.25,c=.25))
    assert cursor.stopped and cursor.execution == before
    response = cursor.records[-1].response
    assert response.candidate_step is not None and response.grid_service_failure
    assert response.action.grid_served == .125
    with pytest.raises(ValueError,match='cannot consume'):
        advance(cursor,current(2))


@pytest.mark.parametrize('constraint',['capacity','available','call_limit','baseline','response','ramp','minimum'])
def test_each_additional_constraint_binds(constraint):
    changes = dict(curtailment_ramp_per_hour=1.,response_time_hours=1.)
    r = current(1,c=.5,available=.5)
    if constraint == 'capacity': changes['committed_capacity'] = .125
    if constraint == 'available': r = replace(r,available_flexibility=.125)
    if constraint == 'call_limit': r = current(1,c=.5,available=.5,call_limit=.125)
    if constraint == 'baseline':
        r = replace(r,observation=replace(r.observation,hour=replace(r.observation.hour,workload_occupancy=.125)))
    if constraint == 'response': changes['response_time_hours'] = .125
    if constraint == 'ramp': changes['curtailment_ramp_per_hour'] = .125
    if constraint == 'minimum': changes['minimum_event_power'] = .6
    cursor = advance(init(**changes),r)
    assert not cursor.stopped
    assert cursor.records[-1].response.action.cfe_served == (0. if constraint == 'minimum' else .125)


def test_no_terminal_action_and_chunking_preserves_state():
    def replay(chunks):
        cursor = init()
        for chunk in chunks:
            for t in chunk:
                cursor = advance(cursor,current(t,c=.125 if t in (23,24) else 0.))
        return cursor
    whole = replay((range(1,25),))
    chunked = replay((range(1,24),range(24,25)))
    assert whole == chunked and not whole.stopped
    assert whole.execution.tracks[0][1].physical.state.active_duration_hours == 2
    assert whole.execution.tracks[0][1].ledger.debt == Q('.25')


def test_future_change_does_not_alter_past_and_fixed_capacity_cannot_drift():
    prefix = advance(init(),current(1,c=.125))
    a = advance(prefix,current(2,c=.25,available=.4))
    b = advance(prefix,current(2,c=.25,available=0.))
    assert a.records[:1] == b.records[:1] == prefix.records
    assert a.records[-1].response.action.cfe_served == .25
    assert b.records[-1].response.action.cfe_served == 0.
    with pytest.raises(ValueError,match='policy identity'):
        replace(prefix,spec=replace(prefix.spec,committed_capacity=.25))
    with pytest.raises(ValueError,match='deterministic replay'):
        replace(prefix.records[0],current=replace(prefix.records[0].current,available_flexibility=0.))


def test_closed_form_continuous_response_matches_independent_finite_enumeration():
    # step=.1: enumerate all pairs directly, independently of support-regime formula.
    for gu,cu,capu,minu in product(range(6),range(6),range(6),range(1,7)):
        expected = max([(0,0)]+[(g,c) for g in range(gu+1) for c in range(cu+1)
                                if minu <= g+c <= capu])
        assert _continuous_response(Q(gu,10),Q(cu,10),Q(capu,10),Q(minu,10)) == (Q(expected[0],10),Q(expected[1],10))


def test_activity_is_aggregate_and_small_served_component_is_retained():
    g,c = _continuous_response(Q('2e-6'),Q('2e-6'),Q('3e-6'),Q('3e-6'))
    assert (g,c) == (Q('2e-6'),Q('1e-6'))
    assert g+c == Q('3e-6')
    cursor = advance(init(committed_capacity=3e-6,minimum_event_power=3e-6),current(1,g=2e-6,c=2e-6))
    assert not cursor.stopped
    assert cursor.records[-1].response.action.cfe_served == Q('1e-6')
    assert cursor.execution.tracks[0][1].ledger.debt == Q('3e-6')


@pytest.mark.parametrize('field,value',[('committed_capacity',True),('committed_capacity',Q(1,2)),
    ('committed_capacity',1.1),('response_time_hours',0.),('minimum_event_power',0.),
    ('curtailment_ramp_per_hour',float('inf')),('recovery_decimal_places',True),
    ('evidence_class','training_certified')])
def test_invalid_or_overclaimed_capacity_contract(field,value):
    with pytest.raises(ValueError):
        init(**{field:value})


def test_source_and_effective_faults_stop_without_candidate():
    r = current(1,c=.125)
    invalid = replace(r,observation=replace(r.observation,hour=replace(r.observation.hour,split='training')))
    cursor = advance(init(),invalid)
    assert cursor.stopped and cursor.records[-1].stage == 'input_validation'
    assert cursor.records[-1].response is None
    cursor = advance(init(B6),current(1,g=.125,c=6e-7))
    assert cursor.stopped and cursor.records[-1].stage == 'policy_decision'
    with pytest.raises(ValueError,match='one typed current'):
        advance(init(),[r,r])


def test_duration_rest_and_event_count_control_actual_actions():
    cursor = init()
    served = []
    for t in range(1,10):
        cursor = advance(cursor,current(t,c=.125))
        assert not cursor.stopped
        served.append(cursor.records[-1].response.action.cfe_served)
    assert served == [.125,.125,.125,0.,0.,.125,.125,.125,0.]
    cursor = advance(cursor,current(10,c=.125))
    cursor = advance(cursor,current(11,c=.125))
    assert cursor.records[-1].response.action.cfe_served == 0.
    assert cursor.execution.tracks[0][1].physical.state.event_count == 2


@pytest.mark.parametrize('limit',['normalized_energy_budget','normalized_debt_limit'])
def test_exact_remaining_energy_and_debt_limit_selected_before_replay(limit):
    cursor = init(envelope=dict(F['envelope'],**{limit:.25}))
    for t in (1,2):
        cursor = advance(cursor,current(t,c=.5))
        assert cursor.records[-1].response.action.cfe_served == .125
    cursor = advance(cursor,current(3,c=.5))
    assert not cursor.stopped and cursor.records[-1].response.action.cfe_served == 0.
    assert cursor.execution.tracks[0][1].ledger.debt == 0
    if limit == 'normalized_energy_budget':
        for t in range(4,8):
            cursor = advance(cursor,current(t,c=.5))
            assert cursor.records[-1].response.action.cfe_served == 0.


def test_fixed_recovery_ceiling_and_immutable_initialization():
    cursor = advance(init(maximum_recovery_power=.0625),current(1,c=.125))
    cursor = advance(cursor,current(2))
    assert cursor.records[-1].response.action.recovery == .0625
    assert cursor.execution.tracks[0][1].ledger.debt == Q('.075')
    with pytest.raises(ValueError,match='zero-history'):
        replace(cursor,initial=cursor.execution)


def test_stop_history_and_available_type_are_guarded():
    cursor = advance(init(),current(1,g=.5))
    with pytest.raises(ValueError,match='cannot have a suffix'):
        replace(cursor,records=cursor.records+cursor.records)
    for value in (True,Q(1,2),float('nan'),1.1,-.1):
        with pytest.raises(ValueError):
            BidirectionalObservation(obs(1),value)


@pytest.mark.parametrize('field,value',[('formal_result',True),('formal_result',0),
    ('training_capacity_certificate',{}),('rule','changed'),('extra','unexpected')])
def test_config_cannot_change_policy_or_claim_training_certificate(field,value):
    with pytest.raises(ValueError,match='draft capacity semantics'):
        BidirectionalPolicy.from_config(dict(CONFIG,**{field:value}),JOINT)


@pytest.mark.parametrize('arm', [NETWORK,CFE,JOINT,B6])
def test_recovery_uses_one_shared_committed_capacity(arm):
    # .4 effective work at eta=.8 needs .5 physical power in one hour.
    envelope = dict(F['envelope'], recovery_efficiency=.8)
    cursor = init(arm, envelope=envelope, committed_capacity=.4,
                  curtailment_ramp_per_hour=1., response_time_hours=1., maximum_recovery_power=1.)
    first = current(1, g=.4 if arm != CFE else 0., c=.4 if arm == CFE else 0., available=1.)
    cursor = advance(cursor, first)
    idle = current(2, business_recovery_headroom=1., cfe_compatible_surplus=1., maximum_recovery_power=1.)
    cursor = advance(cursor, idle)
    assert not cursor.stopped
    assert cursor.records[-1].response.action.recovery == Q('.4')
    assert len(cursor.execution.tracks) == 1
    assert cursor.execution.tracks[0][1].ledger.debt == Q('.08')
    cursor = advance(cursor, current(3, business_recovery_headroom=1., cfe_compatible_surplus=1., maximum_recovery_power=1.))
    assert cursor.records[-1].response.action.recovery == Q('.1')
    assert cursor.execution.tracks[0][1].ledger.debt == 0


def test_bidirectional_policy_legacy_types_are_disjoint():
    from src.rq2_joint_deliverability_boundary_v1 import capacity_policy as old
    from test_rq2_continuous_capacity_policy_v1 import init as old_init, current as old_current
    cursor = init()
    with pytest.raises(ValueError, match='typed'):
        old.advance_capacity_policy(cursor, current(1))
    with pytest.raises(ValueError, match='bidirectional'):
        advance(old_init(), old_current(1))
    with pytest.raises(ValueError, match='typed'):
        advance(cursor, old_current(1))
