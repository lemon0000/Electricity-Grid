from dataclasses import replace
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import h1_controller_timing_development_v1 as api
from tests.test_h1_saved_job_development_v1 import child_command, raw_files
from tests.test_h1_saved_source_parent_development_v1 import environment, source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports, saved

pytestmark = pytest.mark.skipif(os.name != 'nt',reason='Windows directory leases')


def read_controller(c, index=0):
    p = c.timing_root/f'{index:03d}'
    return api.inspect(c.timing_root,index,expected_binding_sha=c.binding_sha256,
        expected_intent_sha=api.io.digest((p/'intent.json').read_bytes()),
        expected_terminal_sha=c.last_observation.record_sha256,
        expected_implementation=c._timing_implementation)


@pytest.fixture
def fake(tmp_path, monkeypatch):
    clock = SimpleNamespace(now=100)
    calls = []
    def init(c,root,**kwargs):
        root.mkdir()
        c._lease = SimpleNamespace(root=root)
        c._parent = SimpleNamespace(_poisoned=False)
        clock.now += 10
    def step(c,*args,**kwargs):
        calls.append('step')
        clock.now += 100
        job = c._lease.root/f'job_{c._timing_index:03d}_non_authoritative'
        job.mkdir()
        identity = dict(pid=123,creation_filetime=456,process_identity='a'*64)
        rows = {'request.json':{},'child.json':identity,
            'observation.json':dict(identity,whole_job_quiescent=True,exit_code=0,reason='child_exited'),
            'job_checks.json':{}}
        for name,row in rows.items(): api.io.write_metadata(job/name,row)
        return SimpleNamespace(head='b'*64,completed_hours=c._timing_index+1,status='ready')
    def close(c): calls.append('close'); clock.now += 30
    monkeypatch.setattr(api.saved.SavedJobController,'__init__',init)
    monkeypatch.setattr(api.saved.SavedJobController,'step_saved_job',step)
    monkeypatch.setattr(api.saved.SavedJobController,'close',close)
    c = api.TimedSavedController(tmp_path/'controller',hours=2,clock=lambda:clock.now)
    raw = api.saved.SavedRaw(str((tmp_path/'raw.bin').resolve()),'c'*64,1)
    def run(): return c.step_saved_job((raw,),expected_source_identity='d'*64,expected_head='e'*64)
    yield c,clock,calls,run
    c.close()


def test_outer_window_and_confirmation_tail_are_distinct(fake,monkeypatch):
    c,clock,calls,run = fake
    write, inspect = api.io.write_metadata, api.inspect
    def delayed(path,doc):
        pin = write(path,doc)
        if path.parent.name == '000' and path.name == 'intent.json': clock.now += 7
        if path.parent.name == '000' and path.name == 'terminal.json': clock.now += 1000
        return pin
    def reviewed(*a,**k):
        result = inspect(*a,**k)
        clock.now += 2000
        return result
    monkeypatch.setattr(api.io,'write_metadata',delayed)
    monkeypatch.setattr(api,'inspect',reviewed)
    run()
    assert c.last_observation.transaction_wall_ns == 107
    assert c.last_observation.confirmation_tail_ns == 3000
    assert c.last_observation.total_until_confirmation_ns == 3107
    assert not c.last_observation.final_tick_persisted
    assert (c.last_observation.record_kind,c.last_observation.index,c.last_observation.outcome_head) == ('transaction',0,'b'*64)
    assert c.initialization_observation.record_kind == 'initialization'
    assert read_controller(c)['confirmation_tail_ns'] is None
    c.close()
    assert c.close_observation.transaction_wall_ns == 30
    assert c.close_observation.record_kind == 'close'
    assert calls == ['step','close']


@pytest.mark.parametrize('name,after', [('intent.json',False),('intent.json',True),
    ('terminal.json',False),('terminal.json',True)])
def test_publication_failure_no_live_receipt_or_retry(fake,monkeypatch,name,after):
    c,clock,calls,run = fake
    write = api.io.write_metadata
    def fail(path,doc):
        if path.parent.name == '000' and path.name == name:
            if after: write(path,doc)
            raise OSError('injected confirmation failure')
        return write(path,doc)
    monkeypatch.setattr(api.io,'write_metadata',fail)
    with pytest.raises(OSError): run()
    assert c._timing_poisoned and c._parent._poisoned
    assert getattr(c,'last_observation',None) is None
    assert ('step' in calls) == (name == 'terminal.json')
    before = len(calls)
    with pytest.raises(ValueError): run()
    assert len(calls) == before


