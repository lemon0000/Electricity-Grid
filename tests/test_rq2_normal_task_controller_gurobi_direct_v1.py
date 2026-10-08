"""Development controller tests; positive source boundary is explicitly synthetic."""
from contextlib import contextmanager
from dataclasses import asdict, fields, replace
from hashlib import sha256
import os
from pathlib import Path
import sys
import subprocess
import time

import pytest

from test_rq2_normal_task_worker_gurobi_direct_v1 import supplied, task, prepared_source, bound_source, source_supplied
from src.rq2_joint_deliverability_boundary_v1 import normal_task_controller_gurobi_direct as api


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows controller and Jobs')
MIB = 1024**2


@pytest.fixture
def configured(task):
    task = replace(task, max_replay_bytes=MIB)
    phase = api.process.TaskProcessBudget(30., .05, 384*MIB, 384*MIB, 3.)
    budget = api.NormalTaskBudget(phase, phase, api.capture.ArchiveCaptureBudget(32*MIB, task.max_record_bytes, 5.),
        150., 10., 768*MIB, 16*MIB, 32*MIB, 72*MIB, 4*MIB, MIB, 512)
    return task, budget, api.worker.codec.development_environment()


def run(root, configured):
    task, budget, env = configured
    return api.supervise_normal_task(root, task, budget=budget, environment=env,
        expected_controller_identity=api.controller_identity(root, task, budget, env))


def synthetic_bootstrap(tmp_path, supplied, monkeypatch, mode='normal'):
    fixture = tmp_path/'synthetic_source_fixture.json'
    request = supplied[0]
    legacy = api.worker.inputs.source_normal.legacy
    binder = api.worker.inputs.stream_binding
    payload = (legacy.load_rts_gmlc_chronological_data(request.upstream_root),
        binder.source_pair.prepare_source_pair(), binder.source_window.load_source_window(),
        legacy.RTS_GMLC_MANIFEST_SHA256)
    fixture.write_bytes(api.journal._bytes(api.worker.kernel._encode(payload)))
    original = api.worker.worker_argv
    def command(path, digest):
        argv = original(path, digest)
        script = f"""
import sys
sys.path.insert(0,{str(api.worker.ROOT)!r})
from pathlib import Path
from types import SimpleNamespace
from src.rq2_joint_deliverability_boundary_v1 import normal_task_worker_gurobi_direct as w
data,pair,window,manifest=w.codec._decode(w.journal._decoded(Path({str(fixture)!r}).read_bytes()))
from copy import deepcopy
legacy=w.inputs.source_normal.legacy
legacy.RTS_GMLC_MANIFEST_SHA256=manifest
legacy.verify_sha256_manifest=lambda root:True
legacy.load_rts_gmlc_chronological_data=lambda root:deepcopy(data)
binder=w.inputs.stream_binding
binder.source_pair.prepare_source_pair=lambda *a,**k:deepcopy(pair)
binder.source_window.load_source_window=lambda *a,**k:deepcopy(window)
binder.source_window.audit._load_config=lambda *a:{{'inputs':{{'power':{{}}}}}}
binder.source_window.audit._verify_package=lambda *a:(None,{{'grid_source_manifest_sha256':manifest}})
binder.source_window.audit._verify_hash=lambda *a:None
fixed_argv=list(sys.orig_argv)
w.worker_argv=lambda *a:fixed_argv
if Path(sys.argv[1]).name.startswith('replay'):
 def forbidden(*a,**k): raise AssertionError('independent replay may not solve')
 w.kernel.native.create_solver=forbidden
 w.kernel.run_normal_only=forbidden
 w.journal.execution.source.run_source_normal=forbidden
"""
        if mode == 'after_normal_intent':
            script += """
original=w.journal.DevelopmentDeclaredGurobiDirectNormalStore._append
def append(self,raw=None):
 original(self,raw)
 if raw is None: w.os._exit(19)
w.journal.DevelopmentDeclaredGurobiDirectNormalStore._append=append
"""
        if mode == 'zero_without_claim': script += 'raise SystemExit(0)\n'
        if mode in ('prepare_pause', 'intent_pause', 'result_pause', 'replay_pause'):
            script += """
import time
def pause():
 Path('waiting').write_text(str(w.os.getpid()))
 while True: time.sleep(.02)
"""
            if mode in ('prepare_pause', 'replay_pause'):
                condition = "True" if mode == 'prepare_pause' else "Path(sys.argv[1]).name.startswith('replay')"
                script += 'if '+condition+': w.inputs.prepare_task_inputs=lambda *a,**k:pause()\n'
            else:
                condition = 'raw is None' if mode == 'intent_pause' else 'raw is not None'
                script += '\noriginal=w.journal.DevelopmentDeclaredGurobiDirectNormalStore._append\ndef append(self,raw=None):\n original(self,raw)\n if '+condition+': pause()\nw.journal.DevelopmentDeclaredGurobiDirectNormalStore._append=append\n'
        script += """
try: w.main()
except BaseException:
 import traceback
 Path('bootstrap_error.txt').write_text(traceback.format_exc())
 raise
"""
        argv[4] = script
        return argv
    monkeypatch.setattr(api.worker, 'worker_argv', command)
    return command


