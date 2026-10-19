"""Tiny pre-definition protocol seams; real Windows handles, no science claim."""
from hashlib import sha256
import gc
import importlib.util
import json
from pathlib import Path
import sys
from threading import Thread
from types import ModuleType, SimpleNamespace
from weakref import ref

import pytest

import experiments
from experiments import h1_phase_dependency_validation_operation_development_v1 as original


@pytest.fixture
def tiny(tmp_path,monkeypatch,request):
    state=dict(reads=0,read_fail=None,opens=0,open_fail=None,infos=0,info_fail=None,
        closes=0,close_fail=set(),live=set(),closed=[],operations=[],on_open=None,read_caps=[],
        projects=0,on_project=None)
    def module(name):
        item=ModuleType('experiments._phase_fault_'+name+'_'+tmp_path.name)
        path=tmp_path/(name+'.py');path.write_text('# tiny protocol seam\n',encoding='utf-8')
        item.__file__=str(path);item.__spec__=None;item.__loader__=None
        monkeypatch.setitem(sys.modules,item.__name__,item)
        return item
    io=module('io');proof=module('proof');symbolic=module('symbolic');prior=module('group');pred=module('predecessor')
    def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
    def digest(raw):return sha256(raw).hexdigest()
    def identity(path):
        info=path.stat()
        return info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns,info.st_ctime_ns
    def read(path,cap):
        state['reads']+=1
        state['read_caps'].append((path,cap))
        if state['reads']==state['read_fail']:raise OSError('injected read failure')
        before=identity(path);raw=path.read_bytes()
        if len(raw)>cap or identity(path)!=before:raise ValueError('tiny read changed')
        return raw,before
    io.encode=encode;io.digest=digest;io.identity=identity;io.META_CAP=1024
    proof.CAP=2**20;proof.exclusion=SimpleNamespace(INPUT_CAP=2**20)
    proof.MISSING=dict(training_ub='unit only',training_lb='unit only',holdout='unit only')
    proof.CATALOG_PIN='a'*64;proof.SCHEMA='tiny_phase_proof';proof.io=io
    proof._resolver=lambda raw:None;proof._node=lambda *args:None
    proof.Resolver=type('UnitResolver',(),{})
    symbolic.io=io;symbolic.proof=proof;symbolic.PROOF='proof.json';symbolic.BASELINE='baseline.json'
    proof_path=tmp_path/symbolic.PROOF;proof_path.write_bytes(b'{"unit_only":true}')
    symbolic.PROOF_PIN=digest(proof_path.read_bytes())
    variant=getattr(request,'param',None)
    data=tmp_path/'data.txt';files={}
    if variant=='depth':data=tmp_path.joinpath(*(['d']*(65-len(tmp_path.parts))),'data.txt')
    if variant=='separate':data=tmp_path/'static_inputs'/'data.txt'
    data.parent.mkdir(parents=True,exist_ok=True);data.write_bytes(b'unit phase data')
    files[data.relative_to(tmp_path).as_posix()]=digest(data.read_bytes())
    if variant=='handles':
        for index in range(1100):
            item=tmp_path/('h'+str(index))/'a'/'b'/'data.txt'
            item.parent.mkdir(parents=True);item.write_bytes(b'bounded unit inventory')
            files[item.relative_to(tmp_path).as_posix()]=digest(item.read_bytes())
    baseline=encode(dict(files_sha256=files))
    (tmp_path/symbolic.BASELINE).write_bytes(baseline);symbolic.BASELINE_PIN=digest(baseline)
    prior.io=io;prior.ROOT=tmp_path;prior.SCHEMA='tiny_phase_group';prior.PROTOCOL='protocol.yaml'
    (tmp_path/prior.PROTOCOL).write_bytes(b'unit: true\n')
    prior.PROTOCOL_PIN=digest((tmp_path/prior.PROTOCOL).read_bytes());prior.symbolic=symbolic
    prior.FLAGS=dict(formal_result=False)
    def project(raw,family,ordinal,implementation):
        state['projects']+=1
        value=dict(schema=prior.SCHEMA,family=family,ordinal=ordinal,implementation=implementation,
            unit_only=True,siblings=[dict(ordinal=ordinal)])
        if state['on_project'] is not None:state['on_project'](value,state['projects'])
        return value
    prior._project=project
    pred.prior=prior;pred.io=io;pred.MAX_FILES=2048;pred.TOTAL_CAP=2**20;pred.SCHEMA='tiny_phase_verifier'
    pred.FLAGS=dict(formal_result=False);pred.read_stable=read
    pred._scope=lambda:None;pred._views=lambda:{};pred.prepare_group=lambda *args:None
    api=original.handles._kernel_api()
    def create(*args):
        state['opens']+=1
        if state['on_open'] is not None:state['on_open']()
        if state['opens']==state['open_fail']:return original.ctypes.c_void_p(-1).value
        value=api.CreateFileW(*args)
        if value!=original.ctypes.c_void_p(-1).value:state['live'].add(value)
        return value
    def close(handle):
        state['closes']+=1
        if state['closes'] in state['close_fail']:
            state['close_fail'].remove(state['closes']);return False
        result=api.CloseHandle(handle)
        if result:state['live'].remove(handle);state['closed'].append(handle)
        return result
    def info(*args):
        state['infos']+=1
        if state['infos']==state['info_fail']:return False
        return api.GetFileInformationByHandleEx(*args)
    fault_api=SimpleNamespace(CreateFileW=create,CloseHandle=close,GetFileInformationByHandleEx=info)
    monkeypatch.setattr(original.handles,'_kernel_api',lambda:fault_api)
    monkeypatch.setattr(experiments,'h1_phase_dependency_verifier_development_v1',pred)
    path=Path(original.__file__);name='experiments._phase_window_fault_'+tmp_path.name
    fresh=ModuleType(name);fresh.__file__=str(path);fresh.__package__='experiments'
    fresh.__spec__=importlib.util.spec_from_file_location(name,path);fresh.__loader__=fresh.__spec__.loader
    monkeypatch.setitem(sys.modules,name,fresh)
    exec(compile(path.read_bytes(),str(path),'exec'),vars(fresh))
    def operation(plan=(('training_ub',0),)):
        value=fresh.PhaseDependencyValidationOperation(plan=plan,diagnostic_only=True)
        state['operations'].append(value);return value
    try:yield SimpleNamespace(m=fresh,state=state,operation=operation,root=tmp_path,data=data,pred=pred)
    finally:
        for value in state['operations']:
            for _ in range(3):
                try:value.retry_cleanup()
                except BaseException:pass
                if not state['live']:break
        fresh._RETRY_ABANDONED()
        assert not state['live'],'tiny fixture leaked actual Windows handles'


