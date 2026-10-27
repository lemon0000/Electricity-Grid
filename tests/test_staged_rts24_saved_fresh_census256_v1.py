"""Finite selected-open protocol checks; no scientific module or real audit installation."""
import ast
import base64
import copy
import dis
import importlib.util
import json
from pathlib import Path
from types import FunctionType
import unittest

ROOT=Path(__file__).absolute().parents[1]
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_pin_v1.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census256_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v21.py'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

fixture=load(ROOT/'tests/test_staged_rts24_saved_fresh_audit_census_v4.py','_prefix256_fixture')
core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v24.py','_prefix256_core')
parent=load(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v21.py','_prefix256_parent')
fixture.BS=NEW;fixture.PROBE=PROBE;fixture.core=core

def complete():
    module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime)
    try:
        for _ in range(256):module.sys.audit('open','D:/allowed','r',0)
    except module.AuditCensusStop:pass
    else:raise AssertionError('256th event did not stop')
    return module,sink

def full_raw():
    module,sink=complete();frames=[json.loads(line) for line in sink.getvalue().splitlines()]
    for row in frames:
        row[1]['start_clock']+=10.;row[1]['snapshot_clock']+=10.
    rows=[['enter',9.0],['exit',9.1],['stage','loader_ready',9.2],['stage','before_adapter_import',9.3],*frames,['stage','after_adapter_import_attempt',11.0]]
    return b''.join(parent.canonical(row)+b'\n' for row in rows)

def good_record():
    path=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v8_non_authoritative/probe_import_discovery.receipt.json'
    record=json.loads(path.read_bytes())['result']['child_record']
    def successor(value):
        if type(value) is str:return 'diagnostic_prefix_complete_256' if value=='diagnostic_prefix_complete_64' else value
        if type(value) is list:return [successor(v) for v in value]
        if type(value) is dict:return {k:successor(v) for k,v in value.items()}
        return value
    return successor(record)

