from dataclasses import replace
from pathlib import Path
import hashlib
import json

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1.boundary import (
    BoundaryAnchor, ContinuationHour, TemporalCarryState, assess_observed_continuation,
)
from src.rq2_joint_deliverability_boundary_v1.multiday import (
    ServiceAction, initialize_joint_replay, replay_joint_chunk,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / 'configs/rq2_continuous_multiday_service_v1.DRAFT.yaml'


@pytest.fixture
def case():
    cfg = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))['synthetic_fixture']
    identity = dict(arm_id='joint_correct_shared', track_id='shared', split='training',
                    power_trajectory_id='synthetic-power', workload_trace_id='synthetic-work',
                    workload_normalization_sha256='1'*64, power_outage_seed=0,
                    power_provenance_sha256='2'*64, workload_provenance_sha256='3'*64)
    anchor = BoundaryAnchor(**identity, power_source_hour=0, workload_source_hour=0)
    state = TemporalCarryState('joint_correct_shared', 'shared', 0., False, 0., None,
                               0, 0., cfg['initial_debt'], False, cfg['accounting_period_id'])
    rows, actions = [], []
    for t in range(1, cfg['hours'] + 1):
        g = cfg['grid_request'] if t in cfg['call_hours'] else 0.
        c = cfg['cfe_request'] if t in cfg['call_hours'] else 0.
        r = cfg['recovery'] if t in cfg['recovery_hours'] else 0.
        rows.append(ContinuationHour(**identity, power_source_hour=t, workload_source_hour=t,
                    grid_request=g, cfe_request=c, workload_occupancy=cfg['baseline_power']))
        actions.append(ServiceAction(r, cfg['baseline_power']-g-c+r, cfg['call_limit'],
                       cfg['business_recovery_headroom'], cfg['cfe_compatible_surplus'],
                       cfg['maximum_recovery_power']))
    return state, anchor, rows, actions, cfg['envelope']


def run(case, **changes):
    state, anchor, rows, actions, envelope = case
    args = dict(anchor=anchor, hours=rows, actions=actions, envelope=envelope)
    args.update(changes)
    cursor = initialize_joint_replay(state, anchor=args.pop('anchor'), envelope=args.pop('envelope'))
    return replay_joint_chunk(cursor, **args).states


@pytest.mark.parametrize('cuts', [[24], [23, 24, 25, 26], [1, 12, 36, 47]])
def test_48h_partition_invariance_and_analytic_debt(case, cuts):
    whole = run(case)
    state, anchor, rows, actions, env = case
    cursor = initialize_joint_replay(state, anchor=anchor, envelope=env)
    parts = []
    start = 0
    for end in cuts + [48]:
        chunk = replay_joint_chunk(cursor, hours=rows[start:end], actions=actions[start:end])
        parts.extend(chunk.states)
        cursor, start = chunk.cursor, end
    assert tuple(parts) == whole
    # Independent analytic prefix oracle, not the state transition implementation.
    for hour, state in enumerate(whole, 1):
        ncall = sum(t <= hour for t in (23, 24, 25))
        nrecover = sum(t <= hour for t in (26, 27, 28))
        assert state.recovery_debt == pytest.approx(.25 * (ncall - nrecover))
        assert state.cumulative_call_energy == pytest.approx(.25 * ncall)
        assert state.event_count == int(hour >= 23)
    assert whole[23].event_active and whole[23].active_duration_hours == 2
    assert whole[23].recovery_debt == .5
    assert whole[24].active_duration_hours == 3
    assert whole[-1].recovery_debt == 0
    assert whole[-1].cumulative_call_energy == .75


@pytest.mark.parametrize('parameter,value,error', [
    ('maximum_event_duration_hours', 2., 'duration'),
    ('normalized_energy_budget', .5, 'energy_budget'),
    ('normalized_debt_limit', .5, 'debt_limit'),
])
def test_next_day_cannot_reset_limits(case, parameter, value, error):
    state, anchor, rows, actions, env = case
    env = dict(env, **{parameter: value})
    cursor = initialize_joint_replay(state, anchor=anchor, envelope=env)
    first = replay_joint_chunk(cursor, hours=rows[:24], actions=actions[:24])
    with pytest.raises(ValueError, match=error):
        replay_joint_chunk(first.cursor, hours=rows[24:], actions=actions[24:])


