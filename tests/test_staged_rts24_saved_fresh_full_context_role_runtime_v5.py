"""Finite, in-memory full-role fixtures; no project target or child executes."""
import ast
import copy
from hashlib import sha256
import importlib.util
from pathlib import Path
from types import FunctionType, SimpleNamespace
import unittest

ROOT = Path(__file__).absolute().parents[1]
SOURCE = ROOT/'experiments/staged_rts24_saved_fresh_full_context_role_runtime_v5.py'
GATED = ('_invoke', '_mechanical_binding', '_cleanup_call', '_new_session', '_time', '_entry')
FIXTURE = '''
def clock():
    STATE['clock_calls']=STATE.get('clock_calls',0)+1
    return 101.0
def owner_entry():
    return STATE['owner']
def owner_sources():
    return STATE['sources']
def cleanup_helper(primary):
    STATE['events'].append('owner_close')
    owner = STATE['owner']
    owner._phase = 'CLOSED' if primary is None else 'UNRESOLVED'
    owner._resource.phase = 'CLOSED'
    owner._resource.pending = [False, False]
    owner._resource.close_calls = [1, 1]
    if STATE.get('close_callback'):
        STATE['close_callback']()
    if STATE.get('carrier'):
        raise STATE['carrier']
def owner_close(primary):
    cleanup_helper(primary)
def context_check(raw, digest):
    return STATE['context']
def role_entry(role, raw, digest):
    return STATE['context']
def hold(sources, caller):
    STATE['events'].append('hold')
    return STATE['held']
def replay(held, digest):
    STATE['events'].append('replay')
    if STATE.get('callback'):
        STATE['callback']()
    if STATE.get('replay_error'):
        raise STATE['replay_error']
    return STATE['payload']
def bookend(held, *, inventory=True):
    STATE['events'].append('inventory')
    return STATE.get('inventory_result')
def caller_image(held):
    return held.image
def program_check():
    return None
def create_owned(request):
    STATE['events'].append('create')
    if STATE.get('create_error'):
        raise STATE['create_error']
    return STATE['child']
def capture_owned(result):
    STATE['events'].append('capture')
    if STATE.get('capture_error'):
        raise STATE['capture_error']
    return None if STATE.get('capture_none') else result
def capture_failed(primary, result):
    STATE['recovery_result'] = result
    if STATE.get('recovery_error'):
        raise STATE['recovery_error']
    return None if STATE.get('recovery_none') else (result or STATE.get('partial'))
def finish_owned(child, digest, deadline):
    STATE['events'].append('quiet')
    child.terminal = True
    return STATE['quiet']
def retained_result(child):
    return STATE['quiet']
def child_is_terminal(child):
    if STATE.get('probe_error'):
        raise STATE['probe_error']
    return child.terminal
def consume_original_output(child, quiet, context):
    STATE['events'].append('output')
    return STATE['output']
def abort_owned(child, primary, deadline):
    STATE['events'].append('abort')
    if STATE.get('abort_error'):
        raise STATE['abort_error']
    child.terminal = True
def child_identity(child):
    return STATE['identity']
def observation_raw(child, quiet):
    return STATE['observation']
'''


def load_original():
    spec = importlib.util.spec_from_file_location('_closed_role_original', SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def transformed():
    tree = ast.parse(SOURCE.read_bytes())
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    modules = {node.module if isinstance(node, ast.ImportFrom) else node.names[0].name for node in imports}
    assert modules == {'ast', 'builtins', 'hashlib', 'json', 'math', 'os', 'pathlib', 'time', 'threading', 'types'}
    changed = []
    for node in tree.body:
        if type(node) is ast.FunctionDef and node.name in GATED:
            index = 1 if isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant) else 0
            assert isinstance(node.body[index], ast.Raise) and node.body[index].exc.func.id == 'FullRoleUnavailable'
            del node.body[index]
            changed.append(node.name)
        if type(node) is ast.FunctionDef and node.name == 'current':
            node.body = [ast.Raise(exc=ast.Call(func=ast.Name(id='FullRoleUnavailable', ctx=ast.Load()),
                                               args=[ast.Constant('synthetic clone has separate provenance')], keywords=[]))]
    assert tuple(changed) == GATED
    ast.fix_missing_locations(tree)
    return ast.unparse(tree).encode('utf-8')


