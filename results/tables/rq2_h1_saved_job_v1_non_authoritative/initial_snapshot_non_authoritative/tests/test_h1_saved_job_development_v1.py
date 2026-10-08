from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import sys

import pytest

from experiments import h1_saved_job_development_v1 as api
from tests.test_h1_saved_source_parent_development_v1 import environment,source_pin
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver,spec
from tests.test_h1_attested_saved_hour_development_v1 import synthetic_reports,saved
from tests.test_h1_attested_source_parent_development_v1 import synthetic_next_hour
from tests.test_h1_parent_snapshot_development_v1 import files

pytestmark=pytest.mark.skipif(os.name!='nt',reason='actual Windows Job tests')


def install_child_source(base):
    """Test-only synthetic loader installation, with existing source bytes untouched."""
    monkeypatch=pytest.MonkeyPatch()
    mkdir,write=Path.mkdir,Path.write_bytes
    expected={base/'upstream'/'SHA256SUMS':b'synthetic-current-source\n',base/'source.yaml':b'{}'}
    with pytest.MonkeyPatch.context() as temporary:
        def same_mkdir(path,*args,**kwargs):
            if path==base/'upstream':
                assert path.is_dir()
                return None
            return mkdir(path,*args,**kwargs)
        def same_write(path,data):
            if path in expected:
                assert path.read_bytes()==data==expected[path]
                return len(data)
            return write(path,data)
        temporary.setattr(Path,'mkdir',same_mkdir)
        temporary.setattr(Path,'write_bytes',same_write)
        value=supplied.__wrapped__(base,monkeypatch)
    environment.__wrapped__(value,monkeypatch)
    return monkeypatch


def child_command(monkeypatch,base,mode='normal'):
    code=(f'import sys,os;from pathlib import Path;sys.path.insert(0,{str(Path.cwd())!r});'
        'from tests.test_h1_saved_job_development_v1 import install_child_source;'
        f'patch=install_child_source(Path({str(base)!r}));'
        'from experiments import h1_saved_job_development_v1 as api;')
    if mode=='identity':code+="api._current_process=lambda:(os.getpid(),1);"
    if mode=='consume':code+="(Path(sys.argv[1]).parent/'consumed.json').write_bytes(b'partial');"
    if mode=='timeout_result':
        code+="(Path(sys.argv[1]).parent/'worker_result.json').write_bytes(b'{}');import time;time.sleep(30);"
    elif mode=='nonzero':code+='raise SystemExit(7);'
    else:
        code+='api.execute_saved_worker(*sys.argv[1:]);'
        if mode=='after_result':code+='raise SystemExit(7);'
        if mode=='twice':
            code+='\ntry:api.execute_saved_worker(*sys.argv[1:])\nexcept FileExistsError:pass\nelse:raise AssertionError("reused consumption")\n'
    def argv(path,pin):return [sys.executable,'-I','-B','-c',code,str(path),pin]
    monkeypatch.setattr(api,'_argv',argv)


def controller(root,env,hours=1,seconds=180.):
    upstream,config,origin,state=env
    return api.SavedJobController(root,api.bounded.source.static_network(state['data']),
        replace(spec(),time_limit_seconds=5.),api.replay.H1HourReplayLimits(3,100,500),origin=origin,
        upstream_root=upstream,config_path=config,dc_bus=1,hours=hours,
        budget=api.process.TaskProcessBudget(seconds,.05,512*api.MIB,768*api.MIB,2.))


def raw_files(root,reports):
    root.mkdir()
    output=[]
    for index,raw in enumerate(reports):
        path=root/f'{index:03d}.bin';path.write_bytes(raw)
        output.append(api.SavedRaw(str(path.resolve()),api.io.digest(raw),len(raw)))
    return tuple(output)


def step(c,env,raws,hour=0):
    return c.step_saved_job(raws,expected_source_identity=source_pin(env,hour),expected_head=c.inspect().head)


def stopped(c,env,raws):
    old=files(c._lease.root)
    with pytest.raises(ValueError):c.step_saved_job(raws,expected_source_identity=source_pin(env),expected_head='f'*64)
    assert files(c._lease.root)==old
    assert c._parent._poisoned


def test_two_real_saved_jobs_reconstruct_carry_and_consume_once(tmp_path,environment,synthetic_reports,monkeypatch):
    child_command(monkeypatch,tmp_path,'twice')
    c=controller(tmp_path/'jobs_non_authoritative',environment,2)
    raws=raw_files(tmp_path/'raw_origin',synthetic_reports)
    try:
        one=step(c,environment,raws)
        assert one.completed_hours==1 and one.status=='ready'
        reports,_=synthetic_next_hour(c._parent,environment,synthetic_reports)
        two=step(c,environment,raw_files(tmp_path/'raw_next',reports),1)
        assert two.completed_hours==2 and two.status=='complete'
        assert not two.independent_hour_jobs_integrated and not two.formal_result
        records=[]
        for hour in range(2):
            root=c._lease.root/f'job_{hour:03d}_non_authoritative'
            request=json.loads((root/'request.json').read_bytes())
            records.append(request['input_receipt'])
            observed=json.loads((root/'observation.json').read_bytes())
            assert observed['exit_code']==0 and observed['whole_job_quiescent']
            assert observed['pid']!=os.getpid()
            assert observed['job_commit_limits_configured']
            assert (root/'consumed.json').is_file() and (root/'job_checks.json').is_file()
            bound=api.job_storage_bound()
            actual=[f for f in root.rglob('*') if f.is_file()]
            assert len(actual)<=bound['files'] and sum(f.stat().st_size for f in actual)<=bound['logical_bytes']
        assert records[0]['before_identity']!=records[1]['before_identity']
        assert records[1]['relative_hour']==1
        for declaration in raws:declaration.read()
    finally:c.close()


