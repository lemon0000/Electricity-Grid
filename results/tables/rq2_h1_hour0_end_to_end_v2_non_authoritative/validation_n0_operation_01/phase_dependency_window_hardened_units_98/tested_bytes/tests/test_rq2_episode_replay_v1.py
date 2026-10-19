from dataclasses import replace
from hashlib import sha256
import json

import pytest

from test_rq2_episode_coordinator_v1 import origins, session, advance
from test_rq2_hourly_transaction_v1 import source, audit, obs, next_hour, REF_SELECTOR, REF_BUDGET, SPEC
from src.rq2_joint_deliverability_boundary_v1 import episode_replay as replay
from src.rq2_joint_deliverability_boundary_v1 import episode_coordinator as ep
from src.rq2_joint_deliverability_boundary_v1 import hourly_transaction as tx
from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_candidate as capture
from src.rq2_joint_deliverability_boundary_v1.prefix_handoff import _encoded


CONFIG = dict(reference_selector=REF_SELECTOR, solver_specification=SPEC,
    reference_budget=REF_BUDGET, budget=ep.EpisodeBudget(2, 30, 30))


def hour(info, disclosure, before):
    return tx._owned(ep.EpisodeHourInput, info=info, disclosure=disclosure,
        source_hour=replace(source((info, disclosure, before.reference_state)),
            power_source_hour=info.current.source_hour, workload_source_hour=100+info.current.source_hour),
        source_audit=audit(info), limits=obs(1, g=0., c=0., due=None).limits,
        due_hour=5, available_flexibility=1.)


@pytest.fixture(scope='module')
def real():
    inputs, common, arms = origins()
    s = ep.EpisodeSession(common, arms, **CONFIG)
    first_input = hour(*inputs[:2], common)
    first = advance(s, *inputs[:2])
    second_inputs = next_hour(first.common)
    second_input = hour(*second_inputs, first.common)
    second = advance(s, *second_inputs)
    return common, arms, (first_input, second_input), second


def archive(item):
    common, arms, hours, snapshot = item
    identity = replay.episode_replay_input_identity(common, arms, hours, **CONFIG)
    return replay.export_episode_archive(snapshot, input_identity=identity), identity


def check(item, data=None, **changes):
    original, identity = archive(item)
    data = original if data is None else data
    expected = dict(CONFIG, expected_sha256=sha256(data).hexdigest(), expected_input_identity=identity)
    expected.update(changes)
    return replay.replay_episode_archive(data, *item[:3], **expected)


def forbid(monkeypatch):
    def failed(*a, **kw): raise AssertionError('solver forbidden during episode replay')
    for obj, name in ((capture, '_solve'), (capture, 'create_solver'),
            (tx.reference_selection, 'select_reference_hour'), (tx.dispatch, 'select_actual_dispatch'),
            (tx.reference_selection, '_solve'), (tx.dispatch, '_solve'), (ep.EpisodeSession, 'advance')):
        monkeypatch.setattr(obj, name, failed)


def test_complete_two_hour_replay_without_solver(real, monkeypatch):
    forbid(monkeypatch)
    report = check(real)
    assert report.archive_reproduced and report.status == 'reproduced_episode'
    assert report.verified_hour_count == 2 and report.verified_arm_result_count == 7
    assert report.business_power_bindings_verified == 7
    assert report.reproduced_snapshot_identity == real[-1].identity
    assert not report.resume_authorized and not report.formal_result and not report.security_certified
    assert not report.native_execution_authenticated
    assert not hasattr(report, 'snapshot') and not hasattr(report, 'cursor')
    assert report.complete_service_certificate is None
    assert real[-1].arms[0].business.execution.tracks[0][1].ledger.debt > 0


@pytest.mark.parametrize('mutation', ['debt','power','candidate','pair','arm_order','exposure',
    'reservation','known_calls','outer_commit','skip','source','state','extra','formal','omit_hour','duplicate_hour'])
