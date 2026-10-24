"""Parent-owned short Python creation and separate synthetic P2 metadata."""
import ast
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import sys
from types import SimpleNamespace

import pytest

from src import staged_rts24_p2_outer_v1 as d
from src import staged_rts24_p2_package_check_v2 as checker
from test_staged_rts24_p2_package_check_v1 import inputs, build, balance, process as legacy_process, forbid_scientific_execution, ROOT


def outer_process(record):
    return dict(record, terminal_reserved_bytes=131072, parent_reserved_bytes=131072,
        parent_reserved_files=1, terminal_reserved_files=1, member_handle_cap=1024)


def fact(context, context_sha, record):
    expected=context['kernel_context']['startup']
    return d.startup_image(dict(schema='staged_rts24_parent_CreateProcess_inputs_v1',authority='DRAFT_NONAUTHORITATIVE',
        context_sha=context_sha,parent_pid=os.getpid(),owner_pid=record['owner_pid'],owner_creation_filetime=record['owner_creation_filetime'],
        argv=expected['argv'],command_line=subprocess.list2cmdline(expected['argv']),cwd=str(Path(expected['cwd']).resolve()),
        environment_sha=context['environment_sha'],created_suspended_in_owned_job=True,actual_os_commandline_independently_verified=False))


def upgrade(case):
    for name in d.SOURCES:
        path=case.inputs.repo/name;path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes((ROOT/name).read_bytes())
    raw=d.context_bytes(case.context);context=d.codec.parse(raw);identity=sha256(raw).hexdigest()
    case.process=outer_process(case.process);startup=fact(context,identity,case.process)
    (case.worker/'outer_context.json').write_bytes(raw);(case.worker/'outer_startup.json').write_bytes(startup)
    case.snapshot=balance(case)
    return SimpleNamespace(case=case,raw=raw,context=context,sha=identity,startup=startup)


@pytest.fixture(scope='module')
def numeric(inputs,tmp_path_factory):return upgrade(build(inputs,tmp_path_factory.mktemp('outer_numeric'),1,numeric=True))


def test_new_protocol_only_extends_the_declared_root_file_set():
    def protocol(path):
        node=next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.FunctionDef) and n.name=='protocol')
        return ast.dump(node,include_attributes=False)
    legacy=(ROOT/'src/staged_rts24_p2_package_check_v1.py').read_text(encoding='utf-8')
    node=next(n for n in ast.parse(legacy).body if isinstance(n,ast.FunctionDef) and n.name=='protocol')
    expected=ast.get_source_segment(legacy,node).replace("'launcher_start.json','start.json'", "'outer_context.json','outer_startup.json','launcher_start.json','start.json'")
    assert protocol(ROOT/'src/staged_rts24_p2_package_check_v2.py')==ast.dump(ast.parse(expected).body[0],include_attributes=False)


def test_saved_reference_numeric_closes_metadata_with_v3_outer_and_v2_inner(numeric):
    result=checker.inspect_package(numeric.raw,numeric.sha,numeric.case.process,numeric.startup)
    assert result['inspection_status']=='numeric_diagnostic_closed',result['protocol_error']
    assert result['startup_record_schema_verified'] and result['point_reference_count']==1
    assert result['points_imported']==result['contract_row_reference_count']==0
    assert result['outer_residual_member_count']==2
    assert all(result[n] is False for n in ('scientific_evidence_adopted','actual_os_commandline_independently_verified',
        'actual_spawn_argv_verified','full_runtime_closure_verified','formal_result','resource_admission'))


def test_legacy_protocol_rejects_new_roots_after_accepting_legacy_launcher_shape(numeric):
    case=numeric.case;raw=dict(case.snapshot['raw']);record=dict(case.process)
    for key in ('parent_reserved_bytes','parent_reserved_files','terminal_reserved_files','member_handle_cap'):record.pop(key)
    record['terminal_reserved_bytes']=16384
    raw['launcher.json']=d.codec.canonical(record)
    snapshot={**case.snapshot,'raw':raw,'pins':{n:d.kernel.pin(b) for n,b in raw.items()}}
    packet=json.loads((case.inputs.packet/'packet.json').read_bytes())
    with pytest.raises(ValueError,match='unknown or missing root file'):
        d.kernel.protocol(snapshot,json.loads(case.context),case.reg,packet,record,True)


