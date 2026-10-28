"""Synthetic project-object graph oracles; no audited source modules execute."""
import ast
import builtins
import copy
import dataclasses
from importlib.machinery import ModuleSpec,SourceFileLoader
import importlib.util
from pathlib import Path
import sys
import tempfile
from types import ModuleType,SimpleNamespace,FunctionType,MappingProxyType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('_producer_graph_under_test',ROOT/'experiments/staged_rts24_saved_fresh_producer_project_graph_v1.py')
graph=importlib.util.module_from_spec(spec);spec.loader.exec_module(graph)


class ProducerProjectGraphTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix='producer_graph_');self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.modules={};self.sources={};self.registry=dict(sys.modules)

    def module(self,suffix,raw):
        name='_producer_graph_fixture_'+suffix;relative=suffix+'.py';module=ModuleType(name)
        allowed=('object','type','int','str','bool','dict','list','tuple','set','frozenset','len','property','staticmethod','classmethod',
            '__build_class__','__import__','getattr','setattr','super','hash','NotImplemented','ValueError','RuntimeError')
        module.__dict__.update(__file__=str(self.root/relative),__package__='',__spec__=None,__loader__=None,
            __builtins__={key:vars(builtins)[key] for key in allowed})
        scope=patch.dict(sys.modules,{name:module});scope.start();self.addCleanup(scope.stop)
        exec(compile(raw,str(self.root/relative),'exec',dont_inherit=True,optimize=0),vars(module),vars(module))
        self.modules[name]=module;self.sources[name]=(relative,raw);self.registry[name]=module
        return module

    def capture(self,**kwargs):return graph.capture(self.modules,self.sources,self.root,registry=self.registry,**kwargs)

    def ordinary(self):
        return self.module('a',b'VALUE=[1,2]\ndef leaf(value=VALUE,*,limit=2):\n    return len(value)+limit\n')

    def test_01_cross_module_aliases_cycles_and_no_function_calls(self):
        left=self.module('a',b'def leaf():\n    raise RuntimeError("project code must not be called")\n')
        right=self.module('b',b'holder=[]\nholder.append(holder)\n')
        left.other=right;right.other=left;right.alias=left.leaf;right.second=left.leaf
        snapshot=self.capture();report=graph.check(snapshot)
        self.assertEqual(report['modules'],2);self.assertTrue(report['structure_and_identity_stable'])
        self.assertEqual(sum(item is left.leaf for item in snapshot._objects),1)
        self.assertTrue(any(item is right.holder for item in snapshot._objects))
        self.assertIn(('not_implemented',),snapshot._graph[1])
        self.module('oracle_a',b'CONST=(1,)\nclass Box:\n    def method(self,value=CONST):\n        return func(value)\ndef func(value=CONST):\n    return len(value)\n')
        self.module('oracle_b',b'from _producer_graph_fixture_oracle_a import Box,func\ndef use(value):\n    return func(value)\n')
        snapshot=self.capture();expected_functions=set();expected_classes=set();expected_globals=set();defaults={}
        self.assertEqual({row[1] for row in snapshot._graph[1] if row[0]=='project_module'},set(self.sources))
        self.assertEqual({name for name,_ in snapshot._graph[0]},set(self.sources))
        # Independent fixture oracle: AST lexical names/defaults, without dis or graph traversal.
        for name,(_,raw) in self.sources.items():
            tree=ast.parse(raw)
            functions=[]
            for item in tree.body:
                if type(item) is ast.FunctionDef:functions.append((item.name,item))
                elif type(item) is ast.ClassDef:
                    expected_classes.add((name,item.name))
                    functions.extend((item.name+'.'+child.name,child) for child in item.body if type(child) is ast.FunctionDef)
            for qualified,node in functions:
                expected_functions.add((name,qualified));defaults[name,qualified]=[item.id for item in node.args.defaults]
                local={arg.arg for arg in node.args.posonlyargs+node.args.args+node.args.kwonlyargs}
                local.update(item.id for statement in node.body for item in ast.walk(statement) if type(item) is ast.Name and type(item.ctx) is ast.Store)
                names={item.id for statement in node.body for item in ast.walk(statement) if type(item) is ast.Name and type(item.ctx) is ast.Load}-local
                for identifier in names:expected_globals.add((name,qualified,identifier,'global' if identifier in vars(self.modules[name]) else 'builtin'))
        observed_functions={};observed_classes=set()
        for row in snapshot._graph[1]:
            if row[0]=='project_function':observed_functions[snapshot._objects[row[1][1]].__name__,row[3]]=row
            elif row[0]=='project_class':
                observed_classes.add((snapshot._objects[row[1][1]].__name__,row[3]))
                self.assertEqual(snapshot._objects[row[4][1]],(object,))
        self.assertEqual(set(observed_functions),expected_functions);self.assertEqual(observed_classes,expected_classes)
        self.assertEqual({row[:4] for row in snapshot._graph[5]},expected_globals)
        for owner,_,identifier,kind,edge in snapshot._graph[5]:
            namespace=vars(self.modules[owner]);expected=namespace[identifier] if kind=='global' else namespace['__builtins__'][identifier]
            self.assertEqual(edge[0],'ref');self.assertIs(snapshot._objects[edge[1]],expected)
        for key,names in defaults.items():
            row=observed_functions[key]
            if not names:self.assertEqual(row[5],('NoneType',None));continue
            default_node=snapshot._graph[1][row[5][1]];self.assertEqual(default_node[0],'tuple');self.assertEqual(len(default_node[1]),len(names))
            for edge,name in zip(default_node[1],names):self.assertIs(snapshot._objects[edge[1]],vars(self.modules[key[0]])[name])
        expected_fallbacks={(name,identifier) for name,_,identifier,kind in expected_globals if kind=='builtin'}
        self.assertEqual({row[:2] for row in snapshot._graph[3]},expected_fallbacks)
        for owner,identifier,edge in snapshot._graph[3]:
            self.assertEqual(edge[0],'ref');self.assertIs(snapshot._objects[edge[1]],vars(self.modules[owner])['__builtins__'][identifier])
        importer='_producer_graph_fixture_oracle_b';original=self.modules['_producer_graph_fixture_oracle_a']
        module_row=next(row for row in snapshot._graph[1] if row[0]=='project_module' and row[1]==importer)
        aliases={key[1]:edge for key,edge in module_row[3]}
        self.assertIs(snapshot._objects[aliases['Box'][1]],original.Box);self.assertIs(snapshot._objects[aliases['func'][1]],original.func)

    def test_02_code_defaults_annotations_and_function_attributes_drift(self):
        for mode in ('code','defaults','kwdefaults','annotations','attributes'):
            with self.subTest(mode=mode):
                module=self.ordinary();snapshot=self.capture();fn=module.leaf
                if mode=='code':fn.__code__=fn.__code__.replace(co_firstlineno=999)
                elif mode=='defaults':fn.__defaults__[0].append(3)
                elif mode=='kwdefaults':fn.__kwdefaults__['limit']=3
                elif mode=='annotations':fn.__annotations__['return']=str
                else:fn.changed=True
                with self.assertRaises(ValueError):graph.check(snapshot)

    def test_03_foreign_project_globals_are_not_external_identity(self):
        self.ordinary();foreign=ModuleType('_foreign_project');foreign.__file__=str(self.root/'foreign.py')
        exec(compile('def foreign():\n    return 1\n',foreign.__file__,'exec'),vars(foreign))
        next(iter(self.modules.values())).foreign=foreign.foreign
        with self.assertRaisesRegex(ValueError,'foreign project function globals'):self.capture()

    def test_04_registry_missing_alias_and_replacement_are_rejected(self):
        for mode in ('missing','alias','replace'):
            with self.subTest(mode=mode):
                module=self.ordinary();snapshot=self.capture();name=module.__name__
                if mode=='missing':self.registry.pop(name)
                elif mode=='alias':self.registry[name+'_alias']=module
                else:self.registry[name]=ModuleType(name)
                with self.assertRaises(ValueError):graph.check(snapshot)
                self.registry={**dict(sys.modules),**self.modules}

    def test_05_module_spec_loader_origin_and_package_drift(self):
        for mode in ('spec','loader','package','origin','loader_state','cached','initializing','extra_loader_state','namespace_state'):
            with self.subTest(mode=mode):
                module=self.ordinary();module.__loader__=SourceFileLoader(module.__name__,module.__file__)
                module.__spec__=ModuleSpec(module.__name__,module.__loader__,origin=module.__file__)
                module.__spec__.loader_state={'x':1};module.__loader__.extra={'x':1}
                if mode=='namespace_state':module.__spec__.loader_state=SimpleNamespace(x=1);module.Alias=module.__spec__.loader_state
                snapshot=self.capture()
                if mode=='spec':module.__spec__.origin='other'
                elif mode=='loader':module.__loader__.path='other'
                elif mode=='package':module.__package__='other'
                elif mode=='origin':module.__file__=str(self.root/'other.py')
                elif mode=='loader_state':module.__spec__.loader_state['x']=2
                elif mode=='cached':module.__spec__._cached='other'
                elif mode=='initializing':module.__spec__._initializing=True
                elif mode=='extra_loader_state':module.__loader__.extra['x']=2
                else:module.__spec__.loader_state.x=2
                with self.assertRaises(ValueError):graph.check(snapshot)
        module=self.module('conditional',b'def call():\n    return ext.leaf()\n')
        external=ModuleType('_producer_graph_external');external.__file__=str(self.root.parent/'external_graph.py')
        external.__loader__=SourceFileLoader(external.__name__,external.__file__)
        external.__spec__=ModuleSpec(external.__name__,external.__loader__,origin=external.__file__)
        external.__spec__.loader_state={'x':1};exec(compile('def leaf():\n    return 1\n',external.__file__,'exec'),vars(external))
        self.registry[external.__name__]=external;module.ext=external;snapshot=self.capture()
        external.__spec__.loader_state['x']=2
        with self.assertRaises(ValueError):graph.check(snapshot)
        snapshot=self.capture();external.leaf=FunctionType(external.leaf.__code__,vars(external))
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_06_slots_properties_and_dataclass_generated_metadata(self):
        module=self.module('a',b'import dataclasses\n@dataclasses.dataclass(frozen=True)\nclass Record:\n    value:int=1\n    rows:list=dataclasses.field(default_factory=list)\nclass Slotted:\n    __slots__=("value",)\n    @property\n    def item(self):\n        return self.value\n    @staticmethod\n    def static():\n        return 1\n    @classmethod\n    def klass(cls):\n        return cls\n')
        snapshot=self.capture();self.assertTrue(graph.check(snapshot)['structure_and_identity_stable'])
        self.assertTrue(any(type(item) is dataclasses.Field for item in snapshot._objects))
        module.Record.__dataclass_fields__['rows'].default_factory=dict
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_07_unselected_project_module_and_class_are_rejected(self):
        self.ordinary();module=ModuleType('_producer_graph_foreign');module.__file__=str(self.root/'foreign.py')
        exec(compile('class Foreign:\n    pass\n',module.__file__,'exec'),vars(module))
        selected=next(iter(self.modules.values()));selected.foreign=module.Foreign;self.registry[module.__name__]=module
        with self.assertRaisesRegex(ValueError,'unselected project module'):self.capture()
        self.registry.pop(module.__name__)
        with self.assertRaises(ValueError):self.capture()

    def test_08_closure_cells_and_mutable_captured_defaults(self):
        module=self.module('a',b'def factory():\n    value=[1]\n    def leaf():\n        return value\n    return leaf\nleaf=factory()\n')
        snapshot=self.capture();self.assertTrue(any(type(item).__name__=='cell' for item in snapshot._objects))
        module.leaf.__closure__[0].cell_contents.append(2)
        with self.assertRaises(ValueError):graph.check(snapshot)

    def test_09_builtin_fallback_and_original_builtin_dictionary(self):
        module=self.ordinary();snapshot=self.capture()
        self.assertTrue(any(row[1]=='len' for row in snapshot._graph[3]))
        module.__dict__['__builtins__']['len']=lambda value:0
        with self.assertRaises(ValueError):graph.check(snapshot)
        module.__dict__['__builtins__']['len']=builtins.len
        module=self.module('b',b'def leaf():\n    return len(())\n')
        module.__dict__['__builtins__']=dict(module.__dict__['__builtins__'])
        with self.assertRaisesRegex(ValueError,'builtins dictionary'):self.capture()

    def test_10_unsupported_instances_partial_and_nonfinite_values(self):
        import functools
        module=self.ordinary()
        for value in (object(),SimpleNamespace(value=1),functools.partial(int,'1'),float('nan')):
            with self.subTest(value_type=type(value).__name__):
                module.unsupported=value
                with self.assertRaises(ValueError):self.capture()
        del module.unsupported
        touched=[]
        class HostileMapping(dict):
            def items(self):touched.append('called');raise RuntimeError('must not call mapping methods')
        module.proxy=MappingProxyType(HostileMapping(x=1))
        with self.assertRaisesRegex(ValueError,'exact dictionary'):self.capture()
        self.assertEqual(touched,[]);del module.proxy
        module=self.module('meta',b'class Meta(type):\n    pass\nclass C(metaclass=Meta):\n    pass\n')
        with self.assertRaises(ValueError):self.capture()

    def test_11_caps_reject_before_returning_a_snapshot(self):
        self.ordinary();self.module('b',b'value=1\n')
        for caps in ((1,50000,256,8388608),(37,1,256,8388608),(37,50000,1,8388608),(37,50000,256,64),(37,50000,256,1024),(38,50000,256,8388608)):
            with self.subTest(caps=caps),self.assertRaisesRegex(ValueError,'cap'):self.capture(caps=caps)

    def test_12_observations_cannot_be_transferred_or_claim_authority(self):
        self.ordinary();snapshot=self.capture();report=graph.check(snapshot)
        self.assertTrue(all(report[name] is False for name in graph.FALSE_FIELDS))
        self.assertIs(report['initial_project_state_authenticated'],False)
        with patch.object(builtins,'NotImplemented',object()):
            with self.assertRaisesRegex(ValueError,'NotImplemented'):graph.check(snapshot)
        for operation in (copy.copy,copy.deepcopy):
            with self.assertRaises(TypeError):operation(snapshot)
        with self.assertRaises(AttributeError):snapshot._caps=(1,2,3,4)
        object.__setattr__(snapshot,'_creator',(0,0))
        with self.assertRaisesRegex(ValueError,'creating project snapshot'):graph.check(snapshot)
