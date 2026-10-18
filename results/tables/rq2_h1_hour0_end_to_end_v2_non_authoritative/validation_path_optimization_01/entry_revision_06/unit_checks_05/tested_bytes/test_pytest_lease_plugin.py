from contextlib import ExitStack
from hashlib import sha256
import importlib.metadata as metadata
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from performance.code_read_lease import CodeReadLease
from performance.metadata_parse_lease import MetadataParseLease
from performance.pytest_lease_plugin import LeasePlugin


class PluginTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory(prefix='plugin_',dir=Path(__file__).parent)
        self.root=Path(self.temporary.name);self.code=self.root/'code.py';self.code.write_bytes(b'a=1\n')
        self.info=self.root/'demo-1.dist-info';self.info.mkdir();self.meta=self.info/'METADATA'
        self.meta.write_bytes(b'Metadata-Version: 2.1\nName: demo\nVersion: 1\n')
        self.read=Path.read_bytes;self.version=metadata.Distribution.version
        self.codes=[];self.records=[];self.terminal={}
        self.plugin=LeasePlugin(self.activate,self.record,self.terminal)

    def tearDown(self):
        self.assertIs(Path.read_bytes,self.read)
        self.assertIs(metadata.Distribution.version,self.version)
        self.assertTrue(all(not scope._handles for scope in self.codes))
        self.temporary.cleanup()

    def activate(self,stack):
        code=CodeReadLease({self.code:sha256(self.code.read_bytes()).hexdigest()},root=self.root)
        self.codes.append(code);stack.enter_context(code)
        parsed=stack.enter_context(MetadataParseLease({self.meta:sha256(self.meta.read_bytes()).hexdigest()}))
        return code,parsed

    def record(self,code,parsed,prefix,nodeid):
        self.records.append(dict(nodeid=nodeid,prefix=prefix,code=code.receipt(),parsed=parsed.receipt()))

    def hook(self):return self.plugin.pytest_runtest_call(SimpleNamespace(nodeid='tests/test_demo.py::test_call'))

    def test_success_records_nodeid_and_releases_hooks(self):
        hook=self.hook();next(hook)
        self.assertEqual(self.code.read_bytes(),b'a=1\n')
        self.assertEqual(metadata.PathDistribution(self.info).version,'1')
        with self.assertRaises(StopIteration):hook.send(None)
        self.assertEqual(self.records[0]['nodeid'],'tests/test_demo.py::test_call')
        self.assertTrue(self.terminal['pytest_test_calls'][0]['scope_exited'])

    def test_testcall_exception_releases_both_hooks(self):
        hook=self.hook();next(hook)
        with self.assertRaisesRegex(RuntimeError,'test failure'):hook.throw(RuntimeError('test failure'))
        self.assertEqual(self.records,[])
        self.assertTrue(self.terminal['pytest_test_calls'][0]['scope_error'])

    def test_second_lease_entry_failure_releases_first_lease(self):
        with patch.object(MetadataParseLease,'__enter__',side_effect=RuntimeError('entry failure')):
            with self.assertRaisesRegex(RuntimeError,'entry failure'):next(self.hook())
        self.assertFalse(self.terminal['pytest_test_calls'][0]['scope_entered'])

    def test_failed_pytest_outcome_is_recorded_as_failure(self):
        hook=self.hook();next(hook)
        with self.assertRaises(StopIteration):hook.send(None)
        self.plugin.pytest_runtest_logreport(SimpleNamespace(nodeid='tests/test_demo.py::test_call',when='call',outcome='failed'))
        self.plugin.pytest_sessionfinish(SimpleNamespace(testscollected=1,testsfailed=1),1)
        self.assertEqual(self.terminal['pytest_call_outcomes'],dict(passed=0,failed=1,skipped=0))
        self.assertEqual(self.terminal['pytest_tests_failed'],1)

    def test_session_scope_preserves_reader_identity_between_test_windows(self):
        with ExitStack() as session:
            code,parsed=self.activate(session);reader=Path.read_bytes;getter=metadata.Distribution.version
            def window(unused):parsed.begin_discovery_window();return code,parsed
            plugin=LeasePlugin(window,self.record,{})
            for index in range(2):
                hook=plugin.pytest_runtest_call(SimpleNamespace(nodeid='test_'+str(index)))
                next(hook)
                with self.assertRaises(StopIteration):hook.send(None)
                self.assertIs(Path.read_bytes,reader)
                self.assertIs(metadata.Distribution.version,getter)


if __name__=='__main__':unittest.main(verbosity=2)
