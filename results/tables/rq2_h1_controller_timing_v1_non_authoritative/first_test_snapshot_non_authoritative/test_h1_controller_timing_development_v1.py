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


def read_controller(c, index=0):
    p = c.timing_root/f'{index:03d}'
    return api.inspect(c.timing_root,index,expected_binding_sha=c.binding_sha256,
        expected_intent_sha=api.io.digest((p/'intent.json').read_bytes()),
        expected_terminal_sha=c.last_observation.terminal_sha256,
        expected_implementation=c._timing_implementation)


@pytest.fixture
def fake(tmp_path, monkeypatch):
    clock = SimpleNamespace(now=100)
    calls = []
    def init(c,root):
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
    c = api.TimedSavedController(tmp_path/'controller',clock=lambda:clock.now)
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
    assert read_controller(c)['confirmation_tail_ns'] is None
    c.close()
    assert c.close_observation.transaction_wall_ns == 30
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
    assert not hasattr(c,'last_observation')
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


@pytest.mark.skipif(os.name != 'nt',reason='real Windows Job')
def test_real_saved_job_outer_envelope(tmp_path,environment,synthetic_reports,monkeypatch):
    child_command(monkeypatch,tmp_path)
    upstream,config,origin,state = environment
    c = api.TimedSavedController(tmp_path/'timed_controller',
        api.saved.bounded.source.static_network(state['data']),replace(spec(),time_limit_seconds=5.),
        api.saved.replay.H1HourReplayLimits(3,100,500),origin=origin,upstream_root=upstream,
        config_path=config,dc_bus=1,hours=1,
        budget=api.saved.process.TaskProcessBudget(180.,.05,512*api.saved.MIB,768*api.saved.MIB,2.))
    try:
        raws = raw_files(tmp_path/'raw',synthetic_reports)
        result = c.step_saved_job(raws,expected_source_identity=source_pin(environment),expected_head=c.inspect().head)
        assert result.status == 'complete' and result.completed_hours == 1
        out = read_controller(c)
        assert out['outcome_head'] == result.head and not out['scientific_replay_verified']
        assert c.last_observation.transaction_wall_ns > 0 and c.last_observation.confirmation_tail_ns > 0
        assert not out['component_budget_verified'] and not result.formal_result
        job = c._lease.root/'job_000_non_authoritative'
        observed = json.loads((job/'observation.json').read_bytes())
        assert observed['whole_job_quiescent'] and observed['exit_code'] == 0
        assert observed['pid'] != os.getpid()
    finally: c.close()
    assert c.close_observation.transaction_wall_ns > 0
    files = [p for p in c.timing_root.rglob('*') if p.is_file()]
    bound = api.additional_content_bound(1)
    assert len(files) == bound['files'] and sum(p.stat().st_size for p in files) <= bound['bytes']
