"""Inject route faults at actual lifecycle hooks and verify required cleanup."""
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

from performance.interpreter_path_policy import InterpreterPathPolicy
from performance.pytest_admission_plugin import AdmissionPlugin


HERE=Path(__file__).resolve().parent


class AdmissionLifecycleTests(unittest.TestCase):
    def setUp(self):
        self.paths=list(sys.path)
        declaration=json.loads((HERE/'interpreter_path_policy_v1.json').read_bytes())
        self.policy=InterpreterPathPolicy(declaration)
        sys.path[:]=declaration['isolated_base_paths'];self.policy.configure()
        self.plugin=AdmissionPlugin(self.policy)
        self.item=SimpleNamespace(nodeid='test_non_authoritative')

    def tearDown(self):sys.path[:]=self.paths

    def hook(self,phase):
        fn=getattr(self.plugin,'pytest_runtest_'+phase)
        return fn(self.item,None) if phase=='teardown' else fn(self.item)

    def test_collection_failure_is_recorded(self):
        sys.path.append(str(HERE))
        with self.assertRaisesRegex(ValueError,'search paths changed'):
            self.plugin.pytest_collection_finish(None)
        self.assertEqual(self.policy.failure['boundary'],'after_collection_before_fixtures')

    def test_setup_entry_failure_prevents_fixture_body(self):
        sys.path.append(str(HERE));hook=self.hook('setup')
        with self.assertRaisesRegex(ValueError,'search paths changed'):next(hook)
        self.assertEqual(self.policy.failure['boundary'],'setup_entry:'+self.item.nodeid)

    def test_setup_exit_failure_is_recorded(self):
        hook=self.hook('setup');next(hook);sys.path.append(str(HERE))
        with self.assertRaisesRegex(ValueError,'search paths changed'):hook.send(None)
        self.assertEqual(self.policy.failure['boundary'],'setup_exit:'+self.item.nodeid)

    def test_call_entry_failure_prevents_test_body(self):
        sys.path.append(str(HERE));hook=self.hook('call')
        with self.assertRaisesRegex(ValueError,'search paths changed'):next(hook)
        self.assertEqual(self.policy.failure['boundary'],'call_entry:'+self.item.nodeid)

    def test_call_exit_poison_still_allows_fixture_teardown(self):
        hook=self.hook('call');next(hook);sys.path.append(str(HERE))
        with self.assertRaisesRegex(ValueError,'search paths changed'):hook.send(None)
        cleanup=[];teardown=self.hook('teardown')
        next(teardown);cleanup.append('fixture_finalizer_executed')
        with self.assertRaisesRegex(ValueError,'poisoned at call_exit'):teardown.send(None)
        self.assertEqual(cleanup,['fixture_finalizer_executed'])
        self.assertEqual(self.policy.failure['boundary'],'call_exit:'+self.item.nodeid)

    def test_teardown_entry_failure_runs_cleanup_before_reporting(self):
        sys.path.append(str(HERE));hook=self.hook('teardown')
        next(hook)
        with self.assertRaisesRegex(ValueError,'search paths changed'):hook.send(None)
        self.assertEqual(self.policy.failure['boundary'],'teardown_entry:'+self.item.nodeid)

    def test_teardown_exit_failure_is_recorded(self):
        hook=self.hook('teardown');next(hook);sys.path.append(str(HERE))
        with self.assertRaisesRegex(ValueError,'search paths changed'):hook.send(None)
        self.assertEqual(self.policy.failure['boundary'],'teardown_exit:'+self.item.nodeid)

    def test_test_exception_keeps_call_exit_and_cleanup(self):
        hook=self.hook('call');next(hook)
        with self.assertRaisesRegex(RuntimeError,'body failure'):hook.throw(RuntimeError('body failure'))
        teardown=self.hook('teardown');next(teardown)
        with self.assertRaises(StopIteration):teardown.send(None)
        self.assertIsNone(self.policy.failure)
        boundaries=[r['boundary'] for r in self.policy.observations]
        self.assertIn('call_exit:'+self.item.nodeid,boundaries)
        self.assertIn('teardown_exit:'+self.item.nodeid,boundaries)


if __name__=='__main__':unittest.main(verbosity=2)
