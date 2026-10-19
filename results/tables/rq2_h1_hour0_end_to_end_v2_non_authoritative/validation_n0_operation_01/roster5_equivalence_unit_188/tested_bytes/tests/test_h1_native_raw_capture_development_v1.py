import json
import struct
from types import SimpleNamespace

import pytest
from pyomo.common.collections import ComponentMap
from pyomo.solvers.plugins.solvers.direct_solver import DirectSolver

from experiments import h1_native_raw_capture_development_v1 as api
from tests.test_h1_linear_export_guard_development_v1 import case
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, spec


class FakeDirect:
    # Use the installed Pyomo driver, but never instantiate a Gurobi object.
    solve = DirectSolver.solve

    def __init__(self, model, native, args, path, fault):
        self.model, self.native, self.args, self.path, self.fault = model, native, args, path, fault
        self.options = {}
        self.apply_calls = self.post_calls = self.close_calls = 0
        self._report_timing = self._save_results = False
        self.name = 'synthetic_direct'

    def available(self, **kwargs): return True
    def _options_string_to_dict(self, value): return {}
    def _initialize_callbacks(self, model): pass

    def _presolve(self, model, **kwargs):
        assert kwargs == dict(load_solutions=False, tee=False)
        self._pyomo_model, self._solver_model = model, self.native
        self._callback = object() if self.fault == 'callback' else None
        self._tee = self._keepfiles = False
        self._pyomo_var_to_solver_var_map = ComponentMap(self.args['variable_forward'])
        self._solver_var_to_pyomo_var_map = dict(self.args['variable_reverse'])
        self._pyomo_con_to_solver_con_map = ComponentMap(self.args['constraint_forward'])
        self._solver_con_to_pyomo_con_map = dict(self.args['constraint_reverse'])
        if self.fault == 'options': self.options['Threads'] = 2

    def _apply_solver(self):
        self.apply_calls += 1
        assert (self.path/'native_raw/000/intent.json').exists()
        assert not (self.path/'native_raw/000/raw.bin').exists()
        if self.fault == 'apply': raise RuntimeError('synthetic optimize error')
        if self.fault == 'negative': self.native.variables[0].X = -1e-12
        if self.fault == 'nonfinite': self.native.variables[0].X = float('nan')
        if self.fault == 'missing': del self.native.variables[0].X
        if self.fault == 'no_incumbent': self.native.SolCount = 0
        if self.fault == 'binding_drift': (self.path/'specification.json').write_bytes(b'{}')
        return SimpleNamespace(rc=0)

    def _postsolve(self):
        self.post_calls += 1
        raw = self.path/'native_raw/000/raw.bin'
        receipt = self.path/'native_raw/000/raw_receipt.json'
        assert raw.exists() and receipt.exists()
        doc = json.loads(receipt.read_bytes())
        assert doc['raw_sha256'] == api.io.digest(raw.read_bytes())
        if self.fault == 'postsolve': raise RuntimeError('postsolve failure')
        if self.fault == 'second_apply': self._apply_solver()
        if self.fault == 'native_drift': self.native.variables[0].X = 2.
        if self.fault == 'matrix_drift': self.native.constraints[0].RHS = 7.
        if self.fault == 'model_drift': self.model.x.set_value(1.)
        return SimpleNamespace(synthetic_results=True)

    def close(self):
        self.close_calls += 1
        if self.fault == 'close': raise RuntimeError('close failure')
        if self.fault == 'close_metadata_drift': (self.path/'binding.json').write_bytes(b'{}')
        if self.fault == 'close_raw_drift': (self.path/'native_raw/000/raw.bin').write_bytes(b'{}')


@pytest.fixture
def setup_case(tmp_path, monkeypatch, no_solver):
    def setup(fault=None):
        model, native, args = case()
        for i, v in enumerate(native.variables):
            v.VarName, v.X = 'v'+str(i), (1., 0., 2.)[i]
        for name, value in dict(Status=2, SolCount=1, ObjVal=5., ObjBound=5., ObjBoundC=5., Runtime=0.01, MIPGap=0.).items():
            setattr(native, name, value)
        native.update = lambda: None
        path = tmp_path/'capture'
        instance = FakeDirect(model, native, args, path, fault)
        monkeypatch.setattr(api, 'GurobiDirect', FakeDirect)
        monkeypatch.setattr(api.old.provenance.adapter, 'create_solver',
                            lambda specification: (instance, api.old.audit.solver_options(specification)))
        owner = api.StageCapture(path, request_sha256='a'*64,
            expected_structure=api.old.audit._structure(model), expected_implementation=api.implementation_identity())
        return model, native, instance, owner
    return setup


