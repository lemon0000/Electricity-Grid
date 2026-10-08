from dataclasses import replace
from copy import copy
import pytest

from test_rq2_hourly_zero_face_transaction_v1 import common, arm
from src.rq2_joint_deliverability_boundary_v1 import scale_episode_zero_face as ep


def inputs(tmp_path, zero=False):
    req, pub = common(tmp_path, zero=zero)
    setups = []
    from test_rq2_scale_selector_v1 import ACT, SPEC
    for name in ep.tx.ARMS:
        cursor, b = arm(req, pub, name)
        setups.append(ep.ArmSetup(cursor.business, cursor.grid, ACT, SPEC, b))
    h = ep.HourInput(req.info, req.disclosure, pub.source_hour, pub.source_audit, pub.mapping,
        pub.current.observation.limits, None if zero else 5, 1.)
    mib = 1024**2
    budget = ep.EpisodeBudget(11, 11, ep.controller.process.TaskProcessBudget(30., .1, 768*mib, 768*mib, 3.),
        32*mib, 16*mib, 16*mib, 8*mib, 2*mib,
        ep.resources.contract.TaskEnvelope('episode', 600, 60, 2048*mib, 512*mib, 256*mib, 1, 10000, 10000),
        1024*mib, 1024*mib, 10000)
    import os
    env = dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    return bind_inputs(req, tuple(setups), (h,), dict(budget=budget, environment=env))


def bind_inputs(req, arms, hours, settings):
    scale = ep.tx.scale
    work, contract = scale.legacy.execution_workload, ep.resources.contract
    declared_hours = tuple(h.info.current.source_hour for h in hours)
    audit, uids = hours[0].source_audit, req.budget.generator_uids
    normal = work.NormalWork('normal', audit.split, audit.normal_input_identity, uids, declared_hours, 1)
    task = work.EpisodeWork('episode', audit.split, 'normal', audit.normal_input_identity,
                            uids, declared_hours, 1, (1, 1, 1, 1))
    mib = 1024**2
    plan = ep.resources.EpisodeResourcePlan((normal,), (task,),
        (contract.TaskEnvelope('normal', 60, 30, 768*mib, 32*mib, 16*mib, 1, 10000, 10000), settings['budget'].envelope),
        contract.SerialResourceBudget(720, 60, 1024*mib, 16*mib, 4096*mib, 8*mib, 1024*mib, 1))
    def budget(role):
        return scale.legacy.budget_for_hour(plan.normals, plan.episodes, plan.envelopes, plan.serial_budget,
            task_id='episode', source_hour=declared_hours[0], role=role)
    b = budget('reference')
    req = replace(req, budget=b, expected_policy_identity=scale.policy_identity(req.selection_spec, req.solver_specification, b))
    rebound = []
    for index, arm in enumerate(arms):
        b, physical = budget('actual:'+str(index)), arm.grid.physical_origin
        grid = scale.initialize_actual_origin(req.info, physical.disclosure, grid_protocol=physical.protocol,
            generation_mw=physical.generation_mw, base_availability=physical.base_availability,
            selector=arm.selector, solver_specification=arm.specification, budget=b,
            expected_policy_identity=scale.policy_identity(arm.selector, arm.specification, b))
        rebound.append(replace(arm, grid=grid, budget=b))
    settings = dict(settings, resource_plan=plan)
    return req, tuple(rebound), hours, settings


def test_real_supervised_four_arm_hour(tmp_path):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        result = owned.advance()
        assert result['status'] == 'observation_window_consumed'
        assert result['reserved_solver_calls'] == 11
        assert [r['status'] for r in result['results']] == [
            'committed', 'physical_network_unresolved', 'committed', 'committed']
        assert [p['role'] for p in result['phase_evidence']] == ['reference', 'actual:0', 'actual:1', 'actual:2', 'actual:3']
        for phase in result['phase_evidence']:
            assert len(phase['files']) == 3
            assert len(phase['record_sha256']) == 64
        with pytest.raises(ValueError, match='consumed'): owned.advance()
        with pytest.raises(TypeError): copy(owned)
    assert len(list(root.glob('*_non_authoritative'))) == 5
    assert (root/'000000.intent.json').exists() and (root/'000000.result.json').exists()
    with pytest.raises((ValueError, FileExistsError)):
        ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings)


