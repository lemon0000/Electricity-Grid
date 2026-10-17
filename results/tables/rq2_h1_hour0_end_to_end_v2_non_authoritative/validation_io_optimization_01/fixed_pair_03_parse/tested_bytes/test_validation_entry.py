"""Faults during initialization must still restore settings and write a terminal."""
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest


HERE=Path(__file__).resolve().parent


class EntryFailureTests(unittest.TestCase):
    def check_fault(self,name,raw):
        with tempfile.TemporaryDirectory(prefix='entry_fault_',dir=HERE) as temporary:
            folder=Path(temporary)
            names=('validation_entry.py','code_read_lease.py','metadata_parse_lease.py',
                'code_allowlist_v3.json','metadata_allowlist_v1.json','test_closure_v1.json')
            sources={key:(HERE/key).read_bytes() for key in names};sources[name]=raw
            for key,value in sources.items():(folder/key).write_bytes(value)
            before=(sys.pycache_prefix,sys.dont_write_bytecode,list(sys.path),list(sys.argv))
            modules={key:value for key,value in sys.modules.items() if key=='performance' or key.startswith('performance.')}
            sys.argv=['entry','unit','plain','failure']
            scope=dict(__file__=str(folder/'validation_entry.py'),__name__='__entry_fault__',
                _pinned_sources=sources,_bootstrap_sources={},_launcher_sha256='test',_manifest_sha256='test')
            try:
                with redirect_stdout(io.StringIO()),self.assertRaises(SystemExit) as failure:
                    exec(compile(sources['validation_entry.py'],scope['__file__'],'exec'),scope)
                self.assertEqual(failure.exception.code,1)
                terminal=json.loads((folder/'failure/terminal.json').read_bytes())
                self.assertEqual(terminal['exit_code'],1)
                self.assertTrue(terminal['interpreter_settings_restored'])
                self.assertEqual((sys.pycache_prefix,sys.dont_write_bytecode,list(sys.path)),before[:3])
                return terminal
            finally:
                sys.pycache_prefix,sys.dont_write_bytecode=before[:2];sys.path[:]=before[2];sys.argv[:]=before[3]
                for key in tuple(sys.modules):
                    if key=='performance' or key.startswith('performance.'):sys.modules.pop(key)
                sys.modules.update(modules)

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


if __name__=='__main__':unittest.main(verbosity=2)
