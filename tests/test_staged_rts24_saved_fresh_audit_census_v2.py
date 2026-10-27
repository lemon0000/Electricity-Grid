"""Bounded census logic, real setter regressions, and transport; no adapter import."""
import ast
import base64
import builtins
import dis
import importlib.util
import io
import json
import os
from pathlib import Path
import sys
from threading import RLock,get_ident
import time
from types import CodeType,FunctionType,MethodType,ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
BS=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census_v2.py'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_cache_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v13.py'
PARENT=ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v13.py'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v16.py','_census_core')
legacy=load(ROOT/'tests/test_staged_rts24_saved_fresh_runtime_handoff_v3.py','_census_legacy')
legacy.BS=BS
legacy_load=legacy.load
def load_with_io(path,name,extra):
    return legacy_load(path,name,{**extra,**dict(_CENSUS_IO=(time.perf_counter,sys.stderr.buffer.write,sys.stderr.buffer.flush,json.dumps))} if path==BS else extra)
legacy.load=load_with_io
def proof_for(helper,context):
    node=next(n for n in ast.parse(PROBE.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='validate_import_helper')
    namespace={**vars(context),'__builtins__':vars(builtins)}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(PROBE),'exec',dont_inherit=True,optimize=0),namespace)
    return namespace['validate_import_helper'](helper,compile(BS.read_bytes(),str(BS),'exec',dont_inherit=True,optimize=0),tuple(vars(builtins).items()),helper._CENSUS_IO)
def legacy_proof(self,helper):return proof_for(helper,legacy.core)
legacy.RuntimeHandoffTests.bs_proof=legacy_proof

class Hooks:
    def __init__(self):self.hooks=[];self.path_importer_cache={};self.modules={}
    def addaudithook(self,fn):self.hooks.append(fn)
    def audit(self,event,*args):
        for fn in tuple(self.hooks):fn(event,args)

def helper(write=None,clock=None,dumps=None,flush=None):
    sink=io.BytesIO();counter=[0.0]
    def tick():counter[0]+=.00001;return counter[0]
    roots=(tick if clock is None else clock,sink.write if write is None else write,sink.flush if flush is None else flush,json.dumps if dumps is None else dumps)
    module=ModuleType('_census_test');vars(module).update(__file__=str(BS),_READ_FILE=core.read_file,_CENSUS_IO=roots)
    exec(compile(BS.read_bytes(),str(BS),'exec',dont_inherit=True,optimize=0),vars(module));return module,sink

def guard_for(module):
    trace=[];entry_module=object();runtime=SimpleNamespace();runtime._resource=SimpleNamespace(owner=runtime);runtime._namespace=SimpleNamespace(module=entry_module,_graph_plan=(None,None,None,(None,)*4+module._CENSUS_IO))
    runtime._boundary_bindings=(None,)*4+((),)
    guard=SimpleNamespace(_busy=False,_state=('ACTIVE',True,0,1,0,0,False,''),_creator=(os.getpid(),get_ident()),_lock=RLock(),
        _event_sets=(('subprocess.Popen',),(),('os.remove',)),_runtime=runtime,_expected_bindings=(),_owner=(None,object()),_finder_bindings=(),
        _internal=None,_paths=(os.path.normcase(os.path.abspath('D:/protected')),),_cache_initial=(),_observed_stage=0,
        _global_bindings=(),_attribute_bindings=(),_namespace=vars(module),_policy_profile={'allowed_entry_module':{'name':'entry'}},
        _image=lambda:('logical guard',),_check_cache=lambda:trace.append('cache'),_ownership=lambda:trace.append('ownership'),_observe_machinery=lambda:trace.append('machinery'))
    guard._commit=module.digest(guard._image());runtime._boundary=guard;module.sys=Hooks();module.sys.modules['entry']=entry_module
    module._CENSUS['cache_ref']=module.sys.path_importer_cache
    start=module._census_start;defaults=list(start.__defaults__)
    names=start.__code__.co_varnames[start.__code__.co_argcount-len(defaults):start.__code__.co_argcount]
    defaults[names.index('_add')]=module.sys.addaudithook;defaults[names.index('_audit')]=module.sys.audit;start.__defaults__=tuple(defaults)
    primary=module.BootstrapImportRejected('logical primary')
    def fault(reason,*args):trace.append(reason);raise primary
    guard._fault=fault;guard._audit_entry=MethodType(module.BootstrapImportBoundary._audit_entry,guard)
    def callback(event,args):module.BootstrapImportBoundary._audit(guard,event,args,object(),())
    module.sys.addaudithook(callback)
    return guard,runtime,trace,primary