def raw(owner):
    return json.loads((owner.raw.root/'000/raw.bin').read_bytes())


def test_actual_pyomo_driver_raw_before_postsolve_and_consumer(setup_case):
    model, native, solver, owner = setup_case()
    def consumer(data, results, owned_model):
        assert solver.post_calls == 1 and owned_model is model and results.synthetic_results
        assert data == (owner.raw.root/'000/raw.bin').read_bytes()
        assert not (owner.root/'complete.json').exists()
        return 'callback_result_only'
    assert owner.run(lambda: model, spec(), consumer) == 'callback_result_only'
    assert (solver.apply_calls, solver.post_calls, solver.close_calls) == (1, 1, 1)
    doc = raw(owner)
    assert doc['variables'][0]['attributes']['X']['atom'] == dict(kind='binary64', value=(1.).hex(), bits='3ff0000000000000')
    for record in (doc, json.loads((owner.root/'binding.json').read_bytes()),
                   json.loads((owner.root/'complete.json').read_bytes())):
        assert all(record[key] is False for key in api.FLAGS)
    assert not doc['values_transformed'] and not doc['scientific_acceptance']
    assert owner.complete and not owner.poisoned
    with pytest.raises(ValueError, match='consumed'):
        owner.run(lambda: model, spec(), consumer)
    assert solver.apply_calls == 1


@pytest.mark.parametrize('fault,post_calls', [('apply', 0), ('missing', 0), ('no_incumbent', 0),
    ('postsolve', 1), ('native_drift', 1), ('matrix_drift', 1), ('model_drift', 1),
    ('binding_drift', 1), ('second_apply', 1), ('close', 1),
    ('close_metadata_drift', 1), ('close_raw_drift', 1)])
def test_failure_retains_evidence_and_stops(setup_case, fault, post_calls):
    model, native, solver, owner = setup_case(fault)
    consumers = []
    with pytest.raises((ValueError, RuntimeError)):
        owner.run(lambda: model, spec(), lambda *args: consumers.append(1))
    assert solver.apply_calls == 1 and solver.post_calls == post_calls and solver.close_calls == 1
    assert (owner.raw.root/'000/raw.bin').exists() and (owner.raw.root/'000/raw_receipt.json').exists()
    assert (owner.raw.root/'aborted.json').exists() and not (owner.root/'complete.json').exists()
    assert owner.poisoned and not owner.complete
    assert consumers == ([1] if fault in ('close', 'close_metadata_drift', 'close_raw_drift') else [])
    if fault == 'apply': assert raw(owner)['apply_error'] == 'RuntimeError'
    if fault == 'missing': assert raw(owner)['variables'][0]['attributes']['X']['available'] is False
    if fault == 'native_drift': assert raw(owner)['variables'][0]['attributes']['X']['atom']['value'] == (1.).hex()
    with pytest.raises(ValueError): owner.run(lambda: model, spec(), lambda *args: None)
    assert solver.apply_calls == 1


@pytest.mark.parametrize('fault', ['negative', 'nonfinite'])
def test_original_numeric_witness_survives_consumer_rejection(setup_case, fault):
    model, native, solver, owner = setup_case(fault)
    expected = (-1e-12).hex() if fault == 'negative' else 'nan'
    def reject(data, *args):
        assert json.loads(data)['variables'][0]['attributes']['X']['atom']['value'] == expected
        raise ValueError('scientific audit rejected')
    with pytest.raises(ValueError, match='scientific audit'):
        owner.run(lambda: model, spec(), reject)
    assert raw(owner)['variables'][0]['attributes']['X']['atom']['value'] == expected
    assert solver.apply_calls == 1 and owner.poisoned