def test_tiny_success_counts_actual_reads_and_exposes_no_legacy_fresh_payload(tiny):
    operation=tiny.operation()
    with operation:
        report=json.loads(operation.prepare_group('training_ub',0))
        assert report['fresh_at_return_only'] is False
        assert report['canonical_equivalence_verified'] is False
        assert 'canonical_predecessor_payload' not in report
        assert 'fresh_at_return_only' not in report['scientific_projection']
    receipt=operation.receipt()
    assert receipt['lifecycle_complete'] and not receipt['canonical_equivalence_verified']
    assert receipt['physical_read_attempts']==tiny.state['reads']==receipt['physical_reads_succeeded']
    assert receipt['inventory_rounds_completed']==3
    assert receipt['held_inventory_projections']==1
    assert not tiny.state['live']


@pytest.mark.parametrize('index',[1,3,8])
def test_partial_handle_acquisition_closes_every_actual_handle(tiny,index):
    tiny.state['open_fail']=index;operation=tiny.operation()
    with pytest.raises(OSError):operation.__enter__()
    receipt=operation.receipt()
    assert receipt['closed'] and receipt['all_handles_closed'] and not receipt['lifecycle_complete']
    assert receipt['original_guard_released'] and receipt['first_failure'] is not None
    assert not tiny.state['live']


@pytest.mark.parametrize('index',[1,5,17])
def test_handle_identity_failure_after_open_closes_acquired_handle(tiny,index):
    tiny.state['info_fail']=index;operation=tiny.operation()
    with pytest.raises(OSError):operation.__enter__()
    assert operation.receipt()['all_handles_closed'] and not tiny.state['live']