def contract():
    raw = SOURCE.read_bytes(); clone = transformed()
    return dict(original_source=dict(bytes=len(raw), sha256=sha256(raw).hexdigest()),
                clone=dict(bytes=len(clone), sha256=sha256(clone).hexdigest()),
                transform='remove_exact_six_leading_unavailable_raises_and_disable_current_v1',
                fixture_sha256=sha256(FIXTURE.encode()).hexdigest(), synthetic_only=True,
                original_public_binding_closed=True, project_target_imports=0, child_processes=0)


class Fixture:
    def __init__(self, role='parent', core_binding=None):
        self.m = m = SimpleNamespace()
        ns = dict(__file__=str(SOURCE), __name__='_synthetic_full_role')
        exec(compile(transformed(), '<synthetic_full_role>', 'exec'), ns)
        m.__dict__.update(ns)
        self.ns = ns
        # All target rows use exactly this finite no-import source namespace.
        self.state = state = dict(events=[], sources={'synthetic': '0'*64})
        self.target = target = dict(STATE=state, __builtins__={})
        exec(compile(FIXTURE, '<fixed_full_role_fixture>', 'exec'), target)
        self.codes = {value.__code__ for value in target.values() if type(value) is FunctionType}
        owner = SimpleNamespace(_phase='LIVE', _consume_state='RUNNING',
                                _resource=SimpleNamespace(phase='LIVE', pending=[True, True], close_calls=[0, 0]))
        if core_binding is not None:
            core_binding=m._capture_core_owner_cleanup(*core_binding)
            owner=core_binding.owner
            self.codes.add(core_binding.packet[0])
        state['owner'] = owner
        caller = dict(source=state['sources'], files={'synthetic_input': [1, '0'*64]})
        context = dict(schema=m.CONTEXT_SCHEMA, scope=m.SCOPE, output_mode='saved_P1_F_validation',
                       authority='DRAFT_NONAUTHORITATIVE', invocation_started=100.0, deadline=280.0,
                       caller_core=caller, caller_sha=sha256(m.canonical(caller)).hexdigest(),
                       source_pins=state['sources'], input_files=caller['files'], repo_root='synthetic', environment={},
                       **{key: False for key in m.GATES})
        state['context'] = context
        self.raw = m.canonical(context); digest = sha256(self.raw).hexdigest()
        state['held'] = SimpleNamespace(image=m.canonical(caller), files=caller['files'])
        state['payload'] = dict(context_sha=digest, caller_sha=context['caller_sha'], full_metrics=['synthetic', 19])
        state.update(output=m.canonical(state['payload']), child=SimpleNamespace(terminal=False), quiet=object(),
                     identity=m.canonical({'synthetic_child': 1}), observation=m.canonical({'synthetic_quiet': True}))
        self.packets = []
        original_invoke = ns['_invoke']; original_cleanup = ns['_cleanup_call']
        original_capture = ns['_capture_cleanup']
        def invoke(row, *args):
            assert row.namespace is target and row.function.__code__ in self.codes and row.prefix == ()
            return original_invoke(row, *args)
        def capture(calls, launcher, quiet, core_cleanup=None):
            result = original_capture(calls, launcher, quiet, core_cleanup)
            self.packets.extend(value for name, value in result if name != 'wrapper_class')
            return result
        def cleanup(packet, *args):
            assert any(packet is allowed for allowed in self.packets) and packet[0] in self.codes
            return original_cleanup(packet, *args)
        ns.update(_invoke=invoke, _cleanup_call=cleanup, _capture_cleanup=capture)
        for name in ('_mechanical_binding', '_new_session', '_time', '_entry'):
            original = ns[name]
            def guarded(*args, _name=name, _original=original, **kwargs):
                subject = args[0]
                actual = subject if _name == '_mechanical_binding' else subject.owner if _name in ('_new_session', '_time') else subject._owner
                assert actual is owner, 'synthetic owner only'
                if _name == '_time':
                    assert subject.clock is target['clock'], 'synthetic clock only'
                return _original(*args, **kwargs)
            ns[name] = guarded
        m.__dict__.update(ns)
        self.calls = tuple((name, m._row(target, name)) for name in m.CALL_NAMES)
        self.request = dict(schema='staged_saved_F_full_role_launch_request_v1', scope=m.SCOPE,
                            context_sha=digest, source_epoch=m.SOURCE_EPOCH, role='fresh', argv=['synthetic-entry'],
                            cwd='synthetic', environment={}, channel_name='synthetic', channel_nonce='synthetic-nonce',
                            global_deadline=280.0, parent_identity='synthetic-owner',
                            manifest_pin=dict(bytes=1, sha256='0'*64), transport_pin=dict(bytes=1, sha256='1'*64))
        receipt = m.canonical(dict(schema='staged_saved_F_role_entry_receipt_v1', role=role,
                                   context_sha=digest, owner_identity='synthetic-owner'))
        self.proof = m._mechanical_entry_binding(owner, role, self.raw, dict(self.calls)['role_entry'], receipt,
                                                m.canonical(self.request) if role == 'parent' else None)
        launch = m._program_binding(m.LaunchBinding, tuple((name, m._row(target, name)) for name in m.LAUNCH_CALLS)) if role == 'parent' else None
        quiet = m._program_binding(m.QuietBinding, tuple((name, m._row(target, name)) for name in m.QUIET_CALLS)) if role == 'parent' else None
        self.kwargs = dict(outer_deadline=280.0, launch_request=self.request if role == 'parent' else None,
                           launch_program=launch, quiet_program=quiet, _clock=target['clock'])
        if core_binding is not None:self.kwargs['core_cleanup']=core_binding
        self.binding = m._mechanical_binding(owner, role, self.raw, self.calls, self.proof, **self.kwargs)
        self.session = m._new_session(self.binding)

    def run(self, *operations):
        result = None
        for operation in operations:
            result = self.m.dispatch(self.session, operation)
        return result

    def until_child(self):
        self.run('reconstruct', 'suspend_for_launch', 'launch_child')


