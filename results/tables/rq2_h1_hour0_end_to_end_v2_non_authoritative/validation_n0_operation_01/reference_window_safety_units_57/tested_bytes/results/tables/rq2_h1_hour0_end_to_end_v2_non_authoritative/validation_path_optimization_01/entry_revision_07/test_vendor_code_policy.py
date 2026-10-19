"""Admission faults for the exact vendor extension and fresh module origins."""
import copy
from importlib.machinery import SourceFileLoader,ModuleSpec
import json
from pathlib import Path
from types import ModuleType
import unittest
from performance import vendor_code_policy as policy

HERE=Path(__file__).resolve().parent


class VendorAdmissionTests(unittest.TestCase):
    def setUp(self):
        self.repo=(HERE/'code_allowlist_v3.json').read_bytes()
        self.vendor=json.loads((HERE/'vendor_code_allowlist_v1.json').read_bytes())

    def reject(self,change):
        value=copy.deepcopy(self.vendor);change(value)
        with self.assertRaises(ValueError):policy.vendor_files(self.repo,json.dumps(value).encode())

    def test_exact_predecessor_and_seven_paths(self):
        actual=policy.vendor_files(self.repo,json.dumps(self.vendor).encode())
        self.assertEqual({str(path):pin for path,pin in actual.items()},policy.VENDOR_PINS)
        self.assertEqual(len(actual),7)

    def test_repository_subset_rejected(self):
        value=json.loads(self.repo);value['files_sha256'].pop(next(iter(value['files_sha256'])))
        with self.assertRaisesRegex(ValueError,'exact predecessor'):
            policy.vendor_files(json.dumps(value).encode(),json.dumps(self.vendor).encode())

    def test_missing_vendor_rejected(self):
        self.reject(lambda value:value['files_sha256'].pop(next(iter(value['files_sha256']))))

    def test_extra_vendor_rejected(self):
        self.reject(lambda value:value['files_sha256'].update({'D:/unlisted.py':'a'*64}))

    def test_wrong_sha_rejected(self):
        self.reject(lambda value:value['files_sha256'].update({next(iter(value['files_sha256'])):'a'*64}))

    def test_same_name_c_support_file_rejected(self):
        def change(value):
            path=next(iter(value['files_sha256']));pin=value['files_sha256'].pop(path)
            value['files_sha256']['C:/support/pyomo/'+Path(path).name]=pin
        self.reject(change)

    def test_path_alias_rejected(self):
        def change(value):
            path=next(iter(value['files_sha256']));pin=value['files_sha256'].pop(path)
            value['files_sha256'][path.lower()]=pin
        self.reject(change)

    def test_extra_schema_field_rejected(self):self.reject(lambda value:value.update(cache_all=True))

    def test_duplicate_json_key_rejected(self):
        with self.assertRaisesRegex(ValueError,'duplicate vendor'):
            policy.vendor_files(self.repo,b'{"root":"D:/","root":"D:/"}')

    def modules(self):
        modules={}
        for name,relative in policy.MODULE_PATHS.items():
            path=str(policy.VENDOR_ROOT/relative);loader=SourceFileLoader(name,path)
            module=ModuleType(name);module.__file__=path;module.__loader__=loader
            module.__spec__=ModuleSpec(name,loader,origin=path);modules[name]=module
        return modules

    def test_preloaded_vendor_rejected_before_lease(self):
        policy.assert_unloaded({})
        for name in policy.MODULE_PATHS:
            with self.assertRaisesRegex(ValueError,'must not precede'):policy.assert_unloaded({name:None})

    def test_origins_bound_to_d_compute(self):
        self.assertEqual(len(policy.origins(self.modules(),required=True)),7)

    def test_required_missing_module_rejected(self):
        with self.assertRaisesRegex(ValueError,'absent'):policy.origins({},required=True)
        self.assertEqual(policy.origins({}),{})

    def test_module_file_origin_drift_rejected(self):
        modules=self.modules();next(iter(modules.values())).__file__='C:/support/GUROBI.py'
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)

    def test_module_spec_origin_drift_rejected(self):
        modules=self.modules();next(iter(modules.values())).__spec__.origin='C:/support/GUROBI.py'
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)

    def test_module_loader_mismatch_rejected(self):
        modules=self.modules();next(iter(modules.values())).__loader__=object()
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)

    def test_module_name_mismatch_rejected(self):
        modules=self.modules();next(iter(modules.values())).__spec__.name='pyomo.wrong'
        with self.assertRaisesRegex(ValueError,'origin differs'):policy.origins(modules)
