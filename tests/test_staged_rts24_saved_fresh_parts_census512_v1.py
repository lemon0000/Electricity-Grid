"""Finite import limit/return protocol; fake hooks only, no scientific import."""
import ast
import copy
import dis
import importlib.util
import json
from pathlib import Path
from types import FunctionType
import unittest

ROOT=Path(__file__).absolute().parents[1]
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census512_parts_v1.py'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census256_v1.py'
PARTS=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_cache_parts_full_v1.py'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

base=load(ROOT/'tests/test_staged_rts24_saved_fresh_census256_v1.py','_parts512_base')
core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v27.py','_parts512_core')
parent=load(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v24.py','_parts512_parent')
fixture=base.fixture;fixture.BS=NEW;fixture.PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v24.py';fixture.core=core

def run_window(count=512,stage=0):
    module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);physical=[0]
    def importer(name):
        for _ in range(count):module.sys.audit('open','D:/allowed','r',0);physical[0]+=1
        guard._observed_stage=stage
        return object()
    try:module.diagnostic_import_once(runtime,_importer=importer)
    except module.AuditCensusStop as error:message=str(error)
    else:raise AssertionError('diagnostic stop absent')
    return module,wire(sink.getvalue()),message,physical[0]

def wire(raw):
    rows=[json.loads(line) for line in raw.splitlines()]
    for row in rows:
        if row[0]=='census':row[1]['start_clock']+=10.;row[1]['snapshot_clock']+=10.
        else:row[-1]+=10.
    rows=[['enter',9.0],['exit',9.1],['stage','loader_ready',9.2],*rows]
    return b''.join(parent.canonical(row)+b'\n' for row in rows)

def compare_record(value,raw):
    argv=['synthetic-finite-observation'];kernel=value['kernel_identity']
    kernel['command_line_sha']=parent.pin(parent.subprocess.list2cmdline(argv).encode('utf-8'))
    identity=dict(pid=kernel['pid'],creation=kernel['process_creation_filetime'])
    return parent.compare_child('import_discovery',b'',parent.canonical(value)+b'\n',raw,1,identity,argv,[])

def record(reason='prefix_complete',stage=0):
    value=base.good_record()
    message='diagnostic_prefix_complete_512' if reason=='prefix_complete' else 'diagnostic_import_return_before512'
    def change(x):
        if type(x) is str:return message if x=='diagnostic_prefix_complete_256' else x
        if type(x) is list:return [change(v) for v in x]
        if type(x) is dict:return {k:change(v) for k,v in x.items()}
        return x
    value=change(value);value['boundary_report'].update(machinery_observed_stage=stage,machinery_authentication_pending=bool(stage),internal_introspection_events=stage*3)
    return value

