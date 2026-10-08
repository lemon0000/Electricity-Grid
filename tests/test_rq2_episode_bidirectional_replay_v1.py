from hashlib import sha256
import pytest

from test_rq2_episode_bidirectional_v1 import inputs, bind_inputs
from src.rq2_joint_deliverability_boundary_v1 import scale_episode_bidirectional as ep, scale_episode_bidirectional_replay as audit


def pins(root):
    return dict(expected_header_sha256=sha256((root/'header.json').read_bytes()).hexdigest(),
        expected_intent_sha256s=tuple(sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.intent.json'))),
        expected_result_sha256s=tuple(sha256(p.read_bytes()).hexdigest() for p in sorted(root.glob('*.result.json'))),
        expected_audit_identity=audit.implementation_identity())


@pytest.fixture(scope='module')
def completed(tmp_path_factory):
    base = tmp_path_factory.mktemp('scale_episode_offline')
    req, arms, hours, settings = inputs(base)
    root = base/'episode_non_authoritative'
    with ep.DevelopmentBidirectionalEpisode(root, req, arms, hours, **settings) as owner:
        owner.advance()
    return root, req, arms, hours, settings, pins(root)


def test_complete_prefix_replays_with_no_execution(completed, monkeypatch):
    root, req, arms, hours, settings, expected = completed
    def forbidden(*args, **kwargs): raise AssertionError('offline audit attempted execution')
    monkeypatch.setattr(ep.controller, 'supervise_selector', forbidden)
    monkeypatch.setattr(ep.tx.scale.native, '_solve', forbidden)
    report = audit.audit_episode(root, req, arms, hours, **settings, **expected)
    assert report['completed_hours'] == 1 and report['observation_window_consumed']
    assert report['selected_phase_chains_replayed'] == 4
    assert report['unresolved_phase_records'] == 1
    assert report['reserved_solver_calls'] == 11
    assert report['solver_calls_by_auditor'] == 0
    assert not report['formal_result'] and not report['executable_resume_available']
    assert not report['complete_service_certified']


def test_business_rejection_persists_pair_and_replays_without_actual_task(tmp_path, monkeypatch):
    from dataclasses import replace
    req, arms, hours, settings = inputs(tmp_path)
    original = arms[2].business
    policy = replace(original.spec, committed_capacity=.125)
    business = ep.tx.business_api.initialize_capacity_policy(policy,
        anchor=original.initial.tracks[0][1].physical.anchor,
        envelope=dict(original.initial.tracks[0][1].physical.envelope),
        accounting_period_id=original.initial.tracks[0][1].ledger.accounting_period_id,
        zero_carry_in_assumption=True)
    arms = (*arms[:2], replace(arms[2], business=business), arms[3])
    root = tmp_path/'business_rejected_non_authoritative'
    with ep.DevelopmentBidirectionalEpisode(root, req, arms, hours, **settings) as owner:
        body = owner.advance()
        cursor = owner._cursors[2]
        assert cursor.halted and cursor.business == business and cursor.grid == arms[2].grid
        assert body['results'][2]['status'] == 'business_rejected'
        assert body['results'][2]['published_pair'] is None
        assert body['results'][3]['status'] == 'committed'
        assert body['phase_evidence'][3] == dict(role='actual:2', status='skipped_business_rejected')
    assert not (root/'000000_actual_2_non_authoritative').exists()
    def forbidden(*args, **kwargs): raise AssertionError('offline audit attempted execution')
    monkeypatch.setattr(ep.controller, 'supervise_selector', forbidden)
    monkeypatch.setattr(ep.tx.scale.native, '_solve', forbidden)
    report = audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    assert report['completed_hours'] == 1 and report['solver_calls_by_auditor'] == 0
    assert report['selected_phase_chains_replayed'] == 3
    assert report['reserved_solver_calls'] == 11


def test_all_analytic_roles_episode_and_zero_solver_replay(tmp_path, monkeypatch):
    req, arms, hours, settings = inputs(tmp_path, zero=True)
    root = tmp_path/'analytic_episode_non_authoritative'
    with ep.DevelopmentBidirectionalEpisode(root, req, arms, hours, **settings) as owner:
        body = owner.advance()
        assert all(result['status'] == 'committed' for result in body['results'])
        assert body['reserved_solver_calls'] == 11
    actual_calls = []
    for phase in body['phase_evidence']:
        receipt = ep.controller._read(root/phase['relative_root']/'receipt_non_authoritative.json')
        actual_calls.append(receipt['inspection']['reported_solver_calls'])
    assert actual_calls == [2, 1, 1, 1, 1]
    def forbidden(*args, **kwargs): raise AssertionError('offline audit attempted execution')
    monkeypatch.setattr(ep.controller, 'supervise_selector', forbidden)
    monkeypatch.setattr(ep.tx.scale.native, '_solve', forbidden)
    report = audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    assert report['selected_phase_chains_replayed'] == 5
    assert report['unresolved_phase_records'] == 0
    assert report['solver_calls_by_auditor'] == 0
    assert report['reserved_solver_calls'] == 11
    assert not report['complete_service_certified'] and not report['formal_result']


@pytest.mark.parametrize('fault', ['role_swap', 'cursor_status', 'reservation', 'artifact'])
def test_rehashed_hour_corruption_rejected(completed, fault):
    root, req, arms, hours, settings, expected = completed
    path = root/'000000.result.json'
    original = path.read_bytes()
    body = ep.controller._read(path)
    if fault == 'role_swap':
        body['phase_evidence'][1], body['phase_evidence'][3] = body['phase_evidence'][3], body['phase_evidence'][1]
    elif fault == 'cursor_status': body['results'][1]['status'] = 'committed'
    elif fault == 'reservation': body['reserved_solver_calls'] = 1
    else: body['phase_evidence'][1]['record_sha256'] = 'a'*64
    try:
        path.write_bytes(ep.controller.worker.store._bytes(body))
        with pytest.raises(ValueError):
            audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    finally:
        path.write_bytes(original)


def test_rehashed_original_plan_in_header_is_rejected(completed):
    root, req, arms, hours, settings, _ = completed
    path = root/'header.json'
    original = path.read_bytes()
    body = ep.controller._read(path)
    body['resource_plan']['serial_budget']['controller_seconds'] += 1
    try:
        path.write_bytes(ep.controller.worker.store._bytes(body))
        with pytest.raises(ValueError, match='header differs from independent inputs'):
            audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    finally:
        path.write_bytes(original)


def test_extra_root_file_is_rejected(completed):
    root, req, arms, hours, settings, _ = completed
    extra = root/'undeclared_inputs.json'
    extra.write_bytes(b'{}')
    try:
        with pytest.raises(ValueError, match='root entry inventory'):
            audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    finally:
        # Only the test-created sentinel in pytest tmp is removed.
        extra.unlink()


def test_pending_intent_is_unknown_and_charged(tmp_path, monkeypatch):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentBidirectionalEpisode(root, req, arms, hours, **settings) as owner:
        def interrupted(*args): raise RuntimeError('stopped')
        monkeypatch.setattr(owner, '_task', interrupted)
        with pytest.raises(RuntimeError): owner.advance()
    report = audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    assert report['status'] == 'pending_unknown' and report['completed_hours'] == 0
    assert report['reserved_solver_calls'] == 11
    assert report['selected_phase_chains_replayed'] == 0
    assert not report['observation_window_consumed']


def test_extra_task_root_is_rejected(completed):
    root, req, arms, hours, settings, expected = completed
    extra = root/'000000_actual_4_non_authoritative'
    extra.mkdir()
    try:
        with pytest.raises(ValueError, match='directory inventory'):
            audit.audit_episode(root, req, arms, hours, **settings, **expected)
    finally: extra.rmdir()


@pytest.mark.parametrize('fault', ['identity', 'boolean_exit', 'resource_errors', 'observation_error', 'markers',
                                 'zero_samples', 'zero_peak', 'elapsed_limit', 'commit_reserve', 'disk_inventory'])
def test_linked_process_identity_forgery_is_rejected(completed, fault):
    root, req, arms, hours, settings, expected = completed
    task = root/'000000_actual_0_non_authoritative'
    paths = [task/'result.json', task/'launch.json', task/'observation.json', root/'000000.result.json']
    originals = {p: p.read_bytes() for p in paths}
    try:
        result = ep.controller._read(paths[0])
        observation = result['observation']
        if fault == 'identity': observation.update(process_identity='a'*64, pid=123456, creation_filetime=123456)
        elif fault == 'boolean_exit': observation['exit_code'] = False
        elif fault == 'resource_errors': observation['last_resource_errors'] = ['system_commit_reserve_breached']
        elif fault == 'observation_error': observation['observation_error_type'] = 'OSError'
        elif fault == 'markers': observation['stop_markers'] = ['task_deadline_stop']
        elif fault == 'zero_samples': observation['runtime_samples'] = 0
        elif fault == 'zero_peak': observation['job_peak_process_commit_bytes'] = 0
        elif fault == 'elapsed_limit': observation['elapsed_seconds'] = 10000.
        elif fault == 'commit_reserve': observation['minimum_runtime_commit_available_bytes'] = 0
        else: observation['minimum_runtime_disk_available_bytes'] = []
        paths[0].write_bytes(ep.controller.worker.store._bytes(result))
        paths[1].write_bytes(ep.controller.worker.store._bytes({k: observation[k] for k in ('process_identity', 'pid', 'creation_filetime')}))
        paths[2].write_bytes(ep.controller.worker.store._bytes(result['observation']))
        hour = ep.controller._read(paths[3])
        phase = hour['phase_evidence'][1]
        phase['process_identity'] = observation['process_identity']
        phase['files'][str(paths[0].relative_to(root))]['sha256'] = sha256(paths[0].read_bytes()).hexdigest()
        paths[3].write_bytes(ep.controller.worker.store._bytes(hour))
        with pytest.raises(ValueError, match='independent command identity|recorded quiet normal exit|crosslink mismatch|invalid pipeline'):
            audit.audit_episode(root, req, arms, hours, **settings, **pins(root))
    finally:
        for path, raw in originals.items(): path.write_bytes(raw)


def test_two_hour_replay_and_skipped_task_directory_rejected(tmp_path, monkeypatch):
    from dataclasses import replace
    from test_rq2_hourly_transaction_v1 import normal_source, view, current, source, audit as source_audit
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
    req, arms, hours, settings = inputs(tmp_path)
    _, prepared = normal_source()
    info = view(prepared, replace(current(2, demand=20.), dc_baseline_mw=25.,
        dc_connected_capacity_mw=25., dc_physical_maximum_mw=30.))
    disclosure = disclose_current(hours[0].disclosure.after, CurrentOutageReport(2, None, None))
    second = replace(hours[0], info=info, disclosure=disclosure, source_audit=source_audit(info),
        source_hour=replace(source((info, disclosure, req.before), '45'), power_source_hour=2, workload_source_hour=102))
    hours += (second,)
    settings['budget'] = replace(settings['budget'], max_solver_calls=22, max_solver_seconds=22)
    req, arms, hours, settings = bind_inputs(req, arms, hours, settings)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentBidirectionalEpisode(root, req, arms, hours, **settings) as owner:
        owner.advance()
        owner.advance()
    expected = pins(root)
    def forbidden(*args, **kwargs): raise AssertionError('offline audit attempted execution')
    monkeypatch.setattr(ep.controller, 'supervise_selector', forbidden)
    report = audit.audit_episode(root, req, arms, hours, **settings, **expected)
    assert report['completed_hours'] == 2 and report['reserved_solver_calls'] == 22
    assert report['selected_phase_chains_replayed'] == 8
    assert report['unresolved_phase_records'] == 1
    extra = root/'000001_actual_1_non_authoritative'
    extra.mkdir()
    with pytest.raises(ValueError, match='directory inventory'):
        audit.audit_episode(root, req, arms, hours, **settings, **expected)
