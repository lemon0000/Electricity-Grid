"""Finite protocol scaffold plus native-audit logical guard; no scientific import."""
import ast
import copy
import dis
import importlib.util
import json
from pathlib import Path
from types import FunctionType,MethodType
import unittest
ROOT = Path(__file__).absolute().parents[1]
NEW = ROOT / 'experiments/staged_rts24_saved_fresh_bootstrap_import_census1024_none_v2.py'

def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module
base = load(ROOT / 'tests/test_staged_rts24_saved_fresh_census256_v1.py', '_parts512_base')
core = load(ROOT / 'experiments/staged_rts24_saved_fresh_pre_entry_lease_v29.py', '_parts512_core')
parent = load(ROOT / 'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v26.py', '_parts512_parent')
fixture = base.fixture
fixture.BS = NEW
fixture.PROBE = ROOT / 'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v27.py'
fixture.core = core

native=load(ROOT/'tests/staged_rts24_saved_fresh_image_entry_fixture_v2.py','_none1024_native_tests')
_plain_guard_for=fixture.guard_for

def census_guard_for(module):
    guard,runtime,trace,primary=_plain_guard_for(module)
    old=ast.parse((ROOT/'experiments/staged_rts24_saved_fresh_bootstrap_import_census512_parts_v1.py').read_bytes())
    cls=next(n for n in old.body if type(n) is ast.ClassDef and n.name=='BootstrapImportBoundary')
    nodes=[copy.deepcopy(n) for n in cls.body if type(n) is ast.FunctionDef and n.name in ('_audit','_audit_entry')]
    context=dict(vars(module))
    exec(compile(ast.Module(body=nodes,type_ignores=[]),'<synthetic_census_audit_scaffold>','exec',dont_inherit=True,optimize=0),context)
    guard._audit_entry=MethodType(context['_audit_entry'],guard)
    assert len(module.sys.hooks)==1
    module.sys.hooks[0]=lambda event,args:context['_audit'](guard,event,args,object(),())
    return guard,runtime,trace,primary

fixture.guard_for=census_guard_for

def run_window(count=1024, stage=0):
    module, sink = fixture.helper()
    guard, runtime, trace, primary = fixture.guard_for(module)
    physical = [0]

    def importer(name):
        for _ in range(count):
            module.sys.audit('open', 'D:/allowed', 'r', 0)
            physical[0] += 1
        guard._observed_stage = stage
        return object()
    try:
        module.diagnostic_import_once(runtime, _importer=importer)
    except module.AuditCensusStop as error:
        message = str(error)
    else:
        raise AssertionError('diagnostic stop absent')
    return (module, wire(sink.getvalue()), message, physical[0])

def wire(raw):
    rows = [json.loads(line) for line in raw.splitlines()]
    for row in rows:
        if row[0] == 'census':
            row[1]['start_clock'] += 10.0
            row[1]['snapshot_clock'] += 10.0
        else:
            row[-1] += 10.0
    rows = [['enter', 9.0], ['exit', 9.1], ['stage', 'loader_ready', 9.2], *rows]
    return b''.join((parent.canonical(row) + b'\n' for row in rows))

def compare_record(value, raw):
    argv = ['synthetic-finite-observation']
    kernel = value['kernel_identity']
    kernel['command_line_sha'] = parent.pin(parent.subprocess.list2cmdline(argv).encode('utf-8'))
    identity = dict(pid=kernel['pid'], creation=kernel['process_creation_filetime'])
    return parent.compare_child('import_discovery', b'', parent.canonical(value) + b'\n', raw, 1, identity, argv, [])

def record(reason='prefix_complete', stage=0):
    value = base.good_record()
    message = 'diagnostic_prefix_complete_1024' if reason == 'prefix_complete' else 'diagnostic_import_return_before1024'

    def change(x):
        if type(x) is str:
            return message if x == 'diagnostic_prefix_complete_256' else x
        if type(x) is list:
            return [change(v) for v in x]
        if type(x) is dict:
            return {k: change(v) for k, v in x.items()}
        return x
    value = change(value)
    value['boundary_report'].update(machinery_observed_stage=stage, machinery_authentication_pending=bool(stage), internal_introspection_events=stage * 3)
    return value

