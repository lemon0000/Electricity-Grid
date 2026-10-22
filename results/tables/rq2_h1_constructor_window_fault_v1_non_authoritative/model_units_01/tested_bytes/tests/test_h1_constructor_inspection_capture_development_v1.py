"""Constructor lifetime and preserved observation-window contracts; no source authority."""
import ast
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
import json
from pathlib import Path
import pickle
from threading import RLock
from types import SimpleNamespace
import importlib.metadata

import pytest

from experiments import h1_constructor_inspection_capture_development_v1 as capture
from experiments import h1_phase_historical_batch_development_v1 as old_history
from experiments import h1_phase_historical_batch_development_v2 as history
from experiments import h1_phase_exact_source_batch_development_v2 as source
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def make(mode='normal', retained=None):
    retained = [] if retained is None else retained
    class Parent:
        def __init__(self):
            self.value = object()
            self.closed = False
            self.inspect_calls = 0
            retained.append(self)
            try:
                if mode != 'none':
                    assert self.inspect() is self.value
                if mode == 'double':
                    self.inspect()
                if mode == 'constructor_failure':
                    raise RuntimeError('constructor failed after accepted inspect')
            except BaseException:
                self.close()
                raise
        def inspect(self):
            self.inspect_calls += 1
            if mode == 'recursive':
                return self.inspect()
            if mode == 'inspection_failure':
                raise RuntimeError('inspection failed')
            return self.value
        def close(self):
            self.closed = True
            if mode == 'close_failure':
                raise RuntimeError('close failed')
    class Reader(capture.ConstructorInspectionCapture, Parent):
        pass
    return Reader()


def test_constructor_capture_is_exact_one_shot_and_cleared(tmp_path):
    reader = make()
    assert reader.inspect_calls == 1
    assert reader._take_constructor_inspection() is reader.value
    assert reader._cic_value is capture._EMPTY
    assert reader._cic_taken and not reader._cic_constructing and not reader._cic_inspecting
    with pytest.raises(ValueError, match='unused'):
        reader._take_constructor_inspection()
    with pytest.raises(ValueError, match='exactly one'):
        reader.inspect()
    reader.close()
    assert reader.closed
    (tmp_path / 'constructor_capture_fact.json').write_text(json.dumps(dict(
        status='DRAFT_NONAUTHORITATIVE', constructor_parent_inspects=1,
        same_object_returned=True, one_shot=True, cleared=True, fake_parent=True,
        actual_source_or_owner_exercised=False, real_native_calls=0, new_normal_jobs=0,
        paired_owner_authenticated=False, phase_events_written=0,
        formal_result=False), indent=2) + '\n', encoding='utf-8')


@pytest.mark.parametrize('mode', ['double', 'recursive', 'inspection_failure', 'constructor_failure'])
def test_failed_constructor_cannot_retain_capture(mode):
    retained = []
    with pytest.raises((ValueError, RuntimeError)):
        make(mode, retained)
    reader = retained[0]
    assert reader._cic_value is capture._EMPTY
    assert not reader._cic_constructing and not reader._cic_inspecting
    assert reader.closed  # Parent constructor's exception handler ran already.
    with pytest.raises(ValueError, match='unused'):
        reader._take_constructor_inspection()
    reader.close()


def test_missing_inspection_and_close_failure_clear_slots():
    reader = make('none')
    with pytest.raises(ValueError, match='unused'):
        reader._take_constructor_inspection()
    reader.close()
    reader = make('close_failure')
    with pytest.raises(RuntimeError, match='close failed'):
        reader.close()
    assert reader._cic_value is capture._EMPTY
    with pytest.raises(ValueError, match='unused'):
        reader._take_constructor_inspection()


@pytest.mark.parametrize('method', ['inspect', '_take_constructor_inspection', 'close'])
def test_foreign_thread_rejected_without_consuming_creator_value(method):
    reader = make()
    with ThreadPoolExecutor(max_workers=1) as pool:
        with pytest.raises(ValueError, match='creator'):
            pool.submit(getattr(reader, method)).result()
    assert reader._take_constructor_inspection() is reader.value
    reader.close()


@pytest.mark.parametrize('function', [copy, deepcopy, pickle.dumps])
def test_capture_cannot_be_copied_or_serialized(function):
    reader = make()
    try:
        with pytest.raises(TypeError):
            function(reader)
    finally:
        reader.close()