@pytest.mark.parametrize('fault,error', [
    ('shared_capacity', 'call limit'), ('balance', 'power balance'),
    ('cfe_surplus', 'headroom'), ('business_headroom', 'headroom'),
    ('future_recovery', 'exceeds accrued debt'), ('missing_action', 'explicit action'),
    ('split', 'cross-split'), ('gap', 'source-hour gap'),
])
def test_replay_rejects_invalid_service_and_continuity(case, fault, error):
    state, anchor, rows, actions, env = case
    rows, actions = list(rows), list(actions)
    if fault == 'shared_capacity':
        actions[23] = replace(actions[23], call_limit=.2)
    elif fault == 'balance':
        actions[23] = replace(actions[23], actual_service_power=1.)
    elif fault == 'cfe_surplus':
        actions[25] = replace(actions[25], cfe_compatible_surplus=0.)
    elif fault == 'business_headroom':
        actions[25] = replace(actions[25], business_recovery_headroom=0.)
    elif fault == 'future_recovery':
        actions[0] = replace(actions[0], recovery=.1, actual_service_power=1.1)
    elif fault == 'missing_action':
        actions.pop()
    elif fault == 'split':
        rows[24] = replace(rows[24], split='holdout')
    else:
        rows[24] = replace(rows[24], power_source_hour=26)
    with pytest.raises(ValueError, match=error):
        run(case, hours=rows, actions=actions)


@pytest.mark.parametrize('event_limit,rest,error', [(1, 2., 'event_count'), (2, 3., 'interevent')])
def test_event_count_and_rest_across_chunk(case, event_limit, rest, error):
    state, anchor, rows, actions, env = case
    rows, actions = list(rows), list(actions)
    for i in range(48):
        call = .25 if i in (20, 23) else 0.
        rows[i] = replace(rows[i], grid_request=call, cfe_request=0.)
        actions[i] = replace(actions[i], recovery=0., actual_service_power=1.-call)
    # Split after hour 23: only two inactive hours separate starts at 21 and 24.
    env = dict(env, maximum_event_count=event_limit, minimum_recovery_hours=rest)
    cursor = initialize_joint_replay(state, anchor=anchor, envelope=env)
    prefix = replay_joint_chunk(cursor, hours=rows[:23], actions=actions[:23])
    with pytest.raises(ValueError, match=error):
        replay_joint_chunk(prefix.cursor, hours=rows[23:], actions=actions[23:])


def test_initial_debt_is_explicit_and_observation_end_is_not_completion(case):
    state, anchor, rows, actions, env = case
    initial = replace(state, recovery_debt=.125, cumulative_call_energy=.125,
                      event_count=1, has_prior_event=True, interevent_rest_hours=2.)
    cursor = initialize_joint_replay(initial, anchor=anchor, envelope=env)
    result = replay_joint_chunk(cursor, hours=rows, actions=actions).states
    assert result[-1].recovery_debt == pytest.approx(.125)
    assert result[-1].cumulative_call_energy == pytest.approx(.875)
    assert result[-1].event_count == 2
    assessment = assess_observed_continuation(anchor=anchor, continuation=rows,
                registered_completion_deadline_hours=None, state=result[-1])
    assert assessment.status == 'blocked_missing_registered_completion_deadline'
    assert not assessment.completion_can_be_evaluated
    short = assess_observed_continuation(anchor=anchor, continuation=rows[:24],
                registered_completion_deadline_hours=48, state=result[23])
    assert short.status == 'blocked_right_censored_incomplete_continuation'


def test_prescribed_replay_prefix_is_unchanged_by_future_actions(case):
    _, _, rows, actions, _ = case
    original = run(case)
    changed = list(actions)
    changed[-1] = replace(changed[-1], actual_service_power=.1)
    prefix = run(case, hours=rows[:24], actions=changed[:24])
    assert prefix == original[:24]  # Replay only; does not certify a policy's causality.


