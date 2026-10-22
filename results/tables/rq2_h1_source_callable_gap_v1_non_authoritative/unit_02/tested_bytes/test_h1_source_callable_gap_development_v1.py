"""Concrete current-guard gaps, with no Reader/solver or installed-file mutation."""
from pathlib import Path

import pytest

from experiments import h1_phase_historical_batch_development_v2 as candidate
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def test_model_number_global_can_drift_while_current_bookends_pass(monkeypatch):
    before=candidate._model_dependency_snapshot()
    assert candidate.model._number(1.,'probe')==1.
    with monkeypatch.context() as patch:
        patch.setattr(candidate.model,'isfinite',lambda value:False)
        candidate._check_dependencies()
        candidate._model_dependencies_unchanged(before)
        with pytest.raises(ValueError,match='finite built-in number'):
            candidate.model._number(1.,'probe')
    candidate._check_dependencies()
    assert candidate.model._number(1.,'probe')==1.


def test_imported_validator_global_can_drift_while_current_bookends_pass(monkeypatch):
    before=candidate._model_dependency_snapshot()
    namespace=candidate.model._validate_request.__globals__
    original=namespace['_finite']
    def changed(*args,**kwargs):raise ValueError('named validator-global fault')
    with monkeypatch.context() as patch:
        patch.setitem(namespace,'_finite',changed)
        candidate._check_dependencies()
        candidate._model_dependencies_unchanged(before)
        with pytest.raises(ValueError,match='named validator-global fault'):
            namespace['_finite'](1.,'probe')
    assert namespace['_finite'] is original
    candidate._check_dependencies()


def test_path_read_callable_alias_is_not_guarded_if_it_returns_same_bytes(monkeypatch):
    before=candidate._model_dependency_snapshot()
    original=Path.read_bytes;calls=[]
    def passthrough(path):
        calls.append(str(path))
        return original(path)
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_bytes',passthrough)
        candidate._check_dependencies()
        candidate._model_dependencies_unchanged(before)
    assert calls  # This is a reachable changed callable, with unchanged snapshot values.
    assert Path.read_bytes is original
    candidate._check_dependencies()
