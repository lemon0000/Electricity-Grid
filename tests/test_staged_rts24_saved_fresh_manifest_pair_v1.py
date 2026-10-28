"""Supplementary parent/Core pairing checks; frozen 48-node evidence is reused."""
import copy
import importlib.util
from pathlib import Path
from types import CodeType
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).absolute().parents[1]


def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


parent=load('experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v36.py','_paired_parent')
core=load('experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py','_paired_core')
constructor=load('experiments/staged_rts24_saved_fresh_consumer_manifest_transform_v2.py','_paired_constructor')


class ManifestPairTests(unittest.TestCase):
    def test_01_exact_successors_and_reused_methods(self):
        for name,before,after in (
                ('core','experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py','experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py'),
                ('probe','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v36.py','tests/staged_rts24_saved_fresh_runtime_handoff_probe_v37.py'),
                ('parent','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v35.py','experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v36.py')):
            self.assertEqual(getattr(constructor,name)((ROOT/before).read_text(encoding='utf8')),(ROOT/after).read_bytes())
        def methods(path):
            unit=compile((ROOT/path).read_bytes(),'<paired_core>','exec',dont_inherit=True,optimize=0)
            cls=next(value for value in unit.co_consts if type(value) is CodeType and value.co_name=='LocalRuntimeInputs')
            return {value.co_name:value for value in cls.co_consts if type(value) is CodeType}
        current=methods('experiments/staged_rts24_saved_fresh_pre_entry_lease_v39.py')
        prior=methods('experiments/staged_rts24_saved_fresh_pre_entry_lease_v38.py')
        for name in ('entry','source_bookend','prepare_consumer','consume_once','close'):
            self.assertEqual(current[name],prior[name])

    def test_02_actual_discovery_parent_to_core_and_path_pin_failures(self):
        code=parent.transport();plan=parent.manifest('discovery',code)
        self.assertEqual(core.check_plan(parent.canonical(plan)),plan)
        self.assertIs(parent.validate_manifest_pair(plan,code),plan)
        for mode in ('old_helper','namespace_pin','import_pin','policy','bootstrap'):
            bad=copy.deepcopy(plan)
            if mode=='old_helper':bad['namespace_helper']['path']=str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py')
            elif mode=='namespace_pin':bad['namespace_helper']['pin']['sha256']='0'*64
            elif mode=='import_pin':bad['import_helper']['pin']['sha256']='0'*64
            elif mode=='policy':bad['import_policy']['path']=str(parent.OUT/'foreign.json')
            else:bad['bootstrap_pin']=parent.pin(b'changed')
            with self.subTest(mode=mode),self.assertRaises((ValueError,AssertionError)):parent.validate_manifest_pair(bad,code)

    def test_03_normal_manifest_pair_and_startup_reference_relationships(self):
        fixture=load('tests/test_staged_rts24_saved_fresh_live_profile_v1.py','_manifest_fixture_only')
        code=parent.transport()
        with tempfile.TemporaryDirectory(prefix='saved_F_manifest_pair_') as tmp:
            folder=Path(tmp);fixture.controller_fixture(folder,code)
            overlay={parent.OUT/name:(folder/name).read_bytes() for name in ('registration.json','startup_profile.json','probe_discovery.receipt.json','profile_admission.exit.json')}
            original=Path.read_bytes
            def read(path):return overlay[path] if path in overlay else original(path)
            # Metadata-only admission fixture at the real fixed paths; no file is published.
            with patch.object(Path,'read_bytes',read):
                plan=parent.manifest('normal',code);self.assertEqual(core.check_plan(parent.canonical(plan)),plan)
                self.assertEqual(plan['startup_profile']['path'],str(parent.OUT/'startup_profile.json'))
                for field in ('startup_profile','import_profile'):
                    bad=copy.deepcopy(plan);bad[field]['path']=str(folder/'foreign.json')
                    with self.subTest(field=field),self.assertRaises((ValueError,AssertionError)):parent.validate_manifest_pair(bad,code)
                bad=copy.deepcopy(plan);bad['namespace_helper']['path']=str(ROOT/'experiments/staged_rts24_saved_fresh_entry_namespace_post_return_v1.py')
                with self.assertRaises(ValueError):parent.validate_manifest_pair(bad,code)
                bad=copy.deepcopy(plan);bad['startup_profile']['path']=str(folder/'startup_profile.json')
                with self.assertRaises(ValueError):core.check_plan(parent.canonical(bad))
