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
            policy=InterpreterPathPolicy(self.declaration)
            sys.path[:] = changed
            with self.assertRaisesRegex(ValueError,'search paths changed'):
                policy.admit('before_audit')

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

    def test_missing_B_cannot_be_masked_by_mutable_dont_write_bytecode(self):
        flags=SimpleNamespace(isolated=1,ignore_environment=1,no_user_site=1,safe_path=True,dont_write_bytecode=0)
        with patch.object(sys,'flags',flags),self.assertRaisesRegex(ValueError,'-I -B'):
            self.policy.configure()

    def test_failed_admission_stays_poisoned_after_restoration(self):
        self.policy.configure();before=list(sys.path)
        sys.path.append(str(HERE))
        with self.assertRaisesRegex(ValueError,'search paths changed'):self.policy.admit('first_failure')
        sys.path[:]=before
        with self.assertRaisesRegex(ValueError,'poisoned at first_failure'):self.policy.admit('after_restore')
        self.assertEqual(self.policy.receipt()['first_failure']['boundary'],'first_failure')

    def test_mutating_original_declaration_does_not_change_owned_policy(self):
        self.declaration['configured_paths'].append('foreign')
        self.policy.configure()
        self.assertNotIn('foreign',sys.path)

    def test_mutating_owned_declaration_is_refused(self):
        self.policy.configure()
        self.policy.declaration['top_level_origins']['numpy']['sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'policy declaration changed'):self.policy.admit('before_audit')

    def test_custom_importer_cache_refused(self):
        self.policy.configure();root=sys.path[0]
        with patch.dict(sys.path_importer_cache,{root:SimpleNamespace(path=root)}):
            with self.assertRaisesRegex(ValueError,'stock configured-root importer required'):
                self.policy.admit('before_audit')

    def test_extra_path_hook_refused(self):
        self.policy.configure();before=list(sys.path_hooks)
        try:
            sys.path_hooks.append(lambda name:None)
            with self.assertRaisesRegex(ValueError,'path hooks changed'):self.policy.admit('before_audit')
        finally:sys.path_hooks[:]=before

    def test_extra_meta_finder_refused(self):
        self.policy.configure();before=list(sys.meta_path)
        try:
            sys.meta_path.insert(0,SimpleNamespace(find_spec=lambda *a:None))
            with self.assertRaisesRegex(ValueError,'meta finders changed'):self.policy.admit('before_audit')
        finally:sys.meta_path[:]=before

    def test_foreign_support_module_is_refused(self):
        self.policy.configure();module=ModuleType('foreign_support')
        module.__file__=self.declaration['top_level_origins']['pygments']['file']
        with patch.dict(sys.modules,foreign_support=module):
            with self.assertRaisesRegex(ValueError,'unfixed user-site module loaded'):
                self.policy.admit('before_audit')

    def test_package_search_path_drift_refused(self):
        self.policy.configure();module=sys.modules['pytest'];before=module.__path__
        try:
            module.__path__=[str(HERE)]
            with self.assertRaisesRegex(ValueError,'loaded top-level module origin differs'):
                self.policy.admit('before_audit')
        finally:module.__path__=before

    def test_configure_failure_keeps_first_boundary(self):
        sys.path.insert(0,str(HERE))
        with self.assertRaisesRegex(ValueError,'startup search paths'):self.policy.configure()
        self.assertEqual(self.policy.receipt()['first_failure']['boundary'],'configure')
        sys.path[:]=self.saved_paths
        with self.assertRaisesRegex(ValueError,'poisoned at configure'):self.policy.admit('entry_exit')

    def test_pytest_configure_failure_keeps_first_boundary(self):
        self.policy.configure()
        with self.assertRaises((KeyError,ValueError)):self.policy.begin_pytest(object())
        self.assertEqual(self.policy.receipt()['first_failure']['boundary'],'pytest_configure')
        with self.assertRaisesRegex(ValueError,'poisoned at pytest_configure'):self.policy.admit('entry_exit')

    def test_support_alias_to_different_allowlisted_file_is_refused(self):
        from importlib.machinery import ModuleSpec,SourceFileLoader
        self.policy.configure()
        original=sys.modules['pygments.token'];module=ModuleType('pygments.forged')
        vars(module).update(vars(original));module.__loader__=SourceFileLoader('pygments.forged',module.__file__)
        module.__spec__=ModuleSpec('pygments.forged',module.__loader__,origin=module.__file__)
        with patch.dict(sys.modules,{'pygments.forged':module}):
            with self.assertRaisesRegex(ValueError,'unfixed user-site module loaded: pygments.forged'):
                self.policy.admit('before_audit')

    def test_support_module_replacement_is_refused(self):
        self.policy.configure();module=ModuleType('pygments.token')
        vars(module).update(vars(sys.modules['pygments.token']))
        with patch.dict(sys.modules,{'pygments.token':module}):
            with self.assertRaisesRegex(ValueError,'support module identity changed: pygments.token'):
                self.policy.admit('before_audit')

    def test_support_module_removal_is_refused(self):
        self.policy.configure()
        with patch.dict(sys.modules):
            sys.modules.pop('pygments.token')
            with self.assertRaisesRegex(ValueError,'previously loaded support module disappeared'):
                self.policy.admit('before_audit')

    def test_support_namespace_from_foreign_root_is_refused(self):
        self.policy.configure();module=ModuleType('pygments.unfixed')
        module.__file__=__file__
        with patch.dict(sys.modules,{'pygments.unfixed':module}):
            with self.assertRaisesRegex(ValueError,'unfixed user-site module loaded: pygments.unfixed'):
                self.policy.admit('before_audit')

    def test_support_namespace_without_file_is_refused(self):
        self.policy.configure();module=ModuleType('colorama.unfixed')
        with patch.dict(sys.modules,{'colorama.unfixed':module}):
            with self.assertRaisesRegex(ValueError,'unfixed user-site module loaded: colorama.unfixed'):
                self.policy.admit('before_audit')


if __name__=='__main__':
    unittest.main(verbosity=2)
