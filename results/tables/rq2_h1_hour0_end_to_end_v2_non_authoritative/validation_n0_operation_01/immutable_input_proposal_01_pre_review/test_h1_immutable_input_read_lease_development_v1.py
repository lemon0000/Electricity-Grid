"""Actual Windows admission and cleanup for explicitly immutable JSON inputs."""
from hashlib import sha256
import importlib.util
import os
from pathlib import Path
import sys
from threading import Thread
from types import ModuleType

import pytest

from experiments import h1_raw_ingress_development_v1 as raw

REPO = Path(__file__).resolve().parents[1]
HERE = REPO / 'results/tables/rq2_h1_hour0_end_to_end_v2_non_authoritative/validation_n0_operation_01'
CODE = HERE / 'code_and_immutable_input_lease_v2.py'
ENTRY = HERE / 'bounded_stable_read_entry_v3.py'
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='actual Windows deny-write/delete handles')


def load(monkeypatch, path, pin=None):
    package = ModuleType('performance')
    package.__path__ = [str(HERE)]
    monkeypatch.setitem(sys.modules, 'performance', package)
    def module(name, source):
        spec = importlib.util.spec_from_file_location(name, source)
        value = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, value)
        spec.loader.exec_module(value)
        return value
    code = module('performance.code_read_lease', CODE)
    package.code_read_lease = code
    bounded = module('performance.bounded_stable_read_entry', ENTRY)
    expected = {p: sha256(p.read_bytes()).hexdigest() for p in (CODE, ENTRY, Path(raw.__file__).resolve())}
    inputs = {path: pin or sha256(path.read_bytes()).hexdigest()}
    return code, bounded.BoundedStableReadLease(expected, root=Path('D:/'), immutable_inputs=inputs)


def test_input_hits_keep_exact_bytes_and_canonical_reader_fresh(tmp_path, monkeypatch):
    path = tmp_path / 'input.json'
    path.write_bytes(b'{"fixed":true}')
    expected = raw.read_stable(path, 256)
    code, lease = load(monkeypatch, path)
    original_open, original_read = Path.open, Path.read_bytes
    with lease:
        for _ in range(8):
            assert path.read_bytes() == expected[0]
        assert raw.read_stable(path, 256) == expected
        receipt = lease.receipt()
        assert receipt['immutable_input_bytes_cached'] and receipt['source_or_result_cache']
        assert receipt['exact_stable_read_calls'] == 1
        assert receipt['code_lease']['immutable_input_read_hits'] == 8
        assert receipt['code_lease']['immutable_input_sha256'] == {str(path): sha256(expected[0]).hexdigest()}
        assert not receipt['code_lease']['live_source_cache']
        assert not receipt['code_lease']['saved_record_cache']
    assert Path.open is original_open and Path.read_bytes is original_read
    assert lease.closed_receipt()['remaining_code_handles'] == 0
    with path.open('r+b'):
        pass


@pytest.mark.parametrize('action', ['write', 'replace', 'unlink', 'rename_parent', 'new_hardlink'])
def test_live_lease_prevents_input_and_namespace_mutation(tmp_path, monkeypatch, action):
    folder = tmp_path / 'held'
    folder.mkdir()
    path = folder / 'input.json'
    path.write_bytes(b'{}')
    replacement = tmp_path / 'replacement.json'
    replacement.write_bytes(b'{"changed":true}')
    _, lease = load(monkeypatch, path)
    with lease:
        with pytest.raises(OSError):
            if action == 'write':
                with path.open('r+b'):
                    pass
            elif action == 'replace':
                os.replace(replacement, path)
            elif action == 'unlink':
                path.unlink()
            elif action == 'rename_parent':
                folder.rename(tmp_path / 'moved')
            else:
                os.link(path, tmp_path / 'new-link.json')
        assert path.read_bytes() == b'{}'
    assert path.read_bytes() == b'{}'


def test_preexisting_writer_rejects_before_cache_dispatch(tmp_path, monkeypatch):
    path = tmp_path / 'input.json'
    path.write_bytes(b'{}')
    _, lease = load(monkeypatch, path)
    original_open, original_read = Path.open, Path.read_bytes
    with path.open('r+b'):
        with pytest.raises(OSError):
            with lease:
                pytest.fail('writer admission must reject')
    assert Path.open is original_open and Path.read_bytes is original_read
    assert lease.closed_receipt()['remaining_code_handles'] == 0


@pytest.mark.parametrize('fault', ['pin', 'hardlink', 'oversize', 'missing'])
def test_failed_admission_restores_every_handle(tmp_path, monkeypatch, fault):
    path = tmp_path / 'input.json'
    path.write_bytes(b'{}')
    if fault == 'hardlink':
        os.link(path, tmp_path / 'alias.json')
    elif fault == 'oversize':
        path.write_bytes(b' ' * (256 * 1024 + 1))
    _, lease = load(monkeypatch, path, '0' * 64 if fault == 'pin' else None)
    if fault == 'missing':
        path.unlink()
    original_open, original_read = Path.open, Path.read_bytes
    with pytest.raises((ValueError, OSError)):
        with lease:
            pytest.fail('admission must reject')
    assert Path.open is original_open and Path.read_bytes is original_read
    assert lease.closed_receipt()['remaining_code_handles'] == 0
    if path.exists():
        with path.open('r+b'):
            pass


def test_nonallowlisted_input_remains_fresh_and_other_thread_does_not_hit(tmp_path, monkeypatch):
    path = tmp_path / 'input.json'
    path.write_bytes(b'{}')
    other = tmp_path / 'live.json'
    other.write_bytes(b'first')
    _, lease = load(monkeypatch, path)
    with lease:
        assert other.read_bytes() == b'first'
        other.write_bytes(b'second')
        assert other.read_bytes() == b'second'
        result = []
        thread = Thread(target=lambda: result.append(path.read_bytes()))
        thread.start()
        thread.join(5)
        assert not thread.is_alive() and result == [b'{}']
        assert lease.receipt()['code_lease']['immutable_input_read_hits'] == 0


def test_body_failure_retains_exception_and_releases_inputs(tmp_path, monkeypatch):
    path = tmp_path / 'input.json'
    path.write_bytes(b'{}')
    _, lease = load(monkeypatch, path)
    marker = RuntimeError('body failure')
    with pytest.raises(RuntimeError) as caught:
        with lease:
            assert path.read_bytes() == b'{}'
            raise marker
    assert caught.value is marker
    assert lease.closed_receipt()['remaining_code_handles'] == 0
    with path.open('r+b'):
        pass