def test_rehashed_episode_tampering_is_rejected(real, mutation):
    data, _ = archive(real)
    payload = json.loads(data)
    saved = payload['snapshot']
    record = saved['attempts'][0]
    arm = record['arm_results'][0]
    if mutation == 'debt': arm['business_candidate']['records'] = []
    elif mutation == 'power': arm['prescribed_power']['numerator'] = '999'
    elif mutation == 'candidate': arm['business_candidate'] = None
    elif mutation == 'pair': arm['published_pair'] = None
    elif mutation == 'arm_order': record['arm_results'].reverse()
    elif mutation == 'exposure': arm['exposure_id'] = '0'*64
    elif mutation == 'reservation': record['reserved_solver_calls'] -= 1
    elif mutation == 'known_calls': record['known_solver_calls'] -= 1
    elif mutation == 'outer_commit': record['outer_committed'] = False
    elif mutation == 'skip': saved['attempts'][1]['skipped_halted_arms'] = []
    elif mutation == 'source': record['hour_input']['due_hour'] = 6
    elif mutation == 'state': saved['common']['halted'] = True
    elif mutation == 'extra': record['unexpected'] = True
    elif mutation == 'formal': saved['formal_result'] = True
    elif mutation == 'omit_hour': saved['attempts'].pop()
    elif mutation == 'duplicate_hour': saved['attempts'][1] = saved['attempts'][0]
    with pytest.raises(ValueError): check(real, _encoded(payload))


def test_independent_source_and_digest_required(real):
    with pytest.raises(ValueError, match='digest'): check(real, expected_sha256='0'*64)
    with pytest.raises(ValueError, match='input identity'): check(real, expected_input_identity='0'*64)
    data, identity = archive(real)
    changed = tx._owned(ep.EpisodeHourInput, **dict(vars(real[2][0]), due_hour=6))
    with pytest.raises(ValueError, match='input identity'):
        replay.replay_episode_archive(data, real[0], real[1], (changed, real[2][1]), **CONFIG,
            expected_sha256=sha256(data).hexdigest(), expected_input_identity=identity)


def test_create_only_archive(real, tmp_path):
    path = tmp_path/'episode_non_authoritative.json'
    data, identity = archive(real)
    assert replay.write_episode_archive(real[-1], path, input_identity=identity) == sha256(data).hexdigest()
    with pytest.raises(FileExistsError): replay.write_episode_archive(real[-1], path, input_identity=identity)
    assert path.read_bytes() == data


def test_final_report_identity_drift(real, monkeypatch):
    owned = replay._owned
    def drift(cls, **kw):
        result = owned(cls, **kw)
        if cls is replay.EpisodeReplayDiagnostic: monkeypatch.setattr(replay, 'SCHEMA', 'changed')
        return result
    monkeypatch.setattr(replay, '_owned', drift)
    with pytest.raises(ValueError, match='schema drift'): check(real)


def test_outer_interruption_preserves_candidates_but_replay_is_partial(monkeypatch):
    inputs, common, arms = origins()
    s = ep.EpisodeSession(common, arms, **CONFIG)
    h = hour(*inputs[:2], common)
    original = tx.advance_arm_hour
    count = 0
    def interrupted(*args):
        nonlocal count
        count += 1
        if count == 2: raise RuntimeError('outside native record')
        return original(*args)
    monkeypatch.setattr(tx, 'advance_arm_hour', interrupted)
    with pytest.raises(RuntimeError): advance(s, *inputs[:2])
    item = common, arms, (h,), s.snapshot
    forbid(monkeypatch)
    report = check(item)
    assert not report.archive_reproduced and report.status == 'partial_episode_evidence'
    assert report.verified_hour_count == 0 and report.verified_arm_result_count == 1
    assert report.reproduced_snapshot_identity is None
    assert s.snapshot.common == common and s.snapshot.arms == arms
    data, _ = archive(item)
    payload = json.loads(data)
    payload['snapshot']['attempts'][0]['outer_committed'] = True
    with pytest.raises(ValueError, match='outer commit'): check(item, _encoded(payload))
    for field, value in (('error', None), ('known_solver_calls', 0), ('started_arm_ids', []),
                         ('unattempted_arms', []), ('source_hour', 999)):
        payload = json.loads(data)
        payload['snapshot']['attempts'][0][field] = value
        with pytest.raises(ValueError): check(item, _encoded(payload))


@pytest.mark.parametrize('fault', ['timeout', 'exception'])
def test_reference_unresolved_or_partial(monkeypatch, fault):
    from test_rq2_reference_selector_v1 import install
    inputs, common, arms = origins()
    s = ep.EpisodeSession(common, arms, **CONFIG)
    h = hour(*inputs[:2], common)
    install(monkeypatch, fault, 0)
    snapshot = advance(s, *inputs[:2])
    forbid(monkeypatch)
    report = check((common, arms, (h,), snapshot))
    assert report.archive_reproduced == (fault == 'timeout')
    assert report.verified_arm_result_count == report.business_power_bindings_verified == 0
    assert report.unverified_attempt_count == (1 if fault == 'exception' else 0)
    if fault == 'exception':
        item = common, arms, (h,), snapshot
        data, _ = archive(item)
        for field, value in (('known_solver_calls', 0), ('solver_calls', 0), ('solver_call_count_complete', False)):
            payload = json.loads(data)
            payload['snapshot']['attempts'][0][field] = value
            with pytest.raises(ValueError): check(item, _encoded(payload))


