from copy import deepcopy
import importlib.util
from pathlib import Path
import threading

import pytest

spec = importlib.util.spec_from_file_location('h1_timing_dev', Path(__file__).resolve().parents[1]/
    'experiments/h1_segment_timing_development_v1.py')
api = importlib.util.module_from_spec(spec)
spec.loader.exec_module(api)


def ledger(ticks):
    values = iter(ticks)
    return api.Ledger('a'*64, clock=lambda: next(values))


def nested():
    log = ledger([0, 10, 20, 40, 70, 100])
    with log.span(0, 'build'):
        with log.span(0, 'native_optimize'):
            pass
    return log.finish()


def test_nested_exclusive_accounting_and_unclassified():
    result = api.analyse(nested())
    assert result['recorded_window_wall_ns'] == 100
    assert result['exclusive_phase_ns']['build'] == 40
    assert result['exclusive_phase_ns']['native_optimize'] == 20
    assert result['unclassified_ns'] == 40
    assert sum(result['exclusive_phase_ns'].values()) + result['unclassified_ns'] == 100
    assert not result['component_budget_verified']
    assert not result['observer_overhead_separated']


def test_exception_keeps_open_intervals_and_poison():
    log = ledger([0, 10, 20])
    with pytest.raises(RuntimeError):
        with log.span(0, 'build'):
            with log.span(0, 'capture'):
                raise RuntimeError('arbitrary text not serialized')
    doc = log.snapshot()
    assert all(s['end_ns'] is None for s in doc['spans'])
    assert all(s['status'] == 'unknown' for s in doc['spans'])
    result = api.analyse(doc)
    assert result['recorded_window_wall_ns'] is None
    assert set(result['exclusive_phase_ns'].values()) == {None}
    with pytest.raises(ValueError):
        log.finish()


def test_clock_reversal_and_wrong_clock_type():
    for last in (-1, 9, True, 2**63):
        log = ledger([0, 10, last])
        with pytest.raises(ValueError):
            with log.span(0, 'audit'):
                pass
        assert log.snapshot()['fault'] == 'clock'
        assert not api.analyse(log.snapshot())['intervals_complete']


def test_duplicate_stage_phase_and_finish_with_open_span():
    log = ledger([0, 1, 2])
    with log.span(0, 'audit'):
        pass
    with pytest.raises(ValueError):
        with log.span(0, 'audit'):
            pass
    other = ledger([0, 1])
    with pytest.raises(ValueError):
        with other.span(0, 'build'):
            other.finish()
    assert not api.analyse(other.snapshot())['intervals_complete']


def test_cross_thread_domain_rejected():
    log = ledger([0])
    errors = []
    def read():
        try:
            log.snapshot()
        except ValueError as error:
            errors.append(str(error))
    thread = threading.Thread(target=read)
    thread.start()
    thread.join()
    assert errors == ['different process/thread clock domain']


@pytest.mark.parametrize('mutation', ['bool_time', 'extra_domain', 'parent_forward',
    'child_outside', 'worker_outside', 'duplicate', 'unknown_phase', 'id_bool',
    'overlap', 'unclosed_sibling', 'bad_identity', 'out_of_order'])
def test_independent_reader_rejects_malformed_intervals(mutation):
    doc = nested()
    rows = doc['spans']
    if mutation == 'bool_time': rows[0]['start_ns'] = True
    elif mutation == 'extra_domain': rows[1]['clock_domain'] = 'b'*32
    elif mutation == 'parent_forward': rows[0]['parent'] = 1
    elif mutation == 'child_outside': rows[1]['end_ns'] = 80
    elif mutation == 'worker_outside': doc['end_ns'] = 60
    elif mutation == 'duplicate': rows[1]['phase'] = 'build'
    elif mutation == 'unknown_phase': rows[0]['phase'] = 'arbitrary'
    elif mutation == 'id_bool': rows[0]['id'] = False
    elif mutation == 'overlap': rows[1]['parent'] = None
    elif mutation == 'unclosed_sibling':
        rows[0]['end_ns'] = None
        rows[0]['status'] = 'open'
        rows[1]['parent'] = None
    elif mutation == 'bad_identity': doc['request_sha256'] = 'g'*64
    elif mutation == 'out_of_order': rows[1]['start_ns'] = 5
    with pytest.raises(ValueError):
        api.analyse(doc)