@pytest.mark.parametrize('field',['context_sha','owner_pid','argv','cwd','environment_sha','command_line','created_suspended_in_owned_job'])
def test_held_startup_fact_substitution_is_rejected(numeric,field):
    value=json.loads(numeric.startup)
    if field=='owner_pid':value[field]+=1
    elif field=='argv':value[field]=value[field]+['extra']
    elif field=='created_suspended_in_owned_job':value[field]=False
    else:value[field]='changed'
    with pytest.raises(ValueError):checker.inspect_package(numeric.raw,numeric.sha,numeric.case.process,d.startup_image(value))


@pytest.mark.parametrize('name',['outer_context.json','outer_startup.json'])
def test_saved_outer_bytes_cannot_be_substituted(numeric,name):
    path=numeric.case.worker/name;original=path.read_bytes()
    try:
        path.write_bytes(b'changed')
        with pytest.raises(ValueError,match='outer/startup'):checker.inspect_package(numeric.raw,numeric.sha,numeric.case.process,numeric.startup)
    finally:path.write_bytes(original)


def test_unknown_quiet_never_reaches_source_or_worker_reads(numeric,monkeypatch):
    record=dict(numeric.case.process,job_quiet_confirmed=False)
    monkeypatch.setattr(d,'read_inputs',lambda *a:pytest.fail('unknown Job read inputs'))
    monkeypatch.setattr(checker.old,'inventory',lambda *a:pytest.fail('unknown Job inventoried'))
    result=checker.inspect_package(numeric.raw,numeric.sha,record,b'not read')
    assert result['inspection_status']=='inspection_prohibited' and result['inventory'] is None


def test_new_source_drift_is_rejected_before_inventory(numeric,monkeypatch):
    target=numeric.case.inputs.repo/d.SOURCES[0];raw=target.read_bytes()
    try:
        target.write_bytes(raw+b'\n')
        monkeypatch.setattr(checker.old,'inventory',lambda *a:pytest.fail('source drift inventoried'))
        with pytest.raises(ValueError,match='outer source changed'):checker.inspect_package(numeric.raw,numeric.sha,numeric.case.process,numeric.startup)
    finally:target.write_bytes(raw)


@pytest.mark.skipif(os.name!='nt',reason='Windows owned suspended creation')
def test_real_parent_capture_precedes_release_and_matches_complete_job(tmp_path):
    argv=[sys.executable,'-B','-s','-c','import time;time.sleep(.3)']
    environment=d.guard.controlled_environment();captured=[];checks=[]
    expected=dict(argv=argv,cwd=str(tmp_path));context_sha='a'*64
    def factory(args,**kw):
        return d.StartupOwner(args,expected=expected,context_sha=context_sha,environment_sha=d.digest(environment),
            sink=lambda raw:captured.append(raw),before_release=lambda:checks.append(bool(captured)),**kw)
    limits=dict(d.kernel.CAPS,wall_seconds=5,no_progress_seconds=5)
    record=d.guard.supervise(argv,cwd=tmp_path,output=tmp_path,progress=tmp_path/'events',limits=limits,owner_factory=factory)
    assert record['exit_code']==0 and record['stop_reason'] is None and record['job_quiet_confirmed']
    assert checks==[True] and len(captured)==1
    context=dict(kernel_context=dict(startup=expected),environment_sha=d.digest(environment))
    value=d.check_startup(captured[0],context,context_sha,record)
    assert value['parent_pid']==os.getpid() and value['created_suspended_in_owned_job']
    assert value['actual_os_commandline_independently_verified'] is False


@pytest.mark.parametrize('wrong',['argv','cwd','environment','commit'])
def test_bad_creation_inputs_never_reach_original_owner(tmp_path,monkeypatch,wrong):
    argv=[str(Path(sys.executable).absolute()),'-B','-c','pass'];expected=dict(argv=list(argv),cwd=str(tmp_path))
    env=d.guard.controlled_environment();kw=dict(cwd=tmp_path,max_process_commit_bytes=1024**3,max_job_commit_bytes=2*1024**3,environment=env)
    if wrong=='argv':argv.append('changed')
    elif wrong=='cwd':kw['cwd']=tmp_path.parent
    elif wrong=='environment':kw['environment']={**env,'EXTRA':'changed'}
    else:kw['max_job_commit_bytes']+=1
    monkeypatch.setattr(d.guard.OwnedChild,'__init__',lambda *a,**k:pytest.fail('bad inputs constructed an owner'))
    with pytest.raises(ValueError):d.StartupOwner(argv,expected=expected,context_sha='a'*64,environment_sha=d.digest(env),sink=lambda raw:None,before_release=lambda:None,**kw)


