"""Explicit fake route/Parent fixtures for the borrowed bridge, no live authority."""
import ast
import copy
import json
from hashlib import sha256
from pathlib import Path
import sys
from threading import Lock, Thread
from types import ModuleType, SimpleNamespace

import pytest
import experiments
from experiments import h1_common_validation_operation_development_v2 as original


@pytest.fixture
def case(tmp_path, monkeypatch, request):
    events = []
    fault = [None]
    guards = tuple(Lock() for _ in range(8))
    for guard in guards:
        guard.acquire()
    marks = tuple(SimpleNamespace(_reference_held=True) for _ in range(3))
    attached = {arm: dict(reference=dict(local_terminal=dict(body=dict(
        controller_root=str(tmp_path / arm), controller_binding_sha256='a'*64,
        controller_terminal_sha256='b'*64)))) for arm in ('cfe', 'joint', 'network')}
    roster = SimpleNamespace(_direct=tuple(sorted(attached)), _replay=lambda: (attached, attached, 'c'*64))
    class Handoff:
        pass
    owner = Handoff()
    owner._state = 'running'
    token = object()
    record = dict(external_active=False, predecessor=(object(), None, None, None, roster, guards[1]),
        common_guards=guards[1:4], bundle_state=(object(), (), guards[4:], marks))
    def verify(h):
        assert h is owner
        if not guards[0].locked():
            raise ValueError('original outer guard changed')
    def operation(h, supplied):
        verify(h)
        if supplied is not token:
            raise ValueError('original operation token required')
        return record
    verify.__qualname__ = '_anchor.<locals>.verify'
    operation.__qualname__ = '_anchor.<locals>.operation'
    api = ModuleType(original._HANDOFF_NAME)
    api.__file__ = str(Path(original.__file__).with_name(original._HANDOFF_NAME.rsplit('.', 1)[1] + '.py'))
    api.Handoff, api._VERIFY_OWNER = Handoff, verify
    monkeypatch.setitem(sys.modules, api.__name__, api)
    monkeypatch.setattr(experiments, api.__name__.rsplit('.', 1)[1], api, raising=False)
    name = 'experiments._borrowed_validation_unit_' + tmp_path.name
    path = Path(original.__file__).resolve()
    module = ModuleType(name)
    module.__file__, module.__package__ = str(path), 'experiments'
    monkeypatch.setitem(sys.modules, name, module)
    monkeypatch.setattr(experiments, name.rsplit('.', 1)[1], module, raising=False)
    sessions = []
    class Session:
        def __init__(self, lease):
            self.lease, self._nonce, self._public_session = lease, object(), 'unit-session'
            self._common_calls, self.rows, self.failure, self.closed = 0, [], None, False
            sessions.append(self)
            module._CLAIM_SESSION(lease, self)
            if fault[0] == 'constructor':
                raise RuntimeError('session constructor')
        def close(self):
            events.append('session_close')
            self.closed = True
            if fault[0] == 'close':
                raise RuntimeError('session close')
        def _poison(self, error):
            events.append('session_poison')
            self.failure = self.failure or repr(error)
            if fault[0] == 'poison':
                raise RuntimeError('session poison')
        def receipt(self):
            return dict(common_executions=copy.deepcopy(self.rows),
                complete=self.closed and self.failure is None and self._common_calls == 22,
                arm_receipts={arm: dict(proof_cleared=self.closed) for arm in attached})
    class Arm:
        pass
    class SourceResult:
        pass
    class CommonResult:
        def __init__(self, session):
            self._session_nonce = session._nonce
            self.manifest, self.source_binding = 'unit-manifest', 'unit-binding'
            self.predecessor_report_payload = b'{"explicit_fake_report":true}'
    def source_prepare(*args, **kwargs):
        raise AssertionError('fake bridge unit must not run numerical source work')
    def prepare(session):
        module._BOOKEND(session.lease)
        if session._common_calls >= 22:
            raise ValueError('common call limit')
        if fault[0] == 'prepare':
            raise RuntimeError('common preparation')
        ordinal = session._common_calls + 1
        full, within, cross = (24, 24, 0) if ordinal == 1 else (0, 0, 48)
        session.rows.append(dict(common_call=ordinal, full_numerical_hour_replays=full,
            within_prefix_revalidations=within, cross_common_numerical_proof_reuses=cross,
            context_evaluations=96))
        session._common_calls = ordinal
        return CommonResult(session)
    def identity():
        return 'd'*64
    helper_name = 'borrowed_unit_routes_' + tmp_path.name
    helper = ModuleType(helper_name)
    for field, value in dict(Session=Session, Arm=Arm, SourceResult=SourceResult,
            CommonResult=CommonResult, prepare=prepare, source_prepare=source_prepare,
            identity=identity, bridge=module).items():
        setattr(helper, field, value)
    monkeypatch.setitem(sys.modules, helper_name, helper)
    bodies = [f'from {helper_name} import Session as GroupWitnessSession, Arm as ArmWitness, bridge as operation_bridge, identity as verifier_identity\n',
        f'from {helper_name} import SourceResult as CommonSourceBundle, source_prepare as prepare_common_bundle, identity as implementation_identity\nfrom experiments import h1_operation_historical_witness_development_v3 as witness\n',
        f'from {helper_name} import CommonResult as PreparedCommonInput, prepare, identity as implementation_identity\nfrom experiments import h1_operation_historical_witness_development_v3 as witness\nfrom experiments import h1_phase_exact_source_current_development_v4 as source\n']
    variant = getattr(request, 'param', None)
    if variant:
        kind, index = variant
        if kind == 'compile':
            bodies[index] += 'invalid python syntax !\n'
        elif kind == 'exec':
            bodies[index] += 'raise RuntimeError("route execution")\n'
    routes = []
    for route, body in zip(original._ROUTE_NAMES, bodies):
        monkeypatch.delitem(sys.modules, route, raising=False)
        monkeypatch.delattr(experiments, route.rsplit('.', 1)[1], raising=False)
        target = tmp_path / (route.rsplit('.', 1)[1] + '.py')
        target.write_text(body, encoding='utf-8')
        routes.append((route, str(target.resolve()), sha256(target.read_bytes()).hexdigest()))
    # Explicit pre-definition AST seam only; the real bridge has fixed routes.
    tree = ast.parse(path.read_bytes(), filename=str(path))
    assignment, = [node for node in tree.body if isinstance(node, ast.Assign)
        and any(isinstance(t, ast.Name) and t.id == '_PINNED_ROUTES' for t in node.targets)]
    assignment.value = ast.parse(repr(tuple(routes)), mode='eval').body
    ast.fix_missing_locations(tree)
    exec(compile(tree, str(path), 'exec'), vars(module))
    attach, common, declaration, finish, abort, receipt = module._bind_handoff(api, Handoff, verify, operation)
    c = SimpleNamespace(m=module, owner=owner, token=token, record=record, fault=fault,
        guards=guards, marks=marks, sessions=sessions, events=events, routes=routes,
        attach=attach, prepare=common, declaration=declaration, finish=finish, abort=abort, receipt=receipt)
    try:
        yield c
    finally:
        if sessions:
            abort(owner, ValueError('unit teardown'))
        for guard in guards:
            if guard.locked():
                guard.release()


