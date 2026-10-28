"""Logical lifecycle/state oracle; no Source49 target module, P1 or native runs."""
import ast
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
from threading import Thread,get_ident
from types import FunctionType,ModuleType,SimpleNamespace
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]
PROGRAM=ROOT/'experiments/staged_rts24_saved_fresh_retained_producer_v1.py'
RAW=PROGRAM.read_bytes()
spec=importlib.util.spec_from_file_location('_retained_under_test',PROGRAM)
engine=importlib.util.module_from_spec(spec);spec.loader.exec_module(engine)
REG=json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_producer_project_graph_v1_non_authoritative/registration.json').read_bytes())
SOURCE_PINS=REG['graph_contract']['source_contract']['source_pins']
SOURCE_RAW={name:(ROOT/name).read_bytes() for name in SOURCE_PINS}
# The logical inventory has the original cardinality/bytes, with synthetic names
# and content. It is never passed off as P1 or a Source49 initial-state oracle.
INPUT_RAW={str(index):b'x'*(2950863-682 if index==0 else 1) for index in range(683)}
FILES={name:dict(bytes=len(raw),sha256=sha256(raw).hexdigest()) for name,raw in INPUT_RAW.items()}

CORE_RAW=b'''
from types import FunctionType
class LocalRuntimeUnresolved(RuntimeError):
    def __init__(self,owner,primary,secondary):
        self.owner=owner;self.primary=primary;self.secondary=secondary
def runtime_seal(owner,phase=None):
    return owner._consume_state,owner._phase,id(owner._namespace),id(owner._adapter)
def check_bindings():pass
def boundary_phase(boundary):return boundary.phase
class LocalRuntimeInputs:
    def entry(self,_c=runtime_seal.__code__,_f=FunctionType,_g=globals(),_d=runtime_seal.__defaults__,
            _b=check_bindings.__code__,_bd=check_bindings.__defaults__,_e=ValueError):
        if self._phase!='LIVE' or self._seal!=_f(_c,_g,'fixed_seal',_d)(self):
            raise _e('logical owner seal changed')
        return self
    def source_bookend(self):
        self.source_calls+=1
        if self.source_error is not None:raise self.source_error
        return self.expected
    def close(self,primary=None):
        self.close_calls+=1
        if self.close_callback is not None:self.close_callback()
        if self.close_error is not None:raise self.close_error
        self._resource.phase='CLOSED';self._boundary.phase='CLOSED';self._namespace._phase='CLOSED'
        self._phase='UNRESOLVED' if primary is not None else 'CLOSED'
        if primary is not None:raise LocalRuntimeUnresolved(self,primary,())
'''
GRAPH_RAW=b'''
class ProducerProjectSnapshot:pass
def _build():return True
def canonical(value):return value
def check(snapshot):
    if not _build():raise ValueError('logical graph changed')
    return dict(structure_and_identity_stable=True)
'''
ENTRY_RAW=b'''
import json
class SavedCallerExpectation:
    def entry(self):
        if STATE.get('expectation_error') is not None:raise STATE['expectation_error']
        if self.raw!=STATE['expectation_raw']:raise ValueError('logical expectation changed')
        return self
def capture_saved_expectation_prebound(source,binding):
    STATE['capture_calls']+=1
    callback=STATE.get('capture_callback')
    if callback is not None:callback()
    if STATE.get('capture_error') is not None:raise STATE['capture_error']
    return STATE['expectation']
def context_from_saved_expectation(expectation,output_root,*,started):
    STATE['context_calls']+=1
    if STATE.get('context_error') is not None:raise STATE['context_error']
    return STATE['context']
def check_expectation_context(raw,digest):
    if STATE.get('check_error') is not None:raise STATE['check_error']
    if STATE['hash'](raw).hexdigest()!=digest:raise ValueError('logical context digest changed')
    return json.loads(raw)
def _expectation_binding_entry(binding):return binding
'''
ADAPTER_RAW=b'''
class HeldInput:pass
def hold(source,expected_image):
    STATE['hold_calls']+=1
    callback=STATE.get('hold_callback')
    if callback is not None:callback()
    if STATE.get('hold_error') is not None:raise STATE['hold_error']
    if expected_image!=STATE['expected_image']:raise ValueError('external image differs')
    return STATE['held']
def caller_image(held):
    return STATE['canonical'](dict(source_pins=held.source_pins,input_files=held.files))
def bookend(held):
    STATE['bookend_calls']+=1
    if STATE.get('bookend_error') is not None:raise STATE['bookend_error']
    callback=STATE.get('bookend_callback')
    if callback is not None:callback()
'''


