"""Ordinary draft fault tests; no formal/native/resource authority."""
from hashlib import sha256
from contextlib import contextmanager
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from time import perf_counter
import unittest
from unittest.mock import patch
from types import ModuleType

from performance import code_read_lease as base
from performance import static_scientific_input_read_lease_v2 as candidate


REPO = Path('D:/CUHKSZ/Research Project/electricity-grid')
UNIT_EVIDENCE = {}


class StaticInputLeaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='h1sio_', dir='D:/')
        self.root = Path(self.temp.name)
        self.original = Path.read_bytes
        self.code = self.root/'a.py'
        self.code.write_bytes(b'value = 1\n')
        for relative, _, _ in candidate.SCIENTIFIC_INPUTS:
            path = self.root/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(self.original(REPO/relative))
        self.science = candidate.scientific_inputs(self.root)

    def tearDown(self):
        try:
            self.assertIs(Path.read_bytes, self.original)
        finally:
            Path.read_bytes = self.original
            self.temp.cleanup()

    def lease(self, **kw):
        return candidate.StaticScientificInputReadLease(
            {str(self.code): sha256(self.original(self.code)).hexdigest()},
            self.science, root=self.root, code_root=Path('D:/'), **kw)

    @contextmanager
    def fault_api(self, close, *, seal_fault=False):
        # Explicitly synthetic module/API for fault injection. Its receipt is
        # never an identity or acceptance receipt for the canonical candidate.
        name = 'performance.static_input_synthetic_close_fault'
        module = ModuleType(name); module.__file__ = candidate.__file__
        module.__package__ = 'performance'
        sys.modules[name] = module
        original_enter = base.CodeReadLease.__enter__
        class BadItems(dict):
            def items(self): raise RuntimeError('injected seal failure')
        def enter(owner):
            value = original_enter(owner)
            if seal_fault: owner._entry = BadItems(owner._entry)
            return value
        try:
            with patch.object(base._kernel, 'CloseHandle', close), patch.object(base.CodeReadLease, '__enter__', enter):
                exec(compile(self.original(Path(candidate.__file__)), candidate.__file__, 'exec'), vars(module))
                scope = module.StaticScientificInputReadLease(
                    {self.code: sha256(self.original(self.code)).hexdigest()}, self.science,
                    root=self.root, code_root=Path('D:/'))
                yield scope
        finally:
            sys.modules.pop(name, None)

    def test_both_scientific_files_deny_write_replace_delete_and_rename(self):
        with self.lease() as scope:
            for name in self.science:
                path = Path(name)
                replacement = self.root/'replacement.json'
                replacement.write_bytes(b'{}')
                for action in (lambda: path.write_bytes(b'{}'),
                               lambda: os.replace(replacement, path),
                               lambda: path.unlink(),
                               lambda: path.rename(path.with_suffix('.renamed'))):
                    with self.assertRaises(PermissionError):
                        action()
                self.assertEqual(path.read_bytes(), self.original(path))
                replacement.unlink()
            with self.assertRaises(PermissionError):
                self.root.rename(self.root.with_name(self.root.name+'_renamed'))
        closed = scope.closed_receipt()
        self.assertTrue(closed['all_handles_closed'])
        self.assertTrue(closed['exit_files_and_ancestors_verified'])
        self.assertTrue(closed['static_scientific_input_bytes_cached'])
        self.assertTrue(closed['repair_cap_table_bytes_cached'])
        for key in ('formal_result', 'resource_admission', 'native_execution_authorized', 'production_seal'):
            self.assertFalse(closed[key])

    def test_unlisted_json_and_proposal_markdown_stay_fresh(self):
        with self.lease() as scope:
            for name in ('third.json', 'proposal.md'):
                path = self.root/name
                path.write_bytes(b'one')
                self.assertEqual(path.read_bytes(), b'one')
                path.write_bytes(b'two')
                self.assertEqual(path.read_bytes(), b'two')
            self.assertEqual(scope.receipt()['fallback_reads'], 4)

    def test_scientific_allowlist_rejects_missing_extra_hash_size_case_relative_and_dotdot(self):
        first = next(iter(self.science))
        changes = []
        missing = dict(self.science); missing.pop(first); changes.append(missing)
        extra = dict(self.science); extra[str(self.root/'third.json')] = dict(sha256='0'*64, size_bytes=2); changes.append(extra)
        for field, value in (('sha256', '0'*64), ('size_bytes', 889)):
            altered = {p: dict(row) for p, row in self.science.items()}
            altered[first][field] = value; changes.append(altered)
        for alias in (first.upper(), str(Path(first).relative_to(self.root)),
                      str(self.root/'..'/self.root.name/Path(first).relative_to(self.root))):
            altered = dict(self.science); altered[alias] = altered.pop(first); changes.append(altered)
        duplicate = dict(self.science); duplicate[first.upper()] = duplicate[first]; changes.append(duplicate)
        for declaration in changes:
            with self.subTest(declaration=declaration), self.assertRaisesRegex(ValueError, 'exact two'):
                candidate.StaticScientificInputReadLease(
                    {self.code: '0'*64}, declaration, root=self.root, code_root=Path('D:/'))

    def test_wrong_scientific_file_bytes_size_and_partial_acquisition_close_handles(self):
        path = Path(next(iter(self.science)))
        original = self.original(path)
        for raw in (b'X'+original[1:], original+b' '):
            path.write_bytes(raw)
            scope = self.lease()
            with self.assertRaises(ValueError):
                scope.__enter__()
            closed = scope.closed_receipt()
            self.assertTrue(closed['all_handles_closed'])
            self.assertTrue(closed['original_alias_restored'])
            self.assertIsNotNone(closed['first_failure'])
            path.write_bytes(original)

    def test_hardlinked_scientific_file_is_rejected(self):
        target = Path(next(iter(self.science)))
        alias = self.root/'linked.json'
        os.link(target, alias)
        scope = self.lease()
        try:
            with self.assertRaisesRegex(ValueError, 'regular local'):
                scope.__enter__()
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])
        finally:
            alias.unlink()

    def test_reparse_ancestor_is_rejected(self):
        target = self.root/'real_results'
        (self.root/'results').rename(target)
        alias = self.root/'results'
        made = subprocess.run(['cmd.exe', '/d', '/c', 'mklink', '/J', str(alias), str(target)], capture_output=True)
        self.assertEqual(made.returncode, 0, made.stderr)
        scope = self.lease()
        try:
            with self.assertRaisesRegex(ValueError, 'regular local'):
                scope.__enter__()
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])
        finally:
            alias.rmdir()
            target.rename(alias)

    def test_existing_writer_denies_acquisition(self):
        target = Path(next(iter(self.science)))
        scope = self.lease()
        with target.open('r+b'):
            with self.assertRaises(OSError):
                scope.__enter__()
        self.assertTrue(scope.closed_receipt()['all_handles_closed'])

    def test_read_hook_code_defaults_closure_state_and_allowlist_mutations_fail(self):
        def other(path):
            return b'foreign'
        for mutation in ('code', 'defaults', 'closure', 'state', 'allowlist', 'data', 'guard', 'science'):
            scope = self.lease()
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                with scope:
                    if mutation == 'code':
                        # Match the wrapper's closure arity while changing code.
                        scope._cached_read.__code__ = scope._cached_read.__code__.replace(co_name='tampered')
                    elif mutation == 'defaults': scope._cached_read.__defaults__ = (None,)
                    elif mutation == 'closure':
                        cell = scope._cached_read.__closure__[0]
                        cell.cell_contents = None
                    elif mutation == 'state': scope._state = 'foreign'
                    elif mutation == 'allowlist': scope._expected = {}
                    elif mutation == 'data': scope._data = {}
                    elif mutation == 'guard': scope._guard = None
                    elif mutation == 'science': scope._science = {}
                    scope.receipt()
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])
            self.assertTrue(scope.closed_receipt()['original_alias_restored'])

    def test_foreign_read_binding_preserved_and_first_body_error_kept(self):
        foreign = lambda path: b'foreign'
        sentinel = RuntimeError('first body failure')
        scope = self.lease()
        try:
            with self.assertRaises(RuntimeError) as caught:
                with scope:
                    Path.read_bytes = foreign
                    raise sentinel
            self.assertIs(caught.exception, sentinel)
            self.assertIs(Path.read_bytes, foreign)
            closed = scope.closed_receipt()
            self.assertTrue(closed['foreign_alias_preserved'])
            self.assertFalse(closed['original_alias_restored'])
            self.assertEqual(closed['first_failure'], repr(sentinel))
            self.assertTrue(closed['cleanup_errors'])
            self.assertTrue(closed['all_handles_closed'])
        finally:
            Path.read_bytes = self.original

    def test_close_handle_failure_retains_only_failed_handle_for_retry(self):
        actual = base._kernel.CloseHandle
        failed = []
        def fail_once(handle):
            if not failed:
                failed.append(handle)
                base.ctypes.set_last_error(5)
                return 0
            return actual(handle)
        with self.fault_api(fail_once) as scope:
            scope.__enter__()
            with self.assertRaises(OSError):
                scope.__exit__(None, None, None)
            closed = scope.closed_receipt()
            self.assertFalse(closed['all_handles_closed'])
            self.assertEqual(scope._handles, failed)
            self.assertEqual(len(closed['cleanup_errors']), 1)
            final = scope.retry_cleanup()
        self.assertTrue(final['all_handles_closed'])
        self.assertTrue(final['cleanup_errors'])
        self.assertIsNotNone(final['first_failure'])

    def test_partial_acquisition_cleanup_failure_preserves_first_failure(self):
        target = Path(next(iter(self.science)))
        target.write_bytes(b'wrong')
        actual = base._kernel.CloseHandle
        enabled = [True]
        def close(handle): return 0 if enabled[0] else actual(handle)
        with self.fault_api(close) as scope:
            with self.assertRaisesRegex(ValueError, 'size differs'):
                scope.__enter__()
            self.assertFalse(scope.closed_receipt()['all_handles_closed'])
            self.assertIn('size differs', scope.closed_receipt()['first_failure'])
            enabled[0] = False
            self.assertTrue(scope.retry_cleanup()['all_handles_closed'])

    def test_body_verification_and_close_faults_keep_first_error_and_retry_history(self):
        actual = base._kernel.CloseHandle
        enabled = [True]
        def close(handle): return 0 if enabled[0] else actual(handle)
        sentinel = RuntimeError('original body error')
        with self.fault_api(close) as scope:
            with self.assertRaises(RuntimeError) as caught:
                with scope:
                    scope._data = {}
                    raise sentinel
            self.assertIs(caught.exception, sentinel)
            closed = scope.closed_receipt()
            self.assertEqual(closed['first_failure'], repr(sentinel))
            self.assertFalse(closed['all_handles_closed'])
            self.assertFalse(closed['exit_files_and_ancestors_verified'])
            enabled[0] = False
            final = scope.retry_cleanup()
            self.assertTrue(final['all_handles_closed'])
            self.assertEqual(final['first_failure'], repr(sentinel))
            self.assertTrue(final['cleanup_errors'])
            with self.assertRaisesRegex(ValueError, 'failed cleanup'):
                scope.retry_cleanup()

    def test_runtime_base_helper_and_kernel_changes_rejected_with_captured_cleanup(self):
        changes = [(base.CodeReadLease, '_open'), (base, '_bytes'), (base, '_key'),
                   (base, '_identity'), (base._kernel, 'CloseHandle'),
                   (base._kernel, 'GetFileInformationByHandleEx'),
                   (candidate, 'SCIENTIFIC_INPUTS'), (candidate, 'scientific_inputs')]
        for obj, name in changes:
            scope = self.lease(); scope.__enter__()
            with self.subTest(name=name), patch.object(obj, name, lambda *a: b'foreign'):
                with self.assertRaisesRegex(ValueError, 'runtime dependency'):
                    scope.receipt()
                with self.assertRaisesRegex(ValueError, 'runtime dependency'):
                    scope.__exit__(None, None, None)
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])
            self.assertFalse(scope.closed_receipt()['exit_files_and_ancestors_verified'])
        for fn in (base.CodeReadLease._open, base._bytes, candidate.scientific_inputs):
            scope = self.lease(); scope.__enter__()
            original = fn.__code__
            try:
                fn.__code__ = original.replace(co_name='tampered')
                with self.assertRaisesRegex(ValueError, 'runtime dependency'):
                    scope.__exit__(None, None, None)
            finally:
                fn.__code__ = original
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])

    def test_immutable_owned_inventory_cannot_be_shrunk_or_replaced(self):
        for name, replacement in (('_handles', []), ('_entry', {}), ('_files', {}), ('_identities', {})):
            scope = self.lease(); scope.__enter__()
            expected = scope._bound_capsule[4]()[0]
            with self.subTest(name=name):
                setattr(scope, name, replacement)
                with self.assertRaisesRegex(ValueError, 'inventory changed'):
                    scope.__exit__(None, None, None)
            closed = scope.closed_receipt()
            self.assertEqual(closed['opened_handle_count'], len(expected))
            self.assertEqual(closed['closed_handle_count'], len(expected))
            self.assertTrue(closed['all_handles_closed'])
            self.assertIsNotNone(closed['first_failure'])
        with self.lease() as scope:
            path = next(iter(scope._entry))
            with self.assertRaises(TypeError): scope._entry[path][1]['identity'] = (0, 0)
            with self.assertRaises(TypeError): scope._entry[path] = None
            with self.assertRaises(AttributeError): scope._handles.clear()

    def test_seal_failure_after_hook_install_restores_alias_and_closes_handles(self):
        with self.fault_api(base._kernel.CloseHandle, seal_fault=True) as scope:
            with self.assertRaisesRegex(RuntimeError, 'injected seal failure'):
                scope.__enter__()
            closed = scope.closed_receipt()
            self.assertTrue(closed['hook_installed'])
            self.assertTrue(closed['original_alias_restored'])
            self.assertTrue(closed['all_handles_closed'])
            self.assertIn('injected seal failure', closed['first_failure'])
            self.assertIs(Path.read_bytes, self.original)

    def test_capsule_function_code_defaults_and_closure_tamper_cannot_forge_cleanup(self):
        for index in range(5):
            for fault in ('code', 'defaults', 'closure'):
                scope = self.lease(); scope.__enter__()
                fn = scope._capsule[index]
                with self.subTest(index=index,fault=fault):
                    if fault == 'code': fn.__code__ = fn.__code__.replace(co_name='tampered')
                    elif fault == 'defaults': fn.__defaults__ = (None,)
                    else: fn.__closure__[0].cell_contents = None
                    with self.assertRaisesRegex(ValueError, 'capsule function'):
                        scope.__exit__(None,None,None)
                closed = scope.closed_receipt()
                self.assertTrue(closed['all_handles_closed'])
                self.assertTrue(closed['original_alias_restored'])
                self.assertIsNotNone(closed['first_failure'])
                self.assertEqual(closed['closed_handle_count'],closed['opened_handle_count'])

    def test_capi_errcheck_argtypes_and_restype_changes_reject_with_independent_close(self):
        for name in ('CloseHandle','GetFileInformationByHandleEx'):
            fn = getattr(base._kernel,name)
            for attribute in ('errcheck','argtypes','restype'):
                scope = self.lease(); scope.__enter__()
                before = getattr(fn,attribute,None)
                try:
                    if attribute == 'errcheck': fn.errcheck = lambda result,function,args: 1
                    elif attribute == 'argtypes': fn.argtypes = ()
                    else: fn.restype = base.ctypes.c_int64
                    with self.assertRaisesRegex(ValueError,'runtime dependency'):
                        scope.__exit__(None,None,None)
                finally:
                    if attribute == 'errcheck' and before is None: del fn.errcheck
                    else: setattr(fn,attribute,before)
                self.assertTrue(scope.closed_receipt()['all_handles_closed'])
                self.assertFalse(scope.closed_receipt()['exit_files_and_ancestors_verified'])

    def test_working_control_field_replacement_cannot_change_owned_cleanup(self):
        for name in ('_capsule_signatures','_release_recipe','_state_recipe','_verify_recipe',
                     '_function_type','_cell_type','_installed_reader','_owner_guard','_path_type','_restore_read','_science_keys','_control'):
            scope = self.lease(); scope.__enter__()
            with self.subTest(name=name):
                setattr(scope,name,None)
                with self.assertRaises(ValueError): scope.__exit__(None,None,None)
            closed = scope.closed_receipt()
            self.assertTrue(closed['all_handles_closed'])
            self.assertTrue(closed['original_alias_restored'])
            self.assertIsNotNone(closed['first_failure'])
        scope = self.lease(); foreign = lambda path:b'foreign'
        try:
            with self.assertRaises(ValueError):
                with scope:
                    scope._installed_reader = foreign
                    Path.read_bytes = foreign
            self.assertIs(Path.read_bytes,foreign)
            self.assertTrue(scope.closed_receipt()['foreign_alias_preserved'])
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])
        finally: Path.read_bytes = self.original

    def test_base_globals_path_and_normcase_code_changes_reject_with_cleanup(self):
        for obj,name in ((base,'sha256'),(base,'Path'),(base.os.path,'normcase'),(Path,'stat')):
            scope = self.lease(); scope.__enter__()
            with self.subTest(name=name), patch.object(obj,name,lambda *args,**kw:None):
                with self.assertRaisesRegex(ValueError,'runtime dependency'):
                    scope.__exit__(None,None,None)
            self.assertTrue(scope.closed_receipt()['all_handles_closed'])

    def test_light_code_reads_never_allow_runtime_drift_to_become_clean_success(self):
        for checkpoint in ('receipt','exit'):
            for fault in ('base_global','path_code','kernel_errcheck','capsule_code','control'):
                scope = self.lease(); scope.__enter__()
                Path(next(iter(self.science))).read_bytes()
                original_code = Path.open.__code__
                api = base._kernel.GetFileInformationByHandleEx
                restore = None
                try:
                    if fault == 'base_global':
                        before = base.sha256; base.sha256 = lambda *a:None
                        restore = lambda:setattr(base,'sha256',before)
                    elif fault == 'path_code':
                        Path.open.__code__ = original_code.replace(co_name='tampered')
                        restore = lambda:setattr(Path.open,'__code__',original_code)
                    elif fault == 'kernel_errcheck':
                        api.errcheck = lambda result,function,args:result
                        restore = lambda:delattr(api,'errcheck')
                    elif fault == 'capsule_code':
                        fn = scope._capsule[2]; fn.__code__ = fn.__code__.replace(co_name='tampered')
                    else: scope._control = None
                    # Light checks may refuse early. They may also return the
                    # held original code; neither outcome is final success.
                    try: self.assertEqual(self.code.read_bytes(),b'value = 1\n')
                    except ValueError: pass
                    if checkpoint == 'receipt':
                        with self.assertRaises(ValueError): scope.receipt()
                    with self.assertRaises(ValueError): scope.__exit__(None,None,None)
                finally:
                    if restore: restore()
                closed = scope.closed_receipt()
                self.assertTrue(closed['all_handles_closed'])
                self.assertTrue(closed['original_alias_restored'])
                self.assertIsNotNone(closed['first_failure'])

    def test_scientific_key_alias_change_cannot_downgrade_real_input_to_light_read(self):
        scope = self.lease(); scope.__enter__()
        scope._science_keys = frozenset()
        with self.assertRaisesRegex(ValueError,'control binding'):
            Path(next(iter(self.science))).read_bytes()
        with self.assertRaises(ValueError): scope.__exit__(None,None,None)
        self.assertTrue(scope.closed_receipt()['all_handles_closed'])

    def test_entry12_refuses_unimplemented_arm_phase_and_plain_cli(self):
        launcher = Path(__file__).parent/'launch_validation.py'
        for kind,mode in [('arm',m) for m in ('plain','leased','parse')]+[('phase',m) for m in ('plain','leased','parse')]+[('pytest','plain')]:
            completed = subprocess.run([sys.executable,'-B','-I',str(launcher),kind,mode,'unsupported_route'],
                capture_output=True,text=True,timeout=15)
            self.assertNotEqual(completed.returncode,0)
            self.assertIn('entry12 supports only',completed.stderr)

    def test_exit_identity_hash_and_nlink_faults_reject_and_close(self):
        for fault in ('identity', 'hash', 'nlink'):
            scope = self.lease(); scope.__enter__()
            original_observation = scope._observation
            def changed(path, handle, directory):
                row = original_observation(path, handle, directory)
                if not directory:
                    if fault == 'identity': row['identity'] = (0, 0)
                    if fault == 'nlink': row['nlink'] = 2
                return row
            try:
                with self.subTest(fault=fault):
                    with patch.object(scope, '_observation', changed), patch.object(
                            base, '_bytes', (lambda handle, cap: b'wrong') if fault == 'hash' else base._bytes):
                        with self.assertRaises(ValueError):
                            scope.__exit__(None, None, None)
                self.assertTrue(scope.closed_receipt()['all_handles_closed'])
                self.assertFalse(scope.closed_receipt()['exit_files_and_ancestors_verified'])
            finally:
                if scope._handles: scope.retry_cleanup()

    def test_genuine_registry_science_identities_and_repair_digest_equal_plain_and_held(self):
        from experiments import h1_outage_registry_development_v1 as registry
        from experiments import h1_origin_grid_step_development_v1 as physical
        def observe():
            return dict(implementation=registry.implementation_identity(),
                        splits={split: dict(identity=row['identity'], cap_table=row['cap_table_sha256'],
                            caps=sha256(json.dumps({k: str(v) for k, v in row['caps'].items()}, sort_keys=True).encode()).hexdigest())
                            for split in ('training', 'holdout') for row in (registry._load(split),)},
                        repair_digest=physical.repair_mechanism_identity())
        plain = observe()
        scope = candidate.StaticScientificInputReadLease(
            {self.code: sha256(self.original(self.code)).hexdigest()}, candidate.scientific_inputs(REPO),
            root=REPO, code_root=Path('D:/'))
        with scope:
            held = observe()
        after = observe()
        self.assertEqual(plain, held)
        self.assertEqual(plain, after)
        UNIT_EVIDENCE['genuine_scientific_equivalence'] = dict(
            observations=plain, plain_equals_held_equals_after=True,
            static_input_hits=scope.closed_receipt()['scientific_input_read_hits'],
            exit_proof=scope.closed_receipt()['exit_files_and_ancestors_verified'], formal_result=False)

    def test_repeated_original_pin_reads_have_equal_bytes_and_measured_io_cost(self):
        from experiments import h1_outage_registry_development_v1 as registry
        pairs = [(REPO/relative, pin) for relative, pin, _ in candidate.SCIENTIFIC_INPUTS]
        count = 1000
        begin = perf_counter()
        for _ in range(count):
            for path, pin in pairs: registry._pin(path, pin)
        plain_seconds = perf_counter()-begin
        scope = candidate.StaticScientificInputReadLease(
            {self.code: sha256(self.original(self.code)).hexdigest()}, candidate.scientific_inputs(REPO),
            root=REPO, code_root=Path('D:/'))
        begin = perf_counter(); scope.__enter__(); entered = perf_counter()
        for _ in range(count):
            for path, pin in pairs: registry._pin(path, pin)
        done = perf_counter(); scope.__exit__(None, None, None); closed = perf_counter()
        receipt = scope.closed_receipt()
        self.assertEqual(receipt['scientific_input_read_hits'], count*2)
        self.assertEqual(receipt['fallback_reads'], 0)
        UNIT_EVIDENCE['original_pin_microbenchmark'] = dict(
            calls=count*2, plain_seconds=plain_seconds,
            entry_seconds=entered-begin, held_pin_seconds=done-entered,
            exit_seconds=closed-done, total_held_seconds=closed-begin,
            sha_checked_every_call=True, numerical_or_source_rows_cached=False,
            full_workflow_speedup_established=False, formal_result=False)

    def test_mixed_code_and_original_pin_read_cost_includes_runtime_checks(self):
        from experiments import h1_outage_registry_development_v1 as registry
        pairs = [(REPO/relative, pin) for relative, pin, _ in candidate.SCIENTIFIC_INPUTS]
        codes = {self.code: sha256(self.original(self.code)).hexdigest()}
        count = 1000
        def work():
            for _ in range(count):
                for _ in range(10): self.code.read_bytes()
                for path, pin in pairs: registry._pin(path, pin)
        old_start = perf_counter()
        with base.CodeReadLease(codes, root=Path('D:/')) as predecessor:
            begin = perf_counter(); work(); predecessor.receipt(); old_seconds = perf_counter()-begin
        old_total = perf_counter()-old_start
        new_start = perf_counter()
        with candidate.StaticScientificInputReadLease(codes, candidate.scientific_inputs(REPO),
                root=REPO, code_root=Path('D:/')) as scope:
            begin = perf_counter(); work(); scope.receipt(); new_seconds = perf_counter()-begin
        new_total = perf_counter()-new_start
        self.assertEqual(scope.closed_receipt()['code_read_hits'], count*10)
        self.assertEqual(scope.closed_receipt()['scientific_input_read_hits'], count*2)
        self.assertEqual(scope.closed_receipt()['full_scientific_checks'], count*2)
        self.assertEqual(scope.closed_receipt()['light_code_checks'], count*10)
        UNIT_EVIDENCE['mixed_code_and_pin_microbenchmark'] = dict(
            code_reads=count*10, original_pin_reads=count*2,
            predecessor_code_lease_seconds=old_seconds, successor_seconds=new_seconds,
            predecessor_total_seconds_including_entry_receipt_exit=old_total,
            successor_total_seconds_including_entry_receipt_exit=new_total,
            measured_runtime_guard_overhead_included=True, formal_result=False,
            full_workflow_speedup_established=False)


if __name__ == '__main__':
    unittest.main(verbosity=2)
