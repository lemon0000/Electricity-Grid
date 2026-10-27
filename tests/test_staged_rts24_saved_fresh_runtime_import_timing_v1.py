"""Single-import diagnostic control and mixed stderr, without importing an adapter."""
import ast
import builtins
import io
import importlib.util
import json
from pathlib import Path
from types import CodeType,FunctionType,ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
BS=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_timing_v1.py'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_v3.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v9.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v9.py'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v12.py','_import_timing_core')
class ImportTimingTests(unittest.TestCase):
    def setUp(self):
        self.bs=ModuleType('_import_timing_helper');vars(self.bs).update(_READ_FILE=core.read_file,__file__=str(BS))
        exec(compile(BS.read_bytes(),str(BS),'exec',dont_inherit=True,optimize=0),vars(self.bs))
    def runtime(self,write=None):
        sink=io.BytesIO();writer=sink.write if write is None else write
        if write is not None:write.__self__=sink
        clock=iter((1.0,2.0,3.0,4.0));defs=(None,None,None,None,lambda:next(clock),writer,sink.flush,json.dumps)
        return SimpleNamespace(_namespace=SimpleNamespace(_graph_plan=(None,None,None,defs))),sink
    def test_original_guard_classes_and_non_loader_functions_are_unchanged(self):
        def nodes(path):return {n.name:n for n in ast.parse(path.read_bytes()).body if type(n) in (ast.ClassDef,ast.FunctionDef)}
        old=nodes(OLD);new=nodes(BS)
        for name,node in old.items():
            if name!='load_bootstrap_adapter':self.assertEqual(ast.dump(node),ast.dump(new[name]),name)
        loader=new['load_bootstrap_adapter'];calls=[n for n in ast.walk(loader) if type(n) is ast.Call and type(n.func) is ast.Name and n.func.id=='diagnostic_import_once']
        self.assertEqual(len(calls),1)
        single=new['diagnostic_import_once'];names=[n.func.id for n in ast.walk(single) if type(n) is ast.Call and type(n.func) is ast.Name]
        self.assertEqual(names.count('_arm'),1);self.assertEqual(names.count('_importer'),1);self.assertEqual(names.count('_cancel'),1)
        block=next(n for n in single.body if type(n) is ast.Try)
        self.assertTrue(any(type(n) is ast.Call and type(n.func) is ast.Name and n.func.id=='_cancel' for statement in block.finalbody for n in ast.walk(statement)))
    def test_single_import_primary_and_cleanup_order(self):
        runtime,sink=self.runtime();events=[];result=object()
        def arm(*args,**kwargs):events.append('arm');self.assertEqual(args,(2,));self.assertIs(kwargs['repeat'],False)
        def cancel():events.append('cancel')
        def imported(name):events.append('import');self.assertEqual(name,'src.staged_rts24_saved_fresh_adoption_v1');return result
        self.assertIs(self.bs.diagnostic_import_once(runtime,_importer=imported,_arm=arm,_cancel=cancel),result)
        self.assertEqual(events,['arm','import','cancel'])
        self.assertEqual([json.loads(line)[1] for line in sink.getvalue().splitlines()],['before_adapter_import','adapter_import_returned','after_adapter_import_attempt'])
        primary=ValueError('import_failure');secondary=OSError('cancel_failure');events=[];runtime,sink=self.runtime()
        def failed(name):events.append('import');raise primary
        def bad_cancel():events.append('cancel');raise secondary
        with self.assertRaises(ValueError) as caught:self.bs.diagnostic_import_once(runtime,_importer=failed,_arm=arm,_cancel=bad_cancel)
        self.assertIs(caught.exception,primary);self.assertEqual(caught.exception.__cause__.exceptions,(secondary,));self.assertEqual(events,['arm','import','cancel'])
        calls=[]
        def bad_write(raw):calls.append('write');raise OSError('stage_failure')
        runtime,sink=self.runtime(bad_write)
        with self.assertRaises(OSError):self.bs.diagnostic_import_once(runtime,_importer=lambda name:calls.append('import'),_arm=lambda *a,**k:calls.append('arm'),_cancel=lambda:calls.append('cancel'))
        self.assertEqual(calls,['write'])
        runtime,sink=self.runtime()
        with self.assertRaises(BaseExceptionGroup) as cancel_only:self.bs.diagnostic_import_once(runtime,_importer=lambda name:result,_arm=lambda *a,**k:None,_cancel=bad_cancel)
        self.assertEqual(cancel_only.exception.exceptions,(secondary,))
        events=[];runtime,sink=self.runtime();arm_error=ValueError('arm_failure')
        def bad_arm(*args,**kwargs):events.append('arm');raise arm_error
        with self.assertRaises(ValueError) as caught:self.bs.diagnostic_import_once(runtime,_importer=lambda name:events.append('import'),_arm=bad_arm,_cancel=cancel)
        self.assertIs(caught.exception,arm_error);self.assertEqual(events,['arm','cancel'])
        count=[0]
        def late_bad_write(raw):
            count[0]+=1
            if count[0]==2:raise OSError('after_import_trace_failure')
        runtime,sink=self.runtime(late_bad_write)
        with self.assertRaises(ValueError) as caught:self.bs.diagnostic_import_once(runtime,_importer=failed,_arm=lambda *a,**k:None,_cancel=lambda:None)
        self.assertIs(caught.exception,primary);self.assertIsInstance(caught.exception.__cause__.exceptions[0],OSError)
    def test_actual_validator_binds_watchdog_defaults(self):
        node=next(n for n in ast.parse(PROBE.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='validate_import_helper')
        context={**vars(core),'__builtins__':vars(builtins)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(PROBE),'exec',dont_inherit=True,optimize=0),context)
        proof=context['validate_import_helper'](self.bs,compile(BS.read_bytes(),str(BS),'exec',dont_inherit=True,optimize=0),tuple(vars(builtins).items()))
        self.assertTrue(proof);self.assertIs(self.bs.diagnostic_import_once.__defaults__[1],self.bs._IMPORT_FAULT.dump_traceback_later)
        original=self.bs.diagnostic_import_once.__defaults__
        for index in (0,1,2,4):
            changed=list(original);changed[index]=lambda:None
            try:
                self.bs.diagnostic_import_once.__defaults__=tuple(changed)
                with self.assertRaises(ValueError):context['validate_import_helper'](self.bs,compile(BS.read_bytes(),str(BS),'exec',dont_inherit=True,optimize=0),tuple(vars(builtins).items()))
            finally:self.bs.diagnostic_import_once.__defaults__=original
    def test_mixed_stderr_preserves_non_json_and_partial_frames(self):
        parent=load(PARENT,'_import_timing_parent')
        raw=b'["enter",1.0]\n["stage","before_adapter_import",1.1]\nTimeout (0:00:02)!\nThread 0x12:\n  File "x", line 1\n["stage","unknown",2.0]\n["stage","after_adapter_import_attempt",NaN]\npartial ["stage"'
        row=parent.parse_diagnostic_stderr(raw)
        self.assertEqual(row['stages'],[['stage','before_adapter_import',1.1]]);self.assertEqual(row['graph_frames'],[['enter',1.0]])
        self.assertTrue(row['stack_present']);self.assertFalse(row['stage_parse_complete']);self.assertEqual(row['unclassified_json_lines'],2)
        import base64
        residual=base64.b64decode(row['non_stage_raw_base64']);self.assertIn(b'Timeout',residual);self.assertIn(b'partial ["stage"',residual);self.assertEqual(parent.pin(residual),row['non_stage_pin'])
        malformed=b'["stage",[],1.0]\n["stage","adapter_import_returned",3.0]'
        row=parent.parse_diagnostic_stderr(malformed)
        self.assertEqual(row['stages'],[]);self.assertEqual(row['unclassified_json_lines'],1)
        self.assertEqual(base64.b64decode(row['non_stage_raw_base64']),malformed)
        partial=parent.compare_child('import_discovery',b'',b'',raw,1,None,[],[])
        self.assertFalse(partial['self_close_witness_present']);self.assertFalse(partial['adapter_import_return_observed'])
        self.assertIsNone(partial['child_record']);self.assertEqual(partial['adapter_import_attempts_upper_bound'],1)
if __name__=='__main__':unittest.main()
