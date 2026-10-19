from dataclasses import replace
import pytest

from test_rq2_episode_bidirectional_v1 import inputs, bind_inputs
from src.rq2_joint_deliverability_boundary_v1 import scale_episode_bidirectional_controller as api


def setup(tmp_path):
    req, arms, hours, settings = inputs(tmp_path)
    packet = api.worker.transport.EpisodeInputs(req, arms, hours, settings['budget'], settings['resource_plan'])
    mib = 1024**2
    allocation = api.PipelineBudget(api.process.TaskProcessBudget(225., .05, 1536*mib, 2048*mib, 3.),
        api.process.TaskProcessBudget(90., .05, 1024*mib, 1024*mib, 3.), 30, 16*mib, 16*mib, 1024*mib, 11014, 1000)
    root = tmp_path/'pipeline_non_authoritative'
    kwargs = dict(allocation=allocation, environment=settings['environment'])
    return root, packet, dict(kwargs, expected_controller_identity=api.controller_identity(root, packet, **kwargs))


@pytest.mark.parametrize('declared_budget', [False, True])
def test_real_persistent_execute_audit_pipeline(tmp_path, monkeypatch, declared_budget):
    root, packet, settings = setup(tmp_path)
    if declared_budget:
        from dataclasses import asdict
        allocation = settings['allocation']
        def bound(b):
            return api.declared.DeclaredTaskProcessBudget(packet.reference_request.budget.resource_contract_identity,
                packet.budget.envelope, **asdict(b))
        settings['allocation'] = replace(allocation, execute=bound(allocation.execute), audit=bound(allocation.audit))
        settings['expected_controller_identity'] = api.controller_identity(root, packet,
            allocation=settings['allocation'], environment=settings['environment'])
    read, protected = api.base._read, []
    def held(path, identity=None):
        if path.name == 'audit_receipt_non_authoritative.json':
            with pytest.raises(ValueError, match='already held'):
                api.local._Lease(root/'episode_non_authoritative', False)
            protected.append(path)
        return read(path, identity)
    monkeypatch.setattr(api.base, '_read', held)
    result = api.supervise_episode(root, packet, **settings)
    assert protected
    assert result['status'] == 'observed_window_replayed'
    assert [p['mode'] for p in result['phases']] == ['execute', 'audit']
    assert all(p['observation']['whole_job_quiescent'] for p in result['phases'])
    assert result['audit']['selected_phase_chains_replayed'] == 4
    assert result['audit']['unresolved_phase_records'] == 1
    assert result['audit']['solver_calls_by_auditor'] == 0
    assert not result['whole_task_resources_verified'] and not result['complete_service_certified']
    for mode in ('execute', 'audit'):
        assert all((root/(mode+'_'+name+'.json')).is_file() for name in ('intent', 'launch', 'observation'))
    with pytest.raises((ValueError, FileExistsError)): api.supervise_episode(root, packet, **settings)


def test_episode_allowance_must_equal_original_resource_plan(tmp_path):
    root, packet, settings = setup(tmp_path)
    packet = replace(packet, budget=replace(packet.budget, max_solver_calls=12, max_solver_seconds=13))
    with pytest.raises(ValueError, match='episode total differs from original resource plan'):
        api.controller_identity(root, packet,
            allocation=settings['allocation'], environment=settings['environment'])
    assert not root.exists()


@pytest.mark.parametrize('fault', ['execute_wall', 'total_wall', 'job', 'archive', 'scratch'])
def test_incomplete_pipeline_allocation_rejected(tmp_path, fault):
    root, packet, settings = setup(tmp_path)
    allocation = settings['allocation']
    if fault == 'execute_wall': allocation = replace(allocation, execute=replace(allocation.execute, max_elapsed_seconds=224.))
    elif fault == 'total_wall': allocation = replace(allocation, controller_seconds=600)
    elif fault == 'job': allocation = replace(allocation, execute=replace(allocation.execute, max_job_commit_bytes=1536*1024**2))
    elif fault == 'archive':
        envelope = replace(packet.budget.envelope, archive_bytes=300*1024**2)
        req, arms, hours, rebound = bind_inputs(packet.reference_request, packet.arms, packet.hours,
            dict(budget=replace(packet.budget, envelope=envelope), environment=settings['environment']))
        packet = api.worker.transport.EpisodeInputs(req, arms, hours, rebound['budget'], rebound['resource_plan'])
    else: allocation = replace(allocation, execute_scratch_bytes=packet.budget.envelope.scratch_bytes)
    with pytest.raises(ValueError): api.controller_identity(root, packet, allocation=allocation, environment=settings['environment'])
    assert not root.exists()


@pytest.mark.parametrize('name', ['execute_intent.json', 'execute_launch.json'])
def test_durable_record_failure_prevents_worker_release(tmp_path, monkeypatch, name):
    root, packet, settings = setup(tmp_path)
    original = api.base._write
    def failed(path, body):
        if path.name == name: raise OSError('injected durable failure')
        return original(path, body)
    monkeypatch.setattr(api.base, '_write', failed)
    with pytest.raises(OSError, match='injected'): api.supervise_episode(root, packet, **settings)
    assert not (root/'episode_non_authoritative').exists()
    assert not (root/'result.json').exists()


