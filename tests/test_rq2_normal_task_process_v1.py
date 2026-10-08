"""Short Windows children and injected observations; no solver or long task."""
from copy import copy
from dataclasses import replace
import os
from pathlib import Path
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as api


pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows task ownership')
MIB = 1024**2
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('stop_outer', [False, True])
def test_nested_task_job_membership_and_outer_quiescence(setup, stop_outer):
    """Reuse the existing owner twice; no solver or episode implementation."""
    import _winapi
    import json
    root = setup[0]
    inner_code = """import pathlib,time
root = pathlib.Path.cwd()
(root/'ready').write_text('ready')
until = time.monotonic()+8
while not (root/'continue').exists():
    if time.monotonic() > until: raise TimeoutError('test handshake')
    time.sleep(.01)
"""
    worker = f"""import sys,os,json
from pathlib import Path
from dataclasses import asdict
sys.stderr = open('worker_error.txt', 'w')
sys.path.insert(0, {str(ROOT)!r})
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as api
root = Path.cwd()
budget = api.TaskProcessBudget(10., .02, 128*1024**2, 256*1024**2, 2.)
host = api.resources.HostResourceBudget(256*1024**2, 16*1024**2,
    (api.resources.DirectoryDemand('scratch', str(root), 1024**2, 8*1024**2),))
argv = [sys.executable, '-I', '-B', '-c', {inner_code!r}]
args = dict(cwd=root, environment=dict(os.environ), budget=budget,
    host_budget=host, expected_host_identity=api.resources.resource_identity(host))
with api.normal_task_child(argv, **args,
        expected_process_identity=api.task_process_identity(argv, **args)) as inner:
    (root/'inner_pid').write_text(str(inner.pid))
    inner.release()
    result = inner.wait()
(root/'inner_result.json').write_text(json.dumps(asdict(result)))
"""
    budget = replace(setup[1], max_elapsed_seconds=15., max_process_commit_bytes=768*MIB,
                     max_job_commit_bytes=1024*MIB)
    host = replace(setup[2], additional_commit_bytes=1024*MIB)
    setup[3]['commit'] = 2048*MIB
    environment = dict(os.environ, TEMP=str(root), TMP=str(root), OMP_NUM_THREADS='1',
                       OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    handle = None
    try:
        with child(setup, worker, budget=budget, host_budget=host,
                   environment=environment,
                   expected_host_identity=api.resources.resource_identity(host)) as owner:
            owner.release()
            until = time.monotonic()+6
            while not (root/'ready').exists():
                assert time.monotonic() < until, 'nested child did not reach handshake'
                assert owner._child._k.WaitForSingleObject(owner._child._process, 0) == 258, (root/'worker_error.txt').read_text()
                time.sleep(.01)
            handle = _winapi.OpenProcess(0x100000 | 0x1000, False, int((root/'inner_pid').read_text()))
            inside = api.c.c_int()
            assert owner._child._k.IsProcessInJob(int(handle), owner._child._job, api.c.byref(inside))
            assert inside.value, 'nested child escaped outer Job'
            if stop_outer:
                owner._started -= 16.
            else:
                (root/'continue').write_text('continue')
            result = owner.wait()
            assert result.whole_job_quiescent
            assert _winapi.WaitForSingleObject(handle, 1000) == 0
            assert result.reason == ('task_deadline_stop' if stop_outer else 'child_exited')
            assert 0 < result.job_peak_total_commit_bytes <= budget.max_job_commit_bytes
            if stop_outer:
                assert not (root/'inner_result.json').exists()
            else:
                inner = json.loads((root/'inner_result.json').read_text())
                assert result.exit_code == inner['exit_code'] == 0
                assert inner['whole_job_quiescent'] and inner['reason'] == 'child_exited'
                assert result.job_peak_total_commit_bytes >= inner['job_peak_total_commit_bytes']
    finally:
        if handle is not None: _winapi.CloseHandle(handle)


@pytest.fixture
def setup(tmp_path, monkeypatch):
    state = dict(commit=1024*MIB, disk=1024*MIB)
    monkeypatch.setattr(api.resources, '_observe_commit',
        lambda: api.resources.CommitObservation(0, state['commit'], 1))
    monkeypatch.setattr(api.resources, '_observe_disk', lambda item, volume:
        api.resources.DiskObservation(item.name, item.directory, volume, state['disk'], 2**40, 2**40))
    budget = api.TaskProcessBudget(5., .02, 128*MIB, 256*MIB, 2.)
    host = api.resources.HostResourceBudget(256*MIB, 16*MIB,
        (api.resources.DirectoryDemand('scratch', str(tmp_path), 64*MIB, 8*MIB),))
    return tmp_path, budget, host, state


def arguments(setup, code='pass', **changes):
    root, budget, host, _ = setup
    args = dict(cwd=root, environment=dict(os.environ, TEMP=str(root), TMP=str(root)), budget=budget,
        host_budget=host, expected_host_identity=api.resources.resource_identity(host))
    args.update(changes)
    argv = [sys.executable, '-I', '-B', '-c', code]
    return argv, dict(**args, expected_process_identity=api.task_process_identity(argv, **args))


def child(setup, code='pass', **changes):
    argv, args = arguments(setup, code, **changes)
    return api.normal_task_child(argv, **args)


def test_suspended_single_use_and_real_exit(setup):
    marker = setup[0]/'ran'
    with child(setup, "from pathlib import Path; Path('ran').write_text('ok')") as owner:
        assert not marker.exists()
        with pytest.raises(RuntimeError): owner.wait()
        with pytest.raises(TypeError): copy(owner)
        owner.release()
        with pytest.raises(RuntimeError): owner.release()
        result = owner.wait()
        assert result.reason == 'child_exited' and result.exit_code == 0
        assert result.whole_job_quiescent and result.runtime_samples > 0
        assert result.job_peak_total_commit_bytes >= result.job_peak_process_commit_bytes > 0
        assert not any((result.hard_disk_quota_enforced, result.whole_task_resources_verified,
                        result.numerical_evidence_verified, result.formal_result))
        with pytest.raises(RuntimeError): owner.wait()
    assert marker.read_text() == 'ok'


def test_initial_refusal_precedes_child_creation(setup, monkeypatch):
    setup[3]['commit'] = 1
    def forbidden(*a, **k): raise AssertionError('no child on refused headroom')
    monkeypatch.setattr(api.process, 'DevelopmentNormalChild', forbidden)
    with pytest.raises(ValueError, match='initial task headroom'):
        with child(setup): pass


def test_runtime_and_prerelease_do_not_double_count_allocated_task_budget(setup):
    with child(setup) as owner:
        setup[3].update(commit=16*MIB, disk=8*MIB)  # Exactly reserves, far below additional+reserve.
        owner.release()
        result = owner.wait()
        assert result.reason == 'child_exited' and result.exit_code == 0
        assert not result.last_resource_errors


@pytest.mark.parametrize('resource', ['commit', 'disk'])
def test_runtime_reserve_breach_stops_and_confirms_job_quiet(setup, resource):
    with child(setup, 'import time; time.sleep(20)') as owner:
        owner.release()
        setup[3][resource] = 1
        result = owner.wait()
        assert result.reason == 'host_resource_reserve_stop'
        assert result.last_resource_errors and result.whole_job_quiescent
        assert result.exit_code == 0xE002


def test_api_failure_keeps_unresolved_reason_and_quiet_job(setup, monkeypatch):
    with child(setup, 'import time; time.sleep(20)') as owner:
        owner.release()
        def fail(): raise OSError('sample failed')
        monkeypatch.setattr(api.resources, '_observe_commit', fail)
        result = owner.wait()
        assert result.reason == 'resource_observation_failed'
        assert result.observation_error_type == 'OSError' and result.whole_job_quiescent
        assert result.minimum_runtime_commit_available_bytes is None


def test_implementation_drift_stops_live_child(setup, monkeypatch):
    with child(setup, 'import time; time.sleep(20)') as owner:
        owner.release()
        original = Path.read_bytes
        target = Path(api.process.__file__).resolve()
        monkeypatch.setattr(Path, 'read_bytes', lambda path:
            original(path)+(b'changed' if path.resolve() == target else b''))
        result = owner.wait()
        assert result.reason == 'resource_observation_failed' and result.whole_job_quiescent
        assert 'post_process_identity_failed' in result.stop_markers


def test_new_task_budget_exceeding_60_does_not_use_old_wait(setup, monkeypatch):
    def forbidden(*a, **k): raise AssertionError('old short wait cannot be called')
    monkeypatch.setattr(api.process.DevelopmentNormalChild, 'wait', forbidden)
    with child(setup, budget=replace(setup[1], max_elapsed_seconds=120.)) as owner:
        owner._started -= 61.  # Inject elapsed time, never actually run a 61-second test.
        owner.release()
        result = owner.wait()
        assert result.elapsed_seconds >= 61 and result.reason == 'child_exited'


def test_deadline_terminates_owned_child_without_touching_bystander(setup):
    bystander = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'import time; time.sleep(20)'],
        creationflags=subprocess.CREATE_NO_WINDOW)
    try:
        with child(setup, 'import time; time.sleep(20)') as owner:
            owner.release()
            owner._started -= 6.
            result = owner.wait()
            assert result.reason == 'task_deadline_stop' and result.whole_job_quiescent
            assert bystander.poll() is None
    finally:
        bystander.terminate()
        bystander.wait(timeout=5)