def test_missing_dispatch_return_is_not_zero_call_success(monkeypatch):
    inputs, common, arms = origins()
    s = ep.EpisodeSession(common, arms, **CONFIG)
    h = hour(*inputs[:2], common)
    def missing(*a, **kw): raise ValueError('dispatch returned no record')
    monkeypatch.setattr(tx.dispatch, 'select_actual_dispatch', missing)
    snapshot = advance(s, *inputs[:2])
    assert snapshot.attempts[0].solver_calls is None
    forbid(monkeypatch)
    report = check((common, arms, (h,), snapshot))
    assert not report.archive_reproduced and report.evidence_gap == 'actual_selector_return_missing'
    assert report.verified_hour_count == 0 and report.reproduced_snapshot_identity is None
    item = common, arms, (h,), snapshot
    data, _ = archive(item)
    for mutation in ('outer_commit', 'status', 'failed_arm_state', 'calls', 'complete', 'unknown_arms'):
        payload = json.loads(data)
        if mutation == 'outer_commit': payload['snapshot']['attempts'][0]['outer_committed'] = False
        elif mutation == 'status':
            payload['snapshot']['attempts'][0]['status'] = 'forged'
            payload['snapshot']['status'] = 'forged'
        elif mutation == 'failed_arm_state': payload['snapshot']['arms'][0]['halted'] = False
        elif mutation == 'calls': payload['snapshot']['attempts'][0]['solver_calls'] = 0
        elif mutation == 'complete': payload['snapshot']['attempts'][0]['solver_call_count_complete'] = True
        else: payload['snapshot']['attempts'][0]['dispatch_call_count_unresolved_arms'] = []
        with pytest.raises(ValueError): check(item, _encoded(payload))


def test_business_rejection_is_recomputed(real, monkeypatch):
    from test_rq2_hourly_transaction_v1 import arm_origin
    inputs, common, _ = origins()
    arms = tuple(arm_origin(inputs, common, arm, capacity=.125) for arm in ep.ARMS)
    s = ep.EpisodeSession(common, arms, **CONFIG)
    h = hour(*inputs[:2], common)
    snapshot = advance(s, *inputs[:2])
    assert snapshot.attempts[0].arm_results[0].status == 'business_rejected'
    forbid(monkeypatch)
    report = check((common, arms, (h,), snapshot))
    assert report.archive_reproduced and report.verified_arm_result_count == 4
    assert report.business_power_bindings_verified == 1


@pytest.mark.parametrize('status', ['attempt_in_progress', 'budget_exhausted'])
def test_missing_invocation_journal_is_not_exportable(real, status):
    snapshot = tx._owned(ep.EpisodeSnapshot, **dict(vars(real[-1]), status=status, halted=True))
    with pytest.raises(ValueError, match='invocation journal'):
        replay.export_episode_archive(snapshot, input_identity='0'*64)


@pytest.mark.parametrize('mutation', ['newline', 'duplicate', 'extra'])
def test_canonical_envelope(real, mutation):
    data, _ = archive(real)
    if mutation == 'newline': data += b'\n'
    elif mutation == 'duplicate': data = data.replace(b'{', b'{"schema":"foreign",', 1)
    else:
        payload = json.loads(data)
        payload['extra'] = True
        data = _encoded(payload)
    with pytest.raises(ValueError): check(real, data)


@pytest.mark.parametrize('missing', ['reference', 'common', 'arm', 'dispatch'])
def test_deleting_complete_returns_is_not_legitimate_partial(real, missing):
    data, _ = archive(real)
    payload = json.loads(data)
    record = payload['snapshot']['attempts'][0]
    if missing == 'reference': record['reference_result'] = None
    elif missing == 'common': record['common_attempt'] = None
    elif missing == 'arm': record['arm_results'] = []
    else: record['arm_results'][0]['dispatch_result'] = None
    with pytest.raises(ValueError): check(real, _encoded(payload))


def test_missing_one_dispatch_can_have_an_unverified_later_hour(monkeypatch):
    inputs, common, arms = origins()
    s = ep.EpisodeSession(common, arms, **CONFIG)
    h1 = hour(*inputs[:2], common)
    original = tx.dispatch.select_actual_dispatch
    calls = 0
    def missing_once(*a, **kw):
        nonlocal calls
        calls += 1
        if calls == 1: raise ValueError('one arm dispatch interrupted')
        return original(*a, **kw)
    monkeypatch.setattr(tx.dispatch, 'select_actual_dispatch', missing_once)
    first = advance(s, *inputs[:2])
    assert first.status == 'advanced' and first.arms[0].halted
    inputs2 = next_hour(first.common)
    h2 = hour(*inputs2, first.common)
    final = advance(s, *inputs2)
    forbid(monkeypatch)
    report = check((common, arms, (h1, h2), final))
    assert not report.archive_reproduced and report.unverified_attempt_count == 2
    assert report.verified_hour_count == 0
    assert report.evidence_gap == 'actual_selector_return_missing'