def test_controller_allowance_cannot_borrow_unused_worker_time(tmp_path, monkeypatch):
    root, packet, settings = setup(tmp_path)
    original, clock = api.base._write, api.time.monotonic
    def written(path, body):
        result = original(path, body)
        if path.name == 'request.json': monkeypatch.setattr(api.time, 'monotonic', lambda: clock()+31.)
        return result
    monkeypatch.setattr(api.base, '_write', written)
    with pytest.raises(TimeoutError, match='controller allowance'):
        api.supervise_episode(root, packet, **settings)
    assert not (root/'execute_intent.json').exists()


def test_entry_budget_covers_internal_and_outer_inventory(tmp_path):
    root, packet, settings = setup(tmp_path)
    allocation = replace(settings['allocation'], max_tree_entries=11013)
    with pytest.raises(ValueError, match='entry allocation'):
        api.controller_identity(root, packet, allocation=allocation, environment=settings['environment'])
    assert not root.exists()


@pytest.mark.parametrize('fault', ['pin', 'envelope'])
def test_declared_outer_budget_must_bind_the_actual_resource_plan(tmp_path, fault):
    from dataclasses import asdict
    root, packet, settings = setup(tmp_path)
    allocation = settings['allocation']
    bound = api.declared.DeclaredTaskProcessBudget(packet.reference_request.budget.resource_contract_identity,
        packet.budget.envelope, **asdict(allocation.execute))
    if fault == 'pin': bound = replace(bound, resource_contract_identity='f'*64)
    else: bound = replace(bound, envelope=replace(bound.envelope, max_wall_seconds=601))
    with pytest.raises(ValueError, match='original episode resource declaration'):
        api.controller_identity(root, packet, allocation=replace(allocation, execute=bound), environment=settings['environment'])
    assert not root.exists()


@pytest.mark.parametrize('field,value', [('exit_code', False), ('stop_markers', ('extra',)),
    ('formal_result', True), ('job_commit_limits_configured', False), ('runtime_samples', True),
    ('job_peak_total_commit_bytes', 10**15), ('elapsed_seconds', float('nan'))])
def test_forged_success_observations_are_rejected(tmp_path, field, value):
    mib = 1024**2
    budget = api.process.TaskProcessBudget(5., .1, mib, 2*mib, 1.)
    host = api.process.resources.HostResourceBudget(2*mib, mib,
        (api.process.resources.DirectoryDemand('root', str(tmp_path), mib, mib),))
    volume = api.process.resources._directory_binding(str(tmp_path))[3]
    observed = api.process.TaskProcessObservation('a'*64, 123, 456, 0, 'child_exited', 1., 2,
        3*mib, ((volume, 3*mib),), (), None, ('direct_child_exit_observed',), 123, 456, True)
    api._successful_observation(observed, budget, host)
    with pytest.raises(ValueError): api._successful_observation(replace(observed, **{field: value}), budget, host)


def test_nested_scratch_and_prospective_parent_write_counted(tmp_path, monkeypatch):
    from types import SimpleNamespace as NS
    (tmp_path/'execute_scratch').mkdir()
    (tmp_path/'execute_scratch'/'tmp').write_bytes(b'12')
    inner = tmp_path/'episode_non_authoritative'/'phase_non_authoritative'/'scratch'
    inner.mkdir(parents=True)
    (inner/'tmp').write_bytes(b'123')
    (tmp_path/'request.json').write_bytes(b'1234')
    packet = NS(budget=NS(envelope=NS(max_wall_seconds=60, archive_bytes=4, scratch_bytes=5)))
    budget = NS(max_supervisor_peak_working_set_bytes=100, max_tree_entries=20, max_outer_scratch_entries=1,
                execute_scratch_bytes=2, audit_scratch_bytes=1)
    monkeypatch.setattr(api.worker.episode.resources.memory, '_peak_working_set_bytes', lambda: 50)
    report = api._measure(tmp_path, packet, budget, api.time.monotonic())
    assert (report['archive_logical_bytes'], report['scratch_logical_bytes']) == (4, 5)
    with pytest.raises(ValueError, match='byte cap'): api._measure(tmp_path, packet, budget, api.time.monotonic(), 1)
    budget.execute_scratch_bytes = 1
    with pytest.raises(ValueError, match='scratch byte allocation'): api._measure(tmp_path, packet, budget, api.time.monotonic())


def test_phase_host_demand_does_not_count_retained_bytes_twice(tmp_path):
    from types import SimpleNamespace as NS
    packet = NS(budget=NS(envelope=NS(archive_bytes=100, scratch_bytes=80, max_job_commit_bytes=10)),
                resource_plan=NS(serial_budget=NS(supervisor_additional_commit_bytes=2,
                    commit_reserve_bytes=1, disk_reserve_bytes=1)))
    allocation = NS(execute_scratch_bytes=20, audit_scratch_bytes=30)
    usage = dict(archive_logical_bytes=40, scratch_logical_bytes=10, audit_scratch_logical_bytes=5)
    host = api._host(tmp_path, packet, allocation, tmp_path/'audit_scratch', usage)
    assert tuple(d.additional_bytes for d in host.directories) == (105, 25)
    assert sum(d.additional_bytes for d in host.directories) == 180-40-10


def test_late_evidence_close_error_still_releases_pipeline_lease(tmp_path, monkeypatch):
    root, packet, settings = setup(tmp_path)
    close = api.local._Lease.close
    def failed(lease):
        close(lease)
        if lease.root == root/'episode_non_authoritative' and (root/'result.json').exists():
            raise OSError('injected late evidence close')
    monkeypatch.setattr(api.local._Lease, 'close', failed)
    with pytest.raises(OSError, match='late evidence close'): api.supervise_episode(root, packet, **settings)
    lease = api.local._Lease(root, False)
    close(lease)