def test_sample_crossing_deadline_preserves_resource_marker(setup, monkeypatch):
    with child(setup, 'import time; time.sleep(20)') as owner:
        owner.release()
        def sample():
            owner._started -= 6.
            return api.resources.CommitObservation(0, 1, 1)
        monkeypatch.setattr(api.resources, '_observe_commit', sample)
        result = owner.wait()
        assert result.reason == 'task_deadline_stop'
        assert 'system_commit_reserve_breached' in result.stop_markers
        assert 'task_deadline_stop' in result.stop_markers


def test_exited_child_does_not_hide_failed_final_reserve(setup):
    with child(setup) as owner:
        owner.release()
        assert owner._child._k.WaitForSingleObject(owner._child._process, 5000) == 0
        setup[3]['disk'] = 1
        result = owner.wait()
        assert result.reason == 'host_resource_reserve_stop' and result.exit_code == 0
        assert 'direct_child_exit_observed' in result.stop_markers


def test_normal_exit_quiesces_surviving_descendant(setup):
    code = "import subprocess,sys; subprocess.Popen([sys.executable,'-I','-B','-c','import time; time.sleep(20)'])"
    with child(setup, code) as owner:
        owner.release()
        result = owner.wait()
        assert result.reason == 'child_exited' and result.whole_job_quiescent
        accounting = api.process._Accounting()
        assert owner._child._k.QueryInformationJobObject(owner._child._job, 1,
            api.c.byref(accounting), api.c.sizeof(accounting), None)
        assert accounting.active == 0


