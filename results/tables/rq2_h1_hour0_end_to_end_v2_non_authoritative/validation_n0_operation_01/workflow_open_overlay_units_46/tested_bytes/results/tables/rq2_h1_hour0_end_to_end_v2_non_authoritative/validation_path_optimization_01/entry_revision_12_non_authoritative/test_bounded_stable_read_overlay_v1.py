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
from types import FunctionType, MappingProxyType
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
    def configured(self, *, open_function=None, close_function=None, before_bind=None, after_quiesce=None, before_byte_enter=None):
        from performance import code_read_lease as base
        previous = sys.modules.pop(overlay.BYTE_MODULE, None)
        context = patch.object(Path, 'open', open_function) if open_function is not None else nullcontext()
        kernel_context = patch.object(base._kernel, 'CloseHandle', close_function) if close_function is not None else nullcontext()
        try:
            with context, kernel_context:
                op = overlay.operation(root=REPO)
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
                    self.last_owner = owner
                    op.adopt(owner)
                    if before_byte_enter is not None: before_byte_enter(owner, module)
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
        self.assertTrue(receipt['canonical_IO_dependencies'])
        self.assertTrue(receipt['eligible_for_canonical_entry_clean'])
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
        op = overlay.operation(root=REPO)
        with self.assertRaisesRegex(ValueError, 'before loading'):
            with op.install(): self.fail('late installation must fail')

    def test_reentry_does_not_restore_or_quiesce_the_active_outer_owner(self):
        for mode in ('install', 'bind'):
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                with self.configured() as (op, owner, module):
                    hook, reader = Path.open, Path.read_bytes
                    with self.assertRaises((TypeError, ValueError)):
                        with (op.install() if mode == 'install' else op.bind(owner)): pass
                    self.assertIs(Path.open, hook)
                    self.assertIs(Path.read_bytes, reader)
                    with self.assertRaisesRegex(ValueError, 'poisoned'): overlay.raw.read_stable(self.file, 100)

    def test_open_enter_fileno_read_and_exit_faults_close_real_streams(self):
        for fault in ('open', 'enter', 'fileno1', 'read', 'fileno2', 'exit_before', 'exit_after', 'close'):
            opened = []
            class FaultStream:
                def __init__(this, stream): this.stream=stream;this.fds=0;this.closes=0;opened.append(this)
                @property
                def closed(this): return this.stream.closed
                def __enter__(this):
                    if fault=='enter': raise OSError('injected enter fault')
                    this.stream.__enter__(); return this
                def fileno(this):
                    this.fds+=1
                    if fault=='fileno'+str(this.fds): raise OSError('injected fileno fault')
                    return this.stream.fileno()
                def read(this,n):
                    if fault=='read': raise OSError('injected read fault')
                    return this.stream.read(n)
                def __exit__(this,*args):
                    if fault in ('exit_before','close'): raise OSError('injected exit fault')
                    result=this.stream.__exit__(*args)
                    if fault=='exit_after': raise OSError('injected exit after close')
                    return result
                def close(this):
                    this.closes+=1
                    if fault=='close': raise OSError('injected retained close fault')
                    return this.stream.close()
            def opening(path,*args,**kwargs):
                if path==self.file and args==('rb',):
                    if fault=='open': raise OSError('injected open fault')
                    return FaultStream(self.open(path,*args,**kwargs))
                return self.open(path,*args,**kwargs)
            try:
                with self.subTest(fault=fault), self.assertRaises(OSError):
                    with self.configured(open_function=opening): overlay.raw.read_stable(self.file,100)
                receipt=self.last.closed_receipt()
                self.assertTrue(receipt['original_open_restored'])
                self.assertIsNotNone(receipt['first_failure'])
                self.assertEqual(receipt['remaining_streams'],1 if fault=='close' else 0)
                if fault=='close': self.assertFalse(opened[0].closed)
                else: self.assertTrue(all(item.closed for item in opened))
            finally:
                for item in opened: item.stream.close()

    def test_second_fstat_fault_is_sticky_even_when_body_catches_it(self):
        original=overlay.raw.os.fstat;calls=[0]
        def fstat(fd):
            calls[0]+=1
            if calls[0]==2: raise OSError('second fstat fault')
            return original(fd)
        with patch.object(overlay.raw.os,'fstat',fstat), self.assertRaises(ValueError):
            with self.configured():
                with self.assertRaisesRegex(OSError,'second fstat'): overlay.raw.read_stable(self.file,100)
                with self.assertRaisesRegex(ValueError,'poisoned'): overlay.raw.read_stable(self.file,100)

    def test_byte_enter_and_exit_failures_restore_hooks_and_never_claim_clean(self):
        def fail_enter(owner,module):
            owner._expected=dict(owner._expected)
        with self.assertRaises(ValueError):
            with self.configured(before_byte_enter=fail_enter): pass
        self.assertTrue(self.last.closed_receipt()['original_open_restored'])
        self.assertIsNotNone(self.last.closed_receipt()['byte_owner_closed_receipt'])
        self.assertTrue(self.last_owner.closed_receipt()['all_handles_closed'])
        with self.assertRaises(ValueError):
            with self.configured() as (op,owner,module):
                overlay.raw.read_stable(self.file,100)
                module._RUNTIME=lambda: (_ for _ in ()).throw(ValueError('byte exit runtime fault'))
        self.assertTrue(op.closed_receipt()['original_open_restored'])
        self.assertIsNotNone(op.closed_receipt()['first_failure'])
        self.assertTrue(owner.closed_receipt()['all_handles_closed'])

    @staticmethod
    def local_values(op):
        pending=[op.adopt,op.bind,op.install,op.closed_receipt];seen=set();values=[]
        while pending:
            value=pending.pop()
            if id(value) in seen:continue
            seen.add(id(value));values.append(value)
            if type(value) is FunctionType:
                pending.extend(c.cell_contents for c in value.__closure__ or ())
                pending.append(getattr(value,'__wrapped__',None))
            elif type(value) is type:
                pending.extend(vars(value).values())
        return values

    def test_local_function_code_mutations_are_sticky_and_restore_real_hooks(self):
        for name in ('check','row_for','forget','drain','__enter__'):
            with self.subTest(function=name),self.assertRaises(ValueError):
                with self.configured() as (op,owner,module):
                    fn,=[v for v in self.local_values(op) if type(v) is FunctionType and v.__name__==name]
                    code=fn.__code__
                    try:
                        fn.__code__=code.replace(co_consts=code.co_consts+('injected code change',))
                        with self.assertRaisesRegex(ValueError,'closure changed'):overlay.raw.read_stable(self.file,100)
                    finally:fn.__code__=code
                    with self.assertRaisesRegex(ValueError,'poisoned'):overlay.raw.read_stable(self.file,100)
            self.assertTrue(op.closed_receipt()['original_open_restored'])
            self.assertEqual(op.closed_receipt()['remaining_streams'],0)

    def test_noop_checker_is_detected_and_caught_failure_remains_sticky(self):
        with self.assertRaises(ValueError):
            with self.configured() as (op,owner,module):
                fn,=[v for v in self.local_values(op) if type(v) is FunctionType and v.__name__=='check']
                original=fn.__code__
                names=original.co_freevars
                source='def factory():\n'+''.join('    '+name+'=None\n' for name in names)
                source+='    def noop(*args,**kwargs):\n        if False:\n            return ('+','.join(names)+',)\n        return None\n    return noop\n'
                namespace={};exec(source,namespace)
                noop=namespace['factory']().__code__
                self.assertEqual(noop.co_freevars,original.co_freevars)
                try:
                    fn.__code__=noop
                    with self.assertRaisesRegex(ValueError,'closure changed'):overlay.raw.read_stable(self.file,100)
                finally:fn.__code__=original
                with self.assertRaisesRegex(ValueError,'poisoned'):overlay.raw.read_stable(self.file,100)
        self.assertIsNotNone(op.closed_receipt()['first_failure'])
        self.assertFalse(op.closed_receipt()['eligible_for_canonical_entry_clean'])

    def test_byte_close_retry_runs_before_restore_after_body_or_partial_enter(self):
        from performance import code_read_lease as base
        actual=base._kernel.CloseHandle
        for partial_enter in (False,True):
            calls=[];first=[True]
            def close(handle):
                calls.append((handle,Path.open))
                if first[0]:first[0]=False;return 0
                return actual(handle)
            close.argtypes,close.restype=actual.argtypes,actual.restype
            def enter_fault(owner,module):
                def observation(*args):raise RuntimeError('partial byte enter fault')
                owner._observation=observation
            try:
                with self.subTest(partial_enter=partial_enter),self.assertRaises((OSError,RuntimeError)):
                    with self.configured(close_function=close,before_byte_enter=enter_fault if partial_enter else None) as (op,owner,module):
                        overlay.raw.read_stable(self.file,100)
                op=self.last;owner=self.last_owner
                receipt=op.closed_receipt()
                self.assertTrue(receipt['byte_cleanup_retry_attempted'])
                self.assertTrue(receipt['byte_owner_closed_receipt']['all_handles_closed'])
                self.assertTrue(receipt['original_open_restored'])
                self.assertTrue(receipt['byte_owner_closed_receipt']['cleanup_errors'])
                self.assertFalse(receipt['eligible_for_canonical_entry_clean'])
                self.assertGreaterEqual(sum(h==calls[0][0] for h,_ in calls),2)
                self.assertTrue(all(hook is not self.open for _,hook in calls))
                UNIT_EVIDENCE['byte_retry_partial_enter' if partial_enter else 'byte_retry_exit']=receipt
            finally:
                # Test cleanup is independent of the assertion and the injected API.
                if hasattr(self,'last_owner'):
                    for handle in self.last_owner._owned_state()[1]:actual(handle)

    def test_body_first_error_keeps_secondary_exit_and_cleanup_history(self):
        primary=RuntimeError('original read body fault');opened=[]
        class Stream:
            def __init__(this,stream):this.stream=stream;this.closes=0;opened.append(this)
            def __enter__(this):this.stream.__enter__();return this
            def fileno(this):return this.stream.fileno()
            def read(this,n):raise primary
            def __exit__(this,*args):raise OSError('secondary stream exit fault')
            def close(this):
                this.closes+=1
                if this.closes==1:raise OSError('secondary first cleanup fault')
                this.stream.close()
            @property
            def closed(this):return this.stream.closed
        def opening(path,*args,**kwargs):
            stream=self.open(path,*args,**kwargs)
            return Stream(stream) if path==self.file and args==('rb',) else stream
        try:
            with self.assertRaises(RuntimeError) as caught:
                with self.configured(open_function=opening):overlay.raw.read_stable(self.file,100)
            self.assertIs(caught.exception,primary)
            self.assertEqual(self.last.closed_receipt()['first_failure'],repr(primary))
            self.assertIn('secondary stream exit fault',' '.join(primary.__notes__))
            self.assertIn('secondary first cleanup fault',' '.join(primary.__notes__))
            self.assertTrue(all(item.closed for item in opened))
        finally:
            for item in opened:item.stream.close()

    def test_audit_controls_and_cleanup_recipes_are_immutable(self):
        with self.configured() as (op,owner,module):
            audit,=[v for v in self.local_values(op) if type(v) is MappingProxyType and 'verifier' in v]
            for name in ('records','verifier','drain_code','drain_values','drain_globals','make','cell'):
                with self.subTest(field=name),self.assertRaises(TypeError):audit[name]=None
            with self.assertRaises(TypeError):audit['drain_globals']['len']=lambda _:0
            overlay.raw.read_stable(self.file,100)
        self.assertTrue(op.closed_receipt()['eligible_for_canonical_entry_clean'])

    def test_raw_builtin_shadow_and_os_stat_rebinding_are_refused(self):
        original_stat=overlay.raw.os.stat
        for name in ('len','ValueError','os.stat'):
            with self.subTest(binding=name),self.assertRaises(ValueError):
                with self.configured() as (op,owner,module):
                    change=(patch.object(overlay.raw.os,'stat',lambda *a,**kw: original_stat(*a,**kw)) if name=='os.stat'
                            else patch.dict(vars(overlay.raw),{name:lambda *a:0}))
                    with change:
                        with self.assertRaises(ValueError):overlay.raw.read_stable(self.file,100)
            self.assertIsNotNone(op.closed_receipt()['first_failure'])

    def test_non_target_missing_and_permission_probes_do_not_poison(self):
        original=self.open
        def opening(path,*a,**kw):
            if path.name=='denied_probe':raise PermissionError('expected probe')
            return original(path,*a,**kw)
        for callback in (None,opening):
            with self.configured(open_function=callback) as (op,owner,module):
                with self.assertRaises(FileNotFoundError):(self.file.parent/'missing_probe').open('rb')
                if callback is not None:
                    with self.assertRaises(PermissionError):(self.file.parent/'denied_probe').open('rb')
                overlay.raw.read_stable(self.file,100)
            self.assertIsNone(op.closed_receipt()['first_failure'])
            self.assertEqual(op.closed_receipt()['canonical_IO_dependencies'],callback is None)

    def test_inapplicable_cap_types_keep_original_fallback_values_and_errors(self):
        class IntSubclass(int):pass
        def result(cap):
            try:return ('value',overlay.raw.read_stable(self.file,cap))
            except BaseException as error:return ('error',type(error).__name__,str(error))
        self.file.write_bytes(b'x')
        caps=(True,False,IntSubclass(100),100.5,2**100)
        baseline=[result(cap) for cap in caps]
        with self.configured() as (op,owner,module):actual=[result(cap) for cap in caps]
        self.assertEqual(actual,baseline)
        self.assertEqual(op.closed_receipt()['raw_fallback_opens'],4)
        self.assertIsNone(op.closed_receipt()['first_failure'])

    def test_foreign_exact_byte_raw_copy_is_rejected_before_import_binding(self):
        original=overlay.raw
        copied=Path(self.temporary.name)/'raw_copy.py';copied.write_bytes(Path(original.__file__).read_bytes())
        raw_spec=importlib.util.spec_from_file_location(original.__name__,copied)
        foreign=importlib.util.module_from_spec(raw_spec);raw_spec.loader.exec_module(foreign)
        helper_name='performance.overlay_foreign_provenance_test'
        helper_spec=importlib.util.spec_from_file_location(helper_name,overlay.__file__)
        helper=importlib.util.module_from_spec(helper_spec)
        try:
            with patch.dict(sys.modules,{original.__name__:foreign,helper_name:helper}),patch.object(sys.modules['experiments'],'h1_raw_ingress_development_v1',foreign):
                helper_spec.loader.exec_module(helper)
                with self.assertRaisesRegex(ValueError,'canonical raw module'):helper.operation(root=REPO)
        finally:sys.modules.pop(helper_name,None)

    def test_registration_failure_retains_then_closes_the_unregistered_stream(self):
        opened=[]
        class Stream:
            def __init__(this,stream):this.stream=stream;this.lookups=0;opened.append(this)
            @property
            def close(this):
                this.lookups+=1
                if this.lookups<=2:raise OSError('registration close lookup fault')
                return this.stream.close
            @property
            def closed(this):return this.stream.closed
        def opening(path,*a,**kw):
            stream=self.open(path,*a,**kw)
            return Stream(stream) if path==self.file and a==('rb',) else stream
        try:
            with self.assertRaisesRegex(OSError,'registration close lookup'):
                with self.configured(open_function=opening):overlay.raw.read_stable(self.file,100)
            self.assertTrue(opened[0].closed)
            self.assertEqual(self.last.closed_receipt()['remaining_streams'],0)
        finally:
            for item in opened:item.stream.close()

    def test_normal_exit_without_closing_is_refused_at_the_call_boundary(self):
        opened=[]
        class Stream:
            def __init__(this,stream):this.stream=stream;opened.append(this)
            def __enter__(this):this.stream.__enter__();return this
            def fileno(this):return this.stream.fileno()
            def read(this,n):return this.stream.read(n)
            def __exit__(this,*args):return False
            def close(this):return this.stream.close()
            @property
            def closed(this):return this.stream.closed
        def opening(path,*a,**kw):
            stream=self.open(path,*a,**kw)
            return Stream(stream) if path==self.file and a==('rb',) else stream
        try:
            with self.assertRaisesRegex(ValueError,'did not close'):
                with self.configured(open_function=opening):overlay.raw.read_stable(self.file,100)
            self.assertTrue(all(item.closed for item in opened))
        finally:
            for item in opened:item.stream.close()

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
            overlay_with_static_reload_bind_byte_entry_exit_seconds=elapsed,
            excludes_first_overlay_and_raw_import=True, identical_bytes_and_stamps=True,
            receipt=op.closed_receipt(), whole_workflow_speedup_established=False)