def test_malicious_exception_repr_cannot_replace_primary_or_skip_cleanup(tiny):
    class BadRepresentation(BaseException):
        def __repr__(self):raise RuntimeError('repr must not run')
    error=BadRepresentation('primary');operation=tiny.operation()
    with pytest.raises(BadRepresentation) as caught:
        with operation:
            operation.prepare_group('training_ub',0)
            raise error
    assert caught.value is error
    receipt=operation.receipt()
    assert receipt['all_handles_closed'] and receipt['original_guard_released']
    assert receipt['first_failure'] is not None and not receipt['lifecycle_complete']


def test_exit_read_failure_is_sticky_and_still_releases_resources(tiny):
    operation=tiny.operation();operation.__enter__();operation.prepare_group('training_ub',0)
    tiny.state['read_fail']=tiny.state['reads']+1
    with pytest.raises(OSError,match='injected read'):operation.close()
    receipt=operation.receipt()
    assert not receipt['exit_physical_validation_completed'] and not receipt['lifecycle_complete']
    assert receipt['physical_read_attempts']==receipt['physical_reads_succeeded']+1
    assert receipt['all_handles_closed'] and not tiny.state['live']


def test_failed_close_retains_resources_and_retries_only_pending_handles(tiny):
    operation=tiny.operation();operation.__enter__();operation.prepare_group('training_ub',0)
    tiny.state['close_fail']={1,3}
    with pytest.raises(OSError,match='CloseHandle'):operation.close()
    first=operation.receipt()
    assert first['state']=='cleanup_pending' and first['pending_handles']==2
    assert not first['immutable_bytes_cleared'] and not first['original_guard_released']
    closes=tiny.state['closes'];operation.retry_cleanup();last=operation.receipt()
    assert tiny.state['closes']==closes+2
    assert last['closed'] and last['all_handles_closed'] and last['immutable_bytes_cleared']
    assert last['original_guard_released'] and not last['lifecycle_complete']
    assert last['first_failure']==first['first_failure']
    assert len(tiny.state['closed'])==len(set(tiny.state['closed']))


@pytest.mark.parametrize('fail_first_close',[False,True])
def test_garbage_collection_closes_or_retains_actual_handles_for_bounded_retry(tiny,fail_first_close):
    operation=tiny.operation();operation.__enter__();operation.prepare_group('training_ub',0)
    count=len(tiny.state['live']);reference=ref(operation)
    assert count>0 and tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==1
    if fail_first_close:tiny.state['close_fail']={1}
    tiny.state['operations'].clear();del operation;gc.collect()
    assert reference() is None
    diagnostic=tiny.m._CLEANUP_DIAGNOSTICS()
    assert diagnostic['active_operations']==0 and diagnostic['abandoned_operations']==1
    assert diagnostic['abandoned_pending_operations']==int(fail_first_close)
    assert len(tiny.state['live'])==int(fail_first_close)
    closes=tiny.state['closes'];tiny.m._RETRY_ABANDONED()
    assert tiny.state['closes']==closes+int(fail_first_close)
    assert not tiny.state['live'] and tiny.m._CLEANUP_DIAGNOSTICS()['abandoned_pending_operations']==0
    assert len(tiny.state['closed'])==count==len(set(tiny.state['closed']))
    # GC/retry changes no runtime bindings and cannot manufacture a clean owner receipt.
    with tiny.operation() as following:following.prepare_group('training_ub',0)
    assert following.receipt()['lifecycle_complete']


def test_failed_explicit_close_does_not_retain_owner_through_exception_tracebacks(tiny):
    operation=tiny.operation();operation.__enter__();operation.prepare_group('training_ub',0)
    tiny.state['close_fail']={1}
    try:operation.close()
    except OSError:pass
    reference=ref(operation);tiny.state['operations'].clear();del operation;gc.collect()
    assert reference() is None and not tiny.state['live']
    assert tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0