@pytest.mark.parametrize('kind', ['interrupt', 'quiescence', 'peak_query'])
def test_failed_wait_never_returns_quiet_report_and_closes_owner(setup, monkeypatch, kind):
    import _winapi
    handle = None
    try:
        with child(setup, 'import time; time.sleep(20)') as owner:
            handle = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), owner._child._process,
                _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS)
            owner.release()
            if kind == 'interrupt':
                def fail(): raise KeyboardInterrupt()
                monkeypatch.setattr(api.resources, '_observe_commit', fail)
                error = KeyboardInterrupt
            elif kind == 'quiescence':
                def fail(**kwargs): raise TimeoutError('quiet unconfirmed')
                monkeypatch.setattr(owner._child, 'quiesce', fail)
                owner._started -= 6.
                error = TimeoutError
            else:
                old = owner._child._k.QueryInformationJobObject
                def fail(job, info, *args):
                    if info == 9: raise OSError('peak unavailable')
                    return old(job, info, *args)
                monkeypatch.setattr(owner._child._k, 'QueryInformationJobObject', fail)
                owner._started -= 6.
                error = OSError
            with pytest.raises(error): owner.wait()
            assert owner._child is None
        assert _winapi.WaitForSingleObject(handle, 5000) == 0
    finally:
        if handle is not None: _winapi.CloseHandle(handle)