class RetainedProducerTests(unittest.TestCase):
    def setUp(self):
        self.state=dict(capture_calls=0,context_calls=0,hold_calls=0,bookend_calls=0,hash=sha256,canonical=engine.canonical)
        self.modules={}
        for name in SOURCE_RAW:
            if name.startswith('src/') and name.endswith('.py') or name==engine.ENTRY:
                module_name=name[:-3].replace('/','.').removesuffix('.__init__')
                module=ModuleType(module_name);module.__file__=str(ROOT/name);self.modules[module_name]=module
        scope=patch.dict(sys.modules,self.modules);scope.start();self.addCleanup(scope.stop)
        self.module=self.modules[engine.ENTRY[:-3].replace('/','.')]
        self.adapter=self.modules[engine.ADAPTER[:-3].replace('/','.')]
        for module,raw in ((self.module,ENTRY_RAW),(self.adapter,ADAPTER_RAW)):
            vars(module)['STATE']=self.state
            exec(compile(raw,module.__file__,'exec',dont_inherit=True,optimize=0),vars(module),vars(module))
        self.core=self.make_module('_logical_retained_core',CORE_RAW)
        self.graph=self.make_module('_logical_retained_graph',GRAPH_RAW)
        self.owner=self.core.LocalRuntimeInputs()
        self.owner.__dict__.update(_creator=(os.getpid(),get_ident()),_phase='LIVE',_consume_state='PREPARED',
            _import_profile_matched=True,_adapter=self.adapter,_sources=tuple(SOURCE_RAW.items()),expected=SOURCE_PINS,
            _namespace=SimpleNamespace(module=self.module,_phase='LIVE'),_resource=SimpleNamespace(phase='LIVE',pending=(False,False)),
            _boundary=SimpleNamespace(phase='LIVE'),source_calls=0,source_error=None,close_calls=0,close_error=None,close_callback=None)
        self.owner._boundary_phase=(FunctionType,self.core.boundary_phase.__code__,vars(self.core),None)
        self.owner._seal=self.core.runtime_seal(self.owner)
        binding=(self.adapter,())
        self.owner._consumer_plan=(self.owner,self.owner._creator,self.owner._namespace,self.owner._boundary,self.adapter,None,
            ROOT,(),binding,(),(), 'expectation_binding',b'logical')
        snapshot=self.graph.ProducerProjectSnapshot()
        snapshot._modules=tuple(self.modules.items());snapshot._registry=sys.modules
        snapshot._sources=tuple((name,(module.__file__[len(str(ROOT))+1:].replace('\\','/'),
            SOURCE_RAW[module.__file__[len(str(ROOT))+1:].replace('\\','/')])) for name,module in self.modules.items())
        self.token=object()
        injected=dict(_RUNTIME_TYPE=self.core.LocalRuntimeInputs,_P1_AUTHORITY=self.token,_ADMITTED_OWNER=self.owner,
            _CAPTURE_CODE=self.module.capture_saved_expectation_prebound.__code__,_GRAPH_MODULE=self.graph,_PROJECT_SNAPSHOT=snapshot)
        self.dispatch_spec=engine.source_dispatch(RAW,injected,GRAPH_RAW)
        self.context,self.guard,_,_=self.dispatch_spec[2]
        self.call=FunctionType(self.dispatch_spec[0],self.dispatch_spec[1])
        context=self.context
        producer=object.__new__(context['RetainedProducer'])
        # A private logical plan is assembled for ordinary body tests. Public
        # prepare still rejects these synthetic functions against Source49.
        rows=tuple(context['function_row'](vars(self.module),name) for name in
            ('context_from_saved_expectation','check_expectation_context','_expectation_binding_entry'))
        rows+=tuple(context['function_row'](vars(self.adapter),name) for name in ('hold','bookend','caller_image'))
        values=dict(_owner=self.owner,_consumer_plan=self.owner._consumer_plan,_binding=binding,_adapter=self.adapter,_module=self.module,
            _roots=rows,_source=SOURCE_PINS,_capture=FunctionType(injected['_CAPTURE_CODE'],vars(self.module)),
            _creator=self.owner._creator,_brand=context['_BRAND'],_authority=self.token,_claimed=False,
            _phase='PREPARED',_busy=False,_close_attempted=False,_failure=None,_expectation=None,_context=None,_context_sha=None,
            _held=None,_snapshot=snapshot,_evidence=[],_operation_lock=engine.Lock(),_operation_owner=None,_pending_reentry=None)
        for name,value in values.items():object.__setattr__(producer,name,value)
        context['_LOCKS'][id(producer)]=(producer,producer._operation_lock)
        context['commit'](producer);context['reserve_state'](self.owner,'RUNNING',producer);context['commit'](producer)
        self.producer=producer
        expected_image=engine.canonical(dict(source_pins=SOURCE_PINS,input_files=FILES))
        expectation=self.module.SavedCallerExpectation();expectation.image=expected_image
        expectation.raw=engine.canonical(dict(caller_expectation_core=json.loads(expected_image),synthetic=True))
        held=self.adapter.HeldInput();held.image=expected_image;held.files=dict(FILES);held.source_pins=SOURCE_PINS
        held.inventory=dict(raw=dict(INPUT_RAW))
        self.state.update(expectation=expectation,expectation_raw=expectation.raw,expected_image=expected_image,held=held,
            context=engine.canonical(dict(expectation_sha=sha256(expectation.raw).hexdigest(),
                caller_expectation_core=json.loads(expected_image),source_pins=SOURCE_PINS,input_files=FILES)))

    def make_module(self,name,raw):
        module=ModuleType(name);module.__file__=str(ROOT/('tests/'+name+'.py'))
        exec(compile(raw,module.__file__,'exec',dont_inherit=True,optimize=0),vars(module),vars(module))
        return module

    def invoke(self,operation,*args,**kwargs):
        return self.call(self.dispatch_spec[2],self.producer,operation,args,kwargs)

    def run_producer(self):return self.invoke('run',ROOT/'results/tables/synthetic_not_written',started='logical')

    def failure(self,operation):
        with self.assertRaises(self.context['RetainedProducerFailure']) as caught:operation()
        failure=caught.exception
        self.assertIs(self.producer._failure,failure);self.assertIsNotNone(failure._seal)
        self.assertEqual(self.owner.close_calls,1);self.assertFalse(self.producer._operation_lock.locked())
        return failure

    def test_01_ordered_same_objects_and_closed_release(self):
        expected=('PREPARED','HELD','G2','G3','CLOSED');observed=[self.producer._phase]
        self.assertIs(self.run_producer(),self.producer);observed.append(self.producer._phase)
        held=self.producer._held;expectation=self.producer._expectation;binding=self.producer._binding
        for stage in ('G2','G3'):
            self.assertIs(self.invoke(stage),self.producer);observed.append(self.producer._phase)
            self.assertIs(self.producer._held,held);self.assertIs(self.producer._expectation,expectation);self.assertIs(self.producer._binding,binding)
        report=self.invoke('close');observed.append(self.producer._phase)
        self.assertEqual(tuple(observed),expected);self.assertEqual(self.owner._consume_state,'CONSUMED')
        self.assertEqual((self.state['capture_calls'],self.state['hold_calls'],self.state['bookend_calls']),(1,1,2))
        for field in ('_owner','_binding','_adapter','_module','_capture','_held','_context','_snapshot','_source','_authority'):
            self.assertIsNone(getattr(self.producer,field))
        self.assertEqual([row['stage'] for row in report['stages']],['G0','G2','G3'])
        self.assertEqual(self.owner.close_calls,1)
        for name in engine.FALSE_FIELDS:self.assertIs(report[name],False)
        report['stages'][0]['stage']='changed'
        self.assertEqual(self.invoke('close')['stages'][0]['stage'],'G0')

    def test_02_exact_capture_code_identity_and_external_image(self):
        self.context['entry'](self.producer)
        self.assertIs(self.producer._capture.__code__,self.context['_CAPTURE_CODE'])
        self.run_producer();self.assertEqual(self.producer._held.image,self.producer._expectation.image)

    def test_03_partial_capture_failure_keeps_original_and_sticky_carrier(self):
        primary=LookupError('capture');self.state['capture_error']=primary
        failure=self.failure(self.run_producer)
        self.assertIs(failure.primary,primary);self.assertIs(failure.runtime_close.primary,primary)
        self.assertEqual(failure.secondary,());self.assertEqual(self.producer._phase,'FAILED')
        for operation in ('run','G2','G3','close'):
            with self.assertRaises(type(failure)) as caught:self.invoke(operation)
            self.assertIs(caught.exception,failure)
        self.assertEqual(self.state['hold_calls'],0)

    def test_04_partial_context_and_hold_failure_table(self):
        # Independent stage oracle: context error prevents hold; hold error occurs
        # only after one external expectation and context.
        primary=RuntimeError('context');self.state['context_error']=primary
        failure=self.failure(self.run_producer)
        self.assertIs(failure.primary,primary);self.assertEqual((self.state['capture_calls'],self.state['context_calls'],self.state['hold_calls']),(1,1,0))

    def test_05_hold_failure_after_context(self):
        primary=OSError('hold');self.state['hold_error']=primary
        self.assertIs(self.failure(self.run_producer).primary,primary)
        self.assertEqual((self.state['capture_calls'],self.state['context_calls'],self.state['hold_calls']),(1,1,1))

    def test_06_primary_and_independent_final_and_close_errors(self):
        primary=LookupError('hold');final=ArithmeticError('context final');close=OSError('close')
        self.state['hold_error']=primary;self.owner.close_error=close
        self.state['hold_callback']=lambda:self.state.update(check_error=final)
        failure=self.failure(self.run_producer)
        self.assertIs(failure.primary,primary)
        self.assertIn(('context_final',final),failure.secondary)
        self.assertIn(('runtime_close',close),failure.secondary)
        self.assertEqual(self.producer._phase,'UNRESOLVED')
        self.assertEqual(self.owner._consume_state,'FAILED')

    def test_07_full_raw_map_rejects_content_tamper(self):
        self.state['held'].inventory['raw']['682']=b'y'
        failure=self.failure(self.run_producer)
        self.assertIn('retained raw content changed',str(failure.primary));self.assertEqual(self.state['bookend_calls'],0)

    def test_08_context_join_rejects_recomputed_wrong_expectation(self):
        context=json.loads(self.state['context']);context['expectation_sha']='0'*64
        self.state['context']=engine.canonical(context)
        self.assertIn('join differs',str(self.failure(self.run_producer).primary))

    def test_09_out_of_order_and_no_evidence_after_failure(self):
        failure=self.failure(lambda:self.invoke('G3'))
        self.assertIn('ordered',str(failure.primary));self.assertEqual(self.producer._evidence,[])
        self.assertEqual(self.owner._consume_state,'FAILED')

    def test_10_swallowed_reentry_aborts_before_success(self):
        pending=[]
        def callback():
            try:self.invoke('G2')
            except ValueError as error:pending.append(error)
        self.state['capture_callback']=callback
        failure=self.failure(self.run_producer)
        self.assertEqual(len(pending),1);self.assertIs(failure.primary,pending[0])
        self.assertEqual(self.producer._evidence,[]);self.assertEqual(self.state['hold_calls'],0)

    def test_11_foreign_thread_rejects_without_mutation_or_cleanup(self):
        before=self.producer._seal;errors=[]
        def callback():
            try:self.invoke('close')
            except BaseException as error:errors.append(error)
        thread=Thread(target=callback);thread.start();thread.join(2)
        self.assertFalse(thread.is_alive());self.assertEqual(len(errors),1)
        self.assertIsNone(self.producer._failure);self.assertEqual(self.producer._seal,before);self.assertEqual(self.owner.close_calls,0)
        self.run_producer();self.invoke('G2');self.invoke('G3');self.invoke('close')

    def test_12_helper_and_graph_drift_use_held_cleanup(self):
        # The helper namespace is observed; private execution globals were
        # captured before this replacement.
        witnesses=self.guard[2][0]
        namespace=witnesses[0][0];namespace['operate']=lambda *args,**kwargs:None
        failure=self.failure(self.run_producer)
        self.assertIn('helper',str(failure.primary));self.assertEqual(self.state['capture_calls'],0)

    def test_13_graph_hidden_build_drift_rejected(self):
        self.graph._build=lambda:True
        failure=self.failure(self.run_producer)
        self.assertIn('helper',str(failure.primary));self.assertEqual(self.state['capture_calls'],0)

    def test_14_owner_slot_exclusive_and_same_plan_cannot_claim_twice(self):
        other=object.__new__(self.context['RetainedProducer'])
        object.__setattr__(other,'_owner',self.owner)
        with self.assertRaises(ValueError):self.context['reserve_state'](self.owner,'RUNNING',other)
        self.assertEqual(self.owner._consume_state,'RUNNING');self.assertEqual(self.owner.close_calls,0)
        self.run_producer();self.invoke('G2');self.invoke('G3');self.invoke('close')

    def test_15_failure_evidence_is_frozen_and_tamper_detected(self):
        self.state['capture_error']=RuntimeError('original');failure=self.failure(self.run_producer)
        for name in ('primary','secondary','producer','runtime_close','_seal'):
            with self.assertRaises(AttributeError):setattr(failure,name,None)
        object.__setattr__(failure,'secondary',(('tampered',RuntimeError('new')),))
        with self.assertRaises(ValueError):self.invoke('close')
        self.assertEqual(self.owner.close_calls,1)

    def test_16_public_prepare_cannot_admit_synthetic_source(self):
        self.owner._consume_state='PREPARED';self.owner._seal=self.core.runtime_seal(self.owner)
        with self.assertRaises(ValueError):
            self.call(self.dispatch_spec[2],None,'prepare',(self.owner,self.token),{})
        self.assertEqual(self.state['capture_calls'],0);self.assertEqual(self.state['hold_calls'],0)
        self.assertEqual(self.owner.close_calls,0)
        with self.assertRaises(ValueError):engine.prepare(self.owner,self.token)

    def test_17_terminal_reentry_is_unresolved_and_never_reports_success(self):
        self.run_producer();self.invoke('G2');self.invoke('G3')
        pending=[]
        def callback():
            try:self.invoke('close')
            except ValueError as error:pending.append(error)
        self.owner.close_callback=callback
        failure=self.failure(lambda:self.invoke('close'))
        self.assertIs(failure.primary,pending[0]);self.assertEqual(self.producer._phase,'UNRESOLVED')
        with self.assertRaises(type(failure)) as caught:self.invoke('close')
        self.assertIs(caught.exception,failure);self.assertEqual(self.owner.close_calls,1)

    def test_18_source_oracle_and_false_contract(self):
        # Independent AST enumeration of the program roots, without calling the
        # production manifest builder or importing any Source49 target.
        _,contract=engine.current();tree=ast.parse(RAW)
        expected=[node.name for node in tree.body if type(node) in (ast.FunctionDef,ast.ClassDef)]
        self.assertEqual(contract['roots'],expected)
        self.assertEqual(contract['P1_reads'],0);self.assertEqual(len(SOURCE_RAW),49);self.assertEqual(len(self.modules),37)
        for name,raw in SOURCE_RAW.items():self.assertEqual(dict(bytes=len(raw),sha256=sha256(raw).hexdigest()),SOURCE_PINS[name])
        for name in engine.FALSE_FIELDS:self.assertIs(contract[name],False)

    def test_19_full_raw_map_rejects_missing_member(self):
        del self.state['held'].inventory['raw']['682']
        self.assertIn('full retained raw map required',str(self.failure(self.run_producer).primary))

    def test_20_bookend_failure_preserves_same_held_and_prior_stage(self):
        self.run_producer();held=self.producer._held
        primary=OSError('G2 bookend');self.state['bookend_error']=primary
        self.assertIs(self.failure(lambda:self.invoke('G2')).primary,primary)
        self.assertIs(self.producer._held,held);self.assertEqual([row['stage'] for row in self.producer._evidence],['G0'])

    def test_21_equal_recompiled_capture_code_is_rejected_by_identity(self):
        original=self.producer._capture
        equal_code=compile(ENTRY_RAW,self.module.__file__,'exec',dont_inherit=True,optimize=0)
        code=next(code for code in equal_code.co_consts if hasattr(code,'co_name') and code.co_name=='capture_saved_expectation_prebound')
        self.assertEqual(code,original.__code__);self.assertIsNot(code,original.__code__)
        original.__code__=code
        self.assertIn('private capture function changed',str(self.failure(self.run_producer).primary))

    def test_22_public_guard_replacement_cannot_bypass_held_verifier(self):
        namespace=self.guard[2][0][0][0]
        namespace['_GUARD']=lambda:None
        self.graph._build=lambda:True
        failure=self.failure(self.run_producer)
        self.assertIn('helper',str(failure.primary));self.assertEqual(self.state['capture_calls'],0)

    def test_23_fake_lock_is_rejected_before_any_callback_or_cleanup(self):
        calls=[]
        class FakeLock:
            def acquire(self,*args):calls.append('acquire');return True
            def release(self):calls.append('release')
        original=self.producer._operation_lock
        object.__setattr__(self.producer,'_operation_lock',FakeLock())
        with self.assertRaises(ValueError):self.run_producer()
        self.assertEqual(calls,[]);self.assertEqual(self.owner.close_calls,0);self.assertIsNone(self.producer._failure)
        object.__setattr__(self.producer,'_operation_lock',original)

    def terminal_fault(self,name,label):
        primary=LookupError('capture');fault=ArithmeticError(label)
        self.state['capture_error']=primary
        def broken(*args):raise fault
        self.context[name]=broken
        failure=self.failure(self.run_producer)
        self.assertIs(failure.primary,primary);self.assertIn((label,fault),failure.secondary)
        self.assertEqual(self.producer._phase,'UNRESOLVED')
        with self.assertRaises(type(failure)) as caught:self.invoke('close')
        self.assertIs(caught.exception,failure);self.assertEqual(self.owner.close_calls,1)

    def test_24_terminal_reset_failure_preserves_primary_and_sticky_record(self):
        self.terminal_fault('_terminal_reset','terminal_reset')

    def test_25_failure_seal_failure_preserves_primary_and_sticky_record(self):
        self.terminal_fault('_terminal_seal','failure_seal')

    def test_26_final_publish_failure_preserves_primary_and_sticky_record(self):
        self.terminal_fault('_terminal_publish','failure_publish')

    def test_27_success_teardown_fault_becomes_sticky_unresolved_failure(self):
        error=ArithmeticError('success reset')
        def broken(*args):raise error
        self.context['_terminal_reset']=broken
        failure=self.failure(self.run_producer)
        self.assertIs(failure.primary,error);self.assertIn(('operation_owner_reset',error),failure.secondary)
        self.assertEqual(self.producer._phase,'UNRESOLVED')

    def test_28_runtime_close_binding_drift_still_runs_held_original_close(self):
        self.core.LocalRuntimeInputs.close=lambda *args:None
        failure=self.failure(self.run_producer)
        self.assertIn('runtime dispatch changed',str(failure.primary))
        self.assertEqual(self.owner._resource.phase,'CLOSED');self.assertEqual(self.producer._phase,'UNRESOLVED')

    def close_mutation(self,callback):
        self.run_producer();self.invoke('G2');self.invoke('G3')
        self.owner.close_callback=callback
        failure=self.failure(lambda:self.invoke('close'))
        self.assertIn('retained data changed during close',str(failure.primary))
        self.assertEqual(self.producer._phase,'UNRESOLVED')
        self.assertIs(self.producer._owner,self.owner);self.assertIs(self.producer._held,self.state['held'])
        with self.assertRaises(type(failure)) as caught:self.invoke('close')
        self.assertIs(caught.exception,failure);self.assertEqual(self.owner.close_calls,1)

    def test_29_close_callback_raw_mutation_is_sticky_unresolved(self):
        self.close_mutation(lambda:self.state['held'].inventory['raw'].__setitem__('0',b'changed'))

    def test_30_close_reset_failure_retains_original_refs_for_evidence(self):
        self.run_producer();self.invoke('G2');self.invoke('G3')
        original=(self.producer._owner,self.producer._binding,self.producer._expectation,self.producer._held)
        error=ArithmeticError('close reset')
        def broken(*args):raise error
        self.context['_terminal_reset']=broken
        failure=self.failure(lambda:self.invoke('close'))
        self.assertIs(failure.primary,error);self.assertEqual(self.producer._phase,'UNRESOLVED')
        self.assertTrue(all(a is b for a,b in zip(original,
            (self.producer._owner,self.producer._binding,self.producer._expectation,self.producer._held))))
        with self.assertRaises(type(failure)) as caught:self.invoke('close')
        self.assertIs(caught.exception,failure);self.assertEqual(self.owner.close_calls,1)

    def test_31_close_callback_expectation_mutation_is_sticky_unresolved(self):
        self.close_mutation(lambda:setattr(self.state['expectation'],'raw',b'changed'))