class CensusTests(unittest.TestCase):
    def test_01_original_statements_preserved(self):
        def nodes(path):return {n.name:n for n in ast.parse(path.read_bytes()).body if type(n) in (ast.ClassDef,ast.FunctionDef)}
        old=nodes(OLD);new=nodes(BS)
        old_imports=[ast.dump(n) for n in ast.parse(OLD.read_bytes()).body if type(n) in (ast.Import,ast.ImportFrom) and not (type(n) is ast.Import and any(a.name=='faulthandler' for a in n.names))]
        self.assertEqual(old_imports,[ast.dump(n) for n in ast.parse(BS.read_bytes()).body if type(n) in (ast.Import,ast.ImportFrom)])
        for name,node in old.items():
            if name=='diagnostic_import_once':continue
            if name!='BootstrapImportBoundary':self.assertEqual(ast.dump(node),ast.dump(new[name]),name);continue
            old_methods={n.name:n for n in node.body if type(n) is ast.FunctionDef};new_methods={n.name:n for n in new[name].body if type(n) is ast.FunctionDef}
            self.assertEqual([ast.dump(n) for n in node.body if type(n) is not ast.FunctionDef],[ast.dump(n) for n in new[name].body if type(n) is not ast.FunctionDef])
            for method,original in old_methods.items():
                current=new_methods[method]
                if method=='_audit':
                    body=next(n for n in current.body if type(n) is ast.Try).body
                    self.assertEqual([ast.dump(n) for n in original.body],[ast.dump(n) for n in body])
                elif method=='_audit_entry':
                    body=next(n for n in current.body if type(n) is ast.Try).body
                    body=[n for n in body if not (type(n) is ast.Assign and type(n.value) is ast.Call and type(n.value.func) is ast.Name and n.value.func.id=='_cut')]
                    self.assertEqual([ast.dump(n) for n in original.body],[ast.dump(n) for n in body])
                else:self.assertEqual(ast.dump(original),ast.dump(current),method)
    def test_02_defaults_proof_and_zero_global_census_functions(self):
        module,sink=helper();self.assertTrue(proof_for(module,core))
        for name,fn in vars(module).items():
            if name.startswith('_census_') and type(fn) is FunctionType:
                self.assertFalse([op for op in dis.get_instructions(fn) if op.opname=='LOAD_GLOBAL'],name)
        fn=module._census_observer;original=fn.__defaults__;changed=list(original);changed[1]=(lambda:0.0,*original[1][1:]);fn.__defaults__=tuple(changed)
        with self.assertRaises(ValueError):proof_for(module,core)
        fn.__defaults__=original
        module._CENSUS={}
        with self.assertRaises(ValueError):proof_for(module,core)
    def test_03_exact_guard_prefix_and_physical_open_boundary(self):
        module,sink=helper();guard,runtime,trace,primary=guard_for(module)
        module.sys.audit('open','D:/allowed','r',0);self.assertEqual(module._CENSUS['entered'],0)
        module._census_start(runtime);physical=0
        for index in range(64):
            try:module.sys.audit('open','D:/allowed','r',0)
            except module.AuditCensusStop:
                self.assertEqual(index,63);break
            physical+=1
        state=module._CENSUS;self.assertEqual((state['entered'],state['passed'],state['observed'],physical),(64,64,64,63))
        self.assertFalse(state['active']);self.assertFalse(guard._busy);self.assertEqual(state['installed'],1)
        module.sys.audit('open','D:/allowed','r',0);self.assertEqual(state['passed'],64)
        rows=[json.loads(line)[1] for line in sink.getvalue().splitlines()]
        self.assertEqual([row['passed'] for row in rows],[0,1,8,16,24,32,40,48,56,64]);self.assertLessEqual(len(rows),12)
    def test_04_clock_io_failure_preserves_guard_primary(self):
        for failure_kind in ('clock','write','flush','dumps'):
            for rejected in (False,True):
                module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._census_start(runtime)
                error=OSError('observation fault');armed=[False]
                def fail(*args,**kwargs):raise error
                if failure_kind=='clock':
                    clock_fn=module._census_clock;defaults=clock_fn.__defaults__;changed=list(defaults);changed[1]=(fail,*defaults[1][1:]);clock_fn.__defaults__=tuple(changed)
                else:
                    emit=module._census_emit;defaults=emit.__defaults__;changed=list(defaults);roots=list(defaults[1]);roots[{'write':1,'flush':2,'dumps':3}[failure_kind]]=fail;changed[1]=tuple(roots);emit.__defaults__=tuple(changed)
                event='open';path='D:/protected/x' if rejected else 'D:/allowed'
                try:module.sys.audit(event,path,'r',0)
                except BaseException as caught:
                    if rejected:
                        self.assertIs(caught,primary)
                        with self.assertRaises(BaseException) as final:module._census_finish('import_error_before64',primary)
                        self.assertIs(final.exception,primary);self.assertIsInstance(primary.__cause__,BaseExceptionGroup)
                    else:self.assertIsInstance(caught,BaseExceptionGroup)
                else:self.fail('census observation fault was accepted')
                self.assertIn('cache',trace);self.assertIn('ownership',trace);self.assertFalse(guard._busy)
    def test_05_early_return_error_and_watchdog_absent(self):
        for returns in (True,False):
            module,sink=helper();guard,runtime,trace,primary=guard_for(module);error=LookupError('original import')
            def importer(name):
                if not returns:raise error
                return object()
            try:module.diagnostic_import_once(runtime,_importer=importer)
            except BaseException as caught:
                if returns:self.assertIsInstance(caught,module.AuditCensusStop);self.assertEqual(str(caught),'diagnostic_import_return_before64')
                else:self.assertIs(caught,error)
            else:self.fail('early import did not stop')
            self.assertFalse(module._CENSUS['active']);self.assertEqual(module._CENSUS['passed'],0)
        broken=[False];observation=OSError('final observation fault');sink=io.BytesIO()
        def writer(raw):
            if broken[0]:raise observation
            return sink.write(raw)
        module,unused=helper(write=writer);guard,runtime,trace,primary=guard_for(module);original=LookupError('import primary')
        def failed(name):broken[0]=True;raise original
        with self.assertRaises(LookupError) as caught:module.diagnostic_import_once(runtime,_importer=failed)
        self.assertIs(caught.exception,original);self.assertIsInstance(original.__cause__,BaseExceptionGroup)
        def leaves(error):
            self.assertIsNot(error,original)
            if isinstance(error,BaseExceptionGroup):
                for item in error.exceptions:leaves(item)
        leaves(original.__cause__)
        module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._CENSUS['installed']=1
        with self.assertRaises(BaseException):module._census_start(runtime)
        self.assertFalse(module._CENSUS['ever_started']);self.assertEqual(len(module.sys.hooks),1)
        node=next(n for n in ast.parse(BS.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='diagnostic_import_once')
        self.assertFalse(any(type(n) is ast.Name and n.id in ('_arm','_cancel','_IMPORT_FAULT') for n in ast.walk(node)))
    def test_06_inclusive_segments_and_rejections(self):
        module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._census_start(runtime);module.sys.audit('open','D:/allowed','r',0)
        buckets=module._CENSUS['buckets'];self.assertTrue(all(row[0]==1 and row[1]>=row[2]>=0 for row in buckets.values()))
        self.assertGreaterEqual(buckets['audit_body_inclusive'][1],buckets['entry_total'][1])
        self.assertGreaterEqual(buckets['entry_total'][1],sum(buckets[name][1] for name in module._CENSUS_PHASES))
        for path,mode in (('D:/protected/x','r'),('D:/allowed','w')):
            module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._census_start(runtime)
            with self.assertRaises(module.BootstrapImportRejected):module.sys.audit('open',path,mode,0)
            self.assertEqual(module._CENSUS['passed'],0);self.assertEqual(module._CENSUS['observed'],0)
        for foreign in (True,False):
            module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._census_start(runtime)
            if foreign:guard._creator=(guard._creator[0]+1,guard._creator[1])
            else:guard._busy=True
            with self.assertRaises(module.BootstrapImportRejected):module.sys.audit('open','D:/allowed','r',0)
            self.assertEqual(module._CENSUS['entered'],0);self.assertFalse(module._CENSUS['inflight'])
    def test_07_frame_and_exception_validation(self):
        parent=load(PARENT,'_census_parent_unit');module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._census_start(runtime)
        module.sys.audit('open','D:/allowed','r',0);raw=sink.getvalue();parsed=parent.parse_diagnostic_stderr(raw)
        self.assertEqual(len(parsed['census_frames']),2)
        for bad in (raw+raw.splitlines(keepends=True)[-1],raw.replace(b'"seq":1',b'"seq":2',1),b' '+raw):
            with self.assertRaises(AssertionError):parent.parse_diagnostic_stderr(bad)
        import copy
        for change in ({'reason':'begin'},{'passed':2,'entered':2,'observed':1},{'reason':'import_return_before64','active':True}):
            frame=copy.deepcopy(parsed['census_frames'][-1]);frame.update(change)
            with self.assertRaises(AssertionError):parent.validate_census_frame(frame)
        frame=copy.deepcopy(parsed['census_frames'][-1]);frame['seq']=3;frame['passed']=8;frame['entered']=8;frame['observed']=7
        frame['buckets']['cache'][1]=0.0;frame['buckets']['cache'][2]=0.0
        with self.assertRaises(AssertionError):parent.parse_diagnostic_stderr(raw+parent.canonical(('census',frame))+b'\n')
        tail=parent.parse_diagnostic_stderr(raw+b'["census",');self.assertIn(b'["census",',base64.b64decode(tail['non_stage_raw_base64']))
        module._CENSUS['seq']=12;module._census_emit('progress')
        with self.assertRaises(BaseExceptionGroup):module._census_raise(None)
        node=next(n for n in ast.walk(ast.parse(PROBE.read_bytes())) if type(n) is ast.FunctionDef and n.name=='image')
        context=dict(remaining=[48],native={'BaseExceptionGroup':BaseExceptionGroup})
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(PROBE),'exec'),context)
        error=ValueError('primary');error.__cause__=BaseExceptionGroup('audit census observation failed',[OSError('write')])
        image=context['image'](error);self.assertTrue(parent.validate_exception_images([image]));self.assertEqual(image['type'],'ValueError')
        error.__cause__=error;context['remaining']=[48];image=context['image'](error);parent.validate_exception_images([image])
    def test_08_real_observer_setter_guards(self):
        for attribute in ('__code__','__defaults__'):
            case=legacy.RuntimeHandoffTests('test_module_code_setter_is_atomically_rejected');case.setUp()
            try:
                guard=case.boundary_seed();target=case.bs._census_observer;old=getattr(target,attribute)
                replacement=(lambda:None).__code__ if attribute=='__code__' else (None,)
                with self.assertRaisesRegex(case.bs.BootstrapImportRejected,'helper_or_finder_function_mutation'):setattr(target,attribute,replacement)
                self.assertIs(getattr(target,attribute),old)
            finally:case.tearDown()
    def test_09_original_cache_globals_ownership_failures(self):
        for part in ('cache','global','ownership'):
            module,sink=helper();guard,runtime,trace,primary=guard_for(module);module._census_start(runtime)
            if part=='cache':guard._check_cache=lambda:(_ for _ in ()).throw(ValueError('cache drift'))
            elif part=='global':guard._global_bindings=(('missing',object(),None,None,None,None),)
            else:guard._ownership=lambda:(_ for _ in ()).throw(ValueError('owner drift'))
            with self.assertRaises(module.BootstrapImportRejected) as caught:module.sys.audit('open','D:/allowed','r',0)
            self.assertIs(caught.exception,primary);self.assertEqual(module._CENSUS['passed'],0)
    def test_10_codec_and_actual_manifest(self):
        parent=load(PARENT,'_census_transport_unit');code=parent.transport();prefix=code.partition(b'\nimport os as _bootstrap_os\n')[0]
        node=next(n for n in ast.walk(ast.parse(code)) if type(n) is ast.Call and type(n.func) is ast.Attribute and n.func.attr=='b85decode')
        import zlib,tokenize
        decoder=zlib.decompressobj(zdict=prefix);payload=decoder.decompress(base64.b85decode(node.args[0].value),131073)
        self.assertTrue(decoder.eof);self.assertFalse(decoder.unused_data or decoder.unconsumed_tail);self.assertLessEqual(len(payload),131072)
        original=parent.CORE.read_bytes()+b'\n'+parent.PROBE.read_bytes();expected=b'import builtins\n'+original.split(b'\nimport builtins\n',1)[1]
        lines=expected.decode().splitlines(keepends=True)
        for token in tokenize.tokenize(io.BytesIO(expected).readline):
            if token.type==tokenize.COMMENT:
                line,col=token.start;lines[line-1]=lines[line-1][:col]+' '*(token.end[1]-col)+lines[line-1][token.end[1]:]
        self.assertEqual(payload,''.join(lines).encode());self.assertEqual(compile(payload,'<pre_entry_payload>','exec'),compile(expected,'<pre_entry_payload>','exec'))
        plan=parent.manifest('discovery',code);self.assertEqual(plan['import_helper'],dict(path=str(BS),pin=parent.pin(BS.read_bytes())))
        samples=(b'x = 1 .real\ny = - - 2\n',b'x = "a" "b"  # note\n',b'if True:\n    x = (1 +\n         2)\n')
        for sample in samples:
            compact=parent.minify_prefix(sample)
            self.assertEqual([(t.type,t.string) for t in tokenize.tokenize(io.BytesIO(sample).readline)],[(t.type,t.string) for t in tokenize.tokenize(io.BytesIO(compact).readline)])
        command=[str(parent.EXE),'-P','-B','-s','-S','-c',code.decode(),'--pre-entry-lease',str(parent.OUT/'probe_import_discovery.plan.json'),'0'*64]
        command_line=parent.subprocess.list2cmdline(command)
        self.assertLessEqual(len(command_line.encode('utf-16-le'))//2,30000)

LEGACY_NODES=('test_module_code_setter_is_atomically_rejected','test_module_defaults_setter_is_atomically_rejected','test_class_code_setter_is_atomically_rejected','test_class_defaults_setter_is_atomically_rejected')
def load_tests(loader,tests,pattern):
    return unittest.TestSuite([loader.loadTestsFromTestCase(CensusTests),*(legacy.RuntimeHandoffTests(name) for name in LEGACY_NODES)])

if __name__=='__main__':unittest.main()