def test_cross_thread_rejected_without_consuming_owner(setup):
    with child(setup) as owner:
        with ThreadPoolExecutor(1) as pool:
            with pytest.raises(RuntimeError): pool.submit(owner.release).result()
        owner.release()
        with ThreadPoolExecutor(1) as pool:
            with pytest.raises(RuntimeError): pool.submit(owner.wait).result()
        assert owner.wait().exit_code == 0


@pytest.mark.parametrize('field,value', [('max_elapsed_seconds', 0), ('max_elapsed_seconds', float('inf')),
    ('max_elapsed_seconds', 3601), ('max_elapsed_seconds', 1e300),
    ('max_elapsed_seconds', True), ('sample_interval_seconds', 2), ('max_quiescence_seconds', 6),
    ('max_process_commit_bytes', True), ('max_job_commit_bytes', 1)])
def test_invalid_task_budget_rejected(setup, field, value):
    with pytest.raises(ValueError): replace(setup[1], **{field: value})


def test_private_scratch_and_host_demand_required(setup):
    with pytest.raises(ValueError, match='scratch'):
        arguments(setup, environment=dict(os.environ, TEMP='elsewhere', TMP='elsewhere'))
    host = replace(setup[2], additional_commit_bytes=1)
    with pytest.raises(ValueError, match='cover task Job'):
        arguments(setup, host_budget=host, expected_host_identity=api.resources.resource_identity(host))


def test_aggregate_peak_observed_for_overlapping_members(setup):
    member = "from pathlib import Path; import time; data=bytearray(16*1024**2); Path('member_ready').write_text('ok'); time.sleep(20)"
    code = f"""
import subprocess,sys,time
from pathlib import Path
data=bytearray(16*1024**2)
subprocess.Popen([sys.executable,'-I','-B','-c',{member!r}])
deadline=time.monotonic()+3
while not Path('member_ready').exists():
    if time.monotonic()>deadline: raise SystemExit(8)
    time.sleep(.01)
"""
    with child(setup, code) as owner:
        owner.release()
        result = owner.wait()
        assert result.exit_code == 0 and result.whole_job_quiescent
        assert result.job_peak_total_commit_bytes > result.job_peak_process_commit_bytes > 0


def test_wrapper_parent_death_kills_owned_child(tmp_path):
    import _winapi
    code = f"""
import os,sys,time
from pathlib import Path
sys.path.insert(0,{str(ROOT)!r})
from src.rq2_joint_deliverability_boundary_v1 import normal_task_process as api
root=Path({str(tmp_path)!r})
budget=api.TaskProcessBudget(30.,.02,128*1024**2,128*1024**2,2.)
host=api.resources.HostResourceBudget(128*1024**2,1024**2,(api.resources.DirectoryDemand('scratch',str(root),1024**2,1024**2),))
argv=[sys.executable,'-I','-B','-c','import time; time.sleep(20)']
args=dict(cwd=root,environment=dict(os.environ,TEMP=str(root),TMP=str(root)),budget=budget,
          host_budget=host,expected_host_identity=api.resources.resource_identity(host))
context=api.normal_task_child(argv,expected_process_identity=api.task_process_identity(argv,**args),**args)
owner=context.__enter__()
owner.release()
pending=root/'pid.pending'
pending.write_text(str(owner.pid))
pending.rename(root/'pid')
deadline=time.monotonic()+15
while not (root/'ack').exists():
    if time.monotonic()>deadline: raise SystemExit(9)
    time.sleep(.01)
os._exit(0)
"""
    parent = subprocess.Popen([sys.executable, '-I', '-B', '-c', code], creationflags=subprocess.CREATE_NO_WINDOW)
    handle = None
    try:
        deadline = time.monotonic()+15
        while not (tmp_path/'pid').exists():
            assert parent.poll() is None
            if time.monotonic()>deadline: raise TimeoutError('parent setup did not finish')
            time.sleep(.02)
        handle = _winapi.OpenProcess(0x00100000, False, int((tmp_path/'pid').read_text()))
        (tmp_path/'ack').write_text('retained process handle acquired')
        assert parent.wait(timeout=5) == 0
        assert _winapi.WaitForSingleObject(handle, 5000) == 0
    finally:
        if parent.poll() is None:
            parent.terminate()
            parent.wait(timeout=5)
        if handle is not None: _winapi.CloseHandle(handle)