def still_owned(c):
    assert all(guard.locked() for guard in c.guards)
    assert all(mark._reference_held for mark in c.marks)


def test_all_twenty_two_returns_close_only_private_proofs_and_bind_counts(case):
    c = case
    c.attach(c.owner, c.token)
    declaration = c.declaration(c.owner)
    for _ in range(22):
        assert c.prepare(c.owner) == ('unit-manifest', 'unit-binding', {'explicit_fake_report': True})
    result = c.finish(c.owner)
    assert result['complete'] and result['closed'] and result['all_arm_proofs_cleared']
    assert tuple(result[key] for key in ('full_numerical_hour_replays', 'within_prefix_revalidations',
        'cross_common_numerical_proof_reuses', 'context_evaluations')) == (24, 24, 1008, 2112)
    assert len(result['common_receipt_sha256s']) == 22
    assert all(result[key] == value for key, value in declaration.items())
    still_owned(c)
    result['complete'] = False
    assert c.receipt(c.owner)['complete']
    with pytest.raises(ValueError, match='active Handoff validation lease'):
        c.m._VERIFY_LEASE(c.sessions[0].lease)


@pytest.mark.parametrize('calls', [0, 1, 21])
def test_early_finish_fails_and_clears_private_session_without_outer_release(case, calls):
    c = case
    c.attach(c.owner, c.token)
    for _ in range(calls):
        c.prepare(c.owner)
    with pytest.raises(ValueError, match='twenty-two'):
        c.finish(c.owner)
    assert c.sessions[0].closed and c.sessions[0].failure
    assert not c.receipt(c.owner)['complete']
    still_owned(c)


