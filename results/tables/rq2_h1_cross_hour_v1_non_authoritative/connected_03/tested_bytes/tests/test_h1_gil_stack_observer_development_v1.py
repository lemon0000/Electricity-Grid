"""Real frame churn, bounded output and sticky diagnostic cleanup failures."""
import json
from pathlib import Path
import sys
from threading import get_ident
from time import monotonic, sleep

import pytest

from tests import h1_gil_stack_observer_development_v1 as m


def churn_until(predicate, timeout=2.):
    deadline = monotonic()+timeout
    while not predicate() and monotonic() < deadline:
        function = compile('(lambda x: sum(i for i in range(x)))(20)', '<frame-churn>', 'eval')
        assert eval(function) == 190
        sleep(.0001)
    assert predicate(), 'bounded sample was not observed'


def test_live_churn_captures_creator_frames_without_changing_trace_hooks(tmp_path):
    path = tmp_path/'stack.jsonl'
    profile, trace = sys.getprofile(), sys.gettrace()
    with m.observe_owner_stack(path, interval_seconds=.001, max_frames=3) as receipt:
        churn_until(lambda:receipt['samples'] >= 3)
    assert receipt['sampler_stopped'] and not receipt['errors']
    assert sys.getprofile() is profile and sys.gettrace() is trace
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert len(rows) >= 3 and receipt['bytes_written'] == path.stat().st_size
    assert all(row['owner_thread'] == get_ident() and 1 <= len(row['frames']) <= 3 for row in rows)
    assert any(frame['function'] == 'churn_until' for row in rows for frame in row['frames'])
    assert all(set(frame) == {'file', 'function', 'line'} for row in rows for frame in row['frames'])


def test_immediate_body_failure_stops_sampler_and_releases_file(tmp_path):
    path = tmp_path/'stack.jsonl'
    with pytest.raises(LookupError, match='body'):
        with m.observe_owner_stack(path) as receipt:
            raise LookupError('body')
    assert receipt['sampler_stopped'] and not receipt['errors']
    path.rename(tmp_path/'released.jsonl')


@pytest.mark.parametrize('budget', ['samples', 'bytes'])
def test_output_budget_is_sticky_and_stops_writer(tmp_path, budget):
    options = {'max_samples': 1} if budget == 'samples' else {'max_bytes': 1024}
    with pytest.raises(RuntimeError, match='budget exceeded'):
        with m.observe_owner_stack(tmp_path/'stack.jsonl', interval_seconds=.001, **options) as receipt:
            churn_until(lambda:receipt['samples'] >= 1 or bool(receipt.get('errors')),
                timeout=1.) if budget == 'samples' else sleep(.03)
            sleep(.03)
    assert receipt['sampler_stopped'] and receipt['errors']


def test_missing_owner_frame_failure_retains_body_exception(tmp_path, monkeypatch):
    monkeypatch.setattr(m.sys, '_current_frames', lambda:{})
    with pytest.raises(RuntimeError, match='no observable frame') as caught:
        with m.observe_owner_stack(tmp_path/'stack.jsonl', interval_seconds=.001) as receipt:
            sleep(.02)
            raise LookupError('original body failure')
    assert isinstance(caught.value.__context__, LookupError)
    assert receipt['sampler_stopped'] and receipt['errors']


def test_writer_io_failure_is_reported_after_stream_release(tmp_path, monkeypatch):
    class Broken:
        closed = False
        def write(self, text): raise OSError('injected write failure')
        def flush(self): raise AssertionError('unreachable')
        def close(self): self.closed = True
    broken = Broken()
    class OutputPath:
        def __init__(self, path): pass
        def open(self, *args, **kwargs): return broken
    # This fault belongs to the observer output stream. Keep process-wide
    # Path.open usable by the invocation's source and receipt checks.
    monkeypatch.setattr(m, 'Path', OutputPath)
    with pytest.raises(RuntimeError, match='injected write failure'):
        with m.observe_owner_stack(tmp_path/'stack.jsonl', interval_seconds=.001) as receipt:
            sleep(.02)
    assert broken.closed and receipt['sampler_stopped']


def test_thread_start_failure_closes_created_stream(tmp_path, monkeypatch):
    class Unstarted:
        def __init__(self, **kwargs): pass
        def start(self): raise OSError('injected start failure')
    monkeypatch.setattr(m, 'Thread', Unstarted)
    path = tmp_path/'stack.jsonl'
    with pytest.raises(OSError, match='injected start failure'):
        with m.observe_owner_stack(path):
            raise AssertionError('unreachable')
    path.rename(tmp_path/'released.jsonl')


def test_join_failure_is_sticky_and_still_completes_bounded_cleanup(tmp_path, monkeypatch):
    actual = m.Thread
    calls = []
    class InterruptedJoin(actual):
        def join(self, timeout):
            calls.append(timeout)
            if len(calls) == 1:
                raise LookupError('injected join failure')
            return super().join(timeout)
    monkeypatch.setattr(m, 'Thread', InterruptedJoin)
    path = tmp_path/'stack.jsonl'
    with pytest.raises(RuntimeError, match='join failed') as caught:
        with m.observe_owner_stack(path) as receipt:
            pass
    assert calls == [1., 1.]
    assert receipt['sampler_stopped'] and receipt['join_errors']
    assert isinstance(caught.value.__cause__, LookupError)
    path.rename(tmp_path/'released.jsonl')


@pytest.mark.parametrize('options', [dict(interval_seconds=True), dict(interval_seconds=0),
    dict(max_frames=129), dict(max_samples=0), dict(max_bytes=1023)])
def test_invalid_bounds_create_no_file(tmp_path, options):
    path = tmp_path/'stack.jsonl'
    with pytest.raises(ValueError, match='bounded exact'):
        with m.observe_owner_stack(path, **options):
            raise AssertionError('unreachable')
    assert not path.exists()