def test_two_real_jobs_capture_then_independent_replay(tmp_path, supplied, configured, monkeypatch):
    synthetic_bootstrap(tmp_path, supplied, monkeypatch)
    root = tmp_path/'two_jobs_non_authoritative'
    result = run(root, configured)
    errors = [(p.name, p.read_text()) for p in root.glob('*_non_authoritative/bootstrap_error.txt')]
    assert result.status == 'completed_development_replay_diagnostic', (result, errors)
    assert result.accepted_record_reproduced and result.replay_status == 'replayed_accepted_declared_normal_record'
    assert len(result.phases) == 2 and all(p.whole_job_quiescent and p.exit_code == 0 for p in result.phases)
    assert not any((result.whole_task_resources_verified, result.hard_disk_quota_enforced,
        result.native_execution_authenticated, result.formal_result))
    captured = api.worker._read(root/'retained_pins.json')
    replay_packet = api.worker._read(root/'replay.request.json')
    assert replay_packet['replay_pins']['record_sha256'] == captured['record_sha256']
    assert replay_packet['replay_pins']['head'] == captured['head']
    assert api.worker._read(root/'final_pins.json') == captured
    assert api.worker._read(root/'capture.supervision.json') == api.worker._read(root/'recapture.supervision.json')
    first = api.worker._read(root/'execute.supervision.json')['host_budget']
    second = api.worker._read(root/'replay.supervision.json')['host_budget']
    assert first['directories'][0]['additional_bytes'] > second['directories'][0]['additional_bytes']
    assert first['additional_commit_bytes'] == second['additional_commit_bytes'] == 384*MIB
    assert (root/'controller.observation.json').exists()
    assert api.worker._read(root/'controller.observation.json')['status'] == 'validated_before_final_observation_write'
    with pytest.raises(FileExistsError): run(root, configured)


def test_real_fixed_entry_missing_source_stays_unresolved(tmp_path, configured):
    root = tmp_path/'missing_non_authoritative'
    result = run(root, configured)
    assert result.status == 'unresolved_task_attempt' and result.stopped_phase == 'execute'
    assert len(result.phases) == 1 and result.phases[0].whole_job_quiescent
    assert result.phases[0].exit_code != 0 and (root/'execute.claim.json').exists()
    assert not (root/'retained_pins.json').exists() and not (root/'replay.intent.json').exists()


@pytest.mark.parametrize('mode', ['after_normal_intent', 'zero_without_claim'])
def test_child_exit_windows_never_capture_or_retry(tmp_path, supplied, configured, monkeypatch, mode):
    synthetic_bootstrap(tmp_path, supplied, monkeypatch, mode)
    root = tmp_path/'exit_non_authoritative'
    result = run(root, configured)
    assert result.status == 'unresolved_task_attempt'
    assert len(result.phases) == 1 and result.phases[0].whole_job_quiescent
    assert not (root/'retained_pins.json').exists() and not (root/'replay.intent.json').exists()
    if mode == 'after_normal_intent':
        import sqlite3
        with sqlite3.connect(root/'normal_non_authoritative'/'normal.sqlite3') as con:
            assert con.execute('SELECT count(*) FROM intent').fetchone() == (1,)
            assert con.execute('SELECT count(*) FROM result').fetchone() == (0,)
    with pytest.raises(FileExistsError): run(root, configured)


