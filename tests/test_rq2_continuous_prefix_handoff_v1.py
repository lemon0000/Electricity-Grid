from dataclasses import replace
from fractions import Fraction as Q
import json
import subprocess
import sys

import pytest

from test_rq2_continuous_capacity_policy_v1 import init, current, advance
from src.rq2_joint_deliverability_boundary_v1 import prefix_handoff as handoff
from src.rq2_joint_deliverability_boundary_v1.debt_cohorts import assess_debt_cohorts
from src.rq2_joint_deliverability_boundary_v1.four_arm_replay import NETWORK, CFE, JOINT, B6


def restored(cursor, origin=None):
    data = handoff.export_prefix_handoff(cursor)
    return handoff.import_prefix_handoff(data, expected_sha256=handoff.prefix_digest(data),
        expected_origin=handoff._origin(cursor) if origin is None else origin)


@pytest.mark.parametrize('arm', [NETWORK, CFE, JOINT, B6])
def test_all_arms_persistent_handoff_matches_uninterrupted_execution(tmp_path, arm):
    origin = init(arm)
    prefix = advance(origin, current(1, g=.0625, c=.0625))
    prefix = advance(prefix, current(2, g=.0625, c=.0625))
    path = tmp_path/'carry_non_authoritative.json'
    digest = handoff.write_prefix_handoff(prefix, path)
    loaded = handoff.read_prefix_handoff(path, expected_sha256=digest, expected_origin=origin)
    assert loaded == prefix and len(loaded.records) == 2
    for hour in range(3, 8):
        obs = current(hour, g=.0625 if hour == 3 else 0., c=.125 if hour == 3 else 0.)
        loaded, prefix = advance(loaded, obs), advance(prefix, obs)
        assert loaded == prefix
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        handoff.write_prefix_handoff(prefix, path)
    assert path.read_bytes() == before


def test_active_carry_preserves_exact_previous_call_duration_energy_debt():
    prefix = init()
    for hour in range(1, 11):
        prefix = advance(prefix, current(hour, c=.125 if hour in (9, 10) else 0.))
    loaded = restored(prefix)
    track = loaded.execution.tracks[0][1]
    assert track.ledger.debt == Q('.25')
    assert track.physical.state.active_duration_hours == 2
    loaded = advance(loaded, current(11, c=.30))
    assert loaded.records[-1].response.action.cfe_served == Q('.25')
    assert loaded.execution.tracks[0][1].ledger.debt == Q('.5')
    loaded = advance(loaded, current(12, c=.30))
    assert loaded.records[-1].response.action.cfe_served == 0
    assert loaded.execution.tracks[0][1].physical.state.event_count == 1


def test_inactive_carry_keeps_rest_and_event_budget():
    prefix = advance(init(), current(1, c=.125))
    prefix = advance(prefix, current(2, c=.125))
    prefix = advance(prefix, current(3, business_recovery_headroom=.15625))
    assert prefix.execution.tracks[0][1].ledger.debt == Q('.125')
    assert prefix.execution.tracks[0][1].physical.state.interevent_rest_hours == 1
    loaded = advance(restored(prefix), current(4, c=.125, business_recovery_headroom=.0625))
    assert loaded.records[-1].response.action.cfe_served == 0
    assert loaded.execution.tracks[0][1].ledger.debt == Q('.075')
    loaded = advance(loaded, current(5, c=.125))
    assert loaded.records[-1].response.action.cfe_served == Q('.125')
    assert loaded.execution.tracks[0][1].physical.state.event_count == 2


def test_missed_deadline_persists_after_import_and_late_recovery():
    obs = current(1, c=.125)
    obs = replace(obs, observation=replace(obs.observation, due_hour=3))
    prefix = advance(init(), obs)
    for t in (2, 3):
        prefix = advance(prefix, current(t, business_recovery_headroom=0.))
    loaded = restored(prefix)
    ledger = loaded.execution.tracks[0][1].ledger
    assert ledger.cohorts[0].missed_at_deadline == Q('.125')
    loaded = advance(loaded, current(4))
    ledger = loaded.execution.tracks[0][1].ledger
    assert ledger.debt == 0
    assert assess_debt_cohorts(ledger) == ((1, 'deadline_missed'),)