@pytest.mark.parametrize('drift', ['alias', 'code', 'defaults', 'class_added'])
def test_capture_definition_drift_rejected_before_constructor(monkeypatch, drift):
    kind = capture.ConstructorInspectionCapture
    if drift == 'alias':
        monkeypatch.setattr(kind, 'inspect', lambda self: None)
    elif drift == 'code':
        function = kind._cic_owner
        monkeypatch.setattr(function, '__code__', function.__code__.replace(co_name='drifted_owner'))
    elif drift == 'defaults':
        monkeypatch.setattr(kind._cic_owner, '__defaults__', (True,))
    else:
        monkeypatch.setattr(kind, '_unregistered', True, raising=False)
    retained = []
    with pytest.raises(ValueError, match='capture.*changed'):
        make(retained=retained)
    assert retained == []


def test_failed_close_preserves_primary_and_closes_other_leases():
    reader = make('close_failure')
    calls = []
    class Lease:
        def close(self):
            calls.append('lease')
    primary = ValueError('original primary')
    captured = {0: object()}
    history._close_replay(reader, [Lease()], captured, True, primary)
    assert captured == {} and calls == ['lease']
    assert reader._cic_value is capture._EMPTY
    assert 'cleanup also failed' in primary.__notes__[0]


def test_post_constructor_bookends_are_preserved_in_order():
    def after_check(path):
        text = Path(path).read_text(encoding='utf-8')
        start = text.index('            base.entry.unchanged(views);inventory()')
        end = text.index('            proofs={}', start)
        return ast.dump(ast.parse('def retained():\n' + '\n'.join(
            line[8:] for line in text[start:end].splitlines()
            if '_check_dependencies()' not in line and '_model_dependencies_unchanged(' not in line)), include_attributes=False)
    assert after_check(old_history.__file__) == after_check(history.__file__)
    text = Path(history.__file__).read_text(encoding='utf-8')
    assert 'state=reader.inspect()' not in text
    assert text.count('state=reader._take_constructor_inspection()') == 1


def test_new_source_still_has_two_reader_calls_around_materialization():
    tree = ast.parse(Path(source.__file__).read_text(encoding='utf-8'))
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    readers = sorted(node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == '_REPLAY_PREFIXES')
    materialize = [node.lineno for node in calls if isinstance(node.func, ast.Name) and node.func.id == '_materialize']
    assert len(readers) == 2 and len(materialize) == 1 and readers[0] < materialize[0] < readers[1]
    assert source.historical is history and history.SCHEMA != old_history.SCHEMA


@pytest.mark.parametrize('pins,selected', [({}, None), ({True: 'a'*64}, None), ({1: 'a'*64}, None),
    ({0:'a'*64, 2:'b'*64}, None), ({0:'bad'}, None), ({192:'a'*64}, None),
    ({0:'a'*64}, (1,)), ({0:'a'*64}, (0,0)), ({0:'a'*64}, (False,))])
def test_bad_map_rejected_before_filesystem_or_reader(pins, selected):
    with pytest.raises(ValueError):
        source.prepare_many('unused', expected_binding_sha256='c'*64,
            expected_registry_identity='d'*64, expected_terminals=pins, selected_hours=selected)


@pytest.mark.parametrize('drift', ['utility_alias', 'parent_method', 'parent_code', 'parent_added'])
def test_historical_dependency_drift_rejects_before_path_read(monkeypatch, drift):
    if drift == 'utility_alias':
        monkeypatch.setattr(old_history, '_observe_prefix', lambda *a: None)
    elif drift == 'parent_method':
        monkeypatch.setattr(history.HistoricalTimedSnapshot, '__init__', lambda *a: None)
    elif drift == 'parent_code':
        function = history.history.HistoricalSnapshot._append
        replacement = (lambda self: None).__code__
        assert function.__closure__ is None
        monkeypatch.setattr(function, '__code__', replacement)
    else:
        monkeypatch.setattr(history.HistoricalTimedSnapshot, '_extra', True, raising=False)
    with pytest.raises(ValueError, match='successor'):
        history.replay_prefixes('unused', expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64, completed_hours=1,
            expected_terminals={0:'b'*64}, selected_hours=(0,))


@pytest.mark.parametrize('window', ['before_constructor', 'before_take', 'empty_before_take'])
@pytest.mark.parametrize('drift', ['empty', 'guard_alias', 'guard_code', 'guard_defaults',
    'pid', 'thread', 'owner_alias', 'owner_code', 'owner_defaults', 'class_alias'])