def test_failure_in_real_base_call_keeps_intent_and_no_terminal(fake,monkeypatch):
    c,clock,calls,run = fake
    def fail(*a,**k): raise RuntimeError('base failed')
    monkeypatch.setattr(api.saved.SavedJobController,'step_saved_job',fail)
    with pytest.raises(RuntimeError): run()
    assert (c.timing_root/'000'/'intent.json').exists()
    assert not (c.timing_root/'000'/'terminal.json').exists()
    assert c._parent._poisoned


def test_clock_reversal_between_transactions_is_rejected(fake):
    c,clock,calls,run = fake
    run()
    clock.now -= 1
    with pytest.raises(ValueError,match='clock reversal'): run()
    assert calls == ['step']


def test_complete_declaration_rejects_before_any_new_file(fake):
    c,clock,calls,run = fake
    run(); run()
    before = {p.relative_to(c.timing_root):p.read_bytes() for p in c.timing_root.rglob('*') if p.is_file() and p.name != 'execution.lock'}
    with pytest.raises(ValueError,match='declared hour cap'): run()
    after = {p.relative_to(c.timing_root):p.read_bytes() for p in c.timing_root.rglob('*') if p.is_file() and p.name != 'execution.lock'}
    assert before == after and not (c.timing_root/'002').exists()
    assert calls == ['step','step']
    assert c.last_observation is None


@pytest.mark.parametrize('mode',['pin','job','extra','implementation','fresh'])
def test_fresh_reader_or_owner_rejects_changed_evidence(fake,monkeypatch,mode):
    c,clock,calls,run = fake
    run()
    if mode == 'pin':
        (c.timing_root/'000'/'terminal.json').write_bytes(b'{}')
    elif mode == 'job':
        (c._lease.root/'job_000_non_authoritative'/'child.json').write_bytes(b'{}')
    elif mode == 'extra':
        (c.timing_root/'000'/'extra').write_bytes(b'')
    elif mode == 'implementation': monkeypatch.setattr(api,'implementation_identity',lambda:'f'*64)
    else:
        original = api.io.read_stable
        count = [0]
        def drift(path,cap):
            value = original(path,cap)
            if path.name == 'child.json':
                count[0] += 1
                if count[0] == 2: return value[0]+b' ',value[1]
            return value
        monkeypatch.setattr(api.io,'read_stable',drift)
    with pytest.raises(ValueError): read_controller(c)
    # A failed independent reader does not mutate the live owner. Explicitly
    # poison here so teardown only releases resources in the damaged fixture.
    c._timing_poisoned = True


def test_reentrant_step_does_not_poison_active_owner(fake):
    c,clock,calls,run = fake
    c._timing_guard.acquire()
    try:
        with pytest.raises(ValueError,match='active'): run()
        assert not c._timing_poisoned
    finally: c._timing_guard.release()
    run()


def test_fresh_confirmation_failure_after_parent_outcome(fake,monkeypatch):
    c,clock,calls,run = fake
    def fail(*a,**k): raise ValueError('fresh failure')
    monkeypatch.setattr(api,'inspect',fail)
    with pytest.raises(ValueError,match='fresh failure'): run()
    assert (c.timing_root/'000'/'terminal.json').exists()
    assert getattr(c,'last_observation',None) is None and c._parent._poisoned


def test_foreign_close_cannot_release_owner_resources(fake):
    from concurrent.futures import ThreadPoolExecutor
    c,clock,calls,run = fake
    with ThreadPoolExecutor(1) as pool:
        with pytest.raises(ValueError,match='owner'): pool.submit(c.close).result()
    assert not calls and not c._timing_poisoned
    run()


@pytest.mark.parametrize('window',['write_before','write_after','release_before','release_after'])
def test_close_fault_preserves_records_and_releases_timing_lease(fake,monkeypatch,window):
    c,clock,calls,run = fake
    run()
    if window.startswith('write'):
        write = api.io.write_metadata
        def fail(path,doc):
            if path.name == 'close.json':
                if window == 'write_after': write(path,doc)
                raise OSError('close fault')
            return write(path,doc)
        monkeypatch.setattr(api.io,'write_metadata',fail)
    else:
        import msvcrt
        locking = msvcrt.locking
        target = c._timing_lease.stream.fileno()
        def fail_release(fd,mode,count):
            if fd == target and mode == msvcrt.LK_UNLCK:
                if window == 'release_after': locking(fd,mode,count)
                raise OSError('release fault')
            return locking(fd,mode,count)
        monkeypatch.setattr(msvcrt,'locking',fail_release)
    with pytest.raises(OSError): c.close()
    assert c._timing_poisoned and c._timing_lease is None
    assert not hasattr(c,'close_observation')
    if window.startswith('release'): monkeypatch.setattr(msvcrt,'locking',locking)
    lease = api.saved.bounded.chunks.base.local._Lease(c.timing_root,False)
    lease.close()


