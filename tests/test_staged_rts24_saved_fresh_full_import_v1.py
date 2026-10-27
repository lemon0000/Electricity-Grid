"""Full-return wrapper and complete-import record protocol; no scientific import."""
import ast
import builtins
import copy
import dis
import importlib.util
import io
import json
from pathlib import Path
import sys
import time
from types import ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_pin_v1.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_full_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v20.py'
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v23.py','_full_core')
parent=load(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v20.py','_full_parent')
graph=load(ROOT/'experiments/staged_rts24_saved_fresh_import_graph_v1.py','_full_graph')
def helper():
    sink=io.BytesIO();module=ModuleType('_full_helper')
    vars(module).update(__file__=str(NEW),_READ_FILE=core.read_file,_CENSUS_IO=(time.perf_counter,sink.write,sink.flush,json.dumps))
    exec(compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0),vars(module));return module
def proof_for(module):
    node=next(n for n in ast.parse(PROBE.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='validate_import_helper')
    context={**vars(core),'__builtins__':vars(builtins)}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(PROBE),'exec',dont_inherit=True,optimize=0),context)
    return context['validate_import_helper'](module,compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0),tuple(vars(builtins).items()),module._CENSUS_IO)
def encoded(rows):return b''.join(parent.canonical(row)+b'\n' for row in rows)
def stage_rows():
    rows=[];clock=1.0
    for name in parent.FULL_STAGES:
        rows.extend((['enter',clock],['exit',clock+.001],['stage',name,clock+.002]));clock+=.01
    return rows
def good_record():
    path=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v8_non_authoritative/probe_import_discovery.receipt.json'
    record=json.loads(path.read_bytes())['result']['child_record']
    record.update(schema='staged_saved_F_runtime_handoff_probe_v2',status='completed',primary=None,secondary=[],failure_phase=None,runtime_preclose='OBSERVED',runtime_phase='CLOSED',boundary_phase='CLOSED',retained_modules=1,source_bookends=3)
    record['boundary_report'].update(phase='CLOSED',optional_Popen_attempts=1,blocked_optional_attempts=1,internal_introspection_events=6,
        forced_numpy_SVE_false=True,import_boundary_completed=True,source49_bookend_equal=True,machinery_observed_stage=2,machinery_authenticated_stage=2,
        finder_function_metadata_bookend_verified=True)
    policy=json.loads((parent.OUT/'import_policy.json').read_bytes());path=str(ROOT/'src/staged_rts24_saved_fresh_adoption_v1.py')
    record['import_profile']=dict(schema='staged_saved_F_B_S_import_observation_v1',authority='DRAFT_NONAUTHORITATIVE',
        modules=[['src.staged_rts24_saved_fresh_adoption_v1','module',path,path,'synthetic_loader']],cache=[],paths=policy['admitted_paths'],
        finder_types=['synthetic']*5,machinery_observed=2,machinery_authenticated=2,optional_attempts=1,
        loaded_python_graph_attested=False,registry_contents_verified=False,native_behavior_verified=False)
    return record

