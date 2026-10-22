"""Concrete current-guard gaps, with no Reader/solver or installed-file mutation."""
from pathlib import Path
from types import SimpleNamespace
import json

import pytest

from experiments import h1_phase_historical_batch_development_v2 as candidate
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_rq2_normal_h1_source_v1 import packet
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_source


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


def test_model_json_global_changes_same_typed_input_identity_after_bookends_pass(monkeypatch):
    current=packet()
    before=candidate._model_dependency_snapshot()
    original=candidate.model.json
    shim=SimpleNamespace(dumps=lambda *args,**kwargs:json.dumps(*args,**kwargs)+' ')
    with monkeypatch.context() as patch:
        patch.setattr(candidate.model,'json',shim)
        candidate._check_dependencies()
        candidate._model_dependencies_unchanged(before)
        assert candidate.model.normal_input_identity(current.inputs)!=current.input_identity
        # normal_h1_source also borrows the model's _digest program, so its
        # static-network identity check rejects before the later input check.
        with pytest.raises(ValueError,match='H1 static network drift or wrong type'):
            normal_h1_source.validate_current(current)
    assert candidate.model.json is original
    normal_h1_source.validate_current(current)


def test_path_sweep_returns_original_snapshot_then_changes_same_typed_input_identity(monkeypatch):
    current=packet();before=candidate._model_dependency_snapshot()
    original=Path.read_bytes;root=Path(candidate.model.__file__).resolve().parents[2]
    target=root/candidate.model.SOURCE_DEPENDENCIES[0];sweeps=[]
    def delayed_change(path):
        raw=original(path)
        if path==target:
            sweeps.append(len(sweeps)+1)
            if len(sweeps)>=2:return raw+b'\n# synthetic read-result fault\n'
        return raw
    with monkeypatch.context() as patch:
        patch.setattr(Path,'read_bytes',delayed_change)
        candidate._check_dependencies()
        candidate._model_dependencies_unchanged(before)
        assert sweeps==[1]
        assert candidate.model.normal_input_identity(current.inputs)!=current.input_identity
        with pytest.raises(ValueError,match='H1 current input drift'):
            normal_h1_source.validate_current(current)
    assert Path.read_bytes is original
    normal_h1_source.validate_current(current)
