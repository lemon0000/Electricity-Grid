from dataclasses import replace
import json
import os
from pathlib import Path

import pytest

from experiments import h1_job_clock_bridge_development_v1 as api
from tests.test_h1_timed_job_controller_development_v1 import install_launcher,step
from tests.test_h1_saved_source_parent_development_v1 import environment
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour

pytestmark = pytest.mark.skipif(os.name != 'nt',reason='owned Windows QPC/Job integration')


def make(root,env,hours=1):
    upstream,config,origin,state = env
    b = api.base
    return api.Controller(root,b.parent.source.static_network(state['data']),replace(spec(),time_limit_seconds=5.),
        b.old.replay.H1HourReplayLimits(3,100,500),origin=origin,upstream_root=upstream,config_path=config,
        dc_bus=1,hours=hours,budget=b.old.process.TaskProcessBudget(300.,.05,512*b.old.MIB,768*b.old.MIB,2.))


def test_interval_arithmetic_and_bounds():
    values = dict(transaction_start=10,job_start=20,worker_start=30,worker_end=80,job_end=90,
        transaction_end=100,native_total=40)
    result = api.analyse(**values)
    assert result == dict(transaction_wall_ns=90,job_window_ns=70,worker_window_ns=50,
        native_total_ns=40,observed_non_native_ns=50)
    for key,value in [('job_start',5),('worker_start',19),('worker_end',91),('transaction_end',89),
                      ('native_total',51),('native_total',True),('job_end',2**63),('worker_end',-1)]:
        with pytest.raises(ValueError):api.analyse(**dict(values,**{key:value}))
    assert api.additional_content_bound(192)['logical_bytes'] == 577*api.CAP+1
    for value in (0,193,True):
        with pytest.raises(ValueError):api.additional_content_bound(value)
    with pytest.raises(TypeError):api.Observation(())


def test_clock_replacement_rejected(monkeypatch):
    assert api.profile()['implementation'] == 'QueryPerformanceCounter()'
    monkeypatch.setattr(api.time,'perf_counter_ns',lambda:1)
    with pytest.raises(ValueError,match='fixed'):api.profile()


def test_two_owned_jobs_clock_containment_and_fresh_replay(tmp_path,environment,synthetic_reports,monkeypatch):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c = make(tmp_path/'clock_controller_non_authoritative',environment,hours=2)
    captured = [];original = c._job
    def job(*args,**kwargs):
        captured.append(args[1]);return original(*args,**kwargs)
    monkeypatch.setattr(c,'_job',job)
    try:
        first = step(c,environment);one = c.last_observation
        assert first.completed_hours == 1 and one.live_clock_profile_and_containment_checked
        rows,_ = synthetic_next_hour(c._parent,environment,synthetic_reports)
        install_launcher(monkeypatch,tmp_path,rows,label='next')
        final = step(c,environment,1);two = c.last_observation
        assert final.status == 'complete' and two.index == 1
        for index,(observation,item) in enumerate(zip((one,two),captured)):
            path = c.clock_root/f'{index:03d}'
            intent_pin = api.io.digest((path/'intent.json').read_bytes())
            checked = api.inspect(c.clock_root,index,item.packet,item.specification,item.limits,
                binding_pin=c.binding_pin,intent_pin=intent_pin,terminal_pin=observation.terminal_sha256)
            assert checked['native_total_ns'] == observation.native_total_ns
            assert checked['transaction_wall_ns'] == observation.transaction_wall_ns
            assert observation.observed_non_native_ns == observation.transaction_wall_ns-observation.native_total_ns
            assert observation.confirmation_tail_ns >= 0
            assert not checked['live_clock_bridge_authenticated'] and not checked['formal_result']
        files=[p for p in c.clock_root.rglob('*') if p.is_file()]
        bound=api.additional_content_bound(2)
        assert len(files)==bound['files'] and sum(p.stat().st_size for p in files)<=bound['logical_bytes']
        # Fresh reader rejects a different clock profile even with an externally
        # supplied updated binding pin; live controller still retains old bytes.
        path=c.clock_root/'binding.json';raw=path.read_bytes();doc=json.loads(raw)
        doc['clock']['units']='seconds';path.write_bytes(api.io.encode(doc))
        with pytest.raises(ValueError,match='binding differs'):
            api.inspect(c.clock_root,1,captured[1].packet,captured[1].specification,captured[1].limits,
                binding_pin=api.io.digest(path.read_bytes()),intent_pin=intent_pin,terminal_pin=two.terminal_sha256)
        path.write_bytes(raw)
    finally:c.close()


@pytest.mark.parametrize('fault',['job_before','job_after','terminal_before','terminal_after','final_read','late_job'])
def test_clock_publication_failures_never_return_or_retry(tmp_path,environment,synthetic_reports,monkeypatch,fault):
    install_launcher(monkeypatch,tmp_path,synthetic_reports)
    c=make(tmp_path/'clock_controller_non_authoritative',environment)
    original=c._save
    def save(path,doc):
        target='job.json' if fault.startswith('job_') else 'terminal.json'
        if path.name==target and fault.endswith(('_before','_after')):
            if fault.endswith('_after'):original(path,doc)
            raise OSError(fault)
        return original(path,doc)
    monkeypatch.setattr(c,'_save',save)
    original_inspect=api.inspect;reached=[]
    def inspect(*args,**kwargs):
        result=original_inspect(*args,**kwargs);reached.append(True)
        if fault=='final_read':raise OSError(fault)
        if fault=='late_job':
            path=c._lease.root/'job_000_non_authoritative/worker_non_authoritative/hour_non_authoritative/commits/000.json'
            raw=path.read_bytes();path.write_bytes(b'['+raw[1:])
        return result
    monkeypatch.setattr(api,'inspect',inspect)
    try:
        with pytest.raises((OSError,ValueError)):step(c,environment)
        assert c._clock_poisoned and c._parent._poisoned and c.last_observation is None
        assert c._parent._journal.inspect().events==(1 if fault.startswith('job_') else 2)
        if fault in ('final_read','late_job'):assert reached==[True]
        job=c._lease.root/'job_000_non_authoritative'
        assert json.loads((job/'observation.json').read_bytes())['exit_code']==0
        assert (job/'worker_result.json').exists()
        with pytest.raises(ValueError):c.step(expected_source_identity='a'*64,expected_head='b'*64)
        assert not (c._lease.root/'job_001_non_authoritative').exists()
    finally:c.close()


def test_close_detaches_clock_lease_before_replacement(tmp_path,environment,monkeypatch):
    c=make(tmp_path/'clock_controller_non_authoritative',environment)
    Lease=api.base.old.bounded.chunks.base.local._Lease
    owner=c._clock_lease;root=owner.root;original=Lease.close;replacement=[]
    def close(lease):
        original(lease)
        if lease is owner:
            replacement.append(Lease(root,False));raise OSError('confirmation')
    monkeypatch.setattr(Lease,'close',close)
    with pytest.raises(OSError,match='confirmation'):c.close()
    assert c._clock_lease is None and c._lease is None
    c.close();replacement[0].check()
    original(replacement[0])
