from contextlib import contextmanager
from dataclasses import asdict, replace
import json
import importlib.util
import os
from pathlib import Path
import sys
import time

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
    # Pytest's pygments dependency is in the current user's site directory;
    # only this test shim explicitly locates it. The default worker does not.
    test_dependency=str(Path(importlib.util.find_spec('pygments').origin).parent.parent)
    code=(f'import sys,os;from pathlib import Path;sys.path.insert(0,{str(Path.cwd())!r});'
        f'sys.path.append({test_dependency!r});'
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
    wrapped='try:\n'+''.join('    '+line+'\n' for line in code.splitlines())
    wrapped+='except BaseException:\n    import traceback\n    from pathlib import Path\n    (Path.cwd()/"saved_job_worker_error.txt").write_bytes(traceback.format_exc().encode()[:4096])\n    raise\n'
    def argv(path,pin):return [sys.executable,'-I','-B','-c',wrapped,str(path),pin]
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
    c=controller(tmp_path/'jobs_non_authoritative',environment,seconds=90.)
    raws=raw_files(tmp_path/'raw',synthetic_reports)
    original=api._read;result_reads=[]
    def observe(path,*a,**k):
        if path.name=='worker_result.json':result_reads.append(path)
        return original(path,*a,**k)
    monkeypatch.setattr(api,'_read',observe)
    if mode=='timeout_result':
        original_wait=api.process.NormalTaskChild.wait
        def after_marker(owner):
            marker=c._lease.root/'job_000_non_authoritative'/'worker_result.json'
            deadline=time.monotonic()+20
            while not marker.exists() and time.monotonic()<deadline:time.sleep(.02)
            assert marker.exists(),'worker did not reach the result-before-exit window'
            owner._started-=owner._budget.max_elapsed_seconds+1
            return original_wait(owner)
        monkeypatch.setattr(api.process.NormalTaskChild,'wait',after_marker)
    try:
        with pytest.raises(ValueError,match='Job unresolved'):step(c,environment,raws)
        assert not result_reads
        root=c._lease.root/'job_000_non_authoritative'
        observed=json.loads((root/'observation.json').read_bytes())
        assert observed['whole_job_quiescent'] and observed['exit_code']!=0
        assert c._parent._journal.inspect().events==1
        assert not (root/'job_checks.json').exists()
        error=root/'scratch_non_authoritative'/'saved_job_worker_error.txt'
        if mode=='identity':assert 'released exact child identity required' in error.read_text()
        if mode=='consume':assert 'FileExistsError' in error.read_text()
        if mode in ('nonzero','after_result'):assert observed['exit_code']==7
        if mode=='timeout_result':assert observed['reason']=='task_deadline_stop'
        if mode in ('after_result','timeout_result'):
            error=root/'scratch_non_authoritative'/'saved_job_worker_error.txt'
            assert (root/'worker_result.json').is_file(),error.read_text() if error.exists() else observed
        if mode=='identity':assert not (root/'consumed.json').exists()
        stopped(c,environment,raws)
    finally:c.close()


@pytest.mark.parametrize('window',['child.json','release_intent.json','after_release_intent'])
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
    if window=='after_release_intent':
        def release_failure(*a,**k):raise OSError('injected pre-release failure')
        monkeypatch.setattr(api.process.NormalTaskChild,'release',release_failure)
    try:
        with pytest.raises(OSError):step(c,environment,raws)
        assert len(handles)==1 and _winapi.WaitForSingleObject(handles[0],1000)==0
        assert not (c._lease.root/'job_000_non_authoritative'/'consumed.json').exists()
        if window=='after_release_intent':assert (c._lease.root/'job_000_non_authoritative'/'release_intent.json').exists()
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


def test_observation_write_failure_does_not_read_completed_worker_result(tmp_path,environment,synthetic_reports,monkeypatch):
    child_command(monkeypatch,tmp_path)
    c=controller(tmp_path/'jobs_non_authoritative',environment)
    raws=raw_files(tmp_path/'raw',synthetic_reports)
    original_write,original_read=api._write,api._read
    result_reads=[]
    def fail(path,*a,**k):
        if path.name=='observation.json':raise OSError('injected observation persistence failure')
        return original_write(path,*a,**k)
    def observe(path,*a,**k):
        if path.name=='worker_result.json':result_reads.append(path)
        return original_read(path,*a,**k)
    monkeypatch.setattr(api,'_write',fail)
    monkeypatch.setattr(api,'_read',observe)
    try:
        with pytest.raises(OSError,match='observation persistence'):step(c,environment,raws)
        assert not result_reads
        root=c._lease.root/'job_000_non_authoritative'
        assert (root/'worker_result.json').is_file() and (root/'consumed.json').is_file()
        assert (c._parent._root/'hour_000_non_authoritative'/'terminal.json').is_file()
        assert not (root/'observation.json').exists() and not (root/'job_checks.json').exists()
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


@pytest.mark.parametrize('name',sorted(api.RECORD_FIELDS))
def test_record_schema_rejects_missing_or_extra_fields(name):
    base={key:None for key in api.RECORD_FIELDS[name]}
    with pytest.raises(ValueError,match='exact saved Job record schema'):
        api._record(Path(name),dict(base,unexpected=True))
    del base[next(iter(base))]
    with pytest.raises(ValueError,match='exact saved Job record schema'):
        api._record(Path(name),base)


def test_default_entry_real_pinned_rts_input_rejects_saved_raw_before_outcome(tmp_path):
    root=Path(__file__).resolve().parents[1]
    old=json.loads((root/'results/tables/rq2_normal_h1_origin_calibration_v3_non_authoritative/request.json').read_bytes())
    origin=api.snapshot.binding.H1SourceDeclaration(**old['source_declaration'])
    receipt=api.snapshot.binding.load_pinned_current(origin,old['upstream_root'],config_path=old['config_path'])
    c=api.SavedJobController(tmp_path/'actual_saved_job_non_authoritative',receipt.network,
        api.snapshot.Rq2SolverSpec(**old['work']['specification']),api.replay.H1HourReplayLimits(**old['limits']),
        origin=origin,upstream_root=old['upstream_root'],config_path=old['config_path'],dc_bus=old['dc_bus'],hours=1,
        budget=api.process.TaskProcessBudget(90.,.05,512*api.MIB,768*api.MIB,2.))
    invalid=raw_files(tmp_path/'invalid_raw',[b'{}'])[0]
    try:
        with pytest.raises(ValueError,match='Job unresolved'):
            c.step_saved_job((invalid,)*232,expected_source_identity=receipt.identity,expected_head=c.inspect().head)
        job=c._lease.root/'job_000_non_authoritative'
        request=json.loads((job/'request.json').read_bytes())
        assert request['input_receipt']['stage_slots']==232
        assert (job/'consumed.json').is_file()
        core=c._parent._root/'hour_000_non_authoritative'/'attested_hour_non_authoritative'
        assert (core/'raw'/'000'/'raw.bin').read_bytes()==b'{}'
        assert not (core/'attestation_terminal.json').exists()
        observed=json.loads((job/'observation.json').read_bytes())
        assert observed['exit_code']==2 and observed['whole_job_quiescent']
        assert c._parent._journal.inspect().events==1 and c._parent._poisoned
        assert not (job/'worker_result.json').exists()
    finally:c.close()


@pytest.mark.parametrize('change',['sufficient','reservation','hard_limits','formal_authority','clock',
    'commit_type','commit_shortage','disk_type','volume_requirements','disk_inventory'])
def test_initial_headroom_record_is_recomputed(tmp_path,change):
    resources=api.process.resources
    host=resources.HostResourceBudget(api.MIB,api.MIB,(resources.DirectoryDemand('test',str(tmp_path),api.MIB,api.MIB),))
    observation=resources.observe_headroom(host,expected_request_identity=resources.resource_identity(host))
    value=json.loads(api.io.encode(asdict(observation)))
    api._validate_initial(value,host)
    if change=='sufficient':value['observed_headroom_sufficient']=False
    if change=='reservation':value['resource_reservation_held']=True
    if change=='hard_limits':value['hard_resource_limits_enforced']=True
    if change=='formal_authority':value['formal_run_authorized']=True
    if change=='clock':value['finished_monotonic_seconds']=float('nan')
    if change=='commit_type':value['commit']['page_size_bytes']=True
    if change=='commit_shortage':value['commit']['limit_pages']=value['commit']['committed_pages']
    if change=='disk_type':value['disks'][0]['caller_available_bytes']=True
    if change=='volume_requirements':value['volume_requirements'][0][1]+=1
    if change=='disk_inventory':value['disks']=[]
    with pytest.raises(ValueError):api._validate_initial(value,host)