@pytest.mark.parametrize('field,value', [
    ('split', 'holdout'), ('power_trajectory_id', 'another-trajectory'),
    ('power_outage_seed', 1), ('workload_trace_id', 'another-trace'),
    ('power_provenance_sha256', '4'*64),
])
def test_returned_cursor_binds_state_to_source_identity(case, field, value):
    state, anchor, rows, actions, env = case
    cursor = initialize_joint_replay(state, anchor=anchor, envelope=env)
    prefix = replay_joint_chunk(cursor, hours=rows[:24], actions=actions[:24])
    other = [replace(row, **{field: value}) for row in rows[24:]]
    with pytest.raises(ValueError):
        replay_joint_chunk(prefix.cursor, hours=other, actions=actions[24:])
    # An alternative anchor cannot be supplied alongside this carried state.
    with pytest.raises(TypeError):
        replay_joint_chunk(prefix.cursor, anchor=other[0], hours=other, actions=actions[24:])


def test_chunk_contract_cannot_be_replaced_or_mutated(case):
    from dataclasses import FrozenInstanceError
    state, anchor, rows, actions, env = case
    env = dict(env, normalized_energy_budget=.5)
    cursor = initialize_joint_replay(state, anchor=anchor, envelope=env)
    prefix = replay_joint_chunk(cursor, hours=rows[:24], actions=actions[:24])
    env['normalized_energy_budget'] = 2.  # Mutating caller mapping cannot change cursor.
    with pytest.raises(ValueError, match='energy_budget'):
        replay_joint_chunk(prefix.cursor, hours=rows[24:], actions=actions[24:])
    with pytest.raises(TypeError):
        replay_joint_chunk(prefix.cursor, hours=rows[24:], actions=actions[24:], envelope=env)
    with pytest.raises(FrozenInstanceError):
        prefix.cursor.envelope = tuple(env.items())


def test_tolerance_mapping_is_consistent_in_power_and_debt(case):
    state, anchor, rows, actions, env = case
    tiny = [replace(row, grid_request=5e-7, cfe_request=5e-7) for row in rows]
    idle = [replace(action, recovery=1e-6, actual_service_power=1.) for action in actions]
    result = run(case, hours=tiny, actions=idle)
    assert result[-1].cumulative_call_energy == 0.
    assert result[-1].recovery_debt == 0.
    assert result[-1].event_count == 0


@pytest.mark.parametrize('changes,error', [
    ({'recovery_debt': .125}, 'debt exceeds'),
    ({'recovery_debt': .125, 'cumulative_call_energy': .125}, 'prior event history'),
])
def test_partial_carry_in_cannot_discard_energy_or_event_history(case, changes, error):
    state, anchor, _, _, env = case
    with pytest.raises(ValueError, match=error):
        initialize_joint_replay(replace(state, **changes), anchor=anchor, envelope=env)


def test_recovery_cannot_hide_an_initial_prefix_debt_violation(case):
    state, anchor, _, _, env = case
    initial = replace(state, recovery_debt=.75, cumulative_call_energy=.75,
                      event_count=1, has_prior_event=True, interevent_rest_hours=2.)
    with pytest.raises(ValueError, match='initial debt limit'):
        initialize_joint_replay(initial, anchor=anchor, envelope=dict(env, normalized_debt_limit=.5))


def test_evidence_table_covers_every_unknown_and_binds_delivery():
    cfg = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    for name in ('summary', 'input_status'):
        path = ROOT / cfg['delivery'][name]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == cfg['delivery'][name+'_sha256']
    status = json.loads((ROOT / cfg['delivery']['input_status']).read_text(encoding='utf-8'))
    evidence = (ROOT / 'docs/model_spec/rq2_continuous_multiday_parameter_evidence_v1.md').read_text(encoding='utf-8')
    table = {}
    for line in evidence.splitlines():
        if line.startswith('| `'):
            columns = [item.strip() for item in line.strip('|').split('|')]
            assert len(columns) == 4
            name = columns[0].strip('`')
            assert name not in table
            table[name] = columns[1:]
    assert set(table) == {row['name'] for row in status['unidentified']}
    for row in status['unidentified']:
        assert table[row['name']][0] == 'null'
        assert all(table[row['name']][1:])
        assert row['value'] is None
    assert cfg['continuous_service_protocol_registered'] is False
