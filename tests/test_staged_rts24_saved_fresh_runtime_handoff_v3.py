"""Logical owner/namespace regressions; no native HANDLE or adapter import."""
import ast
import builtins
import copy
import importlib.util
import json
import os
from pathlib import Path
import pickle
import sys
from threading import get_ident
from types import FunctionType,ModuleType,CodeType
import unittest
from unittest import mock

NATIVE_BUILTINS=tuple(vars(builtins).items())
ROOT=Path(__file__).absolute().parents[1]
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v7.py'
NS=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'
BS=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_v3.py'
spec=importlib.util.spec_from_file_location('_runtime_core_unit',CORE)
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)

def load(path,name,extra):
    module=ModuleType(name);vars(module).update(__file__=str(path),**extra)
    exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0),vars(module))
    return module

class LogicalResource:
    def __init__(self,owner):
        self.owner=owner;self.creator=(os.getpid(),get_ident(),7);self.phase='LIVE'
        self.pending=[(101,'live'),(102,'live')];self.close_calls=[0,0]
        self.guard=dict(active=True,self_live=True,events=[],faults=[],runtime_attempted=False)
        self._early=dict(active=True,blocked=[]);self.observation={'logical':True}
        self.reject=ValueError
    def snapshot(self):return self.observation
    def close(self,owner,primary=None):
        if self.owner is not owner:raise self.reject('logical native owner differs')
        for i in (1,0):
            if self.pending[i] is not None:self.close_calls[i]+=1;self.pending[i]=None
        self.phase='CLOSED';self.guard['self_live']=False