@pytest.mark.parametrize('mode',['identity','consume','nonzero','after_result','timeout_result'])
def test_child_failures_never_publish_parent_outcome(tmp_path,environment,synthetic_reports,monkeypatch,mode):
    child_command(monkeypatch,tmp_path,mode)
    c=controller(tmp_path/'jobs_non_authoritative',environment,seconds=3. if mode=='timeout_result' else 90.)
    raws=raw_files(tmp_path/'raw',synthetic_reports)
    original=api._read;result_reads=[]
    def observe(path,*a,**k):
        if path.name=='worker_result.json':result_reads.append(path)
        return original(path,*a,**k)
    monkeypatch.setattr(api,'_read',observe)
    try:
        with pytest.raises(ValueError,match='Job unresolved'):step(c,environment,raws)
        assert not result_reads
        root=c._lease.root/'job_000_non_authoritative'
        observed=json.loads((root/'observation.json').read_bytes())
        assert observed['whole_job_quiescent'] and observed['exit_code']!=0
        assert c._parent._journal.inspect().events==1
        assert not (root/'job_checks.json').exists()
        if mode in ('after_result','timeout_result'):assert (root/'worker_result.json').is_file()
        if mode=='identity':assert not (root/'consumed.json').exists()
        stopped(c,environment,raws)
    finally:c.close()


@pytest.mark.parametrize('window',['child.json','release_intent.json'])
def test_suspended_child_is_quiesced_on_controller_failure(tmp_path,environment,synthetic_reports,monkeypatch,window):
    import _winapi
    child_command(monkeypatch,tmp_path)
    c=controller(tmp_path/'jobs_non_authoritative',environment)
    raws=raw_files(tmp_path/'raw',synthetic_reports)
    original=api.process.normal_task_child;handles=[]
    @contextmanager
    def capture(*a,**k):
        with original(*a,**k) as child:
            handles.append(_winapi.DuplicateHandle(_winapi.GetCurrentProcess(),child._child._process,
                _winapi.GetCurrentProcess(),0,False,_winapi.DUPLICATE_SAME_ACCESS))
            yield child
    monkeypatch.setattr(api.process,'normal_task_child',capture)
    write=api._write
    def fail(path,*a,**k):
        if path.name==window:raise OSError('injected publication failure')
        return write(path,*a,**k)
    monkeypatch.setattr(api,'_write',fail)
    try:
        with pytest.raises(OSError):step(c,environment,raws)
        assert len(handles)==1 and _winapi.WaitForSingleObject(handles[0],1000)==0
        assert not (c._lease.root/'job_000_non_authoritative'/'consumed.json').exists()
        assert c._parent._journal.inspect().events==1
        stopped(c,environment,raws)
    finally:
        c.close()
        for handle in handles:_winapi.CloseHandle(handle)


def test_source_raw_replacement_after_worker_is_not_accepted(tmp_path,environment,synthetic_reports,monkeypatch):
    child_command(monkeypatch,tmp_path)
    c=controller(tmp_path/'jobs_non_authoritative',environment)
    raws=raw_files(tmp_path/'raw',synthetic_reports)
    original=c._job
    def changed(*a,**k):
        result=original(*a,**k)
        path=Path(raws[0].path);path.write_bytes(path.read_bytes()+b' ')
        return result
    monkeypatch.setattr(c,'_job',changed)
    try:
        with pytest.raises(ValueError,match='saved source raw differs'):step(c,environment,raws)
        assert (c._parent._root/'hour_000_non_authoritative'/'terminal.json').is_file()
        assert c._parent._journal.inspect().events==1
        stopped(c,environment,raws)
    finally:c.close()


@pytest.mark.parametrize('field,value',[('whole_job_quiescent',False),('exit_code',True),
    ('job_commit_limits_configured',False),('formal_result',True),('job_peak_total_commit_bytes',2**40),
    ('elapsed_seconds',float('nan')),('runtime_samples',True),('creation_filetime',13)])
def test_observation_gate_rejects_unresolved_or_overclaim(field,value):
    budget=api.process.TaskProcessBudget(30.,.05,512*api.MIB,768*api.MIB,2.)
    observation=api.process.TaskProcessObservation('a'*64,11,12,0,'child_exited',1.,1,
        None,(),(),None,(),128*api.MIB,128*api.MIB,True)
    api._validate_observation(observation,'a'*64,11,12,budget)
    with pytest.raises(ValueError):api._validate_observation(replace(observation,**{field:value}),'a'*64,11,12,budget)
