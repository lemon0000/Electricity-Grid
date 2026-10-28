"""Logical binding/lifetime faults plus 25 frozen regressions; no cold/P1 runs."""
import ast
from contextlib import contextmanager
import importlib.util
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType,FunctionType,ModuleType,SimpleNamespace
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]


def load(path,name,extra=None):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec)
    module.__dict__.update(extra or {});spec.loader.exec_module(module);return module


legacy=load('tests/test_staged_rts24_saved_fresh_live_profile_v1.py','_consumer_frozen_tests')
core=load('experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py','_consumer_unit_core')
helper=load('experiments/staged_rts24_saved_fresh_entry_namespace_consumer_v2.py','_consumer_unit_helper',
    dict(_RUNTIME_TYPE=core.LocalRuntimeInputs))
RAW={name:(ROOT/name).read_bytes() for name in legacy.parent.source()}


def logical_entry(owner):
    if core.runtime_seal(owner)!=owner._seal:raise ValueError('logical seal differs')
    owner._resource.events.append(('entry',owner._phase,owner._consume_state))
    if owner._resource.post_failure and owner._consume_state=='RUNNING':raise ValueError('injected post-entry failure')
    if owner._consumer_plan is not None:helper.verify_consumer_plan(owner,owner._consumer_plan)
    return owner


def logical_bookend(owner):owner._resource.events.append(('source_bookend',))


def logical_bindings(rows):return None


def logical_close(owner,primary=None):
    resource=owner._resource
    if resource.phase=='CLOSED':
        if owner._failure is not None:raise owner._failure
        return
    resource.events.append(('close',primary));resource.phase='CLOSED'
    secondary=(('logical_cleanup',ValueError('injected close failure')),) if resource.close_failure else ()
    if primary is not None or secondary:
        failure=core.LocalRuntimeUnresolved(owner,primary,secondary)
        object.__setattr__(owner,'_failure',failure);object.__setattr__(owner,'_phase','UNRESOLVED');raise failure from primary
    object.__setattr__(owner,'_phase','CLOSED')


def method_row(name,fn):return (core.LocalRuntimeInputs,name,fn,fn.__code__,fn.__defaults__,fn.__kwdefaults__,fn.__closure__)


def logical_method(name,production_checker=False,putter=None,dispatcher=None):
    fn=vars(core.LocalRuntimeInputs)[name]
    context={**vars(core),'core':core,'helper':helper,'object':object}
    values=dict(zip(fn.__code__.co_varnames[fn.__code__.co_argcount-len(fn.__defaults__):fn.__code__.co_argcount],fn.__defaults__))
    values.update(_close_code=logical_close.__code__,_close_defs=logical_close.__defaults__,_ctx=context,
        _entry_code=logical_entry.__code__,_entry_defs=logical_entry.__defaults__,
        _bookend_code=logical_bookend.__code__,_bookend_defs=logical_bookend.__defaults__)
    if not production_checker:values.update(_check_code=logical_bindings.__code__,_check_defs=logical_bindings.__defaults__)
    if putter is not None:values['_put']=putter
    if dispatcher is not None:values.update(_helper_code=dispatcher.__code__,_helper_defs=dispatcher.__defaults__)
    return FunctionType(fn.__code__,vars(core),'logical_'+name,tuple(values.values()))


def set_owner(owner,**values):
    for name,value in values.items():object.__setattr__(owner,name,value)
    object.__setattr__(owner,'_seal',core.runtime_seal(owner))