def test_capture_binding_fault_windows(monkeypatch, window, drift):
    reader = None if window == 'before_constructor' else make('none' if window == 'empty_before_take' else 'normal')
    original_value = None if reader is None else reader._cic_value
    try:
        with monkeypatch.context() as patch:
            if drift == 'empty':
                patch.setattr(capture, '_EMPTY', object())
            elif drift == 'guard_alias':
                patch.setattr(capture, '_check_definition', lambda: None)
            elif drift.startswith('guard_'):
                f = capture._check_definition
                patch.setattr(f, '__code__' if drift == 'guard_code' else '__defaults__',
                    f.__code__.replace(co_name='drifted_guard') if drift == 'guard_code' else (True,))
            elif drift == 'pid':
                patch.setattr(capture.os, 'getpid', lambda: -1)
            elif drift == 'thread':
                patch.setattr(capture, 'get_ident', lambda: -1)
            elif drift == 'owner_alias':
                patch.setattr(capture.ConstructorInspectionCapture, '_cic_owner', lambda self: None)
            elif drift in ('owner_code', 'owner_defaults'):
                f = capture.ConstructorInspectionCapture._cic_owner
                patch.setattr(f, '__code__' if drift == 'owner_code' else '__defaults__',
                    f.__code__.replace(co_name='drifted_owner') if drift == 'owner_code' else (True,))
            else:
                patch.setattr(capture, 'ConstructorInspectionCapture', object)
            with pytest.raises(ValueError, match='capture.*changed'):
                if reader is None:
                    # Keep the original class even when its module alias drifts.
                    class Parent:
                        def __init__(self):
                            pytest.fail('parent entered after dependency drift')
                    class Reader(history.ConstructorInspectionCapture, Parent):
                        pass
                    Reader()
                else:
                    reader._take_constructor_inspection()
            if reader is not None:
                assert reader._cic_value is original_value and not reader._cic_taken
                reader.close()  # Original closure bindings permit teardown after drift.
                assert reader.closed
    finally:
        if reader is not None:
            reader.close()


@pytest.mark.parametrize('name', ['HistoricalTimedSnapshot', 'ConstructorInspectionCapture',
    '_observe_prefix', '_close_replay', '_function_state'])
def test_historical_local_alias_fault_is_rejected(monkeypatch, name):
    monkeypatch.setattr(history, name, object())
    with pytest.raises(ValueError, match='successor local'):
        history._check_dependencies()


@pytest.mark.parametrize('name', ['process_id', 'empty'])
@pytest.mark.parametrize('window', ['before_constructor', 'before_take'])
def test_capture_closure_cell_fault_is_rejected(monkeypatch, name, window):
    reader = None if window == 'before_constructor' else make()
    function = capture.ConstructorInspectionCapture.__init__
    cells = dict(zip(function.__code__.co_freevars, function.__closure__))
    with monkeypatch.context() as patch:
        patch.setattr(cells[name], 'cell_contents', object())
        with pytest.raises(ValueError, match='capture.*changed'):
            make() if reader is None else reader._take_constructor_inspection()
    if reader is not None:
        assert reader._take_constructor_inspection() is reader.value
        reader.close()


@pytest.mark.parametrize('module,name', [(source, '_REPLAY_PREFIXES'), (source, 'historical'),
    (source, '_materialize'), (history, '_observe_sources'), (history, 'HistoricalTimedSnapshot')])
def test_source_observes_its_and_reader_global_bindings(monkeypatch, module, name):
    monkeypatch.setattr(module, name, object())
    with pytest.raises(ValueError, match='(batch|successor).*alias'):
        source._check_reader_entry()


@pytest.mark.parametrize('name', ['replay_prefixes', '_check_dependencies', '_function_state'])
@pytest.mark.parametrize('drift', ['alias', 'code', 'defaults', 'kwdefaults'])
def test_source_pins_historical_callable_state(monkeypatch, name, drift):
    function = getattr(history, name)
    if drift == 'alias':
        monkeypatch.setattr(history, name, lambda *a, **kw: None)
    else:
        field = dict(code='__code__', defaults='__defaults__', kwdefaults='__kwdefaults__')[drift]
        replacement = dict(code=function.__code__.replace(co_name='drifted_entry'),
                           defaults=(True,), kwdefaults={'drift': True})[drift]
        monkeypatch.setattr(function, field, replacement)
    with pytest.raises(ValueError, match='batch historical'):
        source.prepare_many('unused', expected_binding_sha256='a'*64,
            expected_registry_identity='b'*64, expected_terminals={0:'c'*64})


