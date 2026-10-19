"""Real raw reads and real static byte owner; zero Job/native execution."""
from contextlib import contextmanager, nullcontext
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from threading import Thread
from time import perf_counter
from types import FunctionType
import unittest
from unittest.mock import patch

from performance import bounded_stable_read_overlay_v1 as overlay


UNIT_EVIDENCE = {}
REPO = Path(overlay.raw.__file__).parents[1]


class OverlayTests(unittest.TestCase):
    def setUp(self):
        self.open = Path.open
        self.read_bytes = Path.read_bytes
        self.temporary = tempfile.TemporaryDirectory(prefix='h1_overlay_', dir='D:/')
        self.file = Path(self.temporary.name)/'tiny.bin'
        self.file.write_bytes(b'bounded fresh data')

    def tearDown(self):
        self.assertIs(Path.open, self.open)
        self.assertIs(Path.read_bytes, self.read_bytes)
        self.temporary.cleanup()

    @contextmanager
    def configured(self, *, open_function=None, before_bind=None, after_quiesce=None):
        previous = sys.modules.pop(overlay.BYTE_MODULE, None)
        context = patch.object(Path, 'open', open_function) if open_function is not None else nullcontext()
        try:
            with context:
                op = overlay.operation()
                self.last = op
                with op.install():
                    if before_bind is not None: before_bind()
                    path = Path(__file__).with_name('static_scientific_input_read_lease_v2.py')
                    spec = importlib.util.spec_from_file_location(overlay.BYTE_MODULE, path)
                    module = importlib.util.module_from_spec(spec)
                    sys.modules[overlay.BYTE_MODULE] = module
                    spec.loader.exec_module(module)
                    expected = {Path(overlay.raw.__file__): overlay.RAW_SHA256}
                    scientific = json.loads(Path(__file__).with_name('scientific_input_allowlist_v1.json').read_bytes())['files']
                    owner = module.StaticScientificInputReadLease(expected, scientific, root=REPO, code_root=Path('D:/'))
                    with owner:
                        reader = Path.read_bytes
                        with op.bind(owner):
                            self.assertIs(Path.read_bytes, reader)
                            yield op, owner, module
                        if after_quiesce is not None: after_quiesce()
                    self.assertIs(Path.read_bytes, self.read_bytes)
        finally:
            sys.modules.pop(overlay.BYTE_MODULE, None)
            if previous is not None: sys.modules[overlay.BYTE_MODULE] = previous

    def test_genuine_bookends_bytes_stamps_and_single_owner(self):
        baseline = overlay.raw.read_stable(self.file, 32*1024**2)
        pins = {str(p): sha256(p.read_bytes()).hexdigest() for p in (Path(overlay.__file__), Path(overlay.raw.__file__))}
        with self.configured() as (op, owner, module):
            held_reader = Path.read_bytes
            actual = overlay.raw.read_stable(self.file, 32*1024**2)
            self.assertIs(Path.read_bytes, held_reader)
            self.assertEqual(actual, baseline)
            self.file.write_bytes(b'new content')
            self.assertEqual(overlay.raw.read_stable(self.file, 32*1024**2)[0], b'new content')
        receipt = op.closed_receipt()
        self.assertTrue(receipt['original_open_restored'])
        self.assertTrue(receipt['original_read_bytes_restored'])
        self.assertEqual(receipt['remaining_streams'], 0)
        self.assertEqual(receipt['bounded_read_calls'], 2)
        self.assertEqual(receipt['bounded_requested_bytes'], len(b'bounded fresh data')+1+len(b'new content')+1)
        self.assertEqual(receipt['original_requested_bytes'], 2*(32*1024**2+1))
        self.assertTrue(receipt['byte_owner_closed_receipt']['all_handles_closed'])
        self.assertTrue(receipt['byte_owner_closed_receipt']['exit_files_and_ancestors_verified'])
        self.assertIsNone(receipt['first_failure'])
        self.assertEqual(pins, {p: sha256(Path(p).read_bytes()).hexdigest() for p in pins})
        UNIT_EVIDENCE['genuine'] = dict(baseline_stamp=baseline[1], actual_stamp=actual[1],
            identical_bytes_and_stamp=True, source_pins=pins, receipt=receipt, real_Jobs=0, real_native_calls=0)

    def test_empty_exact_cap_and_one_byte_excess_keep_original_acceptance(self):
        with self.configured():
            for payload in (b'', b'x', b'xyz'):
                self.file.write_bytes(payload)
                self.assertEqual(overlay.raw.read_stable(self.file, len(payload))[0], payload)
            with self.assertRaisesRegex(ValueError, 'file byte cap'): overlay.raw.read_stable(self.file, 2)

    def test_non_target_reads_writes_and_foreign_thread_delegate(self):
        results = []
        with self.configured() as (op, owner, module):
            def body():
                with self.file.open('rb') as stream: results.append(stream.read())
                (self.file.parent/'other.txt').write_text('other')
            thread = Thread(target=body); thread.start(); thread.join(5)
            self.assertFalse(thread.is_alive())
            self.assertEqual(results, [b'bounded fresh data'])
            self.assertEqual((self.file.parent/'other.txt').read_text(), 'other')
        self.assertIsNone(op.closed_receipt()['first_failure'])

    def test_prebind_and_postquiesce_target_calls_are_refused(self):
        for key in ('before_bind', 'after_quiesce'):
            with self.subTest(boundary=key), self.assertRaisesRegex(ValueError, 'bound untraced'):
                with self.configured(**{key: lambda: overlay.raw.read_stable(self.file, 100)}): pass
            self.assertIsNotNone(self.last.closed_receipt()['first_failure'])

    def test_same_code_wrong_globals_and_foreign_thread_poison(self):
        foreign = FunctionType(overlay.raw.read_stable.__code__, dict(vars(overlay.raw)))
        for mode in ('globals', 'thread'):
            errors = []
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                with self.configured():
                    if mode == 'globals':
                        with self.assertRaisesRegex(ValueError, 'foreign globals'): foreign(self.file, 100)
                    else:
                        def body():
                            try: overlay.raw.read_stable(self.file, 100)
                            except BaseException as error: errors.append(error)
                        thread = Thread(target=body); thread.start(); thread.join(5)
                        self.assertFalse(thread.is_alive()); self.assertEqual(len(errors), 1)
                    with self.assertRaisesRegex(ValueError, 'poisoned'): overlay.raw.read_stable(self.file, 100)

    def test_growth_shrink_and_replace_are_detected_by_original_bookends(self):
        original_fstat = overlay.raw.os.fstat
        for mutation in ('append', 'shrink', 'replace'):
            self.file.write_bytes(b'initial')
            calls = [0]
            def fstat(fd):
                value = original_fstat(fd); calls[0] += 1
                if calls[0] == 1:
                    if mutation == 'append':
                        with self.open(self.file, 'ab') as stream: stream.write(b'x')
                    elif mutation == 'shrink':
                        with self.open(self.file, 'wb') as stream: stream.write(b'i')
                    else:
                        replacement = self.file.with_name('replacement.bin')
                        replacement.write_bytes(b'changed')
                        try: replacement.replace(self.file)
                        except PermissionError:
                            # Windows sharing may itself prevent replacement.
                            with self.open(self.file, 'r+b') as stream: stream.write(b'changed')
                return value
            # Install the configured fstat before constructing the operation;
            # the original raw body still invokes it twice and its final path stat.
            with self.subTest(mutation=mutation), patch.object(overlay.raw.os, 'fstat', fstat):
                with self.assertRaisesRegex(ValueError, 'changed|exceeded'):
                    with self.configured(): overlay.raw.read_stable(self.file, 100)

    def test_primary_body_error_survives_cleanup_and_alias_restoration(self):
        primary = RuntimeError('primary diagnostic body')
        with self.assertRaises(RuntimeError) as caught:
            with self.configured(): raise primary
        self.assertIs(caught.exception, primary)
        receipt = self.last.closed_receipt()
        self.assertTrue(receipt['original_open_restored'])
        self.assertIsNotNone(receipt['first_failure'])

    def test_foreign_open_is_preserved_then_test_restores_its_fixture(self):
        foreign = lambda *a, **kw: self.open(*a, **kw)
        try:
            with self.assertRaises(ValueError):
                with self.configured(): Path.open = foreign
            self.assertIs(Path.open, foreign)
            self.assertFalse(self.last.closed_receipt()['original_open_restored'])
        finally: Path.open = self.open

    def test_late_install_is_refused(self):
        self.assertIn(overlay.BYTE_MODULE, sys.modules)
        op = overlay.operation()
        with self.assertRaisesRegex(ValueError, 'before loading'):
            with op.install(): self.fail('late installation must fail')

    def test_local_size_mapping_comparison_preserves_actual_values(self):
        count, cap = 128, 32*1024**2
        start = perf_counter()
        expected = [overlay.raw.read_stable(self.file, cap) for _ in range(count)]
        plain = perf_counter()-start
        start = perf_counter()
        with self.configured() as (op, owner, module):
            actual = [overlay.raw.read_stable(self.file, cap) for _ in range(count)]
        elapsed = perf_counter()-start
        self.assertEqual(actual, expected)
        UNIT_EVIDENCE['local_comparison'] = dict(calls=count, original_seconds=plain,
            overlay_with_import_bind_byte_entry_exit_seconds=elapsed, identical_bytes_and_stamps=True,
            receipt=op.closed_receipt(), whole_workflow_speedup_established=False)
