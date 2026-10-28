"""Synthetic standard-loader -> construction -> graph -> lifecycle bundle."""
import ast
import builtins
from hashlib import sha256
import importlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import get_ident
from threading import Thread
from types import FunctionType,ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]
GRAPH_PATH=ROOT/'experiments/staged_rts24_saved_fresh_producer_project_graph_v3.py'
PROGRAM_PATH=ROOT/'experiments/staged_rts24_saved_fresh_producer_bootstrap_v3.py'
LC_PATH=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v2.py'
BASE_LC_RAW=(ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py').read_bytes()
GRAPH_RAW=GRAPH_PATH.read_bytes();RAW=PROGRAM_PATH.read_bytes();LC_RAW=LC_PATH.read_bytes()


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


graph=load(GRAPH_PATH,'_new_project_graph')
program=load(PROGRAM_PATH,'_new_project_bootstrap')
lifecycle=load(LC_PATH,'_frozen_lifecycle_for_bootstrap')
legacy=load(ROOT/'tests/test_staged_rts24_saved_fresh_producer_project_graph_v1.py','_legacy_graph_regression')
legacy.graph=graph
old_lifecycle=load(ROOT/'tests/test_staged_rts24_saved_fresh_retained_producer_v1.py','_lifecycle_fixtures')
old_lifecycle.engine=lifecycle;old_lifecycle.RAW=LC_RAW;old_lifecycle.PROGRAM=LC_PATH
_ACTIVE=[None]


def _test_audit(event,args):
    if event!='exec':return
    target=_ACTIVE[0]
    if target is not None:target(event,args)


sys.addaudithook(_test_audit)

CORE_RAW=b'''
from types import FunctionType
def runtime_seal(owner,phase=None):return owner._phase
def check_bindings():pass
class Runtime:
    def entry(self,_c=runtime_seal.__code__,_f=FunctionType,_g=globals(),_d=runtime_seal.__defaults__,
            _b=check_bindings.__code__,_bd=check_bindings.__defaults__,_e=ValueError):
        if self._creator!=CREATOR or self._phase not in ('ADOPTED','IMPORTING','OBSERVED','LIVE'):
            raise _e('logical owner unavailable')
        self.entry_calls+=1
        return self
    def source_bookend(self):return {}
    def close(self,primary=None):self.close_calls+=1;self._phase='CLOSED'
'''


class ProducerBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='producer_bootstrap_');self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        token=self.root.name.replace('-','_')
        self.entry_name='_pc_entry_'+token;self.adapter_name='_pc_adapter_'+token;self.dep_name='_pc_dep_'+token
        self.source={self.entry_name:(self.entry_name+'.py',b'ENTRY_VALUE=1\n'),
            self.dep_name:(self.dep_name+'.py',b'VALUE=2\n'),
            self.adapter_name:(self.adapter_name+'.py',('import '+self.dep_name+'\nVALUE=3\n').encode())}
        for name,(relative,raw) in self.source.items():(self.root/relative).write_bytes(raw)
        self.entry=ModuleType(self.entry_name)
        self.entry.__dict__.update(__file__=str(self.root/self.source[self.entry_name][0]),__package__='',
            __spec__=None,__loader__=None,__builtins__=vars(builtins))
        raw=self.source[self.entry_name][1];unit=compile(raw,self.entry.__file__,'exec',dont_inherit=True,optimize=0)
        reference=ModuleType(self.entry_name);exec(unit,vars(reference),vars(reference));exec(unit,vars(self.entry),vars(self.entry))
        scope=patch.dict(sys.modules,{self.entry_name:self.entry});scope.start();self.addCleanup(scope.stop)
        self.saved_path=list(sys.path);sys.path.insert(0,str(self.root));self.addCleanup(lambda:sys.path.__setitem__(slice(None),self.saved_path))
        core=ModuleType('_logical_core');core.__file__=str(self.root/'not_registered_core.py')
        core.__dict__['CREATOR']=(os.getpid(),get_ident())
        exec(compile(CORE_RAW,core.__file__,'exec',dont_inherit=True,optimize=0),vars(core),vars(core))
        self.owner=core.Runtime();self.owner.__dict__.update(_creator=core.CREATOR,_phase='IMPORTING',
            _adapter=None,_consume_state=None,entry_calls=0,close_calls=0,
            _sources=tuple((relative,raw) for relative,raw in self.source.values()),
            _namespace=SimpleNamespace(module=self.entry,_raw=raw,_unit=unit,_exec_attempts=2,_exec_completed=2,_actual_initialized=True))
        self.spec=program.source_program(RAW,dict(_RUNTIME_TYPE=core.Runtime),BASE_LC_RAW)
        self.context=self.spec[2][0];self.dispatch=FunctionType(self.spec[0],self.spec[1])
        self.plan=self.call('_begin',self.owner,self.source,self.root,self.entry_name,self.adapter_name)
        self.addCleanup(lambda:_ACTIVE.__setitem__(0,None))

    def call(self,name,*args,**kwargs):return self.dispatch(self.spec[2],name,args,kwargs)

    def collect(self):
        _ACTIVE[0]=lambda event,args:self.call('observe_exec',self.plan,event,args)
        try:self.adapter=importlib.import_module(self.adapter_name)
        finally:_ACTIVE[0]=None
        return self.call('finalize_project_construction',self.plan,self.adapter)

    def bundle(self):
        self.collect()
        # No actual runtime/P1 grant is produced by this logical process-local
        # object. Frozen lifecycle prepare must reject the synthetic source set.
        code=compile(b'def capture_saved_expectation_prebound(source,binding):pass\n','<synthetic capture>','exec').co_consts[0]
        return self.call('make_project_bootstrap_bundle',self.plan,graph,GRAPH_RAW,lifecycle,LC_RAW,code,None)

    def test_01_standard_loader_exact_exec_rows_and_returned_graph(self):
        self.collect();self.assertEqual(self.plan._phase,'FINAL');self.assertEqual(self.plan._observed,2)
        modules=self.call('selected_modules',self.plan);self.assertEqual(set(modules),set(self.source))
        self.assertIs(modules[self.entry_name],self.entry)
        for name,row in self.plan._rows.items():
            self.assertIs(row[0],sys.modules[name]);self.assertIs(row[1].loader,row[2]);self.assertEqual(row[3],self.plan._units[name])
        snapshot=graph.capture(modules,self.source,self.root,registry=sys.modules)
        self.assertTrue(graph.check(snapshot)['structure_and_identity_stable'])
        self.assertIsNone(self.owner._consume_state)

    def test_02_exec_code_drift_is_sticky_and_blocks_finalize(self):
        (self.root/self.source[self.dep_name][0]).write_bytes(b'VALUE=999\n')
        with self.assertRaises(ValueError) as caught:self.collect()
        original=caught.exception;self.assertIs(self.plan._failure,original)
        self.assertEqual(self.plan._phase,'FAILED');self.assertIsNone(self.owner._consume_state)
        with self.assertRaises(ValueError) as again:self.call('finalize_project_construction',self.plan,self.entry)
        self.assertIs(again.exception,original)

    def test_03_exec_event_without_loader_globals_frame_is_rejected(self):
        name=self.dep_name;relative,_=self.source[name]
        loader=importlib.machinery.SourceFileLoader(name,str(self.root/relative))
        spec=importlib.util.spec_from_loader(name,loader);module=importlib.util.module_from_spec(spec)
        spec._initializing=True;sys.modules[name]=module
        with self.assertRaises(ValueError) as caught:self.call('observe_exec',self.plan,'exec',(self.plan._units[name],))
        self.assertIn('execution frames required',str(caught.exception))
        self.assertIs(self.plan._failure,caught.exception)

    def test_04_missing_exec_set_cannot_finalize_or_claim_slot(self):
        with self.assertRaises(ValueError):self.call('finalize_project_construction',self.plan,self.entry)
        self.assertEqual(self.plan._phase,'FAILED');self.assertIsNone(self.owner._consume_state)

    def test_05_extra_project_alias_rejects_complete_import(self):
        _ACTIVE[0]=lambda event,args:self.call('observe_exec',self.plan,event,args)
        try:self.adapter=importlib.import_module(self.adapter_name)
        finally:_ACTIVE[0]=None
        sys.modules['_pc_extra_alias']=self.adapter
        with self.assertRaises(ValueError) as caught:self.call('finalize_project_construction',self.plan,self.adapter)
        self.assertIn('extra project',str(caught.exception))

    def test_06_registry_replacement_after_final_is_rejected(self):
        self.collect();original=sys.modules[self.dep_name];sys.modules[self.dep_name]=ModuleType(self.dep_name)
        with self.assertRaises(ValueError):self.call('check',self.plan,final=True)
        sys.modules[self.dep_name]=original

    def test_07_duplicate_reload_is_rejected(self):
        self.collect()
        with self.assertRaises(ValueError):self.call('observe_exec',self.plan,'exec',(self.plan._units[self.dep_name],))
        self.assertEqual(self.plan._phase,'FAILED');self.assertIsNone(self.owner._consume_state)

    def test_08_bundle_uses_same_certificate_raw_and_snapshot(self):
        held=self.bundle();plan,seen_graph,snapshot,dispatch,verify_code,context,guard=held[2]
        self.assertIs(plan,self.plan);self.assertIs(seen_graph,graph);self.assertIs(snapshot._registry,sys.modules)
        self.assertEqual(dict(snapshot._modules),self.call('selected_modules',self.plan))
        for name,(_,raw) in self.source.items():self.assertIs(dict(snapshot._sources)[name][1],raw)
        self.assertIsNone(self.owner._consume_state)
        reached=[]
        def downstream(state,producer,operation,args,kwargs):
            state.append(operation);return 'lifecycle_reached'
        routed=list(held[2]);routed[3]=(downstream.__code__,dict(__builtins__={}),reached)
        result=FunctionType(held[0],held[1])(tuple(routed),None,'prepare',(),{})
        self.assertEqual(result,'lifecycle_reached');self.assertEqual(reached,['prepare'])
        with self.assertRaises(ValueError):
            FunctionType(held[0],held[1])(held[2],None,'prepare',(self.owner,object()),{})
        self.assertIsNone(self.owner._consume_state)

    def test_09_unsupported_graph_prevents_lifecycle_dispatch_creation(self):
        self.collect();self.adapter.unsupported=object()
        code=compile(b'pass\n','<unused>','exec')
        with self.assertRaises(ValueError):
            self.call('make_project_bootstrap_bundle',self.plan,graph,GRAPH_RAW,lifecycle,LC_RAW,code,None)
        self.assertIsNone(self.owner._consume_state);self.assertEqual(self.owner.close_calls,0)

    def test_10_entry_raw_proof_tamper_is_rejected(self):
        self.owner._namespace._raw=b'changed'
        with self.assertRaises(ValueError):self.call('check',self.plan)
        self.assertIsNone(self.owner._consume_state)

    def test_11_public_bootstrap_cannot_admit_synthetic_owner(self):
        with self.assertRaises(ValueError):program.begin_project_construction(self.owner)
        with self.assertRaises(ValueError):self.call('begin_project_construction',self.owner)
        self.assertIsNone(self.owner._consume_state)

    def test_12_frozen_boundary_successor_only_adds_fixed_bridge_sites(self):
        original=(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v2.py').read_text(encoding='utf-8')
        current=(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py').read_text(encoding='utf-8')
        old=ast.parse(original);new=ast.parse(current)
        a={n.name:ast.dump(n,include_attributes=False) for n in old.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        b={n.name:ast.dump(n,include_attributes=False) for n in new.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        changed={name for name in a if a[name]!=b[name]}
        self.assertEqual(changed,{'load_bootstrap_adapter','BootstrapImportBoundary'})
        self.assertEqual(set(b)-set(a),{'project_bridge_call'})
        loader=next(n for n in new.body if isinstance(n,ast.FunctionDef) and n.name=='load_bootstrap_adapter')
        def bridge_calls(node):
            return [n for n in ast.walk(node) if isinstance(n,ast.Call) and isinstance(n.func,ast.Call)
                and n.func.args and isinstance(n.func.args[0],ast.Name) and n.func.args[0].id=='_project_code']
        calls=[(n.lineno,ast.literal_eval(n.args[1])) for n in bridge_calls(loader)]
        self.assertEqual([stage for _,stage in sorted(calls)],['before_import','after_import'])
        boundary=next(n for n in new.body if isinstance(n,ast.ClassDef) and n.name=='BootstrapImportBoundary')
        audit=next(n for n in boundary.body if isinstance(n,ast.FunctionDef) and n.name=='_audit')
        self.assertEqual([ast.literal_eval(n.args[1]) for n in bridge_calls(audit)],['exec'])
        for fn in (loader,audit):
            defaults=dict(zip([arg.arg for arg in fn.args.args][-len(fn.args.defaults):],fn.args.defaults))
            self.assertEqual(ast.dump(defaults['_project_code']),ast.dump(ast.parse('project_bridge_call.__code__',mode='eval').body))
            self.assertEqual(ast.dump(defaults['_project_defs']),ast.dump(ast.parse('project_bridge_call.__defaults__',mode='eval').body))
            self.assertEqual(ast.dump(defaults['_project_spec']),ast.dump(ast.Name(id='_PROJECT_BRIDGE',ctx=ast.Load())))
        unit=compile(current,str(ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'),'exec',dont_inherit=True,optimize=0)
        self.assertEqual(unit.co_name,'<module>');self.assertIsNone(self.owner._consume_state)

    def test_16_held_three_bridge_sites_ignore_replaced_public_globals(self):
        path=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py';raw=path.read_bytes()
        unit=compile(raw,str(path),'exec',dont_inherit=True,optimize=0)
        code=next(item for item in unit.co_consts if hasattr(item,'co_name') and item.co_name=='project_bridge_call')
        defaults=(FunctionType,type,len,ValueError,tuple)
        self.assertEqual(code.co_names,())
        with self.assertRaises(ValueError):
            FunctionType(code,dict(__builtins__={}),argdefs=defaults)(None,'exec',self.owner,())
        def target(state,stage,runtime,args):return stage
        held=(target.__code__,dict(__builtins__={}),None)
        calls=[]
        def replaced(*args):calls.append('replacement')
        environment=dict(_project_code=code,_project_defs=defaults,_project_spec=held,_fn=FunctionType,
            _project_factory=FunctionType,runtime=self.owner,self=SimpleNamespace(_runtime=self.owner),args=(),
            adapter=self.entry,project_bridge_call=replaced,_PROJECT_BRIDGE=(replaced,None,None))
        tree=ast.parse(raw)
        sites=[node for node in ast.walk(tree) if isinstance(node,ast.Call) and isinstance(node.func,ast.Call)
            and node.func.args and isinstance(node.func.args[0],ast.Name) and node.func.args[0].id=='_project_code']
        self.assertEqual(len(sites),3)
        result=[eval(compile(ast.Expression(node),'<source bridge site>','eval'),dict(__builtins__={}),environment) for node in sites]
        self.assertEqual(set(result),{'before_import','after_import','exec'});self.assertEqual(calls,[])

    def test_13_source_census_is_compile_only_and_exact(self):
        _,report=program.current()
        self.assertEqual(report['declarations'],dict(modules=37,functions=500,classes=146))
        self.assertEqual(report['source49_target_modules_executed'],0)
        for name in program.FALSE_FIELDS:self.assertIs(report[name],False)

    def test_17_unadmitted_bundle_never_enters_prepare(self):
        self.owner._phase='OBSERVED'
        with self.assertRaisesRegex(ValueError,'same active creating runtime'):self.call('check',self.plan)
        self.owner._phase='IMPORTING'
        held=self.bundle()
        private=held[2][3][2][0]
        self.assertIsNone(private['_P1_AUTHORITY'])
        before=self.owner.entry_calls
        for token in (None,object()):
            with self.assertRaisesRegex(ValueError,'same-owner P1 diagnostic admission required'):
                FunctionType(held[0],held[1])(held[2],None,'prepare',(self.owner,token),{})
        self.assertIsNone(self.owner._consume_state)
        self.assertEqual(self.owner.close_calls,0)
        self.assertGreater(self.owner.entry_calls,before)

    def test_18_local_token_cannot_create_public_import_bridge(self):
        self.owner._phase='ADOPTED'
        code=compile('pass','<unused capture>','exec')
        with self.assertRaisesRegex(ValueError,'local tokens are rejected'):
            self.call('new_import_bridge',self.owner,graph,GRAPH_RAW,lifecycle,LC_RAW,code,object())
        self.assertIsNone(self.owner._consume_state)
        self.assertEqual(self.owner.close_calls,0)

    def test_19_unadmitted_public_bridge_retains_none(self):
        self.owner._phase='ADOPTED'
        code=compile('pass','<unused capture>','exec')
        bridge=self.call('new_import_bridge',self.owner,graph,GRAPH_RAW,lifecycle,LC_RAW,code,None)
        self.assertIsNone(bridge[2][0]['admission'])
        self.assertEqual(bridge[2][0]['phase'],'PREPARED')
        self.assertIsNone(self.owner._consume_state)

    def test_20_local_token_cannot_create_final_bundle(self):
        self.collect();code=compile('pass','<unused capture>','exec')
        with self.assertRaisesRegex(ValueError,'requires no P1 token'):
            self.call('make_project_bootstrap_bundle',self.plan,graph,GRAPH_RAW,lifecycle,LC_RAW,code,object())
        self.assertIsNone(self.owner._consume_state)
        self.assertEqual(self.plan._phase,'FAILED')

    def test_21_unadmitted_contract_does_not_claim_issuer(self):
        _,report=program.current()
        self.assertIs(report['P1_issuer_implemented'],False)
        self.assertEqual(report['operation'],'unadmitted_construction_bundle_only')

    def test_22_unadmitted_report_uses_same_final_certificate(self):
        held=self.bundle()
        self.owner._phase='OBSERVED'
        state=dict(owner=self.owner,creator=program.creator(),phase='BUNDLED',plan=self.plan,
            bundle=held,failure=None,graph=graph,graph_raw=GRAPH_RAW,lifecycle=lifecycle,
            lifecycle_raw=LC_RAW,capture_code=compile('pass','<unused>','exec'),admission=None)
        state['seal']=self.context['pin'](self.context['canonical'](self.context['bridge_image'](state)))
        report=self.context['import_bridge_event'](state,'report',self.owner,())
        self.assertEqual((report['source_modules'],report['loader_execs'],report['entry_execs']),(3,2,2))
        self.assertIs(report['admission_present'],False)
        self.assertEqual(report['P1_reads'],0)
        for name in program.FALSE_FIELDS:self.assertIs(report[name],False)
        self.assertIsNone(self.owner._consume_state)

    def test_14_bundle_detects_public_graph_function_metadata_drift(self):
        held=self.bundle();saved=graph.check.__code__
        def foreign(*args):return dict(structure_and_identity_stable=True)
        graph.check.__code__=foreign.__code__
        try:
            with self.assertRaises(ValueError):FunctionType(held[0],held[1])(held[2],None,'prepare',(),{})
        finally:graph.check.__code__=saved
        self.assertIsNone(self.owner._consume_state)

    def test_15_foreign_thread_exec_poison_is_retained_without_owner_claim(self):
        errors=[]
        def imported():
            try:importlib.import_module(self.dep_name)
            except BaseException as error:errors.append(error)
        _ACTIVE[0]=lambda event,args:self.call('observe_exec',self.plan,event,args)
        try:
            thread=Thread(target=imported);thread.start();thread.join(2)
            self.assertFalse(thread.is_alive())
        finally:_ACTIVE[0]=None
        self.assertEqual(len(errors),1);self.assertIs(self.plan._failure,errors[0])
        self.assertEqual(self.plan._phase,'FAILED');self.assertIsNone(self.owner._consume_state)


class GraphTypeTests(legacy.ProducerProjectGraphTests):
    """The frozen twelve behavioral tests also run against graph successor v2."""

    def test_13_fraction_and_regex_source_values_and_mutations(self):
        module=self.module('typed',b'from fractions import Fraction\nimport re\nZERO=Fraction(0)\nPATTERN=re.compile(\"a+\")\n')
        snapshot=self.capture();self.assertTrue(graph.check(snapshot)['structure_and_identity_stable'])
        object.__setattr__(module.ZERO,'_numerator',1)
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_14_typing_literals_and_protocol_class(self):
        module=self.module('typing',b'from typing import Literal,Protocol\nChoice=Literal[\"a\",\"b\"]\nclass Interface(Protocol):\n    def run(self):pass\n')
        snapshot=self.capture();self.assertTrue(graph.check(snapshot)['structure_and_identity_stable'])
        module.Interface.flag=True
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_15_ctypes_structure_fields_and_semantic_layout(self):
        module=self.module('ctypes',b'import ctypes\nclass Record(ctypes.Structure):\n    _fields_=[(\"value\",ctypes.c_int),(\"count\",ctypes.c_size_t)]\n')
        snapshot=self.capture();self.assertTrue(graph.check(snapshot)['structure_and_identity_stable'])
        rows=[row for row in snapshot._graph[1] if row[0]=='project_ctypes_class']
        self.assertEqual(len(rows),1);self.assertEqual([item[0] for item in rows[0][-1]],['value','count'])
        module.Record._fields_.reverse()
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_16_class_mapping_keys_enum_members_and_future_feature(self):
        module=self.module('keys',b'from __future__ import annotations\nfrom enum import Enum\nclass Kind(Enum):\n    A=\"a\"\nclass Box:pass\nTABLE={Box:(Kind.A,)}\nSET={Box,Kind.A}\n')
        snapshot=self.capture();self.assertTrue(graph.check(snapshot)['structure_and_identity_stable'])
        module.TABLE[module.Box]=(module.Kind.A,'changed')
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_17_custom_metaclass_still_rejected(self):
        self.module('custom',b'class Meta(type):pass\nclass Box(metaclass=Meta):pass\n')
        with self.assertRaises(ValueError):self.capture()

    def test_18_regex_content_change_is_rejected(self):
        module=self.module('regex',b'import re\nPATTERN=re.compile(\"a\")\n')
        snapshot=self.capture();module.PATTERN=__import__('re').compile('b')
        with self.assertRaises(ValueError):graph.check(snapshot)


class LifecycleAbortTests(unittest.TestCase):
    setUp=old_lifecycle.RetainedProducerTests.setUp
    make_module=old_lifecycle.RetainedProducerTests.make_module
    invoke=old_lifecycle.RetainedProducerTests.invoke
    run_producer=old_lifecycle.RetainedProducerTests.run_producer
    failure=old_lifecycle.RetainedProducerTests.failure

    def test_01_outer_bundle_failure_keeps_primary_and_closes_exactly_once(self):
        self.run_producer();primary=ValueError('construction changed')
        def verify(*args):raise PRIMARY
        context=dict(PRIMARY=primary,os=os,get_ident=get_ident,__builtins__=dict(vars(builtins)))
        state=(None,None,None,self.dispatch_spec,verify.__code__,context,None)
        outer=FunctionType(program.bundle_dispatch.__code__,dict(FunctionType=FunctionType,__builtins__=dict(vars(builtins))))
        failure=self.failure(lambda:outer(state,self.producer,'G2',(),{}))
        self.assertIs(failure.primary,primary);self.assertEqual(self.producer._phase,'UNRESOLVED')
        self.assertIn(('bootstrap_bundle',primary),failure.secondary)
        with self.assertRaises(type(failure)) as caught:outer(state,self.producer,'close',(),{})
        self.assertIs(caught.exception,failure);self.assertEqual(self.owner.close_calls,1)

    def test_02_abort_preserves_original_even_with_graph_function_drift(self):
        self.run_producer();self.graph._build=lambda:True;primary=LookupError('outer graph failure')
        self.assertIs(self.failure(lambda:self.invoke('bootstrap_abort',primary)).primary,primary)
