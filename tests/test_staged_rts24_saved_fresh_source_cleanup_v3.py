"""Exact Core47 orchestration/native-close code with explicit synthetic effect domains."""
import ast
import builtins
from hashlib import sha256
import os
from pathlib import Path
import sys
from threading import get_ident
from types import FunctionType, SimpleNamespace, ModuleType
import unittest

ROOT=Path(__file__).absolute().parents[1]
SOURCE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v47.py'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v44.py'
NS=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v4.py'
BS=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'


def selected_source(path,name):
    raw=path.read_text(encoding='utf-8');tree=ast.parse(raw)
    return ast.get_source_segment(raw,next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name==name))


NS_FIXTURE=(selected_source(NS,'verify_helper_bindings')+'''
class LiveEntryNamespace:
    pass
def prepare_runtime_namespace(namespace,runtime):
    _STATE['target']=runtime
    return ('synthetic_namespace',id(namespace.module))
def verify_runtime_namespace(namespace,runtime):
    return namespace
def close_runtime_namespace(namespace,runtime):
    _STATE['events'].append('namespace')
    if _STATE.get('reentry'):_STATE['reentry']()
    if _STATE.get('namespace_error'):raise _STATE['namespace_error']
    del namespace._modules[namespace._aliases[0]]
''').encode()
BS_FIXTURE=(selected_source(BS,'verify_bootstrap_import_bindings')+'''
class BootstrapImportBoundary:
    __slots__=('_state','_creator','_profile_raw')
    def _entry(self):return self
    def close(self,primary=None):
        _STATE['events'].append('boundary')
        if _STATE.get('boundary_error'):raise _STATE['boundary_error']
        self._state=('CLOSED',False,*self._state[2:6],True,self._state[7])
    def phase(self):return self._state[0]
    def profile_raw(self):return self._profile_raw
    def claim_pending(self,runtime):
        if _STATE.get('claim_error'):raise _STATE['claim_error']
        return self
''').encode()


def contract():
    def function(path,cls,name):
        tree=ast.parse(path.read_bytes());node=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name==cls)
        return ast.dump(next(n for n in node.body if isinstance(n,ast.FunctionDef) and n.name==name),include_attributes=False)
    assert function(SOURCE,'_Resource','close')==function(OLD,'_Resource','close')
    pins={str(path):dict(bytes=len(raw:=path.read_bytes()),sha256=sha256(raw).hexdigest()) for path in (SOURCE,OLD,NS,BS)}
    return dict(source_pins=pins,native_close_ast_unchanged=True,
        synthetic_namespace_pin=sha256(NS_FIXTURE).hexdigest(),synthetic_boundary_pin=sha256(BS_FIXTURE).hexdigest(),
        exact_code=['_Resource.__init__','_Resource.open','_Resource.close','LocalPreEntryInputs.transfer_runtime',
                    'LocalRuntimeInputs.prepare_boundary','LocalRuntimeInputs.own_pending_boundary',
                    'LocalRuntimeInputs.close','capture_runtime_cleanup','run_runtime_cleanup'],
        synthetic_effects=['kernel functions','resource snapshot','entry/bookend','namespace lifecycle','B_S lifecycle'],
        exact_verifiers=['verify_helper_bindings','verify_bootstrap_import_bindings'],
        source49_modules_executed=0,P1_reads=0,native_handle_calls=0,fixture_child_processes=0,
        transitive_check_use_equivalence=False,actual_entry_authenticated=False,run_authority=False,actual_F=False)


def load_core():
    raw=SOURCE.read_bytes().replace(b'\r\n',b'\n');prefix,tail=raw.split(b'\nimport builtins\n',1)
    payload=b'import builtins\n'+tail
    core=ModuleType('_source_cleanup_core');core.__file__=str(SOURCE)
    exec(compile(prefix,'<test_nonmain_prefix>','exec',dont_inherit=True,optimize=0),vars(core))
    exec(compile(payload,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0),vars(core))
    core._TEST_PAYLOAD=payload;return core


def spec(fn):return (FunctionType,fn.__code__,fn.__globals__,fn.__defaults__)