@pytest.mark.parametrize('fault', ['intent_write', 'launch_write', 'unconfirmed_quiet', 'reservation'])
def test_controller_failure_before_result_never_reads_archive(tmp_path, configured, monkeypatch, fault):
    root = tmp_path/'fault_non_authoritative'
    calls = []
    @contextmanager
    def fake_child(*a, **k):
        calls.append('spawn')
        class Child:
            pid, creation_filetime = 1, 2
            def release(self): calls.append('release')
            def wait(self):
                return api.process.TaskProcessObservation('1'*64, 1, 2, 0, 'child_exited', .01,
                    1, MIB, (), (), None, (), MIB, MIB, False)
        yield Child()
    monkeypatch.setattr(api.process, 'normal_task_child', fake_child)
    monkeypatch.setattr(api.capture, 'capture_normal_archive', lambda *a, **k:
        (_ for _ in ()).throw(AssertionError('unconfirmed phase must not read archive')))
    if fault in ('intent_write', 'launch_write'):
        original = api.worker._write
        suffix = 'execute.intent.json' if fault == 'intent_write' else 'execute.launch.json'
        def write(path, *a, **k):
            if path.name == suffix: raise OSError('injected write failure')
            return original(path, *a, **k)
        monkeypatch.setattr(api.worker, '_write', write)
    if fault == 'reservation':
        task, budget, env = configured
        configured = task, replace(budget, max_total_elapsed_seconds=10.), env
    result = run(root, configured)
    assert result.status == 'unresolved_task_attempt' and not result.archive_pins
    if fault in ('intent_write', 'reservation'): assert calls == []
    if fault == 'launch_write': assert calls == ['spawn']
    if fault == 'unconfirmed_quiet': assert calls == ['spawn', 'release']
    with pytest.raises(FileExistsError): run(root, configured)


def test_report_cap_refused_before_creating_root(tmp_path, configured):
    task, budget, env = configured
    root = tmp_path/'large_report_non_authoritative'
    with pytest.raises(ValueError, match='budgets disagree'):
        run(root, (replace(task, max_replay_bytes=MIB+1), budget, env))
    assert not root.exists()


@pytest.mark.parametrize('fault', ['unknown', 'hardlink', 'scratch_size', 'entry_count'])
def test_task_tree_inventory_and_byte_bounds(tmp_path, configured, fault):
    task, budget, _ = configured
    root = tmp_path/'tree_non_authoritative'
    root.mkdir()
    scratch = root/'execute_non_authoritative'
    scratch.mkdir()
    if fault == 'unknown': (root/'unexpected').write_bytes(b'x')
    if fault == 'hardlink':
        source = scratch/'file'
        source.write_bytes(b'x')
        os.link(source, scratch/'alias')
    if fault == 'scratch_size': (scratch/'file').write_bytes(b'x'*(budget.scratch_bytes_per_phase+1))
    if fault == 'entry_count':
        budget = replace(budget, max_tree_entries=1)
        (scratch/'file').write_bytes(b'x')
    with pytest.raises(ValueError): api._tree_bytes(root, task, budget, lambda: None)