@pytest.mark.parametrize('fault', ['callback', 'options', 'export'])
def test_preapply_rejection_never_calls_solver(setup_case, fault):
    model, native, solver, owner = setup_case(fault)
    if fault == 'export': native.constraints[0].RHS = 7.
    with pytest.raises(ValueError): owner.run(lambda: model, spec(), lambda *args: pytest.fail('consumer forbidden'))
    assert solver.apply_calls == 0 and solver.close_calls == 1 and owner.poisoned
    assert not (owner.raw.root/'000/raw.bin').exists()


@pytest.mark.parametrize('filename', ['raw.bin', 'raw_receipt.json'])
def test_storage_failure_prevents_postsolve_and_consumer(setup_case, monkeypatch, filename):
    model, native, solver, owner = setup_case()
    original = api.io.write_new
    def fail(path, data):
        if path.name == filename: raise OSError('injected storage failure')
        return original(path, data)
    monkeypatch.setattr(api.io, 'write_new', fail)
    with pytest.raises(OSError): owner.run(lambda: model, spec(), lambda *args: pytest.fail('consumer forbidden'))
    assert solver.apply_calls == 1 and solver.post_calls == 0 and solver.close_calls == 1
    assert owner.poisoned and not (owner.root/'complete.json').exists()
    assert (owner.raw.root/'000/raw.bin').exists() is (filename == 'raw_receipt.json')


def test_consumer_reentry_cannot_start_second_solver(setup_case):
    model, native, solver, owner = setup_case()
    def consume(*args):
        with pytest.raises(ValueError, match='active'):
            owner.run(lambda: model, spec(), lambda *a: None)
        return None
    owner.run(lambda: model, spec(), consume)
    assert solver.apply_calls == 1 and owner.complete


@pytest.mark.parametrize('bits', ['8000000000000000', '7ff8000000001234', 'fff8000000004321'])
def test_exact_binary64_payload_retention(setup_case, bits):
    model, native, solver, owner = setup_case()
    native.variables[0].X = struct.unpack('>d', bytes.fromhex(bits))[0]
    def reject(data, *args):
        assert json.loads(data)['variables'][0]['attributes']['X']['atom']['bits'] == bits
        raise ValueError('downstream rejection')
    with pytest.raises(ValueError, match='downstream'):
        owner.run(lambda: model, spec(), reject)
    assert raw(owner)['variables'][0]['attributes']['X']['atom']['bits'] == bits


@pytest.mark.parametrize('point', ['finish_before', 'finish_after', 'complete_before', 'complete_after'])
def test_terminal_and_publication_failures_remain_unresolved(setup_case, monkeypatch, point):
    model, native, solver, owner = setup_case()
    if point.startswith('finish'):
        original = owner.raw.finish
        def fail():
            if point == 'finish_after': original()
            raise OSError('finish injection')
        monkeypatch.setattr(owner.raw, 'finish', fail)
    else:
        original = api.io.write_metadata
        def fail(path, data):
            if path.name != 'complete.json': return original(path, data)
            if point == 'complete_after': original(path, data)
            raise OSError('complete injection')
        monkeypatch.setattr(api.io, 'write_metadata', fail)
    with pytest.raises(OSError): owner.run(lambda: model, spec(), lambda *a: None)
    assert owner.poisoned and not owner.complete
    assert solver.apply_calls == solver.close_calls == 1
    assert (owner.raw.root/'000/raw.bin').exists()
    assert (owner.raw.root/'terminal.json').exists() is (point != 'finish_before')
    assert (owner.raw.root/'aborted.json').exists() is (point == 'finish_before')
    assert (owner.root/'complete.json').exists() is (point == 'complete_after')
    with pytest.raises(ValueError): owner.run(lambda: model, spec(), lambda *a: None)


@pytest.mark.parametrize('dependency', ['guard', 'syntax', 'grammar'])
def test_inherited_dependency_drift_rejected_before_solver(setup_case, monkeypatch, tmp_path, dependency):
    model, native, solver, owner = setup_case()
    module = api.inherited_guard if dependency == 'guard' else getattr(api.inherited_guard, dependency)
    fake = tmp_path/(dependency+'.py')
    fake.write_bytes(b'changed dependency')
    monkeypatch.setattr(module, '__file__', str(fake))
    with pytest.raises(ValueError, match='implementation changed'):
        owner.run(lambda: model, spec(), lambda *a: None)
    assert solver.apply_calls == 0