@pytest.mark.parametrize('fault', ['duplicate_arm', 'budget'])
def test_invalid_inventory_or_reservation_creates_no_root(tmp_path, fault):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    if fault == 'duplicate_arm': arms = (arms[0], arms[0], arms[2], arms[3])
    else: settings['budget'] = replace(settings['budget'], max_solver_calls=10)
    with pytest.raises(ValueError): ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings)
    assert not root.exists()


def test_interrupted_task_intent_poison_prevents_retry(tmp_path, monkeypatch):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        def stopped(*args): raise RuntimeError('injected task interruption')
        monkeypatch.setattr(owned, '_task', stopped)
        with pytest.raises(RuntimeError): owned.advance()
        with pytest.raises(ValueError, match='interrupted'): owned.advance()
        assert owned._publication is None and owned._index == 0
    assert (root/'000000.intent.json').exists() and not (root/'000000.result.json').exists()


def test_two_real_hours_skip_halted_arm_but_keep_full_reservation(tmp_path):
    from test_rq2_hourly_transaction_v1 import normal_source, view, current, source, audit
    from src.rq2_joint_deliverability_boundary_v1.event_disclosure import disclose_current, CurrentOutageReport
    req, arms, hours, settings = inputs(tmp_path)
    _, prepared = normal_source()
    info = view(prepared, replace(current(2, demand=20.), dc_baseline_mw=25.,
        dc_connected_capacity_mw=25., dc_physical_maximum_mw=30.))
    disclosure = disclose_current(hours[0].disclosure.after, CurrentOutageReport(2, None, None))
    hour = replace(source((info, disclosure, req.before), '45'), power_source_hour=2, workload_source_hour=102)
    second = replace(hours[0], info=info, disclosure=disclosure, source_hour=hour, source_audit=audit(info))
    settings['budget'] = replace(settings['budget'], max_solver_calls=22, max_solver_seconds=22)
    req, arms, hours, settings = bind_inputs(req, arms, hours+(second,), settings)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        first = owned.advance()
        result = owned.advance()
        assert result['reserved_solver_calls'] == result['reserved_solver_seconds'] == 22
        assert result['results'][1]['status'] == 'previously_halted'
        assert result['phase_evidence'][2] == dict(role='actual:1', status='skipped_previously_halted')
        assert owned._cursors[2].grid.physical_carry.source_hour == 2
        from fractions import Fraction
        assert owned._cursors[2].business.execution.tracks[0][1].ledger.debt == Fraction(2,3)
        assert first['status'] == 'advanced'
    assert len(list(root.glob('*_non_authoritative'))) == 9
    assert not (root/'000001_actual_1_non_authoritative').exists()


def test_late_task_failure_keeps_hour_unpublished(tmp_path, monkeypatch):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        original = owned._task
        def failed(name, request):
            if name == '000000_actual_1_non_authoritative':
                raise RuntimeError('late interruption')
            return original(name, request)
        monkeypatch.setattr(owned, '_task', failed)
        with pytest.raises(RuntimeError, match='late'): owned.advance()
        assert owned._cursors is None and owned._publication is None and owned._index == 0
        with pytest.raises(ValueError, match='interrupted'): owned.advance()
    assert (root/'000000_actual_0_non_authoritative'/'result.json').exists()
    assert not (root/'000000.result.json').exists()


def test_consumed_actual_archive_change_rejected(tmp_path):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        result = owned.advance()
        target = root/'000000_actual_0_non_authoritative'/'selector_non_authoritative'/'selector.sqlite3'
        original = target.read_bytes()
        # Test-created archive only: alter it in place while retaining inode.
        target.write_bytes(original+b'changed')
        with pytest.raises(ValueError, match='artifact drift'): owned.advance()
        assert result['phase_evidence'][1]['files'][str(target.relative_to(root))]['sha256'] != ep._file_pin(target)[1]


