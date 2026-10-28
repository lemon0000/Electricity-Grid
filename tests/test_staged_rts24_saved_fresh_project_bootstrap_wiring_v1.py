"""Ordinary metadata/source wiring tests; no native owner or Source49 module exec."""
import ast
import builtins
import copy
import dis
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
from threading import get_ident
import time
from types import CodeType,FunctionType,ModuleType
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]
PROBE=ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v38.py'
RAW=PROBE.read_bytes();UNIT=compile(RAW,str(PROBE),'exec',dont_inherit=True,optimize=0)


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module);return module


core=load('experiments/staged_rts24_saved_fresh_pre_entry_lease_v40.py','_wiring_core40')
parent=load('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v37.py','_wiring_parent37')
transform=load('experiments/staged_rts24_saved_fresh_project_bootstrap_transform_v1.py','_wiring_transform')
transport=parent.transport()


class RuntimeFixture:
    def __init__(self,raw):
        self._phase='ADOPTED';self._raw=raw;self._creator=(os.getpid(),get_ident())
        self._consume_state=None;self.entries=0;self.bookends=0
    def entry(self):self.entries+=1;return self
    def source_bookend(self):self.bookends+=1;return {}


def function(name,context):
    code=next(code for code in UNIT.co_consts if type(code) is CodeType and code.co_name==name)
    return FunctionType(code,context)


def bs_fixture(bridge):
    path=ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_post_return_v4.py'
    module=ModuleType('_wiring_real_B_S4');io=(time.perf_counter,lambda raw:len(raw),lambda:None,json.dumps)
    vars(module).update(__file__=str(path),_READ_FILE=core.read_file,_CENSUS_IO=io,_PROJECT_BRIDGE=bridge)
    unit=compile(path.read_bytes(),str(path),'exec',dont_inherit=True,optimize=0)
    exec(unit,vars(module),vars(module));return module,unit,io


class BootstrapWiringTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix='project_wiring_');self.addCleanup(self.tmp.cleanup)
        self.folder=Path(self.tmp.name)
        self.folder.joinpath('import_policy.json').write_bytes(b'{"synthetic_policy":true}')
        with patch.object(parent,'OUT',self.folder):self.plan=parent.manifest('discovery',transport)
        self.owner=RuntimeFixture(core.canonical(self.plan))
        self.context=dict(vars(core));self.context['LocalRuntimeInputs']=RuntimeFixture
        self.loader=function('prepare_project_bridge',self.context)

    def test_01_exact_transforms_preserve_core_methods(self):
        for name,before,after in transform.PAIRS:
            self.assertEqual(getattr(transform,name)((ROOT/before).read_text(encoding='utf8')),(ROOT/after).read_bytes())
        def methods(path):
            unit=compile((ROOT/path).read_bytes(),'<same_virtual_core>','exec',dont_inherit=True,optimize=0)
            cls=next(code for code in unit.co_consts if type(code) is CodeType and code.co_name=='LocalRuntimeInputs')
            return {code.co_name:code for code in cls.co_consts if type(code) is CodeType}
        old=methods(transform.PAIRS[0][1]);new=methods(transform.PAIRS[0][2])
        self.assertEqual(old,new)

    def test_02_closed_helper_set_and_fixed_paths(self):
        self.assertEqual(core.check_plan(core.canonical(self.plan)),self.plan)
        for mode in ('missing','extra','path','pin_type','pin_unknown'):
            bad=copy.deepcopy(self.plan);refs=bad['producer_helpers']
            if mode=='missing':refs.pop('utilities')
            elif mode=='extra':refs['unknown']=refs['utilities']
            elif mode=='path':refs['capture']['path']=str(self.folder/'capture.py')
            elif mode=='pin_type':refs['capture']['pin']['bytes']=True
            else:refs['capture']['pin']['unknown']=1
            with self.subTest(mode=mode),self.assertRaises(ValueError):core.check_plan(core.canonical(bad))

    def test_03_parent_rejects_legacy_normal_before_transport_launch(self):
        with patch.object(parent.subprocess,'Popen',side_effect=AssertionError('no native launch')) as spawn:
            with self.assertRaisesRegex(AssertionError,'no producer admission'):parent.manifest('normal',transport)
            spawn.assert_not_called()

    def test_04_actual_source_orders_transfer_bridge_and_B_S_definition(self):
        tree=ast.parse(RAW);main=next(node for node in tree.body if type(node) is ast.FunctionDef and node.name=='_probe_main')
        calls=[(node.lineno,ast.unparse(node.func)) for node in ast.walk(main) if type(node) is ast.Call]
        transfer=next(line for line,name in calls if name=='namespace.transfer_runtime')
        bridge=next(line for line,name in calls if name=='prepare_project_bridge')
        validator=next(line for line,name in calls if name=='validate_import_helper')
        load=next(node.lineno for node in ast.walk(main) if type(node) is ast.Call and ast.unparse(node.func)=='_exec')
        self.assertLess(transfer,bridge);self.assertLess(bridge,load);self.assertLess(load,validator)
        self.assertFalse(any(name in ('runtime.consume_once','runtime.prepare_consumer') for _,name in calls))
        self.assertNotIn('object()',ast.unparse(main))
        report=next(node.value for node in ast.walk(main) if type(node) is ast.Assign
            and any(type(target) is ast.Name and target.id=='report' for target in node.targets))
        self.assertEqual(ast.literal_eval(next(k.value for k in report.keywords if k.arg=='schema')),
            'staged_saved_F_project_construction_probe_v1')

    def test_05_real_helper_loader_returns_unadmitted_prepared_bridge(self):
        before={name for name in sys.modules if name=='src' or name.startswith('src.')}
        bridge=self.loader(self.owner,self.plan,compile,exec)
        self.assertIs(bridge[2][0]['owner'],self.owner)
        self.assertIsNone(bridge[2][0]['admission']);self.assertEqual(bridge[2][0]['phase'],'PREPARED')
        self.assertIsNone(self.owner._consume_state);self.assertEqual(self.owner.bookends,2)
        self.assertEqual(before,{name for name in sys.modules if name=='src' or name.startswith('src.')})

    def test_06_wrong_phase_rejects_before_helper_read(self):
        self.owner._phase='LIVE'
        with patch.dict(self.context,read_file=lambda *args:(_ for _ in ()).throw(AssertionError('read'))):
            with self.assertRaisesRegex(ValueError,'pre-import creating runtime'):self.loader(self.owner,self.plan,compile,exec)

    def test_07_helper_content_pin_difference_rejects(self):
        bad=copy.deepcopy(self.plan);bad['producer_helpers']['capture']['pin']['sha256']='0'*64
        self.owner._raw=core.canonical(bad)
        with self.assertRaisesRegex(ValueError,'bookend differs'):self.loader(self.owner,bad,compile,exec)
        self.assertIsNone(self.owner._consume_state)

    def test_08_actual_B_S4_validator_accepts_exact_held_defaults(self):
        def held(state,stage,runtime,args):return None
        bridge=(held.__code__,dict(__builtins__={}),None)
        helper,unit,io=bs_fixture(bridge)
        validator=function('validate_import_helper',dict(vars(core)))
        proof=validator(helper,unit,tuple(vars(builtins).items()),io,bridge)
        self.assertTrue(proof);self.assertEqual(helper._CENSUS['installed'],0)

    def test_09_B_S4_validator_rejects_spec_or_defaults_replacement(self):
        def held(state,stage,runtime,args):return None
        bridge=(held.__code__,dict(__builtins__={}),None)
        for mode in ('spec','tuple_default','load_default','audit_default'):
            helper,unit,io=bs_fixture(bridge)
            if mode=='spec':helper._PROJECT_BRIDGE=(held.__code__,{},None)
            elif mode=='tuple_default':helper.project_bridge_call.__defaults__=helper.project_bridge_call.__defaults__[:-1]+(list,)
            elif mode=='load_default':helper.load_bootstrap_adapter.__defaults__=helper.load_bootstrap_adapter.__defaults__[:-1]+(None,)
            else:helper.BootstrapImportBoundary._audit.__defaults__=helper.BootstrapImportBoundary._audit.__defaults__[:-1]+(None,)
            with self.subTest(mode=mode),self.assertRaises(ValueError):
                function('validate_import_helper',dict(vars(core)))(helper,unit,tuple(vars(builtins).items()),io,bridge)

    def test_10_replaced_native_evaluator_is_rejected(self):
        def foreign(*args,**kwargs):raise AssertionError('executed')
        with self.assertRaisesRegex(ValueError,'held native source evaluator'):self.loader(self.owner,self.plan,compile,foreign)
        self.assertEqual(self.owner.entries,0)

    def test_11_predecessor_registration_link_blocks_program_creation(self):
        original=core.read_file
        def changed(path,pin):
            raw=original(path,pin)
            return raw+b' ' if path==self.plan['producer_helpers']['predecessor_registration']['path'] else raw
        with patch.dict(self.context,read_file=changed):
            with self.assertRaisesRegex(ValueError,'checkpoint-bound complete registration'):self.loader(self.owner,self.plan,compile,exec)
        self.assertIsNone(self.owner._consume_state)

    def test_12_current_contract_keeps_remaining_gates_open(self):
        _,report=transform.current()
        self.assertEqual(report['actual_source49_execs'],0);self.assertEqual(report['P1_reads'],0)
        for name in ('issuer_implemented','parent_terminal_oracle_implemented','whole_workflow_admitted','formal_result','actual_F'):
            self.assertIs(report[name],False)