def test_extra_common_poisons_without_starting_new_numerical_work(case):
    c = case
    c.attach(c.owner, c.token)
    for _ in range(22):
        c.prepare(c.owner)
    with pytest.raises(ValueError, match='limit'):
        c.prepare(c.owner)
    assert c.sessions[0]._common_calls == 22 and c.sessions[0].failure
    c.abort(c.owner, ValueError('extra call'))
    still_owned(c)


@pytest.mark.parametrize('fault', ['constructor', 'prepare', 'close', 'poison'])
def test_failures_close_private_session_and_preserve_outer_ownership(case, fault):
    c = case
    if fault == 'constructor':
        c.fault[0] = fault
        with pytest.raises(RuntimeError, match='constructor'):
            c.attach(c.owner, c.token)
    else:
        c.attach(c.owner, c.token)
        c.fault[0] = fault
        if fault == 'prepare':
            with pytest.raises(RuntimeError, match='preparation'):
                c.prepare(c.owner)
        c.abort(c.owner, ValueError('original failure'))
    assert c.sessions[0].closed and not c.receipt(c.owner)['complete']
    still_owned(c)


@pytest.mark.parametrize('kind', ['guard', 'mark', 'external', 'token', 'foreign_thread'])
def test_borrowed_lifetime_drift_rejects_before_common(case, kind):
    c = case
    c.attach(c.owner, c.token)
    if kind == 'guard':
        c.guards[4].release()
    elif kind == 'mark':
        c.marks[0]._reference_held = False
    elif kind == 'external':
        c.record['external_active'] = True
    elif kind == 'token':
        with pytest.raises(ValueError, match='token'):
            c.attach(c.owner.__class__(), object())
        return
    errors = []
    def invoke():
        try:
            c.prepare(c.owner)
        except BaseException as error:
            errors.append(error)
    if kind == 'foreign_thread':
        thread = Thread(target=invoke)
        thread.start()
        thread.join(timeout=10)
        assert not thread.is_alive()
    else:
        invoke()
    assert len(errors) == 1 and isinstance(errors[0], ValueError)
    assert c.sessions[0]._common_calls == 0 and c.sessions[0].failure


@pytest.mark.parametrize('index', [0, 1, 2])
@pytest.mark.parametrize('kind', ['package', 'module', 'bytes'])
def test_route_drift_rejects_and_captured_private_cleanup_remains_available(case, monkeypatch, index, kind):
    c = case
    c.attach(c.owner, c.token)
    name, path, _ = c.routes[index]
    if kind == 'package':
        monkeypatch.setattr(experiments, name.rsplit('.', 1)[1], ModuleType('foreign'))
    elif kind == 'module':
        monkeypatch.setitem(sys.modules, name, ModuleType('foreign'))
    else:
        path = Path(path)
        path.write_bytes(path.read_bytes() + b'\n# drift\n')
    with pytest.raises(ValueError, match='route changed'):
        c.prepare(c.owner)
    c.abort(c.owner, ValueError('source drift'))
    assert c.sessions[0].closed and c.sessions[0]._common_calls == 0
    still_owned(c)


@pytest.mark.parametrize('case', [(kind, index) for kind in ('compile', 'exec') for index in range(3)], indirect=True)
def test_partial_loader_failure_rolls_back_only_created_routes(case):
    with pytest.raises((SyntaxError, RuntimeError)):
        case.attach(case.owner, case.token)
    assert not case.sessions
    for name, _, _ in case.routes:
        assert name not in sys.modules and name.rsplit('.', 1)[1] not in vars(experiments)
    still_owned(case)


def test_forged_and_copied_leases_do_not_borrow_a_token(case):
    with pytest.raises(TypeError):
        case.m._Lease()
    with pytest.raises(ValueError, match='active Handoff'):
        case.m._VERIFY_LEASE(object.__new__(case.m._Lease))
    case.attach(case.owner, case.token)
    with pytest.raises(TypeError):
        copy.copy(case.sessions[0].lease)
