from copy import deepcopy
from dataclasses import asdict, replace
from hashlib import sha256
from pathlib import Path
import os
from types import SimpleNamespace

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v2 as api
from tests.test_rq2_normal_h1_full_collector_v2 import inputs
from tests.test_rq2_normal_h1_hour_archive_v1 import saved, no_solver

VERIFY_CONSUMED = api.gates.verify_consumed


@pytest.fixture(autouse=True)
def mocked_consumed_gate_with_solver_forbidden(no_solver, monkeypatch):
    monkeypatch.setattr(api.gates, 'verify_consumed', lambda gate: gate['test_request'])


def settings():
    packet, work, resource, serial, limits = inputs()
    plan = api.collector.resources.check_plan((work,), (resource,), serial)
    job = api.process.DeclaredTaskProcessBudget(plan['declaration_identity'], resource.envelope,
        98., .02, 1000, 1000, 2.)
    return packet, work, resource, serial, limits, job


def request(tmp_path):
    packet, work, resource, serial, limits, job = settings()
    root = tmp_path / 'job_non_authoritative'
    return dict(schema=api.SCHEMA, implementation_identity=api.implementation_identity(),
        work=asdict(work), resource=asdict(resource), serial_budget=asdict(serial), limits=asdict(limits),
        job_budget=asdict(job), root=str(root), source_declaration=dict(split='training', power_raw_hour=0,
        workload_raw_hour=0, outage_seed=1, config_sha256='1'*64), source_identity='2'*64,
        network_identity=packet.network.identity, upstream_root=str(tmp_path), config_path=str(tmp_path/'config'), dc_bus=1)


def write_request(tmp_path):
    value = request(tmp_path)
    root = Path(value['root'])
    root.mkdir()
    (root/'scratch_non_authoritative').mkdir()
    pin = api._write(root/'request.json', value)
    plan = api._configuration(value)[-1]
    api._write(root/'intent.json', dict(schema=api.SCHEMA, request_sha256=pin,
        implementation_identity=value['implementation_identity'], resource_declaration_identity=plan['declaration_identity'],
        formal_result=False))
    return value, root, pin


def test_declaration_roundtrip_and_public_gate(tmp_path):
    value = request(tmp_path)
    assert api._configuration(value)[:5] == settings()[1:]
    with pytest.raises(ValueError, match='sealed calibration'):
        api.run_job(tmp_path, value)
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('fault', ['pin', 'envelope', 'short_job', 'job_memory', 'stages', 'variables', 'hours'])
def test_full_job_binding_fails_before_files(fault):
    _, work, resource, serial, limits, job = settings()
    if fault == 'pin': job = replace(job, resource_contract_identity='9'*64)
    elif fault == 'envelope': job = replace(job, envelope=replace(job.envelope, archive_bytes=job.envelope.archive_bytes+1))
    elif fault == 'short_job': job = replace(job, max_elapsed_seconds=97.)
    elif fault == 'job_memory': job = replace(job, max_process_commit_bytes=900, max_job_commit_bytes=900)
    elif fault == 'stages': limits = replace(limits, max_stages=4)
    elif fault == 'variables': limits = replace(limits, max_variables=101)
    elif fault == 'hours': work = replace(work, hours=2)
    with pytest.raises(ValueError): api.bind_job(work, resource, serial, limits, job)


def test_worker_saved_raw_chain_fresh_reopen_and_source_check(tmp_path, saved, monkeypatch):
    value, root, pin = write_request(tmp_path)
    monkeypatch.chdir(root/'scratch_non_authoritative')
    calls, sources = [], []
    def packet(_):
        sources.append(1)
        return settings()[0]
    def solve(*a, **kw):
        calls.append(kw)
        return saved[1][len(calls)-1]
    monkeypatch.setattr(api, '_packet', packet)
    monkeypatch.setattr(api.collector.base.native.capture, 'solve_once', solve)
    report = api._execute_development_worker(root/'request.json', pin, _gate={'test_request': value})
    assert report['summary']['status'] == 'accepted'
    assert report['summary']['stored_reports'] == report['summary']['solver_calls'] == 3
    assert len(calls) == 3 and len(sources) == 4
    assert report['fresh_reopen_equal'] and report['solver_calls_by_replay'] == 0
    api._validate_report(report, pin, api._configuration(value)[-1])
    with pytest.raises((ValueError, FileExistsError)):
        api._execute_development_worker(root/'request.json', pin, _gate={'test_request': value})
    assert len(calls) == 3


