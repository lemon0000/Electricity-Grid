"""Full old-image oracle, local pin lifetime, and bounded method cost only."""
import ast
import builtins
import copy
import dis
from hashlib import sha256
import importlib.util
import io
import json
import os
from pathlib import Path
import statistics
import sys
from threading import RLock,get_ident
import time
from types import FunctionType,ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_image_pin_v1_non_authoritative'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census_v4.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_image_pin_v1.py'
CORE=ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v19.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v16.py'
POLICY=ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v5_non_authoritative/import_policy.json'

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
core=load(CORE,'_image_pin_core')
def helper(path,name):
    sink=io.BytesIO();module=ModuleType(name)
    vars(module).update(__file__=str(path),_READ_FILE=core.read_file,_CENSUS_IO=(time.perf_counter,sink.write,sink.flush,json.dumps))
    exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0),vars(module));return module
def proof_for(module):
    node=next(n for n in ast.parse(PROBE.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='validate_import_helper')
    context={**vars(core),'__builtins__':vars(builtins)}
    exec(compile(ast.Module(body=[node],type_ignores=[]),str(PROBE),'exec',dont_inherit=True,optimize=0),context)
    path=Path(module.__file__)
    return context['validate_import_helper'](module,compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0),tuple(vars(builtins).items()),module._CENSUS_IO)
