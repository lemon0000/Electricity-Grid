"""Namespace semantics with logical inputs; real query HANDLEs belong to cold probes."""
import copy
import builtins
import ast
import dis
import os
from pathlib import Path
import pickle
import sys
from threading import Thread,get_ident
from types import ModuleType,SimpleNamespace,FunctionType,CodeType
import unittest
from unittest import mock

ROOT=Path(__file__).absolute().parents[1]
HELPER=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v1.py'
ENTRY=ROOT/'experiments/staged_rts24_saved_fresh_adoption_v1.py'

class LogicalInputs:
    def __init__(self):self._phase='LIVE';self._resource=SimpleNamespace(pending=[1,2]);self.close_calls=0;self.audit_reads=False;self.audit_close=False
    def entry(self):
        if self._phase!='LIVE':raise ValueError('logical input closed')
        if self.audit_reads:
            with ENTRY.open('rb') as stream:stream.read(1)
        return self
    def source_bytes(self,name):self.entry();return ENTRY.read_bytes()
    def close(self):
        if self._phase!='CLOSED':
            if self.audit_close:sys.audit('electricity_grid.namespace.unit_close')
            self.close_calls+=1;self._resource.pending=[None,None];self._phase='CLOSED'

class EntryNamespaceTests(unittest.TestCase):
    def setUp(self):
        self.helper=ModuleType('_namespace_unit_helper');self.helper.__dict__.update(_INPUT_TYPE=LogicalInputs)
        exec(compile(HELPER.read_bytes(),str(HELPER),'exec',dont_inherit=True,optimize=0),vars(self.helper))
        self.inputs=LogicalInputs();self.owner=None;self.owned_aliases=[]
        self.entry=self.helper.LiveEntryNamespace.entry;self.close=self.helper.LiveEntryNamespace.close
        self.bindings=self.helper.capture_helper_bindings()
    def open(self):
        self.owner=self.helper.open_entry_namespace(self.inputs,self.bindings)
        self.owned_aliases.extend([(self.helper.ACTUAL_NAME,self.owner.module),(self.helper.REFERENCE_NAME,self.owner.reference)])
        return self.owner
    def tearDown(self):
        if self.owner is not None:
            try:self.close(self.owner)
            except BaseException:pass
        self.inputs.close()
        for name,module in self.owned_aliases:
            if sys.modules.get(name) is module:del sys.modules[name]
    def test_real_entry_initializes_dataclasses_and_live_same_inputs(self):
        owner=self.open();self.assertIs(owner._inputs,self.inputs);self.assertEqual(self.inputs.close_calls,0)
        self.assertIs(owner.module.require.__globals__,vars(owner.module))
        self.assertEqual(len(owner.module.EXPECTATION_FILES),53)
        self.assertTrue(owner.module.SavedSuccessorImportBoundary.__dataclass_fields__)
        self.assertIs(self.entry(owner),owner);self.assertGreater(len(owner._objects),100)
        self.close(owner);self.assertEqual(self.inputs.close_calls,1);self.assertNotIn(self.helper.ACTUAL_NAME,sys.modules)
    def test_same_raw_oracle_remains_frozen_after_both_namespaces_change(self):
        owner=self.open();replacement=lambda *a,**k:None
        owner.module.require=owner.reference.require=replacement
        with self.assertRaisesRegex(ValueError,'namespace graph changed'):self.entry(owner)
        with self.assertRaises(self.helper.NamespaceConstructionFailed):self.close(owner)
        self.assertEqual(owner._phase,'UNRESOLVED');self.assertEqual(self.inputs.close_calls,1)
    def test_equal_function_clone_fails_identity_bookend(self):
        owner=self.open();original=owner.module.require
        clone=FunctionType(original.__code__,vars(owner.module),original.__name__,original.__defaults__,original.__closure__)
        clone.__qualname__=original.__qualname__;clone.__annotations__=original.__annotations__.copy();clone.__dict__.update(original.__dict__)
        owner.module.require=clone
        with self.assertRaisesRegex(ValueError,'object identity changed'):self.entry(owner)
    def test_caught_restored_fault_cannot_reopen_namespace(self):
        owner=self.open();original=owner.module.require;owner.module.require=lambda:None
        with self.assertRaises(ValueError) as first:self.entry(owner)
        owner.module.require=original
        with self.assertRaises(ValueError) as second:self.entry(owner)
        self.assertIs(first.exception,second.exception)
        with self.assertRaises(self.helper.NamespaceConstructionFailed) as closed:self.close(owner)
        with self.assertRaises(self.helper.NamespaceConstructionFailed) as repeated:self.close(owner)
        self.assertIs(closed.exception,repeated.exception);self.assertEqual(self.inputs.close_calls,1)
    def test_foreign_alias_preserved_while_native_inputs_close(self):
        owner=self.open();foreign=ModuleType('foreign');sys.modules[self.helper.ACTUAL_NAME]=foreign
        self.owned_aliases.append((self.helper.ACTUAL_NAME,foreign))
        with self.assertRaisesRegex(ValueError,'namespace alias changed'):self.entry(owner)
        with self.assertRaises(self.helper.NamespaceConstructionFailed):self.close(owner)
        self.assertIs(sys.modules[self.helper.ACTUAL_NAME],foreign);self.assertFalse(any(self.inputs._resource.pending))
    def test_extra_alias_is_preserved_and_unresolved(self):
        owner=self.open();name='_extra_entry_alias_unit';sys.modules[name]=owner.module;self.owned_aliases.append((name,owner.module))
        with self.assertRaisesRegex(ValueError,'extra ENTRY namespace alias'):self.entry(owner)
        with self.assertRaises(self.helper.NamespaceConstructionFailed):self.close(owner)
        self.assertIs(sys.modules[name],owner.module);self.assertEqual(owner._phase,'UNRESOLVED')
    def test_reference_registration_never_overwrites_foreign(self):
        foreign=ModuleType('foreign_reference');active=[True]
        def audit(event,args):
            if active[0] and event=='electricity_grid.namespace.registered':sys.modules[self.helper.REFERENCE_NAME]=foreign
        sys.addaudithook(audit)
        try:
            with self.assertRaises(self.helper.NamespaceConstructionFailed) as caught:self.helper.open_entry_namespace(self.inputs,self.bindings)
            self.owner=caught.exception.owner;self.assertIn('alias occupied',str(caught.exception.primary))
            self.assertIs(sys.modules[self.helper.REFERENCE_NAME],foreign);self.assertEqual(self.inputs.close_calls,1)
            self.owned_aliases.extend([(self.helper.REFERENCE_NAME,foreign),(self.helper.ACTUAL_NAME,self.owner.module)])
        finally:active[0]=False
    def test_coherent_graph_helper_and_require_swap_rejected_before_call(self):
        owner=self.open();calls=[]
        with mock.patch.object(self.helper,'NamespaceGraph',lambda *a:calls.append('graph')),mock.patch.object(self.helper,'require',lambda *a:calls.append('require')):
            with self.assertRaisesRegex(ValueError,'namespace helper binding changed'):self.entry(owner)
            self.assertEqual(calls,[])
        with self.assertRaises(self.helper.NamespaceConstructionFailed):self.close(owner)
        self.assertEqual(self.inputs.close_calls,1)
    def test_class_method_and_ordinary_seal_rewrite_rejected(self):
        owner=self.open();calls=[]
        with mock.patch.object(self.helper.LiveEntryNamespace,'_metadata',lambda *a:calls.append('metadata')):
            with self.assertRaisesRegex(ValueError,'namespace helper binding changed'):self.entry(owner)
            for field,value in [('_expected',()),('_objects',()),('_seal',())]:
                with self.assertRaises(AttributeError):setattr(owner,field,value)
            self.assertEqual(calls,[])
    def test_new_global_builtin_shadow_rejected(self):
        owner=self.open()
        with mock.patch.dict(vars(self.helper),{'object':SimpleNamespace(__setattr__=lambda *a:None),'BaseException':None}):
            with self.assertRaisesRegex(ValueError,'namespace helper keys changed'):self.entry(owner)
            with self.assertRaises(self.helper.NamespaceConstructionFailed):self.close(owner)
        self.assertEqual(self.inputs.close_calls,1)
    def test_foreign_thread_rejected(self):
        owner=self.open();errors=[]
        def attempt():
            try:self.entry(owner)
            except BaseException as error:errors.append(error)
        thread=Thread(target=attempt);thread.start();thread.join()
        self.assertEqual(len(errors),1);self.assertIn('creator',str(errors[0]))
    def test_constructor_copy_and_pickle_closed(self):
        with self.assertRaises(TypeError):self.helper.LiveEntryNamespace()
        owner=self.open()
        for function in (copy.copy,copy.deepcopy,pickle.dumps):
            with self.assertRaises(TypeError):function(owner)
    def test_unknown_getter_is_not_executed(self):
        calls=[]
        class Evil:
            @property
            def __class__(self):calls.append('getter');raise AssertionError('not callable')
        module=ModuleType('graph_unknown');module.payload=Evil()
        with self.assertRaisesRegex(ValueError,'unsupported namespace value'):self.helper.NamespaceGraph(module).freeze()
        self.assertEqual(calls,[])
    def test_graph_depth_bound(self):
        module=ModuleType('graph_depth');value=[];module.payload=value
        for _ in range(300):child=[];value.append(child);value=child
        with self.assertRaisesRegex(ValueError,'depth cap'):self.helper.NamespaceGraph(module).freeze()
    def test_source_open_compile_and_graph_swap_never_called(self):
        active=[True];calls=[];original_compile=builtins.compile;original_graph=self.helper.NamespaceGraph
        def evil_compile(*args,**kwargs):calls.append('compile');builtins.compile=original_compile;return original_compile('forged=True','<evil>','exec')
        def audit(event,args):
            if active[0] and event=='open' and str(args[0])==str(ENTRY):
                active[0]=False;builtins.compile=evil_compile;self.helper.NamespaceGraph=lambda *a:calls.append('graph')
        sys.addaudithook(audit)
        try:
            with self.assertRaises(self.helper.NamespaceConstructionFailed) as caught:self.helper.open_entry_namespace(self.inputs,self.bindings)
            self.owner=caught.exception.owner
        finally:active[0]=False;builtins.compile=original_compile;self.helper.NamespaceGraph=original_graph
        self.assertEqual(calls,[]);self.assertEqual(self.inputs.close_calls,1);self.assertEqual(self.owner._phase,'UNRESOLVED')
    def test_input_open_metadata_graph_swap_never_called(self):
        owner=self.open();self.inputs.audit_reads=True;active=[True];calls=[]
        original_graph=self.helper.NamespaceGraph;original_metadata=self.helper.LiveEntryNamespace._metadata
        def audit(event,args):
            if active[0] and event=='open' and str(args[0])==str(ENTRY):
                active[0]=False;self.helper.NamespaceGraph=lambda *a:calls.append('graph')
                self.helper.LiveEntryNamespace._metadata=lambda *a:calls.append('metadata')
        sys.addaudithook(audit)
        try:
            with self.assertRaisesRegex(ValueError,'namespace helper binding changed'):self.entry(owner)
            with self.assertRaises(self.helper.NamespaceConstructionFailed):self.close(owner)
        finally:active[0]=False;self.helper.NamespaceGraph=original_graph;self.helper.LiveEntryNamespace._metadata=original_metadata
        self.assertEqual(calls,[]);self.assertEqual(self.inputs.close_calls,1)
    def test_first_input_open_cannot_redefine_expected_capture(self):
        self.inputs.audit_reads=True;active=[True];calls=[];original_capture=self.helper.capture_helper_bindings
        def audit(event,args):
            if active[0] and event=='open' and str(args[0])==str(ENTRY):
                active[0]=False;self.helper.capture_helper_bindings=lambda:calls.append('capture')
        sys.addaudithook(audit)
        try:
            with self.assertRaises(self.helper.NamespaceConstructionFailed) as caught:self.helper.open_entry_namespace(self.inputs,self.bindings)
            self.owner=caught.exception.owner
        finally:active[0]=False;self.helper.capture_helper_bindings=original_capture
        self.assertEqual(calls,[]);self.assertEqual(self.inputs.close_calls,1)
    def probe_validator(self):
        path=ROOT/'tests/staged_rts24_saved_fresh_entry_namespace_probe_v1.py';tree=ast.parse(path.read_bytes())
        node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='validate_held_namespace_helper')
        namespace=dict(CodeType=CodeType,FunctionType=FunctionType,os=os,sys=sys,get_ident=get_ident,require=self.helper.require,ROOT=ROOT,ENTRY=self.helper.ENTRY)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec',dont_inherit=True,optimize=0),namespace)
        unit=compile(HELPER.read_bytes(),str(HELPER),'exec',dont_inherit=True,optimize=0)
        return namespace['validate_held_namespace_helper'],unit
    def test_actual_probe_validator_accepts_helper_default_roots(self):
        validate,unit=self.probe_validator()
        validate(self.helper,unit,vars(builtins).copy(),LogicalInputs,compile,exec,type,vars)
    def test_actual_probe_validator_rejects_compile_default_replacement(self):
        validate,unit=self.probe_validator();fn=self.helper.open_entry_namespace;original=fn.__defaults__;calls=[]
        names=fn.__code__.co_varnames[fn.__code__.co_argcount-len(original):fn.__code__.co_argcount];values=list(original)
        values[names.index('_compile')]=lambda *a,**k:calls.append('evil_compile');fn.__defaults__=tuple(values)
        try:
            with self.assertRaisesRegex(ValueError,'held helper default differs: _compile'):
                validate(self.helper,unit,vars(builtins).copy(),LogicalInputs,compile,exec,type,vars)
        finally:fn.__defaults__=original
        self.assertEqual(calls,[])
    def test_graph_reader_has_no_global_loads_in_nested_code(self):
        def check(code):
            self.assertFalse([x.argval for x in dis.get_instructions(code) if x.opname in ('LOAD_GLOBAL','STORE_GLOBAL','DELETE_GLOBAL')])
            for value in code.co_consts:
                if type(value) is CodeType:check(value)
        check(self.helper.freeze_namespace_graph.__code__)
    def test_graph_observation_uses_held_reader_during_helper_changes(self):
        owner=self.open();owner.module.CAPS['files']+=1;steps=[0];calls=[]
        original_graph=self.helper.NamespaceGraph;original_require=self.helper.require
        def audit(event,args):
            if event=='object.__getattr__' and len(args)==2 and args[1]=='__code__' and type(args[0]) is FunctionType and args[0].__globals__ is vars(owner.module):
                if steps[0]==0:
                    steps[0]=1;self.helper.NamespaceGraph=lambda *a:calls.append('graph');self.helper.require=lambda *a:calls.append('require')
                elif steps[0]==1:
                    steps[0]=2;self.helper.NamespaceGraph=original_graph;self.helper.require=original_require
        sys.addaudithook(audit)
        try:
            with self.assertRaisesRegex(ValueError,'ENTRY namespace graph changed'):self.entry(owner)
        finally:steps[0]=3;self.helper.NamespaceGraph=original_graph;self.helper.require=original_require
        self.assertEqual(calls,[])
    def test_cleanup_post_bookend_preserves_failure_without_calling_new_bool(self):
        owner=self.open();self.inputs.audit_close=True;active=[True];calls=[]
        def audit(event,args):
            if active[0] and event=='electricity_grid.namespace.unit_close':
                active[0]=False;self.helper.bool=lambda *a:calls.append('bool')
        sys.addaudithook(audit)
        try:
            with self.assertRaises(self.helper.NamespaceConstructionFailed) as first:self.close(owner)
            with self.assertRaises(self.helper.NamespaceConstructionFailed) as second:self.close(owner)
            self.assertIs(first.exception,second.exception)
        finally:
            active[0]=False
            if 'bool' in vars(self.helper):del self.helper.bool
        self.assertEqual(calls,[]);self.assertEqual(self.inputs.close_calls,1);self.assertEqual(owner._phase,'UNRESOLVED')
    def test_graph_keeps_module_name_literals_exact(self):
        module=ModuleType(self.helper.ACTUAL_NAME);module.payload=self.helper.ACTUAL_NAME
        original,_=self.helper.NamespaceGraph(module).freeze();module.payload='<ENTRY_MODULE>'
        changed,_=self.helper.NamespaceGraph(module).freeze();self.assertNotEqual(original,changed)

if __name__=='__main__':unittest.main()
