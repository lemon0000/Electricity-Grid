"""Frozen-reader equivalence and call counts; no native resource or adapter import."""
import ast
import builtins
import dis
from hashlib import sha256
import importlib.util
from pathlib import Path
import sys
from threading import get_ident
import time
from types import CodeType,FunctionType,ModuleType
import unittest

ROOT=Path(__file__).absolute().parents[1]
OLD=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v2.py'
NEW=ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_v3.py'
METRICS=[]
def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
base=load(ROOT/'tests/test_staged_rts24_saved_fresh_entry_namespace_v2.py','_frozen_namespace_regression')
base.HELPER=NEW

class NamespaceCacheRegression(base.EntryNamespaceTests):
    def probe_validator(self):
        path=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v3.py';tree=ast.parse(path.read_bytes())
        node=next(n for n in tree.body if type(n) is ast.FunctionDef and n.name=='validate_held_namespace_helper')
        context=dict(CodeType=CodeType,FunctionType=FunctionType,os=base.os,sys=sys,get_ident=get_ident,require=self.helper.require,ROOT=ROOT,ENTRY=self.helper.ENTRY)
        exec(compile(ast.Module(body=[node],type_ignores=[]),str(path),'exec',dont_inherit=True,optimize=0),context)
        original=context['validate_held_namespace_helper']
        def validator(helper,unit,native,inputs,compiler,executor,typ,namespace):return original(helper,unit,native,inputs,None,compiler,executor,typ,namespace)
        return validator,compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0)

