"""Diagnostic wrapper equivalence; no native resource, model or adapter."""
import ast
import builtins
import contextlib
import dis
import importlib.util
import io
import json
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType,FunctionType,ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
OLD=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v8.py'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
class GraphTimingTests(unittest.TestCase):
    def setUp(self):self.old=load(OLD,'_graph_original');self.new=load(NEW,'_graph_timing')
    def invoke(self,module,writer=None):
        sink=io.BytesIO();times=iter((1.0,2.0));write=sink.write if writer is None else writer
        result=self.new.timed_namespace_graph(module,_clock=lambda:next(times),_write=write,_flush=lambda:None)
        return result,sink.getvalue()
    def test_original_reader_ast_positions_and_code_except_filename_are_equal(self):
        def node(path):return next(n for n in ast.parse(path.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='freeze_namespace_graph')
        self.assertEqual(ast.dump(node(OLD),include_attributes=True),ast.dump(node(NEW),include_attributes=True))
        def normalize(code):
            return code.replace(co_filename=str(OLD),co_consts=tuple(normalize(v) if type(v) is CodeType else v for v in code.co_consts))
        self.assertEqual(self.old.freeze_namespace_graph.__code__,normalize(self.new.freeze_namespace_graph.__code__))
    def test_wrapper_preserves_image_objects_and_exact_frames(self):
        module=ModuleType('_timing_input');module.values={'x':[1,2]};module.code=compile('a=1','<input>','exec')
        expected,original=self.old.freeze_namespace_graph(module);(actual,objects),raw=self.invoke(module)
        self.assertEqual(actual,expected);self.assertEqual(len(objects),len(original));self.assertTrue(all(a is b for a,b in zip(objects,original)))
        self.assertEqual([json.loads(line) for line in raw.splitlines()],[['enter',1.0],['exit',2.0]])
    def test_exception_emits_exit_and_output_failure_keeps_primary(self):
        sink=io.BytesIO();times=iter((1.0,2.0))
        with self.assertRaisesRegex(ValueError,'exact ENTRY module required'):
            self.new.timed_namespace_graph(object(),_clock=lambda:next(times),_write=sink.write,_flush=lambda:None)
        self.assertEqual(len(sink.getvalue().splitlines()),2)
        calls=[0];secondary=OSError('diagnostic pipe failed');times=iter((1.0,2.0))
        def write(raw):
            calls[0]+=1
            if calls[0]==2:raise secondary
        with self.assertRaisesRegex(ValueError,'exact ENTRY module required') as caught:
            self.new.timed_namespace_graph(object(),_clock=lambda:next(times),_write=write,_flush=lambda:None)
        self.assertIs(caught.exception.__cause__,secondary)
    def test_actual_validator_accepts_held_wrapper_roots(self):
        tree=ast.parse(PROBE.read_bytes());fn=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='validate_held_namespace_helper')
        import os
        context=dict(ROOT=ROOT,ENTRY=self.new.ENTRY,CodeType=CodeType,FunctionType=FunctionType,os=os,sys=sys,get_ident=get_ident,require=self.new.require)
        exec(compile(ast.Module(body=[fn],type_ignores=[]),str(PROBE),'exec',dont_inherit=True,optimize=0),context)
        context['validate_held_namespace_helper'](self.new,compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0),vars(builtins).copy(),None,None,compile,exec,type,vars)
        self.assertIs(self.new._TRACE_WRITE.__self__,sys.stderr.buffer)
        self.assertEqual(self.new._TRACE_WRITE.__name__,'write')
    def test_actual_entry_alias_and_cleanup_keep_original_graph(self):
        class Inputs:
            def __init__(self):self._resource=SimpleNamespace(pending=[1,2]);self.close_calls=0
            def entry(self):return self
            def source_bytes(self,name):return (ROOT/name).read_bytes()
            def close(self):self.close_calls+=1;self._resource.pending=[None,None]
        sink=io.BytesIO();stdio=io.TextIOWrapper(sink,encoding='utf-8',write_through=True);owner=None
        with contextlib.redirect_stderr(stdio):
            helper=ModuleType('_timed_entry');vars(helper).update(_INPUT_TYPE=Inputs)
            exec(compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0),vars(helper))
            inputs=Inputs()
            try:
                owner=helper.open_entry_namespace(inputs,helper.capture_helper_bindings())
                image,objects=self.old.freeze_namespace_graph(owner.module)
                self.assertEqual(image,owner._expected);self.assertEqual(len(objects),len(owner._objects));self.assertTrue(all(a is b for a,b in zip(objects,owner._objects)))
            finally:
                if owner is not None:helper.LiveEntryNamespace.close(owner)
            self.assertEqual(inputs.close_calls,1);self.assertNotIn(helper.ACTUAL_NAME,sys.modules)
            frames=[json.loads(line) for line in sink.getvalue().splitlines()];self.assertGreaterEqual(len(frames),6)
            self.assertEqual([row[0] for row in frames],['enter','exit']*(len(frames)//2))
    def test_reader_wrapper_and_nested_code_have_zero_global_opcodes(self):
        def check(code):
            self.assertFalse([v for v in dis.get_instructions(code) if v.opname in ('LOAD_GLOBAL','STORE_GLOBAL','DELETE_GLOBAL')])
            for value in code.co_consts:
                if type(value) is CodeType:check(value)
        check(self.new.freeze_namespace_graph.__code__);check(self.new.timed_namespace_graph.__code__)
if __name__=='__main__':unittest.main()
