"""Ordinary pinned-metadata path and fault tests; no project/model imports."""
from contextlib import contextmanager
from hashlib import sha256
import importlib.metadata as metadata
import json
from pathlib import Path
import sys
import tempfile
from time import perf_counter
import unittest
from unittest.mock import patch

from performance.metadata_parse_lease import MetadataParseLease
from performance import pinned_distribution_resolver_v1 as resolver


UNIT_EVIDENCE = {}


def expected():
    return json.loads(Path(__file__).with_name('metadata_allowlist_v1.json').read_bytes())['files_sha256']


class ResolverTests(unittest.TestCase):
    def setUp(self):
        self.descriptor = vars(metadata.Distribution)['from_name']
        self.version = metadata.Distribution.version

    def tearDown(self):
        self.assertIs(vars(metadata.Distribution)['from_name'], self.descriptor)
        self.assertIs(metadata.Distribution.version, self.version)

    @contextmanager
    def owned(self):
        owner = MetadataParseLease(expected())
        with owner:
            yield owner
        self.assertEqual(owner._handles, [])

    def test_genuine_versions_fresh_instances_and_original_discovery_counts(self):
        plain = {n: metadata.version(n) for n in resolver.NAMES}
        code = self.descriptor.__func__.__code__
        calls = [0]
        def count(frame, event, arg):
            if event == 'call' and frame.f_code is code: calls[0] += 1
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            previous = sys.getprofile()
            try:
                sys.setprofile(count)
                with scope:
                    versions = {n: metadata.version(n) for n in resolver.NAMES}
                    first = metadata.distribution('numpy')
                    second = metadata.distribution('numpy')
                    self.assertIsNot(first, second)
                    self.assertIsNot(first._path, second._path)
                    first._path = Path('D:/foreign_mutable_distribution')
                    self.assertEqual(metadata.version('numpy'), plain['numpy'])
            finally: sys.setprofile(previous)
        self.assertEqual(versions, plain)
        self.assertEqual(calls[0], 16)
        receipt = reader()
        self.assertEqual(receipt['fast_path_calls'], 11)
        self.assertEqual(receipt['fresh_PathDistribution_instances'], 11)
        self.assertEqual(receipt['original_discovery_oracles'], dict(entry=1, exit=1))
        self.assertFalse(receipt['outer_MetadataParseLease_cleanup_proven'])
        self.assertFalse(receipt['owns_OS_handles'])
        self.assertIsNone(receipt['first_failure'])
        self.assertEqual({n: metadata.version(n) for n in resolver.NAMES}, plain)
        UNIT_EVIDENCE['genuine'] = dict(plain_versions=plain, held_versions=versions,
            original_from_name_profile_calls=calls[0], receipt=receipt, formal_result=False)

    def test_unknown_alias_subclass_and_invalid_name_use_native_fallback(self):
        class Subclass(metadata.PathDistribution): pass
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                self.assertEqual(metadata.version('pyomo'), metadata.version('Pyomo'))
                self.assertEqual(Subclass.from_name('numpy').version, metadata.version('numpy'))
                with self.assertRaises(metadata.PackageNotFoundError):
                    metadata.version('h1_unlisted_nonexistent_package_81273')
                with self.assertRaises(ValueError): metadata.version(None)
        receipt = reader()
        self.assertEqual(receipt['fallback_calls'], 4)
        self.assertIsNone(receipt['first_failure'])

    def test_sys_path_and_meta_path_changes_fall_back(self):
        class Finder:
            def find_spec(self, *args, **kwargs): return None
            def find_distributions(self, context): return ()
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                with tempfile.TemporaryDirectory(prefix='h1meta_', dir='D:/') as directory:
                    with patch.object(sys, 'path', [directory, *sys.path]): metadata.version('numpy')
                with patch.object(sys, 'meta_path', [Finder(), *sys.meta_path]): metadata.version('numpy')
        self.assertEqual(reader()['fallback_calls'], 2)
        self.assertIsNone(reader()['first_failure'])

    def test_changed_finder_descriptor_uses_original_discovery(self):
        original = vars(metadata.MetadataPathFinder)['find_distributions']
        def changed(cls, context=metadata.DistributionFinder.Context()):
            return original.__get__(None, cls)(context)
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                with patch.object(metadata.MetadataPathFinder, 'find_distributions', classmethod(changed)):
                    metadata.version('numpy')
        self.assertEqual(reader()['fallback_calls'], 1)
        self.assertIsNone(reader()['first_failure'])

    def test_import_only_finder_has_no_distribution_discovery_effect(self):
        class Finder:
            def find_spec(self, *args, **kwargs): return None
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                with patch.object(sys, 'meta_path', [Finder(), *sys.meta_path]): metadata.version('numpy')
        self.assertEqual(reader()['fast_path_calls'], 1)
        self.assertEqual(reader()['fallback_calls'], 0)

    def test_discovery_closure_changes_call_original_without_fast_reuse(self):
        context = metadata.DistributionFinder.Context
        old_search = metadata.Lookup.search
        old_bool = metadata.Prepared.__bool__
        old_init = context.__init__
        old_stat, old_listdir, old_sub = metadata.os.stat, metadata.os.listdir, metadata.re.sub
        old_basename = metadata.os.path.basename
        class PreparedAlias(metadata.Prepared): pass
        class FinderAlias:
            Context = context
        cases = (
            ('Prepared alias', metadata, 'Prepared', PreparedAlias),
            ('DistributionFinder alias', metadata, 'DistributionFinder', FinderAlias),
            ('Context.path', context, 'path', property(lambda self: vars(self).get('path', sys.path))),
            ('Context.__init__', context, '__init__', lambda self, **kw: old_init(self, **kw)),
            ('Lookup.search', metadata.Lookup, 'search', lambda self, p: old_search(self, p)),
            ('Prepared.__bool__', metadata.Prepared, '__bool__', lambda self: old_bool(self)),
            ('os.stat', metadata.os, 'stat', lambda *a, **kw: old_stat(*a, **kw)),
            ('os.listdir', metadata.os, 'listdir', lambda *a, **kw: old_listdir(*a, **kw)),
            ('os.path.basename', metadata.os.path, 'basename', lambda *a: old_basename(*a)),
            ('re.sub', metadata.re, 'sub', lambda *a, **kw: old_sub(*a, **kw)),
        )
        checked = []
        for label, obj, name, replacement in cases:
            with self.subTest(dependency=label), self.owned() as owner:
                scope, reader = resolver.operation(owner, expected())
                profile_calls = [0]
                code = self.descriptor.__func__.__code__
                def count(frame, event, arg):
                    if event == 'call' and frame.f_code is code: profile_calls[0] += 1
                with scope:
                    previous = sys.getprofile()
                    try:
                        sys.setprofile(count)
                        with patch.object(obj, name, replacement):
                            self.assertEqual(metadata.version('numpy'), '1.26.4')
                    finally: sys.setprofile(previous)
                receipt = reader()
                self.assertEqual(profile_calls[0], 1)
                self.assertEqual(receipt['fast_path_calls'], 0)
                self.assertEqual(receipt['fallback_calls'], 1)
                self.assertIsNone(receipt['first_failure'])
                checked.append(label)
        UNIT_EVIDENCE['discovery_closure_fallback_negatives'] = checked

    def test_builtin_global_shadow_disables_discovery_reuse(self):
        self.assertNotIn('bool', vars(metadata))
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                with patch.dict(vars(metadata), {'bool': lambda value: bool(value)}):
                    self.assertEqual(metadata.version('numpy'), '1.26.4')
        self.assertEqual(reader()['fast_path_calls'], 0)
        self.assertEqual(reader()['fallback_calls'], 1)

    def test_original_resolver_code_or_globals_change_poison_even_after_restore(self):
        original = self.descriptor.__func__
        def changed(cls, name): return None
        @contextmanager
        def mutate_function(name, value):
            # mock.patch tries delattr for function slots that are absent from
            # __dict__; __code__ cannot be deleted. Restore the actual slot.
            before = getattr(original, name)
            try:
                setattr(original, name, value)
                yield
            finally: setattr(original, name, before)
        for mode in ('code', 'defaults', 'globals'):
            with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'poisoned'):
                with self.owned() as owner:
                    scope, reader = resolver.operation(owner, expected())
                    with scope:
                        if mode == 'code':
                            mutation = mutate_function('__code__', changed.__code__)
                        elif mode == 'defaults':
                            mutation = mutate_function('__defaults__', ('numpy',))
                        else:
                            mutation = patch.object(metadata, 'PackageNotFoundError', RuntimeError)
                        with mutation:
                            with self.assertRaisesRegex(ValueError, 'original metadata resolver changed'):
                                metadata.version('numpy')
                        with self.assertRaisesRegex(ValueError, 'poisoned'): metadata.version('numpy')
            receipt = reader()
            self.assertEqual(receipt['fast_path_calls'], 0)
            self.assertIn('original metadata resolver changed', receipt['first_failure'])
            self.assertTrue(receipt['original_alias_restored'])

    def test_extra_parser_inventory_keys_poison(self):
        for name in ('_raw', '_values'):
            with self.subTest(name=name), self.assertRaisesRegex(ValueError, 'poisoned'):
                with self.owned() as owner:
                    scope, reader = resolver.operation(owner, expected())
                    with scope:
                        values = getattr(owner, name)
                        values['unheld_metadata_key'] = b'extra' if name == '_raw' else '99.0'
                        try:
                            with self.assertRaisesRegex(ValueError, 'ownership changed'): metadata.version('numpy')
                        finally: del values['unheld_metadata_key']
                        with self.assertRaisesRegex(ValueError, 'poisoned'): metadata.version('numpy')
            self.assertIsNotNone(reader()['first_failure'])

    def test_parser_inventory_and_cached_version_faults_are_sticky(self):
        for name in ('_raw', '_files', '_identities', '_handles', '_values'):
            with self.subTest(name=name), self.assertRaises(ValueError):
                with self.owned() as owner:
                    scope, reader = resolver.operation(owner, expected())
                    with scope:
                        if name == '_values':
                            before = dict(owner._values)
                            key = next(iter(owner._values))
                            owner._values[key] = 'forged-version'
                            try:
                                with self.assertRaises(ValueError): metadata.version('numpy')
                            finally: owner._values.clear(); owner._values.update(before)
                        else:
                            before = getattr(owner, name)
                            setattr(owner, name, {} if name != '_handles' else [])
                            try:
                                with self.assertRaises(ValueError): metadata.version('numpy')
                            finally: setattr(owner, name, before)
                        with self.assertRaisesRegex(ValueError, 'poisoned'): metadata.version('numpy')
            self.assertIsNotNone(reader()['first_failure'])

    def test_path_distribution_constructor_change_is_refused(self):
        with self.assertRaises(ValueError):
            with self.owned() as owner:
                scope, reader = resolver.operation(owner, expected())
                with scope:
                    with patch.object(metadata.PathDistribution, '__init__', lambda self, p: None):
                        with self.assertRaises(ValueError): metadata.version('numpy')
        self.assertIsNotNone(reader()['first_failure'])

    def test_entry_discovery_failure_rolls_back_and_clears(self):
        def fail(cls, **kwargs): raise RuntimeError('entry discovery failure')
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with patch.object(metadata.Distribution, 'discover', classmethod(fail)):
                with self.assertRaisesRegex(RuntimeError, 'entry discovery failure'):
                    with scope: self.fail('entry must reject')
        receipt = reader()
        self.assertTrue(receipt['original_alias_restored'])
        self.assertTrue(receipt['all_resolver_cached_paths_cleared'])
        self.assertIn('entry discovery failure', receipt['first_failure'])

    def test_exit_discovery_failure_records_cleanup_first_error(self):
        def fail(cls, **kwargs): raise RuntimeError('exit discovery failure')
        patcher = None
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            try:
                with self.assertRaisesRegex(RuntimeError, 'exit discovery failure'):
                    with scope:
                        metadata.version('numpy')
                        patcher = patch.object(metadata.Distribution, 'discover', classmethod(fail))
                        patcher.start()
            finally:
                if patcher is not None: patcher.stop()
        self.assertIn('exit discovery failure', reader()['first_failure'])
        self.assertTrue(reader()['cleanup_errors'])

    def test_half_install_failure_uses_independent_descriptor_restore(self):
        fault = [True]
        def trace(frame, event, arg):
            state = frame.f_locals.get('status') if event == 'line' else None
            if (frame.f_code.co_filename == resolver.__file__ and frame.f_code.co_name == 'scope' and
                    state is not None and state['phase'] == 'active' and fault[0] and
                    vars(metadata.Distribution)['from_name'] is state['descriptor']):
                fault[0] = False
                raise RuntimeError('after descriptor install')
            return trace
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            previous = sys.gettrace()
            try:
                sys.settrace(trace)
                with self.assertRaisesRegex(RuntimeError, 'after descriptor install'):
                    with scope: self.fail('half install must reject')
            finally: sys.settrace(previous)
        self.assertTrue(reader()['original_alias_restored'])
        self.assertIn('after descriptor install', reader()['first_failure'])

    def test_restore_window_failure_records_error_and_preserves_primary(self):
        lines = Path(resolver.__file__).read_text().splitlines()
        target, = [i+1 for i, text in enumerate(lines) if "type.__setattr__(cls, 'from_name', original)" in text]
        fault = [True]
        def trace(frame, event, arg):
            if (event == 'line' and frame.f_code.co_filename == resolver.__file__ and
                    frame.f_code.co_name == 'scope' and frame.f_lineno == target and fault[0]):
                fault[0] = False
                raise RuntimeError('restore window fault')
            return trace
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            previous = sys.gettrace()
            try:
                sys.settrace(trace)
                with self.assertRaisesRegex(RuntimeError, 'restore window fault'):
                    with scope: metadata.version('numpy')
            finally:
                sys.settrace(previous)
                type.__setattr__(metadata.Distribution, 'from_name', self.descriptor)
        self.assertFalse(reader()['original_alias_restored'])
        self.assertIn('restore window fault', reader()['first_failure'])

    def test_foreign_descriptor_is_preserved_and_primary_body_error_kept(self):
        foreign = classmethod(lambda cls, name: None)
        primary = RuntimeError('primary body')
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            try:
                with self.assertRaises(RuntimeError) as caught:
                    with scope:
                        type.__setattr__(metadata.Distribution, 'from_name', foreign)
                        raise primary
                self.assertIs(caught.exception, primary)
                self.assertIs(vars(metadata.Distribution)['from_name'], foreign)
            finally: type.__setattr__(metadata.Distribution, 'from_name', self.descriptor)
        self.assertFalse(reader()['original_alias_restored'])
        self.assertTrue(reader()['all_resolver_cached_paths_cleared'])

    def test_duplicate_distribution_appearing_in_existing_path_fails_exit(self):
        with tempfile.TemporaryDirectory(prefix='h1duplicate_', dir='D:/') as directory:
            with patch.object(sys, 'path', [directory, *sys.path]):
                with self.owned() as owner:
                    scope, reader = resolver.operation(owner, expected())
                    with self.assertRaisesRegex(ValueError, 'unique canonical'):
                        with scope:
                            metadata.version('numpy')
                            added = Path(directory)/'numpy-99.0.dist-info'
                            added.mkdir()
                            (added/'METADATA').write_text('Name: numpy\nVersion: 99.0\n', encoding='utf-8')
        self.assertTrue(reader()['cleanup_errors'])
        self.assertFalse(reader()['transient_discovery_ABA_covered'])

    def test_unchanged_owner_window_reset_preserves_fast_path(self):
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                metadata.version('numpy')
                owner.begin_discovery_window()
                metadata.version('numpy')
        self.assertEqual(reader()['fast_path_calls'], 2)

    def test_stale_route_closed_receipt_is_detached_and_wrong_owner_refused(self):
        with self.assertRaises(TypeError): resolver.operation(object(), expected())
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope:
                route = metadata.Distribution.from_name
                metadata.version('numpy')
                with self.assertRaises(ValueError): resolver.operation(owner, expected())
            before = reader()
            with self.assertRaises(ValueError): route('numpy')
            self.assertEqual(reader(), before)
            before['selected'].clear()
            self.assertTrue(reader()['selected'])

    def test_outer_parse_close_fault_is_not_resolver_cleanup_authority(self):
        original_release = MetadataParseLease._release
        def release_then_fail(owner):
            original_release(owner)
            raise OSError('outer metadata close fault')
        owner = MetadataParseLease(expected())
        with self.assertRaisesRegex(OSError, 'outer metadata close fault'):
            with patch.object(MetadataParseLease, '_release', release_then_fail):
                with owner:
                    scope, reader = resolver.operation(owner, expected())
                    with scope: metadata.version('numpy')
        self.assertFalse(reader()['outer_MetadataParseLease_cleanup_proven'])
        self.assertEqual(owner._handles, [])

    def test_local_discovery_comparison_uses_same_parse_lease_and_versions(self):
        count = 2000
        names = [resolver.NAMES[i % len(resolver.NAMES)] for i in range(count)]
        with self.owned() as owner:
            start = perf_counter()
            baseline = [metadata.version(n) for n in names]
            plain_seconds = perf_counter()-start
        start = perf_counter()
        with self.owned() as owner:
            scope, reader = resolver.operation(owner, expected())
            with scope: actual = [metadata.version(n) for n in names]
        successor_seconds = perf_counter()-start
        self.assertEqual(actual, baseline)
        receipt = reader()
        self.assertEqual(receipt['fast_path_calls'], count)
        UNIT_EVIDENCE['microbenchmark'] = dict(calls=count, parse_lease_with_original_discovery_seconds=plain_seconds,
            pinned_discovery_with_entry_exit_and_outer_lease_seconds=successor_seconds,
            includes_all_successor_boundaries=True, identical_version_values=True,
            scope='local metadata path only; whole-workflow speedup unproved', formal_result=False)