class CodeCacheEquivalence(unittest.TestCase):
    def setUp(self):
        self.old=load(OLD,'_code_cache_old');self.new=load(NEW,'_code_cache_new')
    def counted(self,helper,module):
        calls=[0]
        def counting_sha(raw):calls[0]+=1;return sha256(raw)
        roots=list(helper._GRAPH_ROOTS);roots[-2]=counting_sha
        image,objects=helper.freeze_namespace_graph(module,tuple(roots))
        return image,objects,calls[0]
    def equivalent(self,module):
        a,ao,ac=self.counted(self.old,module);b,bo,bc=self.counted(self.new,module)
        self.assertEqual(a,b);self.assertEqual(len(ao),len(bo));self.assertTrue(all(x is y for x,y in zip(ao,bo)))
        self.assertLessEqual(bc,ac)
        return ac,bc
    def shared_module(self):
        shared=compile('answer=7','<shared>','exec')
        first=compile('first=1','<parent-a>','exec').replace(co_consts=(None,shared))
        second=compile('second=2','<parent-b>','exec').replace(co_consts=(None,shared))
        module=ModuleType('_cache_graph');module.a=first;module.b=second
        fn=FunctionType(shared,vars(module),'later');fn.__module__=module.__name__;module.z=fn
        return module,shared
    def test_shared_nested_code_and_later_visit_preserve_image_and_order(self):
        module,shared=self.shared_module();old,new=self.equivalent(module)
        self.assertEqual((old,new),(5,3));METRICS.append(dict(case='shared_dag',old_hash_calls=old,new_hash_calls=new))
    def test_equal_code_clones_are_not_identity_merged(self):
        code=compile('a=1','<clone>','exec');clone=code.replace()
        self.assertEqual(code,clone);self.assertIsNot(code,clone)
        module=ModuleType('_cache_clones');module.a=code;module.b=clone
        self.assertEqual(self.equivalent(module),(2,2))
        _,objects,_=self.counted(self.new,module);self.assertTrue(any(x is code for x in objects));self.assertTrue(any(x is clone for x in objects))
    def test_filename_and_firstlineno_still_affect_token(self):
        code=compile('a=1','<place-a>','exec');module=ModuleType('_cache_locations');module.a=code
        first=self.new.freeze_namespace_graph(module)[0]
        module.a=code.replace(co_filename='<place-b>');self.equivalent(module);self.assertNotEqual(first,self.new.freeze_namespace_graph(module)[0])
        module.a=code.replace(co_firstlineno=8);self.equivalent(module);self.assertNotEqual(first,self.new.freeze_namespace_graph(module)[0])
    def test_unsupported_nested_constant_still_rejects_and_next_call_is_fresh(self):
        good=compile('a=1','<good>','exec');bad=good.replace(co_consts=(None,{'bad':True}))
        root=good.replace(co_consts=(good,bad));module=ModuleType('_cache_bad');module.a=root
        messages=[]
        for helper in (self.old,self.new):
            with self.assertRaises(ValueError) as error:helper.freeze_namespace_graph(module)
            messages.append(str(error.exception))
        self.assertEqual(messages,['unsupported compiled constant']*2)
        module.a=good;self.assertEqual(self.equivalent(module),(1,1))
    def test_each_freeze_rebuilds_cache_and_observes_mutable_globals(self):
        module,shared=self.shared_module();module.values={'n':1}
        first=self.counted(self.new,module);second=self.counted(self.new,module)
        self.assertEqual(first[0],second[0]);self.assertEqual(first[2],second[2]);self.assertEqual(first[2],3)
        module.values['n']=2;third=self.counted(self.new,module);self.assertNotEqual(first[0],third[0]);self.assertEqual(third[2],3)
        self.equivalent(module)
    def test_reader_and_nested_code_keep_zero_global_opcodes(self):
        def check(code):
            self.assertFalse([x for x in dis.get_instructions(code) if x.opname in ('LOAD_GLOBAL','STORE_GLOBAL','DELETE_GLOBAL')])
            for value in code.co_consts:
                if type(value) is CodeType:check(value)
        check(self.new.freeze_namespace_graph.__code__)
    def test_observable_function_metadata_reads_are_preserved(self):
        module,shared=self.shared_module();records=[];active=[False];current=[None]
        def audit(event,args):
            if active[0] and event=='object.__getattr__' and len(args)>=2 and type(args[0]) is FunctionType and args[0].__globals__ is vars(module):current[0].append((id(args[0]),args[1]))
        sys.addaudithook(audit)
        try:
            for helper in (self.old,self.new):
                rows=[];current[0]=rows;active[0]=True
                helper.freeze_namespace_graph(module);active[0]=False;records.append(rows)
        finally:active[0]=False
        self.assertTrue(records[0]);self.assertEqual(records[0],records[1])
    def test_complete_actual_entry_matches_frozen_reader_and_counts(self):
        class Inputs:
            def __init__(self):self._resource=base.SimpleNamespace(pending=[1,2]);self._phase='LIVE'
            def entry(self):return self
            def source_bytes(self,name):return (ROOT/name).read_bytes()
            def close(self):self._resource.pending=[None,None];self._phase='CLOSED'
        helper=ModuleType('_cache_entry_helper');vars(helper).update(_INPUT_TYPE=Inputs)
        exec(compile(NEW.read_bytes(),str(NEW),'exec',dont_inherit=True,optimize=0),vars(helper))
        owner=helper.open_entry_namespace(Inputs(),helper.capture_helper_bindings())
        try:
            old,new=self.equivalent(owner.module);self.assertLess(new,old)
            timings=dict(old=[],new=[])
            for index in range(3):
                order=(('old',self.old),('new',self.new)) if index%2==0 else (('new',self.new),('old',self.old))
                for name,reader in order:
                    started=time.perf_counter();image,objects=reader.freeze_namespace_graph(owner.module);timings[name].append(time.perf_counter()-started)
                    self.assertEqual(image,owner._expected);self.assertTrue(all(a is b for a,b in zip(objects,owner._objects)))
            METRICS.append(dict(case='actual_entry',old_hash_calls=old,new_hash_calls=new,nodes=len(owner._expected),objects=len(owner._objects),wall_observations=timings,
                whole_chain_speedup_verified=False,actual_F=False,run_authority=False))
        finally:helper.LiveEntryNamespace.close(owner)

if __name__=='__main__':unittest.main()
