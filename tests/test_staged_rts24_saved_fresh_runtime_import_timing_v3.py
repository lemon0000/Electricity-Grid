"""Single-import diagnostic control and mixed stderr, without importing an adapter."""
import ast
import builtins
import base64
import io
import importlib.util
import json
from pathlib import Path
from types import CodeType,FunctionType,ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
BS=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_cache_v1.py'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_v3.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v11.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v11.py'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v14.py','_import_timing_core')
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
        before=json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_cache_path_v1_non_authoritative/helper_snapshots.json').read_bytes())
        self.assertEqual(BS.read_bytes(),base64.b64decode(before[str(BS)]))
        for table in (old,new):
            cls=table['BootstrapImportBoundary']
            cls.body=[node for node in cls.body if not (type(node) is ast.FunctionDef and node.name=='_check_cache')]
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
        def arm(*args,**kwargs):events.append('arm');self.assertEqual(args,(2,));self.assertIs(kwargs['repeat'],False);self.assertIs(kwargs['file'],sink)
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
        for index in (0,1,2,3,4):
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
        identity=dict(pid=7,creation=9);argv=['diagnostic']
        record=dict(schema='staged_saved_F_runtime_handoff_probe_v1',authority='DRAFT_NONAUTHORITATIVE',case='import_discovery',source_epoch=parent.SOURCE_SHA,
            live_at_report=False,status='failed',primary=dict(type='ValueError'),secondary=[],self_handles_closed=True,close_calls=[1,1],
            source_phase='CONSUMED',inputs_phase='CONSUMED',namespace_phase='CONSUMED',runtime_is_resource_owner=True,
            old_inputs_successor_matches=True,old_namespace_successor_matches=True,resource_phase='CLOSED',runtime_phase='UNRESOLVED',
            dll_directory_close_returned=True,namespace_alias_absent=True,kernel_identity=dict(pid=7,process_creation_filetime=9,image_path=str(parent.EXE),command_line_sha=parent.pin(parent.subprocess.list2cmdline(argv).encode('utf-8'))),
            **{name:False for name in parent.FALSE_FIELDS})
        self.assertTrue(parent.validate_diagnostic_record('import_discovery',parent.canonical(record)+b'\n',1,identity,argv)[1])
        for key,value in (('schema','other'),('case','other'),('source_epoch','0'*64),('close_calls',[0,1]),('resource_phase','UNRESOLVED'),('status','completed')):
            changed={**record,key:value}
            with self.assertRaises(AssertionError):parent.validate_diagnostic_record('import_discovery',parent.canonical(changed)+b'\n',1,identity,argv)
        with self.assertRaises(AssertionError):parent.validate_diagnostic_record('import_discovery',b' '+parent.canonical(record)+b'\n',1,identity,argv)
        changed={**record,'dll_directory_close_returned':False}
        self.assertFalse(parent.validate_diagnostic_record('import_discovery',parent.canonical(changed)+b'\n',1,identity,argv)[1])
    def test_prefix_dictionary_transport_preserves_payload_bytes_and_code(self):
        import base64,zlib
        parent=load(PARENT,'_import_timing_transport_parent');code=parent.transport();marker=b'\nimport os as _bootstrap_os\n'
        prefix=code.partition(marker)[0];node=next(n for n in ast.walk(ast.parse(code)) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='b85decode')
        decoder=zlib.decompressobj(zdict=prefix);payload=decoder.decompress(base64.b85decode(node.args[0].value),131073)
        self.assertLessEqual(len(payload),131072);self.assertTrue(decoder.eof);self.assertFalse(decoder.unused_data or decoder.unconsumed_tail)
        original=parent.CORE.read_bytes()+b'\n'+parent.PROBE.read_bytes();expected=b'import builtins\n'+original.split(b'\nimport builtins\n',1)[1]
        import tokenize
        self.assertTrue(expected.isascii());offsets=[];offset=0
        for line in expected.splitlines(keepends=True):offsets.append(offset);offset+=len(line)
        comments=set()
        for token in tokenize.tokenize(io.BytesIO(expected).readline):
            if token.type==tokenize.COMMENT:
                self.assertEqual(token.start[0],token.end[0])
                comments.update(range(offsets[token.start[0]-1]+token.start[1],offsets[token.end[0]-1]+token.end[1]))
        raw_expected=bytes(32 if index in comments else value for index,value in enumerate(expected))
        self.assertEqual(payload,raw_expected)
        self.assertEqual(ast.dump(ast.parse(payload),include_attributes=True),ast.dump(ast.parse(expected),include_attributes=True))
        self.assertEqual(compile(payload,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0),compile(expected,'<pre_entry_payload>','exec',dont_inherit=True,optimize=0))
        command=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(parent.OUT/'probe_import_discovery.plan.json'),'0'*64]
        self.assertLessEqual(len(parent.subprocess.list2cmdline(command).encode('utf-16-le'))//2,30000)
        plan=parent.manifest('discovery',code)
        self.assertEqual(plan['import_helper'],dict(path=str(BS),pin=parent.pin(BS.read_bytes())))
        self.assertEqual(plan['namespace_helper']['path'],str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_timing_v1.py'))
if __name__=='__main__':unittest.main()