@pytest.mark.parametrize('failure', ['inspect', 'after_inspect'])
@pytest.mark.parametrize('cleanup_failure', [None, '_journal', '_anchor', '_root_lease'])
def test_constructor_fault_uses_actual_ordered_parent_close(failure, cleanup_failure):
    # Exact inherited close method, with an equivalent constructor catch window.
    # Inner-close failure retains outer owners for the parent's safe retry.
    calls, retained = [], []
    class Lease:
        def __init__(self, name):
            self.name, self.failed = name, False
        def close(self):
            calls.append(self.name)
            if self.name == cleanup_failure and not self.failed:
                self.failed = True
                raise RuntimeError('inner cleanup failed')
    class Parent:
        close = history.history.HistoricalSnapshot.close
        def __init__(self):
            self._guard, self._closed = RLock(), False
            for name in ('_journal', '_anchor', '_root_lease'):
                setattr(self, name, Lease(name))
            retained.append(self)
            try:
                self.inspect()
                raise ValueError('after accepted inspection')
            except BaseException:
                self.close()
                raise
        def inspect(self):
            if failure == 'inspect':
                raise ValueError('inspection failed')
            return object()
    class Reader(capture.ConstructorInspectionCapture, Parent):
        pass
    with pytest.raises((ValueError, RuntimeError)):
        Reader()
    reader = retained[0]
    assert reader._cic_value is capture._EMPTY and not reader._cic_constructing
    order = ['_journal', '_anchor', '_root_lease']
    stop = len(order) if cleanup_failure is None else order.index(cleanup_failure)+1
    assert calls == order[:stop] and reader._closed
    if cleanup_failure in ('_journal', '_anchor'):
        assert reader._root_lease is not None
    reader.close()
    assert all(getattr(reader, name) is None for name in order)


@pytest.mark.parametrize('drift', ['alias', 'code'])
def test_error_cleanup_uses_original_capture_close_program(monkeypatch, drift):
    reader = make()
    kind = capture.ConstructorInspectionCapture
    with monkeypatch.context() as patch:
        if drift == 'alias':
            patch.setattr(kind, 'close', lambda self: None)
        else:
            function = kind.close
            # Actual no-op body with the same free-cell count; the saved close
            # program must still reach Parent.close instead of this body.
            no_op = (lambda self: None).__code__.replace(co_freevars=function.__code__.co_freevars)
            patch.setattr(function, '__code__', no_op)
        primary = ValueError('dependency drift')
        with pytest.raises(ValueError, match='successor'):
            history._check_dependencies()
        history._close_replay(reader, [], {}, False, primary)
        assert reader.closed and reader._cic_value is capture._EMPTY


@pytest.mark.parametrize('name', ['_materialize', 'implementation_identity'])
@pytest.mark.parametrize('drift', ['code', 'defaults', 'kwdefaults'])
def test_source_pins_own_projection_and_identity_callable(monkeypatch, name, drift):
    function = getattr(source, name)
    field = dict(code='__code__', defaults='__defaults__', kwdefaults='__kwdefaults__')[drift]
    value = dict(code=function.__code__.replace(co_name='drifted_source'),
                 defaults=(True,), kwdefaults={'drift': True})[drift]
    monkeypatch.setattr(function, field, value)
    with pytest.raises(ValueError, match='batch historical callable'):
        source._check_reader_entry()


@pytest.mark.parametrize('name', ['SCHEMA', 'implementation_identity'])
def test_historical_pins_own_schema_and_identity(monkeypatch, name):
    monkeypatch.setattr(history, name, object())
    with pytest.raises(ValueError, match='successor local'):
        history._check_dependencies()


@pytest.mark.parametrize('name', ['_CONSTRUCTOR_CLOSE', '_close_replay'])
@pytest.mark.parametrize('drift', ['code', 'defaults'])
def test_historical_cleanup_helper_state_rejected_before_read(monkeypatch, name, drift):
    function = getattr(history, name)
    field = '__code__' if drift == 'code' else '__defaults__'
    value = function.__code__.replace(co_name='drifted_cleanup') if drift == 'code' else (True,)
    monkeypatch.setattr(function, field, value)
    with pytest.raises(ValueError, match='successor callable'):
        history.replay_prefixes('unused', expected_binding_sha256='a'*64,
            expected_terminal_sha256='b'*64, completed_hours=1,
            expected_terminals={0:'b'*64}, selected_hours=(0,))