@pytest.mark.parametrize('fault', ['pin', 'implementation', 'intent', 'cwd'])
def test_worker_preconditions_never_reach_packet(tmp_path, monkeypatch, fault):
    value, root, pin = write_request(tmp_path)
    monkeypatch.chdir(root/'scratch_non_authoritative')
    monkeypatch.setattr(api, '_packet', lambda *_: pytest.fail('invalid request reached source'))
    if fault == 'pin': pin = '0'*64
    elif fault == 'implementation': monkeypatch.setattr(api, 'implementation_identity', lambda: '0'*64)
    elif fault == 'intent': (root/'intent.json').write_bytes(b'{}')
    elif fault == 'cwd': monkeypatch.chdir(tmp_path)
    with pytest.raises(ValueError): api._execute_development_worker(root/'request.json', pin, _gate={'test_request': value})


def good_report(pin, plan):
    return dict(schema=api.SCHEMA, request_sha256=pin, summary=dict(status='accepted', registry_head='1'*64,
        child_head='2'*64, stored_reports=3, solver_calls=3, projection_identity='3'*64, anchor_record_sha256='4'*64,
        collector_identity='5'*64, resource_declaration_identity=plan['declaration_identity']), fresh_reopen_equal=True,
        solver_calls_by_replay=0, whole_task_resources_verified=False, formal_execution_ready=False, formal_result=False,
        native_execution_authenticated=False)


@pytest.mark.parametrize('fault', ['extra', 'authority', 'calls', 'count', 'projection', 'resource', 'replay', 'fresh', 'status'])
def test_worker_claims_fail_closed(tmp_path, fault):
    plan = api._configuration(request(tmp_path))[-1]
    report = good_report('8'*64, plan)
    if fault == 'extra': report['extra'] = False
    elif fault == 'authority': report['formal_result'] = True
    elif fault == 'calls': report['summary']['solver_calls'] = True
    elif fault == 'count': report['summary']['stored_reports'] = 2
    elif fault == 'projection': report['summary']['projection_identity'] = None
    elif fault == 'resource': report['summary']['resource_declaration_identity'] = '0'*64
    elif fault == 'replay': report['solver_calls_by_replay'] = False
    elif fault == 'fresh': report['fresh_reopen_equal'] = 1
    elif fault == 'status': report['summary']['status'] = 'infeasible'
    with pytest.raises(ValueError): api._validate_report(report, '8'*64, plan)


@pytest.mark.parametrize('fault', ['none', 'deadline', 'not_quiet', 'exit', 'receipt', 'release',
    'identity', 'pid', 'creation', 'type', 'bool_quiet', 'bool_limits', 'authority', 'bool_peak', 'list_errors'])