def test_atexit_cleanup_callback_retries_orphans_without_owner_or_runtime(tiny,monkeypatch):
    operation=tiny.operation();operation.__enter__();operation.prepare_group('training_ub',0)
    tiny.state['close_fail']={1};tiny.state['operations'].clear();del operation;gc.collect()
    assert len(tiny.state['live'])==1
    with monkeypatch.context() as patch:
        patch.setattr(tiny.m,'_RUNTIME',lambda:(_ for _ in ()).throw(ValueError('retired')))
        tiny.m._SHUTDOWN_CLEANUP()
    assert not tiny.state['live']
    assert tiny.m._CLEANUP_DIAGNOSTICS()['abandoned_pending_operations']==0


@pytest.mark.parametrize('dependency',['predecessor','io','group','symbolic','proof'])
def test_individual_source_byte_caps_are_preserved(tiny,dependency):
    module={'predecessor':tiny.pred,'io':tiny.pred.io,'group':tiny.pred.prior,
        'symbolic':tiny.pred.prior.symbolic,'proof':tiny.pred.prior.symbolic.proof}[dependency]
    cap=tiny.pred.io.META_CAP*128 if dependency=='predecessor' else tiny.pred.prior.symbolic.proof.exclusion.INPUT_CAP
    Path(module.__file__).write_bytes(b'#'+b' ' * cap)
    operation=tiny.operation()
    with pytest.raises(ValueError,match='tiny read changed'):operation.__enter__()
    assert operation.receipt()['all_handles_closed'] and not tiny.state['live']
    assert (Path(module.__file__),cap) in tiny.state['read_caps']


def test_each_file_keeps_its_strictest_cap_through_physical_exit(tiny):
    with tiny.operation() as operation:operation.prepare_group('training_ub',0)
    own=Path(tiny.pred.__file__);cap=tiny.pred.io.META_CAP*128
    assert [limit for path,limit in tiny.state['read_caps'] if path==own]==[cap]*3
    assert tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0


@pytest.mark.parametrize('name',['LPCWSTR','DWORD','LPVOID','HANDLE','BOOL'])
def test_wintypes_mutation_before_construction_rejected_before_any_handle(tiny,monkeypatch,name):
    monkeypatch.setattr(tiny.m.wintypes,name,tiny.m.ctypes.c_byte)
    with pytest.raises(ValueError,match='definition-time'):
        tiny.m.PhaseDependencyValidationOperation(plan=(('training_ub',0),),diagnostic_only=True)
    assert tiny.state['opens']==0 and not tiny.state['live']


@pytest.mark.parametrize('field',['restype','argtypes'])
def test_actual_c_signature_mismatch_is_rejected_before_cloning_or_open(tiny,field):
    api=original.handles.ctypes.WinDLL('kernel32',use_last_error=True)
    for name,result_type,argument_types in tiny.m._ABI_SIGNATURES:
        function=getattr(api,name);function.restype=result_type;function.argtypes=argument_types
    function=api.CreateFileW
    if field=='restype':function.restype=tiny.m.ctypes.c_byte
    else:function.argtypes=(tiny.m.ctypes.c_byte,)
    with pytest.raises(ValueError,match='captured Windows ABI'):tiny.m._private_api(api)
    assert tiny.state['opens']==0 and not tiny.state['live']


@pytest.mark.parametrize('tiny',['depth','handles'],indirect=True)
def test_path_depth_and_aggregate_handle_bound_reject_before_any_open(tiny):
    operation=tiny.operation()
    with pytest.raises(ValueError,match='bounded phase file/ancestor handle'):operation.__enter__()
    receipt=operation.receipt()
    assert receipt['closed'] and receipt['all_handles_closed'] and not receipt['lifecycle_complete']
    assert receipt['original_guard_released'] and tiny.state['opens']==0 and not tiny.state['live']
    assert tiny.m._CLEANUP_DIAGNOSTICS()['active_operations']==0


@pytest.mark.parametrize('selection',[('training_lb',0),('training_ub',1),('training_ub',True)])
def test_wrong_or_adaptive_request_poison_cannot_be_continued(tiny,selection):
    operation=tiny.operation()
    with pytest.raises(ValueError,match='exact next'):
        with operation:operation.prepare_group(*selection)
    assert not operation.receipt()['lifecycle_complete']
    with pytest.raises(ValueError,match='lifetime'):operation.prepare_group('training_ub',0)