@contextmanager
def fixture():
    registry={}
    def module(path):
        name=path[:-3].replace('/','.');m=ModuleType(name);m.__file__=str(ROOT/path);registry[name]=m;return m
    def function(m,path,name,defaults=None,kw=None):
        unit=compile(RAW[path],str(ROOT/path),'exec',dont_inherit=True,optimize=0)
        code=next(c for c in unit.co_consts if type(c) is CodeType and c.co_name==name)
        fn=FunctionType(code,vars(m),name,defaults);fn.__kwdefaults__=kw;setattr(m,name,fn);return fn
    adapter_path='src/staged_rts24_saved_fresh_adoption_v1.py';adapter=module(adapter_path)
    for name in ('digest','sources','stamp','caller_image','capture','hold','bookend','project_metrics','validate_metrics',
            'replay','_replay','validate_payload','bind_payload','compare_payloads'):
        function(adapter,adapter_path,name,kw={'inventory':True} if name=='bookend' else None)
    leaves=[]
    for path,name in (('src/staged_rts24_development_v1.py','load_fixture'),
            ('src/staged_rts24_p2_package_check_v1.py','inventory'),('src/staged_rts24_evidence_store_v1.py','read_bytes'),
            ('src/staged_rts24_saved_point_replay_v1.py','_outer')):
        m=module(path);m.ROOT=ROOT
        if name=='load_fixture':m.CONFIG=ROOT/'configs/staged_deliverability_rts24_v1.DRAFT.yaml'
        function(m,path,name,(m.CONFIG,) if name=='load_fixture' else (False,) if name=='read_bytes' else None)
        leaves.append(m)
    adapter.core,adapter.mechanical,adapter.codec=leaves[:3]
    adapter.prefix=module('src/staged_rts24_prefix_replay_v1.py');adapter.prefix.point=leaves[3]
    entry=module(helper.ENTRY);entry.__dict__.update(ast=ast,require=core.require,sys=sys,Path=Path,ROOT=ROOT,
        NEW_SOURCES=(adapter_path,),canonical=core.canonical,FunctionType=FunctionType)
    function(entry,helper.ENTRY,'_expectation_binding_entry')
    owner=object.__new__(core.LocalRuntimeInputs)
    for slot in core.LocalRuntimeInputs.__slots__:object.__setattr__(owner,slot,None)
    resource=SimpleNamespace(owner=owner,phase='LIVE',events=[],post_failure=False,close_failure=False)
    namespace=SimpleNamespace(module=entry,_runtime_peer=owner,_bindings=())
    bindings=helper.capture_helper_bindings()
    namespace._bindings=bindings
    runtime_bindings=tuple((name,vars(adapter)[name],vars(adapter)[name].__code__,vars(adapter)[name].__defaults__,
        core.canonical(vars(adapter)[name].__kwdefaults__),vars(adapter)[name].__closure__)
        for name in ('digest','sources','stamp','caller_image','capture','hold','bookend','project_metrics','validate_metrics',
            'replay','_replay','validate_payload','bind_payload','compare_payloads'))
    boundary=SimpleNamespace(_adapter=adapter,_runtime_bindings=runtime_bindings,
        _retention=tuple(registry.items()))
    phase=lambda boundary:'CLOSED'
    set_owner(owner,_phase='IMPORTING',_raw=b'logical input bytes',_creator=(os.getpid(),get_ident(),1),_resource=resource,
        _namespace=namespace,_boundary=boundary,_boundary_phase=(FunctionType,phase.__code__,phase.__globals__,None),
        _sources=tuple(RAW.items()),_bindings=tuple(method_row(name,fn) for name,fn in (('entry',logical_entry),('source_bookend',logical_bookend))),
        _namespace_specs=(None,(None,None,vars(helper),None)),_consumer_plan=None,_consume_state=None,
        _adapter=None,_retention=(),_import_profile_matched=False)
    with patch.dict(sys.modules,registry):yield owner,adapter,entry,leaves


def prepared_live(owner):
    logical_method('prepare_consumer')(owner)
    set_owner(owner,_phase='LIVE',_adapter=owner._boundary._adapter,_adapter_bindings=owner._boundary._runtime_bindings,_retention=owner._boundary._retention,
        _import_profile_matched=True)


def consume(owner,request=b'{"consumer":"expectation_binding","v":1}',consumer='expectation_binding'):
    return logical_method('consume_once')(owner,consumer,request)


