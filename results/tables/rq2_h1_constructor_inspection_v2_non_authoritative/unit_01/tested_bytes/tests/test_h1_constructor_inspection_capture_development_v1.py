"""Constructor lifetime and preserved observation-window contracts; no source authority."""
import ast
from concurrent.futures import ThreadPoolExecutor
from copy import copy, deepcopy
import json
from pathlib import Path
import pickle

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
            if mode != 'none':
                assert self.inspect() is self.value
            if mode == 'double':
                self.inspect()
            if mode == 'constructor_failure':
                raise RuntimeError('constructor failed after accepted inspect')
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
        monkeypatch.setattr(kind._cic_owner, '__code__', (lambda self: None).__code__)
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
            line[8:] for line in text[start:end].splitlines() if '_check_dependencies()' not in line)), include_attributes=False)
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