def test_snapshot_is_detached_and_exclusive_write(tmp_path):
    log = ledger([0, 1])
    doc = log.finish()
    copy = deepcopy(doc)
    doc['request_sha256'] = 'b'*64
    assert log.snapshot() == copy
    path = tmp_path/'timing.json'
    result = api.write_snapshot(path, copy)
    assert result['bytes'] == path.stat().st_size
    with pytest.raises(FileExistsError):
        api.write_snapshot(path, doc)
    with pytest.raises(ValueError):
        log.finish()


def test_unknown_incomplete_and_closed_empty_are_not_budget_evidence():
    log = ledger([0, 2])
    assert not api.analyse(log.snapshot())['intervals_complete']
    result = api.analyse(log.finish())
    assert result['unclassified_ns'] == 2
    assert not result['instrumentation_coverage_verified']


def test_io_failure_retains_file(tmp_path, monkeypatch):
    path = tmp_path/'timing.json'
    def fail(fd):
        raise OSError('injected fsync failure')
    monkeypatch.setattr(api.os, 'fsync', fail)
    with pytest.raises(OSError, match='injected'):
        api.write_snapshot(path, nested())
    assert path.exists()
    with pytest.raises(FileExistsError):
        api.write_snapshot(path, nested())


def test_short_write_is_rejected(tmp_path, monkeypatch):
    class ShortWriter:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def write(self, raw): return len(raw)-1
    monkeypatch.setattr(api.Path, 'open', lambda *a, **k: ShortWriter())
    with pytest.raises(OSError, match='short timing write'):
        api.write_snapshot(tmp_path/'timing.json', nested())


def test_readback_mismatch_retains_file(tmp_path, monkeypatch):
    path = tmp_path/'timing.json'
    monkeypatch.setattr(api.Path, 'read_bytes', lambda *a: b'wrong')
    with pytest.raises(OSError, match='readback differs'):
        api.write_snapshot(path, nested())
    assert path.exists()


def test_size_cap_and_process_owner(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'MAX_BYTES', 1)
    with pytest.raises(ValueError, match='byte bound'):
        api.write_snapshot(tmp_path/'timing.json', nested())
    assert not (tmp_path/'timing.json').exists()
    log = ledger([0])
    monkeypatch.setattr(api.os, 'getpid', lambda: 1+log._pid)
    with pytest.raises(ValueError, match='different process'):
        log.snapshot()


def test_non_lifo_context_use_poison():
    log = ledger([0, 10, 20])
    first = log.span(0, 'build')
    second = log.span(0, 'audit')
    first.__enter__()
    second.__enter__()
    with pytest.raises(ValueError, match='non-LIFO'):
        first.__exit__(None, None, None)
    with pytest.raises(ValueError, match='poisoned'):
        second.__exit__(None, None, None)
    assert not api.analyse(log.snapshot())['intervals_complete']


def test_external_observer_interval_is_separate(tmp_path):
    doc = nested()
    ticks = iter([1000, 1500])
    receipt = api.write_snapshot(tmp_path/'timing.json', doc, clock=lambda: next(ticks))
    assert receipt['observer_interval_ns'] == 500
    assert receipt['observer_clock_domain'] != doc['clock_domain']
    assert not receipt['receipt_overhead_included']
    assert api.analyse(doc)['recorded_window_wall_ns'] == 100
    ticks = iter([2000, 1999])
    with pytest.raises(ValueError, match='observer clock reversal'):
        api.write_snapshot(tmp_path/'backwards.json', doc, clock=lambda: next(ticks))
    assert (tmp_path/'backwards.json').exists()


def test_status_must_match_interval():
    doc = nested()
    doc['spans'][0]['status'] = 'unknown'
    with pytest.raises(ValueError, match='status/closure'):
        api.analyse(doc)