def test_failed_close_cannot_remove_new_owners_registry(fake,monkeypatch):
    c,clock,calls,run = fake
    run()
    Lease = api.saved.bounded.chunks.base.local._Lease
    old = c._timing_lease
    release = old.close
    new_owners = []
    def after_release():
        release()
        new_owners.append(Lease(c.timing_root,False))
        raise OSError('released before confirmation failure')
    monkeypatch.setattr(old,'close',after_release)
    try:
        with pytest.raises(OSError,match='released before'): c.close()
        assert len(new_owners) == 1 and c._timing_lease is None
        new_owners[0].check()
        with pytest.raises(ValueError,match='already held'): Lease(c.timing_root,False)
        assert not hasattr(c,'close_observation')
    finally:
        for owner in new_owners: owner.close()


def assert_other_process_cannot_open(root):
    import subprocess
    import sys
    code = ('import sys;from pathlib import Path;'
        f'sys.path.insert(0,{str(Path.cwd())!r});'
        'from src.rq2_joint_deliverability_boundary_v1.episode_store import _Lease\n'
        'try:lease=_Lease(Path(sys.argv[1]),False)\n'
        'except OSError as e:sys.exit(0 if e.errno==13 else 2)\n'
        'else:lease.close();sys.exit(3)\n')
    result = subprocess.run([sys.executable,'-I','-B','-c',code,str(root)],
        capture_output=True,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
    assert result.returncode == 0,(result.returncode,result.stderr.decode(errors='replace'))


@pytest.mark.skipif(os.name != 'nt',reason='real Windows Job')
@pytest.mark.parametrize('mode',['success','after_terminal','child_failure'])
def test_real_saved_job_outer_envelope(tmp_path,environment,synthetic_reports,monkeypatch,mode):
    child_command(monkeypatch,tmp_path,'nonzero' if mode == 'child_failure' else 'normal')
    upstream,config,origin,state = environment
    c = api.TimedSavedController(tmp_path/'timed_controller_non_authoritative',
        api.saved.bounded.source.static_network(state['data']),replace(spec(),time_limit_seconds=5.),
        api.saved.replay.H1HourReplayLimits(3,100,500),origin=origin,upstream_root=upstream,
        config_path=config,dc_bus=1,hours=1,
        budget=api.saved.process.TaskProcessBudget(180.,.05,512*api.saved.MIB,768*api.saved.MIB,2.))
    try:
        raws = raw_files(tmp_path/'raw',synthetic_reports)
        def run():
            return c.step_saved_job(raws,expected_source_identity=source_pin(environment),expected_head=c.inspect().head)
        if mode == 'after_terminal':
            write = api.io.write_metadata
            def fail(path,doc):
                pin = write(path,doc)
                if path == c.timing_root/'000'/'terminal.json': raise OSError('outer terminal confirmation')
                return pin
            monkeypatch.setattr(api.io,'write_metadata',fail)
            with pytest.raises(OSError,match='outer terminal confirmation'): run()
            assert c._parent._journal.inspect().events == 2
            assert getattr(c,'last_observation',None) is None and c._timing_poisoned
            return
        if mode == 'child_failure':
            with pytest.raises(ValueError,match='Job unresolved'): run()
            assert c._parent._journal.inspect().events == 1
            observed = json.loads((c._lease.root/'job_000_non_authoritative'/'observation.json').read_bytes())
            assert observed['exit_code'] == 7 and observed['whole_job_quiescent']
            assert not (c.timing_root/'000'/'terminal.json').exists()
            assert getattr(c,'last_observation',None) is None
            return
        result = run()
        assert result.status == 'complete' and result.completed_hours == 1
        out = read_controller(c)
        assert out['outcome_head'] == result.head and not out['scientific_replay_verified']
        assert c.last_observation.transaction_wall_ns > 0 and c.last_observation.confirmation_tail_ns > 0
        assert not out['component_budget_verified'] and not result.formal_result
        job = c._lease.root/'job_000_non_authoritative'
        observed = json.loads((job/'observation.json').read_bytes())
        assert observed['whole_job_quiescent'] and observed['exit_code'] == 0
        assert observed['pid'] != os.getpid()
        write = api.io.write_metadata
        def check_close_lease(path,doc):
            if path == c.timing_root/'close.json':
                assert c._lease is None and c._timing_lease.locked
                with pytest.raises(ValueError,match='already held'):
                    api.saved.bounded.chunks.base.local._Lease(c.timing_root,False)
                assert_other_process_cannot_open(c.timing_root)
            return write(path,doc)
        monkeypatch.setattr(api.io,'write_metadata',check_close_lease)
    finally: c.close()
    assert c.close_observation.transaction_wall_ns > 0
    files = [p for p in c.timing_root.rglob('*') if p.is_file()]
    bound = api.additional_content_bound(1)
    assert len(files) == bound['files'] and sum(p.stat().st_size for p in files) <= bound['bytes']