def source_diagnostic_wire(task, state='accepted'):
    """Synthetic wire for controller validation only, not numerical evidence."""
    accepted, consistent = state == 'accepted', state != 'inconsistent'
    native = dict(model_structure_identity='a'*64, scope='complete_native_record', replay_consistent=True,
        assignment_recomputed=True, canonical_assignment_valid=True, recomputed_objective=0.,
        recomputed_maximum_residual=0., recomputed_maximum_integrality_violation=0., reported_optimal=True,
        reported_native_infeasible=False, optimal_flag_reproduced=True, native_infeasible_flag_reproduced=False,
        recorded_execution_errors=[], replay_errors=[])
    values = dict(record_sha256='1'*64, result_identity='2'*64, replay_identity=task.expected_replay_identity,
        source_input_binding_verified=True, archive_consistent=consistent, native_record_scope='complete_native_record',
        assignment_recomputed=True, normal_witness_reproduced=True, recorded_normal_accepted=accepted,
        recorded_source_accepted=accepted, accepted_record_reproduced=accepted,
        native_replay_json=api.journal._bytes(native).decode(), errors=() if consistent else ('normal_witness_mismatch',),
        status='replayed_accepted_normal_record' if accepted else ('replayed_unresolved_normal_record' if consistent else 'inconsistent_normal_record'),
        solver_calls_by_replay=0, native_execution_authenticated=False, resource_measurements_authenticated=False,
        resume_authorized=False, optimality_certificate=None, infeasibility_certificate=None, formal_result=False,
        security_certified=False)
    return values


def diagnostic_wire(task, state='accepted', source=None):
    if source is None: source = source_diagnostic_wire(task, state)
    consistent, accepted = state != 'inconsistent', state == 'accepted'
    return dict(record_sha256='1'*64, result_identity='2'*64, replay_identity=task.expected_replay_identity,
        archive_consistent=consistent, accepted_record_reproduced=accepted, source_input_binding_verified=True,
        assignment_recomputed=source['assignment_recomputed'], normal_witness_reproduced=source['normal_witness_reproduced'],
        recorded_declared_accepted=accepted, source_replay_json=api.journal._bytes(source).decode(),
        errors=() if consistent else ('source:normal_witness_mismatch',),
        status='replayed_accepted_declared_normal_record' if accepted else (
            'replayed_unresolved_declared_normal_record' if consistent else 'inconsistent_declared_normal_record'),
        solver_calls_by_replay=0, native_execution_authenticated=False, resource_measurements_authenticated=False,
        resume_authorized=False, optimality_certificate=None, infeasibility_certificate=None,
        formal_result=False, security_certified=False)


def encode_report(values):
    return api.journal._bytes(['DeclaredGurobiDirectNormalRecordReplay', [[f.name, api.worker.kernel._encode(values[f.name])]
        for f in fields(api.worker.replay.DeclaredGurobiDirectNormalRecordReplay)]])


def report_claim(values, raw):
    return dict(replay_result_sha256=sha256(raw).hexdigest(), replay_result_bytes=len(raw),
        status=values['status'], archive_consistent=values['archive_consistent'],
        accepted_record_reproduced=values['accepted_record_reproduced'])


@pytest.mark.parametrize('state', ['accepted', 'unresolved', 'inconsistent'])
def test_complete_report_preserves_three_states(configured, state):
    from types import SimpleNamespace
    task = configured[0]
    values = diagnostic_wire(task, state)
    raw = encode_report(values)
    pins = SimpleNamespace(record_sha256='1'*64, claimed_result_identity='2'*64)
    result = api._report(raw, pins, task, report_claim(values, raw))
    assert result['status'] == values['status'] and result['errors'] == values['errors']


@pytest.mark.parametrize('fault', ['authority', 'identity', 'calls_bool', 'consistent_int', 'nested', 'summary',
    'numeric_int', 'scope', 'nested_consistency', 'accepted_relation', 'reported_optimal',
    'reported_native_infeasible', 'native_infeasible_flag_reproduced', 'objective_missing'])
