from pathlib import Path

import pytest

from tests.test_rq2_normal_numerical_execution_v1 import (
    supplied, legacy_request, declared_source, prepared_source, bound_source, source_supplied, setup, worker)


def test_legacy_wire_definition_drift_changes_worker_identity(supplied, tmp_path_factory, monkeypatch):
    args = setup(supplied, tmp_path_factory)
    prior = worker.transport.implementation_identity(supplied)
    read = Path.read_bytes
    target = Path(worker.transport.legacy.__file__).resolve()
    monkeypatch.setattr(Path, 'read_bytes', lambda p: read(p)+b' ' if p.resolve() == target else read(p))
    assert worker.transport.implementation_identity(supplied) != prior
    with pytest.raises(ValueError, match='implementation drift'):
        worker.run_worker(**args)
    assert not args['root'].exists()


def test_wire_inventory_is_part_of_implementation_identity(supplied, monkeypatch):
    prior = worker.transport.implementation_identity(supplied)
    monkeypatch.setattr(worker.transport, 'CLASSES', worker.transport.CLASSES[:-1])
    assert worker.transport.implementation_identity(supplied) != prior