class FullImportTests(unittest.TestCase):
    def test_01_only_wrapper_body_and_held_defaults(self):
        def split(path):
            tree=ast.parse(path.read_bytes());node=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='diagnostic_import_once')
            tree.body.remove(node);return ast.dump(tree),node
        before,a=split(OLD);after,b=split(NEW);self.assertEqual(before,after)
        a.body=b.body=[ast.Pass()];self.assertEqual(ast.dump(a),ast.dump(b))
        module=helper();self.assertTrue(proof_for(module))
        inventory=copy.deepcopy(graph.ADMITTED_INVENTORY);self.assertTrue(graph.validate_inventory(inventory))
        name='src.staged_rts24_saved_fresh_adoption_v1'
        for change in ('factory','<computed>','source_pin','missing_module','unknown_module'):
            changed=copy.deepcopy(inventory)
            if change in ('factory','<computed>'):changed[name]['import_time_calls'][0]['callee']=change
            elif change=='source_pin':changed[name]['pin']['sha256']='0'*64
            elif change=='missing_module':del changed[name]
            else:changed['unknown_module']=copy.deepcopy(changed[name])
            with self.assertRaises(AssertionError):graph.validate_inventory(changed)
    def test_02_return_identity_single_import_no_census_calls(self):
        module=helper();events=[];calls=[];value=object()
        def importer(name):calls.append(name);return value
        def forbidden(*args):raise AssertionError('inactive census dependency called')
        result=module.diagnostic_import_once(SimpleNamespace(),_importer=importer,_start=forbidden,_finish=forbidden,_stop=forbidden,_trace=lambda r,n:events.append(n))
        self.assertIs(result,value);self.assertEqual(calls,['src.staged_rts24_saved_fresh_adoption_v1'])
        self.assertEqual(events,['before_adapter_import','adapter_import_returned','after_adapter_import_attempt'])
        self.assertFalse(module._CENSUS['active']);self.assertFalse(module._CENSUS['ever_started']);self.assertEqual(module._CENSUS['installed'],0)
    def test_03_importer_primary_identity_and_existing_cause(self):
        module=helper();primary=RuntimeError('import primary');cause=ValueError('existing cause');primary.__cause__=cause;events=[]
        def importer(name):raise primary
        with self.assertRaises(RuntimeError) as caught:module.diagnostic_import_once(None,_importer=importer,_trace=lambda r,n:events.append(n))
        self.assertIs(caught.exception,primary);self.assertIs(primary.__cause__,cause)
        self.assertEqual(events,['before_adapter_import','after_adapter_import_attempt'])
    def test_04_trace_failure_preserves_primary_and_cleanup_group(self):
        module=helper();primary=RuntimeError('import primary');cause=ValueError('existing cause');cleanup=OSError('after trace');primary.__cause__=cause
        def importer(name):raise primary
        def trace(r,name):
            if name=='after_adapter_import_attempt':raise cleanup
        with self.assertRaises(RuntimeError) as caught:module.diagnostic_import_once(None,_importer=importer,_trace=trace)
        self.assertIs(caught.exception,primary);self.assertIsInstance(primary.__cause__,BaseExceptionGroup)
        self.assertEqual(primary.__cause__.exceptions,(cause,cleanup));self.assertNotIn(primary,primary.__cause__.exceptions)
        returned=ValueError('returned trace')
        def fail_return(r,name):
            if name=='adapter_import_returned':raise returned
        with self.assertRaises(ValueError) as caught:module.diagnostic_import_once(None,_importer=lambda n:object(),_trace=fail_return)
        self.assertIs(caught.exception,returned)
        with self.assertRaises(BaseExceptionGroup) as caught:module.diagnostic_import_once(None,_importer=lambda n:object(),_trace=trace)
        self.assertEqual(caught.exception.exceptions,(cleanup,))
    def test_05_complete_stages_graphs_and_observed_record(self):
        result=parent.validate_full_stderr(encoded(stage_rows()))
        self.assertTrue(result['full_stage_sequence_verified']);self.assertTrue(result['graph_pairing_verified']);self.assertEqual(result['census_frames'],[])
        value=parent.validate_full_record(good_record());self.assertTrue(value['observed_before_cleanup']);self.assertFalse(value['full_runtime_binding_verified'])
        self.assertFalse(value['all_unselected_events_verified']);self.assertFalse(value['resource_admission'])
        for value in (dict(peak_working_set_bytes=123,error=None),dict(peak_working_set_bytes=None,error='GetProcessMemoryInfo:5')):
            self.assertEqual(parent.validate_memory_observation(value),value)
    def test_06_reject_partial_reordered_and_authority_drift(self):
        rows=stage_rows();faults=[rows[3:],rows+rows[-1:],list(reversed(rows)),[r for r in rows if r[0]=='stage'],rows+[ ['enter',3.0] ],rows+[ ['census',{}] ]]
        for bad in faults:
            with self.assertRaises((AssertionError,KeyError)):parent.validate_full_stderr(encoded(bad))
        for tail in (b'["enter",',b'traceback text\n'):
            with self.assertRaises(AssertionError):parent.validate_full_stderr(encoded(rows)+tail)
        for field,value in (('runtime_preclose','LIVE'),('runtime_preclose',None),('runtime_phase','UNRESOLVED'),('actual_F',True),('primary',{'type':'AuditCensusStop'})):
            record=good_record();record[field]=value
            with self.assertRaises(AssertionError):parent.validate_full_record(record)
        for field,value in (('forced_numpy_SVE_false',False),('machinery_authenticated_stage',0),('machinery_authentication_pending',True),('finder_function_metadata_bookend_verified',False),('resource_admission',True),('extra_field',False)):
            record=good_record();record['boundary_report'][field]=value
            with self.assertRaises(AssertionError):parent.validate_full_record(record)
        record=good_record();record['import_profile']['modules']=[]
        with self.assertRaises(AssertionError):parent.validate_full_record(record)
        for field in ('runtime_preclose','actual_F','guard','schema'):
            record=good_record();del record[field]
            with self.assertRaises(AssertionError):parent.validate_full_record(record)
        for target in ('top','guard'):
            record=good_record();value=record if target=='top' else record['guard'];value['F_completed']=True
            with self.assertRaises(AssertionError):parent.validate_full_record(record)
        record=good_record();del record['guard']['sentinel']
        with self.assertRaises(AssertionError):parent.validate_full_record(record)
        for value in (None,{},dict(peak_working_set_bytes=True,error=None),dict(peak_working_set_bytes=-1,error=None),dict(peak_working_set_bytes=None,error=None),dict(peak_working_set_bytes=1,error='error'),dict(peak_working_set_bytes=None,error=''),dict(peak_working_set_bytes=None,error='e'*161),dict(peak_working_set_bytes=1,error=None,resource_admission=True)):
            with self.assertRaises(AssertionError):parent.validate_memory_observation(value)

if __name__=='__main__':unittest.main()
