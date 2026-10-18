"""Path/origin faults must be refused before an audit callback is permitted."""
import copy
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch

from performance.interpreter_path_policy import InterpreterPathPolicy


HERE = Path(__file__).resolve().parent


class InterpreterPolicyTests(unittest.TestCase):
    def setUp(self):
        self.saved_paths = list(sys.path)
        self.declaration = json.loads((HERE/'interpreter_path_policy_v1.json').read_bytes())
        self.policy = InterpreterPathPolicy(self.declaration)
        sys.path[:] = self.declaration['isolated_base_paths']

    def tearDown(self):
        sys.path[:] = self.saved_paths

    def test_explicit_route_and_exact_duplicate_preserve_search_order(self):
        self.policy.configure()
        before = list(sys.path)
        sys.path.insert(0,before[0])
        row = self.policy.admit('after_fixture')
        self.assertEqual(sys.path,before)
        self.assertEqual(row['effective_sys_path'],before)
        self.assertFalse(row['helper_distribution_result_cache'])

    def test_unknown_startup_root_refused(self):
        sys.path.insert(0,str(HERE))
        with self.assertRaisesRegex(ValueError,'startup search paths'):
            self.policy.configure()

    def test_added_or_reordered_path_refused(self):
        self.policy.configure()
        before = list(sys.path)
        for changed in ([str(HERE),*before], [before[1],before[0],*before[2:]]):
            sys.path[:] = changed
            with self.assertRaisesRegex(ValueError,'search paths changed'):
                self.policy.admit('before_audit')

    def test_nonisolated_flag_refused(self):
        flags = SimpleNamespace(isolated=0)
        with patch.object(sys,'flags',flags),self.assertRaisesRegex(ValueError,'-I -B'):
            self.policy.configure()

    def test_shadow_origin_resolution_refused_before_module_import(self):
        declaration=copy.deepcopy(self.declaration)
        declaration['top_level_origins']['pyomo']['file']=str(HERE/'fake_pyomo.py')
        policy=InterpreterPathPolicy(declaration)
        with self.assertRaisesRegex(ValueError,'planned top-level import origin differs: pyomo'):
            policy.configure()

    def test_changed_origin_file_hash_refused(self):
        declaration=copy.deepcopy(self.declaration)
        declaration['top_level_origins']['numpy']['sha256']='0'*64
        policy=InterpreterPathPolicy(declaration)
        with self.assertRaisesRegex(ValueError,'origin bytes differ: numpy'):
            policy.configure()

    def test_loaded_module_foreign_origin_refused(self):
        module=ModuleType('pyomo');module.__file__=str(HERE/'foreign.py')
        with patch.dict(sys.modules,pyomo=module),self.assertRaisesRegex(ValueError,'loaded top-level module origin differs: pyomo'):
            self.policy.configure()

    def test_loaded_module_replacement_with_same_origin_refused(self):
        self.policy.configure()
        original=sys.modules['pytest']
        module=ModuleType('pytest');vars(module).update(vars(original))
        with patch.dict(sys.modules,pytest=module),self.assertRaisesRegex(ValueError,'module identity changed: pytest'):
            self.policy.admit('before_audit')

    def test_loaded_module_removal_refused(self):
        self.policy.configure()
        with patch.dict(sys.modules):
            sys.modules.pop('pytest')
            with self.assertRaisesRegex(ValueError,'module disappeared: pytest'):
                self.policy.admit('before_audit')

    def test_changed_stock_pathfinder_refused(self):
        from importlib.machinery import PathFinder
        self.policy.configure()
        with patch.object(PathFinder,'find_spec',classmethod(lambda *a:None)):
            with self.assertRaisesRegex(ValueError,'stock import path finder changed'):
                self.policy.admit('before_audit')


if __name__=='__main__':
    unittest.main(verbosity=2)