def test_coherently_rehashed_report_faults_are_not_accepted(configured, fault):
    from types import SimpleNamespace
    task = configured[0]
    values = source_diagnostic_wire(task)
    if fault == 'authority': values['native_execution_authenticated'] = True
    if fault == 'identity': values['record_sha256'] = '0'*64
    if fault == 'calls_bool': values['solver_calls_by_replay'] = False
    if fault == 'consistent_int': values['archive_consistent'] = 1
    if fault == 'nested': values['native_replay_json'] = '{}'
    if fault in ('numeric_int', 'nested_consistency'):
        nested = api.journal._decoded(values['native_replay_json'].encode())
        if fault == 'numeric_int': nested['recomputed_objective'] = 0
        else: nested['replay_consistent'] = False
        values['native_replay_json'] = api.journal._bytes(nested).decode()
    if fault == 'scope': values['native_record_scope'] = 'no_native_record'
    if fault == 'accepted_relation':
        values['accepted_record_reproduced'] = False
        values['status'] = 'replayed_unresolved_normal_record'
    if fault in ('reported_optimal', 'reported_native_infeasible', 'native_infeasible_flag_reproduced', 'objective_missing'):
        nested = api.journal._decoded(values['native_replay_json'].encode())
        if fault == 'objective_missing': nested['recomputed_objective'] = None
        else: nested[fault] = not nested[fault]
        values['native_replay_json'] = api.journal._bytes(nested).decode()
    values = diagnostic_wire(task, source=values)
    raw = encode_report(values)
    claim = report_claim(values, raw)
    if fault == 'summary': claim['accepted_record_reproduced'] = False
    with pytest.raises(ValueError):
        api._report(raw, SimpleNamespace(record_sha256='1'*64, claimed_result_identity='2'*64), task, claim)


@pytest.mark.parametrize('stage', ['prepare_pause', 'intent_pause', 'result_pause', 'replay_pause'])
def test_controller_parent_death_kills_phase_job_and_keeps_attempt(tmp_path, supplied, configured, monkeypatch, stage):
    import _winapi
    root = tmp_path/'parent_death_non_authoritative'
    command = synthetic_bootstrap(tmp_path, supplied, monkeypatch, stage)
    bootstrap = tmp_path/'child_bootstrap.txt'
    bootstrap.write_text(command(root/'execute.request.json', '0'*64)[4], encoding='utf-8')
    task, budget, env = configured
    declaration = tmp_path/'controller_test_inputs.json'
    declaration.write_bytes(api.journal._bytes(dict(task=asdict(task), budget=asdict(budget), environment=env)))
    script = f"""
import sys,os,time,threading,json
from pathlib import Path
sys.path.insert(0,{str(api.worker.ROOT)!r})
from src.rq2_joint_deliverability_boundary_v1 import normal_task_controller_gurobi_direct as c
root=Path({str(root)!r})
body=json.loads(Path({str(declaration)!r}).read_bytes())
task=c.worker.decode_request(body['task'])
b=body['budget']
b['execute']=c.process.TaskProcessBudget(**b['execute'])
b['replay']=c.process.TaskProcessBudget(**b['replay'])
b['capture']=c.capture.ArchiveCaptureBudget(**b['capture'])
budget=c.NormalTaskBudget(**b)
original=c.worker.worker_argv
def command(path,digest):
 argv=original(path,digest)
 argv[4]=Path({str(bootstrap)!r}).read_text(encoding='utf-8')
 return argv
c.worker.worker_argv=command
def die():
 deadline=time.monotonic()+45
 while not (root/'{('replay' if stage == 'replay_pause' else 'execute')}_non_authoritative'/'ack').exists():
  if time.monotonic()>deadline: return
  time.sleep(.02)
 os._exit(0)
threading.Thread(target=die,daemon=True).start()
c.supervise_normal_task(root,task,budget=budget,environment=body['environment'],
 expected_controller_identity=c.controller_identity(root,task,budget,body['environment']))
"""
    parent = subprocess.Popen([sys.executable, '-I', '-B', '-c', script], creationflags=subprocess.CREATE_NO_WINDOW)
    scratch = root/(('replay' if stage == 'replay_pause' else 'execute')+'_non_authoritative')
    handle = None
    try:
        deadline = time.monotonic()+45
        while not (scratch/'waiting').exists():
            assert parent.poll() is None, 'controller ended before injected death window'
            if time.monotonic() > deadline: raise TimeoutError('phase death window not reached')
            time.sleep(.02)
        handle = _winapi.OpenProcess(0x00100000, False, int((scratch/'waiting').read_text()))
        (scratch/'ack').write_text('observation handle held')
        assert parent.wait(timeout=5) == 0
        assert _winapi.WaitForSingleObject(handle, 5000) == 0
        assert (root/'controller.intent.json').exists()
        assert not (root/'controller.observation.json').exists()
        if stage == 'replay_pause': assert (root/'retained_pins.json').exists()
        with pytest.raises(FileExistsError): run(root, configured)
    finally:
        if parent.poll() is None:
            parent.terminate()
            parent.wait(timeout=5)
        if handle is not None: _winapi.CloseHandle(handle)


