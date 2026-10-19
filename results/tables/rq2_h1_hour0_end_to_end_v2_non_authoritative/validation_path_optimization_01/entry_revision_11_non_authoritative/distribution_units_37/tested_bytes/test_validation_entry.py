"""Faults during initialization must still restore settings and write a terminal."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import importlib.metadata as metadata


HERE=Path(__file__).resolve().parent


class EntryFailureTests(unittest.TestCase):
    def check_fault(self,name,raw,*,kind='unit',mode=None,targets=()):
        if mode is None:mode='parse_path' if kind=='pytest' else 'parse'
        with tempfile.TemporaryDirectory(prefix='entry_fault_',dir=HERE) as temporary:
            folder=Path(temporary)
            names=('pinned_distribution_resolver_v1.py','static_scientific_input_read_lease_v2.py','scientific_input_allowlist_v1.json','validation_entry.py','code_read_lease.py','metadata_parse_lease.py','canonical_path_lease.py',
                'interpreter_path_policy.py','interpreter_path_policy_v1.json',
                'pytest_admission_plugin.py',
                'vendor_code_policy.py','vendor_code_allowlist_v1.json','code_allowlist_v3.json','metadata_allowlist_v1.json','test_closure_v1.json','pytest_lease_plugin.py')
            sources={key:(HERE/key).read_bytes() for key in names};sources[name]=raw
            for key,value in sources.items():(folder/key).write_bytes(value)
            import_environment=(list(sys.meta_path),list(sys.path_hooks),dict(sys.path_importer_cache))
            before=(sys.pycache_prefix,sys.dont_write_bytecode,list(sys.path),list(sys.argv))
            policy=json.loads(sources['interpreter_path_policy_v1.json'])
            sys.path[:]=policy['isolated_base_paths']
            modules={key:value for key,value in sys.modules.items() if key=='performance' or key.startswith('performance.')}
            sys.argv=['entry',kind,mode,'failure',*targets]
            scope=dict(__file__=str(folder/'validation_entry.py'),__name__='__entry_fault__',
                _pinned_sources=sources,_bootstrap_sources={},_launcher_sha256='test',_manifest_sha256='test')
            try:
                with redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as failure:
                    exec(compile(sources['validation_entry.py'],scope['__file__'],'exec'),scope)
                self.assertEqual(failure.exception.code,1)
                terminal=json.loads((folder/'failure/terminal.json').read_bytes())
                self.assertEqual(terminal['exit_code'],1)
                self.assertTrue(terminal['interpreter_settings_restored'])
                self.assertEqual((sys.pycache_prefix,sys.dont_write_bytecode,list(sys.path)),
                    (before[0],before[1],policy['isolated_base_paths']))
                return terminal
            finally:
                sys.pycache_prefix,sys.dont_write_bytecode=before[:2];sys.path[:]=before[2];sys.argv[:]=before[3]
                for key in tuple(sys.modules):
                    if key=='performance' or key.startswith('performance.'):sys.modules.pop(key)
                sys.modules.update(modules)
                sys.meta_path[:]=import_environment[0];sys.path_hooks[:]=import_environment[1]
                sys.path_importer_cache.clear();sys.path_importer_cache.update(import_environment[2])

    def test_candidate_compile_failure_restores_and_records(self):
        result=self.check_fault('code_read_lease.py',b'def broken !!!\n')
        self.assertIn('SyntaxError',result['error'])

    def test_malformed_json_restores_and_records(self):
        result=self.check_fault('code_allowlist_v3.json',b'{')
        self.assertIn('JSONDecodeError',result['error'])

    def test_duplicate_json_key_is_rejected(self):
        result=self.check_fault('code_allowlist_v3.json',b'{"files_sha256":{},"files_sha256":{}}')
        self.assertIn('duplicate JSON key',result['error'])

    def test_canonical_duplicate_is_rejected(self):
        result=self.check_fault('code_allowlist_v3.json',b'{"files_sha256":{"D:/a.py":"a","d:/a.py":"a"}}')
        self.assertIn('duplicate canonical',result['error'])

    def test_missing_after_pin_still_records_terminal(self):
        result=self.check_fault('code_read_lease.py',b'from pathlib import Path\nPath(__file__).unlink()\nraise RuntimeError("fault")\n')
        self.assertEqual(len(result['candidate_pin_read_errors']),1)
        self.assertFalse(result['candidate_bytes_unchanged'])

    def test_disallowed_pytest_target_is_rejected_and_recorded(self):
        result=self.check_fault('test_closure_v1.json',b'{"files_sha256":{}}',
            kind='pytest',targets=('tests/test_not_allowlisted.py',))
        self.assertIn('explicit zero-native synthetic test allowlist',result['error'])

    def test_receipt_write_failure_does_not_prevent_setting_restoration(self):
        raw=(HERE/'code_read_lease.py').read_bytes()+b'\n(Path(__file__).parent/"failure/interpreter_path_receipt.json").touch()\n'
        result=self.check_fault('code_read_lease.py',raw,kind='pytest',targets=('tests/test_not_allowlisted.py',))
        self.assertIn('FileExistsError',result['interpreter_receipt_error'])
        self.assertTrue(result['interpreter_settings_restored'])

    def test_whole_pytest_failure_restores_process_leases_and_records(self):
        reader=Path.read_bytes;getter=metadata.Distribution.version
        def main(*args,**kwargs):
            self.assertIsNot(Path.read_bytes,reader)
            self.assertIsNot(metadata.Distribution.version,getter)
            raise RuntimeError('pytest invocation failure')
        fake=SimpleNamespace(main=main,hookimpl=lambda **kw:lambda function:function)
        # This fault exercises the invocation exception after real admission.
        fake.__file__=sys.modules['pytest'].__file__
        fake.__spec__=sys.modules['pytest'].__spec__
        fake.__loader__=sys.modules['pytest'].__loader__
        from types import ModuleType
        module=ModuleType('pytest');vars(module).update(vars(sys.modules['pytest']));vars(module).update(vars(fake))
        with patch.dict(sys.modules,pytest=module):
            result=self.check_fault('test_closure_v1.json',b'{"files_sha256":{}}',
                kind='pytest',mode='parse_path',targets=('tests/test_h1_selector_source_window_development_v1.py',))
        self.assertIs(Path.read_bytes,reader);self.assertIs(metadata.Distribution.version,getter)
        self.assertIn('pytest invocation failure',result['error'])


if __name__=='__main__':unittest.main(verbosity=2)