def fixture(module,empty=False):
    profile=json.loads(POLICY.read_bytes());factory=next(n for n in ast.parse(OLD.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='open_bootstrap_import_boundary')
    loop=next(n for n in factory.body if type(n) is ast.For and type(n.target) is ast.Name and n.target.id=='name' and type(n.iter) is ast.Tuple)
    names=ast.literal_eval(loop.iter);rows=[]
    for name in names:
        value=vars(module)[name];is_fn=type(value) is FunctionType
        rows.append((name,value,value.__code__ if is_fn else None,value.__defaults__ if is_fn else None,module.canonical(value.__kwdefaults__) if is_fn else None,value.__closure__ if is_fn else None))
    own=tuple((n,f,f.__code__,f.__defaults__,module.canonical(f.__kwdefaults__),f.__closure__) for n,f in vars(module.BootstrapImportBoundary).items() if type(f) is FunctionType)
    attrs=tuple((sys,n,getattr(sys,n)) for n in ('addaudithook','audit','getprofile','gettrace','setprofile','settrace','modules','_current_frames','meta_path','path_hooks','path','path_importer_cache','version','executable','dont_write_bytecode'))
    attrs+=((builtins,'__import__',builtins.__import__),)
    attrs+=tuple((m,n,getattr(m,n)) for m,ns in ((module.importlib,('util','machinery','import_module')),(module.util,('find_spec','spec_from_loader')),(module.machinery,('ModuleSpec','FileFinder'))) for n in ns)
    return SimpleNamespace(_expected_bindings=(),_protected_functions=(),_adapter_graph=None,_runtime_bindings=(),_retention=(),_handoff_seen=0,
        _runtime=object(),_path_stage=0,_load_started=False,_cache_initial=tuple(sys.path_importer_cache.items()),_module_initial=tuple(sys.modules.items()),
        _policy_profile=profile,_admitted_paths=tuple(sys.path),_profile_raw=POLICY.read_bytes(),_creator=(os.getpid(),get_ident()),_namespace=vars(module),
        _global_bindings=() if empty else tuple(rows),_attribute_bindings=() if empty else attrs,_own_bindings=() if empty else own,
        _owner_commit='fixture-owner',_lock=RLock(),_codes=(fixture.__code__,),_numpy_path='fixture-numpy',_numpy_state=None,
        _paths=tuple(profile['protected_open_roots'].values()),_event_sets=(tuple(profile['process_events']),tuple(profile['process_event_prefixes']),tuple(profile['mutation_events'])),
        _import_machinery=(tuple(map(id,sys.meta_path)),tuple(map(id,sys.path_hooks)),tuple(sys.path),id(sys.path_importer_cache),id(sys.modules)),
        _machinery_base=(tuple(sys.meta_path),tuple(sys.path_hooks),tuple(sys.path),sys.meta_path,sys.path_hooks,sys.path,sys.path_importer_cache,sys.modules,module.importlib,module.util,module.machinery),
        _finder_plan=(),_finder_bindings=(),_finder_authenticated=(),_observed_stage=0,_authenticated_stage=0,
        _state=('ACTIVE',True,0,1,0,0,False,''),_adapter=None,_adapter_bindings=(),_source_raw=None,_failure=None,_first_error=None)
def logical_guard(module):
    proof=proof_for(module);f=fixture(module);runtime=SimpleNamespace(_boundary_bindings=(None,)*4+(proof,))
    runtime._resource=SimpleNamespace(owner=runtime);runtime._namespace=SimpleNamespace(module=sys)
    f._runtime=runtime;f._expected_bindings=proof;f._policy_profile={**f._policy_profile,'allowed_entry_module':{'name':'sys'}}
    token=object()
    def callback(event,args):return None
    f._owner=(f._creator,callback,token,callback.__code__)
    f._owner_commit=module.digest((f._creator,id(callback),id(callback.__code__),id(token)))
    f._protected_functions=tuple(v for _,_,v,meta in proof if meta is not None)+(callback,)
    f._busy=False;f._internal=None
    guard=object.__new__(module.BootstrapImportBoundary)
    for n,v in vars(f).items():object.__setattr__(guard,n,v)
    object.__setattr__(guard,'_commit',module.digest(guard._image()))
    return guard,proof,token

class ImagePinTests(unittest.TestCase):
    def setUp(self):
        self.old=helper(OLD,'_image_pin_old');self.new=helper(NEW,'_image_pin_new');self.f=fixture(self.new)
        self.before=self.old.BootstrapImportBoundary._image;self.after=self.new.BootstrapImportBoundary._image
    def equal(self,f=None):
        f=self.f if f is None else f;a=self.before(f);b=self.after(f)
        self.assertEqual(a,b);self.assertEqual(self.old.canonical(a),self.new.canonical(b));self.assertEqual(self.old.digest(a),self.new.digest(b));return b
    def test_01_only_image_ast_changes(self):
        def stripped(path):
            tree=ast.parse(path.read_bytes());cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
            cls.body=[n for n in cls.body if not (type(n) is ast.FunctionDef and n.name=='_image')];return ast.dump(tree)
        self.assertEqual(stripped(OLD),stripped(NEW))
    def test_02_complete_image_and_canonical_oracle(self):
        self.equal();self.equal(fixture(self.new,True))
        for phase in ('NEW','INSTALLING','ACTIVE','CLOSED','FAULTED'):
            self.f._state=(phase,True,0,1,0,0,phase=='CLOSED','fault' if phase=='FAULTED' else '')
            for stage in (0,1,2):
                self.f._observed_stage=stage;self.f._authenticated_stage=2 if stage==2 else 0;self.equal()
        self.f._numpy_state=(object(),False);self.f._adapter=object();self.f._adapter_bindings=(('run',fixture,fixture.__code__),)
        self.f._source_raw=self.new.canonical({'source':'bookend'});self.f._retention=(('held',object()),);self.equal()
    def test_03_equal_distinct_empty_large_and_nonbytes_global_kw(self):
        value=bytes(bytearray(b'null'));self.assertIsNot(value,b'null')
        for raw in (b'',value,b'long'*16384):
            self.f._profile_raw=raw;self.f._source_raw=bytes(bytearray(raw))
            self.f._global_bindings=tuple((n,v,c,d,raw if i%3==0 else b'{"k":1}' if i%3==1 else None,k) for i,(n,v,c,d,kw,k) in enumerate(self.f._global_bindings))
            self.f._own_bindings=tuple((n,v,c,d,bytes(bytearray(raw)) if i%2 else b'{}',k) for i,(n,v,c,d,kw,k) in enumerate(self.f._own_bindings));self.equal()
    def test_04_each_image_dependency_changes_without_stale_commit(self):
        node=next(n for n in ast.walk(ast.parse(OLD.read_bytes())) if type(n) is ast.FunctionDef and n.name=='_image')
        fields={n.attr for n in ast.walk(node) if type(n) is ast.Attribute and type(n.value) is ast.Name and n.value.id=='self'}
        baseline=self.new.digest(self.equal());seen=set()
        rows={'_global_bindings':lambda v:v+(('extra',object(),None,None,b'null',None),),
            '_attribute_bindings':lambda v:v+((sys,'extra',object()),),'_own_bindings':lambda v:v+(('extra',fixture,fixture.__code__,None,b'null',None),),
            '_codes':lambda v:v+(self.equal.__func__.__code__,),'_adapter_bindings':lambda v:(('extra',fixture,fixture.__code__),),
            '_numpy_state':lambda v:(object(),False),'_source_raw':lambda v:b'source','_profile_raw':lambda v:v+b' ',
            '_creator':lambda v:(v[0]+1,v[1]),'_admitted_paths':lambda v:v+('extra',),'_paths':lambda v:v+('extra',),
            '_event_sets':lambda v:(v[0]+('extra',),*v[1:]),'_import_machinery':lambda v:v+('extra',),
            '_state':lambda v:('FAULTED',*v[1:7],'fault'),'_owner_commit':lambda v:v+'changed','_numpy_path':lambda v:v+'changed'}
        id_fields={'_expected_bindings','_protected_functions','_adapter_graph','_runtime_bindings','_retention','_runtime','_cache_initial','_module_initial','_policy_profile','_namespace','_lock','_machinery_base','_finder_plan','_finder_bindings','_finder_authenticated','_adapter','_failure','_first_error'}
        for name in sorted(fields):
            previous=getattr(self.f,name)
            value=object() if name in id_fields else rows[name](previous) if name in rows else not previous if type(previous) is bool else previous+1
            setattr(self.f,name,value);current=self.equal();self.assertNotEqual(self.new.digest(current),baseline,name);setattr(self.f,name,previous);seen.add(name)
        self.assertEqual(seen,fields);self.assertEqual(self.new.digest(self.equal()),baseline)
    def test_05_mutable_fallback_and_original_exceptions(self):
        class BytesChild(bytes):
            def __hash__(self):raise AssertionError('subclass must not enter memo')
        def install(raw):self.f._own_bindings=(('a',fixture,fixture.__code__,None,raw,None),('b',fixture,fixture.__code__,None,raw,None))
        for raw in (bytearray(b'a'),memoryview(bytearray(b'a')),BytesChild(b'a')):
            install(raw);before=self.new.digest(self.equal())
            if type(raw) in (bytearray,memoryview):raw[0]=ord('b');self.assertNotEqual(before,self.new.digest(self.equal()))
        for raw in (None,4,'text'):
            install(raw);outcomes=[]
            for method in (self.before,self.after):
                try:method(self.f)
                except BaseException as error:outcomes.append((type(error),str(error)))
            self.assertEqual(len(outcomes),2);self.assertEqual(outcomes[0],outcomes[1])
    def test_06_pin_dicts_remain_independent(self):
        image=self.equal();pins=[]
        def walk(v):
            if type(v) is dict:pins.append(v)
            elif type(v) in (tuple,list):
                for item in v:walk(item)
        walk(image);self.assertEqual(len({id(v) for v in pins}),len(pins))
        original=copy.deepcopy(pins[1:]);pins[0]['sha256']='changed';self.assertEqual(pins[1:],original);self.equal()
    def test_07_pin_order_unique_failures_and_per_call_lifetime(self):
        def calls(module,method):
            original=module.pin;seen=[]
            def counted(raw):seen.append(raw);return original(raw)
            module.pin=counted
            try:
                method(self.f);first=seen[:];method(self.f);self.assertEqual(seen,first+first)
            finally:module.pin=original
            return first
        old=calls(self.old,self.before);new=calls(self.new,self.after);expected=[];unique=set()
        for raw in old:
            if type(raw) is not bytes or raw not in unique:expected.append(raw)
            if type(raw) is bytes:unique.add(raw)
        self.assertEqual(new,expected);self.assertLess(len(new),len(old))
        primary=OSError('first unique value')
        for module,method in ((self.old,self.before),(self.new,self.after)):
            original=module.pin
            def reject(raw):
                if raw==b'null':raise primary
                return original(raw)
            module.pin=reject
            try:
                with self.assertRaises(OSError) as caught:method(self.f)
                self.assertIs(caught.exception,primary)
            finally:module.pin=original
    def test_08_helper_proof_bookends_setter_classifier_and_finder(self):
        guard,proof,token=logical_guard(self.new);self.assertIs(guard._entry(),guard)
        self.assertTrue(any(n=='dict' and v is dict for ctx,n,v,meta in proof))
        for event in ('object.__setattr__','object.__delattr__'):
            for attr in ('__code__','__defaults__','__kwdefaults__'):
                g,p,t=logical_guard(self.new);prior=g._commit
                with self.assertRaisesRegex(self.new.BootstrapImportRejected,'helper_or_finder_function_mutation'):g._audit(event,(self.new.pin,attr),t,p)
                self.assertEqual(g._state[0],'FAULTED');self.assertEqual(g._commit,prior);self.assertNotEqual(prior,self.new.digest(g._image()))
        g,p,t=logical_guard(self.new);object.__setattr__(g,'_load_started',True)
        with self.assertRaisesRegex(ValueError,'original import guard required'):g._audit_entry()
        g,p,t=logical_guard(self.new);fn=self.new.pin;previous=fn.__kwdefaults__;fn.__kwdefaults__={'drift':1}
        try:
            with self.assertRaises(ValueError):g._entry()
            fn.__kwdefaults__['drift']=2
            with self.assertRaises(ValueError):g._entry()
        finally:fn.__kwdefaults__=previous
        def finder():return None
        g,p,t=logical_guard(self.new);object.__setattr__(g,'_observed_stage',2);object.__setattr__(g,'_authenticated_stage',2)
        object.__setattr__(g,'_finder_authenticated',((finder,finder.__code__,None,finder.__globals__,finder.__code__,0),));g._check_finder_authentication()
        finder.__defaults__=(None,)
        with self.assertRaisesRegex(self.new.BootstrapImportRejected,'finder_authentication'):g._check_finder_authentication()
    def test_09_three_round_real_image_digest_cost(self):
        self.equal();rounds=[];small=[]
        def measure(module,method,name,f,scans):
            started=time.perf_counter()
            for _ in range(scans):module.digest(method(f))
            return dict(variant=name,seconds=time.perf_counter()-started,scans=scans)
        for index,order in enumerate((('old','new'),('new','old'),('old','new'))):
            observations=[measure(getattr(self,name),self.before if name=='old' else self.after,name,self.f,128) for name in order]
            rounds.append(dict(round=index+1,order=list(order),observations=observations))
        f=fixture(self.new,True)
        for name in ('old','new'):small.append(measure(getattr(self,name),self.before if name=='old' else self.after,name,f,20))
        old=[r['seconds'] for pair in rounds for r in pair['observations'] if r['variant']=='old'];new=[r['seconds'] for pair in rounds for r in pair['observations'] if r['variant']=='new']
        total=sum(new)/sum(old);median=statistics.median(new)/statistics.median(old);met=total<=.95 and median<=.95
        report=dict(authority='DRAFT_NONAUTHORITATIVE',method_fixture_only=True,rounds=rounds,small_cases=small,
            fixture_rows=dict(global_bindings=len(self.f._global_bindings),own_bindings=len(self.f._own_bindings),attribute_bindings=len(self.f._attribute_bindings)),
            total_ratio_new_over_old=total,median_ratio_new_over_old=median,threshold=.95,benchmark_threshold_met=met,
            candidate_adopted=False,cross_call_cache=False,cold_children_launched=0,adapter_imports=0,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
        raw=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii');self.assertLessEqual(len(raw),65536)
        with (OUT/'metrics.json').open('xb') as stream:stream.write(raw)
        self.assertTrue(met,'predeclared 5 percent total and median benefit not established')

if __name__=='__main__':unittest.main()