def bindings(context,classes=(),bs=False):
    rows=[]
    for space in (context,*classes):
        mapping=space if type(space) is dict else vars(space)
        for name,value in mapping.items():
            metadata=None
            if type(value) is FunctionType:
                kw=value.__kwdefaults__
                metadata=(value.__code__,value.__defaults__,None if kw is None else tuple(sorted(kw.items())) if bs else kw,value.__closure__)
            rows.append((space,name,value,metadata))
        rows.append((mapping if not bs else space,'__expected_keyset__' if bs else 'keyset',tuple(sorted(mapping)),'keyset' if not bs else None))
    return tuple(rows)


class Fixture:
    def __init__(self,transfer=True,failed=(),uncertain=(),audit_error=None):
        self.core=core=load_core();self.state=state=dict(events=[],failed=failed,uncertain=uncertain,audit_error=audit_error)
        self.modules={};self.leaf_calls=[]
        core.sys=SimpleNamespace(**vars(sys));core.sys.modules=self.modules
        def audit(event,*args):
            if event.endswith('transfer_prepared'):state['target']=args[-1]
            if event.endswith(state.get('audit_error') or 'never'):
                raise RuntimeError('injected '+event)
        core.sys.audit=audit
        core._EARLY=dict(active=True,sources_allowed=False,blocked=[])
        class Leaf:
            def __init__(self,name,callback):self.name=name;self.callback=callback;self.argtypes=();self.restype=int
            def __call__(self,*args):
                self_outer.leaf_calls.append((self.name,args));return self.callback(*args)
        self_outer=self
        def close(handle):
            if state.get('close_error',{}).get(handle):raise state['close_error'][handle]
            if handle in state['failed']:core.C.set_last_error(5);return 0
            return 1
        def witness(handle,flags):
            core.C.set_last_error(5 if handle in state['uncertain'] else 6);return 0
        callbacks=dict(GetCurrentProcessId=lambda:os.getpid(),GetCurrentThreadId=lambda:7,
            OpenProcess=lambda *args:101,OpenThread=lambda *args:102,CloseHandle=close,GetHandleInformation=witness)
        held={name:(Leaf(name,fn),(),int) for name,fn in callbacks.items()}
        core.kernel_api=lambda:(object(),held)
        core._Resource.snapshot=lambda resource:{'synthetic_snapshot':True}
        def entry(owner):return owner
        def bookend(owner,_state=state):
            if _state.get('bookend_error'):raise _state['bookend_error']
            return {}
        core._LocalInputs.entry=entry;core.LocalRuntimeInputs.entry=entry;core.LocalRuntimeInputs.source_bookend=bookend
        def reader(path,pin,*args,**kwargs):
            return {'namespace':NS_FIXTURE,'boundary':BS_FIXTURE,'policy':b'policy'}[str(path)]
        core.NS_FIXTURE=NS_FIXTURE;core.BS_FIXTURE=BS_FIXTURE
        core.read_file=FunctionType(reader.__code__,vars(core),'synthetic_read_file',reader.__defaults__)
        core.check_plan=lambda raw:dict(namespace_helper=dict(path='namespace',pin={}),
            import_helper=dict(path='boundary',pin={}),import_policy=dict(path='policy',pin={}))
        self.source=source=object.__new__(core.LocalPreEntryInputs)
        guard=dict(active=True,self_live=False,events=[],faults=[],runtime_attempted=False)
        self.resource=resource=core._Resource(source,guard)
        source._resource=resource;source._ownership=(resource,resource.creator,resource.cleanup_code,FunctionType,BaseException,resource._native_roots)
        self.before_open=(resource.phase,resource._native_roots.opened,tuple(resource.pending))
        native_live=resource.open();source._ownership=(*source._ownership,native_live)
        source._cleanup_seal=(id(resource),id(source._ownership),id(source._ownership[2]),id(source._ownership[3]),id(source._ownership[4]),resource.creator)
        source._sources=();source._raw=b'{}';source._control=();source._runtime_target_type=core.LocalRuntimeInputs
        source._phase='LIVE';source._failure=None;source._successor=None;source._entry_spec=spec(entry)
        self.ns_context=dict(__builtins__=vars(builtins),__name__='_synthetic_namespace',_STATE=state)
        exec(compile(NS_FIXTURE,'namespace','exec',dont_inherit=True,optimize=0),self.ns_context)
        self.namespace=namespace=self.ns_context['LiveEntryNamespace']()
        namespace._inputs=source;namespace._phase='LIVE';namespace._runtime_peer=None;namespace._creator=(os.getpid(),get_ident())
        namespace._modules=self.modules;namespace.module=object();namespace._aliases=('synthetic_entry',)
        namespace._bindings=bindings(self.ns_context,(type(namespace),));self.modules[namespace._aliases[0]]=namespace.module
        self.namespace_specs=tuple(spec(self.ns_context[name]) for name in ('prepare_runtime_namespace','verify_runtime_namespace','close_runtime_namespace'))
        source._bindings=core.capture_bindings()
        self.close_spec=spec(core.LocalRuntimeInputs.close)
        self.owner=None
        if transfer:self.transfer()

    def transfer(self):
        self.owner=self.source.transfer_runtime(self.namespace,self.namespace_specs);return self.owner
    @property
    def packet(self):return self.owner._runtime_cleanup
    def close(self,primary=None):return self.close_spec[0](self.close_spec[1],self.close_spec[2],'held_test_close',self.close_spec[3])(self.owner,primary)
    def native_calls(self):return [(name,args[0]) for name,args in self.leaf_calls if name in ('CloseHandle','GetHandleInformation')]
    def prepare(self,bind=True):
        context=dict(__builtins__=vars(builtins),__name__='_synthetic_boundary',_STATE=self.state,_READ_FILE=self.core.read_file)
        exec(compile(BS_FIXTURE,'boundary','exec',dont_inherit=True,optimize=0),context);self.bs_context=context
        cls=context['BootstrapImportBoundary'];proof=bindings(context,(cls,),bs=True)
        self.owner.prepare_boundary(*(spec(vars(cls)[name]) for name in ('_entry','close','phase','profile_raw','claim_pending')),proof)
        self.boundary=boundary=cls();boundary._state=('INSTALLING',True,0,0,0,0,False,'')
        boundary._creator=self.owner._creator[:2];boundary._profile_raw=b'policy'
        if bind:self.owner.own_pending_boundary(boundary)
        return boundary


