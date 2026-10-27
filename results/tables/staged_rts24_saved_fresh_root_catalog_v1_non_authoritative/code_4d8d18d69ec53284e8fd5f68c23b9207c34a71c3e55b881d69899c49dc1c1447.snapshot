"""Pure static fixtures; audited project sources are never imported."""
import copy
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest import mock


TOOL_PATH = Path(__file__).absolute().parents[1]/'experiments/staged_rts24_saved_fresh_root_catalog_v1.py'
SPEC = importlib.util.spec_from_file_location('_saved_root_catalog_tool', TOOL_PATH)
tool = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tool)


def graph(sources, roots):
    modules = {tool.module_name(path): tool.StaticModule(tool.module_name(path), path, raw.encode())
        for path, raw in sources.items()}
    return tool.ReferenceGraph(modules).build(roots)


class StaticCatalogTests(unittest.TestCase):
    def test_global_alias_and_relative_module(self):
        result = graph({'pkg/main.py': 'from . import helper as h\ndef f(): return h.run()\n',
            'pkg/helper.py': 'def run(): return 1\n'}, ['pkg.main::f'])
        self.assertIn('pkg.main::h', result['nodes'])
        self.assertIn('pkg.helper::run', result['nodes'])
        self.assertIn(['pkg.main::h', 'module:pkg.helper', 'static_candidate'], result['edges'])

    def test_dotted_import_without_alias_keeps_actual_submodule(self):
        result = graph({'pkg/__init__.py': '', 'pkg/helper.py': 'def run(): return 1\n',
            'pkg/main.py': 'import pkg.helper\ndef f(): return pkg.helper.run()\n'}, ['pkg.main::f'])
        self.assertIn(['pkg.main::pkg', 'module:pkg.helper', 'static_candidate'], result['edges'])
        self.assertIn('pkg.helper::run', result['nodes'])

    def test_module_global_shadow_and_builtin_fallback(self):
        result = graph({'pkg/main.py': 'len = 7\ndef f(): return len([])\ndel len\n'}, ['pkg.main::f'])
        self.assertIn('pkg.main::len', result['nodes'])
        self.assertIn('builtin_lookup:len', result['nodes'])
        self.assertEqual(result['nodes']['pkg.main::f']['builtin_fallback_candidates'], ['len'])
        self.assertFalse(result['runtime_closure_verified'])

    def test_builtin_lookup_is_runtime_required(self):
        result = graph({'pkg/main.py': 'def f(): return len([])\n'}, ['pkg.main::f'])
        self.assertIn(['pkg.main::f', 'builtin_lookup:len', 'runtime_required'], result['edges'])

    def test_class_bases_metaclass_descriptor_and_method(self):
        source = 'class Meta(type): pass\nclass Base: pass\nclass C(Base, metaclass=Meta):\n @property\n def x(self): return getattr(self, "y")\n'
        result = graph({'pkg/main.py': source}, ['pkg.main::C'])
        for name in ('Meta', 'Base', 'C.x'):
            self.assertIn('pkg.main::' + name, result['nodes'])
        self.assertIn('getattr', result['nodes']['pkg.main::C.x']['dynamic_name_operators'])
        self.assertTrue(any(e[2] == 'dynamic_open' for e in result['edges']))

    def test_defaults_annotations_and_decorators(self):
        source = 'VALUE=1\nT=int\ndef deco(f): return f\n@deco\ndef f(x:T=VALUE)->T: return x\n'
        result = graph({'pkg/main.py': source}, ['pkg.main::f'])
        self.assertEqual(result['nodes']['pkg.main::f']['definition_expression_names'], ['T', 'VALUE', 'deco'])
        self.assertIn('pkg.main::deco', result['nodes'])

    def test_nested_code_globals_and_closure_cells(self):
        source = 'VALUE=1\ndef f(x):\n def inner(): return x+VALUE\n return inner\n'
        result = graph({'pkg/main.py': source}, ['pkg.main::f'])
        facts = result['nodes']['pkg.main::f']
        self.assertIn('VALUE', facts['global_names'])
        self.assertIn('x', facts['cellvars'])
        self.assertIn('x', facts['freevars'])
        self.assertIn(['pkg.main::f', 'runtime_state:closure_cells:pkg.main::f', 'runtime_required'], result['edges'])

    def test_indirect_ambiguous_definition_remains_open(self):
        result = graph({'pkg/main.py': 'def dep(): return 1\ndef dep(): return 2\ndef f(): return dep()\n'}, ['pkg.main::f'])
        self.assertIn('runtime_state:ambiguous_binding:pkg.main::dep', result['nodes'])

    def test_global_writes_stay_open(self):
        result = graph({'pkg/main.py': 'VALUE=1\ndef f():\n global VALUE\n VALUE=2\n'}, ['pkg.main::f'])
        self.assertEqual(result['nodes']['pkg.main::f']['global_writes'], ['VALUE'])
        self.assertTrue(any(e[2] == 'runtime_required' for e in result['edges']))

    def test_star_import_and_dynamic_import_stay_open(self):
        result = graph({'pkg/main.py': 'from unknown import *\ndef f(): return __import__("late")\n'}, ['module:pkg.main'])
        self.assertIn('dynamic_open:star_import:unknown.*', result['nodes'])
        self.assertIn('__import__', result['nodes']['pkg.main::f']['dynamic_name_operators'])

    def test_native_boundary_does_not_become_python_proof(self):
        result = graph({'pkg/main.py': 'import ctypes\ndef f(): return ctypes.WinDLL("kernel32")\n'}, ['pkg.main::f'])
        self.assertIn(['pkg.main::ctypes', 'external:ctypes', 'native_open'], result['edges'])

    def test_reference_cycles_are_preserved(self):
        result = graph({'pkg/main.py': 'def a(): return b()\ndef b(): return a()\n'}, ['pkg.main::a'])
        self.assertIn(['pkg.main::a', 'pkg.main::b'], result['recursive_components'])
        tool.validate_reference_graph(result)

    def test_self_recursion_is_preserved(self):
        result = graph({'pkg/main.py': 'def a(): return a()\n'}, ['pkg.main::a'])
        self.assertIn(['pkg.main::a'], result['recursive_components'])

    def test_missing_duplicate_and_ambiguous_roots_rejected(self):
        for source, roots in [('def a(): pass\n', ['pkg.main::b']),
            ('def a(): pass\n', ['pkg.main::a', 'pkg.main::a']),
            ('def a(): pass\ndef a(): pass\n', ['pkg.main::a'])]:
            with self.subTest(source=source, roots=roots), self.assertRaises(ValueError):
                graph({'pkg/main.py': source}, roots)

    def test_casefold_module_and_source_alias_rejected(self):
        for paths in [('pkg/A.py', 'pkg/a.py'), ('pkg/a.py', 'PKG/a.py')]:
            with self.subTest(paths=paths), self.assertRaises(ValueError):
                graph({p: 'def f(): pass\n' for p in paths}, ['pkg.a::f'])

    def test_relative_import_cannot_escape_package(self):
        with self.assertRaises(ValueError):
            graph({'pkg/main.py': 'from ... import x\ndef f(): return x\n'}, ['pkg.main::f'])

    def test_audited_module_body_is_never_executed(self):
        result = graph({'pkg/main.py': 'raise RuntimeError("must not run")\ndef f(): return forbidden()\n'}, ['module:pkg.main'])
        self.assertIn('unresolved:pkg.main::forbidden', result['nodes'])
        self.assertIn('dynamic_open:module_initialization:pkg.main', result['nodes'])

    def test_source_pin_drift_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name)/'input.py'; path.write_bytes(b'old')
            expected = tool.pin(b'old')
            self.assertEqual(tool.verified_bytes(path, expected), b'old')
            path.write_bytes(b'new')
            with self.assertRaises(ValueError):
                tool.verified_bytes(path, expected)

    def test_dynamic_edge_cannot_be_promoted(self):
        result = graph({'pkg/main.py': 'def f(x): return getattr(x,"a")\n'}, ['pkg.main::f'])
        edge = next(e for e in result['edges'] if e[2] == 'dynamic_open')
        edge[2] = 'static_candidate'
        with self.assertRaises(ValueError): tool.validate_reference_graph(result)

    def test_runtime_node_and_graph_claims_rejected(self):
        result = graph({'pkg/main.py': 'def f(): return 1\n'}, ['pkg.main::f'])
        for key in ('runtime_closure_verified', 'complete_runtime_call_graph'):
            changed = copy.deepcopy(result); changed[key] = True
            with self.assertRaises(ValueError): tool.validate_reference_graph(changed)
        result['nodes']['pkg.main::f']['runtime_verified'] = True
        with self.assertRaises(ValueError): tool.validate_reference_graph(result)

    def test_evidence_dag_unknown_duplicate_cycle_rejected(self):
        for nodes in [dict(a=dict(requires=['missing'], verified=False)),
            dict(a=dict(requires=['b','b'], verified=False), b=dict(requires=[], verified=False)),
            dict(a=dict(requires=['b'], verified=False), b=dict(requires=['a'], verified=False))]:
            with self.subTest(nodes=nodes), self.assertRaises(ValueError): tool.validate_evidence_dag(nodes)

    def test_evidence_data_cannot_issue_capability(self):
        for field in ('verified', 'produces_authority'):
            node = dict(requires=[], verified=False, produces_authority=False); node[field] = True
            with self.assertRaises(ValueError): tool.validate_evidence_dag(dict(a=node))

    def test_unimplemented_evidence_cannot_claim_witness_or_status(self):
        for field, value in [('status', 'VERIFIED'), ('evidence_ref', 'self.json'), ('runtime_witness', {}), ('artifact_pins', {'fake':{}})]:
            node = dict(requires=[], verified=False, produces_authority=False, status='UNIMPLEMENTED', evidence_ref=None, runtime_witness=None)
            node[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError): tool.validate_evidence_dag(dict(a=node))

    def test_evidence_hold_must_be_same_process_prerequisite(self):
        for requires, target_role in [([], 'host'), (['b'], 'broker')]:
            nodes = dict(a=dict(requires=requires, verified=False, process_role='host', same_process_holds=['b']),
                b=dict(requires=[], verified=False, process_role=target_role))
            with self.subTest(requires=requires, target_role=target_role), self.assertRaises(ValueError):
                tool.validate_evidence_dag(nodes)

    def test_required_evidence_templates_keep_startup_and_self_open(self):
        dag = tool.evidence_dag(); nodes = dag['nodes']
        self.assertEqual(set(dag['topological_order']), set(nodes))
        self.assertIn('system site', nodes['startup_TCB']['open_obligations'])
        self.assertIn('before ENTRY import', nodes['host_pre_ENTRY_bootstrap']['open_obligations'])
        self.assertTrue(all(n['evidence_ref'] is None and n['produces_authority'] is False for n in nodes.values()))
        self.assertTrue(all(v is False for v in tool.FALSE_GATES.values()))

    def test_original_broker_quiet_and_return_chain_preserved(self):
        dag = tool.evidence_dag(); nodes = dag['nodes']
        for name in ('broker_owner_armed', 'broker_ready', 'START', 'context', 'offer', 'ACK', 'broker_ACK_verified',
            'controller_permit', 'fresh_result', 'fresh_quiet', 'G1_compare', 'parent_quiet', 'G2', 'G3',
            'controller_return', 'controller_quiet', 'broker_return', 'broker_quiet', 'H3', 'host_final'):
            self.assertIn(name, nodes)
        for a, b in dag['original_data_edges'] + dag['original_same_process_edges']:
            self.assertIn(a, nodes[b]['requires'])
        self.assertEqual(nodes['startup_TCB']['same_process_holds'], [])
        self.assertEqual(nodes['host_expected']['same_process_holds'], [])

    def test_each_role_has_separate_startup_and_runtime_nodes(self):
        nodes = tool.evidence_dag()['nodes']
        for role in ('host', 'broker', 'controller', 'parent', 'fresh'):
            for phase in ('pre_ENTRY_bootstrap', 'local_self', 'cold_main', 'import_transition', 'live_lease', 'full_input'):
                self.assertEqual(nodes[role+'_'+phase]['process_role'], role)

    def test_failed_or_drifted_predecessor_cannot_admit_next_stage(self):
        path = TOOL_PATH.parents[1]/'results/tables/staged_rts24_saved_fresh_root_catalog_v1_non_authoritative/driver.py'
        spec = importlib.util.spec_from_file_location('catalog_driver_unit', path)
        driver = importlib.util.module_from_spec(spec); spec.loader.exec_module(driver)
        for change in ('accepted', 'kind', 'registration_pin', 'helper_pins', 'source_epoch', 'report_pin'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as folder:
                out = Path(folder); reg = dict(helper_pins={}, source_epoch='expected')
                (out/'registration.json').write_bytes(tool.canonical(reg))
                report = tool.canonical(dict(accepted=True))
                (out/'unittest_report.json').write_bytes(report)
                record = dict(accepted=True, label='unittest', kind='unittest', source_epoch='expected',
                    registration_pin=tool.pin(tool.canonical(reg)), helper_pins={}, report_pin=tool.pin(report))
                record[change] = False if change == 'accepted' else 'changed'
                (out/'unittest.exit.json').write_bytes(tool.canonical(record))
                with mock.patch.object(driver, 'OUT', out), self.assertRaises(AssertionError):
                    driver.prerequisites('catalog', reg)


if __name__ == '__main__':
    unittest.main()
