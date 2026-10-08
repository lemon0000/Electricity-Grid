from types import SimpleNamespace

import pytest

from experiments import h1_native_call_timing_development_v1 as api
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


class Clock:
    now = 100
    def __call__(self): return self.now


class Fake:
    pass


@pytest.fixture
def setup_case(tmp_path, monkeypatch):
    def setup(*, keepfiles=False, suffixes=(), fail=False):
        clock, events = Clock(), []
        class Model:
            def setParam(self, key, val):
                events.append(('param', key, val)); clock.now += 11
            def optimize(self, callback):
                events.append(('optimize', callback)); clock.now += 73
                if fail: raise RuntimeError('optimize failed')
        solver = Fake()
        solver._solver_model = Model()
        solver._tee = False; solver._keepfiles = keepfiles; solver._log_file = 'test-only.log'
        solver._env_options = {'Threads': 1}; solver.options = {'Threads': 1, 'Seed': 3}
        solver._version_major = 12; solver._suffixes = suffixes; solver._callback = None
        solver._needs_updated = True
        monkeypatch.setattr(api, 'GurobiDirect', Fake)
        measurement = api.Measurement(tmp_path/'timing', 'a'*64, 0, clock=clock)
        return measurement, solver, clock, events
    return setup


def test_ast_copy_has_only_one_measurement_insertion():
    api.validate_vendor()


def test_delayed_intent_and_completion_io_are_non_native(setup_case, monkeypatch):
    m, solver, clock, events = setup_case()
    original = api.io.write_metadata
    def delayed(path, doc):
        if path.name in ('intent.json', 'completion.json'): clock.now += 1000
        return original(path, doc)
    monkeypatch.setattr(api.io, 'write_metadata', delayed)
    native = solver._solver_model
    _, receipt = m.apply(solver)
    assert solver._solver_model is native and solver._needs_updated is False
    assert events == [('param','LogToConsole',0),('param','Seed',3),('optimize',None)]
    assert receipt['native_interval_ns'] == 73
    assert receipt['non_native_apply_window_ns'] == 2022
    assert receipt['apply_window_ns'] == 2095
    assert m.closed and not m.poisoned
    assert not receipt['component_budget_verified']
    with pytest.raises(ValueError): m.apply(solver)
    assert sum(x[0]=='optimize' for x in events) == 1


def test_pinned_apply_preserves_suffix_keepfiles_and_option_order(setup_case):
    m, solver, _, events = setup_case(keepfiles=True, suffixes=('dual',))
    _, receipt = m.apply(solver)
    assert events == [('param','LogToConsole',0),('param','LogFile','test-only.log'),
        ('param','Seed',3),('param',api.gurobipy.GRB.Param.QCPDual,1),('optimize',None),
        ('param','LogFile','default')]
    assert receipt['native_interval_ns'] == 73 and receipt['non_native_apply_window_ns'] == 55


@pytest.mark.parametrize('filename', ['intent.json', 'completion.json', 'terminal.json'])
@pytest.mark.parametrize('after_write', [False, True])
def test_journal_failure_never_returns_timing_receipt(setup_case, monkeypatch, filename, after_write):
    m, solver, _, events = setup_case()
    original = api.io.write_metadata
    def fail(path, doc):
        if path.name == filename:
            if after_write: original(path, doc)
            raise OSError('confirmation failed')
        return original(path, doc)
    monkeypatch.setattr(api.io, 'write_metadata', fail)
    returned = []
    with pytest.raises(OSError): returned.append(m.apply(solver))
    assert returned == [] and m.poisoned and not m.closed
    assert (m.root/filename).exists() == after_write
    calls = sum(x[0]=='optimize' for x in events)
    assert calls == (0 if filename == 'intent.json' else 1)
    with pytest.raises(ValueError): m.apply(solver)
    assert sum(x[0]=='optimize' for x in events) == calls


@pytest.mark.parametrize('fault', ['optimize', 'clock', 'callback', 'vendor', 'ast', 'owner', 'tail'])
def test_exception_or_drift_remains_unknown(setup_case, monkeypatch, fault):
    m, solver, clock, events = setup_case(fail=fault=='optimize')
    if fault == 'clock':
        solver._solver_model.optimize = lambda callback: setattr(clock, 'now', -1)
    elif fault == 'callback': solver._callback = object()
    elif fault == 'vendor': monkeypatch.setattr(api.vendor, '_set_options', lambda *args: None)
    elif fault == 'ast': monkeypatch.setattr(api, '_apply_body', lambda *args: None)
    elif fault == 'owner': m.owner = (-1, -1)
    elif fault == 'tail':
        solver._keepfiles = True
        original = solver._solver_model.setParam
        def fail(key, value):
            if value == 'default': raise RuntimeError('post-optimize bookkeeping failure')
            return original(key, value)
        solver._solver_model.setParam = fail
    with pytest.raises((ValueError, RuntimeError)): m.apply(solver)
    assert m.poisoned and not m.closed and not (m.root/'terminal.json').exists()
    if fault in ('callback','vendor','ast','owner'): assert not any(x[0]=='optimize' for x in events)


def test_direct_reentry_rejects_without_poisoning_active_owner(setup_case):
    m, solver, _, events = setup_case()
    m.guard.acquire()
    try:
        with pytest.raises(ValueError): m.apply(solver)
        assert not m.poisoned and not m.started
    finally: m.guard.release()
    assert events == []


@pytest.mark.parametrize('filename', ['binding.json','intent.json','completion.json','terminal.json'])
def test_fresh_reader_requires_intact_chain(setup_case, filename):
    m, solver, _, _ = setup_case(); _, receipt = m.apply(solver)
    (m.root/filename).write_bytes(b'{}')
    with pytest.raises((ValueError, KeyError)):
        api.inspect(m.root, expected_binding_sha=m.binding_pin,
            expected_terminal_sha=receipt['terminal_sha256'], expected_implementation=m.implementation)


def test_three_separate_stage_intervals_are_not_whole_hour_evidence(tmp_path, monkeypatch):
    clock = Clock(); pins = []
    monkeypatch.setattr(api, 'GurobiDirect', Fake)
    for index in range(3):
        solver = Fake(); solver._solver_model = SimpleNamespace(
            setParam=lambda *args: None, optimize=lambda callback: setattr(clock,'now',clock.now+73))
        solver._tee=solver._keepfiles=False; solver._env_options={}; solver.options={}
        solver._version_major=12; solver._suffixes=(); solver._callback=None
        m=api.Measurement(tmp_path/str(index),'a'*64,index,clock=clock)
        _, result=m.apply(solver); pins.append(result['terminal_sha256'])
        assert result['native_interval_ns']==73 and not result['instrumentation_coverage_verified']
    assert len(set(pins))==3