def synthetic_controller_dependencies(root, configured, monkeypatch, process_fault=None, capture_fault=None):
    """Plain synthetic observations only; this helper provides no execution evidence."""
    from types import SimpleNamespace
    task = configured[0]
    execution = dict(store_identity='3'*64, head='4'*64, record_sha256='1'*64, claimed_result_identity='2'*64)
    calls = []
    @contextmanager
    def child(*args, **kwargs):
        name = 'execute' if not calls else 'replay'
        calls.append(name)
        class Child:
            pid, creation_filetime = 23, 45
            def release(self):
                intent = api.worker._read(root/(name+'.intent.json'))
                launch = api.worker._read(root/(name+'.launch.json'))
                claim = dict(**intent, pid=self.pid, launch_sha256=sha256(api.journal._bytes(launch)).hexdigest())
                api.worker._write(root/(name+'.claim.json'), claim)
                completion = execution
                if name == 'replay':
                    values = diagnostic_wire(task)
                    raw = encode_report(values)
                    (root/'replay.result.json').write_bytes(raw)
                    completion = report_claim(values, raw)
                api.worker._write(root/(name+'.complete.json'), dict(**claim, completion=completion,
                    numerical_acceptance_by_controller=False, formal_result=False))
            def wait(self):
                result = api.process.TaskProcessObservation(kwargs['expected_process_identity'], self.pid,
                    self.creation_filetime, 0, 'child_exited', .01, 1, MIB, (), (), None, (), MIB, MIB, True)
                if process_fault == 'type': return SimpleNamespace(**asdict(result))
                if process_fault:
                    value = {'process_identity':'0'*64, 'pid':24, 'creation_filetime':46,
                        'job_commit_limits_configured':False, 'formal_result':True,
                        'whole_task_resources_verified':True, 'hard_disk_quota_enforced':True,
                        'numerical_evidence_verified':True, 'exit_code':False}[process_fault]
                    result = replace(result, **{process_fault:value})
                return result
        yield Child()
    captures = []
    def captured(*args, **kwargs):
        captures.append(kwargs)
        result = api.capture.GurobiDirectNormalArchivePins(kwargs['expected_capture_identity'], execution['store_identity'],
            '5'*64, execution['head'], 'opaque_record_captured', True, execution['record_sha256'], 128,
            execution['claimed_result_identity'])
        if capture_fault == 'type': return SimpleNamespace(**asdict(result))
        if capture_fault == 'post_replay_drift' and len(captures) == 2:
            return replace(result, record_bytes=129)
        if capture_fault and capture_fault != 'post_replay_drift':
            value = {'capture_identity':'0'*64, 'store_identity':'0'*64, 'claimed_result_identity':'0'*64,
                'record_bytes':True, 'intent_present':False, 'result_identity_verified':True,
                'numerical_evidence_replayed':True, 'native_execution_authenticated':True,
                'whole_job_quiescence_verified':True, 'formal_result':True}[capture_fault]
            result = replace(result, **{capture_fault:value})
        return result
    monkeypatch.setattr(api.process, 'normal_task_child', child)
    monkeypatch.setattr(api.capture, 'capture_normal_archive', captured)
    return calls, captures


@pytest.mark.parametrize('fault', ['type', 'process_identity', 'pid', 'creation_filetime',
    'job_commit_limits_configured', 'formal_result', 'whole_task_resources_verified',
    'hard_disk_quota_enforced', 'numerical_evidence_verified', 'exit_code'])