def test_full_319_metadata_with_two_startup_files(inputs,tmp_path):
    full=upgrade(build(inputs,tmp_path))
    binding=d.Binding(full.raw,full.sha)
    # Explicit saved-metadata seam: this fixture was not produced by a P2 run.
    binding._attempted=True;binding._owner_identity=(full.case.process['owner_pid'],full.case.process['owner_creation_filetime'])
    binding.startup_bytes=full.startup
    (full.case.worker/'launcher.json').unlink()
    saved=binding.finish(full.case.process);result=saved['package_inspection']
    assert result['inspection_status']=='success_protocol_closed',result['protocol_error']
    assert (result['point_reference_count'],result['contract_row_reference_count'],result['actual_state_reference_count'])==(319,138,10)
    assert result['mechanical_package_integrity'] and result['startup_record_schema_verified']
    assert result['scientific_evidence_adopted'] is result['resource_admission'] is False
    assert saved['parent_record_saved'] and saved['observation']['caller_supplied_mechanical_claims']['mechanical_package_integrity']
    assert saved['final_storage_accounting']['within_limits']
    with pytest.raises(ValueError,match='already attempted'):binding.finish(full.case.process)
    with pytest.raises(ValueError):d.kernel.inspect_package(full.case.context,full.case.sha,full.case.process,full.case.startup)


def test_unknown_finish_only_saves_parent_diagnostic(numeric,tmp_path,monkeypatch):
    base=json.loads(numeric.case.context);par=tmp_path/'parent';par.mkdir();base['parent_root']=str(par)
    raw=d.context_bytes(d.kernel.validate_context(base));binding=d.Binding(raw,sha256(raw).hexdigest())
    binding._attempted=True  # explicit failed-construction seam, not a P2 launch
    original=d.codec.read_bytes
    def no_worker(path,*a,**kw):
        assert not Path(path).is_relative_to(numeric.case.worker),'unknown Job worker read'
        return original(path,*a,**kw)
    monkeypatch.setattr(d.codec,'read_bytes',no_worker)
    saved=binding.finish(dict(numeric.case.process,job_quiet_confirmed=False))
    assert saved['observation']['inspection_status']=='skipped' and saved['final_storage_accounting'] is None
    assert saved['parent_record_saved']


@pytest.mark.skipif(os.name!='nt',reason='Windows Job cleanup after creation callback failure')
def test_real_failed_capture_closes_suspended_child_before_release(tmp_path):
    import ctypes as C
    from ctypes import wintypes as W
    k=C.WinDLL('kernel32',use_last_error=True)
    k.OpenProcess.argtypes=[W.DWORD,W.BOOL,W.DWORD];k.OpenProcess.restype=W.HANDLE
    k.WaitForSingleObject.argtypes=[W.HANDLE,W.DWORD];k.WaitForSingleObject.restype=W.DWORD
    k.CloseHandle.argtypes=[W.HANDLE];k.CloseHandle.restype=W.BOOL
    retained=[];argv=[sys.executable,'-B','-c','import time;time.sleep(.3)'];env=d.guard.controlled_environment()
    def failed_sink(raw):
        retained.append(k.OpenProcess(0x100000,False,json.loads(raw)['owner_pid']));assert retained[-1]
        raise OSError('capture publication failed')
    try:
        with pytest.raises(OSError,match='capture publication'):
            d.StartupOwner(argv,expected=dict(argv=argv,cwd=str(tmp_path)),context_sha='a'*64,environment_sha=d.digest(env),
                sink=failed_sink,before_release=lambda:pytest.fail('failed capture released'),cwd=tmp_path,
                max_process_commit_bytes=1024**3,max_job_commit_bytes=2*1024**3,environment=env)
        assert retained and k.WaitForSingleObject(retained[0],1000)==0
    finally:
        for handle in retained:assert k.CloseHandle(handle)


@pytest.fixture
def bound(inputs,tmp_path,monkeypatch):
    item=upgrade(build(inputs,tmp_path,1,numeric=True))
    archive=item.case.worker.with_name('saved_protocol');item.case.worker.rename(archive);item.case.worker.mkdir()
    binding=d.Binding(item.raw,item.sha);owners=[]
    def initialize(owner,*a,**kw):
        owner.pid=1000;owner.creation_filetime=4561000;owner.closed=False;owner.released=False;owners.append(owner)
    def release(owner):owner.released=True
    def close(owner):owner.closed=True
    monkeypatch.setattr(d.guard.OwnedChild,'__init__',initialize)
    monkeypatch.setattr(d.guard.OwnedChild,'release',release)
    monkeypatch.setattr(d.guard.OwnedChild,'close',close)
    return SimpleNamespace(binding=binding,item=item,owners=owners)