class Parts512Tests(unittest.TestCase):
    def test_01_guard_ast_headers_and_verified_parts_method(self):
        a=ast.parse(OLD.read_bytes());b=ast.parse(NEW.read_bytes());parts=ast.parse(PARTS.read_bytes())
        allowed={'_census_emit','_census_observer','_census_open_begin','_census_open_end','diagnostic_import_once','_census_finish'}
        class Normalize(ast.NodeTransformer):
            def visit_Constant(self,node):
                if type(node.value) is int and node.value in (256,512):node.value=99999
                elif type(node.value) is str:node.value=node.value.replace('before256','beforeN').replace('before512','beforeN').replace('complete_256','complete_N').replace('complete_512','complete_N').replace('audit_census_v2','audit_census_vN').replace('audit_census_v3','audit_census_vN')
                return node
            def visit_Tuple(self,node):
                if all(type(v) is ast.Constant for v in node.elts) and tuple(v.value for v in node.elts) in ((1,32,64,96,128,160,192,224),(1,64,128,192,256,320,384,448)):
                    node.elts=[ast.Constant('fixed_schedule')];return node
                return self.generic_visit(node)
        for old,new in zip(a.body,b.body):
            if type(old) is ast.FunctionDef and old.name in allowed:
                self.assertEqual(old.name,new.name);self.assertNotEqual(ast.dump(old),ast.dump(new))
                if old.name=='_census_finish':
                    changed=copy.deepcopy(new);branch=next(n for n in changed.body if type(n) is ast.If and type(n.test) is ast.Name and n.test.id=='was_active')
                    refresh=branch.body.pop(0);self.assertEqual(ast.dump(refresh),ast.dump(ast.parse("_state['stage']=_state['boundary']._observed_stage").body[0]));self.assertEqual(ast.dump(old),ast.dump(changed))
                else:self.assertEqual(ast.dump(Normalize().visit(copy.deepcopy(old))),ast.dump(Normalize().visit(copy.deepcopy(new))))
                old.body=new.body=[ast.Pass()]
        ca=next(n for n in a.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary');cb=next(n for n in b.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary');pc=next(n for n in parts.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
        ma=next(n for n in ca.body if type(n) is ast.FunctionDef and n.name=='_check_cache');mb=next(n for n in cb.body if type(n) is ast.FunctionDef and n.name=='_check_cache');mp=next(n for n in pc.body if type(n) is ast.FunctionDef and n.name=='_check_cache')
        self.assertEqual(ast.dump(mb),ast.dump(mp));ma.body=mb.body=[ast.Pass()];self.assertEqual(ast.dump(a),ast.dump(b))
    def test_02_held_defaults_metadata_and_zero_global_census(self):
        module,sink=fixture.helper();self.assertTrue(fixture.proof_for(module,core))
        for name,fn in vars(module).items():
            if name.startswith('_census_') and type(fn) is FunctionType:self.assertFalse([op for op in dis.get_instructions(fn) if op.opname=='LOAD_GLOBAL'],name)
        old=module._census_observer.__defaults__;changed=list(old);changed[1]=(lambda:0.0,*old[1][1:]);module._census_observer.__defaults__=tuple(changed)
        with self.assertRaises(ValueError):fixture.proof_for(module,core)
    def test_03_exact512_and511_physical(self):
        module,raw,message,physical=run_window();parsed=parent.validate_prefix_observation(record(),raw)
        self.assertEqual(message,'diagnostic_prefix_complete_512');self.assertEqual(physical,511)
        self.assertEqual([x['passed'] for x in parsed['census_frames']],[0,1,64,128,192,256,320,384,448,512])
        self.assertEqual(module._CENSUS['observed'],512);self.assertFalse(module._CENSUS['active']);self.assertFalse(module._CENSUS['inflight'])
    def test_04_natural_return_boundaries_and_phase_refresh(self):
        for count in (0,1,63,64,256,511):
            for stage in (0,2):
                module,raw,message,physical=run_window(count,stage);parsed=parent.validate_prefix_observation(record('import_return_before512',stage),raw)
                self.assertEqual(message,'diagnostic_import_return_before512');self.assertEqual(physical,count)
                self.assertEqual(parsed['census_frames'][-1]['passed'],count);self.assertEqual(parsed['census_frames'][-1]['machinery_stage'],stage)
                self.assertEqual([r[1] for r in parsed['stages']],['loader_ready','before_adapter_import','adapter_import_returned','after_adapter_import_attempt'])
    def test_05_clock_io_and_primary_cause(self):
        fixture.CensusTests.test_04_clock_io_failure_preserves_guard_primary(self)
        module,sink=fixture.helper();guard,runtime,trace,unused=fixture.guard_for(module);primary=LookupError('import primary');cause=OSError('prior cause');primary.__cause__=cause
        def importer(name):raise primary
        with self.assertRaises(LookupError) as caught:module.diagnostic_import_once(runtime,_importer=importer)
        self.assertIs(caught.exception,primary);self.assertIs(primary.__cause__,cause)
        parsed=parent.parse_diagnostic_stderr(sink.getvalue());self.assertEqual(parsed['census_frames'][-1]['reason'],'import_error_before512')
    def test_06_strict_schema_schedule_clock_cache_and_phase(self):
        module,raw,message,physical=run_window();rows=[json.loads(line) for line in raw.splitlines()]
        for kind in ('bucket','start','cache','schema','limit','phase_backwards','tail','missing_graph','missing_progress'):
            changed=copy.deepcopy(rows)
            frames=[r[1] for r in changed if r[0]=='census']
            if kind=='bucket':frames[-1]['buckets']['cache'][0]=511
            elif kind=='start':frames[-1]['start_clock']+=.001
            elif kind=='cache':frames[-1]['cache_new']+=1
            elif kind=='schema':frames[-1]['schema']='staged_saved_F_audit_census_v2'
            elif kind=='limit':frames[-1]['limit']=512.0
            elif kind=='phase_backwards':frames[-2]['machinery_stage']=2
            elif kind=='missing_graph':changed=[r for r in changed if r[0] not in ('enter','exit')]
            elif kind=='missing_progress':changed=[r for r in changed if not(r[0]=='census' and r[1]['passed']==256)]
            bad=b''.join(parent.canonical(r)+b'\n' for r in changed)+(b'["census",' if kind=='tail' else b'')
            with self.assertRaises(AssertionError):parent.validate_prefix_stderr(bad)
    def test_07_both_modes_record_authority_and_parent_completion(self):
        for reason in ('prefix_complete','import_return_before512'):
            self.assertTrue(parent.validate_prefix_record(record(reason),reason))
            stage=1 if reason=='import_return_before512' else 0
            module,raw,unused,physical=run_window(64 if stage else 512,stage)
            observed=compare_record(record(reason,stage),raw)
            self.assertTrue(observed['finite_terminal_complete']);self.assertTrue(parent.prefix_terminal_complete(observed,None))
            self.assertIs(observed['prefix_complete'],reason=='prefix_complete');self.assertIs(observed['adapter_import_return_observed'],reason=='import_return_before512')
            result=dict(finite_terminal_complete=True,prefix_complete=reason=='prefix_complete',self_close_witness_present=True,child_record=record(reason))
            self.assertTrue(parent.prefix_terminal_complete(result,None));self.assertFalse(parent.prefix_terminal_complete(result,'timeout'))
            for field,value in (('actual_F',True),('F_completed',True),('runtime_phase','LIVE')):
                changed=record(reason);changed[field]=value
                with self.assertRaises(AssertionError):parent.validate_prefix_record(changed,reason)
        self.assertFalse(parent.prefix_terminal_complete(None,None));self.assertFalse(parent.prefix_terminal_complete(dict(finite_terminal_complete=False,self_close_witness_present=True,child_record={}),None))
        module,raw,unused,physical=run_window();rows=[json.loads(line) for line in raw.splitlines()];partial=b''.join(parent.canonical(r)+b'\n' for r in rows[:-2])
        result=parent.compare_child('import_discovery',b'',b'',partial,1,None,[],[]);self.assertEqual(result['census_terminal_reason'],'no_child_report_after_progress');self.assertFalse(parent.prefix_terminal_complete(result,None))
        module,sink=fixture.helper();guard,runtime,trace,unused=fixture.guard_for(module)
        def importer(name):
            for _ in range(7):module.sys.audit('open','D:/allowed','r',0)
            raise LookupError('import failure fixture')
        with self.assertRaises(LookupError):module.diagnostic_import_once(runtime,_importer=importer)
        value=record();value['primary']=dict(type='LookupError',message='import failure fixture',primary=None,secondary=[],cause=None,group=[],truncated=False);value['secondary']=[]
        result=compare_record(value,wire(sink.getvalue()));self.assertFalse(result['finite_terminal_complete']);self.assertFalse(parent.prefix_terminal_complete(result,None));self.assertEqual(result['census_terminal_reason'],'import_error_before512')
    def test_08_finite_output_duplicate_and_original_guard_rejection(self):
        module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime)
        with self.assertRaises(BaseException):module._census_start(runtime)
        module._CENSUS['seq']=12;module._census_emit('progress')
        with self.assertRaises(BaseExceptionGroup):module._census_raise(None)
        self.assertLessEqual(len(sink.getvalue()),24576)
        for path,mode in (('D:/protected/x','r'),('D:/allowed','w')):
            module,sink=fixture.helper();guard,runtime,trace,primary=fixture.guard_for(module);module._census_start(runtime)
            with self.assertRaises(module.BootstrapImportRejected):module.sys.audit('open',path,mode,0)
            self.assertEqual(module._CENSUS['passed'],0);self.assertEqual(module._CENSUS['observed'],0)

if __name__=='__main__':unittest.main()
