import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from experiments import h1_durable_timing_development_v1 as api


def journal(tmp_path, ticks=None):
    if ticks is None:
        ticks = iter(range(10000))
    return api.Journal(tmp_path/'ledger', 'a'*64, clock=lambda: next(ticks))


def inspect(j):
    return api.inspect(j.root, expected_binding_sha256=j.binding_sha256,
                       expected_terminal_sha256=j.terminal_sha256)


def test_nested_repeated_phases_exclusive_and_remainder(tmp_path):
    j = journal(tmp_path)
    with j.span(0, 'capture'):
        with j.span(0, 'audit'):
            pass
        with j.span(0, 'audit'):
            pass
    out = j.finish()
    assert out['exclusive_phase_ns']['capture'] == 3
    assert out['exclusive_phase_ns']['audit'] == 2
    assert out['unclassified_ns'] == 2
    assert out['recorded_window_wall_ns'] == 7
    assert not out['component_budget_verified']
    assert inspect(j) == out


@pytest.mark.parametrize('window', ['before', 'body', 'end', 'terminal'])
def test_failure_windows_unknown_and_no_retry(tmp_path, monkeypatch, window):
    j = journal(tmp_path)
    original = api.io.write_metadata
    def fail(path, doc):
        if ((window == 'before' and doc.get('kind') == 'begin')
                or (window == 'end' and doc.get('kind') == 'end')
                or (window == 'terminal' and doc.get('kind') == 'terminal')):
            path.write_bytes(b'{')
            raise OSError('injected partial write')
        return original(path, doc)
    monkeypatch.setattr(api.io, 'write_metadata', fail)
    entered = []
    with pytest.raises((OSError, RuntimeError)):
        with j.span(0, 'audit'):
            entered.append(True)
            if window == 'body':
                raise RuntimeError('consumer')
        j.finish()
    assert bool(entered) == (window != 'before')
    assert not inspect(j)['intervals_complete']
    assert inspect(j)['exclusive_phase_ns'] is None
    with pytest.raises(ValueError, match='poisoned'):
        j.finish()


def test_process_stop_after_durable_begin_is_unknown(tmp_path):
    j = journal(tmp_path)
    span = j.span(0, 'audit')
    span.__enter__()
    assert (j.root/'00000.json').exists()
    out = inspect(j)
    assert out['spans_started'] == 1 and out['recorded_window_wall_ns'] is None
    span.__exit__(RuntimeError, RuntimeError('simulated process interruption'), None)


@pytest.mark.parametrize('change', ['delete', 'append', 'replace', 'binding', 'cap'])
def test_fresh_inspection_rejects_damage(tmp_path, change):
    j = journal(tmp_path)
    with j.span(0, 'audit'):
        pass
    j.finish()
    if change == 'delete': (j.root/'00001.json').unlink()
    if change == 'append': (j.root/'foreign').write_bytes(b'')
    if change == 'replace': (j.root/'00001.json').write_bytes(b'{}')
    if change == 'binding': (j.root/'binding.json').write_bytes(b'{}')
    if change == 'cap': (j.root/'00001.json').write_bytes(b' '*2049)
    assert not inspect(j)['intervals_complete']


def test_clock_reversal_and_foreign_owner_poison(tmp_path):
    j = journal(tmp_path, iter([5, 4]))
    with pytest.raises(ValueError, match='clock reversal'):
        with j.span(0, 'audit'): pass
    assert j.poisoned
    other = api.Journal(tmp_path/'other', 'a'*64)
    with ThreadPoolExecutor(1) as pool:
        with pytest.raises(ValueError, match='owner'):
            pool.submit(other.finish).result()
    assert other.poisoned


def test_create_once_and_cap(tmp_path, monkeypatch):
    j = journal(tmp_path)
    with pytest.raises(FileExistsError): journal(tmp_path)
    monkeypatch.setattr(api, 'MAX_SPANS', 1)
    with j.span(0, 'audit'): pass
    with pytest.raises(ValueError, match='cap'):
        with j.span(0, 'audit'): pass


def test_terminal_landed_but_confirmation_failed_stays_unknown(tmp_path, monkeypatch):
    j = journal(tmp_path)
    original = api.io.write_metadata
    def fail(path, doc):
        result = original(path, doc)
        if doc.get('kind') == 'terminal': raise OSError('lost confirmation')
        return result
    monkeypatch.setattr(api.io, 'write_metadata', fail)
    with j.span(0, 'audit'): pass
    with pytest.raises(OSError): j.finish()
    assert j.terminal_sha256 is None
    assert not inspect(j)['intervals_complete']


def test_actual_child_process_exit_leaves_durable_begin(tmp_path):
    import subprocess
    import sys
    from pathlib import Path
    root = tmp_path/'child_journal'
    script = '''
import os, sys
from experiments.h1_durable_timing_development_v1 import Journal
j = Journal(sys.argv[1], 'a'*64)
with j.span(0, 'audit'):
    os._exit(17)
'''
    child = subprocess.run([sys.executable, '-B', '-c', script, str(root)],
        cwd=Path(__file__).resolve().parents[1], capture_output=True, timeout=20)
    assert child.returncode == 17, child.stderr
    pin = api.io.digest((root/'binding.json').read_bytes())
    result = api.inspect(root, expected_binding_sha256=pin)
    assert result['spans_started'] == 1
    assert result['exclusive_phase_ns'] is None and not result['intervals_complete']


def test_binding_write_failure_preserves_create_once_root(tmp_path, monkeypatch):
    def fail(path, document):
        path.write_bytes(b'{')
        raise OSError('binding interrupted')
    monkeypatch.setattr(api.io, 'write_metadata', fail)
    with pytest.raises(OSError): journal(tmp_path)
    assert (tmp_path/'ledger/binding.json').read_bytes() == b'{'
    with pytest.raises(FileExistsError): journal(tmp_path)