def test_forged_process_observations_stop_before_capture(tmp_path, configured, monkeypatch, fault):
    root = tmp_path/'observation_fault_non_authoritative'
    calls, captures = synthetic_controller_dependencies(root, configured, monkeypatch, process_fault=fault)
    result = run(root, configured)
    assert result.status == 'unresolved_task_attempt' and result.stopped_phase == 'execute'
    assert calls == ['execute'] and captures == []


@pytest.mark.parametrize('fault', ['type', 'capture_identity', 'store_identity', 'claimed_result_identity',
    'record_bytes', 'intent_present', 'result_identity_verified', 'numerical_evidence_replayed',
    'native_execution_authenticated', 'whole_job_quiescence_verified', 'formal_result', 'post_replay_drift'])
def test_capture_faults_and_post_replay_archive_drift(tmp_path, configured, monkeypatch, fault):
    root = tmp_path/'capture_fault_non_authoritative'
    calls, captures = synthetic_controller_dependencies(root, configured, monkeypatch, capture_fault=fault)
    result = run(root, configured)
    assert result.status == 'unresolved_task_attempt'
    if fault == 'post_replay_drift':
        assert calls == ['execute', 'replay'] and len(captures) == 2 and result.stopped_phase == 'recapture'
        assert (root/'replay.result.json').exists() and not (root/'final_pins.json').exists()
    else:
        assert calls == ['execute'] and len(captures) == 1 and result.stopped_phase == 'capture'
        assert not (root/'replay.intent.json').exists()


def test_invalid_nested_object_never_invokes_copy_hook(tmp_path, configured):
    task, budget, env = configured
    touched = []
    class Unexpected:
        def __deepcopy__(self, memo): touched.append(True); raise AssertionError('callback executed')
    object.__setattr__(task.source, 'expected_scale', Unexpected())
    with pytest.raises(ValueError, match='plain typed'):
        api.supervise_normal_task(tmp_path/'invalid_non_authoritative', task, budget=budget,
            environment=env, expected_controller_identity='0'*64)
    assert not touched


@pytest.mark.parametrize('stage', ['initial_observation', 'final_write', 'retained_write', 'final_clock_crossing'])
def test_deadlines_and_retained_write_failure(tmp_path, configured, monkeypatch, stage):
    from types import SimpleNamespace
    root = tmp_path/'deadline_non_authoritative'
    calls, captures = synthetic_controller_dependencies(root, configured, monkeypatch)
    offset = [0.]
    final_reads = []
    writing_done = [False]
    real_clock = time.monotonic
    def clock():
        if stage == 'final_clock_crossing' and writing_done[0]:
            final_reads.append(True)
            if len(final_reads) > 1: return real_clock()+1000.
        return real_clock()+offset[0]
    monkeypatch.setattr(api, 'time', SimpleNamespace(monotonic=clock))
    original = api.worker._write
    def write(path, *args, **kwargs):
        if stage == 'retained_write' and path.name == 'retained_pins.json': raise OSError('fsync/write failure')
        result = original(path, *args, **kwargs)
        if stage == 'final_write' and path.name == 'controller.observation.json': offset[0] = 1000.
        if path.name == 'controller.observation.json': writing_done[0] = True
        return result
    monkeypatch.setattr(api.worker, '_write', write)
    if stage == 'initial_observation':
        original_observe = api.resources.observe_headroom
        def observe(*a, **k):
            result = original_observe(*a, **k)
            offset[0] = 1000.
            return result
        monkeypatch.setattr(api.resources, 'observe_headroom', observe)
    if stage == 'final_clock_crossing':
        result = run(root, configured)
        assert result.status == 'completed_development_replay_diagnostic'
        assert result.elapsed_seconds < configured[1].max_total_elapsed_seconds and final_reads == [True]
    elif stage == 'retained_write':
        result = run(root, configured)
        assert result.status == 'unresolved_task_attempt' and calls == ['execute']
        assert not (root/'replay.intent.json').exists()
    else:
        with pytest.raises(TimeoutError): run(root, configured)
        if stage == 'initial_observation': assert not root.exists() and not calls
        else:
            assert calls == ['execute', 'replay'] and len(captures) == 2
            assert api.worker._read(root/'controller.observation.json')['status'] == 'validated_before_final_observation_write'