def test_unknown_deadline_and_fraction_original_are_lossless():
    obs = current(1, c=.125)
    obs = replace(obs, observation=replace(obs.observation,
        hour=replace(obs.observation.hour, cfe_request=Q(1, 7)), due_hour=None))
    prefix = advance(init(), obs)
    loaded = restored(prefix)
    assert loaded == prefix
    assert loaded.records[0].current.observation.hour.cfe_request == Q(1, 7)
    assert assess_debt_cohorts(loaded.execution.tracks[0][1].ledger) == ((1, 'deadline_unidentified'),)
    body = json.loads(handoff.export_prefix_handoff(prefix))
    assert body['records'][0]['original_current']['observation']['hour']['cfe_request'] == {'numerator': '1', 'denominator': '7'}
    assert body['observed_carry_in'] is False and body['evidence_class'] == 'derived_mechanism_state'


@pytest.mark.parametrize('kind', ['empty', 'grid_stop', 'source_gap', 'naked_state'])
def test_unverified_or_stopped_origins_are_not_exportable(kind):
    cursor = init()
    if kind == 'grid_stop':
        cursor = advance(cursor, current(1, g=.25))
    elif kind == 'source_gap':
        cursor = advance(cursor, current(2))
    elif kind == 'naked_state':
        cursor = cursor.initial
    with pytest.raises(ValueError):
        handoff.export_prefix_handoff(cursor)


@pytest.mark.parametrize('field', ['split', 'power_trajectory_id', 'workload_trace_id',
    'power_outage_seed', 'power_provenance_sha256', 'workload_provenance_sha256',
    'workload_normalization_sha256', 'power_source_hour', 'workload_source_hour',
    'spec', 'period', 'envelope', 'arm'])
def test_external_origin_binding_rejects_cross_context(field):
    prefix = advance(init(), current(1, c=.125))
    origin = init()
    track = origin.initial.tracks[0][1]
    anchor, spec, envelope, period = track.physical.anchor, origin.spec, dict(track.physical.envelope), track.ledger.accounting_period_id
    if field == 'spec':
        spec = replace(spec, committed_capacity=.4)
    elif field == 'arm':
        spec = replace(spec, arm_id=NETWORK)
    elif field == 'period':
        period = 'other-period'
    elif field == 'envelope':
        envelope['normalized_energy_budget'] = .9
    else:
        value = getattr(anchor, field)
        changed = 'training' if field == 'split' else ('9'*64 if 'sha256' in field else
            value+1 if type(value) is int else 'other-source')
        anchor = replace(anchor, **{field: changed})
    other = handoff.initialize_capacity_policy(spec, anchor=anchor, envelope=envelope,
        accounting_period_id=period, zero_carry_in_assumption=True)
    with pytest.raises(ValueError, match='origin mismatch'):
        restored(prefix, other)


@pytest.mark.parametrize('fault', ['cohort', 'physical', 'action', 'projection', 'input', 'count', 'gate', 'dependency'])
def test_rehashed_artifact_still_requires_deterministic_replay(fault):
    prefix = advance(init(), current(1, c=.125))
    body = json.loads(handoff.export_prefix_handoff(prefix))
    if fault == 'cohort':
        body['terminal_execution']['tracks']['shared']['ledger']['cohorts'] = []
    elif fault == 'physical':
        body['terminal_execution']['tracks']['shared']['physical']['state']['event_count'] = 0
    elif fault == 'action':
        body['records'][0]['declared_action']['cfe_served']['numerator'] = '0'
    elif fault == 'projection':
        body['records'][0]['executed_request_projection']['hour']['cfe_request'] = .125
    elif fault == 'input':
        body['records'][0]['original_current']['observation']['hour']['cfe_request'] = .25
    elif fault == 'count':
        body['prefix_record_count'] = 99
    elif fault == 'gate':
        body['observed_carry_in'] = True
    else:
        body['implementation_sha256']['src/__init__.py'] = '0'*64
    altered = handoff._encoded(body)
    with pytest.raises(ValueError, match='replay mismatch'):
        handoff.import_prefix_handoff(altered, expected_sha256=handoff.prefix_digest(altered), expected_origin=init())


