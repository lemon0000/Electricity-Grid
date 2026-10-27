"""Cache-parts equivalence, mutation, bounded cost and complete-import protocol."""
import ast
import copy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import time
from types import SimpleNamespace
import unittest

ROOT=Path(__file__).absolute().parents[1]
OLD=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_full_v1.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_cache_parts_full_v1.py'
OUT=ROOT/'results/tables/staged_rts24_saved_fresh_ful_v3_non_authoritative'
METRICS=None

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

fixture=load(ROOT/'tests/test_staged_rts24_saved_fresh_full_import_v1.py','_cache_parts_full_fixture')
fixture.NEW=NEW;fixture.PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v23.py'
fixture.core=load(ROOT/'experiments/staged_rts24_saved_fresh_pre_entry_lease_v26.py','_cache_parts_core')
fixture.parent=load(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v23.py','_cache_parts_parent')

def old_helper():
    saved=fixture.NEW
    try:fixture.NEW=OLD;return fixture.helper()
    finally:fixture.NEW=saved

def outcome(module,before,current):
    module.sys=SimpleNamespace(path_importer_cache=current);guard=SimpleNamespace(_cache_initial=tuple(before.items()))
    try:return ('return',module.BootstrapImportBoundary._check_cache(guard))
    except BaseException as error:return ('error',type(error),str(error))

def oracle(module,key):
    if type(key) is not str or not os.path.isabs(key):return False
    for root in (module.ROOT,module.EXE.parent):
        try:Path(key).relative_to(root)
        except ValueError:continue
        return True
    return False

def cases(module):
    roots=(str(module.ROOT),str(module.EXE.parent));inside=[];outside=[]
    for root in roots:
        inside.extend((root,root+'/x',root+'/.',root+'//X/y',root+'/x/../leaf',root+'/../sibling',root+'/\u0130/\u7f51\u683c',root+'/nul\x00part'))
        outside.extend((root+'_sibling',str(Path(root).parent),root.replace('D:','E:',1),'D:relative','/rooted_without_drive'))
    outside.extend(('', '.', '..', '//server/share/x', '\\\\?\\D:\\outside', b'D:/outside',None,42))
    result=[]
    for expected,values in ((True,inside),(False,outside)):
        for value in values:
            variants=(value,value.replace('\\','/'),value.replace('/','\\'),value.swapcase()) if type(value) is str else (value,)
            result.extend((v,expected) for v in variants)
    class Text(str):pass
    result.append((Text(str(module.ROOT)+'/x'),False))
    return result

def benchmark_cache(module):
    before={'C:/held_origin/predecessor_'+str(i):object() for i in range(11)};current=dict(before)
    roots=(str(module.ROOT),str(module.EXE.parent))
    for i in range(37):
        key=roots[i%2]+'/fixture_'+str(i)+'/nested/segment';finder=module.machinery.FileFinder(key);finder.path=key
        current[key]=None if i%3==0 else finder
    return before,current

class CachePartsFullTests(fixture.FullImportTests):
    def test_01_only_wrapper_body_and_held_defaults(self):
        a=ast.parse(OLD.read_bytes());b=ast.parse(NEW.read_bytes())
        for tree in (a,b):
            cls=next(n for n in tree.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
            method=next(n for n in cls.body if type(n) is ast.FunctionDef and n.name=='_check_cache');method.body=[ast.Pass()]
        self.assertEqual(ast.dump(a),ast.dump(b));module=fixture.helper();self.assertTrue(fixture.proof_for(module))
        inventory=copy.deepcopy(fixture.graph.ADMITTED_INVENTORY);self.assertTrue(fixture.graph.validate_inventory(inventory))
        name='src.staged_rts24_saved_fresh_adoption_v1'
        for field in ('factory','<computed>','source_pin'):
            changed=copy.deepcopy(inventory)
            if field=='source_pin':changed[name]['pin']['sha256']='0'*64
            else:changed[name]['import_time_calls'][0]['callee']=field
            with self.assertRaises(AssertionError):fixture.graph.validate_inventory(changed)
    def test_07_windows_lexical_oracle_and_complete_outcomes(self):
        old=old_helper();new=fixture.helper();before={'C:/held/predecessor':object()}
        checked=0
        for key,expected in cases(old):
            self.assertIs(oracle(old,key),expected,repr(key))
            current={**before,key:None};a=outcome(old,before,current);b=outcome(new,before,current)
            self.assertEqual(a,b,repr(key));self.assertEqual(a[0]=='return',expected,repr(key));checked+=1
        self.assertEqual(checked,128)
    def test_08_each_event_identity_finder_mutation_and_error_order(self):
        old=old_helper();new=fixture.helper();key=str(old.ROOT)+'/valid';held=object();before={'C:/held/predecessor':held}
        finder=old.machinery.FileFinder(key);finder.path=key;valid={**before,key:finder}
        for module in (old,new):self.assertEqual(outcome(module,before,valid),('return',None))
        mutations=[({key:finder},'predecessor importer cache changed'),({**valid,'C:/held/predecessor':object()},'predecessor importer cache changed'),({**valid,str(old.ROOT)+'_outside':None},'importer cache key outside admitted roots'),({**before,key:object()},'new importer cache kind differs')]
        for current,message in mutations:
            a=outcome(old,before,current);b=outcome(new,before,current);self.assertEqual(a,b);self.assertEqual(a[2],message)
        finder.path=key+'/changed'
        for module in (old,new):self.assertEqual(outcome(module,before,valid)[2],'new importer cache kind differs')
        finder.path=key;outside=str(old.ROOT)+'_outside';a=outcome(old,before,{**before,outside:object(),key:object()});b=outcome(new,before,{**before,outside:object(),key:object()});self.assertEqual(a,b);self.assertEqual(a[2],'importer cache key outside admitted roots')
        a=outcome(old,before,{**before,key:object(),outside:object()});b=outcome(new,before,{**before,key:object(),outside:object()});self.assertEqual(a,b);self.assertEqual(a[2],'new importer cache kind differs')
        marker=OSError('finder path comparison primary')
        class RaisingPath:
            def __eq__(self,other):raise marker
        finder.path=RaisingPath()
        for module in (old,new):
            module.sys=SimpleNamespace(path_importer_cache=valid)
            with self.assertRaises(OSError) as caught:module.BootstrapImportBoundary._check_cache(SimpleNamespace(_cache_initial=tuple(before.items())))
            self.assertIs(caught.exception,marker)
    def test_09_metadata_and_no_state_across_calls(self):
        module=fixture.helper();before,current=benchmark_cache(module);module.sys=SimpleNamespace(path_importer_cache=current);guard=SimpleNamespace(_cache_initial=tuple(before.items()))
        original=dict(vars(guard));module.BootstrapImportBoundary._check_cache(guard);self.assertEqual(vars(guard),original)
        current[str(module.ROOT)+'_outside']=None
        with self.assertRaisesRegex(ValueError,'importer cache key outside admitted roots'):module.BootstrapImportBoundary._check_cache(guard)
        self.assertEqual(vars(guard),original)
        module=fixture.helper();method=module.BootstrapImportBoundary._check_cache;original_code=method.__code__;method.__code__=(lambda self:None).__code__
        with self.assertRaises(ValueError):fixture.proof_for(module)
        method.__code__=original_code;self.assertTrue(fixture.proof_for(module))
    def test_10_three_round_bounded_method_cost(self):
        global METRICS
        old=old_helper();new=fixture.helper();before,current=benchmark_cache(old);old.sys=new.sys=SimpleNamespace(path_importer_cache=current)
        guard=SimpleNamespace(_cache_initial=tuple(before.items()));snapshot=tuple(current.items());rounds=[]
        for order in (('old','new'),('new','old'),('old','new')):
            row={}
            for arm in order:
                method=(old if arm=='old' else new).BootstrapImportBoundary._check_cache;start=time.perf_counter()
                for _ in range(32):self.assertIsNone(method(guard))
                row[arm]=time.perf_counter()-start
                self.assertEqual(tuple(current.items()),snapshot)
            rounds.append(row)
        total_old=sum(row['old'] for row in rounds);total_new=sum(row['new'] for row in rounds)
        total_ratio=total_new/total_old;median_ratio=sorted(row['new'] for row in rounds)[1]/sorted(row['old'] for row in rounds)[1]
        METRICS=dict(accepted=total_ratio<=.90 and median_ratio<=.90,authority='DRAFT_NONAUTHORITATIVE',rounds=rounds,orders=[['old','new'],['new','old'],['old','new']],iterations_per_arm_per_round=32,method_calls=192,lexical_cases=128,unit_method_calls_upper_bound=512,
            predecessor_items=11,new_items=37,total_items=48,keys=list(current),total_old_seconds=total_old,total_new_seconds=total_new,total_ratio=total_ratio,median_ratio=median_ratio,threshold=.90,
            old_source_sha256=sha256(OLD.read_bytes()).hexdigest(),new_source_sha256=sha256(NEW.read_bytes()).hexdigest(),actual_F=False,resource_admission=False,formal_result=False,scientific_evidence_adopted=False,candidate_adopted=False)
        self.assertLessEqual(total_ratio,.90);self.assertLessEqual(median_ratio,.90)

if __name__=='__main__':unittest.main()