@pytest.mark.parametrize('name', ['_dependencies', 'normal_input_identity', '_validate', '_encode', '_digest', 'version'])
@pytest.mark.parametrize('drift', ['alias', 'code', 'defaults'])
def test_named_model_dependency_callable_fault_rejected(monkeypatch, name, drift):
    function = getattr(history.model, name)
    if drift == 'alias':
        monkeypatch.setattr(history.model, name, lambda *a, **kw: None)
    else:
        field = '__code__' if drift == 'code' else '__defaults__'
        value = function.__code__.replace(co_name='drifted_model') if drift == 'code' else (True,)
        monkeypatch.setattr(function, field, value)
    with pytest.raises(ValueError, match='successor'):
        history._check_dependencies()


@pytest.mark.parametrize('name', ['CONTRACT', 'TOLERANCE', 'SOURCE_DEPENDENCIES', 'RUNTIME_DISTRIBUTIONS'])
def test_model_dependency_constants_rejected(monkeypatch, name):
    monkeypatch.setattr(history.model, name, object())
    with pytest.raises(ValueError, match='successor dependency alias'):
        history._check_dependencies()


@pytest.mark.parametrize('name', ['Path', '__file__', 'sha256', 'platform'])
def test_model_dependency_global_slots_rejected(monkeypatch, name):
    monkeypatch.setattr(history.model, name, object())
    with pytest.raises(ValueError, match='successor dependency alias'):
        history._check_dependencies()


@pytest.mark.parametrize('name', ['python_version', 'python_implementation'])
@pytest.mark.parametrize('drift', ['alias', 'code', 'defaults'])
def test_platform_dependency_callable_fault_rejected(monkeypatch, name, drift):
    function = getattr(history.model.platform, name)
    if drift == 'alias':
        monkeypatch.setattr(history.model.platform, name, lambda: 'changed')
    else:
        field = '__code__' if drift == 'code' else '__defaults__'
        value = function.__code__.replace(co_name='drifted_platform') if drift == 'code' else (True,)
        monkeypatch.setattr(function, field, value)
    with pytest.raises(ValueError, match='successor'):
        history._check_dependencies()


@pytest.mark.parametrize('name', ['_model_dependency_snapshot', '_model_dependencies_unchanged'])
@pytest.mark.parametrize('drift', ['alias', 'code', 'defaults'])
def test_snapshot_helper_callable_fault_rejected(monkeypatch, name, drift):
    function = getattr(history, name)
    if drift == 'alias':
        monkeypatch.setattr(history, name, lambda *a: None)
    else:
        field = '__code__' if drift == 'code' else '__defaults__'
        value = function.__code__.replace(co_name='drifted_snapshot') if drift == 'code' else (True,)
        monkeypatch.setattr(function, field, value)
    with pytest.raises(ValueError, match='successor'):
        history._check_dependencies()


def test_runtime_metadata_value_drift_is_rejected_at_bookend(monkeypatch):
    before = history._model_dependency_snapshot()
    monkeypatch.setattr(importlib.metadata, 'distribution', lambda name: SimpleNamespace(version='development_changed_version'))
    with pytest.raises(ValueError, match='normal model dependencies changed'):
        history._model_dependencies_unchanged(before)


@pytest.mark.parametrize('version', [None, 1])
def test_runtime_metadata_snapshot_requires_exact_string_values(monkeypatch, version):
    monkeypatch.setattr(importlib.metadata, 'distribution', lambda name: SimpleNamespace(version=version))
    with pytest.raises(ValueError, match='exact normal model dependency snapshot'):
        history._model_dependency_snapshot()


def test_detached_validator_rejects_missing_model_dependency_bookend():
    from experiments import h1_constructor_source_batch_validation_development_v1 as validator
    metrics = tuple(dict(completed_hours=1, selected_hours=[0], parent_inspect_traversals=1,
        constructor_inspection_reused=True, observation_token=str(i)*32) for i in (1, 2))
    batch = source.CurrentBatch({0: object()}, metrics)
    with pytest.raises(ValueError, match='batch observation shape'):
        validator.validate_detached_batch(batch, object(), {0: 'a'*64}, (0,), 'b'*64)