def create(bound):
    binding=bound.binding;expected=binding.context['kernel_context']['startup']
    return binding.owner_factory(expected['argv'],cwd=Path(expected['cwd']),max_process_commit_bytes=1024**3,
        max_job_commit_bytes=2*1024**3,environment=d.guard.controlled_environment())


def record_for(binding):
    record=outer_process(legacy_process(1000))
    files=[p for p in binding.worker.iterdir() if p.is_file()]
    record.update(terminal_bytes=sum(p.stat().st_size for p in files),terminal_files=len(files))
    return record


def test_binding_publishes_both_facts_before_release_and_refuses_repeat(bound):
    owner=create(bound);binding=bound.binding
    assert not owner.released and (binding.worker/'outer_context.json').read_bytes()==binding.raw
    assert (binding.worker/'outer_startup.json').read_bytes()==owner.startup_bytes==binding.startup_bytes
    owner.release();assert owner.released
    with pytest.raises(ValueError,match='already attempted'):create(bound)
    owner.close()


@pytest.mark.parametrize('stage',['before_open','after_write','after_fsync','after_pending_readback','before_rename','after_rename','after_final_readback'])
def test_startup_atomic_failures_close_created_owner_and_retain_originals(bound,monkeypatch,stage):
    original=d.codec.publish
    def publish(path,raw,hook=None):
        def fault(phase,target):
            if phase==stage:raise OSError('startup publication injected')
        return original(path,raw,fault if Path(path).name=='outer_startup.json' else hook)
    monkeypatch.setattr(d.codec,'publish',publish)
    with pytest.raises(d.codec.PublicationError) as error:create(bound)
    assert error.value.phase==stage and bound.owners[0].closed and not bound.owners[0].released
    target=bound.binding.worker/'outer_startup.json';pending=target.with_name(target.name+'.pending')
    assert target.exists() is (stage in ('after_rename','after_final_readback'))
    assert pending.exists() is (stage not in ('before_open','after_rename','after_final_readback'))
    with pytest.raises(ValueError,match='already attempted'):create(bound)


def test_capture_and_close_failure_retain_both_errors_and_cleanup_capability(bound,monkeypatch):
    original=d.codec.publish
    def publish(path,raw,hook=None):
        def fail(phase,target):
            if phase=='after_rename':raise OSError('original capture error')
        return original(path,raw,fail if Path(path).name=='outer_startup.json' else hook)
    def fail_close(owner):raise OSError('cleanup also failed')
    monkeypatch.setattr(d.codec,'publish',publish);monkeypatch.setattr(d.guard.OwnedChild,'close',fail_close)
    with pytest.raises(d.StartupCaptureUnresolved) as error:create(bound)
    failure=error.value
    assert bound.binding.construction_unresolved is failure and failure.owner is bound.owners[0]
    assert failure.phase=='after_rename' and failure.may_have_published and len(failure.expected_sha)==64
    assert failure.cleanup_unknown and failure.job_quiet_confirmed is False and not failure.owner.closed
    assert 'original capture error' in failure.capture_error['message'] and 'cleanup also failed' in failure.cleanup_error['message']
    assert (bound.binding.worker/'outer_startup.json').exists() and not failure.owner.released
    # No retry or invented quiet; the creating parent retains the original
    # live cleanup capability for explicit controlled cleanup.
    with pytest.raises(ValueError,match='already attempted'):create(bound)


