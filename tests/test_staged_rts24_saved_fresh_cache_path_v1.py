"""Method-level equivalence and finite cost; no live audit/runtime is created."""
import ast
import builtins
import io
import importlib.util
import json
from pathlib import Path
import statistics
import time
from types import FunctionType,ModuleType,SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_cache_path_v1_non_authoritative'
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_timing_v1.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_cache_v1.py'
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v10.py'
spec=importlib.util.spec_from_file_location('_cache_path_core',ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v13.py')
core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)

def module(path,name):
    result=ModuleType(name);vars(result).update(__file__=str(path),_READ_FILE=core.read_file)
    exec(compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0),vars(result));return result

class TrackingCache(dict):
    def __init__(self,rows):super().__init__(rows);self.visited=[]
    def items(self):
        for key,value in super().items():self.visited.append(key);yield key,value

class CachePathTests(unittest.TestCase):
    def setUp(self):
        self.old=module(OLD,'_cache_path_old');self.new=module(NEW,'_cache_path_new')
        self.root=str(self.new.ROOT);self.runtime=str(self.new.EXE.parent)
        self.assertEqual(str(self.old.ROOT),self.root);self.assertEqual(str(self.old.EXE.parent),self.runtime)
    def fixture(self,helper,rows,before=(),tracking=False):
        cache=TrackingCache(rows) if tracking else dict(rows)
        helper.sys=SimpleNamespace(path_importer_cache=cache)
        return cache,SimpleNamespace(_cache_initial=tuple(before))
    def result(self,helper,rows,before=()):
        cache,guard=self.fixture(helper,rows,before,True)
        try:helper.BootstrapImportBoundary._check_cache(guard);outcome=('ok','')
        except BaseException as error:outcome=(type(error).__name__,str(error))
        return outcome,cache.visited
    def same(self,rows,before=(),accepted=None):
        old=self.result(self.old,rows,before);new=self.result(self.new,rows,before)
        self.assertEqual(old,new)
        if accepted is not None:self.assertEqual(new[0][0]=='ok',accepted)
        return new
    def test_01_only_cache_method_ast_changes(self):
        old=ast.parse(OLD.read_bytes());new=ast.parse(NEW.read_bytes())
        def strip(tree):
            cls=next(node for node in tree.body if type(node) is ast.ClassDef and node.name=='BootstrapImportBoundary')
            cls.body=[node for node in cls.body if not (type(node) is ast.FunctionDef and node.name=='_check_cache')]
            return ast.dump(tree)
        self.assertEqual(strip(old),strip(new))
    def test_02_paths_and_first_rejection_order(self):
        valid=[self.root,self.runtime,self.root+'/child',self.runtime+'/Lib',self.root.upper()+'/x',self.runtime.replace('\\','/')+'//Lib/./a',self.root+'/x/../y']
        invalid=[self.root+'-other/x',self.runtime+'-other/x','E:/outside','relative','D:relative','\\outside','//server/share/outside',b'D:/bytes',7]
        class Text(str):pass
        class PathTrap:
            def __fspath__(self):raise AssertionError('unexpected fspath')
        invalid.extend((Text(self.root),PathTrap()))
        for key in valid:self.same([(key,None)],accepted=True)
        for key in invalid:
            self.same([(key,None)],accepted=False)
            self.same([(key,None),(self.root+'/later',None)],accepted=False)
            self.same([(self.runtime+'/first',None),(key,None)],accepted=False)
    def test_03_initial_identity_remains_exact(self):
        class Equal:
            def __eq__(self,other):return True
        value=Equal();other=Equal();before=(('initial',value),)
        self.same([('initial',value)],before,True)
        self.same([],before,False)
        self.same([('initial',other)],before,False)
    def test_04_finder_type_and_original_path(self):
        key=str(Path(self.runtime)/'Lib'/'site-packages'/'example');finder=self.new.machinery.FileFinder(key)
        self.same([(key,None)],accepted=True);self.same([(key,finder)],accepted=True)
        self.same([(key,self.new.machinery.FileFinder(self.runtime+'/other'))],accepted=False)
        self.same([(key,object())],accepted=False)
        class Child(self.new.machinery.FileFinder):
            @property
            def path(self):raise AssertionError('subclass path must not be read')
        self.same([(key,object.__new__(Child))],accepted=False)
    def test_05_adjacent_calls_rescan_mutations(self):
        for helper in (self.old,self.new):
            key=str(Path(self.runtime)/'Lib');initial=object();finder=helper.machinery.FileFinder(key)
            cache,guard=self.fixture(helper,[('initial',initial),(key,finder)],[('initial',initial)])
            check=helper.BootstrapImportBoundary._check_cache;check(guard)
            finder.path=self.runtime+'/changed'
            with self.assertRaisesRegex(ValueError,'new importer cache kind differs'):check(guard)
            finder.path=key;cache['E:/new-outside']=None
            with self.assertRaisesRegex(ValueError,'importer cache key outside admitted roots'):check(guard)
            del cache['E:/new-outside'];cache['initial']=object()
            with self.assertRaisesRegex(ValueError,'predecessor importer cache changed'):check(guard)
    def test_06_explicit_constructor_counts_and_per_call_lifetime(self):
        cases=[([],0,0),([(self.root,None)],2,3),([(self.runtime,None)],4,3),([(self.runtime+'/p'+str(i),None) for i in range(8)],32,10),([('relative',None)],0,0)]
        for rows,expected_old,expected_new in cases:
            for helper,expected in ((self.old,expected_old),(self.new,expected_new)):
                calls=[]
                def counted(value):calls.append(value);return Path(value)
                helper.Path=counted;cache,guard=self.fixture(helper,rows)
                for _ in range(2):
                    try:helper.BootstrapImportBoundary._check_cache(guard)
                    except ValueError:pass
                self.assertEqual(len(calls),2*expected)
    def test_07_complete_source_helper_proof(self):
        node=next(n for n in ast.parse(PROBE.read_bytes()).body if type(n) is ast.FunctionDef and n.name=='validate_import_helper')
        context={**vars(core),'__builtins__':vars(builtins)}
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(PROBE),'exec',dont_inherit=True,optimize=0),context)
        proof=context['validate_import_helper'](self.new,compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0),tuple(vars(builtins).items()))
        self.assertTrue(proof)
    def test_08_three_round_real_path_cost(self):
        rounds=[];observations=[]
        def measure(helper,name,case,keys,scans):
            self.assertIs(helper.Path,Path);self.assertIs(helper.os.path,core.os.path)
            cache,guard=self.fixture(helper,[(key,helper.machinery.FileFinder(key)) for key in keys])
            check=helper.BootstrapImportBoundary._check_cache;started=time.perf_counter()
            for _ in range(scans):check(guard)
            seconds=time.perf_counter()-started
            return dict(variant=name,case=case,seconds=seconds,scans=scans,keys_per_scan=len(keys),key_visits=scans*len(keys),
                root_comparisons_derived=scans*len(keys)*(2 if case=='runtime32' else 1),explicit_path_calls_derived=scans*((4*len(keys)) if name=='old' and case=='runtime32' else (2*len(keys)) if name=='old' else len(keys)+2 if keys else 0))
        keys=[str(Path(self.runtime)/'Lib'/'site-packages'/('package_'+str(i))) for i in range(32)]
        for index,order in enumerate((('old','new'),('new','old'),('old','new'))):
            pair=[]
            for name in order:pair.append(measure(getattr(self,name),name,'runtime32',keys,80))
            rounds.append(dict(round=index+1,order=list(order),observations=pair))
        for case,keys in (('empty',[]),('one_ROOT',[self.root])):
            for name in ('old','new'):observations.append(measure(getattr(self,name),name,case,keys,20))
        old=[row['seconds'] for pair in rounds for row in pair['observations'] if row['variant']=='old'];new=[row['seconds'] for pair in rounds for row in pair['observations'] if row['variant']=='new']
        total_ratio=sum(new)/sum(old);median_ratio=statistics.median(new)/statistics.median(old)
        met=total_ratio<=.95 and median_ratio<=.95
        report=dict(authority='DRAFT_NONAUTHORITATIVE',method_fixture_only=True,rounds=rounds,small_cases=observations,
            total_ratio_new_over_old=total_ratio,median_ratio_new_over_old=median_ratio,threshold=.95,benchmark_threshold_met=met,
            current_constructor_counts_are_derived_from_separate_logical_oracle=True,cross_audit_cache=False,candidate_adopted=False,
            cold_children_launched=0,adapter_imports=0,actual_F=False,run_authority=False,formal_result=False,resource_admission=False)
        raw=json.dumps(report,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii');self.assertLessEqual(len(raw),65536)
        with (OUT/'metrics.json').open('xb') as stream:stream.write(raw)
        self.assertTrue(met,'predeclared 5 percent total and median cost benefit not established')

if __name__=='__main__':unittest.main()
