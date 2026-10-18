"""Guard scheduling regressions, including all unchanged v1 reader observations."""
import importlib.util
from pathlib import Path
import sys

import pytest


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / 'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01/bounded_stable_read_entry_v2.py'
SUPPORT = REPO / 'tests/test_h1_bounded_stable_read_entry_development_v1.py'
spec = importlib.util.spec_from_file_location('bounded_entry_v1_test_support', SUPPORT)
prior = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = prior
spec.loader.exec_module(prior)
pytestmark = prior.pytestmark

# Reuse the same differential/fault cases against the successor implementation.
globals().update((name, value) for name, value in vars(prior).items() if name.startswith('test_'))


@pytest.fixture(autouse=True)
def successor_source(monkeypatch):
    monkeypatch.setattr(prior, 'SOURCE', SOURCE)


def test_non_target_opens_do_not_run_full_guard(tmp_path):
    path = tmp_path / 'plain'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    with lease:
        before = lease.receipt()
        for _ in range(64):
            with path.open('rb') as stream:
                assert stream.read(2) == b'ab'
        with pytest.raises(FileNotFoundError):
            (tmp_path / 'absent').open('rb')
        after = lease.receipt()
        assert after['full_checks'] - before['full_checks'] == 1  # receipt only
        assert after['fallback_opens'] - before['fallback_opens'] == 65
        assert after['exact_stable_read_calls'] == 0
        assert after['light_checks'] == before['light_checks']
    assert lease.closed_receipt()['remaining_code_handles'] == 0


def test_one_canonical_read_uses_three_full_two_light_guards(tmp_path):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    with lease:
        before = lease.receipt()
        assert prior.raw.read_stable(path, 32)[0] == b'abcd'
        after = lease.receipt()
        assert after['full_checks'] - before['full_checks'] == 4  # open/read/fstat2/receipt
        assert after['light_checks'] - before['light_checks'] == 2  # enter/fstat1
        assert after['exact_stable_read_calls'] == 1
        assert after['active_streams'] == 0
    closed = lease.closed_receipt()
    assert closed['path_open_restored'] and closed['path_read_bytes_restored']
    assert closed['remaining_streams'] == closed['remaining_proxies'] == 0


@pytest.mark.parametrize('field', ['raw_function', 'raw_code', 'raw_defaults', 'raw_keywords', 'wrapper_code', 'code_read'])
def test_non_target_route_rejects_dispatch_drift(tmp_path, monkeypatch, field):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    module, lease = prior.load()
    original_open, original_read = Path.open, Path.read_bytes
    marker = RuntimeError('body retained')
    try:
        with pytest.raises(RuntimeError) as caught:
            with lease:
                if field == 'raw_function':
                    monkeypatch.setattr(prior.raw, 'read_stable', lambda *a: None)
                elif field == 'raw_code':
                    monkeypatch.setattr(prior.raw.read_stable, '__code__', (lambda *a, **k: None).__code__)
                elif field == 'raw_defaults':
                    monkeypatch.setattr(prior.raw.read_stable, '__defaults__', (1,))
                elif field == 'raw_keywords':
                    monkeypatch.setattr(prior.raw.read_stable, '__kwdefaults__', {'cap': 8})
                elif field == 'wrapper_code':
                    # Keep its closure arity, so the original wrapper still reaches its own route guard.
                    monkeypatch.setattr(Path.open, '__defaults__', (object(),))
                else:
                    monkeypatch.setattr(Path, 'read_bytes', lambda p: b'')
                with pytest.raises(ValueError, match='route|poisoned'):
                    path.open('rb')
                raise marker
        assert caught.value is marker and caught.value.__notes__
        assert lease.closed_receipt()['remaining_code_handles'] == 0
    finally:
        monkeypatch.undo()
        Path.open, Path.read_bytes = original_open, original_read


@pytest.mark.parametrize('edge', ['open', 'enter', 'fileno1', 'read', 'fileno2', 'exit'])
def test_callback_drift_rejected_at_next_boundary_and_stream_closed(tmp_path, monkeypatch, edge):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    original_open = Path.open
    original_defaults = prior.raw.read_stable.__defaults__
    opened = []
    exits = []

    def mutate():
        prior.raw.read_stable.__defaults__ = (object(),)

    def opening(p, *args, **kwargs):
        stream = original_open(p, *args, **kwargs)
        if p != path or args != ('rb',):
            return stream
        opened.append(stream)
        calls = 0
        if edge == 'open':
            mutate()

        def enter():
            if edge == 'enter':
                mutate()

        def fileno():
            nonlocal calls
            calls += 1
            if edge == 'fileno' + str(calls):
                mutate()
            return stream.fileno()

        def read(n):
            result = stream.read(n)
            if edge == 'read':
                mutate()
            return result

        def exit_(*a):
            exits.append(1)
            if edge == 'exit':
                mutate()

        return prior.Stream(stream, read, exit_=exit_, enter=enter, fileno=fileno)

    monkeypatch.setattr(Path, 'open', opening)
    module, lease = prior.load()
    marker = RuntimeError('body retained')
    try:
        with pytest.raises(RuntimeError) as caught:
            with lease:
                if edge == 'exit':
                    prior.raw.read_stable(path, 8)
                    with pytest.raises(ValueError, match='route|poisoned'):
                        lease.receipt()
                else:
                    with pytest.raises(ValueError, match='route|poisoned'):
                        prior.raw.read_stable(path, 8)
                raise marker
        assert caught.value is marker
        assert len(opened) == 1 and opened[0].closed
        assert len(exits) == (0 if edge == 'open' else 1)
        closed = lease.closed_receipt()
        assert closed['remaining_streams'] == closed['remaining_proxies'] == closed['remaining_code_handles'] == 0
    finally:
        prior.raw.read_stable.__defaults__ = original_defaults


def test_read_error_with_guard_drift_preserves_primary(tmp_path, monkeypatch):
    path = tmp_path / 'input'
    path.write_bytes(b'abcd')
    original_open = Path.open
    original_defaults = prior.raw.read_stable.__defaults__
    marker = OSError('original read failure')
    opened = []

    def opening(p, *args, **kwargs):
        stream = original_open(p, *args, **kwargs)
        if p != path or args != ('rb',):
            return stream
        opened.append(stream)

        def read(n):
            prior.raw.read_stable.__defaults__ = (object(),)
            raise marker

        return prior.Stream(stream, read)

    monkeypatch.setattr(Path, 'open', opening)
    module, lease = prior.load()
    try:
        with pytest.raises(OSError) as caught:
            with lease:
                prior.raw.read_stable(path, 8)
        assert caught.value is marker and marker.__notes__
        assert len(opened) == 1 and opened[0].closed
        assert lease.closed_receipt()['remaining_code_handles'] == 0
    finally:
        prior.raw.read_stable.__defaults__ = original_defaults