class Prefix256Tests(unittest.TestCase):
    def test_01_five_body_only_ast_and_held_default_proof(self):
        a=ast.parse(OLD.read_bytes());b=ast.parse(NEW.read_bytes());changed=[]
        allowed={'_census_emit','_census_observer','_census_open_begin','_census_open_end','diagnostic_import_once'}
        for before,after in zip(a.body,b.body):
            if type(before) is ast.FunctionDef and before.name in allowed:
                self.assertNotEqual(ast.dump(before),ast.dump(after));changed.append(before.name);before.body=after.body=[ast.Pass()]
        self.assertEqual(set(changed),allowed);self.assertEqual(ast.dump(a),ast.dump(b))
        module,sink=fixture.helper();self.assertTrue(fixture.proof_for(module,core))
        for name,fn in vars(module).items():
            if name.startswith('_census_') and type(fn) is FunctionType:
                self.assertFalse([op for op in dis.get_instructions(fn) if op.opname=='LOAD_GLOBAL'],name)
        original=module._census_observer.__defaults__;changed=list(original);changed[1]=(lambda:0.0,*original[1][1:]);module._census_observer.__defaults__=tuple(changed)
        with self.assertRaises(ValueError):fixture.proof_for(module,core)
    def test_02_exact_256_guard_passes_and_255_physical_opens(self):
        module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime);physical=0
        for index in range(256):
            try:module.sys.audit('open','D:/allowed','r',0)
            except module.AuditCensusStop as error:
                self.assertEqual(index,255);self.assertEqual(str(error),'diagnostic_prefix_complete_256');break
            physical+=1
        state=module._CENSUS;self.assertEqual((state['entered'],state['passed'],state['observed'],physical),(256,256,256,255))
        self.assertFalse(state['active']);self.assertFalse(state['inflight']);self.assertFalse(guard._busy)
        frames=parent.parse_diagnostic_stderr(sink.getvalue())['census_frames']
        self.assertEqual([row['passed'] for row in frames],[0,1,32,64,96,128,160,192,224,256])
        self.assertEqual(len(frames),10);self.assertTrue(all(row['schema']=='staged_saved_F_audit_census_v2' and row['limit']==256 for row in frames))
    def test_03_early_return_complete_progress_schedule(self):
        for count in (0,7,31,32,63,64,255):
            module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module)
            def importer(name):
                for _ in range(count):module.sys.audit('open','D:/allowed','r',0)
                return object()
            with self.assertRaises(module.AuditCensusStop) as caught:module.diagnostic_import_once(runtime,_importer=importer)
            self.assertEqual(str(caught.exception),'diagnostic_import_return_before256')
            parsed=parent.parse_diagnostic_stderr(sink.getvalue());frames=parsed['census_frames']
            self.assertEqual(frames[-1]['passed'],count);self.assertEqual(frames[-1]['reason'],'import_return_before256')
            self.assertEqual([f['passed'] for f in frames if f['reason']=='progress'],[v for v in (1,32,64,96,128,160,192,224) if v<=count])
            with self.assertRaises(AssertionError):parent.validate_prefix_stderr(sink.getvalue())
    def test_04_clock_io_and_primary_cause_failures(self):
        fixture.CensusTests.test_04_clock_io_failure_preserves_guard_primary(self)
        module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);original=LookupError('import primary');cause=ValueError('existing');original.__cause__=cause
        def importer(name):raise original
        with self.assertRaises(LookupError) as caught:module.diagnostic_import_once(runtime,_importer=importer)
        self.assertIs(caught.exception,original);self.assertIs(original.__cause__,cause)
        self.assertEqual(parent.parse_diagnostic_stderr(sink.getvalue())['census_frames'][-1]['reason'],'import_error_before256')
    def test_05_complete_matrix_rejects_partial_and_schema_drift(self):
        raw=full_raw();parsed=parent.validate_prefix_stderr(raw);self.assertEqual(parsed['census_frames'][-1]['passed'],256)
        rows=[json.loads(line) for line in raw.splitlines()]
        for bad in (raw+b'["census",',raw+parent.canonical(rows[-2])+b'\n',b''.join(parent.canonical(row)+b'\n' for row in rows if row[0] not in ('enter','exit')),raw.replace(b'"limit":256',b'"limit":64',1),raw.replace(b'audit_census_v2',b'audit_census_v1',1),raw.replace(b'"seq":1',b'"seq":2',1)):
            with self.assertRaises(AssertionError):parent.validate_prefix_stderr(bad)
        frame=parsed['census_frames'][-1]
        for field,value in (('entered',257),('passed',True),('limit',256.0),('machinery_stage',True),('installation_seen',True),('diagnostic_error_count',1),('snapshot_clock',float('nan')),('unknown_authority',True)):
            changed=copy.deepcopy(frame);changed[field]=value
            if field=='diagnostic_error_count':
                altered=copy.deepcopy(rows);altered[-2][1]=changed
                with self.assertRaises(AssertionError):parent.validate_prefix_stderr(b''.join(parent.canonical(row)+b'\n' for row in altered))
            else:
                with self.assertRaises(AssertionError):parent.validate_census_frame(changed)
        for kind in ('bucket_count','start_clock','cache_growth'):
            changed=copy.deepcopy(rows)
            if kind=='bucket_count':changed[-2][1]['buckets']['cache'][0]=255
            elif kind=='start_clock':changed[-2][1]['start_clock']+=.001
            else:changed[-2][1]['cache_new']+=1
            with self.assertRaises(AssertionError):parent.validate_prefix_stderr(b''.join(parent.canonical(row)+b'\n' for row in changed))
    def test_06_guard_rejection_record_authority_and_rss(self):
        for path,mode in (('D:/protected/x','r'),('D:/allowed','w')):
            module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime)
            with self.assertRaises(module.BootstrapImportRejected):module.sys.audit('open',path,mode,0)
            self.assertEqual(module._CENSUS['passed'],0);self.assertEqual(module._CENSUS['observed'],0)
        self.assertTrue(parent.validate_prefix_record(good_record()))
        for observed in (0,1,2):
            record=good_record();report=record['boundary_report'];report['machinery_observed_stage']=observed;report['machinery_authentication_pending']=bool(observed);report['internal_introspection_events']=observed*3
            self.assertTrue(parent.validate_prefix_record(record));report['machinery_authentication_pending']=not bool(observed)
            with self.assertRaises(AssertionError):parent.validate_prefix_record(record)
        raw=full_raw();parent.validate_prefix_observation(good_record(),raw)
        record=good_record();record['boundary_report'].update(machinery_observed_stage=1,machinery_authentication_pending=True)
        with self.assertRaises(AssertionError):parent.validate_prefix_observation(record,raw)
        for final_stage in (1,2):
            rows=[json.loads(line) for line in raw.splitlines()]
            for row in rows:
                if row[0]=='census':row[1]['machinery_stage']=min(final_stage,2 if row[1]['passed']>=160 else 1 if row[1]['passed']>=64 else 0)
            record=good_record();record['boundary_report'].update(machinery_observed_stage=final_stage,machinery_authentication_pending=True,internal_introspection_events=final_stage*3)
            parent.validate_prefix_observation(record,b''.join(parent.canonical(row)+b'\n' for row in rows))
            if final_stage==1:
                next(row[1] for row in rows if row[0]=='census' and row[1]['passed']==192)['machinery_stage']=2
                with self.assertRaises(AssertionError):parent.validate_prefix_observation(record,b''.join(parent.canonical(row)+b'\n' for row in rows))
        complete_result=dict(prefix_complete=True,self_close_witness_present=True,child_record=good_record())
        self.assertTrue(parent.prefix_terminal_complete(complete_result,None))
        for result,reason in ((None,None),(dict(complete_result,prefix_complete=False),None),(dict(complete_result,child_record=None),None),(dict(complete_result,self_close_witness_present=False),None),(complete_result,'timeout'),(complete_result,'output_limit_or_reader_error')):
            self.assertFalse(parent.prefix_terminal_complete(result,reason))
        rows=[json.loads(line) for line in raw.splitlines()];partial=b''.join(parent.canonical(row)+b'\n' for row in rows[:-2])
        result=parent.compare_child('import_discovery',b'',b'',partial,1,None,[],[])
        self.assertEqual(result['census_terminal_reason'],'no_child_report_after_progress');self.assertFalse(parent.prefix_terminal_complete(result,None))
        for where,field,value in (('top','actual_F',True),('top','F_completed',True),('top','runtime_phase','LIVE'),('guard','unknown_permission',True),('boundary_report','resource_admission',True),('boundary_report','independent_root_verified',True)):
            record=good_record();(record if where=='top' else record[where])[field]=value
            with self.assertRaises(AssertionError):parent.validate_prefix_record(record)
        record=good_record();del record['guard']['sentinel']
        with self.assertRaises(AssertionError):parent.validate_prefix_record(record)
        for value in (dict(peak_working_set_bytes=123,error=None),dict(peak_working_set_bytes=None,error='GetProcessMemoryInfo:5')):self.assertEqual(parent.validate_memory_observation(value),value)
        for value in (None,{},dict(peak_working_set_bytes=True,error=None),dict(peak_working_set_bytes=-1,error=None),dict(peak_working_set_bytes=None,error=None)):
            with self.assertRaises(AssertionError):parent.validate_memory_observation(value)

if __name__=='__main__':unittest.main()