def test_fresh_process_two_hour_replay(real, tmp_path):
    import os
    from pathlib import Path
    import subprocess
    import sys
    data, identity = archive(real)
    path = tmp_path/'episode_non_authoritative.json'
    path.write_bytes(data)
    script = '''
from dataclasses import replace
from pathlib import Path
import sys
from test_rq2_episode_replay_v1 import origins, hour, CONFIG, replay, ep, tx, capture
from test_rq2_hourly_transaction_v1 import normal_source, view, current
from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
inputs,common,arms=origins()
h1=hour(*inputs[:2],common)
_,prepared=normal_source()
info=view(prepared,replace(current(2,demand=20.),dc_baseline_mw=25.,
    dc_connected_capacity_mw=25.,dc_physical_maximum_mw=30.))
disclosure=disclose_current(inputs[1].after,CurrentOutageReport(2,None,None))
h2=hour(info,disclosure,common)
def forbidden(*a,**kw): raise AssertionError('solver forbidden in fresh process')
capture._solve=capture.create_solver=forbidden
tx.reference_selection._solve=tx.dispatch._solve=forbidden
tx.reference_selection.select_reference_hour=tx.dispatch.select_actual_dispatch=forbidden
ep.EpisodeSession.advance=forbidden
r=replay.replay_episode_archive(Path(sys.argv[1]).read_bytes(),common,arms,(h1,h2),
    expected_sha256=sys.argv[2],expected_input_identity=sys.argv[3],**CONFIG)
assert r.archive_reproduced and r.verified_hour_count==2
assert r.reproduced_snapshot_identity==sys.argv[4]
assert not r.resume_authorized
print('fresh episode matched')
'''
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, '-B', '-c', script, str(path), sha256(data).hexdigest(), identity, real[-1].identity],
        cwd=root, env=dict(os.environ, PYTHONPATH=str(root/'tests')+os.pathsep+str(root)),
        capture_output=True, text=True, timeout=60, check=True)
    assert 'fresh episode matched' in result.stdout


def test_independent_origin_and_policy_mismatch(real):
    data, identity = archive(real)
    with pytest.raises(ValueError):
        replay.replay_episode_archive(data, real[0], real[1][::-1], real[2], **CONFIG,
            expected_sha256=sha256(data).hexdigest(), expected_input_identity=identity)
    with pytest.raises(ValueError):
        check(real, reference_selector=replace(REF_SELECTOR, absolute_gap_mw=2e-7))


def test_actual_partial_record_keeps_exact_known_call_inventory(monkeypatch):
    inputs, common, arms = origins()
    s = ep.EpisodeSession(common, arms, **CONFIG)
    h = hour(*inputs[:2], common)
    original = capture.create_solver
    calls = 0
    def failed_creation(*a, **kw):
        nonlocal calls
        calls += 1
        if calls == 4: raise RuntimeError('actual create interrupted')
        return original(*a, **kw)
    monkeypatch.setattr(capture, 'create_solver', failed_creation)
    snapshot = advance(s, *inputs[:2])
    assert snapshot.attempts[0].arm_results[0].dispatch_result.status == 'unresolved'
    forbid(monkeypatch)
    item = common, arms, (h,), snapshot
    report = check(item)
    assert report.evidence_gap == 'actual_partial_native_evidence' and not report.archive_reproduced
    data, _ = archive(item)
    payload = json.loads(data)
    record = payload['snapshot']['attempts'][0]
    record['known_solver_calls'] += 1
    record['solver_calls'] += 1
    with pytest.raises(ValueError): check(item, _encoded(payload))


def test_fresh_import_source_closure():
    from pathlib import Path
    import subprocess
    import sys
    script = '''
import json,sys
from pathlib import Path
import src.rq2_joint_deliverability_boundary_v1.episode_replay
root=Path.cwd()
print(json.dumps(sorted(Path(m.__file__).resolve().relative_to(root).as_posix()
    for n,m in sys.modules.items() if n=='src' or n.startswith('src.'))))
'''
    completed = subprocess.run([sys.executable, '-B', '-c', script],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30, check=True)
    assert set(json.loads(completed.stdout)) == set(replay.DEPENDENCIES)