@pytest.mark.parametrize('kind',['raising_attributes','wrong_types','oversized'])
def test_malformed_capture_metadata_cannot_hide_the_cleanup_owner(bound,monkeypatch,kind):
    class BadMetadata(OSError):
        def __str__(self):raise RuntimeError('unprintable')
        def __getattribute__(self,name):
            if kind=='raising_attributes' and name in ('phase','expected_sha','may_have_published'):raise RuntimeError('metadata accessor failed')
            return super().__getattribute__(name)
    capture=BadMetadata()
    capture.phase=object() if kind=='wrong_types' else 'x'*65
    capture.expected_sha=object() if kind=='wrong_types' else 'A'*10000
    capture.may_have_published=object()
    def close(owner):raise OSError('cleanup failed')
    def sink(raw):raise capture
    monkeypatch.setattr(d.guard.OwnedChild,'close',close)
    expected=bound.binding.context['kernel_context']['startup']
    with pytest.raises(d.StartupCaptureUnresolved) as error:
        d.StartupOwner(expected['argv'],expected=expected,context_sha=bound.binding.sha,environment_sha=bound.binding.context['environment_sha'],
            sink=sink,before_release=lambda:pytest.fail('failed capture released'),cwd=expected['cwd'],
            max_process_commit_bytes=1024**3,max_job_commit_bytes=2*1024**3,environment=d.guard.controlled_environment())
    failure=error.value
    assert failure.owner is bound.owners[-1] and failure.phase=='startup_capture' and failure.expected_sha is None
    assert failure.may_have_published is True and failure.cleanup_unknown and len(str(failure))<448
    assert failure.job_quiet_confirmed is False and '[message unavailable]' in failure.capture_error['message']


@pytest.mark.parametrize('stage',['before_open','after_write','after_rename'])
def test_context_publication_failure_never_constructs_owner(bound,monkeypatch,stage):
    original=d.codec.publish
    def publish(path,raw,hook=None):
        def fault(phase,target):
            if phase==stage:raise OSError('context publication injected')
        return original(path,raw,fault if Path(path).name=='outer_context.json' else hook)
    monkeypatch.setattr(d.codec,'publish',publish)
    with pytest.raises(d.codec.PublicationError):create(bound)
    assert not bound.owners and bound.binding._attempted


def test_release_input_drift_keeps_child_suspended(bound):
    owner=create(bound);path=bound.item.case.inputs.repo/d.SOURCES[0];original=path.read_bytes()
    try:
        path.write_bytes(original+b'\n')
        with pytest.raises(ValueError,match='outer source changed'):owner.release()
        assert not owner.released
    finally:path.write_bytes(original);owner.close()


def test_fresh_binding_cannot_finalize_a_never_started_process(bound):
    with pytest.raises(ValueError,match='never attempted'):bound.binding.finish(dict(record_for(bound.binding),job_quiet_confirmed=False))
    assert not list(bound.binding.parent.iterdir())


def test_replaced_empty_worker_is_rejected_before_writes(bound):
    binding=bound.binding;old=binding.worker.with_name('replaced_worker')
    binding.worker.rename(old);binding.worker.mkdir()
    with pytest.raises(ValueError,match='directories changed'):create(bound)
    assert not list(binding.worker.iterdir()) and not bound.owners


def test_replaced_parent_is_rejected_even_when_ownership_unknown(bound):
    binding=bound.binding;binding._attempted=True
    old=binding.parent.with_name('replaced_parent');binding.parent.rename(old);binding.parent.mkdir()
    with pytest.raises(ValueError,match='parent directory changed'):binding.finish(dict(record_for(binding),job_quiet_confirmed=False))
    assert not list(binding.parent.iterdir())


@pytest.mark.parametrize('entry',['factory','finish'])
def test_bound_operations_stay_in_the_creating_parent_thread(bound,monkeypatch,entry):
    monkeypatch.setattr(d,'get_ident',lambda:bound.binding._creator[1]+1)
    with pytest.raises(ValueError,match='creating parent'):
        if entry=='factory':create(bound)
        else:bound.binding.finish(dict(record_for(bound.binding),job_quiet_confirmed=False))


@pytest.mark.parametrize('which',['source','outer_context.json','outer_startup.json','launcher.json','parent'])
def test_drift_after_parent_publication_retains_expected_sha_and_unknown_status(bound,monkeypatch,which):
    owner=create(bound);owner.release();owner.close();record=record_for(bound.binding)
    original=d.parent.save_observation
    def save(*a,**kw):
        result=original(*a,**kw)
        if which=='source':path=bound.item.case.inputs.repo/d.SOURCES[0]
        elif which=='parent':path=bound.binding.parent/'parent_observation.json'
        else:path=bound.binding.worker/which
        path.write_bytes(path.read_bytes()+b' ')
        return result
    monkeypatch.setattr(d.parent,'save_observation',save)
    with pytest.raises(d.parent.OuterObservationUnresolved) as error:bound.binding.finish(record)
    assert error.value.phase=='outer_final_bookend' and error.value.may_have_published
    assert len(error.value.expected_sha)==64 and (bound.binding.parent/'parent_observation.json').exists()
    assert error.value.scientific_evidence_adopted is False
