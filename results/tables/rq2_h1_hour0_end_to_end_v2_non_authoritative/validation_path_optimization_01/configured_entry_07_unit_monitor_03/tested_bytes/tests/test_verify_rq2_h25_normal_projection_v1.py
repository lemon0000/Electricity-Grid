from pathlib import Path
from types import SimpleNamespace

import pytest

from experiments import verify_rq2_h25_normal_projection_v1 as entry


@pytest.mark.parametrize('fault', ['wrapper', 'projection'])
def test_changed_verifier_cannot_return_archive_assessment(monkeypatch, fault):
    # Isolate the wrapper's final drift gate; numerical replay has its own suite.
    monkeypatch.setattr(entry.retained, 'snapshot', lambda: {
        'native_record.json': (0, '0'*64, b'{"numerical":{}}')})
    monkeypatch.setattr(entry.retained.entry, 'check', lambda *a: (object(), '1'*64))
    monkeypatch.setattr(entry.retained.entry, 'validate_record', lambda *a: None)
    monkeypatch.setattr(entry.api, 'binding_identity', lambda *a, **k: '2'*64)
    monkeypatch.setattr(entry.api, 'implementation_identity', lambda: '3'*64)
    original_read = Path.read_bytes
    def project(*args, **kwargs):
        if fault == 'wrapper':
            monkeypatch.setattr(Path, 'read_bytes', lambda p: original_read(p)+b' '
                if p.resolve() == Path(entry.__file__).resolve() else original_read(p))
        else: monkeypatch.setattr(entry.api, 'implementation_identity', lambda: '4'*64)
        return {}, SimpleNamespace(hours=(None,)*25, network=SimpleNamespace(units=(None,)*158))
    monkeypatch.setattr(entry.api, 'prepare_information', project)
    original_solver = entry.api.capture.solve_once
    with pytest.raises(ValueError, match='implementation drift'): entry.verify()
    assert entry.api.capture.solve_once is original_solver