@pytest.mark.parametrize('fault', ['digest', 'truncate', 'duplicate', 'nonfinite', 'whitespace', 'fraction'])
def test_invalid_bytes_and_noncanonical_input_fail_closed(fault):
    obs = current(1, c=.125)
    obs = replace(obs, observation=replace(obs.observation,
        hour=replace(obs.observation.hour, cfe_request=Q(1, 7))))
    data = handoff.export_prefix_handoff(advance(init(), obs))
    if fault == 'digest':
        digest = '0'*64
    else:
        if fault == 'truncate': data = data[:-10]
        elif fault == 'duplicate': data = b'{"schema":"other",'+data[1:]
        elif fault == 'nonfinite': data = data.replace(b'"available_flexibility":0.4', b'"available_flexibility":NaN')
        elif fault == 'whitespace': data += b' '
        elif fault == 'fraction': data = data.replace(b'"denominator":"7","numerator":"1"', b'"denominator":"14","numerator":"2"')
        digest = handoff.prefix_digest(data)
    with pytest.raises(ValueError):
        handoff.import_prefix_handoff(data, expected_sha256=digest, expected_origin=init())


@pytest.mark.parametrize('field', ['split', 'power_source_hour', 'workload_source_hour', 'power_trajectory_id'])
def test_suffix_identity_still_checked_after_restore(field):
    loaded = restored(advance(init(), current(1, c=.125)))
    obs = current(2)
    value = getattr(obs.observation.hour, field)
    obs = replace(obs, observation=replace(obs.observation, hour=replace(obs.observation.hour,
        **{field: value+1 if type(value) is int else ('training' if field == 'split' else 'other')})))
    stopped = advance(loaded, obs)
    assert stopped.stopped and stopped.execution == loaded.execution


def test_fresh_import_implementation_closure():
    script = '''
import json, pathlib, sys
from src.rq2_joint_deliverability_boundary_v1 import prefix_handoff as h
root = h.ROOT.resolve()
loaded = set()
for m in tuple(sys.modules.values()):
    name = getattr(m, '__file__', None)
    if name:
        path = pathlib.Path(name).resolve()
        if path.suffix == '.py' and path.is_relative_to(root):
            loaded.add(path.relative_to(root).as_posix())
print(json.dumps(sorted(loaded)))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script], cwd=handoff.ROOT,
        capture_output=True, text=True, check=True)
    assert set(json.loads(result.stdout)) == set(handoff.IMPLEMENTATION)


def test_handoff_resumes_in_a_fresh_python_process(tmp_path):
    prefix = advance(init(), current(1, c=.125))
    prefix = advance(prefix, current(2, c=.125))
    path = tmp_path/'process_carry_non_authoritative.json'
    digest = handoff.write_prefix_handoff(prefix, path)
    script = '''
import pathlib, sys
sys.path.insert(0, str(pathlib.Path.cwd()/'tests'))
from test_rq2_continuous_capacity_policy_v1 import init, current, advance
from src.rq2_joint_deliverability_boundary_v1 import prefix_handoff as h
cursor = h.read_prefix_handoff(sys.argv[1], expected_sha256=sys.argv[2], expected_origin=init())
cursor = advance(cursor, current(3, c=.25))
print(h.prefix_digest(h.export_prefix_handoff(cursor)))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, str(path), digest], cwd=handoff.ROOT,
        capture_output=True, text=True, check=True)
    expected = advance(prefix, current(3, c=.25))
    assert result.stdout.strip() == handoff.prefix_digest(handoff.export_prefix_handoff(expected))
