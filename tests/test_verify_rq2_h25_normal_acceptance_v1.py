import json
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import verify_rq2_h25_normal_acceptance_v1 as api


@pytest.fixture
def archive(tmp_path, monkeypatch):
    # Distinct synthetic archive: real source and record checks remain separate.
    pins = {}
    for name in ('native_record.json', 'intent.json', 'launch.json', 'observation.json'):
        raw = json.dumps({'synthetic': name}).encode()
        (tmp_path / name).write_bytes(raw)
        pins[name] = sha256(raw).hexdigest()
    raw = json.dumps({'file_sha256': dict(pins)}).encode()
    (tmp_path / 'result.json').write_bytes(raw)
    pins['result.json'] = sha256(raw).hexdigest()
    monkeypatch.setattr(api.entry, 'OUTPUT', tmp_path)
    monkeypatch.setattr(api, 'PINS', pins)
    return tmp_path


def test_complete_pinned_archive(archive):
    assert set(api.snapshot()) == set(api.PINS)


@pytest.mark.parametrize('name', sorted(api.PINS))
def test_any_bound_file_change_rejected(archive, name):
    with (archive / name).open('ab') as stream:
        stream.write(b' ')
    with pytest.raises(ValueError, match='pin mismatch'):
        api.snapshot()


def test_manifest_inventory_not_only_its_hash(archive, monkeypatch):
    raw = json.dumps({'file_sha256': {}}).encode()
    (archive / 'result.json').write_bytes(raw)
    monkeypatch.setitem(api.PINS, 'result.json', sha256(raw).hexdigest())
    with pytest.raises(ValueError, match='inventory'):
        api.snapshot()


def test_source_failure_does_not_touch_solver(archive, monkeypatch):
    def fail(*args):
        raise ValueError('injected source failure')
    def forbidden(*args, **kwargs):
        raise AssertionError('source failure must not solve')
    monkeypatch.setattr(api.entry, 'check', fail)
    monkeypatch.setattr(api.entry.run, 'solve_once', forbidden)
    with pytest.raises(ValueError, match='source failure'):
        api.verify()


@pytest.fixture
def guarded(archive, monkeypatch):
    source = api.entry.transport.source
    request = SimpleNamespace(source=SimpleNamespace(expected_input_identity='a' * 64))
    monkeypatch.setattr(api.entry, 'check', lambda *args: (request, 'b' * 64))
    monkeypatch.setattr(api.entry, 'validate_record', lambda *args: None)
    original_snapshot = api.snapshot
    def snapshot():
        result = original_snapshot()
        row = result['native_record.json']
        result['native_record.json'] = (row[0], row[1], b'{"numerical":{}}')
        return result
    monkeypatch.setattr(api, 'snapshot', snapshot)
    monkeypatch.setattr(source, '_prepare', lambda *args: (object(), None))
    monkeypatch.setattr(api.acceptance, 'assess_assignment', lambda *args, **kw: {})
    return ((api.entry.run, 'solve_once'), (api.entry.run.provenance.adapter, 'create_solver'),
            (source, 'run_source'), (source.kernel, 'run_normal_only'),
            (source.kernel.native, '_solve'))


@pytest.mark.parametrize('index', range(5))
def test_each_guard_blocks_and_all_restore(guarded, monkeypatch, index):
    originals = [(module, name, getattr(module, name)) for module, name in guarded]
    def attempt(*args):
        module, name = guarded[index]
        getattr(module, name)()
    monkeypatch.setattr(api.entry.transport.source, '_prepare', attempt)
    with pytest.raises(RuntimeError, match='solver forbidden'):
        api.verify()
    assert all(getattr(module, name) is original for module, name, original in originals)


def test_dependency_drift_rejects_and_restores(guarded, monkeypatch):
    originals = [(module, name, getattr(module, name)) for module, name in guarded]
    read = Path.read_bytes
    drift = [False]
    helper = Path(api.replay.__file__)
    def altered(path):
        raw = read(path)
        return raw + b' ' if drift[0] and path == helper else raw
    def assessment(*args, **kw):
        drift[0] = True
        return {}
    monkeypatch.setattr(Path, 'read_bytes', altered)
    monkeypatch.setattr(api.acceptance, 'assess_assignment', assessment)
    with pytest.raises(ValueError, match='implementation drift'):
        api.verify()
    assert all(getattr(module, name) is original for module, name, original in originals)


def test_success_restores_and_retains_mechanism_role(guarded):
    originals = [(module, name, getattr(module, name)) for module, name in guarded]
    result = api.verify()
    assert result['mechanism_initial_state'] is True
    assert result['observed_power_mapping'] is result['registered_coupling'] is False
    assert result['scope'] == 'retained_h25_numerical_normal_archive_only'
    assert all(getattr(module, name) is original for module, name, original in originals)