def test_interrupt_after_base_construction_has_retained_owner(setup, monkeypatch):
    import _winapi
    saved = {}
    original = api.process.DevelopmentNormalChild.__init__
    def interrupted(instance, *args, **kwargs):
        original(instance, *args, **kwargs)
        saved['owner'] = instance
        saved['handle'] = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), instance._process,
            _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS)
        raise KeyboardInterrupt('base owns handles before outer constructor completes')
    monkeypatch.setattr(api.process.DevelopmentNormalChild, '__init__', interrupted)
    try:
        with pytest.raises(KeyboardInterrupt):
            with child(setup, 'import time; time.sleep(20)'): pass
        assert _winapi.WaitForSingleObject(saved['handle'], 5000) == 0
        assert saved['owner']._job is saved['owner']._process is saved['owner']._thread is None
    finally:
        if 'owner' in saved: saved['owner'].close()
        if 'handle' in saved: _winapi.CloseHandle(saved['handle'])


def test_base_failure_before_owner_initialization_preserves_error(setup, monkeypatch):
    def fail(*args, **kwargs): raise OSError('before base handle acquisition')
    monkeypatch.setattr(api.process.DevelopmentNormalChild, '__init__', fail)
    with pytest.raises(OSError, match='before base handle acquisition'):
        with child(setup): pass


def test_direct_construction_rejected_and_factory_is_lazy(setup, monkeypatch):
    argv, args = arguments(setup)
    with pytest.raises(TypeError, match='context manager'):
        api.NormalTaskChild(argv, **args)
    def forbidden(*args, **kwargs): raise AssertionError('factory must remain lazy')
    monkeypatch.setattr(api.NormalTaskChild, '_initialize', forbidden)
    manager = api.normal_task_child(argv, **args)
    manager.gen.close()


@pytest.mark.parametrize('stage', ['before_initialize', 'after_initialize', 'discard_entered_manager'])
def test_factory_finally_covers_owner_handoff(setup, monkeypatch, stage):
    import gc
    import _winapi
    saved = {}
    original = api.NormalTaskChild._initialize
    def initialize(instance, *args, **kwargs):
        saved['owner'] = instance
        if stage == 'before_initialize':
            raise KeyboardInterrupt('before first owner field')
        original(instance, *args, **kwargs)
        saved['inner'] = instance._child
        saved['handle'] = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), instance._child._process,
            _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS)
        if stage == 'after_initialize':
            raise KeyboardInterrupt('outer initialized before yield')
    monkeypatch.setattr(api.NormalTaskChild, '_initialize', initialize)
    manager = child(setup, 'import time; time.sleep(20)')
    try:
        if stage == 'discard_entered_manager':
            owner = manager.__enter__()
            owner.release()
            del manager
            gc.collect()
        else:
            with pytest.raises(KeyboardInterrupt):
                with manager: pass
        assert getattr(saved['owner'], '_child', None) is None
        if 'handle' in saved:
            assert _winapi.WaitForSingleObject(saved['handle'], 5000) == 0
            inner = saved['inner']
            assert inner._job is inner._process is inner._thread is None
    finally:
        saved['owner'].close()
        if 'handle' in saved: _winapi.CloseHandle(saved['handle'])