class SourceCleanupTests(unittest.TestCase):
    def failure(self,f,primary=None):
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as caught:f.close(primary)
        failure=caught.exception;before=list(f.leaf_calls)
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as repeated:f.close()
        self.assertIs(repeated.exception,failure);self.assertEqual(f.leaf_calls,before)
        self.assertEqual(f.packet.execution_state,'UNRESOLVED');return failure

    def test_01_compiled_source_oracle(self):
        core=load_core();core.check_compiled_namespace(core._TEST_PAYLOAD);self.assertTrue(contract()['native_close_ast_unchanged'])

    def test_02_construction_and_live_handle_truth(self):
        f=Fixture();self.assertEqual(f.before_open,('OPENING',(None,None),(None,None)))
        self.assertIs(f.source._ownership[6],f.resource._native_live)
        self.assertEqual(f.resource._native_live[1],((101,'live'),(102,'live')));f.close()

    def test_03_success_shared_ledgers_and_repeat(self):
        f=Fixture();pending=f.resource.pending;calls=f.resource.close_calls;f.close();f.close()
        self.assertIs(f.resource.pending,pending);self.assertIs(f.resource.close_calls,calls)
        self.assertEqual((pending,calls,f.resource.phase,f.owner._phase),([None,None],[1,1],'CLOSED','CLOSED'))
        self.assertEqual(f.native_calls(),[('CloseHandle',102),('GetHandleInformation',102),('CloseHandle',101),('GetHandleInformation',101)])
        self.assertFalse(f.resource.guard['active']);self.assertFalse(f.core._EARLY['active']);self.assertEqual(f.modules,{})
        for field in ('self_live','sources_allowed','held'):
            f=Fixture();f.close()
            if field=='self_live':f.resource.guard[field]=True
            elif field=='sources_allowed':f.core._EARLY[field]=True
            else:f.resource.held['CloseHandle']=(lambda *a:1,(),int)
            before=f.native_calls();self.failure(f);self.assertEqual(f.native_calls(),before)

    def test_04_precommit_failure_keeps_original_owner(self):
        f=Fixture(False,audit_error='transfer_prepared')
        with self.assertRaises(RuntimeError):f.transfer()
        f.owner=f.state['target'];self.assertIs(f.resource.owner,f.source)
        with self.assertRaisesRegex(ValueError,'not committed'):f.close()
        self.assertEqual(f.native_calls(),[]);f.source.close();self.assertEqual(f.resource.close_calls,[1,1])

    def test_05_postcommit_failure_keeps_active_cleanup(self):
        f=Fixture(False,audit_error='owner_committed')
        with self.assertRaises(f.core.LocalRuntimeUnresolved) as caught:f.transfer()
        f.owner=f.state['target'];self.assertIs(f.resource.owner,f.owner)
        failure=self.failure(f);self.assertIs(failure.primary,caught.exception);self.assertEqual(f.resource.close_calls,[1,1])

    def test_06_prepared_without_boundary_is_safe(self):
        f=Fixture();f.prepare(False);self.assertEqual(f.packet.binding_stage,'BOUNDARY_SPEC')
        f.close();self.assertNotIn('boundary',f.state['events'])

    def test_07_claim_failure_retains_bound_object(self):
        f=Fixture();f.prepare(False);primary=RuntimeError('claim failed');f.state['claim_error']=primary
        with self.assertRaises(RuntimeError):f.owner.own_pending_boundary(f.boundary)
        self.assertIs(f.packet.boundary,f.boundary);self.assertIsNone(f.owner._boundary)
        self.assertIs(self.failure(f,primary).primary,primary);self.assertFalse(f.boundary._state[1]);self.assertEqual(f.resource.close_calls,[1,1])

    def test_08_boundary_proof_drift_retires_hook(self):
        f=Fixture();f.prepare();f.bs_context['_READ_FILE']=lambda *a:None
        failure=self.failure(f);self.assertNotIn('boundary',f.state['events'])
        self.assertEqual(f.boundary._state[:2],('FAULTED',False));self.assertTrue(f.boundary._state[6])
        self.assertIn('import_boundary',[tag for tag,_ in failure.secondary]);self.assertEqual(f.resource.close_calls,[1,1])

    def test_09_boundary_baseexception_is_independent(self):
        f=Fixture();f.prepare();error=KeyboardInterrupt('boundary');f.state['boundary_error']=error
        failure=self.failure(f);self.assertIs(dict(failure.secondary)['import_boundary'],error)
        self.assertFalse(f.boundary._state[1]);self.assertEqual(f.resource.close_calls,[1,1])

    def test_10_foreign_boundary_cannot_execute(self):
        f=Fixture();f.prepare();original=f.boundary;object.__setattr__(f.packet,'boundary',object())
        self.failure(f);self.assertFalse(original._state[1]);self.assertEqual(f.resource.close_calls,[1,1]);self.assertEqual(f.state['events'],[])

    def test_11_malformed_boundary_state_is_not_rewritten(self):
        for state in (('malformed',),('CLOSED',True,0,0,0,0,True,''),('ACTIVE',True,-1,0,0,0,False,'')):
            f=Fixture();f.prepare();f.boundary._state=state
            failure=self.failure(f);self.assertIs(f.boundary._state,state)
            self.assertIn('boundary_retirement',dict(failure.secondary));self.assertEqual(f.resource.close_calls,[1,1])
        for phase in ('ACTIVE','CLOSED'):
            f=Fixture();f.prepare();f.boundary._state=(phase,phase=='ACTIVE',1,1,0,0,phase=='CLOSED','');f.close()

    def test_12_namespace_proof_drift_exact_alias_only(self):
        f=Fixture();f.ns_context['close_runtime_namespace']=lambda *a:None
        self.failure(f);self.assertNotIn('namespace',f.state['events']);self.assertEqual(f.modules,{})
        self.assertEqual(f.resource.close_calls,[1,1])

    def test_13_foreign_alias_including_none_is_preserved(self):
        for value in (None,object()):
            f=Fixture();f.state['namespace_error']=RuntimeError('namespace');f.modules['synthetic_entry']=value
            failure=self.failure(f);self.assertIs(f.modules['synthetic_entry'],value)
            self.assertIn('namespace_retirement',dict(failure.secondary));self.assertEqual(f.resource.close_calls,[1,1])

    def test_14_foreign_modules_container_is_preserved(self):
        f=Fixture();f.core.sys.modules={};f.state['namespace_error']=RuntimeError('namespace')
        self.failure(f);self.assertIs(f.modules['synthetic_entry'],f.namespace.module);self.assertEqual(f.resource.close_calls,[1,1])

    def test_15_native_instance_roots_refuse_before_leaf(self):
        for name in ('api','held','pending','close_calls','guard','_early','cleanup_code','_close_impl','_C','_W','_tuple',
                     '_getpid','_get_ident','_reject','_byref','_set_error','_get_error','_DWORD','_WinError','_any','_unresolved'):
            with self.subTest(name=name):
                f=Fixture();setattr(f.resource,name,object());self.failure(f);self.assertEqual(f.native_calls(),[])

    def test_16_native_api_rows_refuse_before_leaf(self):
        for name in ('CloseHandle','GetHandleInformation','extra'):
            f=Fixture();f.resource.held[name]=(lambda *a:1,(),int)
            self.failure(f);self.assertEqual(f.native_calls(),[])

    def test_17_coordinated_pending_and_opened_cannot_reauthenticate(self):
        f=Fixture(False);f.resource.pending[:]=[(901,'live'),(902,'live')]
        object.__setattr__(f.resource._native_roots,'opened',(901,902))
        with self.assertRaisesRegex(ValueError,'completed-open'):f.transfer()
        self.assertIs(f.resource.owner,f.source);self.assertEqual(f.native_calls(),[])

    def test_18_original_live_seal_is_required(self):
        f=Fixture();f.resource._native_live=(f.resource._native_roots,((101,'live'),(102,'live')),f.resource.creator)
        self.failure(f);self.assertEqual(f.native_calls(),[])

    def test_19_each_close_failure_preserves_pending(self):
        for index,handle in enumerate((101,102)):
            f=Fixture(failed=(handle,));failure=self.failure(f)
            self.assertEqual(f.resource.pending[index],(handle,'live'));self.assertIsNone(f.resource.pending[1-index])
            self.assertEqual(f.resource.close_calls,[1,1]);self.assertEqual(f.resource.phase,'UNRESOLVED')
            self.assertEqual(dict(failure.secondary)['native'].owner,f.owner)
        f=Fixture();error=KeyboardInterrupt('native leaf');f.state['close_error']={102:error}
        failure=self.failure(f);self.assertIs(dict(failure.secondary)['native'].secondary[0][1],error)
        self.assertEqual(f.resource.pending, [None,(102,'live')]);self.assertEqual(f.resource.close_calls,[1,1])

    def test_20_each_witness_failure_never_retries_numeric_handle(self):
        for index,handle in enumerate((101,102)):
            f=Fixture(uncertain=(handle,));self.failure(f)
            self.assertEqual(f.resource.pending[index],(handle,'close_issued'));self.assertEqual(f.resource.close_calls,[1,1])

    def test_21_primary_and_all_secondary_order(self):
        f=Fixture(failed=(101,));f.prepare();primary=RuntimeError('primary')
        f.state['boundary_error']=RuntimeError('boundary');f.state['namespace_error']=RuntimeError('namespace')
        failure=self.failure(f,primary);self.assertIs(failure.primary,primary)
        self.assertEqual([tag for tag,_ in failure.secondary],['import_boundary','boundary_emergency_retirement','namespace','native','pending_handles'])
        self.assertFalse(f.resource.guard['active']);self.assertFalse(f.core._EARLY['active'])

    def test_22_swallowed_reentry_is_sticky(self):
        f=Fixture()
        def reenter():
            try:f.close()
            except ValueError:pass
        f.state['reentry']=reenter;failure=self.failure(f)
        self.assertIs(failure.primary,f.packet.reentry);self.assertEqual(f.resource.close_calls,[1,1])

    def test_23_packet_drift_preserves_independent_native_cleanup(self):
        for name in ('namespace_spec','namespace_proof','core_check','bookend_spec','modules','module','alias','roots','ownership','binding_stage','owner_slots','resource'):
            f=Fixture();object.__setattr__(f.packet,name,('forged',) if name.endswith('spec') else object())
            self.failure(f);self.assertEqual(f.resource.close_calls,[1,1]);self.assertEqual(f.state['events'],[])
        f=Fixture();object.__delattr__(f.packet,'owner_slots');self.failure(f);self.assertEqual(f.resource.close_calls,[1,1])
        f=Fixture();object.__setattr__(f.owner,'_runtime_cleanup_seal',object())
        self.failure(f);self.assertEqual(f.resource.close_calls,[1,1])

    def test_24_incomplete_running_state_never_retries(self):
        f=Fixture();f.packet.ledger[0]='RUNNING';object.__setattr__(f.packet,'execution_state','RUNNING')
        self.failure(f);self.assertEqual(f.native_calls(),[])
        for name,value in (('execution_state','CLOSED'),('execution_state','UNRESOLVED'),('failure',RuntimeError('foreign')),
                           ('native_terminal',True),('domain_errors',(('forged',None),))):
            f=Fixture();object.__setattr__(f.packet,name,value)
            self.failure(f);self.assertEqual(f.resource.close_calls,[1,1])

    def test_25_held_runtime_close_ignores_replaced_class_method(self):
        f=Fixture();called=[];f.core.LocalRuntimeInputs.close=lambda *args:called.append(True)
        self.failure(f);self.assertEqual(called,[]);self.assertEqual(f.resource.close_calls,[1,1])

    def test_26_native_failure_constructor_drift_refuses(self):
        f=Fixture();called=[];f.core.LocalPreEntryUnresolved.__init__=lambda *args:called.append(True)
        self.failure(f);self.assertEqual(called,[]);self.assertEqual(f.native_calls(),[])

    def test_27_held_fields_cannot_be_deleted(self):
        f=Fixture()
        for value,name in ((f.packet,'owner'),(f.resource._native_roots,'rows')):
            with self.assertRaises(AttributeError):delattr(value,name)
        f.close()

    def test_28_control_failure_still_attempts_native(self):
        f=Fixture();object.__delattr__(f.owner,'_failure');failure=self.failure(f)
        self.assertIn('cleanup_control',dict(failure.secondary));self.assertEqual(f.resource.close_calls,[1,1])

    def test_29_duplicate_boundary_bind_is_rejected(self):
        f=Fixture();f.prepare()
        with self.assertRaises(ValueError):f.owner.own_pending_boundary(f.boundary)
        f.close();self.assertEqual(f.state['events'].count('boundary'),1)

    def test_30_core_function_metadata_drift_cannot_execute(self):
        f=Fixture();called=[]
        f.core.LocalRuntimeInputs.source_bookend=lambda *a:called.append(True)
        self.failure(f);self.assertEqual(called,[]);self.assertEqual(f.resource.close_calls,[1,1])

    def test_31_failure_publication_bypasses_constructor(self):
        f=Fixture();called=[];primary=RuntimeError('primary')
        f.core.LocalRuntimeUnresolved.__init__=lambda *a:called.append(True)
        failure=self.failure(f,primary);self.assertIs(failure.primary,primary);self.assertEqual(called,[])
        self.assertEqual(f.resource.close_calls,[1,1])

    def test_32_native_function_metadata_drift_refuses(self):
        f=Fixture();f.core._Resource.close.__defaults__=(RuntimeError('changed'),)
        self.failure(f);self.assertEqual(f.native_calls(),[])


if __name__=='__main__':unittest.main()