class ConsumerBindingTests(legacy.LiveProfileTests):
    def test_26_fixed_source_defaults_and_pre_live_plan(self):
        with fixture() as (owner,adapter,entry,leaves):
            self.assertIs(logical_method('prepare_consumer')(owner),owner)
            self.assertEqual(owner._consume_state,'PREPARED');self.assertEqual(owner._phase,'IMPORTING')
            plan=owner._consumer_plan;self.assertIs(plan[0],owner);self.assertIs(plan[6][2],entry._expectation_binding_entry)
            self.assertEqual(len(plan[7]),10);self.assertEqual(len(plan[10]),6)
            self.assertIs(helper.verify_consumer_plan(owner,plan),plan)

    def test_27_one_shot_real_consumer_body_and_close_before_return(self):
        with fixture() as (owner,adapter,entry,leaves):
            prepared_live(owner);result=consume(owner)
            self.assertEqual(type(result),bytes);value=json.loads(result);self.assertEqual(core.canonical(value),result)
            self.assertTrue(value['same_live_owner']);self.assertEqual(value['binding_members'],10)
            self.assertTrue(all(value[key] is False for key in legacy.parent.FALSE_FIELDS))
            self.assertIs(value['producer_capability_verified'],False)
            self.assertEqual(owner._consume_state,'CONSUMED');self.assertEqual(owner._phase,'CLOSED')
            self.assertEqual(owner._resource.events[-1],('close',None));self.assertEqual(owner._resource.phase,'CLOSED')
            with self.assertRaisesRegex(ValueError,'terminal'):consume(owner)
            self.assertEqual(sum(row[0]=='close' for row in owner._resource.events),1)

    def test_28_default_coherent_wrong_path_and_false_integer(self):
        for mode in ('config','false'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                if mode=='config':
                    adapter.core.CONFIG=ROOT/'configs/wrong.yaml';adapter.core.load_fixture.__defaults__=(adapter.core.CONFIG,)
                else:adapter.codec.read_bytes.__defaults__=(0,)
                with self.assertRaises(core.LocalRuntimeUnresolved) as failure:logical_method('prepare_consumer')(owner)
                self.assertIsInstance(failure.exception.primary,ValueError);self.assertEqual(owner._resource.phase,'CLOSED')

    def test_29_same_code_clone_and_equal_default_identity(self):
        for mode in ('clone','default','kw'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                prepared_live(owner)
                if mode=='clone':
                    fn=leaves[1].inventory;leaves[1].inventory=FunctionType(fn.__code__,vars(leaves[1]),fn.__name__,fn.__defaults__)
                elif mode=='default':leaves[0].load_fixture.__defaults__=(Path(str(leaves[0].CONFIG)),)
                else:adapter.bookend.__kwdefaults__['inventory']=1
                with self.assertRaises(core.LocalRuntimeUnresolved):consume(owner)
                self.assertEqual(owner._resource.phase,'CLOSED')

    def test_30_four_leaf_coherent_replacement(self):
        with fixture() as (owner,adapter,entry,leaves):
            prepared_live(owner)
            for module,name in zip(leaves,('load_fixture','inventory','read_bytes','_outer')):
                fn=vars(module)[name];setattr(module,name,FunctionType(fn.__code__,vars(module),name,fn.__defaults__))
            with self.assertRaises(core.LocalRuntimeUnresolved):consume(owner)
            self.assertEqual(owner._resource.phase,'CLOSED')

    def test_31_plan_replacement_clone_creator_and_retention(self):
        for mode in ('plan','owner','creator','retention','member'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                prepared_live(owner)
                if mode=='plan':object.__setattr__(owner,'_consumer_plan',tuple(list(owner._consumer_plan)))
                elif mode=='owner':
                    plan=list(owner._consumer_plan);plan[0]=object();set_owner(owner,_consumer_plan=tuple(plan))
                elif mode=='creator':set_owner(owner,_creator=(-1,get_ident(),1))
                elif mode=='retention':sys.modules.pop(leaves[2].__name__)
                else:
                    plan=list(owner._consumer_plan);plan[7]=list(plan[7]);set_owner(owner,_consumer_plan=tuple(plan))
                with self.assertRaises(core.LocalRuntimeUnresolved):consume(owner)
                self.assertEqual(owner._resource.phase,'CLOSED')

    def test_32_callback_mutation_and_failure_primary(self):
        for mode in ('mutation','exception'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                prepared_live(owner);calls=[]
                def observer(value,message):
                    calls.append(1);core.require(value,message)
                    if mode=='exception':raise ValueError('injected consumer primary')
                    if len(calls)==11:leaves[0].load_fixture.__defaults__=(Path(str(leaves[0].CONFIG)),)
                entry.require=observer
                with self.assertRaises(core.LocalRuntimeUnresolved) as failure:consume(owner)
                self.assertEqual(owner._resource.phase,'CLOSED')
                self.assertIsInstance(failure.exception.primary,ValueError)
                if mode=='exception':self.assertEqual(str(failure.exception.primary),'injected consumer primary')

    def test_33_reentry_and_failure_retry_are_sticky(self):
        with fixture() as (owner,adapter,entry,leaves):
            prepared_live(owner)
            def reenter(value,message):core.require(value,message);consume(owner)
            entry.require=reenter
            with self.assertRaises(core.LocalRuntimeUnresolved):consume(owner)
            self.assertEqual(owner._resource.phase,'CLOSED')
            with self.assertRaisesRegex(ValueError,'terminal'):consume(owner)
            self.assertEqual(sum(row[0]=='close' for row in owner._resource.events),1)

    def test_34_callback_success_post_or_cleanup_failure_has_no_result(self):
        for mode in ('post','close'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                prepared_live(owner)
                if mode=='post':owner._resource.post_failure=True
                else:owner._resource.close_failure=True
                with self.assertRaises(core.LocalRuntimeUnresolved) as failure:consume(owner)
                self.assertEqual(owner._resource.phase,'CLOSED');self.assertEqual(owner._phase,'UNRESOLVED')
                if mode=='post':self.assertIn('post-entry',str(failure.exception.primary))
                else:self.assertEqual(failure.exception.secondary[0][0],'logical_cleanup')

    def test_35_request_and_non_live_rejection(self):
        for mode in ('request','id','OBSERVED','profile'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                prepared_live(owner)
                if mode=='OBSERVED':set_owner(owner,_phase='OBSERVED')
                elif mode=='profile':set_owner(owner,_import_profile_matched=False)
                with self.assertRaises(core.LocalRuntimeUnresolved):
                    consume(owner,b'{}' if mode=='request' else owner._consumer_plan[12],
                        'other' if mode=='id' else 'expectation_binding')
                self.assertEqual(owner._resource.phase,'CLOSED')

    def test_36_partial_prepare_commit_cleanup(self):
        with fixture() as (owner,adapter,entry,leaves):
            class FaultPut:
                @staticmethod
                def __setattr__(target,name,value):
                    if target is owner and name=='_consume_state':raise ValueError('injected partial plan commit')
                    object.__setattr__(target,name,value)
            with self.assertRaises(core.LocalRuntimeUnresolved) as failure:
                logical_method('prepare_consumer',putter=FaultPut.__setattr__)(owner)
            self.assertIsNotNone(owner._consumer_plan);self.assertEqual(owner._resource.phase,'CLOSED')
            self.assertEqual(str(failure.exception.primary),'injected partial plan commit')

    def test_37_probe_same_owner_preparation_and_no_extra_import(self):
        path=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v36.py';tree=ast.parse(path.read_bytes())
        main=next(node for node in tree.body if type(node) is ast.FunctionDef and node.name=='_probe_main')
        text=ast.unparse(main)
        self.assertLess(text.index('load_bootstrap_adapter(runtime, boundary)'),text.index('runtime.prepare_consumer()'))
        self.assertLess(text.index('runtime.prepare_consumer()'),text.index('runtime.finish_import('))
        self.assertLess(text.index('runtime.finish_import('),text.index('runtime.consume_once('))
        for node in ast.walk(tree):
            if type(node) is ast.ImportFrom:self.assertNotIn(node.module,('src','experiments'))
        self.assertEqual(path.read_bytes().count(b'nfc_v11_non_authoritative'),1)

    def test_38_fixed_manifest_foreign_shapes_and_original_adapter_identity(self):
        for mode in ('roots','edges','sources','uncommitted','adapter_clone'):
            with self.subTest(mode=mode),fixture() as (owner,adapter,entry,leaves):
                if mode=='adapter_clone':
                    fn=adapter.hold;adapter.hold=FunctionType(fn.__code__,vars(adapter),'hold',fn.__defaults__)
                    with self.assertRaises(core.LocalRuntimeUnresolved):logical_method('prepare_consumer')(owner)
                    continue
                prepared_live(owner);plan=list(owner._consumer_plan)
                if mode=='roots':plan[7]=plan[7][1:]+plan[7][:1]
                elif mode=='edges':plan[9]=plan[9][1:]+plan[9][:1]
                elif mode=='sources':plan[10]=plan[10][1:]+plan[10][:1]
                else:set_owner(owner,_consume_state=None)
                set_owner(owner,_consumer_plan=tuple(plan))
                with self.assertRaises(core.LocalRuntimeUnresolved):consume(owner)
                self.assertEqual(owner._resource.phase,'CLOSED')

    def test_39_exception_preserved_with_post_check_secondary(self):
        with fixture() as (owner,adapter,entry,leaves):
            prepared_live(owner);primary=ValueError('injected combined primary')
            def both(value,message):
                leaves[0].load_fixture.__defaults__=(Path(str(leaves[0].CONFIG)),)
                raise primary
            entry.require=both
            with self.assertRaises(core.LocalRuntimeUnresolved) as failure:consume(owner)
            self.assertIs(failure.exception.primary,primary)
            self.assertIsInstance(primary.__cause__,BaseExceptionGroup)
            self.assertTrue(any('metadata' in str(item) for item in primary.__cause__.exceptions))

    def test_40_first_bookend_global_tampering_never_invokes_replacement(self):
        for method in ('prepare_consumer','consume_once'):
            for target in ('held_consumer_helper','require','object'):
                with self.subTest(method=method,target=target),fixture() as (owner,adapter,entry,leaves):
                    if method=='consume_once':prepared_live(owner)
                    set_owner(owner,_bindings=core.capture_bindings());calls=[]
                    def evil(*args,**kwargs):calls.append((args,kwargs));raise AssertionError('replacement must not run')
                    fn=logical_method(method,production_checker=True)
                    with patch.dict(vars(core),{target:evil}):
                        with self.assertRaises(core.LocalRuntimeUnresolved) as failure:
                            fn(owner) if method=='prepare_consumer' else fn(owner,'expectation_binding',owner._consumer_plan[12])
                    self.assertEqual(calls,[]);self.assertEqual(owner._resource.phase,'CLOSED')
                    self.assertIsInstance(failure.exception.primary,ValueError)

    def test_41_malformed_result_rejects_before_commit_and_preserves_cleanup(self):
        def malformed(owner,name):return lambda *args:owner._resource.bad_result
        for value in (None,bytearray(),b'x'*2049):
            with self.subTest(kind=type(value).__name__),fixture() as (owner,adapter,entry,leaves):
                prepared_live(owner);owner._resource.bad_result=value;owner._resource.close_failure=True
                with self.assertRaises(core.LocalRuntimeUnresolved) as failure:
                    logical_method('consume_once',dispatcher=malformed)(owner,'expectation_binding',owner._consumer_plan[12])
                self.assertEqual(owner._consume_state,'FAILED');self.assertEqual(owner._phase,'UNRESOLVED')
                self.assertEqual(str(failure.exception.primary),'bounded consumer bytes required')
                self.assertEqual(failure.exception.secondary[0][0],'logical_cleanup')