def fixture(full_sources=False):
    old=ROOT/'results/tables/staged_rts24_saved_fresh_machinery_transition_v1_non_authoritative/checks_01/admission_repair.json'
    pins=json.loads(old.read_bytes())['source_pins']
    ref=lambda path:dict(path=str(path),pin=core.pin(path.read_bytes()))
    plan=dict(schema='staged_saved_F_runtime_handoff_manifest_v1',authority='DRAFT_NONAUTHORITATIVE',nonce='0'*32,
        source_pins=pins,source_epoch=core.SOURCE_SHA,bootstrap_pin=core.pin(b'logical fixture'),
        executable_pin=dict(bytes=104264,sha256='4a7d81f72d979c088c653b1da12c2f2d81da66bdf8074753c6a9b154d9c86116'),
        python=core._PYTHON,environment=dict(PYTHONHASHSEED='0',PYTHONDONTWRITEBYTECODE='1',PYTHONNOUSERSITE='1',OMP_NUM_THREADS='1',MKL_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1'),
        cwd=str(ROOT),initial_paths=list(core._PATHS),selected_runtime_file_observations={n:core.pin(b'') for n in core.TCB_PATHS},
        startup_absent=list(core.STARTUP_ABSENT),startup_profile=None,case='discovery',namespace_helper=ref(NS),import_helper=ref(BS),
        import_policy=ref(ROOT/'results/tables/staged_rts24_saved_fresh_runtime_guard_v1_non_authoritative/import_policy.json'),import_profile=None)
    owner=object.__new__(core.LocalPreEntryLease);r=LogicalResource(owner)
    owner._resource=r;owner._ownership=(r,r.creator,LogicalResource.close.__code__,FunctionType,BaseException)
    owner._sources=tuple((name,(ROOT/name).read_bytes()) for name in pins if full_sources or name=='experiments/staged_rts24_saved_fresh_adoption_v1.py');owner._raw=core.canonical(plan)
    owner._control=core.control_image();owner._bindings=core.capture_bindings()
    owner._verifier=core.check_bindings;owner._verifier_code=core.check_bindings.__code__;owner._verifier_defaults=core.check_bindings.__defaults__
    owner._entry_spec=(FunctionType,core._LocalInputs.entry.__code__,vars(core),core._LocalInputs.entry.__defaults__)
    owner._exact_type=core.LocalPreEntryLease;owner._target_type=core.LocalPreEntryInputs;owner._runtime_target_type=core.LocalRuntimeInputs
    owner._successor=None;owner._type=type;owner._allocate=object.__new__;owner._error=ValueError;owner._phase='LIVE';owner._failure=None
    owner._commit=core.pin(core.canonical(owner._image()));owner._seal=core.seal_image(owner)
    owner._cleanup_seal=(id(r),id(owner._ownership),id(owner._ownership[2]),id(owner._ownership[3]),id(owner._ownership[4]),r.creator)
    return owner

class RuntimeHandoffTests(unittest.TestCase):
    def setUp(self):
        self.lease=fixture(self._testMethodName=='test_direct_adapter_globals_and_class_graph_are_closed');self.inputs=self.lease.transfer();self.r=self.inputs._resource;self.runtime=None
        self.ns=load(NS,'_runtime_ns_unit',dict(_INPUT_TYPE=core.LocalPreEntryInputs,_RUNTIME_TYPE=core.LocalRuntimeInputs))
        self.namespace=self.ns.open_entry_namespace(self.inputs,self.ns.capture_helper_bindings())
        self.bs=load(BS,'_runtime_bs_unit',dict(_READ_FILE=core.read_file))
        self.ns_close=self.ns.LiveEntryNamespace.close;self.close=core.LocalRuntimeInputs.close
        self.extra=[];self.hooks=[];self.boundary_seeds=[]
    def tearDown(self):
        for active in self.hooks:active[0]=False
        for boundary in self.boundary_seeds:
            old=boundary._state;object.__setattr__(boundary,'_state',(old[0],False,*old[2:]))
        self.runtime=self.runtime or self.namespace._runtime_peer
        if self.runtime is not None:
            try:self.close(self.runtime)
            except BaseException:pass
        try:self.ns_close(self.namespace)
        except BaseException:pass
        for owner in (self.inputs,self.lease):
            try:owner.close()
            except BaseException:pass
        for name,module in [(self.ns.ACTUAL_NAME,self.namespace.module),*self.extra]:
            if sys.modules.get(name) is module:del sys.modules[name]
        self.assertEqual(self.r.close_calls,[1,1])
    def hook(self,event,action):
        active=[True];self.hooks.append(active)
        def observer(name,args):
            if active[0] and name==event:action(args)
        sys.addaudithook(observer)
    def adopt(self):self.runtime=self.namespace.transfer_runtime();return self.runtime
    def ns_specs(self,helper):return tuple((FunctionType,getattr(helper,n).__code__,vars(helper),getattr(helper,n).__defaults__) for n in ('prepare_runtime_namespace','verify_runtime_namespace','close_runtime_namespace'))
    def bs_specs(self,helper):return tuple((FunctionType,vars(helper.BootstrapImportBoundary)[n].__code__,vars(helper),vars(helper.BootstrapImportBoundary)[n].__defaults__) for n in ('_entry','close','phase','profile_raw','claim_pending'))
    def bs_proof(self,helper):
        path=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v3.py';tree=ast.parse(path.read_bytes())
        node=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='validate_import_helper')
        context={**vars(core),'__builtins__':vars(builtins)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec',dont_inherit=True,optimize=0),context)
        return context['validate_import_helper'](helper,compile(BS.read_bytes(),str(BS),'exec',dont_inherit=True,optimize=0),NATIVE_BUILTINS)
    def boundary_seed(self):
        """Exact stage-0 guard; current unit machinery, not factory B3/flags admission."""
        from threading import RLock
        import importlib
        runtime=self.adopt();proof=self.bs_proof(self.bs);runtime.prepare_boundary(*self.bs_specs(self.bs),proof)
        raw=Path(json.loads(runtime._raw)['import_policy']['path']).read_bytes();profile=json.loads(raw)
        data={name:core.read_file(name,expected,links=True) for name,expected in profile['external_sources'].items()}
        plan=self.bs._saved_import_finder_plan(data,profile)
        guard=object.__new__(self.bs.BootstrapImportBoundary);token=object();creator=(os.getpid(),get_ident())
        factory=self.bs.open_bootstrap_import_boundary
        callback_code=next(c for c in factory.__code__.co_consts if type(c) is CodeType and c.co_name=='audit_hook')
        values=dict(audit_fn=self.bs.BootstrapImportBoundary._audit,expected_bindings=proof,guard=guard,token=token)
        def cell(value):return (lambda:value).__closure__[0]
        callback=FunctionType(callback_code,vars(self.bs),'audit_hook',None,tuple(cell(values[name]) for name in callback_code.co_freevars))
        bindings=[]
        names=('sys','os','subprocess','get_ident','ROOT','EXE','_READ_FILE','pin','require','sha256','digest','Path','canonical','parse','_saved_import_inputs','_saved_import_finder_plan','freeze_adapter_roots','check_adapter_roots','ModuleType','FunctionType','CodeType','importlib','util','machinery')
        for name in names:
            value=vars(self.bs)[name];is_fn=type(value) is FunctionType
            bindings.append((name,value,value.__code__ if is_fn else None,value.__defaults__ if is_fn else None,self.bs.canonical(value.__kwdefaults__) if is_fn else None,value.__closure__ if is_fn else None))
        attrs=[(sys,name,getattr(sys,name)) for name in ('addaudithook','audit','getprofile','gettrace','setprofile','settrace','modules','_current_frames','meta_path','path_hooks','path','path_importer_cache','version','executable','dont_write_bytecode')]
        attrs.append((builtins,'__import__',builtins.__import__))
        attrs.extend((module,name,getattr(module,name)) for module,names in ((importlib,('util','machinery','import_module')),(importlib.util,('find_spec','spec_from_loader')),(importlib.machinery,('ModuleSpec','FileFinder'))) for name in names)
        own=tuple((name,fn,fn.__code__,fn.__defaults__,self.bs.canonical(fn.__kwdefaults__),fn.__closure__) for name,fn in vars(type(guard)).items() if type(fn) is FunctionType)
        owner=(creator,callback,token,callback_code);owner_commit=self.bs.digest((creator,id(callback),id(callback_code),id(token)))
        fields=dict(_profile_raw=raw,_creator=creator,_namespace=vars(self.bs),_global_bindings=tuple(bindings),_attribute_bindings=tuple(attrs),_own_bindings=own,
            _owner=owner,_owner_commit=owner_commit,_lock=RLock(),_codes=(),_numpy_path=next(p for p in profile['external_sources'] if p.replace('\\','/').endswith('/numpy/testing/_private/utils.py')),
            _numpy_state=None,_paths=tuple(os.path.normcase(os.path.abspath(p)) for p in profile['protected_open_roots'].values()),
            _event_sets=(tuple(profile['process_events']),tuple(profile['process_event_prefixes']),tuple(profile['mutation_events'])),
            _import_machinery=(tuple(map(id,sys.meta_path)),tuple(map(id,sys.path_hooks)),tuple(sys.path),id(sys.path_importer_cache),id(sys.modules)),
            _machinery_base=(tuple(sys.meta_path),tuple(sys.path_hooks),tuple(sys.path),sys.meta_path,sys.path_hooks,sys.path,sys.path_importer_cache,sys.modules,importlib,importlib.util,importlib.machinery),
            _finder_plan=plan,_finder_bindings=(),_finder_authenticated=(),_observed_stage=0,_authenticated_stage=0,
            _state=('INSTALLING',True,0,0,0,0,False,''),_internal=None,_busy=False,_adapter=None,_adapter_bindings=(),_source_raw=None,_failure=None,_first_error=None,
            _runtime=runtime,_path_stage=0,_load_started=False,_cache_initial=tuple(sys.path_importer_cache.items()),_module_initial=tuple(sys.modules.items()),_policy_profile=profile,
            _admitted_paths=tuple(profile['admitted_paths']),_runtime_bindings=(),_retention=(),_handoff_seen=0,_adapter_graph=None,_expected_bindings=proof,
            _protected_functions=(*tuple(value for _,_,value,metadata in proof if metadata is not None),callback))
        self.assertEqual(set(fields)|{'_commit'},set(type(guard).__slots__))
        for name,value in fields.items():object.__setattr__(guard,name,value)
        object.__setattr__(guard,'_commit',self.bs.digest(guard._image()));runtime.own_pending_boundary(guard)
        self.boundary_seeds.append(guard);sys.addaudithook(callback);sys.audit('electricity_grid.saved_import.installation',token)
        self.assertEqual(guard._state[3],1)
        old=guard._state;object.__setattr__(guard,'_state',('ACTIVE',*old[1:]));object.__setattr__(guard,'_commit',self.bs.digest(guard._image()))
        self.assertIs(guard._entry(),guard);return guard
    def test_complete_builtins_member_change_rejected_without_calling_it(self):
        guard=self.boundary_seed();proof=guard._expected_bindings;entry=self.bs.BootstrapImportBoundary._entry
        check=self.bs.verify_bootstrap_import_bindings;original=builtins.set;calls=[];errors=[];dictionary=vars(builtins)
        def replacement(*args,**kwargs):calls.append('set');return original(*args,**kwargs)
        dictionary['set']=replacement
        try:
            try:check(proof)
            except ValueError as error:errors.append(error)
            try:entry(guard)
            except ValueError as error:errors.append(error)
        finally:dictionary['set']=original
        self.assertEqual(len(errors),2);self.assertEqual(calls,[]);self.assertIs(vars(builtins),dictionary)
    def metadata_setter_case(self,member,attribute):
        target=self.bs.pin if member=='pin' else self.bs.BootstrapImportBoundary.phase
        original=getattr(target,attribute);replacement=(lambda *a:None).__code__ if attribute=='__code__' else (object(),)
        seen=[];busy_getters=[];box=[None]
        self.hook('object.__setattr__',lambda args:seen.append(args[1]) if len(args)>=2 and args[0] is target else None)
        self.hook('object.__getattr__',lambda args:busy_getters.append(args[1]) if box[0] is not None and box[0]._busy and len(args)>=2 and args[0] is target else None)
        guard=self.boundary_seed();box[0]=guard
        try:
            with self.assertRaisesRegex(self.bs.BootstrapImportRejected,'helper_or_finder_function_mutation'):setattr(target,attribute,replacement)
            self.assertIs(getattr(target,attribute),original);self.assertEqual(seen,[attribute]);self.assertEqual(busy_getters,[])
            self.assertEqual(guard._state[0],'FAULTED');self.assertEqual(guard._state[4],1);self.assertEqual(guard._state[7],'helper_or_finder_function_mutation')
        finally:
            old=guard._state;object.__setattr__(guard,'_state',(old[0],False,*old[2:]))
            if getattr(target,attribute) is not original:setattr(target,attribute,original)
    def test_module_code_setter_is_atomically_rejected(self):self.metadata_setter_case('pin','__code__')
    def test_module_defaults_setter_is_atomically_rejected(self):self.metadata_setter_case('pin','__defaults__')
    def test_class_code_setter_is_atomically_rejected(self):self.metadata_setter_case('phase','__code__')
    def test_class_defaults_setter_is_atomically_rejected(self):self.metadata_setter_case('phase','__defaults__')
    def test_removed_req_slot_rejects_noop_before_any_entry(self):
        guard=self.boundary_seed();calls=[]
        self.assertNotIn('_req',type(guard).__slots__)
        with self.assertRaises(AttributeError):object.__setattr__(guard,'_req',lambda *a:calls.append('noop'))
        object.__setattr__(guard,'_commit',self.bs.digest(guard._image()))
        self.assertIs(guard._entry(),guard);self.assertEqual(calls,[])
    def test_builtins_tuple_drift_during_close_caches_failure_and_disables_hook(self):
        guard=self.boundary_seed();close=self.bs.BootstrapImportBoundary.close;original=builtins.tuple
        dictionary=vars(builtins);calls=[];caught=[];primary=ValueError('tuple_drift_primary')
        def replacement(*args,**kwargs):calls.append('tuple');raise AssertionError('changed tuple must not be called')
        dictionary['tuple']=replacement
        try:
            for attempt in (0,1):
                try:close(guard,primary)
                except BaseException as error:caught.append(error)
        finally:dictionary['tuple']=original
        self.assertEqual(len(caught),2);self.assertIs(caught[0],caught[1]);self.assertIsInstance(caught[0],self.bs.BootstrapImportUnresolved)
        self.assertIs(caught[0].primary,primary);self.assertTrue(caught[0].cleanup)
        self.assertEqual(guard._state[0],'FAULTED');self.assertFalse(guard._state[1]);self.assertEqual(calls,[])
    def test_coherent_B_S_globals_replacement_refused_before_factory(self):
        runtime=self.adopt();proof=self.bs_proof(self.bs);runtime.prepare_boundary(*self.bs_specs(self.bs),proof)
        calls=[]
        with mock.patch.object(self.bs,'require',lambda *a:calls.append('require')),mock.patch.object(self.bs,'digest',lambda *a:calls.append('digest')):
            with self.assertRaisesRegex(ValueError,'B_S helper expected binding'):self.bs.open_bootstrap_import_boundary(b'forged',runtime,proof)
        self.assertFalse(calls);self.assertIsNone(runtime._boundary)
    def close_branch_fixture(self):
        from types import SimpleNamespace
        from threading import RLock
        seed=SimpleNamespace(_state=('ACTIVE',True,1,1,0,0,False,''),_failure=None,_first_error=None,_lock=RLock(),
            _profile_raw=b'logical close branch',_numpy_state=(None,False),_observed_stage=2,_authenticated_stage=2,_handoff_seen=1)
        seed._expected_bindings=self.bs_proof(self.bs)
        seed._ownership=lambda:((os.getpid(),get_ident()),None,None);seed._entry=lambda:None;seed._image=lambda:()
        return seed
    def close_branch(self,seed,primary,external):
        original=self.bs.BootstrapImportBoundary.close
        context={**vars(self.bs),'_saved_import_inputs':external}
        return FunctionType(original.__code__,context,'logical_close_branch',original.__defaults__)(seed,primary)
    def test_B_S_close_preserves_primary_and_final_commit_secondary(self):
        seed=self.close_branch_fixture();primary=ValueError('original_import_error');calls=[0]
        def image():
            calls[0]+=1
            if calls[0]==2:raise ValueError('final_commit_error')
            return ()
        seed._image=image
        with self.assertRaises(self.bs.BootstrapImportUnresolved) as first:self.close_branch(seed,primary,lambda raw:None)
        self.assertIs(first.exception.primary,primary);self.assertIn(('close_commit','final_commit_error'),[(k,str(v)) for k,v in first.exception.cleanup])
        self.assertEqual(seed._state[0],'FAULTED');self.assertFalse(seed._state[1])
        with self.assertRaises(self.bs.BootstrapImportUnresolved) as again:self.close_branch(seed,None,lambda raw:None)
        self.assertIs(first.exception,again.exception)
    def test_B_S_terminal_bookend_follows_external_reads(self):
        seed=self.close_branch_fixture();steps=[]
        def entry():
            steps.append('entry')
            if 'external' in steps:raise ValueError('post_external_change')
        def external(raw):steps.append('external')
        seed._entry=entry
        with self.assertRaises(self.bs.BootstrapImportUnresolved) as first:self.close_branch(seed,None,external)
        self.assertEqual(steps,['entry','external','entry']);self.assertEqual(seed._state[0],'FAULTED')
        self.assertTrue(any(k=='terminal_bookend' for k,v in first.exception.cleanup))
    def test_normal_linear_owner_and_old_close_noop(self):
        runtime=self.adopt();self.assertIs(self.r.owner,runtime);self.assertIs(runtime.entry(),runtime)
        self.assertEqual((self.inputs._phase,self.namespace._phase),('CONSUMED','CONSUMED'))
        for old in (self.inputs,self.lease):old.close()
        self.ns_close(self.namespace);self.assertEqual(self.r.close_calls,[0,0])
        with self.assertRaises(ValueError):self.inputs.entry()
        with self.assertRaises(ValueError):self.namespace.entry()
        self.close(runtime);self.close(runtime);self.assertEqual(runtime._phase,'CLOSED')
        self.assertNotIn(self.ns.ACTUAL_NAME,sys.modules)
    def test_public_construction_copy_and_mutators_closed(self):
        runtime=self.adopt()
        for fn in (copy.copy,copy.deepcopy,pickle.dumps):
            with self.assertRaises(TypeError):fn(runtime)
        with self.assertRaises(TypeError):core.LocalRuntimeInputs()
        self.assertNotIn('_set',vars(type(runtime)));self.assertNotIn('_set',vars(self.bs.BootstrapImportBoundary))
        with self.assertRaises(AttributeError):runtime._phase='LIVE'
    def test_precommit_raise_retains_original_owner(self):
        def fail(args):raise ValueError('precommit_unit')
        self.hook('electricity_grid.runtime.transfer_prepared',fail)
        with self.assertRaisesRegex(ValueError,'precommit_unit'):self.namespace.transfer_runtime()
        self.assertIs(self.r.owner,self.inputs);self.assertIsNone(self.namespace._runtime_peer)
    def test_precommit_source_mutation_refuses_before_commit(self):
        seen=[];self.hook('electricity_grid.runtime.owner_committed',lambda args:seen.append(args))
        self.hook('electricity_grid.runtime.transfer_prepared',lambda args:object.__setattr__(self.inputs,'_sources',()))
        original=self.inputs._sources
        try:
            with self.assertRaises(ValueError):self.namespace.transfer_runtime()
            self.assertIs(self.r.owner,self.inputs);self.assertFalse(seen)
        finally:self.inputs._sources=original
    def test_precommit_graph_mutation_refuses_before_commit(self):
        seen=[];self.hook('electricity_grid.runtime.owner_committed',lambda args:seen.append(args))
        original=self.namespace.module.require
        self.hook('electricity_grid.runtime.transfer_prepared',lambda args:setattr(self.namespace.module,'require',lambda *a:None))
        try:
            with self.assertRaises(ValueError):self.namespace.transfer_runtime()
            self.assertIs(self.r.owner,self.inputs);self.assertFalse(seen)
        finally:self.namespace.module.require=original
    def test_precommit_target_mutation_refuses_before_commit(self):
        self.hook('electricity_grid.runtime.transfer_prepared',lambda args:object.__setattr__(args[2],'_sources',()))
        with self.assertRaisesRegex(ValueError,'prepared runtime changed'):self.namespace.transfer_runtime()
        self.assertIs(self.r.owner,self.inputs)
    def test_postcommit_retains_exact_target_and_cached_close_failure(self):
        def fail(args):raise ValueError('postcommit_unit')
        self.hook('electricity_grid.runtime.owner_committed',fail)
        with self.assertRaises(core.LocalRuntimeUnresolved) as caught:self.namespace.transfer_runtime()
        self.runtime=caught.exception.owner;self.assertIs(self.r.owner,self.runtime)
        self.assertIs(self.inputs._successor,self.runtime);self.assertIs(self.namespace._runtime_peer,self.runtime)
        with self.assertRaises(core.LocalRuntimeUnresolved) as first:self.close(self.runtime,caught.exception)
        with self.assertRaises(core.LocalRuntimeUnresolved) as again:self.close(self.runtime)
        self.assertIs(first.exception,again.exception);self.assertEqual(self.r.close_calls,[1,1])
    def test_mixed_namespace_context_refused_before_commit(self):
        other=load(NS,'_runtime_ns_other',dict(_INPUT_TYPE=core.LocalPreEntryInputs,_RUNTIME_TYPE=core.LocalRuntimeInputs))
        a=self.ns_specs(self.ns);b=self.ns_specs(other)
        with self.assertRaisesRegex(ValueError,'single namespace helper context'):self.inputs.transfer_runtime(self.namespace,(a[0],b[1],a[2]))
        self.assertIs(self.r.owner,self.inputs)
    def test_mixed_boundary_context_refused_before_registration(self):
        runtime=self.adopt();a=self.bs_specs(self.bs);other=load(BS,'_runtime_bs_other',dict(_READ_FILE=core.read_file));b=self.bs_specs(other)
        with self.assertRaisesRegex(ValueError,'single boundary helper context'):runtime.prepare_boundary(a[0],b[1],*a[2:],self.bs_proof(self.bs))
        self.assertIsNone(runtime._boundary_entry)
    def test_forged_pending_boundary_refused(self):
        runtime=self.adopt();runtime.prepare_boundary(*self.bs_specs(self.bs),self.bs_proof(self.bs))
        fake=object.__new__(self.bs.BootstrapImportBoundary)
        object.__setattr__(fake,'_creator',runtime._creator[:2]);object.__setattr__(fake,'_profile_raw',b'forged')
        with self.assertRaisesRegex(ValueError,'pinned pending policy'):runtime.own_pending_boundary(fake)
        self.assertIsNone(runtime._boundary);self.assertEqual(runtime._phase,'ADOPTED')
    def test_wrong_import_reader_refused_before_registration(self):
        runtime=self.adopt();other=load(BS,'_runtime_wrong_reader',dict(_READ_FILE=lambda *a,**k:b'forged'))
        with self.assertRaisesRegex(ValueError,'B_S bootstrap imported root'):runtime.prepare_boundary(*self.bs_specs(other),self.bs_proof(other))
        self.assertIsNone(runtime._boundary_entry)
    def test_direct_adapter_globals_and_class_graph_are_closed(self):
        runtime=self.adopt();name='src.staged_rts24_saved_fresh_adoption_v1'
        raw=(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py').read_bytes();tree=ast.parse(raw)
        imports=[n for n in tree.body if type(n) in (ast.Import,ast.ImportFrom)]
        tree.body=[n for n in tree.body if n not in imports]
        import dataclasses
        from hashlib import sha256
        prefix=ModuleType('src.staged_rts24_saved_prefix_replay_v1');journal=ModuleType('src.staged_rts24_journal_v2')
        prefix.core=ModuleType('_logical_adapter_core');prefix.codec=ModuleType('_logical_adapter_codec');prefix.mechanical=ModuleType('_logical_adapter_mechanical')
        prefix.codec.require=core.require;prefix.ROOT=ROOT;journal.SOURCE_PATHS=()
        extra=('src/staged_rts24_saved_fresh_adoption_v1.py','experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py','docs/plan/staged_deliverability_c_saved_fresh_adoption_scope_budget_v1.md')
        prefix.SOURCES=tuple(sorted(n for n,r in runtime._sources if n not in extra))
        adapter=ModuleType(name);vars(adapter).update(dataclass=dataclasses.dataclass,sha256=sha256,Path=Path,sys=sys,prefix=prefix,journal=journal,__file__=str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'))
        with mock.patch.dict(sys.modules,{name:adapter,prefix.__name__:prefix,journal.__name__:journal}):
            exec(compile(tree,str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py'),'exec',dont_inherit=True,optimize=0),vars(adapter))
            proof=self.bs.freeze_adapter_roots(adapter,raw,runtime);self.bs.check_adapter_roots(adapter,proof)
            adapter.GATES['formal_result']=True
            with self.assertRaisesRegex(ValueError,'direct globals or class graph'):self.bs.check_adapter_roots(adapter,proof)
            adapter.GATES['formal_result']=False
            original=adapter.HeldInput;adapter.HeldInput=object
            with self.assertRaisesRegex(ValueError,'direct globals or class graph'):self.bs.check_adapter_roots(adapter,proof)
            adapter.HeldInput=original;self.bs.check_adapter_roots(adapter,proof)
    def test_empty_finish_proof_refused_before_profile(self):
        runtime=self.adopt()
        with self.assertRaisesRegex(ValueError,'handoff incomplete'):runtime.finish_import(ModuleType('fake'),(),())
        self.assertEqual(runtime._phase,'ADOPTED');self.assertFalse(runtime._import_profile_matched)
    def test_consumed_namespace_mutation_does_not_invoke_foreign_metadata(self):
        runtime=self.adopt();calls=[];original=self.namespace._metadata_function
        object.__setattr__(self.namespace,'_metadata_function',lambda *a:calls.append('called'))
        try:
            with self.assertRaisesRegex(ValueError,'immutable fields changed'):runtime.entry()
            self.assertFalse(calls)
        finally:object.__setattr__(self.namespace,'_metadata_function',original)
    def test_runtime_root_rebind_rejected_by_held_checker(self):
        runtime=self.adopt();calls=[]
        with mock.patch.object(core,'check_bindings',lambda *a:calls.append('checker')),mock.patch.object(core,'require',lambda *a:calls.append('require')):
            with self.assertRaisesRegex(ValueError,'binding changed'):runtime.entry()
        self.assertFalse(calls)
    def test_cleanup_secondary_cannot_skip_native_and_repeats_cached_failure(self):
        runtime=self.adopt();foreign=ModuleType('foreign_runtime_alias');sys.modules[self.ns.ACTUAL_NAME]=foreign;self.extra.append((self.ns.ACTUAL_NAME,foreign))
        primary=ValueError('original_failure')
        with self.assertRaises(core.LocalRuntimeUnresolved) as first:self.close(runtime,primary)
        self.assertIs(first.exception.primary,primary);self.assertTrue(any(layer=='namespace' for layer,error in first.exception.secondary))
        self.assertIs(sys.modules[self.ns.ACTUAL_NAME],foreign);self.assertEqual(self.r.close_calls,[1,1])
        with self.assertRaises(core.LocalRuntimeUnresolved) as again:self.close(runtime)
        self.assertIs(first.exception,again.exception)
    def test_malformed_namespace_cleanup_plan_still_closes_native(self):
        runtime=self.adopt();object.__setattr__(runtime,'_namespace_specs',())
        with self.assertRaises(core.LocalRuntimeUnresolved) as first:self.close(runtime)
        self.assertEqual(self.r.close_calls,[1,1]);self.assertTrue(first.exception.secondary)
        with self.assertRaises(core.LocalRuntimeUnresolved) as again:self.close(runtime)
        self.assertIs(first.exception,again.exception)

if __name__=='__main__':unittest.main()