def test_controller_reads_only_after_clean_quiescence_and_never_retries(tmp_path, monkeypatch, fault):
    from contextlib import contextmanager
    value = request(tmp_path)
    root = Path(value['root'])
    state = dict(quiet=False, closed=False, launches=0)
    monkeypatch.setenv('H1_TEST_UNAUTHORIZED_SECRET', 'must-not-enter-child')
    real_read = api._read
    def read(path, *args):
        if Path(path).name == 'worker_result.json':
            assert state['quiet'] and state['closed']
        return real_read(path, *args)
    monkeypatch.setattr(api, '_read', read)
    @contextmanager
    def child(*argv, **kw):
        state['launches'] += 1
        assert (root/'intent.json').is_file() and (root/'launch_intent.json').is_file()
        host = kw['host_budget']
        assert 'H1_TEST_UNAUTHORIZED_SECRET' not in kw['environment']
        assert kw['environment']['TEMP'] == kw['environment']['TMP'] == str(root/'scratch_non_authoritative')
        assert all(kw['environment'][name] == '1' for name in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS'))
        assert host.additional_commit_bytes == 1100
        assert sum(d.additional_bytes for d in host.directories) == value['resource']['envelope']['archive_bytes']+100
        owner = SimpleNamespace(pid=123, creation_filetime=456,
            initial_observation=api.process.legacy.resources.CommitObservation(1, 100, 1000))
        def release():
            assert (root/'child_identity.json').is_file()
            if fault == 'release': raise RuntimeError('release failed')
        def wait():
            state['quiet'] = fault != 'not_quiet'
            pin = sha256((root/'request.json').read_bytes()).hexdigest()
            report = good_report(pin, api._configuration(value)[-1])
            if fault == 'receipt': report['formal_result'] = True
            api._write(root/'worker_result.json', report)
            observation = api.process.legacy.TaskProcessObservation(kw['expected_process_identity'], 123, 456, 2 if fault=='exit' else 0,
                'task_deadline_stop' if fault=='deadline' else 'child_exited', 1., 1, 100000, (), (), None,
                (), 100, 100, state['quiet'])
            if fault == 'identity': observation = replace(observation, process_identity='0'*64)
            elif fault == 'pid': observation = replace(observation, pid=124)
            elif fault == 'creation': observation = replace(observation, creation_filetime=457)
            elif fault == 'type': observation = SimpleNamespace(**asdict(observation))
            elif fault == 'bool_quiet': observation = replace(observation, whole_job_quiescent=1)
            elif fault == 'bool_limits': observation = replace(observation, job_commit_limits_configured=1)
            elif fault == 'authority': observation = replace(observation, whole_task_resources_verified=True)
            elif fault == 'bool_peak': observation = replace(observation, job_peak_process_commit_bytes=True)
            elif fault == 'list_errors': observation = replace(observation, last_resource_errors=[])
            return observation
        owner.release, owner.wait = release, wait
        try: yield owner
        finally: state['closed'] = True
    monkeypatch.setattr(api.process, 'declared_task_child', child)
    if fault == 'none':
        assert api._run_development_job(root, value, _gate={'test_request': value})['summary']['status'] == 'accepted'
        assert (root/'job_checks.json').is_file()
    else:
        with pytest.raises((ValueError, RuntimeError)): api._run_development_job(root, value, _gate={'test_request': value})
        assert not (root/'job_checks.json').exists()
    with pytest.raises((ValueError, FileExistsError)): api._run_development_job(root, value, _gate={'test_request': value})
    assert state['launches'] == 1 and state['closed']
    if fault not in ('release', 'type'):
        assert (root/'process_observation.json').is_file()
    if fault == 'type': assert (root/'observation_failure.json').is_file()


@pytest.mark.parametrize('field', ['whole_task_resources_verified', 'formal_execution_ready'])
def test_outer_collector_authority_cannot_be_silently_downgraded(field):
    item = api.source.h1._owned(api.collector.H1FullCollectorInspection,
        full_collector_identity='1'*64, resource_declaration_identity='2'*64, inspection=None,
        whole_task_resources_verified=False, formal_execution_ready=False)
    object.__setattr__(item, field, True)
    with pytest.raises(ValueError, match='outer collector authority'): api._summary(item, '3'*64)


@pytest.mark.skipif(os.name != 'nt', reason='real Windows Job integration')
@pytest.mark.parametrize('crash', [False, True])
def test_real_job_saved_reports_or_process_death_preserves_attempt(tmp_path, monkeypatch, crash):
    """A test-only worker uses retained raw bytes; it never creates a solver."""
    worker = tmp_path/'saved_raw_worker.py'
    from datetime import datetime
    p = settings()[0]
    row = replace(p.inputs.data.hourly_points[0], timestamp=datetime.fromisoformat(p.source_timestamp))
    sample = api.ROOT/'results/tables/rq2_normal_h1_projection_store_v1_non_authoritative/sample_archive.json'
    worker.write_text(
        'import sys, os, json, datetime\nfrom pathlib import Path\n'
        f'sys.path.insert(0, {str(api.ROOT)!r})\n'
        'from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v2 as api\n'
        'from src.grid.rts_gmlc import *\nimport datetime\n'
        'api.WORKER=Path(__file__)\n'
        f'data={p.network.data!r}\nrow={row!r}\n'
        'api._packet=lambda request: api.source.h1.assemble_current_normal(api.source.h1.static_network(data),'
        'row, "0", relative_hour=0, dc_bus=1, source_time_basis="naive_source_labelled_utc")\n'
        f'rows=iter(json.loads(Path({str(sample)!r}).read_bytes())["reports"])\n'
        'def solve(*args, **kwargs):\n'
        + ('    os._exit(23)\n' if crash else '    return next(rows).encode("ascii")\n')
        + 'api.collector.base.native.capture.solve_once=solve\n'
        'api.gates.verify_consumed=lambda gate: gate["test_request"]\n'
        'try: api._execute_development_worker(sys.argv[1], sys.argv[2], _gate=json.loads(Path(sys.argv[3]).read_bytes()))\n'
        'except BaseException:\n'
        '    import traceback\n'
        '    Path("test_error.txt").write_text(traceback.format_exc())\n'
        '    raise\n', encoding='utf-8')
    monkeypatch.setattr(api, 'WORKER', worker)
    value = request(tmp_path)
    _, work, resource, serial, limits, _ = settings()
    mib = 1024**2
    resource = replace(resource, archive_overhead_bytes=8*mib,
        envelope=replace(resource.envelope, max_wall_seconds=120, non_solver_seconds=117,
            max_job_commit_bytes=512*mib, archive_bytes=resource.envelope.archive_bytes+8*mib, scratch_bytes=8*mib))
    serial = replace(serial, max_total_wall_seconds=130, supervisor_additional_commit_bytes=64*mib,
        commit_reserve_bytes=64*mib, max_additional_commit_bytes=640*mib, disk_reserve_bytes=8*mib,
        max_additional_disk_bytes=resource.envelope.archive_bytes+16*mib)
    plan = api.collector.resources.check_plan((work,), (resource,), serial)
    job = api.process.DeclaredTaskProcessBudget(plan['declaration_identity'], resource.envelope, 118., .25,
        512*mib, 512*mib, 2.)
    value.update(resource=asdict(resource), serial_budget=asdict(serial), job_budget=asdict(job))
    root = Path(value['root'])
    if crash:
        with pytest.raises(ValueError, match='unresolved'): api._run_development_job(root, value, _gate={'test_request': value})
        assert not (root/'worker_result.json').exists()
        assert (root/'anchor_non_authoritative'/'001.json').exists()
    else:
        report = api._run_development_job(root, value, _gate={'test_request': value})
        assert report['summary']['status']=='accepted' and report['summary']['solver_calls']==3
    observation, _ = api._read(root/'process_observation.json')
    assert observation['whole_job_quiescent'] is True
    assert observation['job_commit_limits_configured'] is True
    assert observation['exit_code'] == (23 if crash else 0)
    with pytest.raises((ValueError, FileExistsError)): api._run_development_job(root, value, _gate={'test_request': value})


@pytest.mark.parametrize('entry', ['worker', 'supervisor'])
def test_shared_core_has_no_ungated_native_path(tmp_path, monkeypatch, entry):
    monkeypatch.setattr(api.gates, 'verify_consumed', VERIFY_CONSUMED)
    if entry == 'worker':
        call = lambda: api._execute_development_worker(tmp_path/'missing.json', '0'*64)
    else:
        call = lambda: api._run_development_job(tmp_path/'new', {})
    with pytest.raises(ValueError, match='seal/review/run-authority'): call()
    assert not list(tmp_path.iterdir())