class None1024Tests(native.NativeImageTests, unittest.TestCase):

    def test_01_exact_source_constructor_and_original_audit_statements(self):
        transform = load(ROOT / 'experiments/staged_rts24_saved_fresh_none1024_transform_v1.py', '_none1024_test_constructor')
        source = ROOT / 'experiments/staged_rts24_saved_fresh_bootstrap_import_image_none_v1.py'
        compact=load(ROOT/'experiments/staged_rts24_saved_fresh_prefix_indent_transform_v1.py','_compact_test_constructor')
        self.assertEqual(compact.helper(transform.helper(source.read_text(encoding='utf-8')).decode('utf-8')),NEW.read_bytes())
        self.assertEqual(compact.probe(transform.probe((ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v25.py').read_text(encoding='utf-8')).decode('utf-8')),(ROOT/'tests/staged_rts24_saved_fresh_runtime_handoff_probe_v27.py').read_bytes())
        self.assertEqual(compact.parent(transform.parent((ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v24.py').read_text(encoding='utf-8')).decode('utf-8')),(ROOT/'experiments/staged_rts24_saved_fresh_runtime_handoff_parent_v26.py').read_bytes())
        sample=b'if True:\n    value=1\n    value+=2\n    if value:\n        value+=3\n'
        packed=parent.minify_prefix(sample)
        self.assertLess(len(packed),len(sample))
        self.assertEqual(compact.code_image(compile(sample,'<pre_entry_prefix>','exec',dont_inherit=True,optimize=0)),compact.code_image(compile(packed,'<pre_entry_prefix>','exec',dont_inherit=True,optimize=0)))
        self.assertNotEqual(compact.code_image(compile(b'value=1','<pre_entry_prefix>','exec')),compact.code_image(compile(b'value=2','<pre_entry_prefix>','exec')))
        for invalid in (b'if True:\n value=1\n',b"value='''a\n    b\n'''\n"):
            with self.assertRaises(AssertionError):parent.minify_prefix(invalid)
        a = ast.parse(source.read_bytes())
        b = ast.parse(NEW.read_bytes())
        ca = next((n for n in a.body if type(n) is ast.ClassDef and n.name == 'BootstrapImportBoundary'))
        cb = next((n for n in b.body if type(n) is ast.ClassDef and n.name == 'BootstrapImportBoundary'))

        class Dynamic(ast.NodeTransformer):

            def visit_Call(self, n):
                held={'_image_fn':'_image','_observe_fn':'_observe_machinery','_entry_fn':'_audit_entry'}
                if type(n.func) is ast.Name and n.func.id in held:
                    self_count = len(n.args)
                    assert self_count == 1 and n.args[0].id == 'self'
                    n.func = ast.Attribute(value=ast.Name(id='self', ctx=ast.Load()), attr=held[n.func.id], ctx=ast.Load())
                    n.args = []
                return self.generic_visit(n)
        for old, new in zip(ca.body, cb.body):
            if type(old) is ast.FunctionDef and old.name in ('_audit', '_audit_entry', '_observe_machinery'):
                count = {'_audit':5,'_audit_entry':2,'_observe_machinery':1}[old.name]
                del new.args.args[-count:]
                del new.args.defaults[-count:]
                if old.name == '_audit':
                    outer = next((n for n in new.body if type(n) is ast.Try))
                    lock = next((n for n in outer.body if type(n) is ast.With))
                    checks = [n for n in lock.body if type(n) is ast.If and any((type(v) is ast.Constant and v.value == 'image_metadata' for v in ast.walk(n)))]
                    self.assertEqual(len(checks), 1)
                    lock.body.remove(checks[0])
                Dynamic().visit(new)
                self.assertEqual(ast.dump(old), ast.dump(new))
        for name in transform.CENSUS:
            left = next((n for n in a.body if type(n) is ast.FunctionDef and n.name == name))
            right = next((n for n in b.body if type(n) is ast.FunctionDef and n.name == name))
            left.body = right.body = [ast.Pass()]
        self.assertEqual(ast.dump(a), ast.dump(b))

    def test_02_held_defaults_metadata_and_zero_global_census(self):
        module, sink = fixture.helper()
        self.assertTrue(fixture.proof_for(module, core))
        for name, fn in vars(module).items():
            if name.startswith('_census_') and type(fn) is FunctionType:
                self.assertFalse([op for op in dis.get_instructions(fn) if op.opname == 'LOAD_GLOBAL'], name)
        old = module._census_observer.__defaults__
        changed = list(old)
        changed[1] = (lambda: 0.0, *old[1][1:])
        module._census_observer.__defaults__ = tuple(changed)
        with self.assertRaises(ValueError):
            fixture.proof_for(module, core)

    def test_03_exact1024_and1023_physical(self):
        module, raw, message, physical = run_window()
        parsed = parent.validate_prefix_observation(record(), raw)
        self.assertEqual(message, 'diagnostic_prefix_complete_1024')
        self.assertEqual(physical, 1023)
        self.assertEqual([x['passed'] for x in parsed['census_frames']], [0, 1, 128, 256, 384, 512, 640, 768, 896, 1024])
        self.assertEqual(module._CENSUS['observed'], 1024)
        self.assertFalse(module._CENSUS['active'])
        self.assertFalse(module._CENSUS['inflight'])

    def test_04_natural_return_boundaries_and_phase_refresh(self):
        for count in (0, 1, 127, 128, 512, 1023):
            for stage in (0, 2):
                module, raw, message, physical = run_window(count, stage)
                parsed = parent.validate_prefix_observation(record('import_return_before1024', stage), raw)
                self.assertEqual(message, 'diagnostic_import_return_before1024')
                self.assertEqual(physical, count)
                self.assertEqual(parsed['census_frames'][-1]['passed'], count)
                self.assertEqual(parsed['census_frames'][-1]['machinery_stage'], stage)
                self.assertEqual([r[1] for r in parsed['stages']], ['loader_ready', 'before_adapter_import', 'adapter_import_returned', 'after_adapter_import_attempt'])

    def test_05_clock_io_and_primary_cause(self):
        fixture.CensusTests.test_04_clock_io_failure_preserves_guard_primary(self)
        module, sink = fixture.helper()
        guard, runtime, trace, unused = fixture.guard_for(module)
        primary = LookupError('import primary')
        cause = OSError('prior cause')
        primary.__cause__ = cause

        def importer(name):
            raise primary
        with self.assertRaises(LookupError) as caught:
            module.diagnostic_import_once(runtime, _importer=importer)
        self.assertIs(caught.exception, primary)
        self.assertIs(primary.__cause__, cause)
        parsed = parent.parse_diagnostic_stderr(sink.getvalue())
        self.assertEqual(parsed['census_frames'][-1]['reason'], 'import_error_before1024')

    def test_06_strict_schema_schedule_clock_cache_and_phase(self):
        module, raw, message, physical = run_window()
        rows = [json.loads(line) for line in raw.splitlines()]
        for kind in ('bucket', 'start', 'cache', 'schema', 'limit', 'phase_backwards', 'tail', 'missing_graph', 'missing_progress'):
            changed = copy.deepcopy(rows)
            frames = [r[1] for r in changed if r[0] == 'census']
            if kind == 'bucket':
                frames[-1]['buckets']['cache'][0] = 1023
            elif kind == 'start':
                frames[-1]['start_clock'] += 0.001
            elif kind == 'cache':
                frames[-1]['cache_new'] += 1
            elif kind == 'schema':
                frames[-1]['schema'] = 'staged_saved_F_audit_census_v2'
            elif kind == 'limit':
                frames[-1]['limit'] = 1024.0
            elif kind == 'phase_backwards':
                frames[-2]['machinery_stage'] = 2
            elif kind == 'missing_graph':
                changed = [r for r in changed if r[0] not in ('enter', 'exit')]
            elif kind == 'missing_progress':
                changed = [r for r in changed if not (r[0] == 'census' and r[1]['passed'] == 512)]
            bad = b''.join((parent.canonical(r) + b'\n' for r in changed)) + (b'["census",' if kind == 'tail' else b'')
            with self.assertRaises(AssertionError):
                parent.validate_prefix_stderr(bad)

    def test_07_both_modes_record_authority_and_parent_completion(self):
        for reason in ('prefix_complete', 'import_return_before1024'):
            self.assertTrue(parent.validate_prefix_record(record(reason), reason))
            stage = 1 if reason == 'import_return_before1024' else 0
            module, raw, unused, physical = run_window(128 if stage else 1024, stage)
            observed = compare_record(record(reason, stage), raw)
            self.assertTrue(observed['finite_terminal_complete'])
            self.assertTrue(parent.prefix_terminal_complete(observed, None))
            self.assertIs(observed['prefix_complete'], reason == 'prefix_complete')
            self.assertIs(observed['adapter_import_return_observed'], reason == 'import_return_before1024')
            driver=load(ROOT/'results/tables/staged_rts24_saved_fresh_nfc_v2_non_authoritative/driver.py','_none1024_matrix_test')
            receipt=json.loads((ROOT/'results/tables/staged_rts24_saved_fresh_aoc_v5_non_authoritative/probe_import_discovery.receipt.json').read_bytes())
            receipt.update(result=observed,stdout_raw_base64=parent.base64.b64encode(parent.canonical(observed['child_record'])+b'\n').decode('ascii'),stderr_raw_base64=parent.base64.b64encode(raw).decode('ascii'))
            self.assertTrue(driver.audit_matrix(parent,receipt)['accepted'])
            result = dict(finite_terminal_complete=True, prefix_complete=reason == 'prefix_complete', self_close_witness_present=True, child_record=record(reason))
            self.assertTrue(parent.prefix_terminal_complete(result, None))
            self.assertFalse(parent.prefix_terminal_complete(result, 'timeout'))
            for field, value in (('actual_F', True), ('F_completed', True), ('runtime_phase', 'LIVE')):
                changed = record(reason)
                changed[field] = value
                with self.assertRaises(AssertionError):
                    parent.validate_prefix_record(changed, reason)
        self.assertFalse(parent.prefix_terminal_complete(None, None))
        self.assertFalse(parent.prefix_terminal_complete(dict(finite_terminal_complete=False, self_close_witness_present=True, child_record={}), None))
        module, raw, unused, physical = run_window()
        rows = [json.loads(line) for line in raw.splitlines()]
        partial = b''.join((parent.canonical(r) + b'\n' for r in rows[:-2]))
        result = parent.compare_child('import_discovery', b'', b'', partial, 1, None, [], [])
        self.assertEqual(result['census_terminal_reason'], 'no_child_report_after_progress')
        self.assertFalse(parent.prefix_terminal_complete(result, None))
        module, sink = fixture.helper()
        guard, runtime, trace, unused = fixture.guard_for(module)

        def importer(name):
            for _ in range(7):
                module.sys.audit('open', 'D:/allowed', 'r', 0)
            raise LookupError('import failure fixture')
        with self.assertRaises(LookupError):
            module.diagnostic_import_once(runtime, _importer=importer)
        value = record()
        value['primary'] = dict(type='LookupError', message='import failure fixture', primary=None, secondary=[], cause=None, group=[], truncated=False)
        value['secondary'] = []
        result = compare_record(value, wire(sink.getvalue()))
        self.assertFalse(result['finite_terminal_complete'])
        self.assertFalse(parent.prefix_terminal_complete(result, None))
        self.assertEqual(result['census_terminal_reason'], 'import_error_before1024')

    def test_08_finite_output_duplicate_and_original_guard_rejection(self):
        module, sink = fixture.helper()
        guard, runtime, trace, primary = fixture.guard_for(module)
        module._census_start(runtime)
        with self.assertRaises(BaseException):
            module._census_start(runtime)
        module._CENSUS['seq'] = 12
        module._census_emit('progress')
        with self.assertRaises(BaseExceptionGroup):
            module._census_raise(None)
        self.assertLessEqual(len(sink.getvalue()), 24576)
        for path, mode in (('D:/protected/x', 'r'), ('D:/allowed', 'w')):
            module, sink = fixture.helper()
            guard, runtime, trace, primary = fixture.guard_for(module)
            module._census_start(runtime)
            with self.assertRaises(module.BootstrapImportRejected):
                module.sys.audit('open', path, mode, 0)
            self.assertEqual(module._CENSUS['passed'], 0)
            self.assertEqual(module._CENSUS['observed'], 0)
if __name__ == '__main__':
    unittest.main()