class FullRoleTests(unittest.TestCase):
    def failure(self, f, operation, expected_close=1):
        with self.assertRaises(f.m._FAILURE_TYPES) as caught:
            f.run(operation)
        failure = caught.exception
        with self.assertRaises(f.m._FAILURE_TYPES) as again:
            f.run(operation)
        self.assertIs(again.exception, failure)
        self.assertEqual(f.state['events'].count('owner_close'), expected_close)
        return failure

    def test_01_original_seven_gates(self):
        m = load_original(); touched = []
        fake = SimpleNamespace(clock=lambda: touched.append('clock'))
        for name, args in [('_invoke', (fake,)), ('_mechanical_binding', (None, None, None, None, None)),
                           ('_cleanup_call', (fake,)), ('_new_session', (fake,)), ('_time', (fake,)),
                           ('_entry', (fake,)), ('bind_full_role', ())]:
            with self.assertRaises(m.FullRoleUnavailable):
                getattr(m, name)(*args, **({'outer_deadline': 0.0} if name == '_mechanical_binding' else {}))
        self.assertEqual(touched, [])
        self.assertFalse(m.current()[1]['live_effect_invocation_available'])

    def test_02_clone_provenance_and_allowlist(self):
        f = Fixture(); self.assertTrue(contract()['synthetic_only'])
        with self.assertRaises(f.m.FullRoleUnavailable): f.m.current()
        with self.assertRaises(AssertionError): f.m._invoke(SimpleNamespace(namespace={}))
        with self.assertRaises(AssertionError): f.m._time(SimpleNamespace(owner=object()))

    def test_03_parent_success_and_release(self):
        f = Fixture(); f.until_child(); f.run('quiet_child', 'consume_child', 'late_bookend')
        candidate, payload = f.run('close')
        value = f.m.parse(candidate)
        self.assertEqual([row['phase'] for row in value['phases']], ['G2', 'LAUNCH_READY', 'CHILD_ACTIVE', 'CHILD_QUIET', 'CHILD_COMPARED', 'G3'])
        self.assertEqual(value['phases'][-1]['obligations'], list(f.m.PARENT_OBLIGATIONS))
        self.assertEqual(f.state['events'], ['hold', 'replay', 'create', 'capture', 'quiet', 'output', 'inventory', 'owner_close'])
        self.assertEqual(f.run('close'), (candidate, payload))
        self.assertTrue(f.session._runtime_closed and f.session._child_terminal and f.session._closed)
        self.assertIsNone(f.session._binding); self.assertIsNone(f.session._held)
        self.assertTrue(all(value[key] is False for key in f.m.FALSE_FIELDS))

    def test_04_fresh_independent_success(self):
        f = Fixture('fresh'); f.run('reconstruct', 'late_bookend'); candidate, _ = f.run('close')
        self.assertEqual(f.m.parse(candidate)['phases'][-1]['obligations'], ['LC.fresh.G3'])
        self.assertNotIn('create', f.state['events'])

    def test_05_role_owner_context_join(self):
        for field, value in [('owner', object()), ('role', 'fresh'), ('context_pin', (0, '0'*64))]:
            f = Fixture(); object.__setattr__(f.proof, field, value)
            with self.assertRaises(ValueError):
                f.m._mechanical_binding(f.state['owner'], 'parent', f.raw, f.calls, f.proof, **f.kwargs)

    def test_06_launch_closed_fields_deadline(self):
        for field, value in [('extra', True), ('global_deadline', 281.0), ('role', 'parent'), ('argv', []),
                             ('channel_nonce', ''), ('transport_pin', dict(bytes=1, sha256='z'*64))]:
            f = Fixture(); request = copy.deepcopy(f.request); request[field] = value
            with self.assertRaises(ValueError): f.m._launch_request_data(request, f.state['context'], f.proof)
        f = Fixture(); kwargs = dict(f.kwargs, outer_deadline=200.0)
        with self.assertRaises(ValueError): f.m._mechanical_binding(f.state['owner'], 'parent', f.raw, f.calls, f.proof, **kwargs)

    def test_07_receipt_exact_fields(self):
        f = Fixture(); receipt = f.m.parse(f.proof.receipt); receipt['extra'] = True
        with self.assertRaises(ValueError):
            f.m._mechanical_entry_binding(f.state['owner'], 'parent', f.raw, dict(f.calls)['role_entry'], f.m.canonical(receipt), f.m.canonical(f.request))

    def test_08_create_partial_failure(self):
        f = Fixture(); f.run('reconstruct', 'suspend_for_launch'); error = RuntimeError('create')
        f.state.update(create_error=error, partial=f.state['child'])
        failure = self.failure(f, 'launch_child')
        self.assertIs(failure.primary, error); self.assertTrue(f.state['child'].terminal)
        self.assertEqual(f.state['events'].count('abort'), 1)

    def test_09_capture_failure_keeps_create(self):
        for absent in (False, True):
            f = Fixture(); f.run('reconstruct', 'suspend_for_launch'); error = RuntimeError('capture')
            f.state.update(capture_error=error, recovery_none=absent)
            failure = self.failure(f, 'launch_child')
            self.assertIs(failure.primary, error); self.assertIs(f.session._launch_result, f.state['child'])
            self.assertIs(f.state['recovery_result'], f.state['child'])
            self.assertEqual(f.session._closed, not absent)
            if absent: self.assertFalse(f.session._child_terminal)

    def test_10_capture_none_and_recovery_error(self):
        f = Fixture(); f.run('reconstruct', 'suspend_for_launch'); secondary = RuntimeError('recover')
        f.state.update(capture_none=True, recovery_error=secondary)
        failure = self.failure(f, 'launch_child')
        self.assertIsInstance(failure.primary, ValueError)
        self.assertIn(('launch_capture', secondary), failure.secondary)
        self.assertFalse(f.session._closed)

    def test_11_metadata_helper_drift_cleanup(self):
        f = Fixture(); error = RuntimeError('replay')
        def callback():
            f.target['owner_close'].__code__ = f.target['clock'].__code__
            f.target['cleanup_helper'].__code__ = f.target['clock'].__code__
        f.state.update(callback=callback, replay_error=error)
        self.assertIs(self.failure(f, 'reconstruct').primary, error)
        self.assertTrue(f.session._runtime_closed)

    def test_12_cleanup_packet_tamper_denied(self):
        for builtin in (False, True):
            f = Fixture(); packet = dict(f.binding.cleanup)['owner_close']; called = []
            if builtin: packet[1]['__builtins__']['len'] = lambda *args: called.append('builtin')
            else: packet[1]['cleanup_helper'] = lambda primary: called.append(primary)
            failure = self.failure(f, 'reconstruct', expected_close=0)
            self.assertEqual(called, []); self.assertFalse(f.session._runtime_closed)
            self.assertNotIn('hold', f.state['events'])
            self.assertTrue(any(name == 'runtime_close' for name, _ in failure.secondary))

    def test_13_probe_abort_recheck_and_split_terminal(self):
        f = Fixture(); f.until_child(); error = RuntimeError('probe'); f.state['probe_error'] = error
        failure = self.failure(f, 'bad_operation')
        self.assertTrue(f.session._runtime_closed); self.assertFalse(f.session._child_terminal or f.session._closed)
        self.assertEqual(f.session._phase, 'UNRESOLVED')
        self.assertEqual([name for name, _ in failure.secondary], ['child_terminal_probe', 'child_terminal_after_abort'])

    def test_14_expected_carrier_and_wrong_carrier(self):
        for expected in (True, False):
            f = Fixture(); primary = RuntimeError('primary')
            class Carrier(RuntimeError): pass
            carrier = Carrier('closed'); carrier.owner = f.state['owner']; carrier.primary = primary; carrier.secondary = ()
            # The exception class is held before capture in the source-specific kernel.
            cleanup = dict(f.binding.cleanup); cleanup['wrapper_class'] = Carrier if expected else ValueError
            object.__setattr__(f.binding, 'cleanup', tuple(cleanup.items()))
            object.__setattr__(f.binding, 'seal', f.m._binding_image(f.binding))
            f.state.update(replay_error=primary, carrier=carrier)
            failure = self.failure(f, 'reconstruct')
            self.assertIs(failure.primary, primary)
            self.assertEqual(f.session._runtime_carrier is carrier, expected)
            self.assertEqual(any(name == 'runtime_close' for name, _ in failure.secondary), not expected)

    def test_15_swallowed_reentry_replay(self):
        f = Fixture()
        def callback():
            try: f.run('reconstruct')
            except ValueError: pass
        f.state['callback'] = callback
        failure = self.failure(f, 'reconstruct')
        self.assertIs(failure.primary, f.session._pending_reentry)
        self.assertTrue(f.session._replay_returned)

    def test_16_swallowed_reentry_close(self):
        f = Fixture('fresh'); f.run('reconstruct', 'late_bookend')
        def callback():
            try: f.run('close')
            except ValueError: pass
        f.state['close_callback'] = callback
        failure = self.failure(f, 'close'); self.assertIs(failure.primary, f.session._pending_reentry)
        self.assertIsNotNone(f.session._binding)

    def test_17_replay_encoding_return_retained(self):
        f = Fixture(); f.state['payload']['bad'] = object()
        self.failure(f, 'reconstruct')
        self.assertTrue(f.session._replay_returned); self.assertIs(f.session._replay_result, f.state['payload'])

    def test_18_quiet_identity_and_observation_retained(self):
        for field, slot in [('identity', '_identity_result'), ('observation', '_observation_result')]:
            f = Fixture(); f.until_child(); value = object(); f.state[field] = value
            self.failure(f, 'quiet_child'); self.assertIs(getattr(f.session, slot), value)
            self.assertIs(f.session._quiet, f.state['quiet'])

    def test_19_output_comparison_return_retained(self):
        f = Fixture(); f.until_child(); f.run('quiet_child'); f.state['output'] = b'{"different":true}'
        self.failure(f, 'consume_child'); self.assertEqual(f.session._output_raw, f.state['output'])
        self.assertEqual(f.session._output_return_pin, f.m.pin(f.state['output']))

    def test_20_g3_and_commit_return_retained(self):
        f = Fixture('fresh'); f.run('reconstruct'); value = object(); f.state['inventory_result'] = value
        self.failure(f, 'late_bookend'); self.assertIs(f.session._g3_result, value)
        self.assertTrue(f.session._g3_returned); self.assertEqual(len(f.session._committed), 1)
        f = Fixture('fresh'); f.ns['_commit'] = lambda *a, **k: (_ for _ in ()).throw(RuntimeError('commit'))
        self.failure(f, 'reconstruct'); self.assertIsNotNone(f.session._replay_raw)
        self.assertEqual(f.session._committed, ())
        for name in ('_candidate', '_commit'):
            f = Fixture('fresh'); f.run('reconstruct')
            def broken(*args, **kwargs): raise RuntimeError('G3 publication')
            f.ns[name] = broken
            self.failure(f, 'late_bookend')
            self.assertTrue(f.session._g3_returned); self.assertIsNone(f.session._g3_result)
            self.assertEqual(len(f.session._committed), 1); self.assertIsNotNone(f.session._held)

    def test_21_active_registry_before_and_during_callback(self):
        for callback in (False, True):
            f = Fixture(); foreign = ('foreign',)
            def drift(): f.m._REGISTRY[id(f.session)] = foreign
            if callback: f.state['callback'] = drift
            else: drift()
            self.failure(f, 'reconstruct')
            self.assertIs(f.m._REGISTRY[id(f.session)], foreign)
        for remove in (False, True):
            f = Fixture(); self.failure(f, 'bad_operation')
            if remove: del f.m._TERMINALS[id(f.session)]
            else: f.m._TERMINALS[id(f.session)] = ('foreign',)
            with self.assertRaisesRegex(ValueError, 'sticky failure registry changed'): f.run('reconstruct')
            self.assertEqual(f.state['events'].count('owner_close'), 1)

    def test_22_terminal_foreign_row_preserved(self):
        f = Fixture(); foreign = ('foreign',); f.m._TERMINALS[id(f.session)] = foreign
        failure = self.failure(f, 'reconstruct')
        self.assertIs(f.m._TERMINALS[id(f.session)], foreign)
        self.assertIsInstance(failure, f.m.FullRoleEmergency)

    def test_23_failure_constructor_publish_fingerprint(self):
        for name in ('FullRoleFailure', '_publish_failure', '_failure_fingerprint', '_physical_image'):
            f = Fixture(); error = RuntimeError('primary'); f.state['replay_error'] = error
            def broken(*args, **kwargs): raise RuntimeError('injected preservation fault')
            # physical-image failure is injected after replay to avoid setup failure.
            f.state['callback'] = lambda: f.ns.update({name: broken})
            failure = self.failure(f, 'reconstruct')
            self.assertIs(failure.primary, error); self.assertIsInstance(failure, f.m.FullRoleEmergency)

    def test_24_class_methods_never_dispatch_effects(self):
        f = Fixture(); called = []
        f.m.EffectWindow.switch = lambda *args: called.append('switch')
        f.m.EffectWindow.launch = lambda *args: called.append('launch')
        f.m.EffectWindow.__setattr__ = lambda *args: called.append('setattr')
        f.m.EffectWindow.__getattribute__ = lambda *args: called.append('getattribute')
        f.m.EffectWindow.__init__ = lambda *args: called.append('init')
        f.m._new_window('parent', f.request)
        f.until_child(); f.run('quiet_child', 'consume_child', 'late_bookend', 'close')
        self.assertEqual(called, [])

    def test_25_runner_and_closure_mutation_denied(self):
        for change in ('runner', 'closure', 'wrapper'):
            f = Fixture(); called = []
            if change == 'closure':
                context = next(cell.cell_contents for cell in f.ns['_window_apply'].__closure__ if type(cell.cell_contents) is dict)
                context['__builtins__']['object'] = object()
            elif change == 'runner': f.ns['_window_apply'] = lambda *args: called.append('effect')
            else: f.ns['_window_do'] = lambda *args: called.append('effect')
            if change == 'wrapper':
                f.run('reconstruct'); self.failure(f, 'bad_operation')
            else:
                self.failure(f, 'reconstruct'); self.assertNotIn('hold', f.state['events'])
            self.assertEqual(called, [])

    def test_26_order_and_sticky_no_retry(self):
        for operation in ('launch_child', 'quiet_child', 'consume_child', 'late_bookend', 'close'):
            f = Fixture(); self.failure(f, operation)
            self.assertNotIn('create', f.state['events'])


if __name__ == '__main__':
    unittest.main()
