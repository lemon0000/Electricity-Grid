from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path

import pytest

from src.solvers import rq2_normal_numerical_acceptance_v1 as api
from src.solvers import rq2_objective_provenance_run_v1 as run
from test_rq2_continuous_grid_normal_v1 import fixture
from test_rq2_objective_provenance_run_v1 import spec


@pytest.fixture(scope='module')
def observed():
    inputs = fixture(horizon=2)
    identity = api.stream.normal_input_identity(inputs)
    def builder():
        return api.stream.build_continuous_normal_model(inputs,
            expected_identity=identity,
            expected_implementation_identity=api.stream.implementation_identity())
    model = builder()
    scale = run.audit.model_scale(model)
    numerical = json.loads(run.solve_once(builder, spec(),
        expected_structure=run.audit._structure(model), max_variables=scale.variables,
        max_constraints=scale.constraints, max_payload_bytes=1000000,
        expected_implementation=run.implementation_identity()))
    kwargs = dict(expected_input_identity=identity,
        expected_runner_identity=run.implementation_identity(),
        expected_collector_sha256=sha256(Path(run.provenance.__file__).read_bytes()).hexdigest(),
        expected_adapter_identity=run.provenance.adapter.implementation_identity())
    return inputs, numerical, kwargs


def test_full_assignment_and_chronology_without_solver(observed, monkeypatch):
    inputs, numerical, kwargs = observed
    def forbidden(*args, **kw):
        raise AssertionError('audit must not solve')
    monkeypatch.setattr(run.provenance.adapter, 'create_solver', forbidden)
    report = api.assess_assignment(inputs, numerical, **kwargs)
    assert report['numerical_solver_optimality_accepted']
    assert report['normal_witness_errors'] == []
    assert report['solver_calls_by_verifier'] == 0
    for key in ('formal_result', 'security_certified', 'native_execution_authenticated',
                'whole_task_resources_verified', 'rigorous_exact_optimality_certified'):
        assert report[key] is False


@pytest.mark.parametrize('kind', ['source', 'structure', 'assignment', 'residual', 'runner'])
def test_mismatched_evidence_rejected(observed, kind):
    inputs, original, original_kwargs = observed
    numerical, kwargs = deepcopy(original), dict(original_kwargs)
    if kind == 'source': kwargs['expected_input_identity'] = '0' * 64
    if kind == 'structure': numerical['model_structure_identity'] = '0' * 64
    if kind == 'assignment': numerical['assignment'].pop()
    if kind == 'residual': numerical['maximum_residual'] = 0.1
    if kind == 'runner': kwargs['expected_runner_identity'] = '0' * 64
    with pytest.raises(ValueError):
        api.assess_assignment(inputs, numerical, **kwargs)


def test_chronology_failure_cannot_be_accepted(observed, monkeypatch):
    inputs, numerical, kwargs = observed
    audit = api.stream.audit_normal_assignment
    def failed(*args, **kw):
        witness = audit(*args, **kw)
        object.__setattr__(witness, 'errors', ('injected chronology failure',))
        object.__setattr__(witness, 'terminal_carry', None)
        return witness
    monkeypatch.setattr(api.stream, 'audit_normal_assignment', failed)
    report = api.assess_assignment(inputs, numerical, **kwargs)
    assert not report['numerical_solver_optimality_accepted']
    assert report['normal_witness_errors'] == ['injected chronology failure']
