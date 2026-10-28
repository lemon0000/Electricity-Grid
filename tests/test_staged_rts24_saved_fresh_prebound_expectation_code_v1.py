"""Source derivation and hostile-AST tests; no project module or P1 execution."""
import ast
import copy
import importlib.util
from pathlib import Path
from types import CodeType
import unittest

ROOT=Path(__file__).absolute().parents[1]
spec=importlib.util.spec_from_file_location('_prebound_code_under_test',ROOT/'experiments/staged_rts24_saved_fresh_prebound_expectation_code_v1.py')
builder=importlib.util.module_from_spec(spec);spec.loader.exec_module(builder)


def source_node():
    tree=ast.parse((ROOT/builder.ENTRY).read_bytes())
    return next(node for node in tree.body if type(node) is ast.FunctionDef and node.name=='capture_saved_expectation')


class PreboundExpectationCodeTests(unittest.TestCase):
    def test_01_actual_source_exact_reversible_bridge(self):
        code,report=builder.current()
        self.assertIs(type(code),CodeType);self.assertEqual(code.co_argcount,2)
        self.assertEqual(code.co_varnames[:2],('expected_sources','binding'))
        self.assertTrue(report['inverse_position_ast_equal']);self.assertTrue(report['inverse_complete_code_equal'])
        self.assertTrue(report['second_preparation_dependency_removed']);self.assertEqual(report['P1_reads'],0)
        self.assertTrue(report['full_module_root_code_equal']);self.assertTrue(report['binding_cell_argument_verified'])
        self.assertTrue(report['bookend_code_metadata_only_renamed'])
        self.assertFalse(report['producer_capability_verified']);self.assertFalse(report['actual_F'])

    def test_02_foreign_source_and_opcode_removal(self):
        raw=(ROOT/builder.ENTRY).read_bytes()
        for bad in (raw+b'\n',raw.replace(b'capture_saved_expectation(',b'capture_saved_expectatioX(',1)):
            with self.assertRaisesRegex(ValueError,'frozen ENTRY'):builder.derive(bad)
        code,_=builder.current();pending=[code]
        while pending:
            item=pending.pop();self.assertNotIn('_expectation_adapter',item.co_names)
            pending.extend(value for value in item.co_consts if type(value) is CodeType)

    def test_03_hostile_signatures_and_rebinding(self):
        for mode in ('name','arg','default','decorator','global','extra_binding','wrong_call','wrong_argument','source_rhs','walrus','loop','delete'):
            node=source_node()
            if mode=='name':node.name='other'
            elif mode=='arg':node.args.args[0].arg='binding'
            elif mode=='default':node.args.defaults=[ast.Constant(None)]
            elif mode=='decorator':node.decorator_list=[ast.Name(id='decorator',ctx=ast.Load())]
            elif mode=='global':node.body.append(ast.Global(names=['binding']))
            elif mode=='source_rhs':
                index=next(index for index,item in enumerate(node.body) if type(item) is ast.Assign and any(type(t) is ast.Name and t.id=='source' for t in item.targets))
                node.body[index].value=ast.Constant('foreign source')
            elif mode in ('walrus','loop','delete'):
                text={'walrus':'(binding := None)','loop':'for binding in ():\n    pass','delete':'del binding'}[mode]
                node.body.extend(ast.parse(text).body)
            else:
                target=next(value for value in node.body if type(value) is ast.Assign and any(type(t) is ast.Name and t.id=='binding' for t in value.targets))
                if mode=='extra_binding':node.body.append(copy.deepcopy(target))
                elif mode=='wrong_call':target.value.func.id='other_adapter'
                else:target.value.args[0].id='other_source'
            with self.subTest(mode=mode),self.assertRaises(ValueError):builder.transform(node)

    def test_04_body_and_failure_bookend_ast_preserved(self):
        node=source_node();changed,inverse,index=builder.transform(node)
        self.assertEqual(ast.dump(node,include_attributes=True),ast.dump(inverse,include_attributes=True))
        original=node.body[:index]+node.body[index+1:]
        self.assertEqual([ast.dump(item,include_attributes=True) for item in original],
            [ast.dump(item,include_attributes=True) for item in changed.body])
        self.assertIsNot(changed,node);self.assertEqual(node.args.args[0].arg,'expected_sources')
        self.assertEqual(len(node.args.args),1)