def test_incomplete_plan_and_reentry_are_rejected_without_resource_leak(tiny):
    first=tiny.operation((('training_ub',0),('training_lb',0)))
    with pytest.raises(ValueError,match='fixed phase request plan'):
        with first:first.prepare_group('training_ub',0)
    second=tiny.operation()
    with pytest.raises(ValueError,match='nonreentrant'):
        with second:second.__enter__()
    assert not first.receipt()['lifecycle_complete'] and not second.receipt()['lifecycle_complete']


def test_foreign_thread_cannot_prepare_enter_close_or_poison_owner(tiny):
    operation=tiny.operation();failures=[]
    with operation:
        def compete():
            for function,args in ((operation.__enter__,()),(operation.prepare_group,('training_ub',0)),
                    (operation.close,())):
                try:function(*args)
                except ValueError as error:failures.append(str(error))
        thread=Thread(target=compete);thread.start();thread.join(timeout=5)
        assert not thread.is_alive() and len(failures)==3
        assert operation.receipt()['first_failure'] is None
        operation.prepare_group('training_ub',0)
    assert operation.receipt()['lifecycle_complete']


@pytest.mark.parametrize('name',['_calls','_state','_failure','_opened','_views','_guard','_creator','close'])
def test_writable_working_aliases_cannot_forge_lifecycle_evidence(tiny,name):
    operation=tiny.operation()
    with operation:
        with pytest.raises(AttributeError):setattr(operation,name,None)
        operation.prepare_group('training_ub',0)
    assert operation.receipt()['lifecycle_complete']


def test_declared_distinct_requests_and_actual_write_delete_denial(tiny):
    plan=(('training_ub',0),('training_lb',1),('holdout',2));operation=tiny.operation(plan)
    before=tiny.data.read_bytes()
    with operation:
        with pytest.raises(PermissionError):tiny.data.write_bytes(b'cannot replace held bytes')
        with pytest.raises(PermissionError):tiny.data.unlink()
        for family,ordinal in plan:
            report=json.loads(operation.prepare_group(family,ordinal))
            assert report['scientific_projection']['predecessor_group']['family']==family
            assert report['scientific_projection']['predecessor_group']['ordinal']==ordinal
    assert tiny.data.read_bytes()==before and operation.receipt()['lifecycle_complete']


def test_same_bytes_new_file_identity_before_acquisition_is_rejected(tiny):
    original_raw=tiny.data.read_bytes()
    def replace():
        tiny.state['on_open']=None
        tiny.data.rename(tiny.data.with_suffix('.previous'))
        tiny.data.write_bytes(original_raw)
    tiny.state['on_open']=replace;operation=tiny.operation()
    with pytest.raises(ValueError,match='inventory changed'):operation.__enter__()
    assert operation.receipt()['all_handles_closed'] and not tiny.state['live']


@pytest.mark.parametrize('target',['projection','identity','read','scope','group','encode','flags','module'])
def test_runtime_alias_or_control_replacement_never_yields_clean_data(tiny,monkeypatch,target):
    operation=tiny.operation();operation.__enter__();m=tiny.m
    with monkeypatch.context() as patch:
        if target=='projection':patch.setattr(m,'_projection',lambda *args:{})
        elif target=='identity':patch.setattr(m,'implementation_identity',lambda:'a'*64)
        elif target=='read':patch.setattr(tiny.pred,'read_stable',lambda *args:(b'',()))
        elif target=='scope':patch.setattr(tiny.pred,'_scope',lambda:None)
        elif target=='group':patch.setattr(tiny.pred.prior,'_project',lambda *args:{})
        elif target=='encode':patch.setattr(tiny.pred.io,'encode',lambda value:b'{}')
        elif target=='flags':patch.setitem(m.FLAGS,'formal_result',True)
        else:patch.setitem(sys.modules,m.__name__,ModuleType(m.__name__))
        with pytest.raises(ValueError,match='definition-time'):operation.prepare_group('training_ub',0)
    with pytest.raises(ValueError):operation.close()
    assert not tiny.state['live']
    # Restoring a changed route does not resurrect a retired runtime seal.
    with pytest.raises(ValueError,match='definition-time'):operation.receipt()