@pytest.mark.parametrize('filename', ['scale_selector_zero_face_store.py', 'scale_selector_zero_face_archive.py',
                                      'scale_selector_zero_face.py', 'scale_selector_zero_face_replay.py',
                                      'scale_episode_controller.py',
                                      'scale_selector_store.py', 'normal_task_process.py', 'normal_resources.py',
                                      'episode_store.py', 'continuous_grid_normal.py', 'execution_resource_contract.py'])
def test_dependency_drift_after_intent_precedes_job(tmp_path, monkeypatch, filename):
    from pathlib import Path
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        write = owned._write
        read = Path.read_bytes
        def changed(name, body):
            write(name, body)
            if name.endswith('.intent.json'):
                monkeypatch.setattr(Path, 'read_bytes', lambda p: read(p)+b' ' if p.name == filename else read(p))
        monkeypatch.setattr(owned, '_write', changed)
        with pytest.raises(ValueError, match='implementation drift'): owned.advance()
        assert not list(root.glob('*_non_authoritative'))


def test_environment_values_not_archived_and_close_requires_guard(tmp_path):
    req, arms, hours, settings = inputs(tmp_path)
    marker = 'synthetic-secret-not-for-artifacts-928'
    settings['environment']['EPISODE_TEST_TOKEN'] = marker
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        assert marker not in (root/'header.json').read_text(encoding='utf-8')
        owned._guard.acquire()
        try:
            with pytest.raises(ValueError, match='advancing'): owned.close()
        finally: owned._guard.release()
        owned._environment['EPISODE_TEST_TOKEN'] = 'changed'
        with pytest.raises(ValueError, match='environment drift'): owned.advance()
        assert not (root/'000000.intent.json').exists()


@pytest.mark.parametrize('filename', ['result.json', 'receipt_non_authoritative.json'])
def test_read_to_pin_crosslink_change_cannot_publish_hour(tmp_path, monkeypatch, filename):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    original = ep._file_pin
    changed = False
    def tamper(path):
        nonlocal changed
        if path.name == filename and not changed:
            changed = True
            body = ep.controller._read(path)
            body['extra'] = 'changed_after_consumption'
            path.write_bytes(ep.controller.worker.store._bytes(body))
        return original(path)
    monkeypatch.setattr(ep, '_file_pin', tamper)
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        with pytest.raises(ValueError, match='crosslink'): owned.advance()
        assert owned._index == 0
    assert not (root/'000000.result.json').exists()


def test_episode_deadline_prevents_new_intent(tmp_path):
    req, arms, hours, settings = inputs(tmp_path)
    root = tmp_path/'episode_non_authoritative'
    with ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings) as owned:
        owned._started -= settings['budget'].envelope.max_wall_seconds+1
        with pytest.raises(TimeoutError, match='elapsed'): owned.advance()
        assert not (root/'000000.intent.json').exists()
        assert not list(root.glob('*_non_authoritative'))


@pytest.fixture(scope='module')
def admission_inputs(tmp_path_factory):
    return inputs(tmp_path_factory.mktemp('mixed_episode_admission'))


@pytest.mark.parametrize('mode', ['execute', 'audit'])
@pytest.mark.parametrize('fault', ['old_request', 'before', 'power'])
def test_invalid_initial_request_rejected_before_root_io(tmp_path, admission_inputs, mode, fault):
    from src.rq2_joint_deliverability_boundary_v1 import scale_selector_store as old
    from src.rq2_joint_deliverability_boundary_v1 import scale_episode_zero_face_replay as replay
    req, arms, hours, settings = admission_inputs
    if fault == 'old_request': req = old.SelectorRequest(**vars(req))
    elif fault == 'before': req = replace(req, before=None)
    else: req = replace(req, power=ep.tx.PrescribedDcPower(1, '0', '1', 'mechanism_assumption'))
    root = tmp_path/'must_remain_absent_non_authoritative'
    with pytest.raises(ValueError, match='reference request'):
        if mode == 'execute':
            ep.DevelopmentMixedSelectorEpisode(root, req, arms, hours, **settings)
        else:
            replay.audit_episode(root, req, arms, hours, **settings, expected_header_sha256='0'*64,
                expected_intent_sha256s=(), expected_result_sha256s=(),
                expected_audit_identity=replay.implementation_identity())
    assert not root.exists()
